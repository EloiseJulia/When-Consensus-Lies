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

## H1/H2 regime classification (construction-time; operationalizes prereg §2)
Every reconstructed task is tagged `regime ∈ {H1_external, H2_derivable, EXCLUDED}` AT CONSTRUCTION via
this explicit test (aligns with the frozen prereg §2 regime criterion):

> **Is the disambiguator PRESENT in the prompt/data (→ H2_derivable) or ABSENT & external (→ H1_external)?**

- **H1_external** (carries the primary H1 test): the clause that reveals the true intent is EXTERNAL
  knowledge NOT derivable from the prompt or data (fiscal calendar, contract terms, an org-specific KPI
  definition). A competent/reasoning model CANNOT recover it from context → it MUST default to the
  population-prior (a wrong foil). Examples A (fiscal-quarter), B (35h overtime), D (org KPI).
- **H2_derivable** (the boundary / two-regime demonstrator): the disambiguator is PRESENT in the prompt
  data, so a competent/reasoning model CAN derive the correct non-default itself (weaker models still
  default wrong). Example C (visible outlier → median).
- **EXCLUDED**: cannot be cleanly assigned; kept for descriptive stats only.

Do NOT mislabel an H2 item as H1 (a competent model resolving it would muddy the H1 signal) or vice
versa. Constructor tags `regime`; a DIFFERENT family reviewer re-derives it; disagreement → EXCLUDED.

## Example reversed task A — code_spec (fiscal vs calendar quarter)  [ILLUSTRATIVE · regime = H1_external]
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

## Example reversed task B — policy_qa (non-standard overtime threshold)  [ILLUSTRATIVE · regime = H1_external]
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

## Example reversed task C — data_analysis (median vs mean under skew)  [ILLUSTRATIVE · regime = H2_derivable]
> **REGIME = H2 (derivable).** The disambiguator (the visible outlier 900 / skew) is PRESENT in the
> prompt data, so a competent/reasoning model can SEE the skew and pick the median itself. This is a clean
> within-item TWO-REGIME demonstrator (baseline defaults to mean=wrong; reasoning model sees the
> outlier→median=right). It is NOT an H1 external-knowledge trap — do not mix it into H1.
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

## Example reversed task D — data_analysis (org-specific KPI definition)  [ILLUSTRATIVE · regime = H1_external]
> **REGIME = H1 (external knowledge).** The disambiguator (the org's KPI threshold) is ABSENT from the
> prompt/data and cannot be derived from it — a pure external-knowledge trap analogous to fiscal-quarter
> and 35h overtime. This is the pure-H1 data_analysis item.
- **Dataset (fixed, in the task):** weekly session counts per user `[5, 3, 1, 4, 2, 3, 0, 6, 1, 2]` (10 users).
- **latent_spec (full):** "Per our company KPI, an 'active user' is one with **at least 3 sessions per
  week**. Count how many users are active."
- **prompt (k1, delete the org KPI threshold clause):** "Count how many users in the dataset
  `[5, 3, 1, 4, 2, 3, 0, 6, 1, 2]` (weekly session counts) are 'active users'."
- **key_questions (k1):** ["What session-count threshold defines an 'active user' (the org KPI)?"]
- **Interpretations (executable gold = deterministic integer count):**
  - `I0` (target, NON-default org KPI ≥3): count sessions ≥ 3 → {5,3,4,3,6} = **5**.
  - `I1` (**model default**, WRONG foil — "any activity" ≥1): count sessions ≥ 1 → all but the 0 = **9**.
  - `I2` (other deviation, ≥2): count sessions ≥ 2 → {5,3,4,2,3,6,2} = **7**.
- **Why it's a fair H1 trap:** "active user" with no definition → an unaware model defaults to a standard
  "any activity" notion (`I1` = 9, wrong). The org KPI (≥3) is EXTERNAL knowledge stated only in the full
  spec — not derivable from the session-count data itself (unlike Example C's visible outlier). A human
  reading the full spec agrees the user wanted the org KPI. All golds distinct (5/9/7) → distinguishable.
  Silent failure: the model confidently reports 9 active users, unaware of the org's ≥3 KPI.
- **Expected default-check:** homogeneous agents (incl. reasoning models — external knowledge is NOT
  recoverable from context) converge on `I1` (=9) → convergent delusion persists even for strong reasoners
  (the H1 prediction).

## Reversed spot-check gate (re-run before scaling)
For each reconstructed task, verify and record:
1. Full `latent_spec` clearly specifies the non-default intent; deleted clause reveals it; fair (human agrees).
2. `I0` (target) ≠ the model's natural default; the labeled default foil `I_d` = the model's actual default
   (from the directional default-check).
3. **`regime` tag correct** per the construction-time criterion (disambiguator ABSENT&external → H1_external;
   PRESENT in prompt/data → H2_derivable), cross-family re-derived; disagreement → EXCLUDED.
4. **Per-regime empirical default-check:** H1 items → homogeneous agents (incl. reasoning models) converge
   on the wrong foil (external knowledge unrecoverable); H2 items → reasoning models RESOLVE to the target
   while weaker models default wrong. Items that don't behave per their regime are re-tagged/revised/excluded.
5. Executable gold distinguishes all interpretations (100% distinguishability preserved).
6. Per-variant invariant holds (`len(key_questions)==ambiguity_level==len(interpretations)-1`; k0 empty).
7. Cross-family construction still applies (constructor family ≠ tested families).
Owner signs off on the gate before any registered run.

> **Reaffirmations (owner, 2026-07-15):**
> 1. **The EMPIRICAL per-regime default-check is the FINAL ARBITER of the H1/H2 tag**, not the a-priori
>    heuristic. If an H1-tagged task turns out reasoners resolve it, or an H2-tagged task makes reasoners
>    also fail, the task is RECLASSIFIED or EXCLUDED — observed behavior must match the tag.
> 2. **The reversed spot-check gate returns to the owner for FINAL sign-off before any full-scale /
>    registered run.** The Manager does not self-approve scaling.

## Build plan (AFTER owner signs this spec)
1. Bundle-prerequisite infra fixes (separate slice): temperature control ∈ {0,0.3,0.7,1.0} in run.py/llm.py;
   o-series/reasoning request handling (no logprobs, `max_completion_tokens`, verbalized confidence).
   [DONE — merged #14.] Plus `Task.regime` schema field [Amendment 02, in flight].
2. **Regime plumbing:** add `regime` to `FullSpec` (bench/build.py) and pass it through `assemble_task`
   into `Task.regime`. (build.py is not frozen; minimal change.)
3. **Staged reconstruction (de-risk: one template, then replicate):**
   a. **code_spec FIRST** as the template slice — rewrite its FullSpecs to the reversed property + set
      `regime` per task; do the build.py regime plumbing here; cross-family audit; merge.
   b. **data_analysis + policy_qa** — parallel slices using the established template; each cross-family
      audited; merged. (H1 items like the org-KPI Example D; the median-under-skew H2 demonstrator.)
   Each domain preserves executable gold, deletion ambiguity, per-variant invariant, 100%
   distinguishability, and cross-family construction.
4. Directional default-check pilot (per-regime: H1 → even reasoners default to the wrong foil; H2 →
   reasoners resolve, weaker default wrong) + reversed spot-check gate.
5. Owner sign-off → registered mini-pilot → full-scale.

## Provenance
Spec by Manager (orchestrator). Reconstruction by a spawned sub-agent; auditor family ≠ implementer.
