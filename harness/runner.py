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

from common.llm import BudgetExceeded, DayCapped, LLMClient
from common.schema import AgentRun, Task
from harness.label import label_run as _default_label_run
from harness.run import run_task as _default_run_task


# ── AgentRun identity helpers ────────────────────────────────────────────────

def run_identity(run: AgentRun) -> str:
    """Canonical string key for AgentRun identity.

    Encodes task_id × config × model_role × model_id × seed, which is the
    identity dimension defined in schema.py.  Null-byte separators prevent
    collisions between field values that contain the separator character.
    """
    return "\x00".join([
        run.task_id,
        run.config,
        run.model_role,
        run.model_id,
        str(run.seed),
    ])


def job_key(task_id: str, config: str, seed: int) -> str:
    """Canonical string key for a runner job (task_id × config × seed)."""
    return f"{task_id}\x00{config}\x00{seed}"


# ── Checkpoint store ─────────────────────────────────────────────────────────

class CheckpointStore:
    """Append-only JSONL checkpoint for AgentRun records.

    Two record types written to the same JSONL file:
    - ``{"type": "run", ...AgentRun fields..., "label": ...}``
    - ``{"type": "job_done", "task_id": ..., "config": ..., "seed": ...}``

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

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._done_jobs: Set[str] = set()
        self._run_ids: Set[str] = set()
        self._runs: List[Dict[str, Any]] = []
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
                if rec.get("type") == "job_done":
                    self._done_jobs.add(
                        job_key(rec["task_id"], rec["config"], int(rec["seed"]))
                    )
                elif rec.get("type") == "run":
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
                    rid = run_identity(run)
                    if rid not in self._run_ids:
                        self._run_ids.add(rid)
                        self._runs.append(rec)

    def job_done(self, task_id: str, config: str, seed: int) -> bool:
        """True iff this job has been fully completed and checkpointed."""
        return job_key(task_id, config, seed) in self._done_jobs

    def run_done(self, run: AgentRun) -> bool:
        """True iff this specific AgentRun identity has been checkpointed."""
        return run_identity(run) in self._run_ids

    def _write(self, record: Dict[str, Any]) -> None:
        """Append one record to the JSONL file and fsync."""
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def add_run(self, run: AgentRun) -> None:
        """Checkpoint a single AgentRun.  Idempotent by identity."""
        rid = run_identity(run)
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
        self._write(record)
        self._run_ids.add(rid)
        self._runs.append(record)

    def mark_job_done(self, task_id: str, config: str, seed: int) -> None:
        """Mark a job as fully complete.  Idempotent."""
        k = job_key(task_id, config, seed)
        if k in self._done_jobs:
            return  # already marked — idempotent
        self._write({
            "type": "job_done",
            "task_id": task_id,
            "config": config,
            "seed": seed,
        })
        self._done_jobs.add(k)

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
    """Duck-type LLMClient wrapper adding per-model RPM throttling and day-cap guard.

    Exposes the same interface as LLMClient (``complete()``, ``config``,
    ``cache_dir``, ``offline``) so it can be passed directly to ``run_task()``.

    Day-cap guard: if a model slug is in ``day_capped_models``, ``complete()``
    raises ``DayCapped`` immediately without touching the underlying client.
    This propagates cleanly through ``run_task()`` to the runner's catch block,
    where the model is registered and all future jobs for it are also skipped.
    """

    def __init__(
        self,
        underlying: LLMClient,
        throttler: RpmThrottler,
        day_capped_models: Set[str],
    ) -> None:
        self._c = underlying
        self._throttler = throttler
        self._day_capped = day_capped_models

    @property
    def config(self) -> Dict[str, Any]:
        return self._c.config

    @property
    def cache_dir(self) -> Path:
        return self._c.cache_dir

    @property
    def offline(self) -> bool:
        return self._c.offline

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
        """Throttle + day-cap guard, then delegate to underlying LLMClient."""
        # Resolve slug for per-model throttling/day-cap checks
        if model is not None:
            slug = model
        else:
            from common.config import model_for_role
            slug = model_for_role(role, self._c.config)["model"]

        if slug in self._day_capped:
            raise DayCapped(slug)

        self._throttler.acquire(slug)
        return self._c.complete(
            role=role,
            prompt=prompt,
            seed=seed,
            max_retries=max_retries,
            family=family,
            model=model,
            temperature=temperature,
        )


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
    ) -> None:
        self._cfg = cfg
        self._base_client = base_client
        self._store = CheckpointStore(cfg.checkpoint_path)
        self._throttler = RpmThrottler(cfg.rpm)
        self._day_capped_models: Set[str] = set()
        self._run_task = run_task_fn if run_task_fn is not None else _default_run_task
        self._label_run = label_run_fn if label_run_fn is not None else _default_label_run

    # ── Grid enumeration ──────────────────────────────────────────────────────

    def enumerate_grid(self) -> List[Tuple[str, str, int]]:
        """Return the full job grid as ``(task_id, config, seed)`` tuples.

        The cross-product order is task → config → seed, which is deterministic
        across restarts so resume skips the right jobs.
        """
        grid: List[Tuple[str, str, int]] = []
        for task in self._cfg.tasks:
            for cfg_name in self._cfg.configs:
                for seed in self._cfg.seeds:
                    grid.append((task.id, cfg_name, seed))
        return grid

    def pending_jobs(self) -> List[Tuple[str, str, int]]:
        """Return grid jobs not yet checkpointed as done."""
        return [
            j for j in self.enumerate_grid()
            if not self._store.job_done(j[0], j[1], j[2])
        ]

    # ── Dry run ───────────────────────────────────────────────────────────────

    def dry_run_report(self) -> Dict[str, Any]:
        """Report pending vs done jobs without any network calls.

        Returns a dict with ``total``, ``done``, ``pending``, and
        ``pending_jobs`` (list of ``{task_id, config, seed}`` dicts).
        """
        grid = self.enumerate_grid()
        done = [j for j in grid if self._store.job_done(j[0], j[1], j[2])]
        pending = [j for j in grid if not self._store.job_done(j[0], j[1], j[2])]
        return {
            "total": len(grid),
            "done": len(done),
            "pending": len(pending),
            "pending_jobs": [
                {"task_id": tid, "config": cfg, "seed": s}
                for tid, cfg, s in pending
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
        """
        if dry_run:
            return self.dry_run_report()

        task_map: Dict[str, Task] = {t.id: t for t in self._cfg.tasks}
        grid = self.enumerate_grid()
        completed = 0
        skipped = 0
        failed = 0
        day_capped: List[str] = []

        for task_id, cfg_name, seed in grid:

            # ── Resume: skip completed jobs (idempotent) ───────────────────────
            if self._store.job_done(task_id, cfg_name, seed):
                skipped += 1
                continue

            task = task_map[task_id]

            # ── Build per-job LLMClient (injects seed into config copy) ────────
            # A fresh copy of config ensures different seeds produce genuinely
            # different AgentRun identities without mutating shared state.
            job_config = copy.deepcopy(self._base_client.config)
            job_config["seeds"]["global"] = seed
            job_client = LLMClient(
                config=job_config,
                cache_dir=str(self._base_client.cache_dir),
                offline=self._base_client.offline,
                max_budget_usd=self._cfg.max_budget_usd,
            )
            # Wrap with throttler + day-cap guard (shared set across jobs)
            wrapped = _ThrottledClient(
                job_client, self._throttler, self._day_capped_models
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
            except Exception as exc:
                print(
                    f"[RUNNER] INFRA error on job "
                    f"({task_id!r}, {cfg_name!r}, seed={seed}): {exc}"
                )
                failed += 1
                continue

            # ── Checkpoint: write runs, then mark job done ─────────────────────
            # write each AgentRun first (fsync), then the job_done marker.
            # If crash between add_run() calls, the job is not marked done and
            # will re-run on next invocation (the LLM cache prevents dup calls).
            for run, label in labeled_runs:
                run.label = label
                self._store.add_run(run)
            self._store.mark_job_done(task_id, cfg_name, seed)
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

        Permanent errors (``BudgetExceeded``, ``DayCapped``) re-raise immediately
        and are NEVER retried.  Transient errors sleep with exponential back-off
        (1s, 2s, 4s, ...) and retry up to ``max_infra_retries - 1`` additional times.

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
            except (BudgetExceeded, DayCapped):
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
    """Return True only when BOTH guards pass: RUNNER_LIVE=1 AND a token exists."""
    return os.environ.get("RUNNER_LIVE", "0") == "1" and bool(_token())


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
    args = parser.parse_args(argv)

    if not args.dry_run and not _live_guard():
        print(
            "runner: skipped (RUNNER_LIVE != 1 or no token in "
            "GITHUB_MODELS_TOKEN / GH_MODELS_TOKEN). Set both to run live."
        )
        return

    from common.config import load_config

    cfg = load_config()

    # Import benchmark tasks lazily (do not fail in CI if bench data is absent)
    try:
        from bench.code_spec import generate_tasks
        tasks = generate_tasks()
    except Exception as exc:  # noqa: BLE001
        print(f"[RUNNER] Failed to load tasks: {exc}", file=sys.stderr)
        sys.exit(1)

    client = LLMClient(
        config=cfg,
        offline=(not _live_guard()),
        max_budget_usd=args.budget_usd,
        max_requests_per_min=args.rpm,
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
