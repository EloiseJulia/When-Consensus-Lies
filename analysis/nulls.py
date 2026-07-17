"""Analysis-layer null: population-level cd_primary shuffle null (non-frozen).

# Implementer model family: Claude/Anthropic

BLOCKER 2 FIX — metric-consistent R1 null:
  The pre-registered §11 gate (b) compares real convergent delusion against its
  null distribution under random label assignment.  Amendment 04 makes cd_primary
  (not false_consensus_rate) the PRIMARY metric.  Using the frozen
  ``label_shuffle_null`` (which calls ``false_consensus_rate``) for the null but
  ``cd_primary`` for the real comparison produces INCOMPATIBLE metrics: I_perp
  labels inflate false_consensus_rate (I_perp is eligible as modal wrong) but
  leave cd_primary unchanged (I_perp is ineligible).  A real primary CD of 0.4
  could yield a false_consensus_rate null of 0.605 — a false PASS.

  Fix: this module provides ``cd_primary_shuffle_null``, which uses the SAME
  cross-item reshuffle ALGORITHM as ``harness/nulls.label_shuffle_null`` but
  applies ``analysis.cd.cd_primary`` at each permutation step instead of
  ``harness.metrics.false_consensus_rate``.  Real and null are now measured on
  the same metric.

  ``harness/nulls.py`` remains FROZEN and UNCHANGED.  The frozen
  ``label_shuffle_null`` value may still be reported as a SECONDARY diagnostic
  (Sensitivity A companion metric), but the gate PASS/FAIL decision uses
  ``cd_primary_shuffle_null`` exclusively.

Usage in the §11 gate:
  The null is computed PER CONDITION (H1_external × method × model_class ×
  ambiguity_k).  Conditions with fewer than ``MIN_ITEMS_FOR_NULL`` ensemble cells
  are marked INCONCLUSIVE and CANNOT contribute to a PASS.

Constants:
  NULL_CD_TOLERANCE : float
      Threshold below which null_cd is considered "≈ 0" (per §11 gate criterion
      "convergent delusion ≈ 0 under shuffle").  Default 0.10 (10 pp).
  MIN_ITEMS_FOR_NULL : int
      Minimum number of ensemble cells required for the shuffle null to be
      non-degenerate.  Default 2 (cross-item shuffle on 1 item is a within-item
      permutation, which is a no-op for cd_primary).

Auditor note (for hostile cross-family review):
  ``cd_primary_shuffle_null`` is structurally identical to the frozen
  ``label_shuffle_null`` with ONE substitution: the per-permutation metric call
  is ``analysis.cd.cd_primary`` instead of ``harness.metrics.false_consensus_rate``.
  Test ``test_gate_b_uses_cd_primary_not_false_consensus_rate`` uses labels where
  the two metrics diverge (all-I_perp: cd_primary → 0, false_consensus_rate → 1)
  to confirm the correct function is called.
"""
from __future__ import annotations

import random
from typing import List

from analysis.cd import cd_primary as _cd_primary

#: Null CD is "≈ 0" when ≤ this threshold (§11 gate criterion).
NULL_CD_TOLERANCE: float = 0.10

#: Minimum ensemble cells per condition for a meaningful cross-item shuffle.
MIN_ITEMS_FOR_NULL: int = 2


def cd_primary_shuffle_null(
    items_labels: List[List[str]],
    target: str,
    n_perm: int = 1000,
    seed: int = 42,
) -> float:
    """Population-level label-shuffle null using cd_primary (Amendment 04 primary metric).

    Implements the same cross-item reshuffle algorithm as the frozen
    ``harness.nulls.label_shuffle_null``, but applies ``analysis.cd.cd_primary``
    (not the frozen ``false_consensus_rate``) so real CD and null CD are measured
    on the SAME metric (BLOCKER 2 fix).

    Algorithm (identical to frozen null, metric substituted):
      For each permutation:
        1. Pool ALL agent labels from every item in ``items_labels`` into one
           flat list (preserves exact marginal label frequencies).
        2. Shuffle the pool with the seeded RNG (sampling without replacement).
        3. Deal labels back into items in their original order, each item
           receiving exactly as many labels as it had originally.
        4. Compute mean cd_primary over items for this permutation.
      Return the mean over ``n_perm`` permutations → CD₀.

    Determinism: uses ``random.Random(seed)`` internally.  Identical seed values
    give identical CD₀ results across calls (fully reproducible).

    Args:
        items_labels: List of per-item label lists.  Each inner list holds all
            agent labels for one ensemble cell (one item × one seed in the runner
            grid).  All cells must be from the same condition.  Empty inner lists
            contribute 0.0 cd_primary.
        target: Correct interpretation label (e.g. ``"I0"``).  Passed to
            ``cd_primary`` to identify the target; I_perp is ineligible as modal
            wrong by cd_primary definition.
        n_perm: Number of shuffled permutations to average over.
        seed: Integer RNG seed for reproducibility.

    Returns:
        CD₀ (float in [0, 1]): mean cd_primary over ``n_perm`` shuffled
        permutations.  Returns 0.0 if ``items_labels`` is empty.

    Note:
        For a single-cell condition, the cross-item shuffle reduces to a
        within-cell permutation, which is a no-op for cd_primary (only the label
        multiset matters).  This function returns CD_real in that degenerate case.
        The null is only meaningful for ≥ ``MIN_ITEMS_FOR_NULL`` cells.
    """
    if not items_labels:
        return 0.0

    item_sizes = [len(item) for item in items_labels]
    n_items = len(item_sizes)

    # Pool all labels (preserves exact marginal frequencies per the preregistered
    # R1 algorithm in harness/nulls.py).
    pool: List[str] = []
    for item in items_labels:
        pool.extend(item)

    rng = random.Random(seed)
    total_cd = 0.0

    for _ in range(n_perm):
        # Shuffle a copy — sampling without replacement from the pooled multiset.
        shuffled = pool[:]
        rng.shuffle(shuffled)

        # Deal back into items preserving original sizes.
        offset = 0
        perm_cd_sum = 0.0
        for size in item_sizes:
            item_labels = shuffled[offset : offset + size]
            offset += size
            perm_cd_sum += _cd_primary(item_labels, target)

        total_cd += perm_cd_sum / n_items

    return total_cd / n_perm
