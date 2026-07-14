# Phase 1 Spot-Check Gate — data_analysis + policy_qa (owner sign-off)

Both slices are cross-family audit-clean (Claude constructor / GPT auditor, 0 BLOCKER/MAJOR
on re-audit). This gate asks the owner to confirm that each task's TARGET interpretation
(I0) is the natural default a competent unaware solver would pick. Merge is held until sign-off.

## S2 — data_analysis (10/10 distinguishable, 111 tests). Auditor judgment: ALL YES.

| task_id | Target I0 | Deleted axis | Natural default? |
|---|---|---|---|
| data_mean_001_k0 | Skip None values | none (control) | YES |
| data_mean_001_k1_missing_values | Skip None values | missing_values | YES |
| data_variance_001_k0 | Population variance ÷n | none | YES |
| data_variance_001_k1_formula | Population variance ÷n | formula | YES |
| data_median_001_k0 | Average middle two (even) | none | YES |
| data_median_001_k1_even_handling | Average middle two (even) | even_handling | YES |
| data_filter_001_k0 | Inclusive >= threshold | none | YES |
| data_filter_001_k1_boundary | Inclusive >= threshold | boundary | YES |
| data_group_001_k0 | Preserve original value order | none | YES |
| data_group_001_k1_list_order | Preserve original value order | list_order | YES |

## S3 — policy_qa (20/20 distinguishable, 88 tests). Auditor judgment: 9 YES, 1 DOUBTFUL.

| task_id | Target I0 | Deleted axis/axes | Natural default? |
|---|---|---|---|
| policy_overtime_001_k0 | 40h threshold, 1.5x OT = 950.00 | none | YES |
| policy_interest_001_k0 | 365-day simple interest = 147.95 | none | YES |
| policy_tip_001_k0 | pre-tax, nearest-cent tip = 7.50 | none | YES |
| policy_overtime_001_k1_overtime_threshold | 40h/1.5x = 950.00 | overtime threshold | YES |
| policy_tip_001_k1_tip_base | pre-tax tip = 7.50 | tip base | YES |
| policy_interest_001_k1_day_count | 365-day simple = 147.95 | day count | YES |
| policy_overtime_001_k2_all | 40h/1.5x = 950.00 | threshold; rate | YES |
| policy_interest_001_k2_all | 365-day simple = 147.95 | day count; compounding | YES |
| **policy_refund_001_k2_all** | 365-day basis, cancellation day counted = 271.23 | year basis; cancellation-day counting | **DOUBTFUL** |
| policy_discount_001_k2_all | sequential discounts, nearest-cent = 74.80 | stacking; price rounding | YES |

### The one flagged item
`policy_refund_001_k2_all`: the auditor notes subscription proration can reasonably be
**monthly/calendar-based** rather than 365-day, and whether the **cancellation day** is
counted is itself convention-dependent — so the target may not be an unambiguous natural
default. Options: (a) accept as-is; (b) have a fix sub-agent rework the refund task's axes
so the target is a clear natural default (like the other policy tasks); (c) drop the refund
task from the formal set.
