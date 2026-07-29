# Spec — Matched-Triplet Study (information-availability isolation)

> Origin: simulated-CSCW-reviewer critique §三.1 (item-family confound between H1_external
> and H2_derivable). Status: **DESIGN PROPOSAL — not authorized to run.** Authored by the
> writing partner (language role). Requires owner sign-off + a pre-registration commit
> before any model call. This document adds NO results and changes NO existing claim,
> metric, or hypothesis.

## Problem this addresses
The confirmatory design contrasts two item families:
- **H1_external** (40 items): decisive disambiguator lives *outside* the retained prompt.
- **H2_derivable** (14 items): disambiguator is *inside/derivable* from the retained prompt.

Because H1 and H2 are **different item families**, the cross-family contrast carries an
item-family confound, and the clean within-family manipulation (H1 `k=0` retain-clause vs.
`k≥1` delete-clause) actually varies **fully-specified vs. underspecified**, which is
*correlated with but not identical to* **external vs. internally-derivable**. The paper
already discloses this and states its claim as a **boundary condition** (not "the failure
axis is clause location"). This study would let the paper *earn* the stronger,
information-availability reading directly instead of hedging it.

## Objective
For a **single base task**, produce a **matched triplet** that varies **only the
availability of the decisive information**, holding everything else fixed, and measure
convergent delusion (\cd) across the frozen tested roster. Three conditions per base task:

| Condition | Decisive info is… | Expected recovery route |
|-----------|-------------------|-------------------------|
| **T-full** (fully specified) | present in the prompt | trivial; \cd ≈ 0 (positive control) |
| **T-deriv** (internally derivable) | *not stated*, but uniquely recoverable from other retained prompt content | reasoning over retained input |
| **T-ext** (external) | genuinely absent from the prompt (needs outside convention/clarification) | impossible without asking |

The scientific question: does \cd rise **monotonically** T-full → T-deriv → T-ext, and —
critically — is the **T-deriv vs. T-ext gap** non-trivial? A large T-deriv→T-ext gap is the
direct evidence that the operative variable is **where the information lives relative to the
retained boundary**, not merely "specified vs. underspecified".

## Non-goals
- No new metric. **Reuse the frozen \cd definition (Eq. cd) and the frozen dependence
  estimators verbatim** (Law 7: metric defs are frozen). No LLM judge anywhere.
- No change to H1/H2, the regime criterion, the R2 rule, or any decision rule.
- Not a replacement for Study 2; independent of the detector.
- Not merged to `main` as "confirmatory": this is a **new pre-registered exploratory /
  secondary** analysis, labeled as such, per the existing confirmatory/robustness/
  exploratory tiering.

## Matched-triplet construction (the crux)
For each base task, the three conditions MUST share:
1. **Same base task** (same scenario, same requirement being disambiguated).
2. **Same output space** (identical set of enumerated interpretations I_0 … I_m and the
   off-axis I_perp; identical answer format).
3. **Same executable verifier** (one deterministic gold checker per interpretation, reused
   unchanged across all three conditions — this is what makes \cd comparable).
4. **Same natural default** (the locally-reasonable wrong reading the underspecified prompt
   invites must be the *same* I_k in T-deriv and T-ext, so the two differ only in whether
   that reading is *correctable from the prompt*).
5. **Only** the availability of the decisive clue changes across conditions.

**T-deriv derivability must be real and unique.** The deleted convention has to be
*logically recoverable* from other retained content (e.g., a constraint elsewhere in the
spec, a stated invariant, an example that pins the branch) — verified by a deterministic
check that a correct chain of inference exists, **not** by an LLM. If the clue is not
uniquely recoverable, the item is T-ext, not T-deriv.

## Provenance (HARD LAW 6) — distinct families
- **constructor = a family NOT in the tested pool** (e.g., Google/Gemini), authoring the
  base tasks + the three conditions + enumerations. Kills the "shared-prior-with-constructor"
  objection, consistent with the main benchmark.
- **implementer** (≠ constructor, ≠ auditor): writes the triplet-build + gold framework code.
- **auditor** (≠ implementer): hostile cross-family audit of derivability checks,
  verifier mutual-distinguishability, and anti-leakage.
- Tested roster + seeds + operating point: reuse the frozen Study-1 contract.
- Record every family in the PR body.

## Sample size / power (proposal — owner to set)
- Target **≥ 24 base tasks** (→ 72 condition-instances), stratified across the three
  benchmark domains (`code_spec`, `data_analysis`, `policy_qa`) in the same proportion as
  the frozen set, so the triplet result is comparable to H1/H2.
- Pre-commit the **directional prediction** (\cd: T-full < T-deriv < T-ext) and the
  **primary contrast** (paired T-deriv vs. T-ext, item-clustered bootstrap CI excluding
  zero) *before* running. Power target: detect a T-deriv→T-ext gap of ≥ 0.20 at the
  observed inter-agent dependence.

## Analysis (all pre-registered, deterministic)
- Primary: paired within-base-task \cd(T-ext) − \cd(T-deriv), item-clustered bootstrap
  95% CI; report T-full as the ≈0 positive control.
- Secondary: the same dependence estimators (pairwise same-wrong-label agreement, Fleiss κ,
  ICC, \neff, independence-counterfactual Δ) per condition, to show the T-ext excess is
  *correlated* convergence, not mere difficulty.
- Report the pre-registered \iperp-eligible and \iperp-dropped sensitivity variants.

## Risks & controls
- **Leakage / axis-disclosure**: no condition may name the deleted convention or the foils;
  auditor verifies. (Same rule that excluded interpretation-first from the primary grid.)
- **Difficulty confound**: because the verifier and enumerations are identical across the
  triplet, a pure item-difficulty account predicts *equal* \cd across conditions; a
  T-deriv→T-ext gap therefore isolates availability, not difficulty. Still report the
  independence-counterfactual per condition.
- **Derivable ceiling**: strong reasoning models may *solve* T-deriv, compressing the
  T-full→T-deriv gap; this is expected and interpretable (derivable ≈ specified for capable
  models). The load-bearing contrast is T-deriv vs. T-ext.
- **Constructor bias toward "obvious" derivability**: mitigate by having the auditor family
  independently confirm the inference chain is neither trivial (leaks the answer) nor
  impossible.

## Deliverables
1. `bench/triplet/` build code + per-interpretation gold checkers + derivability checks.
2. A frozen pre-registration commit (directional prediction, primary contrast, power target,
   sensitivity variants) **before** the confirmatory run.
3. Cross-family audit report (report-only).
4. A results artifact (`files/matched_triplet_results.md`) with the paired contrast + CIs.
5. A short paragraph draft for §Study 1 robustness (writing partner will draft prose from
   the artifact once numbers exist — no numbers invented here).

## What this does and does NOT license
- **Does**: if the T-deriv→T-ext gap holds, the paper may state the boundary in
  information-availability terms directly, on matched items, retiring the item-family hedge.
- **Does NOT**: it does not, by itself, establish a general causal law beyond the tested
  tasks/models; the claim stays scoped to the tested roster and domains, like the rest of
  the paper.
