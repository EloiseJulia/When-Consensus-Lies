# Phase 1-R — data_analysis reconstruction under target/default reversal (per-slice plan)

> Manager-authored plan (orchestrator-only). Implementer = Claude family, in worktree
> `.worktrees/phase1r-data_analysis` (branch `slice/phase1r-data_analysis`). Auditor = NON-Claude
> (cross-family, Hard Law 6). Governs the reversed reconstruction of the `data_analysis` domain.
> Template of record: `bench/code_spec/__init__.py` (merged PR #16, `f6e11c1`). Metric FROZEN.

## Why this slice
`data_analysis` on main is still the OLD **target = model's natural default** construction ⇒
convergent_delusion ≈ 0 (the artifact fixed by Amendment 01). Reconstruct it under the REVERSED
property so the target is a deliberately NON-default true intent and the model's default is a WRONG foil.
This domain also carries the project's ONLY clean **H2_derivable** demonstrator (median-under-skew).

## Governing decisions (READ FIRST — these are frozen)
- **Amendment 01** (target/default reversal): I0 = NON-default true intent; model default = a WRONG foil.
- **Amendment 03** (combinatorial): each convention axis is **BINARY** `{target, default}`. A variant
  deleting subset S (|S|=k') has EXACTLY `2^k'` interpretations (all target/default combinations over S,
  axes ∉ S fixed at target). I0 = all-target. The combined-all-default-over-S foil is marked
  `[combined-default]` in its `InterpretationBranch.description` (build.py appends `__combdef` to its
  serialized gold_check automatically — do NOT hand-append it).
- **⭐ Binary-axis ruling (Manager, 2026-07-16, logged):** follow the code_spec #16 binary model. The
  older `paper/specs/phase1-benchmark-reversal-spec.md` Examples B/C/D show a THIRD "other deviation" foil
  (mode / fiscal-July / ≥2) per k=1 axis — those illustrative examples PREDATE Amendment 03 and are
  SUPERSEDED. Do **not** add a third per-axis value; keep every axis strictly `{target, default}` so the
  `2^k'` invariant holds and `bench/build.validate_full_spec` passes. (If the later empirical default-check
  shows models converging on an un-enumerated third value dumped to I_perp, we add it THEN, documented.)
- Metric `convergent_delusion` and all hypotheses/decision rules are FROZEN — do not touch
  `harness/metrics.py`. Preserve executable gold (never LLM-judge), deletion-based ambiguity, cross-family
  construction, and 100% distinguishability.

## Required scientific content (I own the design; you implement it faithfully)
Build reversed families keeping data_analysis's existing executable-gold style (candidate Python code run
in the isolated subprocess `DataChecker`, exact deterministic numeric match). At minimum:

### 1. H2_derivable demonstrator — median-under-visible-skew (REQUIRED; single axis, k=1, binary)
- `regime="H2_derivable"`. Dataset embedded in the prompt: `[2, 4, 4, 4, 5, 5, 7, 900]`.
- Axis `central_tendency`: **target = median** (the outlier 900 is VISIBLE in the data, so a reasoning
  model can DERIVE that the median is the representative "typical value"); **default = arithmetic mean**.
- Interpretations (2): `I0` median = **4.50** (target); `I1` mean = **116.375 → 116.38** (2dp)
  `[combined-default]`, `opened_by="central_tendency"`.
- latent_spec clause (deleted at k=1): "This dataset is dominated by a single extreme outlier (900) that
  distorts the mean; report the MEDIAN as the representative typical value. Answer to 2 decimals."
- key_questions(k1): ["Which measure of central tendency represents the 'typical value' (mean/median)?"]
- Fairness: a human reading the full spec agrees the user wanted the median BECAUSE of the visible skew.

### 2. H1_external demonstrator — org-specific KPI threshold (REQUIRED; single axis, k=1, binary)
- `regime="H1_external"`. Dataset in prompt: weekly session counts `[5, 3, 1, 4, 2, 3, 0, 6, 1, 2]`.
- Axis `active_user_threshold`: **target = ≥3 sessions/week (org KPI)** → count = **5**;
  **default = ≥1 ("any activity")** → count = **9** `[combined-default]`,
  `opened_by="active_user_threshold"`. The KPI threshold is EXTERNAL (not derivable from the data).
- latent_spec clause (deleted at k=1): "Per our company KPI, an 'active user' has AT LEAST 3 sessions per
  week. Count active users."
- key_questions(k1): ["What session-count threshold defines an 'active user' (the org KPI)?"]

### 3. At least one MULTI-AXIS H1_external family (k=2, 4 interps) to exercise the combinatorial machinery
Stack two GENUINELY INDEPENDENT external conventions (deleting one must not change the other's gold —
verify independence, no interaction). Propose the exact axes in your plan.md and get them right; a clean
option: an org-KPI **threshold** axis (≥3 vs ≥1) stacked with an org **reporting-rounding** axis on the
active-user PERCENTAGE of the 10-user base (target = GAAP round-half-up to nearest whole percent; default
= Python round-half-even), e.g. count→percentage→rounded string. Both are external org conventions,
independent (threshold changes the count; rounding changes only the final format), 100% distinguishable.
Emit k0 (control, prompt==latent_spec, 1 interp, empty key_questions), both k1 variants, and the k2_all
variant (4 interps incl. the marked combined-default). If you cannot find a genuinely independent clean
second axis, STOP and flag it in your plan.md rather than forcing an interacting axis.

## Structural invariants to preserve (enforced by build.py + validate.py + tests)
- Per variant deleting S (|S|=k'): `len(key_questions)==k'`, `len(interpretations)==2^k'`, exactly one
  `is_target=True` (I0), exactly one `[combined-default]` marker, 100% distinguishable via executable gold.
- k0 control: empty key_questions, single interpretation, prompt == latent_spec.
- Every non-target interpretation declares `opened_by` (comma-separated axis ids for combinatorial foils).
- Set `regime=` on EVERY FullSpec (H1_external or H2_derivable). No None/untagged reconstructed task.

## Deliverables
1. Rewrite `bench/data_analysis/__init__.py` FullSpecs to the reversed binary-axis combinatorial model
   with `regime` tags; add/replace gold checkers + reference candidates so each interpretation is
   deterministically distinguished; keep the `DataChecker` subprocess harness + cache discipline (PR #7
   infra-error rules) intact.
2. Regenerate `bench/data/data_analysis.jsonl` via `python bench/data_analysis/__init__.py`.
3. Update `tests/test_data_analysis.py` to assert the reversed invariants (mirror
   `tests/test_code_spec.py`: per-variant `len(key_questions)==k'` and `len(interpretations)==2^k'`,
   exactly-one-target, combined-default marker present, regime set, 100% distinguishability). Add a golden
   test pinning I0/default numeric values for the median-skew and org-KPI items.
4. `python -m bench.validate --domain data_analysis` → 100% distinguishable.
5. `python -m pytest -q` → all green (full suite).

## Provenance / process
- Record your model FAMILY in the PR body and in the file header comment (keep `# constructed by: Claude
  (Anthropic) family`). Commit inside the worktree; push `slice/phase1r-data_analysis`. The Manager opens
  the PR, spawns a NON-Claude cross-family audit, routes fixes, and merges after the Law-4 gate
  (build+run + full suite green + cross-family audit 0 BLOCKER/MAJOR). Call out that this is a benchmark
  (science) change prominently in the PR body.
- Self-check gate before marking ready: full pytest green + validate 100% + invariants asserted + fairness
  bar met (a human agrees the full spec genuinely specifies each non-default target).
- Do NOT edit the main checkout. Do NOT touch harness/metrics.py, common/schema.py, or the prereg.

Commit trailer: `Co-authored-by: copilot <copilot@users.noreply.github.com>`.
