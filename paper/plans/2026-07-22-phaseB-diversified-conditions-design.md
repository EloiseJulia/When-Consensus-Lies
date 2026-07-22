# Phase B — Diversified-evidence computational conditions (EXPLORATORY) — design spec

> Manager-authored design + pre-commitment for two NEW, post-hoc **EXPLORATORY** computational conditions
> that test the paper's constructive design principle: *"diversify evidence and interpretations, not merely
> model providers."* Owner chose **Option B** (2026-07-22). Grounding: `comment1.md` §六 Conditions 5 & 7;
> the landscape audit (`paper/research/2026-07-22-multimodel-interface-landscape-audit.md`) shows real
> interfaces offer *synthesis* and could offer *role/evidence diversification*.
>
> **SCIENTIFIC-INTEGRITY STANCE (read first).** These conditions are added AFTER the confirmatory run is
> complete. Reporting them as confirmatory would be p-hacking. Therefore they are:
> (1) **EXPLORATORY / secondary**, never relabeled confirmatory; (2) **pre-committed** here (prompts, roles,
> aggregation, item set, metric, and the directional predictions) BEFORE any run; (3) they change **NO**
> frozen definition — same `cd_primary`/A04 metric, same abstention detector, same H1_external items.
> They are registered via **Amendment 12 (DRAFT)**, which requires **owner @EloiseJulia PERSONAL
> ratification before the run** (never AI-self-signed). No run launches until A12 is ratified.

---

## 1. Why (the CHI payoff)
The paper's negative result: cross-vendor same-prompt comparison does NOT restore interpretive independence
(fake redundancy; `n_eff≈1.1`). Phase B asks whether two interventions that a real multi-model interface
could deploy change that:
- **C5 Cross-vendor synthesis** — the common "one extra model merges all answers" affordance (audit shows
  Open WebUI / PromptQuorum / MultipleChat offer merged/consensus answers). *Hypothesized to NOT help* — a
  synthesizer over shared-wrong answers launders a shared error into one confident wrong answer, possibly
  LOWERING abstention. A valuable NEGATIVE result: synthesis UIs manufacture false confidence.
- **C7 Role-diversified evidence workflow** — the constructive intervention: give agents distinct
  epistemic ROLES (solve / find-missing-info / propose-alternatives / check-defaults / integrate) instead
  of all answering the same question. *Hypothesized to help* — reduce `cd_primary` and/or raise
  clarification-seeking on H1_external items. If it helps with ONLY generic (non-oracle) scaffolding, the
  paper earns a constructive design contribution; if it does NOT help, that strengthens the "the
  information boundary is the problem, not the aggregation recipe" thesis. Either outcome is publishable.

## 2. The two conditions (pre-committed mechanics)

### C5 `cross-vendor-synthesis`
1. **Generation:** the frozen `heterogeneous` cross-family pool (OpenAI gpt-5.4, Anthropic
   claude-sonnet-4.6, Google gemini-3.1-pro) each answer the SAME task prompt INDEPENDENTLY (one shot,
   temperature = the frozen sampling default), producing candidate answers `c1..cN`. Same prompt template
   as `single` (`PROMPT_SINGLE_V2`) — no interpretation hints, no gold reference.
2. **Synthesis:** a synthesizer model produces ONE final answer from `{c1..cN}`. Synthesizer =
   `microsoft/mai-code-1-flash-picker` (the frozen `judge`/constructor family, OUTSIDE the tested pool → no
   provenance contamination; it never contributed a candidate). Synthesizer prompt (pre-committed, generic):
   *"You are given several candidate answers to the same task. Produce the single best final answer in the
   required answer format. If the candidates are based on differing assumptions, choose the most defensible
   and state the final answer."* — NO gold, NO target hint, NO "these may be wrong" priming beyond neutral.
3. **Label:** apply the frozen labeler to the synthesizer's final answer → one interpretation label per
   (item, seed). `cd_primary` for a synthesis "cell" is defined over the seed replicates (the ensemble
   collapses to one answer, so the unit is the synthesized answer across the 3 seeds; report the modal-wrong
   share and the abstention/clarification flag). Also record whether the synthesized answer matches the
   modal candidate (did synthesis inherit the shared wrong interpretation?).

### C7 `role-diversified`
Five cross-family agents, each a DISTINCT generic epistemic role. **Role prompts are GENERIC epistemic
scaffolding and MUST NOT reference the specific missing convention, the target interpretation, the
enumerated foils, or any gold_check** (this is the hard anti-leakage rule — see §4). Roles (pre-committed):
- **R1 Solver** (openai gpt-5.4): answer the task normally, in the answer format.
- **R2 Gap-finder** (anthropic claude-sonnet-4.6): *"List any information NOT specified in the prompt that
  could change the correct answer. Do not answer the task."* (generic; no naming the specific axis).
- **R3 Alternatives** (google gemini-3.1-pro): *"List the distinct plausible interpretations of this task
  that are each consistent with the prompt as written."* (generic; enumerates its OWN interpretations, not
  ours).
- **R4 Default-checker** (openai gpt-5.4, distinct seed): *"State the default assumptions a solver would
  make here, and for each, whether the prompt actually fixes it."*
- **R5 Integrator** (anthropic claude-opus-4.8, reasoning tier): given R1–R4's outputs, produce the final
  answer OR a clarification request. Pre-committed instruction: *"Do not treat agreement among the earlier
  responses as evidence of correctness. If the earlier analysis shows that a decision-relevant detail is
  unspecified, respond with a clarification request in the answer-format's abstain form; otherwise give the
  best final answer."*
- **Label:** frozen labeler on R5's output → one label (or abstain/clarify) per (item, seed).

Family assignments respect Law 6 (constructor microsoft ∉ tested pool; roles drawn from the tested
families). Seeds: the 3 frozen collision-free seeds `[global, global+1000, global+2000]`, stride ≥ role
count.

## 3. Item set, metric, comparison (pre-committed)
- **Items:** the FROZEN H1_external set (40 items) is the primary test bed (the regime where the failure
  occurs). The FROZEN H2_derivable set (14 items) is run as a CONTROL (interventions should not break the
  already-resolved regime). No new items; no item edits.
- **Metric:** the FROZEN `cd_primary`/A04 (modal-wrong over enumerated foils; I_perp ineligible) + the
  frozen rule-based abstention/clarification detector. Report the same A04 sensitivities (I_perp-eligible;
  drop-I_perp). **No new metric.**
- **Baseline for the contrast:** the confirmatory `heterogeneous-MAD` (= "cross-vendor comparison/
  aggregation") on the SAME 40 H1_external items (already in the confirmatory data).
- **Pre-committed predictions (directional, registered BEFORE running):**
  - **P-B1 (C5 synthesis):** `cd_primary(synthesis)` is NOT meaningfully lower than
    `cd_primary(heterogeneous-MAD)` on H1_external (Δ CI overlaps 0 or is positive); abstention stays
    ≈0. Interpretation: synthesis does not restore independence and may increase confident error.
  - **P-B2 (C7 role-diversified):** `cd_primary(role-diversified)` is LOWER than
    `cd_primary(heterogeneous-MAD)` on H1_external, **and/or** the clarification/abstention rate is
    substantially HIGHER, using only generic (non-oracle) scaffolding.
  - Report item-level bootstrap CIs (same machinery as R1a/R1b). Whatever the outcome, report honestly;
    a null for P-B2 is theoretically informative (boundary dominates recipe).

## 4. Anti-leakage & construct-validity guardrails (inviolable for the implementer)
- **No oracle.** No role/synthesis prompt may contain: the target interpretation, the specific deleted
  convention/axis, the enumerated foils, `interp.id`, `gold_check`, `is_target`, or any per-task hint
  derived from the answer key. (This is exactly why the confirmatory `interpretation-diverse` was excluded
  from primary methods — A11. C7 must be honestly generic to be defensible.)
- **Same prompt boundary.** All agents receive the SAME underspecified task prompt as `single`/confirmatory
  — the point is that diversifying ROLES over a shared boundary is what's tested, not diversifying inputs.
- **Additive isolation.** Implement in a NEW driver + NEW module; do NOT edit the confirmatory path in
  `harness/run.py`, `harness/runner.py`, `scripts/registered_run.py`, or any frozen file. Separate
  checkpoint (`.run_partitions/cp_phaseB.jsonl`) and cache (`.llm_cache_phaseB`). Reuse the frozen labeler,
  `cd_primary`, and abstention detector by import only.
- **Offline/CI safe.** `main()` guarded by `RUNNER_LIVE=1` + reachable proxy; `--dry-run` enumerates jobs
  with no network; pure `run()` callable by offline tests (mock client).

## 5. Budget (owner is caution-first)
$0 via the local ghc-api proxy. Estimate: H1_external 40 items × 3 seeds × (C5 ≈ 3 gen + 1 synth = 4 calls;
C7 ≈ 5 role calls) ≈ 40×3×9 ≈ 1,080 calls, + H2 control 14×3×9 ≈ 380 ≈ **~1,460 calls, $0**. Sequential;
resumable checkpoint; lean on cache. Small and safe.

## 6. Process (Manager-owned)
1. **A12 DRAFT → owner PERSONAL ratification** (this doc + the draft amendment). NO run before ratification.
2. Implementer sub-agent (**Claude family**) in worktree `phaseB-diversified`: additive driver + module,
   dry-run + offline unit tests, self-check gate.
3. Hostile auditor (**GPT family**, report-only): verify §4 anti-leakage (grep prompts for gold/target/foil
   leakage), additive isolation, frozen-file untouched, metric reuse, 0 BLOCKER/MAJOR.
4. After owner GO + audit clean: `RUNNER_LIVE=1` run ($0); analyze with frozen machinery; DECISION-LOG row.
5. Write up as EXPLORATORY in Results/Discussion + Future Work; never confirmatory.

## 7. What stays FROZEN (unchanged)
`cd_primary`/A04, H1/H2 hypotheses, regime criterion, R1(A07)/R2(A11) nulls, §9 decision rules, the
confirmatory item set + grid + numbers. Phase B adds exploratory conditions only; it fixes nothing and
chases no significance.
