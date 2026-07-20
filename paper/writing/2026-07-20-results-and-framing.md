# Results & Framing — confirmatory run (Manager writing-prep for owner's Phase-7)

> Manager-prepared draft of the RESULTS + the single strongest claim + honest nulls + figure list, from
> the FROZEN pre-registration + confirmatory run (DECISION-LOG rows 60–74). Numbers from
> `files/phase6_confirmatory_report.md` (confirmatory) + row 72 (R2). The owner writes the paper; this is
> the scientific scaffold. Methods come from the prereg + amendments; Deviations from
> `2026-07-18-deviations-from-preregistration.md` (update with A11).

## 0. The single strongest claim (headline)
Under underspecified prompts whose disambiguator lies OUTSIDE the retained prompt (**H1_external**),
independent LLM agents — **across capability tiers AND model families** — **silently** converge on the SAME
wrong interpretation, and a k-agent ensemble **collapses to ≈1 effective agent** (fake redundancy, ρ→1).
When the same disambiguator is IN the prompt (**H2_derivable**), every tier — including legacy-weak models —
resolves it (CD=0). **The failure axis is the disambiguator's LOCATION, not model capability**; redundant
aggregation does not rescue it; a second, cross-family–constructed benchmark rules out the
"shared-prior-with-the-constructor" artifact. Framing per R5: a *controlled causal characterization of a
correlated-failure regime*, not a first demonstration that consensus can be wrong.

## 1. CONFIRMED results (the three pillars + supports)
Confirmatory run: 54 items (H1=40 / H2=14), frontier roster (OpenAI/Anthropic/Google), 3 seeds, A08 PRIMARY
methods {single, SC-k5, homogeneous-MAD, heterogeneous-MAD}, 16,461 agent rows, $0 on the local proxy.

**① Two-regime main effect (headline) — STRONG.**
- H1_external cd_primary = **0.532** (uniform across ALL classes incl. frontier reasoners); among PARSEABLE
  answers (drop-I_perp) = **0.596**.
- H2_derivable cd_primary = **0.000** (ALL classes incl. weak; drop-I_perp = 0.000 — no parseable agent
  converges on a wrong enumerated label on H2).
- Δ = **0.532** (0.596 parseable), consistent across all three A04 CD variants.
- Per-class H1 CD ≈ 0.52–0.54 (homogeneous/heterogeneous/reasoning/weak all similar) → capability-invariant.

**② ρ→1 fake redundancy (mechanism) — CONFIRMED (P1, Amendment 09).** On H1_external:
- pairwise wrong-agreement = **0.982**, Fleiss κ = 0.971, ICC = **0.894**, **effective ensemble size n_eff =
  1.10** (a k-agent ensemble ≈ 1 independent agent).
- Independence-calibrated counterfactual Δ = **+0.245**, 95% CI **[0.234, 0.257]** (excludes 0) — the observed
  convergence significantly EXCEEDS what independent agents at the same marginal accuracy would produce.
- This is the sharpest evidence (addresses R5 risk #3: cd_primary alone has a high random baseline on binary
  items; the dependence metrics carry the excess-convergence claim).

**③ Silent failure (the "silent" in the title) — CONFIRMED (P2, Amendment 09).** H1_external abstention /
clarification-request rate ≈ **0.02%** while CD = 53% — agents are CONFIDENTLY wrong, essentially never
flag the missing information. (Rule-based detector; human-validation of the sample is the pre-registered
next step.)

**④ H1b (CD rises with ambiguity level k) — SUPPORTED.** k-coefficient = **0.314**, 95% CI [0.177, 0.452];
robust across all three CD variants. Phase diagram: k0→CD≈0, k1→CD≈0.89–0.93, k2→CD≈0.62–0.72, k3 mixed
(high I_perp).

**⑤ R1a (k=0 hard control) — STRONGLY SUPPORTED.** CD on fully-specified k=0 controls = **0.000**; on k≥1
underspecified items = **0.818**; Δ 95% CI **[0.733, 0.899]** (drop-I_perp 0.979, CI [0.961, 0.993]). The
SAME pipeline/labeler yields ≈0 when the prompt is complete and high when one clause is deleted — rules out
a labeler/foil-count artifact. This is the cleanest robustness result.

**⑥ R2 (cross-family construction control) — confound REBUTTED (separate Anthropic-constructed subset,
Amendment 10/11).** Non-Anthropic (OpenAI/Google) models converge on claude-opus-constructed H1 foils at
single-agent cd_primary = **0.72** (0.87 on the 5 construct-valid items) → the "convergence is just a shared
prior WITH THE CONSTRUCTOR" artifact is directly rebutted. (The pre-registered R2 aggregation-amplification
metric is INCONCLUSIVE; per A11 the confound is carried by the single-agent cross-family persistence, as
A07 handled R1.)

## 2. HONEST nulls / reframings (report transparently — a feature, not a bug)
- **H1a (redundant aggregation AMPLIFIES CD): INCONCLUSIVE** (agg−single Δ≈0, CI crosses 0; divergent across
  variants). Reading: redundant aggregation does NOT rescue models (CD stays ~0.53), consistent with the
  thesis; the "fake redundancy" claim is carried by n_eff=1.10 / the independence counterfactual, not by an
  aggregation-amplifies effect.
- **R1b (uniform-over-interpretations null): cd_primary INCONCLUSIVE** (Δ=0.006; the uniform baseline is
  ~0.81 because most items are binary/k=1 where random guessing already yields high apparent modal-wrong) —
  **drop-I_perp SUPPORTED** (Δ=0.167, CI [0.090, 0.249]). R1 robustness rests on R1a + the independence
  counterfactual (both strong), not R1b.
- **Row-35 (heterogeneous cross-family > homogeneous): NOT CONFIRMED** (Δ=−0.003, CI [−0.078, +0.058]).
  REFRAME: cross-family CD is AS HIGH as homogeneous CD → the shared prior operates ACROSS families (a
  cross-family pool is not more diverse in effect than one model sampled repeatedly). This SUPPORTS the
  core thesis (convergent delusion is genuinely cross-family, not single-model determinism) rather than
  refuting it — but the specific "hetero > homo" ordering did not hold.
- **H2 reasoner×capability INTERACTION: UNCOMPUTABLE / expected-null.** The §8 crossed-RE 4-way model does
  not converge (structural empty cells + high-dim; decision-log row 68); pre-registered as SECONDARY and
  (rows 51–52) empirically expected null. Reported transparently; NOT backfilled. The regime MAIN effect
  (well-powered) carries the claim.

## 3. Anomaly (transparent, pre-registered treatment)
17% of cells have I_perp > 0.20 (the pre-registered investigate gate). Two code_spec items
(`code_getitems_001_k1`, `code_roundcurr_001_k1`) have I_perp≈1.0 for capable models: their foil set is
incomplete, so a capable model lands on an UNENUMERATED interpretation → I_perp (ineligible for cd_primary),
which DEFLATES cd_primary. The pre-registered A04 treatment handles this: report cd_primary AND
drop-I_perp (H1 = 0.596 among parseable) AND the I_perp rate (0.115 on H1). NO post-hoc benchmark change
(pre-registration integrity). The two-regime demarcation holds on every variant.

## 4. Figures (data ready in figure_data.all_figure_data + files/phase6_confirmatory_report.md)
- F1 Phase diagram: CD vs (regime × k) — the two-regime + monotone-in-k structure.
- F2 CD-by-regime × model_class (bars): capability-invariance of H1; H2=0 for all.
- F3 Dependence: n_eff / ICC / pairwise-agreement H1 vs H2 (the ρ→1 collapse).
- F4 Abstention rate by regime (silent failure): ≈0% on H1 at CD=53%.
- F5 (sensitivity) SC k=5 vs k=10 n_eff (pending SC-k10 run) — robustness of the collapse at higher k.
- F6 (R2) cross-family single-agent CD (non-Anthropic on Anthropic-constructed) vs same-family reference.

## 5. Methods + Deviations (pointers)
- Methods: frozen prereg `2026-07-15-prereg.md` (`c0a0393`) + SIGNED amendments A01–A11 (roster A06,
  I_perp A04, R1 A07, final-N A08, secondaries A09, R2 A10, R2-interpretation/scope A11).
- Deviations section: `2026-07-18-deviations-from-preregistration.md` (UPDATE to add A10/A11 + the
  confirmatory H1a/R1b/row-35 honest-null outcomes + the I_perp-item note).
- Provenance (Law 6): every code artifact = Claude-implemented, GPT-audited cross-family; labels =
  deterministic executable gold; every design change owner-ratified (no AI self-signed frozen contract).

## 6. What still blocks the very strongest claim (for the discussion / limitations)
- H2 interaction uncomputable (report as expected-null; lead with the regime main effect).
- R1b weak on cd_primary (binary-item baseline) — lean on R1a + independence counterfactual.
- I_perp on 2 items (report drop-I_perp sensitivity).
- P2 abstention detector is rule-based → the pre-registered HUMAN validation of the sample should be done
  before the abstention number is finalized in the paper.
- SC-k10 sensitivity (in progress) to show n_eff→1 persists at higher k.
