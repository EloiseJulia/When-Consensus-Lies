# Amendment 13 CONSTRUCTION + RUN SPEC — for the sub-agents (RATIFIED design)

> Manager-authored (orchestrator-only). Implements the owner-RATIFIED Amendment 13
> (`paper/preregistration/2026-07-23-amendment-13-regime-domain-crossing-RATIFIED.md`). Additive SIDECAR
> only. **The RUN starts only AFTER the Phase 2b pilot finishes** (owner-directed; proxy contention).
> Frozen 54 confirmatory items / `schema.py` / metrics / results are NOT touched.

## 0. Provenance & governance
- Implementer = Claude family (drafts items + executable gold + driver). Cross-family hostile auditor = GPT
  `gpt-5.6-sol` (executable-gold correctness + anti-leakage + genuine H2-derivability + no frozen touch).
- Work in a dedicated worktree/branch off `main`. Never edit the main checkout or any frozen file. New items
  live ONLY in sidecar files `bench/data/amd13_code_spec.jsonl`, `bench/data/amd13_policy_qa.jsonl` (do NOT
  edit the frozen `bench/data/{code_spec,policy_qa,data_analysis}.jsonl`).
- Executable deterministic gold ONLY (Law 7 — no LLM judge). Anti-leakage: no gold/target/foil/key_questions
  text in any tested-agent prompt.
- **Constructor provenance:** items authored with **Microsoft mai-code-1-flash** (the original primary
  constructor, OUTSIDE the tested pool) via the proxy; the Claude implementer orchestrates construction +
  writes the executable checkers, but the item SEMANTICS/prompts are mai-code-generated (documented). The
  regime contrast is computed on cells where tested-family ≠ constructor-family where applicable (A10-style);
  since mai-code is out-of-pool, all tested cells qualify.

## 1. Items to construct (RATIFIED scope: 4 H2 base tasks per domain)
- **code_spec:** 4 NEW `H2_derivable` base tasks. Each: a function spec whose ambiguous behavior is UNIQUELY
  pinned by an IN-PROMPT artifact a careful solver must use — a provided doctest/example I/O, an explicit
  type signature, or an internal invariant (e.g. rounding fn whose example output disambiguates half-even vs
  half-up; indexing fn whose example pins 0- vs 1-based; a fn whose docstring example fixes an edge-case
  convention). Ship k0 (fully specified) + k1 (the derivable-ambiguous variant) per base task.
- **policy_qa:** 4 NEW `H2_derivable` base tasks. Each: a numeric policy item whose disambiguating convention
  is STATED within the provided policy text / derivable by internal consistency (e.g. the threshold/rule is
  defined earlier in the SAME provided passage and must be read+applied), NOT an external org KPI. Ship
  k0 + k1 per base task.
- Each item: `id`, `domain`, `prompt` (k1 = derivable-ambiguous; k0 = fully specified), `latent_spec`,
  `interpretations` [{I0 target, I1.., I_perp}], `ambiguity_level`, `key_questions`, `regime="H2_derivable"`,
  plus EXECUTABLE gold checkers wired the SAME way as the frozen benchmark (see `bench/code_spec.py`,
  `bench/policy_qa.py`, and existing items for the exact contract).
- Also identify/enumerate the MATCHED `H1_external` anchors already present in code_spec/policy_qa for the
  within-domain contrast (do not re-author; reference existing frozen H1 items read-only for comparison).

## 2. Mandatory manipulation-check GATE (pre-committed validity gate)
Before any headline analysis, run the FROZEN oracle-hint recovery probe on the NEW items: supply the oracle
hint and measure recovery-rate. Pre-committed: recovery HIGH on the new H2 items (they ARE derivable) and
LOW on matched H1. **If the new "H2" items do NOT separate (recovery not high), REPORT the construction
failure honestly and DO NOT claim the crossing — do NOT tune items to force separation.** This gate decides
whether H-A13 can be tested at all.

## 3. Run (AFTER the Phase 2b pilot completes)
- Conditions: `single` + `heterogeneous-MAD` (cross-family), ≥ 3 seeds, frozen roster, $0 via proxy,
  resumable checkpoint under `.run_partitions/` (separate namespace, e.g. `cp_amd13_*.jsonl`) + own cache.
  Reuse the frozen harness/labeler/`cd_primary` read-only. Do NOT write any confirmatory checkpoint/cache.
- Metric: frozen `cd_primary` (target I0), per-domain, per-regime.

## 4. Analysis + report (pre-registered SECONDARY robustness — H-A13)
- Per domain (code_spec, policy_qa, and data_analysis for reference): `cd_primary(H1) − cd_primary(H2)` with
  item-level bootstrap CI; pre-committed direction > 0 within each domain.
- A `regime × domain` analysis: show the regime main effect holds with NO explanatory regime×domain
  interaction (i.e. H1→high / H2→low is NOT a domain artifact). Report honestly incl. any null / manipulation-
  check outcome.
- Deliver a report (sidecar, e.g. `files/amd13_results.md`); the Manager integrates into the paper as a
  pre-registered secondary robustness result (like Phase B), never as a confirmatory change.

## 5. Pipeline
Construct items (Claude, mai-code-authored) → GPT cross-family audit (executable-gold correctness, anti-
leakage, genuine H2-derivability via manipulation-check, no frozen touch, sidecar isolation) → merge →
RUN (after pilot) → analyze → report. One clean audit → merge (Law 5). Merge gate = build+run + suite green +
0 BLOCKER/MAJOR (Law 4).

## 6. Out of scope
No edits to frozen files / 54 confirmatory items / schema / metrics. No LLM-judge gold. No tuning to force the
manipulation check. No claim of a confirmatory change — this is pre-registered secondary robustness.
