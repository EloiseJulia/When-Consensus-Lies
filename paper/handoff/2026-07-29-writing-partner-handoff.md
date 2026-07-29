# Handoff — English Writing-Partner session (2026-07-29)

> Role of the retiring session: **English writing-polishing partner** for the owner @EloiseJulia
> (owner prefers Chinese; target text is English; venue = CSCW / PACM HCI). This role touches
> **language / framing / presentation only** — never scientific claims, numbers, hypotheses, metric
> definitions, or provenance (those escalate to the owner). Law 1 (compile after every edit) and
> Laws 6/7 (provenance separation, pre-registration honesty, frozen metric) are inviolable.

## Paper state (verified)
- `paper/tex/consensus-lies.tex` — compiles clean at **29 pages, 0 undefined refs** (last verified this session).
- Template: `\documentclass[acmsmall,screen,review,anonymous]{acmart}`, `\acmJournal{PACMHCI}`.
- **All 972 experiment cells complete; all numbers frozen.** No numbers were changed this session.

## ⚠️ GIT: everything below is UNCOMMITTED
Last commit = DECISION-LOG **row 120** (SHA `26d93894`, "28pp"). The working tree is dirty:
- `M paper/tex/consensus-lies.tex`, `M paper/tex/references.bib`
- Figures were **reorganized into per-figure folders** (git shows the old flat paths as `D`; the new
  `figures/figN_*/` subfolders + `fig1_consensus_lies.pdf` are untracked).
- New untracked artifacts: `paper/specs/matched-triplet-study.md`, `paper/reviews/*.md`,
  `paper/handoff/2026-07-29-*.md`, `paper/paper-overview-zh.md`.
- Junk to ignore/clean: top-level `.llm_cache_*` dirs (not ours to commit).
**Recommendation:** owner (or next session, with owner's OK) should review + commit the writing changes.
This session did NOT commit (writing edits have not been through a cross-family PR audit).

## Build command (Law 1) — verified working
MiKTeX is NOT on PATH. Set it, point TEXINPUTS/BSTINPUTS at the vendored acmart, then pdflatex→bibtex→pdflatex×2:
```powershell
$env:Path="C:\Users\v-elzhang\AppData\Local\Programs\MiKTeX\miktex\bin\x64;"+$env:Path
$repo="C:\Users\v-elzhang\Desktop\MyFolder\When Consensus Lies"
$env:TEXINPUTS="$repo\paper\acmart-primary;"; $env:BSTINPUTS="$repo\paper\acmart-primary;"
cd "$repo\paper\tex"
pdflatex -interaction=nonstopmode -halt-on-error consensus-lies.tex
bibtex consensus-lies          # only needed when citations change
pdflatex -interaction=nonstopmode -halt-on-error consensus-lies.tex
pdflatex -interaction=nonstopmode -halt-on-error consensus-lies.tex
```
Verify: `Output written on ... (29 pages)` + **0 undefined** refs/citations. (The "MiKTeX updates" line is benign.)

## What this session did (chronological)
1. **De-AI-ification pass** (per owner's `润色指南.docx`): removed grandiose filler, meta-signposts,
   self-praise ("strengthens the thesis"), compressed the +0.085 double-statement, `Cross-model nuance:`→`Across models:`.
2. **Figure reorg**: every figure now lives in its own folder — `figures/fig1_overview`, `fig2_phase`,
   `fig3_capability`, `fig4_fake_redundancy`, `fig5_silent`, `fig6_danger_quadrant`, `fig7_auroc`,
   `extra_lpp_mechanism`, `extra_intervention`. `\graphicspath` lists ALL subfolders so bare filenames
   still resolve. Shared generators (`*.py`, `results_verified.json`, `figures_data.json`,
   `latex_includes_v2.tex`) stay at `figures/` root. Old versions preserved, not deleted.
3. **Simulated-CSCW-reviewer round #1** (owner-relayed): triaged; applied writing fixes only.
   - Softened provenance/compliance narration; condensed **Appendix A** ("Deviations…" → **"Preregistration
     Amendments and Deviations"**, 14-row table → 4-category table, governance jargon moved to artifact, kept
     all honest disclosure incl. confirmatory/secondary/exploratory tiers + AU-Probe-not-run + pre-registered
     outcomes). Saved ~1 page.
   - Added a **CD worked example (illustrative)**, a neutral **gloss** on "convergent delusion", a
     `(same wrong label)` clarifier on pairwise agreement.
   - Wrote **`paper/specs/matched-triplet-study.md`** (doc-only design spec for the reviewer's requested
     matched fully-specified/derivable/external experiment; NOT run — needs the governed pipeline + owner sign-off).
4. **A-items (owner-authorized scientific recharacterizations, writing executed):**
   - **H1b dose reclassified `Supported`→`Not supported (non-monotone)`**: primary CD is a THRESHOLD at
     k≥1 (0→0.89) then DECLINES (k2 0.68, k3 0.32) via foil-space + I⊥ dilution. Fixed L619 ("monotone"→threshold),
     §6.4 text, and Table 6 row. Core thesis unaffected (arguably strengthened; consistent with "boundary condition").
   - **Fig 4 n≈8.1 vs N=5 reconciled**: added the n_eff-saturation note (ρ̄≈0.89 ⇒ n_eff→1/ρ̄≈1.12, so the
     5-agent pool and the pooled nominal ≈8.1 both give ≈1.10 — an analytic ceiling).
5. **B-group presentation fixes:** anonymization (see below); scoped "no LLM judge" to *scoring* (enumeration
   is constructor-authored+audited); de-hedged ~7 genuine meta-hedges (kept legitimate scope qualifiers);
   Study-2 abstract calibration (AUROC CI, over-clarification 0.402, oracle paired with weak localization 0.36).
6. **Chained cross-family review pipeline** (Opus 4.8 reviewer → GPT-5.6-Sol reject-case → Opus 4.8 area chair)
   → `paper/reviews/reviewA_opus.md`, `reviewB_gpt_reject.md`, `reviewC_areachair.md`. Verdict: **Reject at CHI /
   Weak-Reject→Major-Revision (R&R) at CSCW**; ~20–25% CSCW as-is, ~40–55% after the escalate items.
7. **Reframing package** (writing lever from the AC): abstract 0.53 labeled "on constructed, default-screened
   items"; added **hidden-profile / common-knowledge** bridge (`stasser1985hidden`, `gigone1993common` in
   references.bib) to connect fake redundancy to CSCW-native group literature; renamed misleading
   "debate/MAD" primary-condition labels → "aggregation" (+ "no inter-agent messages" note); reconciled the
   detection FP `0.095` vs deployment over-clarification `0.402` (different experiments/rosters).
8. **Citation-accuracy fix:** `liang2024` (MAD-*encourages-divergence* paper) moved from the "converge to
   shared misconceptions" cite to the "debate can help" cite; `estornell2024` left as the correct support.
9. **New Figure 1**: owner's hand-drawn graphical abstract `fig1_consensus_lies.pdf` (copied into
   `figures/fig1_overview/`, spaces stripped) now `\includegraphics` for `\label{fig:overview}`. **All numbers
   in it were verified against `figures_data.json`** (n_eff 1.10, nominal 8.1, ICC 0.89, pairwise 0.98, CD 0.53
   pooled / 0.82 on k≥1 / 0.00 H2, abstention 0.03%/0.32%, 54 tasks — all correct). Old `fig_overview3.pdf` kept.

## Anonymization — CAMERA-READY TODO (do NOT forget)
For double-blind review the tex now says a generic "a fourth-vendor frontier code model outside the tested
pool" instead of "Microsoft mai-code-1-flash", drops "Copilot-proxy"/"local", and the roster table constructor
row reads "Fourth vendor / *slug in camera-ready*". **In camera-ready, restore:** constructor =
Microsoft `mai-code-1-flash`; the proxy descriptor; and any withheld slugs. Search the tex for
`slug in camera-ready`.

## Pending / escalate (owner's scientific call — NOT writing; several need data or the governed pipeline)
Ranked by the review pipeline's leverage:
1. **Human pilot (biggest lever; the one "fatal" gap).** A within-subjects reliance study (4/4-agree vs a
   dependence-aware panel), behavioral primary + short survey. Owner's target: **10–20 min/participant**;
   my recommended design = **8 trials, N≈50 within-subjects, ~13 min, ~$150 Prolific**, pre-registered,
   reuse the existing underspecified tasks. **A doc-only design spec was OFFERED but NOT yet written** —
   next session can draft `paper/specs/human-pilot-study.md` on request.
2. **Matched k=1 vs k=1 reanalysis** to kill selection-on-DV (`matched-triplet-study.md` spec already drafted).
3. **Cardinality-matched chance-agreement null** (rescues the inconclusive R1b).
4. **Family-blocked ICC / base-family clustered reanalysis** (n_eff exchangeability + pseudoreplication).
5. Run **ICE** as the detector comparison; disclose constructor + attach artifact for review.
6. Owner's open decisions: whether to keep "convergent delusion" (currently KEPT + gloss); whether to insert
   the v2 data figures / conceptual figures into the body (originals must stay); the deeper "no-attenuation"
   comparison being unmatched (0.685 vs pooled 0.53 not vs k≥1 0.82) — AC FIX-1, statistical, not a wording fix.

## Working style the owner expects (carry forward)
Small, reviewable before→after with a one-line aesthetic/informational reason; be opinionated and argue once
when you disagree, then execute faithfully once she decides; escalate anything touching claims/numbers/
provenance; compile + report pages/undefined after every edit; help her keep HER voice (don't flatten to
generic smooth prose); communicate in Chinese.
