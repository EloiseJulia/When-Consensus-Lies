# Plan — R1 null redefinition per Amendment 07 (slice/r1-null-redef, 2026-07-17)

> Manager-authored spec (Manager writes NO source code). Implemented by a spawned Claude-family sub-agent
> in `.worktrees/r1-null-redef`; audited by a GPT-family sub-agent (Hard Law 6). Implements SIGNED
> Amendment 07 (`paper/preregistration/2026-07-17-amendment-07-r1-null-redefinition-SIGNED.md` — READ IT).

## 0. Why
The §11 MVP pilot showed the frozen R1 label-shuffle null is a mathematical IDENTITY for this thesis
(null_cd == real_cd in every condition), because cd is a function of the label marginal and a
marginal-preserving shuffle can't reduce it for a shared-prior phenomenon. Owner SIGNED Amendment 07:
redefine R1 → **R1a (k=0-control contrast)** + **R1b (uniform-over-interpretations null)**, and DEMOTE the
label-shuffle to a SECONDARY shared-prior diagnostic (retained, still reported, and kept meaningful for
MAD/debate). Re-run the §11 pilot gate with the corrected null before scaling.

## 1. FROZEN — do NOT touch
`harness/metrics.py`, `common/schema.py`, `harness/nulls.py` (the frozen `label_shuffle_null` stays
UNCHANGED — still computed for R1-diag + MAD), `paper/preregistration/*`, `bench/*`, and the metric MATH
in `analysis/cd.py|contrasts.py|decision_rules.py|stats.py`. This slice is ADDITIVE (new null helper) +
edits the NON-frozen §11 gate driver. If any change seems to need a frozen edit, STOP and report it.

## 2. Deliverables

### D1 — `analysis/nulls.py`: add the uniform-over-interpretations null (R1b)
Add `uniform_interpretation_null(items_labels, items_interpretations, target, n_perm=1000, seed=42) -> float`
(additive; do NOT modify the existing `cd_primary_shuffle_null`). For each item, draw each agent's label
UNIFORMLY at random from THAT item's own interpretation-ID set (e.g. `["I0","I1",...,f"I{2**k'-1}"]`, or
the actual interpretation ids from the Task), recompute mean `cd_primary` (from `analysis/cd.py`) over
items, average over `n_perm` permutations → CD_unif. Deterministic via `random.Random(seed)`. The
interpretation set per item MUST come from the item (its `interpretations`/k'), NOT the pooled empirical
labels. Golden test: an item where all agents pick the same foil (real cd≈1.0) with 2 interpretations →
CD_unif ≈ 0.5 (≪ real), proving the null discriminates; a k=2 item (4 interps) → CD_unif lower.

### D2 — `scripts/registered_run.py`: replace the R1 refutation gate with R1a + R1b; demote label-shuffle
- **R1a (k=0-control contrast)** becomes a GATE criterion: compute mean cd_primary on k=0 controls
  (must be ≈ 0, `≤ NULL_CD_TOLERANCE`) AND on k≥1 items (must be > 0); PASS requires CD_k0 ≈ 0 AND
  CD_{k≥1} > CD_k0 (and, where ≥2 items exist, that the difference is positive). Require the pilot batch
  to contain BOTH k=0 controls and k≥1 items for the SAME regime (H1) so the contrast is evaluable; if
  not, that sub-gate is INCONCLUSIVE (not a false PASS).
- **R1b (uniform null)** becomes a GATE criterion: observed CD on k≥1 items ≫ CD_unif (from D1); PASS
  requires observed CD_{k≥1} > CD_unif by a clear margin (define an explicit margin/tolerance; document it).
- **Label-shuffle → SECONDARY DIAGNOSTIC**: keep computing `cd_primary_shuffle_null` and REPORT it
  (per-condition, as today) but it NO LONGER drives PASS/FAIL. Label the report line clearly as a
  "shared-prior diagnostic (null≈real is EXPECTED — evidence of the shared prior, Amdt 07)". Keep the
  frozen `harness/nulls.py::label_shuffle_null` value reported too if already present.
- The overall §11 GATE VERDICT = gate A (cd_primary>0 on k≥1 real items) AND R1a AND R1b AND gate C
  (per-model job completion + cardinality + golden). Print each sub-result PASS/FAIL/INCONCLUSIVE with
  its numbers, plus the label-shuffle diagnostic, the per-condition I_perp rate, and total cost.
- Keep everything else (endpoint-aware loading, per-model gate C, k≥1 pilot selection, guards) intact.

### D3 — tests
Golden/unit tests for D1 (uniform null discriminates) and D2 (R1a passes when k0≈0 & k≥1 high, FAILS when
k0 is high or k≥1≈k0; R1b passes when obs≫uniform, FAILS when obs≈uniform; label-shuffle no longer
affects the verdict; INCONCLUSIVE when the batch lacks k0 or k≥1). Keep the FULL suite green
(`python -m pip install -e . && python -m pytest -q`). Do not pin the mutable live `.llm_cache`.

## 3. Provenance / workflow (Hard Law 6)
Implementer = Claude family (record in the report). Auditor = GPT family (Manager spawns; report-only).
Self-check gate: full build + pytest green; `RUNNER_LIVE` unset ⇒ `scripts/registered_run.py --pilot`
prints "skipped"/exits 0 (no network); a `--pilot --dry-run` shows the grid without executing. Remove any
stray root `plan.md`. Commit on `slice/r1-null-redef` with the Co-authored-by trailer; do NOT push/PR/merge.

## 4. Out of scope
The live pilot RE-RUN (Manager orchestrates after merge) and the full-scale confirmatory run.
