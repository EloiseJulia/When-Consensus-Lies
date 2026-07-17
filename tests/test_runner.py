"""Offline tests for harness/runner.py.

# Implementer model family: Claude/Anthropic

ALL tests run FULLY OFFLINE — zero network calls, zero token use. The mocked-429
day-cap tests monkeypatch ``urllib.request.urlopen`` so no socket is ever opened.

Coverage (per phase3-runner-plan.md requirements + cross-family audit fixes):
  (a) Grid enumeration == AgentRun identity cross-product (task × config × MODEL × seed)
  (b) Resume skips completed jobs (run→kill→rerun → no dup work, no extra calls)
  (c) RPM limiter paces calls per model
  (d) Simulated day-cap 429 stops that model cleanly + leaves resumable checkpoint
  (e) Crash-mid-run loses ≤1 job
  Plus: budget stop, infra retry discipline, dry-run, I_perp rate diagnostic,
        CheckpointStore unit tests, DayCapped exception properties.

Audit-fix regression tests (real integration paths — would FAIL on the pre-fix code):
  * TestFiveDimResume     — BLOCKER 1: 5-dim job key (task,config,role,model,seed)
  * TestMocked429DayCap   — real HTTP 429 UserByModelByDay header drives DayCapped;
                            asserts token/secret NOT leaked in the exception chain
  * TestAggregateBudget   — BLOCKER 2: cumulative ledger stops the run across jobs
                            AND continues (no double-count) across a resume
  * TestAdditiveThrottle  — MAJOR 3: per-job client inherits the internal limiter
                            AND the runner's per-model window still applies
"""

from __future__ import annotations

import collections
import io
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import pytest

from common.llm import BudgetExceeded, Completion, DayCapped
from common.schema import AgentRun, Interpretation, Task
from harness.run import run_task as real_run_task
from harness.runner import (
    ALL_CONFIGS,
    CheckpointStore,
    LedgerWriteError,
    POOL_CONFIGS,
    Runner,
    RunnerConfig,
    RpmThrottler,
    _ThrottledClient,
    _live_ok,
    _token,
    endpoint_identity,
    job_key,
    run_identity,
)


# Default model identity carried by the single-model grid (matches config.yaml
# homogeneous tested-agents baseline and make_run's defaults).
ROLE = "tested_agents"
MODEL = "openai/gpt-4o-mini"


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
    role: str = ROLE,
    model: str = MODEL,
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
    models: Optional[List[Tuple[str, str]]] = None,
    checkpoint_path: Optional[Path] = None,
    rpm: int = 0,  # 0 = unlimited (no sleep in tests)
    run_task_fn: Optional[Callable] = None,
    label_run_fn: Optional[Callable] = None,
    client_factory: Optional[Callable] = None,
    max_budget_usd: Optional[float] = None,
    max_infra_retries: int = 3,
    base_offline: bool = True,
    base_max_rpm: Optional[int] = None,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
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
        offline=base_offline,
        max_requests_per_min=base_max_rpm,
        provider=provider,
        base_url=base_url,
    )

    runner_cfg = RunnerConfig(
        tasks=tasks,
        configs=configs if configs is not None else ["single"],
        seeds=seeds if seeds is not None else [42],
        models=models,
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
        client_factory=client_factory,
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
        # 3 tasks × 2 configs × 1 model × 3 seeds
        assert len(runner.enumerate_grid()) == 3 * 2 * 1 * 3  # 18

    def test_grid_is_exact_cross_product(self, tmp_path):
        tasks = [make_task("t1"), make_task("t2")]
        configs = ["single", "sc", "verifier"]
        seeds = [10, 20]
        runner, _ = _make_runner(tasks, tmp_path, configs=configs, seeds=seeds)
        expected = {
            (tid, cfg, ROLE, MODEL, s)
            for tid in ["t1", "t2"]
            for cfg in configs
            for s in seeds
        }
        assert set(runner.enumerate_grid()) == expected

    def test_grid_includes_model_dimension(self, tmp_path):
        """The grid cross-product includes the (model_role, model_id) dimension."""
        models = [
            ("tested_agents", "openai/gpt-4o-mini"),
            ("tested_agents", "meta/llama-3.3-70b-instruct"),
        ]
        runner, _ = _make_runner(
            [make_task("t1")], tmp_path,
            configs=["single"], seeds=[1], models=models,
        )
        grid = runner.enumerate_grid()
        assert len(grid) == 2  # 1 task × 1 config × 2 models × 1 seed
        assert {mid for _, _, _, mid, _ in grid} == {
            "openai/gpt-4o-mini", "meta/llama-3.3-70b-instruct"
        }

    def test_grid_covers_all_standard_configs(self, tmp_path):
        runner, _ = _make_runner(
            [make_task("t1")], tmp_path,
            configs=ALL_CONFIGS, seeds=[1],
        )
        grid = runner.enumerate_grid()
        assert len(grid) == len(ALL_CONFIGS)
        assert {cfg for _, cfg, _, _, _ in grid} == set(ALL_CONFIGS)

    def test_pending_jobs_initially_full_grid(self, tmp_path):
        tasks = [make_task("t1"), make_task("t2")]
        runner, _ = _make_runner(tasks, tmp_path, configs=["single"], seeds=[1])
        assert len(runner.pending_jobs()) == 2

    def test_single_task_single_config_single_seed(self, tmp_path):
        runner, _ = _make_runner([make_task("t1")], tmp_path)
        grid = runner.enumerate_grid()
        assert len(grid) == 1
        assert grid[0] == ("t1", "single", ROLE, MODEL, 42)


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
        store.mark_job_done("t1", "single", ROLE, MODEL, 42)

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
        store.mark_job_done("t1", "single", ROLE, MODEL, 42)

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
# BLOCKER 1 regression — five-dimensional resume across models
# ─────────────────────────────────────────────────────────────────────────────

class TestFiveDimResume:
    """BLOCKER 1: the job completion key must carry the FULL AgentRun identity
    (task × config × model_role × model_id × seed).  Completing one model's job
    must NOT silently skip a DIFFERENT model's job for the same (task,config,seed).

    On the pre-fix code (job_key omitted model identity) the second model would be
    wrongly reported as already-done and skipped — this test would FAIL there.
    """

    _MODELS = [
        ("tested_agents", "openai/gpt-4o-mini"),
        ("tested_agents", "meta/llama-3.3-70b-instruct"),
    ]

    def _recording_run(self, seen: List[str]):
        def rec_run(task, config, client, **kwargs):
            # The per-job config binds the grid model into the homogeneous slot.
            mid = client.config["roles"]["tested_agents"]["homogeneous"][0]["model"]
            seen.append(mid)
            return [make_run(task.id, config, model=mid,
                             seed=client.config["seeds"]["global"])]
        return rec_run

    def test_job_keys_differ_by_model(self):
        k1 = job_key("t1", "single", "tested_agents", "openai/gpt-4o-mini", 42)
        k2 = job_key("t1", "single", "tested_agents", "meta/llama-3.3-70b-instruct", 42)
        assert k1 != k2, "Job keys must differ when the model differs (BLOCKER 1)"

    def test_job_keys_differ_by_role(self):
        k1 = job_key("t1", "single", "tested_agents", "openai/gpt-4o-mini", 42)
        k2 = job_key("t1", "single", "judge", "openai/gpt-4o-mini", 42)
        assert k1 != k2, "Job keys must differ when the role differs (BLOCKER 1)"

    def test_resume_still_runs_other_model(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        seen: List[str] = []

        runner, _ = _make_runner(
            [make_task("t1")], tmp_path, checkpoint_path=cp,
            configs=["single"], seeds=[42], models=self._MODELS,
            run_task_fn=self._recording_run(seen),
        )
        # Grid spans BOTH models for the same (task, config, seed).
        assert len(runner.enumerate_grid()) == 2

        # Pre-complete ONLY the first model's job (simulate a partial run).
        store = CheckpointStore(cp)
        store.mark_job_done("t1", "single", "tested_agents", "openai/gpt-4o-mini", 42)

        # Resume with a fresh runner loading the same checkpoint.
        seen.clear()
        runner2, _ = _make_runner(
            [make_task("t1")], tmp_path, checkpoint_path=cp,
            configs=["single"], seeds=[42], models=self._MODELS,
            run_task_fn=self._recording_run(seen),
        )
        result = runner2.run()

        # The OTHER model MUST still run — no silent skip.
        assert "meta/llama-3.3-70b-instruct" in seen
        assert "openai/gpt-4o-mini" not in seen, "already-done model must be skipped"
        assert result["completed"] == 1
        assert result["skipped"] == 1

    def test_both_models_produce_distinct_runs(self, tmp_path):
        """A full run over 2 models yields 2 distinct AgentRun identities."""
        cp = tmp_path / "cp.jsonl"
        seen: List[str] = []
        runner, _ = _make_runner(
            [make_task("t1")], tmp_path, checkpoint_path=cp,
            configs=["single"], seeds=[42], models=self._MODELS,
            run_task_fn=self._recording_run(seen),
        )
        result = runner.run()
        assert result["completed"] == 2
        store = CheckpointStore(cp)
        model_ids = {rec["model_id"] for rec in store.all_runs()}
        assert model_ids == {"openai/gpt-4o-mini", "meta/llama-3.3-70b-instruct"}


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
# MAJOR 3 regression — additive throttling (internal limiter + runner window)
# ─────────────────────────────────────────────────────────────────────────────

class TestAdditiveThrottle:
    """MAJOR 3: per-job clients MUST inherit the base ``max_requests_per_min`` so
    the internal per-attempt limiter stays active on every HTTP retry, AND the
    runner's per-model sliding-window throttle is layered ON TOP (additive).

    On the pre-fix code the per-job client dropped ``max_requests_per_min`` (→ None),
    disabling the internal limiter — this test would FAIL there.
    """

    def test_per_job_client_inherits_internal_limiter(self, tmp_path):
        runner, _ = _make_runner(
            [make_task("t1")], tmp_path,
            configs=["single"], seeds=[42], rpm=5, base_max_rpm=7,
        )
        # Runner-level per-model sliding window is present …
        assert runner._throttler._rpm == 5, "runner window must still apply"
        # … AND the per-job client inherits the base internal limiter (not None).
        from common.config import load_config
        job_client = runner._client_factory(load_config(), None)
        assert job_client.max_requests_per_min is not None, (
            "per-job client must keep the internal per-attempt limiter (MAJOR 3)"
        )
        assert job_client.max_requests_per_min == 7

    def test_throttled_client_layers_runner_window_on_top(self, tmp_path):
        """The wrapper still calls the runner throttle even when the underlying
        client also has its own internal limiter (additive, not either/or)."""
        from common.config import load_config
        from common.llm import LLMClient

        acquired: List[str] = []

        class _SpyThrottler(RpmThrottler):
            def acquire(self, model_slug: str) -> None:
                acquired.append(model_slug)
                super().acquire(model_slug)

        client = LLMClient(
            load_config(), cache_dir=str(tmp_path / "cache"),
            offline=True, max_requests_per_min=9,
        )
        spy = _SpyThrottler(rpm=0)
        wrapped = _ThrottledClient(client, spy, set())
        wrapped.complete(role="tested_agents", prompt="x", seed=1)

        assert acquired, "runner throttle must be invoked (layered on top)"
        assert client.max_requests_per_min == 9, "internal limiter remains active"


# ─────────────────────────────────────────────────────────────────────────────
# (d) Day-cap stops model cleanly and leaves resumable checkpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestDayCap:
    """Test (d): day-cap stops model cleanly; resumable checkpoint; no retry."""

    def test_day_cap_stops_model_and_subsequent_jobs(self, tmp_path):
        """t2 day-caps the model; t3 also fails (same model); t1 is checkpointed."""
        tasks = [make_task("t1"), make_task("t2"), make_task("t3")]
        cp = tmp_path / "cp.jsonl"

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
        assert store.job_done("t1", "single", ROLE, MODEL, 42), "t1 must be checkpointed"
        assert not store.job_done("t2", "single", ROLE, MODEL, 42), "t2 must NOT be checkpointed"
        assert not store.job_done("t3", "single", ROLE, MODEL, 42), "t3 must NOT be checkpointed"

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
                raise DayCapped(MODEL)
            return [make_run(task.id, config, seed=client.config["seeds"]["global"])]

        runner1, _ = _make_runner(
            tasks, tmp_path, checkpoint_path=cp, run_task_fn=fake_run_first
        )
        result1 = runner1.run()
        assert result1["status"] == "resumable"
        assert not CheckpointStore(cp).job_done("t1", "single", ROLE, MODEL, 42)

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
        assert CheckpointStore(cp).job_done("t1", "single", ROLE, MODEL, 42)

    def test_day_cap_not_retried(self, tmp_path):
        """DayCapped is a permanent error — must not be retried by _run_job_with_retry."""
        tasks = [make_task("t1")]
        call_count = [0]

        def always_cap(task, config, client, **kwargs):
            call_count[0] += 1
            raise DayCapped(MODEL)

        runner, _ = _make_runner(
            tasks, tmp_path, run_task_fn=always_cap, max_infra_retries=5
        )
        result = runner.run()

        assert call_count[0] == 1, "DayCapped must NOT be retried (permanent error)"
        assert result["status"] == "resumable"

    def test_day_capped_exception_has_model_slug_attribute(self):
        exc = DayCapped(MODEL)
        assert exc.model_slug == MODEL
        assert MODEL in str(exc)
        assert "24h" in str(exc)

    def test_throttled_client_raises_day_capped_for_known_capped_model(self, tmp_path):
        """_ThrottledClient raises DayCapped immediately when model is already capped."""
        from common.config import load_config
        from common.llm import LLMClient

        cfg = load_config()
        client = LLMClient(cfg, cache_dir=str(tmp_path / "cache"), offline=True)
        day_capped: Set[str] = {MODEL}
        throttler = RpmThrottler(rpm=0)
        wrapped = _ThrottledClient(client, throttler, day_capped)

        with pytest.raises(DayCapped) as exc_info:
            wrapped.complete(role="tested_agents", prompt="test", seed=1)
        assert exc_info.value.model_slug == MODEL

    def test_day_capped_importable_from_common_llm(self):
        """DayCapped must be publicly importable from common.llm."""
        from common.llm import DayCapped as DC  # noqa: F401
        assert DC is DayCapped


# ─────────────────────────────────────────────────────────────────────────────
# Mocked HTTP 429 day-cap — REAL online path, token-safety invariant
# ─────────────────────────────────────────────────────────────────────────────

class TestMocked429DayCap:
    """Drives the day-cap through the REAL ``_generate_online`` HTTP path via a
    mocked 429 response carrying ``x-ratelimit-type=UserByModelByDay`` (NOT by
    directly raising DayCapped).  Asserts clean stop + resumable checkpoint +
    NO token/secret leakage in the exception chain (__context__ / __cause__ None).

    No socket is opened — ``urllib.request.urlopen`` is monkeypatched.
    """

    SECRET = "SECRET_TOKEN_DO_NOT_LEAK_deadbeef"

    def _http_429(self, headers: Dict[str, str]) -> urllib.error.HTTPError:
        return urllib.error.HTTPError(
            url="https://models.github.ai/inference/chat/completions",
            code=429,
            msg="Too Many Requests",
            hdrs=headers,  # supports .get("x-ratelimit-type")
            fp=io.BytesIO(b'{"error":"rate limited"}'),
        )

    def test_daycap_from_mocked_429_no_token_leak(self, tmp_path, monkeypatch):
        from common.config import load_config
        from common.llm import LLMClient

        monkeypatch.setenv("GITHUB_MODELS_TOKEN", self.SECRET)
        monkeypatch.delenv("GH_MODELS_TOKEN", raising=False)

        client = LLMClient(
            load_config(), cache_dir=str(tmp_path / "cache"), offline=False
        )

        def fake_urlopen(req, timeout=None):
            raise self._http_429({"x-ratelimit-type": "UserByModelByDay"})

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

        with pytest.raises(DayCapped) as ei:
            client.complete(role="tested_agents", prompt="hello", seed=1)

        exc = ei.value
        # Token-safety invariant: DayCapped is raised OUTSIDE any except scope, so
        # the HTTPError (which can carry auth material) is NOT chained in.
        assert exc.__context__ is None, "__context__ must be None (no leak chain)"
        assert exc.__cause__ is None, "__cause__ must be None (no leak chain)"
        # The secret must not appear anywhere in the exception text.
        assert self.SECRET not in str(exc)
        assert self.SECRET not in repr(exc)
        assert exc.model_slug == MODEL

    def test_regular_429_without_daycap_header_is_retried_then_fails(self, tmp_path, monkeypatch):
        """A 429 WITHOUT the day-cap header is a transient error (retried), not a
        permanent DayCapped — distinguishes the two 429 flavors."""
        from common.config import load_config
        from common.llm import LLMClient

        monkeypatch.setenv("GITHUB_MODELS_TOKEN", self.SECRET)
        monkeypatch.delenv("GH_MODELS_TOKEN", raising=False)
        monkeypatch.setattr(time, "sleep", lambda *_a, **_k: None)  # no real backoff

        client = LLMClient(
            load_config(), cache_dir=str(tmp_path / "cache"), offline=False
        )

        calls = [0]

        def fake_urlopen(req, timeout=None):
            calls[0] += 1
            raise self._http_429({"x-ratelimit-type": "UserByRequest"})  # NOT day cap

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

        with pytest.raises(Exception) as ei:
            client.complete(role="tested_agents", prompt="hello", seed=1)
        # Must NOT be a DayCapped (regular 429 is transient/retriable).
        assert not isinstance(ei.value, DayCapped)
        assert calls[0] > 1, "regular 429 must be retried, not stopped immediately"
        assert self.SECRET not in str(ei.value)

    def test_runner_daycap_via_mocked_429_is_resumable(self, tmp_path, monkeypatch, capsys):
        """End-to-end: the runner drives real online clients whose urlopen returns a
        day-cap 429 → clean resumable checkpoint, and the secret never appears in
        any runner output."""
        from common.config import load_config
        from common.llm import LLMClient

        monkeypatch.setenv("GITHUB_MODELS_TOKEN", self.SECRET)
        monkeypatch.delenv("GH_MODELS_TOKEN", raising=False)

        def fake_urlopen(req, timeout=None):
            raise self._http_429({"x-ratelimit-type": "UserByModelByDay"})

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

        cp = tmp_path / "cp.jsonl"
        base = LLMClient(
            load_config(), cache_dir=str(tmp_path / "cache"), offline=False
        )

        def online_run(task, config, client, **kwargs):
            # Exercises the REAL online complete() path (mocked 429 → DayCapped).
            client.complete(role="tested_agents", prompt=task.prompt, seed=1)
            return [make_run(task.id, config)]

        runner_cfg = RunnerConfig(
            tasks=[make_task("t1"), make_task("t2")],
            configs=["single"], seeds=[42], checkpoint_path=cp, rpm=0,
        )
        runner = Runner(
            runner_cfg, base,
            run_task_fn=online_run, label_run_fn=lambda r, t: "I0",
        )
        result = runner.run()

        assert result["status"] == "resumable"
        assert MODEL in result["day_capped_models"]
        # Resumable checkpoint: no job marked done (all pending for retry).
        store = CheckpointStore(cp)
        assert not store.job_done("t1", "single", ROLE, MODEL, 42)
        assert not store.job_done("t2", "single", ROLE, MODEL, 42)
        # Secret must never appear in any runner-emitted output.
        captured = capsys.readouterr()
        assert self.SECRET not in captured.out
        assert self.SECRET not in captured.err


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
        assert not store2.job_done("t1", "single", ROLE, MODEL, 1), "job must NOT be marked done"
        assert not store2.job_done("t1", "sc", ROLE, MODEL, 2), "job must NOT be marked done"

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
        assert CheckpointStore(cp).job_done("t1", "single", ROLE, MODEL, 42)

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
        assert store.job_done("t1", "single", ROLE, MODEL, 42), "t1 completed before cap"
        assert not store.job_done("t2", "single", ROLE, MODEL, 42), "t2 raised BudgetExceeded"
        assert not store.job_done("t3", "single", ROLE, MODEL, 42), "t3 never reached"

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
# BLOCKER 2 regression — aggregate (cumulative) budget across jobs and resumes
# ─────────────────────────────────────────────────────────────────────────────

class _FakeCostClient:
    """Fake client that reports a real incremental cost per complete() call.

    Mimics the LLMClient duck-type used by the runner (config, cache_dir, offline,
    max_requests_per_min, _total_cost_usd).  Each per-job instance starts its
    ``_total_cost_usd`` at 0, exactly like a real per-job LLMClient.
    """

    def __init__(self, config: Dict[str, Any], cost_per_call: float,
                 cache_dir: str, max_requests_per_min: Optional[int]) -> None:
        self.config = config
        self.cache_dir = Path(cache_dir)
        self.offline = True
        self.max_requests_per_min = max_requests_per_min
        self._total_cost_usd = 0.0
        self._cost_per_call = cost_per_call

    def complete(self, role, prompt, seed=None, **kwargs):
        self._total_cost_usd += self._cost_per_call
        return None  # the fake run_task does not read the completion


class TestAggregateBudget:
    """BLOCKER 2: --budget-usd is a HARD AGGREGATE cap across the WHOLE run and
    across resumes — NOT enforced per job.  The runner maintains a persisted cost
    ledger; when the cumulative total crosses the cap it stops cleanly.

    On the pre-fix code each job's client reset cost to 0 (per-job enforcement),
    so the run would never stop cumulatively — this test would FAIL there.
    """

    COST = 0.10

    def _factory(self, tmp_path):
        def factory(job_config, remaining_budget):
            return _FakeCostClient(
                job_config, cost_per_call=self.COST,
                cache_dir=str(tmp_path / "cache"), max_requests_per_min=None,
            )
        return factory

    def _costing_run(self):
        def run(task, config, client, **kwargs):
            client.complete(role="tested_agents", prompt="x", seed=1)
            return [make_run(task.id, config, seed=client.config["seeds"]["global"])]
        return run

    def test_stops_on_cumulative_not_per_job(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        # budget 0.15, cost 0.10/job over 3 jobs:
        #   job(seed=1): ledger 0.00<0.15 → run → ledger 0.10
        #   job(seed=2): ledger 0.10<0.15 → run → ledger 0.20
        #   job(seed=3): ledger 0.20>=0.15 → STOP (budget_exceeded)
        runner, _ = _make_runner(
            [make_task("t1")], tmp_path, checkpoint_path=cp,
            configs=["single"], seeds=[1, 2, 3], max_budget_usd=0.15,
            run_task_fn=self._costing_run(), client_factory=self._factory(tmp_path),
        )
        result = runner.run()

        assert result["status"] == "budget_exceeded"
        assert result["completed"] == 2, "must stop cumulatively (not per-job)"
        store = CheckpointStore(cp)
        assert store.aggregate_cost_usd == pytest.approx(0.20)

    def test_ledger_persists_and_no_double_count_on_resume(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        runner1, _ = _make_runner(
            [make_task("t1")], tmp_path, checkpoint_path=cp,
            configs=["single"], seeds=[1, 2, 3], max_budget_usd=0.15,
            run_task_fn=self._costing_run(), client_factory=self._factory(tmp_path),
        )
        runner1.run()
        assert CheckpointStore(cp).aggregate_cost_usd == pytest.approx(0.20)

        # Resume: ledger continues from 0.20 (>=0.15) → stops immediately, runs
        # ZERO new jobs, and does NOT double-count the two completed jobs.
        runner2, _ = _make_runner(
            [make_task("t1")], tmp_path, checkpoint_path=cp,
            configs=["single"], seeds=[1, 2, 3], max_budget_usd=0.15,
            run_task_fn=self._costing_run(), client_factory=self._factory(tmp_path),
        )
        result2 = runner2.run()

        assert result2["status"] == "budget_exceeded"
        assert result2["completed"] == 0, "no new jobs run on resume past the cap"
        assert result2["skipped"] == 2, "the two completed jobs are skipped"
        # Ledger unchanged — no double-count of already-completed jobs.
        assert CheckpointStore(cp).aggregate_cost_usd == pytest.approx(0.20)

    def test_remaining_budget_passed_as_subcap(self, tmp_path):
        """Each per-job client receives the REMAINING aggregate budget as its
        sub-cap (decreasing as the ledger grows)."""
        cp = tmp_path / "cp.jsonl"
        seen_remaining: List[Optional[float]] = []

        def spy_factory(job_config, remaining_budget):
            seen_remaining.append(remaining_budget)
            return _FakeCostClient(
                job_config, cost_per_call=self.COST,
                cache_dir=str(tmp_path / "cache"), max_requests_per_min=None,
            )

        runner, _ = _make_runner(
            [make_task("t1")], tmp_path, checkpoint_path=cp,
            configs=["single"], seeds=[1, 2, 3], max_budget_usd=0.15,
            run_task_fn=self._costing_run(), client_factory=spy_factory,
        )
        runner.run()
        # First job: remaining 0.15; second job: remaining 0.05 (0.15 - 0.10).
        assert seen_remaining[0] == pytest.approx(0.15)
        assert seen_remaining[1] == pytest.approx(0.05)


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
        assert not store.job_done("t1", "single", ROLE, MODEL, 42), "Failed job must NOT be checkpointed"
        assert store.job_done("t2", "single", ROLE, MODEL, 42)

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
        assert report["total"] == 2 * 2 * 1 * 2  # 8 (× 1 model)
        assert report["pending"] == 8
        assert report["done"] == 0

    def test_dry_run_reflects_checkpoint_state(self, tmp_path):
        """dry_run report accurately reflects the current checkpoint."""
        cp = tmp_path / "cp.jsonl"

        # Pre-complete one job
        store = CheckpointStore(cp)
        r = make_run("t1", "single", seed=1, label="I0")
        store.add_run(r)
        store.mark_job_done("t1", "single", ROLE, MODEL, 1)

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
        assert report["pending_jobs"][0]["model_id"] == MODEL
        assert report["pending_jobs"][0]["model_role"] == ROLE

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
            store.mark_job_done("t1", "single", ROLE, MODEL, i)

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
        store.mark_job_done("t1", "single", ROLE, MODEL, 99)

        store2 = CheckpointStore(cp)
        assert store2.job_done("t1", "single", ROLE, MODEL, 99)

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
        store.mark_job_done("t1", "sc", ROLE, MODEL, 1)
        store.mark_job_done("t1", "sc", ROLE, MODEL, 1)
        store.mark_job_done("t1", "sc", ROLE, MODEL, 1)
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
        assert not store.job_done("t1", "single", ROLE, MODEL, 1)

    def test_cost_ledger_accumulates_and_persists(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        store = CheckpointStore(cp)
        assert store.aggregate_cost_usd == pytest.approx(0.0)
        store.add_cost(0.05)
        store.add_cost(0.03)
        assert store.aggregate_cost_usd == pytest.approx(0.08)
        # Persisted across reload (append-only ledger)
        assert CheckpointStore(cp).aggregate_cost_usd == pytest.approx(0.08)

    def test_cost_ledger_ignores_nonpositive(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        store = CheckpointStore(cp)
        store.add_cost(0.0)
        store.add_cost(-1.0)
        assert store.aggregate_cost_usd == pytest.approx(0.0)
        # No records written for non-positive deltas.
        assert not cp.exists() or cp.read_text(encoding="utf-8").strip() == ""


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

    def test_job_key_matches_run_identity_dimensions(self):
        """job_key and run_identity encode the SAME five dimensions consistently."""
        run = make_run("t1", "single", "tested_agents", "model_A", seed=7)
        jk = job_key("t1", "single", "tested_agents", "model_A", 7)
        assert jk == run_identity(run)

    def test_job_key_all_unique(self):
        keys = {
            job_key("t1", "single", ROLE, MODEL, 1),
            job_key("t1", "single", ROLE, MODEL, 2),
            job_key("t1", "sc", ROLE, MODEL, 1),
            job_key("t2", "single", ROLE, MODEL, 1),
            job_key("t1", "single", ROLE, "meta/llama-3.3-70b-instruct", 1),
            job_key("t1", "single", "judge", MODEL, 1),
        }
        assert len(keys) == 6


# ─────────────────────────────────────────────────────────────────────────────
# Round-2 audit fixes (real integration paths — would FAIL on the pre-fix code)
# ─────────────────────────────────────────────────────────────────────────────


class _SimulatedCrash(BaseException):
    """A BaseException (NOT an ``Exception``) used to model a hard process crash.

    The runner's infra-retry and run-loop only catch ``Exception`` (and the two
    permanent errors), so this propagates straight out of ``run()`` — exactly
    like the process being killed mid-job, WITHOUT any ``except`` handler (or the
    old post-job ``add_cost``) getting a chance to run.
    """


class _CachingCostClient:
    """Fake client whose completions cost money the FIRST time only.

    A ``shared_cache`` set is threaded through every per-job instance (modelling
    the durable on-disk LLM cache): the first completion for a given key charges
    ``cost_per_call``; a repeat (cache hit, e.g. on resume) charges 0.  Each
    instance's ``_total_cost_usd`` still starts at 0, like a real per-job client.
    """

    def __init__(self, config, cost_per_call, cache_dir, max_requests_per_min,
                 shared_cache):
        self.config = config
        self.cache_dir = Path(cache_dir)
        self.offline = True
        self.max_requests_per_min = max_requests_per_min
        self._total_cost_usd = 0.0
        self._cost_per_call = cost_per_call
        self._shared_cache = shared_cache

    def complete(self, role, prompt, seed=None, **kwargs):
        key = (self.config["seeds"]["global"], role, prompt)
        if key in self._shared_cache:
            return None  # cache hit → zero incremental cost (resume rerun)
        self._shared_cache.add(key)
        self._total_cost_usd += self._cost_per_call
        return None


class TestCostLedgerCrashSafety:
    """BLOCKER B: cost is journaled PER PAID completion (via the throttle
    wrapper's ``cost_sink``) — NOT once after the whole job returns.

    A crash AFTER a paid completion but BEFORE ``mark_job_done`` must therefore
    NOT undercount the aggregate: the ledger entry is already fsync'd.  On the
    pre-fix code cost was appended only after the job returned (success/except
    paths), so a hard crash left NO ledger entry and the resumed run under-counted
    the spend — this test FAILS there and PASSES after the fix.
    """

    COST = 0.10

    def _factory(self, tmp_path, shared_cache):
        def factory(job_config, remaining_budget):
            return _CachingCostClient(
                job_config, cost_per_call=self.COST,
                cache_dir=str(tmp_path / "cache"), max_requests_per_min=None,
                shared_cache=shared_cache,
            )
        return factory

    def _crashing_run(self, crash_holder):
        def run(task, config, client, **kwargs):
            # Pay (journaled per-completion), THEN maybe crash before returning.
            client.complete(role="tested_agents", prompt="x", seed=1)
            if crash_holder["crash"]:
                raise _SimulatedCrash("killed after paid completion, before job_done")
            return [make_run(task.id, config, seed=client.config["seeds"]["global"])]
        return run

    def test_crash_after_paid_completion_is_counted_on_resume(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        shared_cache: Set[Any] = set()
        crash_holder = {"crash": True}

        runner1, _ = _make_runner(
            [make_task("t1")], tmp_path, checkpoint_path=cp,
            configs=["single"], seeds=[1], max_infra_retries=1,
            run_task_fn=self._crashing_run(crash_holder),
            client_factory=self._factory(tmp_path, shared_cache),
        )
        # Hard crash mid-job — propagates out of run() (no except handler runs).
        with pytest.raises(_SimulatedCrash):
            runner1.run()

        # The paid completion was journaled BEFORE the crash — reload proves it.
        assert CheckpointStore(cp).aggregate_cost_usd == pytest.approx(self.COST)
        # And the job was NOT marked done (so it will re-run on resume).
        assert not CheckpointStore(cp).job_done(
            "t1", "single", "tested_agents", MODEL, 1
        )

        # Resume: no crash this time; the completion CACHE-HITS (zero new cost).
        crash_holder["crash"] = False
        runner2, _ = _make_runner(
            [make_task("t1")], tmp_path, checkpoint_path=cp,
            configs=["single"], seeds=[1], max_infra_retries=1,
            run_task_fn=self._crashing_run(crash_holder),
            client_factory=self._factory(tmp_path, shared_cache),
        )
        result = runner2.run()

        assert result["completed"] == 1
        # Ledger still counts the spend EXACTLY once — no undercount, no double.
        assert CheckpointStore(cp).aggregate_cost_usd == pytest.approx(self.COST)


class _RecordingClient:
    """Duck-typed LLMClient that RECORDS each ``complete()`` call and drives the
    REAL ``harness.run.run_task`` offline (zero network, zero token).

    Resolves the invoked model EXACTLY like ``LLMClient``:
      * role-routed calls (single / sc / verifier / diverse) pass ``model=None``
        → resolved via ``model_for_role(role, config)`` (the bound homogeneous
        baseline), proving each grid cell's model actually controls the call;
      * MAD passes explicit ``family``/``model`` per pool agent → recorded as-is,
        proving pool ORDER controls execution order.
    """

    def __init__(self, config, calls, cache_dir="cache",
                 max_requests_per_min=None, cost_per_call=0.0):
        self.config = config
        self.cache_dir = Path(cache_dir)
        self.offline = True
        self.max_requests_per_min = max_requests_per_min
        self._total_cost_usd = 0.0
        self._cost_per_call = cost_per_call
        self._calls = calls

    def complete(self, role, prompt, seed=None, max_retries=3,
                 family=None, model=None, temperature=None):
        from common.config import model_for_role
        if model is None:
            resolved = model_for_role(role, self.config)
            model = resolved["model"]
            family = resolved.get("family")
        self._calls.append({"role": role, "family": family,
                            "model": model, "seed": seed})
        self._total_cost_usd += self._cost_per_call
        return Completion(
            text="FINAL ANSWER: $1.00", model=model,
            tokens_in=1, tokens_out=1, cost_usd=self._cost_per_call,
            logit_conf=None,
        )


def _pool_entries(models: List[str]) -> List[Dict[str, str]]:
    """Build a heterogeneous pool ``[{family, model}, ...]`` from slug list."""
    return [{"family": m.split("/", 1)[0], "model": m} for m in models]


class TestGridRoleRestriction:
    """BLOCKER A (round 3): ``harness.run.run_task`` invokes ONLY the
    ``tested_agents`` role, so the grid must NOT enumerate any other role — a
    non-tested cell could otherwise be marked done for work run_task never ran.

    On the pre-fix (round-2) code an arbitrary role (e.g. ``judge``) was accepted
    and bound; here it is rejected up-front.
    """

    def test_grid_rejects_non_tested_role(self, tmp_path):
        with pytest.raises(ValueError, match="tested_agents"):
            _make_runner(
                [make_task("t1")], tmp_path,
                models=[("judge", "meta/llama-3.3-70b-instruct")],
            )

    def test_grid_accepts_tested_role(self, tmp_path):
        runner, _ = _make_runner(
            [make_task("t1")], tmp_path,
            models=[("tested_agents", "openai/gpt-4o-mini")],
        )
        assert len(runner.enumerate_grid()) == 1


class TestRealRunTaskModelPlumbing:
    """BLOCKER A (round 3), auditor's methodological point: drive the REAL
    ``run_task`` with a RECORDING client to PROVE each grid cell's model actually
    controls the invoked model (not merely that the config dict was mutated).
    """

    _MODELS = [
        ("tested_agents", "openai/gpt-4o-mini"),
        ("tested_agents", "meta/llama-3.3-70b-instruct"),
    ]

    def _factory(self, tmp_path, calls):
        def factory(job_config, remaining_budget):
            return _RecordingClient(
                job_config, calls, cache_dir=str(tmp_path / "cache"),
            )
        return factory

    def test_each_cell_model_controls_real_invocation(self, tmp_path):
        calls: List[Dict[str, Any]] = []
        runner, _ = _make_runner(
            [make_task("t1", domain="policy_qa")], tmp_path,
            configs=["single"], seeds=[42], models=self._MODELS,
            run_task_fn=real_run_task, client_factory=self._factory(tmp_path, calls),
        )
        result = runner.run()
        assert result["completed"] == 2

        # Grid order is task→config→model→seed, so cell 0 = openai, cell 1 = llama.
        assert len(calls) == 2
        assert calls[0]["model"] == "openai/gpt-4o-mini"
        assert calls[1]["model"] == "meta/llama-3.3-70b-instruct"
        # Real run_task always routes via the tested_agents role.
        assert all(c["role"] == "tested_agents" for c in calls)

    def test_stored_runs_reflect_the_invoked_model(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        calls: List[Dict[str, Any]] = []
        runner, _ = _make_runner(
            [make_task("t1", domain="policy_qa")], tmp_path, checkpoint_path=cp,
            configs=["single"], seeds=[42], models=self._MODELS,
            run_task_fn=real_run_task, client_factory=self._factory(tmp_path, calls),
        )
        runner.run()
        stored = {rec["model_id"] for rec in CheckpointStore(cp).all_runs()}
        assert stored == {"openai/gpt-4o-mini", "meta/llama-3.3-70b-instruct"}


class TestHeterogeneousPoolIdentity:
    """BLOCKER A/B: a heterogeneous (pool) config invokes a POOL of models in
    LIST ORDER, so it is keyed by an ORDER-SENSITIVE identity over ``(family,
    model)`` entries (round-3 fix).  The per-model sweep is NOT applied, so
    distinct grid keys can never collapse onto identical pool work, and a pool
    REORDER changes both the key and the executed order (no false-skip).
    """

    A = "openai/gpt-4o-mini"
    B = "meta/llama-3.3-70b-instruct"

    def test_pool_config_is_recognized(self):
        assert "heterogeneous-MAD" in POOL_CONFIGS

    def test_pool_config_yields_single_pool_cell(self, tmp_path):
        # Even with a 2-model sweep, a pool config must yield exactly ONE cell
        # per (task, seed), keyed by the pool identity — never the per-model sweep.
        models = [("tested_agents", self.A), ("tested_agents", self.B)]
        runner, _ = _make_runner(
            [make_task("t1")], tmp_path,
            configs=["heterogeneous-MAD"], seeds=[42], models=models,
        )
        grid = runner.enumerate_grid()
        assert len(grid) == 1, "pool config must not fan out over the model sweep"
        (_tid, cfg_name, model_role, model_id, _seed) = grid[0]
        assert cfg_name == "heterogeneous-MAD"
        assert model_role == "tested_agents"
        assert model_id.startswith("pool:"), "pool cell keyed by pool identity"

    def test_pool_identity_reflects_configured_pool(self, tmp_path):
        runner, _ = _make_runner(
            [make_task("t1")], tmp_path,
            configs=["heterogeneous-MAD"], seeds=[42],
        )
        pool_id = runner.enumerate_grid()[0][3]
        pool = runner._base_client.config["roles"]["tested_agents"]["heterogeneous"]
        for member in pool:
            assert member["model"] in pool_id

    def test_pool_identity_is_order_sensitive(self, tmp_path):
        runner, _ = _make_runner(
            [make_task("t1")], tmp_path,
            configs=["heterogeneous-MAD"], seeds=[42],
        )
        roles = runner._base_client.config["roles"]["tested_agents"]
        roles["heterogeneous"] = _pool_entries([self.A, self.B])
        id_ab = runner._pool_identity()
        roles["heterogeneous"] = _pool_entries([self.B, self.A])
        id_ba = runner._pool_identity()
        assert id_ab != id_ba, "reordering the pool MUST change the identity"

    def test_pool_identity_includes_family(self, tmp_path):
        runner, _ = _make_runner(
            [make_task("t1")], tmp_path,
            configs=["heterogeneous-MAD"], seeds=[42],
        )
        roles = runner._base_client.config["roles"]["tested_agents"]
        roles["heterogeneous"] = [{"family": "openai", "model": self.A}]
        id1 = runner._pool_identity()
        roles["heterogeneous"] = [{"family": "CHANGED", "model": self.A}]
        id2 = runner._pool_identity()
        assert id1 != id2, "changing a member's family MUST change the identity"

    def test_bind_model_is_noop_for_pool_config(self):
        from common.config import load_config
        cfg = load_config()
        before = json.dumps(cfg["roles"]["tested_agents"], sort_keys=True)
        Runner._bind_model(cfg, "heterogeneous-MAD", "tested_agents", "pool:x")
        after = json.dumps(cfg["roles"]["tested_agents"], sort_keys=True)
        assert before == after, "pool config must NOT rebind — work is the pool"

    def test_homogeneous_and_pool_keys_never_collide(self, tmp_path):
        models = [("tested_agents", self.A), ("tested_agents", self.B)]
        runner, _ = _make_runner(
            [make_task("t1")], tmp_path,
            configs=["single", "heterogeneous-MAD"], seeds=[7], models=models,
        )
        grid = runner.enumerate_grid()
        # single → 2 model cells; heterogeneous-MAD → 1 pool cell = 3 total.
        assert len(grid) == 3
        keys = {job_key(*cell) for cell in grid}
        assert len(keys) == 3, "all grid keys must be distinct (no collision)"

    def _run_pool_order(self, tmp_path, order, calls, checkpoint_path=None):
        """Build+run a heterogeneous-MAD runner whose pool is in *order*, driving
        the REAL run_task with a recording client; return (key, result)."""
        tmp_path.mkdir(parents=True, exist_ok=True)
        runner, cp = _make_runner(
            [make_task("t1", domain="policy_qa")], tmp_path,
            checkpoint_path=checkpoint_path,
            configs=["heterogeneous-MAD"], seeds=[42],
            run_task_fn=real_run_task,
            client_factory=lambda jc, rb: _RecordingClient(
                jc, calls, cache_dir=str(tmp_path / "cache")),
        )
        runner._base_client.config["roles"]["tested_agents"]["heterogeneous"] = \
            _pool_entries(order)
        key = job_key(*runner.enumerate_grid()[0])
        result = runner.run()
        return key, result

    def test_pool_reorder_changes_key_and_execution_order(self, tmp_path):
        calls_ab: List[Dict[str, Any]] = []
        calls_ba: List[Dict[str, Any]] = []
        key_ab, res_ab = self._run_pool_order(
            tmp_path / "ab", [self.A, self.B], calls_ab)
        key_ba, res_ba = self._run_pool_order(
            tmp_path / "ba", [self.B, self.A], calls_ba)

        assert res_ab["completed"] == 1 and res_ba["completed"] == 1
        # (B) Reordering the pool changes the checkpoint key (no false-skip).
        assert key_ab != key_ba, "pool reorder MUST change the key"
        # ...and changes the actual first-round execution order in run_mad.
        assert calls_ab[0]["model"] == self.A
        assert calls_ba[0]["model"] == self.B
        assert calls_ab[0]["model"] != calls_ba[0]["model"]

    def test_pool_reorder_no_false_skip_on_shared_checkpoint(self, tmp_path):
        cp = tmp_path / "shared.jsonl"
        calls_ab: List[Dict[str, Any]] = []
        calls_ba: List[Dict[str, Any]] = []
        # Complete order [A, B] first.
        key_ab, res_ab = self._run_pool_order(
            tmp_path / "w", [self.A, self.B], calls_ab, checkpoint_path=cp)
        assert res_ab["completed"] == 1
        # Resume the SAME checkpoint with order [B, A]: different key → must RUN,
        # not be silently skipped as already-done.
        key_ba, res_ba = self._run_pool_order(
            tmp_path / "w", [self.B, self.A], calls_ba, checkpoint_path=cp)
        assert key_ab != key_ba
        assert res_ba["completed"] == 1, "reordered pool must not be false-skipped"
        assert res_ba["skipped"] == 0

    def test_pool_config_runs_and_marks_done(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        calls: List[Dict[str, Any]] = []
        runner, _ = _make_runner(
            [make_task("t1", domain="policy_qa")], tmp_path, checkpoint_path=cp,
            configs=["heterogeneous-MAD"], seeds=[42],
            run_task_fn=real_run_task,
            client_factory=lambda jc, rb: _RecordingClient(
                jc, calls, cache_dir=str(tmp_path / "cache")),
        )
        result = runner.run()
        assert result["completed"] == 1
        pool_id = runner.enumerate_grid()[0][3]
        assert CheckpointStore(cp).job_done(
            "t1", "heterogeneous-MAD", "tested_agents", pool_id, 42
        )


class TestLedgerWriteFailClosed:
    """Manager scope ruling (decision-log row 31): per-call fsync'd journaling is
    SUFFICIENT; a hard-crash losing ≤1 call (~$0.0001) is an ACCEPTED limitation.
    BUT a ledger WRITE failure must FAIL CLOSED — the job is treated as a
    permanent infra failure (not marked done, NOT retried into a $0 cache-hit
    that would silently lose the original spend).
    """

    def test_ledger_write_failure_fails_job_closed_not_retried(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        calls: List[Dict[str, Any]] = []

        def factory(job_config, remaining_budget):
            return _RecordingClient(
                job_config, calls, cache_dir=str(tmp_path / "cache"),
                cost_per_call=0.10,
            )

        runner, _ = _make_runner(
            [make_task("t1", domain="policy_qa")], tmp_path, checkpoint_path=cp,
            configs=["single"], seeds=[42], max_infra_retries=3,
            run_task_fn=real_run_task, client_factory=factory,
        )
        # Force the aggregate cost-ledger journal write to fail.
        def boom(delta):
            raise OSError("simulated ledger write failure (disk full)")
        runner._store.add_cost = boom

        result = runner.run()

        # FAIL CLOSED: the whole run stops resumably, this job NOT completed.
        assert result["status"] == "ledger_unavailable"
        assert result["completed"] == 0
        assert result["failed"] == 1
        # Job NOT marked done → it will not be silently treated as finished.
        assert not CheckpointStore(cp).job_done(
            "t1", "single", "tested_agents", "openai/gpt-4o-mini", 42
        )
        # NOT retried: run_task invoked exactly ONCE (a retry would cache-hit at
        # $0 and lose the original spend). max_infra_retries=3 proves permanence.
        assert len(calls) == 1

    def test_persistent_ledger_failure_stops_whole_run_no_further_paid_calls(
        self, tmp_path
    ):
        """BLOCKER (final): a PERSISTENT ledger-write failure must stop the WHOLE
        runner immediately — not just skip one job and continue to later PAID
        jobs.  With ≥2 pending jobs and an always-failing cost_sink, run_task must
        be invoked for AT MOST the first job (no further paid calls), the run must
        stop resumably, and NO job may be marked done.

        On the pre-fix code (``continue`` after LedgerWriteError) the second paid
        job would still run — spending twice while recording zero cost.  This test
        FAILS there (calls would be 2) and PASSES after the whole-run stop.
        """
        cp = tmp_path / "cp.jsonl"
        calls: List[Dict[str, Any]] = []

        def factory(job_config, remaining_budget):
            return _RecordingClient(
                job_config, calls, cache_dir=str(tmp_path / "cache"),
                cost_per_call=0.10,
            )

        # TWO pending jobs (two seeds → two single-model cells).
        runner, _ = _make_runner(
            [make_task("t1", domain="policy_qa")], tmp_path, checkpoint_path=cp,
            configs=["single"], seeds=[1, 2], max_infra_retries=3,
            run_task_fn=real_run_task, client_factory=factory,
        )
        assert len(runner.enumerate_grid()) == 2

        # PERSISTENT accounting-storage failure: every ledger write raises.
        def boom(delta):
            raise OSError("persistent accounting-disk failure")
        runner._store.add_cost = boom

        result = runner.run()

        # Whole run stopped resumably after the FIRST job's ledger failure.
        assert result["status"] == "ledger_unavailable"
        assert result["completed"] == 0
        # No further paid calls: run_task invoked for AT MOST the first job.
        assert len(calls) == 1, "must not incur paid calls after ledger failure"
        # No job marked done — both remain pending for a healthy-disk resume.
        assert CheckpointStore(cp).n_done_jobs == 0
        assert not CheckpointStore(cp).job_done(
            "t1", "single", "tested_agents", "openai/gpt-4o-mini", 1
        )
        assert not CheckpointStore(cp).job_done(
            "t1", "single", "tested_agents", "openai/gpt-4o-mini", 2
        )

    def test_ledger_write_error_is_permanent_not_retried_unit(self, tmp_path):
        """Unit-level: LedgerWriteError from the wrapper is raised straight out of
        _run_job_with_retry (never retried)."""
        from common.config import load_config

        calls: List[Dict[str, Any]] = []
        runner, _ = _make_runner(
            [make_task("t1", domain="policy_qa")], tmp_path,
            configs=["single"], seeds=[42], max_infra_retries=3,
            run_task_fn=real_run_task,
        )
        rec = _RecordingClient(load_config(), calls, cost_per_call=0.10)

        def boom(delta):
            raise OSError("disk full")

        wrapped = _ThrottledClient(rec, RpmThrottler(0), set(), cost_sink=boom)
        with pytest.raises(LedgerWriteError):
            runner._run_job_with_retry(make_task("t1", domain="policy_qa"),
                                       "single", wrapped)
        assert len(calls) == 1, "must not retry a fail-closed ledger error"


class TestLegacyCheckpointLoad:
    """MAJOR C: legacy ``job_done`` markers written BEFORE the 5-dim change lack
    ``model_role``/``model_id``.  ``_load()`` must never ``KeyError`` on them; a
    partial marker is treated as INCOMPLETE so the job safely re-runs.
    """

    def test_legacy_3field_job_done_loads_without_crash(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        cp.write_text(
            json.dumps({"type": "job_done", "task_id": "t1",
                        "config": "single", "seed": 42}) + "\n",
            encoding="utf-8",
        )
        # Must NOT raise KeyError('model_role').
        store = CheckpointStore(cp)
        # Legacy marker → treated incomplete → job re-runs (job_done == False).
        assert store.job_done(
            "t1", "single", "tested_agents", "openai/gpt-4o-mini", 42
        ) is False
        assert store.n_done_jobs == 0

    def test_legacy_and_valid_records_mixed(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        legacy = json.dumps({"type": "job_done", "task_id": "t1",
                             "config": "single", "seed": 1})
        valid = json.dumps({"type": "job_done", "task_id": "t2",
                            "config": "single", "model_role": "tested_agents",
                            "model_id": "openai/gpt-4o-mini", "seed": 2})
        cp.write_text(legacy + "\n" + valid + "\n", encoding="utf-8")

        store = CheckpointStore(cp)
        # Legacy record ignored (re-run), valid 5-dim record honoured.
        assert store.n_done_jobs == 1
        assert store.job_done("t2", "single", "tested_agents",
                              "openai/gpt-4o-mini", 2)
        assert not store.job_done("t1", "single", "tested_agents",
                                  "openai/gpt-4o-mini", 1)

    def test_legacy_marker_causes_rerun_not_false_skip(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        cp.write_text(
            json.dumps({"type": "job_done", "task_id": "t1",
                        "config": "single", "seed": 42}) + "\n",
            encoding="utf-8",
        )
        seen: List[str] = []

        def rec(task, config, client, **kwargs):
            seen.append(task.id)
            return [make_run(task.id, config,
                             seed=client.config["seeds"]["global"])]

        runner, _ = _make_runner(
            [make_task("t1")], tmp_path, checkpoint_path=cp,
            configs=["single"], seeds=[42], run_task_fn=rec,
        )
        result = runner.run()
        # The legacy job re-runs (safe) rather than being falsely skipped.
        assert result["completed"] == 1
        assert seen == ["t1"]


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER FIX (BLOCKER): checkpoint identity namespaced by provider + base_url
# ═══════════════════════════════════════════════════════════════════════════════

class TestProviderCheckpointNamespace:
    """Switching provider / proxy port must NOT reuse a stale job_done marker."""

    def test_endpoint_identity_default_github_is_empty(self):
        # Canonical default endpoint maps to "" → byte-for-byte backward compat.
        assert endpoint_identity("github_models",
                                 "https://models.github.ai/inference") == ""
        # Trailing slash is normalized to the same "" namespace.
        assert endpoint_identity("github_models",
                                 "https://models.github.ai/inference/") == ""

    def test_endpoint_identity_discriminates_provider_and_port(self):
        gh = endpoint_identity("github_models", "https://models.github.ai/inference")
        px1 = endpoint_identity("copilot_proxy", "http://127.0.0.1:8313/v1")
        px2 = endpoint_identity("copilot_proxy", "http://127.0.0.1:8787/v1")
        assert px1 != gh
        assert px1 != px2
        assert px2 != gh

    def test_job_key_namespaced_by_endpoint(self):
        base = job_key("t1", "single", "tested_agents", "gpt-4o-mini", 42)
        px = job_key("t1", "single", "tested_agents", "gpt-4o-mini", 42,
                     endpoint=endpoint_identity("copilot_proxy", "http://127.0.0.1:8313/v1"))
        assert base != px, "same 5-dim job under a different endpoint must differ"

    def test_default_key_is_byte_identical_to_prefix_5field(self):
        """BLOCKER byte-compat: default (endpoint="") key MUST equal the exact
        pre-fix 5-field null-separated string — no leading endpoint dimension."""
        expected = "t\x00single\x00tested_agents\x00m\x001"
        assert job_key("t", "single", "tested_agents", "m", 1) == expected
        assert job_key("t", "single", "tested_agents", "m", 1, endpoint="") == expected
        run = make_run("t", "single", "tested_agents", "m", seed=1)
        assert run_identity(run) == expected
        assert run_identity(run, endpoint="") == expected

    def test_default_records_have_no_endpoint_field(self, tmp_path):
        """Default-provider (endpoint="") checkpoint records must NOT carry an
        'endpoint' key — byte-for-byte identical to the pre-change format."""
        cp = tmp_path / "cp.jsonl"
        store = CheckpointStore(cp)  # endpoint="" (default)
        store.mark_job_done("t1", "single", "tested_agents", "gpt-4o-mini", 42)
        run = make_run("t1", "single", "tested_agents", "gpt-4o-mini", seed=42)
        store.add_run(run)
        for line in cp.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            assert "endpoint" not in rec, f"default record must omit endpoint: {rec}"

    def test_nondefault_records_persist_endpoint_field(self, tmp_path):
        """A non-default endpoint MUST be persisted so it survives resume."""
        cp = tmp_path / "cp.jsonl"
        ep = endpoint_identity("copilot_proxy", "http://127.0.0.1:8313/v1")
        store = CheckpointStore(cp, endpoint=ep)
        store.mark_job_done("t1", "single", "tested_agents", "gpt-4o-mini", 42)
        recs = [json.loads(l) for l in cp.read_text(encoding="utf-8").splitlines()]
        assert any(r.get("endpoint") == ep for r in recs)

    def test_endpoint_identity_preserves_path_case(self):
        """MAJOR: path case is significant — /API and /api must NOT collide."""
        upper = endpoint_identity("copilot_proxy", "http://127.0.0.1:8313/API")
        lower = endpoint_identity("copilot_proxy", "http://127.0.0.1:8313/api")
        assert upper != lower, "case-sensitive URL paths must yield distinct endpoints"
        # But scheme + host ARE case-insensitive → same namespace.
        a = endpoint_identity("copilot_proxy", "HTTP://127.0.0.1:8313/v1")
        b = endpoint_identity("copilot_proxy", "http://127.0.0.1:8313/v1")
        assert a == b, "scheme/host case must be normalized (case-insensitive)"

    def test_store_namespaces_markers_by_endpoint(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        ep_gh = endpoint_identity("github_models", "https://models.github.ai/inference")
        ep_px = endpoint_identity("copilot_proxy", "http://127.0.0.1:8313/v1")

        gh_store = CheckpointStore(cp, endpoint=ep_gh)
        gh_store.mark_job_done("t1", "single", "tested_agents", "gpt-4o-mini", 42)

        # A store for the proxy endpoint on the SAME file must NOT see it done.
        px_store = CheckpointStore(cp, endpoint=ep_px)
        assert not px_store.job_done("t1", "single", "tested_agents", "gpt-4o-mini", 42)
        # The github endpoint store (reloaded) still sees it done.
        assert CheckpointStore(cp, endpoint=ep_gh).job_done(
            "t1", "single", "tested_agents", "gpt-4o-mini", 42)

    def test_resume_does_not_skip_second_provider_job(self, tmp_path):
        """End-to-end: run a job on copilot_proxy, then github_models on the SAME
        checkpoint must RE-RUN (not skip) the identical (task,config,role,model,seed).
        """
        cp = tmp_path / "cp.jsonl"

        # First run: copilot_proxy provider (offline fake execution).
        runner_px, _ = _make_runner(
            [make_task("t1")], tmp_path, checkpoint_path=cp,
            configs=["single"], seeds=[42], provider="copilot_proxy",
        )
        res_px = runner_px.run()
        assert res_px["completed"] == 1 and res_px["skipped"] == 0

        # Second run: default github_models on the SAME checkpoint file.
        runner_gh, _ = _make_runner(
            [make_task("t1")], tmp_path, checkpoint_path=cp,
            configs=["single"], seeds=[42],  # provider=None → github_models default
        )
        res_gh = runner_gh.run()
        assert res_gh["completed"] == 1, "different provider must NOT be false-skipped"
        assert res_gh["skipped"] == 0

        # Re-running the proxy provider now DOES skip (its marker is present).
        runner_px2, _ = _make_runner(
            [make_task("t1")], tmp_path, checkpoint_path=cp,
            configs=["single"], seeds=[42], provider="copilot_proxy",
        )
        res_px2 = runner_px2.run()
        assert res_px2["completed"] == 0 and res_px2["skipped"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER FIX (MAJOR): provider-aware live guard (token only when required)
# ═══════════════════════════════════════════════════════════════════════════════

class TestProviderAwareLiveGuard:
    """A copilot_proxy live run needs NO token; github_models still requires one."""

    def test_live_ok_requires_runner_live_env(self, monkeypatch):
        monkeypatch.delenv("RUNNER_LIVE", raising=False)
        assert _live_ok(require_auth=False) is False
        assert _live_ok(require_auth=True) is False

    def test_live_ok_proxy_no_token_not_skipped(self, monkeypatch):
        monkeypatch.setenv("RUNNER_LIVE", "1")
        monkeypatch.delenv("GITHUB_MODELS_TOKEN", raising=False)
        monkeypatch.delenv("GH_MODELS_TOKEN", raising=False)
        # require_auth=False (copilot_proxy) → live proceeds without a token.
        assert _live_ok(require_auth=False) is True

    def test_live_ok_github_no_token_still_skips(self, monkeypatch):
        monkeypatch.setenv("RUNNER_LIVE", "1")
        monkeypatch.delenv("GITHUB_MODELS_TOKEN", raising=False)
        monkeypatch.delenv("GH_MODELS_TOKEN", raising=False)
        # require_auth=True (github_models) → still skipped without a token.
        assert _live_ok(require_auth=True) is False

    def test_live_ok_github_with_token_ok(self, monkeypatch):
        monkeypatch.setenv("RUNNER_LIVE", "1")
        monkeypatch.setenv("GITHUB_MODELS_TOKEN", "FAKE_TOKEN_FOR_TEST")
        assert _live_ok(require_auth=True) is True

    def test_provider_require_auth_resolution(self):
        """The provider's require_auth (used by the guard) matches expectations."""
        from common.config import load_config
        from common.llm import resolve_provider_config
        cfg = load_config()
        assert resolve_provider_config(cfg, provider="github_models")["require_auth"] is True
        assert resolve_provider_config(cfg, provider="copilot_proxy")["require_auth"] is False
