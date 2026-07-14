# Phase 1 Reconciliation Plan (fresh Manager restart)

> Re-derived from git ground truth on 2026-07-14. Prior session narrative was STALE and
> is NOT trusted (paper's own Law 1). This file is the single source the Manager writes;
> all code/audit work is delegated to spawned sub-agents in worktrees.

## 1. Ground-truth state table (verified from git, not narrative)

| Item | Branch / PR | Real state (verified) | Notes |
|------|-------------|-----------------------|-------|
| Phase 0 scaffold | PR #1 `slice/phase0-S0-scaffold` | **MERGED** to main (`e58c994`) | `common/`, `tests/`, frozen `schema.py` |
| Orchestrator-only law | main `30ef244` | on main; slices are 1 behind (miss this doc commit) | doc-only |
| Benchmark core (S0) | PR #2 `slice/phase1-S0-core` | **DRAFT**, unmerged | deletion engine + distinguishability validator |
| code_spec (S1) | `slice/phase1-S1-code_spec` @ `fba314d` | **built + fixes ALREADY committed**; clean tree | = S0-core + code_spec (subsumes PR #2) |
| data_analysis (S2) | `slice/phase1-S2-data_analysis` @ `0b21c0f` | **real module**, stacked on S1 head | S1 + `data_analysis/` |
| policy_qa (S3) | `slice/phase1-S3-policy_qa` @ `e5269ac` | **real module**, stacked on S1 head | S1 + `policy_qa/` |

### Topology
`main` → S1(core+code_spec) → { S2 = S1+data_analysis ; S3 = S1+policy_qa }.
S2 and S3 both branch from S1 head `fba314d`, so **both already contain the fixed
code_spec**. Merging S1 into main **subsumes PR #2** (S0-core), which should then be closed.

## 2. Correction to prior narrative (Law 1: verify the real artifact)
The prior brief said the two owner-approved code_spec fixes were "PENDING, not applied."
**Git says otherwise** — commit `c609a92` "per-variant key_questions + fair format domain
(spot-check fixes)" already applied BOTH:
- **(a) key_questions per-variant**: golden invariant test `test_key_questions_invariant`
  present in HEAD, enforcing `len(key_questions) == ambiguity_level == len(interpretations)-1`
  and k=0 control → empty. ✅ applied.
- **(b) format domain**: reworked (NOT dropped) so the TARGET interpretation uses
  round-half-to-even = Python's natural default; axes = rounding / sign / grouping. ✅ applied.

Manager verification (read-only, in S1 worktree): `pytest -q` → **69 passed**;
`bench.validate --domain code_spec` → **21/21 distinguishable (100%)**.
So S1 needs **no fix agent** — only a FRESH cross-family audit, then merge.

## 3. Remaining work to finish Phase 1 (delegated, dependency order)

1. **S1 audit → merge** (in progress):
   - Fresh hostile cross-family audit of code_spec. Author family = Claude (per commits),
     so auditor MUST be a different family (gpt-5). Report-only.
   - If 0 BLOCKER/MAJOR: open PR for S1, merge to main under Law-4 gate. Close PR #2 (S0-core)
     as subsumed. If findings: spawn a fix sub-agent (Claude family), re-audit cross-family.
2. **Fan-out (parallel, independent)** after S1 on main:
   - Rebase S2 (`data_analysis`) and S3 (`policy_qa`) onto merged main (should be conflict-free
     since their code_spec == merged code_spec).
   - Each slice: verify construct → cross-family audit → **STOP** and deliver a 10-task
     spot-check summary to `paper/plans/`. Owner sign-off required (target-is-natural-default
     is a human-judgment gate). Same construction rules as code_spec: deletion-style ambiguity,
     executable gold, per-variant key_questions, invariant test.
3. **Merge each slice** only after Law-4 gate (build+run, full pytest green, cross-family
   audit 0 BLOCKER/MAJOR).

## 4. Final deliverable
`paper/plans/phase1-final-report.md`: what merged, audit trail, spot-check results, and the
format-domain decision (reworked, not dropped). Do NOT start Phase 2 until Phase 1 fully
merged and reported to owner.

## Provenance / laws honored
- Manager = orchestrator only; every code edit via a spawned sub-agent in a worktree.
- implementer family ≠ auditor family (Law 2 / Law 6). Pre-registration intact (Law 7).
- Merge only on Law-4 gate; one clean audit → merge, no endless re-audit (Law 5).
