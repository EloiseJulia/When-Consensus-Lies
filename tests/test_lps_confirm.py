# constructed by: Claude (Anthropic) family
"""Offline unit tests for the Study-2 CONFIRMATORY driver + report.

# Implementer model family: Claude / Anthropic
# Auditor model family: MUST be non-Anthropic (Law 6 — cross-family requirement)

All tests run OFFLINE (no network). They assert:
  1. ``lps_confirm --dry-run`` / ``enumerate_jobs`` enumerate the 54 × 6 × 3 grid.
  2. The run fingerprint captures the model list AND the seed list.
  3. Path guards reject a foreign checkpoint / cache name.
  4. A scripted (mock-client) run writes records carrying the baseline panel.
  5. The report AUROC / flag-confusion / danger-quadrant computations are correct
     on synthetic strata.
  6. ANTI-LEAKAGE (inviolable): a confirm run over a sentinel task leaks no gold.
"""

from __future__ import annotations

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
import lps_confirm as confirm  # noqa: E402
import lps_confirm_report as report  # noqa: E402
import lps_confirm_merge as merge  # noqa: E402


class ScriptedClient:
    def __init__(self, fn, logit_conf: Optional[float] = None):
        self._fn = fn
        self._logit_conf = logit_conf
        self.recorded_prompts: List[str] = []

    def complete(self, role, prompt, seed=None, model=None, temperature=None, **kw):
        self.recorded_prompts.append(prompt)
        text = self._fn(role, prompt, seed)
        return SimpleNamespace(text=text, model=model or "mock", tokens_in=0,
                               tokens_out=0, cost_usd=0.0,
                               logit_conf=self._logit_conf)


@pytest.fixture(autouse=True)
def _stub_labeler(monkeypatch):
    monkeypatch.setattr(lps, "label_run", lambda run, task: run.output)


def _task(tid="T1", prompt="Do the thing.", domain="code_spec") -> Task:
    return Task(
        id=tid, domain=domain, prompt=prompt, latent_spec="spec",
        interpretations=[Interpretation(id="I0", is_target=True, gold_check="g")],
        ambiguity_level=1, key_questions=[], regime="H1_external",
    )


# ── 1. Dry-run / job enumeration ─────────────────────────────────────────────

def test_dry_run_full_grid_54x6x3():
    import registered_run as rr
    from common.config import load_config

    tasks = rr.load_tasks()
    assert len(tasks) == 54
    res = confirm.run(tasks, load_config(), dry_run=True)
    assert res["status"] == "dry_run"
    assert len(confirm.CONFIRM_MODELS) == 6
    assert len(confirm.CONFIRM_SEED_BASES) == 3
    assert res["total"] == 54 * 6 * 3  # 972


def test_enumerate_jobs_shapes():
    tasks = [_task("A"), _task("B")]
    jobs = confirm.enumerate_jobs(tasks, ["m1", "m2"], [10, 20])
    assert len(jobs) == 2 * 2 * 2
    keys = {(j["task_id"], j["model"], j["seed_base"]) for j in jobs}
    assert len(keys) == 8


# ── 2. Fingerprint captures models + seeds ───────────────────────────────────

def test_run_fingerprint_includes_models_and_seeds():
    fp = confirm.run_fingerprint(models=["b", "a"], seed_bases=[3, 1, 2],
                                 k=5, tau=0.0, tau_s=0.5)
    assert fp["models"] == ["a", "b"]          # sorted
    assert fp["seed_bases"] == [1, 2, 3]        # sorted
    assert fp["method_version"] == lps.METHOD_VERSION
    assert fp["k"] == 5 and fp["tau_s"] == 0.5


# ── 2b. Per-model sharding (PARALLEL-safe) ───────────────────────────────────

def test_sanitize_slug():
    assert confirm.sanitize_slug("gpt-5.6-sol") == "gpt-5_6-sol"
    assert confirm.sanitize_slug("anthropic/claude-opus-4.8") == \
        "anthropic_claude-opus-4_8"
    assert confirm.sanitize_slug("gpt-4o-mini") == "gpt-4o-mini"


def test_shard_paths_distinct_per_model():
    a_cp, a_cache = confirm.shard_checkpoint("gpt-5.6-sol"), \
        confirm.shard_cache("gpt-5.6-sol")
    b_cp, b_cache = confirm.shard_checkpoint("gemini-3.1-pro"), \
        confirm.shard_cache("gemini-3.1-pro")
    # Two model shards write DISTINCT checkpoint AND cache paths.
    assert a_cp != b_cp and a_cache != b_cache
    assert a_cp == ".run_partitions/cp_lps_confirm__gpt-5_6-sol.jsonl"
    assert a_cache == ".llm_cache_lps_confirm__gpt-5_6-sol"
    # Shard checkpoints still land under .run_partitions and pass the path guard.
    confirm._validate_output_paths(a_cp, a_cache)
    confirm._validate_output_paths(b_cp, b_cache)


# ── 3. Path guards ───────────────────────────────────────────────────────────

def test_path_guard_rejects_foreign_checkpoint():
    with pytest.raises(ValueError):
        confirm._validate_output_paths(
            ".run_partitions/cp_lps_pilot.jsonl", confirm.CACHE_DIR)


def test_path_guard_rejects_foreign_cache(tmp_path):
    cp = str(tmp_path / "cp_lps_confirm.jsonl")
    with pytest.raises(ValueError):
        confirm._validate_output_paths(cp, ".llm_cache_lps_pilot")


# ── 4. Scripted run writes records with the baseline panel ───────────────────

def test_scripted_run_writes_records_with_baselines(tmp_path):
    dims_json = '[{"dimension": "aggregation method", "values": ["sum", "mean"]}]'

    def fn(role, prompt, seed):
        return dims_json if "JSON array" in prompt else "I0"

    client = ScriptedClient(fn, logit_conf=0.75)
    tasks = [_task("A"), _task("B")]
    cp = str(tmp_path / "cp_lps_confirm.jsonl")
    cache = str(tmp_path / ".llm_cache_lps_confirm")

    result = confirm.run(
        tasks, {}, models=["gpt-4o-mini"], seed_bases=[100, 200],
        checkpoint_path=cp, cache_dir=cache, k=3, _client_override=client,
    )
    assert result["status"] == "ok"
    assert result["completed"] == 2 * 1 * 2   # 2 items × 1 model × 2 seeds
    recs = [r for r in result["results"] if not r.get("_header")]
    assert len(recs) == 4
    for r in recs:
        assert "baselines" in r
        b = r["baselines"]
        assert b["token_available"] is True
        assert b["token_uncertainty"] == pytest.approx(0.25)
        assert b["requirements_probing_count"] == 1
        assert "self_consistency_agreement" in b
        assert r["_fingerprint"]["models"] == ["gpt-4o-mini"]

    # Resume: a second identical run recomputes nothing.
    result2 = confirm.run(
        tasks, {}, models=["gpt-4o-mini"], seed_bases=[100, 200],
        checkpoint_path=cp, cache_dir=cache, k=3, _client_override=client,
    )
    assert result2["completed"] == 0 and result2["skipped"] == 4


def test_resume_fingerprint_mismatch_raises(tmp_path):
    def fn(role, prompt, seed):
        return "I0"
    client = ScriptedClient(fn, logit_conf=0.5)
    tasks = [_task("A")]
    cp = str(tmp_path / "cp_lps_confirm.jsonl")
    cache = str(tmp_path / ".llm_cache_lps_confirm")
    confirm.run(tasks, {}, models=["gpt-4o-mini"], seed_bases=[100],
                checkpoint_path=cp, cache_dir=cache, k=3, _client_override=client)
    # Re-run with a DIFFERENT seed set → incompatible fingerprint → refuse.
    with pytest.raises(RuntimeError):
        confirm.run(tasks, {}, models=["gpt-4o-mini"], seed_bases=[999],
                    checkpoint_path=cp, cache_dir=cache, k=3,
                    _client_override=client)


# ── 4b. Two model-shards → distinct paths + merge dedup ──────────────────────

def _run_shard(tmp_path, model, seed_bases, logit_conf=0.5):
    dims_json = '[{"dimension": "d", "values": ["a", "b"]}]'

    def fn(role, prompt, seed):
        return dims_json if "JSON array" in prompt else "I0"

    client = ScriptedClient(fn, logit_conf=logit_conf)
    cp = str(tmp_path / f"cp_lps_confirm__{confirm.sanitize_slug(model)}.jsonl")
    cache = str(tmp_path / f".llm_cache_lps_confirm__{confirm.sanitize_slug(model)}")
    confirm.run([_task("A"), _task("B")], {}, models=[model], seed_bases=seed_bases,
                checkpoint_path=cp, cache_dir=cache, k=3, _client_override=client)
    return cp


def test_two_shards_distinct_paths_and_merge_dedup(tmp_path):
    cp1 = _run_shard(tmp_path, "gpt-5.6-sol", [100])
    cp2 = _run_shard(tmp_path, "gemini-3.1-pro", [100])
    assert cp1 != cp2                      # concurrent runners → distinct files
    assert Path(cp1).exists() and Path(cp2).exists()

    merged = merge.merge_records([cp1, cp2])
    # 2 items × 2 models × 1 seed = 4 distinct cells; nothing to dedup.
    assert len(merged["records"]) == 4
    assert merged["n_dup"] == 0
    assert set(merged["per_model"]) == {"gpt-5.6-sol", "gemini-3.1-pro"}

    # Re-merging with a DUPLICATED shard path collapses the repeats (dedup by
    # task_id×model×seed×method_version), never double-counts.
    merged_dup = merge.merge_records([cp1, cp2, cp1])
    assert len(merged_dup["records"]) == 4
    assert merged_dup["n_dup"] == 2        # the 2 records of cp1 seen twice
    assert merged_dup["n_conflict"] == 0


def test_merge_glob_and_write(tmp_path):
    _run_shard(tmp_path, "gpt-5.6-sol", [100])
    _run_shard(tmp_path, "gemini-3.1-pro", [100])
    paths = merge.iter_shard_paths(str(tmp_path / "cp_lps_confirm__*.jsonl"))
    assert len(paths) == 2
    merged = merge.merge_records(paths)
    out = str(tmp_path / "cp_lps_confirm_merged.jsonl")
    merge.write_merged(merged["records"], out)
    # Round-trip: the report can load the merged checkpoint (header skipped).
    reloaded = report.load_records(out)
    assert len(reloaded) == 4


# ── 4b. Merge fail-loud validation (BLOCKER-2 fixes) ─────────────────────────

def _write_shard(path, fingerprint, records):
    """Write a shard file: header fingerprint line + one JSON record per line."""
    import json as _json
    lines = [_json.dumps({"_header": True, "_fingerprint": fingerprint})]
    for r in records:
        rr = dict(r)
        rr["_fingerprint"] = fingerprint
        lines.append(_json.dumps(rr))
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def _fp(model, *, k=5, tau=0.0, tau_s=0.5, seed_bases=(100,),
        method_version="lps-test-v1"):
    return {"method_version": method_version, "k": k, "tau": tau, "tau_s": tau_s,
            "models": [model], "seed_bases": list(seed_bases)}


def _cell(tid, model, seed_base, h_ctx=1.0, h_seed=0.2):
    return {"task_id": tid, "model": model, "seed_base": seed_base,
            "H_ctx_max": h_ctx, "H_seed": h_seed}


def test_merge_aborts_on_incompatible_fingerprints(tmp_path):
    # Two shards differing ONLY on the shared knob k → incompatible → abort.
    s1 = _write_shard(tmp_path / "cp_lps_confirm__a.jsonl", _fp("A", k=5),
                      [_cell("T1", "A", 100)])
    s2 = _write_shard(tmp_path / "cp_lps_confirm__b.jsonl", _fp("B", k=3),
                      [_cell("T1", "B", 100)])
    with pytest.raises(merge.MergeError):
        merge.merge_records([s1, s2])


def test_merge_compatible_fingerprints_ok_despite_model_diff(tmp_path):
    # SAME shared fingerprint; only the per-shard `models` field differs → OK.
    s1 = _write_shard(tmp_path / "cp_lps_confirm__a.jsonl", _fp("A"),
                      [_cell("T1", "A", 100)])
    s2 = _write_shard(tmp_path / "cp_lps_confirm__b.jsonl", _fp("B"),
                      [_cell("T1", "B", 100)])
    merged = merge.merge_records([s1, s2])
    assert len(merged["records"]) == 2
    assert merged["n_conflict"] == 0


def test_merge_aborts_on_genuine_conflict(tmp_path):
    # Same dedup key (task_id, model, seed_base, method_version) but DIFFERENT
    # payload across shards → genuine conflict → abort (never silently keep first).
    s1 = _write_shard(tmp_path / "cp_lps_confirm__a.jsonl", _fp("A"),
                      [_cell("T1", "A", 100, h_ctx=1.0)])
    s2 = _write_shard(tmp_path / "cp_lps_confirm__a2.jsonl", _fp("A"),
                      [_cell("T1", "A", 100, h_ctx=0.0)])
    with pytest.raises(merge.MergeError):
        merge.merge_records([s1, s2])


def test_merge_identical_duplicate_is_not_a_conflict(tmp_path):
    # Identical payload for the same key across shards → dedup, NOT a conflict.
    rec = _cell("T1", "A", 100, h_ctx=1.0)
    s1 = _write_shard(tmp_path / "cp_lps_confirm__a.jsonl", _fp("A"), [rec])
    s2 = _write_shard(tmp_path / "cp_lps_confirm__a2.jsonl", _fp("A"), [rec])
    merged = merge.merge_records([s1, s2])
    assert len(merged["records"]) == 1
    assert merged["n_dup"] == 1
    assert merged["n_conflict"] == 0


# ── 5. Report computations on synthetic strata ───────────────────────────────

def _rec(tid, model, stratum, h_ctx, h_seed, *, token_unc=None,
         labels=None, dims=None, axis_match=False):
    return {
        "task_id": tid, "model": model, "stratum": stratum,
        "H_ctx_max": h_ctx, "H_seed": h_seed, "axis_match": axis_match,
        "seed_labels": labels if labels is not None else ["A", "A", "A"],
        "surfaced_dims": dims if dims is not None else [],
        "baselines": {"token_uncertainty": token_unc},
    }


def _synthetic_rows():
    rows = []
    # 4 AMB+: high H_ctx, low H_seed (danger), 1 surfaced dim, token_unc high.
    for i in range(4):
        rows.append(_rec(f"P{i}", "m", report.AMB_POS, 1.0, 0.2,
                         token_unc=0.8, labels=["A", "B", "C"],
                         dims=[{"dimension": "d", "values": ["a", "b"]}],
                         axis_match=(i < 2)))
    # 4 AMB-: zero H_ctx, low H_seed, no dims, token_unc low.
    for i in range(4):
        rows.append(_rec(f"N{i}", "m", report.AMB_NEG, 0.0, 0.2,
                         token_unc=0.1, labels=["A", "A", "A"], dims=[]))
    return rows


def test_report_perfect_separation():
    a = report.analyze_group(_synthetic_rows())
    # H_ctx-self perfectly separates AMB+ (1.0) from AMB- (0.0).
    assert a["aurocs"]["H_ctx_self"]["auroc"] == pytest.approx(1.0)
    # Flag confusion at frozen op point: all AMB+ flagged, no AMB- flagged.
    c = a["flag_confusion"]
    assert c["TP"] == 4 and c["FP"] == 0 and c["FN"] == 0 and c["TN"] == 4
    assert a["flag_precision"] == pytest.approx(1.0)
    assert a["flag_recall"] == pytest.approx(1.0)
    assert a["k0_false_positive_rate"] == pytest.approx(0.0)
    # Danger mass: all 4 AMB+ in the low-H_seed high-H_ctx quadrant.
    assert a["danger_quadrant"]["mass"] == pytest.approx(1.0)
    assert a["danger_quadrant"]["n_danger"] == 4
    # Localization (secondary): 2/4 axis matches.
    assert a["localization_AMB_pos_hit_rate"] == pytest.approx(0.5)


def _multimodel_rows():
    """6 items (3 AMB+, 3 AMB−), EACH appearing across 3 models × 2 seeds = 6 rows.

    Per-item H_ctx is NOISY across rows but its MEAN separates the strata, so a
    correct per-item aggregation must collapse the 36 run cells to 6 item points.
    """
    rows = []
    models = ["m1", "m2", "m3"]
    seeds = [100, 200]
    for i in range(3):  # AMB+ items: mean H_ctx high, low H_seed (danger)
        for m in models:
            for s in seeds:
                hc = 1.0 if (s == 100) else 0.6   # noisy but mean > 0
                rows.append({
                    "task_id": f"P{i}", "model": m, "seed_base": s,
                    "stratum": report.AMB_POS, "H_ctx_max": hc, "H_seed": 0.2,
                    "axis_match": True, "seed_labels": ["A", "B", "C"],
                    "surfaced_dims": [{"dimension": "d", "values": ["a", "b"]}],
                    "baselines": {"token_uncertainty": 0.8},
                })
    for i in range(3):  # AMB- items: H_ctx zero
        for m in models:
            for s in seeds:
                rows.append({
                    "task_id": f"N{i}", "model": m, "seed_base": s,
                    "stratum": report.AMB_NEG, "H_ctx_max": 0.0, "H_seed": 0.2,
                    "axis_match": False, "seed_labels": ["A", "A", "A"],
                    "surfaced_dims": [],
                    "baselines": {"token_uncertainty": 0.1},
                })
    return rows


def test_report_cluster_bootstrap_counts_items_not_run_cells():
    rows = _multimodel_rows()
    assert len(rows) == 36                       # 6 items × 3 models × 2 seeds
    a = report.analyze_group(rows)
    # The unit of analysis is the ITEM: 6 aggregates, NOT 36 run cells.
    assert a["n_items"] == 6
    assert a["n_records"] == 36
    hctx = a["aurocs"]["H_ctx_self"]
    # AUROC computed on per-item points → 3 pos + 3 neg = 6 (never 18+18).
    assert hctx["n_pos"] == 3 and hctx["n_neg"] == 3
    assert hctx["auroc"] == pytest.approx(1.0)
    # Confusion counts are out of the 6 pre-registered items, not 36 rows.
    c = a["flag_confusion"]
    assert c["TP"] + c["FP"] + c["FN"] + c["TN"] == 6
    assert c["TP"] == 3 and c["FP"] == 0
    # Danger mass over the 3 AMB+ items (each mean-H_ctx > 0, mean-H_seed ≤ τ_s).
    assert a["danger_quadrant"]["n_AMB_pos"] == 3
    assert a["danger_quadrant"]["mass"] == pytest.approx(1.0)
    # Cluster CI is item-clustered: perfect separation → CI hugs 1.0.
    assert hctx["ci_lo"] is not None and hctx["ci_lo"] >= 0.9
    assert hctx["ci_hi"] == pytest.approx(1.0)


def test_report_per_item_mean_collapses_noisy_rows():
    # An AMB+ item with MIXED rows (some H_ctx=0) whose MEAN is still > 0 must be
    # a SINGLE flagged item, not counted once per row.
    rows = [
        {"task_id": "P0", "model": "m1", "seed_base": 100, "stratum": report.AMB_POS,
         "H_ctx_max": 1.0, "H_seed": 0.2, "axis_match": True,
         "seed_labels": ["A", "B"], "surfaced_dims": [], "baselines": {}},
        {"task_id": "P0", "model": "m2", "seed_base": 100, "stratum": report.AMB_POS,
         "H_ctx_max": 0.0, "H_seed": 0.2, "axis_match": False,
         "seed_labels": ["A", "A"], "surfaced_dims": [], "baselines": {}},
        {"task_id": "N0", "model": "m1", "seed_base": 100, "stratum": report.AMB_NEG,
         "H_ctx_max": 0.0, "H_seed": 0.2, "axis_match": False,
         "seed_labels": ["A", "A"], "surfaced_dims": [], "baselines": {}},
    ]
    a = report.analyze_group(rows)
    assert a["n_items"] == 2                      # P0 (2 rows) collapses to 1 item
    c = a["flag_confusion"]
    # P0 mean H_ctx = 0.5 > 0 → flagged once; totals out of 2 items.
    assert c["TP"] == 1 and c["FN"] == 0
    assert c["TP"] + c["FP"] + c["FN"] + c["TN"] == 2


def test_report_token_logprob_na_excluded():
    rows = _synthetic_rows()
    # Blank out token uncertainty on half the AMB+ → those excluded, counted N/A.
    rows[0]["baselines"]["token_uncertainty"] = None
    rows[1]["baselines"]["token_uncertainty"] = None
    a = report.analyze_group(rows)
    tok = a["aurocs"]["token_logprob"]
    assert tok["n_na"] == 2
    # Remaining token scores still separate AMB+ (0.8) from AMB- (0.1).
    assert tok["auroc"] == pytest.approx(1.0)


def test_report_baseline_loses_to_detector():
    # H_seed identical across strata → AUROC ~0.5; H_ctx-self perfect → detector wins.
    a = report.analyze_group(_synthetic_rows())
    assert a["aurocs"]["H_seed"]["auroc"] == pytest.approx(0.5)
    assert a["aurocs"]["H_ctx_self"]["auroc"] > a["aurocs"]["H_seed"]["auroc"]


def test_report_flag_recompute_uses_frozen_operating_point():
    # A record stored with a stale flag but H_ctx=0 must NOT be flagged.
    r = _rec("X", "m", report.AMB_POS, 0.0, 0.2)
    assert report._is_flagged_frozen(r) is False
    r2 = _rec("Y", "m", report.AMB_POS, 0.7, 0.4)
    assert report._is_flagged_frozen(r2) is True
    # High H_seed (> tau_s) suppresses the flag even with high H_ctx.
    r3 = _rec("Z", "m", report.AMB_POS, 0.7, 0.9)
    assert report._is_flagged_frozen(r3) is False


def test_report_render_markdown_smoke():
    rows = _synthetic_rows()
    result = {"per_model": {"m": report.analyze_group(rows)},
              "pooled": report.analyze_group(rows), "n_records": len(rows)}
    md = report.render_markdown(result, checkpoint="cp.jsonl", n_models=1)
    assert "Confirmatory detection results" in md
    assert "H_ctx-self" in md and "AUROC" in md


# ── 6. ANTI-LEAKAGE (inviolable) ─────────────────────────────────────────────

_SENTINELS = ["TARGETSENTINEL_I0", "GOLDCHECKSENTINEL", "KEYQUESTIONSENTINEL",
              "LATENTSPECSENTINEL", "IXYZLEAK_TARGET", "IFOILLEAK"]


def _leak_task() -> Task:
    return Task(
        id="LEAK_001", domain="code_spec",
        prompt="Write a function that returns the aggregate of the inputs.",
        latent_spec="LATENTSPECSENTINEL hidden convention.",
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


def test_anti_leakage_confirm_run(tmp_path):
    dims_json = '[{"dimension": "rounding rule", "values": ["up", "down"]}]'

    def fn(role, prompt, seed):
        return dims_json if "JSON array" in prompt else "I0"

    client = ScriptedClient(fn, logit_conf=0.6)
    cp = str(tmp_path / "cp_lps_confirm.jsonl")
    cache = str(tmp_path / ".llm_cache_lps_confirm")
    confirm.run([_leak_task()], {}, models=["gpt-4o-mini"], seed_bases=[100],
                checkpoint_path=cp, cache_dir=cache, k=3, _client_override=client)
    for p in client.recorded_prompts:
        for s in _SENTINELS:
            assert s not in p, f"LEAK: sentinel {s!r} in confirm prompt:\n{p}"
