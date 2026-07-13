# Phase 0 — Delivery Report (slice S0: scaffold)

**Status: MERGED to `main` (squash `e58c994`, PR #1). Phase 0 complete; unblocks Phases 1–7.**

Implementer family: **Anthropic (Claude)** · Auditor family: **OpenAI (GPT)** — distinct per HARD LAW 6 (provenance separation).

## Delivered
- `common/schema.py` — **FROZEN interface contract**: `Interpretation`, `Task`, `AgentRun` (identity key = task_id × config × model_role × model_id × seed).
- `common/config.yaml` + `common/config.py` — role→family routing with an enforced `assert_provenance_separation`.
- `common/llm.py` — `LLMClient` offline mock (no API key/network), deterministic, mode/model-aware disk cache, retry, cost log.
- `harness/metrics.py` — REAL primary metric `false_consensus_rate`/`convergent_delusion`; secondary `marginal_rho`; `a_maj`; `ece`.
- `harness/run.py` + `harness/label.py` — mock deterministic end-to-end path (real logic deferred to Phase 2).
- Stubs: `bench/`, `detector/`, `sim_users/`, `analysis/` (import-clean, raise `NotImplementedError`).
- `tests/` — 29 tests incl. golden metric anchors (written first), provenance, determinism, cache, smoke E2E.

## Merge gate (HARD LAW 4) — PASS/FAIL
| Check | Result |
|---|---|
| A. Artifact build (`pip install -e .`) | PASS |
| B. Imports (all 6 packages) | PASS |
| C. Full suite (`pytest`) | PASS — 29 passed |
| D. Mock E2E run→label→metrics (offline) | PASS — convergent_delusion computed |
| E. Primary metric = convergent-delusion, not binary ρ | PASS — golden anchors 1.0 / 0.4 / 0.0 / 0.6 |
| F. Labels via executable gold, not LLM-judge | PASS — `label_run` deterministic signal |
| G. Provenance separation (4 roles distinct families) | PASS — constructor=google, judge=openai, code_reviewer=deepseek |
| H. Cross-family audit (author≠auditor) 0 BLOCKER/MAJOR | PASS — GPT audited Claude code |

## Cross-family audit trail (4 hostile rounds)
| Round | Findings | Resolution |
|---|---|---|
| R1 | 2 BLOCKER: builtin `hash()` label nondeterminism (per-process salted); provenance assertion too weak + `code_reviewer: anthropic` (= author family) | hashlib.sha256; strengthened assertion (meta roles ∉ homogeneous baseline); code_reviewer→deepseek |
| R2 | 2 MAJOR: `run_task` fabricated `AgentRun.label`; `marginal_rho` was majority-share not error-correlation | `label=""` (separate label stage); real pairwise Pearson `corr(E_i,E_j)` with zero-variance handling |
| R3 | 1 MAJOR: LLM cache key not mode/model-aware (offline mock could serve online; stale model id corrupts provenance) | cache key includes mode + resolved family:model; permanent errors not retried |
| R4 | 0 BLOCKER / 0 MAJOR → **MERGEABLE**; 2 MEDIUM (a_maj tie order-dependence; unknown-role fabricated provenance) | strict unique-majority a_maj; fail-fast on unknown role |

> The cross-family audit worked as the paper's own thesis predicts: same-family self-review + single-process pytest reported "all green / zero deviations", yet a different-family auditor surfaced 2 BLOCKERs and 3 MAJORs (incl. a determinism bug invisible within one process). This is executable-gold + provenance-separation functioning as both science and QA.

## Frozen contract (owner note)
`common/schema.py` is now the **frozen interface**. Any change to its dataclasses requires explicit owner sign-off and must notify all downstream phases (interface drift = silent cross-phase bugs).

## Pre-registration status
Metric **definitions** are locked via golden tests (primary = convergent-delusion). Full H1/H2 pre-registration commit is required later, **before any full-scale run** (Phase 6), per HARD LAW 7.

## Follow-ups for later phases
- Phase 2: implement runtime per-item same-family exclusion for judge/code_reviewer vs the heterogeneous tested pool (currently a documented policy, not yet enforced in code).
- Phase 2: replace mock `run_task`/`label_run` with real config execution + executable-signal labeling (code/data/policy domains).
