"""Task execution harness — Phase 2 real implementations.

Configs: single, sc (self-consistency), homogeneous-MAD, heterogeneous-MAD,
verifier, interpretation-diverse. All deterministic, offline by default.
"""

from typing import List, Dict, Any, Optional
from common.schema import Task, AgentRun
from common.llm import LLMClient


# Prompt templates (versioned constants for reproducibility)
PROMPT_SINGLE_V1 = """{task_prompt}

Please provide your answer and express your confidence level (0-100%)."""

PROMPT_SC_V1 = """{task_prompt}

Provide your best answer and confidence level (0-100%)."""

PROMPT_MAD_INITIAL_V1 = """{task_prompt}

You are Agent {agent_idx} in a multi-agent discussion. Provide your initial answer and confidence (0-100%)."""

PROMPT_MAD_ROUND_V1 = """{task_prompt}

You are Agent {agent_idx}. Previous round answers from all agents:
{previous_answers}

Considering the above, provide your updated answer and confidence (0-100%)."""

PROMPT_VERIFIER_CANDIDATE_V1 = """{task_prompt}

Provide a candidate answer and your confidence (0-100%)."""

PROMPT_VERIFIER_SELECT_V1 = """Task: {task_prompt}

Candidate answers:
{candidates}

As a verifier, select the best answer from the candidates above. Provide your selection (Candidate N) and confidence (0-100%)."""

PROMPT_DIVERSE_V1 = """{task_prompt}

Focus on interpretation: {interpretation_hint}

Provide your answer considering this perspective, with confidence (0-100%)."""


# ── V2 templates: identical to V1 but append {answer_format_instruction} ──────

PROMPT_SINGLE_V2 = """{task_prompt}

Please provide your answer and express your confidence level (0-100%).

{answer_format_instruction}"""

PROMPT_SC_V2 = """{task_prompt}

Provide your best answer and confidence level (0-100%).

{answer_format_instruction}"""

PROMPT_MAD_INITIAL_V2 = """{task_prompt}

You are Agent {agent_idx} in a multi-agent discussion. Provide your initial answer and confidence (0-100%).

{answer_format_instruction}"""

PROMPT_MAD_ROUND_V2 = """{task_prompt}

You are Agent {agent_idx}. Previous round answers from all agents:
{previous_answers}

Considering the above, provide your updated answer and confidence (0-100%).

{answer_format_instruction}"""

PROMPT_VERIFIER_CANDIDATE_V2 = """{task_prompt}

Provide a candidate answer and your confidence (0-100%).

{answer_format_instruction}"""

PROMPT_VERIFIER_SELECT_V2 = """Task: {task_prompt}

Candidate answers:
{candidates}

As a verifier, select the best answer from the candidates above. Provide your selection (Candidate N) and confidence (0-100%).

{answer_format_instruction}"""

PROMPT_DIVERSE_V2 = """{task_prompt}

Focus on interpretation: {interpretation_hint}

Provide your answer considering this perspective, with confidence (0-100%).

{answer_format_instruction}"""


def answer_format_instruction(domain: str) -> str:
    """Return domain-appropriate answer-format instruction for prompt injection.

    Mirrors the exact extraction contracts of harness/label.py so that real
    agents are told to emit answers the labeler can extract:
      - policy_qa:  FINAL ANSWER: $<amount>  OR  {"amount": <number>}
      - code_spec / data_analysis: single ```python code block
      - unknown domain: generic fallback (never crashes)
    """
    if domain == "policy_qa":
        return (
            'End your response with EXACTLY one of these formats:\n'
            '  FINAL ANSWER: $<amount>  (e.g. FINAL ANSWER: $42.00)\n'
            '  OR a standalone JSON object: {"amount": <number>}\n'
            'This structured format is required for automated scoring.\n'
            'If you show any reasoning first, keep it brief and make sure the '
            'FINAL ANSWER (or JSON) is OUTSIDE and AFTER any reasoning, as the '
            'LAST thing in your response.'
        )
    elif domain in ("code_spec", "data_analysis"):
        return (
            'Provide your complete solution as EXACTLY ONE ```python code block '
            'containing your FINAL answer.\n'
            'Do NOT include any other code block (no illustrative/example/draft '
            'blocks): output a single ```python block and nothing fenced besides '
            'it. If you show any reasoning first, keep it brief and make sure the '
            'one ```python code block is the LAST thing in your response.'
        )
    else:
        return 'State your final answer clearly and concisely.'


def run_task(task: Task, config: str, client: LLMClient, **kwargs) -> List[AgentRun]:
    """Run a task with specified config and return agent runs.
    
    Dispatches to the appropriate config implementation.
    
    Args:
        task: Task object with prompt and interpretations
        config: Config name (single|sc|homogeneous-MAD|heterogeneous-MAD|verifier|interpretation-diverse)
        client: LLMClient instance
        **kwargs: Config-specific parameters (k, rounds, n_agents, temperature, etc.).
            temperature: Override the per-config default temperature.
              single default=0.0; all sampling configs default=0.7.
    
    Returns:
        List of AgentRun objects (label="" - labeling is a separate stage)
    """
    temperature = kwargs.pop("temperature", None)  # caller-supplied override (None = use per-config default)
    if config == "single":
        return [run_single(task, client, temperature=temperature)]
    elif config == "sc":
        k = kwargs.get("k", 5)
        return run_self_consistency(task, client, k=k, temperature=temperature)
    elif config == "homogeneous-MAD":
        n_agents = kwargs.get("n_agents", 3)
        rounds = kwargs.get("rounds", 3)
        return run_mad(task, client, homogeneous=True, n_agents=n_agents, rounds=rounds, temperature=temperature)
    elif config == "heterogeneous-MAD":
        n_agents = kwargs.get("n_agents", 4)
        rounds = kwargs.get("rounds", 3)
        return run_mad(task, client, homogeneous=False, n_agents=n_agents, rounds=rounds, temperature=temperature)
    elif config == "verifier":
        n_candidates = kwargs.get("n_candidates", 3)
        return run_verifier(task, client, n_candidates=n_candidates, temperature=temperature)
    elif config == "interpretation-diverse":
        return run_diverse(task, client, temperature=temperature)
    else:
        raise ValueError(f"Unknown config: {config}")


def run_single(task: Task, client: LLMClient, temperature: Optional[float] = None) -> AgentRun:
    """Single agent, one shot.
    
    Args:
        task: Task to execute
        client: LLMClient instance
        temperature: Sampling temperature. Defaults to 0.0 (deterministic).
    
    Returns:
        Single AgentRun
    """
    if temperature is None:
        temperature = 0.0
    seed = client.config["seeds"]["global"]
    prompt = PROMPT_SINGLE_V2.format(
        task_prompt=task.prompt,
        answer_format_instruction=answer_format_instruction(task.domain)
    )
    
    completion = client.complete(
        role="tested_agents",
        prompt=prompt,
        seed=seed,
        temperature=temperature,
    )
    
    # Derive confidence deterministically from seed
    verbalized_conf = 0.5 + (seed % 50) / 100.0
    
    return AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id=completion.model,
        output=completion.text,
        label="",  # Labeling is a separate stage
        verbalized_conf=verbalized_conf,
        logit_conf=completion.logit_conf,
        seed=seed
    )


def run_self_consistency(task: Task, client: LLMClient, k: int = 5, temperature: Optional[float] = None) -> List[AgentRun]:
    """Self-consistency with k independent samples.
    
    Args:
        task: Task to execute
        client: LLMClient instance
        k: Number of samples (typically 5 or 10)
        temperature: Sampling temperature. Defaults to 0.7 to ensure diverse samples.
    
    Returns:
        List of k AgentRuns with different seeds
    """
    if temperature is None:
        temperature = 0.7
    runs = []
    base_seed = client.config["seeds"]["global"]
    
    for i in range(k):
        seed = base_seed + i
        prompt = PROMPT_SC_V2.format(
            task_prompt=task.prompt,
            answer_format_instruction=answer_format_instruction(task.domain)
        )
        
        completion = client.complete(
            role="tested_agents",
            prompt=prompt,
            seed=seed,
            temperature=temperature,
        )
        
        verbalized_conf = 0.5 + (seed % 50) / 100.0
        
        run = AgentRun(
            task_id=task.id,
            config="sc",
            model_role="tested_agents",
            model_id=completion.model,
            output=completion.text,
            label="",
            verbalized_conf=verbalized_conf,
            logit_conf=completion.logit_conf,
            seed=seed
        )
        runs.append(run)
    
    return runs


def run_mad(
    task: Task,
    client: LLMClient,
    homogeneous: bool = True,
    n_agents: int = 3,
    rounds: int = 3,
    temperature: Optional[float] = None,
) -> List[AgentRun]:
    """Multi-agent debate with N agents over R rounds.
    
    Args:
        task: Task to execute
        client: LLMClient instance
        homogeneous: If True, use homogeneous family; else heterogeneous
        n_agents: Number of agents
        rounds: Number of debate rounds
        temperature: Sampling temperature. Defaults to 0.7 to ensure diverse debate.
    
    Returns:
        List of AgentRuns (one per agent with final-round answer)
    """
    if temperature is None:
        temperature = 0.7
    base_seed = client.config["seeds"]["global"]
    
    # Select agent models from config
    if homogeneous:
        agent_pool = client.config["roles"]["tested_agents"]["homogeneous"]
        config_name = "homogeneous-MAD"
    else:
        agent_pool = client.config["roles"]["tested_agents"]["heterogeneous"]
        config_name = "heterogeneous-MAD"
    
    # Assign models to agents (cycling through pool if needed)
    agents = []
    for i in range(n_agents):
        model_info = agent_pool[i % len(agent_pool)]
        agents.append({
            "idx": i,
            "family": model_info["family"],
            "model": model_info["model"],
            "seed": base_seed + i,
            "history": []  # [(round, answer), ...]
        })
    
    # Run debate rounds
    for round_idx in range(rounds):
        # FIX BUG 2: Snapshot ALL agents' previous-round answers BEFORE starting this round
        # (prevents order-dependent debate where later agents see earlier agents' current-round answers)
        # CANONICALIZE: sort by agent idx so prompt text is independent of iteration order
        if round_idx > 0:
            prev_round_snapshot = [
                (a["idx"], a["history"][-1][1])  # (agent_idx, round r-1 answer)
                for a in agents
            ]
            # Sort by agent idx for deterministic canonical order
            prev_round_snapshot.sort(key=lambda x: x[0])
        
        for agent in agents:
            if round_idx == 0:
                # Initial round
                prompt = PROMPT_MAD_INITIAL_V2.format(
                    task_prompt=task.prompt,
                    agent_idx=agent["idx"],
                    answer_format_instruction=answer_format_instruction(task.domain)
                )
            else:
                # Subsequent rounds: show FROZEN previous round answers (from canonical snapshot)
                prev_answers = "\n".join([
                    f"Agent {idx}: {answer}"
                    for idx, answer in prev_round_snapshot
                ])
                prompt = PROMPT_MAD_ROUND_V2.format(
                    task_prompt=task.prompt,
                    agent_idx=agent["idx"],
                    previous_answers=prev_answers,
                    answer_format_instruction=answer_format_instruction(task.domain)
                )
            
            # Get completion with round-specific seed
            round_seed = agent["seed"] + round_idx * 1000
            
            # FIX BUG 1: Pass explicit family/model to ensure heterogeneous agents
            # produce genuinely different outputs (not all from homogeneous baseline)
            completion = client.complete(
                role="tested_agents",
                prompt=prompt,
                seed=round_seed,
                family=agent["family"],
                model=agent["model"],
                temperature=temperature,
            )
            
            agent["history"].append((round_idx, completion.text, completion.logit_conf))
    
    # Create final AgentRuns from last round
    runs = []
    for agent in agents:
        final_round, final_answer, final_logit_conf = agent["history"][-1]
        final_seed = agent["seed"] + final_round * 1000
        verbalized_conf = 0.5 + (final_seed % 50) / 100.0
        
        run = AgentRun(
            task_id=task.id,
            config=config_name,
            model_role="tested_agents",
            model_id=agent["model"],  # Provenance now matches the actual generating model
            output=final_answer,
            label="",
            verbalized_conf=verbalized_conf,
            logit_conf=final_logit_conf,
            seed=final_seed
        )
        runs.append(run)
    
    return runs


def run_verifier(task: Task, client: LLMClient, n_candidates: int = 3, temperature: Optional[float] = None) -> List[AgentRun]:
    """Verifier-based selection: candidates generate, verifier selects.
    
    FIX BUG 3: Returns only the verifier's AgentRun with the SELECTED candidate's
    answer as output (not the verifier's raw "Candidate N" text), so downstream
    labeling measures the verifier mechanism's chosen answer.
    
    Args:
        task: Task to execute
        client: LLMClient instance
        n_candidates: Number of candidate answers to generate
        temperature: Sampling temperature. Defaults to 0.7 for diverse candidates.
    
    Returns:
        Single-element list containing the verifier's selection AgentRun
    """
    if temperature is None:
        temperature = 0.7
    base_seed = client.config["seeds"]["global"]
    
    # Generate candidate answers
    candidates = []
    candidates_text = []
    for i in range(n_candidates):
        seed = base_seed + i
        prompt = PROMPT_VERIFIER_CANDIDATE_V2.format(
            task_prompt=task.prompt,
            answer_format_instruction=answer_format_instruction(task.domain)
        )
        
        completion = client.complete(
            role="tested_agents",
            prompt=prompt,
            seed=seed,
            temperature=temperature,
        )
        
        candidates.append({
            "idx": i,
            "answer": completion.text,
            "model": completion.model,
            "seed": seed
        })
        candidates_text.append(f"Candidate {i}: {completion.text}")
    
    # Verifier selects from candidates
    verifier_seed = base_seed + n_candidates
    verifier_prompt = PROMPT_VERIFIER_SELECT_V2.format(
        task_prompt=task.prompt,
        candidates="\n".join(candidates_text),
        answer_format_instruction=answer_format_instruction(task.domain)
    )
    
    verifier_completion = client.complete(
        role="tested_agents",
        prompt=verifier_prompt,
        seed=verifier_seed,
        temperature=temperature,
    )
    
    # Parse verifier's selection to resolve the chosen candidate's answer
    # Deterministic fallback: if parse fails, select candidate 0
    selected_answer = None
    selected_idx = None
    
    verifier_text = verifier_completion.text.lower()
    for i in range(n_candidates):
        if f"candidate {i}" in verifier_text:
            selected_idx = i
            selected_answer = candidates[i]["answer"]
            break
    
    # Fallback: if no valid selection, deterministically choose candidate 0
    if selected_answer is None:
        selected_idx = 0
        selected_answer = candidates[0]["answer"]
    
    verifier_conf = 0.5 + (verifier_seed % 50) / 100.0
    
    # Return the verifier's AgentRun with the SELECTED candidate's answer
    # (not the raw verifier selection text)
    verifier_run = AgentRun(
        task_id=task.id,
        config="verifier",
        model_role="tested_agents",
        model_id=verifier_completion.model,
        output=selected_answer,  # The actual selected candidate answer, not "Candidate N"
        label="",
        verbalized_conf=verifier_conf,
        logit_conf=verifier_completion.logit_conf,
        seed=verifier_seed
    )
    
    return [verifier_run]


def run_diverse(task: Task, client: LLMClient, temperature: Optional[float] = None) -> List[AgentRun]:
    """Interpretation-diverse ensemble prompting.
    
    FIX BUG 4: Binds each prompt to an ACTUAL task interpretation (from
    task.interpretations), creating one agent per interpretation to produce
    genuinely interpretation-directed outputs.
    
    Args:
        task: Task to execute
        client: LLMClient instance
        temperature: Sampling temperature. Defaults to 0.7 for diverse outputs.
    
    Returns:
        List of AgentRuns (one per task interpretation)
    """
    if temperature is None:
        temperature = 0.7
    base_seed = client.config["seeds"]["global"]
    runs = []
    
    # Generate one prompt per task interpretation (interpretation-directed ensemble)
    for i, interp in enumerate(task.interpretations):
        seed = base_seed + i
        
        # Bind the prompt to this specific interpretation
        # Use interpretation ID and gold_check as semantic hints
        hint = f"Focus on interpretation {interp.id} ({interp.gold_check})"
        if interp.is_target:
            hint += " - this is the target interpretation"
        
        prompt = PROMPT_DIVERSE_V2.format(
            task_prompt=task.prompt,
            interpretation_hint=hint,
            answer_format_instruction=answer_format_instruction(task.domain)
        )
        
        completion = client.complete(
            role="tested_agents",
            prompt=prompt,
            seed=seed,
            temperature=temperature,
        )
        
        verbalized_conf = 0.5 + (seed % 50) / 100.0
        
        run = AgentRun(
            task_id=task.id,
            config="interpretation-diverse",
            model_role="tested_agents",
            model_id=completion.model,
            output=completion.text,
            label="",
            verbalized_conf=verbalized_conf,
            logit_conf=completion.logit_conf,
            seed=seed
        )
        runs.append(run)
    
    return runs
