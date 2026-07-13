"""Test suite: Golden metric assertions (pre-registration anchor).

WRITE THIS FIRST per HARD LAW 7: executable gold before any experiment runs.
These are the three golden cases that define convergent_delusion.
"""

from harness.metrics import false_consensus_rate, convergent_delusion


def test_full_convergent_delusion():
    """All agents wrong on the SAME label → convergent_delusion = 1.0."""
    labels = ["I1"] * 5
    target = "I0"
    
    result = false_consensus_rate(labels, target)
    
    assert result == 1.0, f"Expected 1.0 (full delusion), got {result}"
    
    # Verify alias works identically
    assert convergent_delusion(labels, target) == 1.0


def test_low_convergent_delusion():
    """Agents wrong DIFFERENTLY → low delusion (< 0.5 even though all wrong).
    
    This is the KEY DISTINCTION from binary ρ: binary ρ would be high (all wrong),
    but convergent_delusion is low (no consensus on WHICH wrong interpretation).
    """
    labels = ["I1", "I2", "I3", "I_perp", "I_perp"]
    target = "I0"
    
    result = false_consensus_rate(labels, target)
    
    # Max wrong label is I_perp with 2/5 = 0.4
    assert result == 0.4, f"Expected 0.4, got {result}"
    assert result < 0.5, "Low delusion must be < 0.5"


def test_zero_convergent_delusion():
    """All agents correct → convergent_delusion = 0.0."""
    labels = ["I0"] * 5
    target = "I0"
    
    result = false_consensus_rate(labels, target)
    
    assert result == 0.0, f"Expected 0.0 (no delusion), got {result}"


def test_partial_convergent_delusion():
    """Some correct, some converge on same wrong → partial delusion."""
    labels = ["I0", "I0", "I1", "I1", "I1"]
    target = "I0"
    
    result = false_consensus_rate(labels, target)
    
    # 3 out of 5 on wrong I1 → 0.6
    assert result == 0.6, f"Expected 0.6, got {result}"


def test_empty_labels():
    """Edge case: empty labels list."""
    result = false_consensus_rate([], "I0")
    assert result == 0.0
