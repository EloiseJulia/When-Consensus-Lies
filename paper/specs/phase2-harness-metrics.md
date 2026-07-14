# Phase 2 Spec — Harness + Metrics (Direction A measurement)

Serial in the 0→2→5→6 chain, but the three modules below are INDEPENDENT (they interface
only via the FROZEN `common/schema.py` and the merged `bench/` gold), so they run as parallel
slices, then an integration + pre-registration step. Orchestrator-only: every code change via a
spawned sub-agent in a worktree; implementer family ≠ auditor family (cross-family §5.2).

## Current state (git ground truth, main @ 7d8ef24)
- `harness/metrics.py`: DONE — `false_consensus_rate`/`convergent_delusion` (PRIMARY), `marginal_rho`
  (secondary), `error_indicators`, `a_maj`, `ece`. MISSING: confidence–accuracy slope.
- `harness/label.py`: Phase-0 MOCK (hash-to-interpretation) + Phase-2 stubs raising NotImplementedError.
- `harness/run.py`: Phase-0 MOCK + 6 config stubs raising NotImplementedError.
- Tests present: `test_metrics_golden.py`, `test_marginal_rho.py`, `test_smoke_pipeline.py` (mock).

## INTERFACE CONTRACTS (all slices MUST obey; do NOT edit schema.py)
- `AgentRun.output`: the raw model completion text (string). Config logic lives in run.py; the
  labeler is responsible for extracting the domain answer from `output`.
- `AgentRun.label`: assigned ONLY by `harness/label.py` (never by run.py). One of the task's
  `interpretation.id` values, or `"I_perp"` when the output matches no interpretation.
- Labeling is EXECUTABLE-GOLD ONLY (NEVER an LLM judge): for code/data domains, run the extracted
  candidate answer through EACH interpretation's gold checker (reuse the merged `bench/<domain>`
  hardened runners) and assign the interpretation whose gold it uniquely satisfies; if none →
  `I_perp`; if it satisfies more than one (should not happen given 100% distinguishability) →
  `I_perp` and flag. For policy_qa, parse the numeric answer and exact-cent-match against each
  interpretation's gold amount.
- Determinism/reproducibility: use `common/config.yaml` seeds; `LLMClient` offline mock is the
  default (no network/API key). Everything must pass with the offline mock.

## Slices

### S2a — metrics (branch slice/phase2-S2a-metrics)
- ADD `confidence_accuracy_slope(confidences, correct) -> float`: slope of a simple linear
  regression of correctness (0/1) on confidence (the confidence–accuracy relationship; positive =
  better-calibrated ranking). Return 0.0 if confidence has zero variance. Document the definition.
- KEEP the PRIMARY metric = `convergent_delusion` (= `false_consensus_rate`); do NOT let binary ρ
  become primary. Add a module-level docstring assertion / comment making the primary explicit.
- STRENGTHEN golden tests (`tests/test_metrics_golden.py`) per plan §5.1: convergent-vs-scattered,
  a_maj tie handling, ece known-value, marginal_rho bridge, and a new slope golden case with a
  hand-computed expected value. Golden tests must encode HAND-CALCULATED expected numbers.

### S2b — label (branch slice/phase2-S2b-label)
- IMPLEMENT `label_run(run, task)` to dispatch by `task.domain` to `label_code_domain`,
  `label_data_domain`, `label_policy_domain`, each using EXECUTABLE signals (reuse the merged
  `bench/<domain>` gold checkers / runners). NEVER an LLM judge.
- Extract the candidate answer from `run.output` robustly (e.g. code fence extraction for code
  domains; numeric parse for policy). Assign the interpretation whose gold the answer satisfies;
  `I_perp` if none. Keep the mock available under a clearly-named fallback ONLY for unknown domains.
- Golden tests (`tests/test_label.py`): for each domain, craft synthetic outputs that deterministically
  satisfy a specific interpretation's gold and assert the returned label equals that interpretation id,
  plus an `I_perp` case for garbage output. No network.

### S2c — run (branch slice/phase2-S2c-run)
- IMPLEMENT the 6 configs producing `List[AgentRun]` (leave `label=""`; labeling is a separate stage):
  `single` (1 agent), `sc` self-consistency (k=5 and k=10), `homogeneous-MAD` (anthropic ×N debate),
  `heterogeneous-MAD` (mixed-family debate), `verifier` (verifier-selection), `interpretation-diverse`
  (interpretation-diverse ensemble). Use `common/config.yaml` role routing for family/model selection
  and the offline-deterministic `LLMClient`. Each AgentRun's identity key
  (task_id × config × model_role × model_id × seed) must be unique within a config's run.
- Tests (`tests/test_run_configs.py`): each config returns the expected number/shape of AgentRuns,
  deterministic across repeated calls (same seeds), correct `config`/`model_role`/`model_id`/`seed`
  fields, and MAD produces the expected number of rounds. No network (offline mock).

### S2d — integration + pre-registration (Manager-coordinated, after a/b/c merged)
- Replace/extend `tests/test_smoke_pipeline.py` with a REAL end-to-end pipeline test (run → label →
  metrics) over a few tasks per domain using the offline mock, asserting the pipeline yields a valid
  convergent-delusion number (not the mock hash path).
- PRE-REGISTRATION (Law 7, owner sign-off): a committed doc pinning H1/H2, the PRIMARY metric =
  convergent-delusion, secondary metrics, and the predicted ρ–ambiguity crossover BEFORE any
  full-scale run. Metric definitions frozen thereafter.

## Merge gate (Law 4) per slice
Full `pytest -q` green + cross-family audit 0 BLOCKER/MAJOR. `common/schema.py` untouched; any
`config.yaml` change called out. Owner-facing check for S2a: confirm PRIMARY = convergent-delusion.
