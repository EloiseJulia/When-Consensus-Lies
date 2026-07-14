# Phase 1 Final Report — Benchmark Construction (code_spec, data_analysis, policy_qa)

**Status: COMPLETE.** All three Phase 1 benchmark domains are merged to `main` and verified
on the real merged artifact. Phase 2 NOT started (awaiting owner go-ahead).

Manager: orchestrator-only (wrote no source code; every code change via a spawned sub-agent
in a worktree; cross-family provenance separation maintained throughout).

## 1. What merged (git ground truth)

| main commit | Slice | Content |
|---|---|---|
| `88f3ae7` | Phase 1-S1 (PR #3) | benchmark core framework + `code_spec` domain — **subsumes PR #2 (S0-core)** |
| `358ee22` | Phase 1-S2 (PR #4) | `data_analysis` domain |
| `199933c` | Phase 1-S3 (PR #5) | `policy_qa` domain |

- PR #2 (`slice/phase1-S0-core`) **closed as subsumed** by PR #3.
- Final `main` verification: **`pytest -q` → 120 passed**; distinguishability
  code_spec **21/21**, data_analysis **10/10**, policy_qa **20/20** (all 100%).

## 2. Correction to the starting narrative (Law 1)
The session-start brief said the two code_spec fixes were "pending / not applied." **Git proved
they were already committed** (`c609a92`): per-variant `key_questions` + golden invariant test,
and the `format` domain **reworked** (target rounding = round-half-to-even, Python's natural
default) rather than dropped. Re-derived state from git; did not trust prior narrative.

## 3. Audit trail (cross-family: Claude constructor ⟂ GPT auditor)

### S1 code_spec — 5 fix/audit rounds (deep harness hardening)
The candidate-execution harness was hardened against progressively subtler attacks, each found
by a fresh hostile GPT audit running real PoCs and fixed by a Claude sub-agent:
1. R1 audit: verdict forgery (candidate-writable verdict file/stdout), sort task modeled 2 axes
   as 1, timeout didn't kill descendants, golden test checked counts not identity.
2. R2: 3-level isolation (candidate never sees gold/verdict path), per-test worker, tree-kill.
3. R3: pipe-based verdict (removed shared temp verdict file → sentinel over supervisor stdout).
4. R4: gold-import block (`import bench.code_spec` → run worker with `-S -E -B`, scrubbed env,
   sandbox cwd).
5. R5: cheap hardening (bootstrap script in sandbox so `argv[0]`/`__main__` don't leak repo
   path) + documented threat model.
Final: **0 in-scope BLOCKER/MAJOR**, 79 tests. See §4 for the threat-model decision.

### S2 data_analysis — 2 rounds
R1 audit found the SAME harness class of holes (verdict forgery, gold in candidate frame,
cross-test state contamination across a shared namespace, timeout descendants, golden-test).
Fix ported the hardened code_spec harness (supervisor/worker split, `__DATA_ANALYSIS_VERDICT__`
stdout sentinel, one fresh worker per test, tree-kill, `-S` sandbox) + 11 attack regression
tests. Scratch files (`verify_fixes.py`, `DELIVERY_REPORT.md`) removed before merge.
R2 re-audit: **0 findings**, 111 tests, 10/10 distinguishable.

### S3 policy_qa — 2 rounds + owner-directed rework
policy_qa uses deterministic structured checkers (no candidate code execution → no harness
attack surface). R1 audit: **BLOCKER** — checker accepted adjacent-cent wrong answers
(`abs(cand-exp) > 0.01` passed 949.99 for 950.00); **MAJOR** — golden test checked counts not
identity. Fix: exact integer-cent comparison + 20-task exact `key_questions` golden mapping.
R2 re-audit: **0 findings**. Owner spot-check flagged `policy_refund` as DOUBTFUL → owner chose
REWORK → refund rebuilt with clear natural-default axes (fee-basis on original price; nearest-cent
rounding); R3 re-audit judged both axes natural-default **YES**, 0 findings, 20/20 distinguishable.

## 4. Format-domain & threat-model decisions
- **code_spec `format` domain:** kept but REWORKED so the target is a genuine natural default
  (round-half-to-even = Python's default), not dropped. Axes = rounding / sign / grouping.
- **Harness threat model (owner-approved):** the executable-gold harness GUARANTEES no forged
  verdicts, no incidental gold leakage (gold never in the candidate's process), and no cross-test
  contamination, and it kills the candidate process tree on timeout. It is explicitly **NOT a
  security sandbox** against deliberately malicious candidate code that derives an absolute path
  and `open()`s the gold file. Candidates in this study are cooperative LLM spec-solutions, not
  adversaries. **OS-level sandboxing (container / restricted user with the repo unreadable) is
  noted as FUTURE WORK.** Documented in `bench/code_spec/_runner.py` and `bench/DOMAIN_API.md`.

## 5. Spot-check gates (owner sign-off)
- **data_analysis:** all 10 tasks natural-default YES → owner APPROVED → merged.
- **policy_qa:** 9/10 YES; `policy_refund` DOUBTFUL → owner chose REWORK → reworked, re-audited
  YES → merged.
Detail: `paper/plans/phase1-spotcheck-gate.md`.

## 6. Laws honored
Orchestrator-only delegation (Manager wrote only files under `paper/plans/`); provenance
separation (Claude implementer ⟂ GPT auditor) on every slice; executable gold + pre-registered
per-variant `key_questions` invariant with golden identity tests; merge only after full artifact
build+run, full pytest green, and a cross-family audit with 0 in-scope BLOCKER/MAJOR (Law 4);
one clean audit → merge (Law 5).

## 7. Next
Phase 1 is complete and merged. **Do NOT start Phase 2 until owner go-ahead.** Per the execution
plan, next is Phase 2 (harness + metrics, serial), building on the frozen `common/schema.py`.
Worktree branches (`slice/phase1-S1..S3`) remain for reference; can be pruned on request.
