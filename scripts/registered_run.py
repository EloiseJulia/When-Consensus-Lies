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
import random
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

# R1b margin (Amendment 07): observed CD must exceed the uniform-interpretation
# null by this many percentage points to trigger R1b PASS.
# Rationale: 15 pp sits well below the typical signal (CD_real ≈ 0.6–1.0,
# CD_unif ≈ 0.35–0.50 for 2–4 interpretations → margin ≈ 0.1–0.65) while
# being large enough to absorb Monte Carlo noise (SD of CD_unif estimate at
# n_perm=200 is ≈ 0.016 for 5 agents × 2 interps).  Pre-registered in
# Amendment 07 (2026-07-17).
R1B_MARGIN: float = 0.15


# ── Domain loading (D2) ──────────────────────────────────────────────────────

_ALL_DOMAIN_NAMES = ("code_spec", "data_analysis", "policy_qa")

_DOMAIN_LOADERS = {
    "code_spec":      lambda: __import__("bench.code_spec",    fromlist=["generate_tasks"]).generate_tasks(),
    "data_analysis":  lambda: __import__("bench.data_analysis", fromlist=["generate_tasks"]).generate_tasks(),
    "policy_qa":      lambda: __import__("bench.policy_qa",    fromlist=["generate_tasks"]).generate_tasks(),
    # Amendment 10 (R2 cross-family construction): Anthropic claude-opus-4.8-
    # constructed H1_external subset. ADDITIVE — intentionally NOT in
    # _ALL_DOMAIN_NAMES so it never enters the default confirmatory grid; it is
    # run explicitly via `--domains r2_xf` as a separate R2 partition.
    "r2_xf":          lambda: __import__("bench.r2_xf",        fromlist=["generate_tasks"]).generate_tasks(),
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


# ── Bootstrap CI helpers (Amendment 07 — item-level bootstrap for R1a/R1b) ──

def _bootstrap_ci(
    samples: List[float],
    n_boot: int = 2000,
    seed: int = 42,
) -> Tuple[float, float]:
    """Bootstrap 95% CI for mean(samples), resampling with replacement.

    Returns (lower_2.5pct, upper_97.5pct). Returns (-inf, +inf) for empty input.
    Uses random.Random for determinism.
    """
    if not samples:
        return (float("-inf"), float("inf"))
    rng = random.Random(seed)
    n = len(samples)
    boot_means = sorted(
        sum(rng.choices(samples, k=n)) / n for _ in range(n_boot)
    )
    lo_idx = max(0, int(n_boot * 0.025) - 1)
    hi_idx = min(n_boot - 1, int(n_boot * 0.975))
    return boot_means[lo_idx], boot_means[hi_idx]


def _bootstrap_ci_diff(
    group_a: List[float],
    group_b: List[float],
    n_boot: int = 2000,
    seed: int = 42,
) -> Tuple[float, float]:
    """Bootstrap 95% CI for mean(A) − mean(B), resampling A and B independently.

    Returns (lower_2.5pct, upper_97.5pct). Returns (-inf, +inf) if either group empty.
    """
    if not group_a or not group_b:
        return (float("-inf"), float("inf"))
    rng = random.Random(seed)
    n_a, n_b = len(group_a), len(group_b)
    diffs = sorted(
        sum(rng.choices(group_a, k=n_a)) / n_a - sum(rng.choices(group_b, k=n_b)) / n_b
        for _ in range(n_boot)
    )
    lo_idx = max(0, int(n_boot * 0.025) - 1)
    hi_idx = min(n_boot - 1, int(n_boot * 0.975))
    return diffs[lo_idx], diffs[hi_idx]


def select_pilot_tasks(
    all_tasks: List[Any],
    n_pilot: int = PILOT_MAX_ITEMS,
) -> List[Any]:
    """Select a balanced pilot batch: ~half H1_external, ~half H2_derivable.

    Both halves are drawn with balanced ambiguity_level (k) values so the gate
    exercises both regime classes and multiple k levels.

    MAJOR F fix: the batch MUST include ≥2 H1_external k=0 CONTROL items (for
    R1a bootstrap CI, Amendment 07) AND ≥2 H1_external k≥1 items (for R1a/R1b
    gates).  Both groups need ≥2 items to compute item-level bootstrap CIs.
    RAISES ValueError if the pool cannot satisfy either guarantee.

    When one regime is sparse (fewer than half), the other regime backfills to
    maximise the batch size up to n_pilot.

    Args:
        all_tasks: Full task list from one or more domains.
        n_pilot: Max total tasks (hard cap; default PILOT_MAX_ITEMS).

    Returns:
        List of at most n_pilot tasks, balanced across regimes and k values,
        with ≥2 H1 k=0 controls AND ≥2 H1 k≥1 items (Amendment 07 bootstrap
        CI requirement).
    """
    h1 = [t for t in all_tasks if t.regime == "H1_external"]
    h2 = [t for t in all_tasks if t.regime == "H2_derivable"]

    half = min(n_pilot // 2, len(h1))

    # Amendment 07: guarantee ≥2 k=0 controls AND ≥2 k≥1 items so R1a bootstrap
    # CI is computable and R1b has enough items.
    selected_h1 = _select_h1_with_k0_and_k1_guarantee(h1, half)

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


def _validate_h1_k1_guarantee(tasks: List[Any]) -> None:
    """Raise ValueError if *tasks* has no k≥1 ambiguity group with ≥2 items.

    §11 requires ≥2 H1_external items sharing a k≥1 condition for gates A and
    B.  This helper is called at the end of every code path inside
    :func:`_select_h1_with_k1_guarantee` so the BLOCKER invariant is enforced
    regardless of which branch was taken (pool selection, n<2 truncation, or
    passthrough when len(tasks) ≤ n).
    """
    by_k: Dict[int, int] = {}
    for t in tasks:
        k = t.ambiguity_level
        if k >= 1:
            by_k[k] = by_k.get(k, 0) + 1
    if not any(c >= 2 for c in by_k.values()):
        raise ValueError(
            "Pilot task list has no k≥1 group with ≥2 H1_external items. "
            "§11 gates A and B require ≥2 H1 items sharing a k≥1 condition so "
            "the shuffle null is not degenerate. Ensure the H1 bench includes "
            "≥2 items at the same k≥1 ambiguity level and pass them to the pilot. "
            f"k≥1 item counts in this batch: {dict(sorted(by_k.items()))}"
        )


def _select_h1_with_k1_guarantee(tasks: List[Any], n: int) -> List[Any]:
    """Select up to n H1_external tasks, guaranteeing ≥2 items at some k≥1.

    If the pool has a k≥1 group with ≥2 items, seeds the selection with 2 items
    from that group (picking the group with the most items), then fills the rest
    with balanced-k selection over the remainder.  RAISES ValueError if no k≥1
    group has ≥2 items — there is no valid fallback for §11 gate A/B.
    """
    if len(tasks) <= n:
        result = list(tasks)
        _validate_h1_k1_guarantee(result)
        return result
    if n < 2:
        raise ValueError(
            f"Cannot select {n} H1 pilot tasks and guarantee ≥2 items at k≥1: "
            "need n ≥ 2 to satisfy §11 gate A/B. "
            "Increase PILOT_MAX_ITEMS or the H1 half-budget."
        )

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
        raise ValueError(
            "Pilot selector: no k≥1 ambiguity group has ≥2 H1_external items. "
            "§11 gates A and B require the pilot gate on real UNDERSPECIFIED items "
            "(k≥1) and the shuffle null requires ≥2 items per condition. "
            f"H1 pool: {len(tasks)} items; k distribution: "
            f"{dict(sorted((k, len(ts)) for k, ts in by_k.items()))}. "
            "Ensure the H1 bench loader returns items with at least one k≥1 "
            "ambiguity level that appears ≥2 times."
        )


def _select_h2_with_k1_guarantee(tasks: List[Any], n: int) -> List[Any]:
    """Select up to n H2_derivable tasks, preferring ≥2 items at some k≥1.

    SOFT guarantee (H2): tries to include ≥2 items at the same k≥1 value for
    H2 gate B coverage, but does NOT raise if the pool lacks such items.  Gate
    A/B are primarily H1_external; H2 coverage is a bonus.  Use
    :func:`_select_h1_with_k1_guarantee` for the hard H1 guarantee.
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
        best_k, best_ts = max(k1_groups, key=lambda x: len(x[1]))
        guaranteed = best_ts[:2]
        already_ids = {t.id for t in guaranteed}
        remaining = [t for t in tasks if t.id not in already_ids]
        fill = _select_balanced_k(remaining, n - 2)
        return guaranteed + fill
    else:
        # H2 soft: no valid k≥1 group — fall back to balanced selection without error.
        return _select_balanced_k(tasks, n)


def _select_h1_with_k0_and_k1_guarantee(tasks: List[Any], n: int) -> List[Any]:
    """Select up to n H1_external tasks guaranteeing ≥2 k=0 AND ≥2 k≥1 items.

    Required for Amendment 07 R1a bootstrap CI: R1a compares k=0 vs k≥1 items;
    both groups need ≥2 items for a computable bootstrap CI.

    Raises ValueError if:
      - pool has < 2 k=0 H1 controls, OR
      - pool has no k≥1 group with ≥2 items, OR
      - n < 4 (can't fit 2+2 minimum)
    """
    k0_pool = [t for t in tasks if t.ambiguity_level == 0]
    if len(k0_pool) < 2:
        by_k_diag: Dict[int, int] = {}
        for t in tasks:
            by_k_diag[t.ambiguity_level] = by_k_diag.get(t.ambiguity_level, 0) + 1
        raise ValueError(
            f"Pilot H1 pool has {len(k0_pool)} k=0 control item(s); "
            "≥2 required for R1a bootstrap CI (Amendment 07). "
            "Ensure the bench includes ≥2 fully-specified (k=0) H1_external "
            "control tasks. "
            f"H1 pool: {len(tasks)} items; "
            f"k distribution: {dict(sorted(by_k_diag.items()))}"
        )

    by_k: Dict[int, List[Any]] = {}
    for t in tasks:
        by_k.setdefault(t.ambiguity_level, []).append(t)
    k1_groups = [(k, ts) for k, ts in by_k.items() if k >= 1 and len(ts) >= 2]

    if not k1_groups:
        raise ValueError(
            "Pilot H1 pool has no k≥1 ambiguity group with ≥2 items. "
            "§11 gates A and B require ≥2 H1 items sharing a k≥1 condition so "
            "the R1a/R1b bootstrap CIs are computable. "
            f"H1 pool: {len(tasks)} items; k distribution: "
            f"{dict(sorted((k, len(ts)) for k, ts in by_k.items()))}."
        )

    if len(tasks) <= n:
        return list(tasks)

    if n < 4:
        raise ValueError(
            f"Cannot guarantee ≥2 k=0 AND ≥2 k≥1 H1 items with n={n} < 4 slots. "
            "Increase PILOT_MAX_ITEMS or the H1 half-budget."
        )

    # Seed with 2 k=0 controls.
    k0_seeded = k0_pool[:2]
    already_ids = {t.id for t in k0_seeded}

    # Seed with 2 k≥1 from the group with most items (maximises k coverage).
    best_k, best_ts = max(k1_groups, key=lambda x: len(x[1]))
    k1_seeded = [t for t in best_ts if t.id not in already_ids][:2]
    already_ids.update(t.id for t in k1_seeded)

    # Fill remaining slots with balanced k.
    remaining = [t for t in tasks if t.id not in already_ids]
    fill = _select_balanced_k(remaining, n - len(k0_seeded) - len(k1_seeded))
    return k0_seeded + k1_seeded + fill


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
    from analysis.nulls import NULL_CD_TOLERANCE, MIN_ITEMS_FOR_NULL, cd_primary_shuffle_null, uniform_interpretation_null
    from harness.nulls import label_shuffle_null as _frozen_label_shuffle_null
    from harness.runner import endpoint_identity as _endpoint_identity, POOL_CONFIGS

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

    # Compute the endpoint namespace for the client used — filter tidy load to
    # that endpoint so records from other provider runs (e.g. github_models from
    # an earlier attempt) are never mixed into the same analysis cells.
    expected_ep = _endpoint_identity(client.provider, client.base_url)

    # Build tidy table via D3 adapter (reads checkpoint written by the run above).
    tidy_df = load_runs_tidy(
        checkpoint_path, tasks,
        model_class_map=FRONTIER_MODEL_CLASS_MAP,
        expected_endpoint=expected_ep,
    )

    # ── Gate (c): pipeline integration (MAJOR 5 fix + MAJOR E/MAJOR cardinality) ──
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
    # (iv) MAJOR/MAJOR E — per-job cardinality: enumerate the runner's expected grid
    # and validate each completed job independently.  The old pooled check (groupby
    # item×method×seed across ALL models) masked missing model jobs — a 7-model SC
    # run satisfied len(grp)≥5 even if one model's job had 0 records.  Now we check
    # EACH (task, config, model_id, seed) job separately: non-pool configs require
    # per-model record counts; pool configs check the total pool agent count.
    gate_c_cardinality = True
    if gate_c_status and gate_c_nonempty:
        item_col_v = COLS["item"]
        method_col_v = COLS["method"]
        seed_col_v = COLS["seed"]
        model_col_v = "model"
        run_is_fully_done = run_result.get("status") == "done"
        for (task_id, cfg_name, model_role, model_id, rep_seed) in runner.enumerate_grid():
            # For resumable runs, only check jobs already marked done.
            if not run_is_fully_done:
                if not runner._store.job_done(task_id, cfg_name, model_role, model_id, rep_seed):
                    continue
            min_expected = _GATE_C_MIN_AGENTS.get(cfg_name, 1)
            if cfg_name in POOL_CONFIGS:
                # Pool job: agents share (task, config, seed) but have distinct
                # model slugs.  Check the TOTAL pool agent count.
                count = int((
                    (tidy_df[item_col_v] == task_id)
                    & (tidy_df[method_col_v] == cfg_name)
                    & (tidy_df[seed_col_v] == rep_seed)
                ).sum())
            else:
                # Single-model job: match per-model so a missing model's job (zero
                # records) is not masked by other models' records in the same cell.
                count = int((
                    (tidy_df[item_col_v] == task_id)
                    & (tidy_df[method_col_v] == cfg_name)
                    & (tidy_df[model_col_v] == model_id)
                    & (tidy_df[seed_col_v] == rep_seed)
                ).sum())
            if count < min_expected:
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

    # ── Gate (a): cd_primary > 0 on H1_external k≥1 (UNDERSPECIFIED) items ──
    # BLOCKER fix: gates A and B MUST be restricted to k≥1 items.  k=0 is the
    # fully-specified CONTROL — its CD should be ≈0 — including it would dilute
    # the "CD>0" signal and confound the null.  k=0 CD is reported as a diagnostic.
    real_cd = 0.0
    h1_df = tidy_df[tidy_df[regime_col] == "H1_external"] if gate_c_nonempty else tidy_df.iloc[0:0]
    h1_k1plus_df = h1_df[h1_df[ambiguity_col] >= 1] if len(h1_df) > 0 else h1_df
    h1_k0_df = h1_df[h1_df[ambiguity_col] == 0] if len(h1_df) > 0 else h1_df
    h1_cells: Any = None
    if len(h1_k1plus_df) > 0:
        h1_cells = compute_cell_cd(h1_k1plus_df)
        if len(h1_cells) > 0:
            real_cd = float(h1_cells["cd_primary"].mean())
    gate_a = real_cd > 0.0

    # k=0 CONTROL diagnostic (CD should be ≈0 for fully-specified items).
    # Also drives R1a gate (Amendment 07): requires CD_k0 ≈ 0 for R1a PASS.
    k0_control_cd = 0.0
    _has_k0 = False
    _k0c = None
    if len(h1_k0_df) > 0:
        _k0c = compute_cell_cd(h1_k0_df)
        if len(_k0c) > 0:
            k0_control_cd = float(_k0c["cd_primary"].mean())
            _has_k0 = True

    # Per-item mean CD for k=0 and k≥1 groups (needed for bootstrap CIs).
    _items_k0_cds: List[float] = (
        _k0c.groupby(item_col)["cd_primary"].mean().tolist()
        if _k0c is not None and len(_k0c) > 0
        else []
    )
    _items_k1_cds: List[float] = (
        h1_cells.groupby(item_col)["cd_primary"].mean().tolist()
        if h1_cells is not None and len(h1_cells) > 0
        else []
    )
    _n_k0_items = len(_items_k0_cds)
    _n_k1_items = len(_items_k1_cds)

    # ── R1a: k=0 control contrast (Amendment 07 — replaces label-shuffle gate) ──
    # PASS: CD_k0 ≤ NULL_CD_TOLERANCE (point) AND bootstrap 95% CI of
    #       (mean CD_k≥1 − mean CD_k0) lower bound > 0 (CI excludes 0, positive).
    # INCONCLUSIVE: < 2 items on either side (CI non-computable).
    # FAIL: CD_k0 > tolerance (point check fails) OR CI lower ≤ 0.
    _has_k1plus = h1_cells is not None and len(h1_cells) > 0
    _r1a_ci_lo = float("-inf")
    _r1a_ci_hi = float("inf")

    if _n_k0_items < 2 or _n_k1_items < 2:
        _r1a_status = "inconclusive"
    elif k0_control_cd > NULL_CD_TOLERANCE:
        # k=0 items already show convergence — the setup is contaminated; FAIL.
        _r1a_status = "fail"
    else:
        # Bootstrap 95% CI of (mean CD_k≥1) − (mean CD_k0), items as units.
        _r1a_ci_lo, _r1a_ci_hi = _bootstrap_ci_diff(
            _items_k1_cds, _items_k0_cds, n_boot=2000, seed=42
        )
        _r1a_status = "pass" if _r1a_ci_lo > 0 else "fail"
    gate_r1a = (_r1a_status == "pass")

    # ── R1b: uniform-interpretation null (Amendment 07) ──────────────────────
    # Per-item: diff_i = obs_cd_i − uniform_cd_i (item-aware null, no marginal bias).
    # PASS: bootstrap 95% CI lower bound of mean(diff_i) > 0.
    # INCONCLUSIVE: < 2 k≥1 items (CI non-computable).
    # R1B_MARGIN = 0.15 is an effect-size DIAGNOSTIC only; the CI drives PASS.
    task_interp_map: Dict[str, List[str]] = {
        t.id: [i.id for i in t.interpretations if i.id != "I_perp"]
        for t in tasks
    }
    uniform_null_cd = 0.0
    _r1b_status = "inconclusive"
    _r1b_ci_lo = float("-inf")
    _r1b_ci_hi = float("inf")
    _items_diffs_r1b: List[float] = []

    if _n_k1_items >= 2:
        _r1b_target = str(h1_k1plus_df[target_col].mode().iloc[0])
        _unif_cds_per_item: List[float] = []

        for _iid in h1_cells[item_col].unique():
            _obs_cd_i = float(
                h1_cells[h1_cells[item_col] == _iid]["cd_primary"].mean()
            )
            _item_df = h1_k1plus_df[h1_k1plus_df[item_col] == _iid]
            _item_cells_labels = [
                list(_grp[label_col])
                for _, _grp in _item_df.groupby(
                    [method_col, model_class_col, seed_col], dropna=False
                )
            ]
            _interp_ids_i = task_interp_map.get(str(_iid), ["I0", "I1"])
            _unif_cd_i = uniform_interpretation_null(
                _item_cells_labels,
                [_interp_ids_i] * len(_item_cells_labels),
                _r1b_target,
                n_perm=200,
                seed=42,
            )
            _unif_cds_per_item.append(_unif_cd_i)
            _items_diffs_r1b.append(_obs_cd_i - _unif_cd_i)

        if _unif_cds_per_item:
            uniform_null_cd = sum(_unif_cds_per_item) / len(_unif_cds_per_item)

        if len(_items_diffs_r1b) >= 2:
            _r1b_ci_lo, _r1b_ci_hi = _bootstrap_ci(
                _items_diffs_r1b, n_boot=2000, seed=42
            )
            _r1b_status = "pass" if _r1b_ci_lo > 0 else "fail"
        else:
            _r1b_status = "inconclusive"
    gate_r1b = (_r1b_status == "pass")

    # ── gate_b = R1a AND R1b (Amendment 07 — replaces label-shuffle gate) ────
    gate_b = gate_r1a and gate_r1b

    # ── gate_b_details: R1a + R1b per-gate audit trail ────────────────────────
    gate_b_details: List[Dict] = [
        {
            "gate": "r1a",
            "status": _r1a_status,
            "k0_cd": k0_control_cd,
            "k1plus_cd": real_cd,
            "n_items_k0": _n_k0_items,
            "n_items_k1plus": _n_k1_items,
            "ci_lo": _r1a_ci_lo,
            "ci_hi": _r1a_ci_hi,
            "tol": NULL_CD_TOLERANCE,
            "note": "bootstrap 95% CI of (CD_k≥1 − CD_k0) lower bound > 0; CD_k0 ≤ tol (point check)",
        },
        {
            "gate": "r1b",
            "status": _r1b_status,
            "real_cd": real_cd,
            "uniform_cd": uniform_null_cd,
            "n_items_k1plus": _n_k1_items,
            "ci_lo": _r1b_ci_lo,
            "ci_hi": _r1b_ci_hi,
            "margin_required": R1B_MARGIN,
            "note": "bootstrap 95% CI of mean(obs_cd − uniform_cd) lower bound > 0; margin is effect-size diagnostic",
        },
    ]

    # ── Shuffle null: DIAGNOSTIC ONLY (Amendment 07 — demoted from gate) ─────
    # cd_primary_shuffle_null is still computed per-condition for reporting but
    # NO LONGER drives PASS/FAIL.  null_cd ≈ real_cd is the EXPECTED signature
    # of a shared-prior phenomenon (marginal bias toward the same wrong default),
    # not a "thesis not supported" verdict — Amendment 07 §1.
    # MAJOR 2 (Amdt 07 §2 R1-diag): ALSO compute the FROZEN label_shuffle_null
    # (false_consensus_rate based) per condition — reported separately as the
    # "frozen R1 diagnostic".  Neither drives PASS/FAIL.
    null_cd = 0.0
    null_cd_vals: List[float] = []
    null_cd_frozen_vals: List[float] = []
    shuffle_null_details: List[Dict] = []

    if h1_cells is not None and len(h1_cells) > 0:
        for (method, mc, ambi_k), cond_cells in h1_cells.groupby(
            [method_col, model_class_col, ambiguity_col], dropna=False
        ):
            n_cells = len(cond_cells)
            cond_real_cd = float(cond_cells["cd_primary"].mean())

            # BLOCKER D fix: require ≥ MIN_ITEMS_FOR_NULL DISTINCT ITEMS (tasks).
            n_distinct_items = cond_cells[item_col].nunique()
            if n_distinct_items < MIN_ITEMS_FOR_NULL:
                shuffle_null_details.append({
                    "method": method, "model_class": mc, "ambiguity_k": ambi_k,
                    "n_cells": n_cells,
                    "n_distinct_items": n_distinct_items,
                    "real_cd": cond_real_cd,
                    "null_cd_cd_primary": None,
                    "null_cd_frozen_fcr": None,
                    "null_cd": None,  # backward compat
                    "note": "shared-prior diagnostic (null≈real EXPECTED — Amdt 07): inconclusive",
                })
                continue

            # Reconstruct per-cell label lists for this condition.
            # BLOCKER fix: slice from h1_k1plus_df (k≥1 only), not h1_df.
            cond_mask = (
                (h1_k1plus_df[method_col] == method)
                & (h1_k1plus_df[model_class_col] == mc)
                & (h1_k1plus_df[ambiguity_col] == ambi_k)
            )
            cond_df = h1_k1plus_df[cond_mask]
            target = str(cond_df[target_col].mode().iloc[0])

            cells_labels = [
                list(grp[label_col])
                for _, grp in cond_df.groupby([item_col, seed_col], dropna=False)
            ]

            # cd_primary-consistent null (NOT false_consensus_rate).
            # DIAGNOSTIC ONLY — Amdt 07: null≈real is EXPECTED for shared-prior.
            cond_null_cd = cd_primary_shuffle_null(
                cells_labels, target=target, n_perm=200, seed=42
            )
            null_cd_vals.append(cond_null_cd)

            # FROZEN label_shuffle_null (false_consensus_rate based — Amdt 07 §2).
            # Computed and reported separately; does NOT drive PASS/FAIL.
            cond_frozen_null_cd = _frozen_label_shuffle_null(
                cells_labels, target=target, n_perm=200, seed=42
            )
            null_cd_frozen_vals.append(cond_frozen_null_cd)

            shuffle_null_details.append({
                "method": method, "model_class": mc, "ambiguity_k": ambi_k,
                "n_cells": n_cells,
                "n_distinct_items": n_distinct_items,
                "real_cd": cond_real_cd,
                "null_cd_cd_primary": cond_null_cd,
                "null_cd_frozen_fcr": cond_frozen_null_cd,
                "null_cd": cond_null_cd,  # backward compat alias for null_cd_cd_primary
                "note": "shared-prior diagnostic (null≈real EXPECTED — Amdt 07)",
            })

    null_cd = sum(null_cd_vals) / len(null_cd_vals) if null_cd_vals else 0.0
    null_cd_frozen = (
        sum(null_cd_frozen_vals) / len(null_cd_frozen_vals)
        if null_cd_frozen_vals else 0.0
    )

    gate_pass = gate_a and gate_b and gate_c
    iperp_rate = float((tidy_df[label_col] == "I_perp").mean()) if gate_c_nonempty else 0.0

    return {
        "gate_pass": gate_pass,
        "gate_a": gate_a,
        "gate_b": gate_b,
        "gate_r1a": gate_r1a,
        "gate_r1b": gate_r1b,
        "gate_c": gate_c,
        "real_cd": real_cd,
        "k0_control_cd": k0_control_cd,   # diagnostic: CD of k=0 controls (should ≈0)
        "null_cd": null_cd,                # cd_primary shuffle null (DIAGNOSTIC — Amdt 07)
        "null_cd_frozen": null_cd_frozen,  # FROZEN label_shuffle_null (false_consensus_rate) — Amdt 07 §2
        "null_metric": "cd_primary",       # audit: confirms metric used for null
        "uniform_null_cd": uniform_null_cd, # R1b: uniform interpretation null
        "iperp_rate": iperp_rate,
        "n_items": len(tasks),
        "n_runs": len(tidy_df),
        "total_cost_usd": total_cost,
        "run_result": run_result,
        "conditions": conditions,
        "gate_b_details": gate_b_details,        # R1a + R1b audit trail (Amdt 07)
        "shuffle_null_details": shuffle_null_details,  # per-condition shuffle diagnostic
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
        print("§11 GATE RESULTS (Amendment 07 — R1a+R1b replace label-shuffle gate):")
        print(f"  (a) cd_primary > 0 on H1_external k≥1:  {'PASS' if report['gate_a'] else 'FAIL'}")
        print(f"      real_cd = {report['real_cd']:.4f}")
        # ── R1a/R1b gate details ─────────────────────────────────────────────
        _r1a_det = next((d for d in report["gate_b_details"] if d.get("gate") == "r1a"), {})
        _r1b_det = next((d for d in report["gate_b_details"] if d.get("gate") == "r1b"), {})
        print(f"  (b) R1 robustness gates (Amendment 07):")
        print(f"      R1a k=0-control contrast:         {_r1a_det.get('status', 'n/a').upper()}")
        print(
            f"          CD_k0={report['k0_control_cd']:.4f}  "
            f"CD_k≥1={report['real_cd']:.4f}  "
            f"tol={_r1a_det.get('tol', 0.10)}  "
            f"n_k0={_r1a_det.get('n_items_k0', 'n/a')}  "
            f"n_k1plus={_r1a_det.get('n_items_k1plus', 'n/a')}"
        )
        _r1a_ci_lo = _r1a_det.get('ci_lo', float('-inf'))
        _r1a_ci_hi = _r1a_det.get('ci_hi', float('inf'))
        print(
            f"          bootstrap 95% CI (CD_k≥1−CD_k0): "
            f"[{_r1a_ci_lo:.4f}, {_r1a_ci_hi:.4f}]"
        )
        print(f"      R1b uniform-interpretation null:  {_r1b_det.get('status', 'n/a').upper()}")
        _r1b_ci_lo = _r1b_det.get('ci_lo', float('-inf'))
        _r1b_ci_hi = _r1b_det.get('ci_hi', float('inf'))
        print(
            f"          real_cd={report['real_cd']:.4f}  "
            f"uniform_cd={report['uniform_null_cd']:.4f}  "
            f"margin_diag={_r1b_det.get('margin_required', R1B_MARGIN):.2f}  "
            f"n_k1plus={_r1b_det.get('n_items_k1plus', 'n/a')}"
        )
        print(
            f"          bootstrap 95% CI (obs−uniform): "
            f"[{_r1b_ci_lo:.4f}, {_r1b_ci_hi:.4f}]"
        )
        print(f"      gate_b (R1a AND R1b):              {'PASS' if report['gate_b'] else 'FAIL'}")
        print(f"  [DIAG — Amdt 07] label-shuffle nulls (null≈real EXPECTED for shared-prior):")
        print(
            f"      cd_primary shuffle:  null_cd={report['null_cd']:.4f}  "
            f"null_metric={report['null_metric']}  (shared-prior diagnostic — not a gate)"
        )
        print(
            f"      frozen fcr shuffle:  null_cd_frozen={report['null_cd_frozen']:.4f}  "
            f"[frozen R1 label-shuffle (false_consensus_rate) — shared-prior diagnostic, Amdt 07]"
        )
        print(f"  (c) pipeline integration:             {'PASS' if report['gate_c'] else 'FAIL'}")
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
        if report.get("shuffle_null_details"):
            print("\n  [DIAGNOSTIC] Per-condition label-shuffle nulls (Amdt 07 — shared-prior):")
            for det in report["shuffle_null_details"]:
                cdp_str = f"{det['null_cd_cd_primary']:.4f}" if det.get("null_cd_cd_primary") is not None else "n/a"
                fcr_str = f"{det['null_cd_frozen_fcr']:.4f}" if det.get("null_cd_frozen_fcr") is not None else "n/a"
                print(
                    f"    {det['method']}|{det['model_class']}|k={det['ambiguity_k']}  "
                    f"n_cells={det['n_cells']}  "
                    f"real_cd={det['real_cd']:.4f}  "
                    f"null_cd(cd_primary)={cdp_str}  "
                    f"null_cd(frozen_fcr)={fcr_str}  "
                    f"[shared-prior diagnostic — not a gate]"
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
