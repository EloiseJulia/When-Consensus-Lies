"""Tests for bench/r2_xf — Amendment 10 R2 cross-family construction subset.

The r2_xf items are Anthropic claude-opus-4.8-constructed H1_external traps with
I0 = the NATURAL DEFAULT (which survives deletion of the disambiguating clause)
and one foil per binary convention axis. Coverage:
  - 100% deterministic distinguishability (executable gold + mandatory foils)
  - unique target I0
  - Amdt-03 per-variant invariant len(key_questions)==k==len(interpretations)-1
  - k0 control has EMPTY key_questions and a single I0 interpretation
  - every item carries regime="H1_external" and the r2xf_ id prefix
  - the natural-default I0 is uniquely identified (a foil answer fails the I0 gold)
  - analysis/io.py constructor_family plumbing (additive, byte-identical default)
"""

import json
from pathlib import Path

import pytest

from bench.r2_xf import (
    CHECKERS,
    REFERENCE_CANDIDATES,
    CHECK_SPECS,
    generate_tasks,
    get_checkers_and_candidates,
)
from bench.validate import validate_task
from common.schema import Interpretation, Task


# ── benchmark-structure tests ─────────────────────────────────────────────────

def test_checkers_exist():
    """All 12 interpretation checker ids are present with reference candidates."""
    required = [
        "r2xf_sort_native", "r2xf_sort_ci",
        "r2xf_wc_default", "r2xf_wc_singlespace",
        "r2xf_median_mean", "r2xf_median_lower",
        "r2xf_roundmean_even", "r2xf_roundmean_up",
        "r2xf_days_exclusive", "r2xf_days_inclusive",
        "r2xf_speed_arith", "r2xf_speed_harmonic",
    ]
    for cid in required:
        assert cid in CHECKERS, f"missing checker: {cid}"
        assert cid in REFERENCE_CANDIDATES, f"missing reference: {cid}"
    assert set(CHECK_SPECS) == set(required)


def test_task_count_and_prefix():
    """12 tasks (6 families x {k0, k1}); every id carries the r2xf_ prefix."""
    tasks = generate_tasks()
    assert len(tasks) == 12
    for t in tasks:
        assert t.id.startswith("r2xf_"), f"{t.id}: R2 items must be r2xf_-prefixed"


def test_all_items_h1_external():
    """R2 items are H1_external (external disambiguator), never H2 or untagged."""
    for t in generate_tasks():
        assert t.regime == "H1_external", f"{t.id}: regime={t.regime!r}"


def test_key_questions_invariant():
    """Per-variant invariant: len(key_questions)==k==len(interpretations)-1.

    k0 control: EMPTY key_questions + a single target I0 interpretation.
    """
    tasks = generate_tasks()
    assert tasks
    for t in tasks:
        k = t.ambiguity_level
        assert len(t.key_questions) == k, f"{t.id}: kq={t.key_questions}"
        assert len(t.interpretations) - 1 == k, f"{t.id}: interps"
        targets = [i for i in t.interpretations if i.is_target]
        assert len(targets) == 1 and targets[0].id == "I0", f"{t.id}: unique I0"
        if k == 0:
            assert t.key_questions == [], f"{t.id}: k0 must have empty key_questions"
            assert len(t.interpretations) == 1, f"{t.id}: k0 must have 1 interp"
            assert t.interpretations[0].is_target


def test_k0_and_k1_present_per_family():
    """Each family emits exactly one k0 control and one k1 trap."""
    tasks = generate_tasks()
    k0 = sorted(t.id for t in tasks if t.ambiguity_level == 0)
    k1 = sorted(t.id for t in tasks if t.ambiguity_level == 1)
    assert len(k0) == 6 and len(k1) == 6
    assert all(t.id.endswith("_k0") for t in tasks if t.ambiguity_level == 0)


def test_k1_has_single_combined_default_foil():
    """Every k1 trap surfaces exactly one [combined-default] foil (__combdef)."""
    for t in generate_tasks():
        if t.ambiguity_level == 1:
            combdef = [i for i in t.interpretations
                       if i.gold_check.endswith("__combdef")]
            assert len(combdef) == 1, f"{t.id}: combdef={combdef}"


def test_distinguishability():
    """Executable-gold + mandatory foils => 100% deterministic distinguishability.

    Each interpretation's reference candidate matches ONLY its own checker, and
    every near-miss foil matches AT MOST ONE checker.
    """
    for t in generate_tasks():
        checkers, candidates, foils = get_checkers_and_candidates("r2_xf", t)
        result = validate_task(
            t, checkers, candidates, foils=foils, require_foils=True
        )
        assert result["distinguishable"], f"{t.id}: {result['errors']}"


def test_natural_default_i0_uniquely_identified():
    """The target I0 = natural default; a foil answer must FAIL the I0 checker.

    Guards the H1 construction: I0 (default) and the foil (one-axis deviation)
    are gold-distinct, so a converged-on-foil consensus is scored as NOT-I0.
    """
    for t in generate_tasks():
        if t.ambiguity_level != 1:
            continue
        checkers, candidates, _ = get_checkers_and_candidates("r2_xf", t)
        i0 = next(i.id for i in t.interpretations if i.is_target)
        foil = next(i.id for i in t.interpretations if not i.is_target)
        # I0 reference matches I0 checker; foil reference fails the I0 checker.
        assert checkers[i0].check(candidates[i0]).passed, f"{t.id}: I0 ref"
        assert not checkers[i0].check(candidates[foil]).passed, \
            f"{t.id}: foil answer must not satisfy the I0 target gold"


# ── analysis/io.py constructor_family plumbing (Amendment 10) ──────────────────

def _task(task_id: str) -> Task:
    return Task(
        id=task_id,
        domain="policy_qa",
        prompt="p",
        latent_spec="s",
        interpretations=[
            Interpretation(id="I0", is_target=True, gold_check="g0"),
            Interpretation(id="I1", is_target=False, gold_check="g1"),
        ],
        ambiguity_level=1,
        key_questions=["q?"],
        regime="H1_external",
    )


def _write_checkpoint(path: Path, task_ids) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for tid in task_ids:
            fh.write(json.dumps({
                "type": "run",
                "task_id": tid,
                "config": "single",
                "model_id": "gpt-5.4",
                "label": "I0",
                "seed": 0,
                "replicate_seed": 0,
            }) + "\n")


def test_io_constructor_family_derivation(tmp_path):
    """include_constructor_family=True populates the column from the id prefix."""
    from analysis.io import load_runs_tidy, _derive_constructor_family

    assert _derive_constructor_family("r2xf_code_sort_001_k1_case_convention") == \
        "anthropic/claude-opus-4.8"
    assert _derive_constructor_family("policy_overtime_001_k1") == "mai-code"

    ckpt = tmp_path / "ckpt.jsonl"
    tasks = [_task("r2xf_policy_days_001_k1_day_count"), _task("policy_tip_001_k1")]
    _write_checkpoint(ckpt, [t.id for t in tasks])

    df = load_runs_tidy(ckpt, tasks, include_constructor_family=True)
    assert "constructor_family" in df.columns
    fam = dict(zip(df["task"], df["constructor_family"]))
    assert fam["r2xf_policy_days_001_k1_day_count"] == "anthropic/claude-opus-4.8"
    assert fam["policy_tip_001_k1"] == "mai-code"


def test_io_default_is_byte_identical(tmp_path):
    """Default call (flag off) is byte-identical: NO constructor_family column,
    and existing columns are unchanged."""
    from analysis.io import load_runs_tidy
    from analysis.contrasts import COLS

    ckpt = tmp_path / "ckpt.jsonl"
    tasks = [_task("r2xf_policy_days_001_k1_day_count"), _task("policy_tip_001_k1")]
    _write_checkpoint(ckpt, [t.id for t in tasks])

    df_default = load_runs_tidy(ckpt, tasks)
    assert "constructor_family" not in df_default.columns

    expected_cols = [COLS["item"], COLS["method"], COLS["model_class"],
                     COLS["seed"], COLS["label"], COLS["target"], COLS["regime"],
                     COLS["ambiguity_k"], "model"]
    assert list(df_default.columns) == expected_cols

    # The additive flag must not perturb any existing column's values.
    df_flag = load_runs_tidy(ckpt, tasks, include_constructor_family=True)
    for col in expected_cols:
        assert list(df_flag[col]) == list(df_default[col]), f"column {col} changed"
