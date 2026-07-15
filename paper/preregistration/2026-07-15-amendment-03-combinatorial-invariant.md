# Reconstruction Amendment 03 — combinatorial interpretation sets for reversed multi-axis tasks

> Owner-approved 2026-07-15 (Option A + metric-integrity guardrail). Governs the benchmark reconstruction
> under the target/default reversal. **The convergent-delusion metric and all hypotheses/decision rules
> stay FROZEN.** This only adjusts the per-variant INTERPRETATION STRUCTURE + construction invariant,
> because reversed multi-axis tasks are combinatorial, not 1-foil-per-axis. See design analysis:
> `paper/research/2026-07-15-reconstruction-design-fork.md`.

## Construction model (single-axis convention units + stacking)
- A **convention axis** `C` is a single external convention with a `target` value (the NON-default true
  intent, stated in the full spec) and a `default` value (what an unaware model produces). Each axis must
  be a genuine reversed trap: `target ≠ default` (verified empirically).
- A **task family** stacks `k` GENUINELY INDEPENDENT convention axes `C1..Ck` (deleting/varying one must
  not change another's gold — verify independence; no interaction/collapse).
- A **variant** deleting a subset `S ⊆ {C1..Ck}` (|S| = k') omits the clauses for axes in `S` and RETAINS
  (specifies, at their target values) the axes not in `S`.

## Interpretation set (COMBINATORIAL — the metric-integrity requirement)
For a variant deleting subset `S` (|S| = k'):
- Interpretations = **ALL `2^k'` combinations** where each axis in `S` takes `{target, default}` and axes
  not in `S` are fixed at `target`.
- `I0` = all-target (the true hidden intent).
- The **combined-all-default over S** = every axis in S at `default` = the **designated H1b foil**;
  it MUST be present and clearly MARKED (e.g. interpretation description contains `[combined-default]`).
- The `2^k' − 2` **partial** combinations are ALSO labeled interpretations with executable gold.
  Rationale (owner guardrail): agents converging on a PARTIAL-default combination is still convergent
  delusion and MUST count — the labeler must never send a real shared-wrong convergence to `I_perp`.

## Amended invariant (was: `len(key_questions)==k==len(interpretations)-1`)
For each variant deleting subset S (|S| = k'):
- `len(key_questions) == k'` (exactly the deleted axes), AND
- `len(interpretations) == 2^k'` (full combinatorial set), AND
- exactly one target `I0` (all-target), AND
- the combined-all-default-over-S foil is present and marked, AND
- 100% distinguishability across ALL `2^k'` interpretations via executable gold.
- k0 control: `S = ∅` → prompt == latent_spec, single interpretation `I0`, empty key_questions.
(For k'=1 this reduces to the old shape: 1 key_question, 2 interpretations — backward-consistent.)

## Metric integrity (FROZEN metric, dual reporting)
- `convergent_delusion` (frozen) counts the modal WRONG label over the FULL `2^k'` interpretation set —
  ANY shared-wrong convergence (combined OR partial) counts. Do NOT narrow to combined-default only.
- Analysis reports BOTH: (a) convergence-on-any-shared-wrong (the primary frozen metric) AND
  (b) convergence-on-the-combined-default foil (the designated H1b foil). No cherry-picking; the foil
  choice must not deflate the primary measure.

## Regime + gate (unchanged)
- Per-task `regime` (H1_external / H2_derivable / None) per the construction-time criterion; the EMPIRICAL
  per-regime default-check is the FINAL arbiter (H1 → defaults to a wrong combination even for reasoners;
  H2 → reasoners resolve, weaker default wrong).
- H1b (CD rises with ambiguity level k) measured across k-levels (1<2<3), on both reported measures.
- Reversed spot-check gate returns to the owner for final sign-off before any scaling/registered run.

## Domain guidance
- code_spec: purely H1_external convention traps (fiscal-quarter, 1-based indexing, GAAP rounding, US
  date, etc.), stacked independently for k=1/2/3. Drop the forced H2 `sortnum` (weak models resolve it).
- H2 demonstrators pursued where NATURAL (data_analysis: median-under-visible-skew; the disambiguator is
  in the data → reasoners resolve, weaker default to mean).
