# Study 2 design + pre-registration (DRAFT) — Latent-Premise Sensitivity & the seed/context uncertainty decomposition

> Owner GO 2026-07-23 (brainstorm). A NEW study extending "When Consensus Lies" with a CONSTRUCTIVE
> detector + intervention for the silent convergent-delusion failure. This is a SEPARATE pre-registration
> from the frozen confirmatory study (`c0a0393`); it defines NEW metrics/hypotheses and therefore requires
> owner @EloiseJulia PERSONAL ratification before the confirmatory run (Manager must NOT self-sign). Plan:
> design → implement method+baselines ($0, reversible) → SMALL PILOT to verify the signal exists → owner
> ratifies this prereg + reviews pilot → full run. Primary metrics use EXECUTABLE GOLD wherever possible.

## 0. Motivation & the precise SOTA gap (from the 2026-07-23 SOTA scan)
Our confirmatory study showed: under a shared, underspecified prompt, independent models CONFIDENTLY and
SILENTLY converge on the same wrong interpretation (fake redundancy; abstention ≈ 0.03%). The blind-review
+ Phase B showed blunt interventions (synthesis, generic role-diversification) do NOT fix it.

SOTA uncertainty quantification is built to catch the OPPOSITE failure — arbitrary/confabulatory errors that
show up as HIGH answer dispersion:
- **Semantic entropy** (Farquhar/Kuhn/Gal, Nature 2024): samples answers, clusters by meaning, high entropy
  = uncertain. Authors' OWN stated limitation: *systematic confident errors are NOT flagged*, and it *cannot
  distinguish unanswerable from ambiguous*. → It is BLIND to convergent delusion (low semantic entropy).
- **Token logprob / self-consistency**: same failure — confident convergence ⇒ looks certain.
- **AU-Probe / "Mind the Ambiguity" (arXiv 2601.17284)**: detects ambiguity from INTERNAL ACTIVATIONS →
  WHITE-BOX only; unavailable for the black-box, multi-vendor interfaces our paper is about.
- **Requirements/underspecification probing** (Yang et al. 2025, our cite `yang2025underspecification`):
  inference-only clarifying-question generation, but not tied to a confidence/convergence signal and not
  validated against a gold ambiguous dimension.
- **AbstentionBench** (Meta 2024/25): SOTA models abstain poorly; reasoning-tuning REDUCES abstention →
  corroborates our silent-failure finding (related work, not a method we adopt).

**The hole:** no existing method reliably flags "the answer confidently rests on an UNSTATED premise the user
never fixed," in a BLACK-BOX setting. That is exactly our failure mode.

## 1. Core idea — decompose uncertainty into two axes
The model is NOT uncertain about the ambiguous span (e.g. "fiscal year"); it confidently defaults. The right
signal is not the model's confidence on the token, but the ANSWER's SENSITIVITY to the unstated dimension.
Define, per item (and per model):
- **seed-entropy** `H_seed` = semantic entropy of the answer distribution under RESAMPLING the SAME prompt
  (temperature>0, k samples). This is the SOTA signal. Computed over our ENUMERATED interpretation labels
  via the FROZEN labeler (executable gold), so "semantic clustering" is exact, not embedding-approximate.
- **context-entropy** `H_ctx` = the answer dispersion under COUNTERFACTUAL PINNING of a candidate unstated
  dimension (see §2). High `H_ctx` ⇒ the answer depends on a dimension the prompt did not fix.

**2D diagnostic (the headline concept):**
| | `H_ctx` low | `H_ctx` high |
|---|---|---|
| `H_seed` low | genuinely determined (safe) | **DANGER: confident latent-premise ambiguity (SOTA-blind)** |
| `H_seed` high | rare | openly uncertain (SOTA catches) |

**Pre-registered H-A1 (diagnostic, executable-gold):** On H1_external items, `H_seed` is LOW and
`H_ctx` (for the true deleted axis) is HIGH — i.e. items land in the DANGER quadrant. On H2_derivable items,
BOTH are low (the disambiguator is in-prompt; pinning it does not move the answer). Pre-committed contrast:
mean `H_ctx(H1) − H_ctx(H2) > 0` with item-level bootstrap CI excluding 0, while `H_seed(H1) ≈ H_seed(H2)`
both low. This is falsifiable and uses only the frozen labeler + gold axes.

## 2. The detector — Latent-Premise Probing (LPP), black-box, inference-only, no GPU
Three inference-only stages (model self-generates everything; NO gold/target/foil in any prompt — same
anti-leakage discipline as Phase B / A11):
1. **Assumption surfacing (self-generated):** ask the model to list the decision-relevant assumptions its
   answer depends on that are NOT fixed by the prompt, each with 2–3 alternative values it could take →
   candidate dimensions `D = {d_i}` with values `{v_ij}`. (Generic prompt; no answer key.)
2. **Counterfactual pinning:** for each `d_i`, form pinned prompts `P ⊕ "assume d_i = v_ij"` and collect
   answers `A(P, d_i=v_ij)`. `H_ctx(d_i)` = semantic entropy (frozen labeler) over `{A(P, d_i=v_ij)}_j`.
   The flagged ambiguous dimension = `argmax_i H_ctx(d_i)`; item flagged AMBIGUOUS iff
   `max_i H_ctx(d_i) ≥ τ` AND `H_seed ≤ τ_s` (danger quadrant); τ/τ_s pre-registered (pilot-calibrated, then
   frozen — §6).
3. **Route:** if flagged, emit a TARGETED clarification for the top dimension instead of committing an answer.

## 3. Detection evaluation (uses our EXISTING gold — no new labels)
Ground truth ambiguous axis per item = the benchmark's `key_questions` (the deleted axes; k0 controls have
NONE). Pre-registered detection metrics:
- **H-A2 (localization):** the LPP-flagged dimension (`argmax_i H_ctx`) matches the true deleted axis at
  precision/recall well above the baselines. On k0 controls, LPP should NOT flag (specificity).
- **Baselines (must be shown to fail in the danger quadrant):** (a) semantic entropy on seed resampling —
  gives only a scalar, cannot localize a dimension and is LOW on H1; (b) token-logprob / max-entropy token —
  low on the confident default; (c) self-consistency agreement — high (fake redundancy); (d) requirements-
  probing (Yang-style assumption listing WITHOUT the counterfactual pinning test) — show pinning adds
  precision by filtering "assumptions" that don't actually move the answer.
- Report per-item and pooled precision/recall/F1 with item-level bootstrap CIs; report on H1 vs H2 vs k0.

## 4. Intervention evaluation (the constructive third act) — EXECUTABLE GOLD
- **H-B1 (selective clarification):** LPP triggers clarification on H1_external (needed) but NOT on
  H2_derivable or k0 (not needed) — i.e. HIGH appropriate-clarification on H1 and LOW over-clarification on
  H2/k0. Contrast vs an "always-clarify" baseline (which over-asks) and a "semantic-entropy-gated" baseline
  (which under-asks on convergent delusion because H_seed is low).
- **H-B2 (resolution given clarification):** when the pinned/true convention is supplied (simulated user
  provides the deleted axis value = the gold), the model's answer moves to I0 (cd_primary → 0). Executable
  gold. This shows the failure is RESOLVABLE once the specific unstated dimension is surfaced — unlike Phase
  B's blunt interventions.
- Baselines for B: always-clarify; never-clarify (= confirmatory); semantic-entropy-gated clarify;
  self-consistency-gated clarify. Metric of merit = a cost-sensitive score trading appropriate-clarification
  (H1) against over-clarification (H2/k0), plus post-clarification CD.

## 5. AU-Probe white-box CONTRAST (owner approved; compute-limited)
Reproduce AU-Probe (activation probe for ambiguity) on a SMALL OPEN model that runs on CPU (no GPU): e.g.
Qwen2.5-1.5B / Llama-3.2-1B/3B. Train the probe on our items' activations (ambiguous vs k0), evaluate
localization/detection, and CONTRAST with black-box LPP on the SAME items. Expected framing: AU-Probe may
match or beat LPP WHERE white-box access exists, but is INAPPLICABLE to the GPT/Claude/Gemini multi-vendor
interface setting — positioning LPP as the black-box, cross-vendor-deployable method. **Compute caveat:** if
CPU inference on the open model is too slow for the full item set, run a reduced but pre-specified subset;
report honestly. This contrast is SECONDARY (supports positioning), not the headline.

## 6. Pre-registration discipline
- FREEZE before the confirmatory run: H-A1, H-A2, H-B1, H-B2; the `H_seed`/`H_ctx` definitions; the semantic
  clustering = FROZEN labeler over enumerated interpretations; the thresholds τ/τ_s (pilot-calibrated then
  locked); the item set (the SAME frozen benchmark: 40 H1_external + 14 H2_derivable + k0 controls); ≥3
  seeds; the baseline set; the detection/intervention metrics. NO metric change after freeze.
- **PILOT first** (small, exploratory, explicitly not confirmatory): a few items × 1–2 models to verify the
  DANGER-quadrant signal exists (H1: low `H_seed`, high `H_ctx`; H2: both low) and to calibrate τ/τ_s.
  Report the pilot to the owner WITH this prereg for personal ratification. Only then run the full grid.
- Provenance separation preserved: model-self-generated prompts are GENERIC (no gold); labeling is
  executable gold; implementation (Claude) is cross-family audited (GPT); no fabricated data.

## 7. Budget & feasibility (owner is caution-first)
$0 via the local ghc-api proxy; inference-only (no fine-tuning, no GPU for the black-box method). Per item per
model ≈ assumption-surfacing (1) + pinning (~2–3 dims × 2–3 values ≈ 6) + seed-resample (k≈5–10) ≈ ~15 calls;
× 3 families × ~54 items × 3 seeds ≈ low thousands of calls, $0, sequential + resumable + cached. AU-Probe
open-model CPU pass is the only compute-heavy piece (descope-able).

## 8. Naming / framing (to decide with owner)
Working names: the concept = **seed/context uncertainty decomposition**; the detector = **Latent-Premise
Probing (LPP)**; the danger quadrant = **"confident latent-premise ambiguity."** Paper positioning: (A)
diagnostic (the 2D decomposition exposing the SOTA blind spot) as the concept anchor + (B) LPP detector/
intervention as the constructive method — BOTH, per owner (2026-07-23).

## 9. Open items to confirm with owner (non-blocking for design; decide before freeze)
- τ/τ_s calibration source (pilot) and whether to report a threshold-free version (AUROC of `H_ctx` for
  localizing the deleted axis) as the primary, with the thresholded detector as the deployable instance.
- Exact k for seed-entropy (5 vs 10) and number of pinning values per dimension (cost vs resolution).
- Whether the intervention's "simulated user" (supplying the gold convention on clarification) is acceptable
  as a controlled proxy (executable-gold), with a real-user study deferred to future work (avoids the
  simulated-user overreach the venue dislikes — frame as a controlled oracle, not a human-behavior claim).
