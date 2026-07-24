"""Deterministic offline tests for the Amendment 13/14 run + analysis apparatus.

# Implementer model family: Claude/Anthropic

All tests run FULLY OFFLINE — zero network, zero token. The live path is guarded
by RUNNER_LIVE=1 which is NEVER set here. Covers:

  1. Driver: load_amd_tasks enumerates the right amd13/amd14 grid; dry-run job
     count matches the Runner's enumerated grid; the live guard prints "skipped";
     the path guard rejects confirmatory/other-pass checkpoints & caches.
  2. Manipulation check: verdict logic (high H2 / low H1 → PASS; low H2 → FAIL
     honestly); build_verdict_from_tidy on synthetic labels; anti-leakage on the
     selected tested prompts.
  3. Report: A13 per-domain contrast + regime×domain read from synthetic labels;
     A14 unconditioned pooled rate + delta vs the screened rate.
  4. No confirmatory/frozen touch: default namespaces are amd_run-isolated.
  5. Anti-leakage: no gold/target/foil/key_questions text in any tested prompt.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_SCRIPTS = _REPO_ROOT / "scripts"


def _load(mod_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(mod_name, _SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    sys.modules[mod_name] = mod
    return mod


amd_run = _load("amd_run", "amd_run.py")
manip = _load("amd13_manipulation_check", "amd13_manipulation_check.py")
report = _load("amd_run_report", "amd_run_report.py")


# ── Synthetic tidy-table builder ─────────────────────────────────────────────

def _tidy_rows(specs: List[Dict[str, Any]]) -> pd.DataFrame:
    """Build an agent-level tidy DataFrame from compact per-cell specs.

    Each spec: {item, regime, domain, ambiguity_k, labels:[...], method, model,
    model_class, seed, target}. One row per label.
    """
    rows = []
    for s in specs:
        for lb in s["labels"]:
            rows.append({
                "task": s["item"],
                "method": s.get("method", "single"),
                "model_class": s.get("model_class", "reasoning"),
                "seed": s.get("seed", 1),
                "label": lb,
                "target": s.get("target", "I0"),
                "regime": s["regime"],
                "ambiguity_k": s.get("ambiguity_k", 1),
                "model": s.get("model", "gpt-5.6-sol"),
                "domain": s["domain"],
            })
    return pd.DataFrame(rows)


# ═══════════════════════════ 1. DRIVER ═══════════════════════════

def test_load_amd13_tasks_grid():
    tasks = amd_run.load_amd_tasks("amd13", include_h1_anchors=True)
    h1 = [t for t in tasks if t.regime == "H1_external"]
    h2 = [t for t in tasks if t.regime == "H2_derivable"]
    assert len(h2) == 16, "16 amd13 sidecar H2 items (4 base × k0+k1 × 2 domains)"
    assert len(h1) == 8, "8 matched frozen H1 anchors (4 per domain × 2 domains)"


def test_load_amd14_tasks_grid():
    tasks = amd_run.load_amd_tasks("amd14")
    assert len(tasks) == 48, "48 unfiltered items (24 base × k0+k1)"
    assert all(t.regime == "H1_external" for t in tasks)


def test_expected_job_count_matches_runner_grid():
    """The dry-run job count == the Runner's enumerated grid, for both sets."""
    from common.config import load_config
    cfg = load_config()
    for which, n_expected_tasks in (("amd13", 24), ("amd14", 48)):
        include = which == "amd13"
        tasks = amd_run.load_amd_tasks(which, include_h1_anchors=include)
        assert len(tasks) == n_expected_tasks
        seeds = [1, 2, 3]
        runner, _ = amd_run.build_amd_runner(
            cfg, tasks, which=which,
            checkpoint_path=str(_REPO_ROOT / ".run_partitions" / f"cp_amd_run__{which}.jsonl"),
            cache_dir=str(_REPO_ROOT / f".llm_cache_amd_run_{which}"),
            seeds=seeds, offline=True,
        )
        grid = runner.enumerate_grid()
        expected = amd_run.expected_job_count(len(tasks), seeds=seeds)
        assert len(grid) == expected
        # single (7 models) + heterogeneous-MAD (1 pool) per task per seed = 8
        assert expected == len(tasks) * 8 * 3


def test_dry_run_enumerates_without_live_calls(monkeypatch, capsys):
    monkeypatch.delenv("RUNNER_LIVE", raising=False)
    amd_run.main(["--which", "amd13", "--dry-run"])
    out = capsys.readouterr().out
    assert "skipped" not in out.lower()
    assert "EXPECTED JOB COUNT: 576" in out
    assert "no live calls" in out


def test_live_guard_prints_skipped(monkeypatch, capsys):
    monkeypatch.delenv("RUNNER_LIVE", raising=False)
    with pytest.raises(SystemExit) as exc:
        amd_run.main(["--which", "amd14"])
    assert exc.value.code == 0
    assert "skipped" in capsys.readouterr().out.lower()


def test_path_guard_rejects_confirmatory_paths():
    # Confirmatory / other-pass tokens must be refused anywhere in the path.
    with pytest.raises(ValueError):
        amd_run.validate_output_paths(
            str(_REPO_ROOT / ".run_partitions" / "cp_lps_confirm.jsonl"),
            str(_REPO_ROOT / ".llm_cache_amd_run_amd13"),
        )
    with pytest.raises(ValueError):
        amd_run.validate_output_paths(
            str(_REPO_ROOT / ".run_partitions" / "cp_amd_run__amd13.jsonl"),
            str(_REPO_ROOT / ".llm_cache_registered_run"),
        )
    # A wrong-namespace basename is refused even without a protected token.
    with pytest.raises(ValueError):
        amd_run.validate_output_paths(
            str(_REPO_ROOT / ".run_partitions" / "some_other.jsonl"),
            str(_REPO_ROOT / ".llm_cache_amd_run_amd13"),
        )


def test_path_guard_accepts_own_paths():
    amd_run.validate_output_paths(
        str(_REPO_ROOT / ".run_partitions" / "cp_amd_run__amd13.jsonl"),
        str(_REPO_ROOT / ".llm_cache_amd_run_amd13"),
    )


def test_default_namespaces_are_isolated():
    for which in ("amd13", "amd14"):
        cp, cache, _ = amd_run._which_defaults(which)
        assert "cp_amd_run__" in cp
        assert ".llm_cache_amd_run" in cache
        for tok in ("registered_run", "confirm", "intervention", "pilot", "default_check"):
            assert tok not in Path(cp).name.lower()
            assert tok not in Path(cache).name.lower()


# ═══════════════════════ 2. MANIPULATION CHECK ═══════════════════════

def test_manip_verdict_pass_high_h2_low_h1():
    h2 = {"h2_a": 0.9, "h2_b": 0.8, "h2_c": 1.0}
    h1 = {"h1_a": 0.1, "h1_b": 0.0, "h1_c": 0.2}
    v = manip.manipulation_verdict(h2, h1)
    assert v["gate_pass"] is True
    assert v["cond_h2_high"] and v["cond_h1_low"] and v["cond_separation"]
    assert all(d["pass"] for d in v["h2_items"].values())


def test_manip_verdict_fail_low_h2_honest():
    # H2 items do NOT recover (low) → construction failed; verdict FAIL, no tuning.
    h2 = {"h2_a": 0.1, "h2_b": 0.0, "h2_c": 0.2}
    h1 = {"h1_a": 0.1, "h1_b": 0.0, "h1_c": 0.2}
    v = manip.manipulation_verdict(h2, h1)
    assert v["gate_pass"] is False
    assert not v["cond_h2_high"]
    assert not any(d["pass"] for d in v["h2_items"].values())


def test_manip_verdict_fail_no_separation():
    # H2 high but H1 also high → not separated → FAIL (domain/base-rate confound).
    h2 = {"h2_a": 0.9, "h2_b": 0.8}
    h1 = {"h1_a": 0.9, "h1_b": 0.85}
    v = manip.manipulation_verdict(h2, h1)
    assert v["gate_pass"] is False
    assert not v["cond_separation"]


def test_manip_recovery_rate():
    assert manip.recovery_rate(["I0", "I0", "I1", "I_perp"]) == 0.5
    assert manip.recovery_rate([]) == 0.0


def test_build_verdict_from_tidy_pass():
    h2_specs = [
        {"item": "code_roundhalf_001_k1_tie_convention", "regime": "H2_derivable",
         "domain": "code_spec", "labels": ["I0", "I0", "I0"]},
        {"item": "policy_parking_001_k1_partial_hour", "regime": "H2_derivable",
         "domain": "policy_qa", "labels": ["I0", "I0", "I1"]},
    ]
    h1_specs = [
        {"item": "code_roundcurr_001_k1_rounding_standard", "regime": "H1_external",
         "domain": "code_spec", "labels": ["I1", "I1", "I1"]},
        {"item": "policy_interest_001_k1_compounding", "regime": "H1_external",
         "domain": "policy_qa", "labels": ["I1", "I0", "I1"]},
    ]
    tidy = _tidy_rows(h2_specs + h1_specs)

    class _T:
        def __init__(self, i): self.id = i
    h2_tasks = [_T(s["item"]) for s in h2_specs]
    h1_tasks = [_T(s["item"]) for s in h1_specs]
    v = manip.build_verdict_from_tidy(tidy, h2_tasks, h1_tasks)
    assert v["mean_h2_recovery"] > v["mean_h1_recovery"]
    assert v["gate_pass"] is True


def test_manip_selected_prompts_anti_leakage():
    """No gold/target/foil/key_questions text leaks into any tested prompt."""
    h2, h1 = manip.select_manip_tasks()
    assert len(h2) == 8 and len(h1) == 8
    for t in h2 + h1:
        prompt = t.prompt.lower()
        # The hidden latent_spec / interpretation gold-check ids must not appear.
        for interp in t.interpretations:
            if interp.gold_check:
                assert interp.gold_check.lower() not in prompt
        assert "latent_spec" not in prompt
        assert "gold_check" not in prompt
        assert "key_questions" not in prompt


# ═══════════════════════════ 3. REPORT ═══════════════════════════

def _a13_synthetic_tidy() -> pd.DataFrame:
    specs = []
    # code_spec: 2 H1 items (converge to wrong I1, cd≈1) + 2 H2 items (resolve I0, cd≈0)
    for i in range(2):
        specs.append({"item": f"cs_h1_{i}", "regime": "H1_external", "domain": "code_spec",
                      "labels": ["I1", "I1", "I1"]})
        specs.append({"item": f"cs_h2_{i}", "regime": "H2_derivable", "domain": "code_spec",
                      "labels": ["I0", "I0", "I0"]})
    # policy_qa: same structure
    for i in range(2):
        specs.append({"item": f"pq_h1_{i}", "regime": "H1_external", "domain": "policy_qa",
                      "labels": ["I1", "I1", "I1"]})
        specs.append({"item": f"pq_h2_{i}", "regime": "H2_derivable", "domain": "policy_qa",
                      "labels": ["I0", "I0", "I0"]})
    return _tidy_rows(specs)


def test_a13_per_domain_contrast_and_regime_domain_read():
    tidy = _a13_synthetic_tidy()
    result = report.a13_analysis(tidy, manip_verdict={"gate_pass": True})
    for dom in ("code_spec", "policy_qa"):
        r = result["per_domain"][dom]
        assert r["cd_h1"] == pytest.approx(1.0)
        assert r["cd_h2"] == pytest.approx(0.0)
        assert r["contrast"] == pytest.approx(1.0)
        assert r["ci_lo"] > 0  # CI excludes 0
        assert r["direction_holds"] is True
    assert result["both_domains_sufficient"] is True
    assert result["main_effect"]["significant"] is True
    assert result["interaction"]["significant"] is False
    assert result["regime_effect_holds_within_domain"] is True
    assert result["crossing_supported"] is True
    assert result["provenance_dropped_cells"] == 0


def test_a13_requires_both_named_domains(monkeypatch):
    """MAJOR 5: one strong domain must NOT pass when the other is missing."""
    # Only code_spec present (policy_qa absent) → cannot claim the crossing.
    specs = []
    for i in range(3):
        specs.append({"item": f"cs_h1_{i}", "regime": "H1_external", "domain": "code_spec",
                      "labels": ["I1", "I1", "I1"]})
        specs.append({"item": f"cs_h2_{i}", "regime": "H2_derivable", "domain": "code_spec",
                      "labels": ["I0", "I0", "I0"]})
    result = report.a13_analysis(_tidy_rows(specs), manip_verdict={"gate_pass": True})
    assert result["both_domains_sufficient"] is False
    assert "policy_qa" in result["missing_or_underpowered_domains"]
    assert result["regime_effect_holds_within_domain"] is False
    assert result["crossing_supported"] is False


def test_a13_gate_fail_renders_no_crossing_claim():
    """MAJOR 4: a missing/failed manipulation verdict → validity-failure render only."""
    tidy = _a13_synthetic_tidy()
    # (a) verdict absent
    res_absent = report.a13_analysis(tidy, manip_verdict=None)
    assert res_absent["gate_pass"] is False
    assert res_absent["crossing_supported"] is False
    md_absent = report.render_amd13(res_absent)
    assert "VALIDITY FAILURE" in md_absent
    assert "no regime×domain crossing is asserted" in md_absent
    assert "H-A13 crossing supported: True" not in md_absent
    # (b) verdict present but FAILED
    res_fail = report.a13_analysis(tidy, manip_verdict={"gate_pass": False})
    md_fail = report.render_amd13(res_fail)
    assert "VALIDITY FAILURE" in md_fail
    assert "crossing supported" not in md_fail.lower()


def test_a13_gate_pass_renders_crossing_and_interaction():
    """Gate PASS → full render includes the interaction read + crossing verdict."""
    tidy = _a13_synthetic_tidy()
    res = report.a13_analysis(tidy, manip_verdict={"gate_pass": True})
    md = report.render_amd13(res)
    assert "GATE PASSED: True" in md
    assert "INTERACTION" in md
    assert "H-A13 crossing supported: True" in md


def test_a13_null_contrast_reported_honestly():
    # H2 also converges (cd high) → contrast ≈ 0 → direction does NOT hold.
    specs = []
    for i in range(2):
        specs.append({"item": f"cs_h1_{i}", "regime": "H1_external", "domain": "code_spec",
                      "labels": ["I1", "I1", "I1"]})
        specs.append({"item": f"cs_h2_{i}", "regime": "H2_derivable", "domain": "code_spec",
                      "labels": ["I1", "I1", "I1"]})
        specs.append({"item": f"pq_h1_{i}", "regime": "H1_external", "domain": "policy_qa",
                      "labels": ["I1", "I1", "I1"]})
        specs.append({"item": f"pq_h2_{i}", "regime": "H2_derivable", "domain": "policy_qa",
                      "labels": ["I1", "I1", "I1"]})
    result = report.a13_analysis(_tidy_rows(specs), manip_verdict={"gate_pass": True})
    r = result["per_domain"]["code_spec"]
    assert r["contrast"] == pytest.approx(0.0)
    assert r["direction_holds"] is False
    assert result["regime_effect_holds_within_domain"] is False
    assert result["crossing_supported"] is False


def test_a13_provenance_holdout_drops_constructor_cells():
    specs = [
        {"item": "cs_h1_0", "regime": "H1_external", "domain": "code_spec",
         "labels": ["I1", "I1"], "model": "mai-code-1-flash"},
        {"item": "cs_h1_1", "regime": "H1_external", "domain": "code_spec",
         "labels": ["I1", "I1"], "model": "gpt-5.6-sol"},
    ]
    tidy = _tidy_rows(specs)
    filtered, n = report.apply_provenance_holdout(tidy)
    assert n == 2  # the two mai-code agent rows dropped
    assert all(filtered["model"] != "mai-code-1-flash")


def test_a14_unconditioned_rate_and_delta():
    # 4 unfiltered items: cd values 1.0, 1.0, 0.0, 0.0 → pooled 0.5, delta -0.03.
    specs = [
        {"item": "u0", "regime": "H1_external", "domain": "code_spec", "labels": ["I1", "I1"]},
        {"item": "u1", "regime": "H1_external", "domain": "policy_qa", "labels": ["I1", "I1"]},
        {"item": "u2", "regime": "H1_external", "domain": "code_spec", "labels": ["I0", "I0"]},
        {"item": "u3", "regime": "H1_external", "domain": "data_analysis", "labels": ["I0", "I0"]},
    ]
    result = report.a14_analysis(_tidy_rows(specs))
    assert result["n_items"] == 4
    assert result["pooled_cd_primary"] == pytest.approx(0.5)
    assert result["delta_vs_screened"] == pytest.approx(0.5 - 0.53)
    assert result["fraction_convergent"] == pytest.approx(0.5)


@pytest.mark.parametrize("labels,expected_pooled", [
    (["I1", "I1"], 1.0),   # HIGH: unfiltered rate stays high
    (["I1", "I0"], 0.5),   # ATTENUATED: partly enrichment-driven
    (["I0", "I0"], 0.0),   # NULL: effect vanishes on the unfiltered sample
])
def test_a14_report_structure_identical_across_outcomes(labels, expected_pooled):
    """Integrity: report STRUCTURE + mandatory fields identical across all three
    outcomes (high / attenuated / null); only the numbers differ."""
    specs = [
        {"item": "u0", "regime": "H1_external", "domain": "code_spec", "labels": list(labels)},
        {"item": "u1", "regime": "H1_external", "domain": "policy_qa", "labels": list(labels)},
    ]
    result = report.a14_analysis(_tidy_rows(specs))
    assert result["pooled_cd_primary"] == pytest.approx(expected_pooled)
    md = report.render_amd14(result)
    # Mandatory structural anchors — MUST be present for every outcome.
    for anchor in (
        "# Amendment 14 — unfiltered-sample replication",
        "UNCONDITIONED",
        "HONESTLY regardless of outcome",
        "Pooled UNCONDITIONED cd_primary",
        "Delta vs screened",
        "Screened confirmatory rate",
        "Fraction of unfiltered items",
    ):
        assert anchor in md, f"missing structural field {anchor!r} for outcome {labels}"
    # Mandatory result keys are identical across outcomes.
    assert set(result.keys()) == {
        "n_items", "pooled_cd_primary", "ci_lo", "ci_hi", "screened_rate",
        "delta_vs_screened", "fraction_convergent", "per_item", "provenance_dropped_cells",
    }


def test_report_writes_markdown(tmp_path):
    tidy = _a13_synthetic_tidy()
    md = report.render_amd13(report.a13_analysis(tidy, manip_verdict={"gate_pass": True}))
    path = report.write_report("amd13", md, out_dir=str(tmp_path))
    assert Path(path).exists()
    assert "Amendment 13" in Path(path).read_text(encoding="utf-8")


# ═══════════ 4. BLOCKER 1: strict config allowlist + generated-prompt leakage ═══════════

def test_strict_config_rejection():
    """Only single + heterogeneous-MAD are permitted; everything else is refused."""
    with pytest.raises(ValueError):
        amd_run.validate_configs(["interpretation-diverse"])
    with pytest.raises(ValueError):
        amd_run.validate_configs(["single", "sc"])
    with pytest.raises(ValueError):
        amd_run.validate_configs(["homogeneous-MAD"])
    amd_run.validate_configs(["single", "heterogeneous-MAD"])  # OK


def test_cli_rejects_bad_config(monkeypatch):
    monkeypatch.delenv("RUNNER_LIVE", raising=False)
    with pytest.raises(SystemExit) as exc:
        amd_run.main(["--which", "amd13", "--dry-run", "--configs", "interpretation-diverse"])
    assert exc.value.code == 2


class _RecordingClient:
    """A stub LLMClient that records every generated prompt (no network)."""

    def __init__(self, cfg):
        self.config = cfg
        self.provider = "recording"
        self.base_url = "recording://stub"
        self.prompts: List[str] = []

    def complete(self, role, prompt, seed, temperature=None, family=None, model=None, **kw):
        self.prompts.append(prompt)

        class _C:
            pass
        c = _C()
        c.model = model or "gpt-5.6-sol"
        c.text = "Answer: 42. Confidence: 60%."
        c.logit_conf = 0.6
        return c


def _forbidden_tokens_for(task) -> List[str]:
    toks: List[str] = []
    if getattr(task, "latent_spec", None):
        toks.append(task.latent_spec)
    for kq in getattr(task, "key_questions", None) or []:
        toks.append(kq)
    for interp in task.interpretations:
        if interp.gold_check:
            toks.append(interp.gold_check)
    return toks


def test_generated_prompts_no_gold_leakage():
    """BLOCKER 1: capture the ACTUAL generated prompts sent to tested agents for
    BOTH amd13 AND amd14 under BOTH conditions; assert the harness ADDS no
    gold/target/foil/key_questions/latent_spec/gold_check text beyond what the
    item legitimately presents in ``task.prompt`` (k0 controls legitimately show
    the full spec; k1 underdetermined items must hide the resolution)."""
    from harness.run import run_task
    from common.config import load_config
    cfg = load_config()

    for which in ("amd13", "amd14"):
        tasks = amd_run.load_amd_tasks(which, include_h1_anchors=(which == "amd13"))
        assert tasks
        for task in tasks:
            base = task.prompt  # the ONLY task-derived content single/MAD may embed
            forbidden = _forbidden_tokens_for(task)
            for config in ("single", "heterogeneous-MAD"):
                client = _RecordingClient(cfg)
                run_task(task, config, client)
                assert client.prompts, f"{which}/{config} produced no prompt"
                for prompt in client.prompts:
                    low = prompt.lower()
                    # harness scaffolding tokens must never appear
                    assert "latent_spec" not in low
                    assert "gold_check" not in low
                    assert "key_questions" not in low
                    for tok in forbidden:
                        if not tok:
                            continue
                        # a forbidden token may appear ONLY if the item itself
                        # already contains it (k0 control); the harness must add none.
                        if tok in prompt:
                            assert tok in base, (
                                f"harness LEAKED {tok!r} into {which}/{config} prompt "
                                f"(not present in task.prompt)"
                            )


# ═══════════ 5. BLOCKER 2: report path guard (input + output) ═══════════

def test_report_input_guard_rejects_confirmatory():
    with pytest.raises(ValueError):
        report.validate_report_input(
            str(_REPO_ROOT / ".run_partitions" / "cp_lps_confirm.jsonl"))
    with pytest.raises(ValueError):
        report.validate_report_input(
            str(_REPO_ROOT / ".run_partitions" / "cp_lps_intervention.jsonl"))
    # wrong namespace basename refused even without a protected token
    with pytest.raises(ValueError):
        report.validate_report_input(
            str(_REPO_ROOT / ".run_partitions" / "some_other.jsonl"))
    # own namespace accepted
    report.validate_report_input(
        str(_REPO_ROOT / ".run_partitions" / "cp_amd_run__amd13.jsonl"))


def test_report_output_guard():
    with pytest.raises(ValueError):
        report.validate_report_output(str(_REPO_ROOT / "files" / "confirm_results.md"))
    with pytest.raises(ValueError):
        report.validate_report_output(str(_REPO_ROOT / "files" / "arbitrary.md"))
    report.validate_report_output(str(_REPO_ROOT / "files" / "amd13_results.md"))
    report.validate_report_output(str(_REPO_ROOT / "files" / "amd14_results.md"))


def test_report_write_rejects_protected_out_dir(tmp_path):
    md = "# x"
    bad_dir = tmp_path / "cp_lps_confirm"
    bad_dir.mkdir()
    with pytest.raises(ValueError):
        report.write_report("amd13", md, out_dir=str(bad_dir))


# ═══════════ 6. MAJOR 3: oracle-hint recovery probe supplies the hint ═══════════

def test_probe_task_supplies_oracle_hint():
    """The probe augments the tested prompt with the deleted-axis question(s)
    (the oracle hint) — the ONLY permitted gold-bearing input for the recovery
    probe — while k0 controls (no key_questions) are left unchanged."""
    h2, h1 = manip.select_manip_tasks()
    for task in h2 + h1:
        probe = manip.build_probe_task(task)
        assert probe.id == task.id  # identity preserved for labeling/tidy join
        assert len(probe.prompt) > len(task.prompt)
        assert "recovery probe" in probe.prompt.lower()
        # every deleted-axis question is surfaced as the controlled clarification
        for kq in task.key_questions:
            assert kq in probe.prompt
        # but the target/foil gold-check ids are NOT injected
        for interp in task.interpretations:
            if interp.gold_check:
                assert interp.gold_check not in probe.prompt


def test_probe_task_noop_without_key_questions():
    from common.schema import Task, Interpretation
    t = Task(
        id="ctrl_k0", domain="code_spec", prompt="Do the thing.",
        latent_spec="spec", interpretations=[Interpretation("I0", True, "chk")],
        ambiguity_level=0, key_questions=[], regime="H2_derivable",
    )
    assert manip.build_probe_task(t) is t


def test_write_and_load_manip_verdict(tmp_path):
    verdict = {"gate_pass": True, "mean_h2_recovery": 0.9, "mean_h1_recovery": 0.1,
               "separation": 0.8}
    path = tmp_path / "amd13_manipulation_verdict.json"
    manip.write_verdict(verdict, path=str(path))
    loaded = report.load_manip_verdict(str(path))
    assert loaded["gate_pass"] is True
    # absent file → None (treated as NOT passed)
    assert report.load_manip_verdict(str(tmp_path / "missing.json")) is None
