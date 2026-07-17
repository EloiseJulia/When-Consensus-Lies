# constructed by: Claude (Anthropic) family
"""Offline end-to-end test for the default-check diagnostic (Deliverable 2 + fixture).

Runs with NO network and NO token: the driver drives the deterministic OFFLINE mock
LLM client. Verifies:
  A. The select -> run -> label -> CD/I_perp report pipeline works end-to-end offline.
  B. The enumerated-vs-with-I_perp convergent-delusion math is correct on crafted labels.
  C. Every bench.diagnostic subtler trap is 100% distinguishable (executable gold).
  D. The CLI double-guard: with no env flag / no token, main() prints "skipped", exit 0.

harness/metrics.py is NOT modified; the enumerated variant is a thin script-local helper.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

# ── Import the driver module (scripts/ is not a package) ──────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_DC_PATH = _REPO_ROOT / "scripts" / "default_check.py"
_spec = importlib.util.spec_from_file_location("default_check", _DC_PATH)
default_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(default_check)  # type: ignore[union-attr]


@pytest.fixture(autouse=True)
def _clear_domain_caches():
    """Clear module-level executable-gold result caches before each test (see
    test_pilot_nulls.py) so cross-test checker state never leaks."""
    for mod in ("bench.data_analysis", "bench.code_spec", "bench.diagnostic"):
        try:
            m = __import__(mod, fromlist=["_RESULT_CACHE"])
            getattr(m, "_RESULT_CACHE", {}).clear()
        except (ImportError, AttributeError):
            pass
    yield


@pytest.fixture
def artifacts_dir():
    """A worktree-relative scratch dir for checkpoint + cache (NOT the system temp).
    Cleaned up afterwards."""
    d = _REPO_ROOT / "tests" / "_diag_artifacts"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ── B. CD math: enumerated (I_perp excluded from modal) vs frozen (I_perp eligible) ──

def test_cd_enumerated_vs_frozen_documented_case():
    """labels I1,I1,I_perp,I_perp,I_perp / target I0:
      frozen (I_perp eligible)   -> I_perp is modal wrong = 3/5 = 0.60
      enumerated (I_perp excluded)-> I1 is modal enumerated wrong = 2/5 = 0.40
    I_perp agents STAY in the denominator (len=5) for BOTH."""
    labels = ["I1", "I1", "I_perp", "I_perp", "I_perp"]
    stats = default_check.ensemble_stats(labels, target="I0")
    assert stats["cd_frozen_with_iperp"] == pytest.approx(0.60)
    assert stats["cd_enumerated"] == pytest.approx(0.40)
    assert stats["i_perp_rate"] == pytest.approx(0.60)
    assert stats["resolve_rate_to_I0"] == pytest.approx(0.0)
    assert stats["modal_wrong_enumerated"] == "I1"
    assert default_check.convergent_delusion_enumerated(labels, "I0") == pytest.approx(0.40)


def test_cd_enumerated_equals_frozen_when_no_iperp():
    """With no I_perp, the two CD definitions coincide."""
    labels = ["I1", "I1", "I1", "I0", "I2"]  # I1 modal wrong = 3/5
    stats = default_check.ensemble_stats(labels, target="I0")
    assert stats["cd_frozen_with_iperp"] == pytest.approx(0.60)
    assert stats["cd_enumerated"] == pytest.approx(0.60)
    assert stats["i_perp_rate"] == pytest.approx(0.0)
    assert stats["modal_wrong_enumerated"] == "I1"


def test_cd_all_iperp_diverges():
    """All-I_perp: frozen saturates at 1.0 (I_perp modal), enumerated is 0.0
    (no enumerated wrong foil). This is exactly the offline-mock regime."""
    labels = ["I_perp"] * 5
    stats = default_check.ensemble_stats(labels, target="I0")
    assert stats["cd_frozen_with_iperp"] == pytest.approx(1.0)
    assert stats["cd_enumerated"] == pytest.approx(0.0)
    assert stats["i_perp_rate"] == pytest.approx(1.0)
    assert stats["modal_wrong_enumerated"] is None


def test_cd_full_resolution_to_target():
    """All agents converge on the true target I0: no delusion, full resolution."""
    labels = ["I0", "I0", "I0"]
    stats = default_check.ensemble_stats(labels, target="I0")
    assert stats["cd_frozen_with_iperp"] == pytest.approx(0.0)
    assert stats["cd_enumerated"] == pytest.approx(0.0)
    assert stats["resolve_rate_to_I0"] == pytest.approx(1.0)


def test_cd_empty_labels():
    assert default_check.convergent_delusion_enumerated([], "I0") == 0.0
    stats = default_check.ensemble_stats([], target="I0")
    assert stats["cd_enumerated"] == 0.0
    assert stats["i_perp_rate"] == 0.0


# ── B'. build_report threads the CD math through to per-ensemble rows ──────────

def test_build_report_cd_math_on_crafted_runs():
    """Craft sc-ensemble checkpoint records and confirm build_report reproduces the
    enumerated-vs-frozen split per (task, model)."""
    tasks, task_role = default_check.select_tasks()
    task = next(t for t in tasks if t.id == "code_quarter_001_k1_fiscal_year_start")
    labels = ["I1", "I1", "I_perp", "I_perp", "I_perp"]
    runs = [
        {"task_id": task.id, "config": "sc", "model_id": "deepseek/deepseek-r1",
         "seed": 20260713, "label": lab}
        for lab in labels
    ]
    report = default_check.build_report(runs, tasks, task_role)
    rows = [r for r in report["rows"]
            if r["task_id"] == task.id and r["ensemble_type"] == "homogeneous"]
    assert len(rows) == 1
    row = rows[0]
    assert row["cd_frozen_with_iperp"] == pytest.approx(0.60)
    assert row["cd_enumerated"] == pytest.approx(0.40)
    assert row["i_perp_rate"] == pytest.approx(0.60)
    assert row["regime"] == "H1_external"


# ── A. Full offline end-to-end pipeline (select -> run -> label -> report) ─────

def test_offline_end_to_end_pipeline(artifacts_dir):
    """Drive run_diagnostic against the OFFLINE mock client over a small task subset;
    verify well-formed rows, report keys, and the offline all-I_perp regime."""
    from common.config import load_config
    from common.llm import LLMClient

    cfg = load_config()
    all_tasks, task_role = default_check.select_tasks()
    # Small subset: one strong benchmark trap + one subtler diagnostic trap.
    subset = [t for t in all_tasks
              if t.id in ("code_quarter_001_k1_fiscal_year_start", "diag_weekday_001")]
    assert len(subset) == 2

    client = LLMClient(cfg, cache_dir=str(artifacts_dir / "cache"), offline=True)
    ckpt = artifacts_dir / "ckpt.jsonl"
    report = default_check.run_diagnostic(
        client, subset, task_role,
        checkpoint_path=str(ckpt), sc_k=3, budget_usd=None, rpm=100000,
    )

    # Report shape.
    for key in ("rows", "total_calls", "per_model_calls", "overall_i_perp_rate",
                "gpt4o_mini_excluded", "cd_vs_k_curve", "reasoner_resolution_h2",
                "saturation_disambiguation", "runner_status"):
        assert key in report, f"missing report key {key}"

    assert report["gpt4o_mini_excluded"] is True
    assert "openai/gpt-4o-mini" not in report["per_model_calls"]
    assert report["total_calls"] > 0
    assert report["rows"], "expected non-empty rows"

    # Offline mock outputs are non-code -> every label is I_perp.
    for row in report["rows"]:
        assert 0.0 <= row["cd_enumerated"] <= 1.0
        assert 0.0 <= row["cd_frozen_with_iperp"] <= 1.0
        assert row["i_perp_rate"] == pytest.approx(1.0)
        assert row["cd_enumerated"] == pytest.approx(0.0)  # no enumerated wrong offline
    assert report["overall_i_perp_rate"] == pytest.approx(1.0)

    # The diagnostic labeler was actually routed (both task ids present in rows).
    row_task_ids = {r["task_id"] for r in report["rows"]}
    assert "diag_weekday_001" in row_task_ids
    assert "code_quarter_001_k1_fiscal_year_start" in row_task_ids

    # SCHEMA STABILITY: the DEFAULT (GitHub-Models) report must expose EXACTLY the
    # historical key set — the roster refactor must NOT leak any new top-level key
    # (e.g. roster_name is FRONTIER-only) into the already-logged github diagnostic.
    assert set(report.keys()) == {
        "rows", "reasoner_resolution_h2", "cd_vs_k_curve",
        "saturation_disambiguation", "overall_i_perp_rate", "per_model_calls",
        "total_calls", "total_cost_usd", "gpt4o_mini_excluded", "runner_status",
    }
    assert "roster_name" not in report

    # The human-readable table renders without error.
    table = default_check.render_table(report)
    assert "I_perp" in table

    # Resumability: a second run reuses the checkpoint (no crash, same call semantics).
    report2 = default_check.run_diagnostic(
        client, subset, task_role,
        checkpoint_path=str(ckpt), sc_k=3, budget_usd=None, rpm=100000,
    )
    assert report2["rows"]


# ── C. Distinguishability of every subtler diagnostic trap (executable gold) ──

def test_all_diagnostic_traps_distinguishable():
    from bench import diagnostic
    from bench.validate import validate_task

    tasks = diagnostic.generate_tasks()
    assert len(tasks) >= 3
    for task in tasks:
        checkers, candidates, foils = diagnostic.get_checkers_and_candidates(task)
        result = validate_task(task, checkers, candidates,
                               foils=foils, require_foils=True)
        assert result["distinguishable"], (
            f"{task.id} not distinguishable: {result.get('errors')}"
        )
        # Reversed-property invariant: exactly one target, canonical id I0.
        targets = [i for i in task.interpretations if i.is_target]
        assert len(targets) == 1 and targets[0].id == "I0"


def test_diagnostic_reference_impls_label_to_target():
    """Each trap's I0 reference candidate labels to I0 (the reversed non-default intent)."""
    from bench import diagnostic

    for task in diagnostic.generate_tasks():
        _checkers, candidates, _foils = diagnostic.get_checkers_and_candidates(task)
        i0_code = candidates["I0"]

        class _Run:
            output = "```python\n" + i0_code + "\n```"

        label = diagnostic.label_diagnostic(_Run(), task)
        assert label == "I0", f"{task.id}: I0 reference labelled {label}, expected I0"


# ── D. CLI double-guard: no env flag / no token -> skipped, exit 0 ────────────

def test_main_skips_without_guards(monkeypatch, capsys):
    monkeypatch.delenv("RUN_DEFAULT_CHECK", raising=False)
    monkeypatch.delenv("GITHUB_MODELS_TOKEN", raising=False)
    monkeypatch.delenv("GH_MODELS_TOKEN", raising=False)
    assert default_check._should_run() is False
    with pytest.raises(SystemExit) as exc:
        default_check.main()
    assert exc.value.code == 0
    out = capsys.readouterr().out.lower()
    assert "skip" in out


def test_main_skips_with_flag_but_no_token(monkeypatch):
    monkeypatch.setenv("RUN_DEFAULT_CHECK", "1")
    monkeypatch.delenv("GITHUB_MODELS_TOKEN", raising=False)
    monkeypatch.delenv("GH_MODELS_TOKEN", raising=False)
    assert default_check._should_run() is False


# ── E. Reasoner arm prep: token budget + task-subset invariants ───────────────

def test_max_tokens_per_call_is_raised():
    """MAX_TOKENS_PER_CALL must be >= 8192 so reasoners complete reasoning + answer."""
    assert hasattr(default_check, "MAX_TOKENS_PER_CALL"), \
        "MAX_TOKENS_PER_CALL constant missing from default_check"
    assert default_check.MAX_TOKENS_PER_CALL >= 8192, (
        f"MAX_TOKENS_PER_CALL={default_check.MAX_TOKENS_PER_CALL} is too low; "
        "reasoning tokens count toward max_completion_tokens → truncation risk"
    )
    assert default_check.MAX_TOKENS_PER_CALL == 12288, \
        "Expected exactly 12288 per the reasoner-budget-plan §C"


def test_reasoner_sc_excludes_code_invoice():
    """REASONER_SC_EXCLUDED_IDS must contain all code_invoice K_GRADIENT_IDS."""
    assert hasattr(default_check, "REASONER_SC_EXCLUDED_IDS"), \
        "REASONER_SC_EXCLUDED_IDS constant missing from default_check"
    excluded = default_check.REASONER_SC_EXCLUDED_IDS
    for task_id in default_check.K_GRADIENT_IDS:
        assert task_id in excluded, (
            f"code_invoice task '{task_id}' is NOT in REASONER_SC_EXCLUDED_IDS; "
            "it must be excluded from the reasoner homogeneous-sc pass"
        )


def test_reasoner_sc_pass_skips_code_invoice(artifacts_dir):
    """The sc (pass A) checkpoint must NOT contain any code_invoice task runs;
    the single (pass B) checkpoint MAY contain them (heterogeneous pool keeps kgrad)."""
    from common.config import load_config
    from common.llm import LLMClient
    from harness.runner import CheckpointStore

    cfg = load_config()
    all_tasks, task_role = default_check.select_tasks()
    client = LLMClient(cfg, cache_dir=str(artifacts_dir / "cache"), offline=True)
    ckpt = artifacts_dir / "ckpt.jsonl"
    default_check.run_diagnostic(
        client, all_tasks, task_role,
        checkpoint_path=str(ckpt), sc_k=2, budget_usd=None, rpm=100000,
    )

    store = CheckpointStore(ckpt)
    sc_task_ids = {r["task_id"] for r in store.all_runs() if r["config"] == "sc"}
    for invoice_id in default_check.K_GRADIENT_IDS:
        assert invoice_id not in sc_task_ids, (
            f"code_invoice task '{invoice_id}' appeared in sc (pass A) checkpoint; "
            "it must be excluded from the reasoner homogeneous-sc pass"
        )
