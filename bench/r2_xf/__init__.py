# constructed by: Anthropic claude-opus-4.8 (SECOND constructor family, Amendment 10)
"""R2 cross-family construction subset — Anthropic claude-opus-4.8-constructed items.

Implements SIGNED pre-registration Amendment 10 (R2 cross-family construction
control). Every item in this module was DESIGNED by the Anthropic
``claude-opus-4.8`` constructor family, so it carries
``constructor_family="anthropic/claude-opus-4.8"`` (derived additively in
``analysis/io.py`` from the ``r2xf_`` task-id prefix — NO edit to the frozen
``common/schema.py``). The main benchmark is mai-code-constructed; this subset
supplies the SECOND independent constructor family R2 needs.

Design (H1_external, "hidden-convention trap" — mirrors the main benchmark's
genuine H1 mechanic, e.g. ``code_quarter_001`` fiscal-April quarters):
  - I0 (TARGET, is_target=True) = the NON-obvious interpretation that depends on
    an EXTERNAL / hidden convention or fact NOT present in the retained prompt
    (e.g. "integer division truncates toward zero, per the C/SQL spec"). A
    reasonable UNAWARE solver — lacking the external fact — does NOT produce it.
  - The FOIL (is_target=False, the [combined-default] branch) = the NATURAL
    DEFAULT a language-native / unaware solver writes (e.g. Python ``a // b``
    floor division). Deleting the disambiguating clause LEAVES this default as
    what a solver produces, so unaware models CONVERGE on the foil → the
    convergent-delusion trap fires (high cd_primary over the non-target foil).
  - The disambiguator is genuinely EXTERNAL: NOTHING in the retained prompt lets
    a capable model derive the target (that would make it H2_derivable). The
    prompt_core is deliberately generic; the external convention lives ONLY in
    the deleted requirement-class clause.
  - The TARGET's gold computes the external-convention answer; the FOIL's gold
    computes the natural default. Deterministic executable-gold ``check()``; I0
    uniquely identifiable; enumerated foils; cross-family-FAIR (not tuned to any
    single tested family). Axes are DISTINCT from the main benchmark's families.
  - k in {0, 1}: a k0 control (EMPTY key_questions, prompt==latent_spec) and a
    k1 trap. Amdt-03 per-variant invariant holds:
        len(key_questions) == ambiguity_level == len(interpretations) - 1
    (binary axis => for k=1 exactly one foil, marked [combined-default] via the
    __combdef gold_check suffix appended by bench.build.assemble_task).

Domain flavors (task.domain is set to the REAL host flavor so the harness
answer-format instruction AND the executable label dispatch in harness/label.py
route correctly):
  - code_spec     : Python-function items scored by the host CodeChecker.
  - data_analysis : data-processing items scored by the host DataChecker.
  - policy_qa     : structured numeric {"amount": <float>} items scored by the
                    host StructuredAnswerChecker.

Live-run labeling (ADDITIVE, NO frozen file edited): harness/label.py dispatches
by task.domain to the host domain's ``get_checkers_and_candidates``, which
resolves interpretation ``gold_check`` ids in that host module's CHECKERS dict.
To make this executable-gold path work for the r2_xf items WITHOUT editing any
frozen source file, ``_register_into_host_domains()`` (run once at import)
inserts this module's DISJOINT ``r2xf_``-prefixed checker ids + reference
candidates into the host modules' in-memory registries. This:
  - edits NO source file (the host .py files stay byte-identical),
  - uses ids disjoint from all host ids (no overwrite/collision),
  - only activates when bench.r2_xf is imported (i.e. only for the explicit
    ``--domains r2_xf`` R2 partition; the default confirmatory grid never
    imports this module).
"""

from typing import Any, Dict, List, Tuple

from bench.build import (
    FullSpec,
    InterpretationBranch,
    RequirementClass,
    assemble_task,
    save_tasks,
)
from bench.gold.base import GoldChecker
from common.schema import Task

# Host checker classes (reused; host registries extended additively, never edited).
from bench.code_spec import CodeChecker
from bench.data_analysis import DataChecker
from bench.policy_qa import StructuredAnswerChecker


# ============================================================================
# EXECUTABLE-GOLD SPECS — one deterministic checker per interpretation.
#
# TARGET (I0)  gold = the EXTERNAL / hidden convention (what the deleted clause
#                     asks for; an unaware solver does NOT produce it).
# FOIL         gold = the NATURAL DEFAULT a language-native / unaware solver
#                     writes once the clause is deleted (convergence target).
#
# Each entry: id -> dict with
#   kind        : "code" | "data" | "policy"
#   entrypoint  : function name (code/data only)
#   test_cases  : [(input, expected), ...] (code/data only)
#   expected    : reference structured answer (policy only)
#   candidate   : reference solution (code string, or {"amount": float} dict)
# All ids are r2xf_-prefixed => disjoint from every host-domain checker id.
# ============================================================================

# ── Family 1 (code_spec): integer-division rounding direction ────────────────
# TARGET (external): truncate toward zero (C / SQL / many APIs) -> -7 // 2 = -3.
# FOIL   (default) : Python's native floor division `a // b`     -> -7 // 2 = -4.
_INTDIV_CASES_TRUNC = [((-7, 2), -3), ((7, 2), 3), ((-8, 3), -2), ((-9, 4), -2)]
_INTDIV_CASES_FLOOR = [((-7, 2), -4), ((7, 2), 3), ((-8, 3), -3), ((-9, 4), -3)]

# ── Family 2 (code_spec): weekday numbering convention ───────────────────────
# TARGET (external): ISO 8601 weekday, Monday=1 .. Sunday=7  (date.isoweekday()).
# FOIL   (default) : Python's native date.weekday(), Monday=0 .. Sunday=6.
_WD_CASES_ISO = [((2023, 1, 2), 1), ((2023, 1, 1), 7), ((2023, 1, 4), 3)]
_WD_CASES_PY = [((2023, 1, 2), 0), ((2023, 1, 1), 6), ((2023, 1, 4), 2)]

# ── Family 3 (data_analysis): position-index base for a reported location ─────
# TARGET (external): 1-based row/position number (report/spreadsheet convention).
# FOIL   (default) : 0-based Python list index (list.index()).
_ARGMAX_DATA = [3, 7, 2, 9, 4]                  # max value 9 at 0-based index 3

# ── Family 4 (data_analysis): sort order for numeric-string ids ──────────────
# TARGET (external): NUMERIC order (catalog spec) -> ['1','2','3','10','21'].
# FOIL   (default) : Python-native lexicographic sorted() -> ['1','10','2','21','3'].
_SORTIDS_DATA = ["10", "2", "1", "21", "3"]
_SORTIDS_NUMERIC = sorted(_SORTIDS_DATA, key=int)
_SORTIDS_LEX = sorted(_SORTIDS_DATA)

# ── Family 5 (policy_qa): day-count inclusivity ──────────────────────────────
# TARGET (external): INCLUSIVE count, both endpoints (leave policy) -> 8.
# FOIL   (default) : exclusive arithmetic span end - start (10 - 3)  -> 7.

# ── Family 6 (policy_qa): meaning of "weeks" in a deadline ───────────────────
# TARGET (external): BUSINESS weeks = 5 working days each (SLA) -> 2 weeks = 10.
# FOIL   (default) : calendar weeks = 7 days each -> 2 weeks = 14.


CHECK_SPECS: Dict[str, Dict[str, Any]] = {
    # -- Family 1: integer-division rounding ------------------------------------
    "r2xf_intdiv_trunc": {  # TARGET (external: truncate toward zero)
        "kind": "code",
        "entrypoint": "int_divide",
        "test_cases": _INTDIV_CASES_TRUNC,
        "candidate": (
            "def int_divide(a, b):\n"
            "    q = abs(a) // abs(b)\n"
            "    return q if (a < 0) == (b < 0) else -q\n"
        ),
    },
    "r2xf_intdiv_floor": {  # FOIL (default: Python floor //)
        "kind": "code",
        "entrypoint": "int_divide",
        "test_cases": _INTDIV_CASES_FLOOR,
        "candidate": "def int_divide(a, b):\n    return a // b\n",
    },
    # -- Family 2: weekday numbering --------------------------------------------
    "r2xf_weekday_iso": {  # TARGET (external: ISO Monday=1)
        "kind": "code",
        "entrypoint": "weekday_number",
        "test_cases": _WD_CASES_ISO,
        "candidate": (
            "import datetime\n"
            "def weekday_number(year, month, day):\n"
            "    return datetime.date(year, month, day).isoweekday()\n"
        ),
    },
    "r2xf_weekday_py": {  # FOIL (default: Python .weekday() Monday=0)
        "kind": "code",
        "entrypoint": "weekday_number",
        "test_cases": _WD_CASES_PY,
        "candidate": (
            "import datetime\n"
            "def weekday_number(year, month, day):\n"
            "    return datetime.date(year, month, day).weekday()\n"
        ),
    },
    # -- Family 3: reported position base ---------------------------------------
    "r2xf_argmax_1based": {  # TARGET (external: 1-based position)
        "kind": "data",
        "entrypoint": "max_position",
        "test_cases": [(_ARGMAX_DATA, 4)],
        "candidate": (
            "def max_position(data):\n"
            "    return data.index(max(data)) + 1\n"
        ),
    },
    "r2xf_argmax_0based": {  # FOIL (default: 0-based Python index)
        "kind": "data",
        "entrypoint": "max_position",
        "test_cases": [(_ARGMAX_DATA, 3)],
        "candidate": (
            "def max_position(data):\n"
            "    return data.index(max(data))\n"
        ),
    },
    # -- Family 4: numeric vs lexicographic id sort -----------------------------
    "r2xf_sortids_numeric": {  # TARGET (external: numeric order)
        "kind": "data",
        "entrypoint": "sort_ids",
        "test_cases": [(_SORTIDS_DATA, _SORTIDS_NUMERIC)],
        "candidate": (
            "def sort_ids(ids):\n"
            "    return sorted(ids, key=int)\n"
        ),
    },
    "r2xf_sortids_lex": {  # FOIL (default: lexicographic sorted())
        "kind": "data",
        "entrypoint": "sort_ids",
        "test_cases": [(_SORTIDS_DATA, _SORTIDS_LEX)],
        "candidate": (
            "def sort_ids(ids):\n"
            "    return sorted(ids)\n"
        ),
    },
    # -- Family 5: day-count inclusivity ----------------------------------------
    "r2xf_days_inclusive": {  # TARGET (external: inclusive)
        "kind": "policy",
        "expected": {"amount": 8.0},
        "candidate": {"amount": 8.0},
    },
    "r2xf_days_exclusive": {  # FOIL (default: exclusive end - start)
        "kind": "policy",
        "expected": {"amount": 7.0},
        "candidate": {"amount": 7.0},
    },
    # -- Family 6: business vs calendar weeks -----------------------------------
    "r2xf_weeks_business": {  # TARGET (external: 5-day business weeks)
        "kind": "policy",
        "expected": {"amount": 10.0},
        "candidate": {"amount": 10.0},
    },
    "r2xf_weeks_calendar": {  # FOIL (default: 7-day calendar weeks)
        "kind": "policy",
        "expected": {"amount": 14.0},
        "candidate": {"amount": 14.0},
    },
}


def _build_checker(check_id: str, spec: Dict[str, Any]) -> GoldChecker:
    """Construct the deterministic executable-gold checker for one interpretation."""
    kind = spec["kind"]
    if kind == "code":
        return CodeChecker(spec["test_cases"], entrypoint=spec["entrypoint"],
                           description=check_id)
    if kind == "data":
        return DataChecker(spec["test_cases"], entrypoint=spec["entrypoint"],
                           description=check_id)
    if kind == "policy":
        return StructuredAnswerChecker(spec["expected"], description=check_id)
    raise ValueError(f"Unknown checker kind {kind!r} for {check_id}")


CHECKERS: Dict[str, GoldChecker] = {
    cid: _build_checker(cid, spec) for cid, spec in CHECK_SPECS.items()
}
REFERENCE_CANDIDATES: Dict[str, Any] = {
    cid: spec["candidate"] for cid, spec in CHECK_SPECS.items()
}


# ============================================================================
# ADDITIVE host-registry registration (executable-gold live labeling).
# ============================================================================

def _register_into_host_domains() -> None:
    """Insert r2_xf checkers + candidates into the host domains' registries.

    Enables harness/label.py's domain-dispatched executable-gold labeling to
    resolve the r2xf_ interpretation ids at live-run time. Purely additive: no
    source file is edited, ids are disjoint from all host ids, and this only
    runs when bench.r2_xf is imported (the explicit R2 partition).
    """
    import bench.code_spec as _code
    import bench.data_analysis as _data
    import bench.policy_qa as _policy

    host = {
        "code": (_code.CHECKERS, _code.REFERENCE_IMPLEMENTATIONS),
        "data": (_data.CHECKERS, _data.REFERENCE_IMPLEMENTATIONS),
        "policy": (_policy.CHECKERS, _policy.REFERENCE_ANSWERS),
    }
    for cid, spec in CHECK_SPECS.items():
        checkers, references = host[spec["kind"]]
        # Fail-closed: raise on ANY pre-existing host id UNLESS it is already
        # the identical registered R2 checker (idempotent re-import is fine;
        # a real host-id collision would silently corrupt labeling otherwise).
        if cid in checkers and checkers[cid] is not CHECKERS[cid]:
            raise RuntimeError(f"r2_xf id {cid!r} collides with a host checker id")
        checkers[cid] = CHECKERS[cid]
        references[cid] = REFERENCE_CANDIDATES[cid]


_register_into_host_domains()



# ============================================================================
# PROBLEM LIBRARY — H1_external "hidden-convention traps".
#   I0 (TARGET)      = the EXTERNAL convention (deleted clause; unaware != this)
#   FOIL [comb-def]  = the NATURAL DEFAULT an unaware Python solver writes
# Each family has ONE binary axis; prompt_core is generic (no in-prompt hint).
# ============================================================================

def problem_intdiv_001() -> FullSpec:
    """code_spec / axis integer_division. TARGET=truncate-toward-zero (external)."""
    return FullSpec(
        domain="code_spec",
        task_id="r2xf_code_intdiv_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `int_divide(a, b)` that performs integer division "
            "of two integers a and b and returns the integer quotient."
        ),
        requirement_classes=[
            RequirementClass(
                id="integer_division",
                description="Rounding direction of integer division for negatives",
                clauses=[
                    "Per the external service contract, integer division TRUNCATES "
                    "TOWARD ZERO (as in C and SQL): e.g. int_divide(-7, 2) == -3 "
                    "and int_divide(-8, 3) == -2, not -4 and -3."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default (target): truncate toward zero (C/SQL convention). "
                    "int_divide(-7, 2) == -3. Requires the EXTERNAL contract."
                ),
                is_target=True,
                gold_check="r2xf_intdiv_trunc",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: Python floor division a // b, "
                    "which floors toward -inf. int_divide(-7, 2) == -4."
                ),
                is_target=False,
                gold_check="r2xf_intdiv_floor",
                opened_by="integer_division",
            ),
        ],
        key_questions=[
            "Does integer division truncate toward zero (C/SQL) or floor toward "
            "negative infinity (Python default)?",
        ],
    )


def problem_weekday_001() -> FullSpec:
    """code_spec / axis weekday_numbering. TARGET=ISO Monday=1 (external)."""
    return FullSpec(
        domain="code_spec",
        task_id="r2xf_code_weekday_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `weekday_number(year, month, day)` that returns the "
            "weekday number for the given date."
        ),
        requirement_classes=[
            RequirementClass(
                id="weekday_numbering",
                description="Which weekday-numbering convention to use",
                clauses=[
                    "Per ISO 8601, number weekdays Monday=1, Tuesday=2, ..., "
                    "Sunday=7 (as returned by date.isoweekday())."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default (target): ISO 8601 numbering Monday=1..Sunday=7. "
                    "Requires the EXTERNAL ISO convention."
                ),
                is_target=True,
                gold_check="r2xf_weekday_iso",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: Python date.weekday(), "
                    "Monday=0..Sunday=6."
                ),
                is_target=False,
                gold_check="r2xf_weekday_py",
                opened_by="weekday_numbering",
            ),
        ],
        key_questions=[
            "Number weekdays ISO 8601 (Monday=1..Sunday=7) or Python-native "
            "(Monday=0..Sunday=6)?",
        ],
    )


def problem_argmax_001() -> FullSpec:
    """data_analysis / axis position_base. TARGET=1-based position (external)."""
    return FullSpec(
        domain="data_analysis",
        task_id="r2xf_data_argmax_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `max_position(data)` that returns the position of "
            "the largest value in the list data = [3, 7, 2, 9, 4]."
        ),
        requirement_classes=[
            RequirementClass(
                id="position_base",
                description="Whether reported positions are 0-based or 1-based",
                clauses=[
                    "Per our reporting-system spec, positions are reported as "
                    "1-BASED row numbers (the first element is position 1), so the "
                    "largest value 9 is at position 4."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default (target): 1-based position number = 4. "
                    "Requires the EXTERNAL reporting convention."
                ),
                is_target=True,
                gold_check="r2xf_argmax_1based",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: 0-based Python index "
                    "data.index(max(data)) = 3."
                ),
                is_target=False,
                gold_check="r2xf_argmax_0based",
                opened_by="position_base",
            ),
        ],
        key_questions=[
            "Report the position 1-based (first element = 1) or 0-based (Python "
            "index)?",
        ],
    )


def problem_sortids_001() -> FullSpec:
    """data_analysis / axis id_sort_order. TARGET=numeric order (external)."""
    return FullSpec(
        domain="data_analysis",
        task_id="r2xf_data_sortids_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `sort_ids(ids)` that returns the list of id strings "
            "['10', '2', '1', '21', '3'] sorted in ascending order."
        ),
        requirement_classes=[
            RequirementClass(
                id="id_sort_order",
                description="Whether ids sort numerically or lexicographically",
                clauses=[
                    "Per the catalog specification, the id strings are sorted by "
                    "their NUMERIC value, so the result is "
                    "['1', '2', '3', '10', '21'], not lexicographic order."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default (target): numeric-value order "
                    "['1','2','3','10','21']. Requires the EXTERNAL catalog spec."
                ),
                is_target=True,
                gold_check="r2xf_sortids_numeric",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: Python-native lexicographic "
                    "sorted(ids) = ['1','10','2','21','3']."
                ),
                is_target=False,
                gold_check="r2xf_sortids_lex",
                opened_by="id_sort_order",
            ),
        ],
        key_questions=[
            "Sort the id strings by numeric value or lexicographically (Python "
            "default string order)?",
        ],
    )


def problem_days_001() -> FullSpec:
    """policy_qa / axis day_count. TARGET=inclusive count (external policy)."""
    return FullSpec(
        domain="policy_qa",
        task_id="r2xf_policy_days_001",
        regime="H1_external",
        prompt_core=(
            "A task runs from day 3 to day 10 of the same month. Compute the "
            'number of days it spans. Return {"amount": <number of days>}.'
        ),
        requirement_classes=[
            RequirementClass(
                id="day_count",
                description="Whether the span counts both endpoints",
                clauses=[
                    "Per company leave policy, day spans are counted INCLUSIVELY "
                    "(both the start and end day count), so day 3 to day 10 spans "
                    "8 days."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default (target): inclusive count (both endpoints) = 8. "
                    "Requires the EXTERNAL leave policy."
                ),
                is_target=True,
                gold_check="r2xf_days_inclusive",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: exclusive arithmetic span "
                    "end - start = 10 - 3 = 7."
                ),
                is_target=False,
                gold_check="r2xf_days_exclusive",
                opened_by="day_count",
            ),
        ],
        key_questions=[
            "Count the day span inclusively (both endpoints, per policy) or "
            "exclusively (end - start, the arithmetic default)?",
        ],
    )


def problem_weeks_001() -> FullSpec:
    """policy_qa / axis week_definition. TARGET=business weeks (external SLA)."""
    return FullSpec(
        domain="policy_qa",
        task_id="r2xf_policy_weeks_001",
        regime="H1_external",
        prompt_core=(
            "A deadline is set 2 weeks from the project start. Compute how many "
            'days that deadline is from the start. Return {"amount": <days>}.'
        ),
        requirement_classes=[
            RequirementClass(
                id="week_definition",
                description="Whether a week means calendar days or business days",
                clauses=[
                    "Per our SLA, durations expressed in 'weeks' mean BUSINESS "
                    "weeks of 5 working days each, so 2 weeks = 10 days."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NON-default (target): business weeks, 5 days each -> "
                    "2 * 5 = 10. Requires the EXTERNAL SLA definition."
                ),
                is_target=True,
                gold_check="r2xf_weeks_business",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "MODEL DEFAULT [combined-default]: calendar weeks, 7 days each "
                    "-> 2 * 7 = 14."
                ),
                is_target=False,
                gold_check="r2xf_weeks_calendar",
                opened_by="week_definition",
            ),
        ],
        key_questions=[
            "Does 'weeks' mean 5-day business weeks (per SLA) or 7-day calendar "
            "weeks (the natural default)?",
        ],
    )


_PROBLEMS = [
    problem_intdiv_001,
    problem_weekday_001,
    problem_argmax_001,
    problem_sortids_001,
    problem_days_001,
    problem_weeks_001,
]


# ============================================================================
# TASK GENERATION
# ============================================================================

def generate_tasks() -> List[Task]:
    """Generate the 12 R2 cross-family tasks (6 families x {k0, k1}).

    Per-variant invariant (Amdt-03, enforced by a post-generation gate):
        len(key_questions) == ambiguity_level == len(interpretations) - 1
        k0 control: prompt == latent_spec, EMPTY key_questions, single I0 interp.
        k1 trap: I0 + one [combined-default] foil (gold_check __combdef-suffixed).
    All items are H1_external and carry the r2xf_ id prefix.
    """
    tasks: List[Task] = []

    for make in _PROBLEMS:
        base_spec = make()
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

    # Post-generation invariant gate (fail fast, never silent).
    for t in tasks:
        k_prime = t.ambiguity_level
        if len(t.key_questions) != k_prime:
            raise AssertionError(
                f"{t.id}: expected {k_prime} key_questions, got {len(t.key_questions)}"
            )
        if len(t.interpretations) - 1 != k_prime:
            raise AssertionError(
                f"{t.id}: expected {k_prime + 1} interpretations, "
                f"got {len(t.interpretations)}"
            )
        targets = [i for i in t.interpretations if i.is_target]
        if len(targets) != 1 or targets[0].id != "I0":
            raise AssertionError(f"{t.id}: must have exactly one target I0")
        if t.regime != "H1_external":
            raise AssertionError(f"{t.id}: R2 items must be H1_external")
        if k_prime == 0:
            if t.key_questions != []:
                raise AssertionError(f"{t.id}: k0 control must have empty key_questions")
            if len(t.interpretations) != 1:
                raise AssertionError(f"{t.id}: k0 control must have a single interp")
        else:
            combdef = sum(
                1 for i in t.interpretations if i.gold_check.endswith("__combdef")
            )
            if combdef != 1:
                raise AssertionError(
                    f"{t.id}: expected exactly 1 __combdef interp, got {combdef}"
                )

    return tasks


# ============================================================================
# VALIDATION LOADER — foils are MANDATORY (fail-closed disjointness defense).
# ============================================================================

def get_task_specific_foils(task_id_base: str) -> List[Any]:
    """Near-miss adversarial candidates per family; each matches AT MOST ONE checker."""
    if task_id_base == "r2xf_code_intdiv_001":
        return [
            "def int_divide(a, b):\n    return abs(a) // abs(b)\n",
            "def int_divide(a, b):\n    return -(abs(a) // abs(b))\n",
            "def int_divide(a, b):\n    return a // b + 1\n",
        ]
    if task_id_base == "r2xf_code_weekday_001":
        return [
            "import datetime\ndef weekday_number(year, month, day):\n    return datetime.date(year, month, day).day\n",
            "import datetime\ndef weekday_number(year, month, day):\n    return datetime.date(year, month, day).isoweekday() + 1\n",
            "import datetime\ndef weekday_number(year, month, day):\n    return datetime.date(year, month, day).month\n",
        ]
    if task_id_base == "r2xf_data_argmax_001":
        return [
            "def max_position(data):\n    return max(data)\n",
            "def max_position(data):\n    return len(data)\n",
            "def max_position(data):\n    return data.index(min(data))\n",
        ]
    if task_id_base == "r2xf_data_sortids_001":
        return [
            "def sort_ids(ids):\n    return sorted(ids, key=int, reverse=True)\n",
            "def sort_ids(ids):\n    return sorted(ids, reverse=True)\n",
            "def sort_ids(ids):\n    return list(ids)\n",
        ]
    if task_id_base == "r2xf_policy_days_001":
        return [
            {"amount": 6.0},
            {"amount": 9.0},
            {"amount": 8.5},
        ]
    if task_id_base == "r2xf_policy_weeks_001":
        return [
            {"amount": 7.0},
            {"amount": 12.0},
            {"amount": 5.0},
        ]
    return [{"error": "unknown"}, "N/A", None]


def get_checkers_and_candidates(domain: str, task: Task) -> Tuple[
    Dict[str, GoldChecker], Dict[str, Any], List[Any]
]:
    """Return (checkers, reference-candidates, foils) for a task. Foils MANDATORY."""
    checkers: Dict[str, GoldChecker] = {}
    candidates: Dict[str, Any] = {}

    for interp in task.interpretations:
        check_id = interp.gold_check
        if check_id.endswith("__combdef"):
            check_id = check_id[: -len("__combdef")]
        if check_id not in CHECKERS:
            raise ValueError(f"Unknown checker: {check_id}")
        checkers[interp.id] = CHECKERS[check_id]
        candidates[interp.id] = REFERENCE_CANDIDATES[check_id]

    task_id_base = task.id.split("_k")[0] if "_k" in task.id else task.id
    foils = get_task_specific_foils(task_id_base)

    return checkers, candidates, foils


# ============================================================================
# MAIN: Generate data file
# ============================================================================

if __name__ == "__main__":
    from pathlib import Path

    tasks = generate_tasks()
    output_path = Path(__file__).parent.parent / "data" / "r2_xf.jsonl"
    output_path.parent.mkdir(exist_ok=True)
    save_tasks(tasks, str(output_path))

    print(f"Generated {len(tasks)} r2_xf tasks -> {output_path}")
    levels = {k: sum(1 for t in tasks if t.ambiguity_level == k) for k in (0, 1)}
    print(f"Ambiguity distribution: {levels}")
