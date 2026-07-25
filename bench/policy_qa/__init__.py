# item semantics constructed by Microsoft mai-code-1-flash (out-of-pool constructor); executable gold-checkers + module implemented by Claude (Anthropic), cross-family audited
"""Policy question-answering domain for ambiguous policy interpretation.

This domain features numeric policy calculations where deleting a requirement CLASS
(a convention clause) creates GENUINE ambiguity about the correct answer. Gold
checkers are deterministic (structured equality with numeric tolerance, NO LLM)
because answers are STRUCTURED numeric values (dict with float), not free-form prose.

All answers are {"amount": <float>} with exact cent-precision comparison.
"""

from typing import Any, Dict, List, Tuple
import textwrap
import json

from bench.build import (
    FullSpec,
    InterpretationBranch,
    RequirementClass,
    assemble_task,
    save_tasks,
)
from bench.gold.base import CheckResult, GoldChecker
from common.schema import Task


# ============================================================================
# GOLD CHECKERS - Deterministic structured equality
# ============================================================================

class StructuredAnswerChecker(GoldChecker):
    """Checks a structured answer (dict/str) against expected value deterministically.
    
    NO LLM. Supports:
    - Exact equality for dicts/strings (case-insensitive for strings)
    - Numeric tolerance for float values
    - Rejects wrong types (bool where number expected, etc.)
    """
    
    def __init__(self, expected: Any, description: str = ""):
        """
        Args:
            expected: The expected answer (dict, str, int, float)
            description: Human-readable id for diagnostics
        """
        self.expected = expected
        self.description = description
    
    def _compare(self, candidate: Any, expected: Any) -> Tuple[bool, str]:
        """Recursive structured comparison with type checking."""
        # Type mismatch (reject bool where number expected, etc.)
        if type(candidate) != type(expected):
            # Special case: allow int where float expected (or vice versa)
            if isinstance(candidate, (int, float)) and isinstance(expected, (int, float)):
                pass
            else:
                return False, f"Type mismatch: expected {type(expected).__name__}, got {type(candidate).__name__}"
        
        if isinstance(expected, dict):
            if not isinstance(candidate, dict):
                return False, f"Expected dict, got {type(candidate).__name__}"
            if set(candidate.keys()) != set(expected.keys()):
                return False, f"Key mismatch: expected {set(expected.keys())}, got {set(candidate.keys())}"
            for key in expected:
                passed, msg = self._compare(candidate[key], expected[key])
                if not passed:
                    return False, f"Key '{key}': {msg}"
            return True, "Match"
        
        elif isinstance(expected, str):
            if not isinstance(candidate, str):
                return False, f"Expected str, got {type(candidate).__name__}"
            # Case-insensitive + strip whitespace
            if candidate.strip().lower() != expected.strip().lower():
                return False, f"Expected '{expected}', got '{candidate}'"
            return True, "Match"
        
        elif isinstance(expected, (int, float)):
            if not isinstance(candidate, (int, float)):
                return False, f"Expected number, got {type(candidate).__name__}"
            # Exact cent-precision comparison for monetary amounts (floats)
            # Compare as integer cents to avoid floating-point errors
            if isinstance(expected, float):
                candidate_cents = round(candidate * 100)
                expected_cents = round(expected * 100)
                if candidate_cents != expected_cents:
                    return False, f"Expected {expected}, got {candidate} (off by {abs(candidate - expected):.4f})"
            else:
                if candidate != expected:
                    return False, f"Expected {expected}, got {candidate}"
            return True, "Match"
        
        elif isinstance(expected, bool):
            if not isinstance(candidate, bool):
                return False, f"Expected bool, got {type(candidate).__name__}"
            if candidate != expected:
                return False, f"Expected {expected}, got {candidate}"
            return True, "Match"
        
        elif expected is None:
            if candidate is not None:
                return False, f"Expected None, got {candidate}"
            return True, "Match"
        
        else:
            # Fallback: exact equality
            if candidate != expected:
                return False, f"Expected {expected}, got {candidate}"
            return True, "Match"
    
    def check(self, candidate: Any) -> CheckResult:
        """Check if candidate matches expected structure."""
        # If candidate is a JSON string, parse it first
        if isinstance(candidate, str):
            try:
                candidate = json.loads(candidate)
            except (json.JSONDecodeError, ValueError):
                # Not JSON, treat as plain string
                pass
        
        passed, msg = self._compare(candidate, self.expected)
        details = f"{self.description} - {msg}"
        return CheckResult(passed=passed, details=details)


# ============================================================================
# PROBLEM LIBRARY — COMBINATORIAL-INVARIANT reversed-target policy tasks
# (Amendment 03; SECONDARY breadth / cross-domain consistency domain, prereg §7)
#
# Every axis is strictly BINARY {target, default} and H1_external: the deleted
# clause states an EXTERNAL contract/house convention (non-default true intent);
# deleting it makes an unaware model fall back to the standard/population rule
# (a WRONG foil, marked [combined-default]). Answers are structured
# {"amount": <float>} compared EXACT-CENT (deterministic, NO LLM).
#
# Single-axis families (k=1 -> 2^1 = 2 interps: I0 target + I1 [combined-default]):
#   policy_overtime_001   axis overtime_threshold  I0 OT@35h=1000.00 / def OT@40h=950.00
#   policy_interest_001   axis compounding         I0 monthly=150.75 / def simple=147.95
#   policy_tip_001        axis tip_base            I0 post-tax=8.10  / def pre-tax=7.50
#   policy_refund_001     axis fee_basis           I0 full-base=341.91 / def merch=343.90
#   policy_discount_001   axis discount_basis      I0 additive=73.00 / def sequential=74.80
#
# Multi-axis family (k=2 -> 2^2 = 4 interps; two INDEPENDENT external conventions):
#   policy_paymileage_001 axes overtime_threshold + mileage_rounding
#   (mileage RATE is GIVEN in the prompt at $0.60/mi on 104 mi = $62.40; only a
#    METHOD is disputed, so — unlike a disputed rate — the default is timeless:
#    exact-cent currency is THE universal default; the stated non-default clause
#    rounds the reimbursement UP to the next whole dollar = $63.00.)
#     I0 OT@35h + round-up $63.00 = 1063.00 [all-target]
#     I1 OT@35h + exact-cent $62.40 = 1062.40 [mileage_rounding defaulted]
#     I2 OT@40h + round-up $63.00 = 1013.00 [overtime defaulted]
#     I3 OT@40h + exact-cent $62.40 = 1012.40 [combined-default]
#
# Amended invariant (Amendment 03), per variant deleting S (|S|=k'):
#   len(key_questions) == k'
#   len(interpretations) == 2^k'   (full combinatorial set)
#   I0 = all-target; combined-all-default foil marked [combined-default]
#   (build.py appends __combdef to the serialized gold_check automatically).
#   100% distinguishable across ALL 2^k' via exact-cent structured gold.
# ============================================================================


def problem_overtime_001():
    """k=1 family, single axis overtime_threshold (anchor, REQUIRED).

    H1_external: the union-contract overtime threshold is EXTERNAL policy, not
    prompt-derivable. Model defaults to the standard FLSA 40h rule (a WRONG foil).
    1 req class -> 2^1 = 2 interps: I0 (target) + I1 ([combined-default]).
    """
    return FullSpec(
        domain="policy_qa",
        task_id="policy_overtime_001",
        regime="H1_external",
        prompt_core=(
            "An employee worked 45 hours in one week at a base pay rate of "
            "$20.00 per hour. Overtime hours are paid at 1.5 times the base rate. "
            "Compute the employee's gross pay for the week, rounded to the nearest cent."
        ),
        requirement_classes=[
            RequirementClass(
                id="overtime_threshold",
                description="Weekly hours before overtime applies",
                clauses=[
                    "Under this employer's union contract, overtime begins after "
                    "35 hours per week."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: union-contract overtime after 35h (target). "
                    "35*20 + 10*30 = $1000.00."
                ),
                is_target=True,
                gold_check="overtime_ot35",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: standard FLSA overtime after 40h. "
                    "40*20 + 5*30 = $950.00."
                ),
                is_target=False,
                gold_check="overtime_ot40",
                opened_by="overtime_threshold",
            ),
        ],
        key_questions=[
            "After how many hours per week does overtime begin (the contract threshold)?",
        ],
    )


def problem_interest_001():
    """k=1 family, single axis compounding.

    H1_external: the loan contract's MONTHLY compounding is an EXTERNAL term.
    Model defaults to naive simple interest (a WRONG foil).
    1 req class -> 2^1 = 2 interps: I0 (target) + I1 ([combined-default]).
    """
    return FullSpec(
        domain="policy_qa",
        task_id="policy_interest_001",
        regime="H1_external",
        prompt_core=(
            "A loan of $10,000.00 has an annual interest rate of 6%, based on a "
            "365-day year, and is outstanding for 90 days. Compute the interest "
            "owed, rounded to the nearest cent."
        ),
        requirement_classes=[
            RequirementClass(
                id="compounding",
                description="Whether interest compounds",
                clauses=[
                    "Per the loan contract, interest COMPOUNDS MONTHLY at 6%/12 "
                    "(0.5%) per month over the three months."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: contract monthly compounding (target). "
                    "10000*((1+0.06/12)^3 - 1) = $150.75."
                ),
                is_target=True,
                gold_check="interest_compound_monthly",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: naive simple interest. "
                    "10000*0.06*90/365 = $147.95."
                ),
                is_target=False,
                gold_check="interest_simple",
                opened_by="compounding",
            ),
        ],
        key_questions=[
            "Does interest compound monthly per the contract, or is it simple (non-compounding)?",
        ],
    )


def problem_tip_001():
    """k=1 family, single axis tip_base.

    H1_external: the venue's house gratuity policy (tip on the full post-tax
    total) is an EXTERNAL convention. Model defaults to the standard pre-tax
    etiquette basis (a WRONG foil).
    1 req class -> 2^1 = 2 interps: I0 (target) + I1 ([combined-default]).
    """
    return FullSpec(
        domain="policy_qa",
        task_id="policy_tip_001",
        regime="H1_external",
        prompt_core=(
            "A restaurant bill totals $54.00, consisting of $50.00 for food and "
            "$4.00 in tax. Compute a 15% tip, rounded to the nearest cent."
        ),
        requirement_classes=[
            RequirementClass(
                id="tip_base",
                description="Base amount the gratuity is computed on",
                clauses=[
                    "Per this venue's house gratuity policy, the tip is calculated "
                    "on the full post-tax bill total (food plus tax)."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: house policy tip on the post-tax total (target). "
                    "0.15*54 = $8.10."
                ),
                is_target=True,
                gold_check="tip_posttax",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: standard pre-tax etiquette basis. "
                    "0.15*50 = $7.50."
                ),
                is_target=False,
                gold_check="tip_pretax",
                opened_by="tip_base",
            ),
        ],
        key_questions=[
            "Is the tip calculated on the full post-tax bill total (house policy) "
            "or the standard pre-tax food subtotal?",
        ],
    )


def problem_refund_001():
    """k=1 family, single axis fee_basis.

    H1_external: the return contract's restocking-fee basis (the full credited
    amount, merchandise plus shipping) is an EXTERNAL term. Model defaults to the
    standard basis of merchandise price only (a WRONG foil).
    1 req class -> 2^1 = 2 interps: I0 (target) + I1 ([combined-default]).
    """
    return FullSpec(
        domain="policy_qa",
        task_id="policy_refund_001",
        regime="H1_external",
        prompt_core=(
            "A customer returns merchandise originally priced at $360.00. The "
            "return includes a $19.90 shipping credit, and a 10% restocking fee "
            "applies. Compute the net refund, rounded to the nearest cent."
        ),
        requirement_classes=[
            RequirementClass(
                id="fee_basis",
                description="Base amount the restocking fee is assessed on",
                clauses=[
                    "Per the return contract, the 10% restocking fee is assessed on "
                    "the FULL credited amount (merchandise price plus the shipping credit)."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: fee on the full credited amount (target). "
                    "(360+19.90) - 0.10*(360+19.90) = 379.90 - 37.99 = $341.91."
                ),
                is_target=True,
                gold_check="refund_fullbase",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: fee on the merchandise price only. "
                    "(360+19.90) - 0.10*360 = 379.90 - 36.00 = $343.90."
                ),
                is_target=False,
                gold_check="refund_merchbase",
                opened_by="fee_basis",
            ),
        ],
        key_questions=[
            "Is the 10% restocking fee assessed on the full credited amount "
            "(merchandise plus shipping) or only on the original merchandise price?",
        ],
    )


def problem_discount_001():
    """k=1 family, single axis discount_basis.

    H1_external: the promotion's ADDITIVE stacking term (add the two percentages
    and apply once to the original price) is an EXTERNAL term. Model defaults to
    the standard sequential/compounded stacking (a WRONG foil).
    1 req class -> 2^1 = 2 interps: I0 (target) + I1 ([combined-default]).
    """
    return FullSpec(
        domain="policy_qa",
        task_id="policy_discount_001",
        regime="H1_external",
        prompt_core=(
            "An item is priced at $100.00 and has two promotional discounts of "
            "15% and 12%. Compute the final price, rounded to the nearest cent."
        ),
        requirement_classes=[
            RequirementClass(
                id="discount_basis",
                description="How the two discounts combine",
                clauses=[
                    "Per the promotion terms, the two discount percentages are ADDED "
                    "into a single percentage and applied once to the original price "
                    "(not compounded)."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: additive stacking, one combined percentage (target). "
                    "100*(1 - 0.27) = $73.00."
                ),
                is_target=True,
                gold_check="discount_additive",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: standard sequential/compounded stacking. "
                    "100*0.85*0.88 = $74.80."
                ),
                is_target=False,
                gold_check="discount_sequential",
                opened_by="discount_basis",
            ),
        ],
        key_questions=[
            "Are the two discounts added into a single percentage off the original "
            "price (promotion terms), or applied sequentially/compounded?",
        ],
    )


def problem_pay_mileage_001():
    """k=2 family, axes overtime_threshold + mileage_rounding.

    H1_external: BOTH conventions are EXTERNAL house policy (union-contract
    overtime threshold and a travel-policy rounding rule); the model defaults on
    both when both are deleted.

    WHY THE SECOND AXIS IS TIMELESS (answering the auditor's mileage-rate
    objection): the per-mile RATE is GIVEN in the prompt ($0.60/mi on 104 mi =
    $62.40 exact), so the rate is NOT ambiguous. The only disputed thing is a
    METHOD: how the reimbursement is rounded. The natural default is the ONE
    timeless universal currency convention — settle to the exact cent ($62.40).
    The stated non-default clause is a specific generous house rule — round the
    mileage reimbursement UP to the next whole dollar ($63.00). Deleting that
    clause leaves exactly ONE plausible default (exact cents), not a family of
    year-/employer-dependent numbers, so the reversal is fair: a human reading
    the full latent_spec (which states the round-up rule) agrees the user wanted
    $63.00.

    INDEPENDENCE (verified): total = wages(overtime_threshold)
    + mileage_reimbursement(mileage_rounding) is ADDITIVELY SEPARABLE. The wages
    component depends only on the overtime threshold (1000.00 at 35h, 950.00 at
    40h). The mileage component is a FIXED $62.40 sub-total (104 mi * $0.60/mi)
    that depends only on the rounding rule (63.00 rounded up, 62.40 exact) and
    references NEITHER hours NOR wages. Deleting/varying one axis leaves the
    other component's amount unchanged:
        overtime delta  = 50.00 constant   (I0-I2 = I1-I3 = 50.00)
        rounding delta  =  0.60 constant   (I0-I1 = I2-I3 =  0.60)
    Because the rounding delta (0.60) differs from the overtime delta (50.00)
    and from 0, all four 2x2 combinations are pairwise distinct.

    2 req classes -> 2^2 = 4 interpretations:
      I0  OT@35h + round-up $63.00 = 1063.00 [all-target]
      I1  OT@35h + exact-cent $62.40 = 1062.40 [mileage_rounding defaulted]
      I2  OT@40h + round-up $63.00 = 1013.00 [overtime_threshold defaulted]
      I3  OT@40h + exact-cent $62.40 = 1012.40 [combined-default]

    Combinatorial variants from generate_tasks:
      k0                                 -> {I0}
      k1 delete overtime_threshold       -> {I0, I2}
      k1 delete mileage_rounding         -> {I0, I1}
      k2 delete both                     -> {I0, I1, I2, I3}
    """
    return FullSpec(
        domain="policy_qa",
        task_id="policy_paymileage_001",
        regime="H1_external",
        prompt_core=(
            "An employee worked 45 hours this week at a base pay rate of $20.00 "
            "per hour (overtime hours are paid at 1.5 times the base rate), and "
            "also drove 104 miles for work that are reimbursed at $0.60 per mile. "
            "Compute the employee's total pay for the week (gross wages plus "
            "mileage reimbursement), rounded to the nearest cent."
        ),
        requirement_classes=[
            RequirementClass(
                id="overtime_threshold",
                description="Weekly hours before overtime applies",
                clauses=[
                    "Under this employer's union contract, overtime begins after "
                    "35 hours per week."
                ],
            ),
            RequirementClass(
                id="mileage_rounding",
                description="How the mileage reimbursement is rounded",
                clauses=[
                    "Per the employer's travel policy, the mileage reimbursement "
                    "is rounded UP to the next whole dollar."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: contract overtime after 35h + mileage rounded up "
                    "to the next whole dollar (target, all-target). "
                    "1000.00 + 63.00 = $1063.00."
                ),
                is_target=True,
                gold_check="pay_ot35_roundup",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "Partial default: overtime after 35h + exact-cent mileage "
                    "(mileage_rounding defaulted). 1000.00 + 62.40 = $1062.40."
                ),
                is_target=False,
                gold_check="pay_ot35_exact",
                opened_by="mileage_rounding",
            ),
            InterpretationBranch(
                id="I2",
                description=(
                    "Partial default: standard FLSA overtime after 40h + mileage "
                    "rounded up (overtime_threshold defaulted). "
                    "950.00 + 63.00 = $1013.00."
                ),
                is_target=False,
                gold_check="pay_ot40_roundup",
                opened_by="overtime_threshold",
            ),
            InterpretationBranch(
                id="I3",
                description=(
                    "MODEL DEFAULT [combined-default]: standard FLSA overtime after 40h + "
                    "exact-cent mileage (both defaulted). 950.00 + 62.40 = $1012.40."
                ),
                is_target=False,
                gold_check="pay_ot40_exact",
                opened_by="overtime_threshold,mileage_rounding",
            ),
        ],
        key_questions=[
            "After how many hours per week does overtime begin (the contract threshold)?",
            "How is the mileage reimbursement rounded (the travel-policy rule)?",
        ],
    )


# ============================================================================
# REFERENCE ANSWERS - One structured answer per interpretation (exact-cent gold)
# ============================================================================

REFERENCE_ANSWERS = {
    # Overtime gross pay (policy_overtime_001) — axis overtime_threshold
    "overtime_ot35": {"amount": 1000.00},   # I0 (non-default: 35h contract)
    "overtime_ot40": {"amount": 950.00},    # I1 [combined-default] (40h FLSA)

    # Interest owed (policy_interest_001) — axis compounding
    "interest_compound_monthly": {"amount": 150.75},  # I0 (non-default: monthly compound)
    "interest_simple": {"amount": 147.95},            # I1 [combined-default] (simple)

    # Restaurant tip (policy_tip_001) — axis tip_base
    "tip_posttax": {"amount": 8.10},   # I0 (non-default: post-tax total)
    "tip_pretax": {"amount": 7.50},    # I1 [combined-default] (pre-tax)

    # Merchandise refund (policy_refund_001) — axis fee_basis
    "refund_fullbase": {"amount": 341.91},   # I0 (non-default: fee on full credited amount)
    "refund_merchbase": {"amount": 343.90},  # I1 [combined-default] (fee on merchandise)

    # Stacked discount (policy_discount_001) — axis discount_basis
    "discount_additive": {"amount": 73.00},    # I0 (non-default: additive)
    "discount_sequential": {"amount": 74.80},  # I1 [combined-default] (sequential)

    # Pay + mileage (policy_paymileage_001) — axes overtime_threshold + mileage_rounding
    "pay_ot35_roundup": {"amount": 1063.00},   # I0 (all-target: 35h contract + round-up)
    "pay_ot35_exact": {"amount": 1062.40},     # I1 (mileage_rounding defaulted: exact cents)
    "pay_ot40_roundup": {"amount": 1013.00},   # I2 (overtime defaulted: 40h + round-up)
    "pay_ot40_exact": {"amount": 1012.40},     # I3 [combined-default] (40h + exact cents)
}


# ============================================================================
# CHECKERS REGISTRY
# ============================================================================

CHECKERS = {}

for check_id, expected in REFERENCE_ANSWERS.items():
    CHECKERS[check_id] = StructuredAnswerChecker(expected, description=check_id)


# ============================================================================
# TASK GENERATION
# ============================================================================

def generate_tasks() -> List[Task]:
    """Generate all 14 policy_qa tasks (Amendment 03 combinatorial invariant).

    Amended invariant per variant (enforced by post-generation assertion):
        len(key_questions) == k'       (deleted-axis count)
        len(interpretations) == 2^k'   (full combinatorial set)
        I0 = all-target; combined-all-default marked [combined-default]
        k0 control: prompt==latent_spec, 1 interp, empty key_questions.

    Task count:
        5 k=1 families x 2 variants  = 10
        1 k=2 family   x 4 variants  =  4
        Total                        = 14
    """
    tasks = []

    # ── k=1 single-axis families ─────────────────────────────────────────────
    k1_specs = [
        problem_overtime_001(),
        problem_interest_001(),
        problem_tip_001(),
        problem_refund_001(),
        problem_discount_001(),
    ]

    for base_spec in k1_specs:
        base_id = base_spec.task_id
        axis_id = base_spec.requirement_classes[0].id
        qmap = {
            rc.id: q
            for rc, q in zip(base_spec.requirement_classes, base_spec.key_questions)
        }
        for suffix, delete_ids in [
            ("_k0", []),
            (f"_k1_{axis_id}", [axis_id]),
        ]:
            spec_copy = FullSpec(
                domain=base_spec.domain,
                task_id=base_id + suffix,
                prompt_core=base_spec.prompt_core,
                requirement_classes=base_spec.requirement_classes[:],
                interpretations=base_spec.interpretations[:],
                key_questions=base_spec.key_questions[:],
                regime=base_spec.regime,
            )
            task = assemble_task(
                spec_copy, k=len(delete_ids),
                classes_to_delete=delete_ids if delete_ids else None,
            )
            task.key_questions = [qmap[cid] for cid in delete_ids]
            tasks.append(task)

    # ── k=2 family: policy_paymileage_001 ────────────────────────────────────
    pm_spec = problem_pay_mileage_001()
    pm_qmap = {
        rc.id: q
        for rc, q in zip(pm_spec.requirement_classes, pm_spec.key_questions)
    }
    for suffix, delete_ids in [
        ("_k0",                    []),
        ("_k1_overtime_threshold", ["overtime_threshold"]),
        ("_k1_mileage_rounding",   ["mileage_rounding"]),
        ("_k2_all",                ["overtime_threshold", "mileage_rounding"]),
    ]:
        spec_copy = FullSpec(
            domain=pm_spec.domain,
            task_id=pm_spec.task_id + suffix,
            prompt_core=pm_spec.prompt_core,
            requirement_classes=pm_spec.requirement_classes[:],
            interpretations=pm_spec.interpretations[:],
            key_questions=pm_spec.key_questions[:],
            regime=pm_spec.regime,
        )
        task = assemble_task(
            spec_copy, k=len(delete_ids),
            classes_to_delete=delete_ids if delete_ids else None,
        )
        task.key_questions = [pm_qmap[cid] for cid in delete_ids]
        tasks.append(task)

    # ── Post-generation amended-invariant gate (fail fast) ────────────────────
    for t in tasks:
        k_prime = t.ambiguity_level
        expected_interps = 2 ** k_prime
        if len(t.interpretations) != expected_interps:
            raise AssertionError(
                f"{t.id}: expected 2^{k_prime}={expected_interps} interpretations, "
                f"got {len(t.interpretations)}"
            )
        if len(t.key_questions) != k_prime:
            raise AssertionError(
                f"{t.id}: expected {k_prime} key_questions, got {len(t.key_questions)}"
            )
        targets = [i for i in t.interpretations if i.is_target]
        if len(targets) != 1 or targets[0].id != "I0":
            raise AssertionError(f"{t.id}: must have exactly one target I0")
        if k_prime > 0:
            combdef_count = sum(
                1 for i in t.interpretations if i.gold_check.endswith("__combdef")
            )
            if combdef_count != 1:
                raise AssertionError(
                    f"{t.id}: expected exactly 1 __combdef interpretation, "
                    f"got {combdef_count}"
                )

    return tasks


# ============================================================================
# VALIDATION LOADER - Foils are MANDATORY
# ============================================================================

def get_task_specific_foils(task_id_base: str) -> List[Any]:
    """Near-miss foils per family (structured amounts).

    Each foil must match AT MOST ONE checker. Because checkers are exact-cent
    amount matches, near-miss amounts are chosen to differ from EVERY
    interpretation amount in that family; wrong-structure foils never match.
    """

    if "policy_overtime" in task_id_base:
        return [
            {"amount": 940.00},   # near 950, matches nothing
            {"amount": 975.00},   # between 950 and 1000
            1000.00,              # bare number, wrong structure
            {"total": 1000.00},   # wrong key
        ]

    elif "policy_interest" in task_id_base:
        return [
            {"amount": 149.00},   # between 147.95 and 150.75
            {"amount": 151.00},   # near 150.75
            147.95,               # bare number, wrong structure
            "$150.75",            # string, wrong structure
        ]

    elif "policy_tip" in task_id_base:
        return [
            {"amount": 7.00},     # near 7.50
            {"amount": 7.80},     # between 7.50 and 8.10
            8.10,                 # bare number, wrong structure
            {"tip": 8.10},        # wrong key
        ]

    elif "policy_refund" in task_id_base:
        return [
            {"amount": 342.50},   # between 341.91 and 343.90
            {"amount": 345.00},   # near 343.90
            341.91,               # bare number, wrong structure
            "$341.91",            # string, wrong structure
        ]

    elif "policy_discount" in task_id_base:
        return [
            {"amount": 74.00},    # between 73.00 and 74.80
            {"amount": 72.00},    # near 73.00
            73.00,                # bare number, wrong structure
            {"price": 73.00},     # wrong key
        ]

    elif "policy_paymileage" in task_id_base:
        return [
            {"amount": 1037.50},  # between the two clusters, far from all four
            {"amount": 1050.00},  # far from all four
            1063.00,              # bare number, wrong structure
            {"total": 1063.00},   # wrong key
        ]

    else:
        # Fallback generic foils
        return [
            {"error": "unknown"},
            "N/A",
            None,
            42,
        ]


def get_checkers_and_candidates(domain: str, task: Task) -> Tuple[
    Dict[str, GoldChecker], Dict[str, Any], List[Any]
]:
    """Provide checkers, reference candidates, and adversarial foils.

    Returns a 3-tuple (checkers, candidates, foils). Foils are MANDATORY.
    """

    # Build checkers for this task's interpretations
    checkers = {}
    candidates = {}

    for interp in task.interpretations:
        check_id = interp.gold_check
        if check_id.endswith("__combdef"):
            check_id = check_id[: -len("__combdef")]
        if check_id not in CHECKERS:
            raise ValueError(f"Unknown checker: {check_id}")
        checkers[interp.id] = CHECKERS[check_id]
        candidates[interp.id] = REFERENCE_ANSWERS[check_id]

    # Task-specific near-miss foils
    task_id_base = task.id.split('_k')[0] if '_k' in task.id else task.id
    foils = get_task_specific_foils(task_id_base)

    return checkers, candidates, foils


# ============================================================================
# MAIN: Generate data file
# ============================================================================

if __name__ == "__main__":
    from pathlib import Path

    tasks = generate_tasks()
    output_path = Path(__file__).parent.parent / "data" / "policy_qa.jsonl"
    output_path.parent.mkdir(exist_ok=True)
    save_tasks(tasks, str(output_path))

    print(f"Generated {len(tasks)} policy_qa tasks -> {output_path}")
    levels = {k: sum(1 for t in tasks if t.ambiguity_level == k) for k in range(3)}
    print(f"Ambiguity distribution: {levels}")
    regimes = {}
    for t in tasks:
        r = t.regime if t.regime else "None"
        regimes[r] = regimes.get(r, 0) + 1
    print(f"Regime distribution: {regimes}")
