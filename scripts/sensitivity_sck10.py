# constructed by: Claude (Anthropic) family
"""SC k=10 sensitivity pass driver (A08 §2 scheduled secondary).

# Implementer model family: Claude/Anthropic
# Auditor model family: GPT (Law 6 — cross-family requirement)

Runs the **SC config ONLY** with **k=10** over the full confirmatory grid
(all 3 domains: code_spec + data_analysis + policy_qa, 54 items,
seeds [global, global+1000, global+2000], all 7 frontier models / 4 model
classes) writing to a SEPARATE checkpoint and cache from the confirmatory run.

Reuses the EXISTING machinery in scripts/registered_run.py and harness/runner.py
WITHOUT editing either file (they are imported and parameterized).

IMPORTANT: ``config_kwargs={"sc": {"k": 10}}`` overrides the frozen
``REGISTERED_CONFIG_KWARGS["sc"] = {"k": 5}`` for THIS run only — the frozen
dict in registered_run.py is NEVER modified.  Gate C cardinality is 10 (not 5)
for this run, defined locally here.

OFFLINE / CI SAFE:
    ``main()`` requires RUNNER_LIVE=1 AND a reachable copilot_proxy; if either
    guard fails it prints "skipped" and exits 0 — no network, no cost.
    The ``run()`` function is a pure driver callable by offline unit tests
    (via ``_runner_override`` injection or ``dry_run=True``).

Usage:
    # Dry-run: enumerate sc-only jobs at k=10 (no network)
    python scripts/sensitivity_sck10.py --dry-run

    # Live run ($0 on copilot_proxy)
    RUNNER_LIVE=1 python scripts/sensitivity_sck10.py
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Repo root + scripts dir on sys.path ────────────────────────────────────
_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
# Add scripts/ dir so `import registered_run` resolves the co-located script.
# (scripts/ is intentionally NOT a package — no __init__.py.)
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


# ── Constants ────────────────────────────────────────────────────────────────

#: Separate checkpoint — NEVER write into the confirmatory run's checkpoint.
CHECKPOINT = ".run_partitions/cp_sck10.jsonl"

#: Separate LLM disk cache — keeps SC k=10 samples isolated from k=5 cache.
CACHE_DIR = ".llm_cache_sck10"

#: Match the confirmatory run RPM.
RPM = 30

#: SC-only grid — single/MAD/verifier/interpretation-diverse already run in
#: the confirmatory pass; do NOT re-run them.
_CONFIGS_SCK10: List[str] = ["sc"]

#: config_kwargs override: sc k=10 for this sensitivity pass ONLY.
#: Does NOT touch ``REGISTERED_CONFIG_KWARGS`` in registered_run.py (frozen).
_CONFIG_KWARGS_SCK10: Dict[str, Dict[str, Any]] = {"sc": {"k": 10}}

#: Gate C cardinality: SC at k=10 produces 10 AgentRuns per job.
#: Defined LOCALLY — never edit ``_GATE_C_MIN_AGENTS`` in registered_run.py.
_GATE_C_SCK10: Dict[str, int] = {"sc": 10}

#: Seed stride matching registered_run._SEED_STRIDE (1000).
_SEED_STRIDE: int = 1000


# ── Guards ───────────────────────────────────────────────────────────────────

def _live_ok() -> bool:
    """Return True only when RUNNER_LIVE=1 (no token required for copilot_proxy)."""
    return os.environ.get("RUNNER_LIVE", "0") == "1"


def _proxy_reachable() -> bool:
    """Best-effort: return True if copilot_proxy is accepting connections.

    Uses a 2-second timeout.  An HTTP error response (4xx/5xx) still means
    the server is listening, so HTTPError → True.  Only genuine connection
    failures (URLError, timeout, socket error) → False (offline / CI safe).
    """
    import socket
    import urllib.error
    import urllib.request
    try:
        from common.llm import COPILOT_PROXY_BASE_URL
        # COPILOT_PROXY_BASE_URL already ends in /v1; append /models only.
        url = COPILOT_PROXY_BASE_URL.rstrip("/") + "/models"
    except (ImportError, AttributeError):
        url = "http://127.0.0.1:8313/v1/models"
    try:
        urllib.request.urlopen(url, timeout=2)  # noqa: S310
        return True
    except urllib.error.HTTPError:
        # Server replied with an HTTP error (404, 401, etc.) — it IS reachable.
        return True
    except (urllib.error.URLError, OSError, socket.timeout):
        return False


# ── Driver-local Gate C validation ──────────────────────────────────────────

def _validate_gate_c_sck10(
    checkpoint_path: str,
    min_agents: int = 10,
) -> Dict[str, Any]:
    """Post-run Gate C cardinality check for the sc-at-k=10 sensitivity pass.

    Reads the sc-k=10 checkpoint JSONL and verifies every completed sc job
    (``job_done`` record) has at least ``min_agents`` associated ``run`` records.

    A partial/stale job with fewer records indicates a corrupted or interrupted
    checkpoint — it would silently corrupt n_eff/CD analysis if accepted.

    This check is intentionally LOCAL and SEPARATE from registered_run.py's
    ``_GATE_C_MIN_AGENTS`` (which encodes k=5).  Never import-mutate that dict.

    Args:
        checkpoint_path: Path to the sc-k=10 checkpoint JSONL.
        min_agents: Minimum expected agent records per completed job (default 10).

    Returns:
        Dict with keys:
          - ``"passed"``: bool — True iff all done sc jobs have >= min_agents records
          - ``"checked"``: int — number of completed sc jobs inspected
          - ``"violations"``: list of dicts for jobs with < min_agents agents,
            each with keys task_id, model_id, seed, agent_count, expected
          - ``"note"`` (optional): explanation when checkpoint is absent/empty
    """
    import json

    cp = Path(checkpoint_path)
    if not cp.exists():
        return {
            "passed": True,
            "checked": 0,
            "violations": [],
            "note": "checkpoint absent — no jobs to validate",
        }

    done_sc_jobs: List[Dict[str, Any]] = []
    run_records: List[Dict[str, Any]] = []

    with cp.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            rtype = rec.get("type")
            if rec.get("config") != "sc":
                continue
            if rtype == "job_done":
                required = ("task_id", "config", "model_role", "model_id", "seed")
                if all(k in rec for k in required):
                    done_sc_jobs.append(rec)
            elif rtype == "run":
                run_records.append(rec)

    violations: List[Dict[str, Any]] = []
    for job in done_sc_jobs:
        task_id = job["task_id"]
        model_role = job["model_role"]
        model_id = job["model_id"]
        grid_seed = int(job["seed"])
        job_endpoint = job.get("endpoint", "")

        # Collect unique run identities that match this job's full identity.
        # Mirroring run_identity() in harness/runner.py: the key is
        # [endpoint?,] task_id, config, model_role, model_id, per_agent_seed [, R{replicate_seed}?]
        # Deduplication prevents duplicate checkpoint lines from inflating the count.
        seen_run_ids: set = set()
        for run in run_records:
            # Full job identity match — model_role and endpoint are required
            # to avoid foreign-role or foreign-endpoint records inflating the count.
            if run.get("task_id") != task_id:
                continue
            if run.get("model_role") != model_role:
                continue
            if run.get("model_id") != model_id:
                continue
            if run.get("endpoint", "") != job_endpoint:
                continue
            # Match run to grid seed: use replicate_seed if present (multi-agent
            # records where per-agent seed != grid seed), else fall back to seed
            # (single-agent record or agent-0 where per-agent seed == grid seed).
            rep = run.get("replicate_seed")
            match_seed = int(rep) if rep is not None else int(run.get("seed", -1))
            if match_seed != grid_seed:
                continue
            # Build a unique identity tuple mirroring run_identity() in runner.py.
            per_seed = int(run.get("seed", -1))
            id_parts: List[Any] = [
                run.get("task_id", ""),
                run.get("config", ""),
                run.get("model_role", ""),
                run.get("model_id", ""),
                per_seed,
            ]
            rep_int = int(rep) if rep is not None else None
            if rep_int is not None and rep_int != per_seed:
                id_parts.append(f"R{rep_int}")
            ep = run.get("endpoint", "")
            if ep:
                id_parts.insert(0, ep)
            seen_run_ids.add(tuple(id_parts))

        count = len(seen_run_ids)

        if count < min_agents:
            violations.append({
                "task_id": task_id,
                "model_role": model_role,
                "model_id": model_id,
                "seed": grid_seed,
                "endpoint": job_endpoint,
                "agent_count": count,
                "expected": min_agents,
            })

    return {
        "passed": len(violations) == 0,
        "checked": len(done_sc_jobs),
        "violations": violations,
    }


# ── Pure run function (offline-test-friendly) ────────────────────────────────

def run(
    tasks: List[Any],
    cfg: Dict[str, Any],
    *,
    checkpoint_path: str = CHECKPOINT,
    cache_dir: str = CACHE_DIR,
    rpm: int = RPM,
    seeds: Optional[List[int]] = None,
    dry_run: bool = False,
    offline: bool = False,
    budget_usd: Optional[float] = None,
    _runner_override: Optional[Any] = None,
) -> Dict[str, Any]:
    """Run (or dry-run) the SC k=10 sensitivity pass.

    Pure function — can be called by offline unit tests without any network.
    Inject ``_runner_override=(runner, client)`` to bypass client construction,
    or pass ``dry_run=True`` to enumerate the grid without executing jobs.

    Args:
        tasks: Full task list (all 3 domains, ~54 items for the confirmatory grid).
        cfg: Loaded config dict (from common.config.load_config()).
        checkpoint_path: JSONL checkpoint path (separate from confirmatory run).
        cache_dir: LLM disk cache directory (separate from confirmatory run).
        rpm: Requests per minute per model.
        seeds: Replicate seeds. Default: [global_seed, global_seed+1000,
            global_seed+2000] — same stride as the confirmatory run so k=5 vs
            k=10 comparisons isolate the k effect.
        dry_run: If True, return dry_run_report() without any network calls.
        offline: If True, build an offline LLMClient (for unit tests).
        budget_usd: Optional aggregate budget cap (copilot_proxy is $0).
        _runner_override: Optional (runner, client) tuple; when set, skips
            client/runner construction entirely (test injection point).

    Returns:
        Runner result dict (keys: status, total/done/pending for dry_run,
        or completed/skipped/failed/day_capped_models for live runs).
    """
    import registered_run as _rr

    if seeds is None:
        global_seed = cfg.get("seeds", {}).get("global", 20260713)
        seeds = [
            global_seed,
            global_seed + _SEED_STRIDE,
            global_seed + 2 * _SEED_STRIDE,
        ]

    # Ensure the checkpoint directory exists before the runner tries to write.
    cp = Path(checkpoint_path)
    cp.parent.mkdir(parents=True, exist_ok=True)

    if _runner_override is not None:
        runner, _client = _runner_override
    else:
        runner, _client = _rr.build_runner(
            cfg,
            tasks,
            checkpoint_path=checkpoint_path,
            models=_rr.FRONTIER_SINGLE_MODELS,   # all 7 frontier models / 4 classes
            configs=_CONFIGS_SCK10,               # sc only
            seeds=seeds,
            budget_usd=budget_usd,
            rpm=rpm,
            offline=(offline or dry_run),
            cache_dir=cache_dir,
            config_kwargs=_CONFIG_KWARGS_SCK10,   # k=10 override (not k=5)
        )

    result = runner.run(dry_run=dry_run)

    # ── Driver-local Gate C cardinality check (k=10, sc-only) ────────────────
    # Validates every completed sc job in the checkpoint has >= 10 agent records.
    # This is intentionally LOCAL — never imports/mutates _GATE_C_MIN_AGENTS in
    # registered_run.py (which encodes the confirmatory k=5 expectation).
    if not dry_run:
        gate_c = _validate_gate_c_sck10(
            checkpoint_path, min_agents=_GATE_C_SCK10["sc"]
        )
        n_violations = len(gate_c["violations"])
        if gate_c["passed"]:
            print(
                f"[SCK10 Gate C] PASS — {gate_c['checked']} done sc job(s) "
                f"all have \u2265{_GATE_C_SCK10['sc']} agents"
            )
        else:
            print(
                f"[SCK10 Gate C] FAIL — {n_violations} job(s) with "
                f"<{_GATE_C_SCK10['sc']} agents (partial/stale checkpoint):"
            )
            for v in gate_c["violations"]:
                print(
                    f"  task_id={v['task_id']}  model_id={v['model_id']}  "
                    f"seed={v['seed']}  agents={v['agent_count']}/{v['expected']}"
                )
        result = {**result, "gate_c_sck10": gate_c}
        if not gate_c["passed"]:
            raise RuntimeError(
                f"[SCK10 Gate C] FAILED: {n_violations} sc job(s) have "
                f"<{_GATE_C_SCK10['sc']} agent records. "
                "Partial/stale checkpoint detected — re-run or clear the checkpoint."
            )

    return result


# ── CLI / main ───────────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> None:
    """CLI entry point.

    Guards (both required for live execution):
      1. RUNNER_LIVE=1 env var must be set.
      2. copilot_proxy must be reachable (http://127.0.0.1:8313).

    Either missing → print "skipped" and exit 0 (no network, no cost).
    --dry-run bypasses both guards and enumerates the grid offline.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "SC k=10 sensitivity pass — A08 §2 secondary, sc-config only, "
            "separate checkpoint (.run_partitions/cp_sck10.jsonl)"
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report pending/done grid without executing any jobs",
    )
    parser.add_argument(
        "--checkpoint",
        default=CHECKPOINT,
        help=f"Checkpoint JSONL path (default: {CHECKPOINT})",
    )
    parser.add_argument(
        "--cache-dir",
        default=CACHE_DIR,
        help=f"LLM disk cache directory (default: {CACHE_DIR})",
    )
    parser.add_argument(
        "--rpm",
        type=int,
        default=RPM,
        help=f"Requests per minute per model (default: {RPM})",
    )
    parser.add_argument(
        "--budget-usd",
        type=float,
        default=None,
        help="Hard aggregate budget cap in USD (copilot_proxy is $0)",
    )
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=None,
        help="Override replicate seeds (default: global_seed + 0/1000/2000)",
    )
    parser.add_argument(
        "--domains",
        nargs="+",
        default=None,
        help="Domains to load (default: all 3: code_spec data_analysis policy_qa)",
    )
    args = parser.parse_args(argv)

    # ── Guards (skip for dry-run; required for live) ──────────────────────────
    if not args.dry_run:
        if not _live_ok():
            print(
                "sensitivity_sck10: skipped (RUNNER_LIVE != 1). "
                "Set RUNNER_LIVE=1 to run live (copilot_proxy, no token required)."
            )
            sys.exit(0)
        if not _proxy_reachable():
            print(
                "sensitivity_sck10: skipped (copilot_proxy not reachable at "
                "http://127.0.0.1:8313). Start the proxy before running live."
            )
            sys.exit(0)

    from common.config import load_config
    import registered_run as _rr

    cfg = load_config()
    tasks = _rr.load_tasks(args.domains)  # all 3 domains if None → 54 items

    global_seed = cfg.get("seeds", {}).get("global", 20260713)
    seeds = args.seeds or [
        global_seed,
        global_seed + _SEED_STRIDE,
        global_seed + 2 * _SEED_STRIDE,
    ]

    print("=" * 72)
    print("SC k=10 SENSITIVITY PASS — A08 §2 secondary")
    print("  config=sc only  k=10 (override; confirmatory run uses k=5)")
    print(f"  checkpoint={args.checkpoint}")
    print(f"  cache={args.cache_dir}")
    print(f"  rpm={args.rpm}  seeds={seeds}")
    print(f"  models ({len(_rr.FRONTIER_SINGLE_MODELS)}): {[m for _, m in _rr.FRONTIER_SINGLE_MODELS]}")
    print(f"  gate_c_cardinality={_GATE_C_SCK10}")
    print("=" * 72)
    print(f"\nLoaded {len(tasks)} task(s).")

    result = run(
        tasks,
        cfg,
        checkpoint_path=args.checkpoint,
        cache_dir=args.cache_dir,
        rpm=args.rpm,
        seeds=seeds,
        dry_run=args.dry_run,
        budget_usd=args.budget_usd,
    )

    print(f"\n[SCK10] Result: {result}")
    if args.dry_run:
        total = result.get("total", "?")
        pending = result.get("pending", "?")
        done = result.get("done", "?")
        print(
            f"[SCK10] Dry-run grid: {total} total jobs "
            f"({pending} pending, {done} done) — sc-config only, k=10"
        )


if __name__ == "__main__":
    main()
