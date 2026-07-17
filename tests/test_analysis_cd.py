"""GOLDEN Amendment-04 CD tests (Deliverable 1) — exact, hand-calculated.

Model family of implementer: Claude (Anthropic). Auditor: NON-Claude (GPT).

Per Hard Law 7 these are DETERMINISTIC executable-gold assertions for the A04
convergent-delusion analysis layer. They pin the exact values in the signed
amendment (paper/preregistration/2026-07-15-amendment-04-iperp-treatment.md)
and prove SENSITIVITY A is the FROZEN metric (imported, not reimplemented).
"""

import inspect

from analysis.cd import (
    cd_all_variants,
    cd_primary,
    cd_sensitivity_drop_iperp,
    cd_sensitivity_frozen,
    iperp_rate,
)
from harness.metrics import false_consensus_rate


# --------------------------------------------------------------------------- #
# The headline golden case from the amendment diagnostic.
# labels = ["I1","I1","I_perp","I_perp","I_perp"], target "I0":
#   frozen    = 3/5 = 0.60  (I_perp is the modal wrong, eligible)
#   primary   = 2/5 = 0.40  (I1 modal among ENUMERATED wrong; I_perp ineligible,
#                            but stays in N=5)
#   drop_iperp= 2/2 = 1.0   (I1 is 2/2 among the 2 parseable non-target agents)
#   iperp_rate= 3/5 = 0.60
# --------------------------------------------------------------------------- #
GOLDEN_LABELS = ["I1", "I1", "I_perp", "I_perp", "I_perp"]
GOLDEN_TARGET = "I0"


def test_golden_frozen():
    assert cd_sensitivity_frozen(GOLDEN_LABELS, GOLDEN_TARGET) == 0.60


def test_golden_primary():
    assert cd_primary(GOLDEN_LABELS, GOLDEN_TARGET) == 0.40


def test_golden_drop_iperp():
    assert cd_sensitivity_drop_iperp(GOLDEN_LABELS, GOLDEN_TARGET) == 1.0


def test_golden_iperp_rate():
    assert iperp_rate(GOLDEN_LABELS) == 0.60


def test_golden_all_variants_bundle():
    out = cd_all_variants(GOLDEN_LABELS, GOLDEN_TARGET)
    assert out == {
        "cd_primary": 0.40,
        "cd_sensitivity_frozen": 0.60,
        "cd_sensitivity_drop_iperp": 1.0,
        "iperp_rate": 0.60,
    }


def test_sensitivity_a_is_the_frozen_metric():
    """SENSITIVITY A must be the FROZEN metric, imported (not reimplemented)."""
    # Same value as the frozen function on many inputs...
    cases = [
        (["I1", "I1", "I_perp", "I_perp", "I_perp"], "I0"),
        (["I0", "I0", "I1", "I1", "I1"], "I0"),
        (["I1", "I2", "I3", "I_perp", "I_perp"], "I0"),
        (["I_perp"] * 4, "I0"),
        ([], "I0"),
    ]
    for labels, target in cases:
        assert cd_sensitivity_frozen(labels, target) == false_consensus_rate(labels, target)
    # ...and structurally: cd_sensitivity_frozen delegates to false_consensus_rate.
    src = inspect.getsource(cd_sensitivity_frozen)
    assert "false_consensus_rate" in src


# --------------------------------------------------------------------------- #
# Additional crafted cases.
# --------------------------------------------------------------------------- #

def test_all_correct_is_zero_everywhere():
    labels = ["I0"] * 5
    assert cd_primary(labels, "I0") == 0.0
    assert cd_sensitivity_frozen(labels, "I0") == 0.0
    assert cd_sensitivity_drop_iperp(labels, "I0") == 0.0
    assert iperp_rate(labels) == 0.0


def test_all_iperp_primary_zero_frozen_one():
    labels = ["I_perp"] * 5
    # PRIMARY: no enumerated wrong label -> 0.0 (I_perp ineligible convergent).
    assert cd_primary(labels, "I0") == 0.0
    # SENSITIVITY A (frozen): I_perp eligible -> full 1.0 (the spurious upper bound).
    assert cd_sensitivity_frozen(labels, "I0") == 1.0
    # SENSITIVITY B: no parseable agents remain -> 0.0.
    assert cd_sensitivity_drop_iperp(labels, "I0") == 0.0
    assert iperp_rate(labels) == 1.0


def test_full_enumerated_convergence():
    labels = ["I1"] * 5
    assert cd_primary(labels, "I0") == 1.0
    assert cd_sensitivity_frozen(labels, "I0") == 1.0
    assert cd_sensitivity_drop_iperp(labels, "I0") == 1.0
    assert iperp_rate(labels) == 0.0


def test_iperp_dilutes_primary_but_not_drop():
    # 3 on I1, 2 on I_perp, target I0.
    labels = ["I1", "I1", "I1", "I_perp", "I_perp"]
    assert cd_primary(labels, "I0") == 3 / 5           # I1 modal enumerated, N=5
    assert cd_sensitivity_frozen(labels, "I0") == 3 / 5  # I1 also frozen modal
    assert cd_sensitivity_drop_iperp(labels, "I0") == 1.0  # I1 3/3 among parseable
    assert iperp_rate(labels) == 2 / 5


def test_iperp_would_be_modal_but_ineligible_in_primary():
    # I_perp (3) exceeds I1 (1); frozen picks I_perp, primary must pick I1.
    labels = ["I1", "I_perp", "I_perp", "I_perp", "I0"]
    assert cd_sensitivity_frozen(labels, "I0") == 3 / 5   # I_perp modal wrong
    assert cd_primary(labels, "I0") == 1 / 5              # only enumerated wrong is I1
    assert cd_sensitivity_drop_iperp(labels, "I0") == 1 / 2  # among [I1, I0]: I1 1/2
    assert iperp_rate(labels) == 3 / 5


def test_partial_default_combos_count_as_enumerated_wrong():
    """Amdt-03: partial-default combination labels are genuine enumerated wrong
    interpretations (NOT I_perp) and are eligible as the primary convergent label."""
    # "I1+default" / "I2_partial" are enumerated wrong labels, not I_perp.
    labels = ["I1+default", "I1+default", "I2_partial", "I_perp", "I0"]
    # Enumerated wrong: I1+default (2), I2_partial (1). Modal = 2, N=5.
    assert cd_primary(labels, "I0") == 2 / 5
    # Frozen: same modal (I1+default 2/5) since I_perp only 1.
    assert cd_sensitivity_frozen(labels, "I0") == 2 / 5
    # Drop I_perp -> [I1+default, I1+default, I2_partial, I0] -> 2/4.
    assert cd_sensitivity_drop_iperp(labels, "I0") == 2 / 4
    assert iperp_rate(labels) == 1 / 5


def test_tie_among_enumerated_wrong_reports_modal_count():
    # I1 (2) and I2 (2) tie; modal-wrong COUNT is 2 (frequency, not uniqueness).
    labels = ["I1", "I1", "I2", "I2", "I_perp"]
    assert cd_primary(labels, "I0") == 2 / 5
    assert iperp_rate(labels) == 1 / 5


def test_empty_labels_safe():
    assert cd_primary([], "I0") == 0.0
    assert cd_sensitivity_frozen([], "I0") == 0.0
    assert cd_sensitivity_drop_iperp([], "I0") == 0.0
    assert iperp_rate([]) == 0.0


def test_variants_bounded_relationship():
    """PRIMARY <= FROZEN always (I_perp can only add eligibility, never remove)."""
    cases = [
        (["I1", "I1", "I_perp", "I_perp", "I_perp"], "I0"),
        (["I1", "I_perp", "I_perp", "I_perp", "I0"], "I0"),
        (["I1", "I2", "I2", "I_perp", "I0"], "I0"),
        (["I_perp"] * 3 + ["I1", "I1"], "I0"),
    ]
    for labels, target in cases:
        assert cd_primary(labels, target) <= cd_sensitivity_frozen(labels, target) + 1e-12
