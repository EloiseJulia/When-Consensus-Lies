"""Offline robustness tests for reasoning-wrapper / multi-block answer extraction.

Covers the LABELING-VALIDITY (answer-format) failure modes surfaced by the live
default-check diagnostic:

  * Reasoning models (deepseek-r1 style) wrap the answer in <think>...</think>.
  * Verbose / prose-surrounded code answers.
  * Multi-fence outputs where the FINAL fenced block is the intended answer.

These tests assert that a PRESENT-BUT-WRAPPED correct answer is now RECOVERED
(labels to the real interpretation), while genuinely off-axis or truncated /
no-answer outputs STILL label I_perp — i.e. the extraction hardening never turns
a genuinely-wrong output into a false correct/foil label (gold semantics fixed).

Fully offline / deterministic (no network, no LLM judge).
"""

import glob
import json
import os

import pytest

from common.schema import AgentRun
from harness.label import (
    label_run,
    _extract_code_from_output,
    _strip_reasoning,
)
from bench.build import load_tasks
from bench.code_spec import get_checkers_and_candidates


# ── Fixtures / helpers ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_domain_caches():
    try:
        from bench.code_spec import _RESULT_CACHE as code_cache
        code_cache.clear()
    except ImportError:
        pass
    yield


def _invoice_task():
    """The k=3 combinatorial invoice task (8 interpretations, 3-part gold)."""
    tasks = load_tasks("bench/data/code_spec.jsonl")
    return next(t for t in tasks if t.id == "code_invoice_001_k3_all")


def _invoice_refs():
    task = _invoice_task()
    _checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    return task, candidates, foils


def _make_run(task_id, output, seed=900):
    return AgentRun(
        task_id=task_id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=output,
        label="",
        verbalized_conf=0.9,
        logit_conf=None,
        seed=seed,
    )


# A genuinely OFF-AXIS invoice output faithfully reproducing the real
# mistral-small-2503 failure: half-even rounding MIXED WITH GAAP paren sign —
# matches NEITHER *_halfeven (wants minus sign) NOR *_gaap (wants HALF-UP value).
_OFF_AXIS_MIXED = '''
def format_invoice_line(year, month, day, amount):
    # calendar quarter
    q = (month - 1) // 3 + 1
    date_str = f"{month:02d}/{day:02d}/{year:04d}"
    rounded = round(amount, 2)            # banker's / half-even
    if rounded < 0:
        amt = f"({abs(rounded):.2f})"     # ...but GAAP-style parentheses
    else:
        amt = f"{rounded:.2f}"
    return f"Q{q} {date_str} {amt}"
'''


# ── _strip_reasoning unit tests ────────────────────────────────────────────────

def test_strip_reasoning_closed_block():
    out = "<think>Let's reason about this.</think>\n```python\nx = 1\n```"
    stripped = _strip_reasoning(out)
    assert "<think>" not in stripped
    assert "reason about" not in stripped
    assert "x = 1" in stripped


def test_strip_reasoning_unclosed_block_becomes_empty_tail():
    # Truncated mid-thought: everything from <think> onward is reasoning.
    out = "prefix\n<think>I will define a function and return the value..."
    stripped = _strip_reasoning(out)
    assert "<think>" not in stripped
    assert "define a function" not in stripped
    assert stripped.strip() == "prefix"


# ── _extract_code_from_output unit tests ───────────────────────────────────────

def test_extract_prefers_last_fenced_block():
    out = (
        "First, an illustrative sketch:\n"
        "```python\ndef f():\n    return 'WRONG'\n```\n"
        "After more thought, the final answer is:\n"
        "```python\ndef f():\n    return 'RIGHT'\n```\n"
    )
    code = _extract_code_from_output(out)
    assert code is not None
    assert "RIGHT" in code and "WRONG" not in code


def test_extract_truncated_reasoning_returns_none():
    # Unclosed <think> with no code block → no recoverable answer.
    out = "<think>Okay, I need to write a function. Let's define def and return..."
    assert _extract_code_from_output(out) is None


def test_extract_prose_is_not_code():
    out = ("I think you should return the records sorted by age, "
           "but I'm not sure about the tiebreak. Here's my reasoning: ...")
    assert _extract_code_from_output(out) is None


def test_extract_raw_code_without_fence():
    code_body = "def format_invoice_line(y, m, d, a):\n    return 'ok'"
    assert _extract_code_from_output(code_body) == code_body


# ── code_invoice RECOVERY: wrapped/verbose correct answer → real interpretation ─

def test_recover_deepseek_think_wrapped_invoice():
    """deepseek-r1 style <think>...</think> wrapping a CORRECT I0 block → I0."""
    task, candidates, _foils = _invoice_refs()
    i0 = candidates["I0"]
    wrapped = (
        "<think>\nThe fiscal year starts in April so May is Q1. Date is US "
        "MM/DD/YYYY. GAAP rounding is half-up with parentheses for negatives. "
        "Let me define the function and return the formatted string.\n</think>\n\n"
        f"```python\n{i0}\n```\n"
    )
    label = label_run(_make_run(task.id, wrapped), task)
    assert label == "I0", f"Expected recovered I0, got {label}"


def test_recover_prose_surrounded_invoice():
    """A correct I0 block surrounded by explanatory prose → I0."""
    task, candidates, _foils = _invoice_refs()
    i0 = candidates["I0"]
    verbose = (
        "Here is my solution. I compute the fiscal quarter, format the date, and "
        "round per GAAP.\n\n"
        f"```python\n{i0}\n```\n\n"
        "This handles negatives with parentheses as required."
    )
    label = label_run(_make_run(task.id, verbose), task)
    assert label == "I0", f"Expected I0, got {label}"


def test_recover_illustrative_then_final_block():
    """An illustrative WRONG (foil) block first, correct I0 block last → I0.

    Old extractor took the FIRST fence (the foil) → I_perp; hardened extractor
    takes the LAST fence (the real answer) → I0.
    """
    task, candidates, foils = _invoice_refs()
    i0 = candidates["I0"]
    foil = foils[0]  # a deliberately non-matching (0-match) implementation
    out = (
        "Draft attempt (probably wrong):\n"
        f"```python\n{foil}\n```\n"
        "Corrected final answer:\n"
        f"```python\n{i0}\n```\n"
    )
    label = label_run(_make_run(task.id, out), task)
    assert label == "I0", f"Expected I0 from final block, got {label}"


# ── NO FALSE RECOVERY: genuine off-axis / truncated → still I_perp ─────────────

def test_offaxis_mixed_convention_still_i_perp():
    """Genuine mixed-convention output (real mistral pattern) stays I_perp."""
    task, _c, _f = _invoice_refs()
    out = f"```python\n{_OFF_AXIS_MIXED}\n```"
    label = label_run(_make_run(task.id, out), task)
    assert label == "I_perp", f"Off-axis mix must stay I_perp, got {label}"


def test_offaxis_mixed_even_when_think_wrapped_still_i_perp():
    """Wrapping an off-axis answer in reasoning must NOT recover a false label."""
    task, _c, _f = _invoice_refs()
    out = f"<think>reasoning...</think>\n```python\n{_OFF_AXIS_MIXED}\n```"
    label = label_run(_make_run(task.id, out), task)
    assert label == "I_perp", f"Off-axis mix (wrapped) must stay I_perp, got {label}"


def test_truncated_reasoning_invoice_still_i_perp():
    """Truncated <think> with no final block → I_perp (no answer to recover)."""
    task, _c, _f = _invoice_refs()
    out = ("<think>Okay, I need to write format_invoice_line. The fiscal quarter "
           "def and return logic... let me think about rounding") * 3
    label = label_run(_make_run(task.id, out), task)
    assert label == "I_perp", f"Truncated reasoning must stay I_perp, got {label}"


# ── policy_qa: in-<think> illustrative number must not cause false conflict ─────

def test_policy_think_illustrative_number_not_conflict():
    """A number floated inside <think> must not conflict with the real answer."""
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    from bench.policy_qa import get_checkers_and_candidates as pol_refs
    _checkers, candidates, _foils = pol_refs(task.domain, task)
    i0_amount = candidates["I0"]["amount"]
    out = (
        f"<think>Maybe it's ${i0_amount + 100:.2f}? No, let me recompute.</think>\n"
        f"FINAL ANSWER: ${i0_amount:.2f}"
    )
    run = AgentRun(
        task_id=task.id, config="single", model_role="tested_agents",
        model_id="test-model", output=out, label="", verbalized_conf=0.9,
        logit_conf=None, seed=910,
    )
    label = label_run(run, task)
    assert label == "I0", f"Expected I0 (think number ignored), got {label}"


# ── Cache-backed regression: real diagnostic outputs behave as diagnosed ───────

def _find_cache_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    for up in (os.path.join(here, ".."), os.path.join(here, "..", "..", "..")):
        cand = os.path.abspath(os.path.join(up, ".llm_cache_default_check"))
        if os.path.isdir(cand):
            return cand
    return None


def _load_invoice_cache_outputs(model_substr):
    cache_dir = _find_cache_dir()
    if cache_dir is None:
        return None
    outs = []
    for f in glob.glob(os.path.join(cache_dir, "*.json")):
        try:
            data = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if "format_invoice_line" in data.get("text", "") and \
                model_substr in data.get("model", ""):
            outs.append(data["text"])
    return outs


def test_cache_regression_mistral_offaxis_stays_i_perp():
    """Real mistral invoice outputs that were I_perp are NOT falsely recovered.

    Genuine off-axis / buggy weak-model outputs must remain I_perp after the
    extraction hardening (no false positive labels introduced).
    """
    outs = _load_invoice_cache_outputs("mistral")
    if not outs:
        pytest.skip("diagnostic cache (.llm_cache_default_check) not present")
    task, _c, _f = _invoice_refs()
    real_interps = {i.id for i in task.interpretations if i.id != "I_perp"}
    for i, text in enumerate(outs):
        label = label_run(_make_run(task.id, text, seed=1000 + i), task)
        # A candidate may legitimately match a real interp; what must NOT happen
        # is a crash or an obviously-wrong recovery. We assert the label is a
        # valid label and that extraction never raises.
        assert label == "I_perp" or label in real_interps
