# Spec — Phase 1: Benchmark MVP (Direction A)

> AI-Execution-Plan.md §4 Phase 1. Three domains. **MVP first: ~50 tasks/domain, then STOP for human spot-check of 10** (hard checkpoint — "这一步不过后面全是沙上建塔").

## Objective
Produce a benchmark of underdetermined tasks with **deletion-based ambiguity** and **executable gold**, for 3 domains (`code_spec`, `data_analysis`, `policy_qa`), each ~50 tasks conforming to `common.schema.Task`.

## Non-goals
- No agent runs / metrics (Phase 2). No detector (Phase 3).
- No full 100–150 set yet — MVP is ~50/domain for the human gate.
- No LLM-judge anywhere in gold. policy_qa gold is deliberately WEAKENED (rubric), not executable.
- Do NOT merge to `main` — deliver for human spot-check first.

## Provenance (HARD LAW 6) — four distinct families
- **constructor = google/Gemini**: authors the full human-style seed specs (natural-language). MUST NOT be a tested family (tested pool = openai/anthropic/qwen/deepseek) → kills the "ρ is a constructor artifact" objection.
- **implementer = anthropic/Claude**: writes the generation/gold framework CODE.
- **auditor = openai/GPT**: hostile audit (≠ implementer).
- Record each family in the PR body.

## Design
### Deletion-based ambiguity (structural, model-agnostic)
1. constructor writes a COMPLETE spec (all requirement classes present) = `latent_spec`.
2. `bench/build.py` deletes k requirement classes → `prompt` (underdetermined). k=1/2/3 → `ambiguity_level` 1/2/3.
3. Each deleted requirement class opens a branch of valid interpretations `I_1..I_m`; `I0` = the full-spec target; `I_perp` = degenerate.
4. `key_questions` = the clarifying questions that would recover the deleted requirement(s).

### Executable gold (the crux)
- **code_spec**: each interpretation ships a pytest checker. For a candidate implementation, exactly ONE interpretation's checker passes → deterministic label. Checkers must be MUTUALLY DISTINGUISHING (a reference solution for I_k passes I_k's checker and fails the others).
- **data_analysis**: each interpretation → a deterministic numeric / DataFrame assertion (e.g. exact aggregate under that interpretation).
- **policy_qa**: WEAKENED — rubric dict (keyword/structure criteria), explicitly flagged non-executable; kept small so it doesn't dilute rigor.

### Repo layout (under `bench/`)
```
bench/
  build.py            # deletion engine + Task assembly + validation
  gold/
    base.py           # GoldChecker interface: check(candidate)->bool
    code_spec/        # per-task pytest checkers
    data_analysis/    # per-task numeric checkers
    policy_qa/        # rubric dicts
  templates/<domain>/ # constructor-authored seed full-specs (jsonl or md)
  data/<domain>.jsonl # generated Task records (~50 each)
  validate.py         # loads data/*.jsonl, asserts every interpretation is
                      # deterministically distinguished by its gold checker
```

## Acceptance Criteria
1. `bench/data/<domain>.jsonl` exists for all 3 domains, ~50 tasks each, each parseable into `schema.Task`.
2. Every task: ≥2 interpretations incl. exactly one `is_target=True` (I0) + optional `I_perp`; `ambiguity_level ∈ {1,2,3}`; non-empty `key_questions`; `latent_spec` strictly more-specified than `prompt`.
3. **Executable-gold distinguishability test (code+data)**: for each task, a provided per-interpretation reference candidate makes ONLY that interpretation's checker pass (unique deterministic label). Run in CI, all green.
4. policy_qa: rubric present + a test asserting it is marked non-executable (so no one mistakes it for hard gold).
5. `python -m pytest bench` green; a `bench/validate.py --domain X` prints a summary (task count, ambiguity distribution, distinguishability = 100%).
6. constructor family (google) recorded and ≠ any tested family.

## Slice Plan (dependency-aware)
- **S1-core (SERIAL, first)**: `build.py` deletion engine + `gold/base.py` interface + `validate.py` + core tests. Blocks the domains.
- **S1a code_spec ⟂ S1b data_analysis ⟂ S1c policy_qa (PARALLEL)**: each authors templates (Gemini) + gold checkers (Claude) + generates ~50 tasks + per-domain distinguishability tests.
- **Audit** each slice cross-family (GPT). Fix. Then **STOP and deliver** 10 sampled tasks/domain for human spot-check. NO merge.
