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
from typing import Any, Dict, List, Optional

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
    replicate_seed: Optional[int] = None,
) -> Dict[str, Any]:
    rec = {
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
    # Write replicate_seed only when provided and ≠ seed (mirrors runner behaviour).
    if replicate_seed is not None and replicate_seed != seed:
        rec["replicate_seed"] = replicate_seed
    return rec


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
    """A pool with k=1,2,3 items (each singleton) cannot guarantee ≥2 at same k≥1 → raises.

    BLOCKER: the selector MUST raise ValueError when no k≥1 group has ≥2 items.
    Use a pool large enough that the k≥1 k=1 GROUP specifically has ≥2 items.
    """
    tasks = (
        [_make_task(f"h1_k{k}", regime="H1_external", k=k) for k in [1, 2, 3]]
        + [_make_task(f"h2_k{k}", regime="H2_derivable", k=k) for k in [1, 2, 3]]
    )
    # H1 pool: h1_k1 (1 item), h1_k2 (1 item), h1_k3 (1 item) → no k≥1 group with ≥2 items.
    with pytest.raises(ValueError, match="k≥1"):
        _registered_run.select_pilot_tasks(tasks, n_pilot=6)


def test_select_pilot_tasks_mixed_k_enough_pool():
    """A pool with 2+ items at k=1 succeeds and returns mixed k values."""
    tasks = (
        [_make_task(f"h1_k1_{i}", regime="H1_external", k=1) for i in range(3)]
        + [_make_task(f"h1_k2_{i}", regime="H1_external", k=2) for i in range(2)]
        + [_make_task(f"h2_k{k}", regime="H2_derivable", k=k) for k in [1, 2, 3]]
    )
    selected = _registered_run.select_pilot_tasks(tasks, n_pilot=8)
    k_values = {t.ambiguity_level for t in selected}
    assert len(k_values) >= 2, "Should have multiple k values"


def test_select_pilot_tasks_respects_cap():
    tasks = [_make_task(f"t{i}", regime="H1_external") for i in range(20)]
    selected = _registered_run.select_pilot_tasks(tasks, n_pilot=8)
    assert len(selected) <= 8


def test_select_pilot_tasks_with_few_tasks():
    """A pool with only 1 H1 item cannot guarantee ≥2 k≥1 items → raises."""
    tasks = [_make_task("t1", regime="H1_external"), _make_task("t2", regime="H2_derivable")]
    with pytest.raises(ValueError, match="k≥1"):
        _registered_run.select_pilot_tasks(tasks, n_pilot=10)


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

        B1 fix: all 5 per-agent records for each task share replicate_seed=42
        (the grid seed), so they form ONE ensemble cell in compute_cell_cd.
        Without this, each per-agent seed (42+i) would be a separate singleton.
        """
        records = []
        for task in tasks:
            for seed_off in range(5):
                seed = 42 + seed_off
                if label_pattern == "converging":
                    label = "I1" if seed_off < 4 else "I0"
                elif label_pattern == "all_correct":
                    label = "I0"
                elif label_pattern == "all_iperp":
                    label = "I_perp"
                else:  # mixed
                    label = ["I1", "I1", "I1", "I0", "I_perp"][seed_off % 5]
                # replicate_seed=42 groups all 5 agents into ONE ensemble cell.
                records.append(
                    _make_run_record(
                        task.id, "sc", "gpt-5.4", label,
                        seed=seed, replicate_seed=42
                    )
                )
            # job_done marker (grid seed=42)
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

    def test_gate_b_uses_cd_primary_not_false_consensus_rate(self, tmp_path):
        """gate_b null is computed with cd_primary, NOT false_consensus_rate.

        With all-I_perp labels:
          cd_primary(["I_perp"×5], "I0") = 0  (I_perp ineligible as enumerated wrong)
          false_consensus_rate(["I_perp"×5], "I0") = 1.0  (I_perp is modal wrong)

        So null_cd should be ≈ 0 (cd_primary pool) not ≈ 1.0 (false_consensus_rate pool).
        This is the auditor-critical metric-consistency check for BLOCKER 2.
        """
        from common.config import load_config
        cfg = load_config()
        # Use ≥2 tasks so the condition is not INCONCLUSIVE (MIN_ITEMS_FOR_NULL=2).
        tasks = [_make_task(f"t{i}", regime="H1_external", k=1) for i in range(4)]
        cp = str(tmp_path / "cp.jsonl")
        # Write all-I_perp labels with replicate_seed=42 for proper cell grouping.
        records = []
        for task in tasks:
            for seed_off in range(5):
                records.append(
                    _make_run_record(
                        task.id, "sc", "gpt-5.4", "I_perp",
                        seed=42 + seed_off, replicate_seed=42,
                    )
                )
            records.append({
                "type": "job_done",
                "task_id": task.id, "config": "sc",
                "model_role": "tested_agents", "model_id": "gpt-5.4", "seed": 42,
            })
        _write_jsonl(Path(cp), records)
        runner, client = self._make_noop_runner(cfg, tasks, cp, tmp_path)
        report = _registered_run.run_pilot_gate(
            cfg, tasks,
            checkpoint_path=cp,
            offline=True,
            cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )
        # Metric identity check: null_metric must be "cd_primary".
        assert report["null_metric"] == "cd_primary", (
            f"Expected null_metric='cd_primary'; got {report['null_metric']!r}"
        )
        # cd_primary null for all-I_perp labels: pool has no enumerated-wrong labels
        # → cd_primary_shuffle_null = 0.0 for every permutation.
        # false_consensus_rate null would be ≈ 1.0 (I_perp dominates the pool).
        assert report["null_cd"] < 0.05, (
            f"null_cd should be ≈ 0 with cd_primary metric for all-I_perp labels; "
            f"got {report['null_cd']:.4f}.  If > 0.05, the wrong metric was used."
        )

    def test_gate_b_inconclusive_with_single_cell_condition(self, tmp_path):
        """A condition with only 1 ensemble cell is INCONCLUSIVE → gate_b=False.

        gate_b requires ≥ MIN_ITEMS_FOR_NULL cells per condition.  A single item
        makes the cross-item shuffle degenerate (within-cell permutation, no-op).
        """
        from common.config import load_config
        cfg = load_config()
        tasks = [_make_task("t1", regime="H1_external", k=1)]  # only 1 task
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
        # Only 1 cell in the condition → INCONCLUSIVE → gate_b must stay False.
        assert not report["gate_b"], (
            "gate_b must be False when all conditions are INCONCLUSIVE (< 2 cells)"
        )
        # Verify the INCONCLUSIVE status is recorded in gate_b_details.
        details = report.get("gate_b_details", [])
        assert any(d["status"] == "inconclusive" for d in details), (
            f"Expected at least one INCONCLUSIVE entry in gate_b_details; got {details}"
        )

    def test_report_has_all_required_keys(self, tmp_path):
        """Report dict has all required fields (including B2 and M5 additions)."""
        from common.config import load_config
        cfg = load_config()
        tasks = [_make_task("t1", regime="H1_external")]
        cp = str(tmp_path / "cp.jsonl")
        # Write only a job_done marker — runner will skip, tidy empty → gate FAIL.
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
        required = {
            "gate_pass", "gate_a", "gate_b", "gate_c",
            "real_cd", "null_cd", "null_metric",  # null_metric: B2 addition
            "iperp_rate",
            "n_items", "n_runs", "total_cost_usd",
            "run_result", "conditions",
            "gate_b_details",  # per-condition audit trail: B2 addition
        }
        missing = required - set(report)
        assert not missing, f"Report missing fields: {missing}"
        # null_metric must always be "cd_primary" (auditor check).
        assert report["null_metric"] == "cd_primary"


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


def test_pilot_models_covers_all_four_classes():
    """PILOT_MODELS includes all four model classes (MAJOR 4 fix: M4).

    The pilot must exercise homogeneous, reasoning, weak, and heterogeneous
    model_class coverage so the gate validates cross-family execution and
    model_class disambiguation. FRONTIER_SINGLE_MODELS covers the first three;
    heterogeneous-MAD in PILOT_CONFIGS covers the pool config.
    """
    model_ids = {mid for _, mid in _registered_run.PILOT_MODELS}
    # homogeneous
    assert "gpt-5.4" in model_ids
    # reasoning
    assert any(mid in model_ids for mid in ["gpt-5.6-sol", "claude-opus-4.8", "gemini-3.1-pro-preview"])
    # weak
    assert any(mid in model_ids for mid in ["gpt-4o-mini", "gemini-3.5-flash", "claude-haiku-4.5"])


def test_pilot_configs_covers_minimum_required():
    """PILOT_CONFIGS includes at least single + SC + heterogeneous-MAD (MAJOR 4 fix).

    The pilot must enumerate all required method × class combinations.
    """
    configs = _registered_run.PILOT_CONFIGS
    assert "single" in configs, "Pilot must include 'single' config"
    assert "sc" in configs, "Pilot must include 'sc' config"
    assert "heterogeneous-MAD" in configs, "Pilot must include 'heterogeneous-MAD' for pool coverage"


# ── 5. load_tasks raises ValueError for unknown domains ───────────────────────

def test_load_tasks_raises_for_unknown_domain():
    with pytest.raises(ValueError, match="Unknown domain"):
        _registered_run.load_tasks(["unknown_domain_xyz"])


# ── 6. PILOT_MAX_ITEMS and PILOT_BUDGET_USD are reasonable ───────────────────

def test_pilot_constants_within_spec():
    """Pilot item cap is within [6, 10] per plan spec."""
    assert 6 <= _registered_run.PILOT_MAX_ITEMS <= 10
    assert _registered_run.PILOT_BUDGET_USD >= 0.5  # at least $0.50 defensive cap


# ── 7. BLOCKER 3: --pilot --dry-run makes NO network calls ───────────────────

def test_pilot_dry_run_makes_no_network_calls(monkeypatch, capsys):
    """--pilot --dry-run with RUNNER_LIVE unset must not open any network connection.

    BLOCKER 3 fix: dry_run is now threaded through run_pilot_gate → runner.run().
    The guard at main() level only fires for non-dry-run paths; the pilot branch
    now passes dry_run=True to the runner so zero network calls happen.
    The gate reports FAIL (gate_c requires a completed run) but no connection error.
    """
    monkeypatch.delenv("RUNNER_LIVE", raising=False)
    # Should not raise a connection error or print "skipped" (that's the guard
    # for non-dry-run paths only).
    try:
        _registered_run.main(["--pilot", "--dry-run"])
    except SystemExit as exc:
        # Acceptable: gate FAIL exits 1, or task-load issues
        pass
    out, err = capsys.readouterr()
    # MUST NOT print "skipped" — that's the live guard, not the dry-run path.
    assert "skipped" not in out.lower(), (
        "--pilot --dry-run should not print 'skipped' (that's the live guard); "
        "dry_run must thread through to runner.run(dry_run=True)"
    )


def test_dry_run_full_run_does_not_require_runner_live(monkeypatch, capsys):
    """--dry-run (full run) executes without RUNNER_LIVE (no network)."""
    monkeypatch.delenv("RUNNER_LIVE", raising=False)
    try:
        _registered_run.main(["--dry-run"])
        out = capsys.readouterr().out
        assert "skipped" not in out.lower()
    except SystemExit as exc:
        out, err = capsys.readouterr()
        # Should NOT be the "skipped" guard exit
        assert "skipped" not in out.lower()


# ── 8. MAJOR 6: full run requires ≥3 seeds ───────────────────────────────────

def test_full_run_rejects_fewer_than_3_seeds(monkeypatch, capsys):
    """Full run (non-pilot) with < 3 seeds exits 1 with an error about §10.

    MAJOR 6 fix: §10 (pre-registered) requires ≥3 distinct seeds per
    (item × config). Fewer seeds must be rejected loudly.
    """
    monkeypatch.delenv("RUNNER_LIVE", raising=False)
    # Use --dry-run to avoid the live guard, but provide only 1 seed.
    with pytest.raises(SystemExit) as exc_info:
        _registered_run.main(["--dry-run", "--seeds", "42"])
    assert exc_info.value.code == 1, (
        "Expected exit code 1 when < 3 seeds are provided"
    )
    _, err = capsys.readouterr()
    # Error message should mention seeds and/or §10.
    assert "seed" in err.lower() or "3" in err, (
        f"Error message should mention seeds/§10; got: {err!r}"
    )


def test_full_run_rejects_duplicate_seeds(monkeypatch, capsys):
    """Full run with duplicated seeds (fewer than 3 distinct) exits 1."""
    monkeypatch.delenv("RUNNER_LIVE", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        _registered_run.main(["--dry-run", "--seeds", "42", "42", "42"])
    assert exc_info.value.code == 1


def test_full_run_accepts_three_seeds_in_dry_run(monkeypatch, capsys):
    """Full run with exactly 3 distinct seeds proceeds past the seed check."""
    monkeypatch.delenv("RUNNER_LIVE", raising=False)
    try:
        _registered_run.main(["--dry-run", "--seeds", "1", "2", "3"])
        out = capsys.readouterr().out
        assert "skipped" not in out.lower()
    except SystemExit as exc:
        out, err = capsys.readouterr()
        # If it exits, must NOT be the seed-validation error (code 1 + "seed" in err)
        if exc.code == 1:
            assert "seed" not in err.lower(), (
                "exit 1 with 'seed' in stderr means the seed check failed for 3 seeds"
            )


def test_full_run_default_seeds_are_3(monkeypatch, capsys):
    """Default seeds (no --seeds arg) are ≥3 distinct values (MAJOR 6 fix)."""
    monkeypatch.delenv("RUNNER_LIVE", raising=False)
    # --dry-run with no --seeds: should use ≥3 default seeds, not fail.
    try:
        _registered_run.main(["--dry-run"])
        out = capsys.readouterr().out
        # If it succeeded, seeds were ≥3 (otherwise it would have exited 1).
        assert "skipped" not in out.lower()
    except SystemExit as exc:
        _, err = capsys.readouterr()
        # Must NOT exit because of the seed check.
        assert "seed" not in err.lower(), (
            "Default seeds should be ≥3; the seed-count check must not trigger"
        )


# ── 9. BLOCKER D: gate B requires distinct ITEMS, not just cells ─────────────

def test_gate_b_inconclusive_when_two_cells_from_same_item(tmp_path):
    """Two replicate seeds from ONE item produce 2 cells but 1 distinct item.

    BLOCKER D: gate B must require ≥ MIN_ITEMS_FOR_NULL DISTINCT ITEMS (tasks),
    not just ≥ MIN_ITEMS_FOR_NULL cells.  Two replicates of the same task are
    NOT a cross-item shuffle — the shuffle degenerates to a within-item permutation
    and is not informative.  This condition must be INCONCLUSIVE, not PASS.
    """
    from pathlib import Path as _Path
    from common.config import load_config
    from harness.runner import Runner, RunnerConfig
    from common.llm import LLMClient

    cfg = load_config()

    tasks = [_make_task("t1", regime="H1_external", k=1)]
    cp = str(tmp_path / "cp.jsonl")

    # Two replicate seeds from ONE task.  Stride-1000 so per-agent seeds don't overlap.
    records: list = []
    for rep_seed in [42, 1042]:
        for seed_off in range(5):
            records.append(
                _make_run_record(
                    "t1", "sc", "gpt-5.4", "I1",
                    seed=rep_seed + seed_off,
                    replicate_seed=rep_seed,
                )
            )
        records.append({
            "type": "job_done",
            "task_id": "t1", "config": "sc",
            "model_role": "tested_agents", "model_id": "gpt-5.4",
            "seed": rep_seed,
        })
    _write_jsonl(_Path(cp), records)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "cache"), offline=True)
    runner_cfg = RunnerConfig(
        tasks=tasks, configs=["sc"], seeds=[42, 1042],
        models=[("tested_agents", "gpt-5.4")],
        checkpoint_path=_Path(cp), rpm=0,
    )
    runner = Runner(runner_cfg, client)

    report = _registered_run.run_pilot_gate(
        cfg, tasks, checkpoint_path=cp,
        offline=True, cache_dir=str(tmp_path / "llm_cache"),
        _runner_override=(runner, client),
    )

    # 2 cells from the same item → condition is INCONCLUSIVE → gate_b must be False.
    details = report.get("gate_b_details", [])
    assert any(d["status"] == "inconclusive" for d in details), (
        f"Expected INCONCLUSIVE for 2 cells from 1 item; got: {details}"
    )
    assert not report["gate_b"], (
        "gate_b must be False when all conditions are INCONCLUSIVE "
        "(only 1 distinct item, 2 replicate seeds)"
    )


# ── 10. MAJOR E: gate C fails on partial checkpoint (job_done + 1 agent) ─────

def test_gate_c_fails_when_sc_job_has_only_one_agent_record(tmp_path):
    """MAJOR E: gate C must FAIL if an SC job has only 1 run record (< k=5).

    A checkpoint with all job_done markers but only ONE surviving run record
    per SC job is a partial/stale checkpoint.  Gate C must reject it via the
    cardinality check (MAJOR E fix: each SC cell needs ≥ 5 agents).
    """
    from pathlib import Path as _Path
    from common.config import load_config
    from harness.runner import Runner, RunnerConfig
    from common.llm import LLMClient

    cfg = load_config()

    tasks = [_make_task("t1", regime="H1_external", k=1)]
    cp = str(tmp_path / "cp.jsonl")

    # job_done marker + only 1 agent record (SC needs k=5).
    records = [
        _make_run_record("t1", "sc", "gpt-5.4", "I1", seed=42, replicate_seed=42),
        {
            "type": "job_done",
            "task_id": "t1", "config": "sc",
            "model_role": "tested_agents", "model_id": "gpt-5.4", "seed": 42,
        },
    ]
    _write_jsonl(_Path(cp), records)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "cache"), offline=True)
    runner_cfg = RunnerConfig(
        tasks=tasks, configs=["sc"], seeds=[42],
        models=[("tested_agents", "gpt-5.4")],
        checkpoint_path=_Path(cp), rpm=0,
    )
    runner = Runner(runner_cfg, client)

    report = _registered_run.run_pilot_gate(
        cfg, tasks, checkpoint_path=cp,
        offline=True, cache_dir=str(tmp_path / "llm_cache"),
        _runner_override=(runner, client),
    )

    # 1 agent record for SC job (needs 5) → gate_c_cardinality FAILS → gate_c FAILS.
    assert not report["gate_c"], (
        "gate_c must FAIL when an SC job has only 1 surviving agent record (< k=5). "
        "MAJOR E: cardinality check must catch partial/stale checkpoints."
    )
    assert not report["gate_pass"]


# ── 11. MAJOR F: pilot batch has ≥2 H1 items at same k≥1 ─────────────────────

def test_select_pilot_tasks_has_two_h1_items_at_k1_or_higher():
    """MAJOR F: the selected pilot batch must include ≥2 H1_external items at
    the same k≥1 value so gate B has at least one evaluable underspecified
    condition (§11 requires the gate on k≥1 items).
    """
    from collections import Counter

    # Build a pool with 4 H1 items at k=2 (most) + some k=1, k=3.
    h1_tasks = (
        [_make_task(f"h1_k2_{i}", regime="H1_external", k=2) for i in range(4)]
        + [_make_task("h1_k1", regime="H1_external", k=1)]
        + [_make_task("h1_k3", regime="H1_external", k=3)]
    )
    h2_tasks = [_make_task(f"h2_{i}", regime="H2_derivable", k=1) for i in range(4)]
    all_tasks = h1_tasks + h2_tasks

    selected = _registered_run.select_pilot_tasks(all_tasks, n_pilot=10)

    h1_selected = [t for t in selected if t.regime == "H1_external"]
    k_counts = Counter(t.ambiguity_level for t in h1_selected)

    k1_plus_with_two = {k: c for k, c in k_counts.items() if k >= 1 and c >= 2}
    assert k1_plus_with_two, (
        f"Selected pilot batch has no k≥1 H1 group with ≥2 items. "
        f"k_counts={dict(k_counts)}.  "
        "MAJOR F: select_pilot_tasks must guarantee ≥2 H1 items at some k≥1."
    )


def test_select_pilot_tasks_raises_when_no_k1_group_has_two_items():
    """BLOCKER: selector raises ValueError when every k≥1 group has only 1 item.

    The old code fell back to balanced-k selection, silently returning a batch
    where gate B would be INCONCLUSIVE for all conditions (no ≥2-item k≥1 group).
    §11 requires the pilot gate on underspecified items — a batch that can never
    satisfy this is invalid.  The selector must FAIL LOUDLY instead.
    """
    h1_tasks = [
        _make_task("h1_k1", regime="H1_external", k=1),
        _make_task("h1_k2", regime="H1_external", k=2),
        _make_task("h1_k3", regime="H1_external", k=3),
    ]
    with pytest.raises(ValueError, match="k≥1"):
        _registered_run.select_pilot_tasks(h1_tasks, n_pilot=6)


# ── 12. MINOR: dry-run test monkeypatches LLMClient.complete ─────────────────

def test_pilot_dry_run_network_call_count_is_zero(monkeypatch, capsys):
    """MINOR: monkeypatch LLMClient.complete to count invocations; assert 0.

    --pilot --dry-run with RUNNER_LIVE unset must not invoke LLMClient.complete.
    BLOCKER 3 fix verified: dry_run=True threads to runner.run(dry_run=True).
    """
    monkeypatch.delenv("RUNNER_LIVE", raising=False)

    call_count = [0]
    from common import llm as _llm_module

    def _no_network(self, *args, **kwargs):
        call_count[0] += 1
        raise RuntimeError(
            "LLMClient.complete was called during --pilot --dry-run! "
            "BLOCKER 3 regression: dry_run must thread to runner.run(dry_run=True)."
        )

    monkeypatch.setattr(_llm_module.LLMClient, "complete", _no_network)

    try:
        _registered_run.main(["--pilot", "--dry-run"])
    except SystemExit:
        pass  # Gate FAIL exits 1 — acceptable

    out, _err = capsys.readouterr()

    # Primary: zero network calls.
    assert call_count[0] == 0, (
        f"Expected 0 LLMClient.complete calls; got {call_count[0]}. "
        "dry_run must thread through to runner.run(dry_run=True)."
    )
    # Structural: not the live guard path.
    assert "skipped" not in out.lower(), (
        "--pilot --dry-run must not print 'skipped' (that is the live guard, not dry-run)"
    )


# ── 13. BLOCKER: gates A/B restricted to k≥1 (underspecified) items ──────────

def test_gate_a_b_fail_when_all_h1_items_are_k0(tmp_path):
    """BLOCKER: gates A and B must NOT include k=0 H1 items.

    k=0 is the fully-specified CONTROL.  With all H1 items at k=0, both gate_a
    and gate_b must be False (NEVER PASS), even if labels are converging.
    Also confirms k0_control_cd diagnostic field is present in the report.
    """
    from pathlib import Path as _Path
    from common.config import load_config
    from harness.runner import Runner, RunnerConfig
    from common.llm import LLMClient

    cfg = load_config()
    tasks = [_make_task(f"k0_{i}", regime="H1_external", k=0) for i in range(4)]
    cp = str(tmp_path / "cp.jsonl")

    records = []
    for t in tasks:
        for seed_off in range(5):
            label = "I1" if seed_off < 4 else "I0"
            records.append(_make_run_record(t.id, "sc", "gpt-5.4", label,
                                            seed=42 + seed_off, replicate_seed=42))
        records.append({"type": "job_done", "task_id": t.id, "config": "sc",
                        "model_role": "tested_agents", "model_id": "gpt-5.4", "seed": 42})
    _write_jsonl(_Path(cp), records)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "cache"), offline=True)
    runner_cfg = RunnerConfig(
        tasks=tasks, configs=["sc"], seeds=[42],
        models=[("tested_agents", "gpt-5.4")],
        checkpoint_path=_Path(cp), rpm=0,
    )
    runner = Runner(runner_cfg, client)

    report = _registered_run.run_pilot_gate(
        cfg, tasks, checkpoint_path=cp,
        offline=True, cache_dir=str(tmp_path / "llm_cache"),
        _runner_override=(runner, client),
    )

    assert not report["gate_a"], (
        "gate_a must be False when all H1 items are k=0 (fully specified control). "
        "BLOCKER: gates A/B must be restricted to k>=1 items only."
    )
    assert not report["gate_b"]
    assert not report["gate_pass"]
    assert "k0_control_cd" in report, "report must include k0_control_cd diagnostic field"


def test_gate_a_uses_only_k1_plus_not_k0_mixed_batch(tmp_path):
    """BLOCKER: gate A uses only k>=1 cells even in a mixed k=0+k=1 batch.

    k=0 items converge (4/5 wrong -> CD>0), k=1 items all correct (CD=0).
    If gate A included k=0 items it would PASS; correct behaviour is FAIL
    because the k>=1 items have CD=0.
    """
    from pathlib import Path as _Path
    from common.config import load_config
    from harness.runner import Runner, RunnerConfig
    from common.llm import LLMClient

    cfg = load_config()
    k0_tasks = [_make_task(f"k0_{i}", regime="H1_external", k=0) for i in range(2)]
    k1_tasks = [_make_task(f"k1_{i}", regime="H1_external", k=1) for i in range(2)]
    tasks = k0_tasks + k1_tasks
    cp = str(tmp_path / "cp.jsonl")

    records = []
    for t in k0_tasks:
        for seed_off in range(5):
            label = "I1" if seed_off < 4 else "I0"
            records.append(_make_run_record(t.id, "sc", "gpt-5.4", label,
                                            seed=42 + seed_off, replicate_seed=42))
        records.append({"type": "job_done", "task_id": t.id, "config": "sc",
                        "model_role": "tested_agents", "model_id": "gpt-5.4", "seed": 42})
    for t in k1_tasks:
        for seed_off in range(5):
            records.append(_make_run_record(t.id, "sc", "gpt-5.4", "I0",
                                            seed=42 + seed_off, replicate_seed=42))
        records.append({"type": "job_done", "task_id": t.id, "config": "sc",
                        "model_role": "tested_agents", "model_id": "gpt-5.4", "seed": 42})
    _write_jsonl(_Path(cp), records)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "cache"), offline=True)
    runner_cfg = RunnerConfig(
        tasks=tasks, configs=["sc"], seeds=[42],
        models=[("tested_agents", "gpt-5.4")],
        checkpoint_path=_Path(cp), rpm=0,
    )
    runner = Runner(runner_cfg, client)

    report = _registered_run.run_pilot_gate(
        cfg, tasks, checkpoint_path=cp,
        offline=True, cache_dir=str(tmp_path / "llm_cache"),
        _runner_override=(runner, client),
    )

    assert not report["gate_a"], (
        "gate_a must FAIL: k=1 items all correct -> real_cd=0. "
        "k=0 items (4/5 wrong) must NOT contribute to gate_a. "
        f"real_cd={report['real_cd']:.4f}  k0_control_cd={report.get('k0_control_cd','N/A')}"
    )
    assert report.get("k0_control_cd", 0.0) > 0.0, (
        "k0_control_cd diagnostic should be > 0 (k=0 items were 4/5 wrong)"
    )


def test_select_pilot_tasks_raises_if_h1_pool_is_all_k0():
    """BLOCKER: selector raises when the entire H1 pool is k=0."""
    h1_k0 = [_make_task(f"k0_{i}", regime="H1_external", k=0) for i in range(4)]
    h2 = [_make_task(f"h2_{i}", regime="H2_derivable", k=1) for i in range(4)]
    with pytest.raises(ValueError, match="k"):
        _registered_run.select_pilot_tasks(h1_k0 + h2, n_pilot=10)


# ── 14. MAJOR gate C: per-model cardinality, not pooled ──────────────────────

def test_gate_c_fails_when_one_model_sc_job_has_zero_records(tmp_path):
    """MAJOR gate C: one model's SC job has job_done but 0 agent records.

    The OLD check grouped by (item, method, seed), pooling all models.  With
    gpt-5.4 having 5 records and gpt-5.6-sol having 0, the pool group has 5
    records and passes len>=5.  The NEW per-model enumeration catches that
    gpt-5.6-sol has 0 records and fails gate_c.
    """
    from pathlib import Path as _Path
    from common.config import load_config
    from harness.runner import Runner, RunnerConfig
    from common.llm import LLMClient

    cfg = load_config()
    tasks = [_make_task("t1", regime="H1_external", k=1)]
    cp = str(tmp_path / "cp.jsonl")

    records = []
    for seed_off in range(5):
        records.append(_make_run_record("t1", "sc", "gpt-5.4", "I1",
                                        seed=42 + seed_off, replicate_seed=42))
    records.append({"type": "job_done", "task_id": "t1", "config": "sc",
                    "model_role": "tested_agents", "model_id": "gpt-5.4", "seed": 42})
    # gpt-5.6-sol has job_done but ZERO agent records.
    records.append({"type": "job_done", "task_id": "t1", "config": "sc",
                    "model_role": "tested_agents", "model_id": "gpt-5.6-sol", "seed": 42})
    _write_jsonl(_Path(cp), records)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "cache"), offline=True)
    runner_cfg = RunnerConfig(
        tasks=tasks, configs=["sc"], seeds=[42],
        models=[("tested_agents", "gpt-5.4"), ("tested_agents", "gpt-5.6-sol")],
        checkpoint_path=_Path(cp), rpm=0,
    )
    runner = Runner(runner_cfg, client)

    report = _registered_run.run_pilot_gate(
        cfg, tasks, checkpoint_path=cp,
        offline=True, cache_dir=str(tmp_path / "llm_cache"),
        _runner_override=(runner, client),
    )

    assert not report["gate_c"], (
        "gate_c must FAIL when one model SC job has 0 records. "
        "MAJOR: per-model check must not be masked by pooled aggregation."
    )
    assert not report["gate_pass"]
