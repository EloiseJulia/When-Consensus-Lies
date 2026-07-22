# constructed by: Claude (Anthropic) family
"""Phase B diversified-evidence driver (Amendment 12 — EXPLORATORY secondary).

# Implementer model family: Claude / Anthropic
# Auditor model family: GPT (Law 6 — cross-family requirement)

Runs the TWO exploratory conditions {cross-vendor-synthesis, role-diversified}
(see ``harness/diversified.py``) over the FROZEN confirmatory item set from
``registered_run.load_tasks()`` — H1_external (40 items) as the primary bed +
H2_derivable (14 items) as a control — with the 3 FROZEN grid seeds
[global, global+1000, global+2000].

Additive isolation (design §4): writes to a SEPARATE checkpoint
``.run_partitions/cp_phaseB.jsonl`` and a SEPARATE cache ``.llm_cache_phaseB``.
It NEVER writes the confirmatory checkpoint/cache and NEVER edits the
confirmatory dispatch in ``harness/run.py`` / ``harness/runner.py`` /
``scripts/registered_run.py``.  It imports ``load_tasks`` + ``build_client``
from ``registered_run`` and the frozen labeler ``harness.label.label_run``
WITHOUT editing them.

Each result is labeled with the FROZEN labeler and appended to the checkpoint in
the SAME JSONL record shape (``harness.runner.CheckpointStore``) the confirmatory
run uses, so the existing analysis (cd_primary/A04 + abstention) consumes
``cp_phaseB.jsonl`` exactly as it consumes the confirmatory checkpoint.

OFFLINE / CI SAFE:
    ``main()`` requires RUNNER_LIVE=1 AND a reachable copilot_proxy; if either
    guard fails it prints "skipped" and exits 0 (no network, no cost).
    ``--dry-run`` enumerates the jobs (item x config x seed) with NO network.
    The pure ``run()`` function is callable by offline unit tests with an
    injected mock client (``_client_override``).  Resumable via the checkpoint.

Usage:
    # Dry-run: enumerate jobs (no network)
    python scripts/phaseB_diversified.py --dry-run

    # Live run ($0 on copilot_proxy) — requires a SEPARATE owner GO
    RUNNER_LIVE=1 python scripts/phaseB_diversified.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Repo root + scripts dir on sys.path ────────────────────────────────────
_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
# scripts/ is intentionally NOT a package — add it so `import registered_run`
# resolves the co-located confirmatory driver (imported, never edited).
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from harness.diversified import (  # noqa: E402
    CONFIG_CROSS_VENDOR_SYNTHESIS,
    CONFIG_ROLE_DIVERSIFIED,
    PHASEB_RUNNERS,
)


# ── Constants ────────────────────────────────────────────────────────────────

#: Separate checkpoint — NEVER the confirmatory run's checkpoint.
CHECKPOINT = ".run_partitions/cp_phaseB.jsonl"

#: Separate LLM disk cache — NEVER the confirmatory cache.
CACHE_DIR = ".llm_cache_phaseB"

#: Match the confirmatory run RPM.
RPM = 30

#: The two exploratory conditions (order = enumeration order).
_CONFIGS_PHASEB: List[str] = [
    CONFIG_CROSS_VENDOR_SYNTHESIS,
    CONFIG_ROLE_DIVERSIFIED,
]

#: Seed stride matching registered_run._SEED_STRIDE (1000): the 3 frozen grid
#: seeds are [global, global+1000, global+2000].
_SEED_STRIDE: int = 1000

#: Each config collapses to ONE final AgentRun per (item, seed) job → Gate C
#: minimum cardinality is 1 (like `single` / `verifier`).
_GATE_C_MIN_AGENTS: int = 1

# ── Confirmatory / other-pass artifacts this driver must NEVER overwrite ──────
# (BLOCKER guard — a live run with a bad --checkpoint/--cache-dir could otherwise
#  clobber the confirmatory run's data.)
_FORBIDDEN_CHECKPOINT_NAMES = frozenset({
    "registered_run_checkpoint.jsonl",   # confirmatory full run
    "pilot_gate_checkpoint.jsonl",       # §11 pilot gate
    "cp_sck10.jsonl",                    # A08 sc-k10 sensitivity pass
})
_FORBIDDEN_CACHE_NAMES = frozenset({
    ".llm_cache_registered_run",
    ".llm_cache_pilot_gate",
    ".llm_cache_sck10",
    ".llm_cache_default_check_h2add",
})


def _validate_output_paths(checkpoint_path: str, cache_dir: str) -> None:
    """Reject checkpoint/cache paths that could clobber another run's artifacts.

    Guards (raise ValueError on violation):
      - The checkpoint basename must not be a known confirmatory/other-pass
        checkpoint, and the checkpoint must live under a ``.run_partitions``
        directory OR a temp directory (the latter for tests).
      - The cache basename must not be a known confirmatory/other-pass cache dir.
    """
    import tempfile

    cp = Path(checkpoint_path).resolve()
    if cp.name in _FORBIDDEN_CHECKPOINT_NAMES:
        raise ValueError(
            f"Refusing to use checkpoint {checkpoint_path!r}: name collides with a "
            "confirmatory/other-pass artifact. Phase B must write its OWN checkpoint "
            "(e.g. .run_partitions/cp_phaseB.jsonl)."
        )
    tmp_root = Path(tempfile.gettempdir()).resolve()
    under_runparts = ".run_partitions" in cp.parts
    try:
        under_tmp = cp.is_relative_to(tmp_root)
    except AttributeError:  # Python < 3.9 fallback
        under_tmp = str(cp).startswith(str(tmp_root))
    if not (under_runparts or under_tmp):
        raise ValueError(
            f"Refusing to use checkpoint {checkpoint_path!r}: it is not under a "
            "'.run_partitions' directory (or a temp dir for tests). Phase B keeps "
            "its checkpoint isolated from the confirmatory run."
        )

    cache = Path(cache_dir).resolve()
    if cache.name in _FORBIDDEN_CACHE_NAMES:
        raise ValueError(
            f"Refusing to use cache dir {cache_dir!r}: name collides with a "
            "confirmatory/other-pass LLM cache. Phase B must use its OWN cache "
            "(e.g. .llm_cache_phaseB)."
        )


# ── Guards (mirror scripts/sensitivity_sck10.py) ─────────────────────────────

def _live_ok() -> bool:
    """Return True only when RUNNER_LIVE=1 (no token required for copilot_proxy)."""
    return os.environ.get("RUNNER_LIVE", "0") == "1"


def _proxy_reachable() -> bool:
    """Best-effort: True if copilot_proxy is accepting connections (2s timeout)."""
    import socket
    import urllib.error
    import urllib.request
    try:
        from common.llm import COPILOT_PROXY_BASE_URL
        url = COPILOT_PROXY_BASE_URL.rstrip("/") + "/models"
    except (ImportError, AttributeError):
        url = "http://127.0.0.1:8313/v1/models"
    try:
        urllib.request.urlopen(url, timeout=2)  # noqa: S310
        return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, OSError, socket.timeout):
        return False


# ── Final (model_role, model_id) identity per config ─────────────────────────
# Must match the AgentRun returned by the corresponding runner fn so the
# checkpoint job_done key and the run record agree.

def _final_identity(config: str, cfg: Dict[str, Any]) -> Tuple[str, str]:
    """Return (model_role, model_id) of the FINAL AgentRun produced by *config*.

    C5 synthesis → the frozen judge model (microsoft/mai-code-1-flash-picker).
    C7 role-diversified → the R5 integrator (anthropic/claude-opus-4.8).
    """
    if config == CONFIG_CROSS_VENDOR_SYNTHESIS:
        return "judge", cfg["roles"]["judge"]["model"]
    if config == CONFIG_ROLE_DIVERSIFIED:
        reasoning = cfg["roles"]["tested_agents"].get("reasoning", [])
        for entry in reasoning:
            if entry["family"] == "anthropic":
                return "tested_agents", entry["model"]
        return "tested_agents", "claude-opus-4.8"
    raise ValueError(f"Unknown Phase B config: {config!r}")


def _default_seeds(cfg: Dict[str, Any]) -> List[int]:
    global_seed = cfg.get("seeds", {}).get("global", 20260713)
    return [global_seed, global_seed + _SEED_STRIDE, global_seed + 2 * _SEED_STRIDE]


def enumerate_jobs(
    tasks: List[Any],
    configs: List[str],
    seeds: List[int],
) -> List[Dict[str, Any]]:
    """Enumerate every (item x config x seed) job (no network).

    Returns a list of job dicts with keys: task_id, config, model_role,
    model_id (deferred to run time — left as the pre-committed final identity is
    resolved from config there), seed.
    """
    jobs: List[Dict[str, Any]] = []
    for config in configs:
        for task in tasks:
            for seed in seeds:
                jobs.append({
                    "task_id": task.id,
                    "config": config,
                    "seed": int(seed),
                })
    return jobs


# ── Pure run function (offline-test-friendly) ────────────────────────────────

def run(
    tasks: List[Any],
    cfg: Dict[str, Any],
    *,
    checkpoint_path: str = CHECKPOINT,
    cache_dir: str = CACHE_DIR,
    rpm: int = RPM,
    seeds: Optional[List[int]] = None,
    configs: Optional[List[str]] = None,
    dry_run: bool = False,
    offline: bool = False,
    budget_usd: Optional[float] = None,
    _client_override: Optional[Any] = None,
) -> Dict[str, Any]:
    """Run (or dry-run) the Phase B exploratory conditions.

    Pure function — offline-test-friendly.  Inject ``_client_override`` to bypass
    client construction, or pass ``dry_run=True`` to enumerate with no network.

    Args:
        tasks: Frozen item set (H1_external 40 + H2_derivable 14 = 54 items).
        cfg: Loaded config dict (from common.config.load_config()).
        checkpoint_path: Separate JSONL checkpoint (default cp_phaseB.jsonl).
        cache_dir: Separate LLM disk cache (default .llm_cache_phaseB).
        rpm: Requests per minute per model.
        seeds: Grid seeds. Default: [global, global+1000, global+2000].
        configs: Config subset. Default: both Phase B conditions.
        dry_run: If True, enumerate jobs and return a report (no network).
        offline: If True and no override, build an offline (mock) LLMClient.
        budget_usd: Optional aggregate budget cap (copilot_proxy is $0).
        _client_override: Optional pre-built client (test injection point).

    Returns:
        Dict with ``status`` and job counts.  For dry-run:
        ``{status, total, done, pending, jobs}``.  For a run:
        ``{status, total, completed, skipped, checkpoint}``.
    """
    if seeds is None:
        seeds = _default_seeds(cfg)
    if configs is None:
        configs = list(_CONFIGS_PHASEB)

    # BLOCKER guard: a real (non-dry-run) execution WRITES — never let it target
    # a confirmatory/other-pass checkpoint or cache.  Dry-run is read-only.
    if not dry_run:
        _validate_output_paths(checkpoint_path, cache_dir)

    jobs = enumerate_jobs(tasks, configs, seeds)

    # Ensure the checkpoint directory exists before the store tries to write.
    cp = Path(checkpoint_path)
    cp.parent.mkdir(parents=True, exist_ok=True)

    from harness.runner import CheckpointStore
    store = CheckpointStore(cp)

    # Resolve the FINAL identity of each config once (from config).
    final_id: Dict[str, Tuple[str, str]] = {
        config: _final_identity(config, cfg) for config in configs
    }

    if dry_run:
        done = 0
        for job in jobs:
            role, model = final_id[job["config"]]
            if store.job_done(job["task_id"], job["config"], role, model, job["seed"]):
                done += 1
        total = len(jobs)
        return {
            "status": "dry_run",
            "total": total,
            "done": done,
            "pending": total - done,
            "jobs": jobs,
        }

    # ── Live / offline execution ─────────────────────────────────────────────
    task_by_id = {t.id: t for t in tasks}

    if _client_override is not None:
        client = _client_override
    else:
        import copy
        import registered_run as _rr
        # Deep-copy the config so per-job grid-seed binding
        # (client.config["seeds"]["global"] = seed) never mutates the caller's
        # cfg (which would corrupt _default_seeds on a subsequent call).
        client = _rr.build_client(
            copy.deepcopy(cfg),
            offline=offline,
            cache_dir=cache_dir,
            budget_usd=budget_usd,
            rpm=rpm,
        )

    from harness.label import label_run

    completed = 0
    skipped = 0
    for job in jobs:
        config = job["config"]
        seed = job["seed"]
        role, model = final_id[config]
        task_id = job["task_id"]

        if store.job_done(task_id, config, role, model, seed):
            skipped += 1
            continue

        task = task_by_id[task_id]

        # Bind this job's grid seed so the runner fn's base_seed matches (mirror
        # runner: job_config["seeds"]["global"] = seed).
        client.config["seeds"]["global"] = seed

        runner_fn = PHASEB_RUNNERS[config]
        runs = runner_fn(task, client)

        for run_obj in runs:
            run_obj.label = label_run(run_obj, task)
            # replicate_seed = grid seed groups the (item, seed) cell for the
            # analysis adapter (mirrors runner.add_run(run, replicate_seed=seed)).
            store.add_run(run_obj, replicate_seed=seed)
        store.mark_job_done(task_id, config, role, model, seed)
        completed += 1

    return {
        "status": "ok",
        "total": len(jobs),
        "completed": completed,
        "skipped": skipped,
        "checkpoint": str(cp),
    }


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
            "Phase B exploratory diversified-evidence conditions (Amendment 12) "
            "— cross-vendor-synthesis + role-diversified, separate checkpoint "
            "(.run_partitions/cp_phaseB.jsonl)"
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Enumerate the item x config x seed jobs without executing any",
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
        help="Override grid seeds (default: global + 0/1000/2000)",
    )
    parser.add_argument(
        "--domains",
        nargs="+",
        default=None,
        help="Domains to load (default: all 3: code_spec data_analysis policy_qa)",
    )
    args = parser.parse_args(argv)

    if not args.dry_run:
        if not _live_ok():
            print(
                "phaseB_diversified: skipped (RUNNER_LIVE != 1). "
                "Set RUNNER_LIVE=1 to run live (copilot_proxy, no token required)."
            )
            sys.exit(0)
        if not _proxy_reachable():
            print(
                "phaseB_diversified: skipped (copilot_proxy not reachable at "
                "http://127.0.0.1:8313). Start the proxy before running live."
            )
            sys.exit(0)

    from common.config import load_config
    import registered_run as _rr

    cfg = load_config()
    tasks = _rr.load_tasks(args.domains)  # all 3 domains if None → 54 items

    seeds = args.seeds or _default_seeds(cfg)

    print("=" * 72)
    print("PHASE B — EXPLORATORY diversified-evidence conditions (Amendment 12)")
    print(f"  configs: {_CONFIGS_PHASEB}")
    print(f"  checkpoint={args.checkpoint}")
    print(f"  cache={args.cache_dir}")
    print(f"  rpm={args.rpm}  seeds={seeds}")
    print(f"  gate_c_min_agents={_GATE_C_MIN_AGENTS}")
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

    print(f"\n[PhaseB] Result: {result}")
    if args.dry_run:
        print(
            f"[PhaseB] Dry-run grid: {result['total']} total jobs "
            f"({result['pending']} pending, {result['done']} done) — "
            f"{len(_CONFIGS_PHASEB)} configs x {len(tasks)} items x {len(seeds)} seeds"
        )


if __name__ == "__main__":
    main()
