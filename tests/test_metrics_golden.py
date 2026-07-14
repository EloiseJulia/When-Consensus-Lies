"""Test suite: Golden metric assertions (pre-registration anchor).

WRITE THIS FIRST per HARD LAW 7: executable gold before any experiment runs.
These are the golden cases with HAND-CALCULATED expected values.
"""

from harness.metrics import (
    false_consensus_rate, 
    convergent_delusion,
    a_maj,
    ece,
    confidence_accuracy_slope
)


def test_full_convergent_delusion():
    """All agents wrong on the SAME label → convergent_delusion = 1.0.
    
    HAND CALCULATION: 5 agents all say "I1", target is "I0"
    Wrong labels: ["I1", "I1", "I1", "I1", "I1"]
    Max wrong count: 5
    Total agents: 5
    Result: 5/5 = 1.0
    """
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
    
    HAND CALCULATION: labels = ["I1", "I2", "I3", "I_perp", "I_perp"], target = "I0"
    Wrong labels: all 5 (none match target)
    Counts: I1→1, I2→1, I3→1, I_perp→2
    Max wrong count: 2 (I_perp)
    Total agents: 5
    Result: 2/5 = 0.4
    """
    labels = ["I1", "I2", "I3", "I_perp", "I_perp"]
    target = "I0"
    
    result = false_consensus_rate(labels, target)
    
    # EXACT expected value from hand calculation
    assert result == 0.4, f"Expected 0.4, got {result}"
    assert result < 0.5, "Low delusion must be < 0.5"


def test_zero_convergent_delusion():
    """All agents correct → convergent_delusion = 0.0.
    
    HAND CALCULATION: all labels = "I0", target = "I0"
    Wrong labels: [] (empty)
    Result: 0.0 (no wrong labels exist)
    """
    labels = ["I0"] * 5
    target = "I0"
    
    result = false_consensus_rate(labels, target)
    
    assert result == 0.0, f"Expected 0.0 (no delusion), got {result}"


def test_partial_convergent_delusion():
    """Some correct, some converge on same wrong → partial delusion.
    
    HAND CALCULATION: labels = ["I0", "I0", "I1", "I1", "I1"], target = "I0"
    Wrong labels: ["I1", "I1", "I1"] (3 agents wrong)
    Max wrong count: 3 (all on I1)
    Total agents: 5
    Result: 3/5 = 0.6
    """
    labels = ["I0", "I0", "I1", "I1", "I1"]
    target = "I0"
    
    result = false_consensus_rate(labels, target)
    
    assert result == 0.6, f"Expected 0.6, got {result}"


def test_empty_labels():
    """Edge case: empty labels list."""
    result = false_consensus_rate([], "I0")
    assert result == 0.0


# a_maj tie handling tests (order-independent)
def test_a_maj_strict_tie_returns_zero():
    """Two labels tie for most common → no unique majority → 0.0.
    
    HAND CALCULATION: ["I0", "I1"], both have count 1
    Tie at count=1 → no unique winner → 0.0
    (Order-independent: ["I1", "I0"] must also return 0.0)
    """
    from harness.metrics import a_maj
    
    # Test both orderings
    assert a_maj(["I0", "I1"], "I0") == 0.0
    assert a_maj(["I1", "I0"], "I0") == 0.0
    assert a_maj(["I0", "I1"], "I1") == 0.0


def test_a_maj_unique_plurality_for_target():
    """Target is UNIQUE strict plurality → 1.0.
    
    HAND CALCULATION: ["I0", "I0", "I1"]
    Counts: I0→2, I1→1
    Unique winner: I0
    Target: I0 → matches → 1.0
    """
    from harness.metrics import a_maj
    
    assert a_maj(["I0", "I0", "I1"], "I0") == 1.0


def test_a_maj_unique_plurality_not_for_target():
    """Another label wins unique plurality → 0.0.
    
    HAND CALCULATION: ["I1", "I1", "I0"]
    Counts: I1→2, I0→1
    Unique winner: I1
    Target: I0 → does not match → 0.0
    """
    from harness.metrics import a_maj
    
    assert a_maj(["I1", "I1", "I0"], "I0") == 0.0


# ECE golden test with hand-calculated value
def test_ece_hand_calculated():
    """ECE with known expected value.
    
    HAND CALCULATION with n_bins=10 (default):
    confidences = [0.9, 0.9], correct = [True, False]
    
    Both fall in bin 9 [0.9, 1.0):
      bin_idx = int(0.9 * 10) = 9
      bin_totals[9] = 2
      bin_corrects[9] = 1 (one True)
      bin_confs[9] = 0.9 + 0.9 = 1.8
      
    Per-bin calculation:
      avg_conf = 1.8 / 2 = 0.9
      accuracy = 1 / 2 = 0.5
      weight = 2 / 2 = 1.0
      error = |0.9 - 0.5| = 0.4
      
    ECE = 1.0 * 0.4 = 0.4
    """
    confidences = [0.9, 0.9]
    correct = [True, False]
    
    result = ece(confidences, correct, n_bins=10)
    
    assert abs(result - 0.4) < 1e-9, f"Expected 0.4, got {result}"


# confidence_accuracy_slope golden test with hand-calculated value
def test_confidence_accuracy_slope_hand_calculated():
    """Slope of correctness ~ confidence with known expected value.
    
    HAND CALCULATION:
    confidences = [0.2, 0.4, 0.6, 0.8]
    correct = [False, False, True, True] → as floats: [0.0, 0.0, 1.0, 1.0]
    
    Step 1: Compute means
      mean_conf = (0.2 + 0.4 + 0.6 + 0.8) / 4 = 2.0 / 4 = 0.5
      mean_correct = (0.0 + 0.0 + 1.0 + 1.0) / 4 = 2.0 / 4 = 0.5
    
    Step 2: Compute variance of confidence
      var_conf = [(0.2-0.5)² + (0.4-0.5)² + (0.6-0.5)² + (0.8-0.5)²] / 4
               = [(-0.3)² + (-0.1)² + (0.1)² + (0.3)²] / 4
               = [0.09 + 0.01 + 0.01 + 0.09] / 4
               = 0.2 / 4
               = 0.05
    
    Step 3: Compute covariance
      cov = [(0.2-0.5)×(0.0-0.5) + (0.4-0.5)×(0.0-0.5) + 
             (0.6-0.5)×(1.0-0.5) + (0.8-0.5)×(1.0-0.5)] / 4
          = [(-0.3)×(-0.5) + (-0.1)×(-0.5) + (0.1)×(0.5) + (0.3)×(0.5)] / 4
          = [0.15 + 0.05 + 0.05 + 0.15] / 4
          = 0.4 / 4
          = 0.1
    
    Step 4: Compute slope
      slope = cov / var_conf = 0.1 / 0.05 = 2.0
    
    INTERPRETATION: Perfect positive relationship (slope = 2.0)
    Higher confidence perfectly associates with higher accuracy.
    """
    confidences = [0.2, 0.4, 0.6, 0.8]
    correct = [False, False, True, True]
    
    result = confidence_accuracy_slope(confidences, correct)
    
    assert abs(result - 2.0) < 1e-9, f"Expected 2.0, got {result}"


def test_confidence_accuracy_slope_zero_variance():
    """Zero variance in confidence → undefined slope → return 0.0.
    
    HAND CALCULATION:
    confidences = [0.5, 0.5, 0.5]
    All identical → variance = 0 → slope mathematically undefined → return 0.0
    """
    confidences = [0.5, 0.5, 0.5]
    correct = [True, False, True]
    
    result = confidence_accuracy_slope(confidences, correct)
    
    assert result == 0.0, f"Expected 0.0 for zero-variance case, got {result}"


def test_confidence_accuracy_slope_empty():
    """Empty inputs → 0.0."""
    assert confidence_accuracy_slope([], []) == 0.0


def test_confidence_accuracy_slope_length_mismatch():
    """Length mismatch → 0.0."""
    assert confidence_accuracy_slope([0.5, 0.7], [True]) == 0.0
