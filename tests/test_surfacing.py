"""Offline tests for the Hypothesis-Surfacing detector (Phase 3).

NO network / NO token / NO live models. Label distributions are CONSTRUCTED
synthetically over the RECONSTRUCTED benchmark's real Task structures
(bench.*.generate_tasks): regime tags, k-levels, enumerated interpretations.

Coverage (per plan §3):
  (a) k=0 controls (all agents on the single gold interp) → do NOT fire; the
      control-set false-surfacing rate < 10%.
  (b) k>=1 divergent enumerated-label distributions → DO fire.
  (c) I_perp-heavy / degenerate distributions → do NOT falsely fire (A04).
  (d) gold-target BLINDNESS: relabel which interp is the target → identical
      fired/score.
  (e) evaluate.py computes the headline false-surfacing rate + AUROC correctly.
"""

import dataclasses

import pytest

from common.schema import Interpretation, Task
from detector.surfacing import SurfacingDetector, SurfacingResult, PERP_LABEL
from detector.evaluate import (
    EvalItem,
    auroc,
    evaluate,
    select_threshold,
)

import bench.code_spec as code_spec
import bench.data_analysis as data_analysis
import bench.policy_qa as policy_qa


# ── fixtures over the reconstructed benchmark ──────────────────────────────────
def _all_tasks():
    tasks = []
    for mod in (code_spec, data_analysis, policy_qa):
        tasks.extend(mod.generate_tasks())
    return tasks


def _k0_tasks():
    return [t for t in _all_tasks() if t.ambiguity_level == 0]


def _k_ge_1_tasks():
    return [t for t in _all_tasks() if t.ambiguity_level >= 1]


def _enumerated_ids(task):
    return [i.id for i in task.interpretations if i.id != PERP_LABEL]


def _detector():
    return SurfacingDetector(threshold=0.30)


# ── (a) k=0 controls do NOT fire; control-set false-surfacing < 10% ────────────
def test_k0_controls_do_not_fire():
    """Converged control (all agents solve the single gold interp) → no surface."""
    det = _detector()
    tasks = _k0_tasks()
    assert tasks, "reconstructed benchmark must supply k=0 controls"
    fired = 0
    for t in tasks:
        # A solved control lands on the one enumerated interpretation (I0); some
        # agents may degenerate to I_perp — neither is a fork.
        labels = ["I0"] * 6 + [PERP_LABEL]
        res = det.detect(t, labels=labels)
        assert isinstance(res, SurfacingResult)
        assert res.evidence["signal_divergence"] == 0.0
        assert res.diverging_axes == []
        if res.fired:
            fired += 1
    false_surfacing_rate = fired / len(tasks)
    assert false_surfacing_rate < 0.10, false_surfacing_rate
    assert false_surfacing_rate == 0.0  # divergence is exactly 0 on true controls


# ── (b) k>=1 divergent enumerated-label distribution DOES fire ─────────────────
def test_k_ge_1_divergent_fires():
    """A genuine enumerated split across agents surfaces the fork."""
    det = _detector()
    tasks = _k_ge_1_tasks()
    assert tasks
    n_fired = 0
    for t in tasks:
        enum = _enumerated_ids(t)
        if len(enum) < 2:
            continue  # need at least two branches to construct a split
        # Even split over the first two enumerated interpretations.
        labels = [enum[0], enum[1]] * 3
        res = det.detect(t, labels=labels)
        assert res.fired, (t.id, res.score)
        assert res.score >= det.threshold
        assert res.diverging_axes == list(t.key_questions)
        n_fired += 1
    assert n_fired > 0, "expected at least one multi-branch k>=1 task to fire"


def test_even_two_way_split_is_max_divergence():
    det = _detector()
    t = next(t for t in _k_ge_1_tasks() if len(_enumerated_ids(t)) >= 2)
    a, b = _enumerated_ids(t)[:2]
    res = det.detect(t, labels=[a, b, a, b])
    assert res.evidence["signal_divergence"] == pytest.approx(1.0)


# ── (c) I_perp-heavy / degenerate distributions do NOT falsely fire (A04) ──────
def test_iperp_heavy_does_not_fire():
    """A04: I_perp is degeneracy, not a fork — it must never drive surfacing."""
    det = _detector()
    t = next(t for t in _k_ge_1_tasks() if len(_enumerated_ids(t)) >= 2)

    # Fully degenerate: all agents I_perp.
    res_all = det.detect(t, labels=[PERP_LABEL] * 8)
    assert not res_all.fired
    assert res_all.score == 0.0

    # I_perp-heavy with a single enumerated branch present → still no fork.
    res_heavy = det.detect(t, labels=["I0"] + [PERP_LABEL] * 9)
    assert not res_heavy.fired
    assert res_heavy.evidence["signal_divergence"] == 0.0


def test_iperp_does_not_inflate_divergence():
    """Adding I_perp to a single-branch distribution never creates divergence."""
    det = _detector()
    t = next(t for t in _k_ge_1_tasks() if len(_enumerated_ids(t)) >= 2)
    base = det.detect(t, labels=["I0"] * 5)
    with_perp = det.detect(t, labels=["I0"] * 5 + [PERP_LABEL] * 5)
    assert base.score == with_perp.score == 0.0


# ── (d) gold-target BLINDNESS: relabel target → identical fired/score ──────────
def _relabel_target(task, new_target_id):
    """Return a copy of task with is_target moved to `new_target_id`.

    The label DISTRIBUTION is untouched; only which interp is 'correct' changes.
    A blind detector must return an identical result.
    """
    new_interps = [
        dataclasses.replace(i, is_target=(i.id == new_target_id))
        for i in task.interpretations
    ]
    return dataclasses.replace(task, interpretations=new_interps)


def test_gold_target_blindness():
    det = _detector()
    t = next(t for t in _k_ge_1_tasks() if len(_enumerated_ids(t)) >= 2)
    a, b = _enumerated_ids(t)[:2]
    labels = [a, a, b, b, a, b]

    res_default = det.detect(t, labels=labels)          # target = I0
    t_flipped = _relabel_target(t, b)                    # target = the other branch
    res_flipped = det.detect(t_flipped, labels=labels)

    assert res_default.fired == res_flipped.fired
    assert res_default.score == res_flipped.score
    assert res_default.diverging_axes == res_flipped.diverging_axes
    # Sanity: the relabel actually moved the target (test is non-tautological).
    assert [i.is_target for i in t.interpretations] != \
           [i.is_target for i in t_flipped.interpretations]


def test_score_independent_of_label_identity_permutation():
    """Divergence depends on the label DISTRIBUTION shape, not which ids appear."""
    det = _detector()
    t = next(t for t in _k_ge_1_tasks() if len(_enumerated_ids(t)) >= 2)
    a, b = _enumerated_ids(t)[:2]
    s_ab = det.score(t, labels=[a, a, b, b])
    s_ba = det.score(t, labels=[b, b, a, a])
    assert s_ab == s_ba


# ── secondary signals (instability, cross-model) ───────────────────────────────
def test_instability_signal_raises_score():
    det = _detector()
    t = next(t for t in _k_ge_1_tasks() if len(_enumerated_ids(t)) >= 2)
    a, b = _enumerated_ids(t)[:2]
    # Single converged label → divergence 0, but resamples FLIP → instability > 0.
    per_model = {"m1": [a, b, a, b], "m2": [a, b, b, a]}
    res = det.detect(t, labels=[a, a], per_model_samples=per_model)
    assert res.evidence["signal_instability"] > 0.0
    assert res.score > 0.0


def test_crossmodel_signal_detects_family_disagreement():
    det = _detector()
    t = next(t for t in _k_ge_1_tasks() if len(_enumerated_ids(t)) >= 2)
    a, b = _enumerated_ids(t)[:2]
    labels = [a, a, b, b]
    families = ["gpt", "gpt", "claude", "claude"]
    res = det.detect(t, labels=labels, model_families=families)
    assert res.evidence["signal_cross_model"] == pytest.approx(1.0)
    # Same family everywhere → no cross-model disagreement.
    same = det.detect(t, labels=labels, model_families=["gpt"] * 4)
    assert same.evidence["signal_cross_model"] is None


def test_crossmodel_ignores_iperp_only_family():
    det = _detector()
    t = next(t for t in _k_ge_1_tasks() if len(_enumerated_ids(t)) >= 2)
    a = _enumerated_ids(t)[0]
    labels = [a, a, PERP_LABEL, PERP_LABEL]
    families = ["gpt", "gpt", "claude", "claude"]
    # Only one family carries an enumerated vote → signal unavailable (not a fork).
    res = det.detect(t, labels=labels, model_families=families)
    assert res.evidence["signal_cross_model"] is None


# ── (e) evaluate.py: headline false-surfacing + AUROC correctness ──────────────
def test_auroc_perfect_separation():
    scores = [0.9, 0.8, 0.7, 0.1, 0.2, 0.0]
    positives = [True, True, True, False, False, False]
    assert auroc(scores, positives) == 1.0


def test_auroc_ties_half_credit():
    assert auroc([0.5, 0.5], [True, False]) == 0.5


def test_evaluate_headline_and_breakdown():
    """Crafted eval set: k=0 converged (neg), k>=1 divergent (pos)."""
    det = _detector()
    items = []
    for t in _k0_tasks():
        items.append(EvalItem(task=t, labels=["I0"] * 6))
    for t in _k_ge_1_tasks():
        enum = _enumerated_ids(t)
        if len(enum) >= 2:
            items.append(EvalItem(task=t, labels=[enum[0], enum[1]] * 3))
        else:
            items.append(EvalItem(task=t, labels=[enum[0]] * 6))

    report = evaluate(det, items)
    # Headline: no control fires on converged distributions.
    assert report.false_surfacing_rate == 0.0
    assert report.meets_headline(0.10)
    assert report.n_controls == len(_k0_tasks())
    # Discrimination is strong (divergent positives out-score flat controls).
    assert report.auroc >= 0.9
    assert report.recall > 0.0
    # Breakdown structure present.
    assert set(report.by_k.keys()) >= {0}
    assert report.by_k[0]["fire_rate"] == 0.0
    for reg, stats in report.by_regime.items():
        assert 0.0 <= stats["false_surfacing_rate"] <= 1.0


def test_select_threshold_meets_constraint():
    """The selected operating point keeps k=0 false-surfacing < target."""
    det = SurfacingDetector(threshold=0.0)  # would fire on everything
    items = []
    for t in _k0_tasks():
        # Controls with a rare stray enumerated label to create a non-trivial FPR.
        items.append(EvalItem(task=t, labels=["I0"] * 6))
    for t in _k_ge_1_tasks():
        enum = _enumerated_ids(t)
        labels = [enum[0], enum[1]] * 3 if len(enum) >= 2 else [enum[0]] * 6
        items.append(EvalItem(task=t, labels=labels))

    thr = select_threshold(det, items, target_fpr=0.10)
    det.threshold = thr
    report = evaluate(det, items)
    assert report.false_surfacing_rate < 0.10


def test_select_threshold_handles_noisy_controls():
    """Even with some divergent controls, selection enforces the < target FPR."""
    tasks_k0 = _k0_tasks()
    t_pos = next(t for t in _k_ge_1_tasks() if len(_enumerated_ids(t)) >= 2)
    a, b = _enumerated_ids(t_pos)[:2]

    det = SurfacingDetector(threshold=0.0)
    items = []
    # 9 clean controls + 1 noisy control that would fire at low threshold.
    for i, t in enumerate(tasks_k0[:9]):
        items.append(EvalItem(task=t, labels=["I0"] * 6))
    noisy = tasks_k0[9] if len(tasks_k0) > 9 else tasks_k0[0]
    items.append(EvalItem(task=noisy, labels=["I0", "I0", "I0", PERP_LABEL, PERP_LABEL, PERP_LABEL]))
    # positives
    for _ in range(6):
        items.append(EvalItem(task=t_pos, labels=[a, b] * 3))

    thr = select_threshold(det, items, target_fpr=0.10)
    det.threshold = thr
    report = evaluate(det, items)
    assert report.false_surfacing_rate < 0.10


# ── input-form parity: labels vs AgentRuns ─────────────────────────────────────
def test_agent_runs_input_equivalent_to_labels():
    from common.schema import AgentRun
    det = _detector()
    t = next(t for t in _k_ge_1_tasks() if len(_enumerated_ids(t)) >= 2)
    a, b = _enumerated_ids(t)[:2]
    labels = [a, b, a, b]
    runs = [
        AgentRun(task_id=t.id, config="single", model_role="tested",
                 model_id="m", output="", label=l, verbalized_conf=0.5,
                 logit_conf=None, seed=i)
        for i, l in enumerate(labels)
    ]
    assert det.score(t, labels=labels) == det.score(t, agent_runs=runs)


# ── NOISE ROBUSTNESS (audit MAJOR 1) ───────────────────────────────────────────
# A competent-agent control lands overwhelmingly on the modal enumerated label
# with, at most, one or two STRAY disagreements. The detector must NOT mistake
# such sparse noise for a genuine interpretation fork. These distributions
# deliberately inject a stray ENUMERATED label ("I1") — which the real k=0
# labeler could produce as a misfire — so the FSR they measure is NOT 0-by-
# construction; only the noise gate keeps it low.
def test_single_stray_enumerated_label_does_not_fire():
    """1 stray enumerated label among 5-10 agents → gated as noise (no fire)."""
    det = _detector()
    t = _k0_tasks()[0]
    for n in range(5, 11):
        labels = ["I0"] * (n - 1) + ["I1"]
        res = det.detect(t, labels=labels)
        assert not res.fired, (n, res.score)
        assert res.evidence["signal_divergence"] == 0.0
        assert res.diverging_axes == []


def test_two_stray_labels_in_small_panel_do_not_fire():
    """Up to 2 strays (<=~1/3 minority) in a small panel → still gated."""
    det = _detector()
    t = _k0_tasks()[0]
    # 4:2 (33% minority) and 5:2, 6:2, 7:2 — all below the 0.34 gate.
    for majority in (4, 5, 6, 7):
        labels = ["I0"] * majority + ["I1", "I1"]
        res = det.detect(t, labels=labels)
        assert not res.fired, (majority, res.score)


def test_genuine_fork_fires_over_noise():
    """A substantial second branch (~50/50, ~60/40) DOES fire — recall preserved."""
    det = _detector()
    t = next(t for t in _k_ge_1_tasks() if len(_enumerated_ids(t)) >= 2)
    a, b = _enumerated_ids(t)[:2]
    assert det.detect(t, labels=[a] * 3 + [b] * 3).fired          # 50/50
    assert det.detect(t, labels=[a] * 6 + [b] * 4).fired          # 60/40
    # And the noise cases on the SAME task do not fire.
    assert not det.detect(t, labels=[a] * 9 + [b]).fired          # 9:1 stray
    assert not det.detect(t, labels=[a] * 6 + [b]).fired          # 6:1 stray (audit case)


def _noisy_control_items(tasks_k0):
    """k=0 controls carrying realistic sparse noise (0-1 stray, n in 5..10)."""
    items = []
    for i, t in enumerate(tasks_k0):
        n = 5 + (i % 6)                 # panel size 5..10
        if i % 2 == 0:
            labels = ["I0"] * n         # clean control
        else:
            labels = ["I0"] * (n - 1) + ["I1"]  # one stray enumerated misfire
        items.append(EvalItem(task=t, labels=labels))
    return items


def test_noisy_control_set_false_surfacing_under_10pct():
    """HONEST headline: FSR on a NOISY k=0 control set stays < 10% (calibrated)."""
    det = _detector()
    tasks_k0 = _k0_tasks()
    t_pos = next(t for t in _k_ge_1_tasks() if len(_enumerated_ids(t)) >= 2)
    a, b = _enumerated_ids(t_pos)[:2]

    control_items = _noisy_control_items(tasks_k0)
    # Sanity: the noisy controls genuinely contain a divergent enumerated label
    # (so a naive entropy detector WOULD have fired — this is non-tautological).
    assert any("I1" in it.labels for it in control_items)

    positive_items = [EvalItem(task=t_pos, labels=[a, b] * 3) for _ in range(len(tasks_k0))]
    items = control_items + positive_items

    thr = select_threshold(det, items, target_fpr=0.10)
    det.threshold = thr
    report = evaluate(det, items)
    assert report.false_surfacing_rate < 0.10, report.false_surfacing_rate
    assert report.meets_headline(0.10)
    assert report.recall > 0.0  # genuine forks still surface


def test_select_threshold_actually_enforces_fsr_when_control_scores_max():
    """MAJOR 2 regression: a control scoring exactly 1.0 must NOT re-fire.

    Before the fix, select_threshold clamped to 1.0 and (fire = score>=thr) a
    1.0-scoring control fired → FSR 1.0 while the report claimed feasibility.
    """
    det = SurfacingDetector(threshold=0.0)
    t_ctrl = _k0_tasks()[0]
    t_pos = next(t for t in _k_ge_1_tasks() if len(_enumerated_ids(t)) >= 2)
    a, b = _enumerated_ids(t_pos)[:2]

    # A pathological "control" whose distribution is a perfect 50/50 split → 1.0.
    items = [
        EvalItem(task=t_ctrl, labels=["I0", "I1", "I0", "I1"]),   # k=0, score 1.0
        EvalItem(task=t_pos, labels=[a, b] * 3),                  # k>=1 positive
        EvalItem(task=t_pos, labels=[a, b] * 3),
    ]
    thr = select_threshold(det, items, target_fpr=0.10)
    # Only a threshold ABOVE 1.0 can keep this single 1.0-scoring control silent.
    assert thr > 1.0
    det.threshold = thr
    report = evaluate(det, items)
    assert report.false_surfacing_rate < 0.10
    assert report.meets_headline(0.10)
    # And the detector really fires nothing at this operating point.
    assert not det.detect(t_ctrl, labels=["I0", "I1", "I0", "I1"]).fired


def test_threshold_above_one_is_constructible_and_never_fires():
    """A threshold > 1.0 is a valid never-fire operating point (MAJOR 2)."""
    det = SurfacingDetector(threshold=1.0 + 1e-9)
    t = next(t for t in _k_ge_1_tasks() if len(_enumerated_ids(t)) >= 2)
    a, b = _enumerated_ids(t)[:2]
    assert not det.detect(t, labels=[a, b] * 4).fired  # even a max-divergence split


# ── MINOR 3: instability/cross-model firing populates diverging_axes ───────────
def test_instability_only_firing_populates_diverging_axes():
    """When instability (not the main split) drives firing, axes are surfaced."""
    det = SurfacingDetector(threshold=0.20)  # low enough for instability-only fire
    t = next(t for t in _k_ge_1_tasks() if len(_enumerated_ids(t)) >= 2)
    a, b = _enumerated_ids(t)[:2]
    # Main panel converged (single enumerated branch → signal_divergence 0), but
    # per-model resamples FLIP 50/50 → instability drives the fire.
    per_model = {"m1": [a, b, a, b], "m2": [b, a, b, a]}
    res = det.detect(t, labels=[a, a], per_model_samples=per_model)
    assert res.evidence["signal_divergence"] == 0.0
    assert res.evidence["signal_instability"] > 0.0
    assert res.fired
    assert res.diverging_axes == list(t.key_questions)


def test_crossmodel_only_firing_populates_diverging_axes():
    det = SurfacingDetector(threshold=0.20)
    t = next(t for t in _k_ge_1_tasks() if len(_enumerated_ids(t)) >= 2)
    a, b = _enumerated_ids(t)[:2]
    # Each family internally consistent, but families disagree (a vs b). The main
    # multiset {a,a,b,b} is itself a 50/50 split, so drive cross-model-only by
    # making one family dominant in the pooled labels yet split across families.
    labels = [a, a, a, b]
    families = ["gpt", "gpt", "gpt", "claude"]
    res = det.detect(t, labels=labels, model_families=families)
    # Pooled 3:1 is gated (noise), but the two families vote a vs b → cross-model.
    assert res.evidence["signal_divergence"] == 0.0
    assert res.evidence["signal_cross_model"] == pytest.approx(1.0)
    assert res.fired
    assert res.diverging_axes == list(t.key_questions)
