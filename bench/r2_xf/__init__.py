# constructed by: Anthropic claude-opus-4.8 (SECOND constructor family, Amendment 10)
"""R2 cross-family construction subset — Anthropic claude-opus-4.8-constructed items.

Implements SIGNED pre-registration Amendment 10 (R2 cross-family construction
control). Every item in this module was DESIGNED by the Anthropic
``claude-opus-4.8`` constructor family, so it carries
``constructor_family="anthropic/claude-opus-4.8"`` (derived additively in
``analysis/io.py`` from the ``r2xf_`` task-id prefix — NO edit to the frozen
``common/schema.py``). The main benchmark is mai-code-constructed; this subset
supplies the SECOND independent constructor family R2 needs.

Design (H1_external, "which-convention with a NATURAL DEFAULT"):
  - I0 (target) = the NATURAL DEFAULT a reasonable UNAWARE solver picks — the
    language-native / format-standard / domain-default behavior. It MUST SURVIVE
    deletion of the disambiguating clause: delete it and I0 is still the default.
  - Each foil deviates on EXACTLY ONE convention axis. These are H1 (the
    disambiguator is EXTERNAL knowledge NOT in the retained prompt) so — unlike
    H2 — they are NOT resolvable from the retained prompt.
  - Deterministic executable-gold ``check()``; I0 uniquely identifiable;
    enumerated foils; cross-family-FAIR (not tuned to any single tested family).
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
# Each entry: id -> dict with
#   kind        : "code" | "data" | "policy"
#   entrypoint  : function name (code/data only)
#   test_cases  : [(input, expected), ...] (code/data only)
#   expected    : reference structured answer (policy only)
#   candidate   : reference solution (code string, or {"amount": float} dict)
# All ids are r2xf_-prefixed => disjoint from every host-domain checker id.
# ============================================================================

# ── Family 1 (code_spec): string-sort case convention ────────────────────────
# NATURAL DEFAULT: Python's native sorted() = Unicode code-point order (uppercase
# before lowercase). Foil: case-insensitive sort (external convention).
_SORT_DATA = ["banana", "Apple", "cherry", "Date", "apple"]
_SORT_NATIVE = sorted(_SORT_DATA)              # ['Apple','Date','apple','banana','cherry']
_SORT_CI = sorted(_SORT_DATA, key=str.lower)   # ['Apple','apple','banana','cherry','Date']

# ── Family 2 (code_spec): word-count whitespace-split convention ─────────────
# NATURAL DEFAULT: str.split() (split on ANY run of whitespace, drop empties).
# Foil: split on a single space ' ' (keeps empty tokens from repeated spaces).
_WC_DATA = "  the quick  brown  "
_WC_DEFAULT = len(_WC_DATA.split())            # 3
_WC_SINGLE = len(_WC_DATA.split(" "))          # 8

# ── Family 3 (data_analysis): even-length median convention ──────────────────
# NATURAL DEFAULT: mean of the two middle values (standard statistical median).
# Foil: lower median (the lower of the two middles).
_MED_DATA = [1, 2, 3, 4]

# ── Family 4 (data_analysis): rounding convention for a mean ─────────────────
# NATURAL DEFAULT: Python's built-in round() = round-half-to-even (banker's).
# Foil: round-half-up. Dataset mean lands exactly on x.5 so the two diverge.
_ROUND_DATA = [1, 2, 3, 4]                      # mean 2.5 -> banker 2, half-up 3

# ── Family 5 (policy_qa): day-count convention ───────────────────────────────
# NATURAL DEFAULT: exclusive day span (end - start). Foil: inclusive (both ends).
# start day 3, end day 10 -> exclusive 7, inclusive 8.

# ── Family 6 (policy_qa): average-speed convention ───────────────────────────
# NATURAL DEFAULT: arithmetic mean of the two leg speeds. Foil: harmonic mean.
# same distance at 30 and 60 -> arithmetic 45, harmonic 40.


CHECK_SPECS: Dict[str, Dict[str, Any]] = {
    # -- Family 1: sort case convention -----------------------------------------
    "r2xf_sort_native": {
        "kind": "code",
        "entrypoint": "sort_names",
        "test_cases": [(_SORT_DATA, _SORT_NATIVE)],
        "candidate": "def sort_names(names):\n    return sorted(names)\n",
    },
    "r2xf_sort_ci": {
        "kind": "code",
        "entrypoint": "sort_names",
        "test_cases": [(_SORT_DATA, _SORT_CI)],
        "candidate": "def sort_names(names):\n    return sorted(names, key=str.lower)\n",
    },
    # -- Family 2: word-count split convention ----------------------------------
    "r2xf_wc_default": {
        "kind": "code",
        "entrypoint": "word_count",
        "test_cases": [(_WC_DATA, _WC_DEFAULT)],
        "candidate": "def word_count(s):\n    return len(s.split())\n",
    },
    "r2xf_wc_singlespace": {
        "kind": "code",
        "entrypoint": "word_count",
        "test_cases": [(_WC_DATA, _WC_SINGLE)],
        "candidate": "def word_count(s):\n    return len(s.split(' '))\n",
    },
    # -- Family 3: even-median convention ---------------------------------------
    "r2xf_median_mean": {
        "kind": "data",
        "entrypoint": "median",
        "test_cases": [(_MED_DATA, "2.50")],
        "candidate": (
            "def median(data):\n"
            "    s = sorted(data)\n"
            "    n = len(s)\n"
            "    mid = n // 2\n"
            "    if n % 2 == 0:\n"
            "        return f'{(s[mid - 1] + s[mid]) / 2.0:.2f}'\n"
            "    return f'{float(s[mid]):.2f}'\n"
        ),
    },
    "r2xf_median_lower": {
        "kind": "data",
        "entrypoint": "median",
        "test_cases": [(_MED_DATA, "2.00")],
        "candidate": (
            "def median(data):\n"
            "    s = sorted(data)\n"
            "    n = len(s)\n"
            "    mid = n // 2\n"
            "    if n % 2 == 0:\n"
            "        return f'{float(s[mid - 1]):.2f}'\n"
            "    return f'{float(s[mid]):.2f}'\n"
        ),
    },
    # -- Family 4: mean-rounding convention -------------------------------------
    "r2xf_roundmean_even": {
        "kind": "data",
        "entrypoint": "avg_rounded",
        "test_cases": [(_ROUND_DATA, 2)],
        "candidate": (
            "def avg_rounded(data):\n"
            "    return round(sum(data) / len(data))\n"
        ),
    },
    "r2xf_roundmean_up": {
        "kind": "data",
        "entrypoint": "avg_rounded",
        "test_cases": [(_ROUND_DATA, 3)],
        "candidate": (
            "def avg_rounded(data):\n"
            "    from decimal import Decimal, ROUND_HALF_UP\n"
            "    mean = Decimal(sum(data)) / Decimal(len(data))\n"
            "    return int(mean.quantize(Decimal('1'), rounding=ROUND_HALF_UP))\n"
        ),
    },
    # -- Family 5: day-count convention -----------------------------------------
    "r2xf_days_exclusive": {
        "kind": "policy",
        "expected": {"amount": 7.0},
        "candidate": {"amount": 7.0},
    },
    "r2xf_days_inclusive": {
        "kind": "policy",
        "expected": {"amount": 8.0},
        "candidate": {"amount": 8.0},
    },
    # -- Family 6: average-speed convention -------------------------------------
    "r2xf_speed_arith": {
        "kind": "policy",
        "expected": {"amount": 45.0},
        "candidate": {"amount": 45.0},
    },
    "r2xf_speed_harmonic": {
        "kind": "policy",
        "expected": {"amount": 40.0},
        "candidate": {"amount": 40.0},
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
        # Never clobber a host id (all r2xf_ ids are disjoint; assert to be safe).
        if cid in checkers and cid not in CHECKERS:
            raise RuntimeError(f"r2_xf id {cid!r} collides with a host checker id")
        checkers[cid] = CHECKERS[cid]
        references[cid] = REFERENCE_CANDIDATES[cid]


_register_into_host_domains()


# ============================================================================
# PROBLEM LIBRARY — H1_external, I0 = NATURAL DEFAULT, one binary axis each.
# ============================================================================

def problem_sort_001() -> FullSpec:
    """code_spec / axis case_convention. Default = native code-point sort."""
    return FullSpec(
        domain="code_spec",
        task_id="r2xf_code_sort_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `sort_names(names)` that returns the given list of "
            "strings sorted in ascending order."
        ),
        requirement_classes=[
            RequirementClass(
                id="case_convention",
                description="Which string-ordering convention to sort by",
                clauses=[
                    "Sort using Python's native string comparison — order the "
                    "strings by Unicode code point (the language-default "
                    "ordering), so uppercase letters sort before lowercase."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NATURAL DEFAULT (target): native code-point sort, "
                    "sorted(names). An unaware solver's default in Python."
                ),
                is_target=True,
                gold_check="r2xf_sort_native",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "FOIL [combined-default]: case-insensitive sort, "
                    "sorted(names, key=str.lower) — deviates on the case axis."
                ),
                is_target=False,
                gold_check="r2xf_sort_ci",
                opened_by="case_convention",
            ),
        ],
        key_questions=[
            "Sort by Python's default code-point order, or case-insensitively?",
        ],
    )


def problem_wordcount_001() -> FullSpec:
    """code_spec / axis split_convention. Default = str.split() whitespace split."""
    return FullSpec(
        domain="code_spec",
        task_id="r2xf_code_wordcount_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `word_count(s)` that returns the number of words in "
            "the string s, as an int."
        ),
        requirement_classes=[
            RequirementClass(
                id="split_convention",
                description="Which tokenization convention to count words by",
                clauses=[
                    "Count words using Python's default str.split() — split on "
                    "any run of whitespace, discarding the empty tokens produced "
                    "by leading, trailing, or repeated spaces."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NATURAL DEFAULT (target): len(s.split()) — the Python-native "
                    "whitespace split an unaware solver reaches for."
                ),
                is_target=True,
                gold_check="r2xf_wc_default",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "FOIL [combined-default]: len(s.split(' ')) — splits on a "
                    "single space, keeping empty tokens (deviates on the split axis)."
                ),
                is_target=False,
                gold_check="r2xf_wc_singlespace",
                opened_by="split_convention",
            ),
        ],
        key_questions=[
            "Count words with Python's default whitespace split, or by splitting "
            "on single spaces?",
        ],
    )


def problem_median_001() -> FullSpec:
    """data_analysis / axis even_median. Default = mean of the two middle values."""
    return FullSpec(
        domain="data_analysis",
        task_id="r2xf_data_median_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `median(data)` that returns the median of the list "
            "[1, 2, 3, 4], as a string rounded to 2 decimal places."
        ),
        requirement_classes=[
            RequirementClass(
                id="even_median",
                description="Which even-length median convention to use",
                clauses=[
                    "For an even number of values, use the standard convention: "
                    "the median is the arithmetic MEAN of the two middle values. "
                    "Answer to 2 decimals."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NATURAL DEFAULT (target): mean of the two middles. "
                    "[1,2,3,4] -> (2+3)/2 = '2.50'. The standard median convention."
                ),
                is_target=True,
                gold_check="r2xf_median_mean",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "FOIL [combined-default]: lower median (lower of the two "
                    "middles). [1,2,3,4] -> '2.00' — deviates on the parity axis."
                ),
                is_target=False,
                gold_check="r2xf_median_lower",
                opened_by="even_median",
            ),
        ],
        key_questions=[
            "Even-length median: mean of the two middle values (standard), or the "
            "lower of the two middles?",
        ],
    )


def problem_roundmean_001() -> FullSpec:
    """data_analysis / axis rounding_convention. Default = Python round() (banker's)."""
    return FullSpec(
        domain="data_analysis",
        task_id="r2xf_data_roundmean_001",
        regime="H1_external",
        prompt_core=(
            "Write a function `avg_rounded(data)` that returns the arithmetic mean "
            "of the integer list [1, 2, 3, 4] rounded to the nearest whole number, "
            "as an int."
        ),
        requirement_classes=[
            RequirementClass(
                id="rounding_convention",
                description="Which rounding convention to apply to the mean",
                clauses=[
                    "Round the mean to the nearest whole number using Python's "
                    "built-in default rounding (round-half-to-even / banker's "
                    "rounding, i.e. round(mean))."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NATURAL DEFAULT (target): round(mean) = round-half-to-even. "
                    "mean 2.5 -> 2. The Python-native default rounding."
                ),
                is_target=True,
                gold_check="r2xf_roundmean_even",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "FOIL [combined-default]: round-half-up. mean 2.5 -> 3 — "
                    "deviates on the rounding axis."
                ),
                is_target=False,
                gold_check="r2xf_roundmean_up",
                opened_by="rounding_convention",
            ),
        ],
        key_questions=[
            "Round the mean using Python's default round-half-to-even, or "
            "round-half-up?",
        ],
    )


def problem_days_001() -> FullSpec:
    """policy_qa / axis day_count. Default = exclusive day span (end - start)."""
    return FullSpec(
        domain="policy_qa",
        task_id="r2xf_policy_days_001",
        regime="H1_external",
        prompt_core=(
            "A task starts on day 3 and ends on day 10 of the same month. Compute "
            "the number of days from the start to the end. Return the answer as "
            '{"amount": <number of days>}.'
        ),
        requirement_classes=[
            RequirementClass(
                id="day_count",
                description="Which day-counting convention to use",
                clauses=[
                    "Count the number of days using the standard exclusive "
                    "convention: end minus start (10 - 3), not counting both "
                    "endpoints."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NATURAL DEFAULT (target): exclusive span end - start = 7. "
                    "The default arithmetic day difference."
                ),
                is_target=True,
                gold_check="r2xf_days_exclusive",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "FOIL [combined-default]: inclusive count (both endpoints) = 8 "
                    "— deviates on the day-count axis."
                ),
                is_target=False,
                gold_check="r2xf_days_inclusive",
                opened_by="day_count",
            ),
        ],
        key_questions=[
            "Count the day span exclusively (end - start, standard) or inclusively "
            "(counting both endpoints)?",
        ],
    )


def problem_speed_001() -> FullSpec:
    """policy_qa / axis averaging_method. Default = arithmetic mean of speeds."""
    return FullSpec(
        domain="policy_qa",
        task_id="r2xf_policy_speed_001",
        regime="H1_external",
        prompt_core=(
            "A vehicle travels the SAME distance on two legs of a trip: the first "
            "leg at 30 units/hour and the second at 60 units/hour. Compute the "
            'average speed over the whole trip. Return {"amount": <speed>}.'
        ),
        requirement_classes=[
            RequirementClass(
                id="averaging_method",
                description="Which averaging convention to use for the speeds",
                clauses=[
                    "Compute the average speed as the arithmetic mean of the two "
                    "leg speeds, (30 + 60) / 2."
                ],
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description=(
                    "NATURAL DEFAULT (target): arithmetic mean (30+60)/2 = 45. "
                    "The default 'average of the two numbers' an unaware solver uses."
                ),
                is_target=True,
                gold_check="r2xf_speed_arith",
            ),
            InterpretationBranch(
                id="I1",
                description=(
                    "FOIL [combined-default]: harmonic mean 2/(1/30+1/60) = 40 "
                    "(physically correct for equal distances) — deviates on the "
                    "averaging axis."
                ),
                is_target=False,
                gold_check="r2xf_speed_harmonic",
                opened_by="averaging_method",
            ),
        ],
        key_questions=[
            "Average speed via the arithmetic mean of the two speeds (default), or "
            "the harmonic mean (correct for equal distances)?",
        ],
    )


_PROBLEMS = [
    problem_sort_001,
    problem_wordcount_001,
    problem_median_001,
    problem_roundmean_001,
    problem_days_001,
    problem_speed_001,
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
    if task_id_base == "r2xf_code_sort_001":
        return [
            "def sort_names(names):\n    return sorted(names, reverse=True)\n",
            "def sort_names(names):\n    return sorted(names, key=len)\n",
            "def sort_names(names):\n    return list(names)\n",
        ]
    if task_id_base == "r2xf_code_wordcount_001":
        return [
            "def word_count(s):\n    return len(s)\n",
            "def word_count(s):\n    return len(s.split('\\t'))\n",
            "def word_count(s):\n    return 0\n",
        ]
    if task_id_base == "r2xf_data_median_001":
        return [
            "def median(data):\n    s = sorted(data)\n    return f'{float(s[len(s)//2]):.2f}'\n",
            "def median(data):\n    return f'{float(min(data)):.2f}'\n",
            "def median(data):\n    s = sorted(data)\n    n = len(s)\n    return str((s[n//2-1]+s[n//2])/2.0)\n",
        ]
    if task_id_base == "r2xf_data_roundmean_001":
        return [
            "def avg_rounded(data):\n    return sum(data)\n",
            "def avg_rounded(data):\n    return min(data)\n",
            "def avg_rounded(data):\n    return max(data)\n",
        ]
    if task_id_base == "r2xf_policy_days_001":
        return [
            {"amount": 6.0},
            {"amount": 9.0},
            7.0,
        ]
    if task_id_base == "r2xf_policy_speed_001":
        return [
            {"amount": 50.0},
            {"amount": 90.0},
            45.0,
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
