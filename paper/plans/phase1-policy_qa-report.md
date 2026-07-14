# Phase 1 · Slice S3 · `policy_qa` — Delivery Report

**Branch:** `slice/phase1-S3-policy_qa`
**Constructor / fixer:** Claude (Anthropic) family · **Auditor:** GPT (OpenAI) family — provenance separation (hard law 6) satisfied.
**Status:** Cross-family re-audit **YES / 0 BLOCKER / 0 MAJOR**. Awaiting **human spot-check gate** (10 tasks). NOT merged.

## What this domain is
Convention-based numeric policy questions (overtime pay / loan interest / restaurant tip / subscription refund /
stacked discount). Every answer is a structured `{"amount": <float>}`; the checker compares values with a 0.01 float
tolerance and rejects bool-as-number / type-mismatch / wrong-keys. **Deterministic, no LLM, no subprocess** (candidates
are answer values, not code).

Each ambiguity axis is a competing real-world **convention** with a standard default that SURVIVES clause deletion
(the fairness trap that sank v1 and code_spec's `format`). Deleting the clause that pins a convention opens a genuine
alternative reading, changing the numeric answer.

- 5 base problems, each with **2 axes** → 20 tasks, distribution `{0:5, 1:10, 2:5}` (k=0 controls, 10 single-axis k=1,
  5 both-axes k=2). Covers k up to 2.
- `python -m bench.validate --domain policy_qa` → **20/20 (100%) distinguishable**.
- `python -m pytest tests/test_policy_qa.py -q` → **9 passed**.
- key_questions invariant holds for all tasks: `len(key_questions) == ambiguity_level == len(interpretations) - 1`;
  k=0 controls have `[]`; each question maps to its deleted axis.
- Min pairwise amount gap across all triplets: **0.10** (10× the 0.01 checker tolerance) → no interpretation can be
  mis-scored.

## Axes (TARGET = standard convention default; alternative = real competing convention)
| Problem | Axis | TARGET | Alternative(s) |
| --- | --- | --- | --- |
| overtime | threshold | 40h → $950 | 44h → $910 |
| overtime | rate | 1.5× → $950 | 2× → $1000 |
| interest | day-count | 365-day → $147.95 | 360-day → $150.00 |
| interest | compounding | simple → $147.95 | daily-compound → $149.03 |
| tip | base | pre-tax → $7.50 | on-total → $8.10 |
| tip | rounding | to-cent → $7.50 | up-to-dollar → $8.00 |
| refund | year-basis | 365-day → $271.23 | 360-day → $270.00 |
| refund | cancel-day | day-90 used → $271.23 | day-90 unused → $272.22 |
| discount | stacking | sequential → $74.80 | additive → $73.00 |
| discount | rounding | to-cent → $74.80 | up-to-dollar → $75.00 |

## Audit history (PASS/FAIL)
| Round | Auditor (family) | Verdict | Findings |
| --- | --- | --- | --- |
| 1 | GPT `gpt-5.4` | **NO** | 1 BLOCKER + 2 MAJOR + 1 MINOR |
| 2 (re-audit) | GPT `gpt-5.4` | **YES** | 0 BLOCKER/MAJOR; 1 new MINOR (fixed) |

### Round-1 findings and fixes (all were Manager design flaws, transcribed faithfully)
- **[BLOCKER] tip & discount rounding axes contradicted by the core prompt.** The cores said "nearest cent", pinning
  the very axis being deleted, so the round-to-dollar reading was never truly opened. → Removed "nearest cent" from the
  tip and discount cores; rounding is now genuinely unresolved when its clause is deleted.
- **[MAJOR] interest compounding inconsistent with the surviving day-rate clause.** The non-target used monthly
  compounding while the surviving clause specified a 365-day daily rate. → Changed the compound reading to **daily**
  compounding: `10000·((1+0.06/365)^90 − 1) = 149.03`, consistent with the 365-day clause and distinct from 147.95/150.00.
- **[MAJOR] refund endpoint pinned at "90 days elapsed."** That phrasing blocked the 89-used reading, killing the
  cancel-day ambiguity. → Reworded to "cancels on day 90 after activation" so inclusive (90 used → 271.23) vs exclusive
  (89 used → 272.22) is a real convention conflict.
- **[MINOR] no prompt-consistency guard tests.** → Added `test_deleted_clause_absent_from_prompt` and
  `test_rounding_axis_not_pinned_in_core`; broadened the foils check to all tasks.

### Round-2 finding and fix
- **[MINOR] internal "0.75 min-gap" claim was false** for the k=2 tip/discount triplets (actual min gaps 0.10 / 0.20).
  Still 10–20× the 0.01 checker tolerance, so validate is 20/20 and scoring is unaffected. → Corrected the claim and
  strengthened `test_amounts_pairwise_distinct` from a 0.01 floor to a documented **0.05 (5× tolerance) safety floor**.

## Commits
- `50f2543` initial implementation (convention-based numeric rebuild)
- `146caff` remove scratch verify_step4.py
- `a3c1e54` fix round-1 audit findings (rounding cores, daily compound, refund wording, guard tests)
- `f5df9c2` fix round-2 MINOR (strengthen pairwise-distinctness test floor)

## Human spot-check
See `files/policy_qa-SPOTCHECK.md` (session artifact) — the 10 single-axis (k1) tasks with prompt, key_question, target,
and competing amounts, plus k0-control and k2-combination appendices. **Merge is gated on your per-task approval.**
