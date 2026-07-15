# Phase 2-S2f — MVP pilot: metric + label-shuffle-null machinery validation (slice plan)

> Owner-approved pilot (prereg §11). Orchestrator-only: spawned sub-agent in a worktree; implementer
> family ≠ auditor family. This validates the MEASUREMENT MACHINERY behaves as pre-registered. It is
> NOT evidence for H1/H2 (that requires real-model runs — see the escalation note below).

## Context / constraint (important)
`common/llm.py` online mode is a STUB (`NotImplementedError("Online mode deferred to Phase 1")`); the
only runnable mode is the deterministic offline mock, whose outputs label to `I_perp`. Therefore this
pilot validates the metric + the R1 null on a CONTROLLED batch whose agent outputs deterministically map
to KNOWN interpretations via the executable-gold labeler (same canonical-candidate mechanism used by
tests/test_integration_pipeline.py). Real-model batches are blocked until the online LLM path is
implemented (separate, owner-gated scope item).

## Deliverables
### 1. R1 label-shuffle null implementation (new `harness/nulls.py`) — implements the FROZEN prereg §4 R1
- `label_shuffle_null(items_labels, target, n_perm, seed) -> float` (or similar): given per-item label
  lists within ONE condition, implement the POPULATION-LEVEL / CROSS-ITEM reshuffle EXACTLY as frozen in
  prereg §4 R1: pool ALL agent labels across items in the condition; reassign each (item, agent) slot an
  INDEPENDENT draw from the pooled marginal (preserving each item's agent count); recompute mean
  convergent_delusion (`harness.metrics.false_consensus_rate`) per permutation; average over `n_perm`
  seeded permutations → CD₀. Must NOT be a within-item permutation (that is a no-op). Document this.
- Do NOT modify `harness/metrics.py` (frozen metric defs); import `false_consensus_rate` from it.

### 2. Pilot validation (tests/test_pilot_nulls.py + a short runnable pilot in scripts or as a test)
- **Concentrated batch:** build N (>=20) synthetic items where, within each item, a majority of agents
  land on the SAME wrong interpretation (labels realized through real `label_run` on canonical
  candidates for at least one domain; direct controlled label lists acceptable for the null-math tests).
  Assert mean CD_real is clearly > 0.
- **Null discrimination:** compute CD₀ via `label_shuffle_null`; assert CD_real >> CD₀ (concentration
  exceeds the marginal-driven baseline), matching the frozen R1 prediction direction.
- **Scattered control batch:** items where wrong labels are spread across DIFFERENT interpretations (no
  within-item concentration). Assert CD_real is low AND CD_real ≈ CD₀ (null shows no excess concentration
  to explain) — i.e. the null does NOT false-alarm on scattered errors.
- Determinism: seeded; no network; offline only. Assert reproducibility across repeated calls.

### 3. Pilot result summary (the sub-agent reports numbers; Manager writes the report)
Report CD_real vs CD₀ for concentrated and scattered batches with the seeds used.

## Verification / merge gate (Law 4)
`pip install -e .` + full `pytest -q` green (2x, subprocess-harness flakiness watch). Cross-family audit
0 BLOCKER/MAJOR; the auditor MUST independently confirm the null is a genuine cross-item reshuffle (feed
it a case where a within-item permutation would give the wrong/no-op answer) and recompute the pilot
numbers. `common/schema.py` and `harness/metrics.py` untouched; no `config.yaml` change.

## Escalation recorded (for the Manager to raise with the owner, NOT for this sub-agent)
The real experiment is blocked on implementing `common/llm.py` online mode (real API calls) + API
keys/budget. That is a separate owner-gated scope item; this pilot does not attempt it.

## Provenance
Implementer: Claude/Anthropic. Auditor: GPT family (cross-family).
