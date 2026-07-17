"""FROZEN §9 decision rules — SUPPORTED / REFUTED / INCONCLUSIVE helpers.

Model family of implementer: Claude (Anthropic). Auditor: NON-Claude (GPT).

Implements the frozen prereg §9 support/refute logic for H1a, H1b, H2, R1, R2.
Decisions are COMPUTED from bootstrap confidence intervals / contrasts — never
hard-coded. Per Amendment 04 the rules are evaluated on the PRIMARY CD treatment
and also reported under SENSITIVITY A/B; if PRIMARY and both sensitivities agree
in sign the conclusion is ROBUST, else the divergence is reported honestly.

Two layers:

- Pure CI evaluators (:func:`evaluate_h1a` etc.) take a ``(point, lo, hi)`` CI
  and return a verdict. These are deterministic and golden-testable.
- A data-driven orchestrator (:func:`evaluate_from_data`) computes the required
  CIs from a tidy table via :mod:`analysis.contrasts` + bootstrap and wires R1
  to ``harness.nulls.label_shuffle_null``.
"""

from typing import Callable, Dict, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from analysis import contrasts as C
from analysis.cd import cd_sensitivity_frozen
from analysis.contrasts import COLS, compute_cell_cd
from analysis.stats import bootstrap_confidence_intervals
from harness.nulls import label_shuffle_null

SUPPORTED = "SUPPORTED"
REFUTED = "REFUTED"
INCONCLUSIVE = "INCONCLUSIVE"

CI = Tuple[float, float, float]  # (point, lo, hi)


def _lo_hi(ci: CI) -> Tuple[float, float]:
    _, lo, hi = ci
    return lo, hi


def _excludes_zero(ci: CI) -> bool:
    lo, hi = _lo_hi(ci)
    if np.isnan(lo) or np.isnan(hi):
        return False
    return lo > 0 or hi < 0


def evaluate_h1a(agg_vs_single_ci: CI) -> str:
    """H1a: aggregation does NOT reduce CD vs single.

    SUPPORTED iff the (aggregation - single) CD CI does NOT fall below 0
    (lower bound >= 0). REFUTED iff aggregation significantly REDUCES CD
    (CI entirely < 0). Else INCONCLUSIVE.
    """
    lo, hi = _lo_hi(agg_vs_single_ci)
    if np.isnan(lo) or np.isnan(hi):
        return INCONCLUSIVE
    if lo >= 0:
        return SUPPORTED
    if hi < 0:
        return REFUTED
    return INCONCLUSIVE


def evaluate_h1b(k_coefficient_ci: CI) -> str:
    """H1b: CD increases monotonically with ambiguity k.

    SUPPORTED iff the k coefficient > 0 with CI excluding 0 (lower bound > 0).
    REFUTED iff <= 0 with CI excluding positive (upper bound < 0). Else
    INCONCLUSIVE.
    """
    lo, hi = _lo_hi(k_coefficient_ci)
    if np.isnan(lo) or np.isnan(hi):
        return INCONCLUSIVE
    if lo > 0:
        return SUPPORTED
    if hi < 0:
        return REFUTED
    return INCONCLUSIVE


def evaluate_h2(interaction_ci: CI, reasoner_h2_vs_single_ci: CI) -> str:
    """H2: significant regime x model_class interaction AND reasoner H2 CD not
    significantly above the single-agent baseline.

    SUPPORTED iff the interaction CI excludes 0 AND the reasoner (H2 - single)
    CD CI is NOT significantly positive (lower bound <= 0). REFUTED iff reasoner
    H2 CD is significantly ABOVE single (lower bound > 0), contradicting the
    boundary condition. Else INCONCLUSIVE.
    """
    reasoner_lo, _ = _lo_hi(reasoner_h2_vs_single_ci)
    reasoner_above = (not np.isnan(reasoner_lo)) and reasoner_lo > 0
    if reasoner_above:
        return REFUTED
    if _excludes_zero(interaction_ci):
        return SUPPORTED
    return INCONCLUSIVE


def evaluate_r1(cd_real_minus_shuffled_ci: CI) -> str:
    """R1: (CD_real - CD_shuffled) CI > 0 on H1 items.

    SUPPORTED (pass) iff lower bound > 0. REFUTED iff upper bound < 0. Else
    INCONCLUSIVE.
    """
    lo, hi = _lo_hi(cd_real_minus_shuffled_ci)
    if np.isnan(lo) or np.isnan(hi):
        return INCONCLUSIVE
    if lo > 0:
        return SUPPORTED
    if hi < 0:
        return REFUTED
    return INCONCLUSIVE


def evaluate_r2(cross_family_effect_ci: CI) -> str:
    """R2: cross-family H1 effect CI excludes 0 and is positive.

    SUPPORTED (pass) iff lower bound > 0. REFUTED iff upper bound < 0. Else
    INCONCLUSIVE.
    """
    lo, hi = _lo_hi(cross_family_effect_ci)
    if np.isnan(lo) or np.isnan(hi):
        return INCONCLUSIVE
    if lo > 0:
        return SUPPORTED
    if hi < 0:
        return REFUTED
    return INCONCLUSIVE


def evaluate_all(cis: Dict[str, CI]) -> Dict[str, str]:
    """Evaluate every §9 rule from a dict of named CIs.

    Expected keys (missing keys -> INCONCLUSIVE for that rule):
        ``h1a`` (agg-vs-single), ``h1b`` (k coef), ``h2_interaction``,
        ``h2_reasoner_vs_single``, ``r1`` (real-shuffled), ``r2`` (cross-family).
    """
    nan_ci: CI = (float("nan"), float("nan"), float("nan"))
    return {
        "H1a": evaluate_h1a(cis.get("h1a", nan_ci)),
        "H1b": evaluate_h1b(cis.get("h1b", nan_ci)),
        "H2": evaluate_h2(cis.get("h2_interaction", nan_ci),
                          cis.get("h2_reasoner_vs_single", nan_ci)),
        "R1": evaluate_r1(cis.get("r1", nan_ci)),
        "R2": evaluate_r2(cis.get("r2", nan_ci)),
    }


def robustness_across_variants(verdicts_by_variant: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    """Report robustness across A04 CD variants (agree-in-sign -> robust).

    Args:
        verdicts_by_variant: mapping variant name (e.g. ``"cd_primary"``) ->
            per-hypothesis verdict dict (from :func:`evaluate_all`).

    Returns:
        Per-hypothesis robustness: ``"robust:<VERDICT>"`` when all variants agree,
        else ``"divergent:<primary_verdict>|<others...>"`` reporting the spread.
    """
    if not verdicts_by_variant:
        return {}
    hypotheses = set()
    for v in verdicts_by_variant.values():
        hypotheses.update(v.keys())

    primary = verdicts_by_variant.get("cd_primary", {})
    out: Dict[str, str] = {}
    for h in sorted(hypotheses):
        verdicts = {name: v.get(h, INCONCLUSIVE) for name, v in verdicts_by_variant.items()}
        unique = set(verdicts.values())
        if len(unique) == 1:
            out[h] = f"robust:{next(iter(unique))}"
        else:
            prim = primary.get(h, INCONCLUSIVE)
            others = ",".join(f"{n}={x}" for n, x in sorted(verdicts.items()))
            out[h] = f"divergent:{prim}|{others}"
    return out


# --------------------------------------------------------------------------- #
# Data-driven orchestrator (computes the CIs from a tidy table + bootstrap).
# --------------------------------------------------------------------------- #

def _cd_variant_fn(cd_col: str) -> Callable[[list, str], float]:
    from analysis.cd import CD_VARIANTS
    return CD_VARIANTS[cd_col]


def _mean_cd_of_subset(df: pd.DataFrame, cd_col: str) -> float:
    cells = compute_cell_cd(df)
    if cells.empty:
        return float("nan")
    return float(cells[cd_col].mean())


def _h1a_metric(cd_col: str) -> Callable[[pd.DataFrame], float]:
    method_col = COLS["method"]

    def metric(df: pd.DataFrame) -> float:
        cells = compute_cell_cd(df)
        if cells.empty:
            return float("nan")
        single = cells[cells[method_col] == C.SINGLE_METHOD]
        agg = cells[cells[method_col] != C.SINGLE_METHOD]
        if single.empty or agg.empty:
            return float("nan")
        return float(agg[cd_col].mean() - single[cd_col].mean())

    return metric


def _cross_family_metric(cd_col: str) -> Callable[[pd.DataFrame], float]:
    method_col = COLS["method"]

    def metric(df: pd.DataFrame) -> float:
        cells = compute_cell_cd(df)
        if cells.empty:
            return float("nan")
        hetero = cells[cells[method_col] == C.HETEROGENEOUS_METHOD]
        single = cells[cells[method_col] == C.SINGLE_METHOD]
        if hetero.empty or single.empty:
            return float("nan")
        return float(hetero[cd_col].mean() - single[cd_col].mean())

    return metric


def _h1b_slope_metric(cd_col: str) -> Callable[[pd.DataFrame], float]:
    k_col = COLS["ambiguity_k"]

    def metric(df: pd.DataFrame) -> float:
        cells = compute_cell_cd(df)
        if cells.empty or k_col not in cells.columns:
            return float("nan")
        sub = cells[[k_col, cd_col]].dropna()
        if sub[k_col].nunique() < 2:
            return float("nan")
        slope = np.polyfit(sub[k_col].astype(float), sub[cd_col].astype(float), 1)[0]
        return float(slope)

    return metric


def _r1_metric(n_perm: int = 200) -> Callable[[pd.DataFrame], float]:
    item_col = COLS["item"]
    label_col = COLS["label"]
    target_col = COLS["target"]

    def metric(df: pd.DataFrame) -> float:
        if df.empty:
            return float("nan")
        items_labels = []
        cd_reals = []
        target = df[target_col].iloc[0]
        for _, group in df.groupby(item_col, sort=False):
            labels = list(group[label_col])
            items_labels.append(labels)
            cd_reals.append(cd_sensitivity_frozen(labels, target))
        if not items_labels:
            return float("nan")
        cd_real = float(np.mean(cd_reals))
        cd0 = label_shuffle_null(items_labels, target, n_perm=n_perm, seed=13)
        return cd_real - cd0

    return metric


def evaluate_from_data(
    df: pd.DataFrame,
    cd_col: str = "cd_primary",
    reasoning_model_class: str = "reasoning",
    n_bootstrap: int = 500,
    seed: int = 7,
    r1_n_perm: int = 200,
) -> Dict[str, object]:
    """Compute all §9 verdicts from a tidy agent-level table (one CD variant).

    Wires the contrasts + cluster bootstrap (clustered by ``task``) and R1 to
    ``harness.nulls.label_shuffle_null``. H1a/H1b/R1/R2 are computed on
    ``H1_external`` items; the H2 interaction is computed from the cross-regime
    CD gap by model_class.

    Returns:
        Dict with ``verdicts`` (per-hypothesis), ``cis`` (the computed CIs), and
        ``cd_variant``.
    """
    regime_col = COLS["regime"]
    model_class_col = COLS["model_class"]
    item_col = COLS["item"]

    h1 = df[df[regime_col] == "H1_external"] if regime_col in df.columns else df

    cis: Dict[str, CI] = {}
    cis["h1a"] = bootstrap_confidence_intervals(
        _h1a_metric(cd_col), h1, n_bootstrap=n_bootstrap, cluster=item_col, seed=seed)
    cis["h1b"] = bootstrap_confidence_intervals(
        _h1b_slope_metric(cd_col), h1, n_bootstrap=n_bootstrap, cluster=item_col, seed=seed)
    cis["r2"] = bootstrap_confidence_intervals(
        _cross_family_metric(cd_col), h1, n_bootstrap=n_bootstrap, cluster=item_col, seed=seed)
    cis["r1"] = bootstrap_confidence_intervals(
        _r1_metric(n_perm=r1_n_perm), h1, n_bootstrap=max(100, n_bootstrap // 5),
        cluster=item_col, seed=seed)

    # H2 interaction: (H1 - H2) CD gap for reasoning vs non-reasoning model_class.
    cis["h2_interaction"] = _h2_interaction_ci(df, cd_col, reasoning_model_class,
                                               n_bootstrap, seed)
    cis["h2_reasoner_vs_single"] = _h2_reasoner_vs_single_ci(
        df, cd_col, reasoning_model_class, n_bootstrap, seed)

    verdicts = evaluate_all(cis)
    return {"verdicts": verdicts, "cis": cis, "cd_variant": cd_col}


def _h2_interaction_ci(df, cd_col, reasoning_model_class, n_bootstrap, seed) -> CI:
    regime_col = COLS["regime"]
    model_class_col = COLS["model_class"]
    item_col = COLS["item"]

    def metric(frame: pd.DataFrame) -> float:
        cells = compute_cell_cd(frame)
        if cells.empty or regime_col not in cells.columns or model_class_col not in cells.columns:
            return float("nan")

        def gap(mc_mask) -> float:
            sub = cells[mc_mask]
            h1 = sub[sub[regime_col] == "H1_external"]
            h2 = sub[sub[regime_col] == "H2_derivable"]
            if h1.empty or h2.empty:
                return float("nan")
            return float(h1[cd_col].mean() - h2[cd_col].mean())

        reasoning = gap(cells[model_class_col] == reasoning_model_class)
        other = gap(cells[model_class_col] != reasoning_model_class)
        if np.isnan(reasoning) or np.isnan(other):
            return float("nan")
        # Interaction: reasoners attenuate MORE in H2 -> larger H1-H2 gap.
        return reasoning - other

    return bootstrap_confidence_intervals(metric, df, n_bootstrap=n_bootstrap,
                                          cluster=item_col, seed=seed)


def _h2_reasoner_vs_single_ci(df, cd_col, reasoning_model_class, n_bootstrap, seed) -> CI:
    regime_col = COLS["regime"]
    model_class_col = COLS["model_class"]
    method_col = COLS["method"]
    item_col = COLS["item"]

    def metric(frame: pd.DataFrame) -> float:
        cells = compute_cell_cd(frame)
        if cells.empty or regime_col not in cells.columns:
            return float("nan")
        h2 = cells[cells[regime_col] == "H2_derivable"]
        if model_class_col in h2.columns:
            h2 = h2[h2[model_class_col] == reasoning_model_class]
        reasoner_cd = h2[cd_col].mean()
        single = cells[cells[method_col] == C.SINGLE_METHOD] if method_col in cells.columns else cells
        single_cd = single[cd_col].mean()
        if np.isnan(reasoner_cd) or np.isnan(single_cd):
            return float("nan")
        return float(reasoner_cd - single_cd)

    return bootstrap_confidence_intervals(metric, df, n_bootstrap=n_bootstrap,
                                          cluster=item_col, seed=seed)
