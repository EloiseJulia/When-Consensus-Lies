# Manager Handoff — 2026-07-15

> For a BRAND-NEW manager session with zero access to the retiring manager's context.
> Re-derive everything from git yourself (Hard Law 1); this doc is a map, not gospel.
> You are ORCHESTRATOR-ONLY: write only under paper/, delegate every code change to a
> spawned sub-agent in a worktree, keep implementer-family ≠ auditor-family.

## 0. TL;DR
- Phase 0 & Phase 1: **DONE, merged to `main`**.
- Phase 2 (harness+metrics): metrics ✅, run ✅, data_analysis flakiness fix ✅ (all merged);
  **label slice is NOT merged, but the structured-answer rework is now COMMITTED** on its branch
  at `df827cd` (see §1, §6) — it needs a FRESH cross-family audit → push → PR → merge. Integration
  test + pre-registration NOT started.

> UPDATE (post-retirement, docs-only): the `impl-p2-label` sub-agent completed AFTER the handoff was
> first written. The label rework is COMMITTED (`df827cd`), not uncommitted. §1 and §f below reflect
> this. Independent verification: full suite **167 passed** (1×, 2026-07-15). Still un-audited since
> the rework and un-merged.
- **PRE-REGISTRATION (H1/H2 + metric lock) is NOT done yet — this is a gating blocker before
  any full-scale run. See §D.**

## 1. Git ground truth (verified 2026-07-15)
- **origin/main HEAD = `97058a3`** (Phase 2-S2c run configs, #8).
- **WARNING: the local `main` CHECKOUT is at `e1b8208` — 4 commits BEHIND origin/main.**
  A successor must `git pull --ff-only origin main` in the main checkout before reasoning
  from it. All Phase 2 merges (#6/#7/#8) are on origin/main but not in the local checkout.
- origin/main recent: `97058a3` run(#8) ← `9bc4341` dataflaky fix(#7) ← `385fbdb` metrics(#6)
  ← `e1b8208` phase2 spec ← `7d8ef24` phase1 docs ← `199933c` policy_qa(#3? see PRs) …
  ← `e58c994` Phase 0(#1).

### PRs
| PR | Title | State |
|----|-------|-------|
| #1 | Phase 0 scaffold | MERGED |
| #2 | Phase 1-S0 core | **CLOSED** (subsumed by #3) |
| #3 | Phase 1-S1 code_spec (+core) | MERGED (`88f3ae7`) |
| #4 | Phase 1-S2 data_analysis | MERGED (`358ee22`) |
| #5 | Phase 1-S3 policy_qa | MERGED (`199933c`) |
| #6 | Phase 2-S2a metrics | MERGED (`385fbdb`) |
| #7 | data_analysis flakiness fix | MERGED (`9bc4341`) |
| #8 | Phase 2-S2c run configs | MERGED (`97058a3`) |
| — | Phase 2-S2b **label** | **NO PR yet; branch unmerged** |

### Un-merged branches / worktrees
- `slice/phase2-S2b-label` @ **`df827cd`** (worktree `.worktrees/phase2-label`) — the structured-answer
  rework is **COMMITTED** (owner contract §C4: policy extraction = JSON amount → `FINAL ANSWER:` marker
  → else I_perp; free-text guessing removed; code_spec/data_analysis labeling unchanged; obsolete
  free-text tests removed). Worktree clean except a stray uncommitted deletion of scratch
  `commit_msg.txt` (harmless; discard). Full suite **167 passed** (independent 1× re-run; agent
  reported 2× green). **NOT pushed, NO PR, NOT audited since the rework.** Successor's first job: run a
  FRESH cross-family (non-Claude, e.g. GPT) audit of the new extraction contract + canonical-reference
  invariant, then push → PR → merge.
- `fix/data_analysis-harness-flaky` @ `821bcc2` (worktree `.worktrees/phase2-dataflaky`) — already
  MERGED as #7 (squash). Branch/worktree are leftover; safe to prune.
- Phase 1 slice branches/worktrees (`phase1-*`) — all merged; leftover; safe to prune.
- `slice/phase1-S0-core`, `topic/phase1-benchmark` — obsolete; safe to prune.
- No other uncommitted work outside the label worktree.

## a. STATE by phase
- **Phase 0 (scaffold)** — DONE. `common/` (schema.py FROZEN, config.yaml, llm.py offline mock,
  config.py), `tests/`, local CI. PR #1 `e58c994`. Report: paper/plans/phase0-scaffold-report.md.
- **Phase 1 (benchmark, 3 domains)** — DONE, merged.
  - code_spec: PR #3 `88f3ae7` (subsumes core). 5-round harness hardening. 21/21 distinguishable.
  - data_analysis: PR #4 `358ee22`. 10/10 distinguishable.
  - policy_qa: PR #5 `199933c`. 20/20 distinguishable.
  - Report: paper/plans/phase1-final-report.md (+ per-domain reports, reconcile, spot-check gate).
- **Phase 2 (harness + metrics)** — IN PROGRESS.
  - metrics (S2a): DONE, PR #6 `385fbdb`. convergent_delusion + marginal_rho + a_maj + ece +
    confidence_accuracy_slope. Golden tests hand-calculated.
  - run (S2c): DONE, PR #8 `97058a3`. 6 configs: single / sc(k=5,10) / homogeneous-MAD /
    heterogeneous-MAD / verifier / interpretation-diverse. Extended `common/llm.py` mock hash to
    include family|model (SHARED-INFRA change, called out & audited).
  - data_analysis flakiness fix: DONE, PR #7 `9bc4341` (see §G).
  - **label (S2b): IN-FLIGHT, unmerged.** Executable-signal labeling reusing domain gold checkers.
    Passed most of a cross-family audit but the policy numeric extraction went through several
    BLOCKER rounds; owner then chose a **structured-answer contract** (see §C). That rework was
    being implemented when the manager was retired — **uncommitted in the worktree**.
  - **integration test + PRE-REGISTRATION (S2d): NOT STARTED.**
- **Phase 3+ (detector, rep-analysis, sim-users, stats, writing)** — NOT STARTED.
- **Current authoritative HEAD: origin/main `97058a3`.**

## b. Provenance config (common/config.yaml) — cross-family invariant
Roles (EXPERIMENTAL routing, for the actual paper runs):
- constructor: **google** (gemini-1.5-pro)
- tested_agents: homogeneous **[anthropic]**; heterogeneous **[openai, anthropic, qwen, deepseek]**;
  reasoning [openai o3-mini, deepseek-reasoner]
- judge: **openai** (only if executable gold unavailable)
- code_reviewer: **deepseek** (default; Manager overrides per slice so auditor ≠ implementer)

CODE-CONSTRUCTION provenance actually used this session (implementer-family vs auditor-family —
cross-family held for EVERY audited slice):
| Slice | Implementer | Auditor | Result |
|-------|-------------|---------|--------|
| Phase 0 scaffold | anthropic | openai | clean (4-round) |
| P1 code_spec | Claude | GPT (gpt-5.5/5.6) | clean after 5 rounds |
| P1 data_analysis | Claude | GPT | clean after fixes |
| P1 policy_qa | Claude | GPT | clean after fixes + refund rework |
| P2 metrics | Claude | GPT | clean, 0 findings |
| P2 run | Claude | GPT | clean after 5 findings fixed |
| data_analysis flakiness | Claude | GPT | clean, 0 BLOCKER/MAJOR |
| P2 label | Claude | GPT | **in-flight** (structured-answer rework pending re-audit) |
Invariant HELD: implementer (Claude) ≠ auditor (GPT) on every slice. NOTE the distinction:
config.yaml routing is for the *experiment*; the *code* was built Claude / audited GPT. Both
preserve cross-family separation. A successor spawning fix agents on the label branch must keep
the next label auditor a NON-Claude family.

## c. Human sign-off decisions (owner rulings)
1. **code_spec key_questions per-variant invariant** — key_questions == exactly the deleted axes;
   k0 control empty; invariant len(key_questions)==ambiguity_level==len(interpretations)-1.
   Implemented + golden test `test_key_questions_invariant` in bench/code_spec + tests/test_code_spec.py
   (merged in #3). VERIFIED asserting EXACT question identity, not just counts.
2. **format domain** — **REWORKED, not dropped.** Target rounding = round-half-to-even (Python's
   natural default); axes = rounding / sign / grouping. In bench/code_spec (#3).
3. **policy_refund target** — **REWORKED** to clear natural-default axes (restocking fee on original
   price + nearest-cent rounding; target $343.95), replacing the convention-ambiguous 365-day
   proration. Re-audited natural-default YES. In bench/policy_qa (#5).
4. **policy_qa labeling answer-format contract** — owner ruled (2026-07-15): tested agents MUST emit
   a STRUCTURED final answer (JSON {"amount": N} or `FINAL ANSWER: $<amount>`); the labeler extracts
   ONLY that; genuinely unparseable/ambiguous free-text → **I_perp** (never guess via first/last-number
   heuristics). **THIS IS THE IN-FLIGHT REWORK (§C label) — not yet committed/merged.** Also implies a
   PROMPT-SIDE change: run.py / the policy prompt must INSTRUCT agents to emit that structured answer
   (todo `p2-answerfmt-prompt`, NOT done). This contract must be PRE-REGISTERED.
5. **code_spec sandbox threat model** — the executable-gold harness GUARANTEES no forged verdicts, no
   incidental gold leakage, no cross-test contamination, tree-kill on timeout; it is explicitly NOT a
   security sandbox vs deliberately malicious candidate code (which can open() the gold by derived abs
   path). Candidates are cooperative LLM solutions. Cheap hardening applied (bootstrap-in-sandbox so
   argv[0]/__main__ don't leak repo path; -S -E -B; scrubbed env). OS-level sandbox = FUTURE WORK.
   Documented in bench/code_spec/_runner.py + bench/DOMAIN_API.md. This standard was applied to the
   data_analysis harness too.

## d. PRE-REGISTRATION STATUS  ⚠️ CRITICAL — NOT DONE
- **There is NO committed H1/H2 + metric-definition pre-registration document.** The grep hits for
  "H1/H2/pre-regist" are only incidental mentions in AGENTS.md/plan/specs, NOT an actual frozen
  pre-registration artifact.
- **LOCKED so far (de facto, via merged code + owner rulings):** primary metric =
  convergent_delusion (harness/metrics.py, golden tests); metric definitions for marginal_rho,
  a_maj, ece, confidence_accuracy_slope; the benchmark construction rules; the policy_qa answer
  contract (pending merge).
- **STILL OPEN / must be pre-registered BEFORE any full-scale run (Hard Law 7):** the exact H1 and
  H2 hypothesis statements, the primary + secondary metric definitions as a frozen doc, and the
  predicted ρ–ambiguity crossover / phase-diagram expectation. Per AI-Execution-Plan.md §5.5/§7 and
  Phase 6, the owner must git-commit H1/H2 + metric defs + phase-diagram prediction, after which
  metric definitions must NEVER change. **This is a hard gate: do NOT launch the big experimental
  runs until this is committed and owner-signed.** Suggested location: paper/preregistration/.

## e. Primary metric — implementation status
- harness/metrics.py (origin/main): `false_consensus_rate` (alias `convergent_delusion`) = fraction of
  agents on the single MODAL WRONG label = PRIMARY. Module docstring explicitly says convergent_delusion
  is PRIMARY and binary ρ / marginal_rho is NOT primary. **NOT silently degraded to binary ρ.**
- Secondary: `marginal_rho` (mean pairwise error correlation; bridge to prior lit), `a_maj`
  (order-independent strict-plurality majority accuracy), `ece`, `confidence_accuracy_slope`
  (OLS slope of correctness on confidence; zero-variance → 0.0).
- Golden tests: tests/test_metrics_golden.py + tests/test_marginal_rho.py — hand-calculated constants
  (convergent 1.0 / scattered 0.4 / partial 0.6; slope 2.0; ece 0.4; a_maj ties → 0.0). Cross-family
  audited (independent recomputation), 0 findings.

## f. Open threads / ordered next steps (with deps)
1. **[FIRST] Finish the label slice.** The structured-answer rework is COMMITTED at `df827cd` on
   `slice/phase2-S2b-label` (worktree `.worktrees/phase2-label`), full suite 167 passed, but it is
   NOT pushed, has NO PR, and has NOT been audited since the rework. Run a FRESH cross-family
   (non-Claude) audit of harness/label.py's structured extraction contract + the canonical-reference
   invariant (all 3 domains). If clean → push, PR, merge. If findings → spawn a Claude fix sub-agent,
   re-audit cross-family. (Blocks integration.) Also discard the stray `commit_msg.txt` deletion.
2. **[dep:1] Policy prompt structured-answer instruction** (todo `p2-answerfmt-prompt`): a sub-agent
   must make run.py / the policy prompt instruct agents to end with `FINAL ANSWER: $<amount>` or JSON
   {"amount": N}, matching the labeler contract. Then re-run run/label integration.
3. **[dep:1,2] Phase 2 integration test (S2d):** real end-to-end run→label→metrics over a few tasks
   per domain (offline mock), asserting a valid convergent-delusion number (not the mock hash path).
   Replace/extend tests/test_smoke_pipeline.py.
4. **[dep:3] PRE-REGISTRATION (owner-gated, §D):** commit H1/H2 + frozen metric defs + phase-diagram
   prediction to paper/preregistration/ BEFORE any scale-up. Manager cannot self-approve; owner signs.
5. **[dep:4] Phase 5 sim-users** (0→2→5→6 serial chain) then **Phase 6 stats+figures**; **Phase 3
   detector** can start once interfaces are set; **Phase 4 rep-analysis** needs GPU (defer-able to v2).
6. Housekeeping: `git pull --ff-only` the local main checkout; prune merged worktrees/branches.

Session todo DB (SQLite `todos`): 19 done, 3 in-progress (p2-label, audit-p2-label, fix threads),
2 pending (p2-integration, p2-answerfmt-prompt). This DB does NOT survive the session; treat this
handoff + git as the source of truth.

## g. Known limitations / documented boundaries
- **Harness is not an adversarial security sandbox** (§C5): cooperative-candidate threat model; OS
  sandbox = future work.
- **data_analysis harness flakiness fix (§ merged #7):** root cause was a candidate worker reading its
  input temp-file empty → "bad input" INFRA error that check() wrongly cached as a candidate FAIL,
  cascading 8–25 failures/run. Fix: classify ONLY genuine infra errors (bad input/bad job/spawn-failed/
  supervisor-timeout/verdict-None) as retryable (≤3, raise loudly if persistent); NEVER cache infra
  errors — only deterministic pass/fail; flush+fsync temp files; per-test cache-clearing fixture; real
  50-iter stress test. LESSON: verify subprocess harnesses with REPEATED runs (a single audit run can
  pass flaky code). Stored as a repository memory.
- **policy_qa labeling depends on the structured-answer contract** (§C4): free-text numeric extraction
  was provably unreliable (final amount may be first or last); the contract + I_perp-on-unparseable is
  the accepted, pre-registerable design.
- **Environment:** running many subprocess-heavy tests can leak runaway python processes (infinite-loop
  candidates); a successor may need to reap them (Stop-Process -Id) if `python -c` latency balloons.
  ~39 were reaped this session. Windows-only paths; use backslash paths.

## h. Lessons / cost for the successor
- **Delegation churn was the biggest cost sink.** The label numeric-extraction and data_analysis
  flakiness each took 3–5 sub-agent rounds. When an agent repeatedly rationalizes ("pre-existing",
  "environment issue", residual flakiness), STOP re-prompting the same session — read the code
  yourself to root-cause (Manager may READ), then give the fix agent an EXACT, narrow diagnosis, or
  start a FRESH agent from a clean base. Over-directing a tiring session (e.g. the stdout-channel
  redesign that was already present) backfired.
- **Trust git, not agent self-reports.** Multiple "all green" reports were wrong on independent
  re-run (stale install, cached results, flaky subprocess). Always independently verify: fresh
  `pip install -e .`, run the FULL suite, and for subprocess harnesses run it 3–6× consecutively.
- **Keep manager context lean:** delegate, don't read large files wholesale; this session bloated by
  reading long agent transcripts. Prefer targeted grep/view and the todo DB.
- **A single audit run can pass flaky code** — require repeated-run verification for any subprocess/
  executable-gold change.

## i. Source-of-truth pointers
- **Method/laws:** AGENTS.md (root; hard laws, orchestrator-only, phase order),
  AI-Native-Workflow-可复用模板.md (HOW), AI-Execution-Plan.md (WHAT; §5 verification is most important).
- **Frozen interface:** common/schema.py (FROZEN — changes need owner sign-off).
- **Provenance routing:** common/config.yaml.
- **Primary metric + golden tests:** harness/metrics.py, tests/test_metrics_golden.py,
  tests/test_marginal_rho.py.
- **Harness:** harness/run.py (6 configs), harness/label.py (executable-signal labeling — IN-FLIGHT
  rework in worktree), bench/<domain>/ (hardened gold runners), bench/DOMAIN_API.md.
- **Specs (authoritative WHAT per phase):** paper/specs/phase0-scaffold.md, phase1-benchmark.md,
  phase2-harness-metrics.md.
- **Plans/reports:** paper/plans/phase1-final-report.md, phase1-reconcile.md, phase1-spotcheck-gate.md,
  phase0-scaffold-report.md, and per-domain phase1-*-report.md.
- **This handoff:** paper/handoff/2026-07-15-manager-handoff.md.

## Report currency check
- paper/plans/phase1-final-report.md, phase1-reconcile.md, phase1-spotcheck-gate.md: **CURRENT** for
  Phase 1 (accurately reflect merged code_spec/data_analysis/policy_qa incl. refund rework + threat model).
- paper/specs/phase2-harness-metrics.md: **CURRENT as the slice plan**, but predates (a) the owner
  structured-answer contract for policy_qa labeling and (b) the data_analysis flakiness fix. Treat this
  handoff §C4/§D/§G as the authoritative deltas over that spec.
- **GAPS (no report yet, by design — Phase 2 not finished):** no Phase 2 final report; no
  pre-registration doc; no integration report. A successor should produce these as Phase 2 closes.
