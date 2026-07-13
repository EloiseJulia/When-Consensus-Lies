"""Validation framework for benchmark distinguishability.

Ensures every interpretation is DETERMINISTICALLY DISTINGUISHED:
- Each interpretation's reference candidate passes ONLY that interpretation's checker
- No ambiguity in labeling (mutual exclusion)
"""

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from bench.build import load_tasks
from bench.gold.base import CheckResult, GoldChecker, get_checker
from common.schema import Task


def validate_task(
    task: Task,
    checkers: Dict[str, GoldChecker],
    candidates: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate that a task's interpretations are deterministically distinguished.
    
    Args:
        task: The task to validate
        checkers: Map from interpretation ID to gold checker
        candidates: Map from interpretation ID to reference candidate
    
    Returns:
        Dict with:
        - distinguishable: bool (True if all interpretations uniquely matched)
        - results: List of check results for each (interpretation, candidate) pair
        - errors: List of error messages if validation failed
    """
    errors = []
    results = []
    
    # Check each interpretation has a checker and candidate
    for interp in task.interpretations:
        if interp.id not in checkers:
            errors.append(f"Missing checker for interpretation {interp.id}")
        if interp.id not in candidates:
            errors.append(f"Missing reference candidate for interpretation {interp.id}")
    
    if errors:
        return {
            "distinguishable": False,
            "results": [],
            "errors": errors
        }
    
    # For each interpretation's reference candidate, check against ALL checkers
    for interp in task.interpretations:
        candidate = candidates[interp.id]
        matches = []
        
        for check_interp in task.interpretations:
            checker = checkers[check_interp.id]
            result = checker.check(candidate)
            results.append({
                "candidate_for": interp.id,
                "checked_by": check_interp.id,
                "passed": result.passed,
                "details": result.details
            })
            
            if result.passed:
                matches.append(check_interp.id)
        
        # Candidate should match EXACTLY ONE checker (its own)
        if len(matches) == 0:
            errors.append(f"Candidate for {interp.id} matches NO checkers")
        elif len(matches) > 1:
            errors.append(
                f"Candidate for {interp.id} matches MULTIPLE checkers: {matches}"
            )
        elif matches[0] != interp.id:
            errors.append(
                f"Candidate for {interp.id} matches WRONG checker: {matches[0]}"
            )
    
    return {
        "distinguishable": len(errors) == 0,
        "results": results,
        "errors": errors
    }


def validate_domain(
    domain: str,
    data_path: Optional[Path] = None,
    checker_loader: Optional[callable] = None
) -> Dict[str, Any]:
    """Validate all tasks in a domain.
    
    Args:
        domain: Domain name (e.g., "_example", "code_spec")
        data_path: Optional path to JSONL file (defaults to bench/data/<domain>.jsonl)
        checker_loader: Optional function that takes (domain, task) and returns
                       (checkers_dict, candidates_dict). If None, uses global registry.
    
    Returns:
        Dict with validation summary:
        - domain: str
        - task_count: int
        - ambiguity_distribution: dict of level -> count
        - distinguishable_count: int
        - distinguishable_pct: float
        - failed_tasks: list of task IDs that failed validation
    """
    if data_path is None:
        data_path = Path(__file__).parent / "data" / f"{domain}.jsonl"
    
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    tasks = load_tasks(str(data_path))
    
    ambiguity_dist = defaultdict(int)
    distinguishable_count = 0
    failed_tasks = []
    
    for task in tasks:
        ambiguity_dist[task.ambiguity_level] += 1
        
        # Load checkers and candidates for this task
        if checker_loader:
            checkers, candidates = checker_loader(domain, task)
        else:
            # Use global registry (domain slices must register their checkers)
            checkers = {}
            for interp in task.interpretations:
                checker = get_checker(interp.gold_check)
                if checker is None:
                    raise KeyError(
                        f"No checker registered for {interp.gold_check} "
                        f"(task {task.id}, interpretation {interp.id})"
                    )
                checkers[interp.id] = checker
            
            # Candidates must be provided by checker_loader
            raise NotImplementedError(
                "Default candidate loading not implemented - "
                "provide checker_loader that returns (checkers, candidates)"
            )
        
        validation = validate_task(task, checkers, candidates)
        if validation["distinguishable"]:
            distinguishable_count += 1
        else:
            failed_tasks.append({
                "task_id": task.id,
                "errors": validation["errors"]
            })
    
    return {
        "domain": domain,
        "task_count": len(tasks),
        "ambiguity_distribution": dict(ambiguity_dist),
        "distinguishable_count": distinguishable_count,
        "distinguishable_pct": 100.0 * distinguishable_count / len(tasks) if tasks else 0.0,
        "failed_tasks": failed_tasks
    }


def main():
    parser = argparse.ArgumentParser(
        description="Validate benchmark task distinguishability"
    )
    parser.add_argument(
        "--domain",
        required=True,
        help="Domain to validate (e.g., _example, code_spec, data_analysis)"
    )
    parser.add_argument(
        "--data-path",
        type=Path,
        help="Optional path to JSONL file (defaults to bench/data/<domain>.jsonl)"
    )
    
    args = parser.parse_args()
    
    # Note: This CLI requires domains to register their checkers and provide
    # a checker_loader function. For the _example domain, this is handled in
    # bench/_example/__init__.py
    
    from bench._example import get_checkers_and_candidates
    
    summary = validate_domain(
        args.domain,
        args.data_path,
        checker_loader=get_checkers_and_candidates
    )
    
    print(f"\n=== Validation Summary: {summary['domain']} ===")
    print(f"Tasks: {summary['task_count']}")
    print(f"Ambiguity distribution: {summary['ambiguity_distribution']}")
    print(f"Distinguishable: {summary['distinguishable_count']} / {summary['task_count']} "
          f"({summary['distinguishable_pct']:.1f}%)")
    
    if summary['failed_tasks']:
        print(f"\n⚠️  {len(summary['failed_tasks'])} tasks FAILED validation:")
        for failure in summary['failed_tasks']:
            print(f"  - {failure['task_id']}:")
            for error in failure['errors']:
                print(f"      {error}")
    else:
        print("\n✅ All tasks passed validation (100% distinguishable)")


if __name__ == "__main__":
    main()
