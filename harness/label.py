"""Label assignment via executable signals — NOT LLM judge.

Phase 0 MOCK: deterministic mapping for smoke tests.
Real Phase 2: executable signals from error types, tracebacks, numerical values.
"""

import hashlib
from typing import Dict
from common.schema import AgentRun, Task


def _stable_index(text: str, modulo: int) -> int:
    """Deterministic, cross-process-stable index from a string.

    Uses hashlib (NOT Python's builtin hash(), which is per-process salted and
    would make labeling non-reproducible across interpreter restarts).
    """
    if modulo <= 0:
        raise ValueError("modulo must be positive")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest, 16) % modulo


def label_run(run: AgentRun, task: Task) -> str:
    """Assign interpretation label to an agent run via executable signal.
    
    Phase 0 MOCK: deterministic mapping based on output hash.
    Real implementation in Phase 2 will use:
        - Code domain: error types, traceback patterns, test pass/fail
        - Data domain: numerical value clusters, dataframe assertions
        - Policy domain: rubric matching (weaker, possibly human-labeled)
    
    CRITICAL: NEVER use an LLM judge here — violates executable gold principle.
    
    Args:
        run: AgentRun with output field
        task: Task with interpretations
    
    Returns:
        Label string (one of task.interpretation.id values)
    """
    # Phase 0 mock: hash output to an interpretation
    # Real logic deferred to Phase 2, marked clearly
    
    # === MOCK LOGIC (PHASE 0 ONLY) ===
    # Deterministic across processes (hashlib, not builtin hash()).
    label_idx = _stable_index(run.output, len(task.interpretations))
    return task.interpretations[label_idx].id


# === DEFERRED TO PHASE 2 ===
# Real executable signal extractors

def label_code_domain(run: AgentRun, task: Task) -> str:
    """Extract label from code execution signals. [PHASE 2]
    
    Strategy:
        - Run code in sandbox
        - Capture: exception types, traceback patterns, test outcomes
        - Map to interpretations via gold/ checkers
    """
    raise NotImplementedError("Phase 2: code domain labeling via execution")


def label_data_domain(run: AgentRun, task: Task) -> str:
    """Extract label from data analysis outputs. [PHASE 2]
    
    Strategy:
        - Parse numerical outputs, dataframe shapes
        - Cluster via deterministic thresholds
        - Map to interpretations via gold assertions
    """
    raise NotImplementedError("Phase 2: data domain labeling via value clustering")


def label_policy_domain(run: AgentRun, task: Task) -> str:
    """Extract label from policy text outputs. [PHASE 2]
    
    Strategy:
        - Rubric-based scoring (deterministic if possible)
        - Human labels as fallback (acknowledged limitation)
        - Avoid LLM-as-judge (violates executable gold)
    """
    raise NotImplementedError("Phase 2: policy domain labeling (weakest signal)")
