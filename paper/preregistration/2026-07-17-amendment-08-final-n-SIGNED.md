# Pre-Registration Amendment 08 — Pilot-calibrated final N (DRAFT → owner sign-off at launch)

> Records the CONFIRMATORY-run sample size, item set, config grid, seed count, and the power argument,
> as CALIBRATED BY the §11 MVP pilot. Prereg §10 explicitly delegates final N to the pilot ("the MVP
> pilot empirically calibrates the final N and replicate count"), so this amendment DOCUMENTS that
> calibration for a clean "Deviations from Pre-registration" section; it does NOT change the metric,
> hypotheses, regime criterion, decision rules, R2, or (A07-redefined) R1. **STATUS: DRAFT — finalized
> after the H2 top-up + additions default-check settle the exact item count; owner signs at LAUNCH.**

## 0. Trigger
The §11 MVP pilot PASSED cleanly (decision-log row 60: Gate A cd_primary=0.766; R1a k0-contrast CI
[0.531,1.000]; R1b uniform-null CI [0.030,0.499]; Gate C all jobs complete; I_perp 0.076; $0). Effects are
at ceiling. Per §10 the pilot calibrates N.

## 1. Final item set (FROZEN at sign-off)
Reconstructed reversed benchmark (Amdt 01/02/03), regime-tagged and empirically default-checked:
- code_spec: 20 items (H1_external), k∈{0,1,2,3}
- policy_qa: 14 items (H1_external), k∈{0,1,2}
- data_analysis: 20 items = 6 H1_external + **14 H2_derivable** (7 families × 2 variants: typical, avgprice,
  rate, geomean, harmonic, cumulative, tierank) — H2 top-up MERGED (PR #32, decision-log row 61).
- **Totals: H1_external = 40 · H2_derivable = 14 · GRAND TOTAL = 54 task variants.**
No further item changes after sign-off.

## 2. Config grid & replication (FROZEN at sign-off)
- Methods (PRIMARY run): `single` (N=1 baseline) · `SC k=5` · `homogeneous-MAD N=5` · `heterogeneous-MAD`
  (3-family pool). Model classes: homogeneous (gpt-5.4) · heterogeneous (O/A/G pool) · reasoning (3) ·
  weak (3).
- **Seeds:** 3 distinct, collision-free (stride ≥ ensemble size), per (item × config).
- **Sensitivity pass (SCHEDULED, not dropped):** `SC k=10` + the `verifier` condition are run as an
  EXPLICIT secondary sensitivity pass (the verifier-accomplice result is thematically important — report
  §). Pre-registered here as a SECONDARY, non-headline analysis; same metric/rules.

## 3. Power / precision (calibrated from the pilot)
Pilot effect sizes are ceiling-level: R1a Δ(CD_{k≥1}−CD_k0)=0.766 (CI excl. 0); R1b Δ=0.265 (CI excl. 0);
H1 CD≈1.0; H2 →I0≈1.0. All ≫ §10's target detectable ΔCD≥0.15. With 40 H1 items × 3 seeds × 4 methods the
crossed-RE model (§8) gives power ≈ 1.0 for every PRIMARY H1 contrast and the regime MAIN effect.
- **Honest power limitation (pre-registered):** the H2 reasoner × model_class INTERACTION (§1 secondary)
  rests on ~[≥14] H2 items; even after the top-up it is power-limited and (per rows 51-52) empirically
  expected to be NULL. We REPORT the interaction outcome transparently and NEVER backfill to chase
  significance. The regime MAIN effect (H1 fails-all vs H2 resolved-by-all) is well-powered.

## 4. What stays FROZEN
`cd_primary` + A04 CD variants, H1/H2 hypotheses, the regime criterion, R2, the §9 decision rules, and R1
as redefined by SIGNED Amendment 07 (R1a k0-control + R1b uniform null; label-shuffle demoted). This
amendment fixes only N/grid/seeds/power. The confirmatory results are reported honestly whatever they are.

## 5. Sign-off (at LAUNCH)
- [x] Owner @EloiseJulia confirms the final item counts (H1=40 / H2=14 / 54) + the config grid
      (single + SC-k5 + homMAD-N5 + hetMAD) + 3 seeds [0,1000,2000] + the SCHEDULED verifier/SC-k10
      sensitivity pass. — 2026-07-18
- [x] Owner acknowledges this LOCKS the pre-registration: no design changes after launch. — 2026-07-18

Amendment status: **SIGNED (owner @EloiseJulia, 2026-07-18) at confirmatory launch.** See DECISION-LOG
rows 61-62 (counts) + 65 (sign-off/launch).
