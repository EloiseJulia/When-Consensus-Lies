"""Tests for policy_qa domain — COMBINATORIAL-INVARIANT reversed reconstruction.

policy_qa is the SECONDARY breadth / cross-domain consistency domain (structured
exact-cent answers, reported as a consistency check, NEVER as accuracy; prereg §7).
Mirrors tests/test_code_spec.py for the reversed binary-axis combinatorial model:
  - Amended per-variant invariant: len(key_questions)==k', len(interpretations)==2^k'
  - Combined-default foil marked [combined-default]; serialized via __combdef
  - Regime validity (all H1_external) and reversed-property assertions
  - 100% distinguishability via exact-cent structured gold
  - GOLDEN test pinning the anchor overtime I0/default amounts ($1000 vs $950)
"""

import pytest
from pathlib import Path

from bench.policy_qa import (
    CHECKERS,
    REFERENCE_ANSWERS,
    get_checkers_and_candidates,
    generate_tasks,
    problem_overtime_001,
    problem_interest_001,
    problem_tip_001,
    problem_refund_001,
    problem_discount_001,
    problem_pay_mileage_001,
)
from bench.validate import validate_domain
from common.schema import VALID_REGIMES


ALL_PROBLEMS = [
    problem_overtime_001,
    problem_interest_001,
    problem_tip_001,
    problem_refund_001,
    problem_discount_001,
    problem_pay_mileage_001,
]


def test_checkers_exist():
    """All 14 checker IDs (2 per k=1 family × 5 + 4 for the k=2 family) are present
    in CHECKERS and REFERENCE_ANSWERS."""
    required_checkers = [
        # policy_overtime_001 (k=1, overtime_threshold axis)
        "overtime_ot35", "overtime_ot40",
        # policy_interest_001 (k=1, compounding axis)
        "interest_compound_monthly", "interest_simple",
        # policy_tip_001 (k=1, tip_base axis)
        "tip_posttax", "tip_pretax",
        # policy_refund_001 (k=1, fee_basis axis)
        "refund_fullbase", "refund_merchbase",
        # policy_discount_001 (k=1, discount_basis axis)
        "discount_additive", "discount_sequential",
        # policy_paymileage_001 (k=2, overtime_threshold + mileage_rate axes)
        "pay_ot35_contract", "pay_ot35_irs",
        "pay_ot40_contract", "pay_ot40_irs",
    ]
    for checker_id in required_checkers:
        assert checker_id in CHECKERS, f"Missing checker: {checker_id}"
        assert checker_id in REFERENCE_ANSWERS, f"Missing reference: {checker_id}"


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


def test_golden_overtime_anchor_amounts():
    """GOLDEN: the REQUIRED anchor (k=1, overtime_threshold) pins I0/default amounts.

    I0 = union-contract overtime after 35h = $1000.00 (NON-default true intent).
    Combined-default foil = standard FLSA overtime after 40h = $950.00.
    These are frozen: a regression here inverts the reversed-property construction.
    """
    assert REFERENCE_ANSWERS["overtime_ot35"] == {"amount": 1000.00}
    assert REFERENCE_ANSWERS["overtime_ot40"] == {"amount": 950.00}

    spec = problem_overtime_001()
    target = next(i for i in spec.interpretations if i.is_target)
    assert target.gold_check == "overtime_ot35", "anchor I0 must be the 35h contract term"

    # The k=1 variant surfaces exactly {I0=1000, I1=950 [combined-default]}.
    task = next(t for t in generate_tasks()
                if t.id == "policy_overtime_001_k1_overtime_threshold")
    checkers, candidates, _ = get_checkers_and_candidates("policy_qa", task)
    i0 = next(interp.id for interp in task.interpretations if interp.is_target)
    assert candidates[i0] == {"amount": 1000.00}
    # $950 default answer must FAIL the I0 target checker (reversed property).
    assert not checkers[i0].check({"amount": 950.00}).passed


def test_reversed_property_natural_default_is_foil():
    """REVERSED property: for every family, the model's natural/population default
    answer FAILS the I0 (non-default) target checker and PASSES only the
    combined-default foil checker.
    """
    # (family target checker, natural-default answer, combined-default foil checker)
    cases = [
        ("overtime_ot35", {"amount": 950.00}, "overtime_ot40"),
        ("interest_compound_monthly", {"amount": 147.95}, "interest_simple"),
        ("tip_posttax", {"amount": 7.50}, "tip_pretax"),
        ("refund_fullbase", {"amount": 343.90}, "refund_merchbase"),
        ("discount_additive", {"amount": 74.80}, "discount_sequential"),
    ]
    for target_id, natural_default, foil_id in cases:
        assert not CHECKERS[target_id].check(natural_default).passed, \
            f"{target_id}: natural default must FAIL the I0 target checker"
        assert CHECKERS[foil_id].check(natural_default).passed, \
            f"{foil_id}: natural default must PASS the combined-default foil checker"


def test_target_description_labels_nondefault():
    """I0 description must include 'NON-default'; at least one foil must include
    '[combined-default]' (Amendment 03 marker) in every FullSpec."""
    for spec_fn in ALL_PROBLEMS:
        spec = spec_fn()
        target = next(i for i in spec.interpretations if i.is_target)
        assert "NON-default" in target.description, \
            f"{spec.task_id}: I0 description must contain 'NON-default'"
        foil_descs = [i.description for i in spec.interpretations if not i.is_target]
        assert any("[combined-default]" in d for d in foil_descs), \
            f"{spec.task_id}: a foil must be labeled '[combined-default]'"


def test_combined_default_marked():
    """Amendment 03: for every k>=1 variant, exactly ONE interpretation's gold_check
    ends in '__combdef' (the per-variant combined-all-default marker), and it is
    non-target. k=0 controls have zero markers."""
    tasks = generate_tasks()
    for t in tasks:
        k = t.ambiguity_level
        combdef = [i for i in t.interpretations if i.gold_check.endswith("__combdef")]
        if k == 0:
            assert len(combdef) == 0, f"{t.id}: k=0 control must have no __combdef"
        else:
            assert len(combdef) == 1, \
                f"{t.id}: expected exactly 1 __combdef, got {len(combdef)}: " \
                f"{[i.gold_check for i in t.interpretations]}"
            assert not combdef[0].is_target, \
                f"{t.id}: __combdef interpretation must be non-target"


def test_malformed_powerset_rejected():
    """validate_full_spec rejects combinatorial specs with non-power-set opened_by
    sets (2 classes, 3 non-targets, but duplicate {A} and missing {B})."""
    from bench.build import (
        FullSpec, RequirementClass, InterpretationBranch, validate_full_spec
    )
    malformed = FullSpec(
        domain="policy_qa",
        task_id="test_malformed",
        prompt_core="test core",
        requirement_classes=[
            RequirementClass(id="axis_a", description="Axis A", clauses=["clause A"]),
            RequirementClass(id="axis_b", description="Axis B", clauses=["clause B"]),
        ],
        interpretations=[
            InterpretationBranch(id="I0", description="target", is_target=True,
                                 gold_check="chk_target"),
            InterpretationBranch(id="I1", description="a1", is_target=False,
                                 gold_check="chk_a1", opened_by="axis_a"),
            InterpretationBranch(id="I2", description="a2 dup", is_target=False,
                                 gold_check="chk_a2", opened_by="axis_a"),
            InterpretationBranch(id="I3", description="both", is_target=False,
                                 gold_check="chk_ab", opened_by="axis_a,axis_b"),
        ],
        key_questions=["Q1?", "Q2?"],
        regime="H1_external",
    )
    with pytest.raises(ValueError, match="duplicate"):
        validate_full_spec(malformed)


def test_k2_axes_independent():
    """k=2 pay+mileage: the two external conventions are ADDITIVELY INDEPENDENT.

    The overtime delta (I0-I2) equals (I1-I3), and the mileage delta (I0-I1)
    equals (I2-I3): deleting one axis does not change the other's contribution.
    All four amounts are pairwise distinct.
    """
    a = {k: REFERENCE_ANSWERS[k]["amount"] for k in (
        "pay_ot35_contract", "pay_ot35_irs", "pay_ot40_contract", "pay_ot40_irs"
    )}
    I0, I1, I2, I3 = (a["pay_ot35_contract"], a["pay_ot35_irs"],
                      a["pay_ot40_contract"], a["pay_ot40_irs"])
    # overtime delta constant across mileage settings
    assert round(I0 - I2, 2) == round(I1 - I3, 2) == 50.00
    # mileage delta constant across overtime settings
    assert round(I0 - I1, 2) == round(I2 - I3, 2) == 4.50
    # pairwise distinct with margin well above the 0.01 checker tolerance
    vals = sorted([I0, I1, I2, I3])
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            assert abs(vals[i] - vals[j]) > 0.05, \
                f"pay amounts too close: {vals[i]} vs {vals[j]}"


def test_amounts_pairwise_distinct_per_family():
    """Within each family, all interpretation amounts are pairwise distinct with a
    safety margin (5x) above the checker's 0.01 exact-cent tolerance."""
    families = {
        "overtime": ["overtime_ot35", "overtime_ot40"],
        "interest": ["interest_compound_monthly", "interest_simple"],
        "tip": ["tip_posttax", "tip_pretax"],
        "refund": ["refund_fullbase", "refund_merchbase"],
        "discount": ["discount_additive", "discount_sequential"],
        "paymileage": ["pay_ot35_contract", "pay_ot35_irs",
                       "pay_ot40_contract", "pay_ot40_irs"],
    }
    SAFETY_FLOOR = 0.05
    for name, ids in families.items():
        amounts = sorted(REFERENCE_ANSWERS[i]["amount"] for i in ids)
        for i in range(len(amounts)):
            for j in range(i + 1, len(amounts)):
                diff = abs(amounts[i] - amounts[j])
                assert diff > SAFETY_FLOOR, \
                    f"{name}: amounts {amounts[i]} and {amounts[j]} too close ({diff:.4f})"


def test_task_generation():
    """14 tasks generated with the correct k-distribution (Amendment 03)."""
    tasks = generate_tasks()
    assert len(tasks) == 14, f"Expected 14 tasks, got {len(tasks)}"

    for task in tasks:
        assert task.id, "Task missing ID"
        assert task.domain == "policy_qa", "Wrong domain"
        assert task.prompt, "Task missing prompt"
        assert task.latent_spec, "Task missing latent_spec"
        k = task.ambiguity_level
        assert len(task.interpretations) == 2 ** k, \
            f"{task.id}: expected 2^{k} interps, got {len(task.interpretations)}"
        assert len(task.key_questions) == k, \
            f"{task.id}: key_questions count must equal ambiguity_level"
        targets = [i for i in task.interpretations if i.is_target]
        assert len(targets) == 1 and targets[0].id == "I0", \
            f"{task.id}: must have exactly one target I0"

    levels = {k: sum(1 for t in tasks if t.ambiguity_level == k) for k in range(3)}
    assert levels[0] == 6, f"Expected 6 k=0 controls, got {levels[0]}"
    assert levels[1] == 7, f"Expected 7 k=1 tasks, got {levels[1]}"
    assert levels[2] == 1, f"Expected 1 k=2 task, got {levels[2]}"


def test_task_regime_valid():
    """Every task carries a valid regime value, and all are H1_external."""
    tasks = generate_tasks()
    for t in tasks:
        assert t.regime in VALID_REGIMES, \
            f"{t.id}: invalid regime {t.regime!r}"
    regimes = {t.regime for t in tasks}
    assert regimes == {"H1_external"}, \
        f"policy_qa reversed traps must all be H1_external, got {regimes}"


def test_domain_validation():
    """Domain validation reports 100% distinguishable."""
    data_path = Path(__file__).parent.parent / "bench" / "data" / "policy_qa.jsonl"
    if not data_path.exists():
        pytest.skip("Data file not yet generated")

    summary = validate_domain("policy_qa", data_path, get_checkers_and_candidates)
    assert summary["distinguishable_count"] > 0, "No distinguishable tasks"
    assert summary["distinguishable_pct"] == 100.0, \
        f"Not all tasks distinguishable: {summary['distinguishable_pct']:.1f}%"
    assert len(summary["failed_tasks"]) == 0, f"Tasks failed: {summary['failed_tasks']}"


def test_100pct_reference_candidates_distinguishable():
    """Reference answers pass ONLY their own checker (100% distinguishable)."""
    family_groups = [
        ["overtime_ot35", "overtime_ot40"],
        ["interest_compound_monthly", "interest_simple"],
        ["tip_posttax", "tip_pretax"],
        ["refund_fullbase", "refund_merchbase"],
        ["discount_additive", "discount_sequential"],
        ["pay_ot35_contract", "pay_ot35_irs",
         "pay_ot40_contract", "pay_ot40_irs"],
    ]
    for group in family_groups:
        for target_id in group:
            answer = REFERENCE_ANSWERS[target_id]
            for checker_id in group:
                result = CHECKERS[checker_id].check(answer)
                if checker_id == target_id:
                    assert result.passed, \
                        f"{target_id} must pass its own checker {checker_id}"
                else:
                    assert not result.passed, \
                        f"{target_id} must NOT pass checker {checker_id}"


def test_foils_mandatory():
    """Foils are provided and match AT MOST ONE checker (ALL tasks)."""
    tasks = generate_tasks()
    for task in tasks:
        checkers, candidates, foils = get_checkers_and_candidates("policy_qa", task)
        assert len(foils) > 0, f"Task {task.id} has no foils (MANDATORY)"
        for i, foil in enumerate(foils):
            matches = sum(1 for c in checkers.values() if c.check(foil).passed)
            assert matches <= 1, f"Foil #{i} in {task.id} matches {matches} checkers"


def _all_base_clauses():
    """Map task_id prefix -> list of every requirement clause string."""
    out = {}
    for spec_fn in ALL_PROBLEMS:
        s = spec_fn()
        out[s.task_id] = [c for rc in s.requirement_classes for c in rc.clauses]
    return out


def test_deleted_clause_absent_from_prompt():
    """Deleting an axis must actually remove its clause from the shown prompt.

    For every task, the count of base clauses missing from the emitted prompt
    must equal the ambiguity level (k clauses deleted), and all clauses must
    survive verbatim in the latent_spec.
    """
    base_clauses = _all_base_clauses()
    for t in generate_tasks():
        prefix = t.id.split("_k")[0]
        clauses = base_clauses[prefix]
        missing = [c for c in clauses if c not in t.prompt]
        assert len(missing) == t.ambiguity_level, \
            f"{t.id}: {len(missing)} clauses absent from prompt but k={t.ambiguity_level}"
        for c in clauses:
            assert c in t.latent_spec, f"{t.id}: clause missing from latent_spec: {c!r}"


def test_prompt_vs_latent_spec():
    """k=0 controls have prompt==latent_spec; k>=1 tasks have strictly shorter prompt."""
    for task in generate_tasks():
        if task.ambiguity_level == 0:
            assert task.prompt == task.latent_spec, \
                f"k=0 control {task.id} has prompt != latent_spec"
        else:
            assert len(task.prompt) < len(task.latent_spec), \
                f"k={task.ambiguity_level} task {task.id} prompt not shorter than latent_spec"


def test_no_prompt_leakage_k2():
    """The stacked k=2 family's prompt_core must not leak either axis's convention
    (concrete threshold hours or per-mile rate), so deleting an axis truly removes
    its disambiguator."""
    core = problem_pay_mileage_001().prompt_core
    assert "35 hours" not in core, "k=2 core leaks the 35h contract threshold"
    assert "40 hours" not in core, "k=2 core leaks the 40h default threshold"
    assert "0.70" not in core and "0.655" not in core, "k=2 core leaks a mileage rate"

    # When mileage_rate is the ONLY deleted axis, the $0.70 clause value is gone.
    tasks = generate_tasks()
    mileage_only = next(t for t in tasks
                        if t.id == "policy_paymileage_001_k1_mileage_rate")
    assert "0.70" not in mileage_only.prompt, \
        "mileage_rate deleted but '$0.70/mile' still present in prompt"


def test_structured_answer_checker_exact_cent():
    """StructuredAnswerChecker stays deterministic exact-cent (NO LLM): matches on
    the cent, rejects off-by-a-cent, wrong key, wrong type, and parses JSON strings."""
    checker = CHECKERS["overtime_ot35"]  # expects {"amount": 1000.00}
    assert checker.check({"amount": 1000.00}).passed
    assert checker.check({"amount": 1000.004}).passed          # within half a cent
    assert not checker.check({"amount": 1000.01}).passed        # off by a cent
    assert not checker.check({"total": 1000.00}).passed         # wrong key
    assert not checker.check({"amount": "1000.00"}).passed      # wrong value type
    assert checker.check('{"amount": 1000.00}').passed          # JSON string parsed
    assert not checker.check(1000.00).passed                    # bare number, wrong structure
