# Plan — SC k=10 sensitivity pass driver (A08 §2 scheduled secondary)

> Manager spec for an IMPLEMENT sub-agent (Claude). Additive driver only; nothing frozen changes. Auditor = GPT.
> A08 §2 scheduled SC-k10 + verifier as a SECONDARY sensitivity pass. Verifier is ALREADY in the confirmatory
> data (analyzed). This slice adds the SC-k10 run only.

## Deliverable
NEW `scripts/sensitivity_sck10.py` — a thin driver that reuses the EXISTING registered-run machinery
(`scripts/registered_run.py` run function + the Runner in `harness/runner.py`) to run the **SC config ONLY**
with **k=10**, over the full confirmatory grid (all 3 domains: code_spec+data_analysis+policy_qa, 54 items,
seeds 0/1000/2000, all 4 model classes), writing to a SEPARATE checkpoint `.run_partitions/cp_sck10.jsonl`
and cache dir, $0 on the copilot_proxy. Guarded by RUNNER_LIVE like the main runner.

Key points (read scripts/registered_run.py first to reuse, not duplicate):
- Use `config_kwargs = {"sc": {"k": 10}}` (override the frozen REGISTERED_CONFIG_KWARGS sc k=5 for THIS
  sensitivity run only — do NOT edit REGISTERED_CONFIG_KWARGS in registered_run.py).
- Restrict the run to the `sc` config ONLY (single/MAD/etc. already done in the confirmatory run — do not
  re-run them). If the run function enumerates all configs, filter the grid to config=="sc" (find how the
  configs are enumerated and pass/limit accordingly; if there is no clean filter, add a minimal ADDITIVE
  parameter path — do not edit frozen grid logic destructively).
- Reuse the frontier roster, ≥3 seeds (0/1000/2000), rpm=30, endpoint-namespaced checkpoint.
- The SC k=5 samples from the confirmatory run are in a DIFFERENT checkpoint/cache; this run may re-sample
  (k=10) fresh into its own checkpoint — that is fine ($0). Do NOT write into the confirmatory checkpoints.
- Gate C cardinality for sc at k=10 = 10 agents (adjust the expectation for this driver only; do not edit
  the frozen `_GATE_C_MIN_AGENTS` in registered_run.py — override locally if needed).

## Constraints
- Do NOT edit frozen files: `harness/metrics.py`, `common/schema.py`, `harness/nulls.py` defs, existing
  `bench/*`, `analysis/*` metric math, `paper/preregistration/*`. Reuse `scripts/registered_run.py` +
  `harness/runner.py` WITHOUT editing them (import/parameterize); if an unavoidable change is needed there,
  it MUST be ADDITIVE (new optional param, byte-identical default) and called out for the auditor.
- Offline/CI-safe: `main()` does nothing without RUNNER_LIVE=1 (+ proxy reachable); offline unit test drives
  the driver against the mock client with NO network.

## Self-check
- `python -m pip install -e . && python -m pytest -q` green.
- `python scripts/sensitivity_sck10.py --dry-run` (or equivalent) enumerates ONLY sc-config jobs at k=10.
- `git diff --stat main...HEAD` = only the new driver + its test (+ any ADDITIVE param in registered_run.py/
  runner.py, prominently noted). Nothing frozen.
- Commit on branch; do NOT push/PR (Manager does). Record implementer family = Claude.

## After merge (Manager)
Run live ($0), then analyze: SC-k10 vs SC-k5 vs single — CD by regime, and P1 n_eff/ICC at k=10 (confirm the
ρ→1 collapse persists at higher k). Report as A08 §2 secondary sensitivity.
