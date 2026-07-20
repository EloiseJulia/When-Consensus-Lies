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

    Uses a 2-second timeout; any network error → False (offline / CI safe).
    """
    import urllib.request
    try:
        from common.llm import COPILOT_PROXY_BASE_URL
        url = COPILOT_PROXY_BASE_URL.rstrip("/") + "/v1/models"
    except (ImportError, AttributeError):
        url = "http://127.0.0.1:8313/v1/models"
    try:
        urllib.request.urlopen(url, timeout=2)  # noqa: S310
        return True
    except Exception:
        return False


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

    return runner.run(dry_run=dry_run)


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
