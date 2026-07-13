"""Task execution harness — mock deterministic path for Phase 0.

Real logic for single/SC/MAD/verifier/diverse configs deferred to Phase 2.
Phase 0: produces mock deterministic AgentRuns for end-to-end smoke test.
"""

from typing import List, Dict, Any
from common.schema import Task, AgentRun
from common.llm import LLMClient


def run_task(task: Task, config: str, client: LLMClient, n_agents: int = 5) -> List[AgentRun]:
    """Run a task with specified config and return agent runs.
    
    Phase 0 MOCK: generates deterministic AgentRuns with no real inference.
    Real implementation in Phase 2 will handle:
        - single: one agent, one shot
        - sc: self-consistency with k samples
        - mad: multi-agent debate
        - verifier: verifier-based selection
        - diverse: interpretation-diverse ensemble
    
    Args:
        task: Task object with prompt and interpretations
        config: Config name (single|sc|mad|verifier|diverse)
        client: LLMClient instance
        n_agents: Number of agents to simulate (Phase 0 mock param)
    
    Returns:
        List of AgentRun objects
    """
    # Phase 0 mock: generate deterministic runs
    runs = []
    
    for agent_idx in range(n_agents):
        # Mock: deterministic seed per agent
        seed = client.config["seeds"]["global"] + agent_idx
        
        # Mock: simple prompt construction
        mock_prompt = f"{task.prompt}\n[Agent {agent_idx}]"
        
        # Mock: get completion (offline deterministic)
        completion = client.complete(
            role="tested_agents",
            prompt=mock_prompt,
            seed=seed
        )
        
        # Mock: derive confidence (deterministic from seed)
        mock_conf = 0.5 + (seed % 50) / 100.0  # Range [0.5, 1.0)

        run = AgentRun(
            task_id=task.id,
            config=config,
            model_role="tested_agents",
            model_id=completion.model,
            output=completion.text,
            label="",  # Unlabeled: labeling is a separate stage (label_run in the pipeline)
            verbalized_conf=mock_conf,
            logit_conf=None,  # Mock mode doesn't have logits
            seed=seed
        )
        runs.append(run)
    
    return runs


# === DEFERRED TO PHASE 2 ===
# Real implementations below will replace mock logic

def run_single(task: Task, client: LLMClient) -> AgentRun:
    """Single agent, one shot. [PHASE 2]"""
    raise NotImplementedError("Phase 2: single-agent execution")


def run_self_consistency(task: Task, client: LLMClient, k: int = 5) -> List[AgentRun]:
    """Self-consistency with k samples. [PHASE 2]"""
    raise NotImplementedError("Phase 2: self-consistency ensemble")


def run_mad(task: Task, client: LLMClient, rounds: int = 3) -> List[AgentRun]:
    """Multi-agent debate. [PHASE 2]"""
    raise NotImplementedError("Phase 2: multi-agent debate")


def run_verifier(task: Task, client: LLMClient) -> AgentRun:
    """Verifier-based selection. [PHASE 2]"""
    raise NotImplementedError("Phase 2: verifier mechanism")


def run_diverse(task: Task, client: LLMClient) -> List[AgentRun]:
    """Interpretation-diverse ensemble. [PHASE 2]"""
    raise NotImplementedError("Phase 2: interpretation-diverse prompting")
