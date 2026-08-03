# Pre-registered analysis (FROZEN with the pre-registration — Law 7)

`preregistered_analysis.py` is the confirmatory analysis for the human-reliance study. It is written
and validated **before** data collection; only the input data file changes at run time.

## Run
```bash
# self-test on simulated data (no real data needed): effect demo + null demo
python preregistered_analysis.py

# the frozen confirmatory analysis on real data (same CSV schema)
python preregistered_analysis.py --data path\to\real_trials.csv
```
Requires: `numpy pandas scipy statsmodels`.

## What it does (frozen)
- Applies pre-specified exclusions (`apply_exclusions`).
- **accept** (behavioral): GEE logistic, exchangeable, participant-clustered, item fixed effects.
  Contrasts H-U1a (fake>single), H-U2a (dep<fake).
- **confidence** (subjective): `MixedLM` with crossed participant+item random intercepts.
  Contrasts H-U1b (fake>single), H-U2b (dep<fake).
- Directional (one-sided) tests; **Holm** correction across the 4 primary contrasts at family-wise α=0.05.
- Secondary: gap-identification rate by condition (descriptive/exploratory only).

## Validation (self-test output, seed 0)
- Under the pre-registered effect: rejects **all 4** (Holm p < 0.05).
- Under the null: rejects **none** (Holm p = 1.0).

## Real-data CSV schema (one row per completed trial, after exclusions)
`participant_id, item_id, condition{single|fake|dep}, accept{0,1}, confidence{0..100},
gap_correct{0,1 or blank}, rt_sec, order_index` plus participant-level exclusion columns
`passed_comprehension, passed_attention, total_time_sec, straightline_confidence, duplicate_id`.

**Do not modify the model specs / contrasts / correction after freeze.** Post-freeze changes go in the
pre-registration deviations log and are reported as exploratory.
