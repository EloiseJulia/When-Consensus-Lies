"""Resumable, cache-backed, RPM-throttled experiment runner for When Consensus Lies.

# Implementer model family: Claude/Anthropic

Deliverables (per paper/plans/2026-07-16-phase3-runner-plan.md):
  1. Grid enumeration: cross-product (task, config, seed) keyed by AgentRun identity
  2. Checkpoint/resume: append-only JSONL, fsync per record; skip done jobs on restart
  3. RPM throttle: per-model sliding-window limiter; day-cap stops model cleanly
  4. Cache-first; --dry-run reports pending vs done without any network
  5. Budget passthrough: BudgetExceeded stops cleanly and checkpoints
  6. Infra-error discipline: transient errors retried, NEVER checkpointed on failure
  7. Observability: structured progress + per-condition I_perp RATE diagnostic

Guards (same discipline as scripts/mini_pilot.py):
  Live execution requires BOTH: RUNNER_LIVE=1 env var AND GITHUB_MODELS_TOKEN present.
  Without both guards, main() prints "skipped" and exits 0 — no network, no cost.

Token safety: the token is NEVER printed, logged, or included in any error message.
"""

from __future__ import annotations

import collections
import copy
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple
from urllib.parse import urlsplit, urlunsplit

from common.llm import (
    GITHUB_MODELS_BASE_URL,
    PROVIDER_GITHUB_MODELS,
    BudgetExceeded,
    DayCapped,
    LLMClient,
)
from common.schema import AgentRun, Task
from harness.label import label_run as _default_label_run
from harness.run import run_task as _default_run_task


class LedgerWriteError(Exception):
    """Raised when the aggregate cost-ledger journal write fails.

    Treated as a PERMANENT (non-retried) infra failure for the job: retrying
    would re-run the completion, cache-hit at $0 incremental cost, and silently
    lose the original spend from the aggregate.  Failing closed instead keeps the
    accounting honest — the job is reported failed and is NOT marked done.
    """


# ── AgentRun identity helpers ────────────────────────────────────────────────

def _normalize_base_url(base_url: Optional[str]) -> str:
    """Normalize a base URL for use in a checkpoint namespace.

    Lowercases ONLY the case-insensitive components — the scheme and the host/port
    (netloc) — and strips a single trailing slash, so
    ``http://127.0.0.1:8313/v1`` and ``http://127.0.0.1:8313/v1/`` are the SAME
    namespace. The PATH case is PRESERVED (URL paths are case-sensitive per
    RFC 3986), so ``/API`` and ``/api`` remain DISTINCT endpoints. Different
    hosts/ports/paths always stay distinct.
    """
    raw = (base_url or "").strip().rstrip("/")
    if not raw:
        return ""
    parts = urlsplit(raw)
    if not parts.scheme and not parts.netloc:
        # Not a standard scheme://host URL (e.g. a bare path) — preserve as-is
        # (only surrounding whitespace + trailing slash already stripped).
        return raw
    # scheme + netloc (host:port) are case-insensitive → lowercase; path/query/
    # fragment are case-SENSITIVE → preserve exactly.
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, parts.fragment)
    )


def endpoint_identity(provider: Optional[str], base_url: Optional[str]) -> str:
    """Canonical namespace string for an online endpoint (provider + base_url).

    Used to namespace runner CHECKPOINT identities so that jobs executed against
    genuinely different endpoints — e.g. ``github_models`` vs ``copilot_proxy``, or
    the same provider on a different host/port — are DISTINCT checkpoint entries.
    Without this, switching provider or proxy port would let a stale ``job_done``
    marker silently skip (or dedup) the new endpoint's execution.

    BACKWARD COMPAT: the canonical default endpoint (``github_models`` at its
    default base URL) maps to the EMPTY namespace ``""`` so existing checkpoints
    and their 5-dim job keys are byte-for-byte unchanged. Any other provider or
    base_url yields a distinct non-empty namespace.

    This is a RUNNER-internal identity dimension only; it is intentionally NOT part
    of the frozen ``common/schema.py`` ``AgentRun`` identity.
    """
    if (
        provider == PROVIDER_GITHUB_MODELS
        and _normalize_base_url(base_url) == _normalize_base_url(GITHUB_MODELS_BASE_URL)
    ):
        return ""
    return "\x00".join([provider or "", _normalize_base_url(base_url)])


def run_identity(run: AgentRun, endpoint: str = "") -> str:
    """Canonical string key for AgentRun identity.

    Encodes task_id × config × model_role × model_id × seed, which is the
    identity dimension defined in schema.py.  Null-byte separators prevent
    collisions between field values that contain the separator character.

    ``endpoint`` (default "") is an OPTIONAL runner-level namespace prefix
    (provider + normalized base_url via :func:`endpoint_identity`) so that the
    SAME AgentRun identity executed against different online endpoints is stored
    as distinct checkpoint records. When it is "" (the canonical default) the key
    is BYTE-IDENTICAL to the pre-change 5-field value — the endpoint dimension is
    prepended ONLY when non-empty.
    """
    parts = [
        run.task_id,
        run.config,
        run.model_role,
        run.model_id,
        str(run.seed),
    ]
    if endpoint:
        parts.insert(0, endpoint)
    return "\x00".join(parts)


def job_key(
    task_id: str,
    config: str,
    model_role: str,
    model_id: str,
    seed: int,
    endpoint: str = "",
) -> str:
    """Canonical completion key for a runner job.

    BLOCKER 1 fix: the job key MUST carry the FULL five-dimensional AgentRun
    identity — ``task_id × config × model_role × model_id × seed`` — so that a
    job which differs only in role or model is treated as distinct, not-yet-done
    work.  A key that omits model identity would let a changed/added model reuse
    a stale ``job_done`` marker and silently SKIP the new work on resume.

    PROVIDER fix: an OPTIONAL leading ``endpoint`` namespace (provider +
    normalized base_url) makes a job on ``copilot_proxy`` distinct from the same
    job on ``github_models`` (or on a different proxy port), so resume never skips
    or dedups a genuinely different endpoint's execution. When ``endpoint`` is ""
    (the canonical default) the key is BYTE-IDENTICAL to the pre-change 5-field
    value — the endpoint dimension is prepended ONLY when non-empty — and it
    mirrors :func:`run_identity` exactly.

    Null-byte separators prevent collisions between field values that contain the
    separator character.
    """
    parts = [
        task_id,
        config,
        model_role,
        model_id,
        str(seed),
    ]
    if endpoint:
        parts.insert(0, endpoint)
    return "\x00".join(parts)


# ── Checkpoint store ─────────────────────────────────────────────────────────

class CheckpointStore:
    """Append-only JSONL checkpoint for AgentRun records.

    Two record types written to the same JSONL file:
    - ``{"type": "run", ...AgentRun fields..., "label": ...}``
    - ``{"type": "job_done", "task_id", "config", "model_role", "model_id", "seed"}``
    - ``{"type": "cost_delta", "cost_usd": <float>}`` (aggregate budget ledger)

    Write discipline (crash safety):
    - Every ``add_run()`` and ``mark_job_done()`` call does ``flush() + fsync()``
      before returning, so the OS page cache is durably flushed to disk.
    - A hard kill (SIGKILL, power loss) loses at most the single AgentRun being
      processed at crash time.  The surrounding job is NOT marked done, so it
      re-runs on the next invocation.  The LLM disk cache ensures no duplicate
      HTTP calls for already-computed (identity) prompts.

    Idempotency:
    - ``add_run()`` is a no-op if the run's identity is already in the store.
    - ``mark_job_done()`` is a no-op if the job key is already in the store.
    Both operations are safe to call multiple times.

    Corruption resilience: JSON decode errors on individual lines are skipped
    silently so a single corrupt write does not prevent loading the rest.
    """

    def __init__(self, path: Path, endpoint: str = "") -> None:
        self._path = Path(path)
        # Runner-level endpoint namespace (provider + normalized base_url). All
        # job/run identities produced by THIS store are namespaced by it so a
        # single checkpoint file can safely hold progress for multiple endpoints
        # without cross-serving or falsely skipping a different endpoint's jobs.
        self._endpoint = endpoint
        self._done_jobs: Set[str] = set()
        self._run_ids: Set[str] = set()
        self._runs: List[Dict[str, Any]] = []
        # BLOCKER 2: aggregate cost ledger — accumulated across jobs AND resumes.
        self._aggregate_cost_usd: float = 0.0
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        with open(self._path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue  # corrupt line — skip, do not crash
                rtype = rec.get("type")
                if rtype == "job_done":
                    # MAJOR C: legacy (pre 5-dim) job_done markers written before
                    # this change lack model_role/model_id.  Never crash on them —
                    # treat a marker missing any identity field as INCOMPLETE so
                    # the job re-runs (and cache-hits make it cheap) rather than
                    # falsely-skipping or KeyError-ing on load.
                    if not all(
                        k in rec for k in ("task_id", "config", "model_role", "model_id", "seed")
                    ):
                        continue  # legacy/partial marker → re-run on next invocation
                    try:
                        self._done_jobs.add(
                            job_key(
                                rec["task_id"],
                                rec["config"],
                                rec["model_role"],
                                rec["model_id"],
                                int(rec["seed"]),
                                # Legacy markers predate endpoint namespacing → "".
                                endpoint=rec.get("endpoint", ""),
                            )
                        )
                    except (TypeError, ValueError):
                        continue  # malformed seed etc. → treat as incomplete
                elif rtype == "cost_delta":
                    # BLOCKER 2: replay the persisted ledger so the aggregate
                    # budget continues from the running total across resumes.
                    try:
                        self._aggregate_cost_usd += float(rec["cost_usd"])
                    except (KeyError, TypeError, ValueError):
                        continue  # malformed cost record — skip
                elif rtype == "run":
                    run = AgentRun(
                        task_id=rec["task_id"],
                        config=rec["config"],
                        model_role=rec["model_role"],
                        model_id=rec["model_id"],
                        output=rec["output"],
                        label=rec["label"],
                        verbalized_conf=float(rec["verbalized_conf"]),
                        logit_conf=rec.get("logit_conf"),
                        seed=int(rec["seed"]),
                    )
                    rid = run_identity(run, endpoint=rec.get("endpoint", ""))
                    if rid not in self._run_ids:
                        self._run_ids.add(rid)
                        self._runs.append(rec)

    def job_done(
        self,
        task_id: str,
        config: str,
        model_role: str,
        model_id: str,
        seed: int,
    ) -> bool:
        """True iff this job (full 5-dim identity) has been checkpointed done."""
        return (
            job_key(task_id, config, model_role, model_id, seed, endpoint=self._endpoint)
            in self._done_jobs
        )

    def run_done(self, run: AgentRun) -> bool:
        """True iff this specific AgentRun identity has been checkpointed."""
        return run_identity(run, endpoint=self._endpoint) in self._run_ids

    def _write(self, record: Dict[str, Any]) -> None:
        """Append one record to the JSONL file and fsync."""
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def add_run(self, run: AgentRun) -> None:
        """Checkpoint a single AgentRun.  Idempotent by identity."""
        rid = run_identity(run, endpoint=self._endpoint)
        if rid in self._run_ids:
            return  # already stored — idempotent, no duplicate write
        record: Dict[str, Any] = {
            "type": "run",
            "task_id": run.task_id,
            "config": run.config,
            "model_role": run.model_role,
            "model_id": run.model_id,
            "output": run.output,
            "label": run.label,
            "verbalized_conf": run.verbalized_conf,
            "logit_conf": run.logit_conf,
            "seed": run.seed,
        }
        # Persist the endpoint namespace ONLY when non-empty so default-provider
        # records are byte-for-byte identical to the pre-change format.
        if self._endpoint:
            record["endpoint"] = self._endpoint
        self._write(record)
        self._run_ids.add(rid)
        self._runs.append(record)

    def mark_job_done(
        self,
        task_id: str,
        config: str,
        model_role: str,
        model_id: str,
        seed: int,
    ) -> None:
        """Mark a job (full 5-dim identity) as fully complete.  Idempotent."""
        k = job_key(task_id, config, model_role, model_id, seed, endpoint=self._endpoint)
        if k in self._done_jobs:
            return  # already marked — idempotent
        record: Dict[str, Any] = {
            "type": "job_done",
            "task_id": task_id,
            "config": config,
            "model_role": model_role,
            "model_id": model_id,
            "seed": seed,
        }
        # Persist the endpoint namespace ONLY when non-empty so default-provider
        # job_done markers are byte-for-byte identical to the pre-change format.
        if self._endpoint:
            record["endpoint"] = self._endpoint
        self._write(record)
        self._done_jobs.add(k)

    def add_cost(self, delta_usd: float) -> None:
        """Append an incremental cost to the persisted aggregate ledger.

        BLOCKER 2 fix: budget is a HARD AGGREGATE cap across the whole run and
        across resumes.  Each job's incurred cost is appended here (fsync'd) so
        the running total survives restarts.  Completed jobs are skipped on
        resume, so their already-persisted cost is never double-counted.
        A zero/negative delta is ignored to avoid cluttering the ledger.
        """
        if delta_usd <= 0.0:
            return
        self._write({"type": "cost_delta", "cost_usd": float(delta_usd)})
        self._aggregate_cost_usd += float(delta_usd)

    @property
    def aggregate_cost_usd(self) -> float:
        """Total incurred cost across all jobs and resumes (persisted ledger)."""
        return self._aggregate_cost_usd

    def all_runs(self) -> List[Dict[str, Any]]:
        """Return all checkpointed AgentRun records (read-only copy)."""
        return list(self._runs)

    @property
    def n_done_jobs(self) -> int:
        """Number of fully-completed jobs in the checkpoint."""
        return len(self._done_jobs)

    @property
    def n_runs(self) -> int:
        """Number of individual AgentRun records in the checkpoint."""
        return len(self._run_ids)


# ── RPM throttler ────────────────────────────────────────────────────────────

class RpmThrottler:
    """Per-model sliding-window RPM limiter (60-second window).

    Tracks request timestamps per model slug in a deque.  ``acquire()`` blocks
    until a slot is available within the current 60-second window.

    ``_time_fn`` and ``_sleep_fn`` are injected so tests can control the clock
    without real wall-clock delays.

    ``rpm=0`` disables throttling entirely (useful in offline tests).
    """

    def __init__(
        self,
        rpm: int,
        _time_fn: Callable[[], float] = time.time,
        _sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._rpm = rpm
        self._time_fn = _time_fn
        self._sleep_fn = _sleep_fn
        self._windows: Dict[str, Deque[float]] = (
            collections.defaultdict(collections.deque)
        )

    def acquire(self, model_slug: str) -> None:
        """Block until a request slot is available for *model_slug*.

        Records the slot timestamp immediately on return so the caller does not
        need to call a separate ``record()`` method.
        """
        if self._rpm <= 0:
            return  # unlimited — never block
        window = self._windows[model_slug]
        while True:
            now = self._time_fn()
            cutoff = now - 60.0
            while window and window[0] < cutoff:
                window.popleft()
            if len(window) < self._rpm:
                window.append(now)
                return
            # Window full — wait for oldest entry to expire
            wait = 60.0 - (now - window[0]) + 0.05
            self._sleep_fn(max(wait, 0.0))

    def current_rate(self, model_slug: str) -> int:
        """Count of requests in the last 60 seconds for *model_slug*."""
        window = self._windows.get(model_slug, collections.deque())
        cutoff = self._time_fn() - 60.0
        return sum(1 for t in window if t >= cutoff)


# ── Throttled-client wrapper ─────────────────────────────────────────────────

class _ThrottledClient:
    """Duck-type LLMClient wrapper adding per-model RPM throttling, day-cap guard,
    and PER-COMPLETION cost journaling.

    Exposes the same interface as LLMClient (``complete()``, ``config``,
    ``cache_dir``, ``offline``) so it can be passed directly to ``run_task()``.

    Day-cap guard: if a model slug is in ``day_capped_models``, ``complete()``
    raises ``DayCapped`` immediately without touching the underlying client.
    This propagates cleanly through ``run_task()`` to the runner's catch block,
    where the model is registered and all future jobs for it are also skipped.

    BLOCKER B (crash-safe cost): each ``complete()`` measures the incremental
    cost the underlying client actually incurred and durably journals it via
    ``cost_sink`` IMMEDIATELY — before the surrounding job returns.  A crash
    after a paid completion but before ``mark_job_done`` therefore cannot lose
    that spend (the ledger entry is already fsync'd), and re-runs cache-hit at
    zero incremental cost so there is no double-count.
    """

    def __init__(
        self,
        underlying: LLMClient,
        throttler: RpmThrottler,
        day_capped_models: Set[str],
        cost_sink: Optional[Callable[[float], None]] = None,
    ) -> None:
        self._c = underlying
        self._throttler = throttler
        self._day_capped = day_capped_models
        self._cost_sink = cost_sink

    @property
    def config(self) -> Dict[str, Any]:
        return self._c.config

    @property
    def cache_dir(self) -> Path:
        return self._c.cache_dir

    @property
    def offline(self) -> bool:
        return self._c.offline

    @staticmethod
    def _cost_of(client: Any) -> float:
        return float(getattr(client, "_total_cost_usd", 0.0) or 0.0)

    def complete(
        self,
        role: str,
        prompt: str,
        seed: Optional[int] = None,
        max_retries: int = 3,
        family: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Any:
        """Throttle + day-cap guard, delegate, then journal incremental cost.

        Cost is journaled PER PAID completion via ``cost_sink`` (fsync'd), so a
        crash after paid completions but before the job is marked done cannot
        undercount the aggregate on resume.

        FAIL-CLOSED ledger write: if the journal write itself raises, a permanent
        ``LedgerWriteError`` is surfaced so the job is treated as an infra failure
        and is NEVER retried into a $0 cache-hit that would silently lose the
        spend (the auditor's logic hole).

        ACCEPTED LIMITATION (Manager decision-log row 31): a hard SIGKILL between
        the paid HTTP call and the fsync'd journal write can lose at most ONE
        call's cost (~$0.0001) from the ledger.  This is deliberately NOT guarded
        by worst-case pre-authorization / reserve-settle, because RATE LIMITS —
        not dollars — are the binding constraint for this research cost-guard.
        """
        # Resolve slug for per-model throttling/day-cap checks
        if model is not None:
            slug = model
        else:
            from common.config import model_for_role
            slug = model_for_role(role, self._c.config)["model"]

        if slug in self._day_capped:
            raise DayCapped(slug)

        self._throttler.acquire(slug)
        cost_before = self._cost_of(self._c)
        try:
            result = self._c.complete(
                role=role,
                prompt=prompt,
                seed=seed,
                max_retries=max_retries,
                family=family,
                model=model,
                temperature=temperature,
            )
        except BaseException:
            # The underlying call itself failed.  Best-effort journal any spend
            # that still landed (partial charge), then propagate the ORIGINAL
            # error — a sink error here must not mask the real failure.
            delta = self._cost_of(self._c) - cost_before
            if delta > 0.0 and self._cost_sink is not None:
                try:
                    self._cost_sink(delta)
                except Exception:
                    pass
            raise

        # Success path: journal the incremental cost.  FAIL CLOSED — if the
        # journal write raises, convert it into a permanent LedgerWriteError so
        # the job fails (not marked done, not retried into a $0 cache-hit).
        delta = self._cost_of(self._c) - cost_before
        if delta > 0.0 and self._cost_sink is not None:
            try:
                self._cost_sink(delta)
            except Exception as exc:
                raise LedgerWriteError(
                    "aggregate cost-ledger write failed; failing job closed to "
                    "avoid silently losing spend on a resume cache-hit"
                ) from exc
        return result


# ── Constants ────────────────────────────────────────────────────────────────

#: All configs supported by harness/run.py (order matches harness/run.py dispatch).
ALL_CONFIGS: List[str] = [
    "single",
    "sc",
    "homogeneous-MAD",
    "heterogeneous-MAD",
    "verifier",
    "interpretation-diverse",
]

#: Configs whose executed work is a POOL of distinct models (harness/run.py
#: ``run_mad(homogeneous=False)``).  A single scalar model_id cannot describe
#: such a job, so BLOCKER A binds NOTHING for these and instead keys the job by
#: a canonical POOL identity derived from the configured heterogeneous pool — so
#: the checkpoint key and the actually-executed work stay consistent (two
#: different pools ⇒ different keys; the model sweep is NOT applied here, which
#: prevents distinct keys from executing identical work).
POOL_CONFIGS: Set[str] = {"heterogeneous-MAD"}

#: Conservative default RPM (well below GitHub Models per-minute caps).
DEFAULT_RPM: int = 20

#: Default infra retry count for transient errors.
DEFAULT_INFRA_RETRIES: int = 3


# ── Runner configuration ─────────────────────────────────────────────────────

@dataclass
class RunnerConfig:
    """Configuration for the experiment runner."""
    tasks: List[Task]
    configs: List[str] = field(default_factory=lambda: list(ALL_CONFIGS))
    seeds: List[int] = field(default_factory=lambda: [20260713])
    #: Optional explicit ``(model_role, model_id)`` dimension of the grid.
    #: BLOCKER 1: the grid is the cross-product of task × config × MODEL × seed,
    #: matching the AgentRun identity.  When ``None``, the Runner derives a
    #: single-model default from the base client's config (the homogeneous
    #: tested-agents baseline), preserving the historical one-model behaviour
    #: while still carrying model identity in every completion key.
    models: Optional[List[Tuple[str, str]]] = None
    checkpoint_path: Path = field(
        default_factory=lambda: Path("runner_checkpoint.jsonl")
    )
    rpm: int = DEFAULT_RPM
    max_budget_usd: Optional[float] = None
    max_infra_retries: int = DEFAULT_INFRA_RETRIES


# ── Runner ───────────────────────────────────────────────────────────────────

class Runner:
    """Resumable, cache-backed, RPM-throttled experiment runner.

    **Grid**: cross-product of (task, config, seed).  Each cell is a "job"
    that produces one or more AgentRun records depending on the config:
    single→1, sc→k, homogeneous-MAD→n_agents, heterogeneous-MAD→n_agents,
    verifier→1 (the selected candidate), interpretation-diverse→n_interpretations.

    **Checkpoint discipline**:
    - Each AgentRun is written + fsync'd as soon as it completes.
    - The job is marked "done" only after ALL its AgentRuns are stored.
    - On restart: done jobs are skipped entirely (zero HTTP calls); the LLM
      disk cache guarantees a cache-hit for any previously-computed prompt identity.
    - Worst-case crash loss: the single in-flight AgentRun at crash time.

    **Stop conditions** (checkpoint before exit):
    - ``DayCapped``: model's remaining jobs skipped; exit with ``status="resumable"``
    - ``BudgetExceeded``: stop immediately, checkpoint current state
    - Transient infra error: retry up to ``max_infra_retries`` times with backoff;
      NEVER checkpoint on failure (only genuine completions reach the store)

    **Dependency injection**: ``run_task_fn`` and ``label_run_fn`` can be
    substituted in tests without modifying the module.
    """

    def __init__(
        self,
        cfg: RunnerConfig,
        base_client: LLMClient,
        *,
        run_task_fn: Optional[Callable] = None,
        label_run_fn: Optional[Callable] = None,
        client_factory: Optional[Callable[[Dict[str, Any], Optional[float]], Any]] = None,
    ) -> None:
        self._cfg = cfg
        self._base_client = base_client
        # Namespace the checkpoint by the base client's online endpoint (provider +
        # normalized base_url) so switching provider / proxy port never reuses a
        # stale job_done marker for a genuinely different endpoint.
        self._store = CheckpointStore(
            cfg.checkpoint_path,
            endpoint=endpoint_identity(base_client.provider, base_client.base_url),
        )
        self._throttler = RpmThrottler(cfg.rpm)
        self._day_capped_models: Set[str] = set()
        self._run_task = run_task_fn if run_task_fn is not None else _default_run_task
        self._label_run = label_run_fn if label_run_fn is not None else _default_label_run
        # BLOCKER 2 / MAJOR 3: per-job clients are built through a factory so the
        # aggregate-cost ledger and the propagated RPM limiter are always applied
        # (and so tests can inject a cost-reporting fake client).
        self._client_factory = (
            client_factory if client_factory is not None
            else self._default_client_factory
        )
        # BLOCKER 1/A: resolve the model dimension of the grid.  Default = the
        # single homogeneous tested-agents baseline from the base config.
        self._models: List[Tuple[str, str]] = (
            list(cfg.models) if cfg.models else self._default_models()
        )
        # BLOCKER A (round 3): harness.run.run_task only ever invokes the
        # tested_agents role, so the grid must enumerate ONLY that role.  Reject
        # any other role up-front rather than letting a cell be marked done for
        # work run_task never executes.
        bad_roles = sorted({r for (r, _m) in self._models if r != "tested_agents"})
        if bad_roles:
            raise ValueError(
                "Runner grid only supports the 'tested_agents' role that "
                f"run_task invokes; got unsupported role(s): {bad_roles}"
            )

    def _default_models(self) -> List[Tuple[str, str]]:
        """Derive the default ``(model_role, model_id)`` grid dimension.

        Uses the homogeneous tested-agents baseline from the base client's
        config, so changing that model in ``config.yaml`` changes the model_id
        carried in every job key — which is exactly what makes a model swap a
        NEW, not-yet-done job on resume (BLOCKER 1) rather than a silent skip.
        """
        try:
            homogeneous = self._base_client.config["roles"]["tested_agents"]["homogeneous"]
            model_id = homogeneous[0]["model"]
        except (KeyError, IndexError, TypeError):
            model_id = "unknown"
        return [("tested_agents", model_id)]

    def _pool_identity(self) -> str:
        """Canonical identity for a heterogeneous (pool) config's executed work.

        BLOCKER B (round 3): ``run_mad`` assigns pool members to agent
        indices/seeds in LIST ORDER and passes each member's ``family`` AND
        ``model`` to ``complete()``, so both the ORDER and each ``(family,
        model)`` pair are execution-relevant.  The identity therefore serializes
        the ORDERED pool of ``(family, model)`` entries — reordering the pool, or
        changing any member's family or model, changes the key (no false-skip).
        A single scalar model_id could never describe this pool job.
        """
        try:
            pool = self._base_client.config["roles"]["tested_agents"]["heterogeneous"]
            entries = [f"{m['family']}|{m['model']}" for m in pool]  # ORDER-preserving
        except (KeyError, IndexError, TypeError):
            entries = ["unknown"]
        return "pool:[" + ";".join(entries) + "]"

    def _models_for_config(self, cfg_name: str) -> List[Tuple[str, str]]:
        """Return the ``(model_role, model_id)`` grid dimension for *cfg_name*.

        BLOCKER A: ``harness.run.run_task`` only ever invokes the ``tested_agents``
        role, so the grid enumerates ONLY that role — never roles run_task does
        not use (which could be marked done without ever running).  A single
        tested config invokes ONE tested model, so it sweeps the configured
        ``models``.  A pool config (heterogeneous-MAD) invokes a POOL of models,
        so it yields exactly ONE cell keyed by the ordered pool identity — never
        the per-model sweep, which would make several distinct keys execute
        identical pool work.
        """
        if cfg_name in POOL_CONFIGS:
            return [("tested_agents", self._pool_identity())]
        return list(self._models)

    def _default_client_factory(
        self, job_config: Dict[str, Any], remaining_budget_usd: Optional[float]
    ) -> LLMClient:
        """Build a per-job LLMClient with the aggregate budget sub-cap applied.

        MAJOR 3 fix: propagate the base client's ``max_requests_per_min`` so the
        per-attempt internal rate limiter stays active on every HTTP retry.  The
        runner's per-model sliding-window throttle (``_ThrottledClient``) is
        layered ON TOP of this, giving additive — never weaker — pacing.
        BLOCKER 2 fix: ``remaining_budget_usd`` is the true sub-cap that keeps
        each per-job pre-auth guard consistent with the aggregate ledger.
        PROVIDER fix: propagate the base client's provider/base_url/auth settings so
        a copilot_proxy (or custom-endpoint) base client is not silently reset to
        the GitHub Models default on each per-job reconstruction.
        TOKEN-BUDGET fix: propagate the base client's ``max_tokens_per_call`` so a
        raised per-call output budget (e.g. 12288 for reasoners) is NOT reverted to
        the 4096 default on per-job reconstruction — otherwise reasoners truncate
        mid-reasoning even though the base client was configured with a higher cap.
        """
        return LLMClient(
            config=job_config,
            cache_dir=str(self._base_client.cache_dir),
            offline=self._base_client.offline,
            max_budget_usd=remaining_budget_usd,
            max_requests_per_min=self._base_client.max_requests_per_min,
            max_tokens_per_call=self._base_client.max_tokens_per_call,
            provider=self._base_client.provider,
            base_url=self._base_client.base_url,
            require_auth=self._base_client.require_auth,
            no_temperature_models=self._base_client.no_temperature_models,
        )

    @staticmethod
    def _bind_model(
        job_config: Dict[str, Any],
        cfg_name: str,
        model_role: str,
        model_id: str,
    ) -> None:
        """Bind this grid cell's tested model into the per-job config copy.

        BLOCKER A (round 3): ``harness.run.run_task`` invokes ONLY the
        ``tested_agents`` role, so the grid only ever carries that role.  The
        tested single-model configs (single / sc / homogeneous-MAD / verifier /
        interpretation-diverse) resolve ``tested_agents`` via the *homogeneous*
        baseline, so overriding that baseline to the grid cell's model makes a
        distinct ``model_id`` run genuinely distinct work (a distinct, not-yet-
        done job).  There is deliberately NO arbitrary-role binding: enumerating a
        role run_task never invokes would let a cell be marked done without ever
        running that role's work.

        POOL configs (heterogeneous-MAD) are a no-op: the executed work is the
        configured heterogeneous pool and the job is keyed by the ordered pool
        identity, so binding a scalar here would desync key ↔ work.

        Only mutates the per-job copy — never shared state.
        """
        if cfg_name in POOL_CONFIGS:
            return  # pool identity cell — executed work is the configured pool
        if model_role != "tested_agents":
            # Defensive: the grid is validated to tested_agents-only in __init__,
            # so this is unreachable; never silently rebind another role.
            return
        family = model_id.split("/", 1)[0] if "/" in model_id else model_id
        try:
            roles = job_config.setdefault("roles", {})
            tested = roles.setdefault("tested_agents", {})
            tested["homogeneous"] = [{"family": family, "model": model_id}]
        except (AttributeError, TypeError):
            pass  # malformed config — leave untouched; run_task will surface it

    # ── Grid enumeration ──────────────────────────────────────────────────────

    def enumerate_grid(self) -> List[Tuple[str, str, str, str, int]]:
        """Return the full job grid as ``(task_id, config, model_role, model_id, seed)``.

        BLOCKER 1/A: the grid is the cross-product of task × config × MODEL × seed,
        matching the five-dimensional AgentRun identity, where the MODEL dimension
        is config-aware (per-model sweep for homogeneous configs, single pool
        identity for heterogeneous pool configs).  The deterministic order
        task → config → model → seed makes resume skip exactly the right jobs.
        """
        grid: List[Tuple[str, str, str, str, int]] = []
        for task in self._cfg.tasks:
            for cfg_name in self._cfg.configs:
                for model_role, model_id in self._models_for_config(cfg_name):
                    for seed in self._cfg.seeds:
                        grid.append((task.id, cfg_name, model_role, model_id, seed))
        return grid

    def pending_jobs(self) -> List[Tuple[str, str, str, str, int]]:
        """Return grid jobs not yet checkpointed as done."""
        return [
            j for j in self.enumerate_grid()
            if not self._store.job_done(*j)
        ]

    # ── Dry run ───────────────────────────────────────────────────────────────

    def dry_run_report(self) -> Dict[str, Any]:
        """Report pending vs done jobs without any network calls.

        Returns a dict with ``total``, ``done``, ``pending``, and
        ``pending_jobs`` (list of ``{task_id, config, model_role, model_id,
        seed}`` dicts).
        """
        grid = self.enumerate_grid()
        done = [j for j in grid if self._store.job_done(*j)]
        pending = [j for j in grid if not self._store.job_done(*j)]
        return {
            "total": len(grid),
            "done": len(done),
            "pending": len(pending),
            "pending_jobs": [
                {
                    "task_id": tid,
                    "config": cfg,
                    "model_role": role,
                    "model_id": mid,
                    "seed": s,
                }
                for tid, cfg, role, mid, s in pending
            ],
        }

    # ── Main run loop ─────────────────────────────────────────────────────────

    def run(self, dry_run: bool = False) -> Dict[str, Any]:
        """Execute all pending jobs.

        Args:
            dry_run: If True, return ``dry_run_report()`` without running anything.

        Returns:
            dict with keys: ``status``, ``completed``, ``skipped``, ``failed``,
            ``day_capped_models``.

            ``status`` is one of:
            - ``"done"``: all jobs completed or skipped
            - ``"resumable"``: at least one model was day-capped; remaining jobs
              can be retried after the day-cap resets (~24h)
            - ``"budget_exceeded"``: stopped at budget cap; checkpoint preserved
            - ``"ledger_unavailable"``: the aggregate cost-ledger write failed
              (accounting storage down); the WHOLE run stops cleanly with no
              further paid calls and is resumable once storage is healthy
        """
        if dry_run:
            return self.dry_run_report()

        task_map: Dict[str, Task] = {t.id: t for t in self._cfg.tasks}
        grid = self.enumerate_grid()
        completed = 0
        skipped = 0
        failed = 0
        day_capped: List[str] = []

        for task_id, cfg_name, model_role, model_id, seed in grid:

            # ── Resume: skip completed jobs (idempotent, 5-dim key) ────────────
            if self._store.job_done(task_id, cfg_name, model_role, model_id, seed):
                skipped += 1
                continue

            # ── Aggregate budget gate (BLOCKER 2) ──────────────────────────────
            # The hard cap is enforced across the WHOLE run/resume via the
            # persisted ledger, NOT per job.  Stop cleanly BEFORE spending more
            # once the running total has reached the cap.
            if (
                self._cfg.max_budget_usd is not None
                and self._store.aggregate_cost_usd >= self._cfg.max_budget_usd
            ):
                print(
                    f"[RUNNER] Aggregate budget reached "
                    f"(${self._store.aggregate_cost_usd:.6f} >= "
                    f"${self._cfg.max_budget_usd:.6f}). Checkpointing and stopping."
                )
                self._emit_progress(completed, skipped, failed, grid)
                return {
                    "status": "budget_exceeded",
                    "completed": completed,
                    "skipped": skipped,
                    "failed": failed,
                    "day_capped_models": day_capped,
                }

            task = task_map[task_id]

            # ── Build per-job client (injects seed + binds this grid model) ────
            # A fresh copy of config ensures different seeds/models produce
            # genuinely different AgentRun identities without mutating shared
            # state.  Binding the tested-agents model to this grid cell's model_id
            # makes a different model_id real, distinct work (BLOCKER 1).
            job_config = copy.deepcopy(self._base_client.config)
            job_config["seeds"]["global"] = seed
            self._bind_model(job_config, cfg_name, model_role, model_id)

            # Pass the REMAINING aggregate budget so the per-job pre-auth guard is
            # a true sub-cap of the whole-run cap (BLOCKER 2).
            remaining_budget: Optional[float] = None
            if self._cfg.max_budget_usd is not None:
                remaining_budget = max(
                    0.0, self._cfg.max_budget_usd - self._store.aggregate_cost_usd
                )
            job_client = self._client_factory(job_config, remaining_budget)

            # Wrap with throttler + day-cap guard (shared set across jobs).
            # BLOCKER B: the ledger is journaled PER PAID completion via
            # ``cost_sink`` — NOT once after the whole job returns — so a crash
            # after paid completions but before job_done cannot undercount the
            # aggregate.  On resume the job re-runs and cache-hits cost $0
            # (delta == 0 → not journaled), so there is no double-count either.
            wrapped = _ThrottledClient(
                job_client,
                self._throttler,
                self._day_capped_models,
                cost_sink=self._store.add_cost,
            )

            # ── Execute job with infra-error retry ────────────────────────────
            try:
                labeled_runs = self._run_job_with_retry(task, cfg_name, wrapped)
            except BudgetExceeded as exc:
                print(
                    f"[RUNNER] Budget exceeded: {exc}. Checkpointing and stopping."
                )
                self._emit_progress(completed, skipped, failed, grid)
                return {
                    "status": "budget_exceeded",
                    "completed": completed,
                    "skipped": skipped,
                    "failed": failed,
                    "day_capped_models": day_capped,
                }
            except DayCapped as exc:
                model_slug: str = getattr(exc, "model_slug", str(exc))
                if model_slug not in day_capped:
                    day_capped.append(model_slug)
                self._day_capped_models.add(model_slug)
                print(
                    f"[RUNNER] Day-cap hit for {model_slug!r}. "
                    "Skipping remaining jobs for this model. "
                    "Resume after ~24h cap reset."
                )
                failed += 1
                continue
            except LedgerWriteError as exc:
                # FAIL CLOSED — WHOLE RUN.  A ledger-write failure means the cost
                # accounting store itself is down.  If it is PERSISTENT, continuing
                # to later jobs would incur unjournaled paid spend across the entire
                # remaining grid.  So we STOP the whole runner immediately and
                # cleanly (mirroring BudgetExceeded): no further paid calls may
                # occur while the cost ledger cannot be written.  The current job is
                # NOT marked done; on resume (once disk is healthy) it re-runs and
                # cache-hits cost $0, so nothing is double-counted.
                print(
                    f"[RUNNER] LEDGER WRITE FAILURE on job "
                    f"({task_id!r}, {cfg_name!r}, {model_id!r}, seed={seed}): {exc}. "
                    "Cost ledger unavailable — stopping the whole run cleanly "
                    "(resume once accounting storage is healthy)."
                )
                failed += 1
                self._emit_progress(completed, skipped, failed, grid)
                return {
                    "status": "ledger_unavailable",
                    "completed": completed,
                    "skipped": skipped,
                    "failed": failed,
                    "day_capped_models": day_capped,
                }
            except Exception as exc:
                print(
                    f"[RUNNER] INFRA error on job "
                    f"({task_id!r}, {cfg_name!r}, {model_id!r}, seed={seed}): {exc}"
                )
                failed += 1
                continue

            # ── Checkpoint: runs, then job_done marker ─────────────────────────
            # Cost has ALREADY been journaled per paid completion (BLOCKER B) via
            # the wrapper's ``cost_sink``, so we only persist each AgentRun (fsync)
            # then the job_done marker here.  If a crash occurs before job_done,
            # the job re-runs on resume and cache-hits make ZERO new HTTP calls
            # (delta == 0 → not journaled), so there is neither undercount (paid
            # cost already in the ledger) nor double-count.
            for run, label in labeled_runs:
                run.label = label
                self._store.add_run(run)
            self._store.mark_job_done(task_id, cfg_name, model_role, model_id, seed)
            completed += 1

        self._emit_progress(completed, skipped, failed, grid)
        self._emit_i_perp_rates()

        return {
            "status": "done" if not day_capped else "resumable",
            "completed": completed,
            "skipped": skipped,
            "failed": failed,
            "day_capped_models": day_capped,
        }

    # ── Job execution with infra-error retry ──────────────────────────────────

    def _run_job_with_retry(
        self,
        task: Task,
        cfg_name: str,
        client: _ThrottledClient,
    ) -> List[Tuple[AgentRun, str]]:
        """Execute one job, retrying transient infra errors.

        Permanent errors (``BudgetExceeded``, ``DayCapped``, ``LedgerWriteError``)
        re-raise immediately and are NEVER retried.  In particular a
        ``LedgerWriteError`` must not be retried: the re-run would cache-hit the
        already-paid completion at $0 incremental cost and silently drop the
        original spend from the aggregate (fail-closed).  Transient errors sleep
        with exponential back-off (1s, 2s, 4s, ...) and retry up to
        ``max_infra_retries - 1`` additional times.

        Returns:
            List of ``(AgentRun, label)`` pairs; always non-empty on success.

        Never checkpoints on failure — only genuine completions are returned.
        An empty or invalid model output is a normal AgentRun (labeler → I_perp);
        it is NOT an infra error and is returned, not retried.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(self._cfg.max_infra_retries):
            try:
                runs = self._run_task(task, cfg_name, client)
                labeled: List[Tuple[AgentRun, str]] = []
                for run in runs:
                    lbl = self._label_run(run, task)
                    labeled.append((run, lbl))
                return labeled
            except (BudgetExceeded, DayCapped, LedgerWriteError):
                raise  # permanent — do not retry, propagate to run()
            except Exception as exc:
                last_exc = exc
                if attempt < self._cfg.max_infra_retries - 1:
                    time.sleep(2 ** attempt)
        # All retry attempts exhausted — surface the last exception
        assert last_exc is not None
        raise last_exc

    # ── Observability ─────────────────────────────────────────────────────────

    def _emit_progress(
        self,
        completed: int,
        skipped: int,
        failed: int,
        grid: List[Tuple[str, str, int]],
    ) -> None:
        """Print a single structured progress line (NO token values)."""
        total = len(grid)
        print(
            f"[RUNNER] Progress: {completed} completed | {skipped} skipped "
            f"| {failed} failed | {total} total jobs"
        )

    def _emit_i_perp_rates(self) -> None:
        """Emit per-condition I_perp RATE as a first-class diagnostic (guardrail B).

        Groups completed AgentRuns by (config, model_id) and prints the fraction
        labelled I_perp.  High rates indicate parsing/extraction failures that
        must be investigated before interpreting convergent_delusion metrics.
        """
        runs = self._store.all_runs()
        if not runs:
            return
        groups: Dict[str, List[str]] = collections.defaultdict(list)
        for rec in runs:
            key = f"{rec['config']}|{rec['model_id']}"
            groups[key].append(rec["label"])

        print("[RUNNER] I_perp rates per (config, model_id):")
        for key in sorted(groups):
            labels = groups[key]
            n = len(labels)
            n_perp = sum(1 for lbl in labels if lbl == "I_perp")
            rate = n_perp / n if n else 0.0
            print(f"  {key}: {n_perp}/{n} = {rate:.3f}")


# ── CLI entry point ──────────────────────────────────────────────────────────

def _token() -> str:
    """Read token from env (NEVER printed or logged)."""
    return (
        os.environ.get("GITHUB_MODELS_TOKEN")
        or os.environ.get("GH_MODELS_TOKEN")
        or ""
    )


def _live_guard() -> bool:
    """Return True only when BOTH guards pass: RUNNER_LIVE=1 AND a token exists.

    Retained for the token-required (github_models) path and backward compat.
    Provider-aware callers should use :func:`_live_ok`, which only requires a
    token when the selected provider needs one.
    """
    return os.environ.get("RUNNER_LIVE", "0") == "1" and bool(_token())


def _live_ok(require_auth: bool) -> bool:
    """Provider-aware live guard.

    Live execution requires ``RUNNER_LIVE=1``. A token is additionally required
    ONLY when the selected provider needs auth (``github_models``). The local
    ``copilot_proxy`` needs NO token, so ``RUNNER_LIVE=1`` alone enables it.
    """
    if os.environ.get("RUNNER_LIVE", "0") != "1":
        return False
    if require_auth:
        return bool(_token())
    return True


def main(argv: Optional[List[str]] = None) -> None:
    """CLI entry point (double-guarded for live runs, same discipline as mini_pilot).

    Usage (after Manager has verified the token):
        RUNNER_LIVE=1 python -m harness.runner [--dry-run] [--checkpoint PATH]
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Resumable, cache-backed experiment runner for When Consensus Lies"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report pending/done counts without executing any jobs",
    )
    parser.add_argument(
        "--checkpoint",
        default="runner_checkpoint.jsonl",
        help="Path to the checkpoint JSONL file (default: runner_checkpoint.jsonl)",
    )
    parser.add_argument(
        "--rpm",
        type=int,
        default=DEFAULT_RPM,
        help=f"Requests per minute per model (default: {DEFAULT_RPM})",
    )
    parser.add_argument(
        "--budget-usd",
        type=float,
        default=None,
        help="Hard aggregate budget cap in USD (stops cleanly when exceeded)",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="LLM provider: 'github_models' (token required) or 'copilot_proxy' "
             "(local, no token). Default: config providers.default.",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Override the provider's base URL (e.g. a custom proxy host/port).",
    )
    args = parser.parse_args(argv)

    # Load config FIRST so the provider (and whether a token is required) is known
    # BEFORE the live-guard decision — a copilot_proxy run needs no token.
    from common.config import load_config
    from common.llm import resolve_provider_config

    cfg = load_config()
    prov = resolve_provider_config(cfg, provider=args.provider, base_url=args.base_url)
    live_ok = _live_ok(prov["require_auth"])

    if not args.dry_run and not live_ok:
        need = (
            "RUNNER_LIVE=1 and a token in GITHUB_MODELS_TOKEN / GH_MODELS_TOKEN"
            if prov["require_auth"]
            else "RUNNER_LIVE=1"
        )
        print(
            f"runner: skipped (provider={prov['provider']!r} requires {need}). "
            "Set to run live."
        )
        return

    # Import benchmark tasks lazily (do not fail in CI if bench data is absent)
    try:
        from bench.code_spec import generate_tasks
        tasks = generate_tasks()
    except Exception as exc:  # noqa: BLE001
        print(f"[RUNNER] Failed to load tasks: {exc}", file=sys.stderr)
        sys.exit(1)

    client = LLMClient(
        config=cfg,
        offline=(not live_ok),
        max_budget_usd=args.budget_usd,
        max_requests_per_min=args.rpm,
        provider=prov["provider"],
        base_url=prov["base_url"],
    )

    runner_cfg = RunnerConfig(
        tasks=tasks,
        checkpoint_path=Path(args.checkpoint),
        rpm=args.rpm,
        max_budget_usd=args.budget_usd,
    )
    runner = Runner(runner_cfg, client)
    result = runner.run(dry_run=args.dry_run)
    print(f"[RUNNER] Result: {result}")


if __name__ == "__main__":
    main()
