# Study 2 PRE-REGISTRATION (FROZEN) — Latent-Premise Sensitivity detector & seed/context uncertainty decomposition

> FROZEN 2026-07-23 before the confirmatory run (Law 7). Locks hypotheses, metric definitions, the item set,
> seeds, baselines, and the operating point, as calibrated by the validation pilot (AUROC H_ctx-self=0.86 vs
> semantic-entropy baseline 0.55; precision 1.00; k0 FP 0; danger-quadrant 21/33). Design detail:
> `paper/plans/2026-07-23-study2-latent-premise-sensitivity-design.md` + `...study2-eval-redesign.md`.
> Validated core merged to `main` (impl=Claude, cross-family audit=GPT: anti-leakage clean, non-circular,
> pilot numbers independently reproduced, 0 BLOCKER/MAJOR).
>
> **Authorization provenance (honest — NOT AI-self-signed):** the owner @EloiseJulia gave a CONDITIONAL
> pre-authorization on 2026-07-23 — *"如果信号强值得做你就开跑全量（我现在授权你，给你签字），到时候就不用问我了。如果信号弱就如实汇报，不跑全量，等着我进一步分析"* — delegating the go/no-go to the Manager against a
> pre-committed decision rule. The pilot met the strong-signal bar, so the Manager freezes this prereg and
> launches the confirmatory run under that DELEGATED authority. This is NOT a claim that the owner personally
> ratified each metric line-by-line; any change to THIS frozen prereg after launch would still require the
> owner's personal ratification.

## 1. Hypotheses (FROZEN)
- **H-A1′ (PRIMARY — detection):** the black-box detector signal `H_ctx-self` classifies executable
  gold-ambiguity (AMB+ vs AMB−) with AUROC substantially above chance AND substantially above the
  semantic-entropy baseline `H_seed`. Pre-committed direction: AUROC(H_ctx-self) ≥ 0.75 and
  AUROC(H_ctx-self) − AUROC(H_seed) ≥ 0.15, with item-level bootstrap CIs.
- **H-A1b (danger quadrant — the SOTA-blind claim):** a substantial fraction of AMB+ items are
  low-`H_seed` ∧ high-`H_ctx-self` (model confidently convergent yet answer depends on an unstated axis) —
  the zone where `H_seed`/semantic entropy is blind. Pre-committed: ≥ 40% of AMB+ items in that quadrant.
- **H-A2′ (SECONDARY — localization):** the model's argmax-`H_ctx-self` dimension matches the true deleted
  axis (`key_questions`) above chance. Reported honestly as secondary (pilot localization ≈ 0.33 — a known
  limitation and a recall lever, not a headline).
- **H-B1′ (intervention — selective clarification):** LPP triggers clarification on AMB+ (needed) but not on
  AMB− (k0/unambiguous): appropriate-clarification(AMB+) − over-clarification(AMB−) > 0, and higher than an
  always-clarify baseline's specificity and a semantic-entropy-gated baseline's AMB+ coverage.
- **H-B2′ (intervention — resolution):** when the true convention (the deleted axis's gold value) is supplied
  on clarification (controlled oracle), the answer moves to I0 (cd_primary → 0), by executable gold.

## 2. Metric definitions (FROZEN)
- `H_seed` = semantic entropy (bits) over the FROZEN labeler's enumerated-interpretation labels across k
  resamples of the SAME prompt (temperature 0.7). k = 5 (SECONDARY sensitivity: k = 10).
- `H_ctx-self` = entropy (bits) over mutual-answer-equivalence CLUSTERS of the model's self-generated pinned
  answers, clustered by the FROZEN executable-harness pairwise equality (`_runner_compare`, FLOAT_TOL=1e-9,
  bool type-distinct, int exact, union-find components); unparseable/unrunnable answers excluded; <2 parseable
  ⇒ 0. Model-self-generated dimensions/values ONLY (anti-leakage: no gold/target/foil/key_questions in any
  prompt).
- **gold-ambiguity (executable, detector-independent):** an item is AMB+ iff ≥2 of its OWN enumerated
  interpretations produce different executable results on its test inputs; NON-DISC iff the axis exists but
  interpretations coincide; AMB− iff no deleted axis (k0) or interpretations coincide. Non-circular:
  independent pin-set (benchmark interpretations) from the detector's (model self-pins).
- **PRIMARY analysis = AUROC** of `H_ctx-self` vs gold-ambiguity (threshold-free). **Operating point** =
  item-flag `is_flagged = (H_ctx-self > τ) ∧ (H_seed ≤ τ_s)` with **τ = 0.0** and **τ_s = 0.5 bits** (FROZEN;
  τ_s = the low-`H_seed` "convergent" cutoff used to define the danger quadrant). Report precision/recall at
  the operating point + the k0 false-positive rate.
- Method version `lps-2026-07-23-v5-pairwise-tol` (run-fingerprint enforced).

## 3. Item set, models, seeds (FROZEN)
- **Items:** the SAME frozen benchmark, all 54 (33 AMB+ / 0 NON-DISC / 21 AMB− by executable gold-ambiguity;
  NON-DISC=0 empirically). k0 controls are AMB−. No item edits.
- **Models (confirmatory roster):** the frozen multi-family roster — reasoning tier (openai gpt-5.6-sol,
  anthropic claude-opus-4.8, google gemini-3.1-pro) + weak tier (gpt-4o-mini, claude-haiku-4.5,
  gemini-3.5-flash). Per-model detection + pooled.
- **Seeds:** ≥ 3 collision-free.
- **Baselines (must be shown to lose in the danger quadrant):** `H_seed` (semantic entropy), token-logprob /
  max-token-entropy, self-consistency agreement, requirements-probing (assumption-surfacing WITHOUT the
  pinning test). Same AUROC-vs-gold-ambiguity comparison.
- **Intervention:** H-B1′ selective-clarification vs always-clarify + semantic-entropy-gated; H-B2′
  resolution via the gold-convention oracle (real-user study = future work; framed as a controlled oracle to
  avoid simulated-user overreach).
- **AU-Probe contrast (SECONDARY, compute-caveated):** a small open white-box model on CPU; report a reduced
  pre-specified subset if full is too slow; positions LPP as the black-box, cross-vendor-deployable method.

## 4. What stays fixed / honesty
No confirmatory-study frozen file is touched; the frozen labeler + executable harness are reused read-only;
the detector prompts are generic (anti-leakage). Honest reporting of all nulls/limitations (localization
weak; FNs = surfacing/discrimination coverage; H_ctx-self~H_ctx-gold magnitude corr low because the oracle
magnitude is near-constant — the BINARY AUROC is the meaningful signal). Reported EXPLORATORY→confirmatory
per this prereg; metric defs never change post-freeze.

## 5. Decision rule already met by the pilot (for the record)
Pre-committed GO required: clean AMB+/AMB− separation (met: AUROC 0.86), baseline fails where we succeed
(met: H_seed 0.55 ≈ chance), k0 specificity (met: FP 0), danger-quadrant mass (met: 21/33). Localization
(secondary) weak — disclosed. → GO to the confirmatory run under the owner's delegated pre-authorization.
