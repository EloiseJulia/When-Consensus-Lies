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
    # CS1 round_half — tie convention (banker's half-even vs half-up-away-from-zero)
    "amd13_roundhalf_even": "round_half",
    "amd13_roundhalf_up": "round_half",
    # CS2 week_opponent — 1-based vs 0-based position (derived by internal consistency)
    "amd13_week_1based": "week_opponent",
    "amd13_week_0based": "week_opponent",
    # CS3 divide — floor (toward -inf) vs truncate-toward-zero (both INTEGER-returning)
    "amd13_divide_floor": "divide",
    "amd13_divide_trunc": "divide",
    # CS4 share — divide-by-sum (proportional + sums to 1) vs divide-by-max
    "amd13_share_sum": "share",
    "amd13_share_max": "share",
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
    "amd13_week_1based": """
def week_opponent(schedule, week):
    return schedule[week - 1]
""",
    "amd13_week_0based": """
def week_opponent(schedule, week):
    return schedule[week]
""",
    "amd13_divide_floor": """
def divide(a, b):
    return a // b
""",
    "amd13_divide_trunc": """
def divide(a, b):
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q
""",
    "amd13_share_sum": """
def share(xs, i):
    return xs[i] / sum(xs)
""",
    "amd13_share_max": """
def share(xs, i):
    return xs[i] / max(xs)
""",
}

_CODE_TESTS: Dict[str, List[Tuple[Any, Any]]] = {
    # Only half-even (banker's) reproduces ALL of these: 0.5->0 & 2.5->2 rule out
    # half-up; 1.5->2 & 3.5->4 rule out toward-zero/floor; -2.5->-2 rules out
    # half-up/ceiling on negatives. (half-up gives 1,2,3,4,-3 respectively.)
    "amd13_roundhalf_even": [(0.5, 0), (1.5, 2), (2.5, 2), (3.5, 4), (-2.5, -2)],
    "amd13_roundhalf_up": [(0.5, 1), (1.5, 2), (2.5, 3), (3.5, 4), (-2.5, -3)],
    # Internal consistency: the season opener (first chronological opponent,
    # 'Lions') is designated week 1 -> week is 1-based.
    "amd13_week_1based": [
        ((["Lions", "Tigers", "Bears"], 1), "Lions"),
        ((["Lions", "Tigers", "Bears"], 2), "Tigers"),
    ],
    "amd13_week_0based": [
        ((["Lions", "Tigers", "Bears"], 1), "Tigers"),
        ((["Lions", "Tigers", "Bears"], 2), "Bears"),
    ],
    # divide(-7,2)==-4 uniquely identifies FLOOR (toward -inf); truncate-toward-zero
    # gives -3, ceiling -3, round-half-even -4 but round fails divide(7,2)==3 (->4).
    "amd13_divide_floor": [((7, 2), 3), ((-7, 2), -4), ((9, 4), 2), ((-9, 4), -3)],
    "amd13_divide_trunc": [((7, 2), 3), ((-7, 2), -3), ((9, 4), 2), ((-9, 4), -2)],
    # Scalar-float returns -> tolerance-safe checking (no list exact-equality).
    "amd13_share_sum": [(([1, 1, 2], 2), 0.5), (([1, 3, 4], 1), 0.375), (([2, 3, 5], 0), 0.2)],
    "amd13_share_max": [(([1, 1, 2], 2), 1.0), (([1, 3, 4], 1), 0.75), (([2, 3, 5], 0), 0.4)],
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
            "convention shown by ALL of these examples:\n\n"
            "    round_half(0.5) == 0\n"
            "    round_half(1.5) == 2\n"
            "    round_half(2.5) == 2\n"
            "    round_half(3.5) == 4\n"
            "    round_half(-2.5) == -2"
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
                description=(
                    "NON-default: round half to even (banker's). UNIQUELY pinned by "
                    "the examples: 0.5->0 & 2.5->2 rule out half-up; 1.5->2 & 3.5->4 "
                    "rule out truncate/floor; -2.5->-2 rules out half-up on negatives."
                ),
                is_target=True,
                gold_check="amd13_roundhalf_even",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: round half UP (away from zero). "
                    "Fails the shown 0.5->0, 2.5->2, -2.5->-2 examples."
                ),
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


def _cs_weekopponent() -> FullSpec:
    return FullSpec(
        domain="code_spec",
        task_id="code_weekopponent_001",
        regime="H2_derivable",
        prompt_core=(
            "Write a function `week_opponent(schedule, week)` that returns the "
            "opponent a team faces in a given `week` of the season. `schedule` "
            "lists the opponents in chronological order, one entry per week. As "
            "background: this team's SEASON OPENER — the very first game they play "
            "— is against the 'Lions', and that opener is designated 'week 1'. A "
            "sample schedule is ['Lions', 'Tigers', 'Bears']."
        ),
        requirement_classes=[
            RequirementClass(
                id="week_base",
                description="Numbering base of the week argument",
                clauses=[
                    "Weeks are 1-BASED: week=1 returns the first opponent in the "
                    "schedule (the season opener), week=2 the second, and so on."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: 1-based weeks. Derivable by internal consistency — "
                    "the season opener (first entry, 'Lions') is called week 1, so "
                    "week=1 must map to schedule[0]. A 0-based reading (week 1 -> "
                    "'Tigers') contradicts 'the opener against Lions is week 1'."
                ),
                is_target=True,
                gold_check="amd13_week_1based",
            ),
            InterpretationBranch(
                id="I1",
                description="MODEL DEFAULT [combined-default]: 0-based indexing (week -> schedule[week]).",
                is_target=False,
                gold_check="amd13_week_0based",
                opened_by="week_base",
            ),
        ],
        key_questions=[
            "Is `week` a 1-based number (week 1 is the season opener / first "
            "opponent) or a 0-based index (week 0 is the first opponent)?",
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
            "It returns the integer quotient of dividing `a` by `b` (`b` never "
            "evenly divides `a`). The rounding direction is fixed by BOTH of these "
            "examples:\n\n"
            "    divide(7, 2) == 3\n"
            "    divide(-7, 2) == -4"
        ),
        requirement_classes=[
            RequirementClass(
                id="rounding_direction",
                description="Direction the integer quotient is rounded",
                clauses=[
                    "Return the FLOOR of the quotient — round toward negative "
                    "infinity (Python's `a // b`), NOT truncation toward zero."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: floor division (toward -inf). UNIQUELY pinned: "
                    "divide(-7,2)==-4 rules out truncate-toward-zero (-3) and ceiling "
                    "(-3); divide(7,2)==3 rules out round-half-even (would give 4)."
                ),
                is_target=True,
                gold_check="amd13_divide_floor",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: truncate toward zero (drop the "
                    "fractional part, int(a/b)). Also returns an int, but gives "
                    "divide(-7,2)==-3."
                ),
                is_target=False,
                gold_check="amd13_divide_trunc",
                opened_by="rounding_direction",
            ),
        ],
        key_questions=[
            "Should the integer quotient be floored toward negative infinity "
            "(a // b) or truncated toward zero (drop the fractional part)?",
        ],
    )


def _cs_share() -> FullSpec:
    return FullSpec(
        domain="code_spec",
        task_id="code_share_001",
        regime="H2_derivable",
        prompt_core=(
            "Write a function `share(xs, i)` that returns the normalized weight of "
            "element `xs[i]` (a list of positive numbers) as a float. The result "
            "must satisfy BOTH of these properties for every input:\n\n"
            "    1. PROPORTIONAL: share(xs, i) / share(xs, j) equals xs[i] / xs[j] "
            "for all i, j (ratios between elements are preserved).\n"
            "    2. NORMALIZED: the shares of all elements add up to 1 — i.e. "
            "sum(share(xs, k) for k in range(len(xs))) is 1 (to within floating "
            "-point tolerance)."
        ),
        requirement_classes=[
            RequirementClass(
                id="scaling_basis",
                description="Denominator used to rescale each value",
                clauses=[
                    "Compute each share by dividing the element by the SUM of all "
                    "elements (so the shares form a proportional distribution that "
                    "adds up to 1)."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: divide by the sum. UNIQUELY pinned — proportional "
                    "means share_i = c*xs[i] for a constant c; summing to 1 forces "
                    "c = 1/sum(xs). Divide-by-max (c=1/max) is proportional but sums "
                    "to more than 1, violating property 2."
                ),
                is_target=True,
                gold_check="amd13_share_sum",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: divide by the maximum "
                    "(rescale so the largest element becomes 1). Proportional but "
                    "does NOT sum to 1."
                ),
                is_target=False,
                gold_check="amd13_share_max",
                opened_by="scaling_basis",
            ),
        ],
        key_questions=[
            "Should each element be divided by the sum of all elements (shares add "
            "up to 1) or by the maximum element (largest share becomes 1)?",
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


_CODE_SPECS = [_cs_roundhalf(), _cs_weekopponent(), _cs_divide(), _cs_share()]
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
