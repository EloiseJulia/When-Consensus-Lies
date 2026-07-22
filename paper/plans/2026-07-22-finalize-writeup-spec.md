# Finalize writing spec — Phase B results + strengthening analyses + blind-review revisions

> Manager-authored spec for ONE comprehensive tex-revision pass on `paper/tex/consensus-lies.tex`.
> Integrates: (I) Phase B EXPLORATORY results, (II) two post-hoc strengthening analyses, (III) the
> blind-reviewer (GPT-5.6) A-list writing revisions. **No frozen-science change** — this tempers claims,
> adds honest exploratory/secondary results, and improves precision. Keep the two existing `\todo` lines.
> Numbers below are FINAL (computed 2026-07-22; see `files/strengthening_results.md` and phaseB_report).

## I. Phase B EXPLORATORY results — NEW subsection (Results or Discussion), labeled EXPLORATORY
Frame per `paper/plans/2026-07-22-phaseB-diversified-conditions-design.md` + Amendment 12 (RATIFIED). These
are POST-HOC EXPLORATORY design-intervention conditions — NEVER relabel confirmatory. Report honestly.

Numbers (H1_external, 40 items, 3 seeds; baseline = confirmatory cross-vendor comparison heterogeneous-MAD,
H1 CD = 0.544):
- **Cross-vendor synthesis (C5, "one model merges all answers"):** H1 CD = 0.567, Δ vs baseline =
  **+0.023, 95% CI [−0.033, 0.083]** → synthesis does NOT reduce convergent delusion (CI includes 0,
  point estimate slightly positive); abstention 0%. Supports pre-registered prediction P-B1.
- **Role-diversified evidence workflow (C7: solve / find-missing-info / propose-alternatives /
  check-defaults / integrate-without-treating-agreement-as-correctness):** H1 CD = 0.575, Δ = **+0.031,
  95% CI [−0.052, 0.125]** → generic role diversification does NOT reduce convergent delusion; clarification/
  abstention rose only to 2.5%. Pre-registered prediction P-B2 (that it WOULD help) is **NOT supported**.
- **H2_derivable control:** both conditions CD = 0.000 (interventions do not break the already-resolved
  regime).
- **Honest interpretation (KEY):** Neither changing the aggregation recipe (synthesis) nor imposing generic
  epistemic ROLES over the SAME shared prompt reduces convergent delusion. This is a pre-registered honest
  null that STRENGTHENS the thesis: under a shared information boundary, the failure is driven by the
  boundary, not the aggregation recipe — remedies must diversify the INPUTS/evidence, not merely the vendors
  or the roles. Anti-leakage note: role prompts were generic (no target/foil/gold reference), so this is not
  a "we gave away the answer" artifact. State this explicitly and modestly; do NOT overclaim a solution.
- Add a one-line Methods note: C5/C7 are additive exploratory conditions (Amendment 12, RATIFIED
  2026-07-22), same frozen cd_primary + abstention detector, $0.

## II. Strengthening analyses — integrate into Results/§methods (POST-HOC SECONDARY)
Source: `files/strengthening_results.md`. Label as secondary/post-hoc; pre-stated TOST margins.

### II.a Cross-model label concentration (answers reviewer #6 — R2 is not an N=1 tautology)
On the R2 Anthropic-constructed subset, using single-agent labels from tested models whose family ≠ Anthropic:
- mean per-item cross-model concentration = **0.356, item-level bootstrap 95% CI [0.117, 0.622]**;
- on the items where convergence occurs (k≥1), **five independent models spanning two non-Anthropic families
  (OpenAI, Google) land on the IDENTICAL wrong foil**; **4/12 items have ≥2 distinct non-Anthropic families
  concentrating on the same wrong foil** (per-item concentration up to 1.0 on those items).
- Use this to REPLACE/augment the F5 sentence so "single-agent cd=0.72" is not misread as a within-cell N=1
  quantity: state that INDEPENDENT models from different families converge on the SAME specific foil per item
  (genuine cross-model convergence). Keep R2's pre-registered aggregation metric reported as inconclusive
  (honest); this concentration analysis is the direct cross-model-convergence evidence.

### II.b TOST equivalence (answers reviewer #8 — non-significant ≠ equivalent)
Pre-stated margins: primary ΔCD = 0.15 (Amendment 08 §3 MDE), stricter ΔCD = 0.10.
- **Cross-family ≈ homogeneous (row-35):** Δ = −0.020, equivalent at BOTH ±0.15 (p<0.001) and ±0.10
  (p=0.0007) → the "cross-family convergence is as strong as homogeneous" claim is now backed by a formal
  equivalence test.
- **Reasoning ≈ weak (capability invariance):** Δ = +0.017, equivalent at BOTH ±0.15 and ±0.10 (p=0.006).
- **Weak vs heterogeneous:** equivalent at ±0.15 (p=0.014) but NOT at ±0.10 (p=0.145) — REPORT THIS CAVEAT
  honestly (do not claim full equivalence there).
- Wherever the paper currently says "capability-invariant", "fail identically", or "cross-family ≈
  homogeneous", ATTACH the TOST result and the pre-stated margin; where equivalence is not established at the
  stricter bound, say so.

## III. Blind-review A-list writing revisions (precision/honesty; no science change)
1. **#2 "differ only" overclaim:** H1 (40) and H2 (14) are NOT paired variants of identical tasks. Reword the
   "regimes differ only in disambiguator location" claims to be accurate; state the CAUSAL location claim
   rests on the WITHIN-ITEM k0-vs-k≥1 control (R1a, strongly supported: Δ CI[0.733,0.899]), while H1-vs-H2 is
   a broader regime contrast across different item families. Add paired-variant construction as future work.
2. **#9 "every tier resolves it":** replace with the precise claim — H2 CD = 0 means no convergence on a
   shared wrong foil; report target-accuracy / parseability / I_perp separately (H2 has up to 15.2% I_perp).
   Do not equate CD=0 with "fully resolved."
3. **#8 invariance wording:** soften "capability-invariant"/"identical"/"≈" to "no detectable difference"
   and attach the II.b TOST equivalence result + margin (see above); foreground limited power for the H2
   interaction (14 items).
4. **#10 "confidently wrong"/"silent":** the abstention detector is rule-based and pending human validation
   (\todo stays). Temper: say agents "rarely issued explicit clarification requests" per the rule-based
   detector; qualify "confidently" (we log verbalized/logit confidence but do not over-interpret it pending
   validation). Do not delete the phenomenon, just scope it.
5. **#11 design recs "Directly supported":** recast the design implications as design HYPOTHESES/implications
   (not "directly supported"), since no UI/human study was run; and note Phase B (§I) provides COMPUTATIONAL
   evidence that generic role/synthesis interventions are insufficient. Resolve the dangling
   "interpretation-diverse" mention (either report it as a secondary method excluded from A08 primary per
   A11, or remove the forward reference).
6. **#6 R2 wording:** apply II.a; describe R2 as suggestive (pre-registered metric inconclusive) + the
   cross-model concentration as the direct evidence.
7. **#4 dependence-estimator specification:** add a short Methods paragraph specifying the ICC model
   (one-way random-effects on the wrong-answer indicator per item-cell), the observation unit, the variance
   components, and the n_eff = n/(1+(n−1)ρ̄) exchangeability assumption; acknowledge heterogeneous-agent
   exchangeability as a caveat; cite the analysis code. Do NOT change any number.
8. **#5 independence-counterfactual caveat:** add one honest sentence that the counterfactual resamples from
   each agent's item-marginal accuracy, so shared item difficulty is an alternative account; note the
   convergent evidence from ICC + pairwise agreement + n_eff.
9. **#3 default-check disclosure:** disclose that items were screened by a default check and note this is a
   construct-validity limitation (inclusion partly conditioned on the default behavior); note provenance
   separation (constructor ≠ tested) and the R2 cross-constructor control mitigate it; unfiltered-sample =
   future work.
10. **#1 construct framing:** add a sentence distinguishing that the model's default may be a locally
    reasonable inference from the underspecified prompt (not "irrationality"); the harm is the SILENT,
    correlated convergence on one reading without flagging the ambiguity. Keep "convergent delusion"/"fake
    redundancy" as named phenomena but ensure they are defined in these terms.
11. **#12 landscape audit "nine vs six":** reconcile — the text says nine platforms but the table lists six.
    Either add the remaining verified platforms (Poe, LMArena/TypingMind/Google AI Studio per
    `paper/research/2026-07-22-multimodel-interface-landscape-audit.md`) as rows, OR change the wording to
    "we surveyed nine, and tabulate six representative ones." Add a one-paragraph audit method note (search /
    inclusion criteria / coding dimensions / snapshot date 2026-07-22 / public-materials-only) and keep the
    conservative language.
12. **#14 novelty:** add a sentence contrasting our contribution vs Kim et al. (correlated LLM errors) and
    Yang et al. (underspecification) at the construct/manipulation/metric level — our novelty is the
    interface-centered framing + a controlled executable-gold regime manipulation, not the general
    observation that consensus can be wrong.
13. **#15 ethics/environment:** replace the "$0 ⇒ negligible" inference with the actual request/token volume
    (report the run scale, e.g. thousands of model calls) and note provider terms; do not infer environmental
    impact from marginal billing.
14. **Presentation:** (a) reframe "H2 interaction uncomputable (expected null)" — a failed model fit is not
    evidence for a null; say the crossed random-effects model did not converge (an estimation limitation),
    consistent with the small H2 sample. (b) Soften figure-caption causal claims to match the design.
    (c) Soften "legacy-weak" → "non-frontier"/"weaker". (d) Update the stale `references.bib` header comment
    "Verify all entries" since entries were verified (DECISION-LOG row 80) — optional.

## IV. Build + gate
- Build MiKTeX (full path); pdflatex×1 → bibtex → pdflatex×2; 0 errors, 0 undefined cites; report pages.
- No frozen number changed except the NEW exploratory/secondary results added (Phase B + strengthening);
  confirmatory F1–F5 values unchanged.
- Implementer = Claude; hostile audit = GPT (cross-family); merge only at 0 BLOCKER/MAJOR; DECISION-LOG rows.
