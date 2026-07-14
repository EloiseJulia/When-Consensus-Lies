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
            # Supervisor itself timed out (shouldn't happen in practice)
            result_tuple = (False, "Supervisor timeout (unexpected)")
            _RESULT_CACHE[cache_key] = result_tuple
            return CheckResult(passed=False, details=f"{self.description} - {result_tuple[1]}")

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
        
        if verdict is None:
            msg = "No verdict in supervisor output"
            _RESULT_CACHE[cache_key] = (False, msg)
            return CheckResult(passed=False, details=f"{self.description} - {msg}")

        passed = verdict.get("status") == "pass"
        msg = verdict.get("message", "")
        _RESULT_CACHE[cache_key] = (passed, msg)
        return CheckResult(passed=passed, details=f"{self.description} - {msg}")


# ============================================================================
# PROBLEM LIBRARY - Data analysis problems with requirement classes
# ============================================================================

def problem_compute_mean():
    """Compute mean with ambiguous missing-value handling."""
    
    spec = FullSpec(
        domain="data_analysis",
        task_id="data_mean_001",
        # GENUINE: the prompt states the data MAY contain missing entries, but
        # is neutral on how to handle them once the clause is deleted.
        prompt_core="""Write a function `compute_mean` that calculates the average of a list of numbers that may contain missing entries represented as None.""",
        requirement_classes=[
            RequirementClass(
                id="missing_values",
                description="How to handle None/missing values",
                clauses=["Ignore None values in the calculation (skip them)."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Skip missing values (target - the common aggregation default, "
                            "like statistics/pandas which drop missing entries)",
                is_target=True,
                gold_check="mean_skip_none"
            ),
            InterpretationBranch(
                id="I1",
                description="Propagate None (return None if any None present)",
                is_target=False,
                gold_check="mean_propagate_none",
                opened_by="missing_values"
            ),
        ],
        key_questions=[
            "Should I skip None values or propagate None if any are present?"
        ]
    )
    
    return spec


def problem_compute_variance():
    """Compute variance with ambiguous population vs sample formula."""
    
    spec = FullSpec(
        domain="data_analysis",
        task_id="data_variance_001",
        # GENUINE: for a COMPLETE population, population variance (÷n) is the
        # natural default; the (deleted) clause states that default, and the
        # sample formula (÷n-1) is the plausible alternative-convention delusion.
        prompt_core="""Write a function `compute_variance` that calculates the variance of a list of numbers representing a complete population of measurements.""",
        requirement_classes=[
            RequirementClass(
                id="formula",
                description="Population vs sample variance",
                clauses=["Use the population variance formula (divide by n)."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Population variance (÷n, target - natural default for a "
                            "complete population, e.g. numpy.var default ddof=0)",
                is_target=True,
                gold_check="var_population"
            ),
            InterpretationBranch(
                id="I1",
                description="Sample variance (÷n-1, e.g. statistics.variance)",
                is_target=False,
                gold_check="var_sample",
                opened_by="formula"
            ),
        ],
        key_questions=[
            "Should I use population variance (÷n) or sample variance (÷n-1)?"
        ]
    )
    
    return spec


def problem_compute_median():
    """Compute median with ambiguous even-count averaging."""
    
    spec = FullSpec(
        domain="data_analysis",
        task_id="data_median_001",
        # GENUINE: "median" for even-length lists - average the middle two or pick one?
        prompt_core="""Write a function `compute_median` that finds the median value of a list of numbers.""",
        requirement_classes=[
            RequirementClass(
                id="even_handling",
                description="How to handle even-length lists",
                clauses=["For even-length lists, return the average of the two middle values."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Average two middle values (target - Python statistics.median)",
                is_target=True,
                gold_check="median_average"
            ),
            InterpretationBranch(
                id="I1",
                description="Return lower middle value",
                is_target=False,
                gold_check="median_lower",
                opened_by="even_handling"
            ),
        ],
        key_questions=[
            "For even-length lists, should I average the two middle values or pick one?"
        ]
    )
    
    return spec


def problem_filter_records():
    """Filter records with ambiguous threshold boundary (inclusive vs exclusive)."""
    
    spec = FullSpec(
        domain="data_analysis",
        task_id="data_filter_001",
        # GENUINE: "meets a minimum threshold" is neutral on whether the boundary
        # value itself qualifies. The (deleted) clause states the natural inclusive
        # reading ("minimum" -> the value reaching the threshold counts).
        prompt_core="""Write a function `filter_records` that filters a list of records (dicts with 'value' key) to keep those that meet a given minimum threshold.""",
        requirement_classes=[
            RequirementClass(
                id="boundary",
                description="Whether threshold is inclusive or exclusive",
                clauses=["A record meets the threshold if its value is greater than or equal to the threshold (inclusive)."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Inclusive (value >= threshold, target - 'minimum' includes "
                            "the boundary value)",
                is_target=True,
                gold_check="filter_inclusive"
            ),
            InterpretationBranch(
                id="I1",
                description="Exclusive (value > threshold, strictly above)",
                is_target=False,
                gold_check="filter_exclusive",
                opened_by="boundary"
            ),
        ],
        key_questions=[
            "Does meeting the minimum threshold include values equal to it (>=), or only above it (>)?"
        ]
    )
    
    return spec


def problem_group_by_key():
    """Group records with ambiguous sort order of groups."""
    
    spec = FullSpec(
        domain="data_analysis",
        task_id="data_group_001",
        # GENUINE: "group by category" is neutral on the order of groups
        prompt_core="""Write a function `group_by_key` that groups a list of records (dicts with 'category' and 'value' keys) by category, returning a dict mapping each category to a list of its values.""",
        requirement_classes=[
            RequirementClass(
                id="list_order",
                description="Order of values within each category's list",
                clauses=["Preserve the original order of values within each category's list."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Preserve original order (target - dict iteration order)",
                is_target=True,
                gold_check="group_preserve_order"
            ),
            InterpretationBranch(
                id="I1",
                description="Sort values within each category",
                is_target=False,
                gold_check="group_sort_values",
                opened_by="list_order"
            ),
        ],
        key_questions=[
            "Should I preserve the original order of values or sort them within each category?"
        ]
    )
    
    return spec


# ============================================================================
# REFERENCE IMPLEMENTATIONS - One per interpretation per problem
# ============================================================================

REFERENCE_IMPLEMENTATIONS = {
    # Compute mean
    "mean_skip_none": """
def compute_mean(numbers):
    filtered = [x for x in numbers if x is not None]
    return sum(filtered) / len(filtered) if filtered else 0.0
""",
    "mean_propagate_none": """
def compute_mean(numbers):
    if None in numbers:
        return None
    return sum(numbers) / len(numbers) if numbers else 0.0
""",
    
    # Compute variance
    "var_sample": """
def compute_variance(numbers):
    n = len(numbers)
    if n < 2:
        return 0.0
    mean = sum(numbers) / n
    return sum((x - mean) ** 2 for x in numbers) / (n - 1)
""",
    "var_population": """
def compute_variance(numbers):
    n = len(numbers)
    if n == 0:
        return 0.0
    mean = sum(numbers) / n
    return sum((x - mean) ** 2 for x in numbers) / n
""",
    
    # Compute median
    "median_average": """
def compute_median(numbers):
    sorted_nums = sorted(numbers)
    n = len(sorted_nums)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_nums[mid - 1] + sorted_nums[mid]) / 2.0
    else:
        return sorted_nums[mid]
""",
    "median_lower": """
def compute_median(numbers):
    sorted_nums = sorted(numbers)
    n = len(sorted_nums)
    if n % 2 == 0:
        return sorted_nums[n // 2 - 1]
    else:
        return sorted_nums[n // 2]
""",
    
    # Filter records
    "filter_exclusive": """
def filter_records(records, threshold):
    return [r for r in records if r['value'] > threshold]
""",
    "filter_inclusive": """
def filter_records(records, threshold):
    return [r for r in records if r['value'] >= threshold]
""",
    
    # Group by key
    "group_preserve_order": """
def group_by_key(records):
    result = {}
    for r in records:
        cat = r['category']
        if cat not in result:
            result[cat] = []
        result[cat].append(r['value'])
    return result
""",
    "group_sort_values": """
def group_by_key(records):
    result = {}
    for r in records:
        cat = r['category']
        if cat not in result:
            result[cat] = []
        result[cat].append(r['value'])
    for cat in result:
        result[cat].sort()
    return result
""",
}


# ============================================================================
# TEST CASES - Input/output pairs for each interpretation
# ============================================================================

TEST_CASES = {
    # Compute mean - cases that DISTINGUISH skip vs propagate None
    "mean_skip_none": [
        ([1, 2, 3, 4], 2.5),
        ([10, None, 20], 15.0),  # Discriminating: skip None -> (10+20)/2 = 15
        ([5], 5.0),
    ],
    "mean_propagate_none": [
        ([1, 2, 3, 4], 2.5),
        ([10, None, 20], None),  # Discriminating: propagate None
        ([5], 5.0),
    ],
    
    # Compute variance - cases that DISTINGUISH sample (n-1) vs population (n)
    "var_sample": [
        ([1, 2, 3, 4, 5], 2.5),  # sample var = 10/(5-1) = 2.5
        ([10, 20], 50.0),  # sample var = 100/(2-1) = 50
    ],
    "var_population": [
        ([1, 2, 3, 4, 5], 2.0),  # population var = 10/5 = 2.0
        ([10, 20], 25.0),  # population var = 100/2 = 25
    ],
    
    # Compute median - cases that DISTINGUISH average vs lower for even-length
    # AND that separate median from a plain-mean impostor (BLOCKER fix): the
    # asymmetric cases below have mean != median so "return the mean" fails.
    "median_average": [
        ([1, 2, 3], 2.0),
        ([1, 2, 3, 4], 2.5),  # Discriminating: average of 2 and 3
        ([10, 20], 15.0),  # Discriminating: average of 10 and 20
        ([1, 1, 100], 1.0),  # Anti-mean: median=1 but mean=34.0
        ([1, 2, 3, 100], 2.5),  # Anti-mean: median avg(2,3)=2.5 but mean=26.5
    ],
    "median_lower": [
        ([1, 2, 3], 2.0),
        ([1, 2, 3, 4], 2.0),  # Discriminating: lower middle value
        ([10, 20], 10.0),  # Discriminating: lower middle value
        ([1, 1, 100], 1.0),  # odd-length: middle value
        ([1, 2, 3, 100], 2.0),  # even-length: lower middle = 2
    ],
    
    # Filter records - cases that DISTINGUISH exclusive (>) vs inclusive (>=)
    "filter_exclusive": [
        (([{'value': 5}, {'value': 10}, {'value': 15}], 10), [{'value': 15}]),  # > 10 excludes 10
        (([{'value': 3}, {'value': 7}], 5), [{'value': 7}]),
    ],
    "filter_inclusive": [
        (([{'value': 5}, {'value': 10}, {'value': 15}], 10), [{'value': 10}, {'value': 15}]),  # >= 10 includes 10
        (([{'value': 3}, {'value': 7}], 5), [{'value': 7}]),
    ],
    
    # Group by key - cases that DISTINGUISH preserve vs sort
    "group_preserve_order": [
        (
            [{'category': 'A', 'value': 30}, {'category': 'B', 'value': 10}, 
             {'category': 'A', 'value': 10}, {'category': 'B', 'value': 20}],
            {'A': [30, 10], 'B': [10, 20]}  # Discriminating: original order preserved
        ),
    ],
    "group_sort_values": [
        (
            [{'category': 'A', 'value': 30}, {'category': 'B', 'value': 10}, 
             {'category': 'A', 'value': 10}, {'category': 'B', 'value': 20}],
            {'A': [10, 30], 'B': [10, 20]}  # Discriminating: values sorted
        ),
    ],
}


# ============================================================================
# CHECKERS REGISTRY
# ============================================================================

CHECKERS = {}
ENTRYPOINTS = {
    # Map checker IDs to their entrypoint function names
    "mean_skip_none": "compute_mean",
    "mean_propagate_none": "compute_mean",
    "var_sample": "compute_variance",
    "var_population": "compute_variance",
    "median_average": "compute_median",
    "median_lower": "compute_median",
    "filter_exclusive": "filter_records",
    "filter_inclusive": "filter_records",
    "group_preserve_order": "group_by_key",
    "group_sort_values": "group_by_key",
}

for check_id, test_cases in TEST_CASES.items():
    entrypoint = ENTRYPOINTS[check_id]
    CHECKERS[check_id] = DataChecker(test_cases, entrypoint=entrypoint, description=check_id)


# ============================================================================
# TASK GENERATION
# ============================================================================

def generate_tasks() -> List[Task]:
    """Generate all data_analysis tasks with multiple deletion patterns.

    key_questions invariant (spot-check fix): a task's key_questions are exactly
    the clarifying questions for the axes DELETED in that variant — never the
    full base-problem set. Hence for every emitted task:
        len(key_questions) == ambiguity_level == len(interpretations) - 1
    and the k=0 control has an EMPTY key_questions list. key_questions is the
    gold for the Direction-B (false-surfacing) detector, so a stale question on
    the control would invert that metric; this keeps it deterministic.
    """

    problems = [
        problem_compute_mean(),
        problem_compute_variance(),
        problem_compute_median(),
        problem_filter_records(),
        problem_group_by_key(),
    ]

    tasks = []

    for base_spec in problems:
        base_id = base_spec.task_id
        n_req = len(base_spec.requirement_classes)

        # Deterministic axis -> clarifying-question map (parallel by construction).
        if len(base_spec.key_questions) != n_req:
            raise ValueError(
                f"{base_id}: key_questions ({len(base_spec.key_questions)}) must "
                f"be parallel to requirement_classes ({n_req})"
            )
        qmap = {
            rc.id: q
            for rc, q in zip(base_spec.requirement_classes, base_spec.key_questions)
        }

        def _emit(spec_copy, k, delete_ids):
            task = assemble_task(spec_copy, k=k, classes_to_delete=delete_ids)
            # Override the full-spec key_questions with ONLY the deleted axes.
            task.key_questions = [qmap[cid] for cid in delete_ids]
            return task

        # k=0 CONTROL: unambiguous -> no deleted axes -> no key_questions.
        task_k0 = _emit(base_spec, 0, [])
        task_k0.id = f"{base_id}_k0"
        tasks.append(task_k0)

        # k=1: delete each requirement individually.
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

    return tasks


# ============================================================================
# VALIDATION LOADER
# Task-specific near-miss foils for each problem
# ============================================================================

def get_task_specific_foils(task_id_base: str) -> List[str]:
    """Generate task-specific near-miss foils that test checker boundaries.
    
    Each task gets plausible near-miss foils that might match multiple
    interpretations if checkers aren't truly disjoint.
    """
    
    if "data_mean" in task_id_base:
        return [
            # Near-miss: treats None as zero instead of skip/propagate
            """
def compute_mean(numbers):
    total = sum(0 if x is None else x for x in numbers)
    return total / len(numbers) if numbers else 0.0
""",
            # Near-miss: wrong denominator
            """
def compute_mean(numbers):
    filtered = [x for x in numbers if x is not None]
    return sum(filtered) / len(numbers) if numbers else 0.0
""",
            # Always-fail foil
            """
def compute_mean(numbers):
    raise NotImplementedError()
""",
        ]
    
    elif "data_variance" in task_id_base:
        return [
            # Near-miss: uses n instead of n-1 but with wrong mean calculation
            """
def compute_variance(numbers):
    n = len(numbers)
    if n == 0:
        return 0.0
    mean = sum(numbers) / (n + 1)
    return sum((x - mean) ** 2 for x in numbers) / n
""",
            # Near-miss: standard deviation instead of variance
            """
def compute_variance(numbers):
    n = len(numbers)
    if n < 2:
        return 0.0
    mean = sum(numbers) / n
    return (sum((x - mean) ** 2 for x in numbers) / (n - 1)) ** 0.5
""",
            # Wrong implementation
            """
def compute_variance(numbers):
    return 0.0
""",
        ]
    
    elif "data_median" in task_id_base:
        return [
            # Near-miss: uses upper middle instead of lower or average
            """
def compute_median(numbers):
    sorted_nums = sorted(numbers)
    n = len(sorted_nums)
    if n % 2 == 0:
        return sorted_nums[n // 2]
    else:
        return sorted_nums[n // 2]
""",
            # Near-miss: doesn't sort
            """
def compute_median(numbers):
    n = len(numbers)
    mid = n // 2
    if n % 2 == 0:
        return (numbers[mid - 1] + numbers[mid]) / 2.0
    else:
        return numbers[mid]
""",
            # Wrong: returns mean instead of median
            """
def compute_median(numbers):
    return sum(numbers) / len(numbers)
""",
        ]
    
    elif "data_filter" in task_id_base:
        return [
            # Near-miss: uses < instead of > or >=
            """
def filter_records(records, threshold):
    return [r for r in records if r['value'] < threshold]
""",
            # Near-miss: filters out instead of keeping
            """
def filter_records(records, threshold):
    return [r for r in records if r['value'] <= threshold]
""",
            # Wrong: empty result
            """
def filter_records(records, threshold):
    return []
""",
        ]
    
    elif "data_group" in task_id_base:
        return [
            # Near-miss: sorts by key instead of values
            """
def group_by_key(records):
    result = {}
    for r in sorted(records, key=lambda x: x['category']):
        cat = r['category']
        if cat not in result:
            result[cat] = []
        result[cat].append(r['value'])
    return result
""",
            # Near-miss: reverses values within each category
            """
def group_by_key(records):
    result = {}
    for r in records:
        cat = r['category']
        if cat not in result:
            result[cat] = []
        result[cat].append(r['value'])
    for cat in result:
        result[cat].reverse()
    return result
""",
            # Wrong: flattens all values
            """
def group_by_key(records):
    return {'all': [r['value'] for r in records]}
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
    
    # Task-specific near-miss foils
    # Extract base task ID (before _k0, _k1, etc.)
    task_id_base = task.id.split('_k')[0] if '_k' in task.id else task.id
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
