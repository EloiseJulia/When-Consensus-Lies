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
