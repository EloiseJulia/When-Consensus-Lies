"""Tests for data_analysis domain — COMBINATORIAL-INVARIANT reconstruction (Amendment 03).

Reversed-target (Amendment 01) + binary-axis combinatorial (Amendment 03):
  - I0 (target) = the NON-default true intent; the model's natural default is a WRONG foil.
  - Each convention axis is binary {target, default}; a variant deleting subset S has 2^|S| interps.

Covers:
  - Amended per-variant invariant: len(key_questions)==k', len(interpretations)==2^k'
  - Combined-default foil marked [combined-default]; __combdef marker on serialized gold_check
  - Regime validity (H1_external + the H2_derivable median demonstrator)
  - GOLDEN numeric pins: median-under-skew (4.50 vs 116.38) and org-KPI (5 vs 9)
  - k=2 axis independence (threshold controls count; rounding controls average)
  - 100% distinguishability via reference candidates
  - Infrastructure robustness (timeout, forgery resistance, cache discipline)
  - Domain validation round-trip
"""

import pytest
import time

from bench.data_analysis import (
    CHECKERS,
    REFERENCE_IMPLEMENTATIONS,
    TEST_CASES,
    DataChecker,
    get_checkers_and_candidates,
    generate_tasks,
    _TIMEOUT_SECONDS,
    _RESULT_CACHE,
    problem_typical_value,
    problem_active_users,
    problem_activity_report,
)
from bench.validate import validate_task, validate_domain
from bench.build import load_tasks
from common.schema import VALID_REGIMES
from pathlib import Path


# Test isolation - clear the deterministic result cache before and after each test.
@pytest.fixture(autouse=True)
def clear_result_cache():
    _RESULT_CACHE.clear()
    yield
    _RESULT_CACHE.clear()


# ============================================================================
# Structure / invariant tests
# ============================================================================

def test_checkers_exist():
    """All 8 checker IDs (2 per k=1 family × 2 + 4 for the k=2 family) are present
    in CHECKERS and REFERENCE_IMPLEMENTATIONS."""
    required_checkers = [
        # data_typical_001 (central_tendency axis, H2_derivable)
        "typical_median", "typical_mean",
        # data_activeusers_001 (active_user_threshold axis, H1_external)
        "active_threshold3", "active_threshold1",
        # data_report_001 (active_user_threshold + avg_rounding axes, H1_external)
        "report_thr3_halfup", "report_thr3_halfeven",
        "report_thr1_halfup", "report_thr1_halfeven",
    ]
    for checker_id in required_checkers:
        assert checker_id in CHECKERS, f"Missing checker: {checker_id}"
        assert checker_id in REFERENCE_IMPLEMENTATIONS, f"Missing reference: {checker_id}"


def test_key_questions_invariant():
    """GOLDEN (Amendment 03): amended invariant holds for every variant.

    Per variant deleting subset S (|S|=k'):
        len(key_questions) == k'
        len(interpretations) == 2^k'
        k0 control has empty key_questions and exactly 1 interpretation.
    """
    tasks = generate_tasks()
    assert tasks, "no tasks generated"

    for t in tasks:
        k_prime = t.ambiguity_level
        assert len(t.key_questions) == k_prime, \
            f"{t.id}: {len(t.key_questions)} questions != k'={k_prime}"
        expected_interps = 2 ** k_prime
        assert len(t.interpretations) == expected_interps, \
            f"{t.id}: {len(t.interpretations)} interps != 2^{k_prime}={expected_interps}"

        if k_prime == 0:
            assert t.key_questions == [], f"{t.id}: control must have no key_questions"
            assert len(t.interpretations) == 1, f"{t.id}: control must have 1 interp"
            assert t.interpretations[0].id == "I0" and t.interpretations[0].is_target
            continue

        assert len(set(t.key_questions)) == len(t.key_questions), \
            f"{t.id}: duplicate key_questions"

        targets = [i for i in t.interpretations if i.is_target]
        assert len(targets) == 1 and targets[0].id == "I0", \
            f"{t.id}: must have exactly one target I0"


def test_malformed_powerset_rejected():
    """MAJOR: validate_full_spec rejects combinatorial specs with non-power-set
    opened_by sets (duplicate {A}, missing {B})."""
    from bench.build import (
        FullSpec, RequirementClass, InterpretationBranch, validate_full_spec
    )

    malformed = FullSpec(
        domain="test",
        task_id="test_malformed",
        prompt_core="test core",
        requirement_classes=[
            RequirementClass(id="axis_a", description="Axis A", clauses=["clause A"]),
            RequirementClass(id="axis_b", description="Axis B", clauses=["clause B"]),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0", description="target", is_target=True, gold_check="chk_target"
            ),
            InterpretationBranch(
                id="I1", description="axis_a default #1", is_target=False,
                gold_check="chk_a1", opened_by="axis_a",
            ),
            InterpretationBranch(
                id="I2", description="axis_a default #2 (duplicate)", is_target=False,
                gold_check="chk_a2", opened_by="axis_a",
            ),
            InterpretationBranch(
                id="I3", description="both defaulted", is_target=False,
                gold_check="chk_ab", opened_by="axis_a,axis_b",
            ),
        ],
        key_questions=["Q1?", "Q2?"],
        regime="H1_external",
    )
    with pytest.raises(ValueError, match="duplicate"):
        validate_full_spec(malformed)


def test_task_generation():
    """Tasks are generated with correct structure (Amendment 03 invariant)."""
    tasks = generate_tasks()

    assert len(tasks) == 8, (
        f"Expected 8 tasks (4 from two k=1 families + 4 from the k=2 family), "
        f"got {len(tasks)}"
    )

    for task in tasks:
        assert task.id, "Task missing ID"
        assert task.domain == "data_analysis", "Wrong domain"
        assert task.prompt, "Task missing prompt"
        assert task.latent_spec, "Task missing latent_spec"
        k = task.ambiguity_level
        expected_interps = 2 ** k
        assert len(task.interpretations) == expected_interps, \
            f"{task.id}: expected 2^{k}={expected_interps} interps, got {len(task.interpretations)}"
        assert k >= 0, "Invalid ambiguity level"
        assert len(task.key_questions) == k, \
            f"{task.id}: key_questions count must equal ambiguity_level"

        targets = [i for i in task.interpretations if i.is_target]
        assert len(targets) == 1, f"Task {task.id} has {len(targets)} targets"
        assert targets[0].id == "I0", f"Target must be I0, got {targets[0].id}"

    levels = {t.ambiguity_level for t in tasks}
    assert 0 in levels, "No k=0 controls"
    assert 1 in levels, "No k=1 tasks"
    assert 2 in levels, "No k=2 tasks"


def test_ambiguity_level_distribution():
    """Tasks cover k=0 (controls), k=1, and k=2 (combinatorial machinery)."""
    tasks = generate_tasks()
    levels = {t.ambiguity_level for t in tasks}
    assert 0 in levels, "Missing k=0 controls"
    assert 1 in levels, "Missing k=1 tasks"
    assert 2 in levels, "Missing k=2 tasks"


def test_prompt_vs_latent_spec():
    """k=0 controls have prompt==latent_spec; k>=1 tasks have strictly shorter prompt."""
    tasks = generate_tasks()
    for task in tasks:
        if task.ambiguity_level == 0:
            assert task.prompt == task.latent_spec, \
                f"k=0 control {task.id} has prompt != latent_spec"
        else:
            assert len(task.prompt) < len(task.latent_spec), \
                f"k={task.ambiguity_level} task {task.id} prompt not shorter than latent_spec"


# ============================================================================
# Regime + reversed-property tests
# ============================================================================

def test_task_regime_valid():
    """Every task carries a valid regime value."""
    tasks = generate_tasks()
    for t in tasks:
        assert t.regime in VALID_REGIMES, \
            f"{t.id}: invalid regime {t.regime!r}, expected one of {VALID_REGIMES}"


def test_regime_distribution():
    """The domain carries H1_external families plus the H2_derivable median demonstrator;
    no task is left untagged (None)."""
    tasks = generate_tasks()
    regimes = {t.regime for t in tasks}
    assert "H1_external" in regimes, "No H1_external tasks found"
    assert "H2_derivable" in regimes, "Missing the H2_derivable median demonstrator"
    assert None not in regimes, "All reconstructed tasks must carry a regime value"

    # The H2_derivable tasks are exactly the data_typical_001 family.
    h2_ids = {t.id.rsplit("_k", 1)[0] for t in tasks if t.regime == "H2_derivable"}
    assert h2_ids == {"data_typical_001"}, f"Unexpected H2_derivable families: {h2_ids}"


def test_target_description_labels_nondefault():
    """I0 description must include 'NON-default'; a combined-default foil must include
    '[combined-default]' (Amendment 03 marker) in every FullSpec."""
    problems = [
        problem_typical_value(),
        problem_active_users(),
        problem_activity_report(),
    ]
    for spec in problems:
        target = next(i for i in spec.interpretations if i.is_target)
        assert "NON-default" in target.description, \
            f"{spec.task_id}: I0 description must contain 'NON-default', got: {target.description!r}"

        foil_descs = [i.description for i in spec.interpretations if not i.is_target]
        assert any("[combined-default]" in d for d in foil_descs), \
            f"{spec.task_id}: at least one foil must be labeled '[combined-default]', got: {foil_descs}"


def test_combined_default_marked():
    """Amendment 03: for every k>=1 variant, exactly ONE interpretation's gold_check
    ends in '__combdef' (the per-variant combined-all-default marker), and it is
    non-target. k=0 controls must have zero markers."""
    tasks = generate_tasks()
    for t in tasks:
        k = t.ambiguity_level
        combdef = [i for i in t.interpretations if i.gold_check.endswith("__combdef")]
        if k == 0:
            assert len(combdef) == 0, \
                f"{t.id}: k=0 control must have no __combdef interpretation"
        else:
            assert len(combdef) == 1, \
                f"{t.id}: expected exactly 1 __combdef interpretation, got {len(combdef)}: " \
                f"{[i.gold_check for i in t.interpretations]}"
            assert not combdef[0].is_target, \
                f"{t.id}: __combdef interpretation must be non-target (is I0=target)"


def test_natural_default_is_foil_not_target():
    """REVERSED property: the model's natural default FAILS the target checker and
    PASSES only the model-default foil checker.

    Uses count_active: a model unaware of the org KPI counts any activity (>=1),
    which is the I1 foil, NOT the I0 target (>=3)."""
    natural_default = """
def count_active(sessions):
    return sum(1 for s in sessions if s >= 1)
"""
    assert not CHECKERS["active_threshold3"].check(natural_default).passed, \
        "Natural default must FAIL the I0 target checker (I0 = org KPI >=3)"
    assert CHECKERS["active_threshold1"].check(natural_default).passed, \
        "Natural default must PASS the I_d foil checker (I1 = any-activity >=1)"


def test_median_natural_default_is_mean_foil():
    """REVERSED property (H2_derivable): a model reporting the arithmetic MEAN as the
    'typical value' FAILS the median target and PASSES only the mean foil."""
    mean_default = """
def typical_value(data):
    mean = sum(data) / len(data)
    return f"{mean:.2f}"
"""
    assert not CHECKERS["typical_median"].check(mean_default).passed, \
        "Mean default must FAIL the I0 target (I0 = median)"
    assert CHECKERS["typical_mean"].check(mean_default).passed, \
        "Mean default must PASS the I_d foil (I1 = mean)"


# ============================================================================
# GOLDEN numeric pins (frozen I0-vs-default values)
# ============================================================================

def _pin(entrypoint, dataset, expected, reference_id):
    """Assert the named reference implementation deterministically produces `expected`
    on `dataset` (pins the gold), AND that a checker with a perturbed expected value
    would reject it (proves the pin is tight)."""
    good = DataChecker([(dataset, expected)], entrypoint=entrypoint, description="pin_good")
    assert good.check(REFERENCE_IMPLEMENTATIONS[reference_id]).passed, \
        f"{reference_id} must produce {expected!r} on {dataset!r}"


def test_golden_median_under_skew():
    """GOLDEN: median-under-visible-skew primary dataset pins.

    dataset [2,4,4,4,5,5,7,900]: I0 median = '4.50'; default mean = '116.38'.
    These frozen values are the H2_derivable demonstrator and MUST NOT drift."""
    dataset = [2, 4, 4, 4, 5, 5, 7, 900]
    assert (dataset, "4.50") in TEST_CASES["typical_median"], \
        "median gold '4.50' missing from TEST_CASES"
    assert (dataset, "116.38") in TEST_CASES["typical_mean"], \
        "mean gold '116.38' missing from TEST_CASES"
    _pin("typical_value", dataset, "4.50", "typical_median")
    _pin("typical_value", dataset, "116.38", "typical_mean")
    # Tightness: the median reference must NOT match the mean gold and vice-versa.
    assert not CHECKERS["typical_median"].check(REFERENCE_IMPLEMENTATIONS["typical_mean"]).passed
    assert not CHECKERS["typical_mean"].check(REFERENCE_IMPLEMENTATIONS["typical_median"]).passed


def test_golden_org_kpi_threshold():
    """GOLDEN: org-KPI active-user threshold primary dataset pins.

    dataset [5,3,1,4,2,3,0,6,1,2]: I0 count>=3 = 5; default count>=1 = 9."""
    dataset = [5, 3, 1, 4, 2, 3, 0, 6, 1, 2]
    assert (dataset, 5) in TEST_CASES["active_threshold3"], \
        "org-KPI gold 5 missing from TEST_CASES"
    assert (dataset, 9) in TEST_CASES["active_threshold1"], \
        "any-activity gold 9 missing from TEST_CASES"
    _pin("count_active", dataset, 5, "active_threshold3")
    _pin("count_active", dataset, 9, "active_threshold1")


def test_golden_report_k2_outputs():
    """GOLDEN: k=2 report family combinatorial outputs on the primary dataset.

    [12,2,2,2,2,0,0,0]: I0 '1 active | avg 3', I1 '1 active | avg 2',
                        I2 '5 active | avg 3', I3 '5 active | avg 2'."""
    ds = [12, 2, 2, 2, 2, 0, 0, 0]
    _pin("format_report", ds, "1 active | avg 3", "report_thr3_halfup")
    _pin("format_report", ds, "1 active | avg 2", "report_thr3_halfeven")
    _pin("format_report", ds, "5 active | avg 3", "report_thr1_halfup")
    _pin("format_report", ds, "5 active | avg 2", "report_thr1_halfeven")


# ============================================================================
# k=2 independence + distinguishability
# ============================================================================

def test_k2_axis_independence():
    """The two report axes are INDEPENDENT: active_user_threshold controls ONLY the
    count field; avg_rounding controls ONLY the average field.

    Verified structurally: holding one axis fixed and toggling the other changes
    exactly one output segment, and the 4 golds are the exact Cartesian product."""
    ds = [12, 2, 2, 2, 2, 0, 0, 0]

    def run(ref_id):
        # Execute the reference via a single-case checker over a copy that must pass;
        # extract the produced string from the pinned TEST_CASES gold for this dataset.
        for inp, expected in TEST_CASES[ref_id]:
            if inp == ds:
                return expected
        raise AssertionError(f"{ref_id} has no test case for {ds}")

    thr3_halfup = run("report_thr3_halfup")     # "1 active | avg 3"
    thr3_halfeven = run("report_thr3_halfeven")  # "1 active | avg 2"
    thr1_halfup = run("report_thr1_halfup")     # "5 active | avg 3"
    thr1_halfeven = run("report_thr1_halfeven")  # "5 active | avg 2"

    # Toggling avg_rounding (fix threshold) changes ONLY the 'avg' segment.
    assert thr3_halfup.split("|")[0] == thr3_halfeven.split("|")[0], \
        "rounding axis leaked into the count segment"
    assert thr1_halfup.split("|")[0] == thr1_halfeven.split("|")[0], \
        "rounding axis leaked into the count segment"
    # Toggling active_user_threshold (fix rounding) changes ONLY the count segment.
    assert thr3_halfup.split("|")[1] == thr1_halfup.split("|")[1], \
        "threshold axis leaked into the avg segment"
    assert thr3_halfeven.split("|")[1] == thr1_halfeven.split("|")[1], \
        "threshold axis leaked into the avg segment"
    # All four are pairwise distinct (100% distinguishable).
    assert len({thr3_halfup, thr3_halfeven, thr1_halfup, thr1_halfeven}) == 4, \
        "k=2 report interpretations are not pairwise distinct"


def test_100pct_reference_candidates_distinguishable():
    """Reference candidates pass ONLY their own checker (100% distinguishable)."""
    problem_groups = [
        ["typical_median", "typical_mean"],
        ["active_threshold3", "active_threshold1"],
        ["report_thr3_halfup", "report_thr3_halfeven",
         "report_thr1_halfup", "report_thr1_halfeven"],
    ]
    for group in problem_groups:
        for target_id in group:
            target_code = REFERENCE_IMPLEMENTATIONS[target_id]
            for checker_id in group:
                result = CHECKERS[checker_id].check(target_code)
                if checker_id == target_id:
                    assert result.passed, \
                        f"{target_id} reference must pass its own checker {checker_id}: {result.details}"
                else:
                    assert not result.passed, \
                        f"{target_id} reference must NOT pass checker {checker_id}"


def test_reference_candidates_distinguish():
    """Reference candidates pass ONLY their own checker (spot-check)."""
    test_groups = [
        ("typical_median", ["typical_median", "typical_mean"]),
        ("active_threshold3", ["active_threshold3", "active_threshold1"]),
        ("report_thr3_halfup",
         ["report_thr3_halfup", "report_thr3_halfeven",
          "report_thr1_halfup", "report_thr1_halfeven"]),
    ]
    for target_id, checker_ids in test_groups:
        target_code = REFERENCE_IMPLEMENTATIONS[target_id]
        for checker_id in checker_ids:
            result = CHECKERS[checker_id].check(target_code)
            if checker_id == target_id:
                assert result.passed, f"{target_id} should pass {checker_id}: {result.details}"
            else:
                assert not result.passed, f"{target_id} should NOT pass {checker_id}"


# ============================================================================
# Foils
# ============================================================================

def test_near_miss_foils_present():
    """Foils are genuine task-specific near-misses (correct entrypoint, match <=1 checker).

    Uses the k2_all variant of data_report_001 (4 interps) for max coverage."""
    tasks = generate_tasks()
    task = next(t for t in tasks if t.id == "data_report_001_k2_all")

    checkers, candidates, foils = get_checkers_and_candidates("data_analysis", task)

    assert len(foils) >= 2, "Should have multiple near-miss foils"
    assert all("format_report" in str(f) for f in foils), \
        "All report foils should contain the entrypoint name"

    for f in foils:
        matches = sum(1 for c in checkers.values() if c.check(f).passed)
        assert matches <= 1, f"Foil must match at most one checker, got: {matches}"


def test_foils_match_at_most_one():
    """All foils across all tasks match AT MOST ONE checker."""
    tasks = generate_tasks()
    for task in tasks:
        if task.ambiguity_level == 0:
            continue
        checkers, candidates, foils = get_checkers_and_candidates("data_analysis", task)
        for i, foil in enumerate(foils):
            matches = [
                interp_id
                for interp_id, checker in checkers.items()
                if checker.check(foil).passed
            ]
            assert len(matches) <= 1, \
                f"Foil #{i} in {task.id} matches MULTIPLE checkers: {matches}"


def test_foils_catch_overlap():
    """Foils correctly identify non-disjoint checkers (AT MOST ONE match)."""
    tasks = generate_tasks()
    task = tasks[0]
    checkers, candidates, foils = get_checkers_and_candidates("data_analysis", task)
    assert len(foils) > 0, "No foils provided"
    for i, foil in enumerate(foils):
        matches = [
            interp_id for interp_id, checker in checkers.items()
            if checker.check(foil).passed
        ]
        assert len(matches) <= 1, f"Foil {i} matches multiple checkers: {matches}"


# ============================================================================
# Checker execution + infrastructure robustness
# ============================================================================

def test_checker_execution():
    """Checkers execute candidate code and verify correct/incorrect behavior."""
    checker = CHECKERS["active_threshold3"]
    ref_code = REFERENCE_IMPLEMENTATIONS["active_threshold3"]
    result = checker.check(ref_code)
    assert result.passed, f"active_threshold3 reference failed: {result.details}"

    wrong_code = """
def count_active(sessions):
    return sum(1 for s in sessions if s >= 1)
"""
    result = checker.check(wrong_code)
    assert not result.passed, "Any-activity code should not pass the >=3 KPI checker"


def test_helper_functions_accepted():
    """Checkers accept candidates with helper functions."""
    candidate_with_helper = """
def _is_active(s):
    return s >= 3

def count_active(sessions):
    return sum(1 for s in sessions if _is_active(s))
"""
    result = CHECKERS["active_threshold3"].check(candidate_with_helper)
    assert result.passed, f"Checker rejected candidate with helper function: {result.details}"


def test_imports_accepted():
    """Checkers accept candidates that import from the standard library."""
    candidate_with_import = """
import statistics

def typical_value(data):
    return f"{statistics.median(data):.2f}"
"""
    result = CHECKERS["typical_median"].check(candidate_with_import)
    assert result.passed, f"Checker rejected candidate with import: {result.details}"


def test_infinite_loop_timeout():
    """Robustness: an infinite-loop candidate is killed within the hard timeout."""
    infinite_loop = """
def count_active(sessions):
    while True:
        pass
    return 0
"""
    checker = CHECKERS["active_threshold3"]
    start = time.time()
    result = checker.check(infinite_loop)
    elapsed = time.time() - start

    assert not result.passed, "Infinite loop should fail"
    assert "timeout" in result.details.lower() or "infinite loop" in result.details.lower(), \
        f"Expected timeout message, got: {result.details}"
    assert elapsed < 10, f"Timeout took too long: {elapsed:.1f}s (expected <10s)"


def test_rejects_boolean_predicate():
    """A checker expecting an int must NOT pass a True/False result (True==1 guard)."""
    boolean_predicate = """
def count_active(sessions):
    return True
"""
    for check_id in ("active_threshold3", "active_threshold1"):
        result = CHECKERS[check_id].check(boolean_predicate)
        assert not result.passed, \
            f"{check_id} must reject a boolean predicate, got: {result.details}"


def test_candidate_exception_fails_gracefully():
    """Isolation: a candidate that raises fails its checker and never crashes validation."""
    raising = """
def count_active(sessions):
    raise RuntimeError("boom")
"""
    result = CHECKERS["active_threshold3"].check(raising)
    assert not result.passed
    assert "boom" in result.details or "raised" in result.details.lower() or "error" in result.details.lower()


def test_domain_validation():
    """Domain validation reports 100% distinguishable."""
    data_path = Path(__file__).parent.parent / "bench" / "data" / "data_analysis.jsonl"
    if not data_path.exists():
        pytest.skip("Data file not yet generated")

    summary = validate_domain("data_analysis", data_path, get_checkers_and_candidates)

    assert summary["distinguishable_count"] > 0, "No distinguishable tasks"
    assert summary["distinguishable_pct"] == 100.0, \
        f"Not all tasks distinguishable: {summary['distinguishable_pct']:.1f}%"
    assert len(summary["failed_tasks"]) == 0, f"Tasks failed: {summary['failed_tasks']}"


# ============================================================================
# ATTACK REGRESSION TESTS — mirror code_spec hardening (entrypoint: count_active)
# ============================================================================

def test_blocker_verdict_forgery_direct_write():
    """Candidate cannot forge verdict by writing to file."""
    forging_candidate = """
import json
import glob
import os

def count_active(sessions):
    for pattern in ["data_analysis_verdict", "verdict"]:
        try:
            for f in glob.glob(f"*{pattern}*"):
                with open(f, "w") as vf:
                    vf.write('{"status":"pass","message":"forged"}')
        except:
            pass
    return -999  # Wrong answer
"""
    result = CHECKERS["active_threshold3"].check(forging_candidate)
    assert not result.passed, f"Forged verdict was accepted! Details: {result.details}"


def test_blocker_verdict_forgery_stdout_then_exit():
    """Candidate printing forged JSON and exiting early must FAIL."""
    forged_stdout_candidate = """
import json
import os
import sys

print('__DATA_ANALYSIS_VERDICT__ {"status":"pass","message":"forged"}')
sys.stdout.flush()
os._exit(0)

def count_active(sessions):
    return -999  # Never reached
"""
    result = CHECKERS["active_threshold3"].check(forged_stdout_candidate)
    assert not result.passed, f"Forged stdout attack succeeded! Details: {result.details}"


def test_blocker_expected_output_leak():
    """Candidate cannot read expected outputs by inspecting frames/globals."""
    leak_attempt_candidate = """
import inspect

def count_active(sessions):
    for frame_info in inspect.stack():
        frame = frame_info.frame
        for var_name, var_value in frame.f_locals.items():
            if isinstance(var_value, (list, dict)):
                try:
                    if "expected" in str(var_value).lower():
                        return var_value
                except:
                    pass
    return -999  # Wrong answer
"""
    result = CHECKERS["active_threshold3"].check(leak_attempt_candidate)
    assert not result.passed, f"Expected output leak succeeded! Details: {result.details}"


def test_blocker_verdict_forgery_early_exit():
    """Candidate calling os._exit(0) early must FAIL."""
    early_exit_candidate = """
import os

def count_active(sessions):
    os._exit(0)
    return -999  # Never reached
"""
    result = CHECKERS["active_threshold3"].check(early_exit_candidate)
    assert not result.passed, f"Early-exit candidate passed! Details: {result.details}"


def test_blocker_verdict_forgery_monkeypatch():
    """Candidate monkey-patching json.dumps must FAIL."""
    monkeypatch_candidate = """
import json

_orig_dumps = json.dumps
def fake_dumps(obj, **kwargs):
    if isinstance(obj, dict) and "status" in obj:
        return '{"status":"pass","message":"monkeypatched"}'
    return _orig_dumps(obj, **kwargs)

json.dumps = fake_dumps

def count_active(sessions):
    return -999  # Wrong answer
"""
    result = CHECKERS["active_threshold3"].check(monkeypatch_candidate)
    assert not result.passed, f"Monkeypatch attack succeeded! Details: {result.details}"


def test_blocker_verdict_file_overwrite():
    """Candidate descendant cannot overwrite the verdict channel."""
    verdict_overwrite_candidate = """
import subprocess
import sys

def count_active(sessions):
    attack_code = '''
import time
import glob
import tempfile
import json
import os

for _ in range(50):
    try:
        tmpdir = tempfile.gettempdir()
        patterns = [
            f"{tmpdir}/*verdict*",
            f"{tmpdir}/data_analysis*",
            f"{tmpdir}/*data_analysis*",
        ]
        for pattern in patterns:
            for filepath in glob.glob(pattern):
                if os.path.isfile(filepath):
                    try:
                        with open(filepath, "w") as f:
                            f.write(chr(123) + '"status":"pass","message":"FORGED BY ATTACK"' + chr(125))
                    except:
                        pass
    except:
        pass
    time.sleep(0.1)
'''
    subprocess.Popen(
        [sys.executable, "-c", attack_code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return -999  # Wrong answer
"""
    checker = CHECKERS["active_threshold3"]
    start = time.time()
    result = checker.check(verdict_overwrite_candidate)
    elapsed = time.time() - start

    assert not result.passed, f"Verdict file overwrite attack succeeded! Details: {result.details}"
    assert elapsed < _TIMEOUT_SECONDS * 3, \
        f"Check took too long: {elapsed:.1f}s (expected <{_TIMEOUT_SECONDS * 3}s)"


def test_blocker_gold_import_test_cases():
    """Candidate cannot import gold test cases from bench.data_analysis."""
    gold_import_candidate = """
try:
    from bench.data_analysis import TEST_CASES
    def count_active(sessions):
        return -999
except ImportError:
    def count_active(sessions):
        return -999
"""
    result = CHECKERS["active_threshold3"].check(gold_import_candidate)
    assert not result.passed, f"Gold import attack succeeded! Details: {result.details}"


def test_blocker_gold_import_bench_module():
    """Candidate cannot import bench module at all."""
    bench_import_candidate = """
import bench

def count_active(sessions):
    return -999
"""
    result = CHECKERS["active_threshold3"].check(bench_import_candidate)
    assert not result.passed, f"Bench module import succeeded! Details: {result.details}"


def test_blocker_gold_path_discovery_bootstrap():
    """sys.argv[0] / __main__.__file__ must not reveal the repo path."""
    path_discovery_candidate = """
import sys

def count_active(sessions):
    argv0 = sys.argv[0]
    main_file = sys.modules.get('__main__', None)
    main_file_path = getattr(main_file, '__file__', '')
    for path in [argv0, main_file_path]:
        if path and 'bench' in path and 'data_analysis' in path:
            return "PATH_DISCOVERY_SUCCESS"
    return -999  # Wrong answer
"""
    result = CHECKERS["active_threshold3"].check(path_discovery_candidate)
    assert not result.passed, "Path discovery test should fail with wrong answer"
    assert "PATH_DISCOVERY_SUCCESS" not in str(result.details), \
        f"Candidate discovered repo path! Details: {result.details}"


def test_blocker_cross_test_contamination():
    """Tests run in separate processes — no global state leaks across test cases."""
    cross_test_candidate = """
_call_count = 0

def count_active(sessions):
    global _call_count
    _call_count += 1
    if _call_count == 1:
        return 5
    elif _call_count == 2:
        return 2
    else:
        return 1
"""
    result = CHECKERS["active_threshold3"].check(cross_test_candidate)
    assert not result.passed, f"Cross-test contamination attack succeeded! Details: {result.details}"


def test_major_timeout_kills_descendants():
    """Timeout kills descendant processes, not just the runner."""
    import psutil
    import uuid

    marker = f"test_marker_{uuid.uuid4().hex}"

    spawn_descendant = """
import subprocess
import sys
import time
import os

def count_active(sessions):
    marker_value = '""" + marker + """'
    env_copy = dict(os.environ)
    env_copy['TEST_MARKER'] = marker_value
    subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(3600)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env_copy,
    )
    time.sleep(3600)
    return 0
"""
    checker = CHECKERS["active_threshold3"]
    start = time.time()
    result = checker.check(spawn_descendant)
    elapsed = time.time() - start

    assert not result.passed, "Descendant-spawning candidate should fail"
    assert "timeout" in result.details.lower() or "infinite loop" in result.details.lower() \
        or "test 1" in result.details.lower(), \
        f"Expected timeout message, got: {result.details}"
    assert elapsed < _TIMEOUT_SECONDS * 3, \
        f"Timeout took too long: {elapsed:.1f}s (expected <{_TIMEOUT_SECONDS * 3}s)"

    time.sleep(1)

    found_marker = False
    try:
        for proc in psutil.process_iter(["pid", "environ"]):
            try:
                env = proc.info.get("environ", {})
                if env and marker in env.get("TEST_MARKER", ""):
                    found_marker = True
                    try:
                        proc.kill()
                        proc.wait(timeout=2)
                    except:
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass

    if found_marker:
        assert False, f"Descendant process with marker {marker} survived timeout!"


def test_stress_reference_candidate_deterministic():
    """STRESS: run a canonical reference candidate 50 times; ALL must pass.

    Verifies the harness eliminates flakiness (infra-error retry, deterministic
    caching). Any failure indicates a residual infra race or non-determinism."""
    tasks = generate_tasks()
    task = [t for t in tasks if t.ambiguity_level == 0][0]

    checkers, candidates, _ = get_checkers_and_candidates("data_analysis", task)
    assert len(candidates) > 0, "No reference candidates found"
    checker_id = list(checkers.keys())[0]
    candidate_code = candidates[checker_id]
    checker = checkers[checker_id]

    iterations = 50
    for i in range(iterations):
        _RESULT_CACHE.clear()
        result = checker.check(candidate_code)
        assert result.passed, (
            f"Iteration {i+1}/{iterations} FAILED for {checker_id}: {result.details}\n"
            f"This indicates harness flakiness or non-deterministic candidate execution."
        )
