# Pre-registered analysis (FROZEN with the pre-registration — Law 7)

Confirmatory analysis for the human-reliance study (within-subjects redesign). Written and validated on
**simulated** data before data collection; only the input CSV changes at run time.

## Run
```bash
python preregistered_analysis.py                 # self-test: effect demo + null demo
python preregistered_analysis.py --data real.csv # frozen analysis on real data
python power_analysis.py 150                      # archived power + calibration grid (~minutes)
```
Requires `numpy pandas scipy statsmodels`.

## What it does (frozen)
- Exclusions (`apply_exclusions`): comprehension, attention, duplicate, min total-time. **Confidence
  straightlining is NOT an exclusion** (excluding on a DV biases effects) — kept as a robustness split.
- **PRIMARY confirmatory family = the two behavioral `accept` contrasts on UNDERSPECIFIED items**
  (GEE logistic, exchangeable, participant-clustered, item fixed effects, Mancl–DeRouen bias-reduced
  covariance):
  - H-U1a: accept(fake) > accept(single)   — over-reliance from displayed consensus
  - H-U2a: accept(dep)  < accept(fake)      — dependence disclosure corrects it
  Directional one-sided tests, **Holm** over the 2 at family-wise α = 0.05.
- **SECONDARY (pre-registered, not in the Holm family):**
  - confidence contrasts H-U1b/H-U2b (GEE Gaussian, same structure) — corroborating;
  - **discrimination**: condition × completeness interaction on accept (over all 14 items) — over-reliance
    predicts fake shrinks the completeness slope [accept(complete) − accept(underspecified)], dep restores
    it. Ceiling-robust but lower-powered, hence secondary;
  - first-exposure between-subjects read (each participant's first trial only);
  - objective gap-identification by condition (underspecified, flagged trials only; conditional → biased).

## Why this structure (from the 3-model ROI review)
The 5 **complete** items break the "always-flag" set so the accept baseline is not at floor (the reviewers'
top ROI risk), while the discrimination interaction gives a ceiling-robust check. Making `accept` the
primary keeps power high; confidence + discrimination corroborate.

## Validation (self-test + archived grid, `power_analysis.py`, 150 sims/cell)
- Self-test: rejects both primary contrasts under the pre-registered effect; ~none under the null.
- **Calibration (null, N=65):** per-test type-I ≈ 0.047 / 0.047; FWER ≈ 0.07 (GEE is mildly liberal in
  small samples — pre-register a permutation sensitivity test and re-confirm calibration at the pilot).
- **Power (pre-registered effect):** N=50 → both 0.93; **N=65 → both 0.95**; N=80 → 0.99.
- **Power (conservative/smaller effect):** N=65 → both 0.49; **N=90 → both 0.76.** → if effects may be
  small, recruit ≈ 90.

## Real-data CSV schema (one row per trial; oTree custom export)
`session_code, participant_id, label, item_id, condition{single|fake|dep}, complete{0,1}, accept{0,1},
confidence{1..5}, gap_correct{0,1 or blank}, rt_sec, order_index, group_g, lang,
passed_comprehension, passed_attention, total_time_sec, straightline_confidence, duplicate_id,
age_group, ai_use`

**Do not change the model specs / contrasts / correction after freeze.** Post-freeze changes → the
pre-registration deviations log, reported as exploratory.
