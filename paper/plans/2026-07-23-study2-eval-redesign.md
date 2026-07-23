# Study 2 — REDESIGNED evaluation (executable ambiguity gold; breaks the H1/H2-label dependence)

> Owner decision 2026-07-23 (after 4 pilots): stop using the benchmark's H1/H2 REGIME labels as the
> ambiguity ground truth; define ambiguity by whether pinning changes the EXECUTABLE result. This doc is the
> redesigned evaluation for owner REVIEW before any confirmatory run. It REVISES the §3 evaluation of
> `2026-07-23-study2-latent-premise-sensitivity-design.md`; it does NOT touch the frozen confirmatory study
> or any frozen file (it READS the benchmark's interpretations, changes nothing). Requires owner ratification
> + a validation pilot on the re-stratified items before the confirmatory run.

## 0. Why the old eval was wrong (empirical, from pilot 4)
Item-level flags by regime bucket were H1_k1 2/8, H2 4/6, k0 0/4. But the "H2 false flags" (`data_typical`
central-tendency, `data_rate` interval) are GENUINELY premise-sensitive — pinning mean/median/mode yields
three mutually-disagreeing executable results (H_ctx=1.585). And `code_quarter_k1` (labeled H1) "missed"
because its gold TEST INPUTS don't discriminate the fiscal-year interpretations (all pins → identical
output). ⇒ the H1/H2 REGIME LABEL does not track genuine, testable ambiguity. k0 controls, however, were a
CLEAN negative (0/4) — true "no deleted axis" items never fire. So: keep k0 as gold-negatives; replace the
H1/H2 positive/negative split with an EXECUTABLE ambiguity label.

## 1. The executable ambiguity GOLD standard (detector-independent — this is the anti-circularity core)
For each benchmark item we ALREADY have (frozen, read-only): the deleted axis (`key_questions`) and the
ENUMERATED interpretations `{I0, I1, …, I_k}`, each with a gold implementation / expected result.

**Gold-ambiguity(item) := do the item's OWN enumerated interpretations produce DIFFERENT executable results
on the item's test inputs?** Computed WITHOUT the model:
- code/data: run each interpretation's gold implementation on the item's test inputs (read-only reuse of the
  executable harness); the item is **gold-ambiguous** iff ≥2 interpretations yield DIFFERENT outputs on ≥1
  test input (they are "discriminated"); **gold-non-discriminating** iff all interpretations coincide on the
  given inputs (the axis exists but is untestable there — e.g. `code_quarter` on non-discriminating dates).
- policy_qa (numeric): the item is gold-ambiguous iff its enumerated interpretations have ≥2 distinct
  expected amounts.
- k0 controls have no deleted axis ⇒ gold-UNambiguous by construction.

**Anti-circularity (critical):** the DETECTOR signal `H_ctx-self` clusters the MODEL's OWN self-generated
pins; the GOLD label clusters the BENCHMARK's ENUMERATED interpretations (gold implementations). These are
two INDEPENDENT pin-sets from two independent sources (model vs benchmark author). So evaluating H_ctx-self
against gold-ambiguity is NOT tautological — it asks "does a black-box model, generating its own candidate
premises, recover the benchmark-author's executable ambiguity structure?"

## 2. Re-stratification of items (replaces the H1/H2 positive split)
Compute gold-ambiguity for EVERY item → three strata:
- **AMB+ (gold-ambiguous):** ≥2 enumerated interpretations discriminate on the inputs. (Expected to include
  most H1_k≥1 AND the mislabeled "H2" items like typical/rate.) → detector SHOULD flag.
- **NON-DISC (axis exists but non-discriminating on given inputs):** e.g. `code_quarter`. Reported as a
  SEPARATE stratum (informative; a benchmark-coverage artifact, not a detector error). Optionally: regenerate
  discriminating test inputs (benchmark curation, owner-gated) to move these into AMB+.
- **AMB− (gold-unambiguous):** k0 controls + any item whose interpretations all coincide / disambiguator
  genuinely fixed in prompt. → detector should NOT flag.

## 3. Detection metrics (primary), against the executable gold — clean, non-circular
- **Two H_ctx variants:**
  - `H_ctx-self` = mutual-equivalence entropy over the MODEL's self-generated pins (the DEPLOYABLE detector).
  - `H_ctx-gold` = mutual-equivalence entropy over the BENCHMARK's enumerated-interpretation results (an
    ORACLE upper bound = essentially the gold-ambiguity magnitude).
- **PRIMARY H-A1′ (recovery):** does `H_ctx-self` TRACK gold-ambiguity? Report AUROC / precision-recall of
  `H_ctx-self` (and the item-level flag) for classifying AMB+ vs AMB−, with item-level bootstrap CIs.
  Target: high AUROC; k0 kept at ~0 false-positive (pilot already shows 0/4).
- **PRIMARY H-A2′ (localization):** does the model's argmax-`H_ctx-self` dimension correspond to the true
  deleted axis (`key_questions`) on AMB+ items? Report localization precision/recall. (Independent of the
  gold pins — the model must NAME the axis, gold used only to score.)
- **DANGER QUADRANT (the headline vs SOTA):** on AMB+ items, cross-tabulate `H_seed` (low/high) × `H_ctx-self`
  (low/high). The claim: a substantial mass of AMB+ items sit in **low-`H_seed` ∧ high-`H_ctx-self`** — i.e.
  the model CONVERGES (semantic entropy says "confident/fine") yet the answer DOES depend on the unstated
  axis. This is the executable, non-circular version of "SOTA-blind confident latent-premise ambiguity."
- **Baselines (must miss the danger quadrant):** semantic entropy = `H_seed`; token-logprob; self-consistency
  agreement; requirements-probing (surfacing WITHOUT the pinning test). Show each fails to separate AMB+ from
  AMB− on the low-`H_seed` subset, where `H_ctx-self` succeeds.

## 4. Intervention eval (unchanged in spirit; executable)
- **H-B1′ selective clarification:** LPP triggers a clarification on AMB+ items (needed) but not on AMB−
  (k0/unambiguous). Metric = appropriate-clarification (AMB+) vs over-clarification (AMB−), vs an
  always-clarify baseline and a semantic-entropy-gated baseline (which under-fires on the danger quadrant).
- **H-B2′ resolution:** when the true convention (the deleted axis's gold value) is supplied on clarification,
  the answer moves to I0 (cd_primary→0). Executable gold. Framed as a controlled oracle (simulated user =
  supplying the gold convention), real-user study deferred to future work.

## 5. What this changes vs the 2026-07-23 design doc
- REPLACES §3's "detection ground truth = key_questions match on H1 vs H2" with §1–§3 here (executable
  gold-ambiguity strata; H_ctx-self-tracks-gold as primary; localization + danger-quadrant as the SOTA
  contrast). Everything else (LPP stages, seed/context concept, intervention, AU-Probe contrast, budget,
  provenance) stands.
- Adds a required PRE-STEP: compute gold-ambiguity for all items (read-only executable pass) → the
  AMB+/NON-DISC/AMB− strata. NON-DISC items are reported honestly; regenerating discriminating inputs for
  them is OPTIONAL benchmark curation (owner-gated; must not alter frozen confirmatory items — do it in a
  Study-2 sidecar item set if pursued).

## 6. Governance / next steps (owner review requested)
1. Owner reviews + ratifies this redesigned evaluation (new metrics H-A1′/H-A2′/H-B1′/H-B2′ + the executable
   gold-ambiguity definition). Manager does NOT self-sign.
2. VALIDATION PILOT on the re-stratified items: compute gold-ambiguity strata; re-score the pilot's 9 items
   as AMB+/NON-DISC/AMB−; check `H_ctx-self` AUROC + danger-quadrant mass + localization on AMB+ — a clean
   read now that positives/negatives are defined by execution, not regime labels. Present to owner.
3. Only then freeze the Study-2 prereg (this eval + thresholds pilot-calibrated) and run the confirmatory
   grid ($0). Same anti-leakage (self-gen prompts generic), executable evaluation, cross-family audit.

## 7. Open questions for the owner
- For NON-DISC items (axis untestable on given inputs): report-and-exclude, or invest in regenerating
  discriminating test inputs (a small benchmark-curation effort, Study-2 sidecar)?
- Primary detection metric: threshold-free AUROC of `H_ctx-self` vs gold-ambiguity (recommended, robust), OR
  the thresholded item-level flag (deployable instance) — or both (AUROC primary, flag as the operating
  point)?
- Is the "simulated user supplies the gold convention" oracle acceptable for H-B2′ (controlled, executable),
  with real-user deferred — to avoid the simulated-user overreach the venue dislikes?
