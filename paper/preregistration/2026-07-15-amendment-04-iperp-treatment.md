# Pre-Registration Amendment 04 — I_perp treatment in the primary metric  (DRAFT, owner sign-off required)

> Amends the FROZEN pre-registration `paper/preregistration/2026-07-15-prereg.md` (freeze SHA `c0a0393`),
> §3 (Metrics) reporting/treatment layer only. **The frozen metric DEFINITION in `harness/metrics.py`
> (`false_consensus_rate`) is UNCHANGED and remains frozen.** This amendment fixes, *before any full-scale
> run*, how the degenerate `I_perp` bucket is treated in the PRIMARY convergent-delusion analysis, so the
> choice is principled and pre-registered rather than a post-hoc pick. Owner ruling 2026-07-16 (guardrail
> on O1). Must be SIGNED before any full-scale / registered confirmatory run.

## Timestamp / provenance
- Drafted: 2026-07-16 by the Manager, per owner ruling O1 ("report CD with AND without I_perp; the PRIMARY
  I_perp treatment must be principled and pre-registered … if unspecified, file a documented decision/
  amendment BEFORE full-scale — not a post-hoc pick").
- Status: DRAFT → owner signs off → committed as the amendment of record BEFORE full-scale. No registered
  full-scale run has occurred.

## The issue (why this is needed)
`convergent_delusion` = `false_consensus_rate(labels, target)` = fraction of agents on the single MODAL
WRONG label, with N = all agents. The frozen implementation (verified `harness/metrics.py`) treats
`I_perp` — the degenerate "unparseable / off-axis / non-contract" bucket — as an ELIGIBLE modal-wrong
label. But the thesis (report §2.2) is convergence on the **same wrong interpretation I_k**. Multiple
agents landing in `I_perp` for DIFFERENT reasons (different off-axis outputs, parse failures) is NOT
genuine same-interpretation consensus. Counting `I_perp` as a convergent label can therefore INFLATE CD
with a degeneracy that is not the phenomenon (observed directionally: llama hit `I_perp`-"convergence" at
code_spec k2/k3). The prereg §3 says "unparseable → I_perp" but does NOT fix whether `I_perp` is eligible
to be the convergent label — hence this amendment.

## Why `I_perp` should NOT be the primary convergent label (design support)
Under Amendment 03, the benchmark ENUMERATES every `{target, default}` combination over the deleted axes
(the full `2^k'` set, incl. all partial-default combos). A GENUINE shared-wrong convergence therefore has
an enumerated interpretation to land on; the labeler is required (Amdt 03 guardrail) never to send a real
shared-wrong to `I_perp`. Consequently `I_perp` legitimately represents off-axis / unparseable /
answer-format-non-compliant degeneracy — NOT the "same wrong interpretation" the primary metric is meant
to capture.

## The amendment (I_perp treatment — three-part, frozen-metric-preserving)

**PRIMARY (confirmatory) — `convergent_delusion` over ENUMERATED wrong interpretations only.**
The primary convergent-delusion for all H1/H2 decision rules is the modal-wrong share computed over the
ENUMERATED wrong labels `{I1..Im}` only; `I_perp` is NOT eligible to be the convergent label, but `I_perp`
agents REMAIN in the denominator N (they are non-convergence and correctly DILUTE CD). Formally:
`CD_primary = ( max over w ∈ {enumerated wrong labels} of count(w) ) / N_total`, with `count(I_perp)`
excluded from the max. This is computed by a thin ANALYSIS-LAYER function (new code under analysis/ or the
Phase-6 pipeline) that calls / wraps the data — it does **NOT** modify the frozen `false_consensus_rate`
definition. Rationale: conservative and faithful to "consensus on the SAME I_k"; a high `I_perp` rate
depresses (never inflates) the primary CD.

**SENSITIVITY A (the frozen metric as-is) — `I_perp` eligible.** Report `false_consensus_rate` exactly as
frozen (I_perp eligible as the modal wrong, N = all agents). This is the UPPER-BOUND CD and the direct
pin to the frozen definition. Both PRIMARY and SENSITIVITY A are reported for every H1/H2 cell.

**SENSITIVITY B — drop `I_perp` agents from N.** Report CD computed among PARSEABLE agents only
(`I_perp` agents removed from the denominator). This bounds the other direction (what CD looks like if
degenerate agents are excluded entirely). Reported alongside.

**DIAGNOSTIC (first-class, owner-required) — per-condition `I_perp` RATE.** Report the fraction of agents
mapped to `I_perp` for every condition cell as a first-class result. A high `I_perp` rate is itself a
FINDING (most likely FINAL-ANSWER / code-block answer-format-contract non-compliance) and is FIXABLE. We
pre-register: if any primary (H1_external, executable-gold) condition shows an `I_perp` rate **> 20%**, we
INVESTIGATE and remediate the answer-format-contract compliance (prompt/labeler) and re-run that cell
BEFORE the numbers are trusted for confirmatory analysis — we do NOT silently absorb it into CD.

## Decision-rule mapping (unchanged rules, applied to PRIMARY)
The frozen §9 decision rules (H1a/H1b/H2, R1/R2) are evaluated on the PRIMARY treatment above.
SENSITIVITY A and B are reported for transparency; if PRIMARY and both sensitivities agree in sign, the
conclusion is robust; if they diverge, we report the divergence honestly and treat the I_perp handling as
a material source of uncertainty (no rule/metric change).

## What remains UNCHANGED (still frozen)
- The `harness/metrics.py` `false_consensus_rate` DEFINITION (= SENSITIVITY A) — untouched.
- All hypotheses, the regime criterion, secondary metrics, R1/R2 nulls + predicted directions, the
  silent-failure signature, detector headline, decision rules, and target sample sizes.
- The combinatorial interpretation structure (Amdt 03) and its metric-integrity guardrail (partial-default
  convergence still counts as a genuine enumerated wrong label — it is NOT `I_perp`).

## Sign-off
- [ ] Owner approves the I_perp primary treatment (PRIMARY = enumerated-wrong only, I_perp in N but
      ineligible as the convergent label; SENSITIVITY A = frozen metric with I_perp eligible; SENSITIVITY
      B = drop I_perp from N; DIAGNOSTIC = per-condition I_perp rate with a >20% investigate-before-trust
      gate). Metric DEFINITION remains frozen.
- [ ] Committed as the amendment of record BEFORE any full-scale run.

Amendment status: **DRAFT — awaiting owner sign-off.** Metric definitions remain frozen regardless.
