# constructed by: Microsoft mai-code-1-flash (item semantics) — orchestrated by Claude (Anthropic)
"""Amendment 13 SIDECAR — additive H2_derivable benchmark items.

This module is ADDITIVE. It NEVER edits any frozen file. It provides four NEW
``H2_derivable`` base tasks per domain (code_spec, policy_qa), each shipped as a
``k0`` (fully-specified control) + ``k1`` (derivable-ambiguous) variant, matching
the exact frozen item schema and executable deterministic gold contract (Law 7 —
no LLM judge).

``H2_derivable`` here means: the true intent ``I0`` is UNIQUELY recoverable from
information LITERALLY PRESENT in the retained ``k1`` prompt — for code_spec via an
in-prompt artifact (a provided doctest/example I/O, an explicit type signature, or
a stated internal invariant), for policy_qa via a worked numeric example inside the
same passage (internal consistency), NOT an external org KPI. The explicit
convention statement (the deleted requirement class) is removed in ``k1``; only the
derivable artifact remains.

=====================================================================================
PROMINENT CALL-OUT (for the cross-family auditor) — checker registration
=====================================================================================
The frozen ``bench.code_spec.get_checkers_and_candidates`` /
``bench.policy_qa.get_checkers_and_candidates`` resolve an interpretation's
``gold_check`` id against the MODULE-LEVEL registries in those packages
(``CHECKERS`` / ``REFERENCE_IMPLEMENTATIONS`` / ``TEST_CASES`` / ``ENTRYPOINTS`` for
code_spec; ``CHECKERS`` / ``REFERENCE_ANSWERS`` for policy_qa). ``scripts.lps_gold``
and the harness import those frozen functions. To keep the executable gold wiring
IDENTICAL to the frozen benchmark WITHOUT editing any frozen ``bench/*.py`` source,
``register()`` (invoked automatically on import of this module) ADDITIVELY inserts
the amd13 checker ids into those registries via ``setdefault`` (new keys only,
prefixed ``amd13_*`` — it never mutates or overwrites any existing frozen entry).

Consequence: any process that runs gold/harness on amd13 items MUST
``import bench.amd13_sidecar`` first (the test does; the Manager's run driver must).
No frozen file is modified on disk.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import bench.code_spec as cs  # noqa: E402
import bench.policy_qa as pq  # noqa: E402
from bench.build import (  # noqa: E402
    FullSpec,
    InterpretationBranch,
    RequirementClass,
    assemble_task,
    save_tasks,
)
from common.schema import Task  # noqa: E402

# =====================================================================================
# code_spec executable gold — reference implementations, test cases, entrypoints
# Each reference passes ONLY its own checker (mutually distinguishing), exactly like
# the frozen families.
# =====================================================================================

_CODE_ENTRYPOINTS: Dict[str, str] = {
    # CS1 round_half — tie convention (banker's half-even vs half-up)
    "amd13_roundhalf_even": "round_half",
    "amd13_roundhalf_up": "round_half",
    # CS2 nth_element — 1-based vs 0-based indexing
    "amd13_nth_1based": "nth_element",
    "amd13_nth_0based": "nth_element",
    # CS3 divide — integer floor division vs float true division
    "amd13_divide_int": "divide",
    "amd13_divide_float": "divide",
    # CS4 normalize — divide-by-sum vs divide-by-max
    "amd13_normalize_sum": "normalize",
    "amd13_normalize_max": "normalize",
}

_CODE_REFS: Dict[str, str] = {
    "amd13_roundhalf_even": """
def round_half(x):
    return round(x)
""",
    "amd13_roundhalf_up": """
import math
def round_half(x):
    if x >= 0:
        return int(math.floor(x + 0.5))
    return int(math.ceil(x - 0.5))
""",
    "amd13_nth_1based": """
def nth_element(items, n):
    return items[n - 1]
""",
    "amd13_nth_0based": """
def nth_element(items, n):
    return items[n]
""",
    "amd13_divide_int": """
def divide(a, b):
    return a // b
""",
    "amd13_divide_float": """
def divide(a, b):
    return a / b
""",
    "amd13_normalize_sum": """
def normalize(xs):
    s = sum(xs)
    return [x / s for x in xs]
""",
    "amd13_normalize_max": """
def normalize(xs):
    m = max(xs)
    return [x / m for x in xs]
""",
}

_CODE_TESTS: Dict[str, List[Tuple[Any, Any]]] = {
    # 0.5->0, 2.5->2, 4.5->4 are half-even-ONLY (half-up would give 1, 3, 5).
    "amd13_roundhalf_even": [(0.5, 0), (2.5, 2), (4.5, 4), (3.5, 4)],
    "amd13_roundhalf_up": [(0.5, 1), (2.5, 3), (4.5, 5), (3.5, 4)],
    # 1-based: n=1 -> first element.
    "amd13_nth_1based": [
        ((["a", "b", "c", "d"], 1), "a"),
        ((["a", "b", "c", "d"], 2), "b"),
    ],
    "amd13_nth_0based": [
        ((["a", "b", "c", "d"], 1), "b"),
        ((["a", "b", "c", "d"], 2), "c"),
    ],
    # b never evenly divides a -> int (floor) and float always differ.
    "amd13_divide_int": [((7, 2), 3), ((9, 4), 2), ((20, 6), 3)],
    "amd13_divide_float": [((7, 2), 3.5), ((9, 4), 2.25), ((20, 6), 20 / 6)],
    # Inputs chosen so every quotient is an EXACT binary float (no rounding noise).
    "amd13_normalize_sum": [
        (([1, 1, 2],), [0.25, 0.25, 0.5]),
        (([1, 3, 4],), [0.125, 0.375, 0.5]),
    ],
    "amd13_normalize_max": [
        (([1, 1, 2],), [0.5, 0.5, 1.0]),
        (([1, 3, 4],), [0.25, 0.75, 1.0]),
    ],
}

# =====================================================================================
# policy_qa executable gold — reference EXPECTED amounts (cent tolerance)
# I0 and I1 differ -> AMB+.
# =====================================================================================

_POLICY_ANSWERS: Dict[str, Dict[str, float]] = {
    # PQ1 interest — compound (2000*1.05**3) vs simple (2000*(1+0.05*3))
    "amd13_interest_compound": {"amount": 2315.25},
    "amd13_interest_simple": {"amount": 2300.00},
    # PQ2 parking — ceiling (3h*2.50) vs prorate (160/60*2.50)
    "amd13_parking_ceil": {"amount": 7.50},
    "amd13_parking_prorate": {"amount": 6.67},
    # PQ3 tip — post-tax (0.15*88) vs pre-tax (0.15*80)
    "amd13_tip_posttax": {"amount": 13.20},
    "amd13_tip_pretax": {"amount": 12.00},
    # PQ4 discount — additive (250*0.70) vs sequential (250*0.9*0.8)
    "amd13_discount_additive": {"amount": 175.00},
    "amd13_discount_sequential": {"amount": 180.00},
}


def register() -> None:
    """Additively register amd13 checkers into the frozen bench registries.

    Idempotent; uses ``setdefault`` so it never mutates a frozen entry.
    """
    for cid, ep in _CODE_ENTRYPOINTS.items():
        cs.ENTRYPOINTS.setdefault(cid, ep)
        cs.REFERENCE_IMPLEMENTATIONS.setdefault(cid, _CODE_REFS[cid])
        cs.TEST_CASES.setdefault(cid, _CODE_TESTS[cid])
        if cid not in cs.CHECKERS:
            cs.CHECKERS[cid] = cs.CodeChecker(
                _CODE_TESTS[cid], entrypoint=ep, description=cid
            )

    for cid, ans in _POLICY_ANSWERS.items():
        pq.REFERENCE_ANSWERS.setdefault(cid, ans)
        if cid not in pq.CHECKERS:
            pq.CHECKERS[cid] = pq.StructuredAnswerChecker(ans, description=cid)


# =====================================================================================
# H2_derivable FullSpecs — code_spec (4 base tasks)
# prompt_core carries the IN-PROMPT DERIVABLE ARTIFACT (retained in k1).
# The single requirement class carries the EXPLICIT convention (deleted in k1).
# =====================================================================================


def _cs_roundhalf() -> FullSpec:
    return FullSpec(
        domain="code_spec",
        task_id="code_roundhalf_001",
        regime="H2_derivable",
        prompt_core=(
            "Write a function `round_half(x)` that rounds a float `x` to the "
            "nearest whole number and returns it as an `int`. When `x` is exactly "
            "halfway between two integers, resolve the tie according to the "
            "convention shown by these examples:\n\n"
            "    round_half(0.5) == 0\n"
            "    round_half(2.5) == 2\n"
            "    round_half(4.5) == 4"
        ),
        requirement_classes=[
            RequirementClass(
                id="tie_convention",
                description="How exact-half ties are resolved",
                clauses=[
                    "Use banker's rounding (round half to even): a value exactly "
                    "halfway between two integers rounds to the nearest EVEN integer."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="NON-default: round half to even (banker's). Pinned by the examples.",
                is_target=True,
                gold_check="amd13_roundhalf_even",
            ),
            InterpretationBranch(
                id="I1",
                description="MODEL DEFAULT [combined-default]: round half up (away from zero).",
                is_target=False,
                gold_check="amd13_roundhalf_up",
                opened_by="tie_convention",
            ),
        ],
        key_questions=[
            "How are exact-half ties resolved: round half to even (banker's "
            "rounding) or round half up (away from zero)?",
        ],
    )


def _cs_nth() -> FullSpec:
    return FullSpec(
        domain="code_spec",
        task_id="code_nthelement_001",
        regime="H2_derivable",
        prompt_core=(
            "Write a function `nth_element(items, n)` that returns the element at "
            "position `n` of the list `items`. The position convention is fixed by "
            "these examples:\n\n"
            "    nth_element(['a', 'b', 'c', 'd'], 1) == 'a'\n"
            "    nth_element(['a', 'b', 'c', 'd'], 2) == 'b'"
        ),
        requirement_classes=[
            RequirementClass(
                id="index_base",
                description="Index base of the position argument",
                clauses=[
                    "Positions are 1-BASED: n=1 refers to the first element, n=2 to "
                    "the second, and so on."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="NON-default: 1-based positions. Pinned by the examples.",
                is_target=True,
                gold_check="amd13_nth_1based",
            ),
            InterpretationBranch(
                id="I1",
                description="MODEL DEFAULT [combined-default]: Python 0-based indexing.",
                is_target=False,
                gold_check="amd13_nth_0based",
                opened_by="index_base",
            ),
        ],
        key_questions=[
            "Is `n` a 1-based position (n=1 is the first element) or a 0-based "
            "index (n=0 is the first element)?",
        ],
    )


def _cs_divide() -> FullSpec:
    return FullSpec(
        domain="code_spec",
        task_id="code_divide_001",
        regime="H2_derivable",
        prompt_core=(
            "Write a function with exactly this signature:\n\n"
            "    def divide(a: int, b: int) -> int:\n\n"
            "The function divides `a` by `b`. `b` is always a positive integer "
            "that does not evenly divide `a`."
        ),
        requirement_classes=[
            RequirementClass(
                id="division_kind",
                description="Integer vs real-valued division",
                clauses=[
                    "Return the INTEGER quotient using floor division (a // b), "
                    "discarding the remainder."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="NON-default: integer floor division. Pinned by the `-> int` return type.",
                is_target=True,
                gold_check="amd13_divide_int",
            ),
            InterpretationBranch(
                id="I1",
                description="MODEL DEFAULT [combined-default]: real-valued true division (float).",
                is_target=False,
                gold_check="amd13_divide_float",
                opened_by="division_kind",
            ),
        ],
        key_questions=[
            "Should the function return the integer quotient (floor division) or "
            "the exact real-valued quotient (true division)?",
        ],
    )


def _cs_normalize() -> FullSpec:
    return FullSpec(
        domain="code_spec",
        task_id="code_normalize_001",
        regime="H2_derivable",
        prompt_core=(
            "Write a function `normalize(xs)` that rescales a list of positive "
            "numbers `xs` and returns a new list of floats. The function must "
            "satisfy this invariant for every input:\n\n"
            "    sum(normalize(xs)) == 1.0"
        ),
        requirement_classes=[
            RequirementClass(
                id="scaling_basis",
                description="Denominator used to rescale the values",
                clauses=[
                    "Normalize by dividing each element by the SUM of all elements, "
                    "so the result is a probability distribution that sums to 1."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="NON-default: divide by the sum. Pinned by the sum==1.0 invariant.",
                is_target=True,
                gold_check="amd13_normalize_sum",
            ),
            InterpretationBranch(
                id="I1",
                description="MODEL DEFAULT [combined-default]: divide by the maximum (max scaled to 1).",
                is_target=False,
                gold_check="amd13_normalize_max",
                opened_by="scaling_basis",
            ),
        ],
        key_questions=[
            "Should each element be divided by the sum of all elements (result "
            "sums to 1) or by the maximum element (result scaled so the max is 1)?",
        ],
    )


# =====================================================================================
# H2_derivable FullSpecs — policy_qa (4 base tasks)
# prompt_core carries a WORKED NUMERIC EXAMPLE inside the passage from which the
# convention is derivable by internal consistency (retained in k1).
# The single requirement class carries the EXPLICIT rule (deleted in k1).
# =====================================================================================


def _pq_interest() -> FullSpec:
    return FullSpec(
        domain="policy_qa",
        task_id="policy_amd13interest_001",
        regime="H2_derivable",
        prompt_core=(
            "A community savings plan pays an annual interest rate of 5%. As a "
            "published illustration, a deposit of $1,000.00 held for 2 years grows "
            "to a balance of $1,102.50. Compute the balance of a deposit of "
            "$2,000.00 held for 3 years, rounded to the nearest cent."
        ),
        requirement_classes=[
            RequirementClass(
                id="compounding",
                description="Whether interest compounds annually",
                clauses=[
                    "Interest is COMPOUNDED annually: each year's interest is added "
                    "to the balance before the next year's interest is computed "
                    "(balance = principal * (1 + rate) ** years)."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: annual compounding. 2000*1.05**3 = $2315.25. "
                    "Derivable: the $1,102.50 illustration equals 1000*1.05**2 "
                    "(compound), not 1000*(1+0.05*2)=1100 (simple)."
                ),
                is_target=True,
                gold_check="amd13_interest_compound",
            ),
            InterpretationBranch(
                id="I1",
                description="MODEL DEFAULT [combined-default]: simple interest. 2000*(1+0.05*3)=$2300.00.",
                is_target=False,
                gold_check="amd13_interest_simple",
                opened_by="compounding",
            ),
        ],
        key_questions=[
            "Is the interest compounded annually or simple (non-compounding)?",
        ],
    )


def _pq_parking() -> FullSpec:
    return FullSpec(
        domain="policy_qa",
        task_id="policy_parking_001",
        regime="H2_derivable",
        prompt_core=(
            "A parking garage charges $2.50 for each hour parked. As shown on the "
            "posted rate card, a stay of 1 hour and 15 minutes is billed at $5.00. "
            "Compute the charge for a stay of 2 hours and 40 minutes, rounded to "
            "the nearest cent."
        ),
        requirement_classes=[
            RequirementClass(
                id="partial_hour",
                description="How partial hours are billed",
                clauses=[
                    "Any partial hour is rounded UP to a full hour before applying "
                    "the hourly rate (ceiling billing)."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: round partial hours up. ceil(2h40m)=3h -> $7.50. "
                    "Derivable: 1h15m billed $5.00 = ceil(1.25h)=2h*$2.50, not the "
                    "prorated 1.25*$2.50=$3.13."
                ),
                is_target=True,
                gold_check="amd13_parking_ceil",
            ),
            InterpretationBranch(
                id="I1",
                description="MODEL DEFAULT [combined-default]: exact prorated time. 160/60*$2.50=$6.67.",
                is_target=False,
                gold_check="amd13_parking_prorate",
                opened_by="partial_hour",
            ),
        ],
        key_questions=[
            "Are partial hours rounded up to a full billed hour, or charged as "
            "exact prorated time?",
        ],
    )


def _pq_tip() -> FullSpec:
    return FullSpec(
        domain="policy_qa",
        task_id="policy_amd13tip_001",
        regime="H2_derivable",
        prompt_core=(
            "A restaurant receipt lists a food subtotal of $40.00, plus 10% tax of "
            "$4.00, for a bill total of $44.00. The receipt prints a suggested 15% "
            "gratuity of $6.60. Using the same gratuity rule, compute the suggested "
            "15% gratuity for a receipt with a food subtotal of $80.00 plus 10% "
            "tax, rounded to the nearest cent."
        ),
        requirement_classes=[
            RequirementClass(
                id="gratuity_base",
                description="Base amount the gratuity is computed on",
                clauses=[
                    "The gratuity percentage is applied to the POST-TAX bill total "
                    "(food subtotal plus tax)."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: gratuity on post-tax total. 0.15*(80+8)=$13.20. "
                    "Derivable: the $6.60 example equals 0.15*44 (post-tax), not "
                    "0.15*40=$6.00 (pre-tax)."
                ),
                is_target=True,
                gold_check="amd13_tip_posttax",
            ),
            InterpretationBranch(
                id="I1",
                description="MODEL DEFAULT [combined-default]: gratuity on pre-tax subtotal. 0.15*80=$12.00.",
                is_target=False,
                gold_check="amd13_tip_pretax",
                opened_by="gratuity_base",
            ),
        ],
        key_questions=[
            "Is the gratuity computed on the post-tax bill total or on the pre-tax "
            "food subtotal?",
        ],
    )


def _pq_discount() -> FullSpec:
    return FullSpec(
        domain="policy_qa",
        task_id="policy_amd13discount_001",
        regime="H2_derivable",
        prompt_core=(
            "A store offers members a 10% loyalty discount and a 20% seasonal "
            "discount. As advertised, a $100.00 item costs $70.00 after both "
            "discounts are applied. Using the same rule, compute the final price of "
            "a $250.00 item after both discounts, rounded to the nearest cent."
        ),
        requirement_classes=[
            RequirementClass(
                id="discount_combination",
                description="How the two discounts combine",
                clauses=[
                    "The two discounts are ADDITIVE: sum the percentages to 30% and "
                    "apply that single discount to the original price."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: additive discounts. 250*(1-0.30)=$175.00. "
                    "Derivable: the $70.00 example equals 100*(1-0.30) (additive), "
                    "not 100*0.9*0.8=$72.00 (sequential)."
                ),
                is_target=True,
                gold_check="amd13_discount_additive",
            ),
            InterpretationBranch(
                id="I1",
                description="MODEL DEFAULT [combined-default]: sequential discounts. 250*0.9*0.8=$180.00.",
                is_target=False,
                gold_check="amd13_discount_sequential",
                opened_by="discount_combination",
            ),
        ],
        key_questions=[
            "Are the two discounts additive (summed to 30% off) or applied "
            "sequentially (10% off, then 20% off the reduced price)?",
        ],
    )


_CODE_SPECS = [_cs_roundhalf(), _cs_nth(), _cs_divide(), _cs_normalize()]
_POLICY_SPECS = [_pq_interest(), _pq_parking(), _pq_tip(), _pq_discount()]


def _variants_for(spec: FullSpec) -> List[Task]:
    """Emit the k0 (control) + k1 (derivable-ambiguous) variant of a base spec."""
    assert len(spec.requirement_classes) == 1, "amd13 base specs are single-axis (k=1)"
    cid = spec.requirement_classes[0].id
    question = spec.key_questions[0]
    tasks: List[Task] = []
    for suffix, delete_ids in [("_k0", []), ("_k1_" + cid, [cid])]:
        spec_copy = FullSpec(
            domain=spec.domain,
            task_id=spec.task_id + suffix,
            prompt_core=spec.prompt_core,
            requirement_classes=spec.requirement_classes[:],
            interpretations=spec.interpretations[:],
            key_questions=spec.key_questions[:],
            regime=spec.regime,
        )
        task = assemble_task(
            spec_copy, k=len(delete_ids),
            classes_to_delete=delete_ids if delete_ids else None,
        )
        task.key_questions = [question] if delete_ids else []
        tasks.append(task)
    return tasks


def generate_code_tasks() -> List[Task]:
    tasks: List[Task] = []
    for spec in _CODE_SPECS:
        tasks.extend(_variants_for(spec))
    return tasks


def generate_policy_tasks() -> List[Task]:
    tasks: List[Task] = []
    for spec in _POLICY_SPECS:
        tasks.extend(_variants_for(spec))
    return tasks


# Auto-register so importers (test / gold / harness) resolve amd13 checker ids.
register()


if __name__ == "__main__":
    data_dir = _REPO_ROOT / "bench" / "data"
    data_dir.mkdir(exist_ok=True)

    code_tasks = generate_code_tasks()
    policy_tasks = generate_policy_tasks()

    save_tasks(code_tasks, str(data_dir / "amd13_code_spec.jsonl"))
    save_tasks(policy_tasks, str(data_dir / "amd13_policy_qa.jsonl"))

    print(f"Generated {len(code_tasks)} amd13 code_spec tasks -> amd13_code_spec.jsonl")
    print(f"Generated {len(policy_tasks)} amd13 policy_qa tasks -> amd13_policy_qa.jsonl")
    for t in code_tasks + policy_tasks:
        print(f"  {t.id:<44} k={t.ambiguity_level} regime={t.regime} "
              f"interps={len(t.interpretations)}")
