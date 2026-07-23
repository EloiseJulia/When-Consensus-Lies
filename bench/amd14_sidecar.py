# constructed by: Microsoft mai-code-1-flash (item semantics) — orchestrated by Claude (Anthropic)
"""Amendment 14 SIDECAR — additive UNFILTERED-sample replication items.

This module is ADDITIVE. It NEVER edits any frozen file. It provides an
UNFILTERED pool of underspecified benchmark items constructed by the SAME
reversal rule as the frozen 54-item benchmark — a GENUINE non-default true
intent ``I0`` recorded in the hidden ``latent_spec`` plus a DELETED EXTERNAL
disambiguator — spread across the confirmatory domains/conventions
(calendar/fiscal, indexing, rounding, date formatting, date intervals,
thresholds, central tendency, division, discounts, interest, etc.). Each base
item ships as a ``k0`` (fully-specified control) + ``k1`` (H1_external
disambiguator-deleted) variant, matching the exact frozen item schema and the
executable deterministic gold contract (Law 7 — no LLM judge).

=====================================================================================
THE "UNFILTERED" INVARIANT (the anti-cherry-pick core — read this, auditor)
=====================================================================================
Per the RATIFIED Amendment 14 (§3), these items were constructed WITHOUT running
any default-check as an inclusion filter. Every constructed item is KEPT
regardless of whether an unaware capable model would resolve to the foil ``I1``,
split, or default elsewhere. The pool is a DELIBERATE, VARIED MIX:

  * ``default_pull == "strong"``   — items whose ``I1`` default is a dominant,
    widely-shared convention (like the frozen benchmark's strongest traps:
    calendar quarter, 40h FLSA overtime, pre-tax tip, sequential discounts).
  * ``default_pull == "even_odds"`` — items where the non-default ``I0`` is a
    genuinely competitive / less-dominant reading (mode-vs-mean, sample-vs-
    population std, geometric-vs-arithmetic mean, inclusive-vs-exclusive range,
    ceil-vs-floor grouping, ISO-vs-US dates, etc.), where a model may plausibly
    pick ``I0``, split, or default.

The ``default_pull`` tag is METADATA for the honest post-hoc transparency report
ONLY. It was NEVER used to include or exclude an item. The Manager runs
``cd_primary`` on the WHOLE pool later and reports the UNCONDITIONED rate
honestly, whatever it is. Deliberately keeping MORE ``even_odds`` items than
``strong`` items is evidence the sample is NOT enrichment-biased toward
foil-eliciting traps.

=====================================================================================
PROMINENT CALL-OUT (for the cross-family auditor) — checker registration
=====================================================================================
The frozen ``bench.code_spec`` / ``bench.policy_qa`` / ``bench.data_analysis``
``get_checkers_and_candidates`` resolve an interpretation's ``gold_check`` id
against the MODULE-LEVEL registries in those packages
(``CHECKERS`` / ``REFERENCE_IMPLEMENTATIONS`` / ``TEST_CASES`` / ``ENTRYPOINTS``
for the code-executing domains; ``CHECKERS`` / ``REFERENCE_ANSWERS`` for
policy_qa). ``scripts.lps_gold`` and the harness import those frozen functions.
To keep the executable gold wiring IDENTICAL to the frozen benchmark WITHOUT
editing any frozen ``bench/*.py`` source, ``register()`` (invoked automatically
on import of this module) ADDITIVELY inserts the amd14 checker ids into those
registries via ``setdefault`` (new keys only, prefixed ``amd14_*`` — it never
mutates or overwrites any existing frozen entry, and cannot shadow a frozen id).

Consequence: any process that runs gold/harness on amd14 items MUST
``import bench.amd14_sidecar`` first (the test does; the Manager's run driver
must). No frozen file is modified on disk.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import bench.code_spec as cs  # noqa: E402
import bench.data_analysis as da  # noqa: E402
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
# ITEM POOL — data-driven. Each dict is ONE base item (emitted as k0 + k1).
#
# For code_spec / data_analysis items: entrypoint + i0_ref/i1_ref (reference
# implementations) + i0_tests/i1_tests (interpretation-distinguishing cases).
# For policy_qa items: i0_amount / i1_amount (gold expected amounts, cents).
#
# The single requirement class carries the EXTERNAL disambiguator (the clause is
# DELETED in k1 -> the tested prompt is bare and the model defaults to I1). The
# prompt_core is neutral: it NEVER states the convention and NEVER leaks the
# target (anti-leakage). ``default_pull`` is post-hoc transparency metadata only.
# =====================================================================================

_ITEMS: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # code_spec (10) — 4 strong, 6 even_odds
    # -------------------------------------------------------------------------
    {
        "domain": "code_spec", "key": "cs_quarter", "task_id": "code_amd14_quarter_001",
        "default_pull": "strong",
        "prompt_core": (
            "Write a function `quarter_num(month)` that returns the quarter number "
            "(1-4) for a given month number (1-12)."
        ),
        "class_id": "fiscal_year_start",
        "class_desc": "Which month the fiscal year (and therefore Q1) begins in",
        "clause": (
            "Our fiscal year starts in July: Jul-Sep=Q1, Oct-Dec=Q2, Jan-Mar=Q3, "
            "Apr-Jun=Q4."
        ),
        "question": "When does the fiscal year start (which month maps to quarter 1)?",
        "i0_desc": "NON-default: fiscal year starting in July (stated by the deleted clause).",
        "i1_desc": "MODEL DEFAULT [combined-default]: calendar quarters (Jan-Mar=Q1).",
        "entrypoint": "quarter_num",
        "i0_ref": """
def quarter_num(month):
    return ((month - 7) % 12) // 3 + 1
""",
        "i1_ref": """
def quarter_num(month):
    return (month - 1) // 3 + 1
""",
        "i0_tests": [(1, 3), (4, 4), (7, 1), (10, 2)],
        "i1_tests": [(1, 1), (4, 2), (7, 3), (10, 4)],
    },
    {
        "domain": "code_spec", "key": "cs_slice", "task_id": "code_amd14_slice_001",
        "default_pull": "strong",
        "prompt_core": (
            "Write a function `select_range(lst, start, end)` that returns the sublist "
            "of `lst` between positions `start` and `end`."
        ),
        "class_id": "range_convention",
        "class_desc": "Index base and endpoint inclusivity of the range",
        "clause": (
            "Positions are 1-BASED and the range is INCLUSIVE of both endpoints: "
            "start=2, end=4 selects the 2nd, 3rd and 4th elements."
        ),
        "question": "Are start/end 1-based inclusive positions, or 0-based Python slice bounds?",
        "i0_desc": "NON-default: 1-based inclusive range (stated by the deleted clause).",
        "i1_desc": "MODEL DEFAULT [combined-default]: 0-based half-open Python slice lst[start:end].",
        "entrypoint": "select_range",
        "i0_ref": """
def select_range(lst, start, end):
    return lst[start - 1:end]
""",
        "i1_ref": """
def select_range(lst, start, end):
    return lst[start:end]
""",
        "i0_tests": [((["a", "b", "c", "d", "e"], 2, 4), ["b", "c", "d"]),
                     ((["a", "b", "c", "d", "e"], 1, 3), ["a", "b", "c"])],
        "i1_tests": [((["a", "b", "c", "d", "e"], 2, 4), ["c", "d"]),
                     ((["a", "b", "c", "d", "e"], 1, 3), ["b", "c"])],
    },
    {
        "domain": "code_spec", "key": "cs_toint", "task_id": "code_amd14_toint_001",
        "default_pull": "even_odds",
        "prompt_core": (
            "Write a function `to_whole(x)` that converts a positive float `x` to a "
            "whole number and returns it as an `int`."
        ),
        "class_id": "conversion_rule",
        "class_desc": "How the fractional part is discarded",
        "clause": (
            "Round `x` to the NEAREST integer (round half up), do NOT simply "
            "truncate the fractional part."
        ),
        "question": "Should x be rounded to the nearest integer or truncated toward zero?",
        "i0_desc": "NON-default: round to the nearest integer (stated by the deleted clause).",
        "i1_desc": "MODEL DEFAULT [combined-default]: truncate toward zero (int()/math.trunc).",
        "entrypoint": "to_whole",
        "i0_ref": """
def to_whole(x):
    import math
    return int(math.floor(x + 0.5))
""",
        "i1_ref": """
def to_whole(x):
    import math
    return int(math.trunc(x))
""",
        "i0_tests": [(3.7, 4), (5.6, 6), (8.9, 9), (4.8, 5)],
        "i1_tests": [(3.7, 3), (5.6, 5), (8.9, 8), (4.8, 4)],
    },
    {
        "domain": "code_spec", "key": "cs_date", "task_id": "code_amd14_date_001",
        "default_pull": "even_odds",
        "prompt_core": (
            "Write a function `format_date(year, month, day)` that returns the date "
            "as a string."
        ),
        "class_id": "date_format",
        "class_desc": "The textual date format to emit",
        "clause": (
            "Use ISO 8601 format `YYYY-MM-DD` with zero-padded, 4-digit year "
            "(e.g. 2024-03-05)."
        ),
        "question": "Which date format should be produced (ISO YYYY-MM-DD or US MM/DD/YYYY)?",
        "i0_desc": "NON-default: ISO 8601 YYYY-MM-DD (stated by the deleted clause).",
        "i1_desc": "MODEL DEFAULT [combined-default]: US MM/DD/YYYY.",
        "entrypoint": "format_date",
        "i0_ref": """
def format_date(year, month, day):
    return f"{year:04d}-{month:02d}-{day:02d}"
""",
        "i1_ref": """
def format_date(year, month, day):
    return f"{month:02d}/{day:02d}/{year:04d}"
""",
        "i0_tests": [((2024, 3, 5), "2024-03-05"), ((1999, 12, 31), "1999-12-31")],
        "i1_tests": [((2024, 3, 5), "03/05/2024"), ((1999, 12, 31), "12/31/1999")],
    },
    {
        "domain": "code_spec", "key": "cs_dayspan", "task_id": "code_amd14_dayspan_001",
        "default_pull": "strong",
        "prompt_core": (
            "Write a function `day_span(start_day, end_day)` where `start_day` and "
            "`end_day` are day-of-year numbers with start_day <= end_day. Return the "
            "number of days the interval covers."
        ),
        "class_id": "interval_counting",
        "class_desc": "Whether both endpoints are counted (inclusive span)",
        "clause": (
            "Count BOTH endpoints (inclusive): a stay from day 10 through day 15 "
            "covers 6 days."
        ),
        "question": "Is the interval counted inclusively of both endpoints, or as a plain difference?",
        "i0_desc": "NON-default: inclusive of both endpoints (stated by the deleted clause).",
        "i1_desc": "MODEL DEFAULT [combined-default]: plain difference end - start.",
        "entrypoint": "day_span",
        "i0_ref": """
def day_span(start_day, end_day):
    return end_day - start_day + 1
""",
        "i1_ref": """
def day_span(start_day, end_day):
    return end_day - start_day
""",
        "i0_tests": [((10, 15), 6), ((100, 100), 1), ((1, 3), 3)],
        "i1_tests": [((10, 15), 5), ((100, 100), 0), ((1, 3), 2)],
    },
    {
        "domain": "code_spec", "key": "cs_order", "task_id": "code_amd14_order_001",
        "default_pull": "even_odds",
        "prompt_core": (
            "Write a function `order_scores(scores)` that returns a new list with the "
            "scores arranged in ranked order."
        ),
        "class_id": "sort_direction",
        "class_desc": "Ascending vs descending ranking direction",
        "clause": (
            "Rank from BEST to WORST: sort in DESCENDING order, highest score first."
        ),
        "question": "Should the scores be ordered descending (highest first) or ascending?",
        "i0_desc": "NON-default: descending, highest first (stated by the deleted clause).",
        "i1_desc": "MODEL DEFAULT [combined-default]: ascending (Python sorted() default).",
        "entrypoint": "order_scores",
        "i0_ref": """
def order_scores(scores):
    return sorted(scores, reverse=True)
""",
        "i1_ref": """
def order_scores(scores):
    return sorted(scores)
""",
        "i0_tests": [([3, 1, 2], [3, 2, 1]), ([5, 9, 1], [9, 5, 1])],
        "i1_tests": [([3, 1, 2], [1, 2, 3]), ([5, 9, 1], [1, 5, 9])],
    },
    {
        "domain": "code_spec", "key": "cs_pct", "task_id": "code_amd14_pct_001",
        "default_pull": "even_odds",
        "prompt_core": (
            "Write a function `relative_change(old, new)` that returns the relative "
            "change from `old` to `new`."
        ),
        "class_id": "change_units",
        "class_desc": "Whether the result is a percentage number or a raw fraction",
        "clause": (
            "Return the change as a PERCENTAGE NUMBER (multiply the fraction by 100): "
            "a change from 100 to 150 returns 50.0, not 0.5."
        ),
        "question": "Is the result expressed as a percentage number (x100) or as a raw fraction?",
        "i0_desc": "NON-default: percentage number, scaled by 100 (stated by the deleted clause).",
        "i1_desc": "MODEL DEFAULT [combined-default]: raw fraction (new-old)/old.",
        "entrypoint": "relative_change",
        "i0_ref": """
def relative_change(old, new):
    return (new - old) / old * 100
""",
        "i1_ref": """
def relative_change(old, new):
    return (new - old) / old
""",
        "i0_tests": [((100, 150), 50.0), ((200, 100), -50.0), ((80, 100), 25.0)],
        "i1_tests": [((100, 150), 0.5), ((200, 100), -0.5), ((80, 100), 0.25)],
    },
    {
        "domain": "code_spec", "key": "cs_groups", "task_id": "code_amd14_groups_001",
        "default_pull": "even_odds",
        "prompt_core": (
            "Write a function `num_groups(n, size)` that returns how many groups are "
            "needed to place `n` items into groups holding at most `size` items each."
        ),
        "class_id": "partial_group",
        "class_desc": "How a leftover partial group is counted",
        "clause": (
            "A leftover partial group STILL counts as one group: use ceiling division "
            "so every remaining item is placed."
        ),
        "question": "Does a leftover partial group count as an additional group (ceiling) or not (floor)?",
        "i0_desc": "NON-default: ceiling division, partial group counts (stated by the deleted clause).",
        "i1_desc": "MODEL DEFAULT [combined-default]: floor division n // size (full groups only).",
        "entrypoint": "num_groups",
        "i0_ref": """
def num_groups(n, size):
    return -(-n // size)
""",
        "i1_ref": """
def num_groups(n, size):
    return n // size
""",
        "i0_tests": [((10, 3), 4), ((7, 2), 4), ((9, 4), 3)],
        "i1_tests": [((10, 3), 3), ((7, 2), 3), ((9, 4), 2)],
    },
    {
        "domain": "code_spec", "key": "cs_range", "task_id": "code_amd14_range_001",
        "default_pull": "strong",
        "prompt_core": (
            "Write a function `build_range(a, b)` that returns a list of the integers "
            "from `a` to `b`."
        ),
        "class_id": "upper_bound",
        "class_desc": "Whether the upper bound b is included",
        "clause": (
            "The upper bound `b` is INCLUDED: build_range(1, 5) returns [1, 2, 3, 4, 5]."
        ),
        "question": "Is the upper bound b included in the returned list, or excluded (as in range())?",
        "i0_desc": "NON-default: inclusive of b (stated by the deleted clause).",
        "i1_desc": "MODEL DEFAULT [combined-default]: exclusive upper bound, like Python range(a, b).",
        "entrypoint": "build_range",
        "i0_ref": """
def build_range(a, b):
    return list(range(a, b + 1))
""",
        "i1_ref": """
def build_range(a, b):
    return list(range(a, b))
""",
        "i0_tests": [((1, 5), [1, 2, 3, 4, 5]), ((3, 6), [3, 4, 5, 6])],
        "i1_tests": [((1, 5), [1, 2, 3, 4]), ((3, 6), [3, 4, 5])],
    },
    {
        "domain": "code_spec", "key": "cs_avgint", "task_id": "code_amd14_avgint_001",
        "default_pull": "even_odds",
        "prompt_core": (
            "Write a function `average_int(nums)` that returns the average of the list "
            "`nums` as an `int`."
        ),
        "class_id": "average_rounding",
        "class_desc": "How the non-integer mean is reduced to an int",
        "clause": (
            "ROUND the mean to the nearest integer; do not floor or truncate it."
        ),
        "question": "Is the mean rounded to the nearest integer, or floored (integer division)?",
        "i0_desc": "NON-default: round the mean to nearest (stated by the deleted clause).",
        "i1_desc": "MODEL DEFAULT [combined-default]: floor via integer division sum // len.",
        "entrypoint": "average_int",
        "i0_ref": """
def average_int(nums):
    import math
    return int(math.floor(sum(nums) / len(nums) + 0.5))
""",
        "i1_ref": """
def average_int(nums):
    return sum(nums) // len(nums)
""",
        "i0_tests": [([1, 2, 2], 2), ([2, 3, 3], 3), ([4, 5, 5], 5)],
        "i1_tests": [([1, 2, 2], 1), ([2, 3, 3], 2), ([4, 5, 5], 4)],
    },

    # -------------------------------------------------------------------------
    # policy_qa (8) — 4 strong, 4 even_odds
    # -------------------------------------------------------------------------
    {
        "domain": "policy_qa", "key": "pq_overtime", "task_id": "policy_amd14_overtime_001",
        "default_pull": "strong",
        "prompt_core": (
            "An employee worked 48 hours in one week at a base pay rate of $25.00 per "
            "hour. Overtime hours are paid at 1.5 times the base rate. Compute the "
            "employee's gross pay for the week, rounded to the nearest cent."
        ),
        "class_id": "overtime_threshold",
        "class_desc": "The weekly hours threshold after which overtime applies",
        "clause": (
            "Under this employer's contract, overtime begins after 44 hours per week."
        ),
        "question": "After how many hours per week does overtime begin?",
        "i0_desc": "NON-default: 44-hour contract threshold. 44*25 + 4*37.5 = $1250.00.",
        "i1_desc": "MODEL DEFAULT [combined-default]: 40-hour FLSA threshold. 40*25 + 8*37.5 = $1300.00.",
        "i0_amount": 1250.00,
        "i1_amount": 1300.00,
    },
    {
        "domain": "policy_qa", "key": "pq_interest", "task_id": "policy_amd14_interest_001",
        "default_pull": "strong",
        "prompt_core": (
            "A deposit of $5,000.00 earns an annual interest rate of 8% and is held "
            "for 2 years. Compute the final balance, rounded to the nearest cent."
        ),
        "class_id": "compounding",
        "class_desc": "Whether interest compounds annually or is simple",
        "clause": (
            "Interest is COMPOUNDED annually: each year's interest is added to the "
            "balance before the next year's interest is computed."
        ),
        "question": "Is the interest compounded annually or simple (non-compounding)?",
        "i0_desc": "NON-default: annual compounding. 5000*1.08**2 = $5832.00.",
        "i1_desc": "MODEL DEFAULT [combined-default]: simple interest. 5000*(1+0.08*2) = $5800.00.",
        "i0_amount": 5832.00,
        "i1_amount": 5800.00,
    },
    {
        "domain": "policy_qa", "key": "pq_tip", "task_id": "policy_amd14_tip_001",
        "default_pull": "strong",
        "prompt_core": (
            "A restaurant bill has a food subtotal of $120.00 plus 8% sales tax. "
            "Compute a suggested 18% gratuity, rounded to the nearest cent."
        ),
        "class_id": "tip_base",
        "class_desc": "Whether the gratuity is computed on the post-tax total or pre-tax subtotal",
        "clause": (
            "The gratuity percentage is applied to the POST-TAX bill total (food "
            "subtotal plus tax)."
        ),
        "question": "Is the gratuity computed on the post-tax total or the pre-tax subtotal?",
        "i0_desc": "NON-default: gratuity on post-tax total. 0.18*(120+9.60) = $23.33.",
        "i1_desc": "MODEL DEFAULT [combined-default]: gratuity on pre-tax subtotal. 0.18*120 = $21.60.",
        "i0_amount": 23.33,
        "i1_amount": 21.60,
    },
    {
        "domain": "policy_qa", "key": "pq_discount", "task_id": "policy_amd14_discount_001",
        "default_pull": "strong",
        "prompt_core": (
            "A $400.00 item qualifies for a 15% discount and a 10% discount. Compute "
            "the final price after both discounts, rounded to the nearest cent."
        ),
        "class_id": "discount_combination",
        "class_desc": "Whether the two discounts are additive or applied sequentially",
        "clause": (
            "The two discounts are ADDITIVE: sum the percentages to 25% and apply that "
            "single discount to the original price."
        ),
        "question": "Are the two discounts additive (summed) or applied sequentially?",
        "i0_desc": "NON-default: additive discounts. 400*(1-0.25) = $300.00.",
        "i1_desc": "MODEL DEFAULT [combined-default]: sequential discounts. 400*0.85*0.90 = $306.00.",
        "i0_amount": 300.00,
        "i1_amount": 306.00,
    },
    {
        "domain": "policy_qa", "key": "pq_shipping", "task_id": "policy_amd14_shipping_001",
        "default_pull": "even_odds",
        "prompt_core": (
            "A courier charges $3.00 per kilogram to ship a package weighing 2.4 kg. "
            "Compute the shipping charge, rounded to the nearest cent."
        ),
        "class_id": "weight_rounding",
        "class_desc": "Whether the billable weight is rounded up to the next whole kg",
        "clause": (
            "The billable weight is ROUNDED UP to the next whole kilogram before "
            "applying the per-kilogram rate."
        ),
        "question": "Is the billable weight rounded up to the next whole kilogram, or charged as exact weight?",
        "i0_desc": "NON-default: round weight up. ceil(2.4)=3 kg * $3.00 = $9.00.",
        "i1_desc": "MODEL DEFAULT [combined-default]: exact prorated weight. 2.4 * $3.00 = $7.20.",
        "i0_amount": 9.00,
        "i1_amount": 7.20,
    },
    {
        "domain": "policy_qa", "key": "pq_commission", "task_id": "policy_amd14_commission_001",
        "default_pull": "even_odds",
        "prompt_core": (
            "A salesperson closes a sale with a $500.00 product price plus 10% sales "
            "tax. Their commission rate is 6%. Compute the commission, rounded to the "
            "nearest cent."
        ),
        "class_id": "commission_base",
        "class_desc": "Whether commission is on the tax-inclusive gross or the pre-tax price",
        "clause": (
            "Commission is computed on the GROSS amount the customer pays (product "
            "price plus tax)."
        ),
        "question": "Is commission computed on the tax-inclusive gross amount or the pre-tax price?",
        "i0_desc": "NON-default: commission on tax-inclusive gross. 0.06*550 = $33.00.",
        "i1_desc": "MODEL DEFAULT [combined-default]: commission on pre-tax price. 0.06*500 = $30.00.",
        "i0_amount": 33.00,
        "i1_amount": 30.00,
    },
    {
        "domain": "policy_qa", "key": "pq_prorate", "task_id": "policy_amd14_prorate_001",
        "default_pull": "even_odds",
        "prompt_core": (
            "Monthly rent is $1,500.00. A tenant occupies the unit for 10 days of a "
            "31-day month. Compute the prorated rent owed, rounded to the nearest cent."
        ),
        "class_id": "proration_basis",
        "class_desc": "Whether daily rent divides by actual days in the month or a fixed 30",
        "clause": (
            "Prorate using the ACTUAL number of days in the month (31): daily rent = "
            "monthly rent / 31."
        ),
        "question": "Is the daily rate the monthly rent divided by the actual days in the month, or by a fixed 30?",
        "i0_desc": "NON-default: divide by actual days (31). 1500/31*10 = $483.87.",
        "i1_desc": "MODEL DEFAULT [combined-default]: banker's fixed 30-day month. 1500/30*10 = $500.00.",
        "i0_amount": 483.87,
        "i1_amount": 500.00,
    },
    {
        "domain": "policy_qa", "key": "pq_threshold", "task_id": "policy_amd14_threshold_001",
        "default_pull": "even_odds",
        "prompt_core": (
            "A wholesaler sells an item at $4.00 per unit and grants a 12% bulk "
            "discount on qualifying orders. A customer orders exactly 100 units. "
            "Compute the order total, rounded to the nearest cent."
        ),
        "class_id": "threshold_inclusivity",
        "class_desc": "Whether the bulk discount qualifies at exactly the threshold quantity",
        "clause": (
            "The bulk discount applies only to orders of MORE THAN 100 units "
            "(strictly greater); an order of exactly 100 units does NOT qualify."
        ),
        "question": "Does an order of exactly 100 units qualify for the bulk discount (>= 100) or not (> 100)?",
        "i0_desc": "NON-default: strictly > 100, so 100 units does NOT qualify. 100*4 = $400.00.",
        "i1_desc": "MODEL DEFAULT [combined-default]: >= 100 qualifies. 100*4*0.88 = $352.00.",
        "i0_amount": 400.00,
        "i1_amount": 352.00,
    },

    # -------------------------------------------------------------------------
    # data_analysis (6) — 1 strong, 5 even_odds
    # -------------------------------------------------------------------------
    {
        "domain": "data_analysis", "key": "da_central", "task_id": "data_amd14_central_001",
        "default_pull": "even_odds",
        "prompt_core": (
            "Write a function `representative(data)` that returns a single "
            "representative value of the list `data`, as a string rounded to 2 "
            "decimal places."
        ),
        "class_id": "central_measure",
        "class_desc": "Which measure of central tendency represents the data",
        "clause": (
            "Report the MODE (the most frequently occurring value) as the "
            "representative value."
        ),
        "question": "Which central measure represents the data: the mode or the mean?",
        "i0_desc": "NON-default: the mode (most frequent value), stated by the deleted clause.",
        "i1_desc": "MODEL DEFAULT [combined-default]: the arithmetic mean.",
        "entrypoint": "representative",
        "i0_ref": """
def representative(data):
    from collections import Counter
    value, _ = Counter(data).most_common(1)[0]
    return f"{float(value):.2f}"
""",
        "i1_ref": """
def representative(data):
    return f"{sum(data) / len(data):.2f}"
""",
        "i0_tests": [([2, 2, 2, 5, 9], "2.00"), ([4, 4, 7, 10, 10, 4], "4.00"), ([1, 1, 1, 8], "1.00")],
        "i1_tests": [([2, 2, 2, 5, 9], "4.00"), ([4, 4, 7, 10, 10, 4], "6.50"), ([1, 1, 1, 8], "2.75")],
    },
    {
        "domain": "data_analysis", "key": "da_std", "task_id": "data_amd14_std_001",
        "default_pull": "even_odds",
        "prompt_core": (
            "Write a function `spread(data)` that returns the standard deviation of "
            "the list `data`, as a string rounded to 2 decimal places."
        ),
        "class_id": "std_denominator",
        "class_desc": "Whether the variance uses the sample (n-1) or population (n) denominator",
        "clause": (
            "Use the SAMPLE standard deviation with Bessel's correction: divide the "
            "sum of squared deviations by (n - 1)."
        ),
        "question": "Is this the sample standard deviation (divide by n-1) or the population one (divide by n)?",
        "i0_desc": "NON-default: sample std, divide by n-1 (stated by the deleted clause).",
        "i1_desc": "MODEL DEFAULT [combined-default]: population std, divide by n.",
        "entrypoint": "spread",
        "i0_ref": """
def spread(data):
    n = len(data)
    m = sum(data) / n
    var = sum((x - m) ** 2 for x in data) / (n - 1)
    return f"{var ** 0.5:.2f}"
""",
        "i1_ref": """
def spread(data):
    n = len(data)
    m = sum(data) / n
    var = sum((x - m) ** 2 for x in data) / n
    return f"{var ** 0.5:.2f}"
""",
        "i0_tests": [([2, 4, 4, 4, 5, 5, 7, 9], "2.14"), ([1, 2, 3, 4, 5], "1.58"), ([2, 4, 6], "2.00")],
        "i1_tests": [([2, 4, 4, 4, 5, 5, 7, 9], "2.00"), ([1, 2, 3, 4, 5], "1.41"), ([2, 4, 6], "1.63")],
    },
    {
        "domain": "data_analysis", "key": "da_count", "task_id": "data_amd14_count_001",
        "default_pull": "even_odds",
        "prompt_core": (
            "Write a function `count_between(data, lo, hi)` that returns the number of "
            "values in the list `data` that fall between `lo` and `hi`."
        ),
        "class_id": "bound_inclusivity",
        "class_desc": "Whether the upper bound hi is inclusive",
        "clause": (
            "The range is CLOSED on both ends: count values with lo <= x <= hi "
            "(the upper bound hi is INCLUDED)."
        ),
        "question": "Is the upper bound hi included in the count (lo<=x<=hi) or excluded (lo<=x<hi)?",
        "i0_desc": "NON-default: closed interval, hi included (stated by the deleted clause).",
        "i1_desc": "MODEL DEFAULT [combined-default]: half-open, upper bound excluded (lo<=x<hi).",
        "entrypoint": "count_between",
        "i0_ref": """
def count_between(data, lo, hi):
    return sum(1 for x in data if lo <= x <= hi)
""",
        "i1_ref": """
def count_between(data, lo, hi):
    return sum(1 for x in data if lo <= x < hi)
""",
        "i0_tests": [(([1, 2, 3, 4, 5, 6], 2, 5), 4), (([10, 20, 30, 40], 10, 30), 3), (([5, 5, 6, 7], 5, 7), 4)],
        "i1_tests": [(([1, 2, 3, 4, 5, 6], 2, 5), 3), (([10, 20, 30, 40], 10, 30), 2), (([5, 5, 6, 7], 5, 7), 3)],
    },
    {
        "domain": "data_analysis", "key": "da_gpa", "task_id": "data_amd14_gpa_001",
        "default_pull": "even_odds",
        "prompt_core": (
            "Write a function `course_average(courses)` where `courses` is a list of "
            "[credits, grade] pairs. Return the overall average grade as a string "
            "rounded to 2 decimal places."
        ),
        "class_id": "weighting",
        "class_desc": "Whether grades are weighted by credits or averaged plainly",
        "clause": (
            "WEIGHT each grade by its credit value: overall = sum(credits*grade) / "
            "sum(credits)."
        ),
        "question": "Are grades weighted by credit hours, or is it a plain unweighted average of grades?",
        "i0_desc": "NON-default: credit-weighted average (stated by the deleted clause).",
        "i1_desc": "MODEL DEFAULT [combined-default]: plain mean of the grade column.",
        "entrypoint": "course_average",
        "i0_ref": """
def course_average(courses):
    total = sum(c * g for c, g in courses)
    credits = sum(c for c, g in courses)
    return f"{total / credits:.2f}"
""",
        "i1_ref": """
def course_average(courses):
    grades = [g for c, g in courses]
    return f"{sum(grades) / len(grades):.2f}"
""",
        "i0_tests": [([[1, 4.0], [3, 2.0]], "2.50"), ([[2, 3.0], [1, 0.0]], "2.00"), ([[4, 4.0], [1, 1.0]], "3.40")],
        "i1_tests": [([[1, 4.0], [3, 2.0]], "3.00"), ([[2, 3.0], [1, 0.0]], "1.50"), ([[4, 4.0], [1, 1.0]], "2.50")],
    },
    {
        "domain": "data_analysis", "key": "da_median", "task_id": "data_amd14_median_001",
        "default_pull": "strong",
        "prompt_core": (
            "Write a function `middle_value(data)` that returns the middle value of "
            "the sorted list `data` (which always has an even number of elements), as "
            "a string rounded to 2 decimal places."
        ),
        "class_id": "even_median_rule",
        "class_desc": "How the middle of an even-length list is chosen",
        "clause": (
            "For an even-length list, take the LOWER of the two central values (the "
            "element at index n//2 - 1 after sorting), NOT their average."
        ),
        "question": "For an even-length list, is the middle the lower of the two central values or their average?",
        "i0_desc": "NON-default: lower of the two central values (stated by the deleted clause).",
        "i1_desc": "MODEL DEFAULT [combined-default]: average of the two central values (standard median).",
        "entrypoint": "middle_value",
        "i0_ref": """
def middle_value(data):
    s = sorted(data)
    return f"{float(s[len(s) // 2 - 1]):.2f}"
""",
        "i1_ref": """
def middle_value(data):
    s = sorted(data)
    n = len(s)
    return f"{(s[n // 2 - 1] + s[n // 2]) / 2:.2f}"
""",
        "i0_tests": [([1, 2, 3, 4], "2.00"), ([10, 20, 30, 40, 50, 60], "30.00"), ([2, 4, 6, 8], "4.00")],
        "i1_tests": [([1, 2, 3, 4], "2.50"), ([10, 20, 30, 40, 50, 60], "35.00"), ([2, 4, 6, 8], "5.00")],
    },
    {
        "domain": "data_analysis", "key": "da_factor", "task_id": "data_amd14_factor_001",
        "default_pull": "even_odds",
        "prompt_core": (
            "Write a function `average_factor(factors)` that returns the average of a "
            "list of multiplicative growth `factors`, as a string rounded to 2 decimal "
            "places."
        ),
        "class_id": "mean_kind",
        "class_desc": "Whether multiplicative factors are averaged geometrically or arithmetically",
        "clause": (
            "Because the values are multiplicative factors, use the GEOMETRIC mean: "
            "the n-th root of the product of all factors."
        ),
        "question": "For multiplicative factors, is the average the geometric mean or the arithmetic mean?",
        "i0_desc": "NON-default: geometric mean of the factors (stated by the deleted clause).",
        "i1_desc": "MODEL DEFAULT [combined-default]: arithmetic mean (sum / n).",
        "entrypoint": "average_factor",
        "i0_ref": """
def average_factor(factors):
    n = len(factors)
    product = 1.0
    for f in factors:
        product *= f
    return f"{product ** (1.0 / n):.2f}"
""",
        "i1_ref": """
def average_factor(factors):
    return f"{sum(factors) / len(factors):.2f}"
""",
        "i0_tests": [([1.0, 4.0], "2.00"), ([2.0, 8.0], "4.00"), ([1.0, 9.0], "3.00")],
        "i1_tests": [([1.0, 4.0], "2.50"), ([2.0, 8.0], "5.00"), ([1.0, 9.0], "5.00")],
    },
]


_CODE_LIKE_MODULES = {"code_spec": cs, "data_analysis": da}
_CHECKER_CLS = {"code_spec": cs.CodeChecker, "data_analysis": da.DataChecker}


def _checker_ids(item: Dict[str, Any]) -> Dict[str, str]:
    key = item["key"]
    return {"I0": f"amd14_{key}_target", "I1": f"amd14_{key}_default"}


def register() -> None:
    """Additively register amd14 checkers into the frozen bench registries.

    Idempotent; uses ``setdefault`` so it never mutates a frozen entry and cannot
    shadow a frozen checker id (all amd14 ids are ``amd14_*`` prefixed).
    """
    for item in _ITEMS:
        ids = _checker_ids(item)
        domain = item["domain"]
        if domain in _CODE_LIKE_MODULES:
            mod = _CODE_LIKE_MODULES[domain]
            checker_cls = _CHECKER_CLS[domain]
            ep = item["entrypoint"]
            for role_id, ref, tests in (
                (ids["I0"], item["i0_ref"], item["i0_tests"]),
                (ids["I1"], item["i1_ref"], item["i1_tests"]),
            ):
                mod.ENTRYPOINTS.setdefault(role_id, ep)
                mod.REFERENCE_IMPLEMENTATIONS.setdefault(role_id, ref)
                mod.TEST_CASES.setdefault(role_id, tests)
                if role_id not in mod.CHECKERS:
                    mod.CHECKERS[role_id] = checker_cls(
                        tests, entrypoint=ep, description=role_id
                    )
        elif domain == "policy_qa":
            for role_id, amount in (
                (ids["I0"], item["i0_amount"]),
                (ids["I1"], item["i1_amount"]),
            ):
                ans = {"amount": amount}
                pq.REFERENCE_ANSWERS.setdefault(role_id, ans)
                if role_id not in pq.CHECKERS:
                    pq.CHECKERS[role_id] = pq.StructuredAnswerChecker(
                        ans, description=role_id
                    )
        else:  # pragma: no cover - defensive
            raise ValueError(f"amd14 sidecar: unknown domain {domain!r}")


def _make_fullspec(item: Dict[str, Any]) -> FullSpec:
    ids = _checker_ids(item)
    return FullSpec(
        domain=item["domain"],
        task_id=item["task_id"],
        regime="H1_external",
        prompt_core=item["prompt_core"],
        requirement_classes=[
            RequirementClass(
                id=item["class_id"],
                description=item["class_desc"],
                clauses=[item["clause"]],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=item["i0_desc"],
                is_target=True,
                gold_check=ids["I0"],
            ),
            InterpretationBranch(
                id="I1",
                description=item["i1_desc"],
                is_target=False,
                gold_check=ids["I1"],
                opened_by=item["class_id"],
            ),
        ],
        key_questions=[item["question"]],
    )


def _variants_for(spec: FullSpec) -> List[Task]:
    """Emit the k0 (control) + k1 (H1_external disambiguator-deleted) variants."""
    assert len(spec.requirement_classes) == 1, "amd14 base specs are single-axis (k=1)"
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


def generate_tasks(domain: str) -> List[Task]:
    tasks: List[Task] = []
    for item in _ITEMS:
        if item["domain"] == domain:
            tasks.extend(_variants_for(_make_fullspec(item)))
    return tasks


def item_metadata() -> List[Dict[str, Any]]:
    """Post-hoc transparency metadata (NOT an inclusion criterion)."""
    return [
        {
            "task_id": item["task_id"],
            "domain": item["domain"],
            "default_pull": item["default_pull"],
            "i0": item["i0_desc"],
            "i1": item["i1_desc"],
            "deleted_disambiguator": item["clause"],
        }
        for item in _ITEMS
    ]


# Auto-register so importers (test / gold / harness) resolve amd14 checker ids.
register()


_DOMAIN_FILES = {
    "code_spec": "amd14_code_spec.jsonl",
    "policy_qa": "amd14_policy_qa.jsonl",
    "data_analysis": "amd14_data_analysis.jsonl",
    # Pooled sidecar (the whole unfiltered sample in one file).
    "_pool": "amd14_unfiltered.jsonl",
}


if __name__ == "__main__":
    data_dir = _REPO_ROOT / "bench" / "data"
    data_dir.mkdir(exist_ok=True)

    pool: List[Task] = []
    for domain in ("code_spec", "policy_qa", "data_analysis"):
        tasks = generate_tasks(domain)
        save_tasks(tasks, str(data_dir / _DOMAIN_FILES[domain]))
        pool.extend(tasks)
        print(f"Generated {len(tasks)} amd14 {domain} tasks -> {_DOMAIN_FILES[domain]}")

    save_tasks(pool, str(data_dir / _DOMAIN_FILES["_pool"]))
    print(f"Generated {len(pool)} amd14 tasks total -> {_DOMAIN_FILES['_pool']}")

    strong = sum(1 for it in _ITEMS if it["default_pull"] == "strong")
    even = sum(1 for it in _ITEMS if it["default_pull"] == "even_odds")
    print(f"Base items: {len(_ITEMS)} (default_pull: strong={strong}, even_odds={even})")
    for t in pool:
        print(f"  {t.id:<40} k={t.ambiguity_level} regime={t.regime} "
              f"interps={len(t.interpretations)}")
