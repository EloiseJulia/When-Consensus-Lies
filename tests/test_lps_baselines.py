# constructed by: Claude (Anthropic) family
"""Offline unit tests for the Study-2 confirmatory BASELINE signals.

# Implementer model family: Claude / Anthropic
# Auditor model family: MUST be non-Anthropic (Law 6 — cross-family requirement)

All tests run OFFLINE (no network). They assert:
  1. ``self_consistency_agreement`` / ``_disagreement`` on known label sets.
  2. ``requirements_probing_count`` / ``_flag`` on surfaced-dim lists.
  3. ``token_confidence`` averages ``logit_conf`` (uncertainty = 1 − mean) and
     returns N/A (``available=False``) when the model exposes no logprobs.
  4. ``semantic_entropy_baseline`` reads H_seed off a record.
  5. ``record_baseline_scores`` produces ambiguity-oriented scalars.
  6. ANTI-LEAKAGE (inviolable): the baselines' prompts (token-confidence base
     prompt; requirements-probing surfacing prompt) contain NO gold sentinels.
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
import lps_baselines as baselines  # noqa: E402


# ── Scripted client (records prompts; returns text + optional logit_conf) ─────
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


def _task(prompt="Do the thing.", domain="code_spec") -> Task:
    return Task(
        id="T1", domain=domain, prompt=prompt, latent_spec="spec",
        interpretations=[Interpretation(id="I0", is_target=True, gold_check="g")],
        ambiguity_level=1, key_questions=[], regime="H1_external",
    )


# ── 1. self-consistency ──────────────────────────────────────────────────────

def test_self_consistency_agreement_and_disagreement():
    assert baselines.self_consistency_agreement([]) is None
    assert baselines.self_consistency_disagreement([]) is None
    # All agree → agreement 1.0, disagreement 0.0.
    assert baselines.self_consistency_agreement(["A", "A", "A"]) == 1.0
    assert baselines.self_consistency_disagreement(["A", "A", "A"]) == 0.0
    # Modal fraction 3/5 → agreement 0.6, disagreement 0.4.
    labels = ["A", "A", "A", "B", "C"]
    assert baselines.self_consistency_agreement(labels) == pytest.approx(0.6)
    assert baselines.self_consistency_disagreement(labels) == pytest.approx(0.4)


# ── 2. requirements probing ──────────────────────────────────────────────────

def test_requirements_probing_count_and_flag():
    assert baselines.requirements_probing_count(None) == 0
    assert baselines.requirements_probing_count([]) == 0
    assert baselines.requirements_probing_flag([]) is False
    dims = [{"dimension": "d1", "values": ["a", "b"]},
            {"dimension": "d2", "values": ["x", "y"]}]
    assert baselines.requirements_probing_count(dims) == 2
    assert baselines.requirements_probing_flag(dims) is True


def test_requirements_probing_standalone_uses_surfacing_prompt():
    dims_json = '[{"dimension": "aggregation method", "values": ["sum", "mean"]}]'

    def fn(role, prompt, seed):
        return dims_json if "JSON array" in prompt else "I0"

    client = ScriptedClient(fn)
    out = baselines.requirements_probing(_task(), client, "m")
    assert out["n_dims"] == 1 and out["flag"] is True
    # It issues ONLY the generic surfacing prompt.
    assert any("JSON array" in p for p in client.recorded_prompts)


# ── 3. token confidence ──────────────────────────────────────────────────────

def test_token_confidence_available_averages_logit_conf():
    client = ScriptedClient(lambda r, p, s: "I0", logit_conf=0.8)
    out = baselines.token_confidence(_task(), client, "gpt-4o-mini", k=4, base_seed=0)
    assert out["available"] is True
    assert out["mean_confidence"] == pytest.approx(0.8)
    assert out["uncertainty"] == pytest.approx(0.2)
    assert len(out["logit_confs"]) == 4
    # Replays exactly k generic base-prompt calls.
    assert len(client.recorded_prompts) == 4


def test_token_confidence_na_when_no_logprobs():
    client = ScriptedClient(lambda r, p, s: "I0", logit_conf=None)
    out = baselines.token_confidence(_task(), client, "claude-opus-4.8", k=3)
    assert out["available"] is False
    assert out["mean_confidence"] is None
    assert out["uncertainty"] is None


def test_token_confidence_higher_uncertainty_when_lower_confidence():
    hi = baselines.token_confidence(_task(), ScriptedClient(lambda r, p, s: "x",
                                    logit_conf=0.9), "gpt-4o-mini", k=2)
    lo = baselines.token_confidence(_task(), ScriptedClient(lambda r, p, s: "x",
                                    logit_conf=0.3), "gpt-4o-mini", k=2)
    assert lo["uncertainty"] > hi["uncertainty"]


# ── 4/5. record helpers ──────────────────────────────────────────────────────

def test_semantic_entropy_baseline_reads_h_seed():
    assert baselines.semantic_entropy_baseline({"H_seed": 1.25}) == 1.25
    assert baselines.semantic_entropy_baseline({}) is None


def test_record_baseline_scores_orientation():
    record = {
        "H_seed": 0.9,
        "seed_labels": ["A", "A", "B", "C"],   # disagreement = 0.5
        "surfaced_dims": [{"dimension": "d", "values": ["a", "b"]}],
        "baselines": {"token_uncertainty": 0.4},
    }
    scores = baselines.record_baseline_scores(record)
    assert scores["H_seed"] == 0.9
    assert scores["token_logprob"] == pytest.approx(0.4)
    assert scores["self_consistency"] == pytest.approx(0.5)
    assert scores["requirements_probing"] == pytest.approx(1.0)


def test_record_baseline_scores_token_na():
    record = {"H_seed": 0.0, "seed_labels": ["A"], "surfaced_dims": [],
              "baselines": {"token_uncertainty": None}}
    scores = baselines.record_baseline_scores(record)
    assert scores["token_logprob"] is None


# ── 6. ANTI-LEAKAGE (inviolable) ─────────────────────────────────────────────

_SENTINELS = ["TARGETSENTINEL_I0", "FOILSENTINEL_I1", "GOLDCHECKSENTINEL",
              "KEYQUESTIONSENTINEL", "LATENTSPECSENTINEL", "IXYZLEAK_TARGET",
              "IFOILLEAK"]


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


def _assert_clean(prompts: List[str]):
    for p in prompts:
        for s in _SENTINELS:
            assert s not in p, f"LEAK: sentinel {s!r} found in baseline prompt:\n{p}"


def test_anti_leakage_token_confidence_prompt():
    client = ScriptedClient(lambda r, p, s: "I0", logit_conf=0.5)
    baselines.token_confidence(_leak_task(), client, "gpt-4o-mini", k=3)
    _assert_clean(client.recorded_prompts)
    # Base prompt is the generic task text + answer contract (no gold).
    assert all("aggregate of the inputs" in p for p in client.recorded_prompts)


def test_anti_leakage_requirements_probing_prompt():
    dims_json = '[{"dimension": "aggregation method", "values": ["sum", "mean"]}]'

    def fn(role, prompt, seed):
        return dims_json if "JSON array" in prompt else "I0"

    client = ScriptedClient(fn)
    baselines.requirements_probing(_leak_task(), client, "m")
    _assert_clean(client.recorded_prompts)
