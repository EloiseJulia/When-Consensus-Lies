# constructed by: Claude (Anthropic) family
"""Code specification domain for ambiguous coding problems.

This domain features coding problems where deleting requirement CLASSES creates
genuine, real-world ambiguity about what code to write. Each interpretation is
realized by an actual reference implementation with executable gold checkers.
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

        # The verdict is written to this dedicated file (not stdout), so benign
        # candidate output can never corrupt it.
        fd, verdict_path = tempfile.mkstemp(prefix="codespec_verdict_", suffix=".json")
        os.close(fd)
        try:
            try:
                subprocess.run(
                    [sys.executable, _RUNNER_PATH, verdict_path],
                    input=payload,
                    text=True,
                    # DEVNULL (not PIPE): a candidate-spawned grandchild that
                    # inherits these handles cannot keep the parent blocked past
                    # the timeout.
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired:
                # subprocess.run kills the child on timeout -> runaway code is
                # actually terminated.
                result = (False, "Execution timeout (infinite loop or too slow)")
                _RESULT_CACHE[cache_key] = result
                return CheckResult(passed=False, details=f"{self.description} - {result[1]}")

            try:
                with open(verdict_path, "r", encoding="utf-8") as vf:
                    raw = vf.read().strip()
                verdict = json.loads(raw)
            except Exception as exc:  # noqa: BLE001
                msg = f"No/invalid runner verdict: {exc}"
                _RESULT_CACHE[cache_key] = (False, msg)
                return CheckResult(passed=False, details=f"{self.description} - {msg}")
        finally:
            try:
                os.unlink(verdict_path)
            except OSError:
                pass

        passed = verdict.get("status") == "pass"
        msg = verdict.get("message", "")
        _RESULT_CACHE[cache_key] = (passed, msg)
        return CheckResult(passed=passed, details=f"{self.description} - {msg}")


# ============================================================================
# PROBLEM LIBRARY - Base coding problems with requirement classes
# BLOCKER 2 FIX: All problems rewritten/verified for GENUINE ambiguity
# ============================================================================

def problem_sort_records():
    """Sort a list of records with ambiguous sort order and tiebreak."""
    
    spec = FullSpec(
        domain="code_spec",
        task_id="code_sort_001",
        # GENUINE: prompt says "sorts" which is neutral on direction
        prompt_core="""Write a function `sort_func` that sorts a list of records (dicts with keys 'name' and 'age').""",
        requirement_classes=[
            RequirementClass(
                id="sort_order",
                description="Sort order direction",
                clauses=["Sort in ascending order by age."]
            ),
            RequirementClass(
                id="tiebreak",
                description="Tiebreaker for equal ages",
                clauses=["When ages are equal, maintain stable order (do not reorder ties)."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Ascending, stable (target)",
                is_target=True,
                gold_check="sort_asc_stable"
            ),
            InterpretationBranch(
                id="I1",
                description="Descending, stable",
                is_target=False,
                gold_check="sort_desc_stable",
                opened_by="sort_order"
            ),
            InterpretationBranch(
                id="I2",
                description="Ascending, secondary sort by name",
                is_target=False,
                gold_check="sort_asc_name",
                opened_by="tiebreak"
            ),
        ],
        key_questions=[
            "Should I sort in ascending or descending order?",
            "How should I break ties when ages are equal?"
        ]
    )
    
    return spec


def problem_string_join():
    """Join strings with ambiguous separator and empty handling."""
    
    spec = FullSpec(
        domain="code_spec",
        task_id="code_string_001",
        # GENUINE: "combines" is neutral on how (concatenate vs join with separator)
        prompt_core="""Write a function `join_func` that combines a list of words into a single string.""",
        requirement_classes=[
            RequirementClass(
                id="separator",
                description="What separator to use",
                clauses=["Use a single space as the separator."]
            ),
            RequirementClass(
                id="empty_strings",
                description="How to handle empty strings",
                clauses=["Keep empty strings in the result."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Space separator, keep empty (target)",
                is_target=True,
                gold_check="join_space_keep"
            ),
            InterpretationBranch(
                id="I1",
                description="No separator (concatenate directly), keep empty",
                is_target=False,
                gold_check="join_concat_keep",
                opened_by="separator"
            ),
            InterpretationBranch(
                id="I2",
                description="Space separator, skip empty",
                is_target=False,
                gold_check="join_space_skip",
                opened_by="empty_strings"
            ),
        ],
        key_questions=[
            "What separator should I use between words?",
            "Should I include empty strings or skip them?"
        ]
    )
    
    return spec


def problem_parse_csv_line():
    """Parse CSV line with ambiguous quote and empty field handling."""
    
    spec = FullSpec(
        domain="code_spec",
        task_id="code_csv_001",
        # GENUINE: CSV parsing genuinely ambiguous on quote-stripping and empty-repr
        prompt_core="""Write a function `csv_func` that parses a comma-separated line into a list of fields.""",
        requirement_classes=[
            RequirementClass(
                id="quote_handling",
                description="How to handle quoted fields",
                clauses=["Strip surrounding quotes from fields that are quoted."]
            ),
            RequirementClass(
                id="empty_fields",
                description="How to represent empty fields",
                clauses=["Represent empty fields as empty strings."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Strip quotes, keep empty as '' (target)",
                is_target=True,
                gold_check="csv_strip_empty"
            ),
            InterpretationBranch(
                id="I1",
                description="Keep quotes, keep empty as ''",
                is_target=False,
                gold_check="csv_keep_empty",
                opened_by="quote_handling"
            ),
            InterpretationBranch(
                id="I2",
                description="Strip quotes, represent empty as None",
                is_target=False,
                gold_check="csv_strip_none",
                opened_by="empty_fields"
            ),
        ],
        key_questions=[
            "Should I remove quotes from quoted fields?",
            "How should I represent empty fields?"
        ]
    )
    
    return spec


def problem_count_occurrences():
    """Count with ambiguous case sensitivity and overlapping matches."""
    
    spec = FullSpec(
        domain="code_spec",
        task_id="code_count_001",
        # GENUINE: "counts" is neutral on case and overlap
        prompt_core="""Write a function `count_func` that counts how many times a substring appears in a string.""",
        requirement_classes=[
            RequirementClass(
                id="case_sensitive",
                description="Case sensitivity",
                clauses=["Search is case-sensitive."]
            ),
            RequirementClass(
                id="overlapping",
                description="Count overlapping matches",
                clauses=["Do not count overlapping occurrences."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Case-sensitive, non-overlapping (target)",
                is_target=True,
                gold_check="count_case_nonoverlap"
            ),
            InterpretationBranch(
                id="I1",
                description="Case-insensitive, non-overlapping",
                is_target=False,
                gold_check="count_nocase_nonoverlap",
                opened_by="case_sensitive"
            ),
            InterpretationBranch(
                id="I2",
                description="Case-sensitive, overlapping",
                is_target=False,
                gold_check="count_case_overlap",
                opened_by="overlapping"
            ),
        ],
        key_questions=[
            "Should the search be case-sensitive?",
            "Should I count overlapping occurrences?"
        ]
    )
    
    return spec


def problem_format_number():
    """Format number with ambiguous decimal places, rounding, and sign handling."""
    
    spec = FullSpec(
        domain="code_spec",
        task_id="code_format_001",
        # GENUINE: "formats" is neutral on precision, rounding, sign
        prompt_core="""Write a function `format_func` that formats a floating-point number as a string with decimal places.""",
        requirement_classes=[
            RequirementClass(
                id="decimal_places",
                description="Number of decimal places",
                clauses=["Show 2 decimal places."]
            ),
            RequirementClass(
                id="rounding",
                description="Rounding mode",
                clauses=["Round half up (0.5 rounds to 1)."]
            ),
            RequirementClass(
                id="sign_display",
                description="Sign display for positive numbers",
                clauses=["Do not display a '+' sign for positive numbers."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="2 decimals, round half up, no plus sign (target)",
                is_target=True,
                gold_check="format_2dec_halfup_noplus"
            ),
            InterpretationBranch(
                id="I1",
                description="1 decimal, round half up, no plus sign",
                is_target=False,
                gold_check="format_1dec_halfup_noplus",
                opened_by="decimal_places"
            ),
            InterpretationBranch(
                id="I2",
                description="2 decimals, truncate, no plus sign",
                is_target=False,
                gold_check="format_2dec_trunc_noplus",
                opened_by="rounding"
            ),
            InterpretationBranch(
                id="I3",
                description="2 decimals, round half up, with plus sign",
                is_target=False,
                gold_check="format_2dec_halfup_plus",
                opened_by="sign_display"
            ),
        ],
        key_questions=[
            "How many decimal places should I show?",
            "How should I round the value?",
            "Should I display a '+' sign for positive numbers?"
        ]
    )
    
    return spec


# Removed straw problems per BLOCKER 2:
# - code_filter_001: "positive numbers" already excludes zero; None→1 is arbitrary
# - code_sum_001: empty→-1 is arbitrary; string coercion for "list of numbers" is out-of-spec
# - code_max_001: "maximum VALUE" cannot mean index



# ============================================================================
# REFERENCE IMPLEMENTATIONS - One per interpretation per problem
# ============================================================================

REFERENCE_IMPLEMENTATIONS = {
    # Sort records
    "sort_asc_stable": """
def sort_func(records):
    return sorted(records, key=lambda r: r['age'])
""",
    "sort_desc_stable": """
def sort_func(records):
    return sorted(records, key=lambda r: r['age'], reverse=True)
""",
    "sort_asc_name": """
def sort_func(records):
    return sorted(records, key=lambda r: (r['age'], r['name']))
""",
    
    # String join
    "join_space_keep": """
def join_func(words):
    return ' '.join(words)
""",
    "join_concat_keep": """
def join_func(words):
    return ''.join(words)
""",
    "join_space_skip": """
def join_func(words):
    return ' '.join(w for w in words if w)
""",
    
    # Parse CSV
    "csv_strip_empty": """
def csv_func(line):
    fields = line.split(',')
    return [f.strip('"').strip("'") if f else '' for f in fields]
""",
    "csv_keep_empty": """
def csv_func(line):
    fields = line.split(',')
    return [f if f else '' for f in fields]
""",
    "csv_strip_none": """
def csv_func(line):
    fields = line.split(',')
    result = []
    for f in fields:
        f = f.strip('"').strip("'")
        result.append(None if not f else f)
    return result
""",
    
    # Count occurrences
    "count_case_nonoverlap": """
def count_func(text, substring):
    return text.count(substring)
""",
    "count_nocase_nonoverlap": """
def count_func(text, substring):
    return text.lower().count(substring.lower())
""",
    "count_case_overlap": """
def count_func(text, substring):
    count = 0
    start = 0
    while True:
        pos = text.find(substring, start)
        if pos == -1:
            break
        count += 1
        start = pos + 1
    return count
""",
    
    # Format number - MAJOR 2 FIX: true half-up using Decimal
    "format_2dec_halfup_noplus": """
def format_func(number):
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(str(number))
    rounded = d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f"{rounded:.2f}"
""",
    "format_1dec_halfup_noplus": """
def format_func(number):
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(str(number))
    rounded = d.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
    return f"{rounded:.1f}"
""",
    "format_2dec_trunc_noplus": """
def format_func(number):
    truncated = int(number * 100) / 100
    return f"{truncated:.2f}"
""",
    "format_2dec_halfup_plus": """
def format_func(number):
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(str(number))
    rounded = d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    sign = '+' if number >= 0 else ''
    return f"{sign}{rounded:.2f}"
""",
}


# ============================================================================
# TEST CASES - Input/output pairs for each interpretation
# MAJOR 2 FIX: Added tie-breaking cases for rounding (2.675, 1.005, etc.)
# ============================================================================

TEST_CASES = {
    # Sort records - test cases must produce DIFFERENT outputs for each interpretation
    "sort_asc_stable": [
        (
            [{'name': 'Charlie', 'age': 30}, {'name': 'Bob', 'age': 25}, {'name': 'Alice', 'age': 30}],
            [{'name': 'Bob', 'age': 25}, {'name': 'Charlie', 'age': 30}, {'name': 'Alice', 'age': 30}]
        ),
    ],
    "sort_desc_stable": [
        (
            [{'name': 'Charlie', 'age': 30}, {'name': 'Bob', 'age': 25}, {'name': 'Alice', 'age': 30}],
            [{'name': 'Charlie', 'age': 30}, {'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}]
        ),
    ],
    "sort_asc_name": [
        (
            [{'name': 'Charlie', 'age': 30}, {'name': 'Bob', 'age': 25}, {'name': 'Alice', 'age': 30}],
            [{'name': 'Bob', 'age': 25}, {'name': 'Alice', 'age': 30}, {'name': 'Charlie', 'age': 30}]
        ),
    ],
    
    # String join
    "join_space_keep": [
        (['hello', 'world'], 'hello world'),
        (['a', '', 'b'], 'a  b'),
    ],
    "join_concat_keep": [
        (['hello', 'world'], 'helloworld'),
        (['a', '', 'b'], 'ab'),
    ],
    "join_space_skip": [
        (['hello', 'world'], 'hello world'),
        (['a', '', 'b'], 'a b'),
    ],
    
    # Parse CSV
    "csv_strip_empty": [
        ('"a","b","c"', ['a', 'b', 'c']),
        ('x,,z', ['x', '', 'z']),
    ],
    "csv_keep_empty": [
        ('"a","b","c"', ['"a"', '"b"', '"c"']),
        ('x,,z', ['x', '', 'z']),
    ],
    "csv_strip_none": [
        ('"a","b","c"', ['a', 'b', 'c']),
        ('x,,z', ['x', None, 'z']),
    ],
    
    # Count occurrences - show case-sensitive vs overlapping differences.
    # NOTE: every checker includes a case whose expected count is >= 2, so a
    # boolean predicate (`substring in text` -> True==1/False==0) cannot pass
    # by coincidence (the runner also rejects bool-for-int type mismatches).
    "count_case_nonoverlap": [
        (('HELLO', 'l'), 0),      # Case-sensitive: 'l' not in 'HELLO'
        (('aaa', 'aa'), 1),       # Non-overlapping: count('aa') = 1
        (('banana', 'a'), 3),     # Discriminating: count = 3 (a bool would give 1)
    ],
    "count_nocase_nonoverlap": [
        (('HELLO', 'l'), 2),      # Case-insensitive: finds 'l' in 'HELLO'
        (('aaa', 'aa'), 1),       # Non-overlapping: count('aa') = 1
        (('BaNaNa', 'a'), 3),     # Discriminating: case-insensitive count = 3
    ],
    "count_case_overlap": [
        (('aaa', 'aa'), 2),       # Overlapping: finds 2
        (('HELLO', 'l'), 0),      # Case-sensitive: 'l' not in 'HELLO'
        (('aaaa', 'aa'), 3),      # Discriminating: overlapping count = 3
    ],
    
    # Format number - MAJOR 2 FIX: tie-breaking cases where half-up != Python default
    "format_2dec_halfup_noplus": [
        (3.456, '3.46'),  # Half-up rounding
        (2.675, '2.68'),  # TIE-BREAKER: true half-up gives .68, Python f-string gives .67
        (1.005, '1.01'),  # TIE-BREAKER: true half-up gives .01, default may give .00
        (2.5, '2.50'),
    ],
    "format_1dec_halfup_noplus": [
        (3.456, '3.5'),  # 1 decimal
        (2.675, '2.7'),
        (2.5, '2.5'),
    ],
    "format_2dec_trunc_noplus": [
        (3.456, '3.45'),  # Truncate: .456 → .45 (different from half-up .46)
        (2.675, '2.67'),  # Truncate gives .67
        (2.5, '2.50'),
    ],
    "format_2dec_halfup_plus": [
        (3.456, '+3.46'),  # With plus sign
        (2.675, '+2.68'),
        (-1.5, '-1.50'),  # Negative has minus sign
    ],
}


# ============================================================================
# CHECKERS REGISTRY
# ============================================================================

CHECKERS = {}
ENTRYPOINTS = {
    # Map checker IDs to their entrypoint function names
    "sort_asc_stable": "sort_func",
    "sort_desc_stable": "sort_func",
    "sort_asc_name": "sort_func",
    "join_space_keep": "join_func",
    "join_concat_keep": "join_func",
    "join_space_skip": "join_func",
    "csv_strip_empty": "csv_func",
    "csv_keep_empty": "csv_func",
    "csv_strip_none": "csv_func",
    "count_case_nonoverlap": "count_func",
    "count_nocase_nonoverlap": "count_func",
    "count_case_overlap": "count_func",
    "format_2dec_halfup_noplus": "format_func",
    "format_1dec_halfup_noplus": "format_func",
    "format_2dec_trunc_noplus": "format_func",
    "format_2dec_halfup_plus": "format_func",
}

for check_id, test_cases in TEST_CASES.items():
    entrypoint = ENTRYPOINTS[check_id]
    CHECKERS[check_id] = CodeChecker(test_cases, entrypoint=entrypoint, description=check_id)


# ============================================================================
# TASK GENERATION
# ============================================================================

def generate_tasks() -> List[Task]:
    """Generate all code_spec tasks with multiple deletion patterns."""
    
    # BLOCKER 2 FIX: Only include problems with genuine ambiguity
    problems = [
        problem_sort_records(),
        problem_string_join(),
        problem_parse_csv_line(),
        problem_count_occurrences(),
        problem_format_number(),
    ]
    
    tasks = []
    
    for base_spec in problems:
        base_id = base_spec.task_id
        n_req = len(base_spec.requirement_classes)
        
        # k=0 CONTROL: unambiguous
        task_k0 = assemble_task(base_spec, k=0, classes_to_delete=[])
        task_k0.id = f"{base_id}_k0"
        tasks.append(task_k0)
        
        # k=1: delete each requirement individually
        for i, req_class in enumerate(base_spec.requirement_classes):
            spec_copy = FullSpec(
                domain=base_spec.domain,
                task_id=f"{base_id}_k1_{req_class.id}",
                prompt_core=base_spec.prompt_core,
                requirement_classes=base_spec.requirement_classes[:],
                interpretations=base_spec.interpretations[:],
                key_questions=base_spec.key_questions[:]
            )
            task = assemble_task(spec_copy, k=1, classes_to_delete=[req_class.id])
            tasks.append(task)
        
        # k=2: delete all requirements (if there are exactly 2)
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
            task = assemble_task(spec_copy, k=2, classes_to_delete=req_ids)
            tasks.append(task)
        
        # k=3: delete all requirements (if there are exactly 3)
        if n_req == 3:
            req_ids = [rc.id for rc in base_spec.requirement_classes]
            spec_copy = FullSpec(
                domain=base_spec.domain,
                task_id=f"{base_id}_k3_all",
                prompt_core=base_spec.prompt_core,
                requirement_classes=base_spec.requirement_classes[:],
                interpretations=base_spec.interpretations[:],
                key_questions=base_spec.key_questions[:]
            )
            task = assemble_task(spec_copy, k=3, classes_to_delete=req_ids)
            tasks.append(task)
    
    return tasks


# ============================================================================
# VALIDATION LOADER
# MAJOR 3 FIX: Task-specific near-miss foils for each problem
# ============================================================================

def get_task_specific_foils(task_id_base: str) -> List[str]:
    """Generate task-specific near-miss foils that test checker boundaries.
    
    MAJOR 3 FIX: Each task gets plausible near-miss foils that might match
    multiple interpretations if checkers aren't truly disjoint.
    """
    
    if "code_sort" in task_id_base:
        return [
            # Near-miss: ascending but breaks ties by reverse name (boundary between I0 and I2)
            """
def sort_func(records):
    return sorted(records, key=lambda r: (r['age'], -ord(r['name'][0])))
""",
            # Near-miss: descending but with dict iteration (tests I1 boundary)
            """
def sort_func(records):
    return sorted(records, key=lambda r: -r['age'])
""",
            # Always-fail foil
            """
def sort_func(records):
    raise ValueError("not implemented")
""",
        ]
    
    elif "code_string" in task_id_base:
        return [
            # Near-miss: joins with space but adds extra spaces (boundary test)
            """
def join_func(words):
    return '  '.join(words)
""",
            # Near-miss: filters empty but uses different method (boundary for I2)
            """
def join_func(words):
    return ' '.join([w for w in words if len(w) > 0])
""",
            # Wrong behavior
            """
def join_func(words):
    return ','.join(words)
""",
        ]
    
    elif "code_csv" in task_id_base:
        return [
            # Near-miss: strips only double quotes, not single (boundary test)
            """
def csv_func(line):
    fields = line.split(',')
    return [f.strip('"') if f else '' for f in fields]
""",
            # Near-miss: represents empty as empty list instead of None or ''
            """
def csv_func(line):
    return [f if f else [] for f in line.split(',')]
""",
            # Wrong split character
            """
def csv_func(line):
    return line.split(';')
""",
        ]
    
    elif "code_count" in task_id_base:
        return [
            # Near-miss: case-insensitive but uses different method
            """
def count_func(text, substring):
    import re
    return len(re.findall(substring, text, re.IGNORECASE))
""",
            # Near-miss: overlapping but off-by-one in start position
            """
def count_func(text, substring):
    count = 0
    start = 0
    while start < len(text):
        pos = text.find(substring, start)
        if pos == -1:
            break
        count += 1
        start = pos + 2  # off-by-one: should be +1 for overlap
    return count
""",
            # Wrong: returns boolean
            """
def count_func(text, substring):
    return substring in text
""",
        ]
    
    elif "code_format" in task_id_base:
        return [
            # Near-miss: naive f-string (MAJOR 2 FIX: this MUST fail half-up checker on ties)
            """
def format_func(number):
    return f"{number:.2f}"
""",
            # Near-miss: uses round() which is half-to-even, not half-up
            """
def format_func(number):
    return f"{round(number, 2):.2f}"
""",
            # Near-miss: correct half-up but wrong precision
            """
def format_func(number):
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(str(number))
    rounded = d.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
    return f"{rounded:.2f}"
""",
            # Wrong: returns number instead of string
            """
def format_func(number):
    return number
""",
        ]
    
    else:
        # Fallback generic foils
        return [
            "def func(): raise NotImplementedError()",
            "x = 42",
            "def func(): return None",
        ]


def get_checkers_and_candidates(domain: str, task: Task) -> Tuple[
    Dict[str, GoldChecker], Dict[str, Any], List[Any]
]:
    """Provide checkers, reference candidates, and adversarial foils.
    
    Returns a 3-tuple (checkers, candidates, foils). Foils are candidates that
    must match AT MOST ONE checker; they probe checker disjointness beyond the
    reference candidates.
    """
    
    # Build checkers for this task's interpretations
    checkers = {}
    candidates = {}
    
    for interp in task.interpretations:
        check_id = interp.gold_check
        if check_id not in CHECKERS:
            raise ValueError(f"Unknown checker: {check_id}")
        checkers[interp.id] = CHECKERS[check_id]
        candidates[interp.id] = REFERENCE_IMPLEMENTATIONS[check_id]
    
    # MAJOR 3 FIX: Task-specific near-miss foils
    # Extract base task ID (before _k0, _k1, etc.)
    task_id_base = task.id.split('_k')[0] if '_k' in task.id else task.id
    foils = get_task_specific_foils(task_id_base)

    # NOTE: sandbox/timeout behavior (infinite-loop and blocked-import candidates)
    # is exercised by dedicated unit tests in tests/test_code_spec.py, NOT shipped
    # as per-task foils. Running an infinite-loop foil through validate_domain
    # would cost one full timeout (5s) per checker per task and adds no
    # disjointness signal (it matches nothing). Per-task foils are genuine
    # near-misses of the interpretations only.

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
    print("\nFixed issues:")
    print("  ✓ BLOCKER 1: Entrypoint resolution (allows helpers + imports)")
    print("  ✓ BLOCKER 2: Removed straw ambiguities (filter/sum/max)")
    print("  ✓ MAJOR 1: Sandboxing + timeout")
    print("  ✓ MAJOR 2: Tie-breaking tests for rounding")
    print("  ✓ MAJOR 3: Task-specific near-miss foils")
