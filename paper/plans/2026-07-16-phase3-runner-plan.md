# Phase 3-INFRA-3 — resumable, cache-backed, RPM-throttled experiment runner (per-slice plan)

> Manager-authored plan (orchestrator-only). Implementer = Claude family, in worktree
> `.worktrees/phase3-runner` (branch `slice/phase3-runner`). Auditor = NON-Claude (Hard Law 6).
> This is INFRA (not benchmark science). Must be **token-independent to build + offline-test** (no
> network in CI). Metric/schema/prereg FROZEN — do not touch them.

## Why this slice
Rate limits — not cost — gate scale. `gpt-4o-mini` (the homogeneous ρ-baseline) is per-DAY capped
(x-ratelimit-type=UserByModelByDay, ~12h reset); o-series ~160 req/60s. A full confirmatory run
(≈60–100 items/domain × k-levels × 6 configs × model roles × ≥3 seeds) CANNOT finish in one session.
We need a checkpointed runner that resumes across rate-limit stalls and days and leans on the disk cache.
`scripts/mini_pilot.py` is only a double-guarded SMOKE, not the runner.

## What exists to build on (read these)
- `harness/run.py`: `run_task(task, config, client, **kwargs) -> List[AgentRun]`; 6 configs
  (single, sc, mad-homogeneous, mad-heterogeneous, verifier, diverse); per-config temperature; reasoning
  handling. `harness/label.py` (`label_run`, executable gold). `harness/metrics.py` (frozen).
- `common/llm.py`: online GitHub Models client. Disk cache keys on
  `mode|identity|role|prompt|seed|temperature`; a cache HIT makes ZERO HTTP calls. BudgetExceeded is
  permanent. Token from User-scope `GITHUB_MODELS_TOKEN` (NEVER print/log the token).
- `common/config.yaml`: Option-B role routing (constructor/homogeneous/heterogeneous/reasoning/judge).
- `common/schema.py` (FROZEN): `AgentRun` identity = task_id × config × model_role × model_id × seed.

## Deliverables (build under `harness/` — propose exact module name, e.g. `harness/runner.py`)
1. **A resumable run driver** that enumerates the full job grid as the CROSS-PRODUCT of
   `(task, config, model_role/model_id, seed)` using the `AgentRun` identity key, and executes it,
   producing `AgentRun` records (and their labels) to a durable results store.
2. **Checkpointing / resume:** persist per-job completion to disk (append-only JSONL or SQLite) keyed by
   the AgentRun identity. On restart, SKIP already-completed jobs (idempotent); a re-run with everything
   done is a no-op and makes ZERO HTTP calls. Flush+fsync so a mid-run crash/kill loses at most the
   in-flight job. Must survive a hard kill (rate-limit stall spanning days).
3. **RPM throttling:** a per-model request-rate limiter (configurable RPM, default conservative) so a long
   batch does not trip the per-minute caps; on HTTP 429 with a day-cap signal
   (`x-ratelimit-type=UserByModelByDay`), STOP that model's jobs cleanly, checkpoint, and exit with a
   clear resumable status (do NOT spin retrying a day-capped model). Respect the client's existing bounded
   429/5xx backoff; do not bypass it.
4. **Cache-first:** rely on the client disk cache; never duplicate a completed (identity) call. Support a
   `--dry-run`/plan mode that reports how many jobs are pending vs cache-satisfiable WITHOUT any network.
5. **Budget:** a hard aggregate budget pre-authorization pass-through (BudgetExceeded stops cleanly and
   checkpoints). Cost is trivial but keep the guard.
6. **INFRA-error discipline (mirror PR #7):** transient infra failures (network/spawn/timeout) are
   retried and NEVER checkpointed as completed; only genuine completed AgentRuns are recorded. An empty/
   invalid model output is a normal AgentRun (labeler → I_perp), not an infra error.
7. **Observability:** structured progress log (completed/pending/failed per model×config×domain) with NO
   token leakage; emit the per-condition I_perp RATE as a first-class diagnostic line (owner guardrail B).

## Testing (OFFLINE, token-independent — required)
- Unit-test the driver against the OFFLINE deterministic mock client (`LLMClient` offline default) and/or
  a fake client: verify (a) full grid enumeration matches the AgentRun identity product; (b) resume skips
  completed jobs (run→kill→rerun → no duplicate work, no extra calls); (c) RPM limiter paces calls;
  (d) a simulated day-cap 429 stops that model cleanly and leaves a resumable checkpoint; (e) crash-mid-run
  loses ≤1 job. NO network in any test. Add to `tests/` (e.g. `tests/test_runner.py`).
- `python -m pytest -q` → full suite green.
- Keep `scripts/mini_pilot.py` as-is (still the double-guarded smoke); the runner is the scaled path but
  MUST NOT auto-run at scale in CI (guard live execution behind an explicit env flag + present token,
  same discipline as mini_pilot).

## Provenance / process
- Record model FAMILY in the PR body + a header comment. Commit in the worktree; push
  `slice/phase3-runner`. The Manager opens the PR, spawns a NON-Claude cross-family audit (this touches
  shared infra + money/rate paths — audit hard, expect ≥2 rounds), routes fixes, and merges after the
  Law-4 gate (offline build+tests green + cross-family audit 0 BLOCKER/MAJOR). Call out shared-infra
  changes prominently in the PR body.
- Do NOT run any live/full-scale batch — that is owner-gated after the reversed spot-check gate. Do NOT
  edit the main checkout, harness/metrics.py, common/schema.py, or the prereg.

Commit trailer: `Co-authored-by: copilot <copilot@users.noreply.github.com>`.
