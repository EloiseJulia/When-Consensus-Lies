# Study-2 WRITE-UP SPEC (detection section) — for the Claude writing sub-agent

> Manager-authored spec (orchestrator-only). Owner asked (2026-07-23) to update the paper IN PARALLEL with the
> Phase 2b intervention iteration. Scope: add the **Study 2 DETECTION** arc (CONFIRMED, frozen — DECISION-LOG
> row 88) to `paper/tex/consensus-lies.tex`. Intervention (Phase 2b, H-B1′/H-B2′) and AU-Probe (Phase 2c) are
> STILL RUNNING → write them as clearly-marked `\todo{forthcoming}` placeholders, do NOT invent their results.
> This is ADDITIVE writing; do NOT change any Study-1 number, frozen content, or hypothesis.

## 0. Provenance & governance
- You are the Claude-family writer. A GPT-family auditor (`gpt-5.6-sol`) will cross-family audit for NUMBER
  FIDELITY + OVERCLAIM before merge (Law 6). Record your family in the PR body.
- Work ONLY in your assigned worktree/branch. Never edit the main checkout. Never edit any FROZEN file
  (`paper/preregistration/*FROZEN*`) or any confirmatory artifact. You MAY edit `paper/tex/consensus-lies.tex`
  and `paper/tex/references.bib` (add verified entries only).
- **NO FABRICATION (inviolable):** every number must come verbatim from `files/study2_stage2_results.md` or
  the frozen prereg. Every NEW citation must be a REAL, verifiable paper with correct metadata — if you cannot
  verify it, mark `\todo{verify cite}` rather than inventing DOI/venue. Do NOT write any Phase 2b/2c result.

## 1. Sources of truth (read these; quote numbers exactly)
- `files/study2_stage2_results.md` — the CONFIRMED detection panel (pooled + per-model). Authoritative numbers.
- `paper/preregistration/2026-07-23-study2-prereg-FROZEN.md` — frozen hypotheses H-A1′/A1b/A2′, the
  `H_seed`/`H_ctx-self`/gold-ambiguity definitions, operating point (τ=0, τ_s=0.5), 54 items, ≥3 seeds,
  baseline set, authorization provenance (owner conditional pre-authorization — quote honestly, NOT
  self-signed).
- `paper/plans/2026-07-23-study2-latent-premise-sensitivity-design.md` + `...study2-eval-redesign.md` — the
  concept + non-circular executable-gold-ambiguity rationale (for the method prose).
- `paper/decisions/DECISION-LOG.md` rows 87–89 — provenance/authorization context.

## 2. Key numbers (must appear EXACTLY; cross-check against the results file)
- Pooled **AUROC(H_ctx-self) = 0.895** [0.815, 0.966] vs semantic-entropy **AUROC(H_seed) = 0.581**
  [0.484, 0.675]; **ΔAUROC = 0.314** (pre-committed ≥ 0.15).
- **Danger-quadrant mass = 0.758 (25/33)** (pre-committed ≥ 0.40).
- Operating point (τ=0, τ_s=0.5): pooled **precision 0.926, recall 0.758**, k0 FP-rate 0.095.
- All 6 frontier models (OpenAI/Anthropic/Google × reasoning/weak) individually: H_ctx-self **0.86–0.89** vs
  semantic entropy **0.55–0.61** (reproduce the per-model table faithfully).
- Gold-ambiguity strata: **33 AMB+ / 21 AMB− / 0 NON-DISC** of 54.
- **HONEST caveats (MANDATORY — do not bury):** requirements-probing baseline is strong (pooled **0.810**) →
  the counterfactual-pinning increment is real but MODEST (**+0.085**); **localization is WEAK (0.36**,
  secondary); token-logprob baseline is **N/A** on non-OpenAI slugs.

## 3. Framing (the anti-overclaim contract — my Lead-Researcher guidance)
- **Headline contribution:** *explicitly surfacing latent premises* (in a black-box, cross-vendor,
  inference-only setting) exposes the exact blind spot semantic entropy documents about itself (systematic
  confident errors + can't distinguish unanswerable from ambiguous). Counterfactual pinning is a REFINEMENT
  that adds precision, NOT the whole story.
- Study 1 = the problem (silent convergent delusion / fake redundancy). Study 2 = the constructive black-box
  detector for it. Make the two-study arc explicit and tight.
- Concept: the **seed/context uncertainty decomposition** — `H_seed` (semantic entropy over resamples of the
  SAME prompt = the SOTA signal) vs `H_ctx-self` (answer dispersion under counterfactual PINNING of a
  self-surfaced unstated dimension). The **danger quadrant** = low `H_seed` ∧ high `H_ctx-self` = "confident
  latent-premise ambiguity" = SOTA-blind.
- Method (LPP): (1) model self-surfaces decision-relevant unstated assumptions (generic prompt, NO gold —
  state the anti-leakage discipline); (2) counterfactual-pin each with the model's OWN values, cluster the
  pinned answers by MUTUAL executable equivalence (frozen harness `_compare`, union-find), `H_ctx-self` =
  entropy over clusters; (3) flag if `H_ctx-self > τ ∧ H_seed ≤ τ_s`.
- **Non-circularity** (make this explicit — reviewers will probe it): the gold-ambiguity label clusters the
  BENCHMARK's enumerated interpretations (executable), while the detector clusters the MODEL's self-generated
  pins — two INDEPENDENT pin-sets, so evaluating detector-vs-gold is not tautological.
- Pre-registration: report the CONFIRMED read against the frozen prereg; state the honest authorization
  provenance (owner conditional pre-authorization delegating go/no-go against a pre-committed rule — NOT a
  claim the owner ratified every metric line-by-line).
- Intervention (H-B1′ selective clarification + H-B2′ oracle resolution) and the AU-Probe white-box contrast:
  ONE short paragraph each as `\todo{Phase 2b intervention results forthcoming}` /
  `\todo{Phase 2c AU-Probe white-box contrast forthcoming}` — describe the pre-registered DESIGN only, no
  numbers.

## 4. Structural placement (minimize disruption to frozen Study-1 content)
- Add a new top-level `\section{Study 2: A Black-Box Detector for Confident Latent-Premise Ambiguity}` AFTER
  the Study-1 Results section (after the "Exploratory…" subsection, ~line 710–740) and BEFORE
  `\section{Discussion}`. Subsections: (a) Concept: seed/context decomposition + the danger quadrant; (b) The
  LPP detector (method); (c) Executable gold-ambiguity + non-circularity; (d) Detection results (the table +
  danger quadrant + honest caveats); (e) Intervention + AU-Probe (forthcoming `\todo`s).
- Update the ABSTRACT and INTRODUCTION minimally to preview the two-study arc (one or two sentences — Study 1
  documents the failure; Study 2 gives a black-box detector). Keep Study-1 claims unchanged.
- You MAY add a detection results table (mirror the per-model panel from the results file) and, if
  straightforward, a 2×2 danger-quadrant schematic described in text (no new figure asset required — a
  `\todo{figure}` placeholder is fine if a figure would help).
- Do NOT touch the Deviations appendix's Study-1 content; you may add a Study-2 pre-registration note where
  natural.

## 5. References
- ADD a VERIFIED semantic-entropy citation — Farquhar, Kuhn, Gal et al., "Detecting hallucinations in large
  language models using semantic entropy," Nature 2024 (verify exact authors/volume/DOI before committing; if
  unsure, `\todo{verify cite}`). This is load-bearing (the whole SOTA-blind framing rests on it).
- Reuse existing `yang2025underspecification` for requirements-probing. Add other real, verified cites only as
  needed (e.g. AbstentionBench, CLAMBER, AU-Probe/"Mind the Ambiguity") — VERIFIED metadata only, else
  `\todo{verify cite}`. Do NOT fabricate.

## 6. Build & self-check gate (before PR ready)
- Compile with MiKTeX (`C:\Users\v-elzhang\AppData\Local\Programs\MiKTeX\miktex\bin\x64`, NOT on PATH):
  `pdflatex ×1 → bibtex → pdflatex ×2`; verify via log "Output written on … (N pages)" (pdflatex may exit 1 on
  the update nag — check the log, not just the exit code). Target 0 LaTeX errors, 0 undefined citations/refs.
- Report the new page count, the exact numbers you inserted (so the auditor can diff them against the results
  file), every new bib key added (with verification status), and confirmation that NO Study-1 number changed.
- Do NOT run any experiment. Do NOT merge. Stop at: additive tex/bib + clean compile + PR-ready.

## 7. Out of scope
- No Phase 2b/2c results (forthcoming placeholders only). No Study-1 number/hypothesis/frozen changes. No
  venue/template switch (owner deferred length/template). No fabricated citations or numbers.
