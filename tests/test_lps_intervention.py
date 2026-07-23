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
                                str(tmp_path / ".llm_cache_lps_intv"))


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
                  checkpoint_path=cp, cache_dir=cache, k=3, _client_override=client)
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
                  checkpoint_path=cp, cache_dir=cache, k=3, _client_override=client)
    assert r2["completed"] == 0 and r2["skipped"] == 4


def test_resume_fingerprint_mismatch_raises(tmp_path):
    def fn(role, prompt, seed):
        return "I1"
    client = ScriptedClient(fn)
    cp = str(tmp_path / "cp_lps_intervention.jsonl")
    cache = str(tmp_path / ".llm_cache_lps_intv")
    intv.run([_task("A")], {}, models=["gpt-5.6-sol"], seed_bases=[30260713],
             checkpoint_path=cp, cache_dir=cache, k=3, _client_override=client)
    with pytest.raises(RuntimeError):
        intv.run([_task("A")], {}, models=["gpt-5.6-sol"], seed_bases=[99999999],
                 checkpoint_path=cp, cache_dir=cache, k=3, _client_override=client)


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
    intv._validate_output_paths(str(tmp_path / "cp_lps_intervention.jsonl"),
                                str(tmp_path / ".llm_cache_lps_intv"))


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


def _write_ckpt(path, fp, records):
    lines = [json.dumps({"_header": True, "_fingerprint": fp})]
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
    fp_a = _fp_intv(models=["a"], seed_bases=[100])
    fp_b = _fp_intv(models=["b"], seed_bases=[100])
    p1 = _write_ckpt(tmp_path / "cp_lps_intervention__a.jsonl", fp_a,
                     [_cell("A", "a", 100, fp_a), _cell("B", "a", 100, fp_a)])
    p2 = _write_ckpt(tmp_path / "cp_lps_intervention__b.jsonl", fp_b,
                     [_cell("A", "b", 100, fp_b), _cell("B", "b", 100, fp_b)])
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
    fp = _fp_intv(seed_bases=[100, 200])
    recs = [_cell("A", "m", 100, fp), _cell("A", "m", 200, fp),
            _cell("B", "m", 100, fp)]
    cp = _write_ckpt(tmp_path / "cp_lps_intervention.jsonl", fp, recs)
    with pytest.raises(SystemExit):
        report.main(["--checkpoint", cp, "--out", str(tmp_path / "out.md")])


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
