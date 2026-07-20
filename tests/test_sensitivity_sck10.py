"""Offline tests for scripts/sensitivity_sck10.py (A08 §2 secondary).

# Auditor model family: GPT (Law 6 — implementer = Claude/Anthropic)

All tests run FULLY OFFLINE — zero network calls, zero token use.
RUNNER_LIVE is NEVER set in the test suite.

Coverage:
  1. Guard: RUNNER_LIVE unset → main() prints "skipped" and exits 0.
  2. Grid is restricted to sc config only (no single/MAD/verifier/etc.).
  3. k=10 propagates through config_kwargs to the runner's run_task call.
  4. Gate C cardinality constant for sc at k=10 = 10 (not 5).
  5. Dry-run enumerates ONLY sc-config jobs at k=10 with the correct total.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Load scripts/sensitivity_sck10.py via spec (not a package)
_DRIVER_PATH = _REPO_ROOT / "scripts" / "sensitivity_sck10.py"
_spec = importlib.util.spec_from_file_location("sensitivity_sck10", _DRIVER_PATH)
_driver = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_driver)  # type: ignore[union-attr]

from common.schema import Interpretation, Task


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_task(task_id: str, regime: str = "H1_external", k: int = 1) -> Task:
    return Task(
        id=task_id,
        domain="code_spec",
        prompt=f"prompt {task_id}",
        latent_spec="spec",
        interpretations=[
            Interpretation(id="I0", is_target=True, gold_check="g0"),
            Interpretation(id="I1", is_target=False, gold_check="g1"),
            Interpretation(id="I_perp", is_target=False, gold_check="gp"),
        ],
        ambiguity_level=k,
        key_questions=["q?"],
        regime=regime,
    )


# ── 1. Guard tests ────────────────────────────────────────────────────────────

class TestGuard:
    """RUNNER_LIVE guard: offline → main() skips and exits 0."""

    def test_main_skips_without_runner_live(self, monkeypatch):
        monkeypatch.delenv("RUNNER_LIVE", raising=False)
        with pytest.raises(SystemExit) as exc:
            _driver.main([])
        assert exc.value.code == 0

    def test_main_exits_0_not_1_when_guard_fails(self, monkeypatch):
        """Guard failure must be a clean skip (exit 0), never an error exit."""
        monkeypatch.delenv("RUNNER_LIVE", raising=False)
        with pytest.raises(SystemExit) as exc:
            _driver.main([])
        assert exc.value.code == 0

    def test_dry_run_does_not_require_runner_live(self, tmp_path, monkeypatch):
        """--dry-run must enumerate the grid without RUNNER_LIVE or network."""
        monkeypatch.delenv("RUNNER_LIVE", raising=False)
        from common.config import load_config
        cfg = load_config()
        tasks = [_make_task("t1")]
        # Should complete without raising SystemExit
        result = _driver.run(
            tasks,
            cfg,
            checkpoint_path=str(tmp_path / "cp.jsonl"),
            cache_dir=str(tmp_path / "cache"),
            rpm=0,
            seeds=[0],
            dry_run=True,
            offline=True,
        )
        assert "total" in result


# ── 2. sc-config-only grid ────────────────────────────────────────────────────

class TestSCOnlyGrid:
    """Grid must contain ONLY the sc config."""

    def test_grid_contains_only_sc(self, tmp_path):
        from common.config import load_config
        cfg = load_config()
        tasks = [_make_task("t1"), _make_task("t2")]

        result = _driver.run(
            tasks,
            cfg,
            checkpoint_path=str(tmp_path / "cp.jsonl"),
            cache_dir=str(tmp_path / "cache"),
            rpm=0,
            seeds=[0],
            dry_run=True,
            offline=True,
        )

        pending_configs = {j["config"] for j in result["pending_jobs"]}
        assert pending_configs == {"sc"}, (
            f"Expected only sc in grid; got: {pending_configs}"
        )

    def test_no_confirmatory_configs_in_grid(self, tmp_path):
        """single/MAD/verifier/interpretation-diverse must NOT appear."""
        from common.config import load_config
        cfg = load_config()
        tasks = [_make_task("t1")]

        result = _driver.run(
            tasks,
            cfg,
            checkpoint_path=str(tmp_path / "cp.jsonl"),
            cache_dir=str(tmp_path / "cache"),
            rpm=0,
            seeds=[0],
            dry_run=True,
            offline=True,
        )

        banned = {"single", "homogeneous-MAD", "heterogeneous-MAD",
                  "verifier", "interpretation-diverse"}
        for job in result["pending_jobs"]:
            assert job["config"] not in banned, (
                f"Non-sc config in sc-only grid: {job['config']}"
            )

    def test_configs_constant_is_sc_only(self):
        assert _driver._CONFIGS_SCK10 == ["sc"]


# ── 3. k=10 propagation ───────────────────────────────────────────────────────

class TestK10Propagation:
    """k=10 must propagate via config_kwargs to the runner's run_task invocation."""

    def test_config_kwargs_constant_has_k10(self):
        assert _driver._CONFIG_KWARGS_SCK10 == {"sc": {"k": 10}}

    def test_config_kwargs_not_k5(self):
        """Confirm k=10 is NOT the frozen confirmatory value (k=5)."""
        assert _driver._CONFIG_KWARGS_SCK10["sc"]["k"] != 5

    def test_k10_delivered_to_run_task(self, tmp_path):
        """Runner must call run_task with k=10 (not k=5 or omitted)."""
        from common.config import load_config
        from common.llm import LLMClient
        from common.schema import AgentRun
        from harness.runner import Runner, RunnerConfig

        received_kwargs: List[Dict[str, Any]] = []

        def fake_run_task(task, config, client, **kwargs):
            received_kwargs.append({"config": config, **kwargs})
            k = kwargs.get("k", 5)
            return [
                AgentRun(
                    task_id=task.id,
                    config=config,
                    model_role="tested_agents",
                    model_id="gpt-5.4",
                    output=f"out_{i}",
                    label="I1",
                    verbalized_conf=0.5,
                    logit_conf=None,
                    seed=i,
                )
                for i in range(k)
            ]

        def fake_label(run, task):
            return "I1"

        cfg = load_config()
        client = LLMClient(cfg, cache_dir=str(tmp_path / "cache"), offline=True)

        runner_cfg = RunnerConfig(
            tasks=[_make_task("t1")],
            configs=["sc"],
            seeds=[0],
            models=[("tested_agents", "gpt-5.4")],
            checkpoint_path=tmp_path / "cp.jsonl",
            rpm=0,
            config_kwargs={"sc": {"k": 10}},
        )
        runner = Runner(
            runner_cfg,
            client,
            run_task_fn=fake_run_task,
            label_run_fn=fake_label,
        )
        runner.run()

        assert len(received_kwargs) == 1, "Expected exactly 1 sc job"
        assert received_kwargs[0]["k"] == 10, (
            f"Expected k=10 forwarded to run_task; got k={received_kwargs[0].get('k')}"
        )

    def test_run_function_passes_k10_config_kwargs(self, tmp_path):
        """_driver.run() passes _CONFIG_KWARGS_SCK10 (k=10) to build_runner."""
        from common.config import load_config
        from common.schema import AgentRun
        from harness.runner import Runner, RunnerConfig
        from common.llm import LLMClient

        received_k: List[int] = []

        def fake_run_task(task, config, client, **kwargs):
            k = kwargs.get("k", 5)
            received_k.append(k)
            return [
                AgentRun(
                    task_id=task.id, config=config,
                    model_role="tested_agents", model_id="gpt-5.4",
                    output=f"out_{i}", label="I1", verbalized_conf=0.5,
                    logit_conf=None, seed=i,
                )
                for i in range(k)
            ]

        cfg = load_config()
        client = LLMClient(cfg, cache_dir=str(tmp_path / "cache"), offline=True)

        runner_cfg = RunnerConfig(
            tasks=[_make_task("ta")],
            configs=["sc"],
            seeds=[0],
            models=[("tested_agents", "gpt-5.4")],
            checkpoint_path=tmp_path / "cp2.jsonl",
            rpm=0,
            config_kwargs=_driver._CONFIG_KWARGS_SCK10,
        )
        runner = Runner(
            runner_cfg,
            client,
            run_task_fn=fake_run_task,
            label_run_fn=lambda r, t: "I1",
        )
        runner.run()

        assert received_k == [10], f"Expected [10]; got {received_k}"


# ── 4. Gate C cardinality ─────────────────────────────────────────────────────

class TestGateCCardinality:
    """Gate C cardinality for sc at k=10 must be 10."""

    def test_gate_c_sc_is_10(self):
        assert _driver._GATE_C_SCK10["sc"] == 10

    def test_gate_c_is_not_confirmatory_k5(self):
        assert _driver._GATE_C_SCK10["sc"] != 5

    def test_gate_c_constant_type(self):
        assert isinstance(_driver._GATE_C_SCK10, dict)
        assert "sc" in _driver._GATE_C_SCK10


# ── 5. Dry-run job total ──────────────────────────────────────────────────────

class TestDryRunJobTotal:
    """Dry-run enumerates sc-only jobs: n_tasks × n_models × n_seeds."""

    def test_dry_run_total_with_small_grid(self, tmp_path):
        """2 tasks × 2 models × 1 seed = 2 sc jobs."""
        from common.config import load_config
        from common.llm import LLMClient
        from harness.runner import Runner, RunnerConfig

        cfg = load_config()
        client = LLMClient(
            cfg,
            cache_dir=str(tmp_path / "cache"),
            offline=True,
        )
        runner_cfg = RunnerConfig(
            tasks=[_make_task("t1"), _make_task("t2")],
            configs=["sc"],
            seeds=[42],
            models=[("tested_agents", "gpt-5.4"), ("tested_agents", "gpt-4o-mini")],
            checkpoint_path=tmp_path / "cp.jsonl",
            rpm=0,
            config_kwargs=_driver._CONFIG_KWARGS_SCK10,
        )
        runner = Runner(runner_cfg, client)
        result = runner.run(dry_run=True)

        assert result["total"] == 2 * 2 * 1, (
            f"Expected 4 jobs (2 tasks × 2 models × 1 seed); got {result['total']}"
        )

    def test_dry_run_full_confirmatory_grid(self, tmp_path):
        """54 tasks × 7 frontier models × 3 seeds = 1134 sc-only jobs."""
        from scripts.registered_run import FRONTIER_SINGLE_MODELS, load_tasks
        from common.config import load_config

        cfg = load_config()
        try:
            tasks = load_tasks()  # all 3 domains
        except Exception:
            pytest.skip("Bench data unavailable; skipping full-grid count test")

        global_seed = cfg.get("seeds", {}).get("global", 20260713)
        seeds = [global_seed, global_seed + 1000, global_seed + 2000]

        result = _driver.run(
            tasks,
            cfg,
            checkpoint_path=str(tmp_path / "cp_full.jsonl"),
            cache_dir=str(tmp_path / "cache_full"),
            rpm=0,
            seeds=seeds,
            dry_run=True,
            offline=True,
        )

        n_tasks = len(tasks)
        n_models = len(FRONTIER_SINGLE_MODELS)
        n_seeds = len(seeds)
        expected = n_tasks * n_models * n_seeds

        assert result["total"] == expected, (
            f"Expected {expected} sc-only k=10 jobs "
            f"({n_tasks} tasks × {n_models} models × {n_seeds} seeds); "
            f"got {result['total']}"
        )

# ── 6. Gate C validation ──────────────────────────────────────────────────────

class TestGateCValidation:
    """Driver-local Gate C cardinality validation for sc at k=10.

    Tests:
      - 5-agent completed job → validation flags it (non-vacuous)
      - 10-agent completed job → validation passes
      - run() raises RuntimeError when Gate C detects a <10-agent job
    """

    @staticmethod
    def _write_checkpoint(path: Path, records: list) -> None:
        import json
        with open(path, "w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec) + "\n")

    @staticmethod
    def _run_rec(task_id: str, model_id: str, grid_seed: int, agent_idx: int) -> dict:
        rec: dict = {
            "type": "run",
            "task_id": task_id,
            "config": "sc",
            "model_role": "tested_agents",
            "model_id": model_id,
            "seed": grid_seed + agent_idx,  # per-agent seed
            "output": f"out_{agent_idx}",
            "label": "I1",
            "verbalized_conf": 0.5,
            "logit_conf": None,
        }
        # Persist replicate_seed only when it differs from per-agent seed
        # (mirrors CheckpointStore.add_run behaviour)
        if agent_idx != 0:
            rec["replicate_seed"] = grid_seed
        return rec

    @staticmethod
    def _job_done_rec(task_id: str, model_id: str, seed: int) -> dict:
        return {
            "type": "job_done",
            "task_id": task_id,
            "config": "sc",
            "model_role": "tested_agents",
            "model_id": model_id,
            "seed": seed,
        }

    def test_5_agents_flags_violation(self, tmp_path):
        """Completed sc job with only 5 agents must be flagged as a violation."""
        cp = tmp_path / "cp.jsonl"
        records = [
            *[self._run_rec("t1", "gpt-4o", 0, i) for i in range(5)],
            self._job_done_rec("t1", "gpt-4o", 0),
        ]
        self._write_checkpoint(cp, records)

        result = _driver._validate_gate_c_sck10(str(cp), min_agents=10)

        assert not result["passed"], (
            "Gate C must fail for a 5-agent sc job — got passed=True"
        )
        assert len(result["violations"]) == 1
        v = result["violations"][0]
        assert v["agent_count"] == 5
        assert v["expected"] == 10
        assert v["task_id"] == "t1"
        assert v["model_id"] == "gpt-4o"

    def test_10_agents_passes(self, tmp_path):
        """Completed sc job with exactly 10 agents must pass Gate C."""
        cp = tmp_path / "cp.jsonl"
        records = [
            *[self._run_rec("t1", "gpt-4o", 0, i) for i in range(10)],
            self._job_done_rec("t1", "gpt-4o", 0),
        ]
        self._write_checkpoint(cp, records)

        result = _driver._validate_gate_c_sck10(str(cp), min_agents=10)

        assert result["passed"], f"Gate C must pass for 10-agent job; got {result}"
        assert result["violations"] == []
        assert result["checked"] == 1

    def test_foreign_endpoint_runs_dont_count(self, tmp_path):
        """5 same-endpoint + 5 foreign-endpoint runs must flag Gate C violation.

        Non-vacuous: if Gate C matched only on (task_id, model_id, seed) the
        foreign-endpoint runs would inflate the count to 10 and the assertion
        would fail (passed=True instead of passed=False).
        """
        cp = tmp_path / "cp_ep.jsonl"

        # 5 matching runs (no endpoint field → default endpoint "")
        same_ep = [self._run_rec("t1", "gpt-4o", 0, i) for i in range(5)]

        # 5 foreign-endpoint runs — same task/model/seed but different endpoint
        foreign_ep = []
        for i in range(5):
            rec = self._run_rec("t1", "gpt-4o", 0, i + 5)
            rec["endpoint"] = "github_models\x00https://models.github.ai/inference"
            foreign_ep.append(rec)

        # job_done has no endpoint → matches only the 5 same-endpoint runs
        job_done = self._job_done_rec("t1", "gpt-4o", 0)

        self._write_checkpoint(cp, same_ep + foreign_ep + [job_done])

        result = _driver._validate_gate_c_sck10(str(cp), min_agents=10)

        assert not result["passed"], (
            "Gate C must fail: foreign-endpoint runs must not count toward "
            "the same-endpoint job identity"
        )
        assert len(result["violations"]) == 1
        v = result["violations"][0]
        assert v["agent_count"] == 5, (
            f"Only 5 same-identity runs should count; got agent_count={v['agent_count']}"
        )

    def test_foreign_model_role_runs_dont_count(self, tmp_path):
        """5 same-role + 5 foreign-model_role runs must flag Gate C violation.

        Non-vacuous: if Gate C matched only on (task_id, model_id, seed) the
        foreign-role runs would inflate the count to 10 and the assertion
        would fail (passed=True instead of passed=False).
        """
        cp = tmp_path / "cp_role.jsonl"

        # 5 matching runs (model_role="tested_agents")
        same_role = [self._run_rec("t1", "gpt-4o", 0, i) for i in range(5)]

        # 5 foreign-role runs — same task/model/seed but different model_role
        foreign_role = []
        for i in range(5):
            rec = self._run_rec("t1", "gpt-4o", 0, i + 5)
            rec["model_role"] = "judge_agents"
            foreign_role.append(rec)

        # job_done has model_role="tested_agents" → matches only the 5 same-role runs
        job_done = self._job_done_rec("t1", "gpt-4o", 0)

        self._write_checkpoint(cp, same_role + foreign_role + [job_done])

        result = _driver._validate_gate_c_sck10(str(cp), min_agents=10)

        assert not result["passed"], (
            "Gate C must fail: foreign-model_role runs must not count toward "
            "the tested_agents job identity"
        )
        assert len(result["violations"]) == 1
        v = result["violations"][0]
        assert v["agent_count"] == 5, (
            f"Only 5 same-role runs should count; got agent_count={v['agent_count']}"
        )

    def test_run_raises_on_partial_job(self, tmp_path):
        """run() must raise RuntimeError when Gate C finds a <10-agent sc job.

        Non-vacuous: if _validate_gate_c_sck10 were removed from run() this
        assertion would fail because no RuntimeError would be raised.
        """
        from common.config import load_config
        from common.schema import AgentRun
        from harness.runner import Runner, RunnerConfig
        from common.llm import LLMClient

        cp_path = tmp_path / "cp_partial.jsonl"

        def fake_run_task(task, config, client, **kwargs):
            # Deliberately return only 5 agents — simulates a partial/stale job
            return [
                AgentRun(
                    task_id=task.id,
                    config=config,
                    model_role="tested_agents",
                    model_id="gpt-4o",
                    output=f"out_{i}",
                    label="I1",
                    verbalized_conf=0.5,
                    logit_conf=None,
                    seed=i,
                )
                for i in range(5)
            ]

        cfg = load_config()
        client = LLMClient(cfg, cache_dir=str(tmp_path / "cache"), offline=True)
        runner_cfg = RunnerConfig(
            tasks=[_make_task("t1")],
            configs=["sc"],
            seeds=[0],
            models=[("tested_agents", "gpt-4o")],
            checkpoint_path=cp_path,
            rpm=0,
            config_kwargs={"sc": {"k": 5}},
        )
        runner = Runner(
            runner_cfg,
            client,
            run_task_fn=fake_run_task,
            label_run_fn=lambda r, t: "I1",
        )

        with pytest.raises(RuntimeError, match="Gate C"):
            _driver.run(
                [_make_task("t1")],
                cfg,
                checkpoint_path=str(cp_path),
                cache_dir=str(tmp_path / "cache"),
                seeds=[0],
                dry_run=False,
                offline=False,
                _runner_override=(runner, client),
            )

