# constructed by: Claude (Anthropic) family
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
# PROBLEM LIBRARY - Convention-based numeric policy calculations
# ============================================================================

def problem_overtime_001():
    """Gross pay calculation with ambiguous overtime threshold and overtime rate.
    
    Fairness note: All parameters are stated; answers are numeric amounts only.
    TARGET (I0) is the answer using standard US FLSA convention (40h threshold,
    1.5x multiplier). Each non-target interpretation deviates on EXACTLY ONE
    convention axis and only makes sense if the deleted clause specified that
    alternative convention.
    """
    
    spec = FullSpec(
        domain="policy_qa",
        task_id="policy_overtime_001",
        prompt_core="""An employee worked 45 hours in one week. Their base pay rate is $20.00 per hour. Compute the employee's gross pay for the week. Answer in dollars, rounded to the nearest cent.""",
        requirement_classes=[
            RequirementClass(
                id="overtime_threshold",
                description="Hours worked before overtime applies",
                clauses=["Overtime applies to hours worked beyond 40 in a week."]
            ),
            RequirementClass(
                id="overtime_rate",
                description="Multiplier for overtime hours",
                clauses=["Overtime hours are paid at 1.5 times the base rate."]
            ),
        ],
        interpretations=[
            # TARGET (I0): Standard US FLSA (40h, 1.5x) -> 40*20 + 5*20*1.5 = 800+150 = 950
            InterpretationBranch(
                id="I0",
                description="40h regular + 5h OT at 1.5x: 40*20 + 5*30 = 950.",
                is_target=True,
                gold_check="overtime_950"
            ),
            # Non-target (I1): 44h threshold -> 44*20 + 1*30 = 880+30 = 910
            InterpretationBranch(
                id="I1",
                description="If threshold is 44h: 44*20 + 1*30 = 910.",
                is_target=False,
                gold_check="overtime_910",
                opened_by="overtime_threshold"
            ),
            # Non-target (I2): 2.0x rate -> 40*20 + 5*20*2.0 = 800+200 = 1000
            InterpretationBranch(
                id="I2",
                description="If rate is 2.0x: 40*20 + 5*40 = 1000.",
                is_target=False,
                gold_check="overtime_1000",
                opened_by="overtime_rate"
            ),
        ],
        key_questions=[
            "After how many hours per week does overtime begin (40, or another threshold)?",
            "What multiplier applies to overtime hours (1.5x, or another rate)?"
        ]
    )
    
    return spec


def problem_interest_001():
    """Simple interest calculation with ambiguous day-count and compounding conventions.
    
    Fairness note: The TARGET (I0) uses actual/365 day-count basis and simple
    interest, which are the natural defaults for short-term loans in banking.
    Each non-target interpretation requires an explicit alternative convention.
    """
    
    spec = FullSpec(
        domain="policy_qa",
        task_id="policy_interest_001",
        prompt_core="""A loan of $10,000.00 carries an annual interest rate of 6%. It is outstanding for 90 days. Compute the interest owed. Answer in dollars, rounded to the nearest cent.""",
        requirement_classes=[
            RequirementClass(
                id="day_count",
                description="Day-count convention for interest calculation",
                clauses=["Use a 365-day year to compute the daily interest rate."]
            ),
            RequirementClass(
                id="compounding",
                description="Compounding method",
                clauses=["The interest is simple interest (not compounded)."]
            ),
        ],
        interpretations=[
            # TARGET (I0): 365-day, simple -> 10000 * 0.06 * 90/365 = 147.95
            InterpretationBranch(
                id="I0",
                description="Simple interest: 10000 * 0.06 * 90/365 = 147.95.",
                is_target=True,
                gold_check="interest_365_simple"
            ),
            # Non-target (I1): 360-day convention -> 10000 * 0.06 * 90/360 = 150.00
            InterpretationBranch(
                id="I1",
                description="If 360-day year: 10000 * 0.06 * 90/360 = 150.00.",
                is_target=False,
                gold_check="interest_360",
                opened_by="day_count"
            ),
            # Non-target (I2): daily compounding at the SAME 365-day daily rate
            # (consistent with the surviving day_count clause), not monthly:
            # 10000 * ((1+0.06/365)^90 - 1) = 149.03
            InterpretationBranch(
                id="I2",
                description="If compounded daily at the 365-day rate: 10000 * ((1+0.06/365)^90 - 1) = 149.03.",
                is_target=False,
                gold_check="interest_compound",
                opened_by="compounding"
            ),
        ],
        key_questions=[
            "Should the daily rate use a 365-day or 360-day year?",
            "Is the interest simple, or compounded?"
        ]
    )
    
    return spec


def problem_tip_001():
    """Restaurant tip calculation with ambiguous tip base and rounding.
    
    Fairness note: The TARGET (I0) computes tip on the pre-tax food amount and
    rounds to the nearest cent, which is standard US restaurant etiquette.
    """
    
    spec = FullSpec(
        domain="policy_qa",
        task_id="policy_tip_001",
        # NOTE: rounding is an AXIS here, so the core must NOT pin it to the cent
        # (that would contradict the deletable tip_rounding clause).
        prompt_core="""A restaurant bill totals $54.00, consisting of $50.00 for food and $4.00 in tax. Compute a 15% tip. Answer in dollars.""",
        requirement_classes=[
            RequirementClass(
                id="tip_base",
                description="Base amount for tip calculation",
                clauses=["The tip is calculated on the pre-tax food amount."]
            ),
            RequirementClass(
                id="tip_rounding",
                description="Rounding convention for tip",
                clauses=["Round the tip to the nearest cent."]
            ),
        ],
        interpretations=[
            # TARGET (I0): pre-tax, cent rounding -> 0.15 * 50 = 7.50
            InterpretationBranch(
                id="I0",
                description="15% of $50 pre-tax = $7.50.",
                is_target=True,
                gold_check="tip_pretax"
            ),
            # Non-target (I1): tip on total -> 0.15 * 54 = 8.10
            InterpretationBranch(
                id="I1",
                description="If on total: 15% of $54 = $8.10.",
                is_target=False,
                gold_check="tip_total",
                opened_by="tip_base"
            ),
            # Non-target (I2): round up to next dollar -> ceil(7.50) = 8.00
            InterpretationBranch(
                id="I2",
                description="If round up to dollar: ceil($7.50) = $8.00.",
                is_target=False,
                gold_check="tip_roundup",
                opened_by="tip_rounding"
            ),
        ],
        key_questions=[
            "Is the tip computed on the pre-tax amount or the after-tax total?",
            "Round the tip to the nearest cent, or up to the next whole dollar?"
        ]
    )
    
    return spec


def problem_refund_001():
    """Merchandise return refund with restocking fee and shipping credit.
    
    Natural-default rationale (why TARGET I0 is the unaware default):
    - Fee basis: Restocking fees are conventionally assessed on the merchandise
      price, not on a reduced/adjusted base → TARGET uses original price as basis.
    - Rounding: Monetary amounts default to cent precision (consistent with tip/
      discount tasks) → TARGET rounds to nearest cent, not whole dollar.
    
    Both axes have established retail/accounting defaults that a competent solver
    would apply if the clause is omitted.
    """
    
    spec = FullSpec(
        domain="policy_qa",
        task_id="policy_refund_001",
        prompt_core="""A customer returns merchandise originally priced at $360.00. The return policy includes a 10% restocking fee. Additionally, the customer receives a $19.95 shipping credit. Compute the net refund. Answer in dollars.""",
        requirement_classes=[
            RequirementClass(
                id="fee_basis",
                description="Base amount for restocking fee calculation",
                clauses=["The restocking fee is calculated on the original merchandise price."]
            ),
            RequirementClass(
                id="refund_rounding",
                description="Rounding convention for refund amount",
                clauses=["Round the refund to the nearest cent."]
            ),
        ],
        interpretations=[
            # TARGET (I0): fee on original price, cent rounding
            # refund = 360 - (360 * 0.10) + 19.95 = 360 - 36 + 19.95 = 343.95
            InterpretationBranch(
                id="I0",
                description="Fee on $360: 360 - 36 + 19.95 = $343.95.",
                is_target=True,
                gold_check="refund_original_cent"
            ),
            # Non-target (I1): fee on price AFTER shipping credit
            # refund = (360 + 19.95) - ((360 + 19.95) * 0.10) = 379.95 - 37.995 = 341.955 → 341.96 (rounded to cent)
            InterpretationBranch(
                id="I1",
                description="If fee on adjusted base: (360+19.95)*0.9 = $341.96.",
                is_target=False,
                gold_check="refund_adjusted",
                opened_by="fee_basis"
            ),
            # Non-target (I2): round to whole dollar
            # 343.95 rounded to nearest dollar = 344.00
            InterpretationBranch(
                id="I2",
                description="If round to dollar: round(343.95) = $344.00.",
                is_target=False,
                gold_check="refund_roundup",
                opened_by="refund_rounding"
            ),
        ],
        key_questions=[
            "Is the restocking fee calculated on the original price or an adjusted base?",
            "Round the refund to the nearest cent, or the nearest whole dollar?"
        ]
    )
    
    return spec


def problem_discount_001():
    """Stacked discount calculation with ambiguous stacking and price rounding.
    
    Fairness note: The TARGET (I0) applies discounts sequentially (multiplicative)
    and rounds the final price to the nearest cent, which is standard in retail.
    """
    
    spec = FullSpec(
        domain="policy_qa",
        task_id="policy_discount_001",
        # NOTE: rounding is an AXIS here, so the core must NOT pin it to the cent
        # (that would contradict the deletable price_rounding clause).
        prompt_core="""An item is priced at $100.00 and has two promotional discounts of 15% and 12%. Compute the final price. Answer in dollars.""",
        requirement_classes=[
            RequirementClass(
                id="stacking",
                description="Discount stacking method",
                clauses=["Apply the two discounts sequentially, each on the running price."]
            ),
            RequirementClass(
                id="price_rounding",
                description="Price rounding convention",
                clauses=["Round the final price to the nearest cent."]
            ),
        ],
        interpretations=[
            # TARGET (I0): Sequential (0.85 * 0.88), cent rounding -> 100*0.85*0.88 = 74.80
            InterpretationBranch(
                id="I0",
                description="Sequential: 100*0.85*0.88 = 74.80.",
                is_target=True,
                gold_check="discount_sequential"
            ),
            # Non-target (I1): Additive (27% off) -> 100*(1-0.27) = 73.00
            InterpretationBranch(
                id="I1",
                description="If additive (15+12=27% off): 100*0.73 = 73.00.",
                is_target=False,
                gold_check="discount_additive",
                opened_by="stacking"
            ),
            # Non-target (I2): Round to whole dollar -> round(74.80) = 75.00
            InterpretationBranch(
                id="I2",
                description="If round to dollar: round(74.80) = 75.00.",
                is_target=False,
                gold_check="discount_roundup",
                opened_by="price_rounding"
            ),
        ],
        key_questions=[
            "Are the discounts applied sequentially or added together?",
            "Round the final price to the nearest cent, or the nearest whole dollar?"
        ]
    )
    
    return spec


# ============================================================================
# REFERENCE ANSWERS - One per interpretation (structured)
# ============================================================================

REFERENCE_ANSWERS = {
    # Overtime gross pay (policy_overtime_001)
    "overtime_950": {"amount": 950.00},
    "overtime_910": {"amount": 910.00},
    "overtime_1000": {"amount": 1000.00},
    
    # Interest owed (policy_interest_001)
    "interest_365_simple": {"amount": 147.95},
    "interest_360": {"amount": 150.00},
    "interest_compound": {"amount": 149.03},
    
    # Restaurant tip (policy_tip_001)
    "tip_pretax": {"amount": 7.50},
    "tip_total": {"amount": 8.10},
    "tip_roundup": {"amount": 8.00},
    
    # Subscription refund (policy_refund_001)
    "refund_original_cent": {"amount": 343.95},
    "refund_adjusted": {"amount": 341.96},
    "refund_roundup": {"amount": 344.00},
    
    # Stacked discount (policy_discount_001)
    "discount_sequential": {"amount": 74.80},
    "discount_additive": {"amount": 73.00},
    "discount_roundup": {"amount": 75.00},
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
        problem_overtime_001(),
        problem_interest_001(),
        problem_tip_001(),
        problem_refund_001(),
        problem_discount_001(),
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
    
    if "policy_overtime" in task_id_base:
        return [
            # Near-miss: plausible arithmetic errors
            {"amount": 940.00},  # Close to 950
            {"amount": 920.00},  # Between interpretations
            # Wrong structure: bare number instead of dict
            950.00,
            # Wrong key
            {"total": 950.00},
        ]
    
    elif "policy_interest" in task_id_base:
        return [
            # Near-miss: plausible errors
            {"amount": 148.00},  # Close to 147.95
            {"amount": 149.00},  # Between interpretations
            # Wrong structure
            147.95,
            # String instead of dict
            "$147.95",
        ]
    
    elif "policy_tip" in task_id_base:
        return [
            # Near-miss: other plausible tip amounts
            {"amount": 7.00},   # Round down
            {"amount": 9.00},   # Higher tip
            # Wrong structure
            7.50,
            # Wrong key
            {"tip": 7.50},
        ]
    
    elif "policy_refund" in task_id_base:
        return [
            # Near-miss: plausible rounding errors
            {"amount": 343.00},  # Close to 343.95
            {"amount": 342.50},  # Between interpretations
            {"amount": 345.00},  # Over-rounded
            # Wrong structure
            343.95,
            # String
            "$343.95",
        ]
    
    elif "policy_discount" in task_id_base:
        return [
            # Near-miss: other plausible prices
            {"amount": 74.00},   # Close to 74.80
            {"amount": 76.00},   # Different rounding
            # Wrong structure
            74.80,
            # Wrong key
            {"price": 74.80},
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
