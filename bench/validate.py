"""Validation framework for benchmark distinguishability.

Ensures every interpretation is DETERMINISTICALLY DISTINGUISHED:
- Each interpretation's reference candidate passes ONLY that interpretation's checker
- No ambiguity in labeling (mutual exclusion)
"""

import argparse
import importlib
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from bench.build import load_tasks
from bench.gold.base import CheckResult, GoldChecker, get_checker
from common.schema import Task


class AmbiguousLabelError(Exception):
    """Raised when a candidate matches more than one interpretation checker.

    This makes labeling ambiguity LOUD instead of silent — the core guarantee
    the Phase-2 labeler relies on.
    """


def assign_label(
    candidate: Any,
    checkers: Dict[str, GoldChecker],
    perp_label: str = "I_perp",
) -> str:
    """Deterministically label a candidate against a task's checkers.

    Returns the single matching interpretation id, `perp_label` if none match,
    and RAISES AmbiguousLabelError if two or more match (never silent).
    """
    matches = [cid for cid, ch in checkers.items() if ch.check(candidate).passed]
    if len(matches) > 1:
        raise AmbiguousLabelError(
            f"Candidate matches multiple interpretations: {matches}"
        )
    return matches[0] if matches else perp_label


def validate_task(
    task: Task,
    checkers: Dict[str, GoldChecker],
    candidates: Dict[str, Any],
    foils: Optional[List[Any]] = None,
    require_foils: bool = False,
) -> Dict[str, Any]:
    """Validate that a task's interpretations are deterministically distinguished.
    
    Args:
        task: The task to validate
        checkers: Map from interpretation ID to gold checker
        candidates: Map from interpretation ID to reference candidate
        foils: Optional adversarial candidates that must match AT MOST ONE
               checker. Foils probe checker disjointness beyond the reference
               candidates (defends against overlapping checkers that would
               certify 100% while a real answer matches multiple interps).
        require_foils: When True (used for DOMAIN CERTIFICATION), a task with no
               foils FAILS closed — a domain cannot opt out of the disjointness
               defense and still be certified distinguishable.
    
    Returns:
        Dict with:
        - distinguishable: bool (True if all interpretations uniquely matched)
        - results: List of check results for each (interpretation, candidate) pair
        - errors: List of error messages if validation failed
    """
    errors = []
    results = []

    # Structural invariant: EXACTLY ONE target interpretation, canonical id I0.
    targets = [i for i in task.interpretations if i.is_target]
    if len(targets) != 1:
        errors.append(
            f"Task must have exactly one target interpretation, got {len(targets)}"
        )
    elif targets[0].id != "I0":
        errors.append(
            f"Target interpretation must have id 'I0', got '{targets[0].id}'"
        )
    for interp in task.interpretations:
        if interp.id == "I0" and not interp.is_target:
            errors.append("Interpretation id 'I0' is reserved for the target")

    # Fail-closed: certification requires adversarial foils.
    if require_foils and not foils:
        errors.append(
            "Domain certification requires a non-empty adversarial foil list "
            "(fail-closed disjointness defense)"
        )

    # Benchmark-validity: a task claiming ambiguity (level>=1) must actually
    # open at least one non-target interpretation.
    if task.ambiguity_level >= 1:
        n_nontarget = sum(1 for i in task.interpretations if not i.is_target)
        if n_nontarget < 1:
            errors.append(
                f"ambiguity_level={task.ambiguity_level} but no non-target "
                f"interpretation is present"
            )
    
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

    # Foils: adversarial candidates that must match AT MOST ONE checker.
    for idx, foil in enumerate(foils or []):
        foil_matches = []
        for check_interp in task.interpretations:
            if checkers[check_interp.id].check(foil).passed:
                foil_matches.append(check_interp.id)
        results.append({
            "candidate_for": f"foil[{idx}]",
            "matches": foil_matches,
        })
        if len(foil_matches) > 1:
            errors.append(
                f"Foil #{idx} matches MULTIPLE checkers: {foil_matches} "
                f"(checkers are not disjoint)"
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
            loaded = checker_loader(domain, task)
            if len(loaded) == 3:
                checkers, candidates, foils = loaded
            else:
                checkers, candidates = loaded
                foils = None
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
        
        validation = validate_task(
            task, checkers, candidates, foils=foils, require_foils=True
        )
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
    
    # Dynamically import the domain package's checker loader (plug-in contract:
    # every domain exposes get_checkers_and_candidates(domain, task)).
    try:
        domain_mod = importlib.import_module(f"bench.{args.domain}")
    except ModuleNotFoundError as exc:
        raise SystemExit(
            f"Domain package 'bench.{args.domain}' not found: {exc}"
        )
    try:
        get_checkers_and_candidates = domain_mod.get_checkers_and_candidates
    except AttributeError:
        raise SystemExit(
            f"Domain 'bench.{args.domain}' must define "
            f"get_checkers_and_candidates(domain, task)"
        )
    
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
