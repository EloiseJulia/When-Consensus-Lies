# constructed by: Claude (Anthropic) family
"""Offline unit tests for the executable gold-ambiguity label (Study 2, v2 eval).

# Implementer model family: Claude / Anthropic
# Auditor model family: MUST be non-Anthropic (Law 6 — cross-family requirement)

Assert (all OFFLINE, no network):
  1. gold_ambiguity classifies AMB+ / NON-DISC / AMB- correctly on SYNTHETIC items
     whose interpretation signatures are controlled (via monkeypatch), plus on a
     couple of REAL benchmark items (executed, deterministic).
  2. H_ctx_gold is the entropy over the enumerated-interpretation gold results.
  3. ANTI-CIRCULARITY / anti-leakage: gold-ambiguity consults only the BENCHMARK's
     interpretations — it never builds or reads a model PROMPT (no prompt surface).
  4. The pilot2 AUROC / danger-quadrant analysis computes correct values on a
     controlled synthetic result set.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
for _p in (str(_REPO_ROOT), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common.schema import Task, Interpretation  # noqa: E402

import lps_gold as gold  # noqa: E402
import lps_pilot2 as p2  # noqa: E402


def _task(task_id="G1", *, domain="code_spec", key_questions=None, n_interp=2) -> Task:
    interps = [Interpretation(id=f"I{i}", is_target=(i == 0), gold_check=f"g{i}")
               for i in range(n_interp)]
    return Task(
        id=task_id, domain=domain, prompt="p", latent_spec="s",
        interpretations=interps, ambiguity_level=(1 if key_questions else 0),
        key_questions=key_questions or [], regime="H1_external",
    )


# ── 1. Stratification on synthetic (monkeypatched) items ─────────────────────

def _patch_sigs(monkeypatch, mapping):
    """Force gold interpretation signatures for the item under test."""
    monkeypatch.setattr(gold, "_interpretation_signatures", lambda task: mapping)


def test_amb_pos_when_interpretations_discriminate(monkeypatch):
    _patch_sigs(monkeypatch, {"I0": "out:A", "I1": "out:B"})
    res = gold.gold_ambiguity(_task(key_questions=["axis?"]))
    assert res["stratum"] == gold.STRATUM_AMB_POS
    assert res["n_distinct"] == 2
    assert res["H_ctx_gold"] == pytest.approx(1.0)  # 2 equally-likely clusters


def test_non_disc_when_axis_exists_but_results_coincide(monkeypatch):
    _patch_sigs(monkeypatch, {"I0": "same", "I1": "same"})
    res = gold.gold_ambiguity(_task(key_questions=["axis exists"]))
    assert res["stratum"] == gold.STRATUM_NON_DISC
    assert res["n_distinct"] == 1
    assert res["H_ctx_gold"] == pytest.approx(0.0)


def test_amb_neg_when_no_deleted_axis(monkeypatch):
    # k0 control: single interpretation, no key_questions → gold-UNambiguous.
    _patch_sigs(monkeypatch, {"I0": "only"})
    res = gold.gold_ambiguity(_task(key_questions=[], n_interp=1))
    assert res["stratum"] == gold.STRATUM_AMB_NEG
    assert res["n_distinct"] == 1


def test_none_signatures_excluded_from_distinct(monkeypatch):
    # An interpretation whose gold could not be evaluated (None) is excluded; the
    # two runnable ones still discriminate → AMB+.
    _patch_sigs(monkeypatch, {"I0": "A", "I1": "B", "I2": None})
    res = gold.gold_ambiguity(_task(key_questions=["axis?"], n_interp=3))
    assert res["stratum"] == gold.STRATUM_AMB_POS
    assert res["n_distinct"] == 2


def test_policy_expected_signature_cent_tolerance():
    assert gold._policy_expected_signature({"amount": 123.45}) == "num:12345"
    assert gold._policy_expected_signature(950.0) == "num:95000"
    assert gold._policy_expected_signature({"amount": None}) is None
    assert gold._policy_expected_signature("nope") is None


# ── 2. Real benchmark items (executed, deterministic) ────────────────────────

def _real(task_id):
    import registered_run as rr
    return {t.id: t for t in rr.load_tasks()}[task_id]


def test_real_amb_pos_data_typical():
    # mean vs median central tendency → different gold results → AMB+.
    res = gold.gold_ambiguity(_real("data_typical_001_k1_central_tendency"))
    assert res["stratum"] == gold.STRATUM_AMB_POS
    assert res["n_distinct"] >= 2
    assert res["H_ctx_gold"] > 0.0


def test_real_amb_neg_k0_control():
    # k0 control: no deleted axis → AMB-.
    res = gold.gold_ambiguity(_real("code_quarter_001_k0"))
    assert res["stratum"] == gold.STRATUM_AMB_NEG
    assert res["H_ctx_gold"] == pytest.approx(0.0)


def test_real_policy_amb_pos():
    res = gold.gold_ambiguity(_real("policy_overtime_001_k1_overtime_threshold"))
    assert res["stratum"] == gold.STRATUM_AMB_POS
    assert res["n_distinct"] >= 2


# ── 3. Anti-circularity: gold never constructs a model prompt ────────────────

def test_gold_module_defines_no_prompt_surface():
    # The gold module must not import or expose any prompt template / LLM client —
    # it clusters BENCHMARK interpretations only (independent of the detector's
    # self-generated pins). Guard against accidental prompt leakage.
    src = Path(gold.__file__).read_text(encoding="utf-8")
    assert "PINNING_TEMPLATE" not in src
    assert "ASSUMPTION_SURFACING_TEMPLATE" not in src
    assert ".complete(" not in src  # no LLM calls in the gold path


# ── 4. pilot2 analysis metrics on controlled synthetic results ───────────────

def _row(task_id, stratum, h_seed, h_ctx, flagged, match=False, hgold=1.0):
    return {
        "task_id": task_id, "model": "m", "H_seed": h_seed, "H_ctx_max": h_ctx,
        "is_flagged": flagged, "axis_match": match, "n_pins_total": 2,
        "n_parseable_total": 2, "H_ctx_gold": hgold,
    }


def test_auroc_perfect_separation():
    # AMB+ all high H_ctx, AMB- all zero → AUROC = 1.0.
    scored = [(1.585, 1), (1.0, 1), (0.0, 0), (0.0, 0)]
    assert p2._auroc(scored) == pytest.approx(1.0)


def test_auroc_tie_is_half():
    # All equal scores across classes → AUROC = 0.5 (mid-ranks).
    scored = [(0.0, 1), (0.0, 1), (0.0, 0), (0.0, 0)]
    assert p2._auroc(scored) == pytest.approx(0.5)


def test_auroc_none_when_one_class_empty():
    assert p2._auroc([(1.0, 1), (0.5, 1)]) is None


def test_analyze_counts_and_danger_quadrant():
    gold_by_id = {
        "a1": {"stratum": gold.STRATUM_AMB_POS, "H_ctx_gold": 1.0, "n_distinct": 2},
        "a2": {"stratum": gold.STRATUM_AMB_POS, "H_ctx_gold": 1.585, "n_distinct": 3},
        "n1": {"stratum": gold.STRATUM_AMB_NEG, "H_ctx_gold": 0.0, "n_distinct": 1},
        "n2": {"stratum": gold.STRATUM_AMB_NEG, "H_ctx_gold": 0.0, "n_distinct": 1},
    }
    results = [
        _row("a1", None, 0.0, 1.585, True, match=True),    # danger-quadrant AMB+
        _row("a2", None, 0.9, 1.0, False, match=False),    # AMB+ but high H_seed
        _row("n1", None, 0.0, 0.0, False),                 # AMB- correct negative
        _row("n2", None, 0.0, 0.0, False),                 # AMB- correct negative
    ]
    a = p2.analyze(results, gold_by_id, tau_s=0.5)
    assert a["strata_counts"] == {gold.STRATUM_AMB_POS: 2,
                                  gold.STRATUM_NON_DISC: 0,
                                  gold.STRATUM_AMB_NEG: 2}
    assert a["flag_confusion"] == {"TP": 1, "FP": 0, "FN": 1, "TN": 2}
    assert a["k0_false_positive_rate"] == pytest.approx(0.0)
    # Danger quadrant: only a1 is low-H_seed & high-H_ctx-self.
    assert a["danger_quadrant"]["n_danger"] == 1
    assert a["danger_quadrant"]["mass_over_AMB_pos"] == pytest.approx(0.5)
    assert a["AUROC_H_ctx_self"] == pytest.approx(1.0)
