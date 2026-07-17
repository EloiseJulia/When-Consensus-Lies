"""Offline robustness tests for reasoning-wrapper / multi-block answer extraction.

Covers the LABELING-VALIDITY (answer-format) failure modes surfaced by the live
default-check diagnostic AND the false-recovery paths found by the cross-family
audit. SAFETY-FIRST contract: when the intended answer is genuinely ambiguous,
prefer I_perp over guessing — extraction hardening must NEVER turn a genuinely
wrong / ambiguous output into a correct or foil label.

Guarantees asserted here:
  * A single present-but-wrapped correct answer is RECOVERED (labels to the real
    interpretation): reasoning-wrapped, prose-surrounded, or agreeing blocks.
  * Genuinely off-axis, truncated, nested/unclosed reasoning, disagreeing
    multi-block, and non-code-language fences all STILL label I_perp.
  * The policy_qa path applies AMENDMENT 04 (owner-signed 2026-07-16): <think>
    reasoning is stripped BEFORE the UNCHANGED FINAL-ANSWER/JSON numeric grammar,
    so a <think>-internal scratch number no longer conflicts with the real FINAL
    ANSWER; two DIFFERENT real FINAL answers still → I_perp, and an unclosed
    <think> exposes nothing (nesting-aware) → I_perp.

Fully offline / deterministic (no network, no LLM judge).
"""

import json
import os

import pytest

from common.schema import AgentRun
from harness.label import (
    label_run,
    _extract_code_candidates,
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


# ── _strip_reasoning unit tests (nesting-aware, conservative) ──────────────────

def test_strip_reasoning_closed_block():
    out = "<think>Let's reason about this.</think>\n```python\nx = 1\n```"
    stripped = _strip_reasoning(out)
    assert "<think>" not in stripped
    assert "reason about" not in stripped
    assert "x = 1" in stripped


def test_strip_reasoning_unclosed_block_becomes_empty_tail():
    out = "prefix\n<think>I will define a function and return the value..."
    stripped = _strip_reasoning(out)
    assert "<think>" not in stripped
    assert "define a function" not in stripped
    assert stripped.strip() == "prefix"


def test_strip_reasoning_nested_unclosed_hides_inner_content():
    """BLOCKER 1: nested+unclosed reasoning must NOT expose inner content.

    A naive non-nesting regex would strip <think>..</think> (outer opener to
    INNER closer) and expose the reasoning-internal code as the answer.
    """
    out = "<think>outer <think>inner</think> def leaked(): return 'I0'"
    stripped = _strip_reasoning(out)
    assert "leaked" not in stripped
    assert "inner" not in stripped
    assert stripped.strip() == ""


# ── _extract_code_candidates unit tests ────────────────────────────────────────

def test_extract_returns_all_eligible_blocks_in_order():
    out = (
        "```python\ndef f():\n    return 'A'\n```\n"
        "```python\ndef f():\n    return 'B'\n```\n"
    )
    cands = _extract_code_candidates(out)
    assert len(cands) == 2
    assert "A" in cands[0] and "B" in cands[1]


def test_extract_rejects_non_code_language_fence():
    """BLOCKER 2a: a ```text / ```json fence is not a Python answer."""
    code = "def format_invoice_line(y, m, d, a):\n    return 'ok'"
    assert _extract_code_candidates(f"```text\n{code}\n```") == []
    assert _extract_code_candidates(f"```json\n{code}\n```") == []
    # python / unlabeled fences ARE eligible
    assert _extract_code_candidates(f"```python\n{code}\n```") == [code]
    assert _extract_code_candidates(f"```\n{code}\n```") == [code]


def test_extract_truncated_reasoning_returns_empty():
    out = "<think>Okay, I need to write a function. Let's define def and return..."
    assert _extract_code_candidates(out) == []


def test_extract_prose_is_not_code():
    out = ("I think you should return the records sorted by age, "
           "but I'm not sure about the tiebreak. Here's my reasoning: ...")
    assert _extract_code_candidates(out) == []


def test_extract_raw_code_without_fence():
    code_body = "def format_invoice_line(y, m, d, a):\n    return 'ok'"
    assert _extract_code_candidates(code_body) == [code_body]


# ── code_invoice RECOVERY: single wrapped/verbose correct answer → real interp ─

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
    """A single correct I0 block surrounded by explanatory prose → I0."""
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


def test_recover_agreeing_multi_block():
    """Two blocks that BOTH resolve to I0 → I0 (agreeing blocks recovered)."""
    task, candidates, _foils = _invoice_refs()
    i0 = candidates["I0"]
    out = f"First:\n```python\n{i0}\n```\nRestated identically:\n```python\n{i0}\n```"
    label = label_run(_make_run(task.id, out), task)
    assert label == "I0", f"Expected I0 for agreeing blocks, got {label}"


# ── NO FALSE RECOVERY: disagreeing multi-block / off-axis / truncated → I_perp ─

def test_disagreeing_wrong_then_correct_is_i_perp():
    """BLOCKER 2: WRONG (foil) block then correct I0 block → I_perp (never guess)."""
    task, candidates, foils = _invoice_refs()
    i0 = candidates["I0"]
    foil = foils[0]  # deliberately non-matching (0-match) implementation
    out = f"Draft:\n```python\n{foil}\n```\nFinal:\n```python\n{i0}\n```"
    label = label_run(_make_run(task.id, out), task)
    assert label == "I_perp", f"Disagreeing blocks must be I_perp, got {label}"


def test_disagreeing_correct_then_wrong_illustration_is_i_perp():
    """BLOCKER 2: correct I0 block then a wrong illustration → I_perp."""
    task, candidates, foils = _invoice_refs()
    i0 = candidates["I0"]
    foil = foils[0]
    out = f"Answer:\n```python\n{i0}\n```\nQuick illustration:\n```python\n{foil}\n```"
    label = label_run(_make_run(task.id, out), task)
    assert label == "I_perp", f"Disagreeing blocks must be I_perp, got {label}"


def test_disagreeing_two_real_interps_is_i_perp():
    """Two blocks resolving to DIFFERENT real interpretations → I_perp."""
    task, candidates, _foils = _invoice_refs()
    i0 = candidates["I0"]
    i1 = candidates["I1"]
    out = f"```python\n{i0}\n```\n```python\n{i1}\n```"
    label = label_run(_make_run(task.id, out), task)
    assert label == "I_perp", f"Two-interp multi-block must be I_perp, got {label}"


def test_nested_unclosed_reasoning_invoice_is_i_perp():
    """BLOCKER 1: I0 code that exists ONLY inside nested/unclosed reasoning → I_perp."""
    task, candidates, _foils = _invoice_refs()
    i0 = candidates["I0"]
    # Outer <think> never closes; the I0 code is only inside the reasoning.
    out = f"<think>let me draft <think>sketch</think>\n```python\n{i0}\n```"
    label = label_run(_make_run(task.id, out), task)
    assert label == "I_perp", f"Reasoning-internal code must be I_perp, got {label}"


def test_non_code_language_fence_invoice_is_i_perp():
    """BLOCKER 2a: correct I0 code inside a ```text fence is rejected → I_perp."""
    task, candidates, _foils = _invoice_refs()
    i0 = candidates["I0"]
    out = f"```text\n{i0}\n```"
    label = label_run(_make_run(task.id, out), task)
    assert label == "I_perp", f"Non-code-language fence must be I_perp, got {label}"


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


# ── policy_qa: AMENDMENT 04 (owner-signed 2026-07-16) — <think>-strip re-enabled ─
#
# A04 strips <think> reasoning BEFORE the UNCHANGED FINAL-ANSWER/JSON numeric
# grammar, so a scratch number inside <think> can no longer falsely conflict with
# the real FINAL ANSWER. The grammar, exact-cent matching, and "disagreeing REAL
# amounts → I_perp" rule are byte-for-byte unchanged; only the input is stripped.

def test_policy_think_scratch_number_now_recovers_real_final_answer_a04():
    """A04 (i): a FINAL ANSWER inside <think> that differs from the REAL final
    marker is now STRIPPED — only the real FINAL ANSWER outside <think> is
    extracted → its interpretation (NOT I_perp). Was I_perp under old §7."""
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    from bench.policy_qa import get_checkers_and_candidates as pol_refs
    _checkers, candidates, _foils = pol_refs(task.domain, task)
    i0_amount = candidates["I0"]["amount"]
    out = (
        f"<think>FINAL ANSWER: ${i0_amount + 100:.2f}</think>\n"
        f"FINAL ANSWER: ${i0_amount:.2f}"
    )
    run = AgentRun(
        task_id=task.id, config="single", model_role="tested_agents",
        model_id="test-model", output=out, label="", verbalized_conf=0.9,
        logit_conf=None, seed=910,
    )
    label = label_run(run, task)
    assert label == "I0", \
        f"A04: <think> scratch number stripped, real FINAL ANSWER → I0, got {label}"


def test_policy_two_different_real_final_answers_still_i_perp_a04():
    """A04 (ii): two DIFFERENT real FINAL answers OUTSIDE <think> still conflict
    → I_perp. Stripping reasoning does NOT relax the genuine-conflict rule."""
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    from bench.policy_qa import get_checkers_and_candidates as pol_refs
    _checkers, candidates, _foils = pol_refs(task.domain, task)
    i0_amount = candidates["I0"]["amount"]
    out = (
        f"FINAL ANSWER: ${i0_amount:.2f}\n"
        f"FINAL ANSWER: ${i0_amount + 100:.2f}"
    )
    run = AgentRun(
        task_id=task.id, config="single", model_role="tested_agents",
        model_id="test-model", output=out, label="", verbalized_conf=0.9,
        logit_conf=None, seed=912,
    )
    assert label_run(run, task) == "I_perp", \
        "A04: two different REAL FINAL answers still → I_perp"


def test_policy_unclosed_think_number_no_real_answer_is_i_perp_a04():
    """A04 (iii): an UNCLOSED/truncated <think> containing a number and NO real
    answer outside it recovers nothing (nesting-aware strip drops the open tail)
    → I_perp. Reasoning-internal numbers are never exposed as an answer."""
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    from bench.policy_qa import get_checkers_and_candidates as pol_refs
    _checkers, candidates, _foils = pol_refs(task.domain, task)
    i0_amount = candidates["I0"]["amount"]
    out = f"<think>Let me compute... FINAL ANSWER: ${i0_amount:.2f}"  # never closed
    run = AgentRun(
        task_id=task.id, config="single", model_role="tested_agents",
        model_id="test-model", output=out, label="", verbalized_conf=0.9,
        logit_conf=None, seed=913,
    )
    assert label_run(run, task) == "I_perp", \
        "A04: unclosed <think> with only an in-think number → I_perp (no exposure)"


def test_policy_plain_final_answer_still_labels():
    """A04 (iv) / no-regression: a compliant output with NO <think> labels to its
    interpretation exactly as before (strip is a no-op on reasoning-free text)."""
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    from bench.policy_qa import get_checkers_and_candidates as pol_refs
    _checkers, candidates, _foils = pol_refs(task.domain, task)
    i0_amount = candidates["I0"]["amount"]
    run = AgentRun(
        task_id=task.id, config="single", model_role="tested_agents",
        model_id="test-model", output=f"FINAL ANSWER: ${i0_amount:.2f}",
        label="", verbalized_conf=0.9, logit_conf=None, seed=911,
    )
    assert label_run(run, task) == "I0"


# ── Committed-fixture regression: PINNED per-entry expected labels ─────────────
#
# A small set of REAL model outputs (one I_perp + one non-I_perp per model)
# captured from the live diagnostic run and committed under
# tests/fixtures/invoice_label_regression.json.  Each entry carries its
# expected_label (verified at capture time).
#
# Why this is robust and CI-safe:
#   * No dependency on the gitignored, mutable .llm_cache_default_check directory.
#   * Runs identically on a fresh checkout with no live cache present.
#   * Cache additions (new model runs) never affect the pinned entries.
#
# Why this still catches regressions:
#   * Each entry is asserted per-output (EXACT expected label), not just as a
#     multiset aggregate — a regression that RELABELS any single real output
#     (e.g. a genuine I_perp flipped to I4 by false recovery, or a genuine I7
#     dropped to I_perp by false loss) immediately fails the test.
#   * The fixture includes both off-axis (I_perp) and legitimate-label entries
#     per model, so neither recovery regressions nor loss regressions can hide.

_FIXTURE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "fixtures", "invoice_label_regression.json")


def test_cache_regression_invoice_label_multiset_pinned():
    """Committed real-output fixtures must resolve to their PINNED per-entry labels.

    This is a strict regression guard (no blanket-accept): any labeler change that
    relabels a genuine off-axis output (false recovery) or a genuine correct output
    (false loss) changes exactly one entry and immediately fails the assertion.
    CI-safe: uses a committed fixture file, no live cache required.
    """
    with open(_FIXTURE_PATH, encoding="utf-8") as fh:
        fixture = json.load(fh)
    task = _invoice_task()
    for i, entry in enumerate(fixture):
        model = entry["model"]
        expected = entry["expected_label"]
        text = entry["text"]
        got = label_run(_make_run(task.id, text, seed=2000 + i), task)
        assert got == expected, (
            f"Fixture entry {i} ({model}): expected label={expected!r}, "
            f"got={got!r}. Labeler regression detected."
        )
