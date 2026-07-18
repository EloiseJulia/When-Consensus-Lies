# Pre-Registration Amendment 07 — R1 robustness null redefinition (SIGNED, owner 2026-07-17)

> Amends FROZEN pre-registration `2026-07-15-prereg.md` (freeze `c0a0393`) §4 (co-primary robustness
> null R1) and the R1 clause in §9/§11. **The primary metric (`convergent_delusion`/`cd_primary`, A04),
> the hypotheses, the regime criterion, R2, and the decision rules for H1/H2 are UNCHANGED and remain
> frozen.** This amendment redefines ONLY the R1 robustness null: what it is, what it tests, and its
> role. It was surfaced by the §11 MVP pilot BEFORE any confirmatory run (the pilot's purpose), and the
> replacement criterion is MORE stringent, not easier. **STATUS: SIGNED (owner, 2026-07-17).**

## 0. What the pilot revealed (empirical trigger)
The §11 MVP pilot (455 runs, frontier proxy, $0) computed the frozen R1 label-shuffle null for the first
time on real data. Result: `null_cd == real_cd` to the decimal in EVERY condition
(0.75=0.75, 0.60=0.60, 0.667=0.667, 0.889=0.889, 1.0=1.0…). This is a **mathematical identity, not an
empirical coincidence**, and it exposes that the frozen R1 tests the WRONG thing for this thesis.

## 1. Why the frozen R1 is structurally uninformative here (the argument)
Frozen §4 R1 (label-shuffle, population-level / cross-item): pool all agent labels within a condition,
then **reassign each agent an independent draw from that pooled marginal**, and recompute mean CD → CD₀.
Frozen prediction: CD_real ≫ CD₀; and "**if CD_real ≈ CD₀, the primary effect is an artifact of the
marginals — thesis not supported.**"

The flaw: `convergent_delusion` for **independent** agents is, by construction, a **function of the label
marginal**. A marginal-preserving shuffle preserves the marginal, so it **cannot reduce** CD when agents
are (conditionally) independent draws from a shared distribution. But that shared distribution is exactly
what our thesis is ABOUT: under underspecification, independent agents that share a prior all pick the
**same wrong default** (ρ→1 fake redundancy — report §2.4). **The marginal bias toward a shared wrong
default IS the phenomenon, not a nuisance.** R1 asks "is there excess per-item correlation BEYOND the
marginal?"; our thesis is that the **marginal itself** is delusively concentrated. Hence CD_real ≈ CD₀ is
an EXPECTED signature of the thesis, and the frozen "thesis not supported" reading is incorrect here.

This is NOT rationalizing a failed null. The convergence is proven **independently of any null** by the
DIRECT evidence: e.g. `code_quarter_001_k1` = 35/35 agents on the same wrong foil; `code_quarterdate_001_k2`
= 34/35 on I3; the well-specified `k=0` controls → I0 (CD≈0); H2 derivable items resolve → I0; and
cross-model (different families) convergence on the same foil.

## 2. What changes (R1 redefinition)
**(R1-new) Discriminating anti-artifact null — REPLACES the R1 refutation criterion.** Two components,
BOTH pre-registered, both MORE stringent than a marginal-preserving shuffle:
- **(R1a) Well-specified control contrast (k=0 vs k≥1).** On k=0 controls (fully specified; the natural
  answer is the target), CD must be ≈ 0 (`≤ tol`, pre-registered); on k≥1 underspecified items CD is
  high. The bootstrap 95% CI of (CD_{k≥1} − CD_{k=0}) excludes 0 and is positive. This is a HARD test:
  the SAME pipeline/labeler/metric yields ≈0 when the prompt is complete and high when a clause is
  deleted — an artifact of "skewed foil counts / labeler bias" would inflate BOTH, so k=0≈0 rules it out.
- **(R1b) Uniform-over-interpretations null.** For each item, draw each agent's label uniformly at random
  from THAT item's own interpretation set (I0…I_{2^{k'}−1}); recompute mean CD → CD_unif (average over
  permutations). Prediction: observed CD_{k≥1} ≫ CD_unif (bootstrap 95% CI of the difference excludes 0,
  positive). This tests that the wrong-answer concentration exceeds what random guessing over the item's
  OWN interpretations would produce — an item-aware null that does NOT inherit the shared-marginal bias.

**(R1-diag) Label-shuffle retained as a SECONDARY DIAGNOSTIC, not a refutation gate.** The frozen
population-level label-shuffle value (`harness/nulls.py::label_shuffle_null`, UNCHANGED) is still computed
and REPORTED, reinterpreted as a **shared-prior signature**: CD_shuffle ≈ CD_real is EVIDENCE of a shared
delusive marginal (ρ→1 fake redundancy), consistent with §2.4 — NOT a "thesis not supported" verdict.
It MAY remain INFORMATIVE where it can genuinely move: **MAD / debate / verifier conditions**, where
inter-agent COMMUNICATION can create excess correlation BEYOND the shared-prior marginal — there a
shuffle CAN reduce CD, and R1-shuffle tests that communication-induced excess. Keep it reported there.

## 3. What stays FROZEN / UNCHANGED
`cd_primary` + all metric definitions (A04), H1/H2 hypotheses, the regime criterion, **R2 (cross-family
construction control)**, the H1a/H1b/H2 decision rules (§9), `harness/metrics.py`, `harness/nulls.py`
(the frozen label_shuffle_null is UNTOUCHED and still computed for R1-diag + MAD), `common/schema.py`,
the benchmark construction. R1a/R1b are computed by ADDITIVE non-frozen code; no frozen math changes.

## 4. Stringency note (reviewer pre-empt — this is HARDER, not easier)
The replacement does NOT weaken the robustness bar. The k=0 control (R1a) is a HARD, within-design
falsification test (same machinery must give ≈0 on specified prompts); the uniform null (R1b) is an
item-aware baseline the effect must clear. We are REPLACING a null that is a mathematical identity for
this thesis (uninformative) with two nulls that can actually fail. The thesis's PRIMARY support remains
the DIRECT evidence (per-item concentration + k0-vs-k≥1 + cross-model convergence), so the headline never
hinges on a null choice; both R1-diag and R1a/R1b are reported transparently.

## 5. Timing / integrity
Filed and signed BEFORE the confirmatory run, triggered by the pilot (diagnostic, non-confirmatory).
Pilot data do NOT count toward H1/H2. The §11 pilot gate is re-run with R1a/R1b before scaling.

## 6. Sign-off
- [x] Owner approves redefining R1 to R1a (k=0 control contrast) + R1b (uniform-over-interpretations),
      demoting label-shuffle to a secondary shared-prior diagnostic (retained for MAD/debate). — 2026-07-17
- [x] Owner confirms the replacement is more stringent, both nulls reported transparently, primary
      support = direct evidence. — 2026-07-17

Amendment status: **SIGNED (owner, 2026-07-17).** Metric/hypotheses/regime/R2/decision-rules frozen.
See DECISION-LOG row 57.
