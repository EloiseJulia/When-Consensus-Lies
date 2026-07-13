"""Tests for code_spec domain."""

import pytest

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
    """Verify all checkers are defined."""
    required_checkers = [
        "sort_asc_stable", "sort_desc_stable", "sort_asc_name",
        "filter_strict_skip", "filter_nonneg_skip", "filter_strict_replaceone",
        "join_space_keep", "join_concat_keep", "join_space_skip",
        "sum_zero_convert", "sum_neg_convert", "sum_zero_skip",
        "max_inf_value", "max_zero_value", "max_inf_index",
        "csv_strip_empty", "csv_keep_empty", "csv_strip_none",
        "count_case_nonoverlap", "count_nocase_nonoverlap", "count_case_overlap",
        "format_2dec_halfup_noplus", "format_1dec_halfup_noplus", "format_2dec_trunc_noplus", "format_2dec_halfup_plus",
    ]
    
    for checker_id in required_checkers:
        assert checker_id in CHECKERS, f"Missing checker: {checker_id}"
        assert checker_id in REFERENCE_IMPLEMENTATIONS, f"Missing reference: {checker_id}"


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
    
    # Test filter_strict_skip
    checker = CHECKERS["filter_strict_skip"]
    ref_code = REFERENCE_IMPLEMENTATIONS["filter_strict_skip"]
    result = checker.check(ref_code)
    assert result.passed, f"filter_strict_skip failed: {result.details}"


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
    
    # Test a few specific cases
    test_cases = [
        ("sort_asc_stable", ["sort_asc_stable", "sort_desc_stable", "sort_asc_name"]),
        ("filter_strict_skip", ["filter_strict_skip", "filter_nonneg_skip"]),
        ("join_space_keep", ["join_space_keep", "join_concat_keep", "join_space_skip"]),
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
    assert 2 in levels, "Missing k=2 tasks"


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
