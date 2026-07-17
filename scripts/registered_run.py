# constructed by: Claude (Anthropic) family
"""Registered-run driver for When Consensus Lies.

# Implementer model family: Claude/Anthropic

Deliverables D2 + D4 (paper/plans/2026-07-17-registered-run-wiring-plan.md):

D2: All-3-domain task loader (code_spec + data_analysis + policy_qa) preserving
    Task.regime and Task.ambiguity_level, driving the resumable Runner on the
    Amendment-06 frontier Copilot-proxy roster.

D4: ``--pilot`` mode — a guarded §11 MVP pilot-gate driver that runs a SMALL
    balanced batch (~6-10 items, half H1_external half H2_derivable, mixed k)
    via the Runner on copilot_proxy, labels via executable gold, builds the D3
    tidy table, and checks the pre-registered §11 gate:
      (a) cd_primary > 0 on real H1_external items
      (b) R1 label-shuffle null CD ≈ 0 while real CD > 0 (REUSES harness/nulls.py)
      (c) real run→label→tidy-table→metrics integration passes
    Prints a PASS/FAIL verdict + per-condition I_perp rate + total cost.

OFFLINE / CI SAFE:
    Live execution requires RUNNER_LIVE=1 (no token — copilot_proxy is always free).
    Without this flag both main() and the --pilot path print "skipped" and exit 0
    (no network, no cost). The live path is NEVER triggered in the test suite
    (which never sets RUNNER_LIVE=1).

Hard guards (pilot):
    - Item cap: PILOT_MAX_ITEMS = 10 (never full-scale from this path)
    - Budget cap: PILOT_BUDGET_USD = 1.00 (copilot_proxy is free but defensive)
    - Checkpoint: pilot_gate_checkpoint.jsonl (separate from the full run)

Usage:
    # Pilot gate (verifies §11 gate offline with mock, online with RUNNER_LIVE=1)
    RUNNER_LIVE=1 python scripts/registered_run.py --pilot

    # Full registered run (dry-run: enumerate grid without executing)
    python scripts/registered_run.py --dry-run --domains code_spec data_analysis

    # Full registered run (live, all 3 domains)
    RUNNER_LIVE=1 python scripts/registered_run.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Repo root on sys.path (scripts/ is not a package) ──────────────────────
_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ── Guard: RUNNER_LIVE=1 required; no token needed (copilot_proxy) ──────────

def _live_ok() -> bool:
    """Return True only when RUNNER_LIVE=1 is set (no token required)."""
    return os.environ.get("RUNNER_LIVE", "0") == "1"


# ── Frontier roster for the registered run ───────────────────────────────────
# Amendment-06 copilot-proxy slugs verified live 2026-07-18.
# Single-model sweep configs (single, sc, homogeneous-MAD, verifier,
# interpretation-diverse) iterate over these. heterogeneous-MAD uses the
# config.yaml heterogeneous pool automatically (via runner._pool_identity).

FRONTIER_SINGLE_MODELS: List[Tuple[str, str]] = [
    # homogeneous ρ-baseline
    ("tested_agents", "gpt-5.4"),
    # reasoning
    ("tested_agents", "gpt-5.6-sol"),
    ("tested_agents", "claude-opus-4.8"),
    ("tested_agents", "gemini-3.1-pro-preview"),
    # weak
    ("tested_agents", "gpt-4o-mini"),
    ("tested_agents", "gemini-3.5-flash"),
    ("tested_agents", "claude-haiku-4.5"),
]

# Configs for the full registered run (all six from runner.ALL_CONFIGS).
# heterogeneous-MAD is handled by the pool path in the runner.
REGISTERED_CONFIGS = [
    "single",
    "sc",
    "homogeneous-MAD",
    "heterogeneous-MAD",
    "verifier",
    "interpretation-diverse",
]

# Pilot uses only sc on the homogeneous baseline to keep the batch small.
PILOT_MODELS: List[Tuple[str, str]] = [("tested_agents", "gpt-5.4")]
PILOT_CONFIGS = ["sc"]
PILOT_MAX_ITEMS = 10     # hard item cap — never full-scale from --pilot
PILOT_BUDGET_USD = 1.00  # defensive cap (copilot_proxy is free)

PROVIDER = "copilot_proxy"
FULL_CHECKPOINT = "registered_run_checkpoint.jsonl"
PILOT_CHECKPOINT = "pilot_gate_checkpoint.jsonl"
CACHE_DIR_FULL = ".llm_cache_registered_run"
CACHE_DIR_PILOT = ".llm_cache_pilot_gate"
RPM_DEFAULT = 30
MAX_TOKENS_PER_CALL = 12288  # raised for frontier reasoners


# ── Domain loading (D2) ──────────────────────────────────────────────────────

_ALL_DOMAIN_NAMES = ("code_spec", "data_analysis", "policy_qa")

_DOMAIN_LOADERS = {
    "code_spec":      lambda: __import__("bench.code_spec",    fromlist=["generate_tasks"]).generate_tasks(),
    "data_analysis":  lambda: __import__("bench.data_analysis", fromlist=["generate_tasks"]).generate_tasks(),
    "policy_qa":      lambda: __import__("bench.policy_qa",    fromlist=["generate_tasks"]).generate_tasks(),
}


def load_tasks(domains: Optional[List[str]] = None) -> List[Any]:
    """Load and return tasks from the specified domains (default: all three).

    Preserves Task.regime and Task.ambiguity_level exactly as authored in the
    frozen benches (bench/* files are INVIOLABLE).

    Args:
        domains: List of domain names (subset of "code_spec", "data_analysis",
            "policy_qa"). When None or empty, loads all three.

    Returns:
        Flat list of Task objects from all requested domains.
    """
    if not domains:
        domains = list(_ALL_DOMAIN_NAMES)
    tasks: List[Any] = []
    for domain in domains:
        loader = _DOMAIN_LOADERS.get(domain)
        if loader is None:
            raise ValueError(
                f"Unknown domain {domain!r}; expected one of "
                f"{sorted(_DOMAIN_LOADERS)}"
            )
        tasks.extend(loader())
    return tasks


# ── Balanced pilot-subset selection ─────────────────────────────────────────

def _select_balanced_k(tasks: List[Any], n: int) -> List[Any]:
    """Select up to n tasks with balanced ambiguity_level values (round-robin)."""
    if len(tasks) <= n:
        return list(tasks)
    by_k: Dict[int, List[Any]] = {}
    for t in tasks:
        k = t.ambiguity_level
        by_k.setdefault(k, []).append(t)
    result: List[Any] = []
    k_values = sorted(by_k)
    i = 0
    while len(result) < n:
        k = k_values[i % len(k_values)]
        if by_k[k]:
            result.append(by_k[k].pop(0))
        i += 1
    return result


def select_pilot_tasks(
    all_tasks: List[Any],
    n_pilot: int = PILOT_MAX_ITEMS,
) -> List[Any]:
    """Select a balanced pilot batch: ~half H1_external, ~half H2_derivable.

    Both halves are drawn with balanced ambiguity_level (k) values so the gate
    exercises both regime classes and multiple k levels.

    When one regime is sparse (fewer than half), the other regime backfills to
    maximise the batch size up to n_pilot.

    Args:
        all_tasks: Full task list from one or more domains.
        n_pilot: Max total tasks (hard cap; default PILOT_MAX_ITEMS).

    Returns:
        List of at most n_pilot tasks, balanced across regimes and k values.
    """
    h1 = [t for t in all_tasks if t.regime == "H1_external"]
    h2 = [t for t in all_tasks if t.regime == "H2_derivable"]

    # Request half from each regime.
    half = min(n_pilot // 2, len(h1))
    selected_h1 = _select_balanced_k(h1, half)

    rest = min(n_pilot - len(selected_h1), len(h2))
    selected_h2 = _select_balanced_k(h2, rest)

    # Backfill from H1 if H2 is sparse.
    shortage = n_pilot - len(selected_h1) - len(selected_h2)
    if shortage > 0 and len(h1) > len(selected_h1):
        extra = min(shortage, len(h1) - len(selected_h1))
        selected_h1 = _select_balanced_k(h1, len(selected_h1) + extra)

    return selected_h1 + selected_h2


# ── Runner and analysis helpers ──────────────────────────────────────────────

def build_client(
    cfg: Dict[str, Any],
    *,
    offline: bool,
    cache_dir: str,
    budget_usd: Optional[float],
    rpm: int,
    max_tokens: int = MAX_TOKENS_PER_CALL,
):
    """Build a copilot-proxy LLMClient (no token required)."""
    from common.llm import LLMClient

    return LLMClient(
        cfg,
        cache_dir=cache_dir,
        offline=offline,
        max_budget_usd=budget_usd,
        max_requests_per_min=rpm,
        max_tokens_per_call=max_tokens,
        provider=PROVIDER,
        require_auth=False,
    )


def build_runner(
    cfg: Dict[str, Any],
    tasks: List[Any],
    *,
    checkpoint_path: str,
    models: List[Tuple[str, str]],
    configs: List[str],
    seeds: List[int],
    budget_usd: Optional[float],
    rpm: int,
    offline: bool,
    cache_dir: str,
):
    """Build a configured Runner instance."""
    from harness.runner import Runner, RunnerConfig

    client = build_client(
        cfg,
        offline=offline,
        cache_dir=cache_dir,
        budget_usd=budget_usd,
        rpm=rpm,
    )
    runner_cfg = RunnerConfig(
        tasks=tasks,
        configs=configs,
        seeds=seeds,
        models=models,
        checkpoint_path=Path(checkpoint_path),
        rpm=rpm,
        max_budget_usd=budget_usd,
    )
    return Runner(runner_cfg, client), client


# ── §11 Pilot gate ────────────────────────────────────────────────────────────

def run_pilot_gate(
    cfg: Dict[str, Any],
    tasks: List[Any],
    *,
    checkpoint_path: str,
    budget_usd: float = PILOT_BUDGET_USD,
    rpm: int = RPM_DEFAULT,
    offline: bool = False,
    cache_dir: str = CACHE_DIR_PILOT,
    n_pilot: int = PILOT_MAX_ITEMS,
    seed: int = 20260713,
    _runner_override=None,     # injection point for tests
) -> Dict[str, Any]:
    """Execute the §11 MVP pilot gate and return a structured report.

    Gate conditions (pre-registered §11):
      (a) cd_primary > 0 on at least one H1_external item (real convergent
          delusion observed above zero).
      (b) R1 label-shuffle null: the population-level shuffle null (per
          harness/nulls.py) is < real CD — random reassignment of labels gives
          lower CD than the real item-aligned labels.
      (c) Pipeline integration: runner → checkpoint → load_runs_tidy →
          compute_cell_cd completes without error and produces non-empty output.

    This is a LIVE function. The offline test path is exercised by the unit test
    in tests/test_registered_run.py which passes ``offline=True`` and a synthetic
    checkpoint.

    Args:
        cfg: Loaded config dict.
        tasks: Pre-selected pilot task list (≤ PILOT_MAX_ITEMS items).
        checkpoint_path: Path for the pilot checkpoint JSONL.
        budget_usd: Hard budget cap (defensive; copilot_proxy is free).
        rpm: Requests per minute.
        offline: If True, use offline mock client (for unit tests only).
        cache_dir: LLM disk cache directory.
        n_pilot: Max items (sanity check; tasks should already be capped).
        seed: Global RNG seed.
        _runner_override: Optional (runner, client) tuple for test injection.

    Returns:
        dict with keys: gate_pass, gate_a, gate_b, gate_c, real_cd, null_cd,
        iperp_rate, n_items, n_runs, total_cost_usd, conditions.
    """
    from analysis.cd import cd_primary as _cd_primary_fn
    from analysis.contrasts import COLS, compute_cell_cd
    from analysis.io import FRONTIER_MODEL_CLASS_MAP, load_runs_tidy
    from harness.nulls import label_shuffle_null

    if len(tasks) > n_pilot:
        tasks = tasks[:n_pilot]

    if _runner_override is not None:
        runner, client = _runner_override
    else:
        runner, client = build_runner(
            cfg,
            tasks,
            checkpoint_path=checkpoint_path,
            models=PILOT_MODELS,
            configs=PILOT_CONFIGS,
            seeds=[seed],
            budget_usd=budget_usd,
            rpm=rpm,
            offline=offline,
            cache_dir=cache_dir,
        )

    # Execute the run (or load from cache on resume).
    run_result = runner.run(dry_run=False)
    total_cost = getattr(client, "_total_cost_usd", 0.0)

    # Build tidy table via D3 adapter.
    tidy_df = load_runs_tidy(checkpoint_path, tasks,
                             model_class_map=FRONTIER_MODEL_CLASS_MAP)

    # Gate (c): integration — did we get a non-empty tidy table?
    gate_c = len(tidy_df) > 0

    # Per-condition I_perp rates for diagnostics.
    regime_col = COLS["regime"]
    label_col = COLS["label"]
    method_col = COLS["method"]
    conditions: List[Dict] = []
    if gate_c:
        for (regime, method), grp in tidy_df.groupby([regime_col, method_col], dropna=False):
            labels = list(grp[label_col])
            n = len(labels)
            n_perp = sum(1 for l in labels if l == "I_perp")
            conditions.append({
                "regime": regime,
                "method": method,
                "n_runs": n,
                "iperp_rate": n_perp / n if n else 0.0,
            })

    # Gate (a): cd_primary > 0 on H1_external items.
    real_cd = 0.0
    h1_df = tidy_df[tidy_df[regime_col] == "H1_external"] if gate_c else tidy_df
    if len(h1_df) > 0:
        cells = compute_cell_cd(h1_df)
        if len(cells) > 0:
            real_cd = float(cells["cd_primary"].mean())
    gate_a = real_cd > 0

    # Gate (b): shuffle null CD < real CD (REUSE harness/nulls.py — never redefine).
    null_cd = 0.0
    if gate_c and len(h1_df) > 0:
        item_col = COLS["item"]
        target_col = COLS["target"]
        # Group by item and collect labels for the shuffle null.
        items_labels: List[List[str]] = []
        # Use the first target (by convention "I0" for all bench tasks).
        # Each item may have a different target so we compute null per target value.
        target_vals = h1_df[target_col].unique() if target_col in h1_df.columns else []
        # Simple approach: compute null per unique target and average.
        null_per_target: List[float] = []
        for tgt in target_vals:
            tgt_df = h1_df[h1_df[target_col] == tgt]
            per_item = [list(grp[label_col]) for _, grp in tgt_df.groupby(item_col)]
            if len(per_item) >= 2:
                null_per_target.append(
                    label_shuffle_null(per_item, target=tgt, n_perm=200, seed=42)
                )
        null_cd = sum(null_per_target) / len(null_per_target) if null_per_target else 0.0
    gate_b = null_cd < real_cd if real_cd > 0 else False

    gate_pass = gate_a and gate_b and gate_c
    iperp_rate = float((tidy_df[label_col] == "I_perp").mean()) if gate_c else 0.0

    return {
        "gate_pass": gate_pass,
        "gate_a": gate_a,
        "gate_b": gate_b,
        "gate_c": gate_c,
        "real_cd": real_cd,
        "null_cd": null_cd,
        "iperp_rate": iperp_rate,
        "n_items": len(tasks),
        "n_runs": len(tidy_df),
        "total_cost_usd": total_cost,
        "run_result": run_result,
        "conditions": conditions,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv=None) -> None:
    """CLI entry point. Exits 0 with "skipped" message when RUNNER_LIVE != 1."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Registered-run driver for When Consensus Lies (Amendment 06)"
    )
    parser.add_argument(
        "--pilot",
        action="store_true",
        help="Run the §11 MVP pilot gate (small balanced batch on copilot_proxy)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report pending/done grid without executing any jobs",
    )
    parser.add_argument(
        "--domains",
        nargs="+",
        default=list(_ALL_DOMAIN_NAMES),
        help=(
            "Domains to load (default: all three). "
            "Choices: code_spec, data_analysis, policy_qa"
        ),
    )
    parser.add_argument(
        "--checkpoint",
        default=None,
        help="Checkpoint JSONL path (default: pilot_gate_checkpoint.jsonl or "
             "registered_run_checkpoint.jsonl depending on mode)",
    )
    parser.add_argument(
        "--rpm",
        type=int,
        default=RPM_DEFAULT,
        help=f"Requests per minute per model (default: {RPM_DEFAULT})",
    )
    parser.add_argument(
        "--budget-usd",
        type=float,
        default=None,
        help="Hard aggregate budget cap in USD",
    )
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=None,
        help="Seeds for the grid (default: [global seed from config])",
    )
    args = parser.parse_args(argv)

    # ── Guard ────────────────────────────────────────────────────────────────
    if not args.dry_run and not _live_ok():
        print(
            "registered_run: skipped (RUNNER_LIVE != 1). "
            "Set RUNNER_LIVE=1 to run live (copilot_proxy, no token required)."
        )
        sys.exit(0)

    from common.config import load_config

    cfg = load_config()

    # ── Pilot mode ───────────────────────────────────────────────────────────
    if args.pilot:
        checkpoint = args.checkpoint or PILOT_CHECKPOINT
        print("=" * 72)
        print("§11 MVP PILOT GATE — copilot_proxy, LIVE")
        print(f"  checkpoint={checkpoint}  cache={CACHE_DIR_PILOT}")
        print(f"  max_items={PILOT_MAX_ITEMS}  budget=${PILOT_BUDGET_USD:.2f}  rpm={args.rpm}")
        print(f"  pilot models: {[m for _, m in PILOT_MODELS]}")
        print(f"  pilot configs: {PILOT_CONFIGS}")
        print("=" * 72)

        all_tasks = load_tasks(args.domains)
        pilot_tasks = select_pilot_tasks(all_tasks, n_pilot=PILOT_MAX_ITEMS)
        print(
            f"\nLoaded {len(all_tasks)} total tasks "
            f"({len(args.domains)} domain(s)); "
            f"selected {len(pilot_tasks)} for pilot."
        )
        h1_count = sum(1 for t in pilot_tasks if t.regime == "H1_external")
        h2_count = sum(1 for t in pilot_tasks if t.regime == "H2_derivable")
        print(f"  H1_external={h1_count}  H2_derivable={h2_count}")
        ks = sorted({t.ambiguity_level for t in pilot_tasks})
        print(f"  k values in pilot: {ks}")

        budget = args.budget_usd if args.budget_usd is not None else PILOT_BUDGET_USD
        report = run_pilot_gate(
            cfg,
            pilot_tasks,
            checkpoint_path=checkpoint,
            budget_usd=budget,
            rpm=args.rpm,
        )

        print("\n" + "=" * 72)
        print("§11 GATE RESULTS:")
        print(f"  (a) cd_primary > 0 on H1_external:  {'PASS' if report['gate_a'] else 'FAIL'}")
        print(f"      real_cd = {report['real_cd']:.4f}")
        print(f"  (b) shuffle null < real CD:          {'PASS' if report['gate_b'] else 'FAIL'}")
        print(f"      null_cd = {report['null_cd']:.4f}  real_cd = {report['real_cd']:.4f}")
        print(f"  (c) pipeline integration:            {'PASS' if report['gate_c'] else 'FAIL'}")
        print(f"      n_runs = {report['n_runs']}")
        print()
        print(f"  I_perp rate (all runs): {report['iperp_rate']:.3f}")
        print()
        if report["conditions"]:
            print("  Per-condition I_perp rates:")
            for cond in report["conditions"]:
                print(
                    f"    regime={cond['regime']}  method={cond['method']}  "
                    f"n={cond['n_runs']}  iperp={cond['iperp_rate']:.3f}"
                )
        print()
        verdict = "PASS" if report["gate_pass"] else "FAIL"
        print(f"  TOTAL COST: ${report['total_cost_usd']:.6f} USD")
        print(f"\n  GATE VERDICT: {verdict}")
        print("=" * 72)

        if not report["gate_pass"]:
            sys.exit(1)
        return

    # ── Full registered run ──────────────────────────────────────────────────
    checkpoint = args.checkpoint or FULL_CHECKPOINT
    seeds = args.seeds
    if seeds is None:
        seeds = [cfg.get("seeds", {}).get("global", 20260713)]

    print("=" * 72)
    print("REGISTERED RUN — copilot_proxy, Amendment 06 frontier roster")
    print(f"  checkpoint={checkpoint}  cache={CACHE_DIR_FULL}")
    print(f"  domains={args.domains}  rpm={args.rpm}  seeds={seeds}")
    print(f"  models={[m for _, m in FRONTIER_SINGLE_MODELS]}")
    print("=" * 72)

    all_tasks = load_tasks(args.domains)
    print(f"\nLoaded {len(all_tasks)} task(s) from domain(s): {args.domains}")

    budget = args.budget_usd
    runner, client = build_runner(
        cfg,
        all_tasks,
        checkpoint_path=checkpoint,
        models=FRONTIER_SINGLE_MODELS,
        configs=REGISTERED_CONFIGS,
        seeds=seeds,
        budget_usd=budget,
        rpm=args.rpm,
        offline=False,
        cache_dir=CACHE_DIR_FULL,
    )

    result = runner.run(dry_run=args.dry_run)
    print(f"\n[REGISTERED RUN] Result: {result}")

    if not args.dry_run:
        total_cost = getattr(client, "_total_cost_usd", 0.0)
        print(f"[REGISTERED RUN] Total cost: ${total_cost:.6f} USD")


if __name__ == "__main__":
    main()
