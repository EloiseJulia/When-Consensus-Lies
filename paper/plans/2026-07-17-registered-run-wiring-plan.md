# Plan — Registered-run wiring + MVP pilot gate (slice/registered-run, 2026-07-17)

> Manager-authored spec/plan (Manager writes NO source code). Implemented by a spawned Claude-family
> sub-agent in `.worktrees/registered-run`; audited by a GPT-family sub-agent (Hard Law 6). Merged by the
> Manager after full build+test green + a cross-family audit returns 0 BLOCKER/MAJOR.

## 0. Context (why this slice)
Amendment 06 (frontier proxy roster) + the reversed spot-check gate are SIGNED (decision-log row 53). The
runner (`harness/runner.py`) is already resumable + `copilot_proxy`-ready, and the Phase-6 analysis
pipeline (`analysis/`) is built — but they are NOT yet wired end-to-end for the registered run:
- `common/config.yaml` still holds the OLD GitHub-Models roster (gpt-4o-mini/llama/deepseek/o4-mini).
- `harness/runner.py::main` loads ONLY `bench.code_spec`, not all 3 domains.
- There is NO adapter turning the runner's AgentRun-JSONL into the tidy DataFrame the analysis pipeline
  (`analysis/contrasts.py`, `decision_rules.py`) consumes (columns: item, method, model_class, seed,
  regime, ambiguity_k, model, label/cd, target).
- The prereg §11 MVP-pilot GATE (CD>0 on real; R1 label-shuffle null CD≈0; integration test green) has no
  driver on the frontier roster.

This slice closes those four gaps so the Manager can run the §11 pilot on the proxy and report the gate.

## 1. FROZEN — do NOT touch
`harness/metrics.py`, `common/schema.py`, `paper/preregistration/*`, `harness/nulls.py` metric/null
DEFINITIONS, the executable-gold benchmark construction, `analysis/` metric math. This slice only WIRES
existing frozen components + updates the roster config authorized by the SIGNED Amendment 06. NO schema
changes. If any task seems to need a schema change, STOP and report to the Manager (would need an amendment).

## 2. Deliverables

### D1 — `common/config.yaml`: frontier roster (Amendment 06 option-a, SIGNED)
Replace the `roles.tested_agents` + `constructor`/`judge` roster with the A06 frontier roster. Keep the
`providers:` block; **keep `providers.default: github_models`** (the registered run passes
`--provider copilot_proxy` explicitly — do not change the default, to keep offline/existing paths intact).
| Role | Model(s) | Family |
|------|----------|--------|
| tested_agents.homogeneous (ρ→1 baseline; needs logprobs → OpenAI) | `gpt-5.4` | OpenAI |
| tested_agents.heterogeneous (cross-family MAD headline) | `gpt-5.4`, `claude-sonnet-4.6`, `gemini-3.1-pro-preview` | O/A/G |
| tested_agents.reasoning (H2 strong-reasoner) | `gpt-5.6-sol`, `claude-opus-4.8`, `gemini-3.1-pro-preview` | O/A/G |
| **tested_agents.weak** (NEW sub-role; H2 weak contrast) | `gpt-4o-mini`, `gemini-3.5-flash`, `claude-haiku-4.5` | O/G/A |
| constructor (R2 control) | `mai-code-1-flash-picker` | Microsoft |
| judge (vestigial — executable gold ⇒ ~never invoked) | `mai-code-1-flash-picker` | Microsoft |
| code_reviewer (CODE-audit plane, Manager overrides per slice) | `gpt-5.6-sol` | OpenAI |
- Use the EXACT proxy slugs (bare model ids, no `openai/` prefix — the proxy takes plain slugs; confirm
  against `/v1/models` on the running proxy at `http://127.0.0.1:8313/v1`).
- Adding `tested_agents.weak` mirrors the existing `reasoning` sub-role (config-level, no schema change).
- UPDATE any test that pins the old roster (e.g. asserting `gpt-4o-mini` as homogeneous) to the new roster;
  keep every existing test green. Do NOT weaken provenance-separation assertions — verify Hard Law 6 still
  holds (constructor Microsoft ∉ tested {O,A,G}; judge Microsoft only used when gold absent).

### D2 — All-3-domain task loader for the registered run
Provide a single entry that assembles the reversed benchmark across ALL three domains
(`bench.code_spec`, `bench.data_analysis`, `bench.policy_qa`) into one `List[Task]`, preserving each
Task's `regime` (H1_external/H2_derivable) and `ambiguity_k`. Prefer a small helper (e.g.
`harness/registered.py::load_all_domains()` or a function in a new `scripts/registered_run.py`) rather than
editing the frozen benches. `runner.main` currently hardcodes `code_spec` — either extend it to accept a
`--domains` arg defaulting to all three, or drive the runner from the new `scripts/registered_run.py`.

### D3 — AgentRun-JSONL → tidy-DataFrame adapter (in `analysis/`)
Add a loader (e.g. `analysis/io.py::load_runs_tidy(jsonl_path) -> DataFrame`) that reads the runner's
append-only AgentRun JSONL checkpoint and emits the tidy table the pipeline expects, with columns matching
`analysis/contrasts.py::COLS`: `item` (task_id), `method` (single/sc_k5/homogeneous_mad/heterogeneous_mad),
`model_class` (homogeneous/heterogeneous/reasoning/weak), `seed`, `regime`, `ambiguity_k`, `model`
(model_id), plus the executable-gold `label` and `target` per row so per-cell CD (`analysis/cd.py`) can be
computed. Derive `model_class` from the AgentRun's `model_role`/config (confirm the exact AgentRun field
names in `common/schema.py`; do NOT change the schema — map from what is already persisted). Provide a
golden unit test on a small synthetic AgentRun-JSONL fixture asserting the tidy columns + one CD cell.

### D4 — §11 MVP pilot-gate driver (`scripts/registered_run.py`)
A guarded driver (same discipline as `scripts/mini_pilot.py` / `harness/runner.py`: live only when
`RUNNER_LIVE=1`; `copilot_proxy` needs NO token) that, in `--pilot` mode:
1. Loads a SMALL balanced batch (≈6–10 items, ½ H1_external ½ H2_derivable, mixed k) across domains.
2. Runs the resumable runner on `--provider copilot_proxy` for the frontier grid (single + SC k=5 at
   minimum; homogeneous + heterogeneous + reasoning + weak classes), persisting AgentRun JSONL.
3. Labels via executable gold (`harness.label.label_run`), builds the tidy table (D3), and checks the
   pre-registered §11 GATE:
   - primary `convergent_delusion` (A04 cd_primary) **> 0** on the real underspecified items;
   - **R1 label-shuffle null**: CD under a population-level label shuffle ≈ 0 (reuse `harness/nulls.py`
     if it provides the shuffle; do NOT redefine the null) while real CD > 0;
   - the real run→label→metrics integration test passes AND the golden metric unit tests pass.
4. Prints a GATE verdict (PASS/FAIL per criterion), the per-condition **I_perp rate** (guardrail B,
   investigate if > 0.20), and total cost. It must NOT run at full scale (cap items + a hard budget).
Live execution is MANAGER-orchestrated (the Manager runs it and reports to the owner); the driver itself
must be OFFLINE-verifiable (unit-tested on synthetic/cached data with the live path guarded off).

### D5 — Tests
Golden/unit tests for D3 (adapter) and D4 (gate logic on synthetic data) + updated roster tests (D1).
Keep the FULL suite green (`python -m pip install -e . && python -m pytest -q`). Do not pin the mutable
live `.llm_cache`; use committed fixtures (cf. PR #25 lesson).

## 3. Provenance / workflow (Hard Law 6)
- Implementer = **Claude family**; record the family in the PR body.
- Auditor = **GPT family** (fresh, hostile, report-only). The Manager spawns the audit sub-agent.
- Self-check gate before ready: full build + `pytest -q` green; `--dry-run` of the runner on the frontier
  config lists the expected grid; `RUNNER_LIVE` unset ⇒ driver prints "skipped" and exits 0 (no network).
- Remove any stray `plan.md` the harness drops at repo root before marking ready.

## 4. Out of scope (later, Manager-gated)
The actual LIVE pilot run (Manager orchestrates), the full-scale registered run, and the Phase-6 real
analysis pass. This slice delivers the WIRING + the gate driver, offline-verifiable.
