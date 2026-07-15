"""Example domain for testing the benchmark framework.

This is a self-contained toy domain to prove the deletion engine and
validation framework work end-to-end. NOT one of the 3 real domains.
"""

from typing import Any, Dict, Tuple

from bench.build import (
    FullSpec,
    InterpretationBranch,
    RequirementClass,
    assemble_task,
    save_tasks,
)
from bench.gold.base import CheckResult, GoldChecker
from common.schema import Task


class SumChecker(GoldChecker):
    """Checks if result is a simple sum."""
    def check(self, candidate: Any) -> CheckResult:
        expected = 7
        passed = candidate == expected
        return CheckResult(passed=passed, details=f"Expected {expected}, got {candidate}")


class ProductChecker(GoldChecker):
    """Checks if result is a product."""
    def check(self, candidate: Any) -> CheckResult:
        expected = 12
        passed = candidate == expected
        return CheckResult(passed=passed, details=f"Expected {expected}, got {candidate}")


class MeanChecker(GoldChecker):
    """Checks if result is arithmetic mean."""
    def check(self, candidate: Any) -> CheckResult:
        expected = 3.5
        passed = abs(candidate - expected) < 0.01
        return CheckResult(passed=passed, details=f"Expected {expected}, got {candidate}")


class StringConcatChecker(GoldChecker):
    """Checks if result is string concatenation."""
    def check(self, candidate: Any) -> CheckResult:
        expected = "helloworld"
        passed = candidate == expected
        return CheckResult(passed=passed, details=f"Expected {expected}, got {candidate}")


class StringSpacedChecker(GoldChecker):
    """Checks if result is space-separated string."""
    def check(self, candidate: Any) -> CheckResult:
        expected = "hello world"
        passed = candidate == expected
        return CheckResult(passed=passed, details=f"Expected {expected}, got {candidate}")


def generate_example_tasks():
    """Generate 3 toy tasks for the example domain."""
    
    task1_spec = FullSpec(
        domain="_example",
        task_id="example_arithmetic_001",
        prompt_core="Given two numbers 3 and 4, combine them.",
        requirement_classes=[
            RequirementClass(
                id="operation_type",
                description="Which arithmetic operation to use",
                clauses=["Use addition to combine the numbers."]
            )
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Addition (target)",
                is_target=True,
                gold_check="sum_checker"
            ),
            InterpretationBranch(
                id="I1",
                description="Multiplication (opened by deletion)",
                is_target=False,
                gold_check="product_checker",
                opened_by="operation_type"
            ),
            InterpretationBranch(
                id="I2",
                description="Mean (opened by deletion)",
                is_target=False,
                gold_check="mean_checker",
                opened_by="operation_type"
            ),
        ],
        key_questions=["What operation should I use: addition, multiplication, or mean?"]
    )
    task1 = assemble_task(task1_spec, k=1, classes_to_delete=["operation_type"])
    
    task2_spec = FullSpec(
        domain="_example",
        task_id="example_string_002",
        prompt_core="Combine the words 'hello' and 'world'.",
        requirement_classes=[
            RequirementClass(
                id="separator",
                description="How to separate the words",
                clauses=["Concatenate without any separator."]
            )
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Direct concatenation (target)",
                is_target=True,
                gold_check="string_concat_checker"
            ),
            InterpretationBranch(
                id="I1",
                description="Space-separated (opened by deletion)",
                is_target=False,
                gold_check="string_spaced_checker",
                opened_by="separator"
            ),
        ],
        key_questions=["Should I add a space between the words?"]
    )
    task2 = assemble_task(task2_spec, k=1, classes_to_delete=["separator"])
    
    # Task 3: unambiguous CONTROL (k=0, prompt == latent_spec). Fresh spec (no
    # aliasing) with only the target interpretation present.
    task3_spec = FullSpec(
        domain="_example",
        task_id="example_arithmetic_003",
        prompt_core="Given two numbers 3 and 4, add them.",
        requirement_classes=[
            RequirementClass(
                id="operation_type",
                description="Which arithmetic operation to use",
                clauses=["Use addition to combine the numbers."]
            )
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Addition (target)",
                is_target=True,
                gold_check="sum_checker"
            ),
            InterpretationBranch(
                id="I1",
                description="Multiplication (opened by deletion)",
                is_target=False,
                gold_check="product_checker",
                opened_by="operation_type"
            ),
        ],
        key_questions=["(control) operation is fully specified as addition"]
    )
    task3 = assemble_task(task3_spec, k=0, classes_to_delete=[])
    
    return [task1, task2, task3]


def get_checkers_and_candidates(domain: str, task: Task) -> Tuple[
    Dict[str, GoldChecker], Dict[str, Any], list
]:
    """Provide checkers, reference candidates, and adversarial foils.

    Returns a 3-tuple (checkers, candidates, foils). Foils are candidates that
    must match AT MOST ONE checker; they probe checker disjointness beyond the
    reference candidates.
    """
    
    checkers_map = {
        "sum_checker": SumChecker(),
        "product_checker": ProductChecker(),
        "mean_checker": MeanChecker(),
        "string_concat_checker": StringConcatChecker(),
        "string_spaced_checker": StringSpacedChecker(),
    }
    
    if task.id == "example_arithmetic_001":
        candidates = {
            "I0": 7,
            "I1": 12,
            "I2": 3.5,
        }
        foils = [0, 42, -1]  # match no arithmetic checker
    elif task.id == "example_string_002":
        candidates = {
            "I0": "helloworld",
            "I1": "hello world",
        }
        foils = ["HELLOWORLD", "hello-world", ""]  # match neither checker
    elif task.id == "example_arithmetic_003":
        candidates = {
            "I0": 7,
        }
        foils = [0, 12, 3.5]  # none should match the sole target checker
    else:
        raise ValueError(f"Unknown task: {task.id}")
    
    checkers = {}
    for interp in task.interpretations:
        gold = interp.gold_check
        if gold.endswith("__combdef"):
            gold = gold[: -len("__combdef")]
        checkers[interp.id] = checkers_map[gold]
    
    return checkers, candidates, foils


if __name__ == "__main__":
    from pathlib import Path
    
    tasks = generate_example_tasks()
    output_path = Path(__file__).parent.parent / "data" / "_example.jsonl"
    output_path.parent.mkdir(exist_ok=True)
    save_tasks(tasks, str(output_path))
    print(f"Generated {len(tasks)} example tasks -> {output_path}")
