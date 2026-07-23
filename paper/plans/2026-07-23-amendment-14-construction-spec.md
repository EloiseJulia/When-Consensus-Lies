# Amendment 14 CONSTRUCTION + RUN SPEC — for the sub-agents (RATIFIED design)

> Implements owner-RATIFIED Amendment 14
> (`paper/preregistration/2026-07-23-amendment-14-unfiltered-replication-RATIFIED.md`). Additive SIDECAR
> only. The RUN queues AFTER the Phase 2b 6-model scale + Amendment 13. Frozen 54 / schema / metrics /
> results NOT touched. Read the RATIFIED amendment §0 (integrity commitment — report honestly regardless of
> outcome), §2 (H-A14), §3 (the "unfiltered = NO default-screen filter" core), §4 (run), §5 (provenance).

## 0. Provenance & governance
- Implementer = Claude; cross-family auditor = GPT `gpt-5.6-sol` (executable gold + anti-leakage + confirms
  NO default-screen inclusion filter was applied + sidecar isolation). Work in a dedicated worktree.
- Executable deterministic gold ONLY (Law 7). Anti-leakage. Constructor = mai-code (out-of-pool), documented.

## 1. Deliverable
- NEW sidecar `bench/data/amd14_unfiltered.jsonl`: N≈20–30 underspecified items (same reversal construction:
  a genuine non-default I0 in the hidden `latent_spec` + a deleted disambiguator), across the confirmatory
  domains/conventions. **CRITICAL: do NOT apply the default-check as an inclusion filter** — keep EVERY
  constructed item regardless of whether models default to the foil. Record per-item default behavior post
  hoc for transparency (NEVER for include/exclude).
- Executable gold checkers per item (sidecar module if needed; do NOT edit frozen `bench/*.py`).
- Item schema identical to the frozen items (Task/Interpretation); parses under `common.schema.Task`.

## 2. Run (AFTER Phase 2b 6-model scale + A13)
- Conditions: `single` + `heterogeneous-MAD`, ≥3 seeds, frozen roster, $0, resumable sidecar checkpoint
  (separate namespace, e.g. `cp_amd14_*.jsonl`). Reuse frozen harness/labeler/`cd_primary` read-only.
- Metric: frozen `cd_primary` (target I0).

## 3. Analysis + report (pre-registered SECONDARY robustness — H-A14)
- Report the UNCONDITIONED pooled `cd_primary` on the unfiltered sample + its item distribution + the DELTA
  vs the screened confirmatory rate (≈0.53 pooled), item-level bootstrap CI. HONEST per amendment §0: high,
  attenuated, or null — reported as-is. Deliver `files/amd14_results.md`.

## 4. Pipeline
Construct (Claude+mai-code) → GPT cross-family audit → merge → RUN (queued) → analyze → report honestly.
Merge gate = build+run + suite green + 0 BLOCKER/MAJOR (Law 4). No frozen touch; no LLM-judge; no filter.
