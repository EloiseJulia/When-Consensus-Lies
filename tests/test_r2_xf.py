"""Tests for bench/r2_xf — Amendment 10 R2 cross-family construction subset.

The r2_xf items are Anthropic claude-opus-4.8-constructed H1_external traps with
I0 = the EXTERNAL / hidden convention (the target, which an unaware solver does
NOT produce) and one [combined-default] foil = the NATURAL DEFAULT a Python-
native solver writes once the disambiguating clause is deleted. Coverage:
  - 100% deterministic distinguishability (executable gold + mandatory foils)
  - unique target I0
  - Amdt-03 per-variant invariant len(key_questions)==k==len(interpretations)-1
  - k0 control has EMPTY key_questions and a single I0 interpretation
  - every item carries regime="H1_external" and the r2xf_ id prefix
  - target I0 (external convention) and foil (natural default) are gold-distinct
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
        "r2xf_intdiv_trunc", "r2xf_intdiv_floor",
        "r2xf_weekday_iso", "r2xf_weekday_py",
        "r2xf_argmax_1based", "r2xf_argmax_0based",
        "r2xf_sortids_numeric", "r2xf_sortids_lex",
        "r2xf_days_inclusive", "r2xf_days_exclusive",
        "r2xf_weeks_business", "r2xf_weeks_calendar",
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


def test_target_external_convention_distinct_from_default():
    """The target I0 = external convention; the foil = natural default.

    Guards the H1 construction (correct trap polarity): I0 (external convention)
    and the foil (the Python-native default an UNAWARE solver converges on) are
    gold-distinct, so a converged-on-foil consensus is scored as NOT-I0 and the
    convergent-delusion metric can fire.
    """
    for t in generate_tasks():
        if t.ambiguity_level != 1:
            continue
        checkers, candidates, _ = get_checkers_and_candidates("r2_xf", t)
        i0 = next(i.id for i in t.interpretations if i.is_target)
        foil = next(i.id for i in t.interpretations if not i.is_target)
        # I0 (external) ref matches its gold; the natural-default foil answer
        # must FAIL the I0 target gold (opposite polarity from the old bug).
        assert checkers[i0].check(candidates[i0]).passed, f"{t.id}: I0 ref"
        assert not checkers[i0].check(candidates[foil]).passed, \
            f"{t.id}: natural-default foil must not satisfy the external I0 gold"
        # And the foil reference must satisfy the foil's own (natural-default) gold.
        assert checkers[foil].check(candidates[foil]).passed, f"{t.id}: foil ref"


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

    # Canonical Anthropic family string (matches config.yaml / decision_rules namespace).
    assert _derive_constructor_family("r2xf_code_intdiv_001_k1_integer_division") == \
        "anthropic"
    assert _derive_constructor_family("policy_overtime_001_k1") == "mai-code"

    ckpt = tmp_path / "ckpt.jsonl"
    tasks = [_task("r2xf_policy_days_001_k1_day_count"), _task("policy_tip_001_k1")]
    _write_checkpoint(ckpt, [t.id for t in tasks])

    df = load_runs_tidy(ckpt, tasks, include_constructor_family=True)
    assert "constructor_family" in df.columns
    fam = dict(zip(df["task"], df["constructor_family"]))
    assert fam["r2xf_policy_days_001_k1_day_count"] == "anthropic"
    assert fam["policy_tip_001_k1"] == "mai-code"


def test_r2xf_anthropic_tested_is_same_family(tmp_path):
    """An Anthropic-tested r2xf_ row has constructor_family == tested family (SAME).

    Guards the BLOCKER fix: 'anthropic' == 'anthropic' must hold so that
    decision_rules._r2_construction_ci correctly EXCLUDES the row from the
    cross-family subset (it is same-family, not cross-family).
    """
    from analysis.io import load_runs_tidy, _derive_constructor_family

    r2_task_id = "r2xf_policy_days_001_k1_day_count"
    constructor_fam = _derive_constructor_family(r2_task_id)
    # Canonical Anthropic tested-model family (from config.yaml).
    tested_fam = "anthropic"
    assert constructor_fam == tested_fam, (
        f"Anthropic-tested r2xf_ cell must be SAME-family: "
        f"constructor={constructor_fam!r} vs tested={tested_fam!r}"
    )


def test_r2xf_openai_tested_is_cross_family(tmp_path):
    """An OpenAI-tested r2xf_ row has constructor_family != tested family (CROSS).

    Guards the core R2 control: when tested by gpt-* (family='openai'),
    the Anthropic-constructed r2xf_ items are genuinely cross-family, so the
    convergent-delusion effect on that subset is attribution-clean.
    """
    from analysis.io import _derive_constructor_family

    r2_task_id = "r2xf_code_intdiv_001_k1_integer_division"
    constructor_fam = _derive_constructor_family(r2_task_id)
    tested_fam = "openai"
    assert constructor_fam != tested_fam, (
        f"OpenAI-tested r2xf_ cell must be CROSS-family: "
        f"constructor={constructor_fam!r} vs tested={tested_fam!r}"
    )


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


# ── bench/r2_xf collision guard (Amendment 10) ───────────────────────────────

def test_register_into_host_domains_fail_closed():
    """_register_into_host_domains raises on a real host-id collision (fail-closed).

    Guards the MINOR fix: a genuine collision (a host checker already owns the id
    with a DIFFERENT object) must raise RuntimeError, not silently overwrite.
    """
    from bench.r2_xf import CHECKERS, CHECK_SPECS

    import bench.code_spec as _code

    # Pick the first code-domain r2xf checker to stage a fake collision.
    code_cids = [cid for cid, spec in CHECK_SPECS.items() if spec["kind"] == "code"]
    assert code_cids, "need at least one code-domain r2xf item"
    cid = code_cids[0]

    # Temporarily inject a foreign (different) object under the same id.
    import types
    foreign_checker = types.SimpleNamespace(check=lambda x: x)
    original = _code.CHECKERS.pop(cid, None)  # remove the real r2xf entry if present
    _code.CHECKERS[cid] = foreign_checker      # inject imposter

    try:
        with pytest.raises(RuntimeError, match="collides with a host checker id"):
            # Re-invoke the registration function; it must detect the imposter.
            from bench.r2_xf import _register_into_host_domains
            _register_into_host_domains()
    finally:
        # Restore host registry to a clean state.
        if original is not None:
            _code.CHECKERS[cid] = original
        else:
            _code.CHECKERS.pop(cid, None)


def test_register_into_host_domains_idempotent():
    """Re-importing (identical object) does NOT raise (idempotent re-registration)."""
    # bench.r2_xf is already imported; calling _register_into_host_domains again
    # should be a no-op because checkers[cid] is CHECKERS[cid] for every r2xf id.
    from bench.r2_xf import _register_into_host_domains
    _register_into_host_domains()  # must not raise
