# constructed by: Claude (Anthropic) family
"""Phase B EXPLORATORY diversified-evidence conditions (Amendment 12).

# Implementer model family: Claude / Anthropic
# Auditor model family: GPT (Law 6 — cross-family requirement)

Two POST-HOC, ADDITIVE, EXPLORATORY computational conditions that test the
paper's constructive design principle *"diversify evidence and interpretations,
not merely model providers."*  Pre-committed in
``paper/plans/2026-07-22-phaseB-diversified-conditions-design.md`` and ratified
via Amendment 12 BEFORE any run.

This module is NEW and is NOT imported by the confirmatory path
(``harness/run.py`` ``run_task`` dispatch is untouched).  It reuses the SAME
``LLMClient`` API, the SAME underspecified task prompt boundary, the SAME
``PROMPT_SINGLE_V2`` template + ``answer_format_instruction`` as the
confirmatory ``single`` config, and the SAME frozen labeler downstream.

Two conditions (design §2):

- ``run_cross_vendor_synthesis`` (C5): the frozen ``heterogeneous`` cross-family
  pool (openai gpt-5.4, anthropic claude-sonnet-4.6, google gemini-3.1-pro)
  each answer the SAME underspecified prompt INDEPENDENTLY, then a synthesizer
  (microsoft/mai-code-1-flash-picker — the frozen judge/constructor model,
  OUTSIDE the tested pool) merges the candidates into ONE final answer.

- ``run_role_diversified`` (C7): five cross-family agents each play a DISTINCT
  GENERIC epistemic role (solve / gap-find / alternatives / default-check /
  integrate).  R5 (Integrator) receives R1–R4 and emits the final answer OR a
  clarification/abstain.

HARD ANTI-LEAKAGE RULE (design §4, inviolable): NO prompt below may contain the
target interpretation, the deleted axis/convention, the enumerated foils,
``interp.id``, ``gold_check``, or ``is_target``.  The ONLY task-derived text put
into any prompt is ``task.prompt`` (the same underspecified prompt every
confirmatory agent sees) and ``task.domain`` (used only to select the neutral
answer-format instruction).  ``task.interpretations``, ``task.latent_spec``,
``task.key_questions`` are NEVER read here.  This is why the confirmatory
``interpretation-diverse`` config was excluded from primary methods (A11) — C7
must be honestly generic.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from common.schema import Task, AgentRun
from common.llm import LLMClient

# Reuse the EXACT confirmatory single-config template + neutral answer-format
# instruction (no interpretation hints, no gold reference) by import only.
from harness.run import PROMPT_SINGLE_V2, answer_format_instruction


# ── Config names (exploratory — never in the confirmatory REGISTERED_CONFIGS) ──
CONFIG_CROSS_VENDOR_SYNTHESIS = "cross-vendor-synthesis"
CONFIG_ROLE_DIVERSIFIED = "role-diversified"

#: Within-job per-role seed stride (>= role count, mirrors run.py seed spacing).
#: The 3 FROZEN grid seeds [global, global+1000, global+2000] separate jobs;
#: this stride separates roles/candidates WITHIN one job.  5 >= 5 roles.
ROLE_SEED_STRIDE = 5

#: Default sampling temperature for the independent generations — matches the
#: frozen sampling default of the multi-sample/ensemble configs
#: (sc / MAD / verifier all default to 0.7 in harness/run.py).
_DEFAULT_TEMPERATURE = 0.7


# ── Pre-committed GENERIC prompts (design §2) ────────────────────────────────
# Every string below is GENERIC epistemic scaffolding.  {task_prompt} is the
# SAME underspecified prompt the confirmatory `single` agent receives.
# {answer_format_instruction} is the neutral domain formatting contract.

#: C5 synthesizer prompt (design §2 C5.2, verbatim generic).
PROMPT_C5_SYNTHESIS_V1 = """You are given several candidate answers to the same task.

Task:
{task_prompt}

Candidate answers:
{candidates}

Produce the single best final answer in the required answer format. If the candidates are based on differing assumptions, choose the most defensible and state the final answer.

{answer_format_instruction}"""

#: C7 R1 Solver (design §2 C7.R1) — answer the task normally, in the answer format.
PROMPT_C7_R1_SOLVER_V1 = """{task_prompt}

Answer the task normally.

{answer_format_instruction}"""

#: C7 R2 Gap-finder (design §2 C7.R2, verbatim generic).
PROMPT_C7_R2_GAPFINDER_V1 = """{task_prompt}

List any information NOT specified in the prompt that could change the correct answer. Do not answer the task."""

#: C7 R3 Alternatives (design §2 C7.R3, verbatim generic).
PROMPT_C7_R3_ALTERNATIVES_V1 = """{task_prompt}

List the distinct plausible interpretations of this task that are each consistent with the prompt as written."""

#: C7 R4 Default-checker (design §2 C7.R4, verbatim generic).
PROMPT_C7_R4_DEFAULTCHECK_V1 = """{task_prompt}

State the default assumptions a solver would make here, and for each, whether the prompt actually fixes it."""

#: C7 R5 Integrator (design §2 C7.R5, verbatim generic scaffolding + explicit
#: detector-compatible abstain form).
PROMPT_C7_R5_INTEGRATOR_V1 = """You are integrating several prior analyses of the same task.

Task:
{task_prompt}

Prior responses from four independent agents:
{prior_responses}

Do not treat agreement among the earlier responses as evidence of correctness. If the earlier analysis shows that a decision-relevant detail is unspecified, respond with EXACTLY the following single line and nothing else:
{abstain_form}
Otherwise, give the best final answer in the required answer format.

{answer_format_instruction}"""

#: Explicit clarification/abstain string the FROZEN rule-based abstention
#: detector (analysis/abstention.py) recognizes.  The phrase "cannot determine"
#: matches the SIGNAL_CANNOT_DETERMINE rule
#: ``(?:cannot|...)\s+(?:determine|...)`` (an UNguarded pattern), and
#: "more information is required to determine" matches the SIGNAL_NEED_MORE_INFO
#: rule ``more\s+(?:context|information|...)\s+(?:is\s+)?(?:needed|required|...)``.
#: It is GENERIC (names no specific interpretation/axis/foil) → anti-leakage safe.
ABSTAIN_FORM = (
    "CLARIFICATION NEEDED: the task is ambiguous and I cannot determine which "
    "interpretation is intended; more information is required to determine the "
    "correct answer."
)


# ── Family/model resolution from config roles (no hardcoded roster) ──────────

def _heterogeneous_pool(client: LLMClient) -> List[Dict[str, str]]:
    """Return the frozen cross-family tested pool (openai/anthropic/google)."""
    return list(client.config["roles"]["tested_agents"]["heterogeneous"])


def _model_by_family(pool: List[Dict[str, str]], family: str) -> Tuple[str, str]:
    """Resolve (family, model) for *family* from a config model pool."""
    for entry in pool:
        if entry["family"] == family:
            return entry["family"], entry["model"]
    raise KeyError(f"family {family!r} not found in pool {pool!r}")


def _integrator_model(client: LLMClient) -> Tuple[str, str]:
    """R5 integrator = anthropic reasoning-tier model (claude-opus-4.8)."""
    reasoning = client.config["roles"]["tested_agents"].get("reasoning", [])
    for entry in reasoning:
        if entry["family"] == "anthropic":
            return entry["family"], entry["model"]
    # Defensive fallback to the pre-committed slug.
    return "anthropic", "claude-opus-4.8"


def _verbalized_conf(seed: int) -> float:
    """Deterministic verbalized confidence derived from seed (mirrors run.py)."""
    return 0.5 + (seed % 50) / 100.0


# ── C5: cross-vendor synthesis ───────────────────────────────────────────────

def run_cross_vendor_synthesis(
    task: Task,
    client: LLMClient,
    temperature: Optional[float] = None,
) -> List[AgentRun]:
    """C5 — cross-vendor synthesis (design §2 C5).

    The frozen heterogeneous pool each answer the SAME `PROMPT_SINGLE_V2`
    underspecified prompt INDEPENDENTLY; a pool-external synthesizer
    (microsoft/mai-code-1-flash-picker via the frozen ``judge`` role) merges the
    candidates into ONE final answer using the generic synthesis prompt.

    Returns a single-element list containing the synthesizer's AgentRun
    (config=``cross-vendor-synthesis``), carrying the merged final answer as
    ``output`` (mirrors how ``run_verifier`` returns the selected answer).
    ``AgentRun`` has no free-form field for the candidate answers, so — per the
    additive isolation rule (no schema change) — only the synthesizer run is
    returned.

    Args:
        task: Task to execute (only ``task.prompt`` / ``task.domain`` are read).
        client: LLMClient instance.
        temperature: Sampling temperature for the independent generations.
            Defaults to 0.7 (the frozen sampling default of the ensemble configs).

    Returns:
        ``[synthesizer AgentRun]``.
    """
    if temperature is None:
        temperature = _DEFAULT_TEMPERATURE
    base_seed = client.config["seeds"]["global"]

    pool = _heterogeneous_pool(client)

    # 1) Independent candidate generations over the SAME underspecified prompt.
    candidate_prompt = PROMPT_SINGLE_V2.format(
        task_prompt=task.prompt,
        answer_format_instruction=answer_format_instruction(task.domain),
    )
    candidates_text: List[str] = []
    for i, model_info in enumerate(pool):
        seed = base_seed + i * ROLE_SEED_STRIDE
        completion = client.complete(
            role="tested_agents",
            prompt=candidate_prompt,
            seed=seed,
            family=model_info["family"],
            model=model_info["model"],
            temperature=temperature,
        )
        candidates_text.append(f"Candidate {i}: {completion.text}")

    # 2) Pool-external synthesizer (frozen judge/constructor family — microsoft).
    synth_seed = base_seed + len(pool) * ROLE_SEED_STRIDE
    synth_prompt = PROMPT_C5_SYNTHESIS_V1.format(
        task_prompt=task.prompt,
        candidates="\n".join(candidates_text),
        answer_format_instruction=answer_format_instruction(task.domain),
    )
    synth_completion = client.complete(
        role="judge",
        prompt=synth_prompt,
        seed=synth_seed,
        temperature=temperature,
    )

    synth_run = AgentRun(
        task_id=task.id,
        config=CONFIG_CROSS_VENDOR_SYNTHESIS,
        model_role="judge",
        model_id=synth_completion.model,
        output=synth_completion.text,
        label="",  # labeling is a separate stage
        verbalized_conf=_verbalized_conf(synth_seed),
        logit_conf=synth_completion.logit_conf,
        seed=synth_seed,
    )
    return [synth_run]


# ── C7: role-diversified evidence workflow ───────────────────────────────────

def run_role_diversified(
    task: Task,
    client: LLMClient,
    temperature: Optional[float] = None,
) -> List[AgentRun]:
    """C7 — role-diversified evidence workflow (design §2 C7).

    Five cross-family agents each play a DISTINCT GENERIC epistemic role over
    the SAME underspecified prompt:
      R1 Solver          (openai gpt-5.4)
      R2 Gap-finder      (anthropic claude-sonnet-4.6)
      R3 Alternatives    (google gemini-3.1-pro-preview)
      R4 Default-checker (openai gpt-5.4, distinct seed)
      R5 Integrator      (anthropic claude-opus-4.8) — sees R1–R4, emits the
                          final answer OR a clarification/abstain.

    All role prompts are GENERIC epistemic scaffolding: none names the missing
    convention, target interpretation, foils, or any gold_check (design §4).

    Returns a single-element list containing R5's AgentRun
    (config=``role-diversified``).

    Args:
        task: Task to execute (only ``task.prompt`` / ``task.domain`` are read).
        client: LLMClient instance.
        temperature: Sampling temperature. Defaults to 0.7.

    Returns:
        ``[integrator (R5) AgentRun]``.
    """
    if temperature is None:
        temperature = _DEFAULT_TEMPERATURE
    base_seed = client.config["seeds"]["global"]

    pool = _heterogeneous_pool(client)
    r1_family, r1_model = _model_by_family(pool, "openai")     # Solver
    r2_family, r2_model = _model_by_family(pool, "anthropic")  # Gap-finder
    r3_family, r3_model = _model_by_family(pool, "google")     # Alternatives
    r4_family, r4_model = r1_family, r1_model                  # Default-checker
    r5_family, r5_model = _integrator_model(client)            # Integrator

    fmt = answer_format_instruction(task.domain)

    # R1–R4: distinct generic roles, distinct seeds (stride ROLE_SEED_STRIDE).
    r1_prompt = PROMPT_C7_R1_SOLVER_V1.format(
        task_prompt=task.prompt, answer_format_instruction=fmt
    )
    r2_prompt = PROMPT_C7_R2_GAPFINDER_V1.format(task_prompt=task.prompt)
    r3_prompt = PROMPT_C7_R3_ALTERNATIVES_V1.format(task_prompt=task.prompt)
    r4_prompt = PROMPT_C7_R4_DEFAULTCHECK_V1.format(task_prompt=task.prompt)

    role_calls = [
        ("R1_solver", r1_family, r1_model, r1_prompt),
        ("R2_gapfinder", r2_family, r2_model, r2_prompt),
        ("R3_alternatives", r3_family, r3_model, r3_prompt),
        ("R4_defaultcheck", r4_family, r4_model, r4_prompt),
    ]

    prior_blocks: List[str] = []
    for i, (label, family, model, prompt) in enumerate(role_calls):
        seed = base_seed + i * ROLE_SEED_STRIDE
        completion = client.complete(
            role="tested_agents",
            prompt=prompt,
            seed=seed,
            family=family,
            model=model,
            temperature=temperature,
        )
        prior_blocks.append(f"{label}: {completion.text}")

    # R5 Integrator: sees R1–R4, emits final answer OR clarification/abstain.
    r5_seed = base_seed + 4 * ROLE_SEED_STRIDE
    r5_prompt = PROMPT_C7_R5_INTEGRATOR_V1.format(
        task_prompt=task.prompt,
        prior_responses="\n\n".join(prior_blocks),
        abstain_form=ABSTAIN_FORM,
        answer_format_instruction=fmt,
    )
    r5_completion = client.complete(
        role="tested_agents",
        prompt=r5_prompt,
        seed=r5_seed,
        family=r5_family,
        model=r5_model,
        temperature=temperature,
    )

    r5_run = AgentRun(
        task_id=task.id,
        config=CONFIG_ROLE_DIVERSIFIED,
        model_role="tested_agents",
        model_id=r5_completion.model,
        output=r5_completion.text,
        label="",
        verbalized_conf=_verbalized_conf(r5_seed),
        logit_conf=r5_completion.logit_conf,
        seed=r5_seed,
    )
    return [r5_run]


#: Dispatch table for the Phase B driver (config name → runner fn).
PHASEB_RUNNERS = {
    CONFIG_CROSS_VENDOR_SYNTHESIS: run_cross_vendor_synthesis,
    CONFIG_ROLE_DIVERSIFIED: run_role_diversified,
}
