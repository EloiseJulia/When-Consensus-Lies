"""Golden/unit tests for analysis/io.py (Deliverable D3).

# Implementer model family: Claude/Anthropic

All tests run OFFLINE — zero network calls. Uses synthetic AgentRun-JSONL
fixtures written in-test and Task objects constructed directly.

Coverage:
  1. Golden model_class derivation: priority order verified (heterogeneous-MAD >
     map lookup > heuristic > fallback). Auditor-critical path.
  2. load_runs_tidy on synthetic JSONL: column presence, regime/ambiguity_k passthrough,
     target extraction, model_class assignment.
  3. Missing / empty checkpoint → empty DataFrame with correct columns.
  4. Records with missing task_id, empty label, or unknown type are dropped.
  5. FRONTIER_MODEL_CLASS_MAP covers all Amendment-06 roster slugs.
  6. load_runs_tidy on a multi-domain synthetic JSONL (tasks from multiple domains).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from analysis.contrasts import COLS
from analysis.io import (
    FRONTIER_MODEL_CLASS_MAP,
    _derive_model_class,
    load_runs_tidy,
)
from common.schema import Interpretation, Task


# ── Test helpers ─────────────────────────────────────────────────────────────

def _make_task(
    task_id: str,
    regime: str = "H1_external",
    k: int = 1,
    domain: str = "code_spec",
    target_id: str = "I0",
) -> Task:
    return Task(
        id=task_id,
        domain=domain,
        prompt=f"prompt for {task_id}",
        latent_spec="spec",
        interpretations=[
            Interpretation(id=target_id, is_target=True, gold_check="g0"),
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
    **extra,
) -> Dict[str, Any]:
    return {
        "type": "run",
        "task_id": task_id,
        "config": config,
        "model_role": "tested_agents",
        "model_id": model_id,
        "output": f"output_{task_id}_{model_id}",
        "label": label,
        "verbalized_conf": 0.5,
        "logit_conf": None,
        "seed": seed,
        **extra,
    }


def _write_jsonl(path: Path, records: List[Dict]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


# ── Column names from COLS ────────────────────────────────────────────────────
_ITEM = COLS["item"]
_METHOD = COLS["method"]
_MODEL_CLASS = COLS["model_class"]
_SEED = COLS["seed"]
_LABEL = COLS["label"]
_TARGET = COLS["target"]
_REGIME = COLS["regime"]
_AMBIGUITY_K = COLS["ambiguity_k"]
_MODEL = "model"

_REQUIRED_COLS = [
    _ITEM, _METHOD, _MODEL_CLASS, _SEED, _LABEL, _TARGET, _REGIME, _AMBIGUITY_K, _MODEL
]


# ── 1. model_class derivation (auditor-critical) ──────────────────────────────

class TestDeriveModelClass:
    """Priority order: heterogeneous-MAD > map > heuristic > fallback."""

    def test_heterogeneous_mad_always_wins(self):
        """heterogeneous-MAD config is always 'heterogeneous', ignores map."""
        mc_map = {"gpt-5.4": "homogeneous", "gemini-3.1-pro-preview": "reasoning"}
        # Even if the model_id is in the map as something else, config wins.
        assert _derive_model_class("heterogeneous-MAD", "gpt-5.4", mc_map) == "heterogeneous"
        assert _derive_model_class("heterogeneous-MAD", "claude-sonnet-4.6", mc_map) == "heterogeneous"
        assert _derive_model_class("heterogeneous-MAD", "unknown-model", mc_map) == "heterogeneous"

    def test_map_lookup_beats_heuristic(self):
        """Explicit map entry wins over the config-name heuristic."""
        mc_map = {"gpt-4o-mini": "weak"}
        # "single" config has no heuristic match; map provides the class.
        assert _derive_model_class("single", "gpt-4o-mini", mc_map) == "weak"
        # "homogeneous-MAD" heuristic would give "homogeneous", but map overrides.
        mc_map2 = {"gpt-4o-mini": "custom-class"}
        assert _derive_model_class("homogeneous-MAD", "gpt-4o-mini", mc_map2) == "custom-class"

    def test_heuristic_when_no_map_entry(self):
        """Config-name heuristic fires when map has no entry for model_id."""
        mc_map = {"other-model": "reasoning"}
        assert _derive_model_class("homogeneous-MAD", "unknown-slug", mc_map) == "homogeneous"

    def test_fallback_unknown(self):
        """No matching config heuristic and no map → 'unknown'."""
        assert _derive_model_class("single", "mystery-model", {}) == "unknown"
        assert _derive_model_class("sc", "mystery-model", None) == "unknown"

    def test_none_map_uses_heuristic(self):
        """model_class_map=None falls through to heuristic."""
        assert _derive_model_class("homogeneous-MAD", "any-slug", None) == "homogeneous"
        assert _derive_model_class("sc", "any-slug", None) == "unknown"

    def test_heterogeneous_mad_ignores_none_map(self):
        assert _derive_model_class("heterogeneous-MAD", "gpt-5.4", None) == "heterogeneous"


# ── 2. load_runs_tidy — basic functionality ───────────────────────────────────

class TestLoadRunsTidy:

    def test_returns_correct_columns(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        task = _make_task("t1", regime="H1_external", k=2)
        _write_jsonl(cp, [_make_run_record("t1", "sc", "gpt-5.4", "I0", seed=42)])
        df = load_runs_tidy(cp, [task])
        for col in _REQUIRED_COLS:
            assert col in df.columns, f"Missing column: {col}"

    def test_regime_and_ambiguity_k_passthrough(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        task = _make_task("t1", regime="H2_derivable", k=3)
        _write_jsonl(cp, [_make_run_record("t1", "single", "claude-haiku-4.5", "I1", seed=7)])
        df = load_runs_tidy(cp, [task])
        assert len(df) == 1
        assert df.iloc[0][_REGIME] == "H2_derivable"
        assert df.iloc[0][_AMBIGUITY_K] == 3

    def test_target_extracted_from_task(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        task = _make_task("t1", target_id="I0")
        _write_jsonl(cp, [_make_run_record("t1", "sc", "gpt-5.4", "I1")])
        df = load_runs_tidy(cp, [task])
        assert df.iloc[0][_TARGET] == "I0"

    def test_model_class_from_frontier_map(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        task = _make_task("t1")
        records = [
            _make_run_record("t1", "sc", "gpt-5.4", "I0"),       # homogeneous
            _make_run_record("t1", "sc", "gpt-5.6-sol", "I1"),   # reasoning
            _make_run_record("t1", "sc", "gpt-4o-mini", "I0"),   # weak
            _make_run_record("t1", "heterogeneous-MAD", "gpt-5.4", "I_perp"),  # heterogeneous
        ]
        _write_jsonl(cp, records)
        df = load_runs_tidy(cp, [task])
        assert len(df) == 4
        mc_map = dict(zip(df["model"], df[_MODEL_CLASS]))
        # Note: gpt-5.4 appears twice (sc and heterogeneous-MAD); model_class differs
        sc_rows = df[df[_METHOD] == "sc"]
        hetero_rows = df[df[_METHOD] == "heterogeneous-MAD"]
        assert sc_rows[sc_rows[_MODEL] == "gpt-5.4"].iloc[0][_MODEL_CLASS] == "homogeneous"
        assert sc_rows[sc_rows[_MODEL] == "gpt-5.6-sol"].iloc[0][_MODEL_CLASS] == "reasoning"
        assert sc_rows[sc_rows[_MODEL] == "gpt-4o-mini"].iloc[0][_MODEL_CLASS] == "weak"
        assert hetero_rows.iloc[0][_MODEL_CLASS] == "heterogeneous"

    def test_multiple_items_multiple_seeds(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        tasks = [_make_task("t1"), _make_task("t2", regime="H2_derivable")]
        records = [
            _make_run_record("t1", "sc", "gpt-5.4", "I0", seed=42),
            _make_run_record("t1", "sc", "gpt-5.4", "I1", seed=43),
            _make_run_record("t2", "sc", "gpt-5.4", "I0", seed=42),
        ]
        _write_jsonl(cp, records)
        df = load_runs_tidy(cp, tasks)
        assert len(df) == 3
        assert set(df[_ITEM]) == {"t1", "t2"}

    def test_custom_model_class_map(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        task = _make_task("t1")
        custom_map = {"custom-slug": "custom-class"}
        _write_jsonl(cp, [_make_run_record("t1", "sc", "custom-slug", "I0")])
        df = load_runs_tidy(cp, [task], model_class_map=custom_map)
        assert df.iloc[0][_MODEL_CLASS] == "custom-class"


# ── 3. Edge cases ─────────────────────────────────────────────────────────────

class TestLoadRunsTidyEdgeCases:

    def test_missing_checkpoint_returns_empty(self, tmp_path):
        df = load_runs_tidy(tmp_path / "nonexistent.jsonl", [_make_task("t1")])
        assert len(df) == 0
        for col in _REQUIRED_COLS:
            assert col in df.columns

    def test_empty_checkpoint_returns_empty(self, tmp_path):
        cp = tmp_path / "empty.jsonl"
        cp.write_text("")
        df = load_runs_tidy(cp, [_make_task("t1")])
        assert len(df) == 0

    def test_unknown_task_id_dropped(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        task = _make_task("known_task")
        _write_jsonl(cp, [
            _make_run_record("known_task", "sc", "gpt-5.4", "I0"),
            _make_run_record("unknown_task", "sc", "gpt-5.4", "I1"),
        ])
        df = load_runs_tidy(cp, [task])
        assert len(df) == 1
        assert df.iloc[0][_ITEM] == "known_task"

    def test_empty_label_dropped(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        task = _make_task("t1")
        _write_jsonl(cp, [
            _make_run_record("t1", "sc", "gpt-5.4", "I0"),
            _make_run_record("t1", "sc", "gpt-5.4", ""),  # empty label
        ])
        df = load_runs_tidy(cp, [task])
        assert len(df) == 1

    def test_non_run_type_records_dropped(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        task = _make_task("t1")
        _write_jsonl(cp, [
            {"type": "job_done", "task_id": "t1", "config": "sc",
             "model_role": "tested_agents", "model_id": "gpt-5.4", "seed": 42},
            {"type": "cost_delta", "cost_usd": 0.01},
            _make_run_record("t1", "sc", "gpt-5.4", "I0"),
        ])
        df = load_runs_tidy(cp, [task])
        assert len(df) == 1

    def test_corrupt_json_line_skipped(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        task = _make_task("t1")
        with open(cp, "w") as fh:
            fh.write(json.dumps(_make_run_record("t1", "sc", "gpt-5.4", "I0")) + "\n")
            fh.write("{this is not valid json\n")
            fh.write(json.dumps(_make_run_record("t1", "sc", "gpt-5.4", "I1")) + "\n")
        df = load_runs_tidy(cp, [task])
        assert len(df) == 2  # corrupt line skipped, valid lines loaded

    def test_task_with_none_regime(self, tmp_path):
        cp = tmp_path / "cp.jsonl"
        task = _make_task("t1", regime=None)
        _write_jsonl(cp, [_make_run_record("t1", "sc", "gpt-5.4", "I0")])
        # Task with regime=None is allowed (untagged); row should still be included.
        df = load_runs_tidy(cp, [task])
        assert len(df) == 1
        assert df.iloc[0][_REGIME] is None


# ── 4. Multi-domain load ──────────────────────────────────────────────────────

def test_multi_domain_all_tasks_loaded(tmp_path):
    """load_runs_tidy handles tasks from code_spec + data_analysis + policy_qa."""
    tasks = [
        _make_task("code_001", domain="code_spec", regime="H1_external", k=1),
        _make_task("data_001", domain="data_analysis", regime="H2_derivable", k=2),
        _make_task("policy_001", domain="policy_qa", regime="H1_external", k=3),
    ]
    records = [
        _make_run_record("code_001", "sc", "gpt-5.4", "I0"),
        _make_run_record("data_001", "sc", "gpt-4o-mini", "I1"),
        _make_run_record("policy_001", "sc", "claude-haiku-4.5", "I0"),
    ]
    cp = tmp_path / "multi_domain.jsonl"
    _write_jsonl(cp, records)
    df = load_runs_tidy(cp, tasks)
    assert len(df) == 3
    assert set(df[_ITEM]) == {"code_001", "data_001", "policy_001"}
    # Check regime passthrough
    assert df[df[_ITEM] == "code_001"].iloc[0][_REGIME] == "H1_external"
    assert df[df[_ITEM] == "data_001"].iloc[0][_REGIME] == "H2_derivable"
    # Check k passthrough
    assert df[df[_ITEM] == "code_001"].iloc[0][_AMBIGUITY_K] == 1
    assert df[df[_ITEM] == "data_001"].iloc[0][_AMBIGUITY_K] == 2
    assert df[df[_ITEM] == "policy_001"].iloc[0][_AMBIGUITY_K] == 3
    # Check model_class
    assert df[df[_ITEM] == "code_001"].iloc[0][_MODEL_CLASS] == "homogeneous"
    assert df[df[_ITEM] == "data_001"].iloc[0][_MODEL_CLASS] == "weak"
    assert df[df[_ITEM] == "policy_001"].iloc[0][_MODEL_CLASS] == "weak"


# ── 5. FRONTIER_MODEL_CLASS_MAP covers all Amendment-06 roster slugs ──────────

def test_frontier_map_covers_all_amendment06_slugs():
    """Every A06 roster slug must map to a known class (auditor guard)."""
    expected_slugs = {
        # homogeneous
        "gpt-5.4",
        # reasoning
        "gpt-5.6-sol", "claude-opus-4.8", "gemini-3.1-pro-preview",
        # weak
        "gpt-4o-mini", "gemini-3.5-flash", "claude-haiku-4.5",
        # heterogeneous pool (individual members; pool runs are class="heterogeneous" via config)
        "claude-sonnet-4.6",
    }
    missing = expected_slugs - set(FRONTIER_MODEL_CLASS_MAP)
    assert not missing, f"Missing slugs in FRONTIER_MODEL_CLASS_MAP: {missing}"

    known_classes = {"homogeneous", "reasoning", "weak", "heterogeneous"}
    bad = {s: c for s, c in FRONTIER_MODEL_CLASS_MAP.items() if c not in known_classes}
    assert not bad, f"Unknown model_class values: {bad}"


def test_gpt54_maps_to_homogeneous():
    assert FRONTIER_MODEL_CLASS_MAP["gpt-5.4"] == "homogeneous"


def test_reasoning_slugs_map_correctly():
    assert FRONTIER_MODEL_CLASS_MAP["gpt-5.6-sol"] == "reasoning"
    assert FRONTIER_MODEL_CLASS_MAP["claude-opus-4.8"] == "reasoning"
    assert FRONTIER_MODEL_CLASS_MAP["gemini-3.1-pro-preview"] == "reasoning"


def test_weak_slugs_map_correctly():
    assert FRONTIER_MODEL_CLASS_MAP["gpt-4o-mini"] == "weak"
    assert FRONTIER_MODEL_CLASS_MAP["gemini-3.5-flash"] == "weak"
    assert FRONTIER_MODEL_CLASS_MAP["claude-haiku-4.5"] == "weak"
