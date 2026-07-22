"""Offline tests for scripts/strengthening_analyses.py (post-hoc secondary).

# Implementer model family: Claude (Anthropic)

Uses a tiny synthetic tidy fixture (no checkpoint files, no network, no model
calls) to assert both strengthening analyses run and return the expected keys /
shapes, and that the pre-stated TOST margins and frozen-metric reuse behave as
documented. These are SECONDARY/post-hoc analyses — the tests guard structure
and determinism, not confirmatory numbers.
"""
from __future__ import annotations

import pandas as pd
import pytest

from scripts import strengthening_analyses as SA


# ── Synthetic fixtures ───────────────────────────────────────────────────────
def _r2_single_fixture() -> pd.DataFrame:
    """Minimal R2 single-agent tidy table: 2 items x 3 non-Anthropic models
    (openai gpt-5.4, google gemini-3.1-pro-preview, openai gpt-4o-mini) + 1
    Anthropic reference model, 1 seed. Item A: all three non-Anthropic agents
    converge on wrong foil I1 (concentration=1.0, 2 families). Item B: all
    correct (I0)."""
    rows = []

    def add(task, model, label, target="I0"):
        rows.append({
            SA._ITEM: task, SA._METHOD: "single", SA._MODEL_CLASS: "unknown",
            SA._SEED: 0, SA._LABEL: label, SA._TARGET: target,
            SA._REGIME: "H1_external", "ambiguity_k": 1, SA._MODEL: model,
        })

    # Item A — cross-model convergence on I1.
    add("itemA", "gpt-5.4", "I1")
    add("itemA", "gemini-3.1-pro-preview", "I1")
    add("itemA", "gpt-4o-mini", "I1")
    add("itemA", "claude-opus-4.8", "I2")  # Anthropic reference (separate)
    # Item B — all correct.
    add("itemB", "gpt-5.4", "I0")
    add("itemB", "gemini-3.1-pro-preview", "I0")
    add("itemB", "gpt-4o-mini", "I0")
    add("itemB", "claude-opus-4.8", "I0")
    return pd.DataFrame(rows)


def _conf_fixture() -> pd.DataFrame:
    """Minimal confirmatory tidy table with H1_external cells for the
    heterogeneous-MAD / homogeneous-MAD contrast and reasoning/weak/heterogeneous
    tiers, over 4 shared tasks."""
    rows = []

    def cell(task, method, mc, labels, target="I0", seed=0):
        for lab in labels:
            rows.append({
                SA._ITEM: task, SA._METHOD: method, SA._MODEL_CLASS: mc,
                SA._SEED: seed, SA._LABEL: lab, SA._TARGET: target,
                SA._REGIME: "H1_external", "ambiguity_k": 1, SA._MODEL: "m",
            })

    for i in range(4):
        t = f"t{i}"
        # heterogeneous-MAD cell (model_class heterogeneous)
        cell(t, SA.HETEROGENEOUS_METHOD, "heterogeneous", ["I1", "I1", "I0"])
        # homogeneous-MAD cell (model_class homogeneous)
        cell(t, SA.HOMOGENEOUS_METHOD, "homogeneous", ["I1", "I1", "I0"])
        # reasoning + weak single cells (matched tiers)
        cell(t, "single", "reasoning", ["I1", "I1", "I0"])
        cell(t, "single", "weak", ["I1", "I0", "I0"])
    return pd.DataFrame(rows)


# ── Family mapping ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("slug,fam", [
    ("gpt-5.4", "openai"), ("gpt-4o-mini", "openai"),
    ("claude-opus-4.8", "anthropic"), ("claude-sonnet-4.6", "anthropic"),
    ("gemini-3.1-pro-preview", "google"), ("gemini-3.5-flash", "google"),
    ("mai-code-1-flash-picker", "microsoft"), ("weird-model", "unknown"),
])
def test_family_of(slug, fam):
    assert SA.family_of(slug) == fam


# ── Analysis 1 ───────────────────────────────────────────────────────────────
def test_analysis1_keys_and_shapes():
    r2 = _r2_single_fixture()
    res = SA.analysis1_cross_model_concentration(r2)
    assert res["analysis"] == "cross_model_label_concentration_R2"
    assert "SECONDARY" in res["kind"]
    cf = res["cross_family"]
    for key in ("n_items", "mean_concentration", "median_concentration",
                "boot_ci_lo", "boot_ci_hi", "frac_items_ge2_families_on_foil",
                "mean_n_families_on_modal_foil", "distinct_families"):
        assert key in cf
    # 2 items; item table one row per item.
    assert cf["n_items"] == 2
    assert len(res["item_table"]) == 2
    # Same-family Anthropic reference reported separately.
    assert res["same_family_reference"]["n_items"] == 2


def test_analysis1_cross_model_convergence_values():
    r2 = _r2_single_fixture()
    res = SA.analysis1_cross_model_concentration(r2)
    cf = res["cross_family"]
    # Item A concentration = 3/3 = 1.0 on foil I1 (frozen cd_primary); item B = 0.
    tbl = {r["task"]: r for r in res["item_table"]}
    assert tbl["itemA"]["concentration"] == pytest.approx(1.0)
    assert tbl["itemA"]["modal_wrong_foil"] == "I1"
    assert tbl["itemA"]["n_families_on_modal_foil"] == 2  # openai + google
    assert tbl["itemB"]["concentration"] == pytest.approx(0.0)
    assert tbl["itemB"]["modal_wrong_foil"] is None
    # Aggregate: mean = 0.5; exactly 1/2 items have >=2 families on the foil.
    assert cf["mean_concentration"] == pytest.approx(0.5)
    assert cf["frac_items_ge2_families_on_foil"] == pytest.approx(0.5)
    # Anthropic excluded from cross-family models.
    assert "anthropic" not in cf["distinct_families"]


# ── Analysis 2 ───────────────────────────────────────────────────────────────
def test_analysis2_keys_and_shapes():
    conf = _conf_fixture()
    res = SA.analysis2_tost(conf)
    assert res["analysis"] == "tost_equivalence_H1_external"
    assert res["equivalence_margins"] == {"primary": 0.15, "strict": 0.10}
    a = res["a_hetero_vs_homogeneous"]
    assert a["n_items"] == 4
    assert set(a["tost"]) == {"primary_0.15", "strict_0.10"}
    for key in ("margin", "observed_delta", "p_tost", "equivalent",
                "ci90_lo", "ci90_hi"):
        assert key in a["tost"]["primary_0.15"]
    # Three pairwise tier comparisons.
    assert len(res["b_capability_tiers"]) == 3
    assert "pooled_reference" in a


def test_analysis2_identical_groups_are_equivalent():
    conf = _conf_fixture()
    res = SA.analysis2_tost(conf)
    # hetero vs homo cells are identical label patterns -> delta 0 -> equivalent.
    a = res["a_hetero_vs_homogeneous"]
    assert a["observed_delta"] == pytest.approx(0.0)
    assert a["tost"]["primary_0.15"]["equivalent"] is True
    assert a["tost"]["strict_0.10"]["equivalent"] is True


def test_tost_paired_prestated_margins_are_module_constants():
    # Margins must be the documented pre-stated constants (not data-tuned).
    assert SA.EQUIV_MARGIN_PRIMARY == 0.15
    assert SA.EQUIV_MARGIN_STRICT == 0.10


def test_tost_paired_not_equivalent_when_delta_exceeds_margin():
    # A large, tight difference must NOT be judged equivalent.
    diffs = [0.5] * 10
    out = SA.tost_paired(diffs, margin=0.15)
    assert out["equivalent"] is False


def test_tost_paired_equivalent_when_delta_within_margin():
    diffs = [0.0, 0.01, -0.01, 0.005, -0.005, 0.0, 0.0, 0.01, -0.01, 0.0]
    out = SA.tost_paired(diffs, margin=0.15)
    assert out["equivalent"] is True
    assert out["ci90_lo"] > -0.15 and out["ci90_hi"] < 0.15


# ── Report assembly ──────────────────────────────────────────────────────────
def test_to_markdown_runs():
    rep = {
        "analysis1": SA.analysis1_cross_model_concentration(_r2_single_fixture()),
        "analysis2": SA.analysis2_tost(_conf_fixture()),
        "disclaimer": "SECONDARY / post-hoc.",
        "implementer_model_family": "Claude (Anthropic)",
        "bootstrap_seed": 42,
        "data_dir": "synthetic",
    }
    md = SA.to_markdown(rep)
    assert "Analysis 1" in md and "Analysis 2" in md
    assert "TOST" in md
    assert "0.15" in md
