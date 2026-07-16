# phase1r-policy_qa — implementation plan (Claude/Anthropic implementer)

Reconstructs `bench/policy_qa` under the reversed target/default + combinatorial
binary-axis invariant (Amendment 01 + 03), mirroring the merged code_spec template
(PR #16). policy_qa is the SECONDARY breadth / cross-domain consistency domain
(structured exact-cent answers, NEVER reported as accuracy; prereg §7).

## Reversed families (all regime = H1_external, binary {target, default})

Each single axis is strictly binary; a variant deleting S (|S|=k') has 2^k'
interpretations. I0 = NON-default true intent (stated by the deleted clause);
the model's population default is the WRONG [combined-default] foil.

| family (task_id)        | axis               | I0 (target, non-default)          | default foil [combined-default]     |
|-------------------------|--------------------|-----------------------------------|-------------------------------------|
| policy_overtime_001 ⭐  | overtime_threshold | OT after 35h (union) = $1000.00   | OT after 40h (FLSA) = $950.00       |
| policy_interest_001     | compounding        | monthly compound = $150.75        | simple interest = $147.95           |
| policy_tip_001          | tip_base           | post-tax total (house) = $8.10    | pre-tax subtotal = $7.50            |
| policy_refund_001       | fee_basis          | fee on full credited amt = $341.91| fee on merchandise only = $343.90   |
| policy_discount_001     | discount_basis     | additive single % = $73.00        | sequential/compound = $74.80        |

⭐ = REQUIRED anchor (overtime contract threshold), amounts frozen by a golden test.

## Multi-axis k=2 family (4 interps): policy_paymileage_001

Two GENUINELY INDEPENDENT external conventions on one calculation:
`total = wages(overtime_threshold) + mileage(mileage_rate)` — additively separable.

- I0  OT@35h + $0.70/mi        = 1000.00 + 70.00 = **1070.00** [all-target]
- I1  OT@35h + IRS $0.655/mi   = 1000.00 + 65.50 = **1065.50** [mileage defaulted]
- I2  OT@40h + $0.70/mi        =  950.00 + 70.00 = **1020.00** [overtime defaulted]
- I3  OT@40h + IRS $0.655/mi   =  950.00 + 65.50 = **1015.50** [combined-default]

### k=2 independence argument (verified in test_k2_axes_independent)
The overtime axis only changes the wages term (1000 vs 950); the mileage axis only
changes the mileage term (70.00 vs 65.50). Deleting one axis leaves the other's
contribution unchanged, so the deltas are constant across the other axis:
- overtime delta: I0−I2 = I1−I3 = 50.00
- mileage  delta: I0−I1 = I2−I3 =  4.50
All four amounts are pairwise distinct (min gap 4.50 ≫ 0.01 checker tolerance).

## Deliberate deviations from the plan's illustrative examples ("e.g.")
Amendment 01 (I0 = NON-default; model default = WRONG foil) is inviolable and
governs where the plan's illustrative assignments would make I0 the model's
natural default (which recreates the OLD CD≈0 bug the reconstruction fixes):
- **interest**: plan e.g. was target=365-day vs default=360-day. A naive model
  divides by the calendar 365, so 365 is the *default*, not a non-default trap.
  Replaced the day-count axis with a **compounding** axis: the model defaults to
  naive simple interest (147.95); the contract's monthly compounding (150.75) is
  the genuine non-default term. Clean, unambiguous reversal.
- **tip**: kept the plan's pre-vs-post-tax axis but assigned I0 = post-tax total
  (house policy, non-default) and the pre-tax etiquette basis as the default foil,
  so I0 is genuinely non-default.
- **refund/discount**: used explicit non-standard basis/stacking terms as I0
  (fee on the full credited amount; additive stacking), with the standard retail
  rule as the default foil.

## Structural invariants preserved
- StructuredAnswerChecker unchanged (deterministic exact-cent, NO LLM).
- Per-domain answer-format contract lives in harness/run.py (FINAL ANSWER: $<amount>
  / {"amount": N}); prompts keep "Answer ... rounded to the nearest cent". Untouched.
- No family has a rounding axis, so every prompt_core pins "rounded to the nearest
  cent" without contradicting a deletable clause.
- 14 tasks: 5×2 (single-axis) + 4 (k=2). Distribution k0=6, k1=7, k2=1.
- validate.py: 100% distinguishable. Full pytest suite green.

## Fairness / open concerns
- tip's reversal is the weakest (both pre- and post-tax are plausible model
  outputs); overtime, interest (compounding), refund, discount, and the k=2 family
  are strong reversals. The empirical default-check (later phase) confirms which
  foil the model actually converges to; metric defs are frozen and untouched.
