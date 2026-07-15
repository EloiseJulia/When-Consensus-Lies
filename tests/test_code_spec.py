"""Tests for code_spec domain — COMBINATORIAL-INVARIANT reconstruction (Amendment 03).

Covers:
  - Amended per-variant invariant: len(key_questions)==k', len(interpretations)==2^k'
  - Combined-default foil marked [combined-default] in k>=2 variants
  - Regime validity (all H1_external) and reversed-property assertions
  - 100% distinguishability via reference candidates
  - Infrastructure robustness (timeout, forgery resistance, etc.)
  - Domain validation round-trip
"""

import pytest
import time

from bench.code_spec import (
    CHECKERS,
    REFERENCE_IMPLEMENTATIONS,
    get_checkers_and_candidates,
    generate_tasks,
    _TIMEOUT_SECONDS,
    problem_fiscal_quarter,
    problem_get_items,
    problem_round_currency,
    problem_format_date,
    problem_quarter_date,
    problem_invoice_line,
)
from bench.validate import validate_task, validate_domain
from bench.build import load_tasks
from common.schema import VALID_REGIMES
from pathlib import Path



def test_checkers_exist():
    """All 20 checker IDs (2 per k=1 family × 4 + 4 for k=2 + 8 for k=3) are
    present in CHECKERS and REFERENCE_IMPLEMENTATIONS."""
    required_checkers = [
        # code_quarter_001  (k=1, C_Q axis)
        "quarter_fiscal_april", "quarter_calendar",
        # code_getitems_001 (k=1, C_I axis)
        "getitems_1based_incl", "getitems_0based_excl",
        # code_roundcurr_001 (k=1, C_R axis)
        "roundcurr_halfup_paren", "roundcurr_halfeven_minus",
        # code_date_001     (k=1, C_D axis)
        "date_us_4y", "date_iso_4y",
        # code_quarterdate_001 (k=2, C_Q+C_D axes)
        "quarterdate_fQ_us", "quarterdate_fQ_iso",
        "quarterdate_cal_us", "quarterdate_cal_iso",
        # code_invoice_001  (k=3, C_Q+C_D+C_R axes)
        "invoice_fQ_us_gaap",      "invoice_fQ_us_halfeven",
        "invoice_fQ_iso_gaap",     "invoice_fQ_iso_halfeven",
        "invoice_cal_us_gaap",     "invoice_cal_us_halfeven",
        "invoice_cal_iso_gaap",    "invoice_cal_iso_halfeven",
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
        # key_questions count == deleted-axis count
        assert len(t.key_questions) == k_prime, \
            f"{t.id}: {len(t.key_questions)} questions != k'={k_prime}"
        # interpretations count == 2^k' (combinatorial invariant)
        expected_interps = 2 ** k_prime
        assert len(t.interpretations) == expected_interps, \
            f"{t.id}: {len(t.interpretations)} interps != 2^{k_prime}={expected_interps}"

        # k=0 control: empty key_questions, single interpretation I0
        if k_prime == 0:
            assert t.key_questions == [], f"{t.id}: control must have no key_questions"
            assert len(t.interpretations) == 1, f"{t.id}: control must have 1 interp"
            assert t.interpretations[0].id == "I0" and t.interpretations[0].is_target
            continue

        # No duplicate questions within a variant
        assert len(set(t.key_questions)) == len(t.key_questions), \
            f"{t.id}: duplicate key_questions"

        # Exactly one target I0
        targets = [i for i in t.interpretations if i.is_target]
        assert len(targets) == 1 and targets[0].id == "I0", \
            f"{t.id}: must have exactly one target I0"


def test_malformed_powerset_rejected():
    """MAJOR: validate_full_spec rejects combinatorial specs with non-power-set
    opened_by sets.

    Malformed case: 2 req classes (A, B), 3 non-targets (2^2-1=3), but sets are
    {A}, {A}, {A,B} — duplicate {A}, missing {B}. Must raise ValueError.
    """
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
                gold_check="chk_a2", opened_by="axis_a",   # duplicate of I1's set
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


def test_no_prompt_leakage():
    """BLOCKER 1: stacked family prompt_core must not contain convention-specific
    output examples from any deletable axis.

    The fix: remove the concrete 'e.g.' examples from the prompt_core of the
    stacked families (quarterdate, invoice). Convention-specific examples now
    live ONLY inside their respective deletable requirement clauses, so they
    disappear when that axis is deleted.

    Checks:
      (a) prompt_core strings are convention-neutral (no concrete format values)
      (b) When a date-format axis IS deleted, the US example '05/15/2024' (which
          was in the old prompt_core) must not appear in the assembled prompt.
    """
    # (a) Stacked-family prompt_core must be convention-neutral
    for spec_fn, name in [
        (problem_quarter_date, "quarterdate"),
        (problem_invoice_line, "invoice"),
    ]:
        core = spec_fn().prompt_core
        assert "05/15/2024" not in core, \
            f"{name} prompt_core leaks US date example '05/15/2024'"
        assert "0.13" not in core, \
            f"{name} prompt_core leaks GAAP rounding '0.13'"
        # No literal Q{n}+date combo that reveals fiscal-April
        import re
        assert not re.search(r"Q[1-4]\s+\d{2}/\d{2}/\d{4}", core), \
            f"{name} prompt_core leaks Q+date combo"

    # (b) When date_format_convention is the ONLY deleted axis, verify that
    # the US example '05/15/2024' (previously leaked via prompt_core) is gone.
    tasks = generate_tasks()
    date_only_deleted = [
        t for t in tasks
        if t.id in (
            "code_date_001_k1_date_format_convention",
            "code_quarterdate_001_k1_date_format_convention",
            "code_invoice_001_k1_date_format_convention",
        )
    ]
    assert date_only_deleted, "Expected date-only deletion variants"
    for t in date_only_deleted:
        assert "05/15/2024" not in t.prompt, \
            f"{t.id}: C_D deleted but old prompt_core US-date '05/15/2024' still present"
    """Checkers accept candidates with helper functions (infrastructure test)."""
    candidate_with_helper = """
def helper(x):
    return (x - 4) % 12

def quarter(month):
    return helper(month) // 3 + 1
"""
    checker = CHECKERS["quarter_fiscal_april"]
    result = checker.check(candidate_with_helper)
    assert result.passed, f"Checker rejected candidate with helper function: {result.details}"


def test_blocker1_decimal_import_accepted():
    """Checkers accept candidates that import from decimal (infrastructure test)."""
    candidate_with_import = """
from decimal import Decimal, ROUND_HALF_UP

def round_currency(amount):
    abs_result = Decimal(str(abs(amount))).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    if amount < 0:
        return f"({abs_result})"
    return str(abs_result)
"""
    checker = CHECKERS["roundcurr_halfup_paren"]
    result = checker.check(candidate_with_import)
    assert result.passed, f"Checker rejected candidate with import: {result.details}"


def test_major1_infinite_loop_timeout():
    """Robustness: an infinite-loop candidate is killed within the hard timeout."""
    infinite_loop = """
def quarter(month):
    while True:
        pass
    return 1
"""
    checker = CHECKERS["quarter_fiscal_april"]
    start = time.time()
    result = checker.check(infinite_loop)
    elapsed = time.time() - start

    assert not result.passed, "Infinite loop should fail"
    assert "timeout" in result.details.lower() or "infinite loop" in result.details.lower(), \
        f"Expected timeout message, got: {result.details}"
    assert elapsed < 10, f"Timeout took too long: {elapsed:.1f}s (expected <10s)"


def test_getitems_rejects_boolean_result():
    """A checker expecting a list must not pass a True/False result.
    Mirrors the 'count boolean predicate' guard for the get_items domain.
    """
    boolean_candidate = """
def get_items(lst, start, end):
    return start < end  # bool, not a list
"""
    for check_id in ("getitems_1based_incl", "getitems_0based_excl"):
        result = CHECKERS[check_id].check(boolean_candidate)
        assert not result.passed, \
            f"{check_id} must reject a boolean result, got: {result.details}"


def test_candidate_exception_fails_gracefully():
    """Isolation: a candidate that raises fails its checker (passed=False) and
    never crashes validation."""
    raising = """
def quarter(month):
    raise RuntimeError("boom")
"""
    result = CHECKERS["quarter_fiscal_april"].check(raising)
    assert not result.passed
    assert "boom" in result.details or "raised" in result.details.lower() or "error" in result.details.lower()


def test_natural_default_is_foil_not_target():
    """REVERSED property: the model's natural default FAILS the target checker
    and PASSES only the model-default foil checker.

    Uses round_currency: Python's f"{x:.2f}" is half-even (I1 = model default),
    NOT I0 (half-up + parentheses). This is the CORE reversed-property assertion.
    """
    natural_default = """
def round_currency(amount):
    return f"{amount:.2f}"
"""
    # Natural default FAILS the target (I0 = half-up + parentheses)
    assert not CHECKERS["roundcurr_halfup_paren"].check(natural_default).passed, \
        "Natural default must FAIL the I0 target checker (I0 is non-default)"
    # Natural default PASSES the model-default foil (I1 = half-even + minus sign)
    assert CHECKERS["roundcurr_halfeven_minus"].check(natural_default).passed, \
        "Natural default must PASS the I_d foil checker (I1 is model default)"


def test_i0_target_passes_its_checker():
    """The I0 (NON-default) implementation passes ONLY its own checker."""
    # quarter: fiscal-April I0 passes only quarter_fiscal_april
    target_quarter = """
def quarter(month):
    return (month - 4) % 12 // 3 + 1
"""
    assert CHECKERS["quarter_fiscal_april"].check(target_quarter).passed
    assert not CHECKERS["quarter_calendar"].check(target_quarter).passed

    # date: US format I0 passes only date_us_4y
    target_date = """
def format_date(year, month, day):
    return f"{month:02d}/{day:02d}/{year:04d}"
"""
    assert CHECKERS["date_us_4y"].check(target_date).passed
    assert not CHECKERS["date_iso_4y"].check(target_date).passed


def test_major3_near_miss_foils_present():
    """Foils are genuine near-misses (at most 1 checker match each).

    Uses the k2_all variant of code_quarterdate_001 (4 interps) for max coverage.
    """
    tasks = generate_tasks()
    task = next(t for t in tasks if t.id == "code_quarterdate_001_k2_all")

    checkers, candidates, foils = get_checkers_and_candidates("code_spec", task)

    assert len(foils) >= 2, "Should have multiple near-miss foils"
    assert all("format_quarter_date" in str(f) for f in foils), \
        "All quarterdate foils should contain the entrypoint name"

    for f in foils:
        matches = sum(1 for c in checkers.values() if c.check(f).passed)
        assert matches <= 1, f"Foil must match at most one checker, got: {matches}"


def test_major3_foils_match_at_most_one():
    """All foils across all tasks match AT MOST ONE checker."""
    tasks = generate_tasks()

    for task in tasks:
        if task.ambiguity_level == 0:
            continue  # k=0 controls have no non-target checkers to probe
        checkers, candidates, foils = get_checkers_and_candidates("code_spec", task)

        for i, foil in enumerate(foils):
            matches = [
                interp_id
                for interp_id, checker in checkers.items()
                if checker.check(foil).passed
            ]
            assert len(matches) <= 1, \
                f"Foil #{i} in {task.id} matches MULTIPLE checkers: {matches}"


def test_checker_execution():
    """Checkers execute candidate code and verify correct/incorrect behavior."""
    # quarter_fiscal_april: reference passes, calendar implementation fails
    checker = CHECKERS["quarter_fiscal_april"]
    ref_code = REFERENCE_IMPLEMENTATIONS["quarter_fiscal_april"]
    result = checker.check(ref_code)
    assert result.passed, f"quarter_fiscal_april reference failed: {result.details}"

    wrong_code = """
def quarter(month):
    return (month - 1) // 3 + 1
"""
    result = checker.check(wrong_code)
    assert not result.passed, "Calendar-quarter code should not pass fiscal-april checker"


def test_task_generation():
    """Tasks are generated with correct structure (Amendment 03 invariant)."""
    tasks = generate_tasks()

    assert len(tasks) == 20, (
        f"Expected 20 tasks (8 from k=1 families + 4 from k=2 + 8 from k=3), got {len(tasks)}"
    )

    for task in tasks:
        assert task.id, "Task missing ID"
        assert task.domain == "code_spec", "Wrong domain"
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
    assert 3 in levels, "No k=3 tasks"


# ============================================================================
# NEW: Regime and reversed-property tests (required by reversal spec)
# ============================================================================

def test_task_regime_valid():
    """Every task carries a valid regime value (H1_external, H2_derivable, or None)."""
    tasks = generate_tasks()
    for t in tasks:
        assert t.regime in VALID_REGIMES, \
            f"{t.id}: invalid regime {t.regime!r}, expected one of {VALID_REGIMES}"


def test_regime_distribution():
    """All tasks carry H1_external regime (no H2 in code_spec after Amendment 03)."""
    tasks = generate_tasks()
    regimes = {t.regime for t in tasks}
    assert "H1_external" in regimes, "No H1_external tasks found"
    assert "H2_derivable" not in regimes, "H2_derivable tasks should be absent from code_spec"
    assert None not in regimes, "All tasks must have a regime value"


def test_target_description_labels_nondefault():
    """I0 description must include 'NON-default'; combined-default foil must include
    '[combined-default]' (Amendment 03 marker) in every FullSpec."""
    problems = [
        problem_fiscal_quarter(),
        problem_get_items(),
        problem_round_currency(),
        problem_format_date(),
        problem_quarter_date(),
        problem_invoice_line(),
    ]
    for spec in problems:
        target = next(i for i in spec.interpretations if i.is_target)
        assert "NON-default" in target.description, \
            f"{spec.task_id}: I0 description must contain 'NON-default', got: {target.description!r}"

        foil_descs = [i.description for i in spec.interpretations if not i.is_target]
        assert any("[combined-default]" in d for d in foil_descs), \
            f"{spec.task_id}: at least one foil must be labeled '[combined-default]', got: {foil_descs}"


def test_combined_default_marked():
    """BLOCKER 2 (Amendment 03): for every k>=1 variant, exactly ONE interpretation's
    gold_check ends in '__combdef' (the per-variant combined-all-default marker).
    That interpretation must be non-target. k=0 controls must have zero markers.

    The '__combdef' suffix is appended by assemble_task to the interpretation
    whose opened_by set equals exactly the full deleted-axis set for that variant,
    persisting the designation in the serialized gold_check field.
    """
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


def test_100pct_reference_candidates_distinguishable():
    """Reference candidates pass ONLY their own checker (100% distinguishable)."""
    problem_groups = [
        # k=1 families (2 checkers each)
        ["quarter_fiscal_april", "quarter_calendar"],
        ["getitems_1based_incl", "getitems_0based_excl"],
        ["roundcurr_halfup_paren", "roundcurr_halfeven_minus"],
        ["date_us_4y", "date_iso_4y"],
        # k=2 family (4 checkers)
        ["quarterdate_fQ_us", "quarterdate_fQ_iso",
         "quarterdate_cal_us", "quarterdate_cal_iso"],
        # k=3 family (8 checkers)
        ["invoice_fQ_us_gaap",    "invoice_fQ_us_halfeven",
         "invoice_fQ_iso_gaap",   "invoice_fQ_iso_halfeven",
         "invoice_cal_us_gaap",   "invoice_cal_us_halfeven",
         "invoice_cal_iso_gaap",  "invoice_cal_iso_halfeven"],
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


def test_foils_catch_overlap():
    """Foils correctly identify non-disjoint checkers (AT MOST ONE match)."""
    tasks = generate_tasks()
    task = tasks[0]
    checkers, candidates, foils = get_checkers_and_candidates("code_spec", task)

    assert len(foils) > 0, "No foils provided"

    for i, foil in enumerate(foils):
        matches = [
            interp_id for interp_id, checker in checkers.items()
            if checker.check(foil).passed
        ]
        assert len(matches) <= 1, f"Foil {i} matches multiple checkers: {matches}"


def test_reference_candidates_distinguish():
    """Reference candidates pass ONLY their own checker (spot-check on 3 problems)."""
    test_groups = [
        ("quarter_fiscal_april",   ["quarter_fiscal_april",  "quarter_calendar"]),
        ("getitems_1based_incl",   ["getitems_1based_incl",  "getitems_0based_excl"]),
        ("roundcurr_halfup_paren", ["roundcurr_halfup_paren","roundcurr_halfeven_minus"]),
    ]
    for target_id, checker_ids in test_groups:
        target_code = REFERENCE_IMPLEMENTATIONS[target_id]
        for checker_id in checker_ids:
            result = CHECKERS[checker_id].check(target_code)
            if checker_id == target_id:
                assert result.passed, f"{target_id} should pass {checker_id}: {result.details}"
            else:
                assert not result.passed, f"{target_id} should NOT pass {checker_id}"


def test_domain_validation():
    """Domain validation reports 100% distinguishable."""
    data_path = Path(__file__).parent.parent / "bench" / "data" / "code_spec.jsonl"

    if not data_path.exists():
        pytest.skip("Data file not yet generated")

    summary = validate_domain("code_spec", data_path, get_checkers_and_candidates)

    assert summary["distinguishable_count"] > 0, "No distinguishable tasks"
    assert summary["distinguishable_pct"] == 100.0, \
        f"Not all tasks distinguishable: {summary['distinguishable_pct']:.1f}%"
    assert len(summary["failed_tasks"]) == 0, f"Tasks failed: {summary['failed_tasks']}"


def test_ambiguity_level_distribution():
    """Tasks cover k=0 (controls), k=1, k=2, and k=3 (full H1b gradient)."""
    tasks = generate_tasks()
    levels = {t.ambiguity_level for t in tasks}
    assert 0 in levels, "Missing k=0 controls"
    assert 1 in levels, "Missing k=1 tasks"
    assert 2 in levels, "Missing k=2 tasks"
    assert 3 in levels, "Missing k=3 tasks (needed for H1b gradient)"


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
# BLOCKER / SECURITY infrastructure tests (entrypoints updated to new domain)
# ============================================================================

def test_blocker_verdict_forgery_direct_write():
    """Candidate cannot forge verdict by writing to file."""
    forging_candidate = """
import json
import glob
import os

def quarter(month):
    for pattern in ["codespec_verdict", "verdict"]:
        try:
            for f in glob.glob(f"*{pattern}*"):
                with open(f, "w") as vf:
                    vf.write('{"status":"pass","message":"forged"}')
        except:
            pass
    return 99  # Wrong answer
"""
    checker = CHECKERS["quarter_fiscal_april"]
    result = checker.check(forging_candidate)
    assert not result.passed, f"Forged verdict was accepted! Details: {result.details}"


def test_blocker_verdict_forgery_stdout_then_exit():
    """Candidate printing forged JSON and exiting early must FAIL."""
    forged_stdout_candidate = """
import json
import os
import sys

print(json.dumps({"status":"pass","message":"forged"}))
sys.stdout.flush()
os._exit(0)

def quarter(month):
    return 1  # Never reached
"""
    checker = CHECKERS["quarter_fiscal_april"]
    result = checker.check(forged_stdout_candidate)
    assert not result.passed, f"Forged stdout attack succeeded! Details: {result.details}"


def test_blocker_expected_output_leak():
    """Candidate cannot read expected outputs by inspecting frames/globals."""
    leak_attempt_candidate = """
import sys
import inspect

def quarter(month):
    for frame_info in inspect.stack():
        frame = frame_info.frame
        for var_name, var_value in frame.f_locals.items():
            if isinstance(var_value, (list, dict)):
                try:
                    if "expected" in str(var_value).lower():
                        return var_value
                except:
                    pass
    return 99  # Wrong answer
"""
    checker = CHECKERS["quarter_fiscal_april"]
    result = checker.check(leak_attempt_candidate)
    assert not result.passed, f"Expected output leak succeeded! Details: {result.details}"


def test_blocker_verdict_forgery_early_exit():
    """Candidate calling os._exit(0) early must FAIL."""
    early_exit_candidate = """
import os

def quarter(month):
    os._exit(0)
    return 1  # Never reached
"""
    checker = CHECKERS["quarter_fiscal_april"]
    result = checker.check(early_exit_candidate)
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

def quarter(month):
    return 99  # Wrong answer
"""
    checker = CHECKERS["quarter_fiscal_april"]
    result = checker.check(monkeypatch_candidate)
    assert not result.passed, f"Monkeypatch attack succeeded! Details: {result.details}"


def test_blocker_verdict_file_overwrite():
    """Candidate descendant cannot overwrite the verdict channel."""
    import time

    verdict_overwrite_candidate = """
import subprocess
import sys
import time
import tempfile
import glob
import json
import os

def quarter(month):
    # Spawn a descendant that tries to overwrite any verdict files
    attack_code = '''
import time
import glob
import tempfile
import json

for _ in range(50):
    try:
        tmpdir = tempfile.gettempdir()
        patterns = [
            f"{tmpdir}/*verdict*",
            f"{tmpdir}/codespec*",
            f"{tmpdir}/*codespec*",
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
    return 99  # Wrong answer
"""
    checker = CHECKERS["quarter_fiscal_april"]
    start = time.time()
    result = checker.check(verdict_overwrite_candidate)
    elapsed = time.time() - start

    assert not result.passed, f"Verdict file overwrite attack succeeded! Details: {result.details}"
    assert elapsed < _TIMEOUT_SECONDS * 3, \
        f"Check took too long: {elapsed:.1f}s (expected <{_TIMEOUT_SECONDS * 3}s)"


def test_blocker_gold_import_test_cases():
    """Candidate cannot import gold test cases from bench.code_spec."""
    gold_import_candidate = """
from bench.code_spec import TEST_CASES

def quarter(month):
    for inp, expected in TEST_CASES.get('quarter_fiscal_april', []):
        if inp == month:
            return expected
    return 99
"""
    checker = CHECKERS["quarter_fiscal_april"]
    result = checker.check(gold_import_candidate)

    assert not result.passed, f"Gold import attack succeeded! Details: {result.details}"
    assert "error" in result.details.lower() or "import" in result.details.lower(), \
        f"Expected import error, got: {result.details}"


def test_blocker_gold_import_bench_module():
    """Candidate cannot import bench module at all."""
    bench_import_candidate = """
import bench

def quarter(month):
    return 1
"""
    checker = CHECKERS["quarter_fiscal_april"]
    result = checker.check(bench_import_candidate)
    assert not result.passed, f"Bench module import succeeded! Details: {result.details}"


def test_blocker_gold_path_discovery_bootstrap():
    """sys.argv[0] / __main__.__file__ must not reveal the repo path."""
    path_discovery_candidate = """
import sys

def quarter(month):
    argv0 = sys.argv[0]
    main_file = sys.modules.get('__main__', None)
    main_file_path = getattr(main_file, '__file__', '')
    for path in [argv0, main_file_path]:
        if path and 'bench' in path and 'code_spec' in path:
            return "PATH_DISCOVERY_SUCCESS"
    return 99  # Wrong answer
"""
    checker = CHECKERS["quarter_fiscal_april"]
    result = checker.check(path_discovery_candidate)

    assert not result.passed, f"Path discovery test should fail with wrong answer"
    assert "PATH_DISCOVERY_SUCCESS" not in str(result.details), \
        f"Candidate discovered repo path! Details: {result.details}"


def test_major_timeout_kills_descendants():
    """Timeout kills descendant processes, not just the runner."""
    import psutil
    import uuid

    marker = f"test_marker_{uuid.uuid4().hex}"

    spawn_descendant = f"""
import subprocess
import sys
import time

def quarter(month):
    subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(3600)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={{**__import__('os').environ, 'TEST_MARKER': '{marker}'}},
    )
    time.sleep(3600)
    return 1
"""
    checker = CHECKERS["quarter_fiscal_april"]
    start = time.time()
    result = checker.check(spawn_descendant)
    elapsed = time.time() - start

    assert not result.passed, "Descendant-spawning candidate should fail"
    assert "timeout" in result.details.lower() or "infinite loop" in result.details.lower(), \
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


