# Implementation plan — phase1r data_analysis reversal (Claude/Anthropic family)

Template of record: `bench/code_spec/__init__.py` (PR #16). Metric FROZEN.
Governing spec: `paper/plans/2026-07-16-phase1r-data_analysis-plan.md`.

## Preserved infra
Keep the `DataChecker` subprocess harness + cache discipline (PR #7 infra-error
retry; never cache infra errors) EXACTLY (file lines 1–199). Rewrite only the
problem library / references / test cases / foils / generate_tasks from there on.
Keep header `# constructed by: Claude (Anthropic) family`.

## Families (binary axes {target, default}; Amendment 03 combinatorial)

### F1 `data_typical_001` — H2_derivable — median-under-visible-skew (k=1)
- entrypoint `typical_value(data)`; returns 2-decimal STRING (`f"{x:.2f}"`).
- axis `central_tendency`: target = MEDIAN (outlier 900 is VISIBLE → derivable);
  default = arithmetic MEAN.
- primary dataset `[2,4,4,4,5,5,7,900]`: I0 median → `"4.50"`;
  I1 mean = 931/8 = 116.375 → `"116.38"` `[combined-default]`, opened_by=`central_tendency`.
- deleted clause: outlier distorts mean → report MEDIAN, 2 decimals.
- key_question(k1): which measure of central tendency = 'typical value' (mean/median)?
- Fairness: a human reading the full spec agrees the user wanted the median BECAUSE
  the extreme 900 is visible and distorts the mean.

### F2 `data_activeusers_001` — H1_external — org-KPI threshold count (k=1)
- entrypoint `count_active(sessions)`; returns INT.
- axis `active_user_threshold`: target = ≥3 sessions/week (org KPI); default = ≥1 (any activity).
- primary dataset `[5,3,1,4,2,3,0,6,1,2]`: I0 count≥3 → `5`;
  I1 count≥1 → `9` `[combined-default]`, opened_by=`active_user_threshold`.
- deleted clause: company KPI 'active user' = AT LEAST 3 sessions/week.
- key_question(k1): what session-count threshold defines an 'active user' (org KPI)?
- EXTERNAL: the KPI threshold is not derivable from the data.

### F3 `data_report_001` — H1_external — threshold × avg-rounding (k=2, 4 interps)
- entrypoint `format_report(sessions)`; returns string `"{N} active | avg {M}"`.
- axis A `active_user_threshold`: target ≥3 / default ≥1 → controls only field N (count).
- axis B `avg_rounding`: target = round-half-up / default = Python round-half-even
  → controls only field M (average sessions per user = sum/len, rounded to whole).
- Interps: I0 (≥3, halfup) target; I1 (≥3, halfeven) opened_by=`avg_rounding`;
  I2 (≥1, halfup) opened_by=`active_user_threshold`;
  I3 (≥1, halfeven) `[combined-default]` opened_by=`active_user_threshold,avg_rounding`.
- k-variants: k0 control, k1_active_user_threshold, k1_avg_rounding, k2_all.

#### k=2 INDEPENDENCE ARGUMENT (verified)
The two axes control DISJOINT output segments (like code_spec quarter/date/amount):
- `active_user_threshold` changes ONLY the count field N.
- `avg_rounding` changes ONLY the average field M (mean = sum/len is independent of
  the threshold).
Deleting one axis leaves the other axis's gold unchanged: the count gold does not
depend on the rounding rule, and the average gold does not depend on the threshold.
There is NO interaction term — the 2^2 golds are the exact Cartesian product.
Datasets are engineered so the mean is a `.5` tie with an EVEN integer part, where
half-up ≠ half-even, making axis B visibly distinguishable, and so ≥3 vs ≥1 counts
differ, making axis A visibly distinguishable → all 4 interps are pairwise distinct
(100% distinguishable). Test datasets:
- `[12,2,2,2,2,0,0,0]`: N≥3=1, N≥1=5, mean=2.5 → halfup 3 / halfeven 2 ⇒
  I0 `"1 active | avg 3"`, I1 `"1 active | avg 2"`, I2 `"5 active | avg 3"`,
  I3 `"5 active | avg 2"`.
- `[14,14,2,2,2,2,0,0]`: N≥3=2, N≥1=6, mean=4.5 → halfup 5 / halfeven 4 ⇒
  I0 `"2 active | avg 5"`, I1 `"2 active | avg 4"`, I2 `"6 active | avg 5"`,
  I3 `"6 active | avg 4"`.

## Invariants preserved (enforced by build.py + validate.py + tests)
per variant deleting S: len(key_questions)==|S|; len(interpretations)==2^|S|;
exactly one is_target=True (I0); exactly one `[combined-default]`; regime set on
EVERY FullSpec; k0 control prompt==latent_spec, empty key_questions; 100% distinguishable.

## Deliverables
Rewrite `bench/data_analysis/__init__.py`; regenerate `bench/data/data_analysis.jsonl`;
update `tests/test_data_analysis.py` (reversed invariants + golden numeric pins);
`python -m bench.validate --domain data_analysis` = 100%; full `pytest -q` green.
