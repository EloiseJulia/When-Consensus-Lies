# constructed by: Claude (Anthropic) family
"""Data analysis domain for ambiguous data-processing problems.

This domain features data analysis tasks that compute statistics/aggregations
over small in-memory datasets (lists of numbers or lists of dict records), where
deleting requirement CLASSES creates GENUINE ambiguity with multiple defensible
correct interpretations. Each interpretation is realized by an actual reference
implementation with executable gold checkers.
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


class DataChecker(GoldChecker):
    """Executes a candidate in a separate, killable subprocess.

    Correctness/robustness guarantees (see bench/data_analysis/_runner.py for the
    threat model):
    - HARD timeout: a runaway/infinite-loop candidate is killed, never hangs
      validation and leaves no live thread behind. The verdict travels over a
      dedicated temp file and the child's stdout/stderr are sent to DEVNULL, so
      the parent never blocks on a pipe that a candidate-spawned grandchild
      process might keep open.
    - Isolation: each candidate runs in its own process; candidate stdout/stderr
      is discarded and can never corrupt the verdict channel.
    - Deterministic labeling: a bool result is never accepted where an int/float
      is expected (guards against `True == 1` masquerading as a numeric result).
    NOTE: this is isolation + timeout, NOT a security sandbox — candidates are
    assumed to be non-adversarial model outputs.
    """

    def __init__(self, test_cases: List[Tuple[Any, Any]], entrypoint: str, description: str = ""):
        """
        Args:
            test_cases: List of (input, expected_output) pairs. A tuple input is
                treated as multiple positional args; any other input is a single arg.
            entrypoint: The explicit function name to call (e.g., 'compute_mean').
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

    def _is_infra_error(self, verdict) -> bool:
        """Detect infrastructure errors vs genuine candidate failures.
        
        FLAKINESS FIX A: Infra errors are transient (file I/O race, spawn fail)
        and MUST be retried. Genuine candidate errors (wrong result, exec error,
        no output, invalid output) are deterministic and cacheable.
        
        NARROWLY classified infra errors (after worker-side fsync):
        - verdict is None: supervisor produced no verdict sentinel
        - status=="error" with "bad input": worker couldn't parse OUR input_file (race)
        - status=="error" with "bad job": supervisor couldn't parse job JSON
        - status=="error" with "Worker spawn failed": process spawn error
        
        Everything else is a DETERMINISTIC candidate outcome:
        - "No/invalid output": candidate wrote nothing/malformed (early exit/forgery) = FAIL
        - "Invalid output status": candidate's output_file has bad status = FAIL
        - "Execution error": candidate code crashed = FAIL
        - "Test raised": candidate function raised = FAIL
        - Comparison mismatch: candidate wrong answer = FAIL
        """
        if verdict is None:
            return True  # No verdict = infra error
        
        status = verdict.get("status")
        message = verdict.get("message", "")
        
        # status="error" can be either infra or genuine candidate error
        # Distinguish by message pattern (NARROW classification):
        if status == "error":
            # Infrastructure failures (transient, retry):
            infra_patterns = [
                "bad input",           # Worker couldn't read input_file (race)
                "bad job",             # Supervisor couldn't parse job
                "Worker spawn failed", # Process spawn error
            ]
            for pattern in infra_patterns:
                if pattern in message:
                    return True
            # All other status="error" are genuine candidate failures:
            # "No/invalid output" - candidate wrote nothing = FAIL (forgery/early-exit)
            # "Invalid output status" - candidate output malformed = FAIL
            # "Execution error: ..." - candidate code crashed = FAIL
            # "Test raised: ..." - candidate function raised = FAIL
        
        return False  # Pass/fail/genuine-error are all deterministic

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

        # FLAKINESS FIX A: Retry loop for infrastructure errors (max 3 attempts)
        # Happy path runs worker ONCE. Retries fire only on transient infra errors.
        max_attempts = 3
        last_infra_error = None
        
        for attempt in range(max_attempts):
            # BLOCKER FIX: Verdict delivered over PARENT-OWNED PIPE (supervisor stdout),
            # NOT a shared temp file. The supervisor writes verdict to stdout with a
            # sentinel prefix. The candidate worker's stdout goes to a separate pipe
            # (to supervisor), so candidate cannot write to DataChecker's pipe.
            try:
                result = subprocess.run(
                    [sys.executable, _RUNNER_PATH],  # No verdict_path arg
                    input=payload,
                    text=True,
                    capture_output=True,  # Capture supervisor stdout
                    timeout=_TIMEOUT_SECONDS * 2,  # Allow supervisor its own timeout budget
                )
            except subprocess.TimeoutExpired:
                # Supervisor itself timed out (infra error, retry)
                last_infra_error = "Supervisor timeout (unexpected)"
                continue  # Retry

            # Parse verdict from supervisor stdout (sentinel line)
            verdict = None
            for line in result.stdout.splitlines():
                if line.startswith("__DATA_ANALYSIS_VERDICT__ "):
                    try:
                        verdict_json = line[len("__DATA_ANALYSIS_VERDICT__ "):]
                        verdict = json.loads(verdict_json)
                        break
                    except Exception:  # noqa: BLE001
                        pass
            
            # FLAKINESS FIX A: Check if this is an infra error
            if self._is_infra_error(verdict):
                last_infra_error = verdict.get("message", "No verdict") if verdict else "No verdict in supervisor output"
                continue  # Retry
            
            # FLAKINESS FIX B: Cache ONLY deterministic verdicts (pass/fail/genuine-error)
            # Never cache infra errors or timeouts
            passed = verdict.get("status") == "pass"
            msg = verdict.get("message", "")
            _RESULT_CACHE[cache_key] = (passed, msg)
            return CheckResult(passed=passed, details=f"{self.description} - {msg}")
        
        # FLAKINESS FIX A: All 3 attempts were infra errors - RAISE loudly
        # Do NOT silently return a candidate rejection or cache it
        raise RuntimeError(
            f"data_analysis harness infra failure after {max_attempts} retries: {last_infra_error}"
        )

# ============================================================================
# PROBLEM LIBRARY — COMBINATORIAL-INVARIANT reversed-target tasks (Amendment 03)
#
# Under the REVERSED property (Amendment 01):
#   I0 (target) = the NON-default true intent stated by the full latent_spec
#   I_d (a foil) = the model's natural default (what an unaware solver produces
#     from the underdetermined prompt)
#
# Binary convention axes (Amendment 03), each strictly {target, default}:
#   central_tendency:      target=median          default=arithmetic mean   (H2_derivable)
#   price_weighting:       target=qty-weighted avg default=simple col mean   (H2_derivable)
#   rate_interval:         target=Δtotal/Δtime    default=mean of step deltas(H2_derivable)
#   active_user_threshold: target=>=3 (org KPI)   default=>=1 (any activity)(H1_external)
#   avg_rounding:          target=round-half-up    default=round-half-even   (H1_external)
#
# HARDER H2 demonstrators (frontier-calibrated, per 2026-07-17-harder-h2-plan.md): the
# median-skew trap (data_typical_001) is resolved by ALL frontier models (reasoner AND
# weak), collapsing the reasoner-vs-weak H2 contrast. price_weighting + rate_interval are
# SUBTLER derivable traps: the disambiguator is PRESENT in the data (quantities /
# unequal time gaps), so a strong reasoner CAN recover I0, but the derivation requires a
# genuine reasoning step a weak model skips (it averages the visible column). Both are
# pure-stdlib executable gold (no numpy/pandas → run under the DataChecker `python -S`
# sandbox); the live default-check is the empirical arbiter of which actually splits.
#
# Families:
#   data_typical_001      k_max=1  axis central_tendency       -> 2 variants (k0,k1)  H2_derivable
#   data_avgprice_001     k_max=1  axis price_weighting        -> 2 variants (k0,k1)  H2_derivable
#   data_rate_001         k_max=1  axis rate_interval          -> 2 variants (k0,k1)  H2_derivable
#   data_activeusers_001  k_max=1  axis active_user_threshold  -> 2 variants (k0,k1)  H1_external
#   data_report_001       k_max=2  active_user_threshold+avg_rounding -> 4 variants  H1_external
#
# Amended invariant per variant deleting subset S (|S|=k'):
#   len(key_questions) == k'
#   len(interpretations) == 2^k'   (full combinatorial set)
#   I0 = all-target; combined-all-default foil marked [combined-default]
#   100% distinguishable across ALL 2^k' via executable gold (deterministic numeric).
# ============================================================================


def problem_typical_value():
    """k=1 family, axis central_tendency: median under a VISIBLE extreme outlier.

    H2_derivable: the outlier 900 is present in the prompt's dataset, so a
    reasoning model can DERIVE that the mean is distorted and the MEDIAN is the
    representative 'typical value'. The natural default (arithmetic mean) is the
    WRONG foil.

    1 req class -> 2^1=2 interps: I0 (median, target) + I1 (mean, [combined-default]).
    """
    return FullSpec(
        domain="data_analysis",
        task_id="data_typical_001",
        regime="H2_derivable",
        prompt_core=(
            "Write a function `typical_value(data)` that returns the single "
            "representative 'typical value' of the dataset "
            "[2, 4, 4, 4, 5, 5, 7, 900], as a string rounded to 2 decimal places."
        ),
        requirement_classes=[
            RequirementClass(
                id="central_tendency",
                description="Which measure of central tendency represents the typical value",
                clauses=[
                    "This dataset is dominated by a single extreme outlier (900) that "
                    "distorts the mean; report the MEDIAN as the representative typical "
                    "value. Answer to 2 decimals."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: MEDIAN as the typical value (target). The visible "
                    "outlier 900 distorts the mean, so the median is representative. "
                    "[2,4,4,4,5,5,7,900] -> '4.50'."
                ),
                is_target=True,
                gold_check="typical_median",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: arithmetic MEAN as the typical "
                    "value. [2,4,4,4,5,5,7,900] -> mean 931/8 = 116.375 -> '116.38'."
                ),
                is_target=False,
                gold_check="typical_mean",
                opened_by="central_tendency",
            ),
        ],
        key_questions=[
            "Which measure of central tendency represents the 'typical value' (mean/median)?",
        ],
    )


def problem_avg_price():
    """k=1 family, axis price_weighting: quantity-weighted average price.

    H2_derivable (HARDER trap): the prompt embeds a purchase table whose rows carry
    a QUANTITY column. The quantities are PRESENT in the data, so a reasoning model
    can DERIVE that "the average price" over purchases is the quantity-WEIGHTED
    average (total spent / total units), not the simple mean of the unit_price
    column. The natural default (average the visible unit_price column, ignoring the
    quantities) is the WRONG foil.

    WHY H2 (not H1-external): the disambiguator (the quantity weights) is inside the
    prompt's data, recoverable WITHOUT any external convention — a strong reasoner
    weights by quantity; a weak model averages the column it sees.
    WHY a weak model defaults to the foil: "average price" reads as "mean of the
    price column"; weighting by quantity is an extra derivation step it skips.
    PURE STDLIB: sum/`/`/f-string only — runs under the DataChecker `python -S` sandbox
    with no third-party library.

    1 req class -> 2^1=2 interps: I0 (weighted, target) + I1 (simple, [combined-default]).
    """
    return FullSpec(
        domain="data_analysis",
        task_id="data_avgprice_001",
        regime="H2_derivable",
        prompt_core=(
            "Write a function `average_price(items)` that returns the average price "
            "of the following purchase records as a string rounded to 2 decimal "
            "places. Each record is a [quantity, unit_price] pair: "
            "[[1, 10.0], [1, 20.0], [18, 100.0]]."
        ),
        requirement_classes=[
            RequirementClass(
                id="price_weighting",
                description="How to weight unit prices when averaging (by quantity vs unweighted)",
                clauses=[
                    "The 'average price' is the QUANTITY-WEIGHTED average: total spent "
                    "(sum of quantity*unit_price) divided by the total quantity, NOT the "
                    "unweighted mean of the unit_price column. Answer to 2 decimals."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: QUANTITY-WEIGHTED average price (target). The quantity "
                    "weights are present in the data. [[1,10],[1,20],[18,100]] -> "
                    "1830/20 = '91.50'."
                ),
                is_target=True,
                gold_check="avgprice_weighted",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: unweighted simple mean of the "
                    "unit_price column. [[1,10],[1,20],[18,100]] -> (10+20+100)/3 = "
                    "'43.33'."
                ),
                is_target=False,
                gold_check="avgprice_simple",
                opened_by="price_weighting",
            ),
        ],
        key_questions=[
            "Is 'average price' the quantity-weighted average or the unweighted mean "
            "of the unit_price column?",
        ],
    )


def problem_avg_rate():
    """k=1 family, axis rate_interval: rate of change over UNEQUAL time intervals.

    H2_derivable (HARDER trap): the prompt embeds a series of [time, value] points
    whose time gaps are UNEQUAL. The unequal spacing is PRESENT in the data, so a
    reasoning model can DERIVE that "the average rate of change per unit time" is the
    total change divided by the total elapsed time (which accounts for the spacing),
    not the naive mean of the per-step value deltas (which implicitly treats every
    step as one unit of time). The naive per-step-delta mean is the WRONG foil.

    WHY H2 (not H1-external): the disambiguator (the unequal time gaps) is inside the
    prompt's data, recoverable WITHOUT any external convention — a strong reasoner
    divides total change by total elapsed time; a weak model averages the step deltas.
    WHY a weak model defaults to the foil: "average rate of change" reads as "average
    the step-to-step changes"; accounting for unequal spacing is a step it skips.
    PURE STDLIB: indexing/sum/`/`/f-string only — runs under the DataChecker `python -S`
    sandbox with no third-party library.

    1 req class -> 2^1=2 interps: I0 (total/elapsed, target) + I1 (step-mean, [combined-default]).
    """
    return FullSpec(
        domain="data_analysis",
        task_id="data_rate_001",
        regime="H2_derivable",
        prompt_core=(
            "Write a function `avg_rate(series)` that returns the average rate of "
            "change per unit time of the following measurements as a string rounded "
            "to 2 decimal places. Each point is a [time, value] pair (times are NOT "
            "evenly spaced): [[0, 0], [1, 10], [10, 100]]."
        ),
        requirement_classes=[
            RequirementClass(
                id="rate_interval",
                description="How to average the rate of change given unequal time gaps",
                clauses=[
                    "Because the time points are NOT evenly spaced, the 'average rate of "
                    "change per unit time' is the TOTAL change (last value minus first "
                    "value) divided by the TOTAL elapsed time (last time minus first "
                    "time), NOT the unweighted mean of the per-step value deltas. Answer "
                    "to 2 decimals."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: total change / total elapsed time (target). Accounts "
                    "for the unequal spacing present in the data. [[0,0],[1,10],[10,100]] "
                    "-> (100-0)/(10-0) = '10.00'."
                ),
                is_target=True,
                gold_check="rate_total",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: unweighted mean of the per-step "
                    "value deltas (ignores unequal spacing). [[0,0],[1,10],[10,100]] -> "
                    "mean(10, 90) = '50.00'."
                ),
                is_target=False,
                gold_check="rate_stepmean",
                opened_by="rate_interval",
            ),
        ],
        key_questions=[
            "Is 'average rate of change per unit time' total-change/total-elapsed-time "
            "or the mean of the per-step value deltas?",
        ],
    )


def problem_active_users():
    """k=1 family, axis active_user_threshold: org-specific KPI activity threshold.

    H1_external: the KPI 'active user' threshold (>=3 sessions/week) is an EXTERNAL
    company convention, NOT derivable from the data. The natural default (count any
    activity, >=1) is the WRONG foil.

    1 req class -> 2^1=2 interps: I0 (>=3, target) + I1 (>=1, [combined-default]).
    """
    return FullSpec(
        domain="data_analysis",
        task_id="data_activeusers_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `count_active(sessions)` that takes a list of "
            "per-user weekly session counts "
            "[5, 3, 1, 4, 2, 3, 0, 6, 1, 2] and returns the number of active users."
        ),
        requirement_classes=[
            RequirementClass(
                id="active_user_threshold",
                description="Session-count threshold that defines an active user (org KPI)",
                clauses=[
                    "Per our company KPI, an 'active user' has AT LEAST 3 sessions per "
                    "week. Count active users."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: org KPI threshold >=3 sessions/week (target). "
                    "[5,3,1,4,2,3,0,6,1,2] -> 5 active users."
                ),
                is_target=True,
                gold_check="active_threshold3",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: count any activity, threshold >=1. "
                    "[5,3,1,4,2,3,0,6,1,2] -> 9 active users."
                ),
                is_target=False,
                gold_check="active_threshold1",
                opened_by="active_user_threshold",
            ),
        ],
        key_questions=[
            "What session-count threshold defines an 'active user' (the org KPI)?",
        ],
    )


def problem_activity_report():
    """k=2 family, axes active_user_threshold + avg_rounding.

    H1_external: both conventions are EXTERNAL org policy; model defaults on both.

    INDEPENDENCE: the two axes control DISJOINT output segments (like code_spec's
    quarter/date/amount):
      - active_user_threshold changes ONLY the count field N.
      - avg_rounding changes ONLY the average field M (mean = sum/len is
        independent of the threshold).
    Deleting one axis leaves the other's gold unchanged (no interaction term); the
    2^2 golds are the exact Cartesian product. Datasets are chosen so the mean is a
    '.5' tie with an EVEN integer part (half-up != half-even) and the >=3 vs >=1
    counts differ, so all 4 interpretations are pairwise distinct.

    2 req classes -> 2^2=4 interpretations:
      I0  >=3 + half-up    [all-target]
      I1  >=3 + half-even  [avg_rounding defaulted, partial]
      I2  >=1 + half-up    [active_user_threshold defaulted, partial]
      I3  >=1 + half-even  [combined-default]
    """
    return FullSpec(
        domain="data_analysis",
        task_id="data_report_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `format_report(sessions)` that takes a list of "
            "per-user weekly session counts and returns a one-line summary string "
            "of the form '{N} active | avg {M}', where N is the number of active "
            "users and M is the average sessions per user (total sessions divided "
            "by the number of users) as a whole number."
        ),
        requirement_classes=[
            RequirementClass(
                id="active_user_threshold",
                description="Session-count threshold that defines an active user (org KPI)",
                clauses=[
                    "Per our company KPI, an 'active user' has AT LEAST 3 sessions per "
                    "week; N counts users meeting that threshold."
                ],
            ),
            RequirementClass(
                id="avg_rounding",
                description="Rounding rule for the average sessions per user",
                clauses=[
                    "Round the average M to the nearest whole number using ROUND HALF UP "
                    "(ties round up, e.g. 2.5 -> 3), per our reporting standard."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: KPI threshold >=3 + half-up rounding (target, all-target). "
                    "[12,2,2,2,2,0,0,0] -> '1 active | avg 3'."
                ),
                is_target=True,
                gold_check="report_thr3_halfup",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "Partial default: threshold >=3 + half-even rounding "
                    "(avg_rounding defaulted). [12,2,2,2,2,0,0,0] -> '1 active | avg 2'."
                ),
                is_target=False,
                gold_check="report_thr3_halfeven",
                opened_by="avg_rounding",
            ),
            InterpretationBranch(
                id="I2",
                description=(
                    "Partial default: threshold >=1 + half-up rounding "
                    "(active_user_threshold defaulted). [12,2,2,2,2,0,0,0] -> '5 active | avg 3'."
                ),
                is_target=False,
                gold_check="report_thr1_halfup",
                opened_by="active_user_threshold",
            ),
            InterpretationBranch(
                id="I3",
                description=(
                    "MODEL DEFAULT [combined-default]: threshold >=1 + half-even rounding "
                    "(both defaulted). [12,2,2,2,2,0,0,0] -> '5 active | avg 2'."
                ),
                is_target=False,
                gold_check="report_thr1_halfeven",
                opened_by="active_user_threshold,avg_rounding",
            ),
        ],
        key_questions=[
            "What session-count threshold defines an 'active user' (the org KPI)?",
            "Which rounding rule for the average: half-up (ties up) or Python "
            "default half-even?",
        ],
    )


# ============================================================================
# REFERENCE IMPLEMENTATIONS — one per interpretation per family.
# Each reference must pass ONLY its own checker and FAIL all others.
# ============================================================================

REFERENCE_IMPLEMENTATIONS = {
    # -- data_typical_001 (central_tendency axis) -----------------------------
    "typical_median": """
def typical_value(data):
    s = sorted(data)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        med = (s[mid - 1] + s[mid]) / 2.0
    else:
        med = s[mid]
    return f"{med:.2f}"
""",
    "typical_mean": """
def typical_value(data):
    mean = sum(data) / len(data)
    return f"{mean:.2f}"
""",

    # -- data_avgprice_001 (price_weighting axis, H2_derivable) ---------------
    "avgprice_weighted": """
def average_price(items):
    total_cost = sum(q * p for q, p in items)
    total_qty = sum(q for q, p in items)
    return f"{total_cost / total_qty:.2f}"
""",
    "avgprice_simple": """
def average_price(items):
    prices = [p for q, p in items]
    return f"{sum(prices) / len(prices):.2f}"
""",

    # -- data_rate_001 (rate_interval axis, H2_derivable) ---------------------
    "rate_total": """
def avg_rate(series):
    t0, v0 = series[0]
    t1, v1 = series[-1]
    return f"{(v1 - v0) / (t1 - t0):.2f}"
""",
    "rate_stepmean": """
def avg_rate(series):
    deltas = [series[i + 1][1] - series[i][1] for i in range(len(series) - 1)]
    return f"{sum(deltas) / len(deltas):.2f}"
""",

    # -- data_activeusers_001 (active_user_threshold axis) --------------------
    "active_threshold3": """
def count_active(sessions):
    return sum(1 for s in sessions if s >= 3)
""",
    "active_threshold1": """
def count_active(sessions):
    return sum(1 for s in sessions if s >= 1)
""",

    # -- data_report_001 (active_user_threshold + avg_rounding axes) ----------
    "report_thr3_halfup": """
def format_report(sessions):
    from decimal import Decimal, ROUND_HALF_UP
    active = sum(1 for s in sessions if s >= 3)
    mean = Decimal(sum(sessions)) / Decimal(len(sessions))
    avg = int(mean.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return f"{active} active | avg {avg}"
""",
    "report_thr3_halfeven": """
def format_report(sessions):
    active = sum(1 for s in sessions if s >= 3)
    avg = round(sum(sessions) / len(sessions))
    return f"{active} active | avg {avg}"
""",
    "report_thr1_halfup": """
def format_report(sessions):
    from decimal import Decimal, ROUND_HALF_UP
    active = sum(1 for s in sessions if s >= 1)
    mean = Decimal(sum(sessions)) / Decimal(len(sessions))
    avg = int(mean.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return f"{active} active | avg {avg}"
""",
    "report_thr1_halfeven": """
def format_report(sessions):
    active = sum(1 for s in sessions if s >= 1)
    avg = round(sum(sessions) / len(sessions))
    return f"{active} active | avg {avg}"
""",
}


# ============================================================================
# TEST CASES — input/output pairs for each checker.
# Every PAIR of checkers within a family differs on at least one test case.
# ============================================================================

TEST_CASES = {
    # -- data_typical_001 -----------------------------------------------------
    # Datasets where median != mean so the two checkers are disjoint.
    "typical_median": [
        ([2, 4, 4, 4, 5, 5, 7, 900], "4.50"),   # median avg(4,5)=4.50; mean=116.38
        ([1, 2, 3, 4, 100], "3.00"),            # median 3.00; mean 22.00
        ([10, 20, 30, 1000], "25.00"),          # median avg(20,30)=25.00; mean 265.00
    ],
    "typical_mean": [
        ([2, 4, 4, 4, 5, 5, 7, 900], "116.38"),  # mean 931/8=116.375->116.38
        ([1, 2, 3, 4, 100], "22.00"),           # mean 110/5=22.00
        ([10, 20, 30, 1000], "265.00"),         # mean 1060/4=265.00
    ],

    # -- data_avgprice_001 ----------------------------------------------------
    # Datasets where quantity-weighted avg != simple column mean (clear margins).
    # A [[1,10],[1,20],[18,100]]:  weighted 1830/20=91.50; simple 130/3=43.33
    # B [[2,5],[3,10],[5,20]]:     weighted 140/10=14.00;  simple 35/3=11.67
    # C [[10,1],[1,100]]:          weighted 110/11=10.00;  simple 101/2=50.50
    "avgprice_weighted": [
        ([[1, 10.0], [1, 20.0], [18, 100.0]], "91.50"),
        ([[2, 5.0], [3, 10.0], [5, 20.0]], "14.00"),
        ([[10, 1.0], [1, 100.0]], "10.00"),
    ],
    "avgprice_simple": [
        ([[1, 10.0], [1, 20.0], [18, 100.0]], "43.33"),
        ([[2, 5.0], [3, 10.0], [5, 20.0]], "11.67"),
        ([[10, 1.0], [1, 100.0]], "50.50"),
    ],

    # -- data_rate_001 --------------------------------------------------------
    # Datasets with UNEQUAL time gaps where total/elapsed != mean(step deltas).
    # A [[0,0],[1,10],[10,100]]:   total 100/10=10.00; stepmean mean(10,90)=50.00
    # B [[0,100],[2,120],[3,110]]: total 10/3=3.33;    stepmean mean(20,-10)=5.00
    # C [[0,0],[5,50],[6,50]]:     total 50/6=8.33;    stepmean mean(50,0)=25.00
    "rate_total": [
        ([[0, 0], [1, 10], [10, 100]], "10.00"),
        ([[0, 100], [2, 120], [3, 110]], "3.33"),
        ([[0, 0], [5, 50], [6, 50]], "8.33"),
    ],
    "rate_stepmean": [
        ([[0, 0], [1, 10], [10, 100]], "50.00"),
        ([[0, 100], [2, 120], [3, 110]], "5.00"),
        ([[0, 0], [5, 50], [6, 50]], "25.00"),
    ],

    # -- data_activeusers_001 -------------------------------------------------
    # Datasets where count>=3 != count>=1 so the two checkers are disjoint.
    "active_threshold3": [
        ([5, 3, 1, 4, 2, 3, 0, 6, 1, 2], 5),
        ([3, 3, 2, 1, 0], 2),
        ([1, 2, 3], 1),
    ],
    "active_threshold1": [
        ([5, 3, 1, 4, 2, 3, 0, 6, 1, 2], 9),
        ([3, 3, 2, 1, 0], 4),
        ([1, 2, 3], 3),
    ],

    # -- data_report_001 ------------------------------------------------------
    # Two datasets; mean is a '.5' tie with EVEN integer part (half-up != half-even),
    # and count>=3 != count>=1. All 4 checkers pairwise distinct on both datasets.
    # DS1 [12,2,2,2,2,0,0,0]: N>=3=1, N>=1=5, mean=2.5 -> halfup 3, halfeven 2
    # DS2 [14,14,2,2,2,2,0,0]: N>=3=2, N>=1=6, mean=4.5 -> halfup 5, halfeven 4
    "report_thr3_halfup": [
        ([12, 2, 2, 2, 2, 0, 0, 0], "1 active | avg 3"),
        ([14, 14, 2, 2, 2, 2, 0, 0], "2 active | avg 5"),
    ],
    "report_thr3_halfeven": [
        ([12, 2, 2, 2, 2, 0, 0, 0], "1 active | avg 2"),
        ([14, 14, 2, 2, 2, 2, 0, 0], "2 active | avg 4"),
    ],
    "report_thr1_halfup": [
        ([12, 2, 2, 2, 2, 0, 0, 0], "5 active | avg 3"),
        ([14, 14, 2, 2, 2, 2, 0, 0], "6 active | avg 5"),
    ],
    "report_thr1_halfeven": [
        ([12, 2, 2, 2, 2, 0, 0, 0], "5 active | avg 2"),
        ([14, 14, 2, 2, 2, 2, 0, 0], "6 active | avg 4"),
    ],
}


# ============================================================================
# CHECKERS REGISTRY
# ============================================================================

ENTRYPOINTS = {
    # k=1 family: central tendency
    "typical_median":       "typical_value",
    "typical_mean":         "typical_value",
    # k=1 family: quantity-weighted average price (H2_derivable)
    "avgprice_weighted":    "average_price",
    "avgprice_simple":      "average_price",
    # k=1 family: unequal-interval rate of change (H2_derivable)
    "rate_total":           "avg_rate",
    "rate_stepmean":        "avg_rate",
    # k=1 family: active-user threshold
    "active_threshold3":    "count_active",
    "active_threshold1":    "count_active",
    # k=2 family: threshold x avg-rounding
    "report_thr3_halfup":   "format_report",
    "report_thr3_halfeven": "format_report",
    "report_thr1_halfup":   "format_report",
    "report_thr1_halfeven": "format_report",
}

CHECKERS = {}
for _check_id, _test_cases in TEST_CASES.items():
    _entrypoint = ENTRYPOINTS[_check_id]
    CHECKERS[_check_id] = DataChecker(
        _test_cases, entrypoint=_entrypoint, description=_check_id
    )


# ============================================================================
# TASK GENERATION
# ============================================================================

def generate_tasks() -> List[Task]:
    """Generate all 12 data_analysis tasks (Amendment 03 combinatorial invariant).

    Amended invariant per variant (enforced by post-generation assertion):
        len(key_questions) == k'       (deleted-axis count)
        len(interpretations) == 2^k'   (full combinatorial set)
        I0 = all-target; combined-all-default marked [combined-default]
        k0 control: prompt==latent_spec, 1 interp, empty key_questions.

    Task count:
        4 k=1 families x 2 variants  =  8
        1 k=2 family   x 4 variants  =  4
        Total                        = 12

    The 4 k=1 families are 3 H2_derivable (central_tendency, price_weighting,
    rate_interval) + 1 H1_external (active_user_threshold); the k=2 family is
    H1_external (active_user_threshold x avg_rounding).
    """
    tasks = []

    # -- k=1 single-axis families ---------------------------------------------
    k1_defs = [
        (problem_typical_value(), [
            ("_k0", []),
            ("_k1_central_tendency", ["central_tendency"]),
        ]),
        (problem_avg_price(), [
            ("_k0", []),
            ("_k1_price_weighting", ["price_weighting"]),
        ]),
        (problem_avg_rate(), [
            ("_k0", []),
            ("_k1_rate_interval", ["rate_interval"]),
        ]),
        (problem_active_users(), [
            ("_k0", []),
            ("_k1_active_user_threshold", ["active_user_threshold"]),
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

    # -- k=2 family: data_report_001 ------------------------------------------
    rep_spec = problem_activity_report()
    rep_qmap = {
        rc.id: q
        for rc, q in zip(rep_spec.requirement_classes, rep_spec.key_questions)
    }
    for suffix, delete_ids in [
        ("_k0",                        []),
        ("_k1_active_user_threshold",  ["active_user_threshold"]),
        ("_k1_avg_rounding",           ["avg_rounding"]),
        ("_k2_all",                    ["active_user_threshold", "avg_rounding"]),
    ]:
        spec_copy = FullSpec(
            domain=rep_spec.domain,
            task_id=rep_spec.task_id + suffix,
            prompt_core=rep_spec.prompt_core,
            requirement_classes=rep_spec.requirement_classes[:],
            interpretations=rep_spec.interpretations[:],
            key_questions=rep_spec.key_questions[:],
            regime=rep_spec.regime,
        )
        task = assemble_task(
            spec_copy, k=len(delete_ids),
            classes_to_delete=delete_ids if delete_ids else None,
        )
        task.key_questions = [rep_qmap[cid] for cid in delete_ids]
        tasks.append(task)

    # -- Post-generation amended-invariant gate (fail fast) -------------------
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
        if t.regime not in ("H1_external", "H2_derivable"):
            raise AssertionError(f"{t.id}: reconstructed task must carry a regime tag")
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
# FOILS (near-miss adversarial candidates) — each matches AT MOST ONE checker
# ============================================================================

def get_task_specific_foils(task_id_base: str) -> List[str]:
    """Near-miss foils for each problem family (task_id_base = prefix before '_k')."""

    if task_id_base == "data_typical_001":
        return [
            # Mode (most frequent value): 4.00 on the primary dataset; 0 matches
            """
def typical_value(data):
    from collections import Counter
    mode = Counter(data).most_common(1)[0][0]
    return f"{mode:.2f}"
""",
            # Minimum value; 0 matches
            """
def typical_value(data):
    return f"{min(data):.2f}"
""",
            # Median but WITHOUT rounding to 2 decimals (format mismatch); 0 matches
            """
def typical_value(data):
    s = sorted(data)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return str((s[mid - 1] + s[mid]) / 2.0)
    return str(s[mid])
""",
        ]

    elif task_id_base == "data_avgprice_001":
        return [
            # Total spent (no division at all); matches 0
            """
def average_price(items):
    return f"{sum(q * p for q, p in items):.2f}"
""",
            # Weighted total divided by NUMBER OF RECORDS (not total qty); matches 0
            """
def average_price(items):
    total = sum(q * p for q, p in items)
    return f"{total / len(items):.2f}"
""",
            # Quantity-weighted average WITHOUT the 2-decimal format (str); matches 0
            """
def average_price(items):
    total_cost = sum(q * p for q, p in items)
    total_qty = sum(q for q, p in items)
    return str(total_cost / total_qty)
""",
        ]

    elif task_id_base == "data_rate_001":
        return [
            # Total change WITHOUT dividing by elapsed time; matches 0
            """
def avg_rate(series):
    return f"{series[-1][1] - series[0][1]:.2f}"
""",
            # Mean of per-step RATES (delta_v/delta_t); differs from both golds
            # across the datasets (accidental single-dataset hits cancel out); matches 0
            """
def avg_rate(series):
    rates = [(series[i + 1][1] - series[i][1]) / (series[i + 1][0] - series[i][0])
             for i in range(len(series) - 1)]
    return f"{sum(rates) / len(rates):.2f}"
""",
            # Total change divided by NUMBER OF POINTS (not elapsed time); matches 0
            """
def avg_rate(series):
    change = series[-1][1] - series[0][1]
    return f"{change / len(series):.2f}"
""",
        ]

    elif task_id_base == "data_activeusers_001":
        return [
            # Threshold >=2 (neither KPI nor any-activity); 0 matches
            """
def count_active(sessions):
    return sum(1 for s in sessions if s >= 2)
""",
            # Threshold >=5; 0 matches
            """
def count_active(sessions):
    return sum(1 for s in sessions if s >= 5)
""",
            # Total sessions instead of count of users; 0 matches
            """
def count_active(sessions):
    return sum(sessions)
""",
        ]

    elif task_id_base == "data_report_001":
        return [
            # One-decimal average (format mismatch on M); 0 matches
            """
def format_report(sessions):
    active = sum(1 for s in sessions if s >= 3)
    mean = sum(sessions) / len(sessions)
    return f"{active} active | avg {mean:.1f}"
""",
            # Wrong separator (semicolon instead of pipe); 0 matches
            """
def format_report(sessions):
    from decimal import Decimal, ROUND_HALF_UP
    active = sum(1 for s in sessions if s >= 3)
    mean = Decimal(sum(sessions)) / Decimal(len(sessions))
    avg = int(mean.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return f"{active} active ; avg {avg}"
""",
            # N = number of users (len) instead of active count; 0 matches
            """
def format_report(sessions):
    from decimal import Decimal, ROUND_HALF_UP
    mean = Decimal(sum(sessions)) / Decimal(len(sessions))
    avg = int(mean.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return f"{len(sessions)} active | avg {avg}"
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
    output_path = Path(__file__).parent.parent / "data" / "data_analysis.jsonl"
    output_path.parent.mkdir(exist_ok=True)
    save_tasks(tasks, str(output_path))

    print(f"Generated {len(tasks)} data_analysis tasks -> {output_path}")
    levels = {k: sum(1 for t in tasks if t.ambiguity_level == k) for k in range(4)}
    print(f"Ambiguity distribution: {levels}")
    regimes = {}
    for t in tasks:
        r = t.regime if t.regime else "None"
        regimes[r] = regimes.get(r, 0) + 1
    print(f"Regime distribution: {regimes}")
