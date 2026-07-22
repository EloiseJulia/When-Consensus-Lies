# constructed by: Claude (Anthropic) family
"""Offline tests for the Phase B exploratory diversified-evidence conditions.

# Implementer model family: Claude / Anthropic
# Auditor model family: GPT (Law 6 — cross-family requirement)

All tests run OFFLINE (mock LLMClient, no network). They assert:
  1. Job enumeration counts (2 configs x 54 items x 3 seeds = 324).
  2. The driver writes to the SEPARATE cp_phaseB checkpoint, never the
     confirmatory checkpoint.
  3. ANTI-LEAKAGE (design §4): none of the prompts actually sent for a task
     contains the task's target interpretation text, gold_check, interp.id, or
     the foil labels. (Constructs a task with distinctive gold sentinels and
     asserts every C5/C7 prompt is free of them.)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
for _p in (str(_REPO_ROOT), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common.config import load_config
from common.llm import LLMClient
from common.schema import Task, Interpretation, AgentRun

import harness.diversified as div
import scripts.phaseB_diversified as drv  # noqa: E402  (scripts/ import path set above)


# ─────────────────────────────────────────────────────────────────────────────
# Recording client — captures every prompt actually sent to complete().
# ─────────────────────────────────────────────────────────────────────────────
class RecordingClient(LLMClient):
    """Offline mock client that records every prompt string passed to complete()."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.recorded_prompts: List[str] = []

    def complete(self, role, prompt, *args, **kwargs):  # type: ignore[override]
        self.recorded_prompts.append(prompt)
        return super().complete(role, prompt, *args, **kwargs)


def _leak_task() -> Task:
    """A task whose OFF-LIMITS fields carry distinctive sentinels.

    The sentinels appear ONLY in fields the diversified prompts must NEVER read
    (interpretation ids, gold_check, latent_spec, key_questions). ``task.prompt``
    is generic and contains none of them.
    """
    return Task(
        id="LEAKTASK_001",
        domain="code_spec",
        prompt="Write a function that aggregates the values described above.",
        latent_spec="LATENTSPEC_SECRET_LEAK: the hidden convention is XYZ.",
        interpretations=[
            Interpretation(
                id="IXYZLEAK_TARGET",
                is_target=True,
                gold_check="GOLDCHECK_SECRET_LEAK_QWERTY",
            ),
            Interpretation(
                id="FOILALPHA_LEAK",
                is_target=False,
                gold_check="FOILBETA_LEAK_CHECK",
            ),
        ],
        ambiguity_level=2,
        key_questions=["KEYQ_SECRET_LEAK: which convention applies?"],
        regime="H1_external",
    )


#: Every sentinel that must NOT appear in any prompt (target/foil/id/gold_check).
_SENTINELS = [
    "IXYZLEAK_TARGET",
    "FOILALPHA_LEAK",
    "FOILBETA_LEAK_CHECK",
    "GOLDCHECK_SECRET_LEAK_QWERTY",
    "LATENTSPEC_SECRET_LEAK",
    "KEYQ_SECRET_LEAK",
]


@pytest.fixture()
def cfg():
    return load_config()


@pytest.fixture()
def rec_client(cfg, tmp_path):
    return RecordingClient(
        cfg, cache_dir=str(tmp_path / ".llm_cache_phaseB_test"), offline=True
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Job enumeration counts
# ─────────────────────────────────────────────────────────────────────────────
def test_enumeration_counts(cfg):
    import registered_run as rr

    tasks = rr.load_tasks()
    assert len(tasks) == 54  # 40 H1_external + 14 H2_derivable

    seeds = drv._default_seeds(cfg)
    assert len(seeds) == 3
    assert seeds == [
        cfg["seeds"]["global"],
        cfg["seeds"]["global"] + 1000,
        cfg["seeds"]["global"] + 2000,
    ]

    jobs = drv.enumerate_jobs(tasks, drv._CONFIGS_PHASEB, seeds)
    assert len(jobs) == 2 * 54 * 3 == 324

    # Balanced across the two configs.
    per_config = {c: 0 for c in drv._CONFIGS_PHASEB}
    for j in jobs:
        per_config[j["config"]] += 1
    assert per_config == {
        div.CONFIG_CROSS_VENDOR_SYNTHESIS: 162,
        div.CONFIG_ROLE_DIVERSIFIED: 162,
    }


def test_dry_run_report(cfg, tmp_path):
    import registered_run as rr

    tasks = rr.load_tasks()
    result = drv.run(
        tasks,
        cfg,
        checkpoint_path=str(tmp_path / "cp_phaseB.jsonl"),
        dry_run=True,
    )
    assert result["status"] == "dry_run"
    assert result["total"] == 324
    assert result["done"] == 0
    assert result["pending"] == 324


# ─────────────────────────────────────────────────────────────────────────────
# 2. Driver writes to cp_phaseB, NOT the confirmatory checkpoint
# ─────────────────────────────────────────────────────────────────────────────
def test_driver_writes_separate_checkpoint(cfg, tmp_path):
    import registered_run as rr
    from harness.runner import CheckpointStore

    # Guard: the confirmatory checkpoint file must not be touched.
    confirmatory_cp = _REPO_ROOT / rr.FULL_CHECKPOINT
    before_exists = confirmatory_cp.exists()
    before_mtime = confirmatory_cp.stat().st_mtime if before_exists else None

    tasks = rr.load_tasks()[:3]  # small subset — offline, deterministic
    cp_path = tmp_path / "cp_phaseB.jsonl"

    result = drv.run(
        tasks,
        cfg,
        checkpoint_path=str(cp_path),
        cache_dir=str(tmp_path / ".llm_cache_phaseB"),
        offline=True,
    )

    assert result["status"] == "ok"
    # 2 configs x 3 tasks x 3 seeds = 18 jobs.
    assert result["completed"] == 18
    assert result["total"] == 18
    assert cp_path.exists()

    # Records are consumable by CheckpointStore (same shape as confirmatory).
    store = CheckpointStore(cp_path)
    assert store.n_done_jobs == 18
    assert store.n_runs == 18  # one final AgentRun per job
    configs_seen = {r["config"] for r in store.all_runs()}
    assert configs_seen == {
        div.CONFIG_CROSS_VENDOR_SYNTHESIS,
        div.CONFIG_ROLE_DIVERSIFIED,
    }

    # The confirmatory checkpoint is byte-for-byte untouched.
    after_exists = confirmatory_cp.exists()
    assert after_exists == before_exists
    if before_exists:
        assert confirmatory_cp.stat().st_mtime == before_mtime


def test_driver_resumable(cfg, tmp_path):
    import registered_run as rr

    tasks = rr.load_tasks()[:2]
    cp_path = tmp_path / "cp_phaseB.jsonl"
    common = dict(
        checkpoint_path=str(cp_path),
        cache_dir=str(tmp_path / ".llm_cache_phaseB"),
        offline=True,
    )
    first = drv.run(tasks, cfg, **common)
    assert first["completed"] == 12  # 2 configs x 2 tasks x 3 seeds

    # Re-run: everything already done → all skipped, no new work.
    second = drv.run(tasks, cfg, **common)
    assert second["completed"] == 0
    assert second["skipped"] == 12


# ─────────────────────────────────────────────────────────────────────────────
# 3. ANTI-LEAKAGE — required (design §4)
# ─────────────────────────────────────────────────────────────────────────────
def _assert_no_leak(prompts: List[str]):
    assert prompts, "expected at least one prompt to be recorded"
    joined = "\n".join(prompts)
    # Sanity: the underspecified task prompt IS present (we captured real prompts).
    assert "aggregates the values described above" in joined
    for sentinel in _SENTINELS:
        for i, p in enumerate(prompts):
            assert sentinel not in p, (
                f"ANTI-LEAKAGE VIOLATION: sentinel {sentinel!r} leaked into "
                f"prompt #{i}:\n{p}"
            )


def test_c5_synthesis_no_leak(rec_client):
    task = _leak_task()
    runs = div.run_cross_vendor_synthesis(task, rec_client)
    assert len(runs) == 1
    assert runs[0].config == div.CONFIG_CROSS_VENDOR_SYNTHESIS
    # 3 candidate generations + 1 synthesizer = 4 prompts.
    assert len(rec_client.recorded_prompts) == 4
    _assert_no_leak(rec_client.recorded_prompts)


def test_c7_role_diversified_no_leak(rec_client):
    task = _leak_task()
    runs = div.run_role_diversified(task, rec_client)
    assert len(runs) == 1
    assert runs[0].config == div.CONFIG_ROLE_DIVERSIFIED
    # R1..R4 + R5 integrator = 5 prompts.
    assert len(rec_client.recorded_prompts) == 5
    _assert_no_leak(rec_client.recorded_prompts)


def test_prompt_templates_have_no_oracle_placeholders():
    """The template constants themselves must not reference oracle fields."""
    templates = [
        div.PROMPT_C5_SYNTHESIS_V1,
        div.PROMPT_C7_R1_SOLVER_V1,
        div.PROMPT_C7_R2_GAPFINDER_V1,
        div.PROMPT_C7_R3_ALTERNATIVES_V1,
        div.PROMPT_C7_R4_DEFAULTCHECK_V1,
        div.PROMPT_C7_R5_INTEGRATOR_V1,
    ]
    banned = ["gold_check", "interp.id", "is_target", "interpretation_hint",
              "latent_spec", "target interpretation"]
    for t in templates:
        low = t.lower()
        for b in banned:
            assert b.lower() not in low, f"template references banned token {b!r}"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Provenance: synthesizer is pool-external; roles are cross-family
# ─────────────────────────────────────────────────────────────────────────────
def test_c5_synthesizer_is_pool_external(rec_client):
    task = _leak_task()
    runs = div.run_cross_vendor_synthesis(task, rec_client)
    # Synthesizer = frozen judge model (microsoft/mai-code — outside tested pool).
    assert runs[0].model_role == "judge"
    assert runs[0].model_id == rec_client.config["roles"]["judge"]["model"]
    pool_models = {m["model"] for m in
                   rec_client.config["roles"]["tested_agents"]["heterogeneous"]}
    assert runs[0].model_id not in pool_models


def test_c7_integrator_identity(rec_client):
    task = _leak_task()
    runs = div.run_role_diversified(task, rec_client)
    assert runs[0].model_role == "tested_agents"
    assert runs[0].model_id == "claude-opus-4.8"
