"""Tests for analysis.contrasts, decision_rules, figure_data (Deliverables 2/4/5).

Model family of implementer: Claude (Anthropic). Auditor: NON-Claude (GPT).

Synthetic tables with KNOWN structure:
- convergent delusion rises with ambiguity k (H1b),
- heterogeneous (cross-family) CD exceeds homogeneous/SC CD (row-35 headline),
- H2_derivable attenuates for reasoning models (H2),
so the contrasts return the expected-sign deltas and the §9 decision rules
return the known verdicts. All OFFLINE.
"""

import json

import numpy as np
import pandas as pd

from analysis import decision_rules as dr
from analysis import figure_data as fd
from analysis.contrasts import (
    aggregation_vs_single,
    cd_by_regime,
    cd_vs_k,
    compute_cell_cd,
    cross_model_vs_homogeneous,
)


def _structured_df(seed: int = 0) -> pd.DataFrame:
    """Agent-level table with the injected effects described in the module docstring."""
    rng = np.random.default_rng(seed)
    rows = []
    methods = {"single": 1, "sc": 5, "homogeneous-MAD": 5, "heterogeneous-MAD": 5}
    for task in range(18):
        regime = "H1_external" if task % 2 == 0 else "H2_derivable"
        for k in (1, 2, 3):
            for method, n in methods.items():
                for mc in ("homogeneous", "reasoning"):
                    for seed_i in (0, 1):
                        base = 0.14 * k
                        if method == "heterogeneous-MAD":
                            base += 0.22  # cross-family genuine convergent delusion
                        if regime == "H2_derivable" and mc == "reasoning":
                            base *= 0.2   # reasoners attenuate in H2
                        base = min(base, 0.95)
                        labels = []
                        for _ in range(n):
                            r = rng.random()
                            labels.append("I1" if r < base else
                                          ("I_perp" if r < base + 0.05 else "I0"))
                        for lab in labels:
                            rows.append(dict(
                                task=f"t{task}_k{k}", model=f"m_{mc}", regime=regime,
                                ambiguity_k=k, method=method, model_class=mc,
                                seed=seed_i, label=lab, target="I0"))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Contrasts (Deliverable 2)
# --------------------------------------------------------------------------- #

def test_aggregation_vs_single_reports_all_variants():
    df = _structured_df(0)
    out = aggregation_vs_single(df)
    methods = set(out["method"])
    assert "single" not in methods  # single is the baseline, excluded
    assert {"heterogeneous-MAD", "homogeneous-MAD", "sc"} <= methods
    # Every A04 variant + I_perp rate reported as a delta column.
    for cd in ("cd_primary", "cd_sensitivity_frozen", "cd_sensitivity_drop_iperp",
               "iperp_rate"):
        assert f"delta_{cd}" in out.columns
    hetero = out[out["method"] == "heterogeneous-MAD"].iloc[0]
    assert hetero["delta_cd_primary"] > 0  # aggregation does NOT reduce CD (H1a)


def test_cross_model_vs_homogeneous_headline():
    """Row-35 headline: heterogeneous CD exceeds BOTH homogeneous and SC."""
    df = _structured_df(1)
    out = cross_model_vs_homogeneous(df)
    baselines = set(out["baseline"])
    assert {"homogeneous-MAD", "sc"} <= baselines
    for _, row in out.iterrows():
        assert row["delta_cd_primary"] > 0, \
            f"heterogeneous should exceed {row['baseline']} (genuine vs fake redundancy)"
        assert row["cd_primary_hetero"] > row["cd_primary_baseline"]


def test_cd_vs_k_monotone_increasing():
    df = _structured_df(2)
    out = cd_vs_k(df, by=("method",))
    # For each method, CD is (weakly) increasing across k = 1 < 2 < 3.
    for method, grp in out.groupby("method"):
        grp = grp.sort_values("ambiguity_k")
        vals = list(grp["cd_primary"])
        assert vals[0] <= vals[-1], f"{method}: CD should rise with k, got {vals}"


def test_cd_by_regime_attenuates_for_reasoners():
    df = _structured_df(3)
    out = cd_by_regime(df)
    reasoning = out[out["model_class"] == "reasoning"]
    h1 = reasoning[reasoning["regime"] == "H1_external"]["cd_primary"].iloc[0]
    h2 = reasoning[reasoning["regime"] == "H2_derivable"]["cd_primary"].iloc[0]
    assert h2 < h1, "reasoning-model CD should attenuate in H2_derivable"


def test_compute_cell_cd_preserves_k_per_task():
    df = _structured_df(0)
    cells = compute_cell_cd(df)
    # Each distinct task_id maps to a single ambiguity_k (no collapsing).
    per_task_k = cells.groupby("task")["ambiguity_k"].nunique()
    assert (per_task_k == 1).all()
    assert set(cells["ambiguity_k"]) == {1, 2, 3}


# --------------------------------------------------------------------------- #
# Decision rules (Deliverable 4) — pure evaluators on crafted CIs
# --------------------------------------------------------------------------- #

def test_pure_evaluators_known_verdicts():
    assert dr.evaluate_h1a((0.1, 0.02, 0.2)) == dr.SUPPORTED
    assert dr.evaluate_h1a((-0.1, -0.2, -0.02)) == dr.REFUTED
    assert dr.evaluate_h1a((0.0, -0.1, 0.1)) == dr.INCONCLUSIVE

    assert dr.evaluate_h1b((0.1, 0.01, 0.2)) == dr.SUPPORTED
    assert dr.evaluate_h1b((-0.1, -0.2, -0.01)) == dr.REFUTED
    assert dr.evaluate_h1b((0.05, -0.1, 0.2)) == dr.INCONCLUSIVE

    # H2: interaction excludes 0 AND reasoner H2 not above single -> SUPPORTED.
    assert dr.evaluate_h2((0.2, 0.05, 0.3), (-0.1, -0.3, 0.05)) == dr.SUPPORTED
    # reasoner H2 significantly ABOVE single -> REFUTED regardless of interaction.
    assert dr.evaluate_h2((0.2, 0.05, 0.3), (0.2, 0.05, 0.4)) == dr.REFUTED
    # interaction includes 0 -> INCONCLUSIVE.
    assert dr.evaluate_h2((0.0, -0.2, 0.2), (-0.1, -0.3, 0.0)) == dr.INCONCLUSIVE

    assert dr.evaluate_r1((0.3, 0.1, 0.5)) == dr.SUPPORTED
    assert dr.evaluate_r1((-0.1, -0.3, -0.02)) == dr.REFUTED
    assert dr.evaluate_r1((0.0, -0.1, 0.1)) == dr.INCONCLUSIVE

    assert dr.evaluate_r2((0.2, 0.05, 0.4)) == dr.SUPPORTED
    assert dr.evaluate_r2((-0.2, -0.4, -0.05)) == dr.REFUTED


def test_evaluate_all_and_robustness():
    cis = {
        "h1a": (0.1, 0.02, 0.2),
        "h1b": (0.1, 0.01, 0.2),
        "h2_interaction": (0.2, 0.05, 0.3),
        "h2_reasoner_vs_single": (-0.1, -0.3, 0.05),
        "r1": (0.3, 0.1, 0.5),
        "r2": (0.2, 0.05, 0.4),
    }
    verdicts = dr.evaluate_all(cis)
    assert verdicts == {h: dr.SUPPORTED for h in ("H1a", "H1b", "H2", "R1", "R2")}

    # Robustness is now SIGN-based over the per-variant CI dicts (MAJOR 7):
    # verdict LABELS may differ across variants (a CI margin crossing zero) yet
    # still agree in DIRECTION -> robust. Only a genuine sign flip is divergent.
    weaker = {k: (v[0] * 0.5, v[1] * 0.5 - 0.05, v[2] * 0.5) for k, v in cis.items()}
    robust = dr.robustness_across_variants({
        "cd_primary": cis,
        "cd_sensitivity_frozen": cis,
        "cd_sensitivity_drop_iperp": weaker,  # same signs, looser CIs
    })
    assert all(v.startswith("robust:+") for v in robust.values()), robust

    # A genuine SIGN FLIP on H1a is reported divergent even though one variant
    # alone would read SUPPORTED and the other REFUTED.
    divergent = dr.robustness_across_variants({
        "cd_primary": {"h1a": (0.1, 0.02, 0.2)},
        "cd_sensitivity_frozen": {"h1a": (-0.1, -0.2, -0.02)},
    })
    assert divergent["H1a"].startswith("divergent:")

    # Sign AGREEMENT despite verdict-label disagreement is NOT divergent
    # (this is exactly the case the old label-equality logic mishandled).
    not_divergent = dr.robustness_across_variants({
        "cd_primary": {"h1a": (0.10, 0.02, 0.20)},   # SUPPORTED
        "cd_sensitivity_frozen": {"h1a": (0.03, -0.01, 0.09)},  # INCONCLUSIVE, same sign
    })
    assert not_divergent["H1a"].startswith("robust:+"), not_divergent


def test_evaluate_from_data_supports_h1_and_r1_wiring():
    """Data-driven §9 on the PRIMARY treatment. R1 is wired to
    harness.nulls.label_shuffle_null and must be SUPPORTED when items have
    GENUINE within-item concentration (some items all-I1, some all-I0)."""
    rows = []
    methods = {"single": 1, "heterogeneous-MAD": 5}
    for task in range(16):
        # Genuine within-item concentration on DIVERSE wrong labels: each
        # concentrated item lands entirely on its OWN wrong label, so the
        # pooled marginal is spread across {I1..I4} and the label-shuffle null
        # (which redeals from that spread marginal) yields LOW per-item CD,
        # while real per-item CD is ~1.0 -> R1 fires.
        concentrated_wrong = task % 2 == 0
        wrong_label = f"I{(task % 4) + 1}"
        for k in (1, 2, 3):
            for method, n in methods.items():
                for seed in (0, 1):
                    if concentrated_wrong:
                        labels = [wrong_label] * n
                    else:
                        labels = ["I0"] * n  # all correct
                    for lab in labels:
                        rows.append(dict(
                            task=f"t{task}_k{k}", model="m0", regime="H1_external",
                            ambiguity_k=k, method=method, model_class="reasoning",
                            seed=seed, label=lab, target="I0"))
    df = pd.DataFrame(rows)
    out = dr.evaluate_from_data(df, cd_col="cd_primary", n_bootstrap=80, r1_n_perm=60)
    # Real within-item concentration >> shuffled marginal -> R1 SUPPORTED.
    assert out["verdicts"]["R1"] == dr.SUPPORTED, out["cis"]["r1"]
    assert out["verdicts"]["H1a"] in (dr.SUPPORTED, dr.INCONCLUSIVE)


# --------------------------------------------------------------------------- #
# Audit fixes — failing-pre-fix discriminating tests (BLOCKER 3/4/5, MAJOR 6)
# --------------------------------------------------------------------------- #

def test_r1_shuffle_fidelity_to_harness_null():
    """BLOCKER 3: the local variant-aware cross-item shuffle-null must EXACTLY
    reproduce ``harness.nulls.label_shuffle_null`` when the CD variant is the
    frozen ``cd_sensitivity_frozen`` (which calls the frozen
    ``false_consensus_rate``) at the same seed — proving fidelity to the
    pre-registered null."""
    from analysis.decision_rules import _cross_item_shuffle_cd
    from analysis.cd import cd_sensitivity_frozen
    from harness.nulls import label_shuffle_null

    items = [["I1", "I1", "I0"], ["I0", "I2", "I2"], ["I1", "I0", "I3"],
             ["I2", "I2", "I0"]]
    a = _cross_item_shuffle_cd(items, "I0", cd_sensitivity_frozen, n_perm=120, seed=13)
    b = label_shuffle_null(items, "I0", n_perm=120, seed=13)
    assert abs(a - b) < 1e-12, (a, b)


def test_r1_metric_variant_aware_and_conditioned():
    """BLOCKER 3: ``_r1_metric`` must accept a CD-variant column and evaluate the
    real AND shuffled CD with THAT variant. On items carrying I_perp,
    ``cd_primary`` (I_perp ineligible) and ``cd_sensitivity_frozen`` (I_perp is a
    wrong label) give materially different real CD, so the R1 point differs by
    variant. (Pre-fix ``_r1_metric`` had no cd-variant arg and always used the
    frozen metric -> this call signature fails.)"""
    from analysis.decision_rules import _r1_metric

    rows = []
    for task in range(8):
        conc = task % 2 == 0
        labs = ["I1", "I_perp", "I_perp", "I_perp"] if conc else ["I0", "I0", "I0", "I0"]
        for lab in labs:
            rows.append(dict(task=f"t{task}", model="m0", regime="H1_external",
                             ambiguity_k=1, method="heterogeneous-MAD",
                             model_class="reasoning", seed=0, label=lab, target="I0"))
    df = pd.DataFrame(rows)
    m_primary = _r1_metric("cd_primary", n_perm=80)(df)
    m_frozen = _r1_metric("cd_sensitivity_frozen", n_perm=80)(df)
    assert not np.isnan(m_primary) and not np.isnan(m_frozen)
    # frozen counts I_perp (real CD 0.75) vs primary ignores it (real CD 0.25).
    assert abs(m_primary - m_frozen) > 1e-2, (m_primary, m_frozen)


def test_r2_uses_constructor_family_not_aggregation_method():
    """BLOCKER 4: R2 is the H1 aggregation-vs-single effect on items CONSTRUCTED
    by a cross-family constructor, NOT a heterogeneous-vs-single aggregation
    contrast. Here the effect is large on NATIVE-constructed items but VANISHES
    on cross-constructed items, so R2 must be INCONCLUSIVE. The old
    hetero-minus-single metric (pooling all items) would read strongly positive
    -> SUPPORTED."""
    rows = []

    def add(task, method, constructor, labels):
        for lab in labels:
            rows.append(dict(task=task, model="m0", regime="H1_external",
                             ambiguity_k=1, method=method, model_class="reasoning",
                             seed=0, label=lab, target="I0",
                             constructor_family=constructor))

    for t in range(8):
        # NATIVE items: big aggregation-vs-single gap (single correct, hetero wrong).
        add(f"nat_s_{t}", "single", "native", ["I0"])
        add(f"nat_h_{t}", "heterogeneous-MAD", "native", ["I1", "I1", "I1", "I1"])
    for t in range(8):
        # CROSS-constructed items: NO gap (both single and hetero equally wrong).
        add(f"cr_s_{t}", "single", "cross", ["I1"])
        add(f"cr_h_{t}", "heterogeneous-MAD", "cross", ["I1", "I1", "I1", "I1"])

    df = pd.DataFrame(rows)
    out = dr.evaluate_from_data(df, cd_col="cd_primary", n_bootstrap=150,
                                r1_n_perm=40, native_constructor="native")
    assert out["verdicts"]["R2"] == dr.INCONCLUSIVE, out["cis"]["r2"]


def test_h1b_driven_by_mixed_model_coefficient():
    """BLOCKER 5: H1b comes from the fitted mixed-model AMBIGUITY_K coefficient
    CI (not a raw polyfit slope). The helper must return exactly the model's
    ambiguity_k coefficient + CI."""
    from analysis.decision_rules import _h1b_coef_ci
    from analysis.stats import fit_mixed_effects_model

    df = _structured_df(0)
    h1 = df[df["regime"] == "H1_external"]
    ci = _h1b_coef_ci(h1, "cd_primary")
    cells = compute_cell_cd(h1)
    res = fit_mixed_effects_model(cells, "cd_primary ~ ambiguity_k + (1|model_class)")
    coef = res["coefficients"]["ambiguity_k"]
    lo, hi = res["confidence_intervals"]["ambiguity_k"]
    assert abs(ci[0] - coef) < 1e-9
    assert abs(ci[1] - lo) < 1e-9 and abs(ci[2] - hi) < 1e-9
    assert ci[1] > 0, f"k CI should exclude 0 (positive), got {ci}"


def test_h2_interaction_from_model_coefficient():
    """BLOCKER 5: H2's interaction CI comes from the §8 mixed-model
    regime x model_class coefficient (not a raw mean gap)."""
    from analysis.decision_rules import _h2_interaction_ci
    from analysis.stats import fit_mixed_effects_model

    df = _structured_df(0)
    ci = _h2_interaction_ci(df, "cd_primary", "reasoning")
    assert not np.isnan(ci[0])
    cells = compute_cell_cd(df)
    res = fit_mixed_effects_model(
        cells, "cd_primary ~ regime * model_class + ambiguity_k + (1|method)")
    name = [k for k in res["coefficients"]
            if ":" in k and "regime" in k and "reasoning" in k][0]
    assert abs(ci[0] - res["coefficients"][name]) < 1e-9


def test_h2_reasoner_vs_single_is_matched():
    """MAJOR 6: the H2 boundary contrast must be MATCHED — both sides restricted
    to H2 reasoning cells and the single method EXCLUDED from the aggregation
    side. With H2-reasoning aggregation CD=1 and H2-reasoning single CD=0, the
    matched contrast is +1.0; the old unmatched version (single pooled from
    every regime/class) cancels to 0.0."""
    from analysis.decision_rules import _h2_reasoner_vs_single_ci

    rows = []

    def add(task, regime, mc, method, labels):
        for lab in labels:
            rows.append(dict(task=task, model="m0", regime=regime, ambiguity_k=1,
                             method=method, model_class=mc, seed=0, label=lab,
                             target="I0"))

    for t in range(6):
        add(f"h2r_agg_{t}", "H2_derivable", "reasoning", "heterogeneous-MAD",
            ["I1", "I1", "I1", "I1"])          # H2-reasoning aggregation CD = 1
        add(f"h2r_sng_{t}", "H2_derivable", "reasoning", "single", ["I0"])  # single CD = 0
        add(f"h1_sng_{t}", "H1_external", "homogeneous", "single", ["I1"])  # unmatched noise

    df = pd.DataFrame(rows)
    pt, lo, hi = _h2_reasoner_vs_single_ci(df, "cd_primary", "reasoning",
                                           n_bootstrap=150, seed=1)
    assert pt == 1.0, f"matched H2-reasoning agg-vs-single should be +1.0, got {pt}"


# --------------------------------------------------------------------------- #
# Figure data (Deliverable 5)
# --------------------------------------------------------------------------- #
def test_phase_diagram_table_shape():
    df = _structured_df(0)
    tbl = fd.phase_diagram_table(df)
    assert {"method", "ambiguity_k", "regime", "cd_primary", "iperp_rate"} <= set(tbl.columns)
    # 4 methods x 3 k x 2 regimes = 24 cells.
    assert len(tbl) == 24


def test_method_ambiguity_heatmap_pivot():
    df = _structured_df(0)
    hm = fd.method_ambiguity_heatmap(df, cd_col="cd_primary")
    assert list(hm.columns) == [1, 2, 3]
    assert "heterogeneous-MAD" in hm.index
    # Heterogeneous row exceeds single row at the highest k.
    assert hm.loc["heterogeneous-MAD", 3] > hm.loc["single", 3]


def test_per_regime_cd_table():
    df = _structured_df(0)
    tbl = fd.per_regime_cd(df)
    assert set(tbl["regime"]) == {"H1_external", "H2_derivable"}


def test_all_figure_data_json_serializable():
    df = _structured_df(0)
    bundle = fd.all_figure_data(df)
    s = json.dumps(bundle)  # must not raise
    assert "phase_diagram" in bundle
    assert "method_ambiguity_heatmap" in bundle
    assert bundle["method_ambiguity_heatmap"]["cd_variant"] == "cd_primary"
    assert len(s) > 0
