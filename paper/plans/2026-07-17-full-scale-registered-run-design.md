# Full-scale Registered Run — design for OWNER SIGN-OFF (2026-07-17)

> The §11 MVP pilot PASSED cleanly (decision-log row 60: Gate A + R1a + R1b + Gate C all green, I_perp
> 0.076, $0). Per prereg §11 the gate to scale is satisfied. This document is the CONFIRMATORY-run design
> the Manager brings for owner sign-off BEFORE launch (the "moment before scaling"). Nothing is launched
> until you sign §7. Metric/hypotheses/regime/decision-rules/R2 are FROZEN; R1 was redefined by the SIGNED
> Amendment 07.

## 1. Roster & substrate (SIGNED Amendment 06)
Frontier Copilot proxy (`ghc-api`, $0, uncapped except gpt-4o-mini's intermittent UserByModelByDay — the
resumable day-spanning runner handles it, demonstrated in the pilot). Roster: tested homogeneous=gpt-5.4
(logprobs ρ-baseline); heterogeneous=gpt-5.4/claude-sonnet-4.6/gemini-3.1-pro (O/A/G); reasoning=
gpt-5.6-sol/claude-opus-4.8/gemini-3.1-pro; weak=gpt-4o-mini/gemini-3.5-flash/claude-haiku-4.5;
constructor+judge=mai-code (M, judge vestigial under executable gold); code_reviewer=gpt-5.6-sol.

## 2. ⭐ Item set — RECOMMEND the current reconstructed benchmark (NO expansion)
Current benchmark = **46 task families** across k∈{0,1,2,3}:
- code_spec 20 (all H1_external) · policy_qa 14 (all H1_external) · data_analysis 12 (6 H1_external +
  6 H2_derivable). Totals: **H1_external=40, H2_derivable=6.**
Rationale for NO expansion (vs §10's aspirational 60–100/domain): the effects are ENORMOUS (H1 CD≈1.0;
H2 →I0≈1.0), far above §10's target detectable ΔCD≥0.15. The pilot's R1a CI already excluded 0 with just
2 k≥1 items. §10 explicitly says "the MVP pilot calibrates final N"; the pilot shows the current set is
amply powered for every PRIMARY contrast (see §4). Expansion would be weeks of benchmark work for
negligible power gain on already-saturated effects.
- CAVEAT (transparent): **H2_derivable has only 6 items** (all data_analysis). This bounds the PRECISION
  of the H2 arm — but H2's reasoner-vs-weak INTERACTION is a pre-registered SECONDARY test we expect to be
  NULL (rows 51-52; the two-regime demarcation is a REGIME MAIN EFFECT). We report H2 honestly and, if
  underpowered for the interaction, SAY SO (never backfill). The regime MAIN effect (H1 traps all vs H2
  resolved by all) is well-powered even at 6 vs 40 given Δ≈1.0.

## 3. Config grid & replication (prereg §10)
Per (item × config × model × seed), keyed to the resumable runner's AgentRun identity:
- **Methods:** single (N=1 baseline) · SC k=5 · homogeneous-MAD N=5 · heterogeneous-MAD (3-family pool).
  (RECOMMEND deferring SC k=10 and verifier to a sensitivity pass — k=5 already saturates; k=10 doubles
  SC cost for little marginal information. Decision point for you.)
- **Model classes:** homogeneous (gpt-5.4) · heterogeneous (pool) · reasoning (3) · weak (3).
- **Seeds:** ≥3 distinct, collision-free (stride ≥ ensemble size) per (item × config) — enforced by the
  runner (the ≥3-seed guard from PR #30). Genuine independent replicates (the replicate-seed fix, PR #30).

## 4. Power / precision (grounded in the pilot)
Primary contrasts and their effect sizes (all ≫ the §10 target ΔCD≥0.15):
- H1a aggregation-vs-single, cross-model-vs-homogeneous (row-35 headline), regime H1-vs-H2: pilot Δ≈0.5–1.0.
- R1a k0-vs-k≥1 hard control: pilot CD_k0=0.000 vs CD_{k≥1}=0.766 (Δ≈0.77).
- R1b uniform-null gap: pilot obs 0.766 vs uniform 0.501 (Δ≈0.27).
With 40 H1 items × ≥3 seeds × 4 methods the crossed-RE mixed model (§8) yields tight CIs; power ≈ 1.0 for
every primary H1 contrast. **Only underpowered arm: the H2 reasoner×model_class INTERACTION (6 H2 items)** —
pre-registered SECONDARY, expected null, reported transparently.
- H1a caveat (row 56): for MULTI-model classes (reasoning/weak) "single" is a cross-model pool, not N=1;
  restrict the aggregation-vs-single (H1a) single-baseline to the single-model (homogeneous) class, or
  document the pooled semantics — to settle at the analysis stage.

## 5. Execution plan
Resumable runner on `--provider copilot_proxy`, day-spanning (gpt-4o-mini cap), $0. Estimated grid ≈ a few
thousand jobs (46 items × ~3 seeds × 4 methods × per-model enumeration); many hours to ~a day of wall-clock
on the proxy, fully checkpointed/resumable. Endpoint-namespaced checkpoint (no cross-endpoint pooling).
Then Phase-6 analysis (merged `analysis/` pipeline + A04 CD variants + A07 R1a/R1b + §8/§9 rules) on the
real AgentRun JSONL → figures → writing.

## 6. Pre-registration status
No NEW amendment needed for the item set (§10 delegates final N to the pilot; the pilot calibrated it).
If you choose to FIX the exact N (items/seeds/methods) as a frozen record, I will file a short
**Amendment 08** (N calibration) documenting the pilot-calibrated N + this power argument — recommended for
a clean "Deviations" section. Metric/hypotheses/regime/decision-rules/R2 unchanged; R1 per A07.

## 7. ⭐ OWNER SIGN-OFF (required before launching the confirmatory run)
- [ ] Item set: current 46-task reconstructed benchmark (NO expansion) — or expand H2 first?
- [ ] Config grid: single + SC k=5 + homogeneous-MAD N=5 + heterogeneous-MAD; defer SC k=10 + verifier
      to a sensitivity pass — or include them now?
- [ ] Seeds: ≥3 per (item × config) — confirm 3 (or specify).
- [ ] File Amendment 08 (pilot-calibrated N + power) for the record? (recommended) — or proceed under
      §10's "pilot calibrates N" clause without a new amendment?
- [ ] On sign-off, the Manager launches the resumable confirmatory run (day-spanning, $0), then Phase-6
      real analysis → figures → writing. This is the CONFIRMATORY run; results count toward H1/H2.
