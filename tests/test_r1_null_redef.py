"""Golden/unit tests for Amendment 07 R1 null-redefinition (Deliverable D3).

# Implementer model family: Claude/Anthropic

Amendment 07 (paper/preregistration/2026-07-17-amendment-07-r1-null-redefinition-SIGNED.md):
  - R1a: k=0-control contrast gates PASS/FAIL (replaces label-shuffle gate).
  - R1b: uniform-interpretation null gates PASS/FAIL (replaces label-shuffle gate).
  - Label-shuffle: DEMOTED to shared-prior diagnostic (null≈real EXPECTED — Amdt 07).

Coverage (D3 specification):
  D1 — unit tests for uniform_interpretation_null:
    1. test_uniform_null_discriminates_golden_case
         All-same-foil item (5 agents, all I1), 2 interpretations {I0, I1}, target I0.
         Real cd = 1.0; CD_unif ≈ 0.5 ≪ real (golden discriminator).
    2. test_uniform_null_deterministic
         Same seed → identical CD_unif on two independent calls.
    3. test_uniform_null_three_interpretations
         3 interpretations: CD_unif < real_cd for a concentrated batch.
    4. test_uniform_null_empty_input
         Returns 0.0 for empty items_labels.
    5. test_uniform_null_mismatched_lengths_raises
         Raises ValueError when lists have different lengths.

  D2 — integration tests for R1a/R1b via run_pilot_gate:
    6. test_r1a_passes_k0_near_zero_k1plus_high
         k=0 items all I0 (CD_k0=0) + k=1 items 4/5 I1 (CD_k1=0.8) → R1a PASS.
    7. test_r1a_fails_when_k0_too_high
         k=0 items 4/5 I1 (CD_k0=0.8 > tol) + k=1 items converge → R1a FAIL.
    8. test_r1a_fails_when_k1plus_not_greater_than_k0
         k=0 all I0 (CD_k0=0) + k=1 all I0 (CD_k1=0) → 0 > 0 = False → R1a FAIL.
    9. test_r1a_inconclusive_no_k0_items
         Only k=1 items: R1a INCONCLUSIVE, gate_b False.
    10. test_r1a_inconclusive_no_k1plus_items
         Only k=0 items: R1a INCONCLUSIVE, gate_b False.
    11. test_r1b_passes_obs_much_greater_than_uniform
         k=1 items 4/5 I1: CD_real=0.8, CD_unif≈0.5, margin=0.3>R1B_MARGIN → R1b PASS.
    12. test_r1b_fails_obs_close_to_uniform
         k=1 items 3/5 I1: CD_real=0.6, CD_unif≈0.5, margin=0.1<R1B_MARGIN → R1b FAIL.
    13. test_label_shuffle_no_longer_gates_verdict
         k=0 all I0 + k=1 4/5 I1: shuffle null ≈ 0.8 ≫ tol (old gate would FAIL),
         but new gate_b = R1a(PASS) AND R1b(PASS) → gate_b = True.
    14. test_gate_b_false_when_r1a_inconclusive_overrides_r1b_pass
         Only k=1 items (no k=0): R1a INCONCLUSIVE → gate_b False even if R1b would pass.

All tests run fully offline — zero network calls, zero token use.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from common.schema import Interpretation, Task
from analysis.nulls import uniform_interpretation_null, NULL_CD_TOLERANCE
from analysis.cd import cd_primary

# ── Load scripts/registered_run.py (not a package) ───────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_RR_PATH = _REPO_ROOT / "scripts" / "registered_run.py"
_spec = importlib.util.spec_from_file_location("registered_run_r1", _RR_PATH)
_rr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rr)  # type: ignore[union-attr]

R1B_MARGIN: float = _rr.R1B_MARGIN


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_task(
    task_id: str,
    regime: str = "H1_external",
    k: int = 1,
    n_interps: int = 2,
    domain: str = "code_spec",
) -> Task:
    """Create a test Task with n_interps non-I_perp interpretations + I_perp."""
    interps = [Interpretation(id="I0", is_target=True, gold_check="g0")]
    for i in range(1, n_interps):
        interps.append(Interpretation(id=f"I{i}", is_target=False, gold_check=f"g{i}"))
    interps.append(Interpretation(id="I_perp", is_target=False, gold_check="gp"))
    return Task(
        id=task_id,
        domain=domain,
        prompt=f"prompt {task_id}",
        latent_spec="spec",
        interpretations=interps,
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
    if replicate_seed is not None and replicate_seed != seed:
        rec["replicate_seed"] = replicate_seed
    return rec


def _write_jsonl(path: Path, records: List[Dict]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def _make_noop_runner(cfg, tasks, checkpoint_path: str, tmp_path: Path):
    """Build a noop Runner that skips everything (checkpoint pre-populated)."""
    from harness.runner import Runner, RunnerConfig
    from common.llm import LLMClient

    client = LLMClient(cfg, cache_dir=str(tmp_path / "cache"), offline=True)
    runner_cfg = RunnerConfig(
        tasks=tasks,
        configs=["sc"],
        seeds=[42],
        models=[("tested_agents", "gpt-5.4")],
        checkpoint_path=Path(checkpoint_path),
        rpm=0,
    )
    return Runner(runner_cfg, client), client


def _write_checkpoint_for_tasks(
    path: Path,
    k0_tasks: List[Task],
    k0_label_pattern: str,  # "all_correct" | "converging"
    k1_tasks: List[Task],
    k1_label_pattern: str,
    n_agents: int = 5,
) -> None:
    """Write a checkpoint with labels for k=0 and k≥1 tasks."""
    records: List[Dict] = []
    for task in k0_tasks:
        for seed_off in range(n_agents):
            if k0_label_pattern == "all_correct":
                label = "I0"
            elif k0_label_pattern == "converging":
                label = "I1" if seed_off < (n_agents - 1) else "I0"
            else:
                raise ValueError(f"Unknown k0_label_pattern: {k0_label_pattern!r}")
            records.append(
                _make_run_record(task.id, "sc", "gpt-5.4", label,
                                 seed=42 + seed_off, replicate_seed=42)
            )
        records.append({"type": "job_done", "task_id": task.id, "config": "sc",
                        "model_role": "tested_agents", "model_id": "gpt-5.4", "seed": 42})
    for task in k1_tasks:
        for seed_off in range(n_agents):
            if k1_label_pattern == "all_correct":
                label = "I0"
            elif k1_label_pattern == "converging":
                label = "I1" if seed_off < (n_agents - 1) else "I0"
            elif k1_label_pattern == "weakly_converging":
                # 3/5 on I1, 2/5 on I0 → cd_primary = 0.6
                label = "I1" if seed_off < 3 else "I0"
            elif k1_label_pattern == "below_uniform":
                # 2/5 on I1, 3/5 on I0 → cd_primary = 0.4 < CD_unif≈0.5 → diff < 0
                label = "I1" if seed_off < 2 else "I0"
            else:
                raise ValueError(f"Unknown k1_label_pattern: {k1_label_pattern!r}")
            records.append(
                _make_run_record(task.id, "sc", "gpt-5.4", label,
                                 seed=42 + seed_off, replicate_seed=42)
            )
        records.append({"type": "job_done", "task_id": task.id, "config": "sc",
                        "model_role": "tested_agents", "model_id": "gpt-5.4", "seed": 42})
    _write_jsonl(path, records)


# ─────────────────────────────────────────────────────────────────────────────
# D1 — Unit tests for uniform_interpretation_null
# ─────────────────────────────────────────────────────────────────────────────

class TestUniformInterpretationNull:
    """Unit tests for analysis.nulls.uniform_interpretation_null."""

    def test_discriminates_golden_case(self):
        """Golden case (Amendment 07): all-same-foil item → CD_unif ≈ 0.5 ≪ real 1.0.

        Setup:
          - 1 item, 5 agents, all label I1 (wrong)
          - 2 interpretations: {I0, I1}, target="I0"
          - Real cd_primary = 5/5 = 1.0 (all agents on the enumerated-wrong label)

        Under uniform draws from {I0, I1}:
          - E[I1 count] = 5 × 0.5 = 2.5
          - E[cd_primary] = 2.5 / 5 = 0.5

        Assertions:
          - real_cd = 1.0 (exact)
          - CD_unif ≈ 0.5 (with ±0.03 MC tolerance at n_perm=1000)
          - real_cd - CD_unif > 0.4 (clear discrimination: R1b PASS by large margin)
        """
        TARGET = "I0"
        items_labels = [["I1", "I1", "I1", "I1", "I1"]]
        items_interp_ids = [["I0", "I1"]]

        real_cd = cd_primary(items_labels[0], TARGET)
        assert real_cd == pytest.approx(1.0, abs=1e-9), (
            f"Golden case: real_cd should be exactly 1.0, got {real_cd:.10f}"
        )

        cd_unif = uniform_interpretation_null(
            items_labels, items_interp_ids, TARGET, n_perm=1000, seed=42
        )

        assert abs(cd_unif - 0.5) < 0.03, (
            f"Golden case: CD_unif should be ≈ 0.5 (uniform from {{I0, I1}}, 5 agents), "
            f"got {cd_unif:.4f}.  "
            f"E[I1 count]=2.5, E[cd_primary]=2.5/5=0.5 analytically."
        )
        margin = real_cd - cd_unif
        assert margin > 0.4, (
            f"Golden case: real_cd (1.0) − CD_unif ({cd_unif:.4f}) = {margin:.4f}; "
            f"expected > 0.4 (clear R1b discrimination)."
        )

    def test_deterministic(self):
        """Same seed → identical CD_unif on two independent calls."""
        items_labels = [
            ["I1", "I1", "I1", "I2", "I0"],
            ["I2", "I2", "I1", "I0", "I0"],
        ] * 5
        items_interp_ids = [["I0", "I1", "I2"]] * 10

        cd_a = uniform_interpretation_null(items_labels, items_interp_ids, "I0", n_perm=500, seed=99)
        cd_b = uniform_interpretation_null(items_labels, items_interp_ids, "I0", n_perm=500, seed=99)
        assert cd_a == cd_b, (
            f"Determinism failed: first call={cd_a:.8f}, second call={cd_b:.8f}"
        )

    def test_three_interpretations_discriminates(self):
        """3 interpretations: CD_unif < real_cd for concentrated batch.

        5 items, each with 5 agents all on I1, 3 interpretations {I0, I1, I2}.
        real_cd = 1.0.  Under uniform draws, each agent picks from {I0, I1, I2}
        with p=1/3 each; E[max(I1_count, I2_count)] < 5, so CD_unif < 1.0.
        """
        items_labels = [["I1"] * 5] * 5
        items_interp_ids = [["I0", "I1", "I2"]] * 5

        real_cd = sum(cd_primary(row, "I0") for row in items_labels) / len(items_labels)
        cd_unif = uniform_interpretation_null(
            items_labels, items_interp_ids, "I0", n_perm=1000, seed=42
        )

        assert real_cd == pytest.approx(1.0, abs=1e-9)
        assert cd_unif < real_cd, (
            f"3-interp: expected CD_unif ({cd_unif:.4f}) < real_cd ({real_cd:.4f})"
        )
        assert cd_unif > 0.2, (
            f"3-interp: CD_unif ({cd_unif:.4f}) should be > 0.2 (non-trivial baseline)"
        )
        assert cd_unif < 0.7, (
            f"3-interp: CD_unif ({cd_unif:.4f}) should be < 0.7 (not saturated)"
        )

    def test_empty_input_returns_zero(self):
        """Empty items_labels → returns 0.0 (no-op, not an error)."""
        result = uniform_interpretation_null([], [], "I0", n_perm=100, seed=42)
        assert result == 0.0, f"Expected 0.0 for empty input, got {result}"

    def test_mismatched_lengths_raises(self):
        """len(items_labels) != len(items_interpretation_ids) → ValueError."""
        with pytest.raises(ValueError, match="length"):
            uniform_interpretation_null(
                [["I1", "I1"]],       # 1 item
                [["I0", "I1"], ["I0", "I1"]],  # 2 interp sets
                "I0",
            )

    def test_single_interpretation_gives_zero(self):
        """Single interpretation (only I0): CD_unif = 0 (no enumerated-wrong possible)."""
        items_labels = [["I0", "I0", "I0"]]
        items_interp_ids = [["I0"]]  # only the target

        cd_unif = uniform_interpretation_null(
            items_labels, items_interp_ids, "I0", n_perm=200, seed=42
        )
        assert cd_unif == pytest.approx(0.0, abs=1e-9), (
            f"Single-interp: all draws are I0 (target), cd_primary=0; "
            f"got CD_unif={cd_unif:.6f}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# D2 — Integration tests for R1a/R1b via run_pilot_gate
# ─────────────────────────────────────────────────────────────────────────────

class TestR1GatesViaPilotGate:
    """Integration tests for R1a and R1b gates (Amendment 07) via run_pilot_gate.

    All tests use offline synthetic checkpoints and noop runners — no network calls.
    """

    # ── Test 6: R1a PASS ──────────────────────────────────────────────────────

    def test_r1a_passes_k0_near_zero_k1plus_high(self, tmp_path):
        """R1a PASS: k=0 items all correct (CD_k0=0) + k=1 items converge (CD_k1=0.8).

        CD_k0 = 0 ≤ NULL_CD_TOLERANCE (0.10) AND CD_k1 = 0.8 > CD_k0 = 0 → R1a PASS.
        """
        from common.config import load_config
        cfg = load_config()

        k0_tasks = [_make_task(f"k0_{i}", regime="H1_external", k=0) for i in range(2)]
        k1_tasks = [_make_task(f"k1_{i}", regime="H1_external", k=1) for i in range(2)]
        tasks = k0_tasks + k1_tasks

        cp = str(tmp_path / "cp.jsonl")
        _write_checkpoint_for_tasks(
            Path(cp),
            k0_tasks=k0_tasks, k0_label_pattern="all_correct",
            k1_tasks=k1_tasks, k1_label_pattern="converging",
        )
        runner, client = _make_noop_runner(cfg, tasks, cp, tmp_path)

        report = _rr.run_pilot_gate(
            cfg, tasks, checkpoint_path=cp,
            offline=True, cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )

        r1a_det = next((d for d in report["gate_b_details"] if d.get("gate") == "r1a"), {})
        assert r1a_det.get("status") == "pass", (
            f"R1a should PASS: CD_k0=0 ≤ tol AND CD_k1=0.8 > 0. "
            f"Got status={r1a_det.get('status')!r}, "
            f"k0_cd={r1a_det.get('k0_cd')}, k1plus_cd={r1a_det.get('k1plus_cd')}"
        )
        assert report["gate_r1a"] is True
        assert report["k0_control_cd"] == pytest.approx(0.0, abs=1e-9)
        assert report["real_cd"] == pytest.approx(0.8, abs=1e-6)

    # ── Test 7: R1a FAIL — k0 too high ───────────────────────────────────────

    def test_r1a_fails_when_k0_too_high(self, tmp_path):
        """R1a FAIL: k=0 items converge (CD_k0=0.8 > tol=0.10) → FAIL condition 1."""
        from common.config import load_config
        cfg = load_config()

        k0_tasks = [_make_task(f"k0_{i}", regime="H1_external", k=0) for i in range(2)]
        k1_tasks = [_make_task(f"k1_{i}", regime="H1_external", k=1) for i in range(2)]
        tasks = k0_tasks + k1_tasks

        cp = str(tmp_path / "cp.jsonl")
        _write_checkpoint_for_tasks(
            Path(cp),
            k0_tasks=k0_tasks, k0_label_pattern="converging",  # CD_k0 = 0.8 >> tol
            k1_tasks=k1_tasks, k1_label_pattern="converging",
        )
        runner, client = _make_noop_runner(cfg, tasks, cp, tmp_path)

        report = _rr.run_pilot_gate(
            cfg, tasks, checkpoint_path=cp,
            offline=True, cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )

        r1a_det = next((d for d in report["gate_b_details"] if d.get("gate") == "r1a"), {})
        assert r1a_det.get("status") == "fail", (
            f"R1a should FAIL: CD_k0=0.8 > tol=0.10. "
            f"Got status={r1a_det.get('status')!r}"
        )
        assert report["gate_r1a"] is False
        assert report["k0_control_cd"] > NULL_CD_TOLERANCE, (
            f"k0_control_cd should exceed tol ({NULL_CD_TOLERANCE}), "
            f"got {report['k0_control_cd']:.4f}"
        )

    # ── Test 8: R1a FAIL — k1plus not greater than k0 ────────────────────────

    def test_r1a_fails_when_k1plus_not_greater_than_k0(self, tmp_path):
        """R1a FAIL: both k=0 and k=1 items all correct → CD_k0=0, CD_k1=0 → 0>0 False."""
        from common.config import load_config
        cfg = load_config()

        k0_tasks = [_make_task(f"k0_{i}", regime="H1_external", k=0) for i in range(2)]
        k1_tasks = [_make_task(f"k1_{i}", regime="H1_external", k=1) for i in range(2)]
        tasks = k0_tasks + k1_tasks

        cp = str(tmp_path / "cp.jsonl")
        _write_checkpoint_for_tasks(
            Path(cp),
            k0_tasks=k0_tasks, k0_label_pattern="all_correct",
            k1_tasks=k1_tasks, k1_label_pattern="all_correct",  # CD_k1 = 0 ≤ CD_k0 = 0
        )
        runner, client = _make_noop_runner(cfg, tasks, cp, tmp_path)

        report = _rr.run_pilot_gate(
            cfg, tasks, checkpoint_path=cp,
            offline=True, cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )

        r1a_det = next((d for d in report["gate_b_details"] if d.get("gate") == "r1a"), {})
        assert r1a_det.get("status") == "fail", (
            f"R1a should FAIL: CD_k1=0 is not > CD_k0=0. "
            f"Got status={r1a_det.get('status')!r}, "
            f"k0_cd={r1a_det.get('k0_cd')}, k1plus_cd={r1a_det.get('k1plus_cd')}"
        )
        assert report["gate_r1a"] is False
        # gate_a also fails (real_cd = 0)
        assert not report["gate_a"]

    # ── Test 9: R1a INCONCLUSIVE — no k=0 items ──────────────────────────────

    def test_r1a_inconclusive_no_k0_items(self, tmp_path):
        """R1a INCONCLUSIVE: only k=1 items in batch (no k=0 control group)."""
        from common.config import load_config
        cfg = load_config()

        k1_tasks = [_make_task(f"k1_{i}", regime="H1_external", k=1) for i in range(2)]

        cp = str(tmp_path / "cp.jsonl")
        _write_checkpoint_for_tasks(
            Path(cp),
            k0_tasks=[], k0_label_pattern="all_correct",
            k1_tasks=k1_tasks, k1_label_pattern="converging",
        )
        runner, client = _make_noop_runner(cfg, k1_tasks, cp, tmp_path)

        report = _rr.run_pilot_gate(
            cfg, k1_tasks, checkpoint_path=cp,
            offline=True, cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )

        r1a_det = next((d for d in report["gate_b_details"] if d.get("gate") == "r1a"), {})
        assert r1a_det.get("status") == "inconclusive", (
            f"R1a should be INCONCLUSIVE when there are no k=0 H1 items. "
            f"Got status={r1a_det.get('status')!r}"
        )
        assert report["gate_r1a"] is False
        assert report["gate_b"] is False

    # ── Test 10: R1a INCONCLUSIVE — no k≥1 items ─────────────────────────────

    def test_r1a_inconclusive_no_k1plus_items(self, tmp_path):
        """R1a INCONCLUSIVE: only k=0 items in batch (no underspecified items)."""
        from common.config import load_config
        cfg = load_config()

        k0_tasks = [_make_task(f"k0_{i}", regime="H1_external", k=0) for i in range(2)]

        cp = str(tmp_path / "cp.jsonl")
        _write_checkpoint_for_tasks(
            Path(cp),
            k0_tasks=k0_tasks, k0_label_pattern="all_correct",
            k1_tasks=[], k1_label_pattern="all_correct",
        )
        runner, client = _make_noop_runner(cfg, k0_tasks, cp, tmp_path)

        report = _rr.run_pilot_gate(
            cfg, k0_tasks, checkpoint_path=cp,
            offline=True, cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )

        r1a_det = next((d for d in report["gate_b_details"] if d.get("gate") == "r1a"), {})
        assert r1a_det.get("status") == "inconclusive", (
            f"R1a should be INCONCLUSIVE when there are no k≥1 H1 items. "
            f"Got status={r1a_det.get('status')!r}"
        )
        assert report["gate_r1a"] is False
        assert report["gate_b"] is False
        assert not report["gate_a"]  # gate_a also fails (no k≥1 H1 items)

    # ── Test 11: R1b PASS ─────────────────────────────────────────────────────

    def test_r1b_passes_obs_much_greater_than_uniform(self, tmp_path):
        """R1b PASS: CD_real=0.8 ≫ CD_unif≈0.5, margin=0.3 > R1B_MARGIN=0.15.

        k=0 items all I0 (for R1a), k=1 items 4/5 I1 (CD_real=0.8).
        Uniform null for 2 interpretations {I0, I1}: CD_unif ≈ 0.5.
        0.8 > 0.5 + 0.15 = 0.65 → R1b PASS.
        """
        from common.config import load_config
        cfg = load_config()

        k0_tasks = [_make_task(f"k0_{i}", regime="H1_external", k=0) for i in range(2)]
        k1_tasks = [_make_task(f"k1_{i}", regime="H1_external", k=1) for i in range(2)]
        tasks = k0_tasks + k1_tasks

        cp = str(tmp_path / "cp.jsonl")
        _write_checkpoint_for_tasks(
            Path(cp),
            k0_tasks=k0_tasks, k0_label_pattern="all_correct",
            k1_tasks=k1_tasks, k1_label_pattern="converging",  # CD_real = 0.8
        )
        runner, client = _make_noop_runner(cfg, tasks, cp, tmp_path)

        report = _rr.run_pilot_gate(
            cfg, tasks, checkpoint_path=cp,
            offline=True, cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )

        r1b_det = next((d for d in report["gate_b_details"] if d.get("gate") == "r1b"), {})
        assert r1b_det.get("status") == "pass", (
            f"R1b should PASS: real_cd=0.8 ≫ uniform_cd≈0.5+margin=0.15. "
            f"Got status={r1b_det.get('status')!r}, "
            f"real_cd={r1b_det.get('real_cd')}, uniform_cd={r1b_det.get('uniform_cd')}"
        )
        assert report["gate_r1b"] is True

        # Verify R1b margin is actually met
        uniform_cd = report["uniform_null_cd"]
        real_cd = report["real_cd"]
        assert real_cd > uniform_cd + R1B_MARGIN, (
            f"R1b: real_cd ({real_cd:.4f}) should exceed uniform_cd ({uniform_cd:.4f}) "
            f"+ margin ({R1B_MARGIN}) = {uniform_cd + R1B_MARGIN:.4f}"
        )

    # ── Test 12: R1b FAIL ─────────────────────────────────────────────────────

    def test_r1b_fails_obs_close_to_uniform(self, tmp_path):
        """R1b FAIL: CD_real=0.4 < CD_unif≈0.5 — per-item diff < 0, bootstrap CI lower < 0.

        k=0 items all I0, k=1 items 2/5 I1 (below_uniform → CD_real=0.4).
        Uniform null for {I0, I1}: CD_unif ≈ 0.5.
        Per-item diff ≈ -0.1 for each of 2 items → mean diff ≈ -0.1 → CI lower < 0 → R1b FAIL.
        """
        from common.config import load_config
        cfg = load_config()

        k0_tasks = [_make_task(f"k0_{i}", regime="H1_external", k=0) for i in range(2)]
        k1_tasks = [_make_task(f"k1_{i}", regime="H1_external", k=1) for i in range(2)]
        tasks = k0_tasks + k1_tasks

        cp = str(tmp_path / "cp.jsonl")
        _write_checkpoint_for_tasks(
            Path(cp),
            k0_tasks=k0_tasks, k0_label_pattern="all_correct",
            k1_tasks=k1_tasks, k1_label_pattern="below_uniform",  # CD_real = 0.4 < CD_unif≈0.5
        )
        runner, client = _make_noop_runner(cfg, tasks, cp, tmp_path)

        report = _rr.run_pilot_gate(
            cfg, tasks, checkpoint_path=cp,
            offline=True, cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )

        r1b_det = next((d for d in report["gate_b_details"] if d.get("gate") == "r1b"), {})
        assert r1b_det.get("status") == "fail", (
            f"R1b should FAIL: CD_real=0.4 < CD_unif≈0.5 → per-item diff≈-0.1 → "
            f"bootstrap CI lower < 0. "
            f"Got status={r1b_det.get('status')!r}, "
            f"real_cd={r1b_det.get('real_cd')}, uniform_cd={r1b_det.get('uniform_cd')}, "
            f"ci_lo={r1b_det.get('ci_lo')}"
        )
        assert report["gate_r1b"] is False

        # Confirm obs is BELOW uniform (definitively negative diff)
        uniform_cd = report["uniform_null_cd"]
        real_cd = report["real_cd"]
        assert real_cd < uniform_cd, (
            f"R1b FAIL case: real_cd ({real_cd:.4f}) should be BELOW uniform_cd "
            f"({uniform_cd:.4f}) — per-item diff is negative, CI lower < 0"
        )
        # CI lower bound should be negative (the core bootstrap FAIL criterion)
        assert r1b_det.get("ci_lo", 0.0) < 0, (
            f"R1b FAIL: CI lower bound should be < 0; got ci_lo={r1b_det.get('ci_lo')}"
        )

    # ── Test 13: label-shuffle no longer gates verdict ────────────────────────

    def test_label_shuffle_no_longer_gates_verdict(self, tmp_path):
        """Label-shuffle null no longer affects gate_b, even when null_cd ≈ real_cd.

        This is the core Amendment 07 regression test.

        Setup: k=0 items all I0 + k=1 items 4/5 I1 (CD_real=0.8).
        Shuffle null: pool is {80% I1, 20% I0} (from k=1 items only) → after
        shuffle each item gets ~80% I1 → null_cd ≈ real_cd ≈ 0.8.
        Under the OLD gate: FAIL (null_cd = 0.8 > NULL_CD_TOLERANCE = 0.10).
        Under the NEW gate (Amendment 07): gate_b = R1a(PASS) AND R1b(PASS) = TRUE.

        Assertions:
          - null_cd ≫ NULL_CD_TOLERANCE (old gate would have failed)
          - gate_b = True (new gate passes despite null_cd ≈ real_cd)
          - gate_r1a = True, gate_r1b = True
        """
        from common.config import load_config
        cfg = load_config()

        k0_tasks = [_make_task(f"k0_{i}", regime="H1_external", k=0) for i in range(2)]
        k1_tasks = [_make_task(f"k1_{i}", regime="H1_external", k=1) for i in range(2)]
        tasks = k0_tasks + k1_tasks

        cp = str(tmp_path / "cp.jsonl")
        _write_checkpoint_for_tasks(
            Path(cp),
            k0_tasks=k0_tasks, k0_label_pattern="all_correct",
            k1_tasks=k1_tasks, k1_label_pattern="converging",
        )
        runner, client = _make_noop_runner(cfg, tasks, cp, tmp_path)

        report = _rr.run_pilot_gate(
            cfg, tasks, checkpoint_path=cp,
            offline=True, cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )

        # Key assertion: shuffle null is ≈ real_cd (shared-prior identity — Amdt 07).
        # In this batch all k=1 items have 4/5 I1, so the marginal is 80% I1.
        # A marginal-preserving shuffle preserves that → null_cd ≈ real_cd ≈ 0.8.
        # Under the OLD gate, this would have set gate_b = False.
        null_cd = report["null_cd"]
        real_cd = report["real_cd"]
        assert null_cd > NULL_CD_TOLERANCE, (
            f"Regression check: null_cd ({null_cd:.4f}) should be > tol "
            f"({NULL_CD_TOLERANCE}) to confirm old gate would have failed. "
            f"real_cd={real_cd:.4f}"
        )

        # Core assertion: new gate_b = True despite null_cd ≈ real_cd.
        assert report["gate_b"] is True, (
            f"Amendment 07: gate_b should be TRUE (R1a AND R1b), "
            f"even though null_cd ({null_cd:.4f}) ≈ real_cd ({real_cd:.4f}). "
            f"The label-shuffle null no longer gates the verdict."
        )
        assert report["gate_r1a"] is True, "R1a should PASS (CD_k0=0 ≤ tol AND CD_k1=0.8>0)"
        assert report["gate_r1b"] is True, "R1b should PASS (CD_real=0.8 >> CD_unif≈0.5)"

    # ── Test 14: gate_b False when R1a INCONCLUSIVE overrides R1b PASS ────────

    def test_gate_b_false_when_r1a_inconclusive_overrides_r1b_pass(self, tmp_path):
        """gate_b = R1a AND R1b: if R1a is INCONCLUSIVE (→ False), gate_b = False.

        Only k=1 items (no k=0): R1a INCONCLUSIVE → False.
        R1b: 4/5 I1 → CD_real=0.8 >> CD_unif≈0.5 → PASS.
        gate_b = False AND True = False.
        """
        from common.config import load_config
        cfg = load_config()

        # Only k=1 items — no k=0 for R1a contrast.
        k1_tasks = [_make_task(f"k1_{i}", regime="H1_external", k=1) for i in range(2)]

        cp = str(tmp_path / "cp.jsonl")
        _write_checkpoint_for_tasks(
            Path(cp),
            k0_tasks=[], k0_label_pattern="all_correct",
            k1_tasks=k1_tasks, k1_label_pattern="converging",
        )
        runner, client = _make_noop_runner(cfg, k1_tasks, cp, tmp_path)

        report = _rr.run_pilot_gate(
            cfg, k1_tasks, checkpoint_path=cp,
            offline=True, cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )

        # R1a: no k=0 items → INCONCLUSIVE → gate_r1a = False
        assert report["gate_r1a"] is False, "R1a must be False (INCONCLUSIVE: no k=0 items)"
        # R1b: 0.8 > 0.5+0.15 → PASS (gate_r1b can be True)
        # gate_b = R1a AND R1b = False (even if R1b passes)
        assert report["gate_b"] is False, (
            f"gate_b must be False when R1a is INCONCLUSIVE, "
            f"even if R1b passes. gate_r1a={report['gate_r1a']}, "
            f"gate_r1b={report['gate_r1b']}"
        )

    # ── Test: report dict contains all new Amendment 07 keys ─────────────────

    def test_report_has_amendment07_keys(self, tmp_path):
        """Report dict includes all Amendment 07 keys (gate_r1a, gate_r1b, uniform_null_cd)."""
        from common.config import load_config
        cfg = load_config()

        tasks = [_make_task("t1", regime="H1_external", k=1)]
        cp = str(tmp_path / "cp.jsonl")
        _write_jsonl(Path(cp), [
            {"type": "job_done", "task_id": "t1", "config": "sc",
             "model_role": "tested_agents", "model_id": "gpt-5.4", "seed": 42}
        ])
        runner, client = _make_noop_runner(cfg, tasks, cp, tmp_path)

        report = _rr.run_pilot_gate(
            cfg, tasks, checkpoint_path=cp,
            offline=True, cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )

        amdt07_keys = {"gate_r1a", "gate_r1b", "uniform_null_cd", "shuffle_null_details"}
        missing = amdt07_keys - set(report)
        assert not missing, f"Report missing Amendment 07 keys: {missing}"

        # Backward-compat keys still present
        compat_keys = {
            "gate_pass", "gate_a", "gate_b", "gate_c",
            "real_cd", "null_cd", "null_metric",
            "gate_b_details",
        }
        missing_compat = compat_keys - set(report)
        assert not missing_compat, f"Report missing backward-compat keys: {missing_compat}"


# ─────────────────────────────────────────────────────────────────────────────
# GPT audit fixes — MAJOR 1: bootstrap CI INCONCLUSIVE / PASS / FAIL tests
# ─────────────────────────────────────────────────────────────────────────────

class TestBootstrapCIGates:
    """Tests for bootstrap 95% CI PASS/FAIL/INCONCLUSIVE logic (MAJOR 1 fix)."""

    def test_r1a_inconclusive_single_k0_control(self, tmp_path):
        """R1a INCONCLUSIVE when only 1 k=0 item — < 2 items required for CI.

        A single k=0 item is NOT sufficient for the bootstrap CI of
        (mean CD_k≥1 − mean CD_k0). Must be INCONCLUSIVE, never PASS.
        """
        from common.config import load_config
        cfg = load_config()

        k0_tasks = [_make_task("k0_0", regime="H1_external", k=0)]  # only 1!
        k1_tasks = [_make_task(f"k1_{i}", regime="H1_external", k=1) for i in range(2)]
        tasks = k0_tasks + k1_tasks

        cp = str(tmp_path / "cp.jsonl")
        _write_checkpoint_for_tasks(
            Path(cp),
            k0_tasks=k0_tasks, k0_label_pattern="all_correct",
            k1_tasks=k1_tasks, k1_label_pattern="converging",
        )
        runner, client = _make_noop_runner(cfg, tasks, cp, tmp_path)

        report = _rr.run_pilot_gate(
            cfg, tasks, checkpoint_path=cp,
            offline=True, cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )

        r1a_det = next((d for d in report["gate_b_details"] if d.get("gate") == "r1a"), {})
        assert r1a_det.get("status") == "inconclusive", (
            f"R1a should be INCONCLUSIVE with only 1 k=0 item (CI needs ≥2). "
            f"Got status={r1a_det.get('status')!r}, "
            f"n_items_k0={r1a_det.get('n_items_k0')}"
        )
        assert report["gate_r1a"] is False
        assert report["gate_b"] is False

    def test_r1b_inconclusive_single_k1_item(self, tmp_path):
        """R1b INCONCLUSIVE when only 1 k≥1 item — < 2 items required for CI."""
        from common.config import load_config
        cfg = load_config()

        k1_tasks = [_make_task("k1_0", regime="H1_external", k=1)]  # only 1!

        cp = str(tmp_path / "cp.jsonl")
        _write_checkpoint_for_tasks(
            Path(cp),
            k0_tasks=[], k0_label_pattern="all_correct",
            k1_tasks=k1_tasks, k1_label_pattern="converging",
        )
        runner, client = _make_noop_runner(cfg, k1_tasks, cp, tmp_path)

        report = _rr.run_pilot_gate(
            cfg, k1_tasks, checkpoint_path=cp,
            offline=True, cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )

        r1b_det = next((d for d in report["gate_b_details"] if d.get("gate") == "r1b"), {})
        assert r1b_det.get("status") == "inconclusive", (
            f"R1b should be INCONCLUSIVE with only 1 k≥1 item (CI needs ≥2). "
            f"Got status={r1b_det.get('status')!r}, "
            f"n_items_k1plus={r1b_det.get('n_items_k1plus')}"
        )
        assert report["gate_r1b"] is False

    def test_r1a_bootstrap_ci_lo_positive_on_pass(self, tmp_path):
        """R1a PASS: gate_b_details includes positive ci_lo for bootstrap CI."""
        from common.config import load_config
        cfg = load_config()

        k0_tasks = [_make_task(f"k0_{i}", regime="H1_external", k=0) for i in range(2)]
        k1_tasks = [_make_task(f"k1_{i}", regime="H1_external", k=1) for i in range(2)]
        tasks = k0_tasks + k1_tasks

        cp = str(tmp_path / "cp.jsonl")
        _write_checkpoint_for_tasks(
            Path(cp),
            k0_tasks=k0_tasks, k0_label_pattern="all_correct",
            k1_tasks=k1_tasks, k1_label_pattern="converging",
        )
        runner, client = _make_noop_runner(cfg, tasks, cp, tmp_path)

        report = _rr.run_pilot_gate(
            cfg, tasks, checkpoint_path=cp,
            offline=True, cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )

        r1a_det = next((d for d in report["gate_b_details"] if d.get("gate") == "r1a"), {})
        assert r1a_det.get("status") == "pass"
        ci_lo = r1a_det.get("ci_lo", float("-inf"))
        assert ci_lo > 0, f"R1a PASS must have ci_lo > 0; got ci_lo={ci_lo:.4f}"
        assert r1a_det.get("n_items_k0") == 2
        assert r1a_det.get("n_items_k1plus") == 2

    def test_r1b_bootstrap_ci_lo_positive_on_pass(self, tmp_path):
        """R1b PASS: gate_b_details includes positive ci_lo for bootstrap CI."""
        from common.config import load_config
        cfg = load_config()

        k0_tasks = [_make_task(f"k0_{i}", regime="H1_external", k=0) for i in range(2)]
        k1_tasks = [_make_task(f"k1_{i}", regime="H1_external", k=1) for i in range(2)]
        tasks = k0_tasks + k1_tasks

        cp = str(tmp_path / "cp.jsonl")
        _write_checkpoint_for_tasks(
            Path(cp),
            k0_tasks=k0_tasks, k0_label_pattern="all_correct",
            k1_tasks=k1_tasks, k1_label_pattern="converging",
        )
        runner, client = _make_noop_runner(cfg, tasks, cp, tmp_path)

        report = _rr.run_pilot_gate(
            cfg, tasks, checkpoint_path=cp,
            offline=True, cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )

        r1b_det = next((d for d in report["gate_b_details"] if d.get("gate") == "r1b"), {})
        assert r1b_det.get("status") == "pass"
        ci_lo = r1b_det.get("ci_lo", float("-inf"))
        assert ci_lo > 0, f"R1b PASS must have ci_lo > 0; got ci_lo={ci_lo:.4f}"


# ─────────────────────────────────────────────────────────────────────────────
# GPT audit fix — MAJOR 2: frozen label_shuffle_null diagnostic
# ─────────────────────────────────────────────────────────────────────────────

class TestFrozenLabelShuffleDiagnostic:
    """MAJOR 2: frozen label_shuffle_null (false_consensus_rate) per condition."""

    def test_shuffle_null_details_has_both_null_keys(self, tmp_path):
        """shuffle_null_details entries must have null_cd_cd_primary AND null_cd_frozen_fcr."""
        from common.config import load_config
        cfg = load_config()

        k0_tasks = [_make_task(f"k0_{i}", regime="H1_external", k=0) for i in range(2)]
        k1_tasks = [_make_task(f"k1_{i}", regime="H1_external", k=1) for i in range(2)]
        tasks = k0_tasks + k1_tasks

        cp = str(tmp_path / "cp.jsonl")
        _write_checkpoint_for_tasks(
            Path(cp),
            k0_tasks=k0_tasks, k0_label_pattern="all_correct",
            k1_tasks=k1_tasks, k1_label_pattern="converging",
        )
        runner, client = _make_noop_runner(cfg, tasks, cp, tmp_path)

        report = _rr.run_pilot_gate(
            cfg, tasks, checkpoint_path=cp,
            offline=True, cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )

        details = report.get("shuffle_null_details", [])
        assert details, "Expected at least one shuffle_null_details entry"

        for det in details:
            if det.get("null_cd_cd_primary") is None:
                continue  # inconclusive entry
            assert "null_cd_cd_primary" in det, (
                f"Entry missing null_cd_cd_primary: {det}"
            )
            assert "null_cd_frozen_fcr" in det, (
                f"Entry missing null_cd_frozen_fcr (Amdt 07 §2): {det}"
            )
            assert isinstance(det["null_cd_cd_primary"], float)
            assert isinstance(det["null_cd_frozen_fcr"], float)

    def test_report_has_null_cd_frozen_key(self, tmp_path):
        """Report dict must contain null_cd_frozen (mean FROZEN label_shuffle_null)."""
        from common.config import load_config
        cfg = load_config()

        k0_tasks = [_make_task(f"k0_{i}", regime="H1_external", k=0) for i in range(2)]
        k1_tasks = [_make_task(f"k1_{i}", regime="H1_external", k=1) for i in range(2)]
        tasks = k0_tasks + k1_tasks

        cp = str(tmp_path / "cp.jsonl")
        _write_checkpoint_for_tasks(
            Path(cp),
            k0_tasks=k0_tasks, k0_label_pattern="all_correct",
            k1_tasks=k1_tasks, k1_label_pattern="converging",
        )
        runner, client = _make_noop_runner(cfg, tasks, cp, tmp_path)

        report = _rr.run_pilot_gate(
            cfg, tasks, checkpoint_path=cp,
            offline=True, cache_dir=str(tmp_path / "llm_cache"),
            _runner_override=(runner, client),
        )

        assert "null_cd_frozen" in report, (
            "Report must contain 'null_cd_frozen' (FROZEN label_shuffle_null — Amdt 07 §2)"
        )
        assert isinstance(report["null_cd_frozen"], float)
        assert report["null_cd_frozen"] >= 0.0


# ─────────────────────────────────────────────────────────────────────────────
# GPT audit fix — MINOR: 4-interpretation uniform null scales with set size
# ─────────────────────────────────────────────────────────────────────────────

class TestUniformNullScalesWithInterpretations:
    """MINOR: 4-interpretation uniform null < 2-interpretation baseline (≈0.5)."""

    def test_four_interpretations_lower_than_two(self):
        """All-same-foil item with 4 interpretations yields CD_unif < 2-interp CD_unif.

        With k=2 (4 interpretations {I0, I1, I2, I3}) and 5 agents all labelling I1:
          2-interp (k=1): E[I1_count/5] = 0.5  (half of mass on I1)
          4-interp (k=2): probability mass split across I1, I2, I3
                          → E[max_foil/5] < 0.5  (lower null baseline)

        The 4-interp null is LOWER, confirming the null scales with interpretation-set size.
        """
        items_labels = [["I1", "I1", "I1", "I1", "I1"]]
        target = "I0"

        # 2-interpretation null (k=1)
        cd_unif_2interp = uniform_interpretation_null(
            items_labels, [["I0", "I1"]], target, n_perm=1000, seed=42
        )

        # 4-interpretation null (k=2)
        cd_unif_4interp = uniform_interpretation_null(
            items_labels, [["I0", "I1", "I2", "I3"]], target, n_perm=1000, seed=42
        )

        assert abs(cd_unif_2interp - 0.5) < 0.03, (
            f"2-interp null expected ≈ 0.5; got {cd_unif_2interp:.4f}"
        )
        assert cd_unif_4interp < cd_unif_2interp, (
            f"4-interp CD_unif ({cd_unif_4interp:.4f}) should be < 2-interp CD_unif "
            f"({cd_unif_2interp:.4f}). More interpretations → lower coordination baseline."
        )
        assert cd_unif_4interp > 0.1, (
            f"4-interp CD_unif ({cd_unif_4interp:.4f}) should be > 0.1 (non-trivial)"
        )
        assert cd_unif_4interp < 0.45, (
            f"4-interp CD_unif ({cd_unif_4interp:.4f}) should be < 0.45 (clearly below 2-interp)"
        )
