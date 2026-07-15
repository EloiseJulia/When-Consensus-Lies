# Reconstruction Design Fork — multi-axis deletion vs the reversal  (2026-07-15, owner decision)

> Surfaced by the code_spec reconstruction audit (GPT, 5 BLOCKER + 1 MAJOR) + the Manager's empirical
> default-check. The target/default REVERSAL works at full deletion, but the frozen per-variant
> construction invariant is structurally incompatible with the reversal for MULTI-AXIS (k≥2) tasks.
> This needs an owner ruling because it touches (a) the per-variant invariant (an owner ruling) and
> (b) how H1b (CD rises with ambiguity level k) is operationalized.

## Evidence
- **Reversal works (Manager default-check, temp=0, on the reconstructed k2_all tasks):** all 4
  H1_external code tasks → BOTH mistral-small AND llama-3.3-70b default to the SAME wrong foil I1
  (convergent delusion). The old benchmark gave CD≈0 here; the reversal elicits the phenomenon. ✓
- **Partial (k1) variants are broken (audit, BLOCKERs):** deleting one axis while the other stays
  specified leaks the target / lets a foil contradict the prompt; and secondary axes often have
  target=default (e.g. quarter labels are conventionally 1-indexed) so deleting them doesn't trap.
- **H2 `sortnum` too easy:** weak models already resolve it (both audit + default-check) → no
  weak-fails/reasoner-resolves gradient.

## Root cause (structural)
The frozen invariant `len(key_questions) == ambiguity_level == len(interpretations) - 1` assumes ONE foil
per deleted axis (single-axis deviations from I0). That worked under the OLD design (target = default:
each foil was a non-default deviation the model avoided). Under the REVERSAL (target = non-default):
1. The model, when k axes are deleted, defaults on ALL of them → its actual output is the
   **combined all-defaults** answer. The 1-foil-per-axis scheme does not label that combined output →
   it becomes I_perp, not a counted convergent-delusion foil.
2. For a multi-axis reversed task, EVERY axis must independently have target≠default. Such fully
   independent non-default conventions are scarce, and partial deletion leaves retained axes specifying
   the target. Hence the k1 leakage.
In short: **clean reversed traps are naturally single-axis.**

## Options
**Option A (recommended) — single-axis convention as the unit; stack for the k-gradient.**
- Each external convention is ONE axis where target≠default. A "level-k" task BUNDLES k INDEPENDENT
  such conventions in one full spec. Deleting all k → the model defaults on all k.
- Interpretation set: `I0` (all conventions at their non-default target) + `I1` (the COMBINED all-default
  foil = what a defaulting model produces). Optionally add the k single-axis partial foils if models
  actually emit them (empirically). `key_questions` = the k deleted conventions.
- **Invariant adjustment (owner-approved):** replace `len(interpretations)-1 == k` with:
  `len(key_questions) == k` AND "a combined-all-default foil (`I1`) is present" AND 100%
  distinguishability. (The metric is unchanged; this only fixes how the reversed interpretation set is
  structured.) H1b is measured on the combined-default foil across k-levels.
- k0 control unchanged (fully specified; single interpretation).
- Pros: fair, empirically validated at full deletion, no leakage (every deletion removes a convention
  whose default is a wrong foil). Cons: needs the invariant tweak; H1b tested via bundled conventions.

**Option B — full multi-axis cross-product foils.** Label every "default on a subset of deleted axes"
combination (2^k−1 foils). Fair + complete but foil-count explodes and still breaks the `==k` invariant
(interps-1 = 2^k−1). Not recommended (complexity, sparse foils rarely hit).

**Option C — single-axis only (k∈{0,1}); drop within-benchmark H1b.** Cleanest construction; but H1b
(CD monotonic in k) becomes untestable within the benchmark (would be dropped or deferred). Weakens the
pre-registered contribution.

## Recommendation
**Option A.** It preserves H1b (via bundled independent conventions + a combined-default foil), keeps
every deletion fair (no leakage), matches the empirical success, and needs only a small, transparent
adjustment to the per-variant invariant (documented as a construction amendment; metric stays frozen).
Also: revise/relabel the H2 items — pursue clean H2 (weak-fail/reasoner-resolve) gradients where they
occur NATURALLY (e.g. data_analysis median-under-skew), not forced into code_spec; the empirical
default-check remains the final arbiter of every H1/H2 tag.

## If Option A approved — fixes to the code_spec slice
1. Restructure problems so each deletable axis is an independent non-default convention; add the
   combined-all-default foil `I1`; adjust the invariant + tests.
2. Fix the MAJOR: add a negative rounding tie (e.g. `-0.125 → "(0.13)"`) so half-up vs half-even is
   distinguished on negatives.
3. Re-run the empirical default-check per k-level (H1 → defaults to combined foil; rising with k).
4. Reclassify/revise `sortnum` (H2) or move the H2 demonstrator to data_analysis.
Then re-audit cross-family; owner reversed spot-check gate before scaling.
