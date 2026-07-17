# Registered-run feasibility under per-model daily caps (2026-07-17) — analysis + recommended scope

> Manager analysis (researcher hat) for owner review. NOT yet a pre-registration amendment — it surfaces a
> feasibility crisis in the confirmatory run's reasoning condition and RECOMMENDS a scoped design. Once the
> owner steers the key choices below, I formalize it as **Amendment 05** (asymmetric reasoning-condition N)
> BEFORE any registered run. Empirical basis: the 2026-07-16 default-check (deepseek-r1 ~20/day, o4-mini
> ~25/day daily caps; both re-capped on the 2026-07-17 09:33 resume attempt → caps are a ~24h window).

## 1. The problem — the reasoning condition is INFEASIBLE at the frozen §10 scale
Frozen §10 targets: ≈60–100 items/primary domain, configs {single, SC k5, SC k10, homo-MAD N≥5,
hetero-MAD 4 families, verifier}, ≥3 seeds per (item×config).
Reasoner calls per reasoner model, even at a MINIMAL config subset:
- single(1)+SC-k5(5) = 6 calls/item/seed × 60 items × 3 seeds ≈ **1080 calls/model**.
- Full config participation (add SC-k10, homo-MAD) ≈ **3000–4000 calls/model**.
At ~20–25 calls/model/day this is **~45–180 days/model** of wall-clock. **The reasoning condition cannot
be run at the frozen scale.** (The whole registered run is already day-spanning because gpt-4o-mini — the
homogeneous ρ-baseline — is also daily-capped; the resumable runner is built for this, but the reasoners
are by far the tightest binding constraint.)

## 2. What the reasoning condition actually needs to TEST (so we scope by purpose, not by effect size)
Prereg §1 H2 + §9: the reasoning result is the **`regime × model_class` INTERACTION** (H2 CD attenuates
for reasoners; not significantly above the single-agent baseline). This is a CONTRAST test, not a
full-grid effect-size estimate. It needs: reasoners on a BALANCED set of `H1_external` and `H2_derivable`
items, at single + one aggregation level, with enough replicates for a bootstrap CI on the interaction —
NOT the full 60-item × 6-config × 3-seed grid.

## 3. RECOMMENDED scoped reasoning condition (owner to steer the numbers)
Keep the FULL §10 N for the NON-reasoning model classes (H1 primary test on gpt-4o-mini homogeneous +
weak + hetero-non-reasoner pool — those carry the primary H1a/H1b result). Scope ONLY the reasoning
`model_class`:
- **Items:** a balanced subset of **~16** executable-gold items = **8 `H1_external` + 8 `H2_derivable`**
  (drawn from code_spec + data_analysis; the H2 set centered on the median-under-visible-skew family and
  any other clean H2 we build). Balanced so the interaction is estimable.
- **Configs (reasoners only):** **single(1) + SC-k5(5)** = 6 calls/item/seed. (Drop SC-k10, homo-MAD,
  verifier for the reasoning class — single-vs-SC is enough for the "aggregation doesn't help reasoners"
  contrast.)
- **Seeds (reasoners only):** **2**.
- **Reasoner models:** both `deepseek-r1` + `o4-mini` (per-model caps are parallel, so 2 models do NOT
  slow wall-clock; they strengthen the model_class estimate).
- **Calls:** 16 × 2 × 6 = **~192 calls/reasoner model** → at ~22/day ≈ **~9 days/model** (parallel across
  the 2 models). With the resumable runner + cache, feasible over ~1.5–2 weeks.

## 4. Scientific integrity (how we keep this defensible)
- **Pre-register the asymmetry BEFORE the run** (Amendment 05): the reasoning-class N is smaller than the
  other classes by an EXTERNAL rate constraint, not to fit a result. State it transparently.
- **Honest power note:** the `regime × model_class` interaction for reasoners is estimated on the scoped
  set; report its bootstrap CI honestly. If underpowered (CI too wide to conclude), we report H2 as
  UNDERPOWERED — we do NOT re-scope post-hoc to rescue it (consistent with the frozen §2 manipulation-check
  honesty clause and §9 "report all pre-registered outcomes regardless of direction").
- **Metric + decision rules UNCHANGED** (Amendment 05 touches only per-model_class sample sizes, which §10
  already flags the MVP pilot may calibrate — this is a documented, principled calibration, not a metric
  or hypothesis change).
- The non-reasoning H1 primary test keeps full §10 power, so the headline (H1 + the cross-model /
  fake-redundancy convergent-delusion result, per Amdt-adjacent framing row 35) is NOT weakened.

## 5. ⭐ Owner decision points (steer these, then I draft Amendment 05)
1. Approve the PRINCIPLE — scope the reasoning `model_class` N (asymmetric, rate-constrained,
   pre-registered) while keeping full N for non-reasoning classes?
2. The numbers — ~16 balanced items (8 H1 / 8 H2), single+SC-k5, 2 seeds, both reasoner models
   (~192 calls/model, ~9 days/model)? Adjust up/down?
3. Also consider: gpt-4o-mini (homogeneous ρ-baseline) is daily-capped too — do we (a) run it at full §10
   N across many days via the resumable runner (feasible, just slow), or (b) also lightly scope it? (It is
   less tight than the reasoners; default recommendation: keep full N, run it day-spanning.)
4. Sequencing: do this AFTER the reasoner arm completes + the reversed spot-check gate, or draft Amendment
   05 now in parallel so it's ready at the gate?

## 6. Parallel non-reasoner work available now (not blocked on caps)
- Draft Amendment 05 (this analysis → formal amendment) once §5 is steered.
- Phase 3 detector (Hypothesis-Surfacing) interface/spec design — labels are now stable (labeler hardened
  + A04 in effect); the strategy allows starting this in parallel. Owner go needed to open the phase.
