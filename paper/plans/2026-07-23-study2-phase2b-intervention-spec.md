# Study-2 Phase 2b — Intervention closed-loop IMPLEMENTATION SPEC (for the Claude implementer sub-agent)

> Manager-authored spec (orchestrator-only). Implements the FROZEN prereg hypotheses **H-B1′**
> (selective clarification) and **H-B2′** (oracle resolution) from
> `paper/preregistration/2026-07-23-study2-prereg-FROZEN.md`. Owner-decided run scope (DECISION-LOG row 89):
> **single model `gpt-5.6-sol` × 3 seeds × all 54 items FIRST** (caution-first pilot), then the Manager
> decides whether to scale to the full 6-model roster. This spec is ADDITIVE — it must NOT touch any frozen
> file, any confirmatory checkpoint/cache, or any metric definition. Metric/hypothesis defs are FROZEN;
> do NOT change them (Law 7).

## 0. Provenance & governance (READ FIRST — inviolable)
- **You are the implementer = Claude family.** The independent hostile auditor will be **GPT `gpt-5.6-sol`**
  (different family, Law 6). Record your model family in the PR body.
- Work ONLY in your assigned git worktree/branch. Never edit the main checkout. Never edit any frozen file
  (`paper/preregistration/*FROZEN*`, the frozen benchmark/labeler/harness, confirmatory checkpoints).
- **Anti-leakage (inviolable):** no model-facing prompt may contain any gold / target / foil / key_questions
  / interpretation text. The clarification prompts you generate must be GENERIC. The ONLY place gold enters
  is the H-B2′ **oracle** (the deleted-axis convention supplied "by the simulated user") — and that is an
  EVALUATION-time controlled injection, framed as a controlled oracle, NOT leakage into the detector.
- Executable gold > LLM-judge (Law 7): resolution success is scored by the **executable** `cd_primary`
  label, never by an LLM judge.

## 1. What already exists (reuse read-only; do NOT reimplement)
- `scripts/lps_method.py`:
  - `lpp_detect(task, client, model, *, tau, tau_s, k, ...) -> dict` — returns `is_flagged`,
    `flagged_dimension`, `H_seed`, `H_ctx_max`, `surfaced_dims`, `per_dim`, `seed_labels`. This is the LPP
    gate for H-B1′.
  - `H_seed(...)`, `surface_assumptions(...)`, `H_ctx(...)`, `_label_answer(text, task, model_id, seed)`,
    `_complete_text(client, prompt, model, seed, temperature)`, `_with_contract(prompt, domain)`,
    `answer_signature`, `_sig_equal`.
  - FROZEN operating point: `DEFAULT_TAU=0.0`, `DEFAULT_TAU_S=0.5`, method version
    `lps-2026-07-23-v5-pairwise-tol`.
- `scripts/lps_gold.py`: `gold_ambiguity(task) -> {stratum, n_interp, n_distinct, H_ctx_gold,
  interp_signatures}` with strata `AMB+ / NON-DISC / AMB-`. Use this to define the gold clarification NEED.
- `analysis/cd.py`: `cd_primary(labels, target="I0") -> float` (convergent-delusion; the executable metric),
  plus `cd_all_variants`. The resolution success metric = `cd_primary` over the post-clarification labels.
- `common/schema.py`: `Task` (has `.id, .domain, .prompt, .regime, .ambiguity_level, .key_questions`).
- Benchmark interpretation gold: `bench.<domain>.get_checkers_and_candidates(domain, task)` gives the
  enumerated interpretations `{I0, I1, ...}` and their gold implementations / expected amounts (see
  `lps_gold._interpretation_signatures` for the exact call pattern). `I0` = the user's true hidden intent.
- The confirmatory driver `scripts/lps_confirm.py` is the pattern for: RUNNER_LIVE guard, per-model
  sharded checkpoint under `.run_partitions/`, resumable fingerprinting, `--dry-run`, disk cache. MIRROR
  its safety patterns; do NOT write into its checkpoints/cache.

## 2. H-B1′ — selective clarification (detection→action)
**Claim (frozen):** the LPP gate triggers a clarification on **AMB+** items (needed) but NOT on **AMB−**
(k0 / unambiguous), and does so BETTER than (a) an always-clarify baseline and (b) a semantic-entropy-gated
baseline (which under-fires in the danger zone because `H_seed` is low there).

**Implement:** for each (item, seed), compute the clarify DECISION under each policy, using signals you
already have from `lpp_detect`:
- **LPP-gated (ours):** clarify iff `is_flagged` (i.e. `H_ctx_max > τ ∧ H_seed ≤ τ_s`, FROZEN τ=0, τ_s=0.5).
- **always-clarify baseline:** clarify = True for every item.
- **semantic-entropy-gated baseline:** clarify iff `H_seed > τ_s` (the SOTA policy: ask only when resampling
  looks uncertain). This should MISS the danger quadrant.
- (Optional, if cheap) **self-consistency-gated** and **requirements-probing-gated** for completeness —
  requirements-probing gate = clarify iff ≥1 surfaced dimension exists (surfacing WITHOUT the pinning test),
  to mirror the strong 0.81 detection baseline.

**Gold need:** an item NEEDS clarification iff `gold_ambiguity(task).stratum == "AMB+"`; it should NOT be
clarified iff `AMB-`. Report NON-DISC separately (informative, not an error).

**Pre-registered metric (H-B1′):** per policy, over items aggregated across seeds (mean per item, then over
items, matching the confirmatory per-item aggregation):
- `appropriate_clarification` = clarify-rate on AMB+ (want HIGH).
- `over_clarification` = clarify-rate on AMB− (want LOW; = k0 false-alarm).
- headline contrast = `appropriate_clarification(AMB+) − over_clarification(AMB−) > 0`, and LPP-gated ≥
  each baseline on this net score. Show the semantic-entropy gate has LOW AMB+ coverage in the low-`H_seed`
  danger subset. Report item-level bootstrap CIs (reuse `registered_run._bootstrap_ci` if importable, else a
  simple cluster-by-`task_id` bootstrap consistent with `lps_confirm_report.py`).

## 3. H-B2′ — oracle resolution (does surfacing the right axis FIX the delusion?)
**Claim (frozen):** when the true convention (the deleted axis's gold value) is supplied on clarification
(a CONTROLLED ORACLE = "simulated user"), the answer moves to **I0** and `cd_primary → 0` (executable gold).
Real-user study is future work — frame strictly as a controlled oracle, no human-behavior claim.

**Implement, per (AMB+ item, seed):**
1. **Baseline (never-clarify) answer** — the committed answer WITHOUT clarification. Reuse the same generic
   answer prompt the confirmatory/detector path uses (`_with_contract` + the frozen answer contract) so the
   label is comparable. Label it via `_label_answer`. This reproduces the silent-convergence baseline
   `cd_primary` (~0.5 on AMB+, sanity-check against Study-1/detection).
2. **Oracle-resolved answer** — re-ask with the deleted axis's GOLD convention appended as a user-supplied
   clarification, e.g. `"Clarification from the user: for <axis>, use <gold convention> = <I0 value>."`
   Derive the axis + its I0 convention from the benchmark interpretation gold (I0), NOT from the model. This
   gold text goes ONLY into THIS oracle re-ask (evaluation-time), never into the detector/surfacing prompts.
   Label via `_label_answer`.
3. **Metric:** `cd_primary(labels_baseline, "I0")` vs `cd_primary(labels_oracle, "I0")` over AMB+ items;
   pre-committed direction = oracle `cd_primary → 0` (a large, CI-separated drop). Report the paired delta
   with item-level bootstrap CI. Also report the I0-hit rate (fraction of oracle answers labeled I0).

**Honesty guards:** if some AMB+ items do NOT resolve to I0 even with the oracle (e.g. the model ignores the
convention, or the gold convention is itself under-determined), REPORT that honestly — it bounds how much of
the failure is "surfacable + resolvable." Do NOT tune anything to force cd→0.

## 4. Deliverables (files — all NEW, additive)
- `scripts/lps_intervention.py` — driver: RUNNER_LIVE-guarded, `--models gpt-5.6-sol`, `--seeds <3>`,
  `--dry-run` (enumerates jobs, no calls), resumable per-model checkpoint under `.run_partitions/`
  (e.g. `cp_lps_intervention__<sanitized>.jsonl`) + its OWN disk cache dir (e.g. `.llm_cache_lps_intv/`);
  MUST NOT read/write any confirmatory checkpoint/cache. Computes H-B1′ decisions (all policies) + H-B2′
  baseline/oracle answers per (item, seed).
- `scripts/lps_intervention_report.py` — aggregates the checkpoint → the H-B1′ table (per-policy
  appropriate/over-clarification + net score + CIs) and the H-B2′ table (baseline vs oracle `cd_primary` +
  I0-hit + CI), plus honesty notes (NON-DISC handling, unresolved AMB+). Mirror the reporting/aggregation
  conventions of `scripts/lps_confirm_report.py` (per-item mean across seeds; cluster-bootstrap by task_id).
- `tests/test_lps_intervention.py` — deterministic unit tests with a STUB client (no live calls): (a) LPP
  gate vs always vs semantic-entropy gate produce the expected clarify decisions on synthetic
  AMB+/AMB−/danger-quadrant items; (b) H-B2′ oracle path maps a stub "I0 convention" answer to label I0 and
  drives `cd_primary → 0`, while the baseline path yields a non-zero `cd_primary`; (c) anti-leakage: assert
  no gold/target/foil/key_questions string appears in any DETECTOR/surfacing/clarify prompt (only the oracle
  re-ask may contain the gold convention); (d) the driver refuses to touch confirmatory checkpoints/cache.
- Reuse the frozen method version fingerprint; if you add an intervention version tag, make it a NEW constant
  (e.g. `INTERVENTION_VERSION = "lps-intv-2026-07-23-v1"`), do not mutate `METHOD_VERSION`.

## 5. Self-check gate (before you mark the PR ready)
1. `pytest -q` — full suite GREEN (currently 1014+ tests; your new tests included).
2. `python -c "import common"` build sanity; import all new scripts.
3. `python scripts/lps_intervention.py --models gpt-5.6-sol --seeds <3> --dry-run` enumerates the expected
   job count with NO live calls and NO writes to confirmatory paths.
4. Grep-verify anti-leakage: no gold/target/foil/key_questions/interpretation text can reach a detector or
   clarification prompt (only the H-B2′ oracle re-ask carries the gold convention). Show the guard test.
5. Write the PR body: model family (Claude), files added, the H-B1′/H-B2′ wiring, the anti-leakage argument,
   the "reuses frozen cd_primary/labeler/lpp_detect/gold read-only" note, and a PROMINENT call-out if you
   touched ANY shared infra (you should not need to).
6. **Do NOT run the live grid** — the Manager launches the $0 live run after the cross-family audit + merge.
   Your job ends at: additive code + green tests + clean dry-run + PR ready.

## 6. Explicitly OUT of scope (do not do)
- No changes to any frozen file, confirmatory checkpoint/cache, or metric definition.
- No 6-model run (owner scoped this to gpt-5.6-sol first; the driver must ACCEPT `--models` but the pilot
  runs one model).
- No AU-Probe / Phase 2c work (separate, later).
- No paper/tex edits (the Manager handles writing after results land).
- No fabricated data; no LLM-judge scoring of resolution (executable `cd_primary` only).
