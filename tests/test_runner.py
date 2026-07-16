"""Offline tests for harness/runner.py.

# Implementer model family: Claude/Anthropic

ALL tests run FULLY OFFLINE — zero network calls, zero token use.

Coverage (per phase3-runner-plan.md requirements):
  (a) Grid enumeration == AgentRun identity cross-product
  (b) Resume skips completed jobs (run→kill→rerun → no dup work, no extra calls)
  (c) RPM limiter paces calls per model
  (d) Simulated day-cap 429 stops that model cleanly + leaves resumable checkpoint
  (e) Crash-mid-run loses ≤1 job
  Plus: budget stop, infra retry discipline, dry-run, I_perp rate diagnostic,
        CheckpointStore unit tests, DayCapped exception properties.
"""

from __future__ import annotations

import collections
import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import pytest

from common.llm import BudgetExceeded, DayCapped
from common.schema import AgentRun, Interpretation, Task
from harness.runner import (
    ALL_CONFIGS,
    CheckpointStore,
    Runner,
    RunnerConfig,
    RpmThrottler,
    _ThrottledClient,
    job_key,
    run_identity,
)


# ── Test fixtures / helpers ──────────────────────────────────────────────────

def make_task(task_id: str = "t1", domain: str = "policy_qa") -> Task:
    """Minimal Task suitable for offline tests (no bench data needed)."""
    return Task(
        id=task_id,
        domain=domain,
        prompt=f"test prompt for {task_id}",
        latent_spec="spec",
        interpretations=[
            Interpretation(id="I0", is_target=True, gold_check="c0"),
            Interpretation(id="I1", is_target=False, gold_check="c1"),
            Interpretation(id="I_perp", is_target=False, gold_check="perp"),
        ],
        ambiguity_level=1,
        key_questions=["q?"],
        regime=None,
    )


def make_run(
    task_id: str = "t1",
    config: str = "single",
    role: str = "tested_agents",
    model: str = "openai/gpt-4o-mini",
    seed: int = 1,
    label: str = "I0",
) -> AgentRun:
    """Minimal AgentRun for checkpoint / identity tests."""
    return AgentRun(
        task_id=task_id,
        config=config,
        model_role=role,
        model_id=model,
        output="output",
        label=label,
        verbalized_conf=0.5,
        logit_conf=None,
        seed=seed,
    )


def _make_runner(
    tasks: List[Task],
    tmp_path: Path,
    *,
    configs: Optional[List[str]] = None,
    seeds: Optional[List[int]] = None,
    checkpoint_path: Optional[Path] = None,
    rpm: int = 0,  # 0 = unlimited (no sleep in tests)
    run_task_fn: Optional[Callable] = None,
    label_run_fn: Optional[Callable] = None,
    max_budget_usd: Optional[float] = None,
    max_infra_retries: int = 3,
) -> Tuple[Runner, Path]:
    """Build a Runner with offline LLMClient and fake run_task / label_run."""
    from common.config import load_config
    from common.llm import LLMClient

    if checkpoint_path is None:
        checkpoint_path = tmp_path / "checkpoint.jsonl"

    cfg_dict = load_config()
    client = LLMClient(
        cfg_dict,
        cache_dir=str(tmp_path / "cache"),
        offline=True,
    )

    runner_cfg = RunnerConfig(
        tasks=tasks,
        configs=configs if configs is not None else ["single"],
        seeds=seeds if seeds is not None else [42],
        checkpoint_path=checkpoint_path,
        rpm=rpm,
        max_budget_usd=max_budget_usd,
        max_infra_retries=max_infra_retries,
    )

    def _default_run(task: Task, config: str, client_arg: Any, **kwargs) -> List[AgentRun]:
        seed = client_arg.config["seeds"]["global"]
        return [make_run(task.id, config, seed=seed)]

    def _default_label(run: AgentRun, task: Task) -> str:
        return "I0"

    runner = Runner(
        runner_cfg,
        client,
        run_task_fn=run_task_fn if run_task_fn is not None else _default_run,
        label_run_fn=label_run_fn if label_run_fn is not None else _default_label,
    )
    return runner, checkpoint_path


# ─────────────────────────────────────────────────────────────────────────────
# (a) Grid enumeration
# ─────────────────────────────────────────────────────────────────────────────

class TestGridEnumeration:
    """Test (a): full grid enumeration equals the AgentRun identity cross-product."""

    def test_grid_size_is_task_x_config_x_seed(self, tmp_path):
        tasks = [make_task("t1"), make_task("t2"), make_task("t3")]
        runner, _ = _make_runner(
            tasks, tmp_path,
            configs=["single", "sc"],
            seeds=[1, 2, 3],
        )
        assert len(runner.enumerate_grid()) == 3 * 2 * 3  # 18

    def test_grid_is_exact_cross_product(self, tmp_path):
        tasks = [make_task("t1"), make_task("t2")]
        configs = ["single", "sc", "verifier"]
        seeds = [10, 20]
        runner, _ = _make_runner(tasks, tmp_path, configs=configs, seeds=seeds)
        expected = {
            (tid, cfg, s)
            for tid in ["t1", "t2"]
            for cfg in configs
            for s in seeds
        }
        assert set(runner.enumerate_grid()) == expected

    def test_grid_covers_all_standard_configs(self, tmp_path):
        runner, _ = _make_runner(
            [make_task("t1")], tmp_path,
            configs=ALL_CONFIGS, seeds=[1],
        )
        grid = runner.enumerate_grid()
        assert len(grid) == len(ALL_CONFIGS)
        assert {cfg for _, cfg, _ in grid} == set(ALL_CONFIGS)

    def test_pending_jobs_initially_full_grid(self, tmp_path):
        tasks = [make_task("t1"), make_task("t2")]
        runner, _ = _make_runner(tasks, tmp_path, configs=["single"], seeds=[1])
        assert len(runner.pending_jobs()) == 2

    def test_single_task_single_config_single_seed(self, tmp_path):
        runner, _ = _make_runner([make_task("t1")], tmp_path)
        grid = runner.enumerate_grid()
        assert len(grid) == 1
        assert grid[0] == ("t1", "single", 42)


# ─────────────────────────────────────────────────────────────────────────────
# (b) Resume skips completed jobs
# ─────────────────────────────────────────────────────────────────────────────

class TestResumeIdempotency:
    """Test (b): run→kill→rerun → no duplicate work, no extra calls."""

    def test_full_run_then_rerun_is_noop(self, tmp_path):
        call_count = [0]

        def counting_run(task, config, client, **kwargs):
            call_count[0] += 1
            return [make_run(task.id, config, seed=client.config["seeds"]["global"])]

        tasks = [make_task("t1"), make_task("t2"), make_task("t3")]
        cp = tmp_path / "cp.jsonl"

        runner, _ = _make_runner(tasks, tmp_path, checkpoint_path=cp, run_task_fn=counting_run)
        result1 = runner.run()
        assert call_count[0] == 3
        assert result1["completed"] == 3

        # Re-run with fresh runner loading same checkpoint
        call_count[0] = 0
        runner2, _ = _make_runner(tasks, tmp_path, checkpoint_path=cp, run_task_fn=counting_run)
        result2 = runner2.run()

        assert call_count[0] == 0, "Re-run must make ZERO run_task calls for completed jobs"
        assert result2["skipped"] == 3
        assert result2["completed"] == 0

    def test_partial_resume_only_runs_remaining(self, tmp_path):
        """Simulate kill after t1 completes: resume processes only t2, t3."""
        runs_seen: List[str] = []

        def recording_run(task, config, client, **kwargs):
            runs_seen.append(task.id)
            return [make_run(task.id, config, seed=client.config["seeds"]["global"])]

        cp = tmp_path / "cp.jsonl"

        # Pre-checkpoint t1 as done
        store = CheckpointStore(cp)
        r = make_run("t1", "single", seed=42, label="I0")
        store.add_run(r)
        store.mark_job_done("t1", "single", 42)

        tasks = [make_task("t1"), make_task("t2"), make_task("t3")]
        runner, _ = _make_runner(
            tasks, tmp_path, checkpoint_path=cp, run_task_fn=recording_run
        )
        result = runner.run()

        assert "t1" not in runs_seen, "t1 should be skipped (already checkpointed)"
        assert "t2" in runs_seen
        assert "t3" in runs_seen
        assert result["skipped"] == 1
        assert result["completed"] == 2

    def test_full_rerun_zero_run_task_calls(self, tmp_path):
        """A fully-done rerun is a no-op with ZERO run_task calls."""
        cp = tmp_path / "cp.jsonl"
        store = CheckpointStore(cp)
        r = make_run("t1", "single", seed=42, label="I0")
        store.add_run(r)
        store.mark_job_done("t1", "single", 42)

        call_count = [0]

        def should_not_run(task, config, client, **kwargs):
            call_count[0] += 1
            return []

        runner, _ = _make_runner(
            [make_task("t1")], tmp_path,
            checkpoint_path=cp, run_task_fn=should_not_run,
        )
        result = runner.run()
        assert call_count[0] == 0, "Fully-done rerun must not call run_task"
        assert result["skipped"] == 1
        assert result["completed"] == 0

    def test_pending_jobs_decreases_after_completion(self, tmp_path):
        tasks = [make_task("t1"), make_task("t2")]
        runner, cp = _make_runner(tasks, tmp_path)

        assert len(runner.pending_jobs()) == 2
        runner.run()
        # Reload checkpoint
        runner2, _ = _make_runner(tasks, tmp_path, checkpoint_path=cp)
        assert len(runner2.pending_jobs()) == 0


# ─────────────────────────────────────────────────────────────────────────────
# (c) RPM limiter paces calls
# ─────────────────────────────────────────────────────────────────────────────

class TestRpmThrottler:
    """Test (c): RPM limiter paces calls without real wall-clock delays."""

    class _FakeTime:
        """Deterministic time source for throttler tests."""

        def __init__(self, start: float = 0.0) -> None:
            self._t = start
            self.slept: List[float] = []

        def time(self) -> float:
            return self._t

        def sleep(self, s: float) -> None:
            self.slept.append(s)
            self._t += s

        def advance(self, s: float) -> None:
            self._t += s

    def test_unlimited_rpm_never_blocks(self):
        ft = self._FakeTime()
        throttler = RpmThrottler(rpm=0, _time_fn=ft.time, _sleep_fn=ft.sleep)
        for _ in range(50):
            throttler.acquire("m1")
        assert ft.slept == [], "Unlimited RPM should never sleep"

    def test_allows_exactly_rpm_calls_before_blocking(self):
        ft = self._FakeTime(start=0.0)
        throttler = RpmThrottler(rpm=3, _time_fn=ft.time, _sleep_fn=ft.sleep)
        for _ in range(3):
            throttler.acquire("m1")
        assert ft.slept == [], "First RPM calls must not sleep"

    def test_blocks_on_rpm_exceeded(self):
        ft = self._FakeTime(start=0.0)
        throttler = RpmThrottler(rpm=2, _time_fn=ft.time, _sleep_fn=ft.sleep)
        throttler.acquire("m1")  # 1st — immediate
        throttler.acquire("m1")  # 2nd — immediate (window now full)
        throttler.acquire("m1")  # 3rd — must sleep
        assert len(ft.slept) >= 1, "3rd call should have slept waiting for window slot"
        assert ft.slept[0] > 0.0

    def test_per_model_windows_are_independent(self):
        ft = self._FakeTime()
        throttler = RpmThrottler(rpm=1, _time_fn=ft.time, _sleep_fn=ft.sleep)
        throttler.acquire("model_A")  # immediate — model_A window has 1 slot
        throttler.acquire("model_B")  # immediate — model_B window is separate
        assert ft.slept == [], "Different models should not throttle each other"
        # Next call for model_A should block
        throttler.acquire("model_A")
        assert len(ft.slept) >= 1

    def test_window_expiry_unblocks_subsequent_calls(self):
        ft = self._FakeTime(start=0.0)
        throttler = RpmThrottler(rpm=2, _time_fn=ft.time, _sleep_fn=ft.sleep)
        throttler.acquire("m")
        throttler.acquire("m")
        # Advance past 60-second window
        ft.advance(61.0)
        pre = len(ft.slept)
        # These two should not block — window cleared
        throttler.acquire("m")
        throttler.acquire("m")
        assert len(ft.slept) == pre, "After window expiry, no additional sleep needed"

    def test_current_rate_reflects_recent_calls(self):
        ft = self._FakeTime(start=0.0)
        throttler = RpmThrottler(rpm=10, _time_fn=ft.time, _sleep_fn=ft.sleep)
        for _ in range(5):
            throttler.acquire("m")
        assert throttler.current_rate("m") == 5

    def test_current_rate_excludes_expired(self):
        ft = self._FakeTime(start=0.0)
        throttler = RpmThrottler(rpm=10, _time_fn=ft.time, _sleep_fn=ft.sleep)
        throttler.acquire("m")
        throttler.acquire("m")
        ft.advance(70.0)  # expire all previous entries
        assert throttler.current_rate("m") == 0


# ─────────────────────────────────────────────────────────────────────────────
# (d) Day-cap stops model cleanly and leaves resumable checkpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestDayCap:
    """Test (d): day-cap stops model cleanly; resumable checkpoint; no retry."""

    def test_day_cap_stops_model_and_subsequent_jobs(self, tmp_path):
        """t2 day-caps the model; t3 also fails (same model); t1 is checkpointed."""
        tasks = [make_task("t1"), make_task("t2"), make_task("t3")]
        cp = tmp_path / "cp.jsonl"

        MODEL = "openai/gpt-4o-mini"
        capped = {"hit": False}

        def fake_run(task, config, client, **kwargs):
            if capped["hit"]:
                raise DayCapped(MODEL)
            if task.id == "t2":
                capped["hit"] = True
                raise DayCapped(MODEL)
            return [make_run(task.id, config, seed=client.config["seeds"]["global"])]

        runner, _ = _make_runner(tasks, tmp_path, checkpoint_path=cp, run_task_fn=fake_run)
        result = runner.run()

        assert result["status"] == "resumable"
        assert MODEL in result["day_capped_models"]

        store = CheckpointStore(cp)
        assert store.job_done("t1", "single", 42), "t1 must be checkpointed"
        assert not store.job_done("t2", "single", 42), "t2 must NOT be checkpointed"
        assert not store.job_done("t3", "single", 42), "t3 must NOT be checkpointed"

    def test_day_cap_resume_retries_pending_jobs(self, tmp_path):
        """After day-cap, pending jobs can be successfully retried on next run."""
        tasks = [make_task("t1"), make_task("t2")]
        cp = tmp_path / "cp.jsonl"

        calls: Dict[str, int] = collections.defaultdict(int)
        first_run = [True]

        def fake_run_first(task, config, client, **kwargs):
            calls[task.id] += 1
            if first_run[0] and task.id == "t1":
                first_run[0] = False
                raise DayCapped("openai/gpt-4o-mini")
            return [make_run(task.id, config, seed=client.config["seeds"]["global"])]

        runner1, _ = _make_runner(
            tasks, tmp_path, checkpoint_path=cp, run_task_fn=fake_run_first
        )
        result1 = runner1.run()
        assert result1["status"] == "resumable"
        assert not CheckpointStore(cp).job_done("t1", "single", 42)

        # t2 may have succeeded in the first run (if it ran before the cap flag reset)
        # regardless, on resume the pending job(s) should be reattempted

        def fake_run_resume(task, config, client, **kwargs):
            calls[task.id] += 1
            return [make_run(task.id, config, seed=client.config["seeds"]["global"])]

        runner2, _ = _make_runner(
            tasks, tmp_path, checkpoint_path=cp, run_task_fn=fake_run_resume
        )
        result2 = runner2.run()
        assert result2["status"] == "done"
        assert CheckpointStore(cp).job_done("t1", "single", 42)

    def test_day_cap_not_retried(self, tmp_path):
        """DayCapped is a permanent error — must not be retried by _run_job_with_retry."""
        tasks = [make_task("t1")]
        call_count = [0]

        def always_cap(task, config, client, **kwargs):
            call_count[0] += 1
            raise DayCapped("openai/gpt-4o-mini")

        runner, _ = _make_runner(
            tasks, tmp_path, run_task_fn=always_cap, max_infra_retries=5
        )
        result = runner.run()

        assert call_count[0] == 1, "DayCapped must NOT be retried (permanent error)"
        assert result["status"] == "resumable"

    def test_day_capped_exception_has_model_slug_attribute(self):
        exc = DayCapped("openai/gpt-4o-mini")
        assert exc.model_slug == "openai/gpt-4o-mini"
        assert "openai/gpt-4o-mini" in str(exc)
        assert "24h" in str(exc)

    def test_throttled_client_raises_day_capped_for_known_capped_model(self, tmp_path):
        """_ThrottledClient raises DayCapped immediately when model is already capped."""
        from common.config import load_config
        from common.llm import LLMClient

        cfg = load_config()
        client = LLMClient(cfg, cache_dir=str(tmp_path / "cache"), offline=True)
        day_capped: Set[str] = {"openai/gpt-4o-mini"}
        throttler = RpmThrottler(rpm=0)
        wrapped = _ThrottledClient(client, throttler, day_capped)

        with pytest.raises(DayCapped) as exc_info:
            wrapped.complete(role="tested_agents", prompt="test", seed=1)
        assert exc_info.value.model_slug == "openai/gpt-4o-mini"

    def test_day_capped_importable_from_common_llm(self):
        """DayCapped must be publicly importable from common.llm."""
        from common.llm import DayCapped as DC  # noqa: F401
        assert DC is DayCapped


# ─────────────────────────────────────────────────────────────────────────────
# (e) Crash-mid-run loses at most 1 job
# ─────────────────────────────────────────────────────────────────────────────

class TestCrashResistance:
    """Test (e): crash-mid-run loses ≤1 job (the in-flight one at crash time)."""

    def test_runs_persisted_without_job_done_are_recoverable(self, tmp_path):
        """Simulates crash between add_run() and mark_job_done()."""
        cp = tmp_path / "cp.jsonl"
        store = CheckpointStore(cp)

        run1 = make_run("t1", "single", seed=1, label="I0")
        run2 = make_run("t1", "sc", seed=2, label="I1")

        # Write AgentRuns but do NOT mark_job_done (crash simulation)
        store.add_run(run1)
        store.add_run(run2)
        # CRASH — job_done never written

        store2 = CheckpointStore(cp)
        assert store2.run_done(run1), "run1 must survive crash"
        assert store2.run_done(run2), "run2 must survive crash"
        assert not store2.job_done("t1", "single", 1), "job must NOT be marked done"
        assert not store2.job_done("t1", "sc", 2), "job must NOT be marked done"

    def test_add_run_idempotent_across_crash_and_reload(self, tmp_path):
        """Re-adding the same run after reload is a no-op (no duplicate records)."""
        cp = tmp_path / "cp.jsonl"
        store1 = CheckpointStore(cp)
        run = make_run("t1", "single", seed=42, label="I0")
        store1.add_run(run)

        store2 = CheckpointStore(cp)
        store2.add_run(run)  # idempotent — should not duplicate
        assert store2.n_runs == 1

    def test_job_reruns_on_resume_after_crash(self, tmp_path):
        """Job reruns after crash (job_done absent), but count as completed on retry."""
        tasks = [make_task("t1")]
        cp = tmp_path / "cp.jsonl"

        # Pre-write run without job_done (simulating crash after AgentRun was stored)
        store = CheckpointStore(cp)
        r = make_run("t1", "single", seed=42, label="I0")
        store.add_run(r)
        # Do NOT mark_job_done — crash before that point

        call_count = [0]

        def counting_run(task, config, client, **kwargs):
            call_count[0] += 1
            return [make_run(task.id, config, seed=client.config["seeds"]["global"])]

        runner, _ = _make_runner(tasks, tmp_path, checkpoint_path=cp, run_task_fn=counting_run)
        result = runner.run()

        # Job reruns (expected: crash loses ≤1 job worth of work)
        assert call_count[0] == 1
        assert result["completed"] == 1
        # Now job_done is written
        assert CheckpointStore(cp).job_done("t1", "single", 42)

    def test_checkpoint_survives_corrupt_jsonl_line(self, tmp_path):
        """Corrupt JSON lines in the checkpoint are skipped; valid records intact."""
        cp = tmp_path / "cp.jsonl"
        store = CheckpointStore(cp)
        run = make_run("t1", "single", seed=99, label="I0")
        store.add_run(run)

        # Inject a corrupt line
        with open(cp, "a", encoding="utf-8") as fh:
            fh.write("{CORRUPT NOT JSON}\n")

        store2 = CheckpointStore(cp)
        assert store2.run_done(run), "Valid run must survive corrupt JSONL line"
        assert store2.n_runs == 1


# ─────────────────────────────────────────────────────────────────────────────
# Budget stop
# ─────────────────────────────────────────────────────────────────────────────

class TestBudgetStop:
    def test_budget_exceeded_stops_cleanly(self, tmp_path):
        """BudgetExceeded stops the runner, preserves the partial checkpoint."""
        tasks = [make_task("t1"), make_task("t2"), make_task("t3")]
        cp = tmp_path / "cp.jsonl"

        def capped_run(task, config, client, **kwargs):
            if task.id == "t2":
                raise BudgetExceeded("test cap")
            return [make_run(task.id, config, seed=client.config["seeds"]["global"])]

        runner, _ = _make_runner(tasks, tmp_path, checkpoint_path=cp, run_task_fn=capped_run)
        result = runner.run()

        assert result["status"] == "budget_exceeded"
        store = CheckpointStore(cp)
        assert store.job_done("t1", "single", 42), "t1 completed before cap"
        assert not store.job_done("t2", "single", 42), "t2 raised BudgetExceeded"
        assert not store.job_done("t3", "single", 42), "t3 never reached"

    def test_budget_exceeded_is_permanent_not_retried(self, tmp_path):
        call_count = [0]

        def always_budget(task, config, client, **kwargs):
            call_count[0] += 1
            raise BudgetExceeded("always")

        runner, _ = _make_runner(
            [make_task("t1")], tmp_path,
            run_task_fn=always_budget, max_infra_retries=5,
        )
        runner.run()
        assert call_count[0] == 1, "BudgetExceeded must not be retried"


# ─────────────────────────────────────────────────────────────────────────────
# Infra-error retry discipline
# ─────────────────────────────────────────────────────────────────────────────

class TestInfraErrorRetry:
    def test_transient_error_retried_then_succeeds(self, tmp_path):
        """Transient error on first attempt; succeeds on second attempt."""
        attempts = [0]

        def flaky_run(task, config, client, **kwargs):
            attempts[0] += 1
            if attempts[0] == 1:
                raise RuntimeError("simulated transient network error")
            return [make_run(task.id, config, seed=client.config["seeds"]["global"])]

        runner, _ = _make_runner(
            [make_task("t1")], tmp_path,
            run_task_fn=flaky_run, max_infra_retries=3,
        )
        result = runner.run()

        assert result["completed"] == 1, "Job should succeed after retry"
        assert attempts[0] == 2, "Should have attempted exactly twice"

    def test_all_retries_exhausted_counts_as_failed_not_checkpointed(self, tmp_path):
        """All retries fail → job counted as failed and NOT checkpointed."""
        tasks = [make_task("t1"), make_task("t2")]
        cp = tmp_path / "cp.jsonl"

        def always_fail_t1(task, config, client, **kwargs):
            if task.id == "t1":
                raise RuntimeError("permanent failure")
            return [make_run(task.id, config, seed=client.config["seeds"]["global"])]

        runner, _ = _make_runner(
            tasks, tmp_path, checkpoint_path=cp,
            run_task_fn=always_fail_t1, max_infra_retries=2,
        )
        result = runner.run()

        assert result["failed"] == 1
        assert result["completed"] == 1
        store = CheckpointStore(cp)
        assert not store.job_done("t1", "single", 42), "Failed job must NOT be checkpointed"
        assert store.job_done("t2", "single", 42)

    def test_infra_error_retry_count_respects_max(self, tmp_path):
        """Retry count is bounded by max_infra_retries (not infinite)."""
        attempts = [0]

        def always_fail(task, config, client, **kwargs):
            attempts[0] += 1
            raise RuntimeError("always fails")

        runner, _ = _make_runner(
            [make_task("t1")], tmp_path,
            run_task_fn=always_fail, max_infra_retries=3,
        )
        runner.run()
        assert attempts[0] == 3, "Should retry exactly max_infra_retries times"


# ─────────────────────────────────────────────────────────────────────────────
# Dry run
# ─────────────────────────────────────────────────────────────────────────────

class TestDryRun:
    def test_dry_run_calls_zero_run_task(self, tmp_path):
        """dry_run=True returns report without calling run_task at all."""
        call_count = [0]

        def must_not_run(task, config, client, **kwargs):
            call_count[0] += 1
            return []

        runner, _ = _make_runner(
            [make_task("t1"), make_task("t2")], tmp_path,
            configs=["single", "sc"], seeds=[1, 2],
            run_task_fn=must_not_run,
        )
        report = runner.run(dry_run=True)

        assert call_count[0] == 0, "dry_run must not call run_task"
        assert report["total"] == 2 * 2 * 2  # 8
        assert report["pending"] == 8
        assert report["done"] == 0

    def test_dry_run_reflects_checkpoint_state(self, tmp_path):
        """dry_run report accurately reflects the current checkpoint."""
        cp = tmp_path / "cp.jsonl"

        # Pre-complete one job
        store = CheckpointStore(cp)
        r = make_run("t1", "single", seed=1, label="I0")
        store.add_run(r)
        store.mark_job_done("t1", "single", 1)

        tasks = [make_task("t1"), make_task("t2")]
        runner, _ = _make_runner(
            tasks, tmp_path, configs=["single"], seeds=[1], checkpoint_path=cp
        )
        report = runner.run(dry_run=True)

        assert report["done"] == 1
        assert report["pending"] == 1
        assert report["total"] == 2
        assert len(report["pending_jobs"]) == 1
        assert report["pending_jobs"][0]["task_id"] == "t2"

    def test_dry_run_report_structure(self, tmp_path):
        runner, _ = _make_runner([make_task("t1")], tmp_path)
        report = runner.run(dry_run=True)
        assert "total" in report
        assert "done" in report
        assert "pending" in report
        assert "pending_jobs" in report


# ─────────────────────────────────────────────────────────────────────────────
# I_perp rate diagnostic
# ─────────────────────────────────────────────────────────────────────────────

class TestIPerpRates:
    def test_i_perp_rate_computed_and_emitted(self, tmp_path, capsys):
        """I_perp rate is computed correctly from checkpoint and printed."""
        cp = tmp_path / "cp.jsonl"
        store = CheckpointStore(cp)

        # Add 3 runs: 2 I_perp, 1 I0 → rate = 2/3
        for i, label in enumerate(["I_perp", "I_perp", "I0"]):
            r = make_run("t1", "single", seed=i, label=label)
            store.add_run(r)
            store.mark_job_done("t1", "single", i)

        runner, _ = _make_runner([make_task("t1")], tmp_path, checkpoint_path=cp)
        runner._emit_i_perp_rates()

        captured = capsys.readouterr()
        assert "I_perp" in captured.out
        assert "2/3" in captured.out

    def test_zero_runs_emits_nothing(self, tmp_path, capsys):
        """No runs → no I_perp output (prevent spurious empty lines)."""
        runner, _ = _make_runner([make_task("t1")], tmp_path)
        runner._emit_i_perp_rates()
        assert capsys.readouterr().out == ""

    def test_all_i_perp_emits_rate_100_percent(self, tmp_path, capsys):
        cp = tmp_path / "cp.jsonl"
        store = CheckpointStore(cp)
        for i in range(4):
            r = make_run("t1", "single", seed=i, label="I_perp")
            store.add_run(r)

        runner, _ = _make_runner([make_task("t1")], tmp_path, checkpoint_path=cp)
        runner._emit_i_perp_rates()
        out = capsys.readouterr().out
        assert "4/4" in out
        assert "1.000" in out


# ─────────────────────────────────────────────────────────────────────────────
# CheckpointStore unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckpointStore:
    def test_empty_store_loads_cleanly(self, tmp_path):
        store = CheckpointStore(tmp_path / "cp.jsonl")
        assert store.n_runs == 0
        assert store.n_done_jobs == 0

    def test_nonexistent_path_loads_cleanly(self, tmp_path):
        store = CheckpointStore(tmp_path / "does_not_exist.jsonl")
        assert store.n_runs == 0

    def test_add_run_persisted_on_reload(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        store = CheckpointStore(cp)
        run = make_run("t1", seed=99)
        store.add_run(run)

        store2 = CheckpointStore(cp)
        assert store2.run_done(run)

    def test_mark_job_done_persisted_on_reload(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        store = CheckpointStore(cp)
        store.mark_job_done("t1", "single", 99)

        store2 = CheckpointStore(cp)
        assert store2.job_done("t1", "single", 99)

    def test_add_run_idempotent_in_memory_and_on_disk(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        store = CheckpointStore(cp)
        run = make_run("t1", seed=1)
        store.add_run(run)
        store.add_run(run)
        store.add_run(run)
        assert store.n_runs == 1
        # Reload: still 1
        assert CheckpointStore(cp).n_runs == 1

    def test_mark_job_done_idempotent_single_record(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        store = CheckpointStore(cp)
        store.mark_job_done("t1", "sc", 1)
        store.mark_job_done("t1", "sc", 1)
        store.mark_job_done("t1", "sc", 1)
        lines = cp.read_text(encoding="utf-8").strip().splitlines()
        job_done_lines = [l for l in lines if '"job_done"' in l]
        assert len(job_done_lines) == 1, "Idempotent: exactly one job_done record"

    def test_all_runs_returns_copy(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        store = CheckpointStore(cp)
        store.add_run(make_run("t1", seed=1))
        runs = store.all_runs()
        runs.clear()  # mutate the copy
        assert store.n_runs == 1, "all_runs() must return a copy, not the internal list"

    def test_job_not_done_when_only_runs_present(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        store = CheckpointStore(cp)
        store.add_run(make_run("t1", seed=1))
        assert not store.job_done("t1", "single", 1)


class TestIdentityHelpers:
    def test_run_identity_includes_all_dimensions(self):
        run = make_run("t1", "sc", "tested_agents", "model_A", seed=7)
        identity = run_identity(run)
        assert "t1" in identity
        assert "sc" in identity
        assert "tested_agents" in identity
        assert "model_A" in identity
        assert "7" in identity

    def test_run_identity_distinguishes_seeds(self):
        r1 = make_run("t1", "single", seed=1)
        r2 = make_run("t1", "single", seed=2)
        assert run_identity(r1) != run_identity(r2)

    def test_run_identity_distinguishes_configs(self):
        r1 = make_run("t1", "single")
        r2 = make_run("t1", "sc")
        assert run_identity(r1) != run_identity(r2)

    def test_run_identity_distinguishes_models(self):
        r1 = make_run("t1", "single", model="model_A")
        r2 = make_run("t1", "single", model="model_B")
        assert run_identity(r1) != run_identity(r2)

    def test_run_identity_distinguishes_tasks(self):
        r1 = make_run("t1")
        r2 = make_run("t2")
        assert run_identity(r1) != run_identity(r2)

    def test_job_key_all_unique(self):
        keys = {
            job_key("t1", "single", 1),
            job_key("t1", "single", 2),
            job_key("t1", "sc", 1),
            job_key("t2", "single", 1),
        }
        assert len(keys) == 4
