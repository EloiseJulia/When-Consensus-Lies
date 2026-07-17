"""Analysis-layer I/O: AgentRun-JSONL checkpoint → tidy agent-level DataFrame.

# Implementer model family: Claude/Anthropic

Deliverable D3 (paper/plans/2026-07-17-registered-run-wiring-plan.md):
Load an AgentRun-JSONL checkpoint file written by harness/runner.py and
produce the tidy agent-level DataFrame expected by analysis/contrasts.py.

Columns emitted (matching analysis.contrasts.COLS):
    task         — AgentRun.task_id
    method       — AgentRun.config (e.g. "single", "sc", "homogeneous-MAD")
    model_class  — DERIVED from (config, model_id, model_class_map); see below
    seed         — REPLICATE SEED (the runner JOB's grid seed, not per-agent seed)
    label        — AgentRun.label
    target       — is_target=True interpretation id (from the Task list)
    regime       — Task.regime ("H1_external" | "H2_derivable" | None)
    ambiguity_k  — Task.ambiguity_level (1 | 2 | 3)
    model        — AgentRun.model_id (extra; carries full slug for diagnostics)

BLOCKER 1 FIX — replicate_seed vs per-agent seed:
  An analysis "cell" = ONE ensemble replicate = ONE runner JOB.  An SC job with
  k=5 produces k agents all belonging to ONE cell.  harness/run.py assigns each
  agent seed = base_seed + i (distinct per agent), but compute_cell_cd groups by
  (item, method, model_class, seed) — so using the per-agent seed would split one
  5-agent ensemble into 5 singleton cells, corrupting CD to degenerate values.

  Fix: harness/runner.py CheckpointStore.add_run() now persists ``replicate_seed``
  (the runner grid seed shared by all agents in a job) alongside the per-agent
  ``seed``.  This adapter reads ``replicate_seed`` if present; for legacy records
  (single-agent jobs) where the field is absent, the per-agent ``seed`` is used
  as fallback (it IS the grid seed for single-agent jobs, so no information loss).

  Result: all k agents from one SC job get the SAME seed in the tidy table and
  form EXACTLY ONE cell in compute_cell_cd.

Model-class derivation (INVIOLABLE — do NOT change common/schema.py):
  AgentRun persists: task_id, config, model_role, model_id, output, label,
  verbalized_conf, logit_conf, seed. There is no model_class field. We derive
  model_class from the ALREADY-PERSISTED (config, model_id) pair:
    1. config == "heterogeneous-MAD" → always "heterogeneous" (mixed-family pool;
       individual model_ids are pool members, not a single-model class).
    2. model_id lookup in model_class_map (caller-supplied or FRONTIER_MODEL_CLASS_MAP).
    3. config-name heuristic: "homogeneous-MAD" / "homogeneous" → "homogeneous".
    4. Fallback → "unknown".
  Priority order ensures heterogeneous-MAD is always tagged correctly even when
  individual pool-member slugs also appear in other classes (e.g. gpt-5.4 is both
  the homogeneous baseline AND a heterogeneous pool member).

Auditor note (for hostile cross-family review):
  The model_class derivation depends entirely on config name + model_id, NOT on any
  new schema field. The only mutation risk is a wrong entry in FRONTIER_MODEL_CLASS_MAP
  or a caller-supplied map. Tests in tests/test_analysis_io.py exercise the
  priority order: heterogeneous-MAD overrides the map; map lookup overrides heuristic.
  The replicate_seed fallback logic is exercised by test_sc_ensemble_forms_one_cell.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

from analysis.contrasts import COLS
from common.schema import Task

# ── Amendment-06 frontier roster model-class map ──────────────────────────────
# Maps bare copilot-proxy slugs → model_class label for analysis/contrasts.
# Derived from config.yaml tested_agents sub-roles (D1). Update when roster changes.
FRONTIER_MODEL_CLASS_MAP: Dict[str, str] = {
    # homogeneous — shared-prior ρ-baseline
    "gpt-5.4": "homogeneous",
    # reasoning — frontier reasoning models (3 families)
    "gpt-5.6-sol": "reasoning",
    "claude-opus-4.8": "reasoning",
    "gemini-3.1-pro-preview": "reasoning",
    # weak — non-frontier baselines (3 families)
    "gpt-4o-mini": "weak",
    "gemini-3.5-flash": "weak",
    "claude-haiku-4.5": "weak",
    # heterogeneous pool member (also appears as homogeneous, so priority
    # rule 1 — config=="heterogeneous-MAD" — takes precedence for that config)
    "claude-sonnet-4.6": "heterogeneous",
}

# ── Column name shorthands (from analysis.contrasts.COLS) ────────────────────
_ITEM = COLS["item"]           # "task"
_METHOD = COLS["method"]       # "method"
_MODEL_CLASS = COLS["model_class"]  # "model_class"
_SEED = COLS["seed"]           # "seed"
_LABEL = COLS["label"]         # "label"
_TARGET = COLS["target"]       # "target"
_REGIME = COLS["regime"]       # "regime"
_AMBIGUITY_K = COLS["ambiguity_k"]  # "ambiguity_k"
_MODEL = "model"               # extra column: raw model_id


def _derive_model_class(
    config_name: str,
    model_id: str,
    model_class_map: Optional[Dict[str, str]],
) -> str:
    """Derive model_class from persisted (config, model_id) without schema changes.

    Priority order (see module docstring):
      1. heterogeneous-MAD → "heterogeneous" (always, pool-level assignment).
      2. model_class_map lookup on model_id.
      3. Config-name heuristic ("homogeneous" substring → "homogeneous").
      4. Fallback → "unknown".
    """
    if config_name == "heterogeneous-MAD":
        return "heterogeneous"
    if model_class_map:
        mc = model_class_map.get(model_id)
        if mc is not None:
            return mc
    if "homogeneous" in config_name:
        return "homogeneous"
    return "unknown"


def load_runs_tidy(
    checkpoint_path: Union[str, Path],
    tasks: List[Task],
    *,
    model_class_map: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """Load an AgentRun-JSONL checkpoint into a tidy agent-level DataFrame.

    The emitted table is directly consumable by analysis.contrasts functions
    (compute_cell_cd, aggregation_vs_single, cross_model_vs_homogeneous, etc.)
    because it carries all columns in analysis.contrasts.COLS plus a ``model``
    column with the raw model_id for diagnostics.

    Args:
        checkpoint_path: Path to the runner checkpoint JSONL file (written by
            harness/runner.py CheckpointStore). May be missing → empty DataFrame.
        tasks: Task list used to look up per-task metadata (regime, ambiguity_level,
            target interpretation id). Any task_id not present in ``tasks`` is
            silently dropped (the task was not in this run's scope).
        model_class_map: Optional slug → model_class dict. When None, defaults to
            :data:`FRONTIER_MODEL_CLASS_MAP`. Pass a custom map when using a
            non-frontier roster. Heterogeneous-MAD runs are ALWAYS assigned
            "heterogeneous" regardless of any map entry.

    Returns:
        tidy DataFrame with one row per labeled AgentRun, columns:
            task, method, model_class, seed, label, target, regime, ambiguity_k, model
        An empty DataFrame with the correct columns when the file is missing,
        empty, or contains no valid labeled run records.

    Note:
        Only records of type ``"run"`` with a non-empty ``label`` field are included.
        Records with an empty or unrecognized ``task_id`` are silently dropped.
    """
    checkpoint_path = Path(checkpoint_path)
    if model_class_map is None:
        model_class_map = FRONTIER_MODEL_CLASS_MAP

    # Build task metadata lookup: task_id → (target_label, regime, ambiguity_level)
    task_meta: Dict[str, tuple] = {}
    for task in tasks:
        target = next(
            (i.id for i in task.interpretations if i.is_target), "I0"
        )
        task_meta[task.id] = (target, task.regime, task.ambiguity_level)

    cols = [_ITEM, _METHOD, _MODEL_CLASS, _SEED, _LABEL, _TARGET,
            _REGIME, _AMBIGUITY_K, _MODEL]
    rows: List[Dict] = []

    if not checkpoint_path.exists():
        return pd.DataFrame(columns=cols)

    with open(checkpoint_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") != "run":
                continue
            label = rec.get("label", "")
            if not label:
                continue
            task_id = rec.get("task_id", "")
            meta = task_meta.get(task_id)
            if meta is None:
                continue
            target, regime, ambiguity_level = meta
            config_name = rec.get("config", "")
            model_id = rec.get("model_id", "")
            # B1 fix: use replicate_seed (grid/job seed) if persisted; fall back
            # to per-agent seed for legacy single-agent records where both are equal.
            seed = int(rec.get("replicate_seed", rec.get("seed", 0)))
            mc = _derive_model_class(config_name, model_id, model_class_map)
            rows.append({
                _ITEM: task_id,
                _METHOD: config_name,
                _MODEL_CLASS: mc,
                _SEED: seed,
                _LABEL: label,
                _TARGET: target,
                _REGIME: regime,
                _AMBIGUITY_K: ambiguity_level,
                _MODEL: model_id,
            })

    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)
