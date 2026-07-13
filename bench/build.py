"""Deletion-based ambiguity generation for benchmark tasks.

The deletion engine is model-agnostic and structural:
1. Full spec = set of typed requirement clauses (each tagged with a requirement CLASS)
2. delete_requirements(full_spec, k) removes k requirement classes
3. Result: underdetermined prompt + interpretation branches opened by each deletion

Domain slices supply:
- Full spec with tagged requirement classes
- Per-interpretation gold checkers
- Reference candidates for validation
"""

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Set

from common.schema import Interpretation, Task


@dataclass
class RequirementClass:
    """A category of requirements that can be deleted to create ambiguity."""
    id: str  # e.g., "error_handling", "output_format", "edge_cases"
    description: str
    clauses: List[str]  # Actual requirement text that appears in spec


@dataclass
class InterpretationBranch:
    """Describes one interpretation that becomes valid after deletion."""
    id: str  # "I0" (target) | "I1" | ... | "I_perp"
    description: str
    is_target: bool  # I0 = True, others = False
    gold_check: str  # Points to checker in gold/
    opened_by: Optional[str] = None  # Which requirement class deletion opened this branch


@dataclass
class FullSpec:
    """Complete specification with all requirement classes present."""
    domain: str
    task_id: str
    prompt_core: str  # Base task description (always present)
    requirement_classes: List[RequirementClass]
    interpretations: List[InterpretationBranch]
    key_questions: List[str]  # Questions that recover deleted requirements


def delete_requirements(
    full_spec: FullSpec,
    k: int,
    classes_to_delete: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Delete k requirement classes to create an ambiguous prompt.
    
    Args:
        full_spec: Complete specification
        k: Number of requirement classes to delete (ambiguity level)
        classes_to_delete: Optional list of class IDs to delete (if None, uses first k)
    
    Returns:
        Dict with:
        - underdetermined_prompt: Prompt with k classes removed
        - latent_spec: Full spec text
        - deleted_classes: List of deleted class IDs
        - opened_interpretations: Interpretations that became valid
    """
    if classes_to_delete is None:
        classes_to_delete = [rc.id for rc in full_spec.requirement_classes[:k]]
    elif len(classes_to_delete) != k:
        raise ValueError(f"Must delete exactly {k} classes, got {len(classes_to_delete)}")
    
    deleted_set = set(classes_to_delete)
    
    # Build underdetermined prompt (core + non-deleted requirements)
    kept_classes = [rc for rc in full_spec.requirement_classes if rc.id not in deleted_set]
    
    prompt_parts = [full_spec.prompt_core]
    for rc in kept_classes:
        prompt_parts.extend(rc.clauses)
    underdetermined_prompt = "\n\n".join(prompt_parts)
    
    # Build full latent spec
    latent_parts = [full_spec.prompt_core]
    for rc in full_spec.requirement_classes:
        latent_parts.extend(rc.clauses)
    latent_spec = "\n\n".join(latent_parts)
    
    # Find interpretations opened by this deletion
    opened_interpretations = []
    for interp in full_spec.interpretations:
        if interp.is_target:
            opened_interpretations.append(interp)  # I0 always included
        elif interp.opened_by in deleted_set or interp.opened_by is None:
            opened_interpretations.append(interp)
    
    return {
        "underdetermined_prompt": underdetermined_prompt,
        "latent_spec": latent_spec,
        "deleted_classes": list(deleted_set),
        "opened_interpretations": opened_interpretations,
    }


def assemble_task(
    full_spec: FullSpec,
    k: int,
    classes_to_delete: Optional[List[str]] = None
) -> Task:
    """Assemble a Task record from a full spec with k requirement classes deleted.
    
    Args:
        full_spec: Complete specification
        k: Ambiguity level (1/2/3)
        classes_to_delete: Optional specific classes to delete
    
    Returns:
        Task with underdetermined prompt and interpretation branches
    """
    deletion_result = delete_requirements(full_spec, k, classes_to_delete)
    
    interpretations = [
        Interpretation(
            id=ib.id,
            is_target=ib.is_target,
            gold_check=ib.gold_check
        )
        for ib in deletion_result["opened_interpretations"]
    ]
    
    return Task(
        id=full_spec.task_id,
        domain=full_spec.domain,
        prompt=deletion_result["underdetermined_prompt"],
        latent_spec=deletion_result["latent_spec"],
        interpretations=interpretations,
        ambiguity_level=k,
        key_questions=full_spec.key_questions
    )


def task_to_jsonl(task: Task) -> str:
    """Serialize a Task to a single JSON line."""
    return json.dumps(asdict(task))


def task_from_jsonl(line: str) -> Task:
    """Deserialize a Task from a JSON line."""
    data = json.loads(line)
    # Reconstruct nested dataclasses
    data["interpretations"] = [
        Interpretation(**interp) for interp in data["interpretations"]
    ]
    return Task(**data)


def save_tasks(tasks: List[Task], path: str) -> None:
    """Save tasks to a JSONL file."""
    with open(path, "w", encoding="utf-8") as f:
        for task in tasks:
            f.write(task_to_jsonl(task) + "\n")


def load_tasks(path: str) -> List[Task]:
    """Load tasks from a JSONL file."""
    tasks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(task_from_jsonl(line))
    return tasks
