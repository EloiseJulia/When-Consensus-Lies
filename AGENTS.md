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

## Hard laws (never violate; escalate on conflict)
1. Verify the real artifact (build + run), not just green tests.
2. Independent adversarial audit > self-review. NEVER let the model that wrote code approve its own code.
3. Parallelize only INDEPENDENT slices; dependency chains run SEQUENTIALLY.
4. Shared infra / `schema.py` / `config.yaml` changes: flag for the owner, NEVER self-merge.
5. Know when to stop (one clean audit with 0 new issues → deliver).
6. **Provenance separation**: `constructor ≠ tested ≠ judge ≠ code_reviewer` must be different model families. Every AI-written code / AI label / AI conclusion needs verification NOT from the same AI (deterministic test > cross-family review > human spot-check).
7. **Executable gold + pre-registration**: prefer executable gold (unit test / deterministic value) over LLM-judge. Primary metric = convergent-delusion (consensus on the SAME wrong I_k), NOT binary ρ. Write the golden metric unit test first; git-commit H1/H2 + metric defs before any full-scale run; never change metric definitions afterward.

## Roles & guardrails
- **You (human)**: only mandatory trigger; final judge; the only one who marks PR ready / merges.
- **Manager**: dependency analysis FIRST; writes spec + per-slice plans; owns git/topic; spawns sub-agents; NEVER touches main checkout; NEVER merges to `main`; delivers to human.
- **Sub-agent (implement)**: works only in its own worktree; spec→plan→execute; records its model family in the PR body; self-check gate before ready.
- **Audit agent**: fresh session, no context, hostile; MUST use a model family ≠ the code author's; report-only, never fix/merge.
- **Research agent**: doc-only; outputs to `RESEARCH_DIR`; no code.

## Do NOT touch the main checkout
Agents only `git worktree add` and read-only inspect. Never checkout commits in the main checkout (detached HEAD). PR-first but never merge; ready/merge is a human action.

## Phase order (from AI-Execution-Plan.md)
Phase 0 scaffold `common/`+`tests/` (blocks all; human freezes `schema.py`) → Phase 1 benchmark (code⟂data⟂policy, parallel) → Phase 2 harness+metrics (serial) → Phase 3 detector → Phase 4 rep-analysis (GPU, defer-able) → Phase 5 sim-users → Phase 6 stats+figures → Phase 7 writing. Chain 0→2→5→6 is serial; slices inside Phase 1 and Phase 4 are parallel.
