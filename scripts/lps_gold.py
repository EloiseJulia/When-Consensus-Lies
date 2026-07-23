# constructed by: Claude (Anthropic) family
"""Executable GOLD-AMBIGUITY label for Study 2 (detector-INDEPENDENT).

# Implementer model family: Claude / Anthropic
# Auditor model family: MUST be non-Anthropic (Law 6 — cross-family requirement)

Implements the executable ambiguity ground truth of
``paper/plans/2026-07-23-study2-eval-redesign.md`` §1–§2. For each benchmark item
we ask, WITHOUT the model:

    Do the item's OWN enumerated interpretations {I0, I1, …, I_k} produce DIFFERENT
    executable results on the item's test inputs?

  * code_spec / data_analysis: run each interpretation's GOLD implementation
    (``candidates[iid]``) on the UNION of the item's test inputs (read-only reuse
    of the frozen executable bootstrap via ``lps_method._run_code_outputs``) and
    cluster by output equality.
  * policy_qa (numeric): use each interpretation's gold EXPECTED amount
    (``checker.expected['amount']``) at cent tolerance.

Strata (§2):
  * ``AMB+``     — >= 2 interpretations discriminate (>= 2 distinct gold results).
  * ``NON-DISC`` — a deleted axis exists (``task.key_questions`` non-empty) but all
    interpretations coincide on the given inputs (untestable there; e.g.
    ``code_quarter`` on non-discriminating dates). Reported SEPARATELY.
  * ``AMB-``     — no deleted axis (k0 controls) OR interpretations all coincide
    with no axis. Detector should NOT flag.

``H_ctx_gold`` = mutual-equivalence entropy (BITS) over the enumerated-
interpretation gold RESULTS — the ORACLE ambiguity magnitude (validity check for
the black-box ``H_ctx-self``).

ANTI-CIRCULARITY (design §1, inviolable): this module clusters the BENCHMARK's
ENUMERATED interpretations (gold implementations / expected amounts). The DETECTOR
(``lps_method.H_ctx``) clusters the MODEL's OWN self-generated pins. Two INDEPENDENT
pin-sets from two independent sources — evaluating H_ctx-self against this gold
label is NOT tautological. Gold is used for EVALUATION ONLY and NEVER enters any
prompt the model sees.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
for _p in (str(_REPO_ROOT), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common.schema import Task  # noqa: E402
# Read-only reuse of the gold-FREE executors + entropy (they only RUN code / count
# clusters; they never compare to gold — here we feed them the BENCHMARK's gold
# code, which is a legitimate independent use).
from lps_method import (  # noqa: E402
    _run_code_outputs,
    _task_code_inputs,
    semantic_entropy,
)

STRATUM_AMB_POS = "AMB+"
STRATUM_NON_DISC = "NON-DISC"
STRATUM_AMB_NEG = "AMB-"


def _policy_expected_signature(expected: Any) -> Optional[str]:
    """Cent-tolerance signature of a policy_qa gold expected amount."""
    amount = expected
    if isinstance(expected, dict):
        amount = expected.get("amount")
    if not isinstance(amount, (int, float)) or isinstance(amount, bool):
        return None
    return f"num:{int(round(float(amount) * 100))}"


def _interpretation_signatures(task: Task) -> Dict[str, Optional[str]]:
    """Per-interpretation gold RESULT signature (gold impl output / expected amount).

    Returns ``{interp_id: signature or None}``. None marks an interpretation whose
    gold could not be evaluated (excluded from clustering).
    """
    domain = task.domain
    if domain == "policy_qa":
        from bench.policy_qa import get_checkers_and_candidates
        try:
            checkers, _cands, _foils = get_checkers_and_candidates(domain, task)
        except (ValueError, KeyError, RuntimeError):
            return {}
        return {
            iid: _policy_expected_signature(getattr(ck, "expected", None))
            for iid, ck in checkers.items()
        }

    if domain in ("code_spec", "data_analysis"):
        if domain == "code_spec":
            from bench.code_spec import get_checkers_and_candidates
        else:
            from bench.data_analysis import get_checkers_and_candidates
        try:
            _checkers, candidates, _foils = get_checkers_and_candidates(domain, task)
        except (ValueError, KeyError, RuntimeError):
            return {}
        inputs, entrypoint = _task_code_inputs(task)
        if not inputs or not entrypoint:
            return {}
        sigs: Dict[str, Optional[str]] = {}
        for iid, code in candidates.items():
            sigs[iid] = _run_code_outputs(domain, code, entrypoint, inputs)
        return sigs

    return {}


def gold_ambiguity(task: Task) -> Dict[str, Any]:
    """Executable, detector-independent ambiguity label for one item.

    Returns ``{stratum, n_interp, n_distinct, H_ctx_gold, interp_signatures}``.
    """
    sigs = _interpretation_signatures(task)
    valid = [s for s in sigs.values() if s is not None]
    n_distinct = len(set(valid))
    h_ctx_gold = semantic_entropy(valid)

    if n_distinct >= 2:
        stratum = STRATUM_AMB_POS
    elif task.key_questions:  # axis exists but interpretations coincide here
        stratum = STRATUM_NON_DISC
    else:
        stratum = STRATUM_AMB_NEG

    return {
        "stratum": stratum,
        "n_interp": len(sigs),
        "n_distinct": n_distinct,
        "H_ctx_gold": h_ctx_gold,
        "interp_signatures": sigs,
    }


def stratify(tasks: List[Task]) -> Dict[str, Dict[str, Any]]:
    """Compute gold-ambiguity for every task. Returns ``{task_id: gold_dict}``."""
    return {t.id: gold_ambiguity(t) for t in tasks}
