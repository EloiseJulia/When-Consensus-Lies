# AGENTS.md — When Consensus Lies

> Copilot CLI auto-loads this file for every session. It is the enforced contract.
> Full method: [AI-Native-Workflow-可复用模板.md](AI-Native-Workflow-可复用模板.md) (HOW).
> Full plan: [AI-Execution-Plan.md](AI-Execution-Plan.md) (WHAT). Read both before acting.

## Project constants
- REPO: `When-Consensus-Lies` · OWNER: `EloiseJulia` · DEFAULT_BRANCH: `main`
- REPO_PATH: `C:\Users\v-elzhang\Desktop\MyFolder\When Consensus Lies`
- WORKTREE_ROOT: `<REPO_PATH>/.worktrees`
- SPEC_DIR: `paper/specs/` · PLAN_DIR: `paper/plans/` · RESEARCH_DIR: `paper/research/`
- COMMIT_TRAILER: `Co-authored-by: copilot <copilot@users.noreply.github.com>`
- TEST_CMD: `pytest` · BUILD_CMD: `pip install -e . && python -c "import common"`

## Autonomy mode
Fully autonomous: the Manager runs everything (research, implement, audit, fix, merge)
by spawning sub-agents. No human gate is required to merge. The human reviews
asynchronously via delivered reports + git history. This RELAXES the human-merge
gate ONLY; the scientific laws (6, 7) and cross-family audit (2) are STILL inviolable.

## Hard laws (never violate)
1. Verify the real artifact (build + run), not just green tests.
2. Independent adversarial audit > self-review. NEVER let the model that wrote code approve or audit its own code — the audit sub-agent MUST use a different model family than the implementer.
3. Parallelize only INDEPENDENT slices; dependency chains run SEQUENTIALLY.
4. A PR may be auto-merged to `main` by the Manager ONLY after: full artifact build+run passes, full test suite green, and a cross-family audit returns 0 BLOCKER/MAJOR findings. Shared infra / `schema.py` / `config.yaml` changes must be called out prominently in the PR body before merge.
5. Know when to stop (one clean audit with 0 new issues → merge and move on; do not re-audit endlessly).
6. **Provenance separation (inviolable)**: `constructor ≠ tested ≠ judge ≠ code_reviewer` must be different model families. Every AI-written code / AI label / AI conclusion needs verification NOT from the same AI (deterministic test > cross-family review).
7. **Executable gold + pre-registration (inviolable)**: prefer executable gold (unit test / deterministic value) over LLM-judge. Primary metric = convergent-delusion (consensus on the SAME wrong I_k), NOT binary ρ. Write the golden metric unit test first; git-commit H1/H2 + metric defs before any full-scale run; never change metric definitions afterward.

## Roles & guardrails
- **You (human)**: triggers the Manager once; reviews asynchronously via reports/git history.
- **Manager**: dependency analysis FIRST; writes spec + per-slice plans; owns git/topic; spawns all sub-agents; drives the full lifecycle incl. audit and merge; NEVER edits the main checkout directly (works via worktrees); records a delivery report per phase.
- **Sub-agent (implement)**: works only in its own worktree; spec→plan→execute; records its model family in the PR body; self-check gate before ready.
- **Audit agent**: fresh session, no context, hostile; MUST use a model family ≠ the code author's; report-only, never fix/merge (the Manager applies fixes and re-audits).
- **Research agent**: doc-only; outputs to `RESEARCH_DIR`; no code.

## Do NOT edit the main checkout directly
Agents only `git worktree add` and read-only inspect the main checkout. Never checkout commits in the main checkout (detached HEAD). PR-first; the Manager merges only after the law-4 gate passes.

## Phase order (from AI-Execution-Plan.md)
Phase 0 scaffold `common/`+`tests/` (blocks all; human freezes `schema.py`) → Phase 1 benchmark (code⟂data⟂policy, parallel) → Phase 2 harness+metrics (serial) → Phase 3 detector → Phase 4 rep-analysis (GPU, defer-able) → Phase 5 sim-users → Phase 6 stats+figures → Phase 7 writing. Chain 0→2→5→6 is serial; slices inside Phase 1 and Phase 4 are parallel.
