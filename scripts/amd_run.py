# constructed by: Claude (Anthropic) family
"""Amendment 13 / 14 SIDECAR run driver — When Consensus Lies.

# Implementer model family: Claude/Anthropic

ADDITIVE. Drives a SIDECAR item set (Amendment 13 regime×domain crossing OR
Amendment 14 unfiltered-sample replication) through the pre-registered HEADLINE
conditions ``single`` + ``heterogeneous-MAD`` (cross-family), ≥3 seeds, on the
frozen Amendment-06 roster, $0 via the copilot proxy.

It REUSES the frozen apparatus read-only:
  * ``scripts/registered_run.py``  — ``build_runner`` (LLMClient + Runner wiring),
    the frozen ``FRONTIER_SINGLE_MODELS`` roster, bootstrap-CI helpers.
  * ``harness/runner.py``          — the resumable ``Runner`` grid loop.
  * ``harness/label.py``           — the frozen executable-gold labeler.
  * ``bench.amd13_sidecar`` / ``bench.amd14_sidecar`` — imported so ``register()``
    additively wires the amd* executable-gold checkers into the frozen bench
    registries (never mutating a frozen entry).

ISOLATION (INVIOLABLE):
  * Its checkpoint lives under ``.run_partitions/cp_amd_run__<which>.jsonl`` and
    its cache under ``.llm_cache_amd_run_<which>`` — a path guard REFUSES any
    checkpoint/cache whose resolved path carries a confirmatory / intervention /
    pilot / registered-run token, so it can NEVER read or write another pass's
    artifacts.
  * No frozen file is edited; the frozen 54 confirmatory items / schema / metrics
    / results are untouched. This driver only READS the frozen bench + harness.

OFFLINE / CI SAFE:
  Live execution requires ``RUNNER_LIVE=1`` (no token — the proxy is free). Without
  it (and without ``--dry-run``) ``main()`` prints "skipped" and exits 0 — no
  network, no cost. ``--dry-run`` enumerates the job grid with NO live calls.

Usage::

    python scripts/amd_run.py --which amd13 --dry-run
    python scripts/amd_run.py --which amd14 --dry-run
    RUNNER_LIVE=1 python scripts/amd_run.py --which amd13
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Repo root on sys.path (scripts/ is not a package) ──────────────────────
_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ── Reuse registered_run.py (loaded as a module; scripts/ is not a package) ──

def _load_registered_run():
    """Import scripts/registered_run.py as a module and return it."""
    if "registered_run" in sys.modules:
        return sys.modules["registered_run"]
    path = _SCRIPTS_DIR / "registered_run.py"
    spec = importlib.util.spec_from_file_location("registered_run", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    sys.modules["registered_run"] = mod
    return mod


# ── Constants ────────────────────────────────────────────────────────────────

WHICH_CHOICES = ("amd13", "amd14")
PROVIDER = "copilot_proxy"

# Pre-registered HEADLINE conditions (the cross-family conditions that show fake
# redundancy). NOT the full SC/verifier grid (Amendment 13 §6 / Amendment 14 §4).
#
# STRICTLY ALLOWED — no other config may run. In particular ``interpretation-diverse``
# (harness.run.run_diverse) injects ``interp.gold_check`` into the tested-agent prompt
# (harness/run.py run_diverse), which would LEAK the executable-gold id — an anti-
# leakage violation. Only these two pre-registered conditions are permitted here.
ALLOWED_CONFIGS: Tuple[str, ...] = ("single", "heterogeneous-MAD")
AMD_CONFIGS: List[str] = list(ALLOWED_CONFIGS)
# heterogeneous-MAD uses the config.yaml heterogeneous pool; n_agents=4 (default),
# stated explicitly for auditability (mirrors registered_run).
AMD_CONFIG_KWARGS: Dict[str, Dict[str, Any]] = {"heterogeneous-MAD": {"n_agents": 4}}

# The frozen Amendment-06 single-model roster (reused verbatim from registered_run).
# heterogeneous-MAD is handled by the pool path inside the Runner.

# Sidecar item-file defaults (relative to repo root).
_AMD13_ITEM_FILES = ["bench/data/amd13_code_spec.jsonl", "bench/data/amd13_policy_qa.jsonl"]
_AMD14_ITEM_FILES = ["bench/data/amd14_unfiltered.jsonl"]

# Matched H1_external anchors already present in the FROZEN code_spec / policy_qa
# benches — the within-domain comparison group for the Amendment-13 regime×domain
# contrast. Referenced READ-ONLY (never re-authored). Four per domain, matched to
# the four amd13 H2 base tasks by convention class (rounding / indexing / fiscal /
# derivable-numeric). These frozen items are NOT modified — only read for the
# H1-vs-H2 contrast.
AMD13_H1_ANCHORS: Dict[str, List[str]] = {
    "code_spec": [
        "code_roundcurr_001_k1_rounding_standard",     # matches roundhalf (rounding tie)
        "code_getitems_001_k1_indexing_convention",    # matches weekopponent (0/1-based)
        "code_quarter_001_k1_fiscal_year_start",        # fiscal-boundary convention
        "code_date_001_k1_date_format_convention",      # format convention
    ],
    "policy_qa": [
        "policy_interest_001_k1_compounding",           # matches amd13interest
        "policy_tip_001_k1_tip_base",                   # matches amd13tip
        "policy_discount_001_k1_discount_basis",        # matches amd13discount
        "policy_overtime_001_k1_overtime_threshold",    # threshold convention
    ],
}

# Default seeds: ≥3 distinct (spaced by the registered_run stride so per-agent seed
# ranges never overlap across replicates).
DEFAULT_N_SEEDS = 3
RPM_DEFAULT = 30

# Protected tokens: if ANY appears in the resolved checkpoint/cache path, refuse —
# this driver must be fully isolated from every other pass.
_PROTECTED_PATH_SUBSTR = (
    "registered_run", "cp_lps_confirm", "lps_confirm", "llm_cache_lps_confirm",
    "lps_intervention", "cp_lps_intervention", "llm_cache_lps_intv",
    "intervention", "confirm", "pilot", "pilot_gate", "default_check",
    "sck10", "phaseb",
)


def _which_defaults(which: str) -> Tuple[str, str, List[str]]:
    """Return (checkpoint_path, cache_dir, item_files) for *which*."""
    if which == "amd13":
        return (
            str(_REPO_ROOT / ".run_partitions" / "cp_amd_run__amd13.jsonl"),
            str(_REPO_ROOT / ".llm_cache_amd_run_amd13"),
            _AMD13_ITEM_FILES,
        )
    if which == "amd14":
        return (
            str(_REPO_ROOT / ".run_partitions" / "cp_amd_run__amd14.jsonl"),
            str(_REPO_ROOT / ".llm_cache_amd_run_amd14"),
            _AMD14_ITEM_FILES,
        )
    raise ValueError(f"unknown --which {which!r}; expected one of {WHICH_CHOICES}")


# ── Path guard (isolation) ───────────────────────────────────────────────────

def _rel_lower(p: Path) -> str:
    try:
        return p.resolve().relative_to(_REPO_ROOT.resolve()).as_posix().lower()
    except ValueError:
        return p.resolve().as_posix().lower()


def _scan_protected(path: Path, label: str) -> None:
    rel = _rel_lower(path)
    hit = next((tok for tok in _PROTECTED_PATH_SUBSTR if tok in rel), None)
    if hit is not None:
        raise ValueError(
            f"Refusing {label} {path!s}: protected token {hit!r} appears in the "
            "resolved path — it lives inside a confirmatory/intervention/pilot/"
            "registered-run namespace. The amd_run driver must be fully isolated."
        )


def validate_output_paths(checkpoint_path: str, cache_dir: str) -> None:
    """Reject any checkpoint/cache path that could touch another pass's artifacts.

    (1) basenames must be in the amd_run namespace (``cp_amd_run__*`` / ``.llm_cache_amd_run*``);
    (2) NO protected substring anywhere in the resolved path (so a nested foreign
        directory cannot smuggle a write in).
    """
    cp = Path(checkpoint_path)
    cache = Path(cache_dir)
    if not cp.name.startswith("cp_amd_run__"):
        raise ValueError(
            f"Refusing checkpoint {checkpoint_path!r}: amd_run must write its OWN "
            "checkpoint (cp_amd_run__<which>*.jsonl), never a confirmatory/other-pass file."
        )
    if not cache.name.startswith(".llm_cache_amd_run"):
        raise ValueError(
            f"Refusing cache dir {cache_dir!r}: amd_run must use its OWN cache "
            "(.llm_cache_amd_run*), never a confirmatory/other-pass cache."
        )
    _scan_protected(cp, "checkpoint")
    _scan_protected(cache, "cache dir")


def validate_configs(configs: List[str]) -> None:
    """Reject any config outside the pre-registered {single, heterogeneous-MAD}.

    ``interpretation-diverse`` (and any other config) is REFUSED because its harness
    path can inject gold-bearing text (``interp.gold_check``) into the tested-agent
    prompt — an anti-leakage violation. Only the two pre-registered headline
    conditions are permitted.
    """
    bad = [c for c in configs if c not in ALLOWED_CONFIGS]
    if bad:
        raise ValueError(
            f"Refusing configs {bad!r}: amd_run permits ONLY {list(ALLOWED_CONFIGS)} "
            "(the pre-registered headline conditions). Other configs (e.g. "
            "'interpretation-diverse') can leak the executable-gold id into the "
            "tested-agent prompt — an anti-leakage violation."
        )


def scan_protected_path(path: Path, label: str) -> None:
    """Public wrapper around the protected-token scan (reused by report/manip)."""
    _scan_protected(path, label)


# ── Task loading (sidecar + matched frozen H1 anchors, read-only) ────────────

def _register_sidecar(which: str) -> None:
    """Import the sidecar module and additively register its gold checkers."""
    if which == "amd13":
        import bench.amd13_sidecar as sc  # noqa: WPS433
        sc.register()
    elif which == "amd14":
        import bench.amd14_sidecar as sc  # noqa: WPS433
        sc.register()
    else:
        raise ValueError(f"unknown --which {which!r}")


def _load_h1_anchors() -> List[Any]:
    """Load the matched FROZEN H1_external anchors (read-only) for the A13 contrast."""
    from bench.build import Task  # noqa: F401  (type only)
    import bench.code_spec as cs
    import bench.policy_qa as pq

    by_id: Dict[str, Any] = {}
    for t in cs.generate_tasks():
        by_id[t.id] = t
    for t in pq.generate_tasks():
        by_id[t.id] = t

    anchors: List[Any] = []
    missing: List[str] = []
    for domain, ids in AMD13_H1_ANCHORS.items():
        for tid in ids:
            if tid in by_id:
                anchors.append(by_id[tid])
            else:
                missing.append(tid)
    if missing:
        raise KeyError(
            f"amd_run: matched H1 anchors not found in the frozen benches: {missing}. "
            "Check AMD13_H1_ANCHORS against bench.code_spec / bench.policy_qa."
        )
    return anchors


def load_amd_tasks(
    which: str,
    *,
    items_file: Optional[List[str]] = None,
    include_h1_anchors: bool = True,
) -> List[Any]:
    """Load the sidecar item set (+ matched frozen H1 anchors for amd13).

    Registers the sidecar gold checkers first (so the harness can label the items).

    Args:
        which: ``"amd13"`` or ``"amd14"``.
        items_file: Override the default sidecar JSONL file(s). When None, uses the
            per-``which`` defaults.
        include_h1_anchors: For amd13, also load the matched FROZEN H1_external
            anchors (read-only) for the within-domain regime contrast. Ignored for
            amd14 (its sidecar items are the whole unfiltered H1-type sample).

    Returns:
        Flat list of Task objects (sidecar H2/H1-type items + optional H1 anchors).
    """
    if which not in WHICH_CHOICES:
        raise ValueError(f"unknown --which {which!r}; expected one of {WHICH_CHOICES}")

    _register_sidecar(which)
    from bench.build import load_tasks as _load_jsonl

    _, _, default_files = _which_defaults(which)
    files = items_file if items_file else default_files

    tasks: List[Any] = []
    for f in files:
        path = f if os.path.isabs(f) else str(_REPO_ROOT / f)
        tasks.extend(_load_jsonl(path))

    if which == "amd13" and include_h1_anchors:
        tasks.extend(_load_h1_anchors())

    return tasks


# ── Dry-run job-count helper ─────────────────────────────────────────────────

def expected_job_count(
    n_tasks: int,
    *,
    seeds: List[int],
    configs: List[str] = None,
    n_single_models: Optional[int] = None,
) -> int:
    """Enumerate the expected job count WITHOUT building a Runner.

    grid = tasks × Σ_config(models_for_config) × seeds, where a single-model config
    sweeps ``n_single_models`` models and a pool config (heterogeneous-MAD) is ONE
    pooled cell.
    """
    rr = _load_registered_run()
    if configs is None:
        configs = AMD_CONFIGS
    if n_single_models is None:
        n_single_models = len(rr.FRONTIER_SINGLE_MODELS)
    from harness.runner import POOL_CONFIGS

    per_task_per_seed = 0
    for cfg_name in configs:
        per_task_per_seed += 1 if cfg_name in POOL_CONFIGS else n_single_models
    return n_tasks * per_task_per_seed * len(set(seeds))


# ── Runner wiring (reuse registered_run.build_runner) ────────────────────────

def build_amd_runner(
    cfg: Dict[str, Any],
    tasks: List[Any],
    *,
    which: str,
    checkpoint_path: str,
    cache_dir: str,
    seeds: List[int],
    configs: List[str] = None,
    budget_usd: Optional[float] = None,
    rpm: int = RPM_DEFAULT,
    offline: bool = False,
):
    """Build the amd_run Runner (REUSES registered_run.build_runner)."""
    validate_output_paths(checkpoint_path, cache_dir)
    rr = _load_registered_run()
    if configs is None:
        configs = AMD_CONFIGS
    validate_configs(configs)
    return rr.build_runner(
        cfg,
        tasks,
        checkpoint_path=checkpoint_path,
        models=rr.FRONTIER_SINGLE_MODELS,
        configs=configs,
        seeds=seeds,
        budget_usd=budget_usd,
        rpm=rpm,
        offline=offline,
        cache_dir=cache_dir,
        config_kwargs=AMD_CONFIG_KWARGS,
    )


def _default_seeds(cfg: Dict[str, Any], n: int = DEFAULT_N_SEEDS) -> List[int]:
    rr = _load_registered_run()
    stride = getattr(rr, "_SEED_STRIDE", 1000)
    base = cfg.get("seeds", {}).get("global", 20260713)
    return [base + i * stride for i in range(n)]


# ── CLI ──────────────────────────────────────────────────────────────────────

def _live_ok() -> bool:
    return os.environ.get("RUNNER_LIVE", "0") == "1"


def main(argv=None) -> None:
    """CLI entry point. Prints 'skipped' and exits 0 when RUNNER_LIVE != 1 (non-dry)."""
    parser = argparse.ArgumentParser(
        description="Amendment 13/14 sidecar run driver (single + heterogeneous-MAD)"
    )
    parser.add_argument("--which", choices=WHICH_CHOICES, required=True,
                        help="Which sidecar item set to run.")
    parser.add_argument("--items-file", nargs="+", default=None,
                        help="Override the sidecar JSONL item file(s).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Enumerate the job grid without executing anything.")
    parser.add_argument("--no-h1-anchors", action="store_true",
                        help="amd13 only: skip the matched frozen H1 anchors.")
    parser.add_argument("--configs", nargs="+", default=None,
                        help=f"Conditions to run (default: {AMD_CONFIGS}).")
    parser.add_argument("--seeds", nargs="+", type=int, default=None,
                        help="Seeds (default: 3 distinct spaced seeds).")
    parser.add_argument("--checkpoint", default=None,
                        help="Checkpoint JSONL (default: .run_partitions/cp_amd_run__<which>.jsonl).")
    parser.add_argument("--cache-dir", default=None,
                        help="LLM cache dir (default: .llm_cache_amd_run_<which>).")
    parser.add_argument("--rpm", type=int, default=RPM_DEFAULT)
    parser.add_argument("--budget-usd", type=float, default=None)
    args = parser.parse_args(argv)

    # Guard: live run needs RUNNER_LIVE=1 (dry-run bypasses).
    if not args.dry_run and not _live_ok():
        print(
            "amd_run: skipped (RUNNER_LIVE != 1). "
            "Set RUNNER_LIVE=1 to run live (copilot_proxy, no token required)."
        )
        sys.exit(0)

    from common.config import load_config
    cfg = load_config()

    def_cp, def_cache, _ = _which_defaults(args.which)
    checkpoint = args.checkpoint or def_cp
    cache_dir = args.cache_dir or def_cache
    configs = args.configs or AMD_CONFIGS
    try:
        validate_configs(configs)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    seeds = args.seeds or _default_seeds(cfg)

    # Enforce ≥3 distinct seeds (pre-registered) for a LIVE run (dry-run is exempt).
    if not args.dry_run and len(set(seeds)) < 3:
        print(
            f"ERROR: pre-registered run requires ≥3 distinct seeds; got {seeds}.",
            file=sys.stderr,
        )
        sys.exit(1)

    include_anchors = (args.which == "amd13") and (not args.no_h1_anchors)
    tasks = load_amd_tasks(
        args.which, items_file=args.items_file, include_h1_anchors=include_anchors
    )

    rr = _load_registered_run()
    n_single = len(rr.FRONTIER_SINGLE_MODELS)
    expected = expected_job_count(
        len(tasks), seeds=seeds, configs=configs, n_single_models=n_single,
    )

    print("=" * 72)
    print(f"AMD RUN — {args.which} sidecar — copilot_proxy")
    print(f"  checkpoint={checkpoint}")
    print(f"  cache={cache_dir}")
    print(f"  configs={configs}  seeds={seeds}  rpm={args.rpm}")
    print(f"  single-model roster: {[m for _, m in rr.FRONTIER_SINGLE_MODELS]}")
    print(f"  tasks loaded: {len(tasks)}  (H1_external="
          f"{sum(1 for t in tasks if t.regime == 'H1_external')}, "
          f"H2_derivable={sum(1 for t in tasks if t.regime == 'H2_derivable')})")
    print(f"  EXPECTED JOB COUNT: {expected}")
    print("=" * 72)

    # dry-run also uses no network (offline client) as a defense-in-depth.
    runner, client = build_amd_runner(
        cfg, tasks,
        which=args.which,
        checkpoint_path=checkpoint,
        cache_dir=cache_dir,
        seeds=seeds,
        configs=configs,
        budget_usd=args.budget_usd,
        rpm=args.rpm,
        offline=args.dry_run,
    )

    result = runner.run(dry_run=args.dry_run)

    if args.dry_run:
        total = result.get("total")
        print(f"[DRY-RUN] grid total={total}  done={result.get('done')}  "
              f"pending={result.get('pending')}")
        if total != expected:
            print(
                f"WARNING: enumerated grid total {total} != expected {expected}.",
                file=sys.stderr,
            )
        print("[DRY-RUN] no live calls, no confirmatory writes.")
        return

    print(f"[AMD RUN] Result: {result}")
    total_cost = getattr(client, "_total_cost_usd", 0.0)
    print(f"[AMD RUN] Total cost: ${total_cost:.6f} USD")


if __name__ == "__main__":
    main()
