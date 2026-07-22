# Manager Handoff — "When Consensus Lies" (2026-07-22)

> Authoritative current-state handoff from the retiring Manager session (context saturated) to a fresh
> Manager. READ THIS FIRST, then re-derive ground truth from git (`git --no-pager log --oneline -30 main`;
> `gh pr list --state all`; `git branch -a`) — trust the log over any narrative. Supersedes the
> 2026-07-18 handoff for current state; earlier handoffs (07-15/07-16/07-18) remain valid for history.

---

## 0. One-paragraph status
The pre-registration is FROZEN and owner-locked; the **confirmatory run is COMPLETE** (5,832 jobs, $0) and
**all three headline pillars are CONFIRMED**. A **CSCW full-paper LaTeX draft (15 pp, compiles clean)** exists
with real-data figures, a model-roster table, an Ethics section, and a Deviations-from-Prereg appendix. The
overview **Figure 1 is at v3** (rich visuals + print-legible + scientific-contract-clean). Remaining work is
**writing polish + owner verification** (bib citations, prose voice per CSCW LLM policy), an optional
verifier/SC-k10 sensitivity write-up (already computed), and the P2 human-validation of the abstention
detector (deferred). **No experiment is blocking.**

---

## 1. The science — strongest claim + what confirmed it
**Single strongest, defensible claim (the headline):** a **two-regime MAIN effect** keyed on the
disambiguator's **LOCATION**, not model capability.
- **H1_external** (disambiguating clause deleted & unrecoverable): agents **silently** converge on the same
  WRONG enumerated foil. `cd_primary = 0.532` uniform across ALL model classes incl. frontier reasoners &
  cross-family pools; abstention ≈ 0.02–0.03% (confidently wrong, not uncertain).
- **H2_derivable** (clause retained in-prompt): every tier incl. weak (gpt-4o-mini) resolves → `cd_primary
  = 0.000`. Δ = 0.53.
- **Fake redundancy (ρ→1):** H1 `n_eff = 1.10`, ICC = 0.89, pairwise wrong-agree = 0.98,
  independence-counterfactual Δ = +0.245 CI[0.234,0.257] (excludes 0). **SC-k10 sensitivity confirms the
  collapse persists at k=10** (n_eff=1.095, ICC=0.909).
- Robustness: **R1a (k0-control) STRONGLY SUPPORTED** (Δ CI[0.733,0.899]); **H1b SUPPORTED** (k-coef 0.314
  CI[0.177,0.452]). **R2 confound REBUTTED** by cross-family single-agent CD 0.72–0.87 on Anthropic-built
  foils.

**Honest nulls (a FEATURE — keep reporting them):** H1a INCONCLUSIVE (redundant aggregation neither amplifies
nor rescues; fake-redundancy is carried by n_eff/independence-cf, not H1a); R1b uniform-null INCONCLUSIVE on
cd_primary (high binary baseline) but SUPPORTED under drop-I_perp; row-35 hetero>homo NOT CONFIRMED →
reframed as **cross-family ≈ homogeneous** (shared prior spans families — supportive); H2 interaction
UNCOMPUTABLE (crossed-RE non-convergence, expected null); R2 pre-registered metric INCONCLUSIVE (confound
rebutted separately). Details: `files/phase6_confirmatory_report.md`, DECISION-LOG rows 72–75,
`paper/writing/2026-07-18-deviations-from-preregistration.md`.

---

## 2. Pre-registration & governance (INVIOLABLE)
- Prereg FROZEN at `c0a0393` (2026-07-15). Amendments **A04/A06/A07 SIGNED (A07 owner-personally-ratified)**,
  **A08/A09/A10/A11 SIGNED**, A05 SUPERSEDED. Primary metric = `cd_primary`/A04 (modal-wrong over ENUMERATED
  foils; I_perp in N but ineligible). R1 = A07-redefined R1a (k0-control) + R1b (uniform-null); label-shuffle
  demoted to diagnostic. **A11 scope: H1a/R2 use A08 PRIMARY methods ONLY** {single, sc, homogeneous-MAD,
  heterogeneous-MAD} — the frozen `_h1a_metric` pools all non-single methods, so interpretation-diverse/
  verifier MUST be filtered out.
- **Frozen-contract changes require owner @EloiseJulia PERSONAL ratification. NEVER AI-self-sign "owner."**
  Every design change → append a DECISION-LOG row + (if it touches prereg) a formal Amendment.

---

## 3. What this session (07-20→07-22) delivered
1. **SC-k10 sensitivity** — confirmed ρ→1 collapse persists at k=10 (row 75); integrated into paper F3.
2. **Paper enrichment** — filled the **Deviations appendix** (A01–A11 table + honest rule outcomes),
   **Ethics** section (no human subjects, provider terms, $0/near-zero compute, dual-use release mitigation),
   **model-roster table**, and resolved the default-check / prereg-cite / incomplete-foil `\todo`s. Paper →
   **15 pp, 0 errors**. (commit `1da123e3`)
3. **Figure-creation playbook UPGRADE** — rewrote `paper/research/2026-07-20-ai-figure-creation-playbook.md`
   into a top-venue Figure-1 method: scientific contract, storyboard→wireframe→render-spec, four validation
   gates (structural/render/semantic/final-size), reviewer-simulation, Inkscape-as-master, cross-model
   demoted to optional critique. (commit `b9118e07`)
4. **Overview Figure 1 — v1→v2→v3** (current = **v3**, embedded in paper):
   - v1 = rich but body text ~4.5pt (illegible at column width) + glyph tofu.
   - v2 = playbook-legible (min 20px→7.9pt) + contract-clean but too plain (owner rejected).
   - **v3 = v1's rich visuals (robot agent tiles, family color bars, distinct per-agent glyphs, burst
     rosette badges, refined flasks/outcome circles) + v2's legibility (≥18px, no tofu, flat stable-id) +
     scientific contract.** Produced via Claude contract → GPT-5.6 render → Gemini blind reviewer-sim (read
     all 5 core Qs from the raster). (commit `216e244a`)
   - Artifacts in `paper/tex/figures/`: `fig_overview3.{svg,pdf}`, `_preview.png`, `_alt.txt`,
     `_manifest.json`, `_design_brief.md`. v1 (`fig_overview.*`) and v2 (`fig_overview2.*`) retained as
     backups.

**Merged PRs this project:** #33 (H2 default-check), #34 (P1/P2), #35 (R2 subset), #36 (SC-k10 driver),
#37 (probe fix). Figure/paper/appendix work was committed directly to `main` (paper artifacts under
`paper/*`, not code) — consistent with prior paper-writing commits.

---

## 4. Tech facts the next Manager needs (verified)
- **All runs are $0** via the local **ghc-api Copilot proxy** `http://127.0.0.1:8313/v1` (no token, 40
  frontier models, effectively unlimited). MUST be running for live work; verify with Invoke-RestMethod to
  `/v1/models`. Runner is SEQUENTIAL (`harness/runner.py`); parallelize by DOMAIN (3×); the §10 ≥3-seed
  guard blocks single-seed partitioning; checkpoints in `.run_partitions/cp_<domain>.jsonl`.
- **LaTeX build:** MiKTeX at `C:\Users\v-elzhang\AppData\Local\Programs\MiKTeX\miktex\bin\x64` (NOT on PATH).
  Build: `pdflatex ×1 → (bibtex) → pdflatex ×2`. `pdflatex` prints a MiKTeX-update nag and may exit 1 even
  on success — verify via log "Output written on … (N pages)". Pipe to `| Out-Null` to swallow the nag.
- **Figures:** SVG→PDF via **svglib** (`svg2rlg`+`renderPDF`, pure-Python, Windows-friendly — Inkscape is
  NOT installed here, so svglib is the working fallback). PDF→PNG for QA via MiKTeX Ghostscript
  `mgs.exe -q -dNOPAUSE -dBATCH -sDEVICE=png16m -r150 -o out.png in.pdf` (use `-o`, and ABSOLUTE paths).
  renderPM/cairo backend is NOT available. Flat SVG rule for PPT: 0 `<g>`, 0 `transform=`, stable ids,
  vector icons (not font glyphs ✗✓✂), ASCII subscripts (I0/I1) — the PDF font tofus decorative Unicode.
- **Shell quirks:** fresh process each call (no persisted cwd/env); `&&` only chains native cmds — use `;`
  before PowerShell keywords; no heredoc (pipe a single-quoted here-string to `python -`); kill processes
  with `Stop-Process -Id <literal PID>` only (name/variable forms are guardrail-blocked).

---

## 5. Where things live
- Paper: `paper/tex/consensus-lies.tex` (15 pp, CSCW acmart/PACMHCI acmsmall) + `references.bib` (~30 cites,
  **owner must verify each**) + `figures/` (make_figures.py regenerates the 4 data figures from
  `figures_data.json`; fig_overview3 is the teaser).
- Living record: `paper/decisions/DECISION-LOG.md` (now **row 75**). Amendments: `paper/preregistration/`.
- Writing aids: `paper/writing/` (deviations ledger, results-and-framing), `paper/research/` (R5 novelty,
  CSCW style guide, figure playbook).
- Analysis: `analysis/` (frozen metric math — DO NOT edit), `scripts/registered_run.py`, `harness/`.
- Session artifacts for owner: `~/.copilot/session-state/8b4cb06a-.../files/` (consensus-lies.pdf,
  fig_overview3.svg/png, phase6_confirmatory_report.md, …).

---

## 6. Immediate next steps (no experiment blocking; polish + owner gates)
1. **Owner verification (blocking for submission, owner-only):** verify every `references.bib` citation;
   rewrite figure/LLM-assisted prose in own voice per CSCW 2026 LLM-authorship policy (the draft is a
   SCAFFOLD, marked as such).
2. **P2 abstention detector — human-validation** of the rule-based detector's sample (pre-registered,
   deferred) → then finalize the abstention `\todo` in the paper.
3. **Optional sensitivity write-up:** verifier condition (already in confirmatory data, H1≈0.53/H2 0) +
   SC-k10 (computed) — fold into a short Results/appendix paragraph if desired.
4. **Sharpen for venue:** stress-test the R5 novelty positioning (self-consistency diminishing returns /
   multi-agent debate echo-chamber / sycophancy / correlated-errors–CJT); pre-empt reviewer objections
   (construct validity, artifact, simulated-user overreach, power on the 14 H2 items).
5. Keep DECISION-LOG living; escalate every SCIENTIFIC judgment call to the owner.

---

## 7. Laws (unchanged, inviolable)
Orchestrator-only (Manager writes ONLY specs/plans/reports/decision-log/amendments under `paper/*`, owns
git/gh, spawns a sub-agent in a worktree for EVERY code/audit/fix). Provenance separation (Law 6):
implementer=Claude family, hostile auditor=different family (GPT), report-only. Merge only after full
build+run + suite green + cross-family audit 0 BLOCKER/MAJOR (Law 4). Executable gold > LLM-judge (Law 7).
One clean audit → merge; don't re-audit endlessly (Law 5). NEVER edit frozen files
(`harness/metrics.py`, `common/schema.py`, `harness/nulls.py` defs, `paper/preregistration/*`, `bench/*`
existing items, `analysis/` metric math) or the main checkout directly.
