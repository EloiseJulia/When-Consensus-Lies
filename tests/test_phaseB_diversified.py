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
import scripts.phaseB_report as rep  # noqa: E402


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


# ─────────────────────────────────────────────────────────────────────────────
# 5. BLOCKER — path guard rejects confirmatory checkpoint/cache overrides
# ─────────────────────────────────────────────────────────────────────────────
def test_guard_rejects_confirmatory_checkpoint(cfg, tmp_path):
    import registered_run as rr

    tasks = rr.load_tasks()[:1]
    with pytest.raises(ValueError):
        drv.run(
            tasks,
            cfg,
            checkpoint_path="registered_run_checkpoint.jsonl",
            cache_dir=str(tmp_path / ".llm_cache_phaseB"),
            offline=True,
        )


def test_guard_rejects_confirmatory_cache(cfg, tmp_path):
    import registered_run as rr

    tasks = rr.load_tasks()[:1]
    with pytest.raises(ValueError):
        drv.run(
            tasks,
            cfg,
            checkpoint_path=str(tmp_path / "cp_phaseB.jsonl"),
            cache_dir=".llm_cache_registered_run",
            offline=True,
        )


def test_guard_rejects_non_runpartitions_checkpoint(cfg):
    import registered_run as rr

    tasks = rr.load_tasks()[:1]
    # A cwd-relative checkpoint that is neither under .run_partitions nor temp.
    with pytest.raises(ValueError):
        drv.run(
            tasks,
            cfg,
            checkpoint_path="some_other_dir/cp_phaseB.jsonl",
            cache_dir="some_other_dir/.llm_cache_phaseB",
            offline=True,
        )


def test_guard_allows_run_partitions_path(cfg, tmp_path):
    # A .run_partitions path (under a temp root) is allowed.
    import registered_run as rr

    tasks = rr.load_tasks()[:1]
    cp = tmp_path / ".run_partitions" / "cp_phaseB.jsonl"
    result = drv.run(
        tasks,
        cfg,
        checkpoint_path=str(cp),
        cache_dir=str(tmp_path / ".llm_cache_phaseB"),
        offline=True,
    )
    assert result["status"] == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# 6. MAJOR — R5 abstain form is recognized by the FROZEN detector, not I_perp-lost
# ─────────────────────────────────────────────────────────────────────────────
def test_r5_abstain_form_is_detected_as_abstention():
    from analysis.abstention import detect_abstention

    det = detect_abstention(div.ABSTAIN_FORM)
    assert det["abstained"] is True
    assert det["signal"] in ("CANNOT_DETERMINE", "NEED_MORE_INFO")


def test_r5_clarification_labeled_iperp_but_flagged(cfg):
    """A clarification is I_perp (CD-ineligible) yet VISIBLE to the detector."""
    import registered_run as rr
    from harness.label import label_run
    from analysis.abstention import detect_abstention
    from analysis.cd import cd_primary

    task = next(t for t in rr.load_tasks() if t.domain == "policy_qa")
    target = next((i.id for i in task.interpretations if i.is_target), "I0")

    run_obj = AgentRun(
        task_id=task.id,
        config=div.CONFIG_ROLE_DIVERSIFIED,
        model_role="tested_agents",
        model_id="claude-opus-4.8",
        output=div.ABSTAIN_FORM,
        label="",
        verbalized_conf=0.7,
        logit_conf=None,
        seed=cfg["seeds"]["global"],
    )
    lbl = label_run(run_obj, task)
    # A clarification carries no numeric answer → I_perp (ineligible for CD).
    assert lbl == "I_perp"
    # ... but the FROZEN abstention detector still counts it as clarification.
    assert detect_abstention(run_obj.output)["abstained"] is True
    # I_perp is NOT counted as a convergent wrong interpretation.
    assert cd_primary([lbl], target) == 0.0


def test_r5_prompt_contains_abstain_form(rec_client):
    task = _leak_task()
    div.run_role_diversified(task, rec_client)
    # The R5 integrator prompt (last recorded) must carry the exact abstain form.
    assert any(div.ABSTAIN_FORM in p for p in rec_client.recorded_prompts)


# ─────────────────────────────────────────────────────────────────────────────
# 7. MAJOR — reporter emits the P-B1/P-B2 deltas + CIs + abstention rates
# ─────────────────────────────────────────────────────────────────────────────
def _write_baseline_checkpoint(path: Path, tasks, seeds):
    """Write a small confirmatory-style heterogeneous-MAD checkpoint (all foil)."""
    import json

    with path.open("w", encoding="utf-8") as fh:
        for task in tasks:
            foil = next(
                (i.id for i in task.interpretations
                 if not i.is_target and i.id != "I_perp"),
                None,
            )
            if foil is None:
                continue
            for s in seeds:
                for agent_idx in range(4):  # heterogeneous-MAD n_agents=4
                    rec = {
                        "type": "run",
                        "task_id": task.id,
                        "config": "heterogeneous-MAD",
                        "model_role": "tested_agents",
                        "model_id": "gpt-5.4",
                        "output": f"baseline answer {agent_idx}",
                        "label": foil,  # all agents converge on the SAME foil
                        "verbalized_conf": 0.7,
                        "logit_conf": None,
                        "seed": s + agent_idx,
                        "replicate_seed": s,
                    }
                    fh.write(json.dumps(rec) + "\n")


def test_reporter_emits_deltas_and_abstention(cfg, tmp_path):
    import registered_run as rr

    all_tasks = rr.load_tasks()
    h1_tasks = [
        t for t in all_tasks
        if t.regime == "H1_external"
        and any((not i.is_target and i.id != "I_perp") for i in t.interpretations)
    ][:3]
    assert len(h1_tasks) == 3
    seeds = drv._default_seeds(cfg)

    # 1) Phase B checkpoint from the offline driver (labeled by frozen labeler).
    pb_cp = tmp_path / ".run_partitions" / "cp_phaseB.jsonl"
    drv.run(
        h1_tasks,
        cfg,
        checkpoint_path=str(pb_cp),
        cache_dir=str(tmp_path / ".llm_cache_phaseB"),
        offline=True,
    )
    assert pb_cp.exists()

    # 2) Baseline confirmatory (heterogeneous-MAD) checkpoint for the SAME items.
    base_cp = tmp_path / "confirmatory.jsonl"
    _write_baseline_checkpoint(base_cp, h1_tasks, seeds)

    # 3) Report — reuse the FROZEN CD + bootstrap + abstention machinery.
    report = rep.compute_report(
        str(pb_cp),
        str(base_cp),
        all_tasks,  # pass full task list for metadata lookup
    )

    contrasts = report["contrasts"]
    abstention = report["abstention"]

    for col in ("config", "prediction", "regime", "mean_cd",
                "baseline_mean_cd", "mean_delta", "delta_ci_lo",
                "delta_ci_hi", "n_delta_items"):
        assert col in contrasts.columns

    # Both predictions present on the H1_external bed with 3 paired items each.
    h1 = contrasts[contrasts["regime"] == "H1_external"]
    pb1 = h1[h1["config"] == div.CONFIG_CROSS_VENDOR_SYNTHESIS].iloc[0]
    pb2 = h1[h1["config"] == div.CONFIG_ROLE_DIVERSIFIED].iloc[0]
    assert pb1["prediction"] == "P-B1"
    assert pb2["prediction"] == "P-B2"
    for row in (pb1, pb2):
        assert row["n_delta_items"] == 3
        assert row["baseline_method"] == "heterogeneous-MAD"
        # Baseline all-foil → baseline_mean_cd == 1.0; deltas + CIs finite.
        assert row["baseline_mean_cd"] == 1.0
        import math
        assert math.isfinite(row["mean_delta"])
        assert math.isfinite(row["delta_ci_lo"])
        assert math.isfinite(row["delta_ci_hi"])
        assert row["delta_ci_lo"] <= row["delta_ci_hi"]

    # Abstention table present with a rate column per config.
    assert "abstention_rate" in abstention.columns
    assert set(abstention["config"]) >= {
        div.CONFIG_CROSS_VENDOR_SYNTHESIS,
        div.CONFIG_ROLE_DIVERSIFIED,
    }

