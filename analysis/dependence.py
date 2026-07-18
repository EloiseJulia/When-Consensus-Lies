"""Amendment-09 P1 secondary analysis: deterministic dependence estimators.

# Implementer model family: Claude (Anthropic) — A09 additive secondary.
# Auditor MUST use a different model family (GPT or Gemini) per Law 6.

These are PRE-REGISTERED SECONDARY analyses (Amendment 09 / A09). They SUPPORT
and are reported alongside the primary ``cd_primary`` metric; they do NOT
replace it.

The frozen cell key ``(task × method × model_class × seed)`` from
``analysis.decision_rules._item_level_cells`` / ``analysis.contrasts.compute_cell_cd``
is respected throughout. The column ``model`` (raw model_id) is also required for
the independence counterfactual per-model marginal.

Five estimators (all pure, deterministic, no LLM):

1. ``pairwise_wrong_agreement`` — fraction of wrong-agent pairs choosing the
   SAME wrong enumerated label (I_perp excluded; 0/0 → NaN).

2. ``kappa`` — chance-corrected agreement (Fleiss κ for n≥2 raters on one item,
   Cohen κ dispatch for exactly 2 raters). Measures over the item's
   interpretation set.

3. ``icc_wrong_indicator`` — one-way random-effects ICC of the wrong-indicator
   (0/1) across agents WITHIN cells, estimated across multiple cells (required).
   Formula: ICC = (MS_B − MS_W) / (MS_B + (n₀ − 1)·MS_W), where n₀ is the
   harmonic mean of per-cell agent counts (Shrout & Fleiss 1979, ICC(1,1)).

4. ``effective_ensemble_size`` — n_eff = n / (1 + (n−1)·ρ̄), directly
   operationalising the §2.4 claim that ρ→1 ⇒ n_eff→1 (fake redundancy).

5. ``independence_counterfactual`` — resample each agent's label independently
   from ITS OWN model-marginal empirical distribution (across all items), then
   recompute mean ``cd_primary`` and return ``observed − independent`` with a
   bootstrap 95% CI. Distinct from R1b (uniform-over-interpretations): P1
   preserves each model's marginal accuracy.

``compute_dependence_table(tidy, ...)`` aggregates all estimators per-cell and
returns a per-cell + regime-aggregated summary DataFrame.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from analysis.cd import cd_primary
from analysis.contrasts import COLS

# ── Column shorthands ──────────────────────────────────────────────────────────
_ITEM = COLS["item"]           # "task"
_METHOD = COLS["method"]       # "method"
_MODEL_CLASS = COLS["model_class"]  # "model_class"
_SEED = COLS["seed"]           # "seed"
_LABEL = COLS["label"]         # "label"
_TARGET = COLS["target"]       # "target"
_REGIME = COLS["regime"]       # "regime"
_MODEL = "model"               # raw model_id (extra column from io.py)

#: I_perp sentinel — ineligible as an enumerated wrong answer.
IPERP = "I_perp"

# ── Cell key (frozen — matches decision_rules._item_level_cells) ───────────────
_CELL_COLS: List[str] = [_ITEM, _METHOD, _MODEL_CLASS, _SEED]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Pairwise wrong-agreement (per-cell)
# ─────────────────────────────────────────────────────────────────────────────

def pairwise_wrong_agreement(labels: List[str], target: str) -> float:
    """Fraction of wrong-agent PAIRS choosing the SAME wrong enumerated label.

    Among unordered pairs (i, j) where BOTH agents are wrong
    (label ≠ target AND label ≠ I_perp), the fraction where label_i == label_j.

    Returns NaN when fewer than 2 wrong agents are present (undefined).

    Args:
        labels: All agent labels in one cell.
        target: Correct target label for this item.

    Returns:
        Float in [0, 1], or NaN when fewer than 2 wrong agents.
    """
    wrong = [lbl for lbl in labels if lbl != target and lbl != IPERP]
    if len(wrong) < 2:
        return float("nan")
    n_pairs = 0
    agreements = 0
    for i in range(len(wrong)):
        for j in range(i + 1, len(wrong)):
            n_pairs += 1
            if wrong[i] == wrong[j]:
                agreements += 1
    return agreements / n_pairs if n_pairs > 0 else float("nan")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Chance-corrected agreement — Fleiss κ (per-cell, n≥2 raters, 1 subject)
# ─────────────────────────────────────────────────────────────────────────────

def fleiss_kappa(labels: List[str], categories: Sequence[str]) -> float:
    """Fleiss κ for n raters assigning a single subject to one of the categories.

    Estimand: chance-corrected agreement among the n agents in this cell over
    the item's interpretation set. Uses the per-cell proportions as the marginal
    for chance correction (appropriate when estimating cell-level dependence).

    Formula:
        P_o = Σ_k n_k(n_k−1) / (n(n−1))      [observed agreement fraction]
        P_e = Σ_k (n_k/n)²                    [expected-by-chance fraction]
        κ   = (P_o − P_e) / (1 − P_e)

    Returns NaN when n < 2, fewer than 2 categories are present, or P_e = 1.

    Args:
        labels: Agent labels in this cell (length n).
        categories: The item's full interpretation set (used to bound P_e).

    Returns:
        Float in [−1, 1], or NaN for degenerate inputs.
    """
    n = len(labels)
    if n < 2:
        return float("nan")
    cats = list(categories)
    if len(cats) < 2:
        return float("nan")
    counts = {c: 0 for c in cats}
    for lbl in labels:
        if lbl in counts:
            counts[lbl] += 1
    n_k = list(counts.values())
    p_o = sum(nk * (nk - 1) for nk in n_k) / (n * (n - 1))
    p_e = sum((nk / n) ** 2 for nk in n_k)
    if abs(1.0 - p_e) < 1e-12:
        # P_e = 1 means all raters agree on one category → perfect agreement by convention.
        return 1.0 if abs(p_o - 1.0) < 1e-12 else float("nan")
    return (p_o - p_e) / (1.0 - p_e)


def cohen_kappa(labels: List[str], categories: Sequence[str]) -> float:
    """Cohen κ for exactly 2 raters on one item.

    Dispatches to :func:`fleiss_kappa` with the first two labels. For n=2,
    Fleiss κ and Cohen κ are equivalent (both use per-cell marginals for P_e).

    Returns NaN when fewer than 2 labels are provided.
    """
    if len(labels) < 2:
        return float("nan")
    return fleiss_kappa(labels[:2], categories)


def kappa(labels: List[str], categories: Sequence[str]) -> float:
    """Dispatch to Cohen κ (n=2) or Fleiss κ (n≥3).

    Convenience wrapper that selects the appropriate kappa variant based on the
    number of agents in the cell.

    Args:
        labels: Agent labels in this cell.
        categories: Item interpretation set.

    Returns:
        Float κ in [−1, 1], or NaN for degenerate inputs.
    """
    if len(labels) == 2:
        return cohen_kappa(labels, categories)
    return fleiss_kappa(labels, categories)


def fleiss_kappa_multi(
    ratings: List[List[str]],
    categories: Sequence[str],
) -> float:
    """Multi-subject Fleiss' κ: N items as subjects, agents as raters.

    Estimand: chance-corrected inter-rater agreement across N items, where
    marginal category probabilities are estimated from ALL items pooled (not
    per-item). This avoids the per-cell degeneracy of estimating P_e from a
    single subject's label counts (which algebraically forces κ = −1/(n−1)
    for any non-unanimous single-item cell).

    Grouping: call with all items belonging to the SAME experimental group
    (e.g. same method × model_class × seed), so each item is one subject and
    each agent column is one rater.

    Formula (Fleiss 1971, multi-subject):
        n_ij  = count of agents assigning category j to item i
        p_j   = Σ_i n_ij / Σ_i n_i          (pooled marginal across all items)
        P_i   = Σ_j n_ij(n_ij−1) / [n_i(n_i−1)]  (per-item observed agreement)
        P̄_o  = (1/N) Σ_i P_i                (mean observed agreement)
        P̄_e  = Σ_j p_j²                     (expected agreement under independence)
        κ     = (P̄_o − P̄_e) / (1 − P̄_e)

    Returns NaN when valid N (items with ≥2 raters) < 2, fewer than 2
    categories are present, or P̄_e = 1.

    Args:
        ratings: List of per-item label lists. ``ratings[i]`` is the list of
            all agent labels for item i (i.e. one cell in the item × agents
            matrix, with items as subjects).
        categories: The full interpretation set (bounds the denominator).

    Returns:
        Float κ in (−∞, 1], or NaN for degenerate inputs.
    """
    cats = list(categories)
    k = len(cats)
    if k < 2:
        return float("nan")
    cat_idx = {c: j for j, c in enumerate(cats)}

    total_ratings = 0
    cat_totals = [0] * k
    P_o_sum = 0.0
    valid_N = 0

    for row in ratings:
        ni = len(row)
        if ni < 2:
            continue
        valid_N += 1
        n_ij = [0] * k
        for lbl in row:
            j = cat_idx.get(lbl, -1)
            if j >= 0:
                n_ij[j] += 1
        for j in range(k):
            cat_totals[j] += n_ij[j]
        total_ratings += ni
        P_i = sum(nij * (nij - 1) for nij in n_ij) / (ni * (ni - 1))
        P_o_sum += P_i

    if valid_N < 2 or total_ratings == 0:
        return float("nan")

    P_o = P_o_sum / valid_N
    p_j = [c / total_ratings for c in cat_totals]
    P_e = sum(pj ** 2 for pj in p_j)

    if abs(1.0 - P_e) < 1e-12:
        # All raters agree on the same category across all items.
        return 1.0 if abs(P_o - 1.0) < 1e-12 else float("nan")

    return (P_o - P_e) / (1.0 - P_e)


# ─────────────────────────────────────────────────────────────────────────────
# 3. ICC(1) of wrong-indicator across cells
# ─────────────────────────────────────────────────────────────────────────────

def icc_wrong_indicator(
    cell_labels: List[List[str]],
    target: str,
) -> float:
    """One-way random-effects ICC(1,1) of the wrong-indicator across cells.

    Estimand: the intraclass correlation of the binary wrong-indicator
    (w_ic = 1 if label ≠ target AND label ≠ I_perp, else 0) across agents
    within cells. A high ICC means agents within the same cell systematically
    share wrongness (correlated failure); a low ICC means individual agents'
    wrongness is nearly independent.

    Formula (Shrout & Fleiss 1979, ICC(1,1) one-way random effects):

        n₀  = harmonic mean of per-cell agent counts
        MS_B = SS_between / (N − 1)     [between-cell variance]
        MS_W = SS_within  / Σ(n_i − 1) [within-cell variance]
        ICC  = (MS_B − MS_W) / (MS_B + (n₀ − 1) · MS_W)

    Note: ICC is estimated across cells; computing it on a single cell is
    undefined (returns NaN). A minimum of 2 cells with ≥2 agents each is needed.

    Args:
        cell_labels: List of per-cell label lists. Each inner list is the
            labels of all agents in one cell (item × method × model_class × seed).
        target: Correct target label for ALL cells (all items in one group).
            For multi-item tables, call :func:`compute_dependence_table` which
            passes per-item targets correctly.

    Returns:
        Float ICC in (−∞, 1], or NaN when the data is degenerate.
    """
    # Build wrong-indicator matrix (ragged: different cell sizes allowed)
    indicators: List[List[float]] = []
    for cell in cell_labels:
        row = [1.0 if (lbl != target and lbl != IPERP) else 0.0 for lbl in cell]
        if len(row) >= 1:
            indicators.append(row)

    N = len(indicators)
    if N < 2:
        return float("nan")

    n_i = [len(row) for row in indicators]
    if all(ni < 2 for ni in n_i):
        return float("nan")

    # Grand mean
    all_vals = [v for row in indicators for v in row]
    grand_mean = sum(all_vals) / len(all_vals)

    # Cell means
    cell_means = [sum(row) / len(row) for row in indicators]

    # SS_between and SS_within
    ss_between = sum(n_i[i] * (cell_means[i] - grand_mean) ** 2 for i in range(N))
    ss_within = sum(
        (v - cell_means[i]) ** 2
        for i, row in enumerate(indicators)
        for v in row
    )

    df_between = N - 1
    df_within = sum(ni - 1 for ni in n_i)

    if df_between == 0 or df_within == 0:
        return float("nan")

    ms_between = ss_between / df_between
    ms_within = ss_within / df_within if df_within > 0 else float("nan")

    if math.isnan(ms_within):
        return float("nan")

    # Harmonic mean of group sizes
    n0 = N / sum(1.0 / ni for ni in n_i if ni > 0)

    denominator = ms_between + (n0 - 1) * ms_within
    if abs(denominator) < 1e-15:
        return float("nan")

    return (ms_between - ms_within) / denominator


# ─────────────────────────────────────────────────────────────────────────────
# 4. Effective ensemble size
# ─────────────────────────────────────────────────────────────────────────────

def effective_ensemble_size(n: int, rho_bar: float) -> float:
    """Effective ensemble size given mean pairwise wrong-indicator correlation.

    Formula:  n_eff = n / (1 + (n − 1) · ρ̄)

    Operationalises the §2.4 claim: when ρ̄ → 1 (fully correlated agents)
    n_eff → 1, i.e. the ensemble provides no more information than a single
    agent (fake redundancy). When ρ̄ → 0 (independent agents) n_eff → n.

    Args:
        n: Number of agents in the ensemble cell.
        rho_bar: Estimated mean pairwise correlation of the wrong-indicator
            (typically the ICC value from :func:`icc_wrong_indicator`).

    Returns:
        Float n_eff ≥ 1. Returns n unchanged for n ≤ 1 (degenerate).
    """
    if n <= 1:
        return float(n)
    return n / (1.0 + (n - 1) * rho_bar)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Independence-calibrated counterfactual
# ─────────────────────────────────────────────────────────────────────────────

def _model_marginals(tidy: pd.DataFrame) -> Dict[str, List[str]]:
    """Build per-model empirical marginal label distribution.

    Returns a dict: model_id → list of all labels produced by that model across
    all items in ``tidy`` (the empirical marginal to sample from).
    """
    if _MODEL not in tidy.columns:
        return {}
    marginals: Dict[str, List[str]] = {}
    for model_id, group in tidy.groupby(_MODEL, sort=False):
        marginals[str(model_id)] = list(group[_LABEL])
    return marginals


def _resample_labels(
    tidy: pd.DataFrame,
    marginals: Dict[str, List[str]],
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Return a copy of tidy with each agent's label resampled from its model marginal.

    Each agent label is drawn INDEPENDENTLY from ITS OWN model-marginal empirical
    distribution (i.e., a random draw from the list of labels that model produced
    across all items). This preserves per-model marginal accuracy in expectation
    while destroying cross-agent dependence within cells.
    """
    work = tidy.copy()
    if _MODEL not in work.columns:
        return work
    new_labels = list(work[_LABEL])
    for i, (model_id, _) in enumerate(zip(work[_MODEL], work.index)):
        pool = marginals.get(str(model_id))
        if pool:
            idx = int(rng.integers(0, len(pool)))
            new_labels[i] = pool[idx]
    work = work.copy()
    work[_LABEL] = new_labels
    return work


def _mean_cd_primary(tidy: pd.DataFrame) -> float:
    """Compute mean cd_primary over all (item × method × model_class × seed) cells."""
    if tidy.empty:
        return float("nan")
    cell_cols = [c for c in _CELL_COLS if c in tidy.columns]
    carry = [c for c in (_TARGET, _REGIME) if c in tidy.columns]
    group_cols = cell_cols + [c for c in carry if c not in cell_cols]
    values: List[float] = []
    for _, group in tidy.groupby(group_cols, dropna=False, sort=False):
        labels = list(group[_LABEL])
        target = str(group[_TARGET].iloc[0]) if _TARGET in group.columns else ""
        values.append(cd_primary(labels, target))
    return float(np.nanmean(values)) if values else float("nan")


def independence_counterfactual(
    tidy: pd.DataFrame,
    *,
    n_bootstrap: int = 500,
    seed: int = 42,
    ci: float = 0.95,
    regime: Optional[str] = None,
) -> Dict[str, float]:
    """Observed CD minus independence-calibrated counterfactual CD (bootstrap CI).

    Resample each agent's label independently from ITS OWN model-marginal
    empirical distribution (across all items), recompute mean ``cd_primary``,
    and return ``observed − independent`` with a bootstrap 95% CI.

    Distinct from R1b (uniform-over-interpretations): P1 preserves each model's
    marginal label distribution (and thus its marginal accuracy).

    The bootstrap draws ``n_bootstrap`` independent realizations of the
    counterfactual label assignment and returns the distribution of
    ``observed − counterfactual_b`` as the CI.

    Args:
        tidy: Agent-level tidy table with columns
            ``task, method, model_class, seed, label, target, model``.
        n_bootstrap: Number of bootstrap replicates (default 500).
        seed: RNG seed for reproducibility.
        ci: Confidence level (default 0.95).
        regime: Optional regime filter (e.g. ``"H1_external"``). When provided,
            only rows with that regime are included in the CD computation; the
            marginals are still estimated from the full table (all regimes).

    Returns:
        Dict with keys:
            ``observed``  — mean cd_primary over cells in the regime subset.
            ``cf_mean``   — mean counterfactual CD over bootstrap replicates.
            ``delta``     — ``observed − cf_mean``.
            ``ci_lo``     — lower bound of the bootstrap CI on the delta.
            ``ci_hi``     — upper bound of the bootstrap CI on the delta.
            ``n_bootstrap`` — actual number of valid bootstrap replicates.
    """
    # Build marginals from the FULL table before any regime filter.
    marginals = _model_marginals(tidy)

    # Regime subset for CD computation.
    subset = tidy
    if regime is not None and _REGIME in tidy.columns:
        subset = tidy[tidy[_REGIME] == regime]

    observed = _mean_cd_primary(subset)

    rng = np.random.default_rng(seed)
    alpha = 1.0 - ci
    lo_pct, hi_pct = 100.0 * (alpha / 2.0), 100.0 * (1.0 - alpha / 2.0)

    deltas: List[float] = []
    for _ in range(n_bootstrap):
        resampled_full = _resample_labels(tidy, marginals, rng)
        # Apply same regime filter to resampled data.
        resampled = resampled_full
        if regime is not None and _REGIME in resampled_full.columns:
            resampled = resampled_full[resampled_full[_REGIME] == regime]
        cf_cd = _mean_cd_primary(resampled)
        if not math.isnan(cf_cd):
            deltas.append(observed - cf_cd)

    if not deltas:
        return {
            "observed": observed,
            "cf_mean": float("nan"),
            "delta": float("nan"),
            "ci_lo": float("nan"),
            "ci_hi": float("nan"),
            "n_bootstrap": 0,
        }

    arr = np.array(deltas, dtype=float)
    cf_mean = float(observed - np.mean(arr))  # cf_mean = observed - mean(delta)
    return {
        "observed": observed,
        "cf_mean": cf_mean,
        "delta": float(np.mean(arr)),
        "ci_lo": float(np.percentile(arr, lo_pct)),
        "ci_hi": float(np.percentile(arr, hi_pct)),
        "n_bootstrap": len(deltas),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. Top-level aggregation: compute_dependence_table
# ─────────────────────────────────────────────────────────────────────────────

def compute_dependence_table(
    tidy: pd.DataFrame,
    *,
    interpretation_sets: Optional[Dict[str, List[str]]] = None,
    n_bootstrap: int = 500,
    seed: int = 42,
) -> Tuple[pd.DataFrame, Dict[str, Dict[str, float]]]:
    """Compute per-cell dependence statistics and regime-aggregated summaries.

    Respects the FROZEN cell key ``(task × method × model_class × seed)`` from
    ``analysis.contrasts.compute_cell_cd``. No new cell key is introduced.

    Per-cell columns returned in the cell-level DataFrame:
        ``task, method, model_class, seed, regime, n_agents,
          pairwise_wrong_agreement, kappa, cd_primary``

    Regime-level summary (second return value) maps
    ``regime → {stat: value}`` for:
        ``icc``, ``n_eff_mean``, ``observed_cd``, ``cf_cd``, ``delta``,
        ``ci_lo``, ``ci_hi``.

    Args:
        tidy: Agent-level tidy table from ``analysis.io.load_runs_tidy``.
            Must include columns: task, method, model_class, seed, label,
            target, model. The ``regime`` column is used for grouping if present.
        interpretation_sets: Optional dict mapping task_id → list of all
            interpretation IDs for that item (needed for kappa denominator).
            When absent, the interpretation set is inferred from the labels
            present in the tidy table for that item.
        n_bootstrap: Bootstrap replicates for the independence counterfactual.
        seed: RNG seed.

    Returns:
        Tuple of:
            - ``cell_df``: per-cell DataFrame with dependence statistics.
            - ``regime_summary``: dict of regime → aggregated statistics.
    """
    if tidy.empty:
        cell_df = pd.DataFrame(columns=[
            _ITEM, _METHOD, _MODEL_CLASS, _SEED, _REGIME, "n_agents",
            "pairwise_wrong_agreement", "kappa", "cd_primary",
        ])
        return cell_df, {}

    cell_cols = [c for c in _CELL_COLS if c in tidy.columns]
    carry = [c for c in (_TARGET, _REGIME) if c in tidy.columns]
    group_cols = cell_cols + [c for c in carry if c not in cell_cols]

    cell_rows: List[Dict] = []
    _cell_labels_list: List[List[str]] = []  # parallel: raw labels per cell (for group kappa)
    _cell_cats_list: List[List[str]] = []    # parallel: categories per cell (for group kappa)
    for key, group in tidy.groupby(group_cols, dropna=False, sort=False):
        if not isinstance(key, tuple):
            key = (key,)
        row: Dict = dict(zip(group_cols, key))
        labels = list(group[_LABEL])
        target = str(group[_TARGET].iloc[0]) if _TARGET in group.columns else ""
        row["n_agents"] = len(labels)

        row["cd_primary"] = cd_primary(labels, target)
        row["pairwise_wrong_agreement"] = pairwise_wrong_agreement(labels, target)

        # Derive or look up interpretation set (used below for group kappa).
        task_id = row.get(_ITEM, "")
        if interpretation_sets and task_id in interpretation_sets:
            cats = interpretation_sets[task_id]
        else:
            # Infer from unique labels present in ALL rows for this item.
            item_rows = tidy[tidy[_ITEM] == task_id] if _ITEM in tidy.columns else group
            cats = sorted(item_rows[_LABEL].dropna().unique().tolist())
        # kappa is filled below at group level (multi-subject Fleiss' κ)
        _cell_labels_list.append(labels)
        _cell_cats_list.append(cats)
        cell_rows.append(row)

    # ── Multi-subject Fleiss' κ per (method × model_class × seed) group ───────
    # Each item in the group is one subject; agents are raters.  Pooling items
    # avoids the single-subject degeneracy (per-cell κ = −1/(n−1) for any
    # non-unanimous cell) and gives a valid cross-item agreement estimate.
    _kappa_key_cols = [c for c in [_METHOD, _MODEL_CLASS, _SEED] if c in tidy.columns]
    _kappa_idx: Dict[tuple, List[int]] = {}
    for _i, _row in enumerate(cell_rows):
        _gk = tuple(_row.get(c) for c in _kappa_key_cols)
        _kappa_idx.setdefault(_gk, []).append(_i)
    for _gk, _idxs in _kappa_idx.items():
        _ratings = [_cell_labels_list[_i] for _i in _idxs]
        _cats_group = sorted({cat for _i in _idxs for cat in _cell_cats_list[_i]})
        _kv = fleiss_kappa_multi(_ratings, _cats_group)
        for _i in _idxs:
            cell_rows[_i]["kappa"] = _kv

    cell_df = pd.DataFrame(cell_rows)

    # ── Regime-aggregated summaries ─────────────────────────────────────────
    regime_summary: Dict[str, Dict[str, float]] = {}
    regimes: List[Optional[str]] = [None]
    if _REGIME in cell_df.columns:
        regimes = sorted(cell_df[_REGIME].dropna().unique().tolist())

    for reg in regimes:
        if reg is not None:
            regime_tidy = tidy[tidy[_REGIME] == reg] if _REGIME in tidy.columns else tidy
            regime_cells = cell_df[cell_df[_REGIME] == reg] if _REGIME in cell_df.columns else cell_df
        else:
            regime_tidy = tidy
            regime_cells = cell_df

        # Per-cell ICC: group by the FROZEN four-column cell key so that distinct
        # (method, model_class, seed) cells are NOT merged into one task cluster.
        # Grouping by task alone would mix cells across methods/seeds, inflating
        # within-cluster variance and deflating ICC.
        if all(c in regime_tidy.columns for c in [_TARGET]):
            _icc_key = [c for c in _CELL_COLS if c in regime_tidy.columns]
            cell_label_groups: List[List[str]] = []
            item_targets: List[str] = []
            for _, ig in regime_tidy.groupby(_icc_key, sort=False):
                cell_label_groups.append(list(ig[_LABEL]))
                item_targets.append(str(ig[_TARGET].iloc[0]))
            # Compute ICC with a shared target only when all items have the same target.
            # For a multi-item scenario, compute ICC per-item and average.
            if len(set(item_targets)) == 1:
                icc_val = icc_wrong_indicator(cell_label_groups, item_targets[0])
            else:
                # Average ICC over per-unique-target groups.
                icc_vals = []
                for t in set(item_targets):
                    idx = [i for i, it in enumerate(item_targets) if it == t]
                    sub = [cell_label_groups[i] for i in idx]
                    icc_vals.append(icc_wrong_indicator(sub, t))
                valid = [v for v in icc_vals if not math.isnan(v)]
                icc_val = float(np.mean(valid)) if valid else float("nan")
        else:
            icc_val = float("nan")

        # n_eff using icc as rho_bar proxy.
        n_agents_mean = (
            float(regime_cells["n_agents"].mean()) if not regime_cells.empty else float("nan")
        )
        n_eff = (
            effective_ensemble_size(round(n_agents_mean), icc_val)
            if not math.isnan(icc_val) and not math.isnan(n_agents_mean)
            else float("nan")
        )

        # Pass the FULL tidy table so that per-model marginals are estimated
        # across the full run (all regimes).  The regime filter is applied
        # inside independence_counterfactual via the ``regime`` argument.
        cf = independence_counterfactual(
            tidy, regime=reg, n_bootstrap=n_bootstrap, seed=seed
        )

        regime_summary[str(reg)] = {
            "icc": icc_val,
            "n_eff_mean": n_eff,
            "observed_cd": cf["observed"],
            "cf_cd": cf["cf_mean"],
            "delta": cf["delta"],
            "ci_lo": cf["ci_lo"],
            "ci_hi": cf["ci_hi"],
        }

    return cell_df, regime_summary
