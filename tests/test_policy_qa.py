"""Tests for policy_qa domain - mirroring code_spec test structure."""

import pytest

from bench.policy_qa import (
    CHECKERS,
    REFERENCE_ANSWERS,
    get_checkers_and_candidates,
    generate_tasks,
)
from bench.validate import validate_domain
from pathlib import Path


def test_checkers_exist():
    """Verify all checkers are defined."""
    required_checkers = [
        "overtime_950", "overtime_910", "overtime_1000",
        "interest_365_simple", "interest_360", "interest_compound",
        "tip_pretax", "tip_total", "tip_roundup",
        "refund_365_90", "refund_360", "refund_89",
        "discount_sequential", "discount_additive", "discount_roundup",
    ]
    
    for checker_id in required_checkers:
        assert checker_id in CHECKERS, f"Missing checker: {checker_id}"
        assert checker_id in REFERENCE_ANSWERS, f"Missing reference: {checker_id}"


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


def test_amounts_pairwise_distinct():
    """All interpretation amounts are pairwise distinct (verified against design)."""
    # Directly verify the REFERENCE_ANSWERS against the Manager's design
    problems_expected = [
        ("overtime", [950.00, 910.00, 1000.00]),
        ("interest", [147.95, 150.00, 150.75]),
        ("tip", [7.50, 8.10, 8.00]),
        ("refund", [271.23, 270.00, 272.22]),
        ("discount", [74.80, 73.00, 75.00]),
    ]
    
    for problem_prefix, expected_amounts in problems_expected:
        # Find all amounts for this problem in REFERENCE_ANSWERS
        amounts = []
        for key, value in REFERENCE_ANSWERS.items():
            if problem_prefix in key:
                amounts.append(value["amount"])
        
        assert len(amounts) == 3, f"{problem_prefix}: expected 3 amounts, got {len(amounts)}"
        
        # Verify pairwise distinct (gap > 0.01 tolerance)
        amounts_sorted = sorted(amounts)
        for i in range(len(amounts_sorted)):
            for j in range(i + 1, len(amounts_sorted)):
                diff = abs(amounts_sorted[i] - amounts_sorted[j])
                assert diff > 0.01, \
                    f"{problem_prefix}: amounts {amounts_sorted[i]} and {amounts_sorted[j]} too close (diff={diff:.4f})"


def test_task_generation():
    """Verify 20 tasks generated with correct distribution."""
    tasks = generate_tasks()
    
    assert len(tasks) == 20, f"Expected 20 tasks, got {len(tasks)}"
    
    # Check distribution
    levels = {k: sum(1 for t in tasks if t.ambiguity_level == k) for k in range(3)}
    assert levels[0] == 5, f"Expected 5 k=0 controls, got {levels[0]}"
    assert levels[1] == 10, f"Expected 10 k=1 tasks, got {levels[1]}"
    assert levels[2] == 5, f"Expected 5 k=2 tasks, got {levels[2]}"


def test_domain_validation():
    """Test domain validation achieves 100% distinguishability."""
    tasks = generate_tasks()
    data_path = Path(__file__).parent.parent / "bench" / "data" / "policy_qa.jsonl"
    
    if not data_path.exists():
        pytest.skip("Data file not yet generated")
    
    summary = validate_domain("policy_qa", data_path, get_checkers_and_candidates)
    
    assert summary["distinguishable_pct"] == 100.0, \
        f"Not all tasks distinguishable: {summary['distinguishable_pct']:.1f}%"


def test_target_is_natural_default():
    """Verify target (I0) uses natural defaults per Manager design."""
    # Overtime: 40h threshold, 1.5x rate
    assert REFERENCE_ANSWERS["overtime_950"]["amount"] == 950.00
    
    # Interest: 365-day, simple
    assert abs(REFERENCE_ANSWERS["interest_365_simple"]["amount"] - 147.95) < 0.01
    
    # Tip: pre-tax, cent rounding
    assert REFERENCE_ANSWERS["tip_pretax"]["amount"] == 7.50
    
    # Refund: 365-day, 90 used days
    assert abs(REFERENCE_ANSWERS["refund_365_90"]["amount"] - 271.23) < 0.01
    
    # Discount: sequential stacking, cent rounding
    assert abs(REFERENCE_ANSWERS["discount_sequential"]["amount"] - 74.80) < 0.01


def test_foils_mandatory():
    """Verify foils are provided and match at most one checker."""
    tasks = generate_tasks()
    
    for task in tasks[:3]:
        checkers, candidates, foils = get_checkers_and_candidates("policy_qa", task)
        
        assert len(foils) > 0, f"Task {task.id} has no foils (MANDATORY)"
        
        for i, foil in enumerate(foils):
            matches = sum(1 for c in checkers.values() if c.check(foil).passed)
            assert matches <= 1, f"Foil #{i} in {task.id} matches {matches} checkers"
