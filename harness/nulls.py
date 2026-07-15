"""Robustness null machinery — pre-registered R1 label-shuffle null.

Pre-registration reference: paper/preregistration/2026-07-15-prereg.md §4 R1.

KEY DESIGN RATIONALE — why within-item permutation is a no-op:
---------------------------------------------------------------
`false_consensus_rate(labels, target)` (alias `convergent_delusion`) depends
ONLY on the per-item label multiset — specifically, it computes which wrong label
appears most often WITHIN that item and divides by the total number of agents on
that item. Shuffling the labels WITHIN a single item does not change which labels
are present or how many of each there are; the multiset (and therefore CD) is
invariant under within-item permutation. A null built on within-item permutation
would always return CD_real, making it completely uninformative.

Why the cross-item reshuffle is the correct null:
-------------------------------------------------
By pooling ALL agent labels from ALL items in a condition and randomly dealing
them back into the original (item, agent) slot shape — preserving each item's
agent count but destroying the association between item identity and label — we
create a counterfactual world where labels are assigned independently from the
condition's marginal label frequencies. The resulting CD₀ (average convergent
delusion under this null) answers: "How concentrated would per-item label
distributions be if agents merely sampled from the population-level label
distribution, with no real within-item consensus?"

If CD_real >> CD₀, the real concentration exceeds what marginal frequencies
alone explain — the within-item concentration is genuine, not an artifact of
a skewed label marginal. If CD_real ≈ CD₀, the apparent concentration is
fully explained by the marginal, and the thesis is not supported.

Implementation note on sampling mechanics:
------------------------------------------
Shuffling the pooled label list and dealing labels back into item slots
(each slot gets the next label in the shuffled list) is equivalent to
sampling WITHOUT replacement from the pooled multiset. This preserves the
condition's EXACT marginal label frequencies across the permutation, which
is the pre-registered intended realization (prereg §4 R1).
"""

import random
from typing import List

from harness.metrics import false_consensus_rate


def label_shuffle_null(
    items_labels: List[List[str]],
    target: str,
    n_perm: int = 1000,
    seed: int = 42,
) -> float:
    """Compute CD₀: the R1 label-shuffle null baseline for convergent_delusion.

    Implements the pre-registered (prereg §4 R1, 2026-07-15) POPULATION-LEVEL
    / CROSS-ITEM reshuffle null. All items in `items_labels` must belong to the
    SAME condition (same regime / method / model / ambiguity cell).

    **Why within-item permutation is a no-op (and therefore wrong):**
    `convergent_delusion` depends only on the per-item label *multiset*. Shuffling
    labels within one item leaves the multiset unchanged, so CD is identical before
    and after — a within-item null always returns CD_real and is meaningless as a
    baseline. See module docstring for the full rationale.

    **Cross-item reshuffle algorithm (per permutation):**
    1. Pool ALL agent labels from every item in the condition into one flat list,
       preserving the condition's overall label frequency distribution exactly.
    2. Shuffle the pooled list using the seeded RNG (sampling without replacement
       from the pooled multiset — see module docstring).
    3. Deal the shuffled labels back into items in their original order, each item
       receiving exactly as many labels as it originally had (preserving per-item
       agent counts).
    4. Compute mean convergent_delusion over items for this permutation.
    Average over `n_perm` permutations → CD₀.

    Determinism: uses `random.Random(seed)` internally. Identical `seed` values
    produce identical CD₀ results across calls (fully reproducible).

    Args:
        items_labels: List of per-item label lists. Each inner list holds all
            agent labels for that item. Must all be from the same condition.
            Empty inner lists are supported (contribute 0.0 CD per item).
        target: The correct interpretation label (e.g., "I0"). Passed directly
            to `false_consensus_rate` to identify wrong labels.
        n_perm: Number of shuffled permutations to average over. Default 1000
            gives a stable estimate; increase for smoother CD₀.
        seed: Integer RNG seed for full reproducibility. Default 42.

    Returns:
        CD₀ (float in [0, 1]): mean convergent_delusion averaged over n_perm
        shuffled permutations. Returns 0.0 if `items_labels` is empty.

    Note:
        For a single-item batch, the cross-item shuffle reduces to a within-item
        permutation (there is only one item, so labels can only be rearranged
        within it). This is mathematically a no-op for convergent_delusion, and
        the function will return CD_real in that degenerate case. The null is
        only meaningful when there are multiple items in the condition.
    """
    if not items_labels:
        return 0.0

    # Record each item's slot count so we can deal labels back correctly.
    item_sizes = [len(item) for item in items_labels]
    n_items = len(item_sizes)

    # Pool ALL labels from ALL items (preserves exact marginal frequencies).
    pool: List[str] = []
    for item in items_labels:
        pool.extend(item)

    rng = random.Random(seed)
    total_cd = 0.0

    for _ in range(n_perm):
        # Shuffle a copy of the pooled list (sampling without replacement
        # from the pooled multiset — preserves exact marginal frequencies).
        shuffled = pool[:]
        rng.shuffle(shuffled)

        # Deal labels back into items with their original sizes.
        offset = 0
        perm_cd_sum = 0.0
        for size in item_sizes:
            item_labels = shuffled[offset : offset + size]
            offset += size
            perm_cd_sum += false_consensus_rate(item_labels, target)

        total_cd += perm_cd_sum / n_items

    return total_cd / n_perm
