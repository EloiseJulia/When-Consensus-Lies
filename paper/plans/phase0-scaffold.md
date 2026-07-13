# Plan — Phase 0 slice S0 (scaffold)

Worktree: `.worktrees/phase0-scaffold` · Branch: `slice/phase0-S0-scaffold` · Base: `main` · Draft PR.
Implementer model family: **Anthropic (Claude)** — recorded here + in PR body for cross-family audit.
Auditor model family: **OpenAI (GPT)** — must differ from implementer (HARD LAW 6).

## Data flow (mock end-to-end)
```
Task(mock) ──run_task(config, LLMClient offline)──▶ [AgentRun ×k]
          ──label_run(executable signal)──────────▶ labels ∈ {I0,I1,...,I_perp}
          ──metrics.false_consensus_rate(labels)──▶ convergent-delusion value
```

## Step checklist
1. `pyproject.toml` (setuptools, py>=3.10), dev deps: pytest, pyyaml. Packages: common, bench, harness, detector, sim_users, analysis.
2. `common/schema.py` — dataclasses exactly per spec (incl. `seed` on AgentRun). Add module docstring: "FROZEN after Phase 0 — changes require owner sign-off."
3. `common/config.yaml` — role routing per AI-Execution-Plan §2; `seeds.global: 20260713`.
4. `common/config.py` — `load_config()`, `model_for_role(role)`, `assert_provenance_separation()` (constructor/tested/judge/code_reviewer families pairwise distinct).
5. `common/llm.py` — `LLMClient` offline mock (deterministic hash(role,prompt,seed)); disk cache; retry; cost log (0 in mock). No SDK/key required.
6. `harness/metrics.py` — REAL: `false_consensus_rate` (= modal-wrong-label share among non-target = convergent-delusion), `convergent_delusion` alias, `marginal_rho` (secondary), `a_maj`, `ece`. Docstrings state primary metric ≠ binary ρ.
7. `harness/run.py::run_task`, `harness/label.py::label_run` — mock deterministic path (real logic deferred to Phase 2, guarded with clear markers).
8. Stubs: `bench/build.py`, `detector/surface.py`, `sim_users/study.py`, `analysis/stats.py` — importable, raise `NotImplementedError` in bodies.
9. `tests/test_metrics_golden.py` FIRST (the 3 golden assertions), then `tests/test_smoke_pipeline.py` (mock Task end-to-end), `tests/test_provenance.py` (families distinct), `tests/test_imports.py`.
10. `pip install -e .` ; `python -c "import common"` ; `pytest` all green.

## Test steps
- `python -m pip install -e .`
- `python -c "import common,bench,harness,detector,sim_users,analysis"`
- `python -m pytest -q`
- Manual smoke: `python -c "from tests smoke ..."` (covered by test_smoke_pipeline).

## Push points
- After skeleton compiles (import passes) → push.
- After golden test green → push.
- After full pytest green + smoke → push, ready for audit.
