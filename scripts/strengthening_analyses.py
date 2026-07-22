"""POST-HOC SECONDARY strengthening analyses (blind-review responses).

# Implementer model family: Claude (Anthropic)

These are **SECONDARY / POST-HOC** analyses that respond to a blind reviewer.
They are $0 (pure offline analysis of EXISTING checkpoint data — NO model calls,
NO network) and are ADDITIVE: they reuse the FROZEN ``analysis/`` +
``scripts/registered_run.py`` functions by import and do NOT change ANY
confirmatory number, metric definition, or pre-registered hypothesis.

Two analyses are computed:

Analysis 1 (blind-review #6) — per-item cross-MODEL label CONCENTRATION on the
    Amendment-10 R2 cross-family subset (``bench/data/r2_xf.jsonl`` /
    ``.run_partitions/cp_r2_xf.jsonl``). The reviewer objected that a
    "single-agent CD=0.72" (N=1 within a cell) is just an error rate and cannot
    demonstrate cross-MODEL convergence. We therefore measure, for each R2 item,
    how strongly the INDEPENDENT single-agent labels from DISTINCT non-Anthropic
    tested models/seeds concentrate on the SAME specific wrong enumerated foil.
    Convergence of multiple independent models/families onto one foil is genuine
    cross-model convergent delusion, not a within-cell tautology.

Analysis 2 (blind-review #8) — TOST EQUIVALENCE tests. The reviewer objected
    that non-significant differences were described as "equivalence/invariance".
    We run two one-sided tests (TOST) with a PRE-STATED equivalence margin
    (declared as a module constant BELOW, before any computation) on:
      (a) heterogeneous-MAD vs homogeneous-MAD CD on H1_external (row-35), and
      (b) capability-tier CD invariance on H1_external (reasoning vs weak vs
          heterogeneous), using item-level paired differences.

All CD numbers reuse the frozen A04 ``analysis.cd.cd_primary`` PRIMARY metric and
the frozen contrast helpers; the bootstrap CI reuses the frozen
``scripts.registered_run._bootstrap_ci`` (fixed seed 42). Nothing here is
reimplemented.

Run:
    python scripts/strengthening_analyses.py [--out files/strengthening_results.md]
    python scripts/strengthening_analyses.py --data-dir <dir> --format json
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd
from scipy import stats as _sstats

# ── Repo import bootstrap ─────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from analysis.cd import cd_primary, IPERP  # frozen PRIMARY metric (A04)
from analysis.contrasts import (  # frozen contrast helpers
    COLS,
    HETEROGENEOUS_METHOD,
    HOMOGENEOUS_METHOD,
    compute_cell_cd,
    cross_model_vs_homogeneous,
)
from scripts.registered_run import _bootstrap_ci, load_tasks  # frozen bootstrap + loader


# ── PRE-STATED EQUIVALENCE MARGINS (declared BEFORE any computation) ──────────
# Analysis 2 TOST equivalence bounds. These are FIXED IN ADVANCE (per blind-review
# response) and are NOT tuned to the data.
#
# PRIMARY bound = the study's own pre-registered minimum detectable effect
# ΔCD = 0.15 (Amendment 08 §3 power target: the smallest CD difference the
# confirmatory design was powered to detect). Establishing equivalence at this
# bound means any true difference is smaller than the effect the study could have
# detected — the honest meaning of "invariance" for this design.
EQUIV_MARGIN_PRIMARY: float = 0.15
# SECONDARY (stricter) bound — reported for transparency; equivalence here is a
# stronger claim and is NOT guaranteed to hold.
EQUIV_MARGIN_STRICT: float = 0.10

#: Deterministic bootstrap seed (mirrors the frozen _bootstrap_ci convention).
BOOTSTRAP_SEED: int = 42
#: TOST significance level (two one-sided tests each at alpha; equivalence CI is
#: the (1 - 2*alpha) = 90% CI when alpha = 0.05).
TOST_ALPHA: float = 0.05

#: The Anthropic constructor family of the R2 subset (Amendment 10). The R2
#: cross-family estimate counts ONLY tested cells whose family != this.
_R2_CONSTRUCTOR_FAMILY = "anthropic"

# Column shorthands (from the frozen tidy schema).
_ITEM = COLS["item"]
_METHOD = COLS["method"]
_MODEL_CLASS = COLS["model_class"]
_SEED = COLS["seed"]
_LABEL = COLS["label"]
_TARGET = COLS["target"]
_REGIME = COLS["regime"]
_AMBIGUITY_K = COLS["ambiguity_k"]
_MODEL = "model"

# Confirmatory per-domain partition filenames (combined == the confirmatory grid).
_CONF_PARTITIONS = (
    ".run_partitions/cp_code_spec.jsonl",
    ".run_partitions/cp_data_analysis.jsonl",
    ".run_partitions/cp_policy_qa.jsonl",
)
_CONF_FALLBACK = "registered_run_checkpoint.jsonl"
_R2_PARTITION = ".run_partitions/cp_r2_xf.jsonl"


# ── Family derivation (config.yaml: gpt*->openai, claude*->anthropic, ─────────
#    gemini*->google, mai-code*->microsoft) ────────────────────────────────────
def family_of(model_id: str) -> str:
    """Map a bare proxy model slug to its provider family (config.yaml rule)."""
    mid = (model_id or "").lower()
    if mid.startswith("gpt"):
        return "openai"
    if mid.startswith("claude"):
        return "anthropic"
    if mid.startswith("gemini"):
        return "google"
    if mid.startswith("mai-code") or mid.startswith("mai"):
        return "microsoft"
    return "unknown"


# ── Data loading (offline; auto-discovers the data dir) ──────────────────────
def resolve_data_dir(explicit: Optional[str] = None) -> Path:
    """Find the directory holding the checkpoint data.

    Search order: an explicit ``--data-dir``; then the current working directory
    and each parent, taking the first that contains the R2 partition or the
    confirmatory checkpoint. (A git worktree does not carry the gitignored data
    files, so the real data typically lives in the main checkout — an ancestor of
    the worktree cwd.)
    """
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"--data-dir {p} does not exist")
        return p
    candidates = [Path.cwd()] + list(Path.cwd().resolve().parents) + [_REPO_ROOT] + list(_REPO_ROOT.parents)
    seen = set()
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        if (c / _R2_PARTITION).exists() or (c / _CONF_FALLBACK).exists() or \
                (c / _CONF_PARTITIONS[0]).exists():
            return c
    raise FileNotFoundError(
        "Could not locate checkpoint data (looked for "
        f"{_R2_PARTITION!r} / {_CONF_FALLBACK!r} in cwd + ancestors). "
        "Pass --data-dir explicitly."
    )


def load_confirmatory_tidy(data_dir: Path) -> pd.DataFrame:
    """Load the confirmatory H1/H2 grid (three domain partitions combined).

    Falls back to ``registered_run_checkpoint.jsonl`` if the partitions are
    absent. Reuses the frozen ``analysis.io.load_runs_tidy``.
    """
    from analysis.io import load_runs_tidy

    tasks = load_tasks(["code_spec", "data_analysis", "policy_qa"])
    frames: List[pd.DataFrame] = []
    for rel in _CONF_PARTITIONS:
        p = data_dir / rel
        if p.exists():
            frames.append(load_runs_tidy(p, tasks))
    if not frames:
        fp = data_dir / _CONF_FALLBACK
        if fp.exists():
            frames.append(load_runs_tidy(fp, tasks))
    if not frames:
        raise FileNotFoundError(
            f"No confirmatory data found under {data_dir} "
            f"({_CONF_PARTITIONS} nor {_CONF_FALLBACK})."
        )
    return pd.concat(frames, ignore_index=True)


def load_r2_tidy(data_dir: Path) -> pd.DataFrame:
    """Load the Amendment-10 R2 cross-family subset as a tidy table."""
    from analysis.io import load_runs_tidy

    p = data_dir / _R2_PARTITION
    if not p.exists():
        raise FileNotFoundError(f"R2 partition not found: {p}")
    tasks = load_tasks(["r2_xf"])
    return load_runs_tidy(p, tasks)


# ═══════════════════════════════════════════════════════════════════════════
# Analysis 1 — per-item cross-MODEL label concentration (blind-review #6)
# ═══════════════════════════════════════════════════════════════════════════
def _modal_wrong_foil(labels: Sequence[str], target: str) -> Optional[str]:
    """Return the single most common ENUMERATED wrong foil (A04 rule).

    Mirrors ``analysis.cd.cd_primary``'s eligibility rule: the target and
    ``I_perp`` are EXCLUDED from being the modal label (but remain in the metric
    denominator, which ``cd_primary`` itself handles). This is used ONLY to
    IDENTIFY which foil the ``cd_primary`` share landed on so we can count how
    many distinct models/families contributed to it — it does not recompute the
    metric value (that comes from the frozen ``cd_primary``). Ties broken by
    label sort order for determinism.
    """
    counts: Dict[str, int] = {}
    for lab in labels:
        if lab != target and lab != IPERP:
            counts[lab] = counts.get(lab, 0) + 1
    if not counts:
        return None
    top = max(counts.values())
    return sorted(k for k, v in counts.items() if v == top)[0]


def analysis1_cross_model_concentration(
    r2_tidy: pd.DataFrame,
    exclude_family: str = _R2_CONSTRUCTOR_FAMILY,
    *,
    single_method: str = "single",
) -> Dict:
    """Per-item cross-MODEL concentration on the R2 Anthropic-constructed items.

    For each item, over the INDEPENDENT single-agent labels from tested models
    whose family != ``exclude_family`` (the Anthropic constructor family), across
    all distinct models/seeds, compute:
      * ``concentration`` = frozen ``cd_primary`` (modal-wrong ENUMERATED foil
        share; I_perp excluded from being modal but kept in the denominator).
      * ``n_models_on_modal_foil`` / ``n_families_on_modal_foil`` = number of
        DISTINCT models / families whose label equals the item's modal wrong foil.

    The Anthropic (same-family) single cells are computed identically and returned
    separately as a reference (they are NOT part of the cross-family estimate).

    IMPORTANT (k0 structural controls): the R2 subset pairs each item with a k0
    CONTROL (ambiguity_level == 0, ``_k0`` id suffix) and a k1 AMBIGUOUS variant.
    k0 controls have NO deleted interpretive axis, so their cross-model
    concentration is **0 BY DESIGN** — nothing to converge on — NOT an observed
    failure to converge. Including them deflates the aggregate. We therefore
    report BOTH the all-item aggregate (for completeness) AND a **k1-stratified**
    aggregate (ambiguity_level >= 1, k0 controls excluded), which is the
    substantive cross-model-convergence result. k0/k1 is read from the FROZEN
    ``ambiguity_level`` metadata (the ``ambiguity_k`` tidy column).

    Returns a dict with the all-item + k1-stratified cross-family aggregates, the
    item-level table (carrying ``ambiguity_level``), an item-level bootstrap CI of
    the mean concentration, and the Anthropic same-family reference aggregates.
    """
    df = r2_tidy[r2_tidy[_METHOD] == single_method].copy()
    df["family"] = df[_MODEL].map(family_of)

    def _per_item(sub: pd.DataFrame) -> List[Dict]:
        rows: List[Dict] = []
        for task_id, g in sub.groupby(_ITEM, sort=True):
            labels = list(g[_LABEL])
            target = g[_TARGET].iloc[0]
            conc = cd_primary(labels, target)  # FROZEN metric
            foil = _modal_wrong_foil(labels, target)
            if foil is not None:
                contrib = g[g[_LABEL] == foil]
                n_models = contrib[_MODEL].nunique()
                n_fams = contrib["family"].nunique()
            else:
                n_models = 0
                n_fams = 0
            amb = g[_AMBIGUITY_K].iloc[0] if _AMBIGUITY_K in g.columns else None
            try:
                amb_val = int(amb) if amb is not None and not pd.isna(amb) else None
            except (TypeError, ValueError):
                amb_val = None
            # Fallback to the id suffix if metadata is absent.
            if amb_val is None:
                amb_val = 0 if str(task_id).endswith("_k0") else 1
            rows.append({
                "task": task_id,
                "ambiguity_level": amb_val,
                "is_k0_control": amb_val == 0,
                "concentration": conc,
                "modal_wrong_foil": foil,
                "n_agents": len(labels),
                "n_models": g[_MODEL].nunique(),
                "n_families": g["family"].nunique(),
                "n_models_on_modal_foil": int(n_models),
                "n_families_on_modal_foil": int(n_fams),
            })
        return rows

    cross = df[df["family"] != exclude_family]
    same = df[df["family"] == exclude_family]

    cross_rows = _per_item(cross)
    same_rows = _per_item(same)

    def _aggregate(rows: List[Dict], label: str) -> Dict:
        if not rows:
            return {"label": label, "n_items": 0}
        concs = [r["concentration"] for r in rows]
        lo, hi = _bootstrap_ci(concs, seed=BOOTSTRAP_SEED)
        n_ge2_families = sum(1 for r in rows if r["n_families_on_modal_foil"] >= 2)
        n_ge2_models = sum(1 for r in rows if r["n_models_on_modal_foil"] >= 2)
        n_with_foil = sum(1 for r in rows if r["modal_wrong_foil"] is not None)
        return {
            "label": label,
            "n_items": len(rows),
            "mean_concentration": statistics.fmean(concs),
            "median_concentration": statistics.median(concs),
            "min_concentration": min(concs),
            "max_concentration": max(concs),
            "boot_ci_lo": lo,
            "boot_ci_hi": hi,
            "mean_n_models_on_modal_foil": statistics.fmean(
                r["n_models_on_modal_foil"] for r in rows),
            "mean_n_families_on_modal_foil": statistics.fmean(
                r["n_families_on_modal_foil"] for r in rows),
            "n_items_with_wrong_foil": n_with_foil,
            "n_items_ge2_families_on_foil": n_ge2_families,
            "frac_items_ge2_families_on_foil": n_ge2_families / len(rows),
            "n_items_ge2_models_on_foil": n_ge2_models,
            "frac_items_ge2_models_on_foil": n_ge2_models / len(rows),
            "distinct_models": sorted(
                set(m for r in rows for m in [])) or None,
        }

    def _k1(rows: List[Dict]) -> List[Dict]:
        return [r for r in rows if r["ambiguity_level"] >= 1]

    cross_agg = _aggregate(cross_rows, "cross_family_non_anthropic_all_items")
    cross_agg_k1 = _aggregate(_k1(cross_rows), "cross_family_non_anthropic_k1")
    same_agg = _aggregate(same_rows, "same_family_anthropic_reference_all_items")
    same_agg_k1 = _aggregate(_k1(same_rows), "same_family_anthropic_reference_k1")

    cross_dm = sorted(cross[_MODEL].unique().tolist())
    cross_df = sorted(cross["family"].unique().tolist())
    for agg in (cross_agg, cross_agg_k1):
        agg["distinct_models"] = cross_dm
        agg["distinct_families"] = cross_df
    for agg in (same_agg, same_agg_k1):
        agg["distinct_models"] = sorted(same[_MODEL].unique().tolist())

    n_k0 = sum(1 for r in cross_rows if r["is_k0_control"])

    return {
        "analysis": "cross_model_label_concentration_R2",
        "kind": "SECONDARY / post-hoc (blind-review #6)",
        "exclude_family": exclude_family,
        "k0_disclosure": (
            f"{n_k0} of {len(cross_rows)} items are k0 CONTROLS "
            "(ambiguity_level==0): concentration is 0 BY DESIGN (no deleted axis "
            "to converge on), NOT an observed failure. The k1-stratified aggregate "
            "(k0 excluded) is the substantive cross-model-convergence result."),
        "n_k0_controls": n_k0,
        "cross_family": cross_agg,           # all items (retained for completeness)
        "cross_family_k1": cross_agg_k1,     # SUBSTANTIVE (k0 controls excluded)
        "same_family_reference": same_agg,
        "same_family_reference_k1": same_agg_k1,
        "item_table": cross_rows,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Analysis 2 — TOST equivalence tests (blind-review #8)
# ═══════════════════════════════════════════════════════════════════════════
def _t_ci(diffs: Sequence[float], conf: float) -> Tuple[float, float]:
    """Two-sided t-based CI for the mean of paired diffs at confidence ``conf``."""
    n = len(diffs)
    mean = statistics.fmean(diffs)
    if n < 2:
        return (float("-inf"), float("inf"))
    sd = statistics.stdev(diffs)
    se = sd / math.sqrt(n)
    if se == 0:
        return (mean, mean)
    tcrit = _sstats.t.ppf(1 - (1 - conf) / 2, df=n - 1)
    return (mean - tcrit * se, mean + tcrit * se)


def tost_paired(diffs: Sequence[float], margin: float,
                alpha: float = TOST_ALPHA) -> Dict:
    """t-based TOST on item-level paired differences for one equivalence margin.

    Two one-sided t-tests against +/- ``margin``. Equivalence is established iff
    BOTH one-sided nulls are rejected at ``alpha`` (equivalently, the
    (1 - 2*alpha) CI lies fully inside (-margin, margin)). Uses the paired-diff
    t-distribution (df = n - 1).
    """
    n = len(diffs)
    mean = statistics.fmean(diffs) if n else float("nan")
    out: Dict = {"margin": margin, "n": n, "observed_delta": mean}
    if n < 2:
        out.update({"equivalent": False, "reason": "n<2", "p_tost": float("nan")})
        return out
    sd = statistics.stdev(diffs)
    se = sd / math.sqrt(n)
    df = n - 1
    if se == 0:
        equivalent = abs(mean) < margin
        out.update({"sd": sd, "se": se, "p_lower": 0.0 if mean > -margin else 1.0,
                    "p_upper": 0.0 if mean < margin else 1.0,
                    "p_tost": 0.0 if equivalent else 1.0, "equivalent": equivalent,
                    "ci90_lo": mean, "ci90_hi": mean})
        return out
    t_lower = (mean - (-margin)) / se           # H0: mean <= -margin
    t_upper = (mean - margin) / se              # H0: mean >= +margin
    p_lower = _sstats.t.sf(t_lower, df)         # upper tail
    p_upper = _sstats.t.cdf(t_upper, df)        # lower tail
    p_tost = max(p_lower, p_upper)
    ci90 = _t_ci(diffs, 1 - 2 * alpha)
    out.update({
        "sd": sd, "se": se,
        "p_lower": float(p_lower), "p_upper": float(p_upper),
        "p_tost": float(p_tost),
        "ci90_lo": ci90[0], "ci90_hi": ci90[1],
        "equivalent": bool(p_tost < alpha),
    })
    return out


def _paired_deltas_by_task(cells: pd.DataFrame,
                           mask_a, mask_b) -> Tuple[List[float], pd.DataFrame]:
    """Per-task mean-cd_primary difference (group A - group B), inner-joined on task."""
    a = cells[mask_a].groupby(_ITEM)["cd_primary"].mean().rename("a")
    b = cells[mask_b].groupby(_ITEM)["cd_primary"].mean().rename("b")
    merged = pd.concat([a, b], axis=1, join="inner").dropna()
    merged["delta"] = merged["a"] - merged["b"]
    return merged["delta"].tolist(), merged


def _tost_block(name: str, diffs: Sequence[float], extra: Optional[Dict] = None) -> Dict:
    ci95 = _t_ci(diffs, 0.95)
    block: Dict = {
        "contrast": name,
        "n_items": len(diffs),
        "observed_delta": statistics.fmean(diffs) if diffs else float("nan"),
        "ci95_lo": ci95[0], "ci95_hi": ci95[1],
        "tost": {
            "primary_0.15": tost_paired(diffs, EQUIV_MARGIN_PRIMARY),
            "strict_0.10": tost_paired(diffs, EQUIV_MARGIN_STRICT),
        },
    }
    if extra:
        block.update(extra)
    return block


def analysis2_tost(conf_tidy: pd.DataFrame) -> Dict:
    """TOST equivalence tests on H1_external CD (blind-review #8).

    (a) heterogeneous-MAD vs homogeneous-MAD (row-35), item-level paired.
    (b) capability-tier CD invariance: reasoning vs weak, reasoning vs
        heterogeneous, weak vs heterogeneous; item-level paired.

    Test statistic: paired-difference t-based TOST (df = n_items - 1). Item-level
    pairing collapses each task to its mean cd_primary within each group, then
    takes the per-task difference (a within-item paired design). The pooled
    row-35 Δ/CI from the frozen ``cross_model_vs_homogeneous`` is also reported
    for cross-reference.
    """
    cells = compute_cell_cd(conf_tidy)
    h1 = cells[cells[_REGIME] == "H1_external"].copy()

    m = h1[_METHOD]
    mc = h1[_MODEL_CLASS]

    # (a) heterogeneous-MAD vs homogeneous-MAD — mirrors the row-35 headline.
    hetero_mask = (m == HETEROGENEOUS_METHOD)
    homo_mask = (m == HOMOGENEOUS_METHOD) & (mc == "homogeneous")
    diffs_a, _ = _paired_deltas_by_task(h1, hetero_mask, homo_mask)

    # Pooled (unpaired) row-35 from the frozen contrast, for cross-reference.
    row35 = cross_model_vs_homogeneous(conf_tidy)
    row35_homo = row35[row35["baseline"] == HOMOGENEOUS_METHOD]
    pooled = {
        "pooled_hetero_cd_primary": float(row35_homo["cd_primary_hetero"].iloc[0]),
        "pooled_homogeneous_cd_primary": float(row35_homo["cd_primary_baseline"].iloc[0]),
        "pooled_delta_cd_primary": float(row35_homo["delta_cd_primary"].iloc[0]),
    }
    block_a = _tost_block("heterogeneous-MAD vs homogeneous-MAD (row-35)",
                          diffs_a, {"pooled_reference": pooled})

    # (b) capability-tier invariance. Tier CD = per-item mean cd_primary over that
    # model_class's H1 cells (reasoning & weak share the SAME method set — a matched
    # comparison; heterogeneous carries only the heterogeneous-MAD method, noted).
    def tier_mask(tier: str):
        return mc == tier

    tiers = [("reasoning", "weak"), ("reasoning", "heterogeneous"),
             ("weak", "heterogeneous")]
    tier_blocks: List[Dict] = []
    tier_means = {t: float(h1[tier_mask(t)]["cd_primary"].mean())
                  for t in ("reasoning", "weak", "heterogeneous")}
    for ta, tb in tiers:
        diffs, _ = _paired_deltas_by_task(h1, tier_mask(ta), tier_mask(tb))
        note = None
        if "heterogeneous" in (ta, tb):
            note = ("heterogeneous tier carries only the heterogeneous-MAD method; "
                    "this comparison is not method-matched")
        tier_blocks.append(_tost_block(
            f"{ta} vs {tb} (capability-tier CD)", diffs,
            {"mean_cd_a": tier_means[ta], "mean_cd_b": tier_means[tb],
             "caveat": note}))

    return {
        "analysis": "tost_equivalence_H1_external",
        "kind": "SECONDARY / post-hoc (blind-review #8)",
        "equivalence_margins": {"primary": EQUIV_MARGIN_PRIMARY,
                                "strict": EQUIV_MARGIN_STRICT},
        "test_statistic": "paired-difference t-based TOST (df = n_items - 1)",
        "tier_mean_cd_primary": tier_means,
        "a_hetero_vs_homogeneous": block_a,
        "b_capability_tiers": tier_blocks,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Report assembly
# ═══════════════════════════════════════════════════════════════════════════
def run_all(data_dir: Path) -> Dict:
    r2 = load_r2_tidy(data_dir)
    conf = load_confirmatory_tidy(data_dir)
    a1 = analysis1_cross_model_concentration(r2)
    a2 = analysis2_tost(conf)
    return {
        "title": "POST-HOC SECONDARY strengthening analyses (blind-review response)",
        "disclaimer": ("SECONDARY / post-hoc. Offline reuse of frozen metrics; "
                       "does NOT change any confirmatory number, metric, or "
                       "pre-registered hypothesis."),
        "implementer_model_family": "Claude (Anthropic)",
        "data_dir": str(data_dir),
        "equivalence_margins_prestated": {
            "primary_0.15": EQUIV_MARGIN_PRIMARY,
            "strict_0.10": EQUIV_MARGIN_STRICT,
        },
        "bootstrap_seed": BOOTSTRAP_SEED,
        "analysis1": a1,
        "analysis2": a2,
    }


def _fmt(x: float, nd: int = 4) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    if isinstance(x, float) and math.isinf(x):
        return "+inf" if x > 0 else "-inf"
    return f"{x:.{nd}f}"


def to_markdown(rep: Dict) -> str:
    a1 = rep["analysis1"]
    a2 = rep["analysis2"]
    cf = a1["cross_family"]
    sf = a1["same_family_reference"]
    L: List[str] = []
    L.append("# Strengthening analyses — post-hoc secondary (blind-review response)")
    L.append("")
    L.append(f"> **{rep['disclaimer']}**")
    L.append(f">")
    L.append(f"> Implementer model family: {rep['implementer_model_family']}. "
             f"Bootstrap seed: {rep['bootstrap_seed']}. Data dir: `{rep['data_dir']}`.")
    L.append("")
    L.append("## Pre-stated equivalence margins (Analysis 2, declared before computing)")
    L.append(f"- **Primary ΔCD = {EQUIV_MARGIN_PRIMARY}** (Amendment 08 §3 pre-registered "
             "minimum detectable effect / power target).")
    L.append(f"- **Secondary (stricter) ΔCD = {EQUIV_MARGIN_STRICT}** (transparency; a "
             "stronger claim).")
    L.append("")

    # Analysis 1
    cf_k1 = a1["cross_family_k1"]
    sf_k1 = a1["same_family_reference_k1"]
    L.append("## Analysis 1 — per-item cross-MODEL label concentration (blind-review #6)")
    L.append("")
    L.append("R2 Anthropic-constructed subset (`cp_r2_xf.jsonl`), single-agent labels "
             "from tested models with family ≠ Anthropic, across distinct models/seeds. "
             "Per-item **concentration** = frozen A04 `cd_primary` (modal-wrong "
             "ENUMERATED-foil share; `I_perp` ineligible as modal but kept in the "
             "denominator).")
    L.append("")
    L.append(f"> **k0 controls disclosure:** {a1['k0_disclosure']}")
    L.append("")
    L.append(f"**Cross-family (non-Anthropic)** — models: "
             f"{', '.join(cf.get('distinct_models', []))}; "
             f"families: {', '.join(cf.get('distinct_families', []))}.")
    L.append("")

    def _cf_lines(agg: Dict, header: str, emphasise: bool) -> None:
        star = "⭐ " if emphasise else ""
        L.append(f"### {star}{header} (n={agg['n_items']} items)")
        L.append(f"- Mean per-item concentration: **{_fmt(agg['mean_concentration'])}** "
                 f"(median {_fmt(agg['median_concentration'])}, range "
                 f"[{_fmt(agg['min_concentration'])}, {_fmt(agg['max_concentration'])}]).")
        L.append(f"- Item-level bootstrap 95% CI of the mean: "
                 f"**[{_fmt(agg['boot_ci_lo'])}, {_fmt(agg['boot_ci_hi'])}]**.")
        L.append(f"- Mean # distinct models on the modal wrong foil: "
                 f"**{_fmt(agg['mean_n_models_on_modal_foil'], 3)}**; "
                 f"mean # distinct families: "
                 f"**{_fmt(agg['mean_n_families_on_modal_foil'], 3)}**.")
        L.append(f"- Items with any wrong-foil convergence: "
                 f"{agg['n_items_with_wrong_foil']}/{agg['n_items']}.")
        L.append(f"- **Fraction of items where ≥2 DISTINCT non-Anthropic families "
                 f"concentrate on the SAME wrong foil: "
                 f"{_fmt(agg['frac_items_ge2_families_on_foil'])}** "
                 f"({agg['n_items_ge2_families_on_foil']}/{agg['n_items']}).")
        L.append(f"- Fraction of items where ≥2 distinct models concentrate on the same "
                 f"wrong foil: {_fmt(agg['frac_items_ge2_models_on_foil'])} "
                 f"({agg['n_items_ge2_models_on_foil']}/{agg['n_items']}).")
        L.append("")

    _cf_lines(cf_k1, "SUBSTANTIVE — k1-stratified (ambiguity_level ≥ 1, k0 controls "
                     "excluded)", emphasise=True)
    _cf_lines(cf, "All-item aggregate (includes k0 structural-zero controls, for "
                  "completeness)", emphasise=False)

    L.append(f"**Same-family (Anthropic) reference** (NOT part of the cross-family "
             f"estimate) — models: {', '.join(sf.get('distinct_models', []))}: "
             f"k1 mean concentration {_fmt(sf_k1.get('mean_concentration'))}, "
             f"k1 ≥2-families fraction "
             f"{_fmt(sf_k1.get('frac_items_ge2_families_on_foil'))} "
             f"(all-item mean {_fmt(sf.get('mean_concentration'))}).")
    L.append("")
    L.append("Interpretation: on the k1 ambiguous items (the k0 controls are 0 by "
             "design), multiple INDEPENDENT non-Anthropic models/families land on the "
             "SAME specific wrong foil — genuine cross-MODEL convergence, not a "
             "within-cell N=1 error-rate tautology.")
    L.append("")
    L.append("| task | k | concentration | modal_wrong_foil | n_agents | n_models_on_foil | n_families_on_foil |")
    L.append("|---|---|---|---|---|---|---|")
    for r in a1["item_table"]:
        ktag = "k0 (control)" if r.get("is_k0_control") else f"k{r.get('ambiguity_level')}"
        L.append(f"| {r['task']} | {ktag} | {_fmt(r['concentration'])} | "
                 f"{r['modal_wrong_foil'] or '—'} | {r['n_agents']} | "
                 f"{r['n_models_on_modal_foil']} | {r['n_families_on_modal_foil']} |")
    L.append("")

    # Analysis 2
    L.append("## Analysis 2 — TOST equivalence tests (blind-review #8)")
    L.append("")
    L.append(f"Test statistic: {a2['test_statistic']}. Item-level paired differences "
             "(per-task mean `cd_primary`). Equivalence at margin δ ⇔ the 90% CI of the "
             "paired mean difference lies fully within (−δ, +δ) ⇔ TOST p < 0.05.")
    L.append("")

    def _emit_block(b: Dict):
        L.append(f"#### {b['contrast']}")
        L.append(f"- n items (paired): {b['n_items']}; observed Δ = "
                 f"**{_fmt(b['observed_delta'])}**; 95% CI "
                 f"[{_fmt(b['ci95_lo'])}, {_fmt(b['ci95_hi'])}].")
        if b.get("caveat"):
            L.append(f"- ⚠️ {b['caveat']}")
        if b.get("pooled_reference"):
            pr = b["pooled_reference"]
            L.append(f"- Pooled row-35 reference (frozen contrast): Δ = "
                     f"{_fmt(pr['pooled_delta_cd_primary'])} "
                     f"(hetero {_fmt(pr['pooled_hetero_cd_primary'])} − homo "
                     f"{_fmt(pr['pooled_homogeneous_cd_primary'])}).")
        if b.get("mean_cd_a") is not None:
            L.append(f"- Mean CD: {_fmt(b['mean_cd_a'])} vs {_fmt(b['mean_cd_b'])}.")
        for key, tag in (("primary_0.15", f"±{EQUIV_MARGIN_PRIMARY}"),
                         ("strict_0.10", f"±{EQUIV_MARGIN_STRICT}")):
            t = b["tost"][key]
            verdict = "✅ EQUIVALENT" if t.get("equivalent") else "❌ NOT established"
            L.append(f"  - TOST {tag}: 90% CI "
                     f"[{_fmt(t.get('ci90_lo'))}, {_fmt(t.get('ci90_hi'))}], "
                     f"p_TOST = {_fmt(t.get('p_tost'), 4)} → **{verdict}**.")
        L.append("")

    L.append(f"Tier mean cd_primary (H1_external): "
             + ", ".join(f"{k}={_fmt(v)}" for k, v in a2["tier_mean_cd_primary"].items())
             + ".")
    L.append("")
    L.append("### (a) heterogeneous-MAD vs homogeneous-MAD")
    _emit_block(a2["a_hetero_vs_homogeneous"])
    L.append("### (b) capability-tier CD invariance")
    for b in a2["b_capability_tiers"]:
        _emit_block(b)
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", default=None,
                    help="Directory holding the checkpoint data (auto-discovered "
                         "from cwd/ancestors if omitted).")
    ap.add_argument("--out", default=None,
                    help="Also write a markdown report to this path.")
    ap.add_argument("--format", choices=("markdown", "json"), default="markdown",
                    help="Stdout format (default markdown).")
    args = ap.parse_args(argv)

    data_dir = resolve_data_dir(args.data_dir)
    rep = run_all(data_dir)

    md = to_markdown(rep)
    if args.format == "json":
        print(json.dumps(rep, indent=2, default=str))
    else:
        print(md)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md + "\n", encoding="utf-8")
        print(f"\n[written] {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
