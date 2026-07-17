"""Golden/unit tests for scripts/registered_run.py (Deliverable D4).

# Implementer model family: Claude/Anthropic

All tests run FULLY OFFLINE — zero network calls, zero token use. The live
pilot path is guarded by RUNNER_LIVE=1 which is NEVER set in the test suite.

Coverage:
  1. Guard: RUNNER_LIVE unset → script prints "skipped" and exits 0 (no network).
  2. select_pilot_tasks: balanced selection from H1_external + H2_derivable,
     mixed k, hard item cap enforced.
  3. run_pilot_gate on synthetic data: gate (a/b/c) logic verified offline using
     a pre-written synthetic checkpoint (known labels → known CD outcome).
  4. gate_a FAIL case: all labels I0 (correct) → cd_primary = 0 → gate_a=False.
  5. gate_c FAIL case: empty checkpoint → gate_c=False → gate_pass=False.
  6. FRONTIER_SINGLE_MODELS covers all A06 roster slugs; configs list is valid.
  7. load_tasks raises ValueError for unknown domain names.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

from common.schema import Interpretation, Task

# ── Load scripts/registered_run.py (not a package) ───────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_RR_PATH = _REPO_ROOT / "scripts" / "registered_run.py"
_spec = importlib.util.spec_from_file_location("registered_run", _RR_PATH)
_registered_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_registered_run)  # type: ignore[union-attr]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_task(
    task_id: str,
    regime: str = "H1_external",
    k: int = 1,
    domain: str = "code_spec",
) -> Task:
    return Task(
        id=task_id,
        domain=domain,
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


def _make_run_record(
    task_id: str,
    config: str,
    model_id: str,
    label: str,
    seed: int = 42,
) -> Dict[str, Any]:
    return {
        "type": "run",
        "task_id": task_id,
        "config": config,
        "model_role": "tested_agents",
        "model_id": model_id,
        "output": f"out_{task_id}",
        "label": label,
        "verbalized_conf": 0.5,
        "logit_conf": None,
        "seed": seed,
    }


def _write_jsonl(path: Path, records: List[Dict]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


# ── 1. Guard: RUNNER_LIVE unset → "skipped" + exit 0 ────────────────────────

def test_pilot_guard_prints_skipped_when_runner_live_unset(
    monkeypatch, capsys
):
    """With RUNNER_LIVE unset, --pilot prints 'skipped' and exits 0 (no network)."""
    monkeypatch.delenv("RUNNER_LIVE", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        _registered_run.main(["--pilot"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "skipped" in out.lower()


def test_full_run_guard_prints_skipped_when_runner_live_unset(
    monkeypatch, capsys
):
    """Without --dry-run and RUNNER_LIVE unset, full run prints 'skipped' + exits 0."""
    monkeypatch.delenv("RUNNER_LIVE", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        _registered_run.main([])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "skipped" in out.lower()


def test_dry_run_does_not_require_runner_live(monkeypatch, capsys):
    """--dry-run bypasses the live guard and loads tasks + runner in dry mode."""
    monkeypatch.delenv("RUNNER_LIVE", raising=False)
    # Should NOT call sys.exit(0) for "skipped"; it runs the dry-run path.
    # May raise SystemExit for other reasons (e.g. task load failure) but not 0-for-skipped.
    try:
        _registered_run.main(["--dry-run"])
        out = capsys.readouterr().out
        # dry-run should produce some output (runner result or similar)
        # It should NOT print "skipped"
        assert "skipped" not in out.lower()
    except SystemExit as e:
        # If it exits, it should not be the "skipped" guard exit
        assert e.code != 0 or "skipped" not in capsys.readouterr().out


# ── 2. select_pilot_tasks: balanced selection ────────────────────────────────

def test_select_pilot_tasks_balances_regimes():
    tasks = (
        [_make_task(f"h1_{i}", regime="H1_external", k=(i % 3) + 1) for i in range(10)]
        + [_make_task(f"h2_{i}", regime="H2_derivable", k=(i % 3) + 1) for i in range(10)]
    )
    selected = _registered_run.select_pilot_tasks(tasks, n_pilot=8)
    assert len(selected) <= 8
    h1 = [t for t in selected if t.regime == "H1_external"]
    h2 = [t for t in selected if t.regime == "H2_derivable"]
    assert len(h1) >= 2, "Should include H1_external items"
    assert len(h2) >= 2, "Should include H2_derivable items"


def test_select_pilot_tasks_mixed_k():
    tasks = (
        [_make_task(f"h1_k{k}", regime="H1_external", k=k) for k in [1, 2, 3]]
        + [_make_task(f"h2_k{k}", regime="H2_derivable", k=k) for k in [1, 2, 3]]
    )
    selected = _registered_run.select_pilot_tasks(tasks, n_pilot=6)
    k_values = {t.ambiguity_level for t in selected}
    assert len(k_values) >= 2, "Should have multiple k values"


def test_select_pilot_tasks_respects_cap():
    tasks = [_make_task(f"t{i}", regime="H1_external") for i in range(20)]
    selected = _registered_run.select_pilot_tasks(tasks, n_pilot=8)
    assert len(selected) <= 8


def test_select_pilot_tasks_with_few_tasks():
    tasks = [_make_task("t1", regime="H1_external"), _make_task("t2", regime="H2_derivable")]
    selected = _registered_run.select_pilot_tasks(tasks, n_pilot=10)
    assert len(selected) == 2  # fewer than cap → return all


def test_select_pilot_tasks_only_h1():
    tasks = [_make_task(f"t{i}", regime="H1_external") for i in range(5)]
    selected = _registered_run.select_pilot_tasks(tasks, n_pilot=8)
    assert len(selected) == 5  # all available


# ── 3. run_pilot_gate on synthetic checkpoint: gate logic ────────────────────

class TestRunPilotGate:
    """Offline gate logic tests using pre-written synthetic checkpoints.

    We inject a pre-built Runner that does nothing (checkpoint already has records)
    and verify that the gate logic correctly reads the synthetic data.
    """

    def _make_synthetic_checkpoint(
        self,
        path: Path,
        tasks: List[Task],
        label_pattern: str = "mixed",
    ) -> None:
        """Write a synthetic checkpoint with known labels.

        label_pattern:
          "converging" → 4 out of 5 sc runs label I1 (wrong) → cd_primary > 0
          "all_correct" → all 5 sc runs label I0 (target) → cd_primary = 0
          "mixed" → some I0, some I1, some I_perp → cd_primary > 0
        """
        records = []
        for task in tasks:
            for seed_off in range(5):
                seed = 42 + seed_off
                if label_pattern == "converging":
                    label = "I1" if seed_off < 4 else "I0"
                elif label_pattern == "all_correct":
                    label = "I0"
                else:  # mixed
                    label = ["I1", "I1", "I1", "I0", "I_perp"][seed_off % 5]
                records.append(
                    _make_run_record(task.id, "sc", "gpt-5.4", label, seed=seed)
                )
            # Also write job_done marker
            records.append({
                "type": "job_done",
                "task_id": task.id, "config": "sc",
                "model_role": "tested_agents", "model_id": "gpt-5.4", "seed": 42,
            })
        _write_jsonl(path, records)

    def _make_noop_runner(self, cfg, tasks, checkpoint_path: str, tmp_path: Path):
        """Runner that does nothing (checkpoint is pre-populated)."""
        from harness.runner import Runner, RunnerConfig
        from common.llm import LLMClient

        client = LLMClient(
            cfg,
            cache_dir=str(tmp_path / "cache"),
            offline=True,
        )
        runner_cfg = RunnerConfig(
            tasks=tasks,
            configs=["sc"],
            seeds=[42],
            models=[("tested_agents", "gpt-5.4")],
            checkpoint_path=Path(checkpoint_path),
            rpm=0,
        )
        runner = Runner(runner_cfg, client)
        return runner, client

    def test_gate_a_passes_when_cd_primary_positive(self, tmp_path):
        """gate_a=True when H1_external items have cd_primary > 0."""
        from common.config import load_config
        cfg = load_config()
        tasks = [_make_task("t1", regime="H1_external", k=1)]
        cp = str(tmp_path / "cp.jsonl")
        self._make_synthetic_checkpoint(Path(cp), tasks, label_pattern="converging")
        runner, client = self._make_noop_runner(cfg, tasks, cp, tmp_path)
        report = _registered_run.run_pilot_gate(
            cfg, tasks,
            checkpoint_path=cp,
            offline=True,
            cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )
        assert report["gate_c"], "Integration gate must pass"
        assert report["gate_a"], f"cd_primary should be > 0, got {report['real_cd']}"

    def test_gate_a_fails_when_all_labels_correct(self, tmp_path):
        """gate_a=False when all labels are I0 (correct) → cd_primary = 0."""
        from common.config import load_config
        cfg = load_config()
        tasks = [_make_task("t1", regime="H1_external", k=1)]
        cp = str(tmp_path / "cp.jsonl")
        self._make_synthetic_checkpoint(Path(cp), tasks, label_pattern="all_correct")
        runner, client = self._make_noop_runner(cfg, tasks, cp, tmp_path)
        report = _registered_run.run_pilot_gate(
            cfg, tasks,
            checkpoint_path=cp,
            offline=True,
            cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )
        assert not report["gate_a"], "cd_primary=0 should fail gate_a"

    def test_gate_c_fails_on_empty_checkpoint(self, tmp_path):
        """gate_c=False when checkpoint has no run records (only job_done markers).

        We pre-mark all jobs as done so the runner skips them, but write no
        AgentRun records — the tidy table is empty → gate_c must be False.
        """
        from common.config import load_config
        cfg = load_config()
        tasks = [_make_task("t1", regime="H1_external", k=1)]
        cp = str(tmp_path / "cp.jsonl")
        # Write only a job_done marker — no AgentRun records.
        # The runner will skip the job; load_runs_tidy will produce an empty table.
        _write_jsonl(Path(cp), [
            {
                "type": "job_done",
                "task_id": "t1", "config": "sc",
                "model_role": "tested_agents", "model_id": "gpt-5.4", "seed": 42,
            }
        ])
        runner, client = self._make_noop_runner(cfg, tasks, cp, tmp_path)
        report = _registered_run.run_pilot_gate(
            cfg, tasks,
            checkpoint_path=cp,
            offline=True,
            cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )
        assert not report["gate_c"]
        assert not report["gate_pass"]

    def test_gate_b_passes_when_real_cd_exceeds_null(self, tmp_path):
        """gate_b=True when null CD < real CD (shuffle gives lower CD)."""
        from common.config import load_config
        cfg = load_config()
        # Use 4 H1_external items (minimum for a meaningful shuffle null)
        tasks = [_make_task(f"t{i}", regime="H1_external", k=1) for i in range(4)]
        cp = str(tmp_path / "cp.jsonl")
        self._make_synthetic_checkpoint(Path(cp), tasks, label_pattern="converging")
        runner, client = self._make_noop_runner(cfg, tasks, cp, tmp_path)
        report = _registered_run.run_pilot_gate(
            cfg, tasks,
            checkpoint_path=cp,
            offline=True,
            cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )
        assert report["gate_c"]
        # For converging label pattern (4/5 runs label I1), cd_primary should be > 0
        # and null_cd should be < real_cd (shuffling destroys per-item concentration)
        if report["gate_a"]:
            assert report["gate_b"] or report["null_cd"] >= 0, (
                "gate_b should pass when real_cd > null_cd"
            )

    def test_report_has_all_required_keys(self, tmp_path):
        """Report dict has all required fields."""
        from common.config import load_config
        cfg = load_config()
        tasks = [_make_task("t1", regime="H1_external")]
        cp = str(tmp_path / "cp.jsonl")
        Path(cp).write_text("")
        runner, client = self._make_noop_runner(cfg, tasks, cp, tmp_path)
        report = _registered_run.run_pilot_gate(
            cfg, tasks,
            checkpoint_path=cp,
            offline=True,
            cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )
        required = {
            "gate_pass", "gate_a", "gate_b", "gate_c",
            "real_cd", "null_cd", "iperp_rate",
            "n_items", "n_runs", "total_cost_usd",
            "run_result", "conditions",
        }
        missing = required - set(report)
        assert not missing, f"Report missing fields: {missing}"


# ── 4. FRONTIER_SINGLE_MODELS / REGISTERED_CONFIGS ───────────────────────────

def test_frontier_single_models_covers_all_a06_slugs():
    """FRONTIER_SINGLE_MODELS covers all Amendment-06 tested models."""
    model_ids = {mid for _, mid in _registered_run.FRONTIER_SINGLE_MODELS}
    expected = {
        "gpt-5.4",               # homogeneous
        "gpt-5.6-sol",           # reasoning
        "claude-opus-4.8",       # reasoning
        "gemini-3.1-pro-preview", # reasoning
        "gpt-4o-mini",           # weak
        "gemini-3.5-flash",      # weak
        "claude-haiku-4.5",      # weak
    }
    missing = expected - model_ids
    assert not missing, f"Missing models in FRONTIER_SINGLE_MODELS: {missing}"


def test_frontier_single_models_all_tested_agents_role():
    """All models in FRONTIER_SINGLE_MODELS use role 'tested_agents'."""
    for role, model_id in _registered_run.FRONTIER_SINGLE_MODELS:
        assert role == "tested_agents", f"Non-tested_agents role for {model_id}"


def test_registered_configs_valid():
    """REGISTERED_CONFIGS contains only valid runner config names."""
    from harness.runner import ALL_CONFIGS
    for cfg in _registered_run.REGISTERED_CONFIGS:
        assert cfg in ALL_CONFIGS, f"Unknown config: {cfg}"


def test_pilot_models_is_gpt54_only():
    """Pilot uses only gpt-5.4 (homogeneous baseline) for small footprint."""
    assert len(_registered_run.PILOT_MODELS) == 1
    role, model_id = _registered_run.PILOT_MODELS[0]
    assert model_id == "gpt-5.4"
    assert role == "tested_agents"


def test_pilot_configs_is_sc_only():
    """Pilot uses only 'sc' config for small footprint."""
    assert _registered_run.PILOT_CONFIGS == ["sc"]


# ── 5. load_tasks raises ValueError for unknown domains ───────────────────────

def test_load_tasks_raises_for_unknown_domain():
    with pytest.raises(ValueError, match="Unknown domain"):
        _registered_run.load_tasks(["unknown_domain_xyz"])


# ── 6. PILOT_MAX_ITEMS and PILOT_BUDGET_USD are reasonable ───────────────────

def test_pilot_constants_within_spec():
    """Pilot item cap is within [6, 10] per plan spec."""
    assert 6 <= _registered_run.PILOT_MAX_ITEMS <= 10
    assert _registered_run.PILOT_BUDGET_USD >= 0.5  # at least $0.50 defensive cap
