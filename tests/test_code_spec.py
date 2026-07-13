"""Tests for code_spec domain - including fixes for all 5 audit findings."""

import pytest
import time

from bench.code_spec import (
    CHECKERS,
    REFERENCE_IMPLEMENTATIONS,
    get_checkers_and_candidates,
    generate_tasks,
)
from bench.validate import validate_task, validate_domain
from bench.build import load_tasks
from pathlib import Path


def test_checkers_exist():
    """Verify all checkers are defined (BLOCKER 2: removed straw problems)."""
    required_checkers = [
        "sort_asc_stable", "sort_desc_stable", "sort_asc_name",
        "join_space_keep", "join_concat_keep", "join_space_skip",
        "csv_strip_empty", "csv_keep_empty", "csv_strip_none",
        "count_case_nonoverlap", "count_nocase_nonoverlap", "count_case_overlap",
        "format_2dec_halfup_noplus", "format_1dec_halfup_noplus", "format_2dec_trunc_noplus", "format_2dec_halfup_plus",
    ]
    
    for checker_id in required_checkers:
        assert checker_id in CHECKERS, f"Missing checker: {checker_id}"
        assert checker_id in REFERENCE_IMPLEMENTATIONS, f"Missing reference: {checker_id}"


def test_blocker1_helper_functions_accepted():
    """BLOCKER 1 FIX: Checkers accept candidates with helper functions."""
    candidate_with_helper = """
def helper(x):
    return x * 2

def sort_func(records):
    # Uses a helper - should still work
    return sorted(records, key=lambda r: r['age'])
"""
    
    checker = CHECKERS["sort_asc_stable"]
    result = checker.check(candidate_with_helper)
    assert result.passed, f"Checker rejected candidate with helper function: {result.details}"


def test_blocker1_decimal_import_accepted():
    """BLOCKER 1 FIX: Checkers accept candidates that import from decimal."""
    candidate_with_import = """
from decimal import Decimal, ROUND_HALF_UP

def format_func(number):
    d = Decimal(str(number))
    rounded = d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f"{rounded:.2f}"
"""
    
    checker = CHECKERS["format_2dec_halfup_noplus"]
    result = checker.check(candidate_with_import)
    assert result.passed, f"Checker rejected candidate with import: {result.details}"


def test_major1_infinite_loop_timeout():
    """MAJOR 1 FIX: Infinite loop candidates fail within timeout."""
    infinite_loop = """
def sort_func(records):
    while True:
        pass
    return records
"""
    
    checker = CHECKERS["sort_asc_stable"]
    start = time.time()
    result = checker.check(infinite_loop)
    elapsed = time.time() - start
    
    assert not result.passed, "Infinite loop should fail"
    assert "timeout" in result.details.lower() or "infinite loop" in result.details.lower(), \
        f"Expected timeout message, got: {result.details}"
    assert elapsed < 10, f"Timeout took too long: {elapsed:.1f}s (expected <10s)"


def test_major1_import_os_blocked():
    """MAJOR 1 FIX: Candidates importing os/socket are blocked."""
    import_os = """
def sort_func(records):
    import os
    return os.listdir('.')
"""
    
    checker = CHECKERS["sort_asc_stable"]
    result = checker.check(import_os)
    assert not result.passed, f"import os should be blocked, but got: {result.details}"


def test_major1_import_socket_blocked():
    """MAJOR 1 FIX: Candidates importing socket are blocked."""
    import_socket = """
def count_func(text, substring):
    import socket
    return 0
"""
    
    checker = CHECKERS["count_case_nonoverlap"]
    result = checker.check(import_socket)
    assert not result.passed, f"import socket should be blocked, but got: {result.details}"


def test_major2_naive_fstring_rejected_by_halfup():
    """MAJOR 2 FIX: Naive f-string formatting FAILS half-up checker on tie cases."""
    naive_formatter = """
def format_func(number):
    return f"{number:.2f}"
"""
    
    checker = CHECKERS["format_2dec_halfup_noplus"]
    result = checker.check(naive_formatter)
    assert not result.passed, \
        f"Naive f-string should FAIL half-up checker on tie-breaking cases, but got: {result.details}"


def test_major2_true_halfup_passes():
    """MAJOR 2 FIX: True half-up implementation passes."""
    true_halfup = """
def format_func(number):
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(str(number))
    rounded = d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f"{rounded:.2f}"
"""
    
    checker = CHECKERS["format_2dec_halfup_noplus"]
    result = checker.check(true_halfup)
    assert result.passed, f"True half-up should pass: {result.details}"


def test_major3_near_miss_foils_present():
    """MAJOR 3 FIX: foils are genuine task-specific near-misses (not generic junk).

    After removing the vacuous timeout/import junk foils, every per-task foil
    must be task-specific, and at least one must be a genuine near-miss that
    matches EXACTLY ONE interpretation checker (probing the boundary between
    interpretations, not just failing everything).
    """
    tasks = generate_tasks()
    # Pick the sort task with the most interpretations (so near-miss foils that
    # target alternative interpretations are actually exercised; a k=0 control
    # exposes only I0's checker).
    sort_tasks = [t for t in tasks if "code_sort" in t.id]
    task = max(sort_tasks, key=lambda t: len(t.interpretations))

    checkers, candidates, foils = get_checkers_and_candidates("code_spec", task)

    assert len(foils) >= 2, "Should have multiple near-miss foils"

    # All foils are task-specific (use the correct entrypoint name).
    assert all("sort_func" in str(f) for f in foils), \
        "All foils should be task-specific (contain the entrypoint)"

    # At least one foil is a genuine near-miss: matches exactly one checker.
    near_miss = 0
    for f in foils:
        matches = sum(1 for c in checkers.values() if c.check(f).passed)
        assert matches <= 1, "Foil must match at most one checker"
        if matches == 1:
            near_miss += 1
    assert near_miss >= 1, \
        "At least one foil must be a genuine near-miss (matches exactly one interpretation)"


def test_major3_foils_match_at_most_one():
    """MAJOR 3 FIX: All foils (including near-miss) match AT MOST ONE checker."""
    tasks = generate_tasks()
    
    for task in tasks[:3]:  # Test a few tasks
        checkers, candidates, foils = get_checkers_and_candidates("code_spec", task)
        
        for i, foil in enumerate(foils):
            matches = []
            for interp_id, checker in checkers.items():
                if checker.check(foil).passed:
                    matches.append(interp_id)
            assert len(matches) <= 1, \
                f"Foil #{i} in {task.id} matches MULTIPLE checkers: {matches}"


def test_checker_execution():
    """Test that checkers actually execute code and verify behavior."""
    
    # Test sort_asc_stable
    checker = CHECKERS["sort_asc_stable"]
    ref_code = REFERENCE_IMPLEMENTATIONS["sort_asc_stable"]
    result = checker.check(ref_code)
    assert result.passed, f"sort_asc_stable failed: {result.details}"
    
    # Test with wrong code (should fail)
    wrong_code = """
def sort_func(records):
    return sorted(records, key=lambda r: r['age'], reverse=True)
"""
    result = checker.check(wrong_code)
    assert not result.passed, "Wrong code should not pass sort_asc_stable"


def test_task_generation():
    """Test that tasks are generated correctly."""
    tasks = generate_tasks()
    
    assert len(tasks) > 0, "No tasks generated"
    
    # Check structure
    for task in tasks:
        assert task.id, "Task missing ID"
        assert task.domain == "code_spec", "Wrong domain"
        assert task.prompt, "Task missing prompt"
        assert task.latent_spec, "Task missing latent_spec"
        assert len(task.interpretations) >= 1, "Task has no interpretations"
        assert task.ambiguity_level >= 0, "Invalid ambiguity level"
        assert len(task.key_questions) > 0, "Task has no key questions"
        
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
    checkers, candidates, foils = get_checkers_and_candidates("code_spec", task)
    
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
    
    # Test a few specific cases (BLOCKER 2: filter/sum/max removed)
    test_cases = [
        ("sort_asc_stable", ["sort_asc_stable", "sort_desc_stable", "sort_asc_name"]),
        ("join_space_keep", ["join_space_keep", "join_concat_keep", "join_space_skip"]),
        ("csv_strip_empty", ["csv_strip_empty", "csv_keep_empty", "csv_strip_none"]),
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
    data_path = Path(__file__).parent.parent / "bench" / "data" / "code_spec.jsonl"
    
    # If data file doesn't exist, skip this test (will be created by main)
    if not data_path.exists():
        pytest.skip("Data file not yet generated")
    
    # Validate the domain
    summary = validate_domain("code_spec", data_path, get_checkers_and_candidates)
    
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
