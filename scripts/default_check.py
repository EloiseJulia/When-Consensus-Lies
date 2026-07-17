# constructed by: Claude (Anthropic) family
"""default_check.py — EXPLORATORY default-check diagnostic driver (offline-guarded).

Purpose (see paper/plans/2026-07-16-default-check-diagnostic-plan.md):
  Validate regime tags + trap behavior + the per-condition I_perp RATE + the O2
  CD-saturation disambiguation BEFORE the registered run. Results are EXPLORATORY —
  they do NOT count toward H1/H2 support. The metric is FROZEN.

OFFLINE / CI SAFE: the CLI ``main()`` does NOTHING unless BOTH guards pass:
  1. RUN_DEFAULT_CHECK=1 environment variable is set
  2. GITHUB_MODELS_TOKEN or GH_MODELS_TOKEN environment variable is present
Without both, it prints "skipped" and exits 0 — no network, no cost. (Same double-guard
discipline as scripts/mini_pilot.py and harness/runner.py.) The token is NEVER logged.

LIVE execution is the MANAGER's job (after a clean cross-family audit). This module is
written OFFLINE-verifiable; the offline unit test drives ``run_diagnostic`` /
``build_report`` against the deterministic mock client with no network and no token.

What it does when live:
  - Uses harness/runner.py (resumable, RPM-throttled, disk-cache-backed, hard budget cap).
  - Runs a SMALL curated task set (strong H1 traps + a code_invoice k-gradient + the H2
    median-skew item + the 4 SUBTLER diagnostic traps from bench/diagnostic).
  - Pool weights the REASONER-vs-WEAKER contrast; gpt-4o-mini is EXCLUDED to protect its
    daily cap for the registered mini-pilot baseline.
  - Labels via executable gold (harness.label.label_run for benchmark tasks; the
    diagnostic labeler for the subtler traps) — NEVER an LLM judge.
  - Reports per (task, regime, model_class): convergent_delusion BOTH ways
    (enumerated-foils-only AND the frozen false_consensus_rate with I_perp eligible), the
    I_perp RATE, the resolve-to-I0 rate (H2 reasoner-resolution / H1 default-wrong), and
    the CD-vs-k curve for the code_invoice family. Emits JSONL + a human-readable table.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# ── Token / guard helpers (token NEVER printed) ───────────────────────────────

def _token() -> str:
    return (
        os.environ.get("GITHUB_MODELS_TOKEN")
        or os.environ.get("GH_MODELS_TOKEN")
        or ""
    )


def _should_run() -> bool:
    """Double-guard: explicit env flag AND a present token."""
    return os.environ.get("RUN_DEFAULT_CHECK", "0") == "1" and bool(_token())


# ── Diagnostic constants (task set, pool, budget) ─────────────────────────────

TARGET_LABEL = "I0"           # the reversed-target interpretation id (always I0)

# STRONG H1 traps (existing benchmark) — expected to saturate CD near 1.0 at k=1.
STRONG_TRAP_IDS = [
    "code_quarter_001_k1_fiscal_year_start",
    "policy_overtime_001_k1_overtime_threshold",
    "data_activeusers_001_k1_active_user_threshold",
]

# code_invoice k-gradient family — probes CD saturation vs k (k1/k2/k3).
K_GRADIENT_IDS = [
    "code_invoice_001_k1_fiscal_year_start",
    "code_invoice_001_k2_fiscal_date",
    "code_invoice_001_k3_all",
]

# H2 median-under-visible-skew item — reasoners should RESOLVE to I0 (median).
H2_TASK_ID = "data_typical_001_k1_central_tendency"

# Diagnostic SUBTLER traps come from bench.diagnostic.generate_tasks() (ids diag_*).

# Pool (owner ruling): reasoner-vs-weaker weighted, gpt-4o-mini EXCLUDED.
# Homogeneous within-ensemble convergence (config "sc", k=5, temperature 0.7).
# REASONER-WEIGHTED: BOTH reasoners in the sc ensemble alongside ONE weak model, so the
# within-ensemble convergence signal is dominated by reasoners (that is what validates
# H1/H2). llama stays in the heterogeneous single-pass pool only.
HOMOGENEOUS_MODELS: List[Tuple[str, str]] = [
    ("tested_agents", "deepseek/deepseek-r1"),          # reasoner
    ("tested_agents", "openai/o4-mini"),                # reasoner
    ("tested_agents", "mistral-ai/mistral-small-2503"), # weak
]

# Heterogeneous diverse pool (config "single", one independent sample per family).
# deepseek-r1 + o4-mini (reasoners) + mistral-small + llama (weak). NO gpt-4o-mini.
POOL_MODELS: List[Tuple[str, str]] = [
    ("tested_agents", "deepseek/deepseek-r1"),
    ("tested_agents", "openai/o4-mini"),
    ("tested_agents", "mistral-ai/mistral-small-2503"),
    ("tested_agents", "meta/llama-3.3-70b-instruct"),
]

# Model-class tags (for per model_class reporting).
REASONER_SLUGS = {"deepseek/deepseek-r1", "openai/o4-mini"}
WEAK_SLUGS = {"mistral-ai/mistral-small-2503", "meta/llama-3.3-70b-instruct"}

SC_K = 5                        # within-ensemble samples (temperature > 0)
BUDGET_USD = 0.50               # hard aggregate cap (Runner stops cleanly + resumes)
RPM = 10                        # conservative per-model requests/min
CACHE_DIR = ".llm_cache_default_check"
CHECKPOINT = "default_check_checkpoint.jsonl"

# Raised token budget for reasoning models: 4096 is exhausted mid-<think> on complex
# tasks (reasoning tokens count toward max_completion_tokens → truncation → I_perp).
# Daily cap is on request COUNT not tokens, so a higher per-call budget does not worsen
# the cap. 12288 is safe for both reasoning and weak models (8-12k output cap is harmless
# for non-reasoners). See paper/plans/2026-07-16-reasoner-budget-plan.md §C.
MAX_TOKENS_PER_CALL = 12288

# Task subset for the REASONER homogeneous-sc pass (pass A).
# code_invoice is EXCLUDED: it is a complex 3-part combinatorial task that produces
# off-axis (I_perp) output even for weak models; it also caused the deepseek-r1
# truncation. The k-gradient diagnostic (kgrad role) is preserved in the heterogeneous
# single pass (pass B) only. Essential reasoner cells: strong H1 traps + H2 + subtlers.
REASONER_SC_EXCLUDED_IDS: frozenset = frozenset(K_GRADIENT_IDS)


# ── Roster abstraction (parametrizes the model plane; task plane is shared) ────
# The GitHub-Models driver and the frontier (Copilot-proxy) re-validation driver
# share the SAME task set, labeling, CD/I_perp math, report assembly and rendering.
# The ONLY axis that differs is the model roster (which slugs run pass A / pass B
# and how each slug is classified). A ``Roster`` bundles that model plane so the
# frontier driver (scripts/default_check_frontier.py, Amendment 06) reuses every
# pure function here with zero duplication.

class Roster:
    """The model plane of a default-check run (task plane stays shared/frozen).

    - ``homogeneous_models``: (role, slug) grid swept by pass A (config "sc") — each
      slug runs its OWN homogeneous within-ensemble sc ensemble (k samples).
    - ``pool_models``: (role, slug) grid swept by pass B (config "single") — one
      independent sample per family (the heterogeneous diverse pool).
    - ``reasoner_slugs`` / ``weak_slugs`` / ``rho_baseline_slugs``: model_class tags
      for per (task, regime, model_class) reporting.
    - ``reasoner_sc_excluded_ids``: task ids removed from pass A (code_invoice kgrad).

    Implemented as a plain (non-dataclass) class on purpose: this driver is loaded
    via importlib as a NON-package module (scripts/ is not importable), so it is not
    registered in ``sys.modules`` under its ``__module__`` name. ``@dataclass`` +
    ``from __future__ import annotations`` would then fail its KW_ONLY/ClassVar probe
    (``sys.modules.get(cls.__module__)`` → None). A hand-written ``__init__`` avoids
    that entirely and keeps the roster hashable/immutable-in-practice.
    """

    def __init__(
        self,
        name: str,
        homogeneous_models,
        pool_models,
        reasoner_slugs,
        weak_slugs,
        reasoner_sc_excluded_ids=None,
        rho_baseline_slugs=frozenset(),
    ) -> None:
        self.name = name
        self.homogeneous_models = tuple(homogeneous_models)
        self.pool_models = tuple(pool_models)
        self.reasoner_slugs = frozenset(reasoner_slugs)
        self.weak_slugs = frozenset(weak_slugs)
        self.reasoner_sc_excluded_ids = (
            frozenset(K_GRADIENT_IDS) if reasoner_sc_excluded_ids is None
            else frozenset(reasoner_sc_excluded_ids)
        )
        self.rho_baseline_slugs = frozenset(rho_baseline_slugs)

    def model_class(self, slug: str) -> str:
        if slug in self.reasoner_slugs:
            return "reasoner"
        if slug in self.weak_slugs:
            return "weak"
        if slug in self.rho_baseline_slugs:
            return "rho_baseline"
        return "other"


# The default (GitHub-Models) roster, assembled from the module constants above so
# existing behavior is byte-identical when no roster is passed.
GITHUB_ROSTER = Roster(
    name="github_models",
    homogeneous_models=tuple(HOMOGENEOUS_MODELS),
    pool_models=tuple(POOL_MODELS),
    reasoner_slugs=frozenset(REASONER_SLUGS),
    weak_slugs=frozenset(WEAK_SLUGS),
    reasoner_sc_excluded_ids=REASONER_SC_EXCLUDED_IDS,
)


def model_class(slug: str) -> str:
    """Back-compat module-level classifier (delegates to the default GitHub roster)."""
    return GITHUB_ROSTER.model_class(slug)


# ── Enumerated-only convergent delusion (thin helper — metrics.py is FROZEN) ──

def convergent_delusion_enumerated(labels: List[str], target: str,
                                   perp_label: str = "I_perp") -> float:
    """CD over ENUMERATED wrong foils only.

    I_perp is NOT eligible to be the modal-wrong label, but agents labelled I_perp STAY
    IN THE DENOMINATOR (Amendment-04 sensitivity variant). Contrast with the FROZEN
    harness.metrics.false_consensus_rate, where I_perp IS eligible as the modal wrong.

    Returns the frequency (over ALL labels, incl. I_perp agents) of the most common
    ENUMERATED wrong foil, or 0.0 if there are no enumerated wrong foils.
    """
    if not labels:
        return 0.0
    wrong_counts: Dict[str, int] = {}
    for label in labels:
        if label != target and label != perp_label:
            wrong_counts[label] = wrong_counts.get(label, 0) + 1
    if not wrong_counts:
        return 0.0
    return max(wrong_counts.values()) / len(labels)


def _modal_wrong_enumerated(labels: List[str], target: str,
                            perp_label: str = "I_perp") -> Optional[str]:
    wrong_counts: Dict[str, int] = {}
    for label in labels:
        if label != target and label != perp_label:
            wrong_counts[label] = wrong_counts.get(label, 0) + 1
    if not wrong_counts:
        return None
    # Deterministic tie-break: highest count, then lexicographically smallest id.
    return sorted(wrong_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def ensemble_stats(labels: List[str], target: str = TARGET_LABEL) -> Dict[str, Any]:
    """Compute the full per-ensemble diagnostic summary from a list of labels."""
    from harness.metrics import false_consensus_rate  # FROZEN metric

    n = len(labels)
    n_perp = sum(1 for x in labels if x == "I_perp")
    n_target = sum(1 for x in labels if x == target)
    return {
        "n": n,
        "labels": list(labels),
        "target": target,
        "cd_enumerated": convergent_delusion_enumerated(labels, target),
        "cd_frozen_with_iperp": false_consensus_rate(labels, target),
        "modal_wrong_enumerated": _modal_wrong_enumerated(labels, target),
        "i_perp_rate": (n_perp / n) if n else 0.0,
        "resolve_rate_to_I0": (n_target / n) if n else 0.0,
    }


# ── Task selection ────────────────────────────────────────────────────────────

def select_tasks() -> Tuple[List[Any], Dict[str, str]]:
    """Return (tasks, task_role) for the diagnostic.

    ``task_role`` maps task_id -> one of {"strong", "kgrad", "h2", "subtler"} so the
    report can group and compare strong vs subtler (the saturation instrument).
    """
    from bench.code_spec import generate_tasks as gen_code
    from bench.data_analysis import generate_tasks as gen_data
    from bench.policy_qa import generate_tasks as gen_policy
    from bench.diagnostic import generate_tasks as gen_diag

    by_id = {t.id: t for t in (gen_code() + gen_data() + gen_policy())}

    wanted: List[Tuple[str, str]] = (
        [(tid, "strong") for tid in STRONG_TRAP_IDS]
        + [(tid, "kgrad") for tid in K_GRADIENT_IDS]
        + [(H2_TASK_ID, "h2")]
    )

    tasks: List[Any] = []
    task_role: Dict[str, str] = {}
    for tid, role in wanted:
        if tid not in by_id:
            raise KeyError(f"default_check: expected benchmark task '{tid}' not found")
        tasks.append(by_id[tid])
        task_role[tid] = role

    for t in gen_diag():                       # 4 subtler diagnostic traps
        tasks.append(t)
        task_role[t.id] = "subtler"

    return tasks, task_role


# ── Labeling: route diagnostic tasks to the diagnostic labeler ────────────────

def make_label_run_fn() -> Callable[[Any, Any], str]:
    """Return a label_run(run, task) that routes diag_* tasks to the diagnostic
    executable-gold labeler and everything else to the FROZEN harness.label.label_run.
    harness/label.py is NOT modified.
    """
    from harness.label import label_run as bench_label_run
    from bench.diagnostic import is_diagnostic_task, label_diagnostic

    def _label(run: Any, task: Any) -> str:
        if is_diagnostic_task(task):
            return label_diagnostic(run, task)
        return bench_label_run(run, task)

    return _label


# ── Runner passes ─────────────────────────────────────────────────────────────

def run_diagnostic(
    client,
    tasks: List[Any],
    task_role: Dict[str, str],
    *,
    checkpoint_path: str = CHECKPOINT,
    seed: Optional[int] = None,
    sc_k: int = SC_K,
    budget_usd: Optional[float] = BUDGET_USD,
    rpm: int = RPM,
    roster: Roster = GITHUB_ROSTER,
) -> Dict[str, Any]:
    """Execute the diagnostic against *client* (offline mock OR live) and build the report.

    Two Runner passes share ONE checkpoint + the client's disk cache:
      A. config "sc"     over roster.homogeneous_models → within-ensemble convergence.
      B. config "single" over roster.pool_models        → heterogeneous diverse pool +
                                                          single reasoner resolution pass.

    ``client`` fully controls online/offline (offline mock needs no token/network), so the
    same code path is exercised by the offline unit test and by the Manager's live run.
    ``roster`` selects the model plane (GitHub-Models by default; the frontier driver
    passes FRONTIER_ROSTER). Returns the report dict (also written as JSONL by ``main``).
    """
    from harness.run import run_task as base_run_task
    from harness.runner import CheckpointStore

    if seed is None:
        seed = client.config["seeds"]["global"]

    label_fn = make_label_run_fn()

    # Force sc's k for this diagnostic (Runner calls run_task without kwargs; inject a
    # wrapper that sets k so within-ensemble size is exactly sc_k).
    def _run_task_fn(task, config, cli, **kwargs):
        if config == "sc":
            kwargs.setdefault("k", sc_k)
        return base_run_task(task, config, cli, **kwargs)

    # Pass A + B share the checkpoint; the Runner uses the injected run_task/label fns.
    from harness.runner import Runner, RunnerConfig

    def _pass(configs, models, pass_tasks):
        cfg = RunnerConfig(
            tasks=pass_tasks,
            configs=configs,
            seeds=[seed],
            models=list(models),
            checkpoint_path=Path(checkpoint_path),
            rpm=rpm,
            max_budget_usd=budget_usd,
        )
        runner = Runner(cfg, client, run_task_fn=_run_task_fn, label_run_fn=label_fn)
        return runner.run()

    # Pass A: homogeneous sc — code_invoice EXCLUDED (see roster.reasoner_sc_excluded_ids).
    sc_tasks = [t for t in tasks if t.id not in roster.reasoner_sc_excluded_ids]
    status_a = _pass(["sc"], roster.homogeneous_models, sc_tasks)

    # Pass B: heterogeneous single pass over all tasks (including code_invoice kgrad).
    status_b = _pass(["single"], roster.pool_models, tasks)

    # Read back every checkpointed run and build the report.
    store = CheckpointStore(Path(checkpoint_path),
                            endpoint=_endpoint_identity_for(client))
    report = build_report(store.all_runs(), tasks, task_role,
                          total_cost_usd=store.aggregate_cost_usd, roster=roster)
    report["runner_status"] = {"pass_a_sc": status_a, "pass_b_single": status_b}
    report["roster_name"] = roster.name
    return report


def _endpoint_identity_for(client) -> Optional[str]:
    """Read-back must use the SAME endpoint namespace the Runner wrote under, so a
    copilot_proxy run is not read through the github_models namespace (and vice versa)."""
    try:
        from harness.runner import endpoint_identity
        return endpoint_identity(client.provider, client.base_url)
    except Exception:
        return None


# ── Report assembly (pure function — offline-testable) ────────────────────────

def build_report(
    runs: List[Dict[str, Any]],
    tasks: List[Any],
    task_role: Dict[str, str],
    *,
    total_cost_usd: float = 0.0,
    roster: Roster = GITHUB_ROSTER,
) -> Dict[str, Any]:
    """Build the machine-readable diagnostic report from checkpointed AgentRun records.

    ``runs`` = list of dicts with keys task_id, config, model_id, seed, label (as written
    by harness.runner.CheckpointStore). Produces per-ensemble rows plus derived summaries:
      - homogeneous rows: one per (task, model) over the sc ensemble (within-ensemble CD).
      - heterogeneous_pool rows: one per task over the single-pass runs (one sample/family).
      - single_reasoner rows on the H2 task (reasoner-resolution check).
      - CD-vs-k curve for the code_invoice family.
      - strong-vs-subtler CD comparison (the O2 saturation instrument).
      - per-model call counts + total cost.
    """
    ambiguity = {t.id: t.ambiguity_level for t in tasks}
    regimes = {t.id: t.regime for t in tasks}

    # Group labels by (task, config, model).
    grouped: Dict[Tuple[str, str, str], List[str]] = defaultdict(list)
    per_model_calls: Dict[str, int] = defaultdict(int)
    for rec in runs:
        key = (rec["task_id"], rec["config"], rec["model_id"])
        grouped[key].append(rec["label"])
        per_model_calls[rec["model_id"]] += 1

    rows: List[Dict[str, Any]] = []

    # Homogeneous within-ensemble rows (config "sc").
    for (task_id, config, model_id), labels in sorted(grouped.items()):
        if config != "sc":
            continue
        stats = ensemble_stats(labels)
        rows.append({
            "task_id": task_id,
            "regime": regimes.get(task_id),
            "ambiguity_level": ambiguity.get(task_id),
            "task_role": task_role.get(task_id),
            "ensemble_type": "homogeneous",
            "model_id": model_id,
            "model_class": roster.model_class(model_id),
            **stats,
        })

    # Heterogeneous diverse-pool rows: one independent sample per family (config "single").
    pool_by_task: Dict[str, List[str]] = defaultdict(list)
    for (task_id, config, model_id), labels in grouped.items():
        if config == "single":
            pool_by_task[task_id].extend(labels)
    for task_id in sorted(pool_by_task):
        stats = ensemble_stats(pool_by_task[task_id])
        rows.append({
            "task_id": task_id,
            "regime": regimes.get(task_id),
            "ambiguity_level": ambiguity.get(task_id),
            "task_role": task_role.get(task_id),
            "ensemble_type": "heterogeneous_pool",
            "model_id": "pool[" + ",".join(sorted({m for (_t, c, m) in grouped
                                                    if c == "single" and _t == task_id})) + "]",
            "model_class": "heterogeneous",
            **stats,
        })

    # Single reasoner-resolution rows on the H2 task (config "single", reasoner slugs).
    reasoner_resolution: List[Dict[str, Any]] = []
    for (task_id, config, model_id), labels in sorted(grouped.items()):
        if config == "single" and task_id == H2_TASK_ID and model_id in roster.reasoner_slugs:
            stats = ensemble_stats(labels)
            reasoner_resolution.append({
                "task_id": task_id,
                "regime": regimes.get(task_id),
                "model_id": model_id,
                "model_class": "reasoner",
                "resolved_to_I0": stats["resolve_rate_to_I0"] >= 0.5,
                **stats,
            })

    # CD-vs-k curve for the code_invoice family (homogeneous sc, per model).
    kcurve: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["ensemble_type"] == "homogeneous" and row["task_id"] in K_GRADIENT_IDS:
            kcurve[row["model_id"]].append({
                "k": row["ambiguity_level"],
                "task_id": row["task_id"],
                "cd_enumerated": row["cd_enumerated"],
                "cd_frozen_with_iperp": row["cd_frozen_with_iperp"],
            })
    for model_id in kcurve:
        kcurve[model_id].sort(key=lambda d: d["k"])

    # Strong-vs-subtler CD comparison (the O2 saturation instrument). Uses homogeneous
    # rows only, averaged across models, split by task_role.
    def _mean(xs: List[float]) -> Optional[float]:
        return sum(xs) / len(xs) if xs else None

    strong_cd = [r["cd_enumerated"] for r in rows
                 if r["ensemble_type"] == "homogeneous" and r["task_role"] == "strong"]
    subtler_cd = [r["cd_enumerated"] for r in rows
                  if r["ensemble_type"] == "homogeneous" and r["task_role"] == "subtler"]
    strong_cd_frozen = [r["cd_frozen_with_iperp"] for r in rows
                        if r["ensemble_type"] == "homogeneous" and r["task_role"] == "strong"]
    subtler_cd_frozen = [r["cd_frozen_with_iperp"] for r in rows
                         if r["ensemble_type"] == "homogeneous" and r["task_role"] == "subtler"]

    saturation = {
        "strong_mean_cd_enumerated": _mean(strong_cd),
        "subtler_mean_cd_enumerated": _mean(subtler_cd),
        "strong_mean_cd_frozen": _mean(strong_cd_frozen),
        "subtler_mean_cd_frozen": _mean(subtler_cd_frozen),
        # Interpretation guide (decided BEFORE the run, per the plan):
        #   subtler CD ~1.0  -> saturation robust/real (report "immediate failure").
        #   subtler CD <1.0  -> the measure DISCRIMINATES; strong-trap saturation is
        #                       an artifact of trap strength (add subtler/finer measure).
        "note": ("If subtler_mean_cd < strong_mean_cd (and < 1.0) the CD measure "
                 "DISCRIMINATES → strong-trap saturation is a trap-strength artifact. "
                 "If subtler CD also ~1.0 → saturation is robust/real."),
    }

    # Overall I_perp rate (guardrail B: a high rate flags answer-format non-compliance).
    all_labels = [rec["label"] for rec in runs]
    overall_i_perp = (sum(1 for x in all_labels if x == "I_perp") / len(all_labels)
                      if all_labels else 0.0)

    return {
        "rows": rows,
        "reasoner_resolution_h2": reasoner_resolution,
        "cd_vs_k_curve": dict(kcurve),
        "saturation_disambiguation": saturation,
        "overall_i_perp_rate": overall_i_perp,
        "per_model_calls": dict(per_model_calls),
        "total_calls": len(runs),
        "total_cost_usd": total_cost_usd,
        "gpt4o_mini_excluded": not any("gpt-4o-mini" in m for m in per_model_calls),
    }


# ── Human-readable rendering ──────────────────────────────────────────────────

def render_table(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("=" * 100)
    lines.append("DEFAULT-CHECK DIAGNOSTIC (EXPLORATORY — does NOT count toward H1/H2)")
    lines.append("=" * 100)
    hdr = (f"{'task_id':38} {'k':>2} {'regime':11} {'ensemble':18} "
           f"{'class':13} {'n':>3} {'CDenum':>7} {'CDfroz':>7} {'Iperp':>6} {'->I0':>6}")
    lines.append(hdr)
    lines.append("-" * len(hdr))
    for r in report["rows"]:
        lines.append(
            f"{r['task_id'][:38]:38} {str(r['ambiguity_level']):>2} "
            f"{str(r['regime'] or '-'):11} {r['ensemble_type']:18} "
            f"{r['model_class']:13} {r['n']:>3} "
            f"{r['cd_enumerated']:>7.3f} {r['cd_frozen_with_iperp']:>7.3f} "
            f"{r['i_perp_rate']:>6.3f} {r['resolve_rate_to_I0']:>6.3f}"
        )

    lines.append("")
    lines.append("H2 REASONER RESOLUTION (data_typical median-skew — expect resolve->I0):")
    if report["reasoner_resolution_h2"]:
        for r in report["reasoner_resolution_h2"]:
            lines.append(f"  {r['model_id']:32} resolve->I0={r['resolve_rate_to_I0']:.3f} "
                         f"resolved={r['resolved_to_I0']} labels={r['labels']}")
    else:
        lines.append("  (no reasoner single-pass runs present)")

    lines.append("")
    lines.append("CD-vs-k CURVE (code_invoice family, homogeneous sc, per model):")
    for model_id, pts in report["cd_vs_k_curve"].items():
        curve = " ".join(f"k{p['k']}={p['cd_enumerated']:.2f}" for p in pts)
        lines.append(f"  {model_id:32} {curve}")

    lines.append("")
    s = report["saturation_disambiguation"]
    lines.append("O2 SATURATION DISAMBIGUATION (strong vs subtler, homogeneous mean CD):")
    lines.append(f"  strong  mean CDenum={s['strong_mean_cd_enumerated']}  "
                 f"CDfrozen={s['strong_mean_cd_frozen']}")
    lines.append(f"  subtler mean CDenum={s['subtler_mean_cd_enumerated']}  "
                 f"CDfrozen={s['subtler_mean_cd_frozen']}")
    lines.append(f"  {s['note']}")

    lines.append("")
    lines.append(f"Overall I_perp rate: {report['overall_i_perp_rate']:.3f}  "
                 f"(guardrail B: investigate if > 0.20)")
    lines.append(f"Total calls: {report['total_calls']}  "
                 f"per-model: {report['per_model_calls']}")
    lines.append(f"Total cost (nominal): ${report['total_cost_usd']:.4f}  "
                 f"gpt-4o-mini excluded: {report['gpt4o_mini_excluded']}")
    lines.append("=" * 100)
    return "\n".join(lines)


def write_report(report: Dict[str, Any], out_dir: str = ".") -> Tuple[str, str]:
    """Write the JSONL machine summary and the human table; return their paths."""
    out = Path(out_dir)
    jsonl_path = out / "default_check_summary.jsonl"
    table_path = out / "default_check_table.txt"
    with open(jsonl_path, "w", encoding="utf-8") as fh:
        # One JSON object per line: rows first, then the derived-summary object.
        for row in report["rows"]:
            fh.write(json.dumps({"type": "row", **row}) + "\n")
        summary = {k: v for k, v in report.items() if k != "rows"}
        fh.write(json.dumps({"type": "summary", **summary}) + "\n")
    with open(table_path, "w", encoding="utf-8") as fh:
        fh.write(render_table(report) + "\n")
    return str(jsonl_path), str(table_path)


# ── CLI entry point (double-guarded) ──────────────────────────────────────────

def main() -> None:
    if not _should_run():
        print(
            "default_check: skipped (RUN_DEFAULT_CHECK != 1 or no token in "
            "GITHUB_MODELS_TOKEN / GH_MODELS_TOKEN). Set both to run live."
        )
        sys.exit(0)

    # Live path (Manager only). Imports are local so offline/CI never needs them.
    from common.config import load_config
    from common.llm import LLMClient

    cfg = load_config()
    tasks, task_role = select_tasks()

    print("=" * 70)
    print("DEFAULT-CHECK DIAGNOSTIC — LIVE (EXPLORATORY)")
    print(f"  tasks={len(tasks)}  sc_k={SC_K}  budget=${BUDGET_USD:.2f}  rpm={RPM}")
    print(f"  max_tokens_per_call={MAX_TOKENS_PER_CALL}  (raised for reasoner completion)")
    print(f"  reasoner-sc excludes: {sorted(REASONER_SC_EXCLUDED_IDS)}")
    print(f"  homogeneous models={[m for _r, m in HOMOGENEOUS_MODELS]}")
    print(f"  pool models={[m for _r, m in POOL_MODELS]}  (gpt-4o-mini EXCLUDED)")
    print("=" * 70)

    client = LLMClient(
        cfg,
        cache_dir=CACHE_DIR,
        offline=False,
        max_budget_usd=BUDGET_USD,
        max_requests_per_min=RPM,
        max_tokens_per_call=MAX_TOKENS_PER_CALL,
    )

    report = run_diagnostic(client, tasks, task_role,
                            checkpoint_path=CHECKPOINT, budget_usd=BUDGET_USD, rpm=RPM)
    jsonl_path, table_path = write_report(report)
    print(render_table(report))
    print(f"\nWrote machine summary -> {jsonl_path}")
    print(f"Wrote human table     -> {table_path}")
    print("\nNOTE: EXPLORATORY only — report to the Manager; does NOT count toward H1/H2.")


if __name__ == "__main__":
    main()
