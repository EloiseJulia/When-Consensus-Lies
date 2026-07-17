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

import random

import numpy as np
import pandas as pd

from analysis import contrasts as C
from analysis.cd import CD_VARIANTS
from analysis.contrasts import COLS, compute_cell_cd
from analysis.stats import bootstrap_confidence_intervals, fit_mixed_effects_model

SUPPORTED = "SUPPORTED"
REFUTED = "REFUTED"
INCONCLUSIVE = "INCONCLUSIVE"

#: Model-cluster column (agent-level tidy table). Distinct from ``model_class``
#: (the family) — this is the specific model identifier used for the SECOND
#: clustering dimension in the item- AND model-clustered bootstrap (§8).
MODEL_COL = "model"
#: Constructor-family column: which model family CONSTRUCTED the benchmark item.
#: Drives the R2 cross-family CONSTRUCTION control (prereg §9 R2).
CONSTRUCTOR_COL = "constructor_family"

CI = Tuple[float, float, float]  # (point, lo, hi)
_NAN_CI: CI = (float("nan"), float("nan"), float("nan"))


def _cluster_cols(df: pd.DataFrame) -> list:
    """Two-way (item AND model) clustering columns present in ``df``.

    §8 requires item- and model-clustered inference. Returns ``[task, model]``
    when a ``model`` column is present, else falls back to ``[task]``.
    """
    item = COLS["item"]
    cols = [item] if item in df.columns else []
    if MODEL_COL in df.columns:
        cols.append(MODEL_COL)
    return cols


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


#: Hypothesis -> the CI key(s) whose SIGN(S) carry that hypothesis's effect.
#: H2 is COMPOSITE (prereg §9): a significant regime x model_class interaction
#: AND the matched reasoner-H2 baseline check — BOTH must be sign-robust.
_ROBUST_KEYS = {
    "H1a": "h1a",
    "H1b": "h1b",
    "H2": ["h2_interaction", "h2_reasoner_vs_single"],
    "R1": "r1",
    "R2": "r2",
}


def _sign(x: float) -> Optional[str]:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    if x > 0:
        return "+"
    if x < 0:
        return "-"
    return "0"


def _component_signs(cis_by_variant, key):
    """Per-component sign summary across variants -> (robust_tag, missing, details)."""
    signs = []
    details = []
    missing = False
    for variant, cis in cis_by_variant.items():
        ci = cis.get(key) if cis else None
        s = _sign(ci[0]) if ci is not None else None
        if s is None:
            missing = True
            details.append(f"{variant}:{key}=NA")
        else:
            signs.append(s)
            details.append(f"{variant}:{key}={s}{round(float(ci[0]), 3)}")
    distinct = set(signs)
    if not signs:
        return ("indeterminate", missing, details)
    if len(distinct) == 1:
        return (f"robust:{next(iter(distinct))}", missing, details)
    return ("divergent", missing, details)


def robustness_across_variants(cis_by_variant: Dict[str, Dict[str, CI]]) -> Dict[str, str]:
    """Report robustness across A04 CD variants by SIGN agreement (Amendment 04).

    Robustness is judged from the SIGNED point estimates of each variant's CI
    (agree-in-sign => robust), NOT by comparing verdict LABELS. Two variants can
    return different verdict labels (e.g. SUPPORTED vs INCONCLUSIVE) purely
    because a CI margin crosses zero, yet still agree on the direction of the
    effect — that is robust. Sign DISAGREEMENT (a genuine flip) is the real
    non-robustness and is reported honestly.

    H2 is COMPOSITE (prereg §9): robustness requires BOTH the regime x
    model_class interaction AND the matched reasoner-H2-vs-single baseline
    component to be sign-robust; a sensitivity that flips EITHER component is
    reported divergent (MAJOR D).

    Args:
        cis_by_variant: mapping variant name (e.g. ``"cd_primary"``) -> the
            per-hypothesis CI dict (``{"h1a": (pt, lo, hi), ...}``) as produced
            by :func:`evaluate_from_data` (its ``cis`` field).

    Returns:
        Per-hypothesis robustness:
        ``"robust:<sign>"`` (or ``"robust:<sign>(partial)"`` when some variant
        lacked the estimate); for composite H2 ``"robust:<i_sign>&<b_sign>"``.
        ``"divergent:<details>"`` when any (component's) sign flips.
    """
    if not cis_by_variant:
        return {}
    out: Dict[str, str] = {}
    for hyp, key in _ROBUST_KEYS.items():
        keys = key if isinstance(key, list) else [key]
        comp = [_component_signs(cis_by_variant, k) for k in keys]
        tags = [c[0] for c in comp]
        any_missing = any(c[1] for c in comp)
        all_details = [d for c in comp for d in c[2]]
        if any(t == "divergent" for t in tags):
            out[hyp] = "divergent:" + ",".join(all_details)
        elif all(t.startswith("robust:") for t in tags):
            signs = "&".join(t.split(":", 1)[1] for t in tags)
            out[hyp] = f"robust:{signs}" + ("(partial)" if any_missing else "")
        else:
            out[hyp] = "indeterminate:" + ",".join(all_details)
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
    """H1a aggregation-vs-single delta (reused for the R2 cross-family subset).

    R2 asks whether the H1 aggregation effect SURVIVES benchmark CONSTRUCTION
    by a DIFFERENT model family. The effect itself is the ordinary
    aggregation-vs-single CD delta; R2 evaluates it on the cross-constructed
    subset (see :func:`_r2_construction_ci`).
    """
    return _h1a_metric(cd_col)


def _item_level_cells(df: pd.DataFrame) -> pd.DataFrame:
    """Item-level CD cells with a representative ``model`` id per cell.

    ``compute_cell_cd`` groups by (task, method, model_class, seed) and computes
    CD over the cell's agents (it does NOT split by the specific model, so a
    heterogeneous cell correctly aggregates across models). For the §8 parallel
    item-level model we still need a ``model`` grouping column, so we attach the
    cell's representative model id (the first model in the cell) — enabling the
    frozen ``(1|model)`` random intercept without disturbing the CD values.
    """
    cells = compute_cell_cd(df)
    if cells.empty or MODEL_COL not in df.columns:
        return cells
    keys = [COLS["item"], COLS["method"], COLS["model_class"], COLS["seed"]]
    keys = [k for k in keys if k in df.columns and k in cells.columns]
    if not keys:
        return cells
    rep = df.groupby(_group_key(keys), sort=False)[MODEL_COL].agg(
        lambda s: s.iloc[0]).reset_index()
    return cells.merge(rep, on=keys, how="left")


def _group_key(cols):
    cols = list(cols)
    return cols[0] if len(cols) == 1 else cols


def _frozen_fixed_rhs(cells: pd.DataFrame) -> str:
    """The FROZEN §8 fixed structure ``regime * ambiguity_k * method * model_class``.

    Only factors that actually VARY (>1 level) are included, so a subset with a
    constant factor (e.g. H1-only data has one regime) does not create a
    collinear/degenerate term. ``ambiguity_k`` is kept numeric (continuous), the
    others categorical — matching the frozen model.
    """
    order = [COLS["regime"], COLS["ambiguity_k"], COLS["method"], COLS["model_class"]]
    factors = [c for c in order if c in cells.columns and cells[c].nunique() > 1]
    return " * ".join(factors) if factors else "1"


def _frozen_re_terms(cells: pd.DataFrame) -> str:
    """The FROZEN §8 crossed random intercepts ``(1|task) + (1|model)``.

    Both are retained whenever their columns are present (BLOCKER A: never drop
    the ``(1|task)`` random intercept — task-level covariates k / regime are
    identifiable from BETWEEN-task variation WITH a random intercept, and
    dropping it would treat within-task method/seed/model repetitions as
    independent and understate uncertainty). If the crossed fit does not
    converge, :func:`analysis.stats.fit_mixed_effects_model` degrades through its
    LABELED fallback chain (never silently dropping the task grouping).
    """
    terms = []
    if COLS["item"] in cells.columns:
        terms.append(f"(1|{COLS['item']})")
    if MODEL_COL in cells.columns:
        terms.append(f"(1|{MODEL_COL})")
    return (" + " + " + ".join(terms)) if terms else ""


def _h1b_coef_ci(df: pd.DataFrame, cd_col: str) -> CI:
    """H1b: the AMBIGUITY_K coefficient CI from the FROZEN §8 item-level model.

    Fits the pre-registered parallel item-level convergent-delusion model
    ``<cd> ~ regime * ambiguity_k * method * model_class + (1|task) + (1|model)``
    and returns the CI of the ``ambiguity_k`` coefficient (H1b SUPPORTED iff it
    is > 0 with the CI excluding 0). Both random intercepts are retained; if the
    crossed fit does not converge the LABELED fallback chain applies (BLOCKER A).
    """
    cells = _item_level_cells(df)
    if cells.empty or cd_col not in cells.columns:
        return _NAN_CI
    k_col = COLS["ambiguity_k"]
    if k_col not in cells.columns or cells[k_col].nunique() < 2:
        return _NAN_CI
    formula = f"{cd_col} ~ {_frozen_fixed_rhs(cells)}{_frozen_re_terms(cells)}"
    res = fit_mixed_effects_model(cells, formula)
    coef = res["coefficients"].get(k_col)
    ci = res["confidence_intervals"].get(k_col)
    if coef is None or ci is None:
        return _NAN_CI
    return (float(coef), float(ci[0]), float(ci[1]))


# --------------------------------------------------------------------------- #
# R1 — variant-aware cross-item label-shuffle null, WITHIN each condition cell.
# --------------------------------------------------------------------------- #

def _cross_item_shuffle_cd(items_labels, target, cd_fn, n_perm: int = 200,
                           seed: int = 13) -> float:
    """Variant-aware cross-item reshuffle null (mirrors harness.label_shuffle_null).

    Identical algorithm to :func:`harness.nulls.label_shuffle_null` (pool all
    labels of a condition, shuffle, deal back into the original item slot shape,
    average CD over items, mean over permutations) but parameterised by the A04
    CD variant ``cd_fn`` so R1 can be evaluated on ``cd_primary`` (or any
    sensitivity). When ``cd_fn`` is ``cd_sensitivity_frozen`` and the seed is the
    same, this returns EXACTLY ``label_shuffle_null`` (proven by test).
    """
    if not items_labels:
        return 0.0
    item_sizes = [len(it) for it in items_labels]
    n_items = len(item_sizes)
    pool = []
    for it in items_labels:
        pool.extend(it)
    rng = random.Random(seed)
    total = 0.0
    for _ in range(n_perm):
        shuffled = pool[:]
        rng.shuffle(shuffled)
        offset = 0
        s = 0.0
        for size in item_sizes:
            s += cd_fn(shuffled[offset:offset + size], target)
            offset += size
        total += s / n_items
    return total / n_perm


def _r1_metric(cd_col: str, n_perm: int = 200, seed: int = 13
               ) -> Callable[[pd.DataFrame], float]:
    """R1 metric: (CD_real - CD_shuffled), variant-aware, per CONDITION cell.

    ``harness.nulls`` requires the shuffle null to be computed over items of ONE
    condition (regime x method x model x ambiguity). We therefore compute the
    real vs shuffled CD WITHIN each such cell using the requested A04 variant,
    then combine cells weighted by their item count (a global pool would mix
    conditions and violate the null's boundary).
    """
    item_col = COLS["item"]
    label_col = COLS["label"]
    target_col = COLS["target"]
    cd_fn = CD_VARIANTS[cd_col]

    cell_key_cols = [COLS["regime"], COLS["method"], MODEL_COL, COLS["ambiguity_k"]]

    def metric(df: pd.DataFrame) -> float:
        if df.empty:
            return float("nan")
        keys = [c for c in cell_key_cols if c in df.columns]
        groups = df.groupby(keys, dropna=False, sort=False) if keys else [((), df)]
        acc = 0.0
        total_w = 0
        for _, cell in groups:
            items_labels = [list(g[label_col]) for _, g in cell.groupby(item_col, sort=False)]
            if not items_labels:
                continue
            target = cell[target_col].iloc[0]
            cd_real = float(np.mean([cd_fn(lab, target) for lab in items_labels]))
            cd0 = _cross_item_shuffle_cd(items_labels, target, cd_fn, n_perm=n_perm, seed=seed)
            w = len(items_labels)
            acc += w * (cd_real - cd0)
            total_w += w
        if total_w == 0:
            return float("nan")
        return acc / total_w

    return metric


def evaluate_from_data(
    df: pd.DataFrame,
    cd_col: str = "cd_primary",
    reasoning_model_class: str = "reasoning",
    n_bootstrap: int = 500,
    seed: int = 7,
    r1_n_perm: int = 200,
    tested_family_col: str = "model_family",
    model_family_map: Optional[Dict[str, str]] = None,
) -> Dict[str, object]:
    """Compute all §9 verdicts from a tidy agent-level table (one CD variant).

    Wiring per the frozen prereg + Amendment 04:

    - H1a: aggregation-vs-single CD delta, item- AND model-clustered bootstrap.
    - H1b: the AMBIGUITY_K coefficient CI from the FROZEN §8 item-level model
      ``<cd> ~ regime*ambiguity_k*method*model_class + (1|task) + (1|model)``.
    - H2:  the regime x model_class INTERACTION coefficient CI from that same
      frozen §8 model, plus the MATCHED H2-reasoning aggregation-vs-single
      contrast.
    - R1:  variant-aware cross-item shuffle null computed WITHIN each condition
      cell, item- AND model-clustered bootstrap.
    - R2:  the H1 aggregation-vs-single effect on the RELATIONALLY cross-family
      constructed observations (``constructor_family`` != the tested model's
      family), item- AND model-clustered.

    Args:
        tested_family_col: column naming the tested model's FAMILY (for R2's
            relational cross-family test). If absent, ``model_family_map`` maps
            the ``model`` id -> family.
        model_family_map: optional ``{model_id: family}`` fallback for R2.

    Returns:
        Dict with ``verdicts`` (per-hypothesis), ``cis`` (the computed CIs), and
        ``cd_variant``.
    """
    regime_col = COLS["regime"]
    h1 = df[df[regime_col] == "H1_external"] if regime_col in df.columns else df

    cis: Dict[str, CI] = {}
    cis["h1a"] = bootstrap_confidence_intervals(
        _h1a_metric(cd_col), h1, n_bootstrap=n_bootstrap,
        cluster=_cluster_cols(h1), seed=seed)
    cis["h1b"] = _h1b_coef_ci(h1, cd_col)
    cis["r2"] = _r2_construction_ci(h1, cd_col, n_bootstrap, seed,
                                    tested_family_col, model_family_map)
    cis["r1"] = bootstrap_confidence_intervals(
        _r1_metric(cd_col, n_perm=r1_n_perm), h1,
        n_bootstrap=max(80, n_bootstrap // 5),
        cluster=_cluster_cols(h1), seed=seed)

    cis["h2_interaction"] = _h2_interaction_ci(df, cd_col, reasoning_model_class)
    cis["h2_reasoner_vs_single"] = _h2_reasoner_vs_single_ci(
        df, cd_col, reasoning_model_class, n_bootstrap, seed)

    verdicts = evaluate_all(cis)
    return {"verdicts": verdicts, "cis": cis, "cd_variant": cd_col}


def _tested_family(df: pd.DataFrame, tested_family_col: str,
                   model_family_map: Optional[Dict[str, str]]) -> Optional[pd.Series]:
    """Per-observation tested-model FAMILY (for R2's relational cross-family test)."""
    if tested_family_col in df.columns:
        return df[tested_family_col]
    if model_family_map is not None and MODEL_COL in df.columns:
        return df[MODEL_COL].map(model_family_map)
    return None


def _r2_construction_ci(df, cd_col, n_bootstrap, seed,
                        tested_family_col, model_family_map) -> CI:
    """R2: aggregation-vs-single CD effect on RELATIONALLY cross-family items.

    R2 is the cross-family CONSTRUCTION control: an observation is cross-family
    constructed iff its ``constructor_family`` differs from the TESTED model's
    family (a relational comparison, NOT a "non-modal constructor" heuristic —
    if every tested model is family A and every item is constructed by family B,
    then EVERY observation is cross-family). R2 is SUPPORTED iff the
    aggregation-vs-single effect on that cross-family subset has a CI excluding 0
    and positive (the H1 effect SURVIVES cross-family construction).
    """
    if CONSTRUCTOR_COL not in df.columns:
        return _NAN_CI
    fam = _tested_family(df, tested_family_col, model_family_map)
    if fam is None:
        return _NAN_CI
    cross = df[df[CONSTRUCTOR_COL].astype(object) != fam.astype(object)]
    if cross.empty:
        return _NAN_CI
    return bootstrap_confidence_intervals(
        _cross_family_metric(cd_col), cross, n_bootstrap=n_bootstrap,
        cluster=_cluster_cols(cross), seed=seed)


def _h2_interaction_ci(df, cd_col, reasoning_model_class) -> CI:
    """H2 interaction: the regime x model_class coefficient CI from the FROZEN §8 model.

    Fits the pre-registered item-level model
    ``<cd> ~ regime * ambiguity_k * method * model_class + (1|task) + (1|model)``
    (both random intercepts retained; LABELED fallback chain if the crossed fit
    does not converge — BLOCKER A) and returns the CI of the TWO-WAY
    ``regime x model_class`` interaction term (the reasoning x H2_derivable
    coefficient), isolating it from any higher-order interaction that also
    involves method or ambiguity_k.
    """
    cells = _item_level_cells(df)
    regime_col = COLS["regime"]
    mc_col = COLS["model_class"]
    method_col = COLS["method"]
    k_col = COLS["ambiguity_k"]
    if (cells.empty or regime_col not in cells.columns or mc_col not in cells.columns
            or cells[regime_col].nunique() < 2 or cells[mc_col].nunique() < 2):
        return _NAN_CI
    formula = f"{cd_col} ~ {_frozen_fixed_rhs(cells)}{_frozen_re_terms(cells)}"
    res = fit_mixed_effects_model(cells, formula)
    coefs = res["coefficients"]
    cis = res["confidence_intervals"]

    def _is_two_way(name: str) -> bool:
        # A pure regime x model_class interaction: contains both factors, no
        # higher-order factor (method / ambiguity_k), exactly one ':'.
        return (":" in name and name.count(":") == 1
                and "regime[" in name and (mc_col + "[") in name
                and (method_col + "[") not in name and k_col not in name)

    name = None
    for k in coefs:
        if _is_two_way(k) and reasoning_model_class in k:
            name = k
            break
    if name is None:
        for k in coefs:
            if _is_two_way(k):
                name = k
                break
    if name is None or name not in cis:
        return _NAN_CI
    lo, hi = cis[name]
    return (float(coefs[name]), float(lo), float(hi))


def _h2_reasoner_vs_single_ci(df, cd_col, reasoning_model_class, n_bootstrap, seed) -> CI:
    """H2 boundary check: MATCHED H2-reasoning aggregation vs single.

    Both sides are restricted to ``H2_derivable`` reasoning-model cells, and the
    aggregation side EXCLUDES the single method (matched aggregation-vs-single).
    The earlier (buggy) version pooled the single baseline from EVERY
    regime/class, which is unmatched and cancels the contrast to ~0.
    """
    regime_col = COLS["regime"]
    mc_col = COLS["model_class"]
    method_col = COLS["method"]

    frame = df
    if regime_col in frame.columns:
        frame = frame[frame[regime_col] == "H2_derivable"]
    if mc_col in frame.columns:
        frame = frame[frame[mc_col] == reasoning_model_class]
    if frame.empty:
        return _NAN_CI

    def metric(fr: pd.DataFrame) -> float:
        cells = compute_cell_cd(fr)
        if cells.empty or method_col not in cells.columns:
            return float("nan")
        agg = cells[cells[method_col] != C.SINGLE_METHOD]
        single = cells[cells[method_col] == C.SINGLE_METHOD]
        if agg.empty or single.empty:
            return float("nan")
        return float(agg[cd_col].mean() - single[cd_col].mean())

    return bootstrap_confidence_intervals(metric, frame, n_bootstrap=n_bootstrap,
                                          cluster=_cluster_cols(frame), seed=seed)
