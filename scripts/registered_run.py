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

# Pilot runs single + SC(k=5) across ALL four model classes (homogeneous,
# heterogeneous, reasoning, weak) so the gate validates cross-family execution
# and model_class disambiguation (MAJOR 4 fix).
PILOT_MODELS: List[Tuple[str, str]] = FRONTIER_SINGLE_MODELS  # all 7 frontier models
PILOT_CONFIGS = ["single", "sc", "heterogeneous-MAD"]  # single + SC + pool config
PILOT_MAX_ITEMS = 10     # hard item cap — never full-scale from --pilot
PILOT_BUDGET_USD = 1.00  # defensive cap (copilot_proxy is free)

# BLOCKER C fix: per-config kwargs forwarded to run_task.
# homogeneous-MAD: §10 requires N≥5; run_task default is 3 (too low).
# sc: k=5 (matches §10 registered default; explicit to avoid ambiguity).
# heterogeneous-MAD: n_agents=4 (default); explicit for auditability.
REGISTERED_CONFIG_KWARGS: Dict[str, Dict[str, Any]] = {
    "sc":               {"k": 5},
    "homogeneous-MAD":  {"n_agents": 5},
    "heterogeneous-MAD": {"n_agents": 4},
}
# Pilot uses the same per-config params (pilot is a representative subset).
PILOT_CONFIG_KWARGS: Dict[str, Dict[str, Any]] = REGISTERED_CONFIG_KWARGS

# BLOCKER A (defense-in-depth): generate replicate seeds with a stride ≥ max
# ensemble size (k=5 for SC, n_agents=5 for MAD) so per-agent seed ranges
# [base..base+k-1] NEVER OVERLAP across replicates.  With stride 1000 a full
# k=5 range occupies seeds [base..base+4] leaving [base+5..base+999] unused
# before the next replicate — 200× safety margin.
# The identity fix (run_identity now includes replicate_seed) is the primary
# defense; this stride is defense-in-depth hygiene.
_SEED_STRIDE = 1000

# Gate C cardinality: minimum expected AgentRuns per completed job.
# A job_done marker with fewer run records indicates a partial/stale checkpoint.
_GATE_C_MIN_AGENTS: Dict[str, int] = {
    "single": 1,
    "sc": 5,             # k=5 (REGISTERED_CONFIG_KWARGS)
    "homogeneous-MAD": 5,   # n_agents=5 (REGISTERED_CONFIG_KWARGS / §10)
    "heterogeneous-MAD": 4,  # n_agents=4 (default)
    "verifier": 1,
    "interpretation-diverse": 1,  # varies by task; check ≥1 as minimum
}

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

    MAJOR F fix: the batch MUST include ≥2 H1_external items that share a k≥1
    value so gate B can evaluate the shuffle null on underspecified items (§11
    requires the gate on k≥1 items; a condition with only 1 item is INCONCLUSIVE
    per MIN_ITEMS_FOR_NULL).  When the input H1_external pool has such a group,
    we prioritise picking ≥2 items from it before filling the rest with balanced k.

    When one regime is sparse (fewer than half), the other regime backfills to
    maximise the batch size up to n_pilot.

    Args:
        all_tasks: Full task list from one or more domains.
        n_pilot: Max total tasks (hard cap; default PILOT_MAX_ITEMS).

    Returns:
        List of at most n_pilot tasks, balanced across regimes and k values,
        with ≥2 H1_external items at the same k≥1 (when the pool permits).
    """
    h1 = [t for t in all_tasks if t.regime == "H1_external"]
    h2 = [t for t in all_tasks if t.regime == "H2_derivable"]

    half = min(n_pilot // 2, len(h1))

    # MAJOR F fix: guarantee ≥2 H1 items sharing a k≥1 value so gate B has
    # at least one evaluable underspecified condition.
    selected_h1 = _select_h1_with_k1_guarantee(h1, half)

    rest = min(n_pilot - len(selected_h1), len(h2))
    selected_h2 = _select_h2_with_k1_guarantee(h2, rest)

    # Backfill from H1 if H2 is sparse.
    shortage = n_pilot - len(selected_h1) - len(selected_h2)
    if shortage > 0:
        already_ids = {t.id for t in selected_h1}
        remaining = [t for t in h1 if t.id not in already_ids]
        extra = min(shortage, len(remaining))
        if extra > 0:
            selected_h1 = selected_h1 + _select_balanced_k(remaining, extra)

    return selected_h1 + selected_h2


def _select_h1_with_k1_guarantee(tasks: List[Any], n: int) -> List[Any]:
    """Select up to n H1_external tasks, prioritising ≥2 items at some k≥1.

    If the pool has a k≥1 group with ≥2 items, seeds the selection with 2 items
    from that group (picking the group with the most items), then fills the rest
    with balanced-k selection over the remainder.  Falls back to plain balanced-k
    if no k≥1 group has ≥2 items or n < 2.
    """
    if len(tasks) <= n:
        return list(tasks)
    if n < 2:
        return _select_balanced_k(tasks, n)

    # Find k≥1 groups with ≥2 items.
    by_k: Dict[int, List[Any]] = {}
    for t in tasks:
        k = t.ambiguity_level
        by_k.setdefault(k, []).append(t)
    k1_groups = [(k, ts) for k, ts in by_k.items() if k >= 1 and len(ts) >= 2]

    if k1_groups:
        # Pick the k≥1 group with the most items (maximises future coverage).
        best_k, best_ts = max(k1_groups, key=lambda x: len(x[1]))
        guaranteed = best_ts[:2]
        already_ids = {t.id for t in guaranteed}
        remaining = [t for t in tasks if t.id not in already_ids]
        fill = _select_balanced_k(remaining, n - 2)
        return guaranteed + fill
    else:
        return _select_balanced_k(tasks, n)


def _select_h2_with_k1_guarantee(tasks: List[Any], n: int) -> List[Any]:
    """Select up to n H2_derivable tasks, prioritising ≥2 items at some k≥1.

    Same guarantee logic as :func:`_select_h1_with_k1_guarantee` so gate B
    can also evaluate H2_derivable underspecified conditions.
    """
    return _select_h1_with_k1_guarantee(tasks, n)  # same algorithm


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
    config_kwargs: Optional[Dict[str, Dict[str, Any]]] = None,
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
        config_kwargs=config_kwargs,
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
    dry_run: bool = False,
    cache_dir: str = CACHE_DIR_PILOT,
    n_pilot: int = PILOT_MAX_ITEMS,
    seed: int = 20260713,
    _runner_override=None,     # injection point for tests
) -> Dict[str, Any]:
    """Execute the §11 MVP pilot gate and return a structured report.

    Gate conditions (pre-registered §11):
      (a) cd_primary > 0 on at least one H1_external item (real convergent
          delusion observed above zero).
      (b) R1 shuffle null (BLOCKER 2 fix): population-level cross-item shuffle
          using ``analysis.nulls.cd_primary_shuffle_null`` (same primary metric
          as gate a).  Computed PER CONDITION (method × model_class × ambiguity_k).
          Conditions with fewer than MIN_ITEMS_FOR_NULL cells are INCONCLUSIVE and
          cannot contribute a PASS.  Gate b = at least one condition has
          real_cd > 0 AND null_cd ≤ NULL_CD_TOLERANCE.
      (c) Pipeline integration (MAJOR 5 fix): (i) run completed with no failures,
          (ii) tidy table is non-empty, (iii) golden cd_primary metric assertion
          passes (known input → expected output verified inline).

    BLOCKER 3 fix:
      ``dry_run=True`` threads through to ``runner.run(dry_run=True)`` so
      ``--pilot --dry-run`` from the CLI makes zero network calls even when
      RUNNER_LIVE is unset.  The gate will report FAIL (gate_c requires a
      completed run) but will never open a network connection.

    Args:
        cfg: Loaded config dict.
        tasks: Pre-selected pilot task list (≤ PILOT_MAX_ITEMS items).
        checkpoint_path: Path for the pilot checkpoint JSONL.
        budget_usd: Hard budget cap (defensive; copilot_proxy is free).
        rpm: Requests per minute.
        offline: If True, use offline mock client (unit tests only).
        dry_run: If True, run in dry-run mode (no network calls); gate will FAIL.
        cache_dir: LLM disk cache directory.
        n_pilot: Max items (sanity check; tasks should already be capped).
        seed: Global RNG seed.
        _runner_override: Optional (runner, client) tuple for test injection.

    Returns:
        dict with keys:
          gate_pass, gate_a, gate_b, gate_c — overall + per-gate booleans
          real_cd, null_cd — mean primary CD and mean null CD across conditions
          null_metric       — always "cd_primary" (for audit verification)
          iperp_rate        — fraction of all runs labeled I_perp
          n_items, n_runs, total_cost_usd
          run_result        — raw runner result dict
          conditions        — per-(regime, method) I_perp diagnostic list
          gate_b_details    — per-condition gate_b result list (for audit)
    """
    from analysis.cd import cd_primary as _cd_primary_fn
    from analysis.contrasts import COLS, compute_cell_cd
    from analysis.io import FRONTIER_MODEL_CLASS_MAP, load_runs_tidy
    from analysis.nulls import NULL_CD_TOLERANCE, MIN_ITEMS_FOR_NULL, cd_primary_shuffle_null

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
            offline=(offline or dry_run),  # dry-run also uses no network
            cache_dir=cache_dir,
            config_kwargs=PILOT_CONFIG_KWARGS,  # BLOCKER C: sc k=5, homogeneous-MAD n_agents=5
        )

    # Execute the run (or dry-run report).
    # BLOCKER 3: thread dry_run through so --pilot --dry-run makes no network calls.
    run_result = runner.run(dry_run=dry_run)
    total_cost = getattr(client, "_total_cost_usd", 0.0)

    # Build tidy table via D3 adapter (reads checkpoint written by the run above).
    tidy_df = load_runs_tidy(checkpoint_path, tasks,
                             model_class_map=FRONTIER_MODEL_CLASS_MAP)

    # ── Gate (c): pipeline integration (MAJOR 5 fix + MAJOR E cardinality) ───
    # (i) Run completed successfully (no failures, not a dry-run report).
    run_status = run_result.get("status")
    gate_c_status = (
        run_status in ("done", "resumable")
        and run_result.get("failed", 0) == 0
        and not dry_run  # dry-run never produces completed runs
    )
    # (ii) Non-empty tidy table.
    gate_c_nonempty = len(tidy_df) > 0
    # (iii) Golden metric assertion: verify cd_primary math is correct on known input.
    # Auditor-visible golden case: [I1,I1,I1,I1,I0] with target I0 → 4 enumerated
    # wrong (I1 ×4), 5 total → cd_primary = 4/5 = 0.8.
    _golden_labels = ["I1", "I1", "I1", "I1", "I0"]
    _golden_target = "I0"
    _golden_expected = 0.8
    gate_c_golden = abs(_cd_primary_fn(_golden_labels, _golden_target) - _golden_expected) < 1e-9
    # (iv) MAJOR E — cardinality: each completed SC job must have ≥ k=5 run records;
    # each single job ≥ 1.  A stale checkpoint with only 1 surviving run record
    # for an SC job has len(group) < 5 → gate_c_cardinality = False.
    gate_c_cardinality = True
    if gate_c_status and gate_c_nonempty:
        item_col_v = COLS["item"]
        method_col_v = COLS["method"]
        seed_col_v = COLS["seed"]
        for (_, meth, _), grp in tidy_df.groupby(
            [item_col_v, method_col_v, seed_col_v], dropna=False
        ):
            min_expected = _GATE_C_MIN_AGENTS.get(meth, 1)
            if len(grp) < min_expected:
                gate_c_cardinality = False
                break
    gate_c = gate_c_status and gate_c_nonempty and gate_c_golden and gate_c_cardinality

    # ── Per-condition I_perp rates (diagnostic) ───────────────────────────────
    regime_col = COLS["regime"]
    label_col = COLS["label"]
    method_col = COLS["method"]
    model_class_col = COLS["model_class"]
    ambiguity_col = COLS["ambiguity_k"]
    item_col = COLS["item"]
    target_col = COLS["target"]
    seed_col = COLS["seed"]

    conditions: List[Dict] = []
    if gate_c_nonempty:
        for (regime, method), grp in tidy_df.groupby([regime_col, method_col], dropna=False):
            lbs = list(grp[label_col])
            n = len(lbs)
            n_perp = sum(1 for lb in lbs if lb == "I_perp")
            conditions.append({
                "regime": regime,
                "method": method,
                "n_runs": n,
                "iperp_rate": n_perp / n if n else 0.0,
            })

    # ── Gate (a): cd_primary > 0 on H1_external cells ─────────────────────────
    real_cd = 0.0
    h1_df = tidy_df[tidy_df[regime_col] == "H1_external"] if gate_c_nonempty else tidy_df.iloc[0:0]
    h1_cells: Any = None
    if len(h1_df) > 0:
        h1_cells = compute_cell_cd(h1_df)
        if len(h1_cells) > 0:
            real_cd = float(h1_cells["cd_primary"].mean())
    gate_a = real_cd > 0.0

    # ── Gate (b): per-condition cd_primary shuffle null ≈ 0 (BLOCKER 2 fix) ───
    # Uses cd_primary_shuffle_null (NOT the frozen label_shuffle_null which calls
    # false_consensus_rate) so real and null metrics are consistent.
    gate_b = False
    null_cd = 0.0
    null_cd_vals: List[float] = []
    gate_b_details: List[Dict] = []

    if h1_cells is not None and len(h1_cells) > 0:
        for (method, mc, ambi_k), cond_cells in h1_cells.groupby(
            [method_col, model_class_col, ambiguity_col], dropna=False
        ):
            n_cells = len(cond_cells)
            cond_real_cd = float(cond_cells["cd_primary"].mean())

            # BLOCKER D fix: require ≥ MIN_ITEMS_FOR_NULL DISTINCT ITEMS (tasks),
            # not just ≥ MIN_ITEMS_FOR_NULL cells.  Two replicate seeds from ONE
            # item produce n_cells=2 but only 1 distinct item — the cross-item
            # shuffle degenerates to a within-item permutation (no-op).  Only a
            # genuine cross-item shuffle (≥2 distinct tasks) is meaningful.
            n_distinct_items = cond_cells[item_col].nunique()
            if n_distinct_items < MIN_ITEMS_FOR_NULL:
                gate_b_details.append({
                    "method": method, "model_class": mc, "ambiguity_k": ambi_k,
                    "n_cells": n_cells,
                    "n_distinct_items": n_distinct_items,
                    "status": "inconclusive",
                    "real_cd": cond_real_cd, "null_cd": None,
                })
                continue

            # Reconstruct per-cell label lists for this condition.
            cond_mask = (
                (h1_df[method_col] == method)
                & (h1_df[model_class_col] == mc)
                & (h1_df[ambiguity_col] == ambi_k)
            )
            cond_df = h1_df[cond_mask]
            target = str(cond_df[target_col].mode().iloc[0])

            cells_labels = [
                list(grp[label_col])
                for _, grp in cond_df.groupby([item_col, seed_col], dropna=False)
            ]

            # cd_primary-consistent null (NOT false_consensus_rate).
            cond_null_cd = cd_primary_shuffle_null(
                cells_labels, target=target, n_perm=200, seed=42
            )
            null_cd_vals.append(cond_null_cd)

            cond_pass = cond_real_cd > 0.0 and cond_null_cd <= NULL_CD_TOLERANCE
            if cond_pass:
                gate_b = True

            gate_b_details.append({
                "method": method, "model_class": mc, "ambiguity_k": ambi_k,
                "n_cells": n_cells,
                "n_distinct_items": n_distinct_items,
                "status": "pass" if cond_pass else "fail",
                "real_cd": cond_real_cd,
                "null_cd": cond_null_cd,
            })

    null_cd = sum(null_cd_vals) / len(null_cd_vals) if null_cd_vals else 0.0

    gate_pass = gate_a and gate_b and gate_c
    iperp_rate = float((tidy_df[label_col] == "I_perp").mean()) if gate_c_nonempty else 0.0

    return {
        "gate_pass": gate_pass,
        "gate_a": gate_a,
        "gate_b": gate_b,
        "gate_c": gate_c,
        "real_cd": real_cd,
        "null_cd": null_cd,
        "null_metric": "cd_primary",   # audit: confirms metric used for null
        "iperp_rate": iperp_rate,
        "n_items": len(tasks),
        "n_runs": len(tidy_df),
        "total_cost_usd": total_cost,
        "run_result": run_result,
        "conditions": conditions,
        "gate_b_details": gate_b_details,  # per-condition gate_b audit trail
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
        # BLOCKER 3: thread dry_run through so --pilot --dry-run makes zero
        # network calls even when RUNNER_LIVE is unset.
        report = run_pilot_gate(
            cfg,
            pilot_tasks,
            checkpoint_path=checkpoint,
            budget_usd=budget,
            rpm=args.rpm,
            dry_run=args.dry_run,
        )

        print("\n" + "=" * 72)
        print("§11 GATE RESULTS:")
        print(f"  (a) cd_primary > 0 on H1_external:  {'PASS' if report['gate_a'] else 'FAIL'}")
        print(f"      real_cd = {report['real_cd']:.4f}")
        print(f"  (b) cd_primary shuffle null ≤ tol:  {'PASS' if report['gate_b'] else 'FAIL'}")
        print(f"      null_cd = {report['null_cd']:.4f}  null_metric = {report['null_metric']}")
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
        if report.get("gate_b_details"):
            print("\n  Per-condition gate_b (cd_primary shuffle null):")
            for det in report["gate_b_details"]:
                null_str = f"{det['null_cd']:.4f}" if det["null_cd"] is not None else "n/a"
                print(
                    f"    {det['method']}|{det['model_class']}|k={det['ambiguity_k']}  "
                    f"n_cells={det['n_cells']}  status={det['status']}  "
                    f"real_cd={det['real_cd']:.4f}  null_cd={null_str}"
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
        # §10 requires ≥3 distinct seeds per (item × config) for the full run.
        # BLOCKER A (defense-in-depth): space seeds by _SEED_STRIDE (1000) so
        # per-agent seed ranges [base..base+k-1] NEVER OVERLAP across replicates
        # (k=5 for SC/MAD, so stride 1000 gives 200× safety margin).
        # The identity fix (run_identity includes replicate_seed) is the primary
        # defense; the stride is hygiene for correctness at the runner level too.
        global_seed = cfg.get("seeds", {}).get("global", 20260713)
        seeds = [global_seed, global_seed + _SEED_STRIDE, global_seed + 2 * _SEED_STRIDE]
    # Enforce ≥3 seeds for full-scale execution (MAJOR 6 fix — §10 requirement).
    if len(set(seeds)) < 3:
        print(
            f"ERROR: §10 (pre-registered) requires ≥3 distinct seeds per "
            f"(item × config) for the full registered run. Got {len(seeds)} "
            f"seed(s): {seeds}. Pass --seeds with ≥3 distinct values.",
            file=sys.stderr,
        )
        sys.exit(1)

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
        config_kwargs=REGISTERED_CONFIG_KWARGS,  # BLOCKER C: homogeneous-MAD n_agents=5, sc k=5
    )

    result = runner.run(dry_run=args.dry_run)
    print(f"\n[REGISTERED RUN] Result: {result}")

    if not args.dry_run:
        total_cost = getattr(client, "_total_cost_usd", 0.0)
        print(f"[REGISTERED RUN] Total cost: ${total_cost:.6f} USD")


if __name__ == "__main__":
    main()
