"""Metrics implementation — REAL math (science-critical, not stubs).

PRIMARY METRIC: convergent_delusion (false_consensus_rate)
  = fraction of agents concentrated on the SAME single wrong label
  ≠ binary ρ (which only measures any-wrong vs correct)

SECONDARY: marginal_rho (binary correlation bridge to prior literature)
"""

from typing import List, Tuple
import math


def false_consensus_rate(labels: List[str], target: str) -> float:
    """Compute convergent delusion: fraction agreeing on the SAME wrong label.
    
    This is the PRIMARY METRIC for the paper. It measures whether agents not only
    fail, but fail *in the same way* (consensus on a specific wrong interpretation).
    
    Algorithm:
        1. Filter out all target-correct labels
        2. Find the most common wrong label
        3. Return its frequency among all agents
    
    Examples:
        >>> false_consensus_rate(["I1"]*5, target="I0")
        1.0  # All 5 wrong on the SAME I1 → full convergent delusion
        
        >>> false_consensus_rate(["I1","I2","I3","I_perp","I_perp"], target="I0")
        0.4  # Max wrong is I_perp with 2/5 → less than half, low delusion
        
        >>> false_consensus_rate(["I0"]*5, target="I0")
        0.0  # All correct → no delusion
        
        >>> false_consensus_rate(["I0","I0","I1","I1","I1"], target="I0")
        0.6  # 3/5 converged on wrong I1
    
    Args:
        labels: List of agent labels (e.g., ["I0", "I1", "I1", "I_perp"])
        target: The correct label (e.g., "I0")
    
    Returns:
        Float in [0, 1]: share of agents on the modal wrong label
    """
    if not labels:
        return 0.0
    
    # Count frequencies of all wrong labels
    wrong_counts = {}
    for label in labels:
        if label != target:
            wrong_counts[label] = wrong_counts.get(label, 0) + 1
    
    # If no one is wrong, delusion is zero
    if not wrong_counts:
        return 0.0
    
    # Find max count of any single wrong label
    max_wrong_count = max(wrong_counts.values())
    
    # Return as fraction of total population
    return max_wrong_count / len(labels)


# Alias for clarity in paper
convergent_delusion = false_consensus_rate


def marginal_rho(labels: List[str], target: str) -> float:
    """Compute marginal agreement rate (binary: correct vs any-wrong).
    
    SECONDARY METRIC: bridges to prior literature on binary correlation.
    Does NOT distinguish which wrong interpretation agents land on.
    
    Args:
        labels: List of agent labels
        target: The correct label
    
    Returns:
        Float in [0, 1]: Phi coefficient proxy (share agreeing on majority label)
    """
    if not labels:
        return 0.0
    
    # Count correct vs wrong
    correct_count = sum(1 for label in labels if label == target)
    wrong_count = len(labels) - correct_count
    
    # Majority label
    majority_count = max(correct_count, wrong_count)
    
    return majority_count / len(labels)


def a_maj(labels: List[str], target: str) -> float:
    """Compute majority-vote accuracy.
    
    Args:
        labels: List of agent labels
        target: The correct label
    
    Returns:
        1.0 if majority label equals target, else 0.0
    """
    if not labels:
        return 0.0
    
    # Count frequencies
    counts = {}
    for label in labels:
        counts[label] = counts.get(label, 0) + 1
    
    # Find majority label (ties go to first occurrence)
    majority_label = max(labels, key=lambda x: (counts[x], -labels.index(x)))
    
    return 1.0 if majority_label == target else 0.0


def ece(confidences: List[float], correct: List[bool], n_bins: int = 10) -> float:
    """Compute Expected Calibration Error.
    
    Standard calibration metric: bins predictions by confidence, computes
    |confidence - accuracy| per bin, weighted by bin size.
    
    Args:
        confidences: List of confidence scores in [0, 1]
        correct: List of boolean correctness indicators
        n_bins: Number of bins for calibration curve
    
    Returns:
        ECE value (lower is better calibrated)
    """
    if not confidences or len(confidences) != len(correct):
        return 0.0
    
    # Bin by confidence
    bin_edges = [i / n_bins for i in range(n_bins + 1)]
    bin_totals = [0] * n_bins
    bin_corrects = [0] * n_bins
    bin_confs = [0.0] * n_bins
    
    for conf, corr in zip(confidences, correct):
        # Find bin index
        bin_idx = min(int(conf * n_bins), n_bins - 1)
        bin_totals[bin_idx] += 1
        bin_corrects[bin_idx] += int(corr)
        bin_confs[bin_idx] += conf
    
    # Compute weighted calibration error
    total = len(confidences)
    ece_sum = 0.0
    
    for i in range(n_bins):
        if bin_totals[i] > 0:
            avg_conf = bin_confs[i] / bin_totals[i]
            accuracy = bin_corrects[i] / bin_totals[i]
            weight = bin_totals[i] / total
            ece_sum += weight * abs(avg_conf - accuracy)
    
    return ece_sum
