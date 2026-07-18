# Pre-Registration Amendment 10 — R2 cross-family construction control (operationalization)

> Operationalizes the FROZEN prereg §9 **R2 (cross-family construction control)**, which the Phase-6
> smoke test found was uncomputable because `constructor_family` was never populated (DECISION-LOG row 68).
> Owner ruled OPTION B (2026-07-18): genuinely RE-CONSTRUCT an H1 subset with a SECOND constructor family
> and re-run. This amendment documents the construction design + analysis so R2 can be computed as
> pre-registered. It does NOT change the primary metric (`cd_primary`/A04), the hypotheses, the regime
> criterion, R1 (A07), or the §9 R2 SUPPORT/REFUTE rule itself — it only supplies the cross-constructed
> data R2 requires. **STATUS: DRAFT — owner signs before the R2 subset run counts.**

## 0. What R2 tests (frozen §9)
R2 (cross-family construction control): H1 convergent delusion PERSISTS on benchmark items constructed by
a model family DIFFERENT from the tested agents — ruling out the confound "ρ is just a shared prior WITH
THE CONSTRUCTOR" (i.e. the traps were built to match the tested models' own prior). Frozen R2 rule
(decision_rules.evaluate_r2): the cross-family H1 aggregation-vs-single (CD) effect CI excludes 0 and is
positive → SUPPORTED.

## 1. Second constructor family (owner-selected)
**Anthropic `claude-opus-4.8`.** Distinct from the ORIGINAL constructor (mai-code) and, per item, distinct
from the tested families it is evaluated against. Because the main benchmark is mai-code-constructed and
this subset is Anthropic-constructed, the study now spans TWO independent constructor families.

## 2. Cross-family evaluation cells (which cells count for R2)
R2 is computed ONLY on cells where the TESTED model family ≠ the constructor family (Anthropic). I.e. the
tested OpenAI (gpt-5.4/5.6-sol/4o-mini) + Google (gemini-3.1-pro/3.5-flash) + mai-code cells on the
Anthropic-constructed items. Anthropic-tested cells (claude-*) on Anthropic-constructed items are the
SAME-family cells → EXCLUDED from the R2 cross-family estimate (reported separately as a same-family
reference). This is the genuine cross-constructor control.

## 3. Construction protocol (executable-gold, H1_external)
- **Generator:** `claude-opus-4.8` (via the local proxy) GENERATES the item semantics — the ambiguous
  scenario, the single deleted OUTSIDE-knowledge disambiguator (H1_external), the enumerated foils, and —
  per the FROZEN Amendment-01 target-reversal convention — the polarity: TARGET I0 = the interpretation
  requiring the EXTERNAL/hidden convention (NOT the natural default), and the FOIL(s) = the NATURAL DEFAULT
  a reasonable unaware solver produces. An unaware model lands on the FOIL → cd_primary (modal share over
  non-target foils) is high → the trap. (See the Correction note at the end of this amendment.)
- **Wrapping:** a construction sub-agent implements each generated spec in the existing bench format
  (deterministic executable-gold `check()`, unique-I0 fairness, Amdt-03 combinatorial invariants where
  k>1, `regime="H1_external"`, and the NEW immutable field `constructor_family="anthropic/claude-opus-4.8"`).
- **Coverage:** ~9–12 H1_external items across the 3 domains (code_spec / policy_qa / data_analysis),
  k∈{0,1} at minimum (k0 control + k1 trap). Empirically default-checked like the main benchmark.
- **constructor_family plumbing:** added as task metadata and propagated ADDITIVELY through
  `analysis/io.load_runs_tidy` (no change to the FROZEN `common/schema.py` if avoidable; if a Task field is
  required, it is an additive immutable field that does not alter existing identities/behavior).

## 4. Run & analysis
- **Run:** the R2 items go through the SAME frontier roster and grid as the confirmatory run (single +
  heterogeneous-MAD × the 4 model classes, 3 seeds), as a separate partition/checkpoint, $0 on the proxy.
- **Analysis:** `decision_rules.evaluate_r2` on the cross-family cells (§2); bootstrap 95% CI of the H1
  aggregation-vs-single (CD) effect excludes 0 & positive → R2 SUPPORTED. Same-family Anthropic cells
  reported alongside as a reference (not the R2 estimate).

## 5. Provenance (Law 6) & integrity
Constructor family = Anthropic ⇒ the item-construction GENERATOR is claude-opus, and the R2 estimate uses
NON-Anthropic tested cells. The construction sub-agent's CODE audit MUST be a DIFFERENT family than the
code author (Claude impl → GPT audit), as usual. R2 items are H1 traps built to the SAME frozen H1
criterion; no result peeking drives their design (they are deterministic, executable-gold).

## 6. What stays FROZEN
`cd_primary`/A04, H1/H2 hypotheses, the regime criterion, R1 (A07), the §9 decision rules INCLUDING the R2
SUPPORT/REFUTE rule. This amendment only supplies the cross-constructed data R2 was always meant to run on.

## 7. Sign-off
- [x] Owner @EloiseJulia approves the R2-B construction design (Anthropic claude-opus-4.8 second
      constructor; ~9–12 H1 items; cross-family cells = non-Anthropic tested; executable-gold; additive
      constructor_family). — 2026-07-18
- [x] Owner acknowledges R2 results are reported honestly whatever they are. — 2026-07-18

Amendment status: **SIGNED (owner @EloiseJulia, 2026-07-18).** See DECISION-LOG row 69.

## Correction note (2026-07-19, non-substantive — aligns text to frozen A01)
As-signed §3 mis-described the trap polarity as "NATURAL-DEFAULT target I0" — this contradicted the FROZEN
Amendment-01 target-reversal convention (verified against main item `code_quarter_001`: TARGET I0 = the
external/hidden-convention interpretation, e.g. fiscal-April; FOIL = the natural default an unaware solver
writes, e.g. calendar). The implemented R2 items follow the CORRECT (A01) polarity. This note corrects the
amendment TEXT to match A01 and the implementation; it changes NO design choice (A01's polarity was always
frozen), the metric, the R2 rule, or the constructor family. A GPT cross-family audit surfaced the
mis-description; the owner is notified for transparency (governance: no silent change to a signed doc).
DECISION-LOG row 70.
