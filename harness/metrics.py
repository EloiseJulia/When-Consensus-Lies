"""Metrics implementation — REAL math (science-critical, not stubs).

PRIMARY METRIC: convergent_delusion (false_consensus_rate)
  = fraction of agents concentrated on the SAME single wrong label
  ≠ binary ρ (which only measures any-wrong vs correct)

SECONDARY METRICS (diagnostic/bridge, NOT primary):
  - marginal_rho: binary error correlation (bridge to prior literature)
  - confidence_accuracy_slope: calibration ranking diagnostic
  - ece: expected calibration error
  - a_maj: majority-vote accuracy

CRITICAL: convergent_delusion is PRIMARY. Do NOT treat binary ρ or
marginal_rho as primary — they cannot distinguish concentrated vs scattered errors.
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


def error_indicators(labels: List[str], target: str) -> List[int]:
    """Binary error vector E where E_k = 1 if agent/task k is wrong, else 0."""
    return [0 if label == target else 1 for label in labels]


def _pearson(x: List[float], y: List[float]):
    """Pearson correlation, or None if either series has zero variance."""
    n = len(x)
    if n == 0 or len(y) != n:
        return None
    mx = sum(x) / n
    my = sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx == 0 or syy == 0:
        return None  # correlation undefined when a series is constant
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    return sxy / math.sqrt(sxx * syy)


def marginal_rho(error_matrix: List[List[int]]) -> float:
    """Mean pairwise error correlation across agents (SECONDARY bridge metric).

    Implements marginal ρ = mean over agent pairs of corr(E_i, E_j), where E_i is
    agent i's binary error vector ACROSS TASKS (1 = wrong on that task). This is the
    binary-correlation bridge to prior literature and is NOT the primary metric —
    it cannot tell whether agents fail on the SAME wrong interpretation, only whether
    their errors co-occur. Use `false_consensus_rate` (convergent_delusion) as primary.

    Args:
        error_matrix: rows = agents, cols = tasks; each entry in {0, 1} (1 = error).
                      Build a row with `error_indicators(labels, target)`.

    Returns:
        Mean Pearson correlation over pairs with defined variance; 0.0 if none
        (e.g. all agents always correct or always wrong → no error variance to
        correlate, so ρ is reported as 0.0 rather than a spurious 1.0).
    """
    n = len(error_matrix)
    if n < 2:
        return 0.0
    corrs = []
    for i in range(n):
        for j in range(i + 1, n):
            c = _pearson(error_matrix[i], error_matrix[j])
            if c is not None:
                corrs.append(c)
    return sum(corrs) / len(corrs) if corrs else 0.0


def a_maj(labels: List[str], target: str) -> float:
    """Majority-vote accuracy with strict, order-independent tie handling.

    Returns 1.0 only if `target` is the UNIQUE strict plurality winner. If two or
    more labels tie for the top count there is no majority winner, so the result
    is 0.0 regardless of list order (avoids order-dependent scoring).

    Args:
        labels: List of agent labels
        target: The correct label

    Returns:
        1.0 if target is the unique modal label, else 0.0
    """
    if not labels:
        return 0.0

    counts = {}
    for label in labels:
        counts[label] = counts.get(label, 0) + 1

    max_count = max(counts.values())
    winners = [label for label, c in counts.items() if c == max_count]

    return 1.0 if len(winners) == 1 and winners[0] == target else 0.0


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


def confidence_accuracy_slope(confidences: List[float], correct: List[bool]) -> float:
    """Compute the slope of OLS linear regression of correctness on confidence.
    
    This is a SECONDARY DIAGNOSTIC metric that measures the confidence-accuracy
    relationship: positive slope means higher confidence associates with higher
    accuracy (better-ranked calibration), negative slope means miscalibration.
    
    Formula: slope = cov(confidence, correct) / var(confidence)
    where correct is treated as 1.0 for True, 0.0 for False.
    
    Returns 0.0 if:
      - confidences is empty
      - lengths mismatch
      - confidence has zero variance (slope is mathematically undefined)
    
    Examples:
        >>> confidence_accuracy_slope([0.2, 0.4, 0.6, 0.8], [False, False, True, True])
        2.0  # Perfect positive relationship
        
        >>> confidence_accuracy_slope([0.5, 0.5, 0.5], [True, False, True])
        0.0  # Zero variance in confidence → undefined slope
    
    Args:
        confidences: List of confidence scores (floats, typically in [0, 1])
        correct: List of boolean correctness indicators
    
    Returns:
        Float: OLS slope of correct ~ confidence, or 0.0 if undefined
    """
    if not confidences or len(confidences) != len(correct):
        return 0.0
    
    n = len(confidences)
    
    # Convert correct to float
    correct_float = [1.0 if c else 0.0 for c in correct]
    
    # Compute means
    mean_conf = sum(confidences) / n
    mean_correct = sum(correct_float) / n
    
    # Compute variance of confidence
    var_conf = sum((c - mean_conf) ** 2 for c in confidences) / n
    
    # If zero variance, slope is undefined
    if var_conf == 0.0:
        return 0.0
    
    # Compute covariance
    cov = sum((conf - mean_conf) * (corr - mean_correct) 
              for conf, corr in zip(confidences, correct_float)) / n
    
    # Return slope
    return cov / var_conf
