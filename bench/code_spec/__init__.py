# constructed by: Claude (Anthropic) family
"""Code specification domain — REVERSED-TARGET benchmark tasks.

This domain features coding problems where deleting a requirement class creates
genuine, real-world ambiguity. Under the REVERSED property (Amendment 01):
  - I0 (target) = the NON-default true intent stated by the full latent_spec
  - I_d (one foil) = the model's natural default (what an unaware solver produces
    from the underdetermined prompt)
  - regime: H1_external (disambiguator absent & external) or H2_derivable
    (disambiguator present/derivable in prompt data)

Each interpretation is realized by an actual reference implementation with
executable gold checkers. 100% distinguishability is enforced by validate.py.
"""

from typing import Any, Dict, List, Tuple
import textwrap

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
# GOLD CHECKERS - Execute candidate code in an ISOLATED subprocess
# ============================================================================

import json
import os
import subprocess
import sys
import tempfile

_RUNNER_PATH = os.path.join(os.path.dirname(__file__), "_runner.py")
_TIMEOUT_SECONDS = 5.0

# Deterministic execution => results are cacheable. Keyed by (checker id,
# candidate source) to avoid re-spawning a subprocess for repeated
# (checker, candidate) pairs during n×n validation across k-variants.
_RESULT_CACHE: Dict[Tuple[str, str], Tuple[bool, str]] = {}


class CodeChecker(GoldChecker):
    """Executes a candidate in a separate, killable subprocess.

    Correctness/robustness guarantees (see bench/code_spec/_runner.py for the
    threat model):
    - HARD timeout: a runaway/infinite-loop candidate is killed, never hangs
      validation and leaves no live thread behind. The verdict travels over a
      dedicated temp file and the child's stdout/stderr are sent to DEVNULL, so
      the parent never blocks on a pipe that a candidate-spawned grandchild
      process might keep open.
    - Isolation: each candidate runs in its own process; candidate stdout/stderr
      is discarded and can never corrupt the verdict channel.
    - Deterministic labeling: a bool result is never accepted where an int is
      expected (guards against `True == 1` masquerading as a count).
    NOTE: this is isolation + timeout, NOT a security sandbox — candidates are
    assumed to be non-adversarial model outputs.
    """

    def __init__(self, test_cases: List[Tuple[Any, Any]], entrypoint: str, description: str = ""):
        """
        Args:
            test_cases: List of (input, expected_output) pairs. A tuple input is
                treated as multiple positional args; any other input is a single arg.
            entrypoint: The explicit function name to call (e.g., 'sort_func').
            description: Human-readable id for diagnostics.
        """
        self.test_cases = test_cases
        self.entrypoint = entrypoint
        self.description = description

    def _serialize_cases(self) -> List[Dict[str, Any]]:
        cases = []
        for inp, expected in self.test_cases:
            multi = isinstance(inp, tuple)
            cases.append({
                "multi": multi,
                "input": list(inp) if multi else inp,
                "expected": expected,
            })
        return cases

    def check(self, candidate: Any) -> CheckResult:
        if not isinstance(candidate, str):
            return CheckResult(passed=False,
                               details=f"Candidate must be Python code string, got {type(candidate)}")

        cache_key = (self.description, candidate)
        cached = _RESULT_CACHE.get(cache_key)
        if cached is not None:
            passed, msg = cached
            return CheckResult(passed=passed, details=f"{self.description} - {msg}")

        payload = json.dumps({
            "candidate": candidate,
            "entrypoint": self.entrypoint,
            "test_cases": self._serialize_cases(),
        })

        # BLOCKER FIX: Verdict delivered over PARENT-OWNED PIPE (supervisor stdout),
        # NOT a shared temp file. The supervisor writes verdict to stdout with a
        # sentinel prefix. The candidate worker's stdout goes to a separate pipe
        # (to supervisor), so candidate cannot write to CodeChecker's pipe.
        try:
            result = subprocess.run(
                [sys.executable, _RUNNER_PATH],  # No verdict_path arg
                input=payload,
                text=True,
                capture_output=True,  # Capture supervisor stdout
                timeout=_TIMEOUT_SECONDS * 2,  # Allow supervisor its own timeout budget
            )
        except subprocess.TimeoutExpired:
            # Supervisor itself timed out (shouldn't happen in practice)
            result_tuple = (False, "Supervisor timeout (unexpected)")
            _RESULT_CACHE[cache_key] = result_tuple
            return CheckResult(passed=False, details=f"{self.description} - {result_tuple[1]}")

        # Parse verdict from supervisor stdout (sentinel line)
        verdict = None
        for line in result.stdout.splitlines():
            if line.startswith("__CODESPEC_VERDICT__ "):
                try:
                    verdict_json = line[len("__CODESPEC_VERDICT__ "):]
                    verdict = json.loads(verdict_json)
                    break
                except Exception:  # noqa: BLE001
                    pass
        
        if verdict is None:
            msg = "No verdict in supervisor output"
            _RESULT_CACHE[cache_key] = (False, msg)
            return CheckResult(passed=False, details=f"{self.description} - {msg}")

        passed = verdict.get("status") == "pass"
        msg = verdict.get("message", "")
        _RESULT_CACHE[cache_key] = (passed, msg)
        return CheckResult(passed=passed, details=f"{self.description} - {msg}")



# ============================================================================


# ============================================================================
# PROBLEM LIBRARY — COMBINATORIAL-INVARIANT reversed-target tasks (Amendment 03)
#
# Single-axis convention units (H1_external) stacked for k-gradient:
#   C_Q  fiscal_year_start:      target=fiscal-April    default=calendar
#   C_D  date_format_convention: target=US MM/DD/YYYY   default=ISO YYYY-MM-DD
#   C_R  rounding_standard:      target=GAAP halfup+parens  default=Python halfeven+minus
#   C_I  indexing_convention:    target=1-based inclusive   default=Python 0-based exclusive
#
# Families:
#   code_quarter_001     k_max=1  axis C_Q        -> 2 variants (k0, k1)
#   code_getitems_001    k_max=1  axis C_I        -> 2 variants
#   code_roundcurr_001   k_max=1  axis C_R        -> 2 variants [MAJOR fix: neg-tie test]
#   code_date_001        k_max=1  axis C_D        -> 2 variants
#   code_quarterdate_001 k_max=2  axes C_Q+C_D   -> 4 variants (k0,2xk1,k2_all)
#   code_invoice_001     k_max=3  axes C_Q+C_D+C_R -> 8 variants (k0,3xk1,3xk2,k3_all)
#
# Amended invariant (Amendment 03):
#   len(key_questions) == k' == |S| (deleted axes)
#   len(interpretations) == 2^k'  (full combinatorial set)
#   I0 = all-target; combined-all-default foil marked [combined-default]
#   100% distinguishable across ALL 2^k' via executable gold.
# ============================================================================


def problem_fiscal_quarter():
    """k=1 family, single axis C_Q: fiscal-April quarter.

    H1_external: org fiscal-year-start is EXTERNAL policy, not prompt-derivable.
    1 req class -> 2^1=2 interps: I0 (target) + I1 ([combined-default]).
    """
    return FullSpec(
        domain="code_spec",
        task_id="code_quarter_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `quarter(month)` that returns the quarter number "
            "for a given calendar month number (1-12)."
        ),
        requirement_classes=[
            RequirementClass(
                id="fiscal_year_start",
                description="Fiscal year start month",
                clauses=[
                    "Our fiscal year starts in April: "
                    "Apr-Jun=Q1, Jul-Sep=Q2, Oct-Dec=Q3, Jan-Mar=Q4."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: fiscal-April start, 1-indexed (target). "
                    "Apr=1, Jul=2, Oct=3, Jan=4."
                ),
                is_target=True,
                gold_check="quarter_fiscal_april",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: calendar quarters 1-indexed. "
                    "Jan=1, Apr=2, Jul=3, Oct=4."
                ),
                is_target=False,
                gold_check="quarter_calendar",
                opened_by="fiscal_year_start",
            ),
        ],
        key_questions=[
            "When does the fiscal year start (which month maps to quarter 1)?",
        ],
    )


def problem_get_items():
    """k=1 family, single axis C_I: 1-based inclusive indexing.

    H1_external: the 1-based inclusive convention is an EXTERNAL API contract.
    1 req class -> 2^1=2 interps: I0 (target) + I1 ([combined-default]).
    """
    return FullSpec(
        domain="code_spec",
        task_id="code_getitems_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `get_items(lst, start, end)` that returns a "
            "sublist of `lst` from position `start` to position `end`."
        ),
        requirement_classes=[
            RequirementClass(
                id="indexing_convention",
                description="Index base and end-inclusivity",
                clauses=[
                    "Positions use 1-BASED INDEXING (start=1 selects the first element) "
                    "and the `end` position is INCLUSIVE, as required by the external API "
                    "specification."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: 1-based indexing, inclusive end (target). "
                    "Equivalent to lst[start-1:end]."
                ),
                is_target=True,
                gold_check="getitems_1based_incl",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: Python 0-based indexing, exclusive end. "
                    "Equivalent to lst[start:end]."
                ),
                is_target=False,
                gold_check="getitems_0based_excl",
                opened_by="indexing_convention",
            ),
        ],
        key_questions=[
            "What indexing convention: 1-based inclusive (start=1 for first, end included) "
            "or Python 0-based exclusive (start=0 for first, end excluded)?",
        ],
    )


def problem_round_currency():
    """k=1 family, single axis C_R: GAAP half-up + parentheses for negatives.

    H1_external: the GAAP accounting standard is EXTERNAL; model defaults to Python.
    1 req class -> 2^1=2 interps: I0 (target) + I1 ([combined-default]).

    MAJOR fix (Amendment 03): negative-tie test case -0.125 -> '(0.13)' added
    so a wrong candidate using half-even on negatives cannot pass the checker.
    """
    return FullSpec(
        domain="code_spec",
        task_id="code_roundcurr_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `round_currency(amount)` that rounds a monetary "
            "amount to exactly 2 decimal places and returns it as a string."
        ),
        requirement_classes=[
            RequirementClass(
                id="rounding_standard",
                description="Rounding rule and sign convention for negatives",
                clauses=[
                    "Per our company's GAAP-aligned accounting standard: use ROUND HALF UP "
                    "(ties round away from zero, e.g. 0.125 -> '0.13', -0.125 -> '(0.13)'); "
                    "and use parentheses for negative amounts (e.g. -1.50 -> '(1.50)')."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: GAAP half-up + parentheses for negatives (target). "
                    "0.125->'0.13', -0.125->'(0.13)', -1.5->'(1.50)'."
                ),
                is_target=True,
                gold_check="roundcurr_halfup_paren",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: Python f\"{x:.2f}\" half-even + minus. "
                    "0.125->'0.12', -0.125->'-0.12', -1.5->'-1.50'."
                ),
                is_target=False,
                gold_check="roundcurr_halfeven_minus",
                opened_by="rounding_standard",
            ),
        ],
        key_questions=[
            "Which rounding standard: GAAP half-up with parentheses for negatives, "
            "or Python default half-even with standard minus sign?",
        ],
    )


def problem_format_date():
    """k=1 family, single axis C_D: US MM/DD/YYYY date format.

    H1_external: the US reporting-system convention is EXTERNAL; model defaults to ISO.
    1 req class -> 2^1=2 interps: I0 (target) + I1 ([combined-default]).
    """
    return FullSpec(
        domain="code_spec",
        task_id="code_date_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `format_date(year, month, day)` that formats "
            "a date as a string."
        ),
        requirement_classes=[
            RequirementClass(
                id="date_format_convention",
                description="Date format (US vs ISO)",
                clauses=[
                    "Use US format: MM/DD/YYYY with zero-padded month and day "
                    "(e.g., January 5, 2023 -> '01/05/2023'). This is our "
                    "internal reporting system's required format with 4-digit years."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: US format MM/DD/YYYY, 4-digit year (target). "
                    "(2023,1,5)->'01/05/2023'."
                ),
                is_target=True,
                gold_check="date_us_4y",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: ISO 8601 YYYY-MM-DD, 4-digit year. "
                    "(2023,1,5)->'2023-01-05'."
                ),
                is_target=False,
                gold_check="date_iso_4y",
                opened_by="date_format_convention",
            ),
        ],
        key_questions=[
            "What date format: US (MM/DD/YYYY) or ISO 8601 (YYYY-MM-DD)?",
        ],
    )


def problem_quarter_date():
    """k=2 family, axes C_Q + C_D: fiscal quarter AND US date format.

    H1_external: both conventions are EXTERNAL; model defaults on both when both
    are deleted.  INDEPENDENCE: quarter uses only month; date uses year/month/day
    separately; varying one axis does not change the other's gold.

    2 req classes -> 2^2=4 interpretations:
      I0  fiscal-Apr + US date   [all-target]
      I1  fiscal-Apr + ISO date  [C_D defaulted, partial]
      I2  calendar   + US date   [C_Q defaulted, partial]
      I3  calendar   + ISO date  [combined-default]

    Combinatorial variants from generate_tasks:
      k0                 -> {I0}
      k1 delete C_Q      -> {I0, I2}
      k1 delete C_D      -> {I0, I1}
      k2 delete C_Q+C_D  -> {I0, I1, I2, I3}
    """
    return FullSpec(
        domain="code_spec",
        task_id="code_quarterdate_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `format_quarter_date(year, month, day)` that "
            "returns a string of the form 'Q{n} {date}', combining the fiscal "
            "quarter label and the formatted date, separated by a space."
        ),
        requirement_classes=[
            RequirementClass(
                id="fiscal_year_start",
                description="Fiscal year start month for quarter computation",
                clauses=[
                    "Our fiscal year starts in April: "
                    "Apr-Jun=Q1, Jul-Sep=Q2, Oct-Dec=Q3, Jan-Mar=Q4."
                ],
            ),
            RequirementClass(
                id="date_format_convention",
                description="Date format for the date component",
                clauses=[
                    "Use US date format: MM/DD/YYYY with zero-padded month and day "
                    "(e.g., May 15, 2024 -> '05/15/2024'). 4-digit year."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: fiscal-April quarter + US date format (target, all-target). "
                    "(2024,5,15)->'Q1 05/15/2024'."
                ),
                is_target=True,
                gold_check="quarterdate_fQ_us",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "Partial default: fiscal-April quarter + ISO date (C_D defaulted). "
                    "(2024,5,15)->'Q1 2024-05-15'."
                ),
                is_target=False,
                gold_check="quarterdate_fQ_iso",
                opened_by="date_format_convention",
            ),
            InterpretationBranch(
                id="I2",
                description=(
                    "Partial default: calendar quarter + US date (C_Q defaulted). "
                    "(2024,5,15)->'Q2 05/15/2024'."
                ),
                is_target=False,
                gold_check="quarterdate_cal_us",
                opened_by="fiscal_year_start",
            ),
            InterpretationBranch(
                id="I3",
                description=(
                    "MODEL DEFAULT [combined-default]: calendar quarter + ISO date "
                    "(C_Q and C_D both defaulted). (2024,5,15)->'Q2 2024-05-15'."
                ),
                is_target=False,
                gold_check="quarterdate_cal_iso",
                opened_by="fiscal_year_start,date_format_convention",
            ),
        ],
        key_questions=[
            "Which fiscal year start: April (our fiscal year) or January (calendar year)?",
            "What date format: US (MM/DD/YYYY) or ISO 8601 (YYYY-MM-DD)?",
        ],
    )


def problem_invoice_line():
    """k=3 family, axes C_Q + C_D + C_R: fiscal quarter, US date, GAAP rounding.

    H1_external: all three conventions are EXTERNAL; model defaults on all three
    when all are deleted.  The three axes are INDEPENDENT: quarter uses only month;
    date uses year/month/day; amount uses only the amount value.

    3 req classes -> 2^3=8 interpretations (all {target,default} combinations):
      I0  fQ + US + GAAP       [all-target]
      I1  fQ + US + halfeven   [C_R defaulted]
      I2  fQ + ISO + GAAP      [C_D defaulted]
      I3  fQ + ISO + halfeven  [C_D,C_R defaulted]
      I4  cal + US + GAAP      [C_Q defaulted]
      I5  cal + US + halfeven  [C_Q,C_R defaulted]
      I6  cal + ISO + GAAP     [C_Q,C_D defaulted]
      I7  cal + ISO + halfeven [combined-default: all defaulted]
    """
    return FullSpec(
        domain="code_spec",
        task_id="code_invoice_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `format_invoice_line(year, month, day, amount)` that "
            "returns a space-separated string of three parts: the fiscal quarter "
            "label ('Q{n}'), the formatted date string, and the rounded monetary "
            "amount string."
        ),
        requirement_classes=[
            RequirementClass(
                id="fiscal_year_start",
                description="Fiscal year start month for quarter computation",
                clauses=[
                    "Our fiscal year starts in April: "
                    "Apr-Jun=Q1, Jul-Sep=Q2, Oct-Dec=Q3, Jan-Mar=Q4."
                ],
            ),
            RequirementClass(
                id="date_format_convention",
                description="Date format for the date component",
                clauses=[
                    "Use US date format: MM/DD/YYYY with zero-padded month and day "
                    "(e.g., May 15, 2024 -> '05/15/2024'). 4-digit year."
                ],
            ),
            RequirementClass(
                id="rounding_standard",
                description="Rounding rule and sign convention for the amount",
                clauses=[
                    "Per our GAAP-aligned accounting standard: use ROUND HALF UP "
                    "(ties round away from zero, e.g. 0.125 -> '0.13', -0.125 -> '(0.13)'); "
                    "and use parentheses for negative amounts (e.g. -1.50 -> '(1.50)')."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: fiscal-April + US date + GAAP rounding (target, all-target). "
                    "(2024,5,15,0.125)->'Q1 05/15/2024 0.13'."
                ),
                is_target=True,
                gold_check="invoice_fQ_us_gaap",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "Partial default: fiscal-April + US date + half-even (C_R defaulted). "
                    "(2024,5,15,0.125)->'Q1 05/15/2024 0.12'."
                ),
                is_target=False,
                gold_check="invoice_fQ_us_halfeven",
                opened_by="rounding_standard",
            ),
            InterpretationBranch(
                id="I2",
                description=(
                    "Partial default: fiscal-April + ISO date + GAAP (C_D defaulted). "
                    "(2024,5,15,0.125)->'Q1 2024-05-15 0.13'."
                ),
                is_target=False,
                gold_check="invoice_fQ_iso_gaap",
                opened_by="date_format_convention",
            ),
            InterpretationBranch(
                id="I3",
                description=(
                    "Partial default: fiscal-April + ISO date + half-even "
                    "(C_D, C_R defaulted). (2024,5,15,0.125)->'Q1 2024-05-15 0.12'."
                ),
                is_target=False,
                gold_check="invoice_fQ_iso_halfeven",
                opened_by="date_format_convention,rounding_standard",
            ),
            InterpretationBranch(
                id="I4",
                description=(
                    "Partial default: calendar + US date + GAAP (C_Q defaulted). "
                    "(2024,5,15,0.125)->'Q2 05/15/2024 0.13'."
                ),
                is_target=False,
                gold_check="invoice_cal_us_gaap",
                opened_by="fiscal_year_start",
            ),
            InterpretationBranch(
                id="I5",
                description=(
                    "Partial default: calendar + US date + half-even "
                    "(C_Q, C_R defaulted). (2024,5,15,0.125)->'Q2 05/15/2024 0.12'."
                ),
                is_target=False,
                gold_check="invoice_cal_us_halfeven",
                opened_by="fiscal_year_start,rounding_standard",
            ),
            InterpretationBranch(
                id="I6",
                description=(
                    "Partial default: calendar + ISO date + GAAP "
                    "(C_Q, C_D defaulted). (2024,5,15,0.125)->'Q2 2024-05-15 0.13'."
                ),
                is_target=False,
                gold_check="invoice_cal_iso_gaap",
                opened_by="fiscal_year_start,date_format_convention",
            ),
            InterpretationBranch(
                id="I7",
                description=(
                    "MODEL DEFAULT [combined-default]: calendar + ISO date + half-even "
                    "(all three defaulted). (2024,5,15,0.125)->'Q2 2024-05-15 0.12'."
                ),
                is_target=False,
                gold_check="invoice_cal_iso_halfeven",
                opened_by="fiscal_year_start,date_format_convention,rounding_standard",
            ),
        ],
        key_questions=[
            "Which fiscal year start: April (our fiscal year) or January (calendar year)?",
            "What date format: US (MM/DD/YYYY) or ISO 8601 (YYYY-MM-DD)?",
            "Which rounding standard: GAAP half-up with parentheses for negatives, "
            "or Python default half-even with minus sign?",
        ],
    )


# ============================================================================
# REFERENCE IMPLEMENTATIONS — one per interpretation per family.
# Each reference must pass ONLY its own checker and FAIL all others.
# ============================================================================

REFERENCE_IMPLEMENTATIONS = {
    # ── code_quarter_001 (C_Q axis) ──────────────────────────────────────────
    "quarter_fiscal_april": """
def quarter(month):
    return (month - 4) % 12 // 3 + 1
""",
    "quarter_calendar": """
def quarter(month):
    return (month - 1) // 3 + 1
""",

    # ── code_getitems_001 (C_I axis) ─────────────────────────────────────────
    "getitems_1based_incl": """
def get_items(lst, start, end):
    return lst[start - 1:end]
""",
    "getitems_0based_excl": """
def get_items(lst, start, end):
    return lst[start:end]
""",

    # ── code_roundcurr_001 (C_R axis) ────────────────────────────────────────
    "roundcurr_halfup_paren": """
def round_currency(amount):
    from decimal import Decimal, ROUND_HALF_UP
    abs_result = Decimal(str(abs(amount))).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    if amount < 0:
        return f"({abs_result})"
    return str(abs_result)
""",
    "roundcurr_halfeven_minus": """
def round_currency(amount):
    return f"{amount:.2f}"
""",

    # ── code_date_001 (C_D axis) ──────────────────────────────────────────────
    "date_us_4y": """
def format_date(year, month, day):
    return f"{month:02d}/{day:02d}/{year:04d}"
""",
    "date_iso_4y": """
def format_date(year, month, day):
    return f"{year:04d}-{month:02d}-{day:02d}"
""",

    # ── code_quarterdate_001 (C_Q + C_D axes) ────────────────────────────────
    "quarterdate_fQ_us": """
def format_quarter_date(year, month, day):
    q = (month - 4) % 12 // 3 + 1
    return f"Q{q} {month:02d}/{day:02d}/{year:04d}"
""",
    "quarterdate_fQ_iso": """
def format_quarter_date(year, month, day):
    q = (month - 4) % 12 // 3 + 1
    return f"Q{q} {year:04d}-{month:02d}-{day:02d}"
""",
    "quarterdate_cal_us": """
def format_quarter_date(year, month, day):
    q = (month - 1) // 3 + 1
    return f"Q{q} {month:02d}/{day:02d}/{year:04d}"
""",
    "quarterdate_cal_iso": """
def format_quarter_date(year, month, day):
    q = (month - 1) // 3 + 1
    return f"Q{q} {year:04d}-{month:02d}-{day:02d}"
""",

    # ── code_invoice_001 (C_Q + C_D + C_R axes) ──────────────────────────────
    "invoice_fQ_us_gaap": """
def format_invoice_line(year, month, day, amount):
    from decimal import Decimal, ROUND_HALF_UP
    q = (month - 4) % 12 // 3 + 1
    date_str = f"{month:02d}/{day:02d}/{year:04d}"
    abs_result = Decimal(str(abs(amount))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    amount_str = f"({abs_result})" if amount < 0 else str(abs_result)
    return f"Q{q} {date_str} {amount_str}"
""",
    "invoice_fQ_us_halfeven": """
def format_invoice_line(year, month, day, amount):
    q = (month - 4) % 12 // 3 + 1
    date_str = f"{month:02d}/{day:02d}/{year:04d}"
    return f"Q{q} {date_str} {amount:.2f}"
""",
    "invoice_fQ_iso_gaap": """
def format_invoice_line(year, month, day, amount):
    from decimal import Decimal, ROUND_HALF_UP
    q = (month - 4) % 12 // 3 + 1
    date_str = f"{year:04d}-{month:02d}-{day:02d}"
    abs_result = Decimal(str(abs(amount))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    amount_str = f"({abs_result})" if amount < 0 else str(abs_result)
    return f"Q{q} {date_str} {amount_str}"
""",
    "invoice_fQ_iso_halfeven": """
def format_invoice_line(year, month, day, amount):
    q = (month - 4) % 12 // 3 + 1
    date_str = f"{year:04d}-{month:02d}-{day:02d}"
    return f"Q{q} {date_str} {amount:.2f}"
""",
    "invoice_cal_us_gaap": """
def format_invoice_line(year, month, day, amount):
    from decimal import Decimal, ROUND_HALF_UP
    q = (month - 1) // 3 + 1
    date_str = f"{month:02d}/{day:02d}/{year:04d}"
    abs_result = Decimal(str(abs(amount))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    amount_str = f"({abs_result})" if amount < 0 else str(abs_result)
    return f"Q{q} {date_str} {amount_str}"
""",
    "invoice_cal_us_halfeven": """
def format_invoice_line(year, month, day, amount):
    q = (month - 1) // 3 + 1
    date_str = f"{month:02d}/{day:02d}/{year:04d}"
    return f"Q{q} {date_str} {amount:.2f}"
""",
    "invoice_cal_iso_gaap": """
def format_invoice_line(year, month, day, amount):
    from decimal import Decimal, ROUND_HALF_UP
    q = (month - 1) // 3 + 1
    date_str = f"{year:04d}-{month:02d}-{day:02d}"
    abs_result = Decimal(str(abs(amount))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    amount_str = f"({abs_result})" if amount < 0 else str(abs_result)
    return f"Q{q} {date_str} {amount_str}"
""",
    "invoice_cal_iso_halfeven": """
def format_invoice_line(year, month, day, amount):
    q = (month - 1) // 3 + 1
    date_str = f"{year:04d}-{month:02d}-{day:02d}"
    return f"Q{q} {date_str} {amount:.2f}"
""",
}


# ============================================================================
# TEST CASES — input/output pairs for each checker.
# Every PAIR of checkers within a family differs on at least one test case.
# ============================================================================

TEST_CASES = {
    # ── code_quarter_001 ─────────────────────────────────────────────────────
    "quarter_fiscal_april": [
        (4, 1), (7, 2), (10, 3), (1, 4),
    ],
    "quarter_calendar": [
        (1, 1), (4, 2), (7, 3), (10, 4),
    ],

    # ── code_getitems_001 ────────────────────────────────────────────────────
    "getitems_1based_incl": [
        (([10, 20, 30, 40, 50], 2, 4), [20, 30, 40]),
        (([10, 20, 30, 40, 50], 1, 3), [10, 20, 30]),
    ],
    "getitems_0based_excl": [
        (([10, 20, 30, 40, 50], 2, 4), [30, 40]),
        (([10, 20, 30, 40, 50], 1, 3), [20, 30]),
    ],

    # ── code_roundcurr_001 ───────────────────────────────────────────────────
    # 0.125 (exact 1/8): halfup=0.13, halfeven=0.12
    # -0.125 (MAJOR fix): halfup_paren=(0.13), halfeven_minus=-0.12
    "roundcurr_halfup_paren": [
        (0.125, "0.13"),
        (-0.125, "(0.13)"),
        (-1.5, "(1.50)"),
        (2.0, "2.00"),
    ],
    "roundcurr_halfeven_minus": [
        (0.125, "0.12"),
        (-0.125, "-0.12"),
        (-1.5, "-1.50"),
        (2.0, "2.00"),
    ],

    # ── code_date_001 ────────────────────────────────────────────────────────
    "date_us_4y": [
        ((2023, 1, 5), "01/05/2023"),
        ((2023, 12, 31), "12/31/2023"),
    ],
    "date_iso_4y": [
        ((2023, 1, 5), "2023-01-05"),
        ((2023, 12, 31), "2023-12-31"),
    ],

    # ── code_quarterdate_001 ─────────────────────────────────────────────────
    # (2024,5,15): fQ=Q1(May), cal=Q2(May), US=05/15/2024, ISO=2024-05-15
    # (2024,1,10): fQ=Q4(Jan), cal=Q1(Jan), US=01/10/2024, ISO=2024-01-10
    "quarterdate_fQ_us": [
        ((2024, 5, 15), "Q1 05/15/2024"),
        ((2024, 1, 10), "Q4 01/10/2024"),
    ],
    "quarterdate_fQ_iso": [
        ((2024, 5, 15), "Q1 2024-05-15"),
        ((2024, 1, 10), "Q4 2024-01-10"),
    ],
    "quarterdate_cal_us": [
        ((2024, 5, 15), "Q2 05/15/2024"),
        ((2024, 1, 10), "Q1 01/10/2024"),
    ],
    "quarterdate_cal_iso": [
        ((2024, 5, 15), "Q2 2024-05-15"),
        ((2024, 1, 10), "Q1 2024-01-10"),
    ],

    # ── code_invoice_001 ─────────────────────────────────────────────────────
    # (2024,5,15,0.125): fQ=Q1,cal=Q2, US=05/15/2024,ISO=2024-05-15
    #   GAAP(+)=0.13, halfeven(+)=0.12
    # (2024,1,10,-0.125): fQ=Q4,cal=Q1
    #   GAAP(neg)=(0.13), halfeven(neg)=-0.12
    "invoice_fQ_us_gaap": [
        ((2024, 5, 15, 0.125),  "Q1 05/15/2024 0.13"),
        ((2024, 1, 10, -0.125), "Q4 01/10/2024 (0.13)"),
    ],
    "invoice_fQ_us_halfeven": [
        ((2024, 5, 15, 0.125),  "Q1 05/15/2024 0.12"),
        ((2024, 1, 10, -0.125), "Q4 01/10/2024 -0.12"),
    ],
    "invoice_fQ_iso_gaap": [
        ((2024, 5, 15, 0.125),  "Q1 2024-05-15 0.13"),
        ((2024, 1, 10, -0.125), "Q4 2024-01-10 (0.13)"),
    ],
    "invoice_fQ_iso_halfeven": [
        ((2024, 5, 15, 0.125),  "Q1 2024-05-15 0.12"),
        ((2024, 1, 10, -0.125), "Q4 2024-01-10 -0.12"),
    ],
    "invoice_cal_us_gaap": [
        ((2024, 5, 15, 0.125),  "Q2 05/15/2024 0.13"),
        ((2024, 1, 10, -0.125), "Q1 01/10/2024 (0.13)"),
    ],
    "invoice_cal_us_halfeven": [
        ((2024, 5, 15, 0.125),  "Q2 05/15/2024 0.12"),
        ((2024, 1, 10, -0.125), "Q1 01/10/2024 -0.12"),
    ],
    "invoice_cal_iso_gaap": [
        ((2024, 5, 15, 0.125),  "Q2 2024-05-15 0.13"),
        ((2024, 1, 10, -0.125), "Q1 2024-01-10 (0.13)"),
    ],
    "invoice_cal_iso_halfeven": [
        ((2024, 5, 15, 0.125),  "Q2 2024-05-15 0.12"),
        ((2024, 1, 10, -0.125), "Q1 2024-01-10 -0.12"),
    ],
}


# ============================================================================
# CHECKERS REGISTRY
# ============================================================================

ENTRYPOINTS = {
    # k=1 families
    "quarter_fiscal_april":     "quarter",
    "quarter_calendar":         "quarter",
    "getitems_1based_incl":     "get_items",
    "getitems_0based_excl":     "get_items",
    "roundcurr_halfup_paren":   "round_currency",
    "roundcurr_halfeven_minus": "round_currency",
    "date_us_4y":               "format_date",
    "date_iso_4y":              "format_date",
    # k=2 family
    "quarterdate_fQ_us":        "format_quarter_date",
    "quarterdate_fQ_iso":       "format_quarter_date",
    "quarterdate_cal_us":       "format_quarter_date",
    "quarterdate_cal_iso":      "format_quarter_date",
    # k=3 family
    "invoice_fQ_us_gaap":       "format_invoice_line",
    "invoice_fQ_us_halfeven":   "format_invoice_line",
    "invoice_fQ_iso_gaap":      "format_invoice_line",
    "invoice_fQ_iso_halfeven":  "format_invoice_line",
    "invoice_cal_us_gaap":      "format_invoice_line",
    "invoice_cal_us_halfeven":  "format_invoice_line",
    "invoice_cal_iso_gaap":     "format_invoice_line",
    "invoice_cal_iso_halfeven": "format_invoice_line",
}

CHECKERS = {}
for _check_id, _test_cases in TEST_CASES.items():
    _entrypoint = ENTRYPOINTS[_check_id]
    CHECKERS[_check_id] = CodeChecker(
        _test_cases, entrypoint=_entrypoint, description=_check_id
    )


# ============================================================================
# TASK GENERATION
# ============================================================================

def generate_tasks() -> List[Task]:
    """Generate all 20 code_spec tasks (Amendment 03 combinatorial invariant).

    Amended invariant per variant (enforced by post-generation assertion):
        len(key_questions) == k'       (deleted-axis count)
        len(interpretations) == 2^k'   (full combinatorial set)
        I0 = all-target; combined-all-default marked [combined-default]
        k0 control: prompt==latent_spec, 1 interp, empty key_questions.

    Task count:
        4 k=1 families x 2 variants     =  8
        1 k=2 family   x 4 variants     =  4
        1 k=3 family   x 8 variants     =  8
        Total                           = 20
    """
    tasks = []

    # ── k=1 single-axis families ─────────────────────────────────────────────
    k1_defs = [
        (problem_fiscal_quarter(),  [
            ("_k0", []),
            ("_k1_fiscal_year_start", ["fiscal_year_start"]),
        ]),
        (problem_get_items(), [
            ("_k0", []),
            ("_k1_indexing_convention", ["indexing_convention"]),
        ]),
        (problem_round_currency(), [
            ("_k0", []),
            ("_k1_rounding_standard", ["rounding_standard"]),
        ]),
        (problem_format_date(), [
            ("_k0", []),
            ("_k1_date_format_convention", ["date_format_convention"]),
        ]),
    ]

    for base_spec, variant_defs in k1_defs:
        qmap = {
            rc.id: q
            for rc, q in zip(base_spec.requirement_classes, base_spec.key_questions)
        }
        for suffix, delete_ids in variant_defs:
            spec_copy = FullSpec(
                domain=base_spec.domain,
                task_id=base_spec.task_id + suffix,
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

    # ── k=2 family: code_quarterdate_001 ─────────────────────────────────────
    qd_spec = problem_quarter_date()
    qd_qmap = {
        rc.id: q
        for rc, q in zip(qd_spec.requirement_classes, qd_spec.key_questions)
    }
    for suffix, delete_ids in [
        ("_k0",                        []),
        ("_k1_fiscal_year_start",      ["fiscal_year_start"]),
        ("_k1_date_format_convention", ["date_format_convention"]),
        ("_k2_all",                    ["fiscal_year_start", "date_format_convention"]),
    ]:
        spec_copy = FullSpec(
            domain=qd_spec.domain,
            task_id=qd_spec.task_id + suffix,
            prompt_core=qd_spec.prompt_core,
            requirement_classes=qd_spec.requirement_classes[:],
            interpretations=qd_spec.interpretations[:],
            key_questions=qd_spec.key_questions[:],
            regime=qd_spec.regime,
        )
        task = assemble_task(
            spec_copy, k=len(delete_ids),
            classes_to_delete=delete_ids if delete_ids else None,
        )
        task.key_questions = [qd_qmap[cid] for cid in delete_ids]
        tasks.append(task)

    # ── k=3 family: code_invoice_001 ─────────────────────────────────────────
    inv_spec = problem_invoice_line()
    inv_qmap = {
        rc.id: q
        for rc, q in zip(inv_spec.requirement_classes, inv_spec.key_questions)
    }
    for suffix, delete_ids in [
        ("_k0",                        []),
        ("_k1_fiscal_year_start",      ["fiscal_year_start"]),
        ("_k1_date_format_convention", ["date_format_convention"]),
        ("_k1_rounding_standard",      ["rounding_standard"]),
        ("_k2_fiscal_date",    ["fiscal_year_start", "date_format_convention"]),
        ("_k2_fiscal_rounding",["fiscal_year_start", "rounding_standard"]),
        ("_k2_date_rounding",  ["date_format_convention", "rounding_standard"]),
        ("_k3_all",            ["fiscal_year_start", "date_format_convention",
                                 "rounding_standard"]),
    ]:
        spec_copy = FullSpec(
            domain=inv_spec.domain,
            task_id=inv_spec.task_id + suffix,
            prompt_core=inv_spec.prompt_core,
            requirement_classes=inv_spec.requirement_classes[:],
            interpretations=inv_spec.interpretations[:],
            key_questions=inv_spec.key_questions[:],
            regime=inv_spec.regime,
        )
        task = assemble_task(
            spec_copy, k=len(delete_ids),
            classes_to_delete=delete_ids if delete_ids else None,
        )
        task.key_questions = [inv_qmap[cid] for cid in delete_ids]
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
        # __combdef marker: every k>0 task must have EXACTLY ONE combined-default
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
# FOILS (near-miss adversarial candidates)
# ============================================================================

def get_task_specific_foils(task_id_base: str) -> List[str]:
    """Near-miss foils for each problem family (task_id_base = prefix before '_k')."""

    if task_id_base == "code_quarter_001":
        return [
            # July-start FY: May -> Q4 (not Q1/Q2); 0 checkers
            """
def quarter(month):
    return (month - 7) % 12 // 3 + 1
""",
            # Returns month unchanged; 0 matches
            """
def quarter(month):
    return month
""",
            # Always 1; fails on month=7; 0 matches
            """
def quarter(month):
    return 1
""",
        ]

    elif task_id_base == "code_getitems_001":
        return [
            # 0-based inclusive: lst[start:end+1]; 0 matches
            """
def get_items(lst, start, end):
    return lst[start:end + 1]
""",
            # Returns full list; 0 matches
            """
def get_items(lst, start, end):
    return lst[:]
""",
            # Both offsets wrong; 0 matches
            """
def get_items(lst, start, end):
    return lst[start - 1:end - 1]
""",
        ]

    elif task_id_base == "code_roundcurr_001":
        return [
            # half-even + parentheses: wrong on 0.125 (gives '0.12' not '0.13'); 0 matches
            """
def round_currency(amount):
    if amount < 0:
        return f"({abs(amount):.2f})"
    return f"{amount:.2f}"
""",
            # Returns float, not string; 0 matches
            """
def round_currency(amount):
    from decimal import Decimal, ROUND_HALF_UP
    return float(Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
""",
            # str(amount) unchanged; 0 matches
            """
def round_currency(amount):
    return str(amount)
""",
        ]

    elif task_id_base == "code_date_001":
        return [
            # European DD/MM/YYYY; 0 matches
            """
def format_date(year, month, day):
    return f"{day:02d}/{month:02d}/{year:04d}"
""",
            # US without zero-padding; 0 matches
            """
def format_date(year, month, day):
    return f"{month}/{day}/{year}"
""",
            # ISO 2-digit year; 0 matches
            """
def format_date(year, month, day):
    return f"{year % 100:02d}-{month:02d}-{day:02d}"
""",
        ]

    elif task_id_base == "code_quarterdate_001":
        return [
            # July-start FY + US: May -> Q4 "Q4 05/15/2024"; 0 matches
            """
def format_quarter_date(year, month, day):
    q = (month - 7) % 12 // 3 + 1
    return f"Q{q} {month:02d}/{day:02d}/{year:04d}"
""",
            # Fiscal-April + EU DD/MM: "Q1 15/05/2024"; 0 matches
            """
def format_quarter_date(year, month, day):
    q = (month - 4) % 12 // 3 + 1
    return f"Q{q} {day:02d}/{month:02d}/{year:04d}"
""",
            # 0-indexed fiscal-April + US: "Q0 05/15/2024"; 0 matches
            """
def format_quarter_date(year, month, day):
    q = (month - 4) % 12 // 3
    return f"Q{q} {month:02d}/{day:02d}/{year:04d}"
""",
        ]

    elif task_id_base == "code_invoice_001":
        return [
            # July-start FY + US + GAAP: May -> Q4 "Q4 05/15/2024 0.13"; 0 matches
            """
def format_invoice_line(year, month, day, amount):
    from decimal import Decimal, ROUND_HALF_UP
    q = (month - 7) % 12 // 3 + 1
    date_str = f"{month:02d}/{day:02d}/{year:04d}"
    abs_result = Decimal(str(abs(amount))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    amount_str = f"({abs_result})" if amount < 0 else str(abs_result)
    return f"Q{q} {date_str} {amount_str}"
""",
            # Fiscal-April + EU DD/MM + GAAP: "Q1 15/05/2024 0.13"; 0 matches
            """
def format_invoice_line(year, month, day, amount):
    from decimal import Decimal, ROUND_HALF_UP
    q = (month - 4) % 12 // 3 + 1
    date_str = f"{day:02d}/{month:02d}/{year:04d}"
    abs_result = Decimal(str(abs(amount))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    amount_str = f"({abs_result})" if amount < 0 else str(abs_result)
    return f"Q{q} {date_str} {amount_str}"
""",
            # Fiscal-April + US + raw str(amount): "Q1 05/15/2024 0.125"; 0 matches
            """
def format_invoice_line(year, month, day, amount):
    q = (month - 4) % 12 // 3 + 1
    date_str = f"{month:02d}/{day:02d}/{year:04d}"
    return f"Q{q} {date_str} {amount}"
""",
        ]

    else:
        return ["def func(): raise NotImplementedError()"]


def get_checkers_and_candidates(domain: str, task: Task) -> Tuple[
    Dict[str, GoldChecker], Dict[str, Any], List[Any]
]:
    """Return (checkers, reference-candidates, near-miss-foils) for a task."""
    checkers = {}
    candidates = {}

    for interp in task.interpretations:
        # Strip __combdef suffix — it's a serialized marker, not a checker key.
        check_id = interp.gold_check
        if check_id.endswith("__combdef"):
            check_id = check_id[: -len("__combdef")]
        if check_id not in CHECKERS:
            raise ValueError(f"Unknown checker: {check_id}")
        checkers[interp.id] = CHECKERS[check_id]
        candidates[interp.id] = REFERENCE_IMPLEMENTATIONS[check_id]

    task_id_base = task.id.split("_k")[0] if "_k" in task.id else task.id
    foils = get_task_specific_foils(task_id_base)

    return checkers, candidates, foils


# ============================================================================
# MAIN: Generate data file
# ============================================================================

if __name__ == "__main__":
    from pathlib import Path

    tasks = generate_tasks()
    output_path = Path(__file__).parent.parent / "data" / "code_spec.jsonl"
    output_path.parent.mkdir(exist_ok=True)
    save_tasks(tasks, str(output_path))

    print(f"Generated {len(tasks)} code_spec tasks -> {output_path}")
    levels = {k: sum(1 for t in tasks if t.ambiguity_level == k) for k in range(4)}
    print(f"Ambiguity distribution: {levels}")
    regimes = {}
    for t in tasks:
        r = t.regime if t.regime else "None"
        regimes[r] = regimes.get(r, 0) + 1
    print(f"Regime distribution: {regimes}")
