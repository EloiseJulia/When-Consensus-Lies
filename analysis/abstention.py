"""Amendment-09 P2 secondary analysis: rule-based abstention / clarification detector.

# Implementer model family: Claude (Anthropic) — A09 additive secondary.
# Auditor MUST use a different model family (GPT or Gemini) per Law 6.

⭐ A09 GUARDRAIL (INVIOLABLE — owner-required per Amendment 09 §2):
    The abstention/clarification classifier MUST NOT be a SAME-FAMILY LLM-judge
    (shared-blind-spot / provenance risk, Law 6). This module implements a
    RULE-BASED detector only (deterministic, transparent, inspectable regex/keyword
    grammar). Any future upgrade to a learned classifier MUST use a CROSS-FAMILY
    model validated against a HUMAN-spot-checked sample (see
    :func:`export_validation_sample` and :func:`future_classifier_hook`).
    Executable/deterministic ALWAYS preferred over LLM-judge (Law 7).

This module provides:

- :data:`ABSTENTION_RULES` — editable documented list of (signal_category,
  compiled_patterns) tuples. Edit this list to add/remove/tune rules.
- :func:`detect_abstention` — pure function classifying one output string;
  returns ``{"abstained": bool, "signal": str, "evidence": str}``.
- :func:`abstention_table` — aggregate abstention rate by regime × model_class.
- :func:`export_validation_sample` — emit a random sample to CSV/JSONL for
  human spot-check validation.
- :func:`future_classifier_hook` — documented interface for a future cross-family
  LLM classifier (NOT wired; raises NotImplementedError if called).

No LLM is invoked anywhere in this module.
"""
from __future__ import annotations

import csv
import json
import random
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

from analysis.contrasts import COLS

# ── Column shorthands ──────────────────────────────────────────────────────────
_REGIME = COLS["regime"]
_MODEL_CLASS = COLS["model_class"]
# The output column added by io.load_runs_tidy(include_output=True).
_OUTPUT = "output"

# ─────────────────────────────────────────────────────────────────────────────
# Signal categories
# ─────────────────────────────────────────────────────────────────────────────

#: Possible ``signal`` values returned by :func:`detect_abstention`.
SIGNAL_CANNOT_DETERMINE = "CANNOT_DETERMINE"
SIGNAL_NEED_MORE_INFO = "NEED_MORE_INFO"
SIGNAL_CLARIFICATION_QUESTION = "CLARIFICATION_QUESTION"
SIGNAL_EXPLICIT_ABSTENTION = "EXPLICIT_ABSTENTION"
SIGNAL_AMBIGUITY_FLAG = "AMBIGUITY_FLAG"
SIGNAL_ASSUMING = "ASSUMING"
SIGNAL_WHICH_MEAN = "WHICH_MEAN"
#: Returned when no abstention signal is detected.
SIGNAL_CONFIDENT_COMMIT = "CONFIDENT_COMMIT"

# ─────────────────────────────────────────────────────────────────────────────
# Rule list — edit this constant to add, remove, or tune rules.
# Each entry: (signal_category: str, patterns: List[re.Pattern])
# Rules are tested in ORDER; the FIRST match wins.
# ─────────────────────────────────────────────────────────────────────────────

def _p(pattern: str) -> re.Pattern:
    """Compile a case-insensitive pattern."""
    return re.compile(pattern, re.IGNORECASE)


#: Documented, editable rule list for the abstention detector.
#:
#: Rule categories (in priority order):
#:
#: 1. EXPLICIT_ABSTENTION — outright refusal/abstention phrases.
#: 2. CANNOT_DETERMINE — epistemic impossibility phrases.
#: 3. NEED_MORE_INFO — explicit information-insufficiency phrases.
#: 4. WHICH_MEAN — direct clarification request about the referent.
#: 5. CLARIFICATION_QUESTION — trailing clarifying question (ends with "?").
#: 6. AMBIGUITY_FLAG — explicit labelling of the prompt as ambiguous.
#: 7. ASSUMING — hedged assumption announcement (partial abstention).
#:
#: Each entry is a (signal_category, list_of_compiled_re_patterns) tuple.
ABSTENTION_RULES: List[Tuple[str, List[re.Pattern]]] = [
    # 1. Explicit refusal / abstention
    (SIGNAL_EXPLICIT_ABSTENTION, [
        _p(r"\bi\s+(?:must\s+)?(?:abstain|refuse|decline)\b"),
        _p(r"\bcannot\s+(?:and\s+will\s+not|provide|give)\b"),
        _p(r"\bI\s+(?:am\s+not\s+able|am\s+unable)\s+to\s+(?:answer|respond|provide)\b"),
        _p(r"\bI\s+won['']t\s+(?:answer|respond|provide)\b"),
    ]),

    # 2. Epistemic impossibility — "cannot / impossible to determine"
    (SIGNAL_CANNOT_DETERMINE, [
        _p(r"\b(?:cannot|can['']t|impossible\s+to|not\s+possible\s+to)\s+"
           r"(?:determine|know|tell|say|decide|conclude|ascertain|identify)\b"),
        _p(r"\b(?:there\s+is\s+)?(?:no\s+way\s+(?:to\s+)?(?:know|tell|determine))\b"),
        _p(r"\b(?:it\s+is\s+)?(?:unknowable|indeterminate|undecidable)\b"),
        _p(r"\bcannot\s+be\s+(?:determined|known|inferred|concluded)\b"),
    ]),

    # 3. Insufficient information / needs more context
    (SIGNAL_NEED_MORE_INFO, [
        _p(r"\b(?:need|require|lack|missing|without|have\s+no)\b.{0,40}"
           r"(?:more\s+)?(?:information|context|detail|data|clarification|specification)\b"),
        _p(r"\b(?:insufficient|inadequate|incomplete)\s+"
           r"(?:information|context|data|detail)\b"),
        _p(r"\bmore\s+(?:context|information|detail|data)\s+(?:is\s+)?(?:needed|required|necessary)\b"),
        _p(r"\bwithout\s+(?:more|additional|further)\s+"
           r"(?:context|information|detail|clarification)\b"),
        _p(r"\bI\s+don['']t\s+have\s+(?:enough|sufficient)\s+"
           r"(?:context|information|detail)\b"),
    ]),

    # 4. Direct clarification request — "which X did you mean?"
    (SIGNAL_WHICH_MEAN, [
        _p(r"\bwhich\b.{0,60}(?:did\s+you\s+mean|do\s+you\s+mean|are\s+you\s+referring)\b"),
        _p(r"\bwhat\s+(?:do\s+you\s+mean|did\s+you\s+mean)\s+by\b"),
        _p(r"\bcould\s+you\s+(?:please\s+)?clarify\s+(?:which|what|whether)\b"),
        _p(r"\bplease\s+(?:clarify|specify|indicate)\s+(?:which|what|whether)\b"),
        _p(r"\bare\s+you\s+(?:referring|asking)\s+(?:to|about)\b.{0,40}\?"),
    ]),

    # 5. Trailing clarifying question (the output ends with a "?" question about
    #    the task's meaning — strong signal of requested clarification).
    (SIGNAL_CLARIFICATION_QUESTION, [
        # Ends with an explicit clarification/disambiguation question.
        _p(r"(?:which|what|could\s+you|can\s+you|would\s+you|do\s+you\s+mean)"
           r"[^.!?]{0,120}\?\s*$"),
        _p(r"(?:clarify|specify|elaborate|disambiguate|explain\s+what\s+you\s+mean)"
           r"[^.!?]{0,80}\?\s*$"),
        # "Are you asking about X or Y?" disambiguation question at end.
        _p(r"(?:are\s+you\s+asking|are\s+you\s+referring|do\s+you\s+want)"
           r"[^.!?]{0,120}\?\s*$"),
    ]),

    # 6. Ambiguity flag — labels the prompt as ambiguous/unclear.
    (SIGNAL_AMBIGUITY_FLAG, [
        _p(r"\b(?:the\s+)?(?:question|prompt|task|request|statement)\s+is\s+"
           r"(?:ambiguous|unclear|vague|underspecified|ambiguous)\b"),
        _p(r"\bthis\s+(?:is|seems?|appears?)\s+(?:ambiguous|unclear|vague|underspecified)\b"),
        _p(r"\bthe\s+(?:intent|meaning|referent)\s+(?:is|remains?)\s+(?:unclear|ambiguous)\b"),
        _p(r"\bmultiple\s+(?:valid\s+)?interpretations?\s+(?:are\s+)?possible\b"),
        _p(r"\bit['']s\s+(?:not\s+)?(?:clear|obvious)\s+(?:which|what|whether)\b"),
    ]),

    # 7. Hedged assumption — agent explicitly names what it ASSUMES about the
    #    referent/question, signalling unresolved interpretation ambiguity.
    #    A committed answer that merely states an analytical assumption and then
    #    gives a final interpretation is NOT an abstention (abstained=False).
    #    These patterns therefore require the assumption to be explicitly about
    #    WHICH interpretation / what "you mean" / what "you're asking" — not
    #    any general methodological assumption.
    (SIGNAL_ASSUMING, [
        _p(r"\b(?:assuming|i['']ll\s+assume|i['']m\s+assuming|let\s+me\s+assume)\b"
           r".{0,80}(?:you\s+mean|you['']re\s+asking|this\s+refers\s+to)\b"),
        _p(r"\bassuming\s+(?:that\s+)?(?:by|you\s+mean|this\s+is\s+about)\b"),
        _p(r"\bi\s+(?:will|shall|am\s+going\s+to)\s+assume\b.{0,80}"
           r"(?:you\s+(?:mean|are\s+asking|are\s+referring)|"
           r"the\s+question\s+(?:refers|is\s+about))\b"),
        _p(r"\bin\s+the\s+absence\s+of\s+(?:more|additional|further)\s+"
           r"(?:context|information)\b"),
    ]),
]


# ─────────────────────────────────────────────────────────────────────────────
# Core classifier
# ─────────────────────────────────────────────────────────────────────────────

def detect_abstention(output: str) -> Dict[str, object]:
    """Classify an agent output as abstained / clarification-requested / committed.

    Pure, deterministic, transparent rule-based classifier. No LLM is invoked.

    Tests each rule in :data:`ABSTENTION_RULES` in order; the FIRST match wins.
    Returns the matched signal category, the matched evidence span, and a boolean
    ``abstained`` flag that is True for all signal categories except
    ``CONFIDENT_COMMIT``.

    ``ASSUMING`` counts as ``abstained=True`` (the agent hedges rather than
    committing) but is the weakest signal. Reviewers may wish to treat it
    separately for reporting.

    Args:
        output: Raw agent output string (AgentRun.output).

    Returns:
        Dict with keys:
            ``abstained`` (bool)     — True iff any abstention signal found.
            ``signal``   (str)       — Signal category (see SIGNAL_* constants).
            ``evidence`` (str)       — The matched substring (empty on no match).
    """
    if not output or not isinstance(output, str):
        return {"abstained": False, "signal": SIGNAL_CONFIDENT_COMMIT, "evidence": ""}

    for signal, patterns in ABSTENTION_RULES:
        for pat in patterns:
            m = pat.search(output)
            if m:
                return {
                    "abstained": True,
                    "signal": signal,
                    "evidence": m.group(0).strip(),
                }

    return {"abstained": False, "signal": SIGNAL_CONFIDENT_COMMIT, "evidence": ""}


# ─────────────────────────────────────────────────────────────────────────────
# Aggregate table
# ─────────────────────────────────────────────────────────────────────────────

def abstention_table(
    tidy: pd.DataFrame,
    *,
    regime_col: Optional[str] = None,
    model_class_col: Optional[str] = None,
) -> pd.DataFrame:
    """Abstention rate by regime × model_class.

    The silent-failure prediction (Amendment 09 §2): LOW abstention on
    ``H1_external`` despite HIGH ``cd_primary`` — agents are CONFIDENTLY WRONG,
    not appropriately uncertain.

    Requires the ``output`` column (from ``load_runs_tidy(include_output=True)``).

    Args:
        tidy: Agent-level tidy table including an ``output`` column.
        regime_col: Column name for regime (default: ``"regime"``).
        model_class_col: Column name for model class (default: ``"model_class"``).

    Returns:
        DataFrame with columns:
            ``regime``, ``model_class``, ``n_agents``,
            ``n_abstained``, ``abstention_rate``,
            ``signal_counts`` (dict of signal → count, as a string).
        Each row is one (regime × model_class) group. A row with
        ``regime="ALL"`` + ``model_class="ALL"`` gives the grand total.
    """
    regime_col = regime_col or _REGIME
    mc_col = model_class_col or _MODEL_CLASS

    if _OUTPUT not in tidy.columns:
        raise ValueError(
            "abstention_table requires an 'output' column. "
            "Call load_runs_tidy(include_output=True) to include it."
        )

    # Classify each row.
    results = [detect_abstention(str(out)) for out in tidy[_OUTPUT]]
    work = tidy.copy()
    work["_abstained"] = [r["abstained"] for r in results]
    work["_signal"] = [r["signal"] for r in results]

    group_cols = [c for c in (regime_col, mc_col) if c in work.columns]

    rows: List[Dict] = []

    def _agg_group(df: pd.DataFrame, regime_val: str, mc_val: str) -> Dict:
        n = len(df)
        n_abs = int(df["_abstained"].sum())
        sig_counts = df["_signal"].value_counts().to_dict()
        return {
            "regime": regime_val,
            "model_class": mc_val,
            "n_agents": n,
            "n_abstained": n_abs,
            "abstention_rate": n_abs / n if n > 0 else float("nan"),
            "signal_counts": str(sig_counts),
        }

    if group_cols:
        for keys, group in work.groupby(group_cols, dropna=False, sort=True):
            if not isinstance(keys, tuple):
                keys = (keys,)
            key_dict = dict(zip(group_cols, keys))
            reg_val = str(key_dict.get(regime_col, ""))
            mc_val = str(key_dict.get(mc_col, ""))
            rows.append(_agg_group(group, reg_val, mc_val))

    # Grand total.
    rows.append(_agg_group(work, "ALL", "ALL"))

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Human-validation sample export
# ─────────────────────────────────────────────────────────────────────────────

def export_validation_sample(
    tidy: pd.DataFrame,
    output_path: Union[str, Path],
    *,
    n_sample: int = 100,
    seed: int = 0,
    fmt: str = "jsonl",
    stratify_by_signal: bool = True,
) -> int:
    """Export a random sample of (output, rule_verdict) rows for human spot-check.

    The exported file is intended for a HUMAN reviewer (or a CROSS-FAMILY
    classifier, per the A09 guardrail) to validate that the rule-based detector
    is classifying correctly. It is NOT used to train or evaluate a same-family
    model.

    Args:
        tidy: Agent-level tidy table with an ``output`` column.
        output_path: Destination file path (CSV or JSONL).
        n_sample: Number of rows to sample (default 100).
        seed: Random seed for reproducibility.
        fmt: ``"jsonl"`` (default) or ``"csv"``.
        stratify_by_signal: If True, attempt to over-sample rare signal
            categories so that each category is represented.

    Returns:
        Number of rows written.
    """
    if _OUTPUT not in tidy.columns:
        raise ValueError(
            "export_validation_sample requires an 'output' column. "
            "Call load_runs_tidy(include_output=True)."
        )

    # Classify all rows.
    results = [detect_abstention(str(out)) for out in tidy[_OUTPUT]]
    work = tidy[[_OUTPUT]].copy()
    work["_rule_signal"] = [r["signal"] for r in results]
    work["_abstained"] = [r["abstained"] for r in results]
    work["_evidence"] = [r["evidence"] for r in results]

    rng = random.Random(seed)

    if stratify_by_signal:
        # Sample proportionally, guaranteeing at least 1 row per signal.
        signals = work["_rule_signal"].unique().tolist()
        per_signal = max(1, n_sample // max(len(signals), 1))
        sample_rows: List[pd.DataFrame] = []
        for sig in signals:
            sub = work[work["_rule_signal"] == sig]
            k = min(per_signal, len(sub))
            sample_rows.append(sub.sample(n=k, random_state=rng.randint(0, 2**31)))
        sample = pd.concat(sample_rows, ignore_index=True)
        if len(sample) < n_sample:
            remaining = work.drop(sample.index, errors="ignore")
            extra = min(n_sample - len(sample), len(remaining))
            if extra > 0:
                sample = pd.concat([
                    sample,
                    remaining.sample(n=extra, random_state=rng.randint(0, 2**31)),
                ], ignore_index=True)
    else:
        k = min(n_sample, len(work))
        sample = work.sample(n=k, random_state=rng.randint(0, 2**31))

    output_path = Path(output_path)
    fmt = fmt.lower()

    # Rename internal columns to public names for export.
    export_df = sample.rename(columns={
        "_rule_signal": "rule_signal",
        "_abstained": "abstained",
        "_evidence": "evidence",
    })

    if fmt == "csv":
        export_df.to_csv(output_path, index=False)
    else:
        with open(output_path, "w", encoding="utf-8") as fh:
            for _, row_s in export_df.iterrows():
                rec = {
                    "output": row_s[_OUTPUT],
                    "rule_signal": row_s["rule_signal"],
                    "abstained": row_s["abstained"],
                    "evidence": row_s["evidence"],
                }
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return len(sample)


# ─────────────────────────────────────────────────────────────────────────────
# Future cross-family classifier hook (NOT wired — see A09 guardrail)
# ─────────────────────────────────────────────────────────────────────────────

def future_classifier_hook(
    outputs: List[str],
    *,
    classifier_family: str,
    model_endpoint: Optional[str] = None,
) -> List[Dict[str, object]]:
    """Documented interface for a FUTURE cross-family LLM abstention classifier.

    ⭐ A09 GUARDRAIL: This function MUST NOT be wired to a SAME-FAMILY LLM-judge.
    The ``classifier_family`` argument MUST be different from the implementer
    family (Claude). Acceptable values: ``"GPT"`` / ``"Gemini"`` or a
    deterministic rule override ``"rules_only"``.

    This function currently raises ``NotImplementedError`` and is provided ONLY
    to document the intended interface and enforce the cross-family requirement.
    The Manager should spawn a cross-family sub-agent when ready to implement.

    Intended signature (for future implementer):
        - Take a list of output strings.
        - Return a list of dicts with the same schema as ``detect_abstention``.
        - Validate against :func:`export_validation_sample` spot-check output
          (human agreement required before deployment per A09 §2).

    Args:
        outputs: List of agent output strings to classify.
        classifier_family: MUST be ``"GPT"``, ``"Gemini"``, ``"rules_only"``,
            or another non-Claude family identifier.
        model_endpoint: Optional endpoint/model-id for the cross-family LLM.

    Raises:
        NotImplementedError: Always — this is not yet implemented.
        ValueError: If ``classifier_family`` is ``"Claude"`` or any variant
            (same-family LLM-judge is forbidden by A09 guardrail).
    """
    forbidden = {"claude", "anthropic", "claude-sonnet", "claude-opus", "claude-haiku"}
    if classifier_family.lower().split("-")[0] in forbidden or "claude" in classifier_family.lower():
        raise ValueError(
            f"A09 guardrail violation: classifier_family={classifier_family!r} is a "
            "same-family (Claude) LLM-judge. The abstention classifier MUST be "
            "cross-family (GPT/Gemini) or rule-based to avoid shared blind spots."
        )
    raise NotImplementedError(
        "future_classifier_hook is not yet implemented. "
        "Implement using a cross-family LLM (non-Claude) + human validation per A09 §2."
    )
