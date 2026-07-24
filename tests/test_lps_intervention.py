# constructed by: Claude (Anthropic) family
"""Offline unit tests for the Study-2 INTERVENTION driver + report (Phase 2b).

# Implementer model family: Claude / Anthropic
# Auditor model family: MUST be non-Anthropic (Law 6 — cross-family requirement)

All tests run OFFLINE (no network / no live model). They assert:
  1. H-B1' clarify decisions per policy on synthetic AMB+/AMB−/danger records
     (LPP fires in the danger quadrant where the semantic-entropy gate is blind;
     neither fires on k0/AMB−).
  2. H-B2' oracle path → label I0 → executable ``cd_primary`` → 0, while the
     never-clarify baseline path yields a non-zero ``cd_primary``.
  3. ANTI-LEAKAGE (inviolable): no gold / target / foil / key_questions /
     interpretation text reaches ANY detector / surfacing / clarify prompt — ONLY
     the H-B2' oracle re-ask (marked ``Clarification from the user:``) may carry
     the gold convention.
  4. The driver REFUSES to read/write any confirmatory checkpoint/cache.
  5. Dry-run / job enumeration / fingerprint sanity + report aggregation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List, Optional

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
for _p in (str(_REPO_ROOT), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common.schema import Task, Interpretation  # noqa: E402
import lps_method as lps  # noqa: E402
import lps_gold as lgold  # noqa: E402
import lps_intervention as intv  # noqa: E402
import lps_intervention_merge as merge  # noqa: E402
import lps_intervention_report as report  # noqa: E402
from analysis.cd import cd_primary  # noqa: E402


class ScriptedClient:
    """Records every prompt; returns a scripted completion by prompt content."""

    def __init__(self, fn):
        self._fn = fn
        self.recorded_prompts: List[str] = []

    def complete(self, role, prompt, seed=None, model=None, temperature=None, **kw):
        self.recorded_prompts.append(prompt)
        text = self._fn(role, prompt, seed)
        return SimpleNamespace(text=text, model=model or "mock", tokens_in=0,
                               tokens_out=0, cost_usd=0.0, logit_conf=None)


@pytest.fixture(autouse=True)
def _stub_labeler(monkeypatch):
    # Identity labeler: the returned model text IS the interpretation label.
    monkeypatch.setattr(lps, "label_run", lambda run, task: run.output)


def _task(tid="T1", prompt="Do the thing.", domain="code_spec",
          latent_spec="spec", key_questions=None) -> Task:
    return Task(
        id=tid, domain=domain, prompt=prompt, latent_spec=latent_spec,
        interpretations=[Interpretation(id="I0", is_target=True, gold_check="g")],
        ambiguity_level=1, key_questions=key_questions or [], regime="H1_external",
    )


# ── 1. H-B1' clarify decisions per policy ────────────────────────────────────

def _detect(*, is_flagged, h_seed, seed_labels, surfaced_dims):
    return {
        "is_flagged": is_flagged,
        "H_seed": h_seed,
        "H_ctx_max": 1.0 if is_flagged else 0.0,
        "seed_labels": seed_labels,
        "surfaced_dims": surfaced_dims,
    }


def test_clarify_danger_quadrant_lpp_fires_se_blind():
    # AMB+ DANGER item: confident reseed (low H_seed, consistent labels) yet a
    # surfaced dimension changes the answer → LPP flags; the semantic-entropy gate
    # is BLIND (H_seed ≤ τ_s), self-consistency is blind (labels agree).
    d = _detect(is_flagged=True, h_seed=0.2, seed_labels=["I1", "I1", "I1"],
                surfaced_dims=[{"dimension": "aggregation", "values": ["a", "b"]}])
    c = intv.clarify_decisions(d)
    assert c["lpp_gated"] is True
    assert c["always"] is True
    assert c["semantic_entropy_gated"] is False      # H_seed ≤ τ_s → blind
    assert c["self_consistency_gated"] is False       # labels agree → blind
    assert c["requirements_probing_gated"] is True    # ≥1 surfaced dim


def test_clarify_high_hseed_semantic_entropy_fires():
    # When resampling looks uncertain (H_seed > τ_s), the SE gate DOES fire; the
    # LPP item flag requires H_seed ≤ τ_s so is_flagged is provided separately.
    d = _detect(is_flagged=False, h_seed=0.9, seed_labels=["I0", "I1", "I2"],
                surfaced_dims=[{"dimension": "x", "values": ["a", "b"]}])
    c = intv.clarify_decisions(d)
    assert c["semantic_entropy_gated"] is True
    assert c["self_consistency_gated"] is True         # labels disagree
    assert c["lpp_gated"] is False


def test_clarify_k0_amb_neg_none_fire_except_always():
    # AMB− / k0 control: no answer-changing dimension, confident + consistent → the
    # LPP / SE / self-consistency / requirements gates all STAY SILENT (only the
    # always-clarify baseline fires → it over-clarifies).
    d = _detect(is_flagged=False, h_seed=0.0, seed_labels=["I0", "I0", "I0"],
                surfaced_dims=[])
    c = intv.clarify_decisions(d)
    assert c["lpp_gated"] is False
    assert c["semantic_entropy_gated"] is False
    assert c["self_consistency_gated"] is False
    assert c["requirements_probing_gated"] is False
    assert c["always"] is True


# ── 2. H-B2' oracle resolution (executable cd_primary) ───────────────────────

def test_compute_cell_hb2_oracle_resolves_baseline_does_not():
    dims_json = '[{"dimension": "aggregation", "values": ["sum", "mean"]}]'

    def fn(role, prompt, seed):
        if intv.ORACLE_PREFIX in prompt:
            return "I0"           # oracle re-ask → converges on the true intent
        if "JSON array" in prompt:
            return dims_json        # assumption surfacing
        return "I1"                 # H_seed / H_ctx pins / baseline commit → wrong

    client = ScriptedClient(fn)
    task = _task(latent_spec="Use the arithmetic mean over the group.",
                 key_questions=["Which aggregation applies?"])
    rec = intv.compute_cell(task, client, "gpt-5.6-sol", 30260713,
                            k=3, tau=intv.TAU, tau_s=intv.TAU_S,
                            stratum="AMB+")
    assert rec["b2"] is not None
    assert rec["b2"]["baseline_label"] == "I1"
    assert rec["b2"]["oracle_label"] == "I0"
    # Executable resolution metric: baseline stays wrong, oracle → I0.
    assert cd_primary([rec["b2"]["baseline_label"]], "I0") == pytest.approx(1.0)
    assert cd_primary([rec["b2"]["oracle_label"]], "I0") == pytest.approx(0.0)


def test_compute_cell_hb2_skipped_for_amb_neg():
    def fn(role, prompt, seed):
        return '[{"dimension": "d", "values": ["a", "b"]}]' \
            if "JSON array" in prompt else "I1"

    client = ScriptedClient(fn)
    rec = intv.compute_cell(_task(), client, "gpt-5.6-sol", 30260713,
                            k=3, tau=intv.TAU, tau_s=intv.TAU_S, stratum="AMB-")
    assert rec["b2"] is None           # never-clarify oracle only runs on AMB+


def test_hb2_report_aggregation_drop_to_zero():
    # 2 AMB+ items × 2 seeds: baseline I1 (cd=1), oracle I0 (cd=0), I0-hit=1.
    recs = []
    for tid in ("P0", "P1"):
        for s in (30260713, 30270713):
            recs.append({
                "task_id": tid, "model": "m", "seed_base": s, "stratum": "AMB+",
                "H_seed": 0.2, "clarify": {p: False for p in intv.CLARIFY_POLICIES},
                "b2": {"baseline_label": "I1", "oracle_label": "I0"},
            })
    items = report.aggregate_by_item(recs, {})
    hb2 = report.analyze_hb2(items)
    assert hb2["n_AMB_pos"] == 2
    assert hb2["baseline_cd"] == pytest.approx(1.0)
    assert hb2["oracle_cd"] == pytest.approx(0.0)
    assert hb2["delta_cd"] == pytest.approx(1.0)
    assert hb2["i0_hit_rate"] == pytest.approx(1.0)
    assert hb2["n_unresolved"] == 0


def test_hb2_report_honesty_unresolved_reported():
    # An AMB+ item the oracle does NOT resolve (oracle still I1) must be flagged
    # honestly as unresolved — never tuned away.
    recs = [{
        "task_id": "P0", "model": "m", "seed_base": 30260713, "stratum": "AMB+",
        "H_seed": 0.2, "clarify": {p: False for p in intv.CLARIFY_POLICIES},
        "b2": {"baseline_label": "I1", "oracle_label": "I1"},
    }]
    items = report.aggregate_by_item(recs, {})
    hb2 = report.analyze_hb2(items)
    assert hb2["oracle_cd"] == pytest.approx(1.0)
    assert hb2["n_unresolved"] == 1
    assert "P0" in hb2["unresolved_ids"]
    assert hb2["i0_hit_rate"] == pytest.approx(0.0)


# ── H-B1' report aggregation ─────────────────────────────────────────────────

def _hb1_rows():
    rows = []
    # 3 AMB+ danger items: lpp+always+requirements fire; SE/self-consistency don't.
    for i in range(3):
        rows.append({
            "task_id": f"P{i}", "model": "m", "seed_base": 30260713,
            "stratum": "AMB+", "H_seed": 0.2,
            "clarify": {"lpp_gated": True, "always": True,
                        "semantic_entropy_gated": False,
                        "self_consistency_gated": False,
                        "requirements_probing_gated": True},
            "b2": {"baseline_label": "I1", "oracle_label": "I0"},
        })
    # 3 AMB− k0 items: only always fires.
    for i in range(3):
        rows.append({
            "task_id": f"N{i}", "model": "m", "seed_base": 30260713,
            "stratum": "AMB-", "H_seed": 0.1,
            "clarify": {"lpp_gated": False, "always": True,
                        "semantic_entropy_gated": False,
                        "self_consistency_gated": False,
                        "requirements_probing_gated": False},
            "b2": None,
        })
    return rows


def test_hb1_report_net_score_lpp_beats_always():
    items = report.aggregate_by_item(_hb1_rows(), {})
    hb1 = report.analyze_hb1(items)
    lpp = hb1["per_policy"]["lpp_gated"]
    always = hb1["per_policy"]["always"]
    se = hb1["per_policy"]["semantic_entropy_gated"]
    # LPP: appropriate 1.0 on AMB+, over 0.0 on AMB− → net 1.0.
    assert lpp["appropriate"] == pytest.approx(1.0)
    assert lpp["over"] == pytest.approx(0.0)
    assert lpp["net"] == pytest.approx(1.0)
    # Always: appropriate 1.0 but over 1.0 → net 0.0 (loses on specificity).
    assert always["net"] == pytest.approx(0.0)
    # Semantic-entropy: blind in the danger subset → 0 coverage there.
    assert se["danger_coverage"] == pytest.approx(0.0)
    assert lpp["danger_coverage"] == pytest.approx(1.0)
    assert lpp["net"] >= always["net"] and lpp["net"] >= se["net"]


def test_report_render_markdown_smoke():
    recs = _hb1_rows()
    result = report.analyze(recs, {})
    md = report.render_markdown(result, checkpoint="cp.jsonl", n_models=1)
    assert "Intervention closed-loop results" in md
    assert "H-B1'" in md and "H-B2'" in md
    assert "cd_primary" in md


# ── 3. ANTI-LEAKAGE (inviolable) ─────────────────────────────────────────────

_SENTINELS = ["LATENTSPECSENTINEL", "KEYQUESTIONSENTINEL", "GOLDCHECKSENTINEL",
              "IXYZLEAK_TARGET", "IFOILLEAK"]


def _leak_task() -> Task:
    return Task(
        id="LEAK_001", domain="code_spec",
        prompt="Write a function that returns the aggregate of the inputs.",
        latent_spec="LATENTSPECSENTINEL: use the arithmetic mean.",
        interpretations=[
            Interpretation(id="IXYZLEAK_TARGET", is_target=True,
                           gold_check="GOLDCHECKSENTINEL_target"),
            Interpretation(id="IFOILLEAK", is_target=False,
                           gold_check="GOLDCHECKSENTINEL_foil"),
        ],
        ambiguity_level=1,
        key_questions=["KEYQUESTIONSENTINEL: which convention applies?"],
        regime="H1_external",
    )


def test_anti_leakage_only_oracle_carries_gold():
    dims_json = '[{"dimension": "rounding rule", "values": ["up", "down"]}]'

    def fn(role, prompt, seed):
        if intv.ORACLE_PREFIX in prompt:
            return "I0"
        if "JSON array" in prompt:
            return dims_json
        return "I1"

    client = ScriptedClient(fn)
    task = _leak_task()
    intv.compute_cell(task, client, "gpt-4o-mini", 30260713,
                      k=3, tau=intv.TAU, tau_s=intv.TAU_S, stratum="AMB+")

    oracle_prompts = [p for p in client.recorded_prompts
                      if intv.ORACLE_PREFIX in p]
    other_prompts = [p for p in client.recorded_prompts
                     if intv.ORACLE_PREFIX not in p]

    # Exactly one oracle re-ask; it DOES carry the gold convention (latent_spec +
    # the deleted axis) — the allowed evaluation-time controlled injection.
    assert len(oracle_prompts) == 1
    assert "LATENTSPECSENTINEL" in oracle_prompts[0]
    assert "KEYQUESTIONSENTINEL" in oracle_prompts[0]

    # EVERY other prompt (H_seed, surfacing, H_ctx pins, baseline commit) is
    # gold-free.
    for p in other_prompts:
        for s in _SENTINELS:
            assert s not in p, f"LEAK: sentinel {s!r} in non-oracle prompt:\n{p}"
    # The gold_check / interpretation-id sentinels never appear ANYWHERE.
    for p in client.recorded_prompts:
        assert "GOLDCHECKSENTINEL" not in p
        assert "IXYZLEAK_TARGET" not in p and "IFOILLEAK" not in p


def test_oracle_clarification_derived_from_benchmark_gold():
    task = _leak_task()
    text = intv.oracle_clarification_text(task)
    assert text.startswith(intv.ORACLE_PREFIX)
    assert "LATENTSPECSENTINEL" in text          # gold convention (latent_spec)
    assert "KEYQUESTIONSENTINEL" in text          # deleted axis (key_questions)


# ── 4. Driver refuses confirmatory / foreign checkpoints + caches ────────────

def test_path_guard_rejects_confirmatory_checkpoint():
    with pytest.raises(ValueError):
        intv._validate_output_paths(
            ".run_partitions/cp_lps_confirm.jsonl", intv.CACHE_DIR)


def test_path_guard_rejects_confirmatory_shard_checkpoint():
    with pytest.raises(ValueError):
        intv._validate_output_paths(
            ".run_partitions/cp_lps_confirm__gpt-5_6-sol.jsonl", intv.CACHE_DIR)


def test_path_guard_rejects_confirmatory_cache(tmp_path):
    cp = str(tmp_path / "cp_lps_intervention.jsonl")
    with pytest.raises(ValueError):
        intv._validate_output_paths(cp, ".llm_cache_lps_confirm")


def test_path_guard_rejects_pilot_artifacts():
    with pytest.raises(ValueError):
        intv._validate_output_paths(
            ".run_partitions/cp_lps_pilot.jsonl", intv.CACHE_DIR)


def test_path_guard_accepts_own_paths(tmp_path):
    # Its OWN namespaced checkpoint+cache pass the guard.
    intv._validate_output_paths(intv.CHECKPOINT, intv.CACHE_DIR)
    intv._validate_output_paths(intv.shard_checkpoint("gpt-5.6-sol"),
                                intv.shard_cache("gpt-5.6-sol"))
    intv._validate_output_paths(str(tmp_path / "cp_lps_intervention.jsonl"),
                                str(tmp_path / ".llm_cache_lps_intv"),
                                allowed_roots=[str(tmp_path)])


def test_run_refuses_confirmatory_checkpoint(tmp_path):
    def fn(role, prompt, seed):
        return "I1"
    client = ScriptedClient(fn)
    with pytest.raises(ValueError):
        intv.run([_task("A")], {}, models=["gpt-5.6-sol"], seed_bases=[30260713],
                 checkpoint_path=".run_partitions/cp_lps_confirm.jsonl",
                 cache_dir=str(tmp_path / ".llm_cache_lps_intv"), k=3,
                 _client_override=client)


def test_shard_paths_distinct_and_namespaced():
    a = intv.shard_checkpoint("gpt-5.6-sol")
    b = intv.shard_checkpoint("gemini-3.1-pro")
    assert a != b
    assert a == ".run_partitions/cp_lps_intervention__gpt-5_6-sol.jsonl"
    assert intv.shard_cache("gpt-5.6-sol") == ".llm_cache_lps_intv__gpt-5_6-sol"


# ── 5. Dry-run / enumeration / fingerprint / resume ──────────────────────────

def test_dry_run_default_pilot_grid():
    import registered_run as rr
    from common.config import load_config
    tasks = rr.load_tasks()
    assert len(tasks) == 54
    res = intv.run(tasks, load_config(), dry_run=True)
    assert res["status"] == "dry_run"
    assert len(intv.DEFAULT_MODELS) == 1
    assert len(intv.DEFAULT_SEED_BASES) == 3
    assert res["total"] == 54 * 1 * 3        # 162 pilot jobs


def test_enumerate_jobs_shapes():
    jobs = intv.enumerate_jobs([_task("A"), _task("B")], ["m1", "m2"], [10, 20])
    assert len(jobs) == 8
    keys = {(j["task_id"], j["model"], j["seed_base"]) for j in jobs}
    assert len(keys) == 8


def test_fingerprint_includes_intervention_version_models_seeds():
    fp = intv.run_fingerprint(models=["b", "a"], seed_bases=[3, 1, 2],
                              k=5, tau=0.0, tau_s=0.5)
    assert fp["intervention_version"] == intv.INTERVENTION_VERSION
    assert fp["method_version"] == lps.METHOD_VERSION
    assert fp["models"] == ["a", "b"]
    assert fp["seed_bases"] == [1, 2, 3]


def test_scripted_run_writes_records_and_resumes(tmp_path):
    dims_json = '[{"dimension": "d", "values": ["a", "b"]}]'

    def fn(role, prompt, seed):
        if intv.ORACLE_PREFIX in prompt:
            return "I0"
        if "JSON array" in prompt:
            return dims_json
        return "I1"

    client = ScriptedClient(fn)
    cp = str(tmp_path / "cp_lps_intervention.jsonl")
    cache = str(tmp_path / ".llm_cache_lps_intv")
    tasks = [_task("A", key_questions=["axis?"]), _task("B")]

    r1 = intv.run(tasks, {}, models=["gpt-5.6-sol"], seed_bases=[30260713, 30270713],
                  checkpoint_path=cp, cache_dir=cache, k=3, _client_override=client,
                  allowed_roots=[str(tmp_path)])
    assert r1["status"] == "ok"
    assert r1["completed"] == 2 * 1 * 2
    recs = [x for x in r1["results"] if not x.get("_header")]
    assert len(recs) == 4
    for rec in recs:
        assert "clarify" in rec
        assert set(rec["clarify"]) == set(intv.CLARIFY_POLICIES)
        assert rec["_fingerprint"]["intervention_version"] == \
            intv.INTERVENTION_VERSION

    # Resume: a second identical run recomputes nothing.
    r2 = intv.run(tasks, {}, models=["gpt-5.6-sol"], seed_bases=[30260713, 30270713],
                  checkpoint_path=cp, cache_dir=cache, k=3, _client_override=client,
                  allowed_roots=[str(tmp_path)])
    assert r2["completed"] == 0 and r2["skipped"] == 4


def test_resume_fingerprint_mismatch_raises(tmp_path):
    def fn(role, prompt, seed):
        return "I1"
    client = ScriptedClient(fn)
    cp = str(tmp_path / "cp_lps_intervention.jsonl")
    cache = str(tmp_path / ".llm_cache_lps_intv")
    intv.run([_task("A")], {}, models=["gpt-5.6-sol"], seed_bases=[30260713],
             checkpoint_path=cp, cache_dir=cache, k=3, _client_override=client,
             allowed_roots=[str(tmp_path)])
    with pytest.raises(RuntimeError):
        intv.run([_task("A")], {}, models=["gpt-5.6-sol"], seed_bases=[99999999],
                 checkpoint_path=cp, cache_dir=cache, k=3, _client_override=client,
                 allowed_roots=[str(tmp_path)])


# ── [MAJOR 1] Path isolation is NOT bypassable by nested foreign directories ──

def test_path_guard_rejects_nested_confirmatory_dir_bypass():
    # The auditor's exact bypass: a valid intervention BASENAME nested inside a
    # confirmatory-namespace DIRECTORY must be REJECTED (full-path scan + exact
    # parent-root requirement), not accepted.
    with pytest.raises(ValueError):
        intv._validate_output_paths(
            ".run_partitions/cp_lps_confirm_archive/cp_lps_intervention.jsonl",
            intv.CACHE_DIR)


def test_path_guard_rejects_nested_foreign_cache_bypass():
    # The auditor's exact cache bypass: a valid intervention cache basename nested
    # inside a registered_run cache DIRECTORY must be REJECTED.
    with pytest.raises(ValueError):
        intv._validate_output_paths(
            intv.CHECKPOINT, ".llm_cache_registered_run/.llm_cache_lps_intv")


def test_path_guard_rejects_deep_nested_pilot_dir():
    with pytest.raises(ValueError):
        intv._validate_output_paths(
            ".run_partitions/lps_pilot/cp_lps_intervention__m.jsonl", intv.CACHE_DIR)


def test_path_guard_accepts_legit_after_hardening(tmp_path):
    # A genuinely isolated intervention path is still ACCEPTED after the hardening.
    intv._validate_output_paths(intv.CHECKPOINT, intv.CACHE_DIR)
    intv._validate_output_paths(intv.shard_checkpoint("gpt-5.6-sol"),
                                intv.shard_cache("gpt-5.6-sol"))
    # An out-of-repo scratch dir is accepted ONLY when injected EXPLICITLY.
    intv._validate_output_paths(str(tmp_path / "cp_lps_intervention.jsonl"),
                                str(tmp_path / ".llm_cache_lps_intv"),
                                allowed_roots=[str(tmp_path)])


# ── [MAJOR 2] Report/merge integrity — fail loud, never silently concatenate ──

def _fp_intv(**over):
    fp = {"intervention_version": intv.INTERVENTION_VERSION,
          "method_version": lps.METHOD_VERSION, "k": 5, "tau": 0.0, "tau_s": 0.5,
          "seed_bases": [100, 200], "models": ["m"]}
    fp.update(over)
    return fp


def _cell(tid, model, seed, fp, **over):
    rec = {"task_id": tid, "model": model, "seed_base": seed, "stratum": "AMB+",
           "clarify": {p: False for p in intv.CLARIFY_POLICIES}, "b2": None,
           "_fingerprint": fp}
    rec.update(over)
    return rec


def _write_ckpt(path, fp, records, roster=None):
    if roster is None:
        roster = {
            "models": sorted({r["model"] for r in records}),
            "seed_bases": sorted({r["seed_base"] for r in records}),
            "items": sorted({r["task_id"] for r in records}),
        }
    header = {"_header": True, "_fingerprint": fp, "_roster": roster}
    lines = [json.dumps(header)]
    lines.extend(json.dumps(r) for r in records)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def test_merge_complete_grid_ok(tmp_path):
    fp = _fp_intv(seed_bases=[100, 200])
    recs = [_cell(t, "m", s, fp) for t in ("A", "B") for s in (100, 200)]
    p = _write_ckpt(tmp_path / "cp_lps_intervention__m.jsonl", fp, recs)
    merged = merge.merge_records([p])
    assert len(merged["records"]) == 4
    assert merged["n_conflict"] == 0


def test_merge_model_diff_same_shared_fp_ok(tmp_path):
    # Multi-model grid: each shard stamps the SAME full roster (models a AND b);
    # union of observed cells exactly fills the declared grid.
    fp_a = _fp_intv(models=["a"], seed_bases=[100])
    fp_b = _fp_intv(models=["b"], seed_bases=[100])
    roster = {"models": ["a", "b"], "seed_bases": [100], "items": ["A", "B"]}
    p1 = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp_a,
                     [_cell("A", "a", 100, fp_a), _cell("B", "a", 100, fp_a)],
                     roster=roster)
    p2 = _write_ckpt(tmp_path / "cp_lps_intervention__b.jsonl", fp_b,
                     [_cell("A", "b", 100, fp_b), _cell("B", "b", 100, fp_b)],
                     roster=roster)
    merged = merge.merge_records([p1, p2])
    assert len(merged["records"]) == 4          # 2 items × 2 models × 1 seed
    assert merged["n_conflict"] == 0


def test_merge_conflicting_duplicate_raises(tmp_path):
    # (a) same cell key, DIFFERENT payload → abort (never keep-first silently).
    fp = _fp_intv(seed_bases=[100])
    r1 = _cell("A", "m", 100, fp, H_seed=0.2)
    r2 = _cell("A", "m", 100, fp, H_seed=0.9)
    p = _write_ckpt(tmp_path / "cp_lps_intervention__m.jsonl", fp, [r1, r2])
    with pytest.raises(merge.MergeError):
        merge.merge_records([p])


def test_merge_identical_duplicate_dedups_not_conflict(tmp_path):
    fp = _fp_intv(seed_bases=[100])
    r = _cell("A", "m", 100, fp, H_seed=0.2)
    p1 = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp, [r])
    p2 = _write_ckpt(tmp_path / "cp_lps_intervention__a2.jsonl", fp, [r])
    merged = merge.merge_records([p1, p2])
    assert len(merged["records"]) == 1
    assert merged["n_dup"] == 1 and merged["n_conflict"] == 0


def test_merge_missing_cell_raises(tmp_path):
    # (b) interrupted grid: (B, m, 200) missing → abort (not silently averaged).
    fp = _fp_intv(seed_bases=[100, 200])
    recs = [_cell("A", "m", 100, fp), _cell("A", "m", 200, fp),
            _cell("B", "m", 100, fp)]
    p = _write_ckpt(tmp_path / "cp_lps_intervention__m.jsonl", fp, recs)
    with pytest.raises(merge.MergeError):
        merge.merge_records([p])


def test_merge_version_mismatch_raises(tmp_path):
    # (c) incompatible intervention_version across shards → abort.
    fp1 = _fp_intv(models=["a"], seed_bases=[100])
    fp2 = _fp_intv(models=["b"], seed_bases=[100],
                   intervention_version="lps-intv-OTHER")
    p1 = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp1,
                     [_cell("A", "a", 100, fp1)])
    p2 = _write_ckpt(tmp_path / "cp_lps_intervention__b.jsonl", fp2,
                     [_cell("A", "b", 100, fp2)])
    with pytest.raises(merge.MergeError):
        merge.merge_records([p1, p2])


def test_merge_method_version_mismatch_raises(tmp_path):
    fp1 = _fp_intv(models=["a"], seed_bases=[100])
    fp2 = _fp_intv(models=["b"], seed_bases=[100], method_version="lps-OTHER")
    p1 = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp1,
                     [_cell("A", "a", 100, fp1)])
    p2 = _write_ckpt(tmp_path / "cp_lps_intervention__b.jsonl", fp2,
                     [_cell("A", "b", 100, fp2)])
    with pytest.raises(merge.MergeError):
        merge.merge_records([p1, p2])


def test_merge_malformed_record_raises(tmp_path):
    # (d) a corrupt line raises rather than being silently dropped.
    fp = _fp_intv(seed_bases=[100])
    p = tmp_path / "cp_lps_intervention__m.jsonl"
    p.write_text(json.dumps({"_header": True, "_fingerprint": fp})
                 + "\nNOT VALID JSON\n", encoding="utf-8")
    with pytest.raises(merge.MergeError):
        merge.merge_records([str(p)])


def test_merge_unstamped_record_raises(tmp_path):
    # A record with no _fingerprint cannot be version-verified → abort.
    fp = _fp_intv(seed_bases=[100])
    rec = {"task_id": "A", "model": "m", "seed_base": 100}   # no _fingerprint
    p = tmp_path / "cp_lps_intervention__m.jsonl"
    p.write_text(json.dumps({"_header": True, "_fingerprint": fp})
                 + "\n" + json.dumps(rec) + "\n", encoding="utf-8")
    with pytest.raises(merge.MergeError):
        merge.merge_records([str(p)])


def test_report_main_aborts_on_incomplete_grid(tmp_path, capsys):
    # End-to-end: the report CLI refuses to emit metrics from an interrupted grid.
    # (Inject tmp_path as an allowed root so the grid check — not the path guard —
    # is what aborts.)
    fp = _fp_intv(seed_bases=[100, 200])
    recs = [_cell("A", "m", 100, fp), _cell("A", "m", 200, fp),
            _cell("B", "m", 100, fp)]
    cp = _write_ckpt(tmp_path / "cp_lps_intervention.jsonl", fp, recs,
                     roster={"models": ["m"], "seed_bases": [100, 200],
                             "items": ["A", "B"]})
    with pytest.raises(SystemExit):
        report.main(["--checkpoint", cp, "--out", str(tmp_path / "out.md")],
                    allowed_roots=[str(tmp_path)])


# ── [MINOR 3] H-B2' INTEGRATION test through the REAL frozen labeler ─────────

def test_hb2_real_labeler_resolves_to_I0(monkeypatch):
    # Restore the REAL executable labeler (undo the autouse identity stub) and run
    # a domain-valid oracle answer through it: a gold-I0-convention answer must
    # land on I0 → cd_primary → 0, while a non-I0 (I1) answer gives non-zero
    # cd_primary. Deterministic: concrete benchmark Task + gold answer strings,
    # NO live model calls.
    from harness.label import label_run as _real_label
    monkeypatch.setattr(lps, "label_run", _real_label)

    import registered_run as rr
    from bench.policy_qa import get_checkers_and_candidates
    tasks = rr.load_tasks()
    task = next(t for t in tasks
                if t.domain == "policy_qa"
                and lgold.gold_ambiguity(t)["stratum"] == lgold.STRATUM_AMB_POS)
    _ch, cand, _foils = get_checkers_and_candidates(task.domain, task)

    oracle_answer = json.dumps({"amount": cand["I0"]["amount"]})
    baseline_answer = json.dumps({"amount": cand["I1"]["amount"]})

    oracle_label = lps._label_answer(oracle_answer, task, model_id="m", seed=0)
    baseline_label = lps._label_answer(baseline_answer, task, model_id="m", seed=0)

    # REAL labeler: the gold-I0-convention answer is labeled I0 (not merely echoed).
    assert oracle_label == "I0"
    assert baseline_label != "I0"
    # Executable resolution metric moves as pre-committed.
    assert cd_primary([oracle_label] * 3, "I0") == pytest.approx(0.0)
    assert cd_primary([baseline_label] * 3, "I0") > 0.0


def test_hb2_compute_cell_end_to_end_real_labeler(monkeypatch):
    # compute_cell wired to the REAL labeler on a real AMB+ policy_qa item: a
    # scripted client emits the gold I0 amount for the oracle re-ask and a wrong
    # (I1) amount otherwise → b2 baseline is non-I0, oracle is I0.
    from harness.label import label_run as _real_label
    monkeypatch.setattr(lps, "label_run", _real_label)

    import registered_run as rr
    from bench.policy_qa import get_checkers_and_candidates
    tasks = rr.load_tasks()
    task = next(t for t in tasks
                if t.domain == "policy_qa"
                and lgold.gold_ambiguity(t)["stratum"] == lgold.STRATUM_AMB_POS)
    _ch, cand, _foils = get_checkers_and_candidates(task.domain, task)
    i0_amt = cand["I0"]["amount"]
    i1_amt = cand["I1"]["amount"]

    def fn(role, prompt, seed):
        if intv.ORACLE_PREFIX in prompt:
            return json.dumps({"amount": i0_amt})     # oracle → true convention
        if "JSON array" in prompt:
            return '[{"dimension": "threshold", "values": ["a", "b"]}]'
        return json.dumps({"amount": i1_amt})          # else → a wrong interp

    client = ScriptedClient(fn)
    rec = intv.compute_cell(task, client, "gpt-5.6-sol", 30260713,
                            k=3, tau=intv.TAU, tau_s=intv.TAU_S,
                            stratum=lgold.STRATUM_AMB_POS)
    assert rec["b2"] is not None
    assert rec["b2"]["oracle_label"] == "I0"
    assert rec["b2"]["baseline_label"] != "I0"
    assert cd_primary([rec["b2"]["oracle_label"]], "I0") == pytest.approx(0.0)
    assert cd_primary([rec["b2"]["baseline_label"]], "I0") > 0.0


# ── Re-audit round 3: temp-escape / version-equality / declared-roster /
#    malformed-keys / merge-report I/O isolation ─────────────────────────────

def test_path_guard_rejects_system_temp_in_production():
    # MAJOR-1 (re-audit): a path under the system temp dir must be REJECTED in
    # production (no allowed_roots injected) — the guard never hard-allows %TEMP%.
    import tempfile
    tmp = Path(tempfile.gettempdir())
    cp = str(tmp / "audit-outside" / "cp_lps_intervention.jsonl")
    cache = str(tmp / "audit-outside" / ".llm_cache_lps_intv")
    with pytest.raises(ValueError):
        intv._validate_output_paths(cp, cache)                      # production mode
    # …but accepted when the caller injects that exact root EXPLICITLY.
    intv._validate_output_paths(cp, cache, allowed_roots=[str(tmp / "audit-outside")])


def test_run_rejects_system_temp_without_injected_root(tmp_path):
    # The driver run() must also refuse an out-of-repo scratch dir unless the
    # caller injects it — proving the plumbing is not bypassable via run().
    def fn(role, prompt, seed):
        return "I1"
    client = ScriptedClient(fn)
    import tempfile
    tmp = Path(tempfile.gettempdir()) / "audit-outside-run"
    with pytest.raises(ValueError):
        intv.run([_task("A")], {}, models=["m"], seed_bases=[1],
                 checkpoint_path=str(tmp / "cp_lps_intervention.jsonl"),
                 cache_dir=str(tmp / ".llm_cache_lps_intv"), k=3,
                 _client_override=client)


def test_merge_rejects_wrong_but_uniform_version(tmp_path):
    # MAJOR-2 (re-audit): a self-consistent checkpoint stamped a WRONG version
    # (uniform across records, so cross-record agreement passes) must still RAISE
    # because it does not EQUAL the current module constants.
    fp = _fp_intv(seed_bases=[100], intervention_version="WRONG",
                  method_version="WRONG")
    p = _write_ckpt(tmp_path / "cp_lps_intervention__m.jsonl", fp,
                    [_cell("A", "m", 100, fp)])
    with pytest.raises(merge.MergeError):
        merge.merge_records([p])


def test_merge_rejects_wrong_intervention_version_only(tmp_path):
    fp = _fp_intv(seed_bases=[100], intervention_version="WRONG")
    p = _write_ckpt(tmp_path / "cp_lps_intervention__m.jsonl", fp,
                    [_cell("A", "m", 100, fp)])
    with pytest.raises(merge.MergeError):
        merge.merge_records([p])


def test_merge_declared_roster_missing_model_raises(tmp_path):
    # MAJOR-3 (re-audit): the fingerprint/header DECLARES models ["a","b"] but only
    # "a" is present → completeness measured against the DECLARED roster RAISES
    # (must not overstate completeness from the observed universe).
    fp = _fp_intv(models=["a"], seed_bases=[100])
    roster = {"models": ["a", "b"], "seed_bases": [100], "items": ["A"]}
    p = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp,
                    [_cell("A", "a", 100, fp)], roster=roster)
    with pytest.raises(merge.MergeError):
        merge.merge_records([p])


def test_merge_declared_roster_missing_item_raises(tmp_path):
    fp = _fp_intv(models=["a"], seed_bases=[100])
    roster = {"models": ["a"], "seed_bases": [100], "items": ["A", "B"]}
    p = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp,
                    [_cell("A", "a", 100, fp)], roster=roster)
    with pytest.raises(merge.MergeError):
        merge.merge_records([p])


def test_merge_no_roster_raises(tmp_path):
    # A checkpoint with NO declared roster header cannot be completeness-verified
    # against the intended grid → abort (never fall back to observed universe).
    fp = _fp_intv(seed_bases=[100])
    p = tmp_path / "cp_lps_intervention__m.jsonl"
    p.write_text(json.dumps({"_header": True, "_fingerprint": fp})
                 + "\n" + json.dumps(_cell("A", "m", 100, fp)) + "\n",
                 encoding="utf-8")
    with pytest.raises(merge.MergeError):
        merge.merge_records([str(p)])


def test_merge_declared_roster_complete_ok(tmp_path):
    # Sanity: when every declared cell IS present, merge succeeds and echoes the
    # declared roster.
    fp = _fp_intv(models=["a", "b"], seed_bases=[100])
    roster = {"models": ["a", "b"], "seed_bases": [100], "items": ["A"]}
    p1 = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp,
                     [_cell("A", "a", 100, fp)], roster=roster)
    p2 = _write_ckpt(tmp_path / "cp_lps_intervention__b.jsonl", fp,
                     [_cell("A", "b", 100, fp)], roster=roster)
    merged = merge.merge_records([p1, p2])
    assert len(merged["records"]) == 2
    assert merged["roster"] == {"models": ["a", "b"], "seed_bases": [100],
                                "items": ["A"]}


@pytest.mark.parametrize("bad", [
    {"task_id": None, "model": "m", "seed_base": 100},
    {"task_id": "A", "model": None, "seed_base": 100},
    {"task_id": "A", "model": "m", "seed_base": None},
    {"model": "m", "seed_base": 100},                       # task_id absent
    {"task_id": "A", "seed_base": 100},                     # model absent
    {"task_id": "A", "model": "m"},                         # seed_base absent
    {"task_id": "A", "model": "m", "seed_base": "100"},     # seed_base wrong type
    {"task_id": "A", "model": "m", "seed_base": True},      # bool is not an int
    {"task_id": "", "model": "m", "seed_base": 100},        # empty task_id
])
def test_merge_malformed_identity_keys_raise(tmp_path, bad):
    # MAJOR-4 (re-audit): a record with a missing / None / wrong-typed identity key
    # must RAISE (never enter the cell universe and silently satisfy completeness).
    fp = _fp_intv(seed_bases=[100])
    rec = dict(bad)
    rec["_fingerprint"] = fp
    p = tmp_path / "cp_lps_intervention__m.jsonl"
    p.write_text(json.dumps({"_header": True, "_fingerprint": fp,
                             "_roster": {"models": ["m"], "seed_bases": [100],
                                         "items": ["A"]}})
                 + "\n" + json.dumps(rec) + "\n", encoding="utf-8")
    with pytest.raises(merge.MergeError):
        merge.merge_records([str(p)])


def _confirmatory_ckpt(tmp_path):
    """Write a plausible CONFIRMATORY checkpoint (protected namespace) on disk."""
    d = tmp_path / ".run_partitions"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "cp_lps_confirm.jsonl"
    p.write_text(json.dumps({"_header": True}) + "\n", encoding="utf-8")
    return str(p)


def test_merge_main_rejects_out_into_confirmatory(tmp_path):
    # MAJOR-5 (re-audit): merge --out into a confirmatory path is REJECTED.
    fp = _fp_intv(seed_bases=[100])
    shard = _write_ckpt(tmp_path / "cp_lps_intervention__m.jsonl", fp,
                        [_cell("A", "m", 100, fp)])
    bad_out = str(tmp_path / "cp_lps_confirm.jsonl")
    with pytest.raises(SystemExit):
        merge.main(["--shards", shard, "--out", bad_out],
                   allowed_roots=[str(tmp_path)])


def test_merge_main_rejects_confirmatory_input_shard(tmp_path):
    # merge --shards pointing at a confirmatory checkpoint is REJECTED.
    bad_shard = _confirmatory_ckpt(tmp_path)
    good_out = str(tmp_path / "cp_lps_intervention_merged.jsonl")
    with pytest.raises(SystemExit):
        merge.main(["--shards", bad_shard, "--out", good_out],
                   allowed_roots=[str(tmp_path)])


def test_report_main_rejects_confirmatory_checkpoint_input(tmp_path):
    # MAJOR-5 (re-audit): report --checkpoint reading a confirmatory checkpoint is
    # REJECTED before any pooling.
    bad_cp = _confirmatory_ckpt(tmp_path)
    with pytest.raises(SystemExit):
        report.main(["--checkpoint", bad_cp, "--out", str(tmp_path / "out.md")],
                    allowed_roots=[str(tmp_path)])


def test_report_main_rejects_out_into_confirmatory(tmp_path):
    fp = _fp_intv(seed_bases=[100])
    cp = _write_ckpt(tmp_path / "cp_lps_intervention.jsonl", fp,
                     [_cell("A", "m", 100, fp)])
    bad_out = str(tmp_path / ".run_partitions" / "cp_lps_confirm.jsonl")
    (tmp_path / ".run_partitions").mkdir(parents=True, exist_ok=True)
    with pytest.raises(SystemExit):
        report.main(["--checkpoint", cp, "--out", bad_out],
                    allowed_roots=[str(tmp_path)])


# ── Re-audit round 4: frozen-report allowlist / strict identical roster /
#    merged round-trip / full pipeline self-consistency ────────────────────────

def _repo(*parts):
    return str(_REPO_ROOT.joinpath(*parts))


def test_report_out_rejects_frozen_prereg_path():
    # BLOCKER (re-audit): a report must NOT be writable over the FROZEN prereg.
    with pytest.raises(ValueError):
        intv.validate_merge_io_path(
            _repo("paper", "preregistration",
                  "2026-07-23-study2-prereg-FROZEN.md"),
            label="--out", is_checkpoint=False)


def test_report_out_rejects_any_paper_path():
    with pytest.raises(ValueError):
        intv.validate_merge_io_path(
            _repo("paper", "plans", "some-plan.md"),
            label="--out", is_checkpoint=False)


def test_report_out_rejects_confirmatory_phase_report():
    with pytest.raises(ValueError):
        intv.validate_merge_io_path(
            _repo("files", "phase6_confirmatory_report.md"),
            label="--out", is_checkpoint=False)


def test_report_out_rejects_stage_report():
    with pytest.raises(ValueError):
        intv.validate_merge_io_path(
            _repo("files", "study2_stage3_results.md"),
            label="--out", is_checkpoint=False)


def test_report_out_rejects_non_md_extension():
    with pytest.raises(ValueError):
        intv.validate_merge_io_path(
            _repo("files", "study2_intervention_results.txt"),
            label="--out", is_checkpoint=False)


def test_report_out_rejects_files_wrong_prefix():
    with pytest.raises(ValueError):
        intv.validate_merge_io_path(
            _repo("files", "some_other_report.md"),
            label="--out", is_checkpoint=False)


def test_report_out_accepts_intervention_namespace():
    # The one legit destination IS accepted.
    intv.validate_merge_io_path(
        _repo("files", "study2_intervention_results.md"),
        label="--out", is_checkpoint=False)


def test_report_main_rejects_write_to_frozen(tmp_path):
    # End-to-end: the report CLI refuses to overwrite the FROZEN prereg even with
    # an injected test root (the paper/ + FROZEN guard is unconditional).
    fp = _fp_intv(seed_bases=[100])
    cp = _write_ckpt(tmp_path / "cp_lps_intervention.jsonl", fp,
                     [_cell("A", "m", 100, fp)])
    frozen = _repo("paper", "preregistration",
                   "2026-07-23-study2-prereg-FROZEN.md")
    with pytest.raises(SystemExit):
        report.main(["--checkpoint", cp, "--out", frozen],
                    allowed_roots=[str(tmp_path)])


def test_report_main_rejects_write_to_confirmatory_report(tmp_path):
    fp = _fp_intv(seed_bases=[100])
    cp = _write_ckpt(tmp_path / "cp_lps_intervention.jsonl", fp,
                     [_cell("A", "m", 100, fp)])
    with pytest.raises(SystemExit):
        report.main(["--checkpoint", cp,
                     "--out", _repo("files", "phase6_confirmatory_report.md")],
                    allowed_roots=[str(tmp_path)])


# ── [MAJOR 2] Strict identical-roster enforcement across shards ──────────────

def test_merge_shard_missing_roster_among_others_raises(tmp_path):
    # A shard with NO _roster is rejected even though ANOTHER shard supplies one.
    fp_a = _fp_intv(models=["a"], seed_bases=[100])
    fp_b = _fp_intv(models=["b"], seed_bases=[100])
    roster = {"models": ["a", "b"], "seed_bases": [100], "items": ["A"]}
    good = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp_a,
                       [_cell("A", "a", 100, fp_a)], roster=roster)
    bad = tmp_path / "cp_lps_intervention__b.jsonl"   # header WITHOUT _roster
    bad.write_text(json.dumps({"_header": True, "_fingerprint": fp_b})
                   + "\n" + json.dumps(_cell("A", "b", 100, fp_b)) + "\n",
                   encoding="utf-8")
    with pytest.raises(merge.MergeError):
        merge.merge_records([good, str(bad)])


def test_merge_two_shards_different_rosters_raise(tmp_path):
    # Differing declared rosters ABORT (never union-away the difference).
    fp = _fp_intv(models=["a"], seed_bases=[100])
    r1 = {"models": ["a"], "seed_bases": [100], "items": ["A"]}
    r2 = {"models": ["a"], "seed_bases": [100], "items": ["A", "B"]}
    p1 = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp,
                     [_cell("A", "a", 100, fp)], roster=r1)
    p2 = _write_ckpt(tmp_path / "cp_lps_intervention__a2.jsonl", fp,
                     [_cell("A", "a", 100, fp)], roster=r2)
    with pytest.raises(merge.MergeError):
        merge.merge_records([p1, p2])


def test_merge_undeclared_cell_raises(tmp_path):
    # An observed cell for a model NOT in the declared roster ABORTS.
    fp = _fp_intv(models=["a"], seed_bases=[100])
    roster = {"models": ["a"], "seed_bases": [100], "items": ["A"]}
    recs = [_cell("A", "a", 100, fp), _cell("A", "b", 100, fp)]  # b undeclared
    p = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp, recs,
                    roster=roster)
    with pytest.raises(merge.MergeError):
        merge.merge_records([p])


def test_merge_undeclared_item_raises(tmp_path):
    fp = _fp_intv(models=["a"], seed_bases=[100])
    roster = {"models": ["a"], "seed_bases": [100], "items": ["A"]}
    recs = [_cell("A", "a", 100, fp), _cell("Z", "a", 100, fp)]  # Z undeclared
    p = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp, recs,
                    roster=roster)
    with pytest.raises(merge.MergeError):
        merge.merge_records([p])


# ── [MAJOR 3] Merged output round-trips through its own strict loader ────────

def test_write_merged_requires_roster_and_fingerprint(tmp_path):
    out = str(tmp_path / "cp_lps_intervention_merged.jsonl")
    with pytest.raises(merge.MergeError):
        merge.write_merged([], out, fingerprint={"intervention_version": "x"},
                           roster=None)
    with pytest.raises(merge.MergeError):
        merge.write_merged([], out, fingerprint=None,
                           roster={"models": ["m"], "seed_bases": [100],
                                   "items": ["A"]})


def test_write_merged_roundtrips_through_strict_loader(tmp_path):
    fp = _fp_intv(models=["m"], seed_bases=[100])
    roster = {"models": ["m"], "seed_bases": [100], "items": ["A", "B"]}
    recs = [_cell("A", "m", 100, fp), _cell("B", "m", 100, fp)]
    shard = _write_ckpt(tmp_path / "cp_lps_intervention__m.jsonl", fp, recs,
                        roster=roster)
    merged = merge.merge_records([shard])

    out = tmp_path / "cp_lps_intervention_merged.jsonl"
    merge.write_merged(merged["records"], str(out),
                       fingerprint=merged["shared_fingerprint"],
                       roster=merged["roster"])

    # The merged checkpoint re-validates through the SAME strict loader: header
    # carries _roster + _fingerprint, versions equal the constants, and the
    # observed cells EXACTLY fill the declared roster.
    reloaded = merge.merge_records([str(out)])
    assert len(reloaded["records"]) == 2
    assert reloaded["roster"] == {"models": ["m"], "seed_bases": [100],
                                  "items": ["A", "B"]}
    header = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert header["_roster"] == roster
    assert header["_fingerprint"]["intervention_version"] == \
        intv.INTERVENTION_VERSION
    assert header["_fingerprint"]["method_version"] == lps.METHOD_VERSION


def test_pipeline_merge_then_report_end_to_end(tmp_path):
    # CONVERGENCE: write a valid multi-cell checkpoint (stamped roster) → merge it
    # → report from the MERGED output, all through strict validation. Proves the
    # whole driver→merge→report pipeline is self-consistent.
    rows = _hb1_rows()
    fp = _fp_intv(models=["m"], seed_bases=[30260713])
    for r in rows:
        r["_fingerprint"] = fp
    roster = {"models": ["m"], "seed_bases": [30260713],
              "items": sorted(r["task_id"] for r in rows)}
    shard = _write_ckpt(tmp_path / "cp_lps_intervention__m.jsonl", fp, rows,
                        roster=roster)

    merged_out = str(tmp_path / "cp_lps_intervention_merged.jsonl")
    merge.main(["--shards", shard, "--out", merged_out],
               allowed_roots=[str(tmp_path)])
    assert Path(merged_out).exists()

    report_out = tmp_path / "study2_intervention_results.md"
    report.main(["--checkpoint", merged_out, "--out", str(report_out)],
                allowed_roots=[str(tmp_path)])
    assert report_out.exists()
    text = report_out.read_text(encoding="utf-8")
    assert "H-B1'" in text and "cd_primary" in text


# ── Re-audit round 4 (final): _norm_roster must be STRICT + LOSSLESS ─────────

def test_roster_float_seed_raises(tmp_path):
    # (a) A float seed (100.9) is REJECTED by type validation — never int()-coerced.
    fp = _fp_intv(models=["a"], seed_bases=[100])
    roster = {"models": ["a"], "seed_bases": [100.9], "items": ["A"]}
    p = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp,
                    [_cell("A", "a", 100, fp)], roster=roster)
    with pytest.raises(merge.MergeError):
        merge.merge_records([p])


def test_roster_bool_seed_raises(tmp_path):
    # bool is an int subclass — it must NOT slip through the seed type check.
    fp = _fp_intv(models=["a"], seed_bases=[100])
    roster = {"models": ["a"], "seed_bases": [True], "items": ["A"]}
    p = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp,
                    [_cell("A", "a", 100, fp)], roster=roster)
    with pytest.raises(merge.MergeError):
        merge.merge_records([p])


def test_roster_str_seed_raises(tmp_path):
    fp = _fp_intv(models=["a"], seed_bases=[100])
    roster = {"models": ["a"], "seed_bases": ["100"], "items": ["A"]}
    p = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp,
                    [_cell("A", "a", 100, fp)], roster=roster)
    with pytest.raises(merge.MergeError):
        merge.merge_records([p])


def test_roster_int_vs_float_seed_not_lossily_identical(tmp_path):
    # (b) [100] vs [100.9] must be DIFFERENT — the old int()-coercion made them
    # falsely identical. Now the float shard raises (lossless, fail-loud).
    fp = _fp_intv(models=["a"], seed_bases=[100])
    r_int = {"models": ["a"], "seed_bases": [100], "items": ["A"]}
    r_flt = {"models": ["a"], "seed_bases": [100.9], "items": ["A"]}
    p1 = _write_ckpt(tmp_path / "cp_lps_intervention__a1.jsonl", fp,
                     [_cell("A", "a", 100, fp)], roster=r_int)
    p2 = _write_ckpt(tmp_path / "cp_lps_intervention__a2.jsonl", fp,
                     [_cell("A", "a", 100, fp)], roster=r_flt)
    with pytest.raises(merge.MergeError):
        merge.merge_records([p1, p2])


def test_roster_duplicate_axis_entry_raises(tmp_path):
    # (c) A duplicated axis entry signals a malformed roster — never silently
    # de-duplicated.
    fp = _fp_intv(models=["a"], seed_bases=[100])
    roster = {"models": ["a", "a"], "seed_bases": [100], "items": ["A"]}
    p = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp,
                    [_cell("A", "a", 100, fp)], roster=roster)
    with pytest.raises(merge.MergeError):
        merge.merge_records([p])


def test_roster_duplicate_seed_raises(tmp_path):
    fp = _fp_intv(models=["a"], seed_bases=[100])
    roster = {"models": ["a"], "seed_bases": [100, 100], "items": ["A"]}
    p = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp,
                    [_cell("A", "a", 100, fp)], roster=roster)
    with pytest.raises(merge.MergeError):
        merge.merge_records([p])


def test_roster_non_list_axis_raises(tmp_path):
    fp = _fp_intv(models=["a"], seed_bases=[100])
    roster = {"models": ["a"], "seed_bases": 100, "items": ["A"]}
    p = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp,
                    [_cell("A", "a", 100, fp)], roster=roster)
    with pytest.raises(merge.MergeError):
        merge.merge_records([p])


def test_legit_pilot_roster_validates_and_roundtrips(tmp_path):
    # (d) The real integer-seed pilot roster still validates + round-trips.
    seeds = [30260713, 30270713, 30280713]
    fp = _fp_intv(models=["m"], seed_bases=seeds)
    roster = {"models": ["m"], "seed_bases": seeds, "items": ["A"]}
    recs = [_cell("A", "m", s, fp) for s in seeds]
    shard = _write_ckpt(tmp_path / "cp_lps_intervention__m.jsonl", fp, recs,
                        roster=roster)
    merged = merge.merge_records([shard])
    assert merged["roster"] == {"models": ["m"], "seed_bases": sorted(seeds),
                                "items": ["A"]}

    out = tmp_path / "cp_lps_intervention_merged.jsonl"
    merge.write_merged(merged["records"], str(out),
                       fingerprint=merged["shared_fingerprint"],
                       roster=merged["roster"])
    reloaded = merge.merge_records([str(out)])
    assert reloaded["roster"] == {"models": ["m"], "seed_bases": sorted(seeds),
                                  "items": ["A"]}
    assert len(reloaded["records"]) == 3


# ── Concurrent per-model shards: --roster-models declared-roster override ─────

def test_shard_by_model_roster_models_dryrun_stamps_full_roster(capsys):
    # --shard-by-model --models A --roster-models A B C : enumerate ONLY A's
    # jobs, but the DECLARED roster stamped into the shard header = {A, B, C}.
    intv.main(["--shard-by-model", "--models", "gpt-5.6-sol",
               "--roster-models", "gpt-5.6-sol", "claude-opus-4.8", "gemini-3.1-pro",
               "--seeds", "30260713", "30270713", "30280713", "--dry-run"])
    out = capsys.readouterr().out
    # One processed model × 54 items × 3 seeds = 162 jobs enumerated.
    assert "162 jobs" in out
    assert "54 items × 1 models × 3 seeds" in out
    # Declared roster stamped into every shard is the canonical full set.
    declared = sorted({"gpt-5.6-sol", "claude-opus-4.8", "gemini-3.1-pro"})
    assert f"Declared roster (stamped into every shard): {declared}" in out


def test_roster_models_forwarded_to_run(monkeypatch):
    # In the live shard loop the resolved declared roster (full set) — NOT the
    # single processed --models — is forwarded to run(roster_models=...).
    monkeypatch.setattr(intv.pilot1, "_live_ok", lambda: True)
    monkeypatch.setattr(intv.pilot1, "_proxy_reachable", lambda: True)
    captured: List[Any] = []

    def _stub_run(tasks, cfg, **kw):
        captured.append(kw)
        return {"completed": 0, "skipped": 0, "total": 0,
                "checkpoint": kw.get("checkpoint_path")}

    monkeypatch.setattr(intv, "run", _stub_run)
    intv.main(["--shard-by-model", "--models", "gpt-5.6-sol",
               "--roster-models", "gpt-5.6-sol", "claude-opus-4.8",
               "--seeds", "30260713"])
    assert len(captured) == 1
    kw = captured[0]
    assert kw["models"] == ["gpt-5.6-sol"]                       # processes ONE
    assert kw["roster_models"] == ["claude-opus-4.8", "gpt-5.6-sol"]  # stamps FULL


def test_roster_models_subset_violation_raises():
    # A processed model NOT in the declared roster fails loud.
    with pytest.raises(SystemExit):
        intv.main(["--shard-by-model", "--models", "gpt-5.6-sol",
                   "--roster-models", "claude-opus-4.8", "gemini-3.1-pro",
                   "--seeds", "30260713", "--dry-run"])


def test_no_roster_models_unchanged_behavior(capsys):
    # Backward compat: without --roster-models the declared roster is derived
    # from --models exactly as before.
    intv.main(["--shard-by-model", "--models", "gpt-5.6-sol",
               "--seeds", "30260713", "--dry-run"])
    out = capsys.readouterr().out
    assert "Declared roster (stamped into every shard): ['gpt-5.6-sol']" in out


# ── PER-CELL FAULT TOLERANCE (additive): a hanging/erroring cell → N/A, never a
#    shard crash; N/A cells count for completeness but leak into NO metric ─────

def _ok_fn():
    dims_json = '[{"dimension": "d", "values": ["a", "b"]}]'

    def fn(role, prompt, seed):
        if intv.ORACLE_PREFIX in prompt:
            return "I0"
        if "JSON array" in prompt:
            return dims_json
        return "I1"
    return fn


def test_run_records_na_on_compute_cell_exception_and_continues(tmp_path, monkeypatch):
    # (a) A cell that raises must be recorded as an N/A cell (same identity keys +
    # "na": true + na_reason, NO signal fields) and the loop MUST continue — never
    # crash the shard. The FIRST cell (item A) raises; the rest succeed.
    client = ScriptedClient(_ok_fn())
    cp = str(tmp_path / "cp_lps_intervention.jsonl")
    cache = str(tmp_path / ".llm_cache_lps_intv")
    tasks = [_task("A"), _task("B")]

    real_compute = intv.compute_cell

    def _boom_on_A(task, client, model, seed_base, **kw):
        if task.id == "A":
            raise TimeoutError("socket read timed out after 240s")
        return real_compute(task, client, model, seed_base, **kw)

    monkeypatch.setattr(intv, "compute_cell", _boom_on_A)

    r = intv.run(tasks, {}, models=["gpt-5.6-sol"], seed_bases=[30260713, 30270713],
                 checkpoint_path=cp, cache_dir=cache, k=3, _client_override=client,
                 allowed_roots=[str(tmp_path)])
    assert r["status"] == "ok"
    # 2 items × 1 model × 2 seeds = 4 cells all "completed" (2 real, 2 N/A).
    assert r["completed"] == 4
    assert r["na"] == 2
    recs = [x for x in r["results"] if not x.get("_header")]
    na_recs = [x for x in recs if x.get("na") is True]
    ok_recs = [x for x in recs if not x.get("na")]
    assert len(na_recs) == 2 and len(ok_recs) == 2
    for na in na_recs:
        assert na["task_id"] == "A"
        assert na["na"] is True
        assert na["na_reason"].startswith("TimeoutError:")
        assert "signal" not in na  # no leakage-prone key
        # An N/A cell carries NO signal fields.
        for k in ("H_seed", "is_flagged", "clarify", "b2", "seed_labels"):
            assert k not in na
        # It DOES carry the full identity + a fingerprint the merge needs.
        for k in ("task_id", "model", "seed_base", "stratum", "_fingerprint"):
            assert k in na
    for ok in ok_recs:
        assert ok["task_id"] == "B"
        assert "clarify" in ok and ok.get("na") is not True


def test_run_records_na_on_wallclock_timeout(tmp_path, monkeypatch):
    # The per-cell wall-clock guard: a cell that HANGS past CELL_TIMEOUT_SECONDS is
    # recorded N/A and the loop continues (the daemon worker is abandoned).
    import threading as _t
    client = ScriptedClient(_ok_fn())
    cp = str(tmp_path / "cp_lps_intervention.jsonl")
    cache = str(tmp_path / ".llm_cache_lps_intv")

    real_compute = intv.compute_cell
    release = _t.Event()

    def _hang_on_A(task, client, model, seed_base, **kw):
        if task.id == "A":
            release.wait(30)  # block until released (or the guard abandons us)
            return real_compute(task, client, model, seed_base, **kw)
        return real_compute(task, client, model, seed_base, **kw)

    monkeypatch.setattr(intv, "compute_cell", _hang_on_A)
    monkeypatch.setattr(intv, "CELL_TIMEOUT_SECONDS", 0.5)

    try:
        r = intv.run([_task("A"), _task("B")], {}, models=["gpt-5.6-sol"],
                     seed_bases=[30260713], checkpoint_path=cp, cache_dir=cache,
                     k=3, _client_override=client, allowed_roots=[str(tmp_path)])
    finally:
        release.set()
    assert r["completed"] == 2 and r["na"] == 1
    na = [x for x in r["results"] if x.get("na") is True]
    assert len(na) == 1 and na[0]["task_id"] == "A"
    assert "CELL_TIMEOUT_SECONDS" in na[0]["na_reason"]


def _na_cell(tid, model, seed, fp, reason="TimeoutError: hang"):
    return {"task_id": tid, "model": model, "seed_base": seed, "stratum": "AMB+",
            "na": True, "na_reason": reason, "_fingerprint": fp}


def test_merge_accepts_grid_with_one_na_cell(tmp_path):
    # (b) A grid where ONE cell is N/A (2 real + 1 N/A = 3 = complete) merges OK;
    # the N/A cell counts as present for completeness and is tracked separately.
    fp = _fp_intv(models=["m"], seed_bases=[100])
    roster = {"models": ["m"], "seed_bases": [100], "items": ["A", "B", "C"]}
    recs = [_cell("A", "m", 100, fp), _cell("B", "m", 100, fp),
            _na_cell("C", "m", 100, fp)]
    p = _write_ckpt(tmp_path / "cp_lps_intervention__m.jsonl", fp, recs,
                    roster=roster)
    merged = merge.merge_records([p])
    assert len(merged["records"]) == 3
    assert merged["n_na"] == 1
    assert merged["per_model_na"] == {"m": 1}
    # Completeness is satisfied — no MergeError raised.


def test_merge_missing_real_cell_still_raises_even_with_na(tmp_path):
    # N/A only fills the cell it OCCUPIES — a genuinely missing cell still aborts.
    fp = _fp_intv(models=["m"], seed_bases=[100])
    roster = {"models": ["m"], "seed_bases": [100], "items": ["A", "B", "C"]}
    recs = [_cell("A", "m", 100, fp), _na_cell("B", "m", 100, fp)]  # C missing
    p = _write_ckpt(tmp_path / "cp_lps_intervention__m.jsonl", fp, recs,
                    roster=roster)
    with pytest.raises(merge.MergeError):
        merge.merge_records([p])


def test_report_excludes_na_from_all_metrics_and_discloses(tmp_path):
    # (c) The report must EXCLUDE N/A cells from every metric AND disclose them.
    fp = _fp_intv(models=["gemini-3.5-flash"], seed_bases=[30260713, 30270713,
                                                           30280713])
    rows = []
    # AMB+ item with 3 seeds: 2 real (baseline I1 / oracle I0, clarify all False),
    # 1 N/A (the pathological hang). The N/A seed must NOT move ANY number.
    for s in (30260713, 30270713):
        rows.append({
            "task_id": "code_invoice_001_k1_date_format_convention",
            "model": "gemini-3.5-flash", "seed_base": s, "stratum": "AMB+",
            "H_seed": 0.2, "clarify": {p: True for p in intv.CLARIFY_POLICIES},
            "b2": {"baseline_label": "I1", "oracle_label": "I0"},
            "_fingerprint": fp,
        })
    rows.append(_na_cell("code_invoice_001_k1_date_format_convention",
                         "gemini-3.5-flash", 30280713, fp,
                         reason="TimeoutError: cell exceeded "
                                "CELL_TIMEOUT_SECONDS=240s"))

    result = report.analyze(rows, {})
    # Live cells = 2 (N/A excluded); the single item aggregates over 2 of 3 seeds.
    assert result["n_records"] == 2
    assert result["n_na"] == 1
    pooled = result["pooled"]
    assert pooled["n_items"] == 1
    # The one AMB+ item used the remaining 2 seeds → clean cd_primary values.
    hb2 = pooled["hb2"]
    assert hb2["n_AMB_pos"] == 1
    assert hb2["baseline_cd"] == pytest.approx(1.0)
    assert hb2["oracle_cd"] == pytest.approx(0.0)
    # The item aggregate saw exactly 2 rows (the N/A seed was dropped).
    items = report.aggregate_by_item(
        [r for r in rows if r.get("na") is not True], {})
    assert items[0]["n_rows"] == 2

    md = report.render_markdown(result, checkpoint="cp.jsonl", n_models=1)
    assert "N/A cells excluded from ALL metrics (1)" in md
    assert "gemini-3.5-flash 1" in md
    assert "code_invoice_001_k1_date_format_convention seed 30280713" in md


def test_report_na_only_item_dropped_entirely(tmp_path):
    # An item whose EVERY seed is N/A simply vanishes from the item set (it can
    # never contribute a metric) — still disclosed.
    fp = _fp_intv(models=["m"], seed_bases=[100])
    rows = [_na_cell("Z", "m", 100, fp)]
    result = report.analyze(rows, {})
    assert result["n_records"] == 0
    assert result["pooled"]["n_items"] == 0
    assert result["n_na"] == 1
    md = report.render_markdown(result, checkpoint="cp.jsonl", n_models=0)
    assert "N/A cells excluded from ALL metrics (1)" in md


def test_report_no_na_discloses_zero(tmp_path):
    # A fully-successful grid discloses "N/A cells excluded: 0".
    result = report.analyze(_hb1_rows(), {})
    assert result["n_na"] == 0
    md = report.render_markdown(result, checkpoint="cp.jsonl", n_models=1)
    assert "N/A cells excluded: 0" in md


def test_successful_grid_records_byte_identical_to_compute_cell(tmp_path):
    # (d) A fully-successful grid is UNCHANGED: each persisted record equals what
    # compute_cell produces directly (plus the _fingerprint the driver stamps),
    # with NO "na"/"na_reason" keys anywhere. Proves the SUCCESS path is untouched.
    fn = _ok_fn()
    client = ScriptedClient(fn)
    cp = str(tmp_path / "cp_lps_intervention.jsonl")
    cache = str(tmp_path / ".llm_cache_lps_intv")
    tasks = [_task("A", key_questions=["axis?"]), _task("B")]

    r = intv.run(tasks, {}, models=["gpt-5.6-sol"], seed_bases=[30260713],
                 checkpoint_path=cp, cache_dir=cache, k=3, _client_override=client,
                 allowed_roots=[str(tmp_path)])
    assert r["na"] == 0
    recs = [x for x in r["results"] if not x.get("_header")]
    assert len(recs) == 2
    for rec in recs:
        assert "na" not in rec and "na_reason" not in rec
        # Reproduce the cell directly and compare (drop the driver-only fingerprint).
        stratum = rec["stratum"]
        direct = intv.compute_cell(
            _task(rec["task_id"], key_questions=["axis?"]
                  if rec["task_id"] == "A" else None),
            ScriptedClient(fn), rec["model"], rec["seed_base"],
            k=3, tau=intv.TAU, tau_s=intv.TAU_S, stratum=stratum)
        persisted = {k: v for k, v in rec.items() if k != "_fingerprint"}
        assert persisted == direct



