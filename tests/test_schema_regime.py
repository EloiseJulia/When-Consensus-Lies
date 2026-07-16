"""Tests for the owner-approved Amendment 02: Task.regime schema field.

Covers:
- Valid regime values accepted (H1_external, H2_derivable, None/omitted)
- Invalid values strictly rejected (guardrail 1 — golden test)
- JSONL round-trip with regime present (guardrail 2a)
- Backward-compat: old JSONL record missing "regime" key → regime is None (guardrail 2b)
- Existing on-disk bench data still loads and yields regime=None for all records

No network access; all tests are offline.
"""

import json

import pytest

from bench.build import load_tasks, task_from_jsonl, task_to_jsonl
from common.schema import Interpretation, Task, VALID_REGIMES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_task(**overrides) -> Task:
    """Build a minimal valid Task with all required fields."""
    defaults = dict(
        id="t001",
        domain="code_spec",
        prompt="Write a function that does X.",
        latent_spec="Write a function that does X with requirement Y.",
        interpretations=[
            Interpretation(id="I0", is_target=True, gold_check="check_i0"),
            Interpretation(id="I1", is_target=False, gold_check="check_i1"),
        ],
        ambiguity_level=1,
        key_questions=["What about Y?"],
    )
    defaults.update(overrides)
    return Task(**defaults)


# ---------------------------------------------------------------------------
# 1. Valid values accepted
# ---------------------------------------------------------------------------

def test_regime_h1_external_accepted():
    task = _minimal_task(regime="H1_external")
    assert task.regime == "H1_external"


def test_regime_h2_derivable_accepted():
    task = _minimal_task(regime="H2_derivable")
    assert task.regime == "H2_derivable"


def test_regime_none_explicit_accepted():
    task = _minimal_task(regime=None)
    assert task.regime is None


def test_regime_omitted_defaults_to_none():
    """Omitting regime entirely must default to None (backward-compat constructor)."""
    task = Task(
        id="t002",
        domain="policy_qa",
        prompt="Describe the policy.",
        latent_spec="Describe the policy fully.",
        interpretations=[Interpretation(id="I0", is_target=True, gold_check="c0")],
        ambiguity_level=1,
        key_questions=["Q1"],
    )
    assert task.regime is None


def test_valid_regimes_constant():
    """VALID_REGIMES is the single source of truth and contains exactly the three allowed values."""
    assert set(VALID_REGIMES) == {"H1_external", "H2_derivable", None}
    assert len(VALID_REGIMES) == 3


# ---------------------------------------------------------------------------
# 2. Invalid values rejected — guardrail 1 (golden test)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_value", [
    "H1",
    "H2",
    "foo",
    "h1_external",           # wrong case
    "h2_derivable",          # wrong case
    "H1_External",           # mixed case
    "H1_external ",          # trailing space
    " H1_external",          # leading space
    "",                      # empty string
    "excluded",
    "untagged",
    "H1external",            # missing underscore
])
def test_invalid_regime_raises(bad_value):
    """Any value outside VALID_REGIMES must raise ValueError — a typo cannot silently pass."""
    with pytest.raises(ValueError, match="Task.regime must be one of"):
        _minimal_task(regime=bad_value)


# ---------------------------------------------------------------------------
# 3a. JSONL round-trip WITH regime present
# ---------------------------------------------------------------------------

def test_jsonl_roundtrip_with_regime():
    """A Task with regime='H1_external' survives a full JSONL serialize/deserialize cycle."""
    original = _minimal_task(regime="H1_external")
    line = task_to_jsonl(original)

    # The regime key must appear in the JSON output.
    raw = json.loads(line)
    assert raw["regime"] == "H1_external"

    restored = task_from_jsonl(line)

    assert restored.id == original.id
    assert restored.domain == original.domain
    assert restored.prompt == original.prompt
    assert restored.latent_spec == original.latent_spec
    assert restored.ambiguity_level == original.ambiguity_level
    assert restored.key_questions == original.key_questions
    assert restored.regime == "H1_external"
    assert len(restored.interpretations) == len(original.interpretations)
    assert restored.interpretations[0].id == original.interpretations[0].id
    assert restored.interpretations[0].is_target == original.interpretations[0].is_target
    assert restored.interpretations[1].id == original.interpretations[1].id
    assert restored.interpretations[1].is_target == original.interpretations[1].is_target


def test_jsonl_roundtrip_regime_h2():
    """Round-trip also works for H2_derivable."""
    original = _minimal_task(regime="H2_derivable")
    restored = task_from_jsonl(task_to_jsonl(original))
    assert restored.regime == "H2_derivable"


def test_jsonl_roundtrip_regime_none_explicit():
    """Round-trip preserves regime=None when explicitly set."""
    original = _minimal_task(regime=None)
    restored = task_from_jsonl(task_to_jsonl(original))
    assert restored.regime is None


# ---------------------------------------------------------------------------
# 3b. Backward-compat: OLD record (no "regime" key) deserializes to regime=None
# ---------------------------------------------------------------------------

def test_old_jsonl_without_regime_key_backward_compat():
    """An on-disk record that pre-dates Amendment 02 (no 'regime' key) must load
    with regime=None — proves backward-compatibility explicitly."""
    task = _minimal_task(regime="H1_external")
    raw = json.loads(task_to_jsonl(task))

    # Simulate a pre-amendment record by removing the key entirely.
    assert "regime" in raw
    del raw["regime"]
    assert "regime" not in raw

    old_line = json.dumps(raw)
    restored = task_from_jsonl(old_line)

    assert restored.regime is None
    # All other fields still intact.
    assert restored.id == task.id
    assert restored.domain == task.domain
    assert restored.ambiguity_level == task.ambiguity_level
    assert len(restored.interpretations) == len(task.interpretations)


# ---------------------------------------------------------------------------
# 4. Existing bench data still loads and yields regime=None
# ---------------------------------------------------------------------------

import os

BENCH_DATA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "bench", "data"
)

@pytest.mark.parametrize("filename", [
    "policy_qa.jsonl",
])
def test_existing_bench_data_loads(filename):
    """Pre-amendment on-disk benchmark files must still load (no 'regime' key in them)
    and every Task must have regime is None.
    Note: code_spec.jsonl and data_analysis.jsonl have been reconstructed under
    Amendment 01 (target/default reversal) and now carry regime values — they are
    tested separately in test_code_spec.py / test_data_analysis.py::test_task_regime_valid."""
    path = os.path.join(BENCH_DATA_DIR, filename)
    if not os.path.exists(path):
        pytest.skip(f"Bench data file not found: {path}")

    tasks = load_tasks(path)
    assert len(tasks) > 0, f"Expected at least one task in {filename}"
    for task in tasks:
        assert task.regime is None, (
            f"Pre-amendment task {task.id!r} in {filename} should have regime=None, "
            f"got {task.regime!r}"
        )
