# phase3-runner — implementation plan

> Implementer: Claude/Anthropic family (claude-sonnet)
> Worktree: .worktrees/phase3-runner  Branch: slice/phase3-runner

## Module layout

```
common/llm.py          (surgical addition — DayCapped exception + day-cap HTTP detection)
harness/runner.py      (NEW — the resumable runner, all 7 deliverables)
tests/test_runner.py   (NEW — offline token-independent tests)
```

## harness/runner.py internals

### Key types
- `run_identity(run)` → `task_id\x00config\x00model_role\x00model_id\x00seed`
- `job_key(task_id, config, seed)` → canonical string for a job

### CheckpointStore
- Append-only JSONL with two record types: `{"type":"run",...}` and `{"type":"job_done",...}`
- `flush()+fsync()` after EVERY record write → lose at most the in-flight job on crash
- Idempotent: `add_run(run)` no-ops if identity already in store
- `mark_job_done(task_id, config, seed)` only called after ALL AgentRuns for the job are stored

### RpmThrottler
- Per-model-slug deque of timestamps (sliding 60-second window)
- `_time_fn`/`_sleep_fn` injected for deterministic testing
- `rpm=0` means unlimited

### _ThrottledClient
- Duck-types LLMClient (exposes `.complete()`, `.config`, `.cache_dir`, `.offline`)
- On `complete()`: resolves slug, checks `day_capped` set (raises DayCapped immediately),
  calls `throttler.acquire(slug)`, then delegates to underlying LLMClient

### Runner
- Constructor accepts `run_task_fn` / `label_run_fn` for DI (testability)
- `enumerate_grid()` → cross-product (task, config, seed)
- `run(dry_run=False)`:
  1. Skip jobs in checkpoint (resume idempotency)
  2. Build per-job LLMClient with seed set in config copy
  3. Wrap in _ThrottledClient with shared day_capped_models set
  4. Call `_run_job_with_retry(task, config, wrapped_client)`
  5. On success: `add_run()` per AgentRun + `mark_job_done()`
  6. On DayCapped: record model in day_capped_models, continue (status=resumable)
  7. On BudgetExceeded: checkpoint and exit immediately
  8. On transient error: retry (max_infra_retries) with backoff, never checkpoint on failure
- Emit progress + per-condition I_perp RATE at end

### CLI guard (same discipline as mini_pilot.py)
- `_live_guard()` → `RUNNER_LIVE=1` AND token present
- Without guards: prints "skipped" and exits

## common/llm.py additions (surgical)

1. `class DayCapped(Exception)` — public permanent stop, has `.model_slug`
2. In `_generate_online` HTTP loop: detect `x-ratelimit-type=UserByModelByDay` header
   - Set `_is_day_cap=True` inside HTTPError handler (before closing exc)
   - In decision logic: if `_is_day_cap` → set `_day_cap_hit=True`, break (no retry)
   - After loop: if `_day_cap_hit` → `raise DayCapped(slug)` (outside except scope, __context__=None)
3. In `complete()`: add `DayCapped` to permanent exceptions list (no retry)

## tests/test_runner.py coverage

| Test class | What it verifies |
|---|---|
| TestGridEnumeration | (a) cross-product size, all combos, pending_jobs initial |
| TestResumeIdempotency | (b) skip done jobs, partial resume, full rerun = 0 calls |
| TestRpmThrottler | (c) unlimited never sleeps, RPM=2 allows 2 then blocks, per-model independent |
| TestDayCap | (d) stops model cleanly, resumable checkpoint, DayCapped not retried |
| TestCrashResistance | (e) runs persisted without job_done, idempotent re-add, corrupt line survived |
| TestBudgetStop | BudgetExceeded stops cleanly, partial checkpoint preserved |
| TestInfraErrorRetry | transient retried, all retries exhausted = failed (not checkpointed) |
| TestDryRun | dry_run=True → 0 run_task calls |
| TestIPerpRates | 2/3 I_perp rate computed and emitted |
| TestCheckpointStore | unit tests for all store operations |
| TestDayCappedException | DayCapped importable, has model_slug, not retried by runner |
