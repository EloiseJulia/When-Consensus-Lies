"""Tests for analysis/abstention.py — A09 P2 rule-based abstention detector.

Golden hand cases per the plan spec §3 and Amendment 09 §2.
All tests are deterministic (no LLM, no network).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import pytest

from analysis.abstention import (
    ABSTENTION_RULES,
    SIGNAL_AMBIGUITY_FLAG,
    SIGNAL_ASSUMING,
    SIGNAL_CANNOT_DETERMINE,
    SIGNAL_CLARIFICATION_QUESTION,
    SIGNAL_CONFIDENT_COMMIT,
    SIGNAL_EXPLICIT_ABSTENTION,
    SIGNAL_NEED_MORE_INFO,
    SIGNAL_WHICH_MEAN,
    abstention_table,
    detect_abstention,
    export_validation_sample,
    future_classifier_hook,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _tidy_with_output(outputs, regimes=None, model_classes=None) -> pd.DataFrame:
    n = len(outputs)
    regimes = regimes or (["H1_external"] * n)
    model_classes = model_classes or (["reasoning"] * n)
    return pd.DataFrame({
        "task": [f"T{i}" for i in range(n)],
        "method": ["sc"] * n,
        "model_class": model_classes,
        "seed": [1] * n,
        "label": ["I1"] * n,
        "target": ["I0"] * n,
        "regime": regimes,
        "ambiguity_k": [1] * n,
        "model": [f"m{i}" for i in range(n)],
        "output": outputs,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 1. detect_abstention — positive (should detect abstention)
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectAbstentionPositive:

    def test_cannot_determine(self):
        out = "Based on the information provided, I cannot determine which specification applies."
        r = detect_abstention(out)
        assert r["abstained"] is True
        assert r["signal"] == SIGNAL_CANNOT_DETERMINE
        assert len(r["evidence"]) > 0

    def test_cant_determine_contraction(self):
        out = "I can't determine the correct answer without more context."
        r = detect_abstention(out)
        assert r["abstained"] is True
        assert r["signal"] == SIGNAL_CANNOT_DETERMINE

    def test_impossible_to_know(self):
        out = "It is impossible to know which interpretation is intended here."
        r = detect_abstention(out)
        assert r["abstained"] is True
        assert r["signal"] == SIGNAL_CANNOT_DETERMINE

    def test_need_more_information(self):
        out = "I need more information to provide a definitive answer."
        r = detect_abstention(out)
        assert r["abstained"] is True
        assert r["signal"] == SIGNAL_NEED_MORE_INFO

    def test_insufficient_context(self):
        out = "There is insufficient context to resolve this ambiguity."
        r = detect_abstention(out)
        assert r["abstained"] is True
        assert r["signal"] == SIGNAL_NEED_MORE_INFO

    def test_which_did_you_mean(self):
        out = "I can't tell which specification did you mean — A or B?"
        r = detect_abstention(out)
        assert r["abstained"] is True
        # Should match WHICH_MEAN (or CANNOT_DETERMINE first) — either signals abstention
        assert r["signal"] in (SIGNAL_WHICH_MEAN, SIGNAL_CANNOT_DETERMINE, SIGNAL_CLARIFICATION_QUESTION)

    def test_explicit_clarification_which(self):
        out = "Could you please clarify which version of the API you are referring to?"
        r = detect_abstention(out)
        assert r["abstained"] is True
        assert r["signal"] in (SIGNAL_WHICH_MEAN, SIGNAL_CLARIFICATION_QUESTION)

    def test_trailing_clarification_question(self):
        out = "This could refer to multiple things. Which one do you mean?"
        r = detect_abstention(out)
        assert r["abstained"] is True

    def test_ambiguous_flag(self):
        out = "This question is ambiguous and multiple valid interpretations are possible."
        r = detect_abstention(out)
        assert r["abstained"] is True
        assert r["signal"] in (SIGNAL_AMBIGUITY_FLAG,)

    def test_ambiguous_the_question_is_ambiguous(self):
        out = "The question is ambiguous — it could mean either X or Y."
        r = detect_abstention(out)
        assert r["abstained"] is True

    def test_assuming_hedge(self):
        out = "I'll assume you mean the first interpretation and proceed accordingly."
        r = detect_abstention(out)
        assert r["abstained"] is True
        assert r["signal"] == SIGNAL_ASSUMING

    def test_explicit_abstention_refuse(self):
        out = "I refuse to answer this question as stated."
        r = detect_abstention(out)
        assert r["abstained"] is True
        assert r["signal"] == SIGNAL_EXPLICIT_ABSTENTION

    def test_i_abstain(self):
        out = "I abstain from providing an answer given the ambiguity."
        r = detect_abstention(out)
        assert r["abstained"] is True
        assert r["signal"] == SIGNAL_EXPLICIT_ABSTENTION

    def test_cannot_be_determined(self):
        out = "The correct interpretation cannot be determined from the available evidence."
        r = detect_abstention(out)
        assert r["abstained"] is True
        assert r["signal"] == SIGNAL_CANNOT_DETERMINE

    def test_i_dont_have_enough_context(self):
        out = "I don't have enough context to answer this with confidence."
        r = detect_abstention(out)
        assert r["abstained"] is True
        assert r["signal"] == SIGNAL_NEED_MORE_INFO


# ─────────────────────────────────────────────────────────────────────────────
# 2. detect_abstention — negative (should NOT detect abstention)
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectAbstentionNegative:

    def test_confident_wrong_answer(self):
        """A confidently wrong output must NOT be classified as abstention."""
        out = "The function should use the recursive algorithm I2."
        r = detect_abstention(out)
        assert r["abstained"] is False
        assert r["signal"] == SIGNAL_CONFIDENT_COMMIT
        assert r["evidence"] == ""

    def test_confident_correct_answer(self):
        out = "The correct interpretation is I0: use the iterative approach."
        r = detect_abstention(out)
        assert r["abstained"] is False
        assert r["signal"] == SIGNAL_CONFIDENT_COMMIT

    def test_no_hedging_long_output(self):
        out = (
            "After careful analysis, the specification clearly indicates that the "
            "function must handle the edge case using the first interpretation. "
            "This is consistent with the documented behavior in version 2.0."
        )
        r = detect_abstention(out)
        assert r["abstained"] is False
        assert r["signal"] == SIGNAL_CONFIDENT_COMMIT

    def test_empty_string(self):
        r = detect_abstention("")
        assert r["abstained"] is False
        assert r["signal"] == SIGNAL_CONFIDENT_COMMIT

    def test_none_input(self):
        r = detect_abstention(None)  # type: ignore[arg-type]
        assert r["abstained"] is False
        assert r["signal"] == SIGNAL_CONFIDENT_COMMIT

    def test_deterministic_same_output(self):
        """Same input always produces same output (determinism)."""
        out = "The correct answer is I1 because of the spec definition."
        r1 = detect_abstention(out)
        r2 = detect_abstention(out)
        assert r1 == r2

    def test_non_abstaining_question_ending(self):
        """Output ending with a rhetorical question is not necessarily abstention."""
        out = "I select interpretation I2. Isn't that what the spec says?"
        # This may or may not trigger — but it should not be a confident wrong
        # that gets a false positive for high-confidence signals.
        r = detect_abstention(out)
        # The key assertion: if abstained, it must have a non-empty evidence.
        if r["abstained"]:
            assert len(r["evidence"]) > 0

    def test_word_determine_in_positive_context(self):
        """The word 'determine' in a confident context should NOT trigger."""
        out = "After analysis I determine that interpretation I1 is correct."
        r = detect_abstention(out)
        # "I determine" (positive confident assertion) should not fire cannot_determine
        assert r["signal"] == SIGNAL_CONFIDENT_COMMIT


# ─────────────────────────────────────────────────────────────────────────────
# 3. detect_abstention — output schema
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectAbstentionSchema:

    def test_returns_dict_with_required_keys(self):
        r = detect_abstention("cannot determine the answer")
        assert set(r.keys()) >= {"abstained", "signal", "evidence"}

    def test_abstained_is_bool(self):
        r = detect_abstention("I need more information")
        assert isinstance(r["abstained"], bool)

    def test_signal_is_str(self):
        r = detect_abstention("clearly the answer is I1")
        assert isinstance(r["signal"], str)

    def test_evidence_is_str(self):
        r = detect_abstention("I cannot determine the answer")
        assert isinstance(r["evidence"], str)

    def test_confident_commit_has_empty_evidence(self):
        r = detect_abstention("The answer is I1.")
        assert r["signal"] == SIGNAL_CONFIDENT_COMMIT
        assert r["evidence"] == ""


# ─────────────────────────────────────────────────────────────────────────────
# 4. ABSTENTION_RULES structure
# ─────────────────────────────────────────────────────────────────────────────

class TestAbstentionRules:

    def test_rules_is_list(self):
        assert isinstance(ABSTENTION_RULES, list)
        assert len(ABSTENTION_RULES) >= 4

    def test_each_rule_has_signal_and_patterns(self):
        for entry in ABSTENTION_RULES:
            signal, patterns = entry
            assert isinstance(signal, str)
            assert isinstance(patterns, list)
            assert len(patterns) >= 1

    def test_all_signal_constants_present(self):
        signals = {e[0] for e in ABSTENTION_RULES}
        for expected in [
            SIGNAL_CANNOT_DETERMINE, SIGNAL_NEED_MORE_INFO, SIGNAL_WHICH_MEAN,
            SIGNAL_AMBIGUITY_FLAG, SIGNAL_ASSUMING, SIGNAL_EXPLICIT_ABSTENTION,
        ]:
            assert expected in signals, f"Missing rule category: {expected}"


# ─────────────────────────────────────────────────────────────────────────────
# 5. abstention_table
# ─────────────────────────────────────────────────────────────────────────────

class TestAbstentionTable:

    def test_basic_table(self):
        outputs = [
            "I cannot determine the answer.",
            "The answer is clearly I1.",
            "I need more information.",
            "The answer is I2.",
        ]
        regimes = ["H1_external", "H1_external", "H2_derivable", "H2_derivable"]
        model_classes = ["reasoning", "reasoning", "weak", "weak"]
        tidy = _tidy_with_output(outputs, regimes, model_classes)
        table = abstention_table(tidy)
        assert isinstance(table, pd.DataFrame)
        assert "abstention_rate" in table.columns
        assert "n_agents" in table.columns
        assert "regime" in table.columns
        assert "model_class" in table.columns

    def test_all_abstained(self):
        outputs = ["I cannot determine.", "Need more information.", "I cannot tell."]
        tidy = _tidy_with_output(outputs)
        table = abstention_table(tidy)
        grand = table[table["regime"] == "ALL"]
        assert float(grand.iloc[0]["abstention_rate"]) == pytest.approx(1.0)

    def test_none_abstained(self):
        outputs = ["Answer is I1.", "Answer is I2.", "Answer is I0."]
        tidy = _tidy_with_output(outputs)
        table = abstention_table(tidy)
        grand = table[table["regime"] == "ALL"]
        assert float(grand.iloc[0]["abstention_rate"]) == pytest.approx(0.0)

    def test_grand_total_row_present(self):
        tidy = _tidy_with_output(["Answer is I1.", "I cannot determine."])
        table = abstention_table(tidy)
        assert "ALL" in table["regime"].values

    def test_raises_without_output_column(self):
        tidy = pd.DataFrame({"task": ["T1"], "label": ["I1"]})
        with pytest.raises(ValueError, match="output"):
            abstention_table(tidy)

    def test_h1_external_lower_abstention_prediction(self):
        """Silent-failure scenario: agents abstain on H2 but commit on H1."""
        outputs_h1 = ["The answer is I1."] * 10  # confident (wrong)
        outputs_h2 = ["I cannot determine which is meant."] * 10  # abstaining
        tidy = _tidy_with_output(
            outputs_h1 + outputs_h2,
            regimes=["H1_external"] * 10 + ["H2_derivable"] * 10,
        )
        table = abstention_table(tidy)
        h1_row = table[table["regime"] == "H1_external"]
        h2_row = table[table["regime"] == "H2_derivable"]
        h1_rate = float(h1_row["abstention_rate"].iloc[0])
        h2_rate = float(h2_row["abstention_rate"].iloc[0])
        assert h1_rate < h2_rate  # H1 agents commit (low abstention), H2 abstain


# ─────────────────────────────────────────────────────────────────────────────
# 6. export_validation_sample
# ─────────────────────────────────────────────────────────────────────────────

class TestExportValidationSample:

    def test_jsonl_export(self, tmp_path):
        outputs = [f"output_{i}" for i in range(20)]
        outputs[0] = "I cannot determine the answer."
        tidy = _tidy_with_output(outputs)
        out_file = tmp_path / "sample.jsonl"
        n = export_validation_sample(tidy, out_file, n_sample=10, seed=1)
        assert n == 10
        with open(out_file) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == 10
        for rec in lines:
            assert "output" in rec
            assert "rule_signal" in rec
            assert "abstained" in rec
            assert "evidence" in rec

    def test_csv_export(self, tmp_path):
        outputs = [f"answer_{i}" for i in range(15)]
        tidy = _tidy_with_output(outputs)
        out_file = tmp_path / "sample.csv"
        n = export_validation_sample(tidy, out_file, n_sample=5, seed=2, fmt="csv")
        assert n == 5
        df = pd.read_csv(out_file)
        assert "output" in df.columns
        assert "rule_signal" in df.columns

    def test_export_fewer_than_n(self, tmp_path):
        """When tidy has fewer rows than n_sample, export all available."""
        outputs = ["answer_1", "answer_2"]
        tidy = _tidy_with_output(outputs)
        out_file = tmp_path / "sample.jsonl"
        n = export_validation_sample(tidy, out_file, n_sample=50, seed=0)
        assert n == 2

    def test_raises_without_output_column(self, tmp_path):
        tidy = pd.DataFrame({"task": ["T1"]})
        with pytest.raises(ValueError, match="output"):
            export_validation_sample(tidy, tmp_path / "x.jsonl")


# ─────────────────────────────────────────────────────────────────────────────
# 7. future_classifier_hook (guardrail enforcement)
# ─────────────────────────────────────────────────────────────────────────────

class TestFutureClassifierHook:

    def test_raises_not_implemented_for_cross_family(self):
        with pytest.raises(NotImplementedError):
            future_classifier_hook(["some output"], classifier_family="GPT")

    def test_raises_not_implemented_for_gemini(self):
        with pytest.raises(NotImplementedError):
            future_classifier_hook(["some output"], classifier_family="Gemini")

    def test_raises_value_error_for_claude_family(self):
        """A09 guardrail: calling with Claude family MUST raise ValueError."""
        with pytest.raises(ValueError, match="guardrail"):
            future_classifier_hook(["some output"], classifier_family="Claude")

    def test_raises_value_error_for_claude_variant(self):
        with pytest.raises(ValueError, match="guardrail"):
            future_classifier_hook(["output"], classifier_family="claude-opus")

    def test_raises_value_error_for_anthropic(self):
        with pytest.raises(ValueError, match="guardrail"):
            future_classifier_hook(["output"], classifier_family="Anthropic")


# ─────────────────────────────────────────────────────────────────────────────
# 8. A09 guardrail: no LLM call anywhere in the module
# ─────────────────────────────────────────────────────────────────────────────

class TestNoLlmCall:

    def test_detect_abstention_is_pure_regex(self):
        """detect_abstention must be deterministic and not call any network/LLM.

        We call it 100 times and verify identical output each time.
        """
        out = "I cannot determine which specification you mean."
        results = [detect_abstention(out) for _ in range(100)]
        assert all(r == results[0] for r in results), "Non-deterministic output detected"

    def test_abstention_table_is_deterministic(self):
        outputs = ["I need more info.", "The answer is I1."]
        tidy = _tidy_with_output(outputs)
        t1 = abstention_table(tidy)
        t2 = abstention_table(tidy)
        assert t1.equals(t2)
