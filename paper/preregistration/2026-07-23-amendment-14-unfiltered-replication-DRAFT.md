# Amendment 14 (DRAFT — awaiting owner @EloiseJulia PERSONAL ratification) — unfiltered-sample replication

> STATUS: **DRAFT. NOT SIGNED. NOT frozen. NO construction or run until owner personally ratifies.** The
> Manager NEVER self-signs a frozen-contract change. Motivation: owner raised the benchmark SELECTION-BIAS
> concern (2026-07-23) — the confirmatory benchmark's inclusion was partly conditioned on an empirical
> default-check (unaware capable models produce the intended foil), which "could inflate observed
> convergence" (already disclosed in the paper's Construct-validity subsection). This amendment does the
> paper's already-listed future work — a fully UNFILTERED-sample replication (NO default screen) — as a
> pre-registered SECONDARY robustness experiment to bound how much of the effect is enrichment-driven.

## 0. Scientific-integrity commitment (owner-agreed 2026-07-23)
Owner directive: "先A和B都做，如果B做出来效果好就保留，效果不好就不要B只做A." Operationalized WITHOUT selective
reporting: **B (this experiment) is PRE-REGISTERED and REPORTED HONESTLY regardless of outcome.** The
"keep/drop" governs PROMINENCE, NOT suppression:
- If the unfiltered convergent-delusion rate stays HIGH → B becomes a PROMINENT headline rebuttal to the
  selection-bias attack.
- If it ATTENUATES → that is an HONEST, INFORMATIVE bound (the effect is partly enrichment-driven); we report
  it and SHARPEN the claim to its conditional form. We do NOT delete a valid disconfirming result.
- B is dropped ENTIRELY only for METHODOLOGICAL INVALIDITY (e.g. no clean unfiltered sample can be
  constructed), never to hide a valid-but-inconvenient result. (Consistent with the project's refusal to
  fabricate the abstention labels.)

## 1. What this ADDS (and must NOT touch)
- ADDS a pre-registered SECONDARY ROBUSTNESS replication on a NEW, ADDITIVE **sidecar item set**
  (`bench/data/amd14_*.jsonl`) of underspecified items constructed by the SAME reversal rule (a genuine
  non-default I0 + a deleted disambiguator) but WITHOUT the default-screen inclusion filter — i.e. items are
  KEPT regardless of whether unaware models default to the foil.
- **INVIOLABLE:** does NOT modify the frozen `bench/data/*.jsonl`, the 54 confirmatory items, `schema.py`,
  any metric, or any confirmatory result. Reported as pre-registered secondary robustness (like A12/A13).

## 2. Pre-registered hypothesis + reporting rule (FROZEN on ratification)
- **H-A14 (unfiltered convergence):** on the UNFILTERED sample (no default-screen), the cross-family
  convergent-delusion rate on H1-type (external-disambiguator-deleted) items is reported UNCONDITIONALLY.
  Pre-committed READING (not a pass/fail gate): compare unfiltered `cd_primary` to the screened confirmatory
  rate (≈0.53 pooled / higher on strong traps). We report the unfiltered rate + the DELTA with item-level
  bootstrap CI. NO tuning; the outcome (high, attenuated, or null) is reported as-is.
- Metric = the FROZEN `cd_primary` (target I0); NO metric redefinition. Same anti-leakage; executable gold.

## 3. Item construction (the "unfiltered" definition — the anti-cherry-pick core)
- Build a POOL of N underspecified items across the same domains/conventions as the confirmatory benchmark
  (calendar/fiscal, rounding, indexing, thresholds, central-tendency, etc.), each with a genuine non-default
  I0 (in the hidden `latent_spec`) and a deleted disambiguator — the SAME reversal construction.
- **DO NOT run the default-check as an inclusion filter.** Keep EVERY constructed item, including ones where
  models split, resolve to I0, or default elsewhere. The whole point is the UNCONDITIONED rate. (Record each
  item's default-behavior post hoc for transparency, but never use it to include/exclude.)
- Executable deterministic gold per item (Law 7). Constructor = Microsoft mai-code (out-of-pool), documented.
- Sample size: RECOMMENDED N ≈ 20–30 unfiltered items (caution-first; enough for a bootstrap CI on the
  pooled rate). Owner to confirm §7.

## 4. Run + analysis
- Conditions: `single` + `heterogeneous-MAD` (the headline cross-family conditions that show fake
  redundancy), ≥ 3 seeds, frozen roster, $0 via proxy, resumable sidecar checkpoint (separate namespace).
- Analysis: pooled unfiltered `cd_primary` + its distribution across items; the DELTA vs the screened rate;
  the fraction of unfiltered items that still exhibit convergent delusion. Report honestly per §0/§2.
- Deliver `files/amd14_results.md`; Manager integrates as a pre-registered secondary robustness result and
  updates the Construct-validity/Limitations framing accordingly.

## 5. Provenance / anti-leakage
Constructor out-of-pool (mai-code); executable gold (no LLM judge); no gold/target/foil/key_questions in any
tested-agent prompt; per-item family separation; cross-family audit of the construction + run code.

## 6. Pipeline
Construct unfiltered items (Claude+mai-code) → GPT cross-family audit (executable gold, anti-leakage, NO
default-screen filter applied, sidecar isolation, no frozen touch) → merge → RUN (queued after the Phase 2b
6-model scale + A13) → analyze → report honestly (per §0).

## 7. Owner ratification points (confirm/adjust BEFORE construction)
1. **Sample size:** OK with N ≈ 20–30 unfiltered items? (adjust)
2. **Conditions:** `single` + `heterogeneous-MAD`, ≥3 seeds, $0? (or add SC/verifier?)
3. **Constructor:** mai-code (out-of-pool), executable gold — OK?
4. **Integrity framing (§0):** confirm you agree B is reported honestly regardless of outcome (prominence,
   not suppression). If you truly want B DROPPED on a valid-but-weak result, say so now — but I will flag
   that as selective reporting and recommend against it.
