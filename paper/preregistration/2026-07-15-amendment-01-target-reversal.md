# Pre-Registration Amendment 01 — Target/Default Reversal  (DRAFT, owner sign-off required)

> Amends the FROZEN pre-registration `paper/preregistration/2026-07-15-prereg.md` (freeze SHA
> `c0a0393`). **The primary/secondary METRIC DEFINITIONS ARE UNCHANGED and remain frozen.** This
> amendment records a benchmark **construct-validity fix**, transparently and timestamped BEFORE any
> registered run. It is NOT effect-maximizing tuning.

## Timestamp / provenance
- Drafted: 2026-07-15, by the Manager, after the owner-approved directional real-model batch.
- Evidence: `paper/research/2026-07-15-directional-findings.md` (directional batch on GitHub Models).
- Status: DRAFT → owner signs off → committed as the amendment of record BEFORE the registered mini-pilot
  or any full-scale run. No registered run has occurred yet.

## What is being amended
The original benchmark construction ruling required **target I0 = "the natural default a reasonable
unaware solver would pick."** Empirically (directional batch), this makes a competent model compute the
default = the target = **correct**, so convergent_delusion ≈ 0 on those tasks. The benchmark therefore
**cannot exhibit the pre-registered phenomenon** (silent consensus failure requires agents to converge
on a WRONG interpretation).

## The amendment (REVERSED property)
For every ambiguous (k≥1) task, the **target I0 is a deliberately NON-default true intent**, and the
model's **natural default is one of the WRONG foils (I1…Im)**. The full `latent_spec` clearly specifies
the non-default intent; the DELETED clause is exactly what would reveal it; without that clause the
shared-prior default lands on a wrong foil → silent consensus failure is possible.

Rationale: this is a **construct-validity fix** (target=default ⟹ CD≈0 ⟹ H1 untestable), not
effect-size tuning. It does not change any metric, hypothesis statement, decision rule, robustness null,
or analysis plan in the frozen prereg — only the benchmark items' target/foil assignment so the metric
can actually be exercised.

## What remains UNCHANGED (still frozen)
- Primary metric `convergent_delusion` and all secondary metrics (`marginal_rho`, `a_maj`, `ece`,
  `confidence_accuracy_slope`) — definitions untouched.
- H1/H2 hypotheses, the H1/H2 construction-time regime criterion, decision rules, target sample sizes.
- Co-primary robustness nulls (R1 label-shuffle, R2 cross-family construction) and their predicted
  directions. R1's null is UNAFFECTED (it operates on labels). R2 (cross-family construction) still
  applies to the reconstructed benchmark.
- Executable gold (never LLM-judge), deletion-based ambiguity, per-variant `key_questions` invariant
  (`len(key_questions)==ambiguity_level==len(interpretations)-1`), cross-family construction control.
- The silent-failure signature (§5) and detector headline (§6).

## Fairness bar (carried over — do NOT re-break)
The reversed target must be a GENUINE, reasonable intent that the full spec clearly states (the same bar
that previously killed the `format` decimals axis and the convention-ambiguous `policy_refund`). It must
NOT be a gotcha: a human reading the full `latent_spec` must agree the user genuinely wanted the
non-default, and the deleted clause is precisely what conveys it.

## Verification added for the reversal
1. **Empirical default-check:** on a directional pilot, homogeneous agents must actually converge on the
   WRONG foil (the model's default) for each reconstructed trap task — confirming target ≠ real default.
   Tasks where models still land on the target are NOT valid traps and are revised or excluded.
2. **Reversed human spot-check gate:** re-run the Phase-1 spot-check gate on reconstructed tasks,
   verifying the REVERSED property (target=non-default, default=wrong foil, fair full spec). Owner signs
   off before scaling.

## Sign-off
- [x] Owner approves the target/default reversal amendment (metric frozen; construct-validity fix). —
      approved 2026-07-15 ("COMMIT Amendment 01 ... Approved"). Both example tasks approved as passing
      the fairness bar; data_analysis example added to the reconstruction spec for a separate gate.
- [x] Committed as the amendment of record. Reconstruction proceeds per
      `paper/specs/phase1-benchmark-reversal-spec.md` AFTER the data_analysis example is approved and the
      reversed spot-check gate passes.

Amendment status: **APPROVED & IN EFFECT** (owner-signed 2026-07-15). Metric definitions remain frozen.
Amendment commit SHA: recorded by the commit immediately following this edit (see `git log`).
