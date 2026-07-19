# Pre-Registration Amendment 11 — R2 interpretation + H1a/R2 primary-method scope (owner-ratified)

> Clarifies the ROLE and SCOPE of the R2 (cross-family construction control) analysis after the R2 subset
> was run. Analogous to Amendment 07 for R1: it does NOT change the FROZEN metric (`cd_primary`/A04), the
> FROZEN §9 `evaluate_r2` rule, the hypotheses, the regime criterion, or R1. It (a) records that the
> pre-registered R2 aggregation-amplification metric is INCONCLUSIVE and is NOT the sharpest test of the
> construct-validity confound R2 targets; (b) designates the cross-family SINGLE-AGENT CD persistence as
> the direct rebuttal of that confound; (c) restricts the H1a/R2 PRIMARY estimate to the A08 primary method
> grid; (d) excludes one construct-invalid R2 item. **STATUS: owner-ratified 2026-07-19 (decisions
> ①②③ below); results reported honestly whatever they are.**

## 0. What R2 targets (frozen §9)
R2 rules out the confound "the convergent delusion is just a shared prior WITH THE CONSTRUCTOR" — i.e. the
tested models converge on the foil only because the SAME family that built the traps shares their prior.
The main benchmark is mai-code-constructed; A10 added an Anthropic (claude-opus-4.8)-constructed H1 subset.

## 1. Empirical R2 result (A10 subset, 1296 jobs, $0)
- **Construct validity (direct confound rebuttal):** on the Anthropic-constructed H1 items, NON-Anthropic
  tested models (OpenAI + Google) converge on the foils at **single-agent cd_primary = 0.722** (0.867 on
  the 5 construct-valid items). Convergent delusion PERSISTS under cross-family construction → the
  shared-prior-with-the-constructor confound is DIRECTLY REBUTTED. Same-family (Anthropic-tested) CD is
  lower (0.264), a moderate familiarity effect, reported as reference.
- **Pre-registered §9 R2 metric (aggregation-vs-single CD delta, cross-family, strictly positive →
  SUPPORTED):** INCONCLUSIVE across all slices (primary methods): all-k Δ=−0.024 CI[−0.067,+0.001];
  k1-only Δ=−0.048 CI[−0.120,+0.006]; k1 no-sortids Δ=−0.057 CI[−0.138,0.000]. Redundant aggregation
  (sc/MAD) neither amplifies nor significantly reduces CD (CD stays ~0.67–0.72).

## 2. ① R2 role clarification (owner-ratified) — analogous to A07/R1
The frozen §9 R2 metric (does aggregation AMPLIFY CD cross-family?) is INCONCLUSIVE and is NOT the sharpest
test of the construct-confound. As with the R1 label-shuffle (A07), the pre-registered metric is retained
and REPORTED HONESTLY (INCONCLUSIVE), but the confound R2 targets is carried by the DIRECT evidence: the
cross-family SINGLE-AGENT CD persistence (0.72–0.87), which no aggregation choice can explain away. The
`evaluate_r2` rule and all frozen math are UNCHANGED; this only records the interpretation.

## 3. ② Construct-validity exclusion (owner-ratified)
`r2xf_data_sortids_001` (k0+k1) did NOT trap (cross-family k1 cd_primary=0.083 — unaware models still sort
numerically; "numeric id sort" is weakly derivable from the ids being numeric strings, so its target is not
a genuinely EXTERNAL convention). It is EXCLUDED from the R2 estimate as construct-invalid (transparent,
recorded). The R2 verdict is INCONCLUSIVE with OR without it.

## 4. ③ H1a/R2 primary-method scope (owner-ratified) — applies to the MAIN analysis too
The frozen `_h1a_metric`/`_cross_family_metric` pool ALL non-single methods. The A08 PRIMARY method grid is
`{single, sc, homogeneous-MAD, heterogeneous-MAD}`. The H1a AND R2 PRIMARY estimates are computed on the
A08 PRIMARY methods ONLY. `interpretation-diverse` (a diversity-injection method, expected to reduce CD)
and `verifier` (accomplice condition; scheduled sensitivity) are NON-primary → reported as SECONDARY
sensitivity, NOT pooled into the primary H1a/R2 aggregation set. This is correct application of A08 (the
frozen metric is unchanged; only the INPUT method subset is A08-primary). Rationale: pooling a
diversity-injection method into "aggregation" would conflate diversity's benefit with redundant
aggregation's (non-)benefit and contaminate the H1a headline.

## 5. What stays FROZEN
`cd_primary`/A04, H1/H2 hypotheses, the regime criterion, R1 (A07), the §9 decision rules INCLUDING
`evaluate_r2`, and all metric math. This amendment records interpretation + the A08-primary analysis scope
+ one construct-validity exclusion; it changes no frozen definition.

## 6. Sign-off
- [x] Owner @EloiseJulia ratifies ① (R2 INCONCLUSIVE reported honestly; cross-family single-agent
      persistence is the direct confound rebuttal; note recorded). — 2026-07-19
- [x] Owner ratifies ② (exclude construct-invalid `r2xf_data_sortids_001`, recorded). — 2026-07-19
- [x] Owner ratifies ③ (H1a/R2 primary estimate = A08 primary methods; interpretation-diverse/verifier
      → secondary sensitivity). — 2026-07-19

Amendment status: **RATIFIED (owner @EloiseJulia, 2026-07-19).** See DECISION-LOG row 72.
