# Spec — Phase 0: Scaffold `common/` + `tests/` + empty module interfaces + local CI

> Slice `[S0]` from AI-Execution-Plan.md §4. **Blocks all other phases.** Single serial slice.

## Objective
Stand up an installable Python package (`pip install -e .`) with:
- `common/` full set: `llm.py` (multi-provider client, role-based model routing, cache/retry/cost log), `schema.py` (the project-wide interface contract dataclasses), `config.yaml` (role×family routing + seeds).
- Empty-but-importable module interfaces for `bench/`, `harness/` (`run.py`, `label.py`, `metrics.py`), `detector/`, `sim_users/`, `analysis/`.
- `tests/` skeleton, **including `tests/test_metrics_golden.py` written FIRST** (executable gold for the primary metric).
- A mock `Task` that runs end-to-end **run → label → metrics** with NO network calls.
- Local CI = `pytest` green.

## Non-goals (do NOT do in Phase 0)
- No real benchmark items, no real LLM calls, no real detector/statistics logic — **stubs only** (raise `NotImplementedError` or return typed placeholders).
- No GPU / representation analysis (Phase 4).
- No changing metric *definitions* after they are committed (pre-registration discipline starts here).
- No provider SDK hard-dependency: `llm.py` must import and run in **mock/offline mode** without any API key.

## Surface (public interfaces other phases import)
- `from common.schema import Interpretation, Task, AgentRun` — frozen after Phase 0.
- `from common.config import load_config, model_for_role` — reads `common/config.yaml`.
- `from common.llm import LLMClient` — `.complete(role=..., prompt=...)`; offline/mock deterministic mode keyed by global seed; cache + retry + cost log.
- `from harness.run import run_task` ; `from harness.label import label_run` ; `from harness.metrics import false_consensus_rate, convergent_delusion, marginal_rho, a_maj, ece`.

## Design
### `common/schema.py` (the contract — mirror AI-Execution-Plan §3)
```python
@dataclass
class Interpretation:
    id: str            # "I0" | "I1" | ... | "I_perp"
    is_target: bool
    gold_check: str    # points at an executable checker in gold/ (fn name or test file)

@dataclass
class Task:
    id: str; domain: str          # code_spec | data_analysis | policy_qa
    prompt: str                   # underdetermined prompt (k requirement-classes deleted)
    latent_spec: str              # full spec (visible to scorer, hidden from tested agents)
    interpretations: list         # List[Interpretation]
    ambiguity_level: int          # 1|2|3 = how many requirement classes deleted
    key_questions: list           # golden clarifying questions

@dataclass
class AgentRun:
    task_id: str; config: str     # single|sc|mad|verifier|diverse
    model_role: str; model_id: str
    output: str; label: str       # L_i in {I0,...,I_perp}, assigned by label.py via executable signal
    verbalized_conf: float; logit_conf: float | None
    seed: int                     # identity dimension — avoid silent config collisions
```
> **Identity-dimension rule (self-check gate):** an `AgentRun` is uniquely keyed by `task_id × config × model_role × model_id × seed`. Missing any = silent collision.

### `common/config.yaml` (provenance separation — HARD LAW 6)
Mirror AI-Execution-Plan §2: `constructor` (openai), `tested_agents` (homogeneous [anthropic]; heterogeneous [openai,anthropic,google,qwen,deepseek]; reasoning), `judge` (google), `code_reviewer` (anthropic). `seeds.global = 20260713`. The four roles `constructor / tested / judge / code_reviewer` MUST be mutually distinct families.

### `common/llm.py`
- `LLMClient(config)` with `.complete(role, prompt, seed=None) -> Completion`.
- **Offline/mock mode default** (no key needed): deterministic output = hash(role, prompt, seed). Cache to disk; retry wrapper; per-call cost log (0 in mock).
- `model_for_role(role)` resolves family→model id from config.

### `harness/` stubs with a WORKING end-to-end mock path
- `run.py::run_task(task, config, client) -> list[AgentRun]` — mock produces deterministic outputs.
- `label.py::label_run(run, task) -> str` — maps output → `L_i` via **executable signal** (mock: deterministic mapping), NEVER an LLM judge.
- `metrics.py` — REAL implementations of the metric math (these are science-critical, not stubs):
  - `false_consensus_rate(labels, target)` — fraction agreeing on the SAME single wrong label (the modal non-target label share), = **convergent-delusion**.
  - `marginal_rho(...)` — secondary binary-correlation bridge only.
  - `a_maj`, `ece` — standard.

### Packaging / CI
- `pyproject.toml` (setuptools), packages = common, bench, harness, detector, sim_users, analysis.
- `pip install -e .` then `python -c "import common"` must pass.
- `pytest` green.

## Acceptance Criteria
1. `pip install -e .` succeeds; `python -c "import common, bench, harness, detector, sim_users, analysis"` passes.
2. `pytest` green, **including `tests/test_metrics_golden.py`**:
   - `false_consensus_rate(labels=["I1"]*5, target="I0") == 1.0` (all wrong on SAME I1 → convergent-delusion = 1.0).
   - `false_consensus_rate(labels=["I1","I2","I3","I_perp","I_perp"], target="I0") < 0.5` (each wrong differently → low, **even though binary ρ high**).
   - A case where everyone is correct (`["I0"]*5`) → `0.0`.
3. A mock `Task` runs end-to-end `run_task → label_run → metrics` producing a convergent-delusion number, with **no network**.
4. `common/config.yaml` has constructor/tested/judge/code_reviewer as mutually-distinct families.
5. `common/llm.py` imports and runs in offline mock mode with NO API key set.
6. Reproducible: global seed wired; mock outputs deterministic across reruns; API-result cache present.

## Slice Plan
Single serial slice `S0`. Steps: package skeleton → `schema.py` → `config.yaml` + `config.py` loader → `llm.py` offline mock → `metrics.py` real math → `run.py`/`label.py` mock path → module stubs → `tests/` (golden FIRST) → `pip install -e .` + `pytest` green → mock end-to-end smoke.
