# Pre-Registration Amendment 02 — `Task.regime` schema field  (owner-approved 2026-07-15)

> Records a controlled, backward-compatible evolution of the FROZEN `common/schema.py`, owner-signed per
> the freeze policy. **No metric change.** This only IMPLEMENTS STORAGE for the per-task H1/H2 regime tag
> that was ALREADY pre-registered in `paper/preregistration/2026-07-15-prereg.md` §2 (regime criterion)
> and refined in Amendment 01 + `paper/specs/phase1-benchmark-reversal-spec.md`.

## Change
Add one backward-compatible field to the `Task` dataclass:
```python
regime: Optional[str] = None   # "H1_external" | "H2_derivable" | None (excluded/untagged)
```
- **Allowed values (constrained + tested):** exactly `{"H1_external", "H2_derivable", None}`. A validation
  (golden test) rejects any other value so a typo'd regime cannot silently pass (a silent mislabel would be
  a silent failure in our own pipeline — the very thing we study).
- **Backward-compatible:** default `None`; existing code/tests that build `Task` without `regime` are
  unaffected. **JSONL round-trip proven by test:** new records serialize `regime`; OLD records lacking the
  field deserialize to `regime=None` (not asserted-away — tested explicitly).

## What stays frozen / unchanged
- All metric definitions (`convergent_delusion` primary; secondaries) — untouched.
- H1/H2 hypotheses, regime CRITERION (§2), decision rules, robustness nulls, analysis plan.
- Every other `schema.py` structure (`Interpretation`, `AgentRun`) and field.

## Semantics (linked to prereg §2 + Amendment 01)
`regime` is assigned AT CONSTRUCTION by the operational test "disambiguator ABSENT & external → H1_external;
PRESENT in prompt/data → H2_derivable" (cross-family re-derived; disagreement → `None`=excluded). The
**empirical per-regime default-check is the FINAL arbiter** of the tag (behavior must match the tag, else
reclassify/exclude). `None` = excluded/untagged (kept for descriptive stats only).

## Notification to all phases (freeze policy requirement)
- harness/label.py, harness/run.py, harness/metrics.py: unaffected (do not read `regime`).
- bench/*: generators write `regime`; `bench/build.py` load/save round-trips it (backward-compatible).
- analysis/stats (Phase 6): consumes `regime` for the H1/H2 mixed-effects split.
- Phase-2 pipeline + golden tests: unaffected (regime defaults to None where unset).

## Sign-off
Owner approved 2026-07-15 ("Add regime: Optional[str]=None to Task ... Approved") with guardrails:
constrained values + validation test, JSONL round-trip test, documented amendment. Metric frozen.
