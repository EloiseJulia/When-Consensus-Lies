# Pre-registration (DRAFT — not yet frozen)

**Study:** Do people over-rely on unanimous multi-model AI "consensus," and does surfacing the
*mechanism* of that consensus (a shared prompt with an unstated detail) reduce it?
**Paper:** *When Consensus Lies: Fake Redundancy in Multi-Model AI Systems* — human-validation study.
**Status:** DRAFT for owner review. **Do NOT collect data until this is frozen on OSF/AsPredicted and a
mandatory pilot (§11) passes its go/no-go.**
**Provenance (Law 7):** hypotheses, conditions, primary DVs, exclusions, and the analysis script must be
frozen *before* the first non-pilot participant. No metric redefinition afterward.

> This design was revised after a 3-model adversarial ROI review (Opus 5 / GPT-5.6 / Gemini 3.1). Key
> changes: added well-specified ("complete") items so the accept baseline is not at floor; the primary DV
> is the behavioral accept contrast (well-powered); the `dep` disclosure states the *mechanism*, not a
> verdict; inert exclusions were fixed. ⚠️ `‹CONFIRM›` items remain.

---

## 1. Background & why this study

The paper establishes, as **system properties** (no humans needed): **A** — five same-prompt agents supply
≈ one independent judgment (n_eff = 1.10, ICC = 0.89; within-item ΔCD = 0.82); **B** — product UIs render
this as independent corroboration ("N/N agree"). Two claims the paper currently **borrows from the
literature**: **C** — people read unanimity as reliability and under-account for source non-independence
(correlation/system neglect; Budescu & Yu 2007; Enke & Zimmermann 2019; Levy et al. 2022); **D** —
surfacing evidential dependence would reduce that over-reliance.

This study **measures C and D directly**. It is *not* logically required (the loop closes on A/B + borrowed
C); its purpose is borrowed→measured and human-in-the-loop CSCW fit. Scope is limited to C and D.

## 2. Hypotheses

Conditions: **single** (one AI model's answer), **fake** ("5 of 5 AI models agree"), **dep** (same 5-model
agreement + a disclosure of the *mechanism*: the five were sent the **same prompt**, which left one needed
detail unspecified — each model filled it on its own; the disclosure does **not** reveal the correct value).

**Primary (confirmatory), on UNDERSPECIFIED items — behavioral acceptance:**
- **H-U1a (C):** P(accept-as-is | fake) > P(accept-as-is | single)
- **H-U2a (D):** P(accept-as-is | dep)  < P(accept-as-is | fake)

**Secondary (pre-registered, not in the confirmatory family):**
- **H-U1b / H-U2b (confidence):** the same fake>single / dep<fake pattern on the 1–5 star rating
  of confidence that the **displayed AI answer itself is correct and ready to use** (not confidence
  in the participant's decision or selected clarification).
- **Discrimination (H-Disc):** displayed consensus degrades the ability to tell a well-specified answer
  from an underspecified one — i.e., **fake shrinks** the accept gap [accept(complete) − accept(underspec)]
  vs single (condition × completeness interaction < 0), and **dep restores** it.

Exploratory: first-exposure (first-trial) read; gap-identification accuracy; age / AI-literacy moderation.

## 3. Design

- Online, **within-subjects**, single ~11-minute session, bilingual (English / 简体中文, chosen on the
  first page), delivered as one participant link.
- **3 display conditions × 14 items**, balanced **Latin square**: `condition(group g, item i) =
  CONDITIONS[(i + g) mod 3]`, `g` assigned round-robin; trial order and the four substantive
  clarifying-option positions randomized per participant (a fixed fifth **Other** option is added).
  (With 14 items over 3 conditions the per-participant condition counts are
  4–5 each; across the 3 groups every item appears in all three conditions.)
- **Completeness factor:** 9 items are **underspecified** (a decisive convention is unstated → appropriate
  response = flag); 5 items are **complete** (the convention is stated → appropriate response = accept).
  The complete items break the "always-flag" set (keeping the accept baseline off the floor) and enable the
  discrimination check. Participants do not hold the missing convention on underspecified items (matches the
  lost-handoff scenario, §8.4 of the paper).

## 4. Participants

- **All ages eligible** (no 18+ gate): we deliberately want age variation. **Minors (<18) require guardian
  consent per IRB — confirm the consent/assent procedure before recruiting minors** (‹CONFIRM›). Because
  Prolific prohibits <18, all-ages recruitment implies a **team/local channel** (university pool / WeChat /
  平台如见数), not Prolific.
- **Target ≈ 65 analyzable; recruit with a buffer for exclusions.** If effects may be small, **recruit ≈ 90**
  (see §10).
- Team-recruited volunteers; no payment. Fixed-N stopping rule; no optional stopping / peeking.

## 5. Materials

**5.1 Items (14 = 9 underspecified + 5 complete).** Lay-readable workplace-handoff queries covering the
paper's H1_external **convention types** (fiscal-year start, rounding/remainder, inclusive/exclusive date
range, dedup, timezone, percentage base, mean-vs-median, business-vs-calendar days, null/blank). Each
**underspecified** item's answer silently commits to one value of the unstated convention (appropriate
response = flag); item answers are stripped of text that would self-disclose the convention. The **5
complete** items state the convention (e.g., "our fiscal year starts in January"), so the answer is correct
(appropriate response = accept). Items are bilingual, identical across the three display conditions; authored
by one model family and **audited for construct validity by a different family** (see `STIMULI-v2.md` /
`otree/reliance/stimuli.py`).

**5.2 Display conditions (the only manipulation).** Scenario/task/answer text is identical across conditions;
only the evidence framing differs, shown in a **consistent card** with **real model-name chips** (ChatGPT,
Gemini, Claude, Copilot, DeepSeek; single = 1 chip, fake/dep = 5 chips). The "agreement" displays are
**curated illustrations**, disclosed at debrief.
- **single:** one AI model's answer.
- **fake:** 5 AI models were asked and all 5 agree (+ a length-matched neutral note).
- **dep:** the same 5-model agreement **plus a mechanism disclosure** — "all five models were sent the
  **same prompt**, which did not specify one needed detail; each model filled that gap on its own." This
  states the *cause* of the correlated agreement, **not** a verdict ("counts as one, not five"), so a
  positive H-U2a reflects the participant reasoning about shared-source dependence, not obeying an
  instruction to discount. Neutral (non-alarm) styling.
- **Caveats (‹CONFIRM›, owner-decided):** confidence is a **1–5 star** rating (not a 0–100 slider); real
  brand names are used (possible brand-trust confound; the 1-vs-5 count is the manipulation and brand
  exposure is spread across items); the comprehension check's correct option is **pre-selected** (so it is
  not used as an exclusion).

## 6. Procedure (~11 min)

Language choice → **consent** (§13, with a recorded affirmative-consent control) → instructions
(pre-announcing that some tasks show 1 AI and others 5, and that **some answers are fine to use**) → a
non-scored **worked example** (which does **not** state the answer key) → comprehension check (correct
option pre-selected; ≤2 attempts) → **14 trials** → one instructed-response **attention check** (after
trial 8) → brief demographics (**age bracket**, incl. "Under 18"; + one AI-literacy item) → **debrief**
(discloses the curated displays and the deliberate underspecification).

Per trial, the participant first chooses **Accept-as-is vs Flag-missing-info** and gives a **1–5 star
rating of confidence in the displayed AI answer itself**. This decision is then committed. Only if
Flag was chosen does a second page reveal the clarification choices: four substantive options
(exactly one GOLD on underspecified items) plus **Other**. Participants may view the prior page in a
read-only panel but cannot revise the submitted decision or confidence.

## 7. Measures

- **Primary (confirmatory):** accept-as-is (binary), on **underspecified** items.
- **Secondary:** confidence (1–5 stars); **discrimination** = accept(complete) − accept(underspecified) by
  condition; objective **gap-identification** (underspecified & flagged trials only; deterministic scoring
  against the item key — no LLM judge); first-exposure accept.
- Recorded per trial: `session_code, participant_id, label, item_id, condition, complete, accept, confidence,
  gap_choice (4 = Other), gap_correct,
  rt_sec, order_index, group_g, lang` + participant-level exclusion fields.

## 8. Exclusion criteria (pre-specified, applied before analysis)

Exclude a participant **only if**: fails the **attention check**; or **duplicate** id. **No minimum-time
exclusion** — fast responders are kept. The comprehension check is pre-selected and is **not** an
exclusion; **confidence-straightlining is NOT an exclusion** (excluding on a DV biases effects). Total time
and straightlining are recorded for description only. Excluded participants are replaced up to the
recruitment cap; report N excluded.

## 9. Analysis plan

- **PRIMARY (confirmatory) = the two behavioral accept contrasts on UNDERSPECIFIED items:** GEE logistic
  regression, exchangeable working correlation, clustered on participant, item fixed effects,
  **Mancl–DeRouen bias-reduced covariance**. Contrasts H-U1a (fake vs single), H-U2a (dep vs fake),
  directional one-sided, **Holm** over the 2 at family-wise α = 0.05. This is the frozen engine and matches
  the power simulation (§10). A crossed-random-intercept GLMM is a sensitivity check.
- **Calibration safeguard:** GEE is mildly liberal in small samples (FWER ≈ 0.07 in the N=65 null
  simulation), so a **cluster-permutation test** (shuffling condition labels within participant) is
  pre-registered as the calibrated sensitivity analysis, and calibration is re-checked at the pilot.
- **SECONDARY:** confidence contrasts H-U1b/H-U2b (GEE Gaussian, same structure; the 1–5 rating treated as
  approximately interval, with an ordinal mixed model as sensitivity); **discrimination** (condition ×
  completeness interaction on accept, over all 14 items); first-exposure; gap-identification. Reported
  descriptively / with uncorrected one-sided p, **not** in the Holm family.
- **Toolchain:** Python `statsmodels`, frozen script `analysis/preregistered_analysis.py`; power in
  `analysis/power_analysis.py`. The script is validated on simulated data (rejects both primary contrasts
  under the pre-registered effect, ~none under the null) and frozen with this document.
- Confirmatory vs exploratory strictly separated in reporting.

## 10. Power analysis

Simulation-based (`analysis/power_analysis.py`; GEE logistic with participant + item random intercepts;
150 sims/cell), family-wise Holm over the 2 primary accept contrasts.

| effect | N | power H-U1a | power H-U2a | **both** |
|---|---|---|---|---|
| pre-registered (underspecified accept single/fake/dep ≈ .40/.57/.42) | 50 | 0.98 | 0.95 | 0.93 |
| pre-registered | **65** | 0.97 | 0.97 | **0.95** |
| pre-registered | 80 | 0.99 | 0.99 | 0.99 |
| **conservative** (fake +0.5 logit; dep restores) | 65 | 0.62 | 0.64 | **0.49** |
| conservative | 90 | 0.83 | 0.84 | **0.76** |

**Decision:** **recruit ≈ 65** for the expected effect (both-power 0.95); **recruit ≈ 90 if effects may be
small.** Calibration (N=65 null): per-test type-I ≈ 0.047; FWER ≈ 0.07 → the permutation sensitivity (§9)
and a pilot calibration check guard against the mild liberality. **Smallest effects of interest
(pre-registered):** fake−single ≥ ‹CONFIRM: 8 pp› on accept; dep−fake ≥ ‹CONFIRM: 6 pp›.

## 11. Mandatory pilot (go / no-go) — before freeze / launch

Run a **design-validation pilot, n ≈ 20**, on the real app (data discarded). Proceed **only if all** hold;
otherwise revise and re-pilot:
1. **Ceiling/floor:** accept(single, underspecified) ∈ **[0.35, 0.75]**.
2. **Manipulation:** accept(fake) − accept(single) on underspecified ≥ **+5 pp** in the predicted direction.
3. **Gap-ID informativeness:** GOLD accuracy **< 0.90** (else harden the distractors).
4. **Suspicion funnel:** **< 40%** of pilot participants correctly name the hypothesis (blind-coded probe).
5. Re-estimate power at the pilot baseline and set final N.

## 12. Deviations log
(Empty at freeze. Any post-freeze change is appended with date + reason; it does not alter the confirmatory
analysis.)

## 13. Ethics

- IRB / exemption: ‹CONFIRM: Chang'an University route›. Do not launch before determination.
- **Consent:** a recorded affirmative-consent control before any stimulus; PI name, IRB #,
  voluntary withdrawal, and a decline path stated (see `ethics/consent.md`). **All ages**; minors need
  guardian consent (‹CONFIRM›).
- **Deception (mild):** the multi-model "agreement" displays are curated and the items intentionally
  underspecified; a **full debrief** discloses this and the aim.
- Data: anonymous platform/label IDs only; stored de-identified; retained ‹N years›; aggregate/anonymized
  results may be shared with the paper (OSF).

### Open items to confirm before freezing
Platform/recruitment channel & pay; minors' guardian-consent procedure (or restrict to 18+); min-time
threshold; smallest effects of interest; IRB route; whether to keep 1–5 stars vs 0–100 and real vs generic
model names (currently kept per owner).
