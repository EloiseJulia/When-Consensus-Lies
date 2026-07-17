"""Amendment-04 convergent-delusion (CD) computations — analysis layer.

Model family of implementer: Claude (Anthropic). Auditor: NON-Claude (GPT).

This module implements the signed **Amendment 04** (paper/preregistration/
2026-07-15-amendment-04-iperp-treatment.md) I_perp treatment as a thin
ANALYSIS-LAYER wrapper. It does NOT modify the FROZEN metric definition in
``harness/metrics.py`` — SENSITIVITY A imports and calls the frozen
``false_consensus_rate`` directly (the frozen definition is the sensitivity
anchor, per Hard Law 7).

The four A04 quantities (all computed per item over that item's agent labels):

- ``cd_primary``            — PRIMARY (confirmatory). Modal share over the
  ENUMERATED wrong labels ``{I1..Im}`` only; ``I_perp`` is INELIGIBLE to be the
  convergent label but REMAINS in the denominator ``N = len(labels)`` (I_perp
  agents dilute, never inflate, CD).
- ``cd_sensitivity_frozen`` — SENSITIVITY A. The frozen metric exactly as-is
  (``I_perp`` eligible as modal wrong, ``N = len(labels)``). Upper-bound CD.
  Imports + calls ``harness.metrics.false_consensus_rate`` (do not reimplement).
- ``cd_sensitivity_drop_iperp`` — SENSITIVITY B. Drop ``I_perp`` agents from
  ``N``, then modal-wrong share among the remaining parseable agents.
- ``iperp_rate``            — DIAGNOSTIC. Fraction of agents mapped to ``I_perp``.

Golden case (mirrors the A04 diagnostic), labels
``["I1","I1","I_perp","I_perp","I_perp"]`` with target ``"I0"``:
    cd_sensitivity_frozen   = 0.60   (I_perp modal wrong, 3/5)
    cd_primary              = 0.40   (I1 modal enumerated wrong, 2/5)
    cd_sensitivity_drop_iperp = 1.0  (I1 is 2/2 among the 2 parseable agents)
    iperp_rate              = 0.60   (3/5 agents in I_perp)
"""

from typing import Dict, List

from harness.metrics import false_consensus_rate

#: The degenerate / unparseable / off-axis bucket (common/schema.py Interpretation).
IPERP = "I_perp"


def cd_primary(labels: List[str], target: str) -> float:
    """A04 PRIMARY: modal share over ENUMERATED wrong labels only.

    ``I_perp`` is ineligible to be the convergent label, but I_perp agents stay
    in the denominator ``N = len(labels)``. Formally::

        CD_primary = ( max_{w in enumerated-wrong} count(w) ) / N_total

    with ``count(I_perp)`` excluded from the max. If there is no enumerated
    wrong label present, CD_primary = 0.0.

    Args:
        labels: All agent interpretation labels for one item.
        target: The correct (target) interpretation label, e.g. ``"I0"``.

    Returns:
        Float in [0, 1].
    """
    if not labels:
        return 0.0

    enumerated_wrong: Dict[str, int] = {}
    for label in labels:
        if label != target and label != IPERP:
            enumerated_wrong[label] = enumerated_wrong.get(label, 0) + 1

    if not enumerated_wrong:
        return 0.0

    max_enumerated = max(enumerated_wrong.values())
    return max_enumerated / len(labels)


def cd_sensitivity_frozen(labels: List[str], target: str) -> float:
    """A04 SENSITIVITY A: the FROZEN metric exactly as-is (I_perp eligible).

    Pins to the frozen definition by importing and calling
    ``harness.metrics.false_consensus_rate`` — the frozen metric is the
    sensitivity anchor and MUST NOT be reimplemented here.

    Args:
        labels: All agent interpretation labels for one item.
        target: The correct (target) interpretation label.

    Returns:
        Float in [0, 1]: the upper-bound CD (I_perp may be the modal wrong).
    """
    return false_consensus_rate(labels, target)


def cd_sensitivity_drop_iperp(labels: List[str], target: str) -> float:
    """A04 SENSITIVITY B: drop I_perp agents from N, then modal-wrong share.

    Removes ``I_perp`` agents entirely (from the denominator too), then computes
    the modal-wrong share among the remaining parseable agents. Bounds CD from
    the "exclude degenerate agents" direction. Reuses the frozen metric on the
    filtered label list.

    Args:
        labels: All agent interpretation labels for one item.
        target: The correct (target) interpretation label.

    Returns:
        Float in [0, 1]; 0.0 if no parseable agents remain.
    """
    parseable = [label for label in labels if label != IPERP]
    return false_consensus_rate(parseable, target)


def iperp_rate(labels: List[str]) -> float:
    """A04 DIAGNOSTIC: fraction of agents mapped to ``I_perp``.

    A high I_perp rate is a first-class FINDING (per A04, most likely
    answer-format-contract non-compliance) and is pre-registered with a >20%
    investigate-before-trust gate on primary H1_external cells.

    Args:
        labels: All agent interpretation labels for one item.

    Returns:
        Float in [0, 1]: count(I_perp) / len(labels); 0.0 for empty input.
    """
    if not labels:
        return 0.0
    return sum(1 for label in labels if label == IPERP) / len(labels)


#: Ordered mapping of the three A04 CD variant names to their functions. Every
#: contrast/figure is reported across ALL THREE (+ the I_perp rate) per A04.
CD_VARIANTS = {
    "cd_primary": cd_primary,
    "cd_sensitivity_frozen": cd_sensitivity_frozen,
    "cd_sensitivity_drop_iperp": cd_sensitivity_drop_iperp,
}


def cd_all_variants(labels: List[str], target: str) -> Dict[str, float]:
    """Compute all three A04 CD variants + the I_perp rate for one item.

    Returns:
        Dict with keys ``cd_primary``, ``cd_sensitivity_frozen``,
        ``cd_sensitivity_drop_iperp`` and ``iperp_rate``.
    """
    out = {name: fn(labels, target) for name, fn in CD_VARIANTS.items()}
    out["iperp_rate"] = iperp_rate(labels)
    return out
