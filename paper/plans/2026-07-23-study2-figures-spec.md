# Study-2 FIGURES SPEC — for the Claude figure sub-agent

> Manager-authored (orchestrator-only). Owner ratified (2026-07-23) TWO Study-2 figures: (F-DQ) a
> danger-quadrant diagram and (F-AUROC) an AUROC-vs-baselines empirical figure with 6-model consistency.
> Additive; use REAL data only; NEVER plot fabricated data points or invent numbers. Do NOT change any
> result number or frozen content.

## 0. Provenance & governance
- You are the Claude-family figure author. A GPT-family auditor (`gpt-5.6-sol`) cross-family audits for DATA
  FIDELITY + no-fabrication + legibility before merge (Law 6). Record your family in the PR body.
- Work ONLY in your assigned worktree/branch. Never touch the main checkout or frozen files. You MAY add
  `paper/tex/figures/*` assets + a generator + `\includegraphics` + captions in `consensus-lies.tex`.
- **NO FABRICATION (inviolable):** every plotted value must trace to a real data source below. If you plot a
  scatter, each point must be REAL per-item data — never invent point positions. If real per-item data cannot
  be cleanly extracted, fall back to a clearly-captioned CONCEPTUAL schematic that contains NO data points
  masquerading as measured (label it a schematic).

## 1. Conventions to follow (read first)
- `paper/tex/figures/make_figures.py` — the existing figure generator. FOLLOW its style/output conventions
  (fonts ≥18px equivalent, flat stable IDs, colorblind-safe palette, vector PDF output). Add your two figures
  here (a new function each), do NOT rewrite existing figures.
- `analysis/figure_data.py` — existing figure-data helpers (reuse if useful).
- Existing Study-1 figures compile via `\includegraphics{fig_*.pdf}` resolved from `paper/tex/figures/`.
  Match that pattern: output `fig_danger_quadrant.pdf` and `fig_auroc_comparison.pdf` there.

## 2. Data sources (authoritative — quote exactly, invent nothing)
- **`files/study2_stage2_results.md`** — the CONFIRMED per-model + pooled numbers (authoritative for F-AUROC).
- **Per-item signals for F-DQ scatter:** the confirmatory checkpoint `.run_partitions/cp_lps_confirm__*.jsonl`
  (read-only) + the existing `scripts/lps_confirm_report.py` / `scripts/lps_gold.py` / `analysis` code, which
  already aggregate per-item `H_seed`, `H_ctx-self`, and the executable gold stratum (AMB+/AMB−). Extract the
  per-item means the SAME way `lps_confirm_report.py` does (per-item mean across model×seed cells). If you
  add an export path, reuse the frozen aggregation — do NOT recompute with a different rule. If clean
  extraction is infeasible in time, use the conceptual fallback (see F-DQ below) — do NOT fabricate points.

## 3. F-DQ — the danger-quadrant figure
- Axes: `H_seed` (semantic entropy, the SOTA signal) on one axis, `H_ctx-self` (LPP) on the other. Shade the
  **low-`H_seed` ∧ high-`H_ctx-self`** quadrant as the DANGER ZONE = "confident latent-premise ambiguity
  (semantic-entropy-blind)". Mark the frozen thresholds (τ_s = 0.5 on H_seed; τ = 0 on H_ctx).
- **Preferred (data-driven):** scatter the 54 real items at their per-item (`H_seed`, `H_ctx-self`) means,
  colored by executable gold stratum (AMB+ vs AMB−). This shows AMB+ items concentrating in the danger zone
  (the 25/33 = 0.758 danger-quadrant mass) while semantic entropy stays low — REAL, non-fabricated.
- **Fallback (only if per-item extraction infeasible):** a clean 2×2 conceptual schematic with the four
  quadrant labels (genuinely-determined / DANGER / rare / openly-uncertain) and NO fake data points; caption
  it explicitly as a schematic. State in your report which version you used and why.
- Caption must state the danger-quadrant mass (0.758, 25/33) and that semantic entropy is blind there.

## 4. F-AUROC — the empirical AUROC comparison
- Grouped bars (or dot-with-CI): per-model AND pooled AUROC for **H_ctx-self (LPP)** vs **H_seed
  (semantic entropy)** vs **requirements-probing** (and optionally self-consistency). Use the EXACT values +
  95% CIs from `files/study2_stage2_results.md`:
  - Pooled: LPP **0.895** [0.815, 0.966], semantic-entropy **0.581** [0.484, 0.675], req-probing **0.810**
    [0.680, 0.931].
  - Per-model LPP 0.856–0.887 vs semantic-entropy 0.551–0.606 vs req-probing 0.794–0.832 (use the exact
    per-row numbers from the table for all 6 models: claude-haiku-4.5, claude-opus-4.8, gemini-3.1-pro,
    gemini-3.5-flash, gpt-4o-mini, gpt-5.6-sol).
  - Draw a chance line at 0.5.
- The figure must make the HONEST story visible: LPP clearly separates from semantic entropy (≈chance), but
  requirements-probing is ALSO strong (0.810) — do NOT hide the modest LPP-vs-req-probing gap (+0.085). The
  caption states this honestly.

## 5. Integrate + build
- Add both figures to the Study-2 section (F-DQ near the danger-quadrant concept subsection; F-AUROC in the
  detection-results subsection) with informative captions. Keep captions honest (no overclaim).
- Regenerate the assets via `make_figures.py`, then compile MiKTeX (`pdflatex → bibtex → pdflatex ×2`);
  verify "Output written on … (N pages)", 0 errors, 0 undefined refs, and that BOTH new figures appear.
- Commit assets (fig PDFs), the generator diff, and the tex with EXPLICIT `git add` paths + Co-authored-by
  trailer. Do NOT merge.

## 6. Self-check + report
Report: which F-DQ version (data-driven vs schematic) and why; every number/point source (so the auditor can
diff vs `study2_stage2_results.md`); confirmation NO result number changed; new page count + "Output written";
any data-extraction caveats. Do NOT fabricate. Do NOT run experiments. Do NOT merge.
