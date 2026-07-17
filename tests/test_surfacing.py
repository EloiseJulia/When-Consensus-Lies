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
