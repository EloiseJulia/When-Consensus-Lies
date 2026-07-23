# constructed by: Claude (Anthropic) family
"""Offline unit tests for the LPS method + pilot (Study 2).

# Implementer model family: Claude / Anthropic
# Auditor model family: MUST be non-Anthropic (Law 6 — cross-family requirement)

All tests run OFFLINE (no network). They assert:
  1. ``semantic_entropy`` returns correct BITS on known label distributions.
  2. ``H_seed`` / ``H_ctx`` compute the correct entropy given a scripted client
     + stubbed labeler (labels controlled exactly).
  3. ``surface_assumptions`` parses JSON (incl. fenced) into dims.
  4. ``lps_pilot --dry-run`` enumerates the 9-item x N-model grid with no network.
  5. ANTI-LEAKAGE (inviolable): with a task carrying distinctive gold sentinels,
     NONE of the method's prompts (assumption-surfacing, seed-resample, pinning)
     contains any target/foil/gold_check/interp.id/key_questions/latent_spec text.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
for _p in (str(_REPO_ROOT), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common.schema import Task, Interpretation  # noqa: E402

import lps_method as lps  # noqa: E402
import lps_pilot  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Scripted client — returns a caller-controlled text; records every prompt.
# ─────────────────────────────────────────────────────────────────────────────
class ScriptedClient:
    """Offline client. ``fn(role, prompt, seed)`` -> text. Records all prompts."""

    def __init__(self, fn):
        self._fn = fn
        self.recorded_prompts: List[str] = []

    def complete(self, role, prompt, seed=None, model=None, temperature=None, **kw):
        self.recorded_prompts.append(prompt)
        text = self._fn(role, prompt, seed)
        return SimpleNamespace(text=text, model=model or "mock", tokens_in=0,
                               tokens_out=0, cost_usd=0.0, logit_conf=None)


def _identity_labeler(run, task):
    """Stub frozen labeler: the label IS the raw output (exact control in tests)."""
    return run.output


@pytest.fixture(autouse=True)
def _stub_labeler(monkeypatch):
    """Make ``_label_answer`` return the raw output verbatim as the label."""
    monkeypatch.setattr(lps, "label_run", _identity_labeler)


def _dummy_task(prompt="Do the thing.", domain="code_spec") -> Task:
    return Task(
        id="T1", domain=domain, prompt=prompt, latent_spec="spec",
        interpretations=[Interpretation(id="I0", is_target=True, gold_check="g")],
        ambiguity_level=1, key_questions=[], regime="H1_external",
    )


# ── 1. semantic_entropy correctness (BITS) ───────────────────────────────────

def test_semantic_entropy_known_distributions():
    assert lps.semantic_entropy([]) == 0.0
    assert lps.semantic_entropy(["I0"]) == 0.0
    assert lps.semantic_entropy(["I0", "I0", "I0"]) == 0.0
    # 50/50 over two clusters = 1 bit.
    assert lps.semantic_entropy(["I0", "I1"]) == pytest.approx(1.0)
    # uniform over 4 clusters = 2 bits.
    assert lps.semantic_entropy(["I0", "I1", "I2", "I_perp"]) == pytest.approx(2.0)
    # 3:1 split = 0.8112781 bits.
    expected = -(0.75 * math.log2(0.75) + 0.25 * math.log2(0.25))
    assert lps.semantic_entropy(["I0", "I0", "I0", "I1"]) == pytest.approx(expected)


# ── 2. H_seed / H_ctx entropy over controlled labels ─────────────────────────

def test_H_seed_entropy_from_scripted_labels():
    # k=4 resamples → labels I0,I0,I1,I1 (by seed offset) → 1 bit.
    seq = {0: "I0", 1: "I0", 2: "I1", 3: "I1"}
    client = ScriptedClient(lambda role, prompt, seed: seq[seed])
    res = lps.H_seed(_dummy_task(), client, "m", k=4, temperature=0.7, base_seed=0)
    assert res["labels"] == ["I0", "I0", "I1", "I1"]
    assert res["H_seed"] == pytest.approx(1.0)
    # Every seed-resample prompt = task.prompt + the executable answer contract
    # (coverage fix); the contract carries no gold and is identical across k.
    assert len(client.recorded_prompts) == 4
    for p in client.recorded_prompts:
        assert p.startswith("Do the thing.")
        assert lps._answer_contract("code_spec") in p
    assert len(set(client.recorded_prompts)) == 1  # identical across resamples


def test_H_seed_degenerate_zero_entropy():
    client = ScriptedClient(lambda role, prompt, seed: "I0")
    res = lps.H_seed(_dummy_task(), client, "m", k=5, base_seed=10)
    assert res["H_seed"] == 0.0


def _sig_by_text(monkeypatch):
    """Monkeypatch answer_signature so the signature IS the returned text
    (except the literal 'BROKEN', which is treated as unparseable → None)."""
    monkeypatch.setattr(lps, "answer_signature",
                        lambda task, text: None if text == "BROKEN" else text)


def test_H_ctx_mutual_equiv_distinct_results_high(monkeypatch):
    # Refinement: three pins yield three DIFFERENT results that disagree with
    # each other → 3 clusters → H_ctx = log2(3), even though NONE matches gold
    # (the signatures R1/R2/R3 are arbitrary, never compared to a gold answer).
    _sig_by_text(monkeypatch)

    def fn(role, prompt, seed):
        if "V2" in prompt:
            return "R2"
        if "V3" in prompt:
            return "R3"
        return "R1"
    client = ScriptedClient(fn)
    dims = [{"dimension": "typical measure", "values": ["V1_mean", "V2_median", "V3_mode"]}]
    res = lps.H_ctx(_dummy_task(), client, "m", dims, base_seed=0)
    d = res["per_dim"][0]
    assert d["n_parseable"] == 3
    assert d["n_clusters"] == 3
    assert d["H_ctx"] == pytest.approx(math.log2(3))
    assert res["flagged_dimension"] == "typical measure"


def test_H_ctx_mutual_equiv_same_result_zero(monkeypatch):
    # An in-prompt-fixed / nonexistent dimension: every pin gives the SAME result
    # → 1 cluster → H_ctx = 0 (no false flag).
    _sig_by_text(monkeypatch)
    client = ScriptedClient(lambda role, prompt, seed: "SAME")
    dims = [{"dimension": "irrelevant", "values": ["a", "b", "c"]}]
    res = lps.H_ctx(_dummy_task(), client, "m", dims, base_seed=0)
    d = res["per_dim"][0]
    assert d["n_parseable"] == 3
    assert d["n_clusters"] == 1
    assert d["H_ctx"] == pytest.approx(0.0)
    assert res["flagged_dimension"] is None


def test_H_ctx_excludes_unrunnable_pins(monkeypatch):
    # A broken/unrunnable pin (e.g. language=Java breaking the harness) is EXCLUDED
    # — it does not inflate H_ctx as its own singleton cluster. Here two pins are
    # BROKEN → only 1 parseable remains → H_ctx = 0.
    _sig_by_text(monkeypatch)

    def fn(role, prompt, seed):
        return "R1" if "V1" in prompt else "BROKEN"
    client = ScriptedClient(fn)
    dims = [{"dimension": "language", "values": ["V1_py", "V2_java", "V3_ruby"]}]
    res = lps.H_ctx(_dummy_task(), client, "m", dims, base_seed=0)
    d = res["per_dim"][0]
    assert d["signatures"] == ["R1", None, None]
    assert d["n_parseable"] == 1
    assert d["H_ctx"] == pytest.approx(0.0)   # <2 parseable → 0, no singleton inflation
    assert res["flagged_dimension"] is None


def test_H_ctx_excludes_unrunnable_keeps_genuine_switch(monkeypatch):
    # One BROKEN pin excluded, two remaining pins DISAGREE → genuine switch = 1 bit.
    _sig_by_text(monkeypatch)

    def fn(role, prompt, seed):
        if "V1" in prompt:
            return "RA"
        if "V2" in prompt:
            return "RB"
        return "BROKEN"
    client = ScriptedClient(fn)
    dims = [{"dimension": "threshold", "values": ["V1", "V2", "V3_broken"]}]
    res = lps.H_ctx(_dummy_task(), client, "m", dims, base_seed=0)
    d = res["per_dim"][0]
    assert d["n_parseable"] == 2
    assert d["H_ctx"] == pytest.approx(1.0)
    assert res["flagged_dimension"] == "threshold"


def test_H_ctx_argmax_across_dims(monkeypatch):
    # dim A: all same (0 bits); dim B: two distinct (1 bit) → argmax = B.
    _sig_by_text(monkeypatch)

    def fn(role, prompt, seed):
        if "dimB" in prompt:
            return "RB2" if "BV2" in prompt else "RB1"
        return "RA"
    client = ScriptedClient(fn)
    dims = [
        {"dimension": "dimA", "values": ["AV1", "AV2"]},
        {"dimension": "dimB", "values": ["BV1", "BV2"]},
    ]
    res = lps.H_ctx(_dummy_task(), client, "m", dims, base_seed=0)
    per = {d["dimension"]: d["H_ctx"] for d in res["per_dim"]}
    assert per["dimA"] == pytest.approx(0.0)
    assert per["dimB"] == pytest.approx(1.0)
    assert res["H_ctx_max"] == pytest.approx(1.0)
    assert res["flagged_dimension"] == "dimB"


def test_H_ctx_empty_dims():
    client = ScriptedClient(lambda role, prompt, seed: "I0")
    res = lps.H_ctx(_dummy_task(), client, "m", [], base_seed=0)
    assert res["H_ctx_max"] == 0.0
    assert res["flagged_dimension"] is None


# ── 2b. Gold-free answer_signature executor (real, deterministic) ────────────

def _fenced(code: str) -> str:
    return f"```python\n{code}\n```"


def _real_task(task_id: str):
    import registered_run as rr
    tasks = {t.id: t for t in rr.load_tasks()}
    return tasks[task_id]


def test_answer_signature_code_execution_distinguishes_behaviour():
    # Gold-FREE: two code answers with DIFFERENT behaviour on the task's own inputs
    # get DIFFERENT signatures; identical code gets the SAME signature. Never
    # compared to the gold answer.
    task = _real_task("code_quarter_001_k0")  # entrypoint: quarter(month)
    calendar = _fenced("def quarter(month):\n    return (month - 1) // 3 + 1")
    fiscal = _fenced(
        "def quarter(month):\n    return ((month - 4) % 12) // 3 + 1"
    )
    sig_cal = lps.answer_signature(task, calendar)
    sig_fis = lps.answer_signature(task, fiscal)
    sig_cal2 = lps.answer_signature(task, calendar)
    assert sig_cal is not None and sig_fis is not None
    assert sig_cal != sig_fis          # different behaviour → different clusters
    assert sig_cal == sig_cal2         # deterministic


def test_answer_signature_code_unparseable_returns_none():
    task = _real_task("code_quarter_001_k0")
    assert lps.answer_signature(task, "I cannot write that code.") is None


def test_answer_signature_numeric_cent_tolerance():
    task = _real_task("policy_overtime_001_k0")
    # The frozen extractor accepts only the structured contract (JSON 'amount'
    # or a 'FINAL ANSWER: $...' money line); answer_signature reuses it gold-free.
    assert lps.answer_signature(task, '{"amount": 123.45}') == "num:12345"
    assert lps.answer_signature(task, '{"amount": 123.45}') == \
        lps.answer_signature(task, 'FINAL ANSWER: $123.45')
    assert lps.answer_signature(task, '{"amount": 99.99}') != \
        lps.answer_signature(task, '{"amount": 123.45}')
    assert lps.answer_signature(task, "no number here") is None

def test_is_format_dim_filters_language_and_tooling():
    assert lps._is_format_dim({"dimension": "programming language",
                               "values": ["Python", "Java"]}) is True
    assert lps._is_format_dim({"dimension": "library", "values": ["pandas", "numpy"]}) is True
    assert lps._is_format_dim({"dimension": "output encoding",
                               "values": ["utf-8", "ascii"]}) is True
    # Values are all language names even if the dim name is neutral.
    assert lps._is_format_dim({"dimension": "impl", "values": ["python", "java"]}) is True
    # Genuine answer-semantic axes must NOT be filtered.
    assert lps._is_format_dim({"dimension": "fiscal year start",
                               "values": ["January", "April"]}) is False
    assert lps._is_format_dim({"dimension": "date format convention",
                               "values": ["ISO 8601", "US MM/DD/YYYY"]}) is False
    assert lps._is_format_dim({"dimension": "rounding standard",
                               "values": ["half-up", "half-even"]}) is False


def test_surface_assumptions_backstop_drops_format_dims():
    payload = (
        '[{"dimension": "active user threshold", "values": ["7 days", "30 days"]},'
        ' {"dimension": "programming language", "values": ["Python", "Java"]}]'
    )
    client = ScriptedClient(lambda role, prompt, seed: payload)
    kept, dropped = lps.surface_assumptions_detailed(_dummy_task(), client, "m")
    assert [d["dimension"] for d in kept] == ["active user threshold"]
    assert [d["dimension"] for d in dropped] == ["programming language"]
    # Default surface_assumptions applies the filter.
    assert [d["dimension"] for d in lps.surface_assumptions(_dummy_task(), client, "m")] \
        == ["active user threshold"]


# ── 3. Assumption parsing ────────────────────────────────────────────────────

def test_surface_assumptions_parses_fenced_json():
    payload = (
        "Here you go:\n```json\n"
        '[{"dimension": "fiscal year start", "values": ["January", "April"]},'
        ' {"dimension": "rounding", "values": ["half-up", "half-even"]}]'
        "\n```\n"
    )
    client = ScriptedClient(lambda role, prompt, seed: payload)
    dims = lps.surface_assumptions(_dummy_task(), client, "m")
    assert [d["dimension"] for d in dims] == ["fiscal year start", "rounding"]
    assert dims[0]["values"] == ["January", "April"]


def test_surface_assumptions_drops_malformed_and_single_value():
    payload = (
        '[{"dimension": "ok", "values": ["a", "b"]},'
        ' {"dimension": "toofew", "values": ["only"]},'
        ' {"bad": "entry"}]'
    )
    client = ScriptedClient(lambda role, prompt, seed: payload)
    dims = lps.surface_assumptions(_dummy_task(), client, "m")
    assert [d["dimension"] for d in dims] == ["ok"]


def test_surface_assumptions_no_json_returns_empty():
    client = ScriptedClient(lambda role, prompt, seed: "I cannot help with that.")
    assert lps.surface_assumptions(_dummy_task(), client, "m") == []


# ── 4. Dry-run enumeration (no network) ──────────────────────────────────────

def test_pilot_dry_run_enumerates_grid():
    import registered_run as rr
    from common.config import load_config

    tasks = rr.load_tasks()
    cfg = load_config()
    res = lps_pilot.run(tasks, cfg, models=["m1", "m2"], dry_run=True)
    assert res["status"] == "dry_run"
    # 9 pre-specified items x 2 models = 18 jobs.
    assert res["total"] == 9 * 2
    assert len(res["jobs"]) == 18
    ids = {j["task_id"] for j in res["jobs"]}
    assert ids == set(lps_pilot.PILOT_ITEM_IDS)


def test_pilot_dry_run_default_models():
    import registered_run as rr
    from common.config import load_config

    res = lps_pilot.run(rr.load_tasks(), load_config(), dry_run=True)
    assert res["total"] == 9 * len(lps_pilot.PILOT_MODELS)


# ── 5. ANTI-LEAKAGE (inviolable) ─────────────────────────────────────────────

_SENTINELS = [
    "TARGETSENTINEL_I0",
    "FOILSENTINEL_I1",
    "GOLDCHECKSENTINEL",
    "KEYQUESTIONSENTINEL",
    "LATENTSPECSENTINEL",
    "IXYZLEAK_TARGET",
    "IFOILLEAK",
]


def _leak_task() -> Task:
    """Task whose OFF-LIMITS fields carry distinctive sentinels; prompt is clean."""
    return Task(
        id="LEAK_001",
        domain="code_spec",
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


def _assert_no_sentinels(prompts: List[str]):
    off_limits = _SENTINELS + [
        "LATENTSPECSENTINEL", "GOLDCHECKSENTINEL", "KEYQUESTIONSENTINEL",
        "IXYZLEAK_TARGET", "IFOILLEAK",
    ]
    for p in prompts:
        for s in off_limits:
            assert s not in p, f"LEAK: sentinel {s!r} found in prompt:\n{p}"


def test_anti_leakage_all_stages(monkeypatch):
    # Labeler stubbed by the autouse fixture; make surfacing return real dims so
    # the pinning stage actually emits prompts to inspect.
    dims_json = (
        '[{"dimension": "aggregation method", "values": ["sum", "mean"]}]'
    )

    def fn(role, prompt, seed):
        # Assumption-surfacing prompt is the long templated one → return JSON.
        if "JSON array" in prompt:
            return dims_json
        return "I0"

    client = ScriptedClient(fn)
    task = _leak_task()

    # Run every stage that emits a prompt.
    lps.H_seed(task, client, "m", k=3, base_seed=0)
    dims = lps.surface_assumptions(task, client, "m")
    assert dims and dims[0]["dimension"] == "aggregation method"
    lps.H_ctx(task, client, "m", dims, base_seed=0)

    _assert_no_sentinels(client.recorded_prompts)
    # Sanity: pinning prompts DID include the model's own value tokens.
    assert any("sum" in p and "aggregation method" in p for p in client.recorded_prompts)


def test_anti_leakage_via_lpp_detect(monkeypatch):
    dims_json = '[{"dimension": "rounding rule", "values": ["up", "down"]}]'

    def fn(role, prompt, seed):
        if "JSON array" in prompt:
            return dims_json
        return "I0"

    client = ScriptedClient(fn)
    task = _leak_task()
    res = lps.lpp_detect(task, client, "m", k=3, base_seed=0)
    assert "H_seed" in res and "H_ctx_max" in res
    _assert_no_sentinels(client.recorded_prompts)


# ── 2c. Executable answer contract (coverage fix) ────────────────────────────

def test_answer_contract_stdlib_clause_for_code_domains():
    for dom in ("code_spec", "data_analysis"):
        c = lps._answer_contract(dom)
        assert "```python" in c
        assert "standard library" in c.lower()
    # policy_qa gets the money/JSON contract, no stdlib clause.
    pol = lps._answer_contract("policy_qa")
    assert "FINAL ANSWER" in pol
    assert "standard library" not in pol.lower()


def test_contract_appended_to_seed_and_pinning_prompts():
    def fn(role, prompt, seed):
        if "JSON array" in prompt:
            return '[{"dimension": "threshold", "values": ["v1", "v2"]}]'
        return "I0"
    client = ScriptedClient(fn)
    task = _dummy_task(domain="code_spec")
    contract = lps._answer_contract("code_spec")

    lps.H_seed(task, client, "m", k=2, base_seed=0)
    seed_prompts = list(client.recorded_prompts)
    assert seed_prompts and all(contract in p for p in seed_prompts)

    client.recorded_prompts.clear()
    dims = lps.surface_assumptions(task, client, "m")
    lps.H_ctx(task, client, "m", dims, base_seed=0)
    pin_prompts = [p for p in client.recorded_prompts if "assume" in p.lower()]
    assert pin_prompts and all(contract in p for p in pin_prompts)


# ── 2d. PRIMARY item-level flag logic (H_ctx>0 AND H_seed low) ───────────────

def _detect_client(pin_map, seed_text_fn):
    """Client for lpp_detect: JSON dims for surfacing, pin_map[value] for pins,
    seed_text_fn(seed) for seed-resamples."""
    def fn(role, prompt, seed):
        if "JSON array" in prompt:
            return '[{"dimension": "threshold", "values": ["V1", "V2"]}]'
        if "assume" in prompt.lower():
            return pin_map["V2"] if "V2" in prompt else pin_map["V1"]
        return seed_text_fn(seed)
    return ScriptedClient(fn)


def test_item_flag_true_when_hctx_positive_and_hseed_low(monkeypatch):
    _sig_by_text(monkeypatch)
    # Distinct pin results → H_ctx>0; constant seed answer → H_seed=0 → FLAG.
    client = _detect_client({"V1": "RA", "V2": "RB"}, lambda seed: "SAME")
    res = lps.lpp_detect(_dummy_task(), client, "m", k=5, base_seed=0)
    assert res["H_ctx_max"] > 0.0
    assert res["H_seed"] == pytest.approx(0.0)
    assert res["is_flagged"] is True
    assert res["flagged_dimension"] == "threshold"


def test_item_flag_false_when_hseed_high(monkeypatch):
    _sig_by_text(monkeypatch)
    # Distinct pin results → H_ctx>0, BUT seed answer alternates → H_seed high →
    # NOT the danger quadrant (openly uncertain), so item is NOT flagged.
    client = _detect_client({"V1": "RA", "V2": "RB"}, lambda seed: f"S{seed % 2}")
    res = lps.lpp_detect(_dummy_task(), client, "m", k=5, base_seed=0, tau_s=0.5)
    assert res["H_ctx_max"] > 0.0
    assert res["H_seed"] > 0.5
    assert res["is_flagged"] is False


def test_item_flag_false_when_hctx_zero(monkeypatch):
    _sig_by_text(monkeypatch)
    # Pins all agree → H_ctx=0 → not flagged even though H_seed is low.
    client = _detect_client({"V1": "SAME", "V2": "SAME"}, lambda seed: "SAME")
    res = lps.lpp_detect(_dummy_task(), client, "m", k=5, base_seed=0)
    assert res["H_ctx_max"] == pytest.approx(0.0)
    assert res["is_flagged"] is False


def test_lpp_detect_reports_coverage_counts(monkeypatch):
    # V1 parseable, V2 unparseable (BROKEN) → coverage 1/2 for the one dim.
    _sig_by_text(monkeypatch)
    client = _detect_client({"V1": "RA", "V2": "BROKEN"}, lambda seed: "SAME")
    res = lps.lpp_detect(_dummy_task(), client, "m", k=3, base_seed=0)
    assert res["n_pins_total"] == 2
    assert res["n_parseable_total"] == 1


# ── axis_match heuristic (reporting-only) ────────────────────────────────────

def test_axis_match_positive_and_negative():
    kq = ["When does the fiscal year start (which month maps to quarter 1)?"]
    assert lps.axis_match("fiscal year start month", kq) is True
    assert lps.axis_match("output color theme", kq) is False
    assert lps.axis_match("", kq) is False
    assert lps.axis_match("anything", []) is False


# ── Auditor Issue 1 (final): tolerance-aware PAIRWISE executable clustering ───

def test_code_results_equal_mirrors_harness_tolerance():
    # Elementwise pairwise equality uses the frozen harness _compare: within
    # FLOAT_TOL == equal; bool stays type-distinct; int/float unified by value.
    assert lps._code_results_equal("code_spec", [0.3], [0.1 + 0.2]) is True
    assert lps._code_results_equal("code_spec", [3], [3.0]) is True
    assert lps._code_results_equal("code_spec", [True], [1]) is False
    assert lps._code_results_equal("code_spec", [0.3], [0.31]) is False
    # Different lengths / non-lists fall back to exact equality.
    assert lps._code_results_equal("code_spec", [1, 2], [1]) is False


def test_pairwise_clustering_tolerance_boundary_vs_rounding():
    # THE boundary case the auditor called out: 4.9e-10 and 1.4e-9 differ by
    # 9.1e-10 < FLOAT_TOL (1e-9) → the frozen harness says EQUAL, so they MUST land
    # in ONE cluster under the pairwise rule. Rounding to 9 digits would have split
    # them (round(4.9e-10, 9) == 0.0 but round(1.4e-9, 9) == 1e-9) → 2 clusters.
    a, b = 4.9e-10, 1.4e-9
    assert abs(a - b) < 1e-9                       # harness-equal
    assert round(a, 9) != round(b, 9)              # rounding WOULD have split them
    # Pairwise / union-find clustering keeps them together → 1 cluster, H_ctx = 0.
    h, n = lps.cluster_entropy(
        [[a], [b]], lambda x, y: lps._code_results_equal("code_spec", x, y)
    )
    assert n == 1
    assert h == pytest.approx(0.0)
    # A genuinely different value forms its own cluster (2 clusters, 1 bit).
    h2, n2 = lps.cluster_entropy(
        [[a], [b], [5.0]], lambda x, y: lps._code_results_equal("code_spec", x, y)
    )
    assert n2 == 2
    assert h2 == pytest.approx(-(2 / 3) * math.log2(2 / 3) - (1 / 3) * math.log2(1 / 3))


def test_cluster_entropy_non_transitive_chain_merges():
    # Tolerance equality is NON-TRANSITIVE: a~b and b~c pairwise, but a and c are
    # NOT within tolerance. Connected-components (union-find) still merges all three
    # into ONE cluster — the principled behaviour a hashable signature cannot give.
    a, b, c = [0.0], [0.9e-9], [1.8e-9]
    assert lps._code_results_equal("code_spec", a, b) is True
    assert lps._code_results_equal("code_spec", b, c) is True
    assert lps._code_results_equal("code_spec", a, c) is False  # 1.8e-9 > FLOAT_TOL
    h, n = lps.cluster_entropy(
        [a, b, c], lambda x, y: lps._code_results_equal("code_spec", x, y)
    )
    assert n == 1
    assert h == pytest.approx(0.0)


# ── Auditor Issue 2: configured tau actually suppresses borderline flags ──────

def test_tau_suppresses_borderline_flag(monkeypatch):
    _sig_by_text(monkeypatch)
    # Two distinct pin results → 2 clusters over 2 pins → H_ctx = 1.0 bit.
    # H_seed = 0 (constant reseed) → danger quadrant.
    client = _detect_client({"V1": "RA", "V2": "RB"}, lambda seed: "SAME")
    # tau = 0.0 (pilot operating point): borderline H_ctx=1.0 IS flagged.
    res0 = lps.lpp_detect(_dummy_task(), client, "m", k=5, base_seed=0, tau=0.0)
    assert res0["H_ctx_max"] == pytest.approx(1.0)
    assert res0["is_flagged"] is True
    # Raise tau above the borderline H_ctx → the SAME item is now suppressed.
    res_hi = lps.lpp_detect(_dummy_task(), client, "m", k=5, base_seed=0, tau=1.5)
    assert res_hi["H_ctx_max"] == pytest.approx(1.0)
    assert res_hi["is_flagged"] is False


# ── Auditor Issue 3: checkpoint fingerprint prevents silent incompatible reuse ─

def _fp_checkpoint_paths():
    cp = _REPO_ROOT / ".run_partitions" / "cp_lps_test_fingerprint.jsonl"
    cache = _REPO_ROOT / ".llm_cache_lps_test_fingerprint"
    return cp, cache


@pytest.fixture()
def _fp_checkpoint():
    cp, cache = _fp_checkpoint_paths()
    cp.parent.mkdir(parents=True, exist_ok=True)
    if cp.exists():
        cp.unlink()
    yield cp, cache
    if cp.exists():
        cp.unlink()


def test_resume_refuses_incompatible_fingerprint(monkeypatch, _fp_checkpoint):
    _sig_by_text(monkeypatch)
    cp, cache = _fp_checkpoint
    task = _dummy_task()
    client = _detect_client({"V1": "RA", "V2": "RB"}, lambda seed: "SAME")

    # Seed a checkpoint recorded under k=5.
    fp5 = lps_pilot.run_fingerprint(models=["m"], k=5, base_seed=0, tau=0.0, tau_s=0.5)
    with cp.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"_header": True, "_fingerprint": fp5}) + "\n")
        fh.write(json.dumps({"task_id": task.id, "model": "m",
                             "_fingerprint": fp5}) + "\n")

    # Re-running with a DIFFERENT k must refuse to reuse the old record.
    with pytest.raises(RuntimeError, match="fingerprint mismatch"):
        lps_pilot.run(
            [task], {}, models=["m"], checkpoint_path=str(cp), cache_dir=str(cache),
            k=3, base_seed=0, tau=0.0, tau_s=0.5, select_pilot=False,
            _client_override=client,
        )


def test_resume_reuses_matching_fingerprint(monkeypatch, _fp_checkpoint):
    _sig_by_text(monkeypatch)
    cp, cache = _fp_checkpoint
    task = _dummy_task()
    client = _detect_client({"V1": "RA", "V2": "RB"}, lambda seed: "SAME")

    fp5 = lps_pilot.run_fingerprint(models=["m"], k=5, base_seed=0, tau=0.0, tau_s=0.5)
    with cp.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"_header": True, "_fingerprint": fp5}) + "\n")
        fh.write(json.dumps({"task_id": task.id, "model": "m",
                             "_fingerprint": fp5}) + "\n")

    # Same fingerprint (k=5) → the record is reused (skipped), no error, no rerun.
    res = lps_pilot.run(
        [task], {}, models=["m"], checkpoint_path=str(cp), cache_dir=str(cache),
        k=5, base_seed=0, tau=0.0, tau_s=0.5, select_pilot=False,
        _client_override=client,
    )
    assert res["status"] == "ok"
    assert res["skipped"] == 1
    assert res["completed"] == 0


def test_method_version_is_v5_pairwise():
    # The clustering ALGORITHM is tolerance-aware pairwise / union-find (v5). The
    # version string must reflect that so a pre-pairwise (v4) checkpoint is refused.
    assert lps.METHOD_VERSION == "lps-2026-07-23-v5-pairwise-tol"
    fp = lps_pilot.run_fingerprint(models=["m"], k=5, base_seed=0, tau=0.0, tau_s=0.5)
    assert fp["method_version"] == "lps-2026-07-23-v5-pairwise-tol"


def test_resume_refuses_old_method_version(monkeypatch, _fp_checkpoint):
    _sig_by_text(monkeypatch)
    cp, cache = _fp_checkpoint
    task = _dummy_task()
    client = _detect_client({"V1": "RA", "V2": "RB"}, lambda seed: "SAME")

    # A checkpoint written by the OLD (pre-pairwise) method — same k/seed/tau, but a
    # stale method_version. It must be refused, not silently reused.
    old_fp = lps_pilot.run_fingerprint(models=["m"], k=5, base_seed=0, tau=0.0, tau_s=0.5)
    old_fp = dict(old_fp)
    old_fp["method_version"] = "lps-2026-07-23-v4-tol-equiv"
    with cp.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"_header": True, "_fingerprint": old_fp}) + "\n")
        fh.write(json.dumps({"task_id": task.id, "model": "m",
                             "_fingerprint": old_fp}) + "\n")

    with pytest.raises(RuntimeError, match="fingerprint mismatch"):
        lps_pilot.run(
            [task], {}, models=["m"], checkpoint_path=str(cp), cache_dir=str(cache),
            k=5, base_seed=0, tau=0.0, tau_s=0.5, select_pilot=False,
            _client_override=client,
        )

