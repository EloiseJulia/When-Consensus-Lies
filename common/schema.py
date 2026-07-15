"""FROZEN after Phase 0 — changes require owner sign-off.

Core data structures defining the interface contract for the project.
These dataclasses mirror AI-Execution-Plan §3.

Amendment 02 (owner-approved 2026-07-15): added Task.regime field.
See paper/preregistration/2026-07-15-amendment-02-regime-field.md.
"""

from dataclasses import dataclass
from typing import List, Optional

# Single source of truth for allowed regime values (Amendment 02).
VALID_REGIMES = ("H1_external", "H2_derivable", None)


@dataclass
class Interpretation:
    """A single interpretation of an ambiguous task.
    
    I0 = true hidden intent (target)
    I1..Im = plausible misinterpretations
    I_perp = degenerate/noise outputs
    """
    id: str  # "I0" | "I1" | ... | "I_perp"
    is_target: bool
    gold_check: str  # Points to executable checker in gold/ (fn name or test file)


@dataclass
class Task:
    """An underdetermined task with multiple valid interpretations."""
    id: str
    domain: str  # code_spec | data_analysis | policy_qa
    prompt: str  # Underdetermined prompt (k requirement-classes deleted)
    latent_spec: str  # Full spec (visible to scorer, hidden from tested agents)
    interpretations: List[Interpretation]
    ambiguity_level: int  # 1|2|3 = how many requirement classes deleted
    key_questions: List[str]  # Golden clarifying questions
    regime: Optional[str] = None  # "H1_external" | "H2_derivable" | None (excluded/untagged)

    def __post_init__(self) -> None:
        if self.regime not in VALID_REGIMES:
            raise ValueError(
                f"Task.regime must be one of {VALID_REGIMES!r}, got {self.regime!r}"
            )


@dataclass
class AgentRun:
    """A single agent execution on a task.
    
    Identity-dimension rule: uniquely keyed by task_id × config × model_role × model_id × seed.
    Missing any dimension = silent collision.
    """
    task_id: str
    config: str  # single|sc|mad|verifier|diverse
    model_role: str
    model_id: str
    output: str
    label: str  # L_i in {I0, I1, ..., I_perp}, assigned by label.py via executable signal
    verbalized_conf: float
    logit_conf: Optional[float]
    seed: int  # Identity dimension — avoid silent config collisions
