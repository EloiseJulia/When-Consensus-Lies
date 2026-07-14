# Phase 2-S2e — Answer-format prompt instruction (slice plan)

> Orchestrator-only: implemented by a spawned sub-agent in a worktree; implementer family ≠ auditor
> family. Small, focused slice. Unblocks the Phase-2 integration test (S2d).

## Why
`harness/label.py` now requires structured, executable-extractable answers, but `harness/run.py`'s
prompt templates (`PROMPT_*_V1`) never INSTRUCT agents to emit them. Without a matching instruction,
real agents would produce free-text that the labeler maps to `I_perp` en masse. This slice adds a
per-domain answer-format instruction so the *prompt contract* matches the *labeler contract*
(pre-registration §7).

## Scope (harness/run.py + tests only; do NOT touch common/schema.py or config.yaml)
1. Add a per-domain answer-format instruction, appended to EVERY config's prompt (single, sc,
   MAD-initial + MAD-round, verifier-candidate + verifier-select, diverse). Introduce `..._V2`
   template constants (keep `_V1` for provenance/history) OR a helper
   `answer_format_instruction(task.domain) -> str` appended at format time. Prefer the helper +
   `_V2` constants so the versioning is explicit and reproducible.
   - **policy_qa:** instruct the agent to end its response with a line exactly
     `FINAL ANSWER: $<amount>` (or a JSON object `{"amount": <number>}`), matching the labeler.
   - **code_spec:** instruct the agent to return its solution as a single ```python fenced code block
     (what `label_code_domain` extracts).
   - **data_analysis:** same single ```python fenced code block expectation.
   - Keep the existing confidence request (0-100%).
2. Route by `task.domain`. If domain is unknown, fall back to a generic instruction (no crash).
3. Determinism: offline `LLMClient` mock remains default; prompts stay deterministic given seeds.
   The prompt text change WILL change mock outputs (mock hashes the prompt) — update any tests that
   asserted exact prompt/output text; keep asserting shape/fields/determinism, not brittle text.

## Tests (tests/test_run_configs.py + a new/extended check)
- Assert each config's emitted prompt CONTAINS the domain-appropriate answer-format instruction
  (e.g. policy_qa prompt contains `FINAL ANSWER:`; code_spec/data_analysis contain a ```python fence
  instruction). Assert across all 6 configs and both MAD phases.
- Keep existing per-config shape/determinism tests green.
- No network (offline mock).

## Verification / merge gate (Law 4)
`python -m pip install -e .` + full `python -m pytest -q` green; cross-family audit 0 BLOCKER/MAJOR
(implementer ≠ auditor family). `common/schema.py` untouched; no `config.yaml` change; call out that
this touches the shared run harness prompts (all configs) in the PR body. This is a prompt-contract
change that is pre-registration-relevant (the emitted answer-format is fixed here) — note it in the PR.

## Provenance
Implementer: TBD family (record in PR body). Auditor: a DIFFERENT family (Manager assigns so the audit
is cross-family; if implemented by Claude, audit with GPT, and vice-versa).
