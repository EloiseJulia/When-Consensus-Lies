# CHI Reframing Spec — "When Consensus Lies" → same-prompt multi-model interfaces

> Manager-authored implementation spec (orchestrator-only; NO source edits by Manager).
> Executes owner-approved **Option A** (2026-07-22): reposition the EXISTING, completed paper from CSCW to
> CHI by REFRAMING/PRESENTATION only. **No hypothesis, metric, estimand, data, or pre-registration change.**
> Source of the reframing direction: `comment1.md` (an external reviewer's suggestions, adopted with
> judgment). Grounding evidence: `paper/research/2026-07-22-multimodel-interface-landscape-audit.md`.
> Target file: `paper/tex/consensus-lies.tex` (+ `references.bib` additions for platform cites).

---

## 0. Non-negotiable guardrails for the implementer
- **DO NOT** change any number, hypothesis (H1/H2/H1a/H1b/R1a/R1b/R2), estimand, metric definition
  (`cd_primary`, `n_eff`, Eq. CD/neff), condition set, or result. The confirmatory run is frozen and done.
- **DO NOT** edit frozen files (`harness/metrics.py`, `common/schema.py`, `harness/nulls.py`,
  `paper/preregistration/*`, `analysis/` metric math, `bench/*` items). This is a TEX + BIB job only.
- **DO NOT** overclaim: no popularity/usage numbers, no real-world harm claims, no naming a platform as a
  culprit. Landscape framing = "a growing class of interfaces," per the audit doc's conservative language.
- **DO NOT** claim a human study or a deployed design was run. C3 (human study) and C4 (interface
  evaluation) are **explicitly future work**. Keep the honest-nulls posture.
- The paper remains an **executable-gold computational + landscape-audit** contribution. The design
  contribution is a **concept + design implications**, not an evaluated system.
- Keep the "SCAFFOLD / AI-assisted draft" honesty; owner will do final voice/citation pass.
- Preserve every existing `\cite{}`; only ADD platform citations. Build must stay clean (0 errors).

## 1. Core reframe (the one-sentence pivot)
FROM: a general finding that "AI multi-agent consensus can fail."
TO: a study of an **emerging HCI interaction paradigm — same-prompt multi-model interfaces** — that asks
whether model plurality actually delivers *independent corroboration*.

Chain the paper interrogates (state it explicitly in the intro):
`model plurality ⇒ perspective plurality ⇒ independent corroboration ⇒ higher trustworthiness`
and show the middle two links break when the disambiguator is outside the shared prompt:
`different models ⇏ independent interpretations/evidence`.

Headline slogan to thread through abstract/intro/discussion:
**"Model diversity is not necessarily evidence diversity."** / "Same-prompt pluralism can create answer
multiplicity without evidential independence."

Keep **convergent delusion** and **fake redundancy** as the phenomenon terms, but NOT as the title's central
word ("delusion" is too strong for a CHI title).

## 2. Title (implementer picks ONE; default = option 1 unless owner overrides)
1. **One Prompt, Many Models, One Blind Spot: Fake Redundancy in Multi-Model AI Interfaces**  ← default
2. Model Plurality Is Not Evidence Plurality: Auditing Multi-Model AI Comparison Interfaces
3. Many Models, Shared Assumptions: Rethinking Consensus in Multi-Model AI Interfaces
Keep an optional subtitle nod to the phenomenon term if desired. Update `\title{}` and the running header.

## 3. Abstract rewrite (≈180–220 words)
Rework the existing abstract so its FIRST 2 sentences name the real interface paradigm (users send one
prompt to several models — GPT/Claude/Gemini/etc. — and read parallel answers / consensus / a synthesized
answer as corroboration), citing the landscape. Then keep the existing scientific core verbatim in substance:
one manipulated factor (disambiguator inside vs outside the shared prompt), executable-gold, cross-family
convergence `cd≈0.53`, abstention ≈0.03%, `n_eff=1.10`, H2 resolves at `cd=0`, constructor-artifact ruled
out. Close on the design turn: interfaces should surface *evidential dependence*, not agent count. Do NOT add
new numbers.

## 4. Contribution restructure (keep FOUR; reorient — do not invent unrun work)
Map to `comment1.md` §四 but stay honest about what was actually done:
1. **Conceptual + interaction-paradigm.** Identify the hidden assumption in same-prompt multi-model
   interfaces (agreement across models = independent corroboration) and name **fake redundancy**: under a
   shared information boundary, model plurality yields answer multiplicity without evidential independence.
   (Motivated by the landscape audit, §NEW.)
2. **Empirical (large-scale computational).** The existing pre-registered executable-gold result, now
   described with product-facing condition names (§6): single vs repeated-sampling vs cross-vendor
   comparison/aggregation vs interpretation-first — model diversity and capability do NOT restore
   interpretive independence.
3. **Methodological.** The executable-gold protocol measuring correlated error (not accuracy), no LLM judge,
   pre-registered. (Unchanged in substance; keep.)
4. **Design.** A **dependence-aware multi-model interface** *concept* + design implications: show shared-input
   / missing-context / shared-interpretation / alternative-interpretation signals and a request-clarification
   action, instead of "4/4 models agree." Grounded in the landscape gap (interfaces show plurality but rarely
   input-dependence). **Framed as design implications + a proposed concept, evaluation is future work.**

The old 4 contributions (Empirical/Methodological/Conceptual/Design) largely survive — this is a reordering
+ interface framing, not new claims.

## 5. NEW background subsection: multi-model comparison interfaces
Add a subsection in the Background/Related-Work section (§"Consensus, Grounding..."), e.g.
`\subsection{Same-prompt multi-model comparison interfaces}` that:
- Establishes the paradigm exists (landscape audit): one prompt → many models → parallel/consensus/
  synthesized answers → user judgment. Cite 4–6 verified platforms from the audit's bibliography
  (ChatHub, Open WebUI multi-model, PromptQuorum, MultipleChat, Poe multi-bot, Google AI Studio compare).
- States the audit's key asymmetry: these interfaces commonly offer plurality/comparison/consensus/synthesis
  and sometimes claim improved trust/verification, but **rarely** signal that all models share the same
  input or warn the prompt may be missing information.
- Uses ONLY conservative language ("A growing class of multi-model interfaces allows users to query multiple
  models with the same prompt"). No popularity claims. Position as a **landscape analysis**, not market
  research. A compact version of the audit's coding table MAY be added as a small table or moved to an
  appendix; the full audit stays in `paper/research/`.

## 6. Condition relabeling (dual naming — presentation only)
In §"Conditions and estimands" and Results, keep the frozen internal names but add product-facing labels so a
CHI reader maps conditions to real interface behaviors. The mapping (existing confirmatory `config` values):
| internal (frozen) | product-facing label (add) | interface behavior |
|---|---|---|
| `single` | Single-model assistance | one model answers once |
| `sc` (k=5; k=10 sens.) | Repeated sampling (self-consistency) | one model resampled, majority |
| `heterogeneous-MAD` | Cross-vendor comparison/aggregation | different vendors, same prompt, aggregated |
| `homogeneous-MAD` | Same-vendor ensemble | same model ensemble (ρ→1 baseline) |
| `interpretation-diverse` | Interpretation-first comparison | agents disclose task interpretation before answering |
| `verifier` | Verifier-augmented | secondary check pass |
Do NOT rename in code or re-run; this is a labeling gloss in prose/tables only. Note explicitly that our
"cross-vendor comparison" is the strongest real-world platform condition, and that a pure *synthesis*
condition (one extra model merges all answers) and a *role-diversified* workflow are **future computational
conditions** (Option B), not yet run — say so honestly in Future Work.

## 7. Discussion / Implications — retarget to CHI
- Rename `\section{Implications for CSCW and Collaborative AI Systems}` →
  `\section{Design Implications for Multi-Model Interfaces}` (or "for Human–AI Interfaces").
- The existing 8 implications already fit; foreground: measure dependence not agreement; aggregate
  interpretations before answers; route on contextual completeness; **diversify evidence and interpretations,
  not merely model providers** (make this the closing design principle, per comment §四).
- Recast implication (1) as the concrete **dependence-aware consensus display** (the C4 concept): instead of
  "4/4 agree," show shared-input=Yes, context-completeness=Uncertain, common vs alternative interpretation,
  recommended action = request the missing convention.

## 8. Future Work (NEW or expanded) — honest scoping of C3/C4 + Option B
Add a short Future Work paragraph (in Discussion or Limitations) stating that the natural next steps are:
- **A human-subjects study (~50 participants, within-subjects)** testing whether cross-model agreement raises
  adoption, whether that causes over-reliance when models share a wrong interpretation, and whether a
  dependence-aware interface increases clarification-seeking. (Design sketch available; not yet run —
  requires IRB.)
- **Computational conditions** for cross-vendor *synthesis* and *role-diversified evidence workflows*, to
  test whether diversifying evidence/interpretations (not vendors) reduces wrong consensus.
- **Evaluating** the proposed dependence-aware interface.
Keep this modest and clearly labeled as future work; do not imply any of it was done.

## 9. Metadata
- CCS: keep Human-centered computing top concept; ADD an HCI/interaction concept if apt (e.g.
  "Human-centered computing~HCI theory, concepts and paradigms" / "Empirical studies in HCI"). Keep AI concept.
- Keywords: ADD `multi-model interfaces, model comparison, same-prompt querying, evidential independence,
  trust and reliance, human-AI interaction`; keep existing relevant ones. Drop nothing scientific.
- Document class stays acmart; if the current class option is `sigconf`/`acmsmall` for PACMHCI, LEAVE the
  build format as-is unless it fails — CHI vs PACMHCI template choice is an owner decision; note it in the PR
  body but do not switch templates in this pass.
- The `\todo{Anonymized for review.}` and abstention `\todo` stay as-is (owner-owned).

## 10. Build + self-check gate (implementer must pass before ready)
- Build: MiKTeX at `C:\Users\v-elzhang\AppData\Local\Programs\MiKTeX\miktex\bin\x64` (not on PATH).
  `pdflatex ×1 → bibtex → pdflatex ×2`; verify log "Output written on ... (N pages)". Swallow the update nag.
- Verify: 0 LaTeX errors; all `\cite{}` resolve (no `??`); page count reported; new platform cites present in
  `references.bib` with URLs + accessed dates from the audit bibliography.
- Diff hygiene: confirm NO change to any number/hypothesis/metric/result sentence (grep the diff for changed
  digits in Results/abstract — there should be none except relocation).
- Record the implementer's model family in the PR body (must be Claude family for the cross-family audit).

## 11. Provenance / process (Manager-owned)
- Implementer sub-agent: **Claude family**, in a worktree `chi-reframe`.
- Auditor sub-agent: **different family (GPT, e.g. gpt-5.6-sol)**, report-only, hostile: checks §0 guardrails,
  no frozen-science drift, no overclaim, citations resolve, build clean, CHI-appropriateness.
- Merge only after 0 BLOCKER/MAJOR (Law 4). Manager appends a DECISION-LOG row: venue/presentation reframe,
  before→after, WHY (owner Option A, CHI target, comment1.md), Affects = framing/presentation only,
  Deviation? = **N** (no hypothesis/metric/prereg change). Call out in PR body that only tex+bib changed.
