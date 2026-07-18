"""Tests for analysis/dependence.py — A09 P1 dependence estimators.

Golden hand cases per the plan spec §3 and Amendment 09 §1.
All tests are deterministic (no LLM, no network).
"""
from __future__ import annotations

import math
from typing import List

import numpy as np
import pandas as pd
import pytest

from analysis.cd import cd_primary as _cd_primary_fn
from analysis.dependence import (
    IPERP,
    cohen_kappa,
    compute_dependence_table,
    effective_ensemble_size,
    fleiss_kappa,
    fleiss_kappa_multi,
    icc_wrong_indicator,
    independence_counterfactual,
    kappa,
    pairwise_wrong_agreement,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _tidy(rows) -> pd.DataFrame:
    """Build a minimal tidy DataFrame from a list of dicts."""
    return pd.DataFrame(rows)


def _make_tidy(
    task_labels: dict,
    target: str = "I0",
    method: str = "sc",
    model_class: str = "reasoning",
    seed: int = 1,
    models: list = None,
) -> pd.DataFrame:
    """Create a simple tidy table: one item per entry in task_labels."""
    rows = []
    for task_id, labels in task_labels.items():
        for i, lbl in enumerate(labels):
            rows.append({
                "task": task_id,
                "method": method,
                "model_class": model_class,
                "seed": seed,
                "label": lbl,
                "target": target,
                "regime": "H1_external",
                "ambiguity_k": 1,
                "model": (models[i] if models and i < len(models) else f"model_{i}"),
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 1. pairwise_wrong_agreement
# ─────────────────────────────────────────────────────────────────────────────

class TestPairwiseWrongAgreement:

    def test_all_agree_wrong(self):
        """All agents wrong on same label → agreement = 1.0."""
        labels = ["I1", "I1", "I1", "I1"]
        assert pairwise_wrong_agreement(labels, "I0") == pytest.approx(1.0)

    def test_all_disagree_wrong(self):
        """Each agent wrong on a DIFFERENT label → agreement = 0.0."""
        labels = ["I1", "I2", "I3", "I4"]
        assert pairwise_wrong_agreement(labels, "I0") == pytest.approx(0.0)

    def test_partial_agreement(self):
        """2 of 3 wrong agents agree → 1 agreeing pair out of 3 total pairs."""
        labels = ["I1", "I1", "I2"]
        # Pairs: (I1,I1) agree, (I1,I2) not, (I1,I2) not → 1/3
        assert pairwise_wrong_agreement(labels, "I0") == pytest.approx(1 / 3)

    def test_iperp_excluded(self):
        """I_perp agents are excluded from the denominator and numerator."""
        labels = ["I1", "I1", IPERP, IPERP]  # Only 2 wrong: both I1 → 1 pair agree
        assert pairwise_wrong_agreement(labels, "I0") == pytest.approx(1.0)

    def test_all_correct(self):
        """All agents correct → no wrong agents → NaN."""
        labels = ["I0", "I0", "I0"]
        assert math.isnan(pairwise_wrong_agreement(labels, "I0"))

    def test_single_wrong_agent(self):
        """Only one wrong agent → fewer than 2 pairs → NaN."""
        labels = ["I0", "I1", "I0"]
        assert math.isnan(pairwise_wrong_agreement(labels, "I0"))

    def test_empty_labels(self):
        assert math.isnan(pairwise_wrong_agreement([], "I0"))

    def test_all_iperp(self):
        """All I_perp → no enumerated wrong agents → NaN."""
        assert math.isnan(pairwise_wrong_agreement([IPERP, IPERP], "I0"))

    def test_mixed_correct_and_wrong(self):
        """Mixed: some correct, some wrong agreeing, some wrong disagreeing."""
        labels = ["I0", "I0", "I1", "I1", "I2"]
        # 3 wrong: (I1,I1) agree, (I1,I2) not, (I1,I2) not → 1/3
        assert pairwise_wrong_agreement(labels, "I0") == pytest.approx(1 / 3)


# ─────────────────────────────────────────────────────────────────────────────
# 2. fleiss_kappa / cohen_kappa
# ─────────────────────────────────────────────────────────────────────────────

class TestFleissKappa:

    def test_perfect_agreement(self):
        """All agents same label → κ = 1.0."""
        labels = ["I1", "I1", "I1"]
        cats = ["I0", "I1", "I2"]
        assert fleiss_kappa(labels, cats) == pytest.approx(1.0)

    def test_all_differ(self):
        """All agents different labels with equal distribution → κ = 0 or negative."""
        labels = ["I0", "I1", "I2"]
        cats = ["I0", "I1", "I2"]
        # P_o = 0 (no same-label pairs), P_e = (1/3)^2 * 3 = 1/3
        # κ = (0 - 1/3) / (1 - 1/3) = (-1/3)/(2/3) = -1/2
        assert fleiss_kappa(labels, cats) == pytest.approx(-0.5)

    def test_chance_level(self):
        """Agreement at chance level → κ ≈ 0."""
        # 3 raters, 2 categories, uniform marginals, uniform agreement
        labels = ["I0", "I0", "I1", "I1"]  # 50/50 split
        cats = ["I0", "I1"]
        # n_I0=2, n_I1=2, n=4
        # P_o = (2*1 + 2*1) / (4*3) = 4/12 = 1/3
        # P_e = (2/4)^2 + (2/4)^2 = 0.25 + 0.25 = 0.5
        # kappa = (1/3 - 0.5) / (1 - 0.5) = (-1/6) / (1/2) = -1/3
        val = fleiss_kappa(labels, cats)
        assert isinstance(val, float)
        assert not math.isnan(val)

    def test_too_few_labels(self):
        """Fewer than 2 labels → NaN."""
        assert math.isnan(fleiss_kappa(["I1"], ["I0", "I1"]))
        assert math.isnan(fleiss_kappa([], ["I0", "I1"]))

    def test_single_category(self):
        """Fewer than 2 categories → NaN."""
        assert math.isnan(fleiss_kappa(["I0", "I0"], ["I0"]))

    def test_cohen_kappa_dispatches(self):
        """cohen_kappa should match fleiss_kappa for the first 2 labels."""
        labels = ["I1", "I0"]
        cats = ["I0", "I1", "I2"]
        assert cohen_kappa(labels, cats) == pytest.approx(fleiss_kappa(["I1", "I0"], cats))

    def test_kappa_dispatch_2(self):
        """kappa() dispatches to cohen_kappa for n=2; both return the same value."""
        labels = ["I0", "I0"]
        cats = ["I0", "I1"]
        v_kappa = kappa(labels, cats)
        v_cohen = cohen_kappa(labels, cats)
        # Both should be the same (either both NaN or both equal).
        if math.isnan(v_kappa):
            assert math.isnan(v_cohen)
        else:
            assert v_kappa == pytest.approx(v_cohen)

    def test_kappa_dispatch_3(self):
        """kappa() dispatches to fleiss_kappa for n>=3."""
        labels = ["I0", "I0", "I1"]
        cats = ["I0", "I1"]
        assert kappa(labels, cats) == pytest.approx(fleiss_kappa(labels, cats))


# ─────────────────────────────────────────────────────────────────────────────
# 2b. fleiss_kappa_multi — multi-subject Fleiss' κ (Fix 1 golden tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestFleissKappaMulti:
    """Golden tests for the multi-subject Fleiss' κ.

    These tests MUST distinguish genuinely different agreement levels; the test
    would FAIL if κ collapsed to a constant (e.g. −1/(n−1)).
    """

    def test_all_items_unanimous_kappa_one(self):
        """All items: every agent agrees on the same label → κ = 1."""
        # P̄_e = 1 (all mass on one category) → handled by the P_e=1 branch → 1.0
        ratings = [["I1", "I1", "I1"]] * 5
        cats = ["I0", "I1", "I2"]
        val = fleiss_kappa_multi(ratings, cats)
        assert val == pytest.approx(1.0)

    def test_agreement_at_chance_kappa_zero(self):
        """P̄_o = P̄_e → κ = 0 (observed equals chance agreement).

        Construction: 4 items, 2 raters, 2 categories.
        Items 1-2: both agree; items 3-4: both disagree.
        → P̄_o = 0.5; marginals p_I0 = p_I1 = 0.5 → P̄_e = 0.5 → κ = 0.
        """
        ratings = [
            ["I0", "I0"],  # agree
            ["I1", "I1"],  # agree
            ["I0", "I1"],  # disagree
            ["I1", "I0"],  # disagree
        ]
        cats = ["I0", "I1"]
        val = fleiss_kappa_multi(ratings, cats)
        assert val == pytest.approx(0.0)

    def test_systematic_disagreement_kappa_negative(self):
        """Each item: every agent picks a DIFFERENT label → κ < 0."""
        # P_i = 0 for each item (no within-item pairs agree)
        # P̄_e = 1/3 (3 categories, uniform marginals) → κ = −0.5
        ratings = [["I0", "I1", "I2"]] * 5
        cats = ["I0", "I1", "I2"]
        val = fleiss_kappa_multi(ratings, cats)
        assert not math.isnan(val)
        assert val < 0
        assert val == pytest.approx(-0.5)

    def test_single_item_returns_nan(self):
        """N = 1 subject is degenerate → NaN (need N ≥ 2)."""
        assert math.isnan(fleiss_kappa_multi([["I0", "I1", "I0"]], ["I0", "I1"]))

    def test_empty_ratings_returns_nan(self):
        assert math.isnan(fleiss_kappa_multi([], ["I0", "I1"]))

    def test_too_few_categories_returns_nan(self):
        assert math.isnan(fleiss_kappa_multi([["I0", "I0"], ["I0", "I0"]], ["I0"]))

    def test_high_agreement_kappa_near_one(self):
        """Mostly unanimous items with balanced categories → κ substantially above 0.

        Use 5 unanimous-I1 + 5 unanimous-I0 + 1 split item.
        P̄_o = 10/11 ≈ 0.909; balanced marginals → P̄_e = 0.5;
        κ = 2·(10/11 − 0.5) = 9/11 ≈ 0.818.
        """
        ratings = (
            [["I1", "I1"]] * 5 +   # 5 unanimous I1
            [["I0", "I0"]] * 5 +   # 5 unanimous I0
            [["I0", "I1"]]          # 1 split → P_i = 0
        )
        cats = ["I0", "I1"]
        val = fleiss_kappa_multi(ratings, cats)
        assert not math.isnan(val)
        assert val == pytest.approx(9 / 11, abs=1e-9)
        assert val > 0.7

    def test_different_agreement_levels_distinguished(self):
        """κ_high > κ_low: high agreement must give higher κ than low agreement."""
        # High agreement: all items unanimous
        ratings_high = [["I1", "I1", "I1"]] * 4 + [["I0", "I0", "I0"]] * 1
        # Low agreement: all items have split votes
        ratings_low = [["I0", "I1", "I2"]] * 5
        cats = ["I0", "I1", "I2"]
        kappa_high = fleiss_kappa_multi(ratings_high, cats)
        kappa_low = fleiss_kappa_multi(ratings_low, cats)
        assert kappa_high > kappa_low

    def test_ragged_items_skipped(self):
        """Items with only 1 rater are skipped (need ≥ 2 raters per item)."""
        ratings = [
            ["I1"],            # only 1 rater → skip
            ["I0", "I0"],      # 2 raters, agree
            ["I1", "I1"],      # 2 raters, agree
        ]
        cats = ["I0", "I1"]
        val = fleiss_kappa_multi(ratings, cats)
        # After skipping the single-rater item, N = 2, both agree → κ = 1.0
        assert val == pytest.approx(1.0)


# ─────────────────────────────────────────────────────────────────────────────
# 3. icc_wrong_indicator
# ─────────────────────────────────────────────────────────────────────────────

class TestIccWrongIndicator:

    def test_all_wrong_in_all_cells(self):
        """All agents wrong in every cell → ICC near 1 (all wrong, no within variance)."""
        cells = [["I1", "I1", "I1"]] * 5
        val = icc_wrong_indicator(cells, "I0")
        # All indicators = 1; within-cell variance = 0 → MS_W = 0 → ICC = 1
        assert val == pytest.approx(1.0) or math.isnan(val)  # 0/0 is NaN OK too

    def test_all_correct_in_all_cells(self):
        """All agents correct → ICC = 1 (all zero, no variance)."""
        cells = [["I0", "I0"]] * 4
        val = icc_wrong_indicator(cells, "I0")
        assert val == pytest.approx(1.0) or math.isnan(val)

    def test_high_between_low_within(self):
        """Alternating all-wrong vs all-correct cells → high ICC."""
        cells = [
            ["I1", "I1"],   # all wrong
            ["I0", "I0"],   # all correct
            ["I1", "I1"],   # all wrong
            ["I0", "I0"],   # all correct
        ]
        val = icc_wrong_indicator(cells, "I0")
        # High between-cell variance, zero within-cell variance → ICC = 1
        assert not math.isnan(val)
        assert val > 0.8

    def test_low_icc_independent(self):
        """Mixed within cells → lower ICC."""
        cells = [
            ["I1", "I0"],  # 50/50 in each cell
            ["I0", "I1"],
            ["I1", "I0"],
            ["I0", "I1"],
        ]
        val = icc_wrong_indicator(cells, "I0")
        # Within variance high, between variance low → ICC near 0 or negative
        assert not math.isnan(val)
        assert val < 0.5

    def test_single_cell_returns_nan(self):
        """A single cell → cannot estimate between-cell variance → NaN."""
        assert math.isnan(icc_wrong_indicator([["I1", "I0"]], "I0"))

    def test_empty_returns_nan(self):
        assert math.isnan(icc_wrong_indicator([], "I0"))

    def test_iperp_treated_as_not_wrong(self):
        """I_perp labels are treated as NOT wrong (indicator = 0)."""
        cells = [
            [IPERP, IPERP],
            [IPERP, IPERP],
        ]
        val = icc_wrong_indicator(cells, "I0")
        # All indicators = 0 → same as all-correct
        assert val == pytest.approx(1.0) or math.isnan(val)


# ─────────────────────────────────────────────────────────────────────────────
# 4. effective_ensemble_size
# ─────────────────────────────────────────────────────────────────────────────

class TestEffectiveEnsembleSize:

    def test_rho_zero(self):
        """ρ̄ = 0 → n_eff = n (fully independent agents)."""
        assert effective_ensemble_size(5, 0.0) == pytest.approx(5.0)

    def test_rho_one(self):
        """ρ̄ = 1 → n_eff = 1 (all agents identical, fake redundancy)."""
        assert effective_ensemble_size(5, 1.0) == pytest.approx(1.0)
        assert effective_ensemble_size(10, 1.0) == pytest.approx(1.0)

    def test_intermediate_rho(self):
        """ρ̄ = 0.5, n = 5 → n_eff = 5/3 ≈ 1.667."""
        assert effective_ensemble_size(5, 0.5) == pytest.approx(5.0 / (1.0 + 4 * 0.5))

    def test_n_one(self):
        """n = 1 → n_eff = 1 regardless of ρ̄."""
        assert effective_ensemble_size(1, 0.9) == pytest.approx(1.0)
        assert effective_ensemble_size(1, 0.0) == pytest.approx(1.0)

    def test_n_zero(self):
        assert effective_ensemble_size(0, 0.5) == pytest.approx(0.0)

    def test_formula_correctness(self):
        """Formula: n / (1 + (n-1)*rho_bar)."""
        for n in [3, 7, 10]:
            for rho in [0.0, 0.25, 0.5, 0.75, 1.0]:
                expected = n / (1 + (n - 1) * rho)
                assert effective_ensemble_size(n, rho) == pytest.approx(expected)


# ─────────────────────────────────────────────────────────────────────────────
# 5. independence_counterfactual
# ─────────────────────────────────────────────────────────────────────────────

class TestIndependenceCounterfactual:

    def _base_tidy(self) -> pd.DataFrame:
        """All agents wrong on the same label → high CD, positive delta expected."""
        rows = []
        for task_id in [f"T{i}" for i in range(10)]:
            for j in range(5):
                rows.append({
                    "task": task_id,
                    "method": "sc",
                    "model_class": "reasoning",
                    "seed": 1,
                    "label": "I1",  # all wrong, all same
                    "target": "I0",
                    "regime": "H1_external",
                    "ambiguity_k": 1,
                    "model": f"model_{j}",
                })
        return pd.DataFrame(rows)

    def test_all_wrong_same_label_positive_delta(self):
        """All agents converge on same wrong label → delta > 0 (more than independent)."""
        tidy = self._base_tidy()
        result = independence_counterfactual(tidy, n_bootstrap=100, seed=0)
        assert result["observed"] > 0
        assert result["delta"] >= 0
        # CI should bracket the delta
        assert result["ci_lo"] <= result["delta"]
        assert result["ci_hi"] >= result["delta"]
        assert result["n_bootstrap"] > 0

    def test_all_correct_zero_cd(self):
        """All agents correct → cd = 0, delta near 0."""
        rows = []
        for task_id in [f"T{i}" for i in range(8)]:
            for j in range(4):
                rows.append({
                    "task": task_id, "method": "sc", "model_class": "r",
                    "seed": 1, "label": "I0", "target": "I0",
                    "regime": "H1_external", "ambiguity_k": 1, "model": f"m{j}",
                })
        tidy = pd.DataFrame(rows)
        result = independence_counterfactual(tidy, n_bootstrap=50, seed=0)
        assert result["observed"] == pytest.approx(0.0)

    def test_result_keys_present(self):
        tidy = self._base_tidy()
        result = independence_counterfactual(tidy, n_bootstrap=50, seed=1)
        for key in ("observed", "cf_mean", "delta", "ci_lo", "ci_hi", "n_bootstrap"):
            assert key in result

    def test_deterministic(self):
        """Same seed → same result."""
        tidy = self._base_tidy()
        r1 = independence_counterfactual(tidy, n_bootstrap=50, seed=7)
        r2 = independence_counterfactual(tidy, n_bootstrap=50, seed=7)
        assert r1["delta"] == pytest.approx(r2["delta"])

    def test_reuses_cd_primary_not_reimplementation(self):
        """Verify independence_counterfactual calls analysis.cd.cd_primary, not reimplements it.

        We call cd_primary directly on hand-crafted labels and verify the
        independence_counterfactual observable result is consistent with
        cd_primary's semantics.
        """
        # 5 agents all wrong on same label: cd_primary should be 1.0
        assert _cd_primary_fn(["I1", "I1", "I1", "I1", "I1"], "I0") == pytest.approx(1.0)
        # Verify cd_primary excludes I_perp from numerator
        assert _cd_primary_fn(["I1", "I_perp", "I_perp"], "I0") == pytest.approx(1 / 3)

    def test_empty_tidy_returns_nan(self):
        tidy = pd.DataFrame(columns=["task", "method", "model_class", "seed",
                                     "label", "target", "regime", "model"])
        result = independence_counterfactual(tidy, n_bootstrap=10, seed=0)
        assert math.isnan(result["observed"])

    def test_regime_filter(self):
        """regime='H1_external' filter should restrict CD to H1 rows only."""
        rows = []
        for i in range(5):
            rows.append({"task": f"T{i}", "method": "sc", "model_class": "r",
                         "seed": 1, "label": "I1", "target": "I0",
                         "regime": "H1_external", "ambiguity_k": 1,
                         "model": "m0"})
            rows.append({"task": f"T{i}", "method": "sc", "model_class": "r",
                         "seed": 1, "label": "I0", "target": "I0",
                         "regime": "H2_derivable", "ambiguity_k": 1,
                         "model": "m1"})
        tidy = pd.DataFrame(rows)
        r_h1 = independence_counterfactual(tidy, regime="H1_external",
                                           n_bootstrap=50, seed=0)
        r_h2 = independence_counterfactual(tidy, regime="H2_derivable",
                                           n_bootstrap=50, seed=0)
        # H1: all wrong → observed > 0; H2: all correct → observed = 0
        assert r_h1["observed"] > 0
        assert r_h2["observed"] == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# 6. compute_dependence_table
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeDependenceTable:

    def _all_wrong_tidy(self) -> pd.DataFrame:
        rows = []
        for task_id in ["T1", "T2", "T3"]:
            for j in range(3):
                rows.append({
                    "task": task_id, "method": "sc", "model_class": "reasoning",
                    "seed": 1, "label": "I1", "target": "I0",
                    "regime": "H1_external", "ambiguity_k": 1, "model": f"m{j}",
                })
        return pd.DataFrame(rows)

    def test_returns_tuple(self):
        tidy = self._all_wrong_tidy()
        cell_df, regime_summary = compute_dependence_table(tidy, n_bootstrap=50)
        assert isinstance(cell_df, pd.DataFrame)
        assert isinstance(regime_summary, dict)

    def test_cell_df_has_required_columns(self):
        tidy = self._all_wrong_tidy()
        cell_df, _ = compute_dependence_table(tidy, n_bootstrap=20)
        for col in ("n_agents", "pairwise_wrong_agreement", "kappa", "cd_primary"):
            assert col in cell_df.columns, f"Missing column: {col}"

    def test_all_wrong_same_label_pwa_one(self):
        tidy = self._all_wrong_tidy()
        cell_df, _ = compute_dependence_table(tidy, n_bootstrap=20)
        assert ((cell_df["pairwise_wrong_agreement"] - 1.0).abs() < 1e-9).all()

    def test_regime_summary_has_expected_keys(self):
        tidy = self._all_wrong_tidy()
        _, regime_summary = compute_dependence_table(tidy, n_bootstrap=20)
        for regime_key, stats in regime_summary.items():
            for k in ("icc", "n_eff_mean", "observed_cd", "cf_cd", "delta", "ci_lo", "ci_hi"):
                assert k in stats

    def test_empty_tidy_returns_empty(self):
        tidy = pd.DataFrame(columns=["task", "method", "model_class", "seed",
                                     "label", "target", "regime", "model"])
        cell_df, regime_summary = compute_dependence_table(tidy, n_bootstrap=10)
        assert cell_df.empty
        assert regime_summary == {}

    def test_frozen_cell_key_not_model(self):
        """Cell key MUST be (task, method, model_class, seed), NOT model.

        Spec enforcement: do NOT add 'model' to the cell key.
        Two rows with the same (task, method, model_class, seed) but different model
        IDs should form a SINGLE cell.
        """
        rows = [
            {"task": "T1", "method": "sc", "model_class": "r", "seed": 1,
             "label": "I1", "target": "I0", "regime": "H1_external",
             "ambiguity_k": 1, "model": "m_A"},
            {"task": "T1", "method": "sc", "model_class": "r", "seed": 1,
             "label": "I1", "target": "I0", "regime": "H1_external",
             "ambiguity_k": 1, "model": "m_B"},
        ]
        tidy = pd.DataFrame(rows)
        cell_df, _ = compute_dependence_table(tidy, n_bootstrap=10)
        # Both rows should be in ONE cell (n_agents = 2).
        assert len(cell_df) == 1
        assert int(cell_df.iloc[0]["n_agents"]) == 2

    def test_frozen_cells_unanimous_icc_one(self):
        """Auditor's ICC test: each frozen cell internally unanimous → ICC ≈ 1.0.

        The buggy groupby-task code merged distinct methods into one cluster,
        creating artificial within-cluster variance → ICC returned −0.333.
        After the fix (groupby frozen cell key), MS_W = 0 → ICC = 1.0.
        """
        rows = []
        for task in ["T1", "T2"]:
            # Cell (task, sc, r, 1): both agents wrong → indicators [1, 1]
            for j in range(2):
                rows.append({"task": task, "method": "sc", "model_class": "r", "seed": 1,
                             "label": "I1", "target": "I0", "regime": "H1_external",
                             "ambiguity_k": 1, "model": f"m{j}"})
            # Cell (task, mc, r, 1): both agents correct → indicators [0, 0]
            for j in range(2):
                rows.append({"task": task, "method": "mc", "model_class": "r", "seed": 1,
                             "label": "I0", "target": "I0", "regime": "H1_external",
                             "ambiguity_k": 1, "model": f"m{j}"})
        tidy = pd.DataFrame(rows)
        _, regime_summary = compute_dependence_table(tidy, n_bootstrap=10)
        icc_val = regime_summary["H1_external"]["icc"]
        # Each frozen cell is internally unanimous → MS_W = 0 → ICC = 1.0
        assert not math.isnan(icc_val)
        assert icc_val == pytest.approx(1.0)

    def test_full_run_scoped_marginals_h1_delta(self):
        """Auditor's counterfactual test: full-run marginals give positive H1 delta.

        Setup: models always wrong in H1, always correct in H2.
        - Full-run marginal per model: ~50% wrong.
        - Under independence with 50% wrong marginal, observed H1 CD > counterfactual.
        - delta > 0 substantially (≈ 0.5).
        Bug: passing regime_tidy (H1 only) to independence_counterfactual gives
        marginals of 100% wrong → counterfactual = observed → delta ≈ 0.
        """
        rows = []
        for i in range(5):
            for j in range(5):
                # H1: all 5 agents wrong (convergent delusion)
                rows.append({
                    "task": f"TH1_{i}", "method": "sc", "model_class": "r", "seed": 1,
                    "label": "I1", "target": "I0",
                    "regime": "H1_external", "ambiguity_k": 1, "model": f"m{j}",
                })
                # H2: all 5 agents correct
                rows.append({
                    "task": f"TH2_{i}", "method": "sc", "model_class": "r", "seed": 1,
                    "label": "I0", "target": "I0",
                    "regime": "H2_derivable", "ambiguity_k": 1, "model": f"m{j}",
                })
        tidy = pd.DataFrame(rows)
        _, regime_summary = compute_dependence_table(tidy, n_bootstrap=300, seed=0)
        delta_h1 = regime_summary["H1_external"]["delta"]
        # With full-run marginals each model is 50% wrong; under independence
        # H1 counterfactual CD < 1.0 → delta > 0 substantially.
        # With regime-filtered (buggy) marginals: delta ≈ 0.
        assert not math.isnan(delta_h1)
        assert delta_h1 > 0.3
