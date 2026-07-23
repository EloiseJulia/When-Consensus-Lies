# Novelty-differentiation INTEGRATION SPEC — for the Claude writing sub-agent

> Manager-authored (orchestrator-only). Owner ratified (2026-07-23) FULL integration of the novelty-collision
> review (`paper/research/2026-07-23-novelty-collision-review.md`) into `paper/tex/consensus-lies.tex`:
> add + differentiate the two HIGH-risk collisions (ICE / Hou 2024, Kim et al. 2025) and the MEDIUM ones,
> re-scope the Abstract/Introduction to front-load the differentiators, and sharpen the pinning-vs-surfacing
> separation. Additive/prose; do NOT change any NUMBER, hypothesis, or frozen content.

## 0. Provenance & governance
- You are the Claude-family writer. A GPT-family auditor (`gpt-5.6-sol`) cross-family audits for citation
  correctness + overclaim + no-number-change before merge (Law 6). Record your family in the PR body.
- Work ONLY in your assigned worktree/branch (off current `main`, which already contains the Study-2
  detection section). Never touch the main checkout or any FROZEN file. You MAY edit `consensus-lies.tex` and
  `references.bib` (VERIFIED entries only).
- **NO FABRICATION (inviolable):** every citation must be a REAL paper with correct metadata. Two are already
  Manager-verified (use these exact metadata):
  - `hou2024decomposing` — Hou, Liu, Qian, Andreas, Chang, Zhang, "Decomposing Uncertainty for Large Language
    Models through Input Clarification Ensembling," ICML 2024 (Oral), PMLR 235:19023–19042, arXiv:2311.08718.
  - `kim2025correlated` — Elliot Kim, Avi Garg, Kenny Peng, Nikhil Garg, "Correlated Errors in Large Language
    Models," ICML 2025, arXiv:2506.07962.
  Any OTHER new cite (e.g. Estornell & Liu NeurIPS 2024 "Multi-LLM Debate"; verify Yang et al. venue already
  in bib) must be independently verified before adding, else leave `\todo{verify cite}` — do NOT invent.
- Do NOT change any Study-1 or Study-2 NUMBER, CI, table value, hypothesis, or estimand. Prose + citations +
  framing ONLY.

## 1. Source of truth
`paper/research/2026-07-23-novelty-collision-review.md` — the full review, incl. Section 6 with DRAFTED
differentiator sentences for Intro/Abstract/novelty-restatement. Use those drafts as starting material
(tighten to the paper's voice; do not copy verbatim if it introduces any claim not supported by our results).

## 2. Required edits
### (a) Study 2 Related Work — ICE differentiation [BLOCKING — the single most important gap]
Add `hou2024decomposing` (ICE) to the Study-2 / uncertainty-quantification related work and EXPLICITLY
differentiate: ICE decomposes uncertainty into aleatoric/epistemic via input-clarification ensembling
(conceptually close to our H_seed/H_ctx decomposition), BUT LPP (i) specifically targets the low-H_seed ∧
high-H_ctx **danger quadrant** where semantic entropy is blind by design (ICE does not target this regime);
(ii) uses **counterfactual pinning of self-surfaced premises** rather than open-ended clarification
generation — a sharper answer-sensitivity signal that filters assumptions which change the framing but not the
executable answer; (iii) evaluates against **executable gold-ambiguity** (not LLM-judge); (iv) runs
identically across three vendors **without logit access** (deployable on multi-vendor same-prompt interfaces,
unlike white-box AU-Probe). Keep the HONEST caveat: the pinning increment over requirements-probing alone is
modest (+0.085 AUROC) — frame the headline as "exposes a failure mode semantic entropy cannot reach," not
"beats every baseline." (See review §6 R2 draft.)

### (b) Study 1 differentiation from Kim et al. + Estornell & Liu
Add `kim2025correlated` (and, if verified, Estornell & Liu NeurIPS 2024) to Study-1 related work with the
crisp rebuttal: Kim et al. document cross-provider correlated errors as an observed PROPERTY at scale; we
contribute the first CONTROLLED, pre-registered, capability-invariant, executable-gold demonstration that the
disambiguator's LOCATION causally switches the failure on/off (cd 0.53 ↔ 0.00, n_eff=1.10), reframed as a
multi-model interface-design variable. Estornell & Liu prove debate CONVERGES on shared misconceptions in
THEORY; we give the controlled information-location experiment. (Review §6.)

### (c) Abstract + Introduction re-scope (front-load the differentiators)
Minimal edits so the Abstract and Intro state up-front that the contribution is NOT rediscovering correlated
errors / uncertainty decomposition but (Study 1) the controlled causal disambiguator-location phase boundary
and (Study 2) the danger-quadrant detector that reaches semantic entropy's blind spot. Use the review's §6
drafted sentences, tightened. Do NOT overstate; keep scope to the 54-item executable benchmark + tested
models.

### (d) Pinning-vs-surfacing separation (sharpen, no new experiment)
We ALREADY report the requirements-probing baseline (surfacing WITHOUT pinning, pooled 0.810) vs the full
detector (0.895). Frame this existing contrast EXPLICITLY as the ablation that separates LPP from open
clarification/ICE: pinning adds a real but modest +0.085 by filtering non-answer-changing assumptions. Do NOT
invent a new ablation or numbers — just frame the existing one as the decisive separator, honestly.

## 3. What NOT to do
- No new experiments/numbers; no Phase 2b/2c results; no Study-1/Study-2 number or hypothesis change.
- No fabricated citations; no venue/template switch; no editing frozen files.
- Do not overclaim the pinning increment or generalize beyond tested items/models.

## 4. Build & self-check gate
- Compile MiKTeX (`C:\Users\v-elzhang\AppData\Local\Programs\MiKTeX\miktex\bin\x64`): `pdflatex → bibtex →
  pdflatex ×2`; verify "Output written on … (N pages)", 0 errors, 0 undefined citations/refs.
- Report: every new bib key + verification status; the exact prose added per (a)-(d); new page count;
  confirmation NO number/hypothesis changed; any `\todo{verify cite}` left. Do NOT merge; do NOT run experiments.
