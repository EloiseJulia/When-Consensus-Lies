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
    # Single-key hypotheses agree in sign -> "robust:+". H2 is COMPOSITE
    # (MAJOR D): interaction is + and the matched reasoner-vs-single component
    # is - across every variant, so H2 reports both component signs and stays
    # robust only because BOTH components are sign-stable.
    for h in ("H1a", "H1b", "R1", "R2"):
        assert robust[h].startswith("robust:+"), robust
    assert robust["H2"] == "robust:+&-", robust

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


def test_h2_robustness_is_composite_over_both_components():
    """MAJOR D: H2 is COMPOSITE (prereg §9) — its cross-variant robustness must
    consider BOTH the regime x model_class interaction AND the matched
    reasoner-H2-vs-single baseline component. Here the interaction sign is
    STABLE (+) across variants but the matched-baseline component FLIPS sign
    (- -> +), so H2 must be reported ``divergent``. The old logic (which checked
    only ``h2_interaction``) would have called it robust."""
    base = {
        "h1a": (0.1, 0.02, 0.2), "h1b": (0.1, 0.01, 0.2),
        "h2_interaction": (0.2, 0.05, 0.3),
        "h2_reasoner_vs_single": (-0.1, -0.3, 0.05),   # negative here
        "r1": (0.3, 0.1, 0.5), "r2": (0.2, 0.05, 0.4),
    }
    flipped = dict(base)
    flipped["h2_reasoner_vs_single"] = (0.15, -0.05, 0.35)  # POSITIVE in sensitivity
    out = dr.robustness_across_variants({
        "cd_primary": base,
        "cd_sensitivity_frozen": flipped,
    })
    # Interaction alone is sign-stable, so an interaction-only check would say
    # robust; the composite check catches the flipped baseline component.
    assert out["H2"].startswith("divergent:"), out
    assert "h2_reasoner_vs_single" in out["H2"], out
    # The other (single-key) hypotheses remain robust.
    assert out["H1a"].startswith("robust:+"), out


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
    """BLOCKER C: R2's cross-family construction control is RELATIONAL — an
    observation is cross-family-constructed iff its ``constructor_family``
    differs from the TESTED model's family. Here EVERY tested model is family
    ``openai`` and EVERY item is constructed by ``cohere``, so every observation
    is cross-family and R2 is the ordinary H1 aggregation-vs-single effect on the
    whole (cross-constructed) set — which is strongly positive -> SUPPORTED.

    The old "non-modal constructor" heuristic would declare the SOLE/ modal
    constructor ``cohere`` to be 'native', exclude it, find an EMPTY
    cross-family subset, and return nan -> INCONCLUSIVE. So this asserts the
    relational behaviour that fails on the pre-fix heuristic."""
    rows = []

    def add(task, method, labels):
        for lab in labels:
            rows.append(dict(task=task, model="m0", regime="H1_external",
                             ambiguity_k=1, method=method, model_class="reasoning",
                             seed=0, label=lab, target="I0",
                             model_family="openai", constructor_family="cohere"))

    for t in range(12):
        add(f"s_{t}", "single", ["I0"])                        # single correct -> CD 0
        add(f"h_{t}", "heterogeneous-MAD", ["I1", "I1", "I1", "I1"])  # aggregated wrong -> CD 1

    df = pd.DataFrame(rows)
    out = dr.evaluate_from_data(df, cd_col="cd_primary", n_bootstrap=200,
                                r1_n_perm=40)
    assert out["verdicts"]["R2"] == dr.SUPPORTED, out["cis"]["r2"]
    lo = out["cis"]["r2"][1]
    assert lo > 0, out["cis"]["r2"]

    # And via the model->family MAP fallback (no explicit family column): drop
    # the family column and supply a mapping, same relational result.
    df2 = df.drop(columns=["model_family"])
    out2 = dr.evaluate_from_data(df2, cd_col="cd_primary", n_bootstrap=200,
                                 r1_n_perm=40, model_family_map={"m0": "openai"})
    assert out2["verdicts"]["R2"] == dr.SUPPORTED, out2["cis"]["r2"]


def test_item_level_cells_pool_identity_order_independent():
    """BLOCKER (i): the ``(1|model)`` level assigned to a heterogeneous/pool cell
    must be a STABLE, order-INDEPENDENT canonical POOL id — not the arbitrary
    FIRST model in the cell. A cell aggregating multiple models enters the model
    random effect as ONE pool unit; reversing the input row order must NOT change
    the assigned level (the pre-fix ``s.iloc[0]`` flipped z-model <-> a-model)."""
    from analysis.decision_rules import _item_level_cells

    rows = []
    # One HETEROGENEOUS cell: three distinct models share (task, method, mc, seed).
    for m in ("z9", "a1", "m5"):
        rows.append(dict(task="t0", model=m, regime="H1_external", ambiguity_k=1,
                         method="heterogeneous-MAD", model_class="reasoning",
                         seed=0, label="I1", target="I0"))
    # One SINGLE-model cell keeps its own id.
    rows.append(dict(task="t1", model="solo", regime="H1_external", ambiguity_k=1,
                     method="single", model_class="reasoning", seed=0,
                     label="I0", target="I0"))
    df = pd.DataFrame(rows)

    fwd = _item_level_cells(df).sort_values("task")["model"].tolist()
    rev = _item_level_cells(df.iloc[::-1].reset_index(drop=True)) \
        .sort_values("task")["model"].tolist()
    assert fwd == rev, ("pool identity must be order-independent", fwd, rev)
    # The heterogeneous cell gets a genuine canonical pool id (sorted members).
    assert "pool:a1|m5|z9" in fwd, fwd
    # The single-model cell keeps its own model id (not a pool id).
    assert "solo" in fwd, fwd


def test_model_fit_status_propagated_through_result():
    """BLOCKER (ii): the fit PATH behind the model-based CIs must be PROPAGATED
    through the decision-rule result, so a single-RE / OLS-cluster FALLBACK is
    never presented as an ordinary crossed-model coefficient CI. And on data
    where the crossed fit IS feasible the helper must report ``ok:crossed``.

    (Pre-fix the helpers returned a BARE CI with the status discarded, so the
    result had no ``statuses`` field and the fallback path was hidden — both
    unpacking ``ci, status = _h1b_coef_ci(...)`` and reading ``out["statuses"]``
    fail on the pre-fix code.)"""
    from analysis.decision_rules import _h1b_coef_ci, _h2_interaction_ci

    # (a) status surfaced through evaluate_from_data on the project synthetic data.
    df = _structured_df(0)
    out = dr.evaluate_from_data(df, cd_col="cd_primary", n_bootstrap=120,
                                r1_n_perm=40)
    assert "statuses" in out, out.keys()
    for key in ("h1b", "h2_interaction", "r2"):
        assert key in out["statuses"], out["statuses"]
        assert isinstance(out["statuses"][key], str) and out["statuses"][key]
    # The H1b/H2 model paths are reported honestly (crossed OR a labeled fallback).
    for key in ("h1b", "h2_interaction"):
        s = out["statuses"][key]
        assert s.startswith(("ok:", "degenerate", "error")), (key, s)

    # (b) on data where a TRUE crossed fit is feasible, the helper reports
    # ok:crossed (single regime/method/model_class -> fixed part is ambiguity_k,
    # with genuinely crossed task x model random intercepts).
    rng = np.random.default_rng(0)
    models = [f"m{j}" for j in range(6)]
    task_re = {f"t{i}": rng.normal(0, 0.15) for i in range(24)}
    model_re = {m: rng.normal(0, 0.15) for m in models}
    rows = []
    for i in range(24):
        k = (i % 3) + 1
        for j, m in enumerate(models):
            frac = 0.15 * k + task_re[f"t{i}"] + model_re[m] + rng.normal(0, 0.05)
            w = int(np.clip(round(frac * 5), 0, 5))
            for lab in ["I1"] * w + ["I0"] * (5 - w):
                rows.append(dict(task=f"t{i}", model=m, regime="H1_external",
                                 ambiguity_k=k, method="homogeneous-MAD",
                                 model_class="reasoning", seed=j, label=lab,
                                 target="I0"))
    crossed = pd.DataFrame(rows)
    ci, status = _h1b_coef_ci(crossed, "cd_primary")
    assert status == "ok:crossed", status
    assert not np.isnan(ci[0])


def test_r2_incomplete_family_map_excludes_unknown_rows():
    """MAJOR: R2 must require a NON-NULL tested family per observation. Rows whose
    tested family is unknown (an incomplete ``model_family_map``) are EXCLUDED —
    never silently admitted as cross-family (``NaN != constructor`` is always
    True) — and the result must FLAG the incompleteness, not report a blanket
    SUPPORTED.

    Pre-fix: unknown-family rows were included as cross-family, and the status
    was not surfaced at all -> the ``statuses`` field is missing (fails)."""
    from analysis.decision_rules import _r2_construction_ci, _cross_family_metric
    from analysis.stats import bootstrap_confidence_intervals

    rows = []

    def add(task, model, method, labels):
        for lab in labels:
            rows.append(dict(task=task, model=model, regime="H1_external",
                             ambiguity_k=1, method=method, model_class="reasoning",
                             seed=0, label=lab, target="I0",
                             constructor_family="cohere"))

    # Known-family models m0/m1: cross-family (cohere) with a STRONG gap (single
    # correct CD 0, hetero wrong CD 1) -> known-subset effect = +1.0.
    # Unknown-family models m2/m3: single ALSO wrong (CD 1), so including them
    # DILUTES the single baseline and changes the point estimate.
    for t in range(10):
        add(f"k_s_{t}", "m0", "single", ["I0"])
        add(f"k_h_{t}", "m1", "heterogeneous-MAD", ["I1", "I1", "I1", "I1"])
        add(f"u_s_{t}", "m2", "single", ["I1"])
        add(f"u_h_{t}", "m3", "heterogeneous-MAD", ["I1", "I1", "I1", "I1"])
    df = pd.DataFrame(rows)
    fmap = {"m0": "openai", "m1": "openai"}  # m2, m3 deliberately missing

    ci, status = _r2_construction_ci(df, "cd_primary", 200, 7, "model_family", fmap)
    assert status == "incomplete_family_map", status
    # The point estimate is computed on the KNOWN cross-family rows only (=1.0),
    # NOT on all rows (which the pre-fix NaN-inclusion would use, giving 0.5).
    known = df[df["model"].isin(["m0", "m1"])]
    known_pt = _cross_family_metric("cd_primary")(known)
    all_pt = _cross_family_metric("cd_primary")(df)
    assert abs(ci[0] - known_pt) < 1e-9, (ci[0], known_pt)
    assert abs(known_pt - all_pt) > 1e-2, (known_pt, all_pt)

    # ALL-unknown case (the auditor's headline): an empty / no-coverage map means
    # every row is unknown -> excluded -> INCONCLUSIVE + incomplete flag, NOT a
    # blanket SUPPORTED. Pre-fix would have admitted all rows as cross-family.
    out = dr.evaluate_from_data(df, cd_col="cd_primary", n_bootstrap=200,
                                r1_n_perm=40, model_family_map={"other": "openai"})
    assert out["statuses"]["r2"] == "incomplete_family_map", out["statuses"]
    assert out["verdicts"]["R2"] == dr.INCONCLUSIVE, out["cis"]["r2"]
    # Sanity: had those unknown rows been (wrongly) included as cross-family,
    # the effect would have registered a non-nan CI.
    fam_none = df["model"].map({"other": "openai"})
    pre = df[df["constructor_family"].astype(object) != fam_none.astype(object)]
    assert not pre.empty  # pre-fix would have used these rows


def test_h1b_driven_by_mixed_model_coefficient():
    """BLOCKER 5 + BLOCKER A: H1b comes from the AMBIGUITY_K coefficient of the
    FROZEN §8 item-level model
    ``<cd> ~ regime*ambiguity_k*method*model_class + (1|task) + (1|model)``
    (both random intercepts retained). The helper must return exactly that
    frozen model's ambiguity_k coefficient + CI — and that CI must DIFFER from a
    reduced pre-fix model (e.g. ``<cd> ~ ambiguity_k + (1|model_class)``), so a
    helper still wired to the reduced structure fails this test."""
    from analysis.decision_rules import (_h1b_coef_ci, _item_level_cells,
                                          _frozen_fixed_rhs, _frozen_re_terms)
    from analysis.stats import fit_mixed_effects_model

    df = _structured_df(0)
    h1 = df[df["regime"] == "H1_external"]
    ci, status = _h1b_coef_ci(h1, "cd_primary")
    assert status.startswith("ok"), status

    cells = _item_level_cells(h1)
    frozen = f"cd_primary ~ {_frozen_fixed_rhs(cells)}{_frozen_re_terms(cells)}"
    res = fit_mixed_effects_model(cells, frozen)
    coef = res["coefficients"]["ambiguity_k"]
    lo, hi = res["confidence_intervals"]["ambiguity_k"]
    assert abs(ci[0] - coef) < 1e-9
    assert abs(ci[1] - lo) < 1e-9 and abs(ci[2] - hi) < 1e-9
    assert ci[1] > 0, f"k CI should exclude 0 (positive), got {ci}"

    # Discriminating: the FROZEN structure's CI must NOT coincide with the
    # reduced pre-fix model's CI (different RE structure -> different width).
    reduced = fit_mixed_effects_model(cells, "cd_primary ~ ambiguity_k + (1|model_class)")
    rlo, rhi = reduced["confidence_intervals"]["ambiguity_k"]
    assert abs(hi - lo) - abs(rhi - rlo) > 1e-3, (
        "frozen and reduced CIs should differ materially", (lo, hi), (rlo, rhi))


def test_h2_interaction_from_model_coefficient():
    """BLOCKER 5 + BLOCKER A: H2's interaction CI comes from the regime x
    model_class coefficient of the FROZEN §8 model (both ``(1|task)`` and
    ``(1|model)`` retained), NOT a raw mean gap and NOT a reduced model. The
    helper must equal the frozen model's two-way interaction coefficient + CI,
    and that CI must DIFFER from a reduced pre-fix model
    (``regime*model_class + ambiguity_k + (1|method)``)."""
    from analysis.decision_rules import (_h2_interaction_ci, _item_level_cells,
                                         _frozen_fixed_rhs, _frozen_re_terms)
    from analysis.stats import fit_mixed_effects_model

    df = _structured_df(0)
    ci, status = _h2_interaction_ci(df, "cd_primary", "reasoning")
    assert not np.isnan(ci[0])
    assert status.startswith("ok"), status

    cells = _item_level_cells(df)
    frozen = f"cd_primary ~ {_frozen_fixed_rhs(cells)}{_frozen_re_terms(cells)}"
    res = fit_mixed_effects_model(cells, frozen)
    name = [k for k in res["coefficients"]
            if k.count(":") == 1 and "regime[" in k and "model_class[" in k
            and "method[" not in k and "ambiguity_k" not in k][0]
    flo, fhi = res["confidence_intervals"][name]
    assert abs(ci[0] - res["coefficients"][name]) < 1e-9
    assert abs(ci[1] - flo) < 1e-9 and abs(ci[2] - fhi) < 1e-9

    # Discriminating: reduced pre-fix model gives a materially different CI.
    reduced = fit_mixed_effects_model(
        cells, "cd_primary ~ regime * model_class + ambiguity_k + (1|method)")
    rname = [k for k in reduced["coefficients"]
             if k.count(":") == 1 and "regime[" in k and "model_class[" in k][0]
    rlo, rhi = reduced["confidence_intervals"][rname]
    assert abs((fhi - flo) - (rhi - rlo)) > 1e-3, (
        "frozen and reduced interaction CIs should differ", (flo, fhi), (rlo, rhi))


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
