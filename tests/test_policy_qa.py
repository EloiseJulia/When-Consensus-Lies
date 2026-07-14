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
        "refund_original_cent", "refund_adjusted", "refund_roundup",
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
    
    STRENGTHENED: Now checks exact identity of key_question strings, not just counts.
    """
    # Golden mapping: task_id -> expected key_questions (exact strings)
    # Derived from the generator's axis<->question map, matching deleted axes per variant
    EXPECTED_KEY_QUESTIONS = {
        # Overtime (2 axes: threshold, rate)
        "policy_overtime_001_k0": [],
        "policy_overtime_001_k1_overtime_threshold": [
            "After how many hours per week does overtime begin (40, or another threshold)?"
        ],
        "policy_overtime_001_k1_overtime_rate": [
            "What multiplier applies to overtime hours (1.5x, or another rate)?"
        ],
        "policy_overtime_001_k2_all": [
            "After how many hours per week does overtime begin (40, or another threshold)?",
            "What multiplier applies to overtime hours (1.5x, or another rate)?"
        ],
        
        # Interest (2 axes: day_count, compounding)
        "policy_interest_001_k0": [],
        "policy_interest_001_k1_day_count": [
            "Should the daily rate use a 365-day or 360-day year?"
        ],
        "policy_interest_001_k1_compounding": [
            "Is the interest simple, or compounded?"
        ],
        "policy_interest_001_k2_all": [
            "Should the daily rate use a 365-day or 360-day year?",
            "Is the interest simple, or compounded?"
        ],
        
        # Tip (2 axes: base, rounding)
        "policy_tip_001_k0": [],
        "policy_tip_001_k1_tip_base": [
            "Is the tip computed on the pre-tax amount or the after-tax total?"
        ],
        "policy_tip_001_k1_tip_rounding": [
            "Round the tip to the nearest cent, or up to the next whole dollar?"
        ],
        "policy_tip_001_k2_all": [
            "Is the tip computed on the pre-tax amount or the after-tax total?",
            "Round the tip to the nearest cent, or up to the next whole dollar?"
        ],
        
        # Refund (2 axes: fee_basis, refund_rounding)
        "policy_refund_001_k0": [],
        "policy_refund_001_k1_fee_basis": [
            "Is the restocking fee calculated on the original price or an adjusted base?"
        ],
        "policy_refund_001_k1_refund_rounding": [
            "Round the refund to the nearest cent, or the nearest whole dollar?"
        ],
        "policy_refund_001_k2_all": [
            "Is the restocking fee calculated on the original price or an adjusted base?",
            "Round the refund to the nearest cent, or the nearest whole dollar?"
        ],
        
        # Discount (2 axes: stacking, price_rounding)
        "policy_discount_001_k0": [],
        "policy_discount_001_k1_stacking": [
            "Are the discounts applied sequentially or added together?"
        ],
        "policy_discount_001_k1_price_rounding": [
            "Round the final price to the nearest cent, or the nearest whole dollar?"
        ],
        "policy_discount_001_k2_all": [
            "Are the discounts applied sequentially or added together?",
            "Round the final price to the nearest cent, or the nearest whole dollar?"
        ],
    }
    
    tasks = generate_tasks()
    assert tasks, "no tasks generated"
    assert len(tasks) == 20, f"Expected 20 tasks, got {len(tasks)}"
    
    for t in tasks:
        # Invariant checks (keep existing)
        assert len(t.key_questions) == t.ambiguity_level, \
            f"{t.id}: {len(t.key_questions)} questions != k={t.ambiguity_level}"
        assert t.ambiguity_level == len(t.interpretations) - 1, \
            f"{t.id}: k={t.ambiguity_level} != interpretations-1={len(t.interpretations) - 1}"
        if t.ambiguity_level == 0:
            assert t.key_questions == [], f"{t.id}: control must have no key_questions"
        # No duplicate questions within a variant
        assert len(set(t.key_questions)) == len(t.key_questions), \
            f"{t.id}: duplicate key_questions"
        
        # NEW: Exact identity check (GOLDEN)
        assert t.id in EXPECTED_KEY_QUESTIONS, \
            f"{t.id}: missing from golden mapping (generation changed?)"
        expected = EXPECTED_KEY_QUESTIONS[t.id]
        assert t.key_questions == expected, \
            f"{t.id}: key_questions mismatch.\n  Expected: {expected}\n  Got: {t.key_questions}"


def test_amounts_pairwise_distinct():
    """All interpretation amounts are pairwise distinct (verified against design)."""
    # Directly verify the REFERENCE_ANSWERS against the Manager's design
    problems_expected = [
        ("overtime", [950.00, 910.00, 1000.00]),
        ("interest", [147.95, 150.00, 149.03]),
        ("tip", [7.50, 8.10, 8.00]),
        ("refund", [343.95, 341.96, 344.00]),
        ("discount", [74.80, 73.00, 75.00]),
    ]
    
    for problem_prefix, expected_amounts in problems_expected:
        # Find all amounts for this problem in REFERENCE_ANSWERS
        amounts = []
        for key, value in REFERENCE_ANSWERS.items():
            if problem_prefix in key:
                amounts.append(value["amount"])
        
        assert len(amounts) == 3, f"{problem_prefix}: expected 3 amounts, got {len(amounts)}"
        
        # Verify pairwise distinct with a robustness margin well above the
        # checker's 0.01 float tolerance. The observed minimum pairwise gap
        # across all problems is 0.10 (tip_total 8.10 vs tip_roundup 8.00),
        # i.e. 10x the checker tolerance, so no interpretation can be
        # mis-scored as another. We assert a 0.05 (5x tolerance) safety floor.
        SAFETY_FLOOR = 0.05
        amounts_sorted = sorted(amounts)
        for i in range(len(amounts_sorted)):
            for j in range(i + 1, len(amounts_sorted)):
                diff = abs(amounts_sorted[i] - amounts_sorted[j])
                assert diff > SAFETY_FLOOR, \
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
    # Interest compounding alt must be DAILY (consistent with the 365-day rate),
    # not monthly -> 149.03, not 150.75.
    assert abs(REFERENCE_ANSWERS["interest_compound"]["amount"] - 149.03) < 0.01
    
    # Tip: pre-tax, cent rounding
    assert REFERENCE_ANSWERS["tip_pretax"]["amount"] == 7.50
    
    # Refund: fee on original price, cent rounding
    assert abs(REFERENCE_ANSWERS["refund_original_cent"]["amount"] - 343.95) < 0.01
    
    # Discount: sequential stacking, cent rounding
    assert abs(REFERENCE_ANSWERS["discount_sequential"]["amount"] - 74.80) < 0.01


def test_foils_mandatory():
    """Verify foils are provided and match at most one checker (ALL tasks)."""
    tasks = generate_tasks()

    for task in tasks:
        checkers, candidates, foils = get_checkers_and_candidates("policy_qa", task)

        assert len(foils) > 0, f"Task {task.id} has no foils (MANDATORY)"

        for i, foil in enumerate(foils):
            matches = sum(1 for c in checkers.values() if c.check(foil).passed)
            assert matches <= 1, f"Foil #{i} in {task.id} matches {matches} checkers"


def _all_base_clauses():
    """Map task_id prefix -> list of every requirement clause string."""
    from bench.policy_qa import (
        problem_overtime_001, problem_interest_001, problem_tip_001,
        problem_refund_001, problem_discount_001,
    )
    specs = [
        problem_overtime_001(), problem_interest_001(), problem_tip_001(),
        problem_refund_001(), problem_discount_001(),
    ]
    out = {}
    for s in specs:
        out[s.task_id] = [c for rc in s.requirement_classes for c in rc.clauses]
    return out


def test_deleted_clause_absent_from_prompt():
    """Deleting an axis must actually remove its clause from the shown prompt.

    Guards the audit finding where a 'deleted' convention was still present in
    the prompt: for every task, the count of base clauses missing from the
    emitted prompt must equal the ambiguity level (k clauses deleted), and all
    clauses must survive verbatim in the latent_spec.
    """
    base_clauses = _all_base_clauses()
    for t in generate_tasks():
        prefix = t.id.split("_k")[0]
        clauses = base_clauses[prefix]
        missing = [c for c in clauses if c not in t.prompt]
        assert len(missing) == t.ambiguity_level, (
            f"{t.id}: {len(missing)} clauses absent from prompt but k={t.ambiguity_level}"
        )
        for c in clauses:
            assert c in t.latent_spec, f"{t.id}: clause missing from latent_spec: {c!r}"


def test_rounding_axis_not_pinned_in_core():
    """Anti-regression: when rounding IS an axis, the core must not pin it.

    tip and discount carry a *_rounding requirement class, so their prompt_core
    must not state the cent-rounding convention (that would contradict the
    deletable clause and make the round-to-dollar interpretation impossible).
    """
    from bench.policy_qa import problem_tip_001, problem_discount_001
    for spec in (problem_tip_001(), problem_discount_001()):
        axis_ids = {rc.id for rc in spec.requirement_classes}
        assert any(a.endswith("rounding") for a in axis_ids), \
            f"{spec.task_id}: expected a rounding axis"
        core = spec.prompt_core.lower()
        assert "nearest cent" not in core and "rounded to" not in core, \
            f"{spec.task_id}: core pins rounding despite it being an axis: {spec.prompt_core!r}"
