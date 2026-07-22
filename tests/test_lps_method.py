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
    # All seed-resample prompts are exactly task.prompt (no added text).
    assert client.recorded_prompts == ["Do the thing."] * 4


def test_H_seed_degenerate_zero_entropy():
    client = ScriptedClient(lambda role, prompt, seed: "I0")
    res = lps.H_seed(_dummy_task(), client, "m", k=5, base_seed=10)
    assert res["H_seed"] == 0.0


def test_H_ctx_per_dimension_entropy_and_argmax():
    # dim A: values→[I0,I0] (0 bits); dim B: values→[I0,I1] (1 bit) → argmax=B.
    def fn(role, prompt, seed):
        return "I1" if "B_VALUE_2" in prompt else "I0"
    client = ScriptedClient(fn)
    dims = [
        {"dimension": "dimA", "values": ["A_VALUE_1", "A_VALUE_2"]},
        {"dimension": "dimB", "values": ["B_VALUE_1", "B_VALUE_2"]},
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


# ── axis_match heuristic (reporting-only) ────────────────────────────────────

def test_axis_match_positive_and_negative():
    kq = ["When does the fiscal year start (which month maps to quarter 1)?"]
    assert lps.axis_match("fiscal year start month", kq) is True
    assert lps.axis_match("output color theme", kq) is False
    assert lps.axis_match("", kq) is False
    assert lps.axis_match("anything", []) is False
