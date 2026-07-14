# Phase 2-S2d — Integration test (real run→label→metrics) — slice plan

> Orchestrator-only: spawned sub-agent in a worktree; implementer family ≠ auditor family.
> Completes Phase-2 engineering. Does NOT include the pre-registration freeze or the MVP pilot
> (those are owner-gated, separate).

## Why
`tests/test_smoke_pipeline.py` only exercises the Phase-0 MOCK hash path: the offline `LLMClient`
emits `MOCK_OUTPUT_...`, which the labeler correctly maps to `I_perp`, so the "pipeline" never
produces a MEANINGFUL convergent-delusion number driven by real executable-gold labeling. We need a
real end-to-end test that drives the label→metrics stages with CONTROLLED outputs that
deterministically map to KNOWN interpretations, plus a genuine `run_task` wiring pass.

## Scope (tests only — add tests/test_integration_pipeline.py; do NOT touch schema.py/config.yaml/src)
1. **Controlled end-to-end golden case (the meaningful assertion), per PRIMARY domain (code_spec,
   data_analysis) and secondary (policy_qa):**
   - Load real bench tasks via the bench loader; pick a task with ≥2 non-target interpretations.
   - Use the domain's canonical candidates (the same `get_checkers_and_candidates(domain, task)` /
     canonical-reference mechanism used by tests/test_label.py) to build a controlled set of
     `AgentRun.output` strings: e.g. 3 agents emit the candidate that satisfies interpretation I1,
     1 emits the I0 (target) candidate, 1 emits I2 — wrapped in the format the labeler expects
     (code fence for code/data; `FINAL ANSWER: $<amount>` for policy_qa).
   - Run the REAL `label_run(run, task)` on each → assert labels == the intended interpretation ids
     (not I_perp).
   - Feed labels to `harness.metrics`: assert `convergent_delusion` == the HAND-COMPUTED value
     (e.g. 3/5 = 0.6), `a_maj` (I1 is modal wrong, target I0 not plurality → 0.0), and that
     `marginal_rho` / `ece` / `confidence_accuracy_slope` run without error on the assembled vectors.
     These are the end-to-end GOLDEN assertions (hand-calculated, frozen).
2. **Real run wiring pass:** for a couple of real bench tasks per domain, call `run_task(task,
   config=..., client=LLMClient(offline))` for at least `single`, `sc`, and one MAD/verifier config;
   then `label_run` each output; then compute metrics. Assert: runs have the right shape/identity
   fields, `run.label == ""` out of run_task, labels ∈ valid set, `convergent_delusion ∈ [0,1]` float.
   This exercises the true code path (not asserting a specific value, since mock outputs → mostly
   I_perp — that's expected and fine for the wiring check).
3. **Include the golden metric tests:** ensure `tests/test_metrics_golden.py` and
   `tests/test_marginal_rho.py` remain and are part of the suite; the new integration test must not
   duplicate-but-contradict them. (Owner requirement: integration test includes the golden metric tests.)
4. Replace or clearly supersede the trivial parts of `tests/test_smoke_pipeline.py` (keep the
   offline-no-network check; upgrade the meaningful pipeline assertion into the new file, or keep both
   with the new file carrying the real assertion). No network; offline mock only; deterministic.

## Verification / merge gate (Law 4)
`pip install -e .` + full `pytest -q` green (run 2x for flakiness — this pipeline touches the
subprocess executable-gold harnesses, which have had flakiness before; verify repeated runs).
Cross-family audit 0 BLOCKER/MAJOR. `common/schema.py` untouched; no `config.yaml` change.

## Provenance
Implementer: Claude/Anthropic (record in PR body). Auditor: GPT family (cross-family). The auditor must
independently recompute the hand-calculated end-to-end golden values and confirm the controlled outputs
truly map to the asserted interpretations (not accidentally I_perp).
