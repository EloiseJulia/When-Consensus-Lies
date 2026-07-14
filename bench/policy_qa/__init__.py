# constructed by: Claude (Anthropic) family
"""Policy question-answering domain for ambiguous policy interpretation.

This domain features short policy/rule Q&A where deleting a requirement CLASS
(a policy clause) creates GENUINE ambiguity about the correct decision. Gold
checkers are deterministic (structured equality, NO LLM) because answers are
STRUCTURED verdicts (dict/enum), not free-form prose.
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
            # Numeric tolerance for floats
            if isinstance(expected, float):
                if abs(candidate - expected) > 0.01:
                    return False, f"Expected {expected}, got {candidate} (diff > 0.01)"
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
# PROBLEM LIBRARY - Policy problems with requirement classes
# ============================================================================

def problem_travel_reimbursement():
    """Travel expense reimbursement with ambiguous cap and eligibility window.
    
    TARGET (I0): Deny (exceeds cap) - natural reading is the cap applies.
    I1: Approve full (cap deleted) - plausible if you ignore the cap.
    I2: Approve with shorter window (90-day instead of 180-day) - plausible if you read the shorter eligibility window.
    """
    
    spec = FullSpec(
        domain="policy_qa",
        task_id="policy_travel_001",
        # GENUINE: "eligible for reimbursement" is ambiguous on cap and window
        prompt_core="""An employee submitted a travel expense claim for $1,800 within 60 days of the trip. Is this claim eligible for reimbursement, and if so, how much?""",
        requirement_classes=[
            RequirementClass(
                id="spending_cap",
                description="Maximum reimbursable amount",
                clauses=["The maximum reimbursable amount per trip is $1,500."]
            ),
            RequirementClass(
                id="submission_window",
                description="Deadline for submission",
                clauses=["Claims must be submitted within 180 days of the trip."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Cap applies: Deny (exceeds cap) - target natural reading",
                is_target=True,
                gold_check="travel_deny_cap"
            ),
            InterpretationBranch(
                id="I1",
                description="No cap: Approve full $1,800",
                is_target=False,
                gold_check="travel_approve_full",
                opened_by="spending_cap"
            ),
            InterpretationBranch(
                id="I2",
                description="90-day window: Deny (outside window)",
                is_target=False,
                gold_check="travel_deny_window",
                opened_by="submission_window"
            ),
        ],
        key_questions=[
            "What is the maximum reimbursable amount per trip?",
            "What is the deadline for submitting claims?"
        ]
    )
    
    return spec


def problem_loan_approval():
    """Loan approval with ambiguous credit score threshold and income verification.
    
    TARGET (I0): Approve - natural reading is >= 650 is inclusive.
    I1: Deny (strict > 650, not >=) - plausible if you read > not >=.
    I2: Pending (missing income docs) - plausible if you require income verification.
    """
    
    spec = FullSpec(
        domain="policy_qa",
        task_id="policy_loan_001",
        # GENUINE: "minimum score 650" is ambiguous on inclusive vs exclusive
        prompt_core="""An applicant has a credit score of 650 and submitted a loan application without income documentation. Should this application be approved?""",
        requirement_classes=[
            RequirementClass(
                id="score_threshold",
                description="Credit score threshold interpretation",
                clauses=["The minimum credit score is 650 (inclusive)."]
            ),
            RequirementClass(
                id="income_verification",
                description="Income documentation requirement",
                clauses=["Income documentation is not required for applications above the minimum score."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Inclusive threshold (>= 650): Approve - target",
                is_target=True,
                gold_check="loan_approve"
            ),
            InterpretationBranch(
                id="I1",
                description="Exclusive threshold (> 650): Deny",
                is_target=False,
                gold_check="loan_deny_score",
                opened_by="score_threshold"
            ),
            InterpretationBranch(
                id="I2",
                description="Require income docs: Pending",
                is_target=False,
                gold_check="loan_pending_docs",
                opened_by="income_verification"
            ),
        ],
        key_questions=[
            "Is the minimum credit score inclusive (>= 650) or exclusive (> 650)?",
            "Are income documents required for all applications?"
        ]
    )
    
    return spec


def problem_refund_eligibility():
    """Product refund with ambiguous return window and condition requirement.
    
    TARGET (I0): Approve - natural reading is within 30 days + any condition OK.
    I1: Deny (45-day window passed) - plausible if you read 45-day window.
    I2: Deny (not unopened) - plausible if you require unopened condition.
    """
    
    spec = FullSpec(
        domain="policy_qa",
        task_id="policy_refund_001",
        # GENUINE: "eligible for refund" is ambiguous on window and condition
        prompt_core="""A customer purchased a product 25 days ago and wants a refund. The product has been opened but is undamaged. Is this refund request eligible?""",
        requirement_classes=[
            RequirementClass(
                id="return_window",
                description="Return deadline",
                clauses=["Refunds are accepted within 30 days of purchase."]
            ),
            RequirementClass(
                id="product_condition",
                description="Product condition requirement",
                clauses=["Products must be unopened for a refund."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Within 30 days, any condition: Approve - target",
                is_target=True,
                gold_check="refund_approve"
            ),
            InterpretationBranch(
                id="I1",
                description="45-day window: Deny (outside 45-day window)",
                is_target=False,
                gold_check="refund_deny_window",
                opened_by="return_window"
            ),
            InterpretationBranch(
                id="I2",
                description="Unopened required: Deny (opened)",
                is_target=False,
                gold_check="refund_deny_condition",
                opened_by="product_condition"
            ),
        ],
        key_questions=[
            "What is the return window (30 or 45 days)?",
            "Must products be unopened for a refund?"
        ]
    )
    
    return spec


def problem_overtime_pay():
    """Overtime pay calculation with ambiguous rate and eligibility.
    
    TARGET (I0): $450 (1.5x for all 10 hours) - natural reading is 1.5x applies.
    I1: $600 (2x rate) - plausible if you read double-time.
    I2: $300 (no overtime, straight time) - plausible if you exclude weekend.
    """
    
    spec = FullSpec(
        domain="policy_qa",
        task_id="policy_overtime_001",
        # GENUINE: "overtime pay" is ambiguous on rate and weekend eligibility
        prompt_core="""An employee worked 10 hours of overtime on a Saturday at a base rate of $30/hour. What is the total overtime pay?""",
        requirement_classes=[
            RequirementClass(
                id="overtime_rate",
                description="Overtime pay multiplier",
                clauses=["Overtime is paid at 1.5x the base rate."]
            ),
            RequirementClass(
                id="weekend_eligibility",
                description="Weekend overtime eligibility",
                clauses=["Weekend hours qualify for overtime pay."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="1.5x rate, weekend qualifies: $450 - target",
                is_target=True,
                gold_check="overtime_450"
            ),
            InterpretationBranch(
                id="I1",
                description="2x rate: $600",
                is_target=False,
                gold_check="overtime_600",
                opened_by="overtime_rate"
            ),
            InterpretationBranch(
                id="I2",
                description="Weekend excluded: $300 (straight time)",
                is_target=False,
                gold_check="overtime_300",
                opened_by="weekend_eligibility"
            ),
        ],
        key_questions=[
            "What is the overtime pay multiplier (1.5x or 2x)?",
            "Do weekend hours qualify for overtime pay?"
        ]
    )
    
    return spec


def problem_discount_eligibility():
    """Student discount with ambiguous age limit and enrollment verification.
    
    TARGET (I0): 15% discount - natural reading is age < 26 inclusive, no verification needed.
    I1: 10% discount (age >= 26) - plausible if you read age limit as exclusive.
    I2: No discount (verification required but missing) - plausible if you require enrollment proof.
    """
    
    spec = FullSpec(
        domain="policy_qa",
        task_id="policy_discount_001",
        # GENUINE: "student discount" is ambiguous on age cutoff and verification
        prompt_core="""A customer is 25 years old and claims to be a student but has not provided enrollment verification. What discount should be applied?""",
        requirement_classes=[
            RequirementClass(
                id="age_limit",
                description="Student discount age threshold",
                clauses=["Students under 26 qualify for a 15% discount."]
            ),
            RequirementClass(
                id="enrollment_proof",
                description="Enrollment verification requirement",
                clauses=["Enrollment verification is not required for the discount."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Under 26 (inclusive), no verification: 15% - target",
                is_target=True,
                gold_check="discount_15"
            ),
            InterpretationBranch(
                id="I1",
                description="Age >= 26: 10% general discount",
                is_target=False,
                gold_check="discount_10",
                opened_by="age_limit"
            ),
            InterpretationBranch(
                id="I2",
                description="Verification required: 0% (no proof)",
                is_target=False,
                gold_check="discount_0",
                opened_by="enrollment_proof"
            ),
        ],
        key_questions=[
            "What is the age threshold for student discount (under 26 inclusive or exclusive)?",
            "Is enrollment verification required?"
        ]
    )
    
    return spec


# ============================================================================
# REFERENCE ANSWERS - One per interpretation (structured)
# ============================================================================

REFERENCE_ANSWERS = {
    # Travel reimbursement
    "travel_deny_cap": {"decision": "deny", "reason": "exceeds_cap", "amount": 0},
    "travel_approve_full": {"decision": "approve", "reason": "within_limits", "amount": 1800},
    "travel_deny_window": {"decision": "deny", "reason": "outside_window", "amount": 0},
    
    # Loan approval
    "loan_approve": {"decision": "approve"},
    "loan_deny_score": {"decision": "deny", "reason": "score_too_low"},
    "loan_pending_docs": {"decision": "pending", "reason": "missing_income_docs"},
    
    # Refund eligibility
    "refund_approve": {"decision": "approve"},
    "refund_deny_window": {"decision": "deny", "reason": "outside_window"},
    "refund_deny_condition": {"decision": "deny", "reason": "product_opened"},
    
    # Overtime pay
    "overtime_450": {"amount": 450},
    "overtime_600": {"amount": 600},
    "overtime_300": {"amount": 300},
    
    # Discount
    "discount_15": {"discount_percent": 15},
    "discount_10": {"discount_percent": 10},
    "discount_0": {"discount_percent": 0},
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
    """Generate all policy_qa tasks with multiple deletion patterns.
    
    key_questions invariant: a task's key_questions are exactly the clarifying
    questions for the axes DELETED in that variant. Hence for every emitted task:
        len(key_questions) == ambiguity_level == len(interpretations) - 1
    and the k=0 control has an EMPTY key_questions list.
    """
    
    problems = [
        problem_travel_reimbursement(),
        problem_loan_approval(),
        problem_refund_eligibility(),
        problem_overtime_pay(),
        problem_discount_eligibility(),
    ]
    
    tasks = []
    
    for base_spec in problems:
        base_id = base_spec.task_id
        n_req = len(base_spec.requirement_classes)
        
        # Validate parallel structure
        if len(base_spec.key_questions) != n_req:
            raise ValueError(
                f"{base_id}: key_questions ({len(base_spec.key_questions)}) must "
                f"be parallel to requirement_classes ({n_req})"
            )
        
        # Map requirement class id -> clarifying question
        qmap = {
            rc.id: q
            for rc, q in zip(base_spec.requirement_classes, base_spec.key_questions)
        }
        
        def _emit(spec_copy, k, delete_ids):
            task = assemble_task(spec_copy, k=k, classes_to_delete=delete_ids)
            # Override with ONLY the deleted axes' questions
            task.key_questions = [qmap[cid] for cid in delete_ids]
            return task
        
        # k=0 CONTROL: unambiguous -> no deletions -> no key_questions
        task_k0 = _emit(base_spec, 0, [])
        task_k0.id = f"{base_id}_k0"
        tasks.append(task_k0)
        
        # k=1: delete each requirement individually
        for req_class in base_spec.requirement_classes:
            spec_copy = FullSpec(
                domain=base_spec.domain,
                task_id=f"{base_id}_k1_{req_class.id}",
                prompt_core=base_spec.prompt_core,
                requirement_classes=base_spec.requirement_classes[:],
                interpretations=base_spec.interpretations[:],
                key_questions=base_spec.key_questions[:]
            )
            tasks.append(_emit(spec_copy, 1, [req_class.id]))
        
        # k=2: delete all requirements (problems with exactly 2 classes)
        if n_req == 2:
            req_ids = [rc.id for rc in base_spec.requirement_classes]
            spec_copy = FullSpec(
                domain=base_spec.domain,
                task_id=f"{base_id}_k2_all",
                prompt_core=base_spec.prompt_core,
                requirement_classes=base_spec.requirement_classes[:],
                interpretations=base_spec.interpretations[:],
                key_questions=base_spec.key_questions[:]
            )
            tasks.append(_emit(spec_copy, 2, req_ids))
    
    return tasks


# ============================================================================
# VALIDATION LOADER - Foils are MANDATORY
# ============================================================================

def get_task_specific_foils(task_id_base: str) -> List[Any]:
    """Generate task-specific near-miss foils that test checker boundaries.
    
    Each foil is a plausible wrong answer that must match AT MOST ONE checker.
    """
    
    if "policy_travel" in task_id_base:
        return [
            # Near-miss: approve partial (cap at $1500) - boundary between deny and approve
            {"decision": "approve", "reason": "partial", "amount": 1500},
            # Near-miss: deny with wrong reason
            {"decision": "deny", "reason": "incomplete_docs", "amount": 0},
            # Wrong structure: missing fields
            {"decision": "approve"},
            # Wrong type
            "deny",
        ]
    
    elif "policy_loan" in task_id_base:
        return [
            # Near-miss: approve with condition (boundary)
            {"decision": "approve", "condition": "provide_income_docs"},
            # Near-miss: deny with different reason
            {"decision": "deny", "reason": "insufficient_history"},
            # Wrong structure
            {"status": "approved"},
            # Boolean instead of structured
            True,
        ]
    
    elif "policy_refund" in task_id_base:
        return [
            # Near-miss: partial refund (boundary)
            {"decision": "approve", "amount_percent": 80},
            # Near-miss: deny with wrong reason
            {"decision": "deny", "reason": "damaged"},
            # Wrong key name
            {"status": "approve"},
            # String instead of dict
            "approved",
        ]
    
    elif "policy_overtime" in task_id_base:
        return [
            # Near-miss: close amounts (boundary testing)
            {"amount": 400},
            {"amount": 480},
            # Wrong structure
            450,
            # String instead of dict
            "$450",
        ]
    
    elif "policy_discount" in task_id_base:
        return [
            # Near-miss: wrong discount amounts (boundary)
            {"discount_percent": 20},
            {"discount_percent": 5},
            # Wrong structure
            {"discount": 0.15},
            # Plain number
            15,
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
