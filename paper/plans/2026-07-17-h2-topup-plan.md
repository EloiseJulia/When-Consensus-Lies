# Plan — H2 top-up (slice/h2-topup, 2026-07-17)

> Manager-authored spec (Manager writes NO source code). Implemented by a spawned Claude-family sub-agent
> in `.worktrees/h2-topup`; audited by a GPT-family sub-agent (Hard Law 6). Pre-launch checklist item #2
> (owner, 2026-07-17): "if H2 is thin (<~10), do a small H2 top-up first (re-run the spot-check gate on
> the additions)."

## 0. Why
The regime MAIN-EFFECT contrast (H1_external fails-all vs H2_derivable resolved-by-all) is the paper's
core two-regime demarcation. Current benchmark has only **6 H2_derivable items** (3 families ×
{k0 control, k1}: data_typical, data_avgprice, data_rate). To firmly anchor the contrast, ADD ~4 new
H2_derivable families so total H2 items ≥ ~14. H1 (40 items) is already ample; do NOT change H1.

## 1. FROZEN — do NOT touch
`common/schema.py`, `harness/metrics.py`, `harness/nulls.py` defs, `paper/preregistration/*`, and the
EXISTING benchmark items in code_spec / policy_qa / the current data_analysis families. Do NOT modify or
renumber existing tasks (identity stability). This slice is ADDITIVE: new H2_derivable families only.

## 2. What defines a valid H2_derivable item (the regime criterion — READ the existing 3 exemplars first)
Study `bench/data_analysis/__init__.py` — specifically `data_typical` (median-vs-mean under a skew VISIBLE
in the prompt), `data_avgprice` (weighted vs unweighted when weights are IN the data), `data_rate`
(unequal-interval rate). Match their structure EXACTLY. A valid H2_derivable task:
- **Derivable disambiguator IN the retained prompt**: the information needed to pick the target
  interpretation I0 is PRESENT in the (clause-deleted) prompt / the data itself — a capable model can
  RESOLVE it from context WITHOUT external knowledge. (Contrast H1_external, where the disambiguator is
  deleted and only recoverable via external/domain knowledge.) This is the FROZEN regime criterion.
- **Executable gold**: deterministic numeric answer per interpretation (like the existing data tasks);
  the labeler distinguishes ALL interpretations. NEVER an LLM judge.
- **Fairness**: I0 (target) is the natural, uniquely-derivable answer from the retained prompt; each
  non-target foil deviates on exactly one axis; the model's naive default = a wrong foil. The deleted
  clause is exactly what a naive solver would miss but a careful one derives from the visible data.
- **Combinatorial structure (Amendment 03)**: `len(interpretations)==2^k'`, exactly one I0, one
  `[combined-default]` foil, `len(key_questions)==ambiguity_level==k'`, k0 control has empty key_questions.
  Generate the standard variants (at least k0 control + k1; add k2 where natural).
- **regime = "H2_derivable"** on every variant.

## 3. Deliverable — ~4 new H2_derivable data_analysis families (→ total H2 items ≥ ~14)
Add ~4 new families of DERIVABLE numeric-analysis ambiguity where the resolving signal is visible in the
data/prompt. Candidate axes (pick ones with a clean natural default + executable gold; AVOID
fee/cap/threshold axes with no default when the clause is deleted — cf. the benchmark-design memory):
- central tendency variants beyond median/mean where the data shape dictates the choice;
- growth/rate aggregation (geometric vs arithmetic when the series is multiplicative and VISIBLE);
- normalization/per-unit when units differ IN the provided rows;
- cumulative vs per-period when the framing is derivable from the column semantics in-prompt;
- tie/ordering handling when ties are present in the data;
- inclusive/exclusive boundary when the data makes the intended boundary derivable.
Each MUST be genuinely DERIVABLE (not external-knowledge). Keep them distinct from the existing 3 families
and from each other. Follow the exact code patterns + docstring/fairness conventions already in
`bench/data_analysis/__init__.py`.

## 4. Validation (self-check before ready)
- `python bench/data_analysis/__init__.py` (regenerate) + `python -m bench.validate --domain data_analysis`
  → 100% distinguishable, invariants hold on ALL variants (existing + new).
- `python -m pytest -q` → FULL suite green (add/extend data_analysis tests for the new families:
  distinguishability, 2^k' invariant, key_questions==k', regime=="H2_derivable", executable-gold values).
- Confirm the new H2 count: print the H2_derivable family + variant totals (target ≥ ~14 variants).

## 5. Provenance / workflow (Hard Law 6)
Implementer = Claude family (record in report). Auditor = GPT family (Manager spawns; report-only; MUST
scrutinize the FAIRNESS + DERIVABILITY of each new item — the key risk is an item that's actually
H1_external, ambiguous gold, or a fee/cap axis with no default). Remove any stray root `plan.md`. Commit
on `slice/h2-topup` with the Co-authored-by trailer; do NOT push/PR/merge.

## 6. AFTER merge (Manager)
Re-run the empirical default-check on the NEW H2 items ONLY (frontier proxy) to confirm the H2 tag
EMPIRICALLY: capable models RESOLVE the derivable ambiguity → I0 (not the foil). Reclassify/exclude any
item whose behavior doesn't match H2 (log it). This is the "re-run the spot-check gate on the additions"
per the owner's checklist. Then finalize Amendment 08 (final N) for owner sign-off.
