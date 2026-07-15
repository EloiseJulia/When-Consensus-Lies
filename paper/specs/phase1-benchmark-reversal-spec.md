# Phase 1-R — Benchmark Target/Default Reversal — Reconstruction Spec (DRAFT for owner review)

> Reconstruct benchmark tasks so the TARGET is a deliberately NON-default true intent and the model's
> natural default is a WRONG foil. Owner reviews THIS spec + the two example tasks below BEFORE any mass
> rebuild. Governed by pre-registration Amendment 01. Metric FROZEN — do not touch `harness/metrics.py`.

## Design constraints (owner-mandated)
1. **Genuine prior-trap, not a gotcha (fairness bar).** The full `latent_spec` must clearly and
   reasonably specify the non-default true intent. The DELETED clause is exactly what would reveal it. A
   human reading the full spec agrees the user genuinely wanted the non-default. (Same bar that killed
   `format`/`policy_refund` — do not re-break it.)
2. **Model default = a WRONG foil**, verified empirically (directional pilot: do homogeneous agents
   actually converge on the wrong foil?). Tasks failing this are revised/excluded.
3. **Reversed human spot-check gate** on reconstructed tasks; owner signs off before scaling.
4. **Transparent** as Amendment 01 (metric frozen; construct-validity fix, timestamped pre-run).
5. **Preserve:** executable gold (never LLM-judge), deletion-based ambiguity, per-variant invariant
   `len(key_questions)==ambiguity_level==len(interpretations)-1`, cross-family construction. Metric frozen.

## The REVERSED property (per task, operational)
- `I0` (`is_target=True`) = the NON-default true intent stated by the full `latent_spec`.
- Exactly ONE foil `I_d ∈ {I1..Im}` = the **model's natural default** (what an unaware solver produces
  from the deleted prompt). Other foils = other single-axis deviations.
- `key_questions` (k-variant) = exactly the deleted axes (unchanged invariant). k0 control = fully
  specified (prompt == latent_spec), single interpretation, empty key_questions.
- Executable gold per interpretation unchanged in KIND (unit-test/deterministic value / exact-cent).

## Example reversed task A — code_spec (fiscal vs calendar quarter)  [ILLUSTRATIVE]
- **latent_spec (full):** "Write `quarter(month)` returning the quarter (1–4) for a calendar month
  number 1–12. Our FISCAL YEAR STARTS IN APRIL: Apr–Jun→1, Jul–Sep→2, Oct–Dec→3, Jan–Mar→4."
- **prompt (k1, delete the fiscal-start clause):** "Write `quarter(month)` returning the quarter (1–4)
  for a calendar month number 1–12."
- **key_questions (k1):** ["When does the fiscal year start (which month maps to quarter 1)?"]
- **Interpretations (gold = the output vector over months 1..12):**
  - `I0` (target, NON-default): fiscal-April → [4,4,4,1,1,1,2,2,2,3,3,3] for months 1..12.
  - `I1` (**model default**, WRONG foil): calendar quarters → [1,1,1,2,2,2,3,3,3,4,4,4].
  - `I2` (other deviation): fiscal-July start → [3,3,3,4,4,4,1,1,1,2,2,2].
- **Why it's a fair trap:** the full spec explicitly says fiscal-year-starts-April; delete that clause and
  an unaware model defaults to calendar quarters (`I1`, wrong). A human reading the full spec agrees the
  user wanted fiscal-April. Executable gold: run candidate `quarter(m)` for m=1..12, exact vector match.
- **Expected default-check:** homogeneous agents converge on `I1` (calendar) → convergent delusion.

## Example reversed task B — policy_qa (non-standard overtime threshold)  [ILLUSTRATIVE]
- **latent_spec (full):** "Under this employer's union contract, overtime (1.5×) begins after 35 hours
  per week. An employee worked 45 hours at $20.00/hr base. Compute gross pay, rounded to the nearest
  cent."
- **prompt (k1, delete the 35-hour clause):** "An employee worked 45 hours at $20.00/hr base. Compute
  the employee's gross pay for the week under the employer's overtime policy, rounded to the nearest
  cent."
- **key_questions (k1):** ["After how many hours per week does overtime begin (the contract threshold)?"]
- **Interpretations (gold = exact-cent amount):**
  - `I0` (target, NON-default): OT after 35h → 35×20 + 10×(20×1.5) = 700 + 300 = **$1000.00**.
  - `I1` (**model default**, WRONG foil): standard OT after 40h → 40×20 + 5×30 = 800 + 150 = **$950.00**.
  - `I2` (other deviation): flat, no overtime → 45×20 = **$900.00**.
- **Why it's a fair trap:** the full spec states the 35h contract threshold; delete it and an unaware
  model defaults to the standard 40h rule (`I1` = $950, wrong). Silent failure: the model confidently
  returns $950, not knowing this employer's 35h contract; the user (who knows) is misled with no error
  signal. Executable gold: exact-cent match.
- **Expected default-check:** homogeneous agents converge on `I1` ($950) → convergent delusion.

## Example reversed task C — data_analysis (median vs mean under skew)  [ILLUSTRATIVE, owner-gate]
- **Dataset (fixed, in the task):** `[2, 4, 4, 4, 5, 5, 7, 900]` (n=8; one extreme outlier = 900).
- **latent_spec (full):** "This dataset is dominated by a single extreme outlier (900), which badly
  distorts the arithmetic mean. Report the **median** as the representative typical value. Answer to two
  decimals."
- **prompt (k1, delete the skew/median clause):** "Report the representative typical value of the
  dataset `[2, 4, 4, 4, 5, 5, 7, 900]`. Answer to two decimals."
- **key_questions (k1):** ["Which measure of central tendency represents the 'typical value' here
  (mean, median, or mode)?"]
- **Interpretations (executable gold = deterministic numeric, exact to 2 decimals):**
  - `I0` (target, NON-default): **median** = (4th+5th of sorted)/2 = (4+5)/2 = **4.50**.
  - `I1` (**model default**, WRONG foil): arithmetic **mean** = 931/8 = **116.38**.
  - `I2` (other deviation): **mode** = most frequent value = **4.00**.
- **Why it's a fair trap (the subtlest domain):** "typical value" with no context → an unaware model
  defaults to the arithmetic **mean** (`I1` = 116.38), which the outlier makes grossly unrepresentative.
  The full spec legitimately and clearly specifies the **median** (`I0` = 4.50) *because* of the skew —
  the deleted clause ("dominated by an outlier … report the median") is exactly what reveals it. A human
  reading the full spec agrees the user genuinely wanted the median. All three golds are distinct
  (4.50 / 116.38 / 4.00) → 100% distinguishable. Executable gold: run candidate code, exact-2dp match.
- **Expected default-check:** homogeneous agents converge on `I1` (mean = 116.38) → convergent delusion;
  the user (who knows the data is skewed) is silently handed a wildly wrong "typical value".

## Reversed spot-check gate (re-run before scaling)
For each reconstructed task, verify and record:
1. Full `latent_spec` clearly specifies the non-default intent; deleted clause reveals it; fair (human agrees).
2. `I0` (target) ≠ the model's natural default; the labeled default foil `I_d` = the model's actual default
   (from the directional default-check).
3. Executable gold distinguishes all interpretations (100% distinguishability preserved).
4. Per-variant invariant holds (`len(key_questions)==ambiguity_level==len(interpretations)-1`; k0 empty).
5. Cross-family construction still applies (constructor family ≠ tested families).
Owner signs off on the gate before any registered run.

## Build plan (AFTER owner signs this spec)
1. Bundle-prerequisite infra fixes (separate slice): temperature control ∈ {0,0.3,0.7,1.0} in run.py/llm.py;
   o-series/reasoning request handling (no logprobs, `max_completion_tokens`, verbalized confidence).
2. Reconstruct all domains per the reversed property (sub-agent; cross-family audit; distinguishability +
   invariant tests green).
3. Directional default-check pilot (homogeneous agents converge on the wrong foil) + reversed spot-check gate.
4. Owner sign-off → registered mini-pilot → full-scale.

## Provenance
Spec by Manager (orchestrator). Reconstruction by a spawned sub-agent; auditor family ≠ implementer.
