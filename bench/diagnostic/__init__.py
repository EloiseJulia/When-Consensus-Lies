# constructed by: Claude (Anthropic) family
"""DIAGNOSTIC (EXPLORATORY) subtler-trap fixture — SEPARATE from the registered benchmark.

These tasks are the instrument for the O2 CD-saturation disambiguation (see
paper/plans/2026-07-16-default-check-diagnostic-plan.md). They are DELIBERATELY SUBTLER
reversed traps: each keeps the reversed property (I0 = NON-default true intent stated by
the full latent_spec; the [combined-default] foil = the model's natural default, which is
WRONG), executable gold, 100% distinguishability, a regime tag, and fairness (a human
reading the full latent_spec agrees the non-default is genuinely intended) — but with a
WEAKER default-pull than the corresponding STRONG benchmark trap, so a discriminating
convergent_delusion should land STRICTLY BETWEEN 0 and 1 rather than saturating at 1.0.

IMPORTANT provenance / scope guarantees:
  - These are NOT written into bench/data/*.jsonl (the registered benchmark). They are a
    diagnostic fixture only, pending the saturation finding + a later full audit if promoted.
  - Tasks keep their REAL domain ("code_spec" / "data_analysis") so harness.run's
    answer_format_instruction still asks agents for a single ```python code block, but their
    ids are prefixed "diag_" so a custom label_run_fn can route them here without touching
    the frozen harness/label.py.
  - Executable gold reuses the hardened, isolated subprocess checkers from the domain
    packages (CodeChecker / DataChecker) — NO new _runner is needed.

Why each subtler trap's default-pull is weaker than its strong counterpart:
  diag_weekday_001    (vs code_quarter):  BOTH weekday conventions are pervasive
      (Python isoweekday() Monday-first vs Excel WEEKDAY / US calendars Sunday-first),
      so a meaningful minority of models independently picks each → the default is not a
      near-universal single choice.
  diag_unique_001     (vs code_getitems): "return the unique items" genuinely splits
      between sorted(set(...)) and order-preserving dict.fromkeys(...) (and unordered
      list(set(...)) → I_perp), so no single dominant default.
  diag_avgnonzero_001 (vs data_activeusers): the strong trap uses an ARBITRARY external KPI
      threshold no model guesses; here both "per user" (÷len) and "per active user"
      (÷nonzero) are natural readings of "average sessions", a much weaker default.
  diag_stddev_001     (vs data_activeusers): sample (n-1) vs population (n) std is a classic
      genuine split (numpy ddof=0 vs pandas/statistics.stdev n-1) → weak default.
"""

from typing import Any, Dict, List, Optional, Tuple

from bench.build import FullSpec, InterpretationBranch, RequirementClass, assemble_task
from bench.code_spec import CodeChecker
from bench.data_analysis import DataChecker
from bench.gold.base import GoldChecker
from common.schema import Task

# Reuse the frozen executable-signal extractor so diagnostic labeling mirrors the
# real domain labelers exactly (code fence / raw code extraction).
from harness.label import _extract_code_from_output


# Diagnostic task ids all carry this prefix so a driver can route labeling here
# without modifying harness/label.py (which is dispatch-by-domain).
DIAG_PREFIX = "diag_"


# ============================================================================
# SUBTLER-TRAP PROBLEM LIBRARY (each a k=1 reversed trap: I0 + [combined-default])
# ============================================================================

def problem_weekday():
    """code_spec subtler trap: weekday numbering convention.

    Target I0 = US business calendar (Sunday=1..Saturday=7). Default foil = ISO-8601
    (Monday=1..Sunday=7, i.e. Python's isoweekday()). SUBTLER because both conventions
    are pervasive in the wild, unlike the strong `code_quarter` trap where calendar
    quarters are a near-universal single default.
    """
    return FullSpec(
        domain="code_spec",
        task_id="diag_weekday_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `day_number(day_name)` that returns the integer "
            "day-of-week number for a full English weekday name such as 'Monday' or "
            "'Sunday'."
        ),
        requirement_classes=[
            RequirementClass(
                id="week_start_convention",
                description="Which day is day 1 of the week",
                clauses=[
                    "Use the US business-calendar convention where the week STARTS ON "
                    "SUNDAY: Sunday=1, Monday=2, Tuesday=3, Wednesday=4, Thursday=5, "
                    "Friday=6, Saturday=7."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: US Sunday-first 1-based numbering (target). "
                    "'Sunday'->1, 'Monday'->2, 'Saturday'->7."
                ),
                is_target=True,
                gold_check="weekday_us_sunday",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: ISO-8601 Monday-first numbering "
                    "(Python isoweekday). 'Monday'->1, 'Sunday'->7."
                ),
                is_target=False,
                gold_check="weekday_iso_monday",
                opened_by="week_start_convention",
            ),
        ],
        key_questions=[
            "Which day is day 1 of the week (Sunday per US business calendar, or Monday "
            "per ISO-8601)?",
        ],
    )


def problem_unique():
    """code_spec subtler trap: unique-elements ordering convention.

    Target I0 = first-occurrence (insertion) order. Default foil = sorted ascending.
    SUBTLER because "return the unique items" genuinely splits between sorted(set(...))
    and order-preserving dict.fromkeys(...) in the wild.
    """
    return FullSpec(
        domain="code_spec",
        task_id="diag_unique_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `unique(items)` that takes a list and returns a list of "
            "its unique elements with duplicates removed."
        ),
        requirement_classes=[
            RequirementClass(
                id="ordering_convention",
                description="Ordering of the returned unique elements",
                clauses=[
                    "Preserve FIRST-OCCURRENCE order: list each distinct element in the "
                    "order it first appears in the input (do NOT sort)."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: first-occurrence (insertion) order (target). "
                    "[3,1,2,1,3,2]->[3,1,2]."
                ),
                is_target=True,
                gold_check="unique_insertion_order",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: sorted ascending. "
                    "[3,1,2,1,3,2]->[1,2,3]."
                ),
                is_target=False,
                gold_check="unique_sorted",
                opened_by="ordering_convention",
            ),
        ],
        key_questions=[
            "In what order should the unique elements be returned (first-occurrence "
            "order, or sorted)?",
        ],
    )


def problem_avg_nonzero():
    """data_analysis subtler trap: average basis (active users only vs all users).

    Target I0 = average over NON-zero (active) users only. Default foil = average over
    all users (sum/len). SUBTLER because both are natural readings of "average sessions",
    unlike the strong `data_activeusers` trap whose >=3 KPI threshold is arbitrary/external.
    """
    return FullSpec(
        domain="data_analysis",
        task_id="diag_avgnonzero_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `average_sessions(sessions)` that returns the average "
            "number of sessions per user for the dataset [5, 0, 3, 0, 4, 0, 2, 2], as a "
            "string rounded to 2 decimal places."
        ),
        requirement_classes=[
            RequirementClass(
                id="average_basis",
                description="Which users are counted in the average",
                clauses=[
                    "Compute the average over ACTIVE users ONLY — exclude users with zero "
                    "sessions from BOTH the numerator and the denominator."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: mean over non-zero (active) users (target). "
                    "[5,0,3,0,4,0,2,2] -> 16/5 -> '3.20'."
                ),
                is_target=True,
                gold_check="avg_nonzero",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: mean over ALL users. "
                    "[5,0,3,0,4,0,2,2] -> 16/8 -> '2.00'."
                ),
                is_target=False,
                gold_check="avg_all",
                opened_by="average_basis",
            ),
        ],
        key_questions=[
            "Is the average taken over active (non-zero) users only, or over all users?",
        ],
    )


def problem_stddev():
    """data_analysis subtler trap: sample vs population standard deviation.

    Target I0 = SAMPLE std (Bessel's correction, ÷ n-1). Default foil = POPULATION std
    (÷ n). SUBTLER: this is a classic genuine split (numpy ddof=0 vs pandas/statistics.stdev
    n-1), so the default is far weaker than an external policy threshold.
    """
    return FullSpec(
        domain="data_analysis",
        task_id="diag_stddev_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `spread(data)` that returns the standard deviation of the "
            "dataset [2, 4, 4, 4, 5, 5, 7, 9], as a string rounded to 2 decimal places."
        ),
        requirement_classes=[
            RequirementClass(
                id="stddev_estimator",
                description="Sample vs population standard deviation",
                clauses=[
                    "Use the SAMPLE standard deviation (Bessel's correction: divide the "
                    "sum of squared deviations by n-1), treating the data as a sample."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default: sample std, ÷ (n-1) (target). "
                    "[2,4,4,4,5,5,7,9] -> '2.14'."
                ),
                is_target=True,
                gold_check="std_sample",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: population std, ÷ n. "
                    "[2,4,4,4,5,5,7,9] -> '2.00'."
                ),
                is_target=False,
                gold_check="std_population",
                opened_by="stddev_estimator",
            ),
        ],
        key_questions=[
            "Sample standard deviation (÷ n-1) or population standard deviation (÷ n)?",
        ],
    )


# ============================================================================
# REFERENCE IMPLEMENTATIONS — each passes ONLY its own checker.
# ============================================================================

REFERENCE_IMPLEMENTATIONS: Dict[str, str] = {
    # -- diag_weekday_001 -----------------------------------------------------
    "weekday_us_sunday": """
def day_number(day_name):
    order = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    return order.index(day_name) + 1
""",
    "weekday_iso_monday": """
def day_number(day_name):
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return order.index(day_name) + 1
""",

    # -- diag_unique_001 ------------------------------------------------------
    "unique_insertion_order": """
def unique(items):
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
""",
    "unique_sorted": """
def unique(items):
    return sorted(set(items))
""",

    # -- diag_avgnonzero_001 --------------------------------------------------
    "avg_nonzero": """
def average_sessions(sessions):
    nz = [s for s in sessions if s != 0]
    return f"{sum(nz) / len(nz):.2f}"
""",
    "avg_all": """
def average_sessions(sessions):
    return f"{sum(sessions) / len(sessions):.2f}"
""",

    # -- diag_stddev_001 ------------------------------------------------------
    "std_sample": """
def spread(data):
    import statistics
    return f"{statistics.stdev(data):.2f}"
""",
    "std_population": """
def spread(data):
    import statistics
    return f"{statistics.pstdev(data):.2f}"
""",
}


# ============================================================================
# TEST CASES — every pair within a family differs on EVERY listed case.
# ============================================================================

TEST_CASES: Dict[str, List[Tuple[Any, Any]]] = {
    # -- diag_weekday_001 (input is a single string arg) ----------------------
    "weekday_us_sunday": [
        ("Sunday", 1), ("Monday", 2), ("Wednesday", 4), ("Saturday", 7),
    ],
    "weekday_iso_monday": [
        ("Sunday", 7), ("Monday", 1), ("Wednesday", 3), ("Saturday", 6),
    ],

    # -- diag_unique_001 (input is a single list arg) -------------------------
    "unique_insertion_order": [
        ([3, 1, 2, 1, 3, 2], [3, 1, 2]),
        ([5, 5, 4, 6, 4], [5, 4, 6]),
    ],
    "unique_sorted": [
        ([3, 1, 2, 1, 3, 2], [1, 2, 3]),
        ([5, 5, 4, 6, 4], [4, 5, 6]),
    ],

    # -- diag_avgnonzero_001 --------------------------------------------------
    "avg_nonzero": [
        ([5, 0, 3, 0, 4, 0, 2, 2], "3.20"),
        ([10, 0, 0, 0, 0], "10.00"),
        ([4, 4, 0, 0], "4.00"),
    ],
    "avg_all": [
        ([5, 0, 3, 0, 4, 0, 2, 2], "2.00"),
        ([10, 0, 0, 0, 0], "2.00"),
        ([4, 4, 0, 0], "2.00"),
    ],

    # -- diag_stddev_001 ------------------------------------------------------
    "std_sample": [
        ([2, 4, 4, 4, 5, 5, 7, 9], "2.14"),
        ([1, 2, 3, 4, 5], "1.58"),
    ],
    "std_population": [
        ([2, 4, 4, 4, 5, 5, 7, 9], "2.00"),
        ([1, 2, 3, 4, 5], "1.41"),
    ],
}


ENTRYPOINTS: Dict[str, str] = {
    "weekday_us_sunday": "day_number",
    "weekday_iso_monday": "day_number",
    "unique_insertion_order": "unique",
    "unique_sorted": "unique",
    "avg_nonzero": "average_sessions",
    "avg_all": "average_sessions",
    "std_sample": "spread",
    "std_population": "spread",
}

# Code-domain checkers use CodeChecker; data-domain checkers use DataChecker.
# (Both are isolated-subprocess executable-gold checkers reused from the domain
# packages — see their module docstrings for the threat model.)
_CODE_CHECKS = {"weekday_us_sunday", "weekday_iso_monday",
                "unique_insertion_order", "unique_sorted"}

CHECKERS: Dict[str, GoldChecker] = {}
for _check_id, _cases in TEST_CASES.items():
    _entry = ENTRYPOINTS[_check_id]
    _cls = CodeChecker if _check_id in _CODE_CHECKS else DataChecker
    # Namespace the description so the domain checkers' module-level result caches
    # never collide with a real-benchmark checker of the same shape.
    CHECKERS[_check_id] = _cls(_cases, entrypoint=_entry, description="diag_" + _check_id)


# ============================================================================
# ADVERSARIAL FOILS (must match AT MOST ONE checker) — disjointness defense.
# ============================================================================

def get_task_specific_foils(task_id_base: str) -> List[str]:
    if task_id_base == "diag_weekday_001":
        return [
            # 0-based Sunday-first (off-by-one): matches neither; 0 checkers.
            """
def day_number(day_name):
    order = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    return order.index(day_name)
""",
            # Constant; 0 checkers.
            """
def day_number(day_name):
    return 1
""",
        ]
    if task_id_base == "diag_unique_001":
        return [
            # Reversed-order unique; 0 checkers.
            """
def unique(items):
    seen = set()
    out = []
    for x in reversed(items):
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
""",
            # Sorted descending; 0 checkers.
            """
def unique(items):
    return sorted(set(items), reverse=True)
""",
        ]
    if task_id_base == "diag_avgnonzero_001":
        return [
            # Median instead of a mean; 0 checkers.
            """
def average_sessions(sessions):
    s = sorted(sessions)
    n = len(s)
    m = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0
    return f"{m:.2f}"
""",
            # Unrounded mean-of-all (format mismatch); 0 checkers.
            """
def average_sessions(sessions):
    return str(sum(sessions) / len(sessions))
""",
        ]
    if task_id_base == "diag_stddev_001":
        return [
            # Variance (not std); 0 checkers.
            """
def spread(data):
    import statistics
    return f"{statistics.pvariance(data):.2f}"
""",
            # Range instead of std; 0 checkers.
            """
def spread(data):
    return f"{max(data) - min(data):.2f}"
""",
        ]
    return ["def _f():\n    raise NotImplementedError()"]


# ============================================================================
# TASK GENERATION + CHECKER/CANDIDATE LOADING + LABELING
# ============================================================================

_PROBLEMS = [problem_weekday, problem_unique, problem_avg_nonzero, problem_stddev]


def generate_tasks() -> List[Task]:
    """Generate the 4 diagnostic subtler-trap Tasks (each k=1, 2 interpretations).

    Enforces the same per-variant invariant as the real domains:
      len(key_questions) == 1, len(interpretations) == 2^1 == 2, exactly one target I0,
      exactly one [combined-default] foil (marked __combdef by assemble_task).
    """
    tasks: List[Task] = []
    for factory in _PROBLEMS:
        spec = factory()
        delete_id = spec.requirement_classes[0].id
        task = assemble_task(spec, k=1, classes_to_delete=[delete_id])
        tasks.append(task)

    for t in tasks:
        if len(t.interpretations) != 2:
            raise AssertionError(f"{t.id}: expected 2 interpretations, got {len(t.interpretations)}")
        if len(t.key_questions) != 1:
            raise AssertionError(f"{t.id}: expected 1 key_question, got {len(t.key_questions)}")
        targets = [i for i in t.interpretations if i.is_target]
        if len(targets) != 1 or targets[0].id != "I0":
            raise AssertionError(f"{t.id}: must have exactly one target I0")
        combdef = sum(1 for i in t.interpretations if i.gold_check.endswith("__combdef"))
        if combdef != 1:
            raise AssertionError(f"{t.id}: expected exactly 1 __combdef foil, got {combdef}")
    return tasks


def _base_id(task: Task) -> str:
    return task.id.split("_k")[0] if "_k" in task.id else task.id


def get_checkers_and_candidates(task: Task) -> Tuple[
    Dict[str, GoldChecker], Dict[str, Any], List[Any]
]:
    """Return (checkers, reference-candidates, near-miss-foils) for a diagnostic task."""
    checkers: Dict[str, GoldChecker] = {}
    candidates: Dict[str, Any] = {}
    for interp in task.interpretations:
        check_id = interp.gold_check
        if check_id.endswith("__combdef"):
            check_id = check_id[: -len("__combdef")]
        if check_id not in CHECKERS:
            raise ValueError(f"Unknown diagnostic checker: {check_id}")
        checkers[interp.id] = CHECKERS[check_id]
        candidates[interp.id] = REFERENCE_IMPLEMENTATIONS[check_id]
    foils = get_task_specific_foils(_base_id(task))
    return checkers, candidates, foils


def is_diagnostic_task(task: Task) -> bool:
    """True iff *task* is one of the diagnostic subtler-trap tasks."""
    return task.id.startswith(DIAG_PREFIX)


def label_diagnostic(run: Any, task: Task) -> str:
    """Executable-gold label for a diagnostic task (NEVER an LLM judge).

    Mirrors harness.label.label_code_domain / label_data_domain: extract the candidate
    code from run.output, run it through EACH interpretation's gold checker, and return
    the interpretation id whose checker UNIQUELY passes, else "I_perp".
    """
    candidate_code = _extract_code_from_output(run.output)
    if candidate_code is None:
        return "I_perp"
    checkers, _, _ = get_checkers_and_candidates(task)
    passed = []
    for interp in task.interpretations:
        if interp.id == "I_perp":
            continue
        checker = checkers.get(interp.id)
        if checker is None:
            continue
        if checker.check(candidate_code).passed:
            passed.append(interp.id)
    if len(passed) == 1:
        return passed[0]
    return "I_perp"
