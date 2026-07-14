"""Tests for data_analysis domain."""

import pytest
import time

from bench.data_analysis import (
    CHECKERS,
    REFERENCE_IMPLEMENTATIONS,
    get_checkers_and_candidates,
    generate_tasks,
)
from bench.validate import validate_task, validate_domain
from bench.build import load_tasks
from pathlib import Path


def test_checkers_exist():
    """Verify all checkers are defined."""
    required_checkers = [
        "mean_skip_none", "mean_propagate_none",
        "var_sample", "var_population",
        "median_average", "median_lower",
        "filter_exclusive", "filter_inclusive",
        "group_preserve_order", "group_sort_values",
    ]
    
    for checker_id in required_checkers:
        assert checker_id in CHECKERS, f"Missing checker: {checker_id}"
        assert checker_id in REFERENCE_IMPLEMENTATIONS, f"Missing reference: {checker_id}"


def test_key_questions_invariant():
    """GOLDEN: key_questions == deleted axes for every variant (deterministic).

    Enforces len(key_questions) == ambiguity_level == len(interpretations) - 1,
    and that the k=0 control carries ZERO key_questions. key_questions is the
    gold for the Direction-B (false-surfacing) detector; a stale question would
    invert that metric and destroy the unambiguous control.
    """
    tasks = generate_tasks()
    assert tasks, "no tasks generated"
    for t in tasks:
        assert len(t.key_questions) == t.ambiguity_level, \
            f"{t.id}: {len(t.key_questions)} questions != k={t.ambiguity_level}"
        assert t.ambiguity_level == len(t.interpretations) - 1, \
            f"{t.id}: k={t.ambiguity_level} != interpretations-1={len(t.interpretations) - 1}"
        if t.ambiguity_level == 0:
            assert t.key_questions == [], f"{t.id}: control must have no key_questions"
        # No duplicate questions within a variant.
        assert len(set(t.key_questions)) == len(t.key_questions), \
            f"{t.id}: duplicate key_questions"


def test_helper_functions_accepted():
    """Checkers accept candidates with helper functions."""
    candidate_with_helper = """
def helper(x):
    return x * 2

def compute_mean(numbers):
    # Uses a helper - should still work
    filtered = [x for x in numbers if x is not None]
    return sum(filtered) / len(filtered) if filtered else 0.0
"""
    
    checker = CHECKERS["mean_skip_none"]
    result = checker.check(candidate_with_helper)
    assert result.passed, f"Checker rejected candidate with helper function: {result.details}"


def test_imports_accepted():
    """Checkers accept candidates that import from statistics."""
    candidate_with_import = """
import statistics

def compute_variance(numbers):
    return statistics.variance(numbers) if len(numbers) >= 2 else 0.0
"""
    
    checker = CHECKERS["var_sample"]
    result = checker.check(candidate_with_import)
    assert result.passed, f"Checker rejected candidate with import: {result.details}"


def test_infinite_loop_timeout():
    """Robustness: an infinite-loop candidate is killed within the hard timeout.

    The checker runs candidates in a separate subprocess; subprocess.run kills
    the child on timeout, so runaway code is actually terminated (no leaked
    thread, no hang).
    """
    infinite_loop = """
def compute_mean(numbers):
    while True:
        pass
    return 0.0
"""
    
    checker = CHECKERS["mean_skip_none"]
    start = time.time()
    result = checker.check(infinite_loop)
    elapsed = time.time() - start
    
    assert not result.passed, "Infinite loop should fail"
    assert "timeout" in result.details.lower() or "infinite loop" in result.details.lower(), \
        f"Expected timeout message, got: {result.details}"
    assert elapsed < 10, f"Timeout took too long: {elapsed:.1f}s (expected <10s)"


def test_rejects_boolean_predicate():
    """Science bug: a boolean predicate must NOT be labeled as matching numeric
    checkers. Python's True==1/False==0 would otherwise let boolean results
    masquerade as numeric results."""
    boolean_predicate = """
def compute_mean(numbers):
    return True
"""
    for check_id in ("mean_skip_none", "mean_propagate_none"):
        result = CHECKERS[check_id].check(boolean_predicate)
        assert not result.passed, \
            f"{check_id} must reject a boolean predicate, got: {result.details}"


def test_candidate_exception_fails_gracefully():
    """Isolation: a candidate that raises fails its checker (passed=False) and
    never crashes validation."""
    raising = """
def compute_mean(numbers):
    raise RuntimeError("boom")
"""
    result = CHECKERS["mean_skip_none"].check(raising)
    assert not result.passed
    assert "boom" in result.details or "raised" in result.details.lower() or "error" in result.details.lower()


def test_natural_default_is_target():
    """Fairness: the natural default (skip None) IS the target."""
    naive_mean = """
def compute_mean(numbers):
    filtered = [x for x in numbers if x is not None]
    return sum(filtered) / len(filtered) if filtered else 0.0
"""
    assert CHECKERS["mean_skip_none"].check(naive_mean).passed, \
        "Natural skip-None default must PASS the target checker"


def test_near_miss_foils_present():
    """Foils are genuine task-specific near-misses (not generic junk).

    After removing vacuous timeout/import junk foils, every per-task foil must
    be task-specific (built around the correct entrypoint) and must match AT
    MOST ONE interpretation checker. A near-miss may legitimately match ZERO
    checkers when it is a plausible-but-clearly-wrong answer that lands on the
    discriminating boundary of every interpretation; the invariant we enforce
    is disjointness (never matching two interpretations), not a minimum count
    of single-matches.
    """
    tasks = generate_tasks()
    # Pick the mean task with the most interpretations
    mean_tasks = [t for t in tasks if "data_mean" in t.id]
    task = max(mean_tasks, key=lambda t: len(t.interpretations))

    checkers, candidates, foils = get_checkers_and_candidates("data_analysis", task)

    assert len(foils) >= 2, "Should have multiple near-miss foils"

    # All foils are task-specific (use the correct entrypoint name).
    assert all("compute_mean" in str(f) for f in foils), \
        "All foils should be task-specific (contain the entrypoint)"

    # Enforced invariant: no foil may match more than one checker (label leak).
    for f in foils:
        matches = sum(1 for c in checkers.values() if c.check(f).passed)
        assert matches <= 1, "Foil must match at most one checker"


def test_foils_match_at_most_one():
    """All foils (including near-miss) match AT MOST ONE checker."""
    tasks = generate_tasks()
    
    for task in tasks[:3]:  # Test a few tasks
        checkers, candidates, foils = get_checkers_and_candidates("data_analysis", task)
        
        for i, foil in enumerate(foils):
            matches = []
            for interp_id, checker in checkers.items():
                if checker.check(foil).passed:
                    matches.append(interp_id)
            assert len(matches) <= 1, \
                f"Foil #{i} in {task.id} matches MULTIPLE checkers: {matches}"


def test_checker_execution():
    """Test that checkers actually execute code and verify behavior."""
    
    # Test mean_skip_none
    checker = CHECKERS["mean_skip_none"]
    ref_code = REFERENCE_IMPLEMENTATIONS["mean_skip_none"]
    result = checker.check(ref_code)
    assert result.passed, f"mean_skip_none failed: {result.details}"
    
    # Test with wrong code (should fail)
    wrong_code = """
def compute_mean(numbers):
    if None in numbers:
        return None
    return sum(numbers) / len(numbers) if numbers else 0.0
"""
    result = checker.check(wrong_code)
    assert not result.passed, "Wrong code should not pass mean_skip_none"


def test_task_generation():
    """Test that tasks are generated correctly."""
    tasks = generate_tasks()
    
    assert len(tasks) > 0, "No tasks generated"
    
    # Check structure
    for task in tasks:
        assert task.id, "Task missing ID"
        assert task.domain == "data_analysis", "Wrong domain"
        assert task.prompt, "Task missing prompt"
        assert task.latent_spec, "Task missing latent_spec"
        assert len(task.interpretations) >= 1, "Task has no interpretations"
        assert task.ambiguity_level >= 0, "Invalid ambiguity level"
        # key_questions == deleted axes: empty for the k=0 control, else k of them
        # (see test_key_questions_invariant for the full golden check).
        assert len(task.key_questions) == task.ambiguity_level, \
            f"{task.id}: key_questions must equal ambiguity_level"
        
        # Check target interpretation
        targets = [i for i in task.interpretations if i.is_target]
        assert len(targets) == 1, f"Task {task.id} has {len(targets)} targets"
        assert targets[0].id == "I0", f"Target must be I0, got {targets[0].id}"
    
    # Check ambiguity distribution
    levels = [t.ambiguity_level for t in tasks]
    assert 0 in levels, "No k=0 controls"
    assert any(k >= 1 for k in levels), "No ambiguous tasks"


def test_foils_catch_overlap():
    """Test that foils correctly identify non-disjoint checkers."""
    
    # Generate a sample task
    tasks = generate_tasks()
    task = tasks[0]
    
    # Get checkers and foils
    checkers, candidates, foils = get_checkers_and_candidates("data_analysis", task)
    
    # Verify foils exist
    assert len(foils) > 0, "No foils provided"
    
    # Each foil should match AT MOST ONE checker
    for i, foil in enumerate(foils):
        matches = []
        for interp_id, checker in checkers.items():
            if checker.check(foil).passed:
                matches.append(interp_id)
        assert len(matches) <= 1, f"Foil {i} matches multiple checkers: {matches}"


def test_reference_candidates_distinguish():
    """Test that reference candidates pass ONLY their own checker."""
    
    # Test a few specific cases
    test_cases = [
        ("mean_skip_none", ["mean_skip_none", "mean_propagate_none"]),
        ("var_sample", ["var_sample", "var_population"]),
        ("median_average", ["median_average", "median_lower"]),
    ]
    
    for target_id, checker_ids in test_cases:
        target_code = REFERENCE_IMPLEMENTATIONS[target_id]
        
        for checker_id in checker_ids:
            checker = CHECKERS[checker_id]
            result = checker.check(target_code)
            
            if checker_id == target_id:
                assert result.passed, f"{target_id} should pass {checker_id}: {result.details}"
            else:
                assert not result.passed, f"{target_id} should NOT pass {checker_id}"


def test_domain_validation():
    """Test domain validation after task generation."""
    
    # First generate the data file
    tasks = generate_tasks()
    data_path = Path(__file__).parent.parent / "bench" / "data" / "data_analysis.jsonl"
    
    # If data file doesn't exist, skip this test (will be created by main)
    if not data_path.exists():
        pytest.skip("Data file not yet generated")
    
    # Validate the domain
    summary = validate_domain("data_analysis", data_path, get_checkers_and_candidates)
    
    assert summary["distinguishable_count"] > 0, "No distinguishable tasks"
    assert summary["distinguishable_pct"] == 100.0, f"Not all tasks distinguishable: {summary['distinguishable_pct']:.1f}%"
    assert len(summary["failed_tasks"]) == 0, f"Tasks failed: {summary['failed_tasks']}"


def test_ambiguity_level_distribution():
    """Test that tasks cover required ambiguity levels."""
    tasks = generate_tasks()
    
    levels = {t.ambiguity_level for t in tasks}
    
    assert 0 in levels, "Missing k=0 controls"
    assert 1 in levels, "Missing k=1 tasks"


def test_prompt_vs_latent_spec():
    """Test that ambiguous tasks have strictly less specified prompts."""
    tasks = generate_tasks()
    
    for task in tasks:
        if task.ambiguity_level == 0:
            # Control: prompt should equal latent_spec
            assert task.prompt == task.latent_spec, f"k=0 control {task.id} has prompt != latent_spec"
        else:
            # Ambiguous: prompt should be strictly less specified
            assert len(task.prompt) < len(task.latent_spec), \
                f"k={task.ambiguity_level} task {task.id} prompt not less specified than latent_spec"


def test_variance_formulas_distinguish():
    """Test that sample and population variance produce different results."""
    # For [1,2,3,4,5]: mean=3, sum of squares=10
    # Sample var (n-1): 10/4 = 2.5
    # Population var (n): 10/5 = 2.0
    
    sample_ref = REFERENCE_IMPLEMENTATIONS["var_sample"]
    population_ref = REFERENCE_IMPLEMENTATIONS["var_population"]
    
    # Sample should pass sample checker, fail population checker
    assert CHECKERS["var_sample"].check(sample_ref).passed
    assert not CHECKERS["var_population"].check(sample_ref).passed
    
    # Population should pass population checker, fail sample checker
    assert CHECKERS["var_population"].check(population_ref).passed
    assert not CHECKERS["var_sample"].check(population_ref).passed


def test_median_formulas_distinguish():
    """Test that average and lower median produce different results for even-length."""
    # For [1,2,3,4]: average of middle two = 2.5, lower middle = 2
    
    average_ref = REFERENCE_IMPLEMENTATIONS["median_average"]
    lower_ref = REFERENCE_IMPLEMENTATIONS["median_lower"]
    
    # Average should pass average checker, fail lower checker
    assert CHECKERS["median_average"].check(average_ref).passed
    assert not CHECKERS["median_lower"].check(average_ref).passed
    
    # Lower should pass lower checker, fail average checker
    assert CHECKERS["median_lower"].check(lower_ref).passed
    assert not CHECKERS["median_average"].check(lower_ref).passed


def test_filter_boundary_distinguishes():
    """Test that exclusive and inclusive boundaries produce different results."""
    # For threshold=10, value=10: exclusive excludes, inclusive includes
    
    exclusive_ref = REFERENCE_IMPLEMENTATIONS["filter_exclusive"]
    inclusive_ref = REFERENCE_IMPLEMENTATIONS["filter_inclusive"]
    
    # Exclusive should pass exclusive checker, fail inclusive checker
    assert CHECKERS["filter_exclusive"].check(exclusive_ref).passed
    assert not CHECKERS["filter_inclusive"].check(exclusive_ref).passed
    
    # Inclusive should pass inclusive checker, fail exclusive checker
    assert CHECKERS["filter_inclusive"].check(inclusive_ref).passed
    assert not CHECKERS["filter_exclusive"].check(inclusive_ref).passed


def test_group_order_distinguishes():
    """Test that preserve and sort order produce different results."""
    
    preserve_ref = REFERENCE_IMPLEMENTATIONS["group_preserve_order"]
    sort_ref = REFERENCE_IMPLEMENTATIONS["group_sort_values"]
    
    # Preserve should pass preserve checker, fail sort checker
    assert CHECKERS["group_preserve_order"].check(preserve_ref).passed
    assert not CHECKERS["group_sort_values"].check(preserve_ref).passed
    
    # Sort should pass sort checker, fail preserve checker
    assert CHECKERS["group_sort_values"].check(sort_ref).passed
    assert not CHECKERS["group_preserve_order"].check(sort_ref).passed
