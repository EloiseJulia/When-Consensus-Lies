"""Hypothesis surfacing via forced interpretation branching.

Phase 3: Detect latent assumptions by divergence in forced branches.
"""


def surface_latent_assumptions(task, agent_runs) -> dict:
    """Surface hidden assumptions via interpretation branching.
    
    [PHASE 3]
    
    Args:
        task: Task object
        agent_runs: List of AgentRun objects
    
    Returns:
        Dict with 'assumptions', 'suspicion_scores', 'warnings'
    """
    raise NotImplementedError("Phase 3: hypothesis surfacing detector")


def compute_divergence_score(branch_outputs) -> float:
    """Compute divergence between interpretation branches.
    
    [PHASE 3]
    """
    raise NotImplementedError("Phase 3: divergence scoring")
