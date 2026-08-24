# Pre-registration (FROZEN)

**Study:** Do people over-rely on unanimous multi-model AI "consensus," and does surfacing the
*mechanism* of that consensus (a shared prompt with an unstated detail) reduce it?
**Paper:** *When Consensus Lies: Fake Redundancy in Multi-Model AI Systems* — human-validation study.
**Status:** **FROZEN 2026-08-24.** The git commit carrying this document is the freeze point; the
OSF/AsPredicted record mirrors it. Confirmatory data collection begins only after this commit, and all
data recorded before it is outside the confirmatory dataset (§8).
**Provenance (Law 7):** hypotheses, conditions, primary DVs, exclusions, and the analysis script
(`analysis/preregistered_analysis.py`) are frozen with this document. No metric redefinition afterward;
any later change is appended to the deviations log (§12) and reported as exploratory.

> This design was revised after a 3-model adversarial ROI review (Opus 5 / GPT-5.6 / Gemini 3.1). Key
> changes: added well-specified ("complete") items so the accept baseline is not at floor; the primary DV
> is the behavioral accept contrast (well-powered); the `dep` disclosure states the *mechanism*, not a
> verdict; inert exclusions were fixed.

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

- **All ages eligible** (no 18+ gate): we deliberately want age variation. Minors (<18) participate under
  the guardian-consent procedure of the approved protocol (§13). Because Prolific prohibits <18, all-ages
  recruitment implies a **team/local channel** (university pool / WeChat / 平台如见数), not Prolific.
- **Target ≈ 65 analyzable; recruit with a buffer for exclusions.** If effects may be small, **recruit ≈ 90**
  (see §10). Pre-freeze observation: roughly half of the people who open the link complete all 14 trials,
  so reaching 65 analyzable participants requires on the order of 130 link opens.
- Team-recruited volunteers; **no payment**. Fixed-N stopping rule; no optional stopping / peeking (the
  §11.2 interim check examines no contrast and therefore does not constitute peeking).

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
Gemini, Claude, MAI, DeepSeek; single = 1 chip, fake/dep = 5 chips). The "agreement" displays are
**curated illustrations**, disclosed at debrief.
- **single:** one AI model's answer.
- **fake:** 5 AI models were asked and all 5 agree (+ a length-matched neutral note).
- **dep:** the same 5-model agreement **plus a mechanism disclosure** — "all five models were sent the
  **same prompt**, which did not specify one needed detail; each model filled that gap on its own." This
  states the *cause* of the correlated agreement, **not** a verdict ("counts as one, not five"), so a
  positive H-U2a reflects the participant reasoning about shared-source dependence, not obeying an
  instruction to discount. Neutral (non-alarm) styling.
- **Caveats (owner-decided, settled at freeze):** confidence is a **1–5 star** rating (not a 0–100 slider);
  real brand names are used (possible brand-trust confound; the 1-vs-5 count is the manipulation and brand
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
Flag was chosen, the first Confirm click locks the decision/confidence and the hidden clarification
section reveals four substantive options (exactly one GOLD on underspecified items) plus **Other**,
below the navigation buttons. The second click submits the item. The real **Back to previous page /
返回上一页** control can return to the instructions or an earlier trial; participants may edit a
prior response, and the last submitted values are retained.

## 7. Measures

- **Primary (confirmatory):** accept-as-is (binary), on **underspecified** items.
- **Secondary:** confidence (1–5 stars); **discrimination** = accept(complete) − accept(underspecified) by
  condition.
- **Exploratory:** first-exposure accept; objective **gap-identification** (underspecified & flagged trials
  only; deterministic scoring against the item key — no LLM judge). Gap identification is **exploratory
  rather than secondary** because on every underspecified item the GOLD option is the only substantive one
  and the three distractors concern formatting, so `gap_correct` largely indexes *whether the participant
  flagged for a substantive reason* rather than fine-grained localization of the missing premise (§11.1).
  It is reported descriptively and no claim rests on it.
- Recorded per trial: `session_code, participant_id, label, item_id, condition, complete, accept, confidence,
  gap_choice (4 = Other), gap_correct,
  rt_sec, order_index, group_g, lang` + participant-level exclusion fields.

## 8. Exclusion criteria (pre-specified, applied before analysis)

**Confirmatory dataset.** Only oTree sessions created **after this freeze commit** contribute to the
confirmatory analysis. At freeze the database still held pre-freeze development, demo, and pilot sessions,
all run on an **earlier version of the instrument**; they are excluded wholesale. Their full export was
archived offline before launch, and the sessions themselves are **deleted from the production database
before the confirmatory session is created**, so a post-launch export contains confirmatory data only and
the analysis script needs no session filter. For auditability the 19 deleted pre-freeze session codes were:
`2dntn1fq, 311tpalg, 4sm6z03e, 5ip6qfe1, 6ooaay1y, 9loic7o5, ae2rgx5o, c9hs1uvy, ciuwofod, csfmicg4,
dkuq55qp, j87wlnsh, l4qyr3ee, om27jr6v, weaylru1, wkk0jcnk, wsmyieb4, yu38q0ns, zm8sktvr` (174 participant
slots, 7 of them completers; last pre-freeze activity 2026-08-24T12:13Z).

Note that an oTree room **pre-creates every participant slot when a session is created**, so an export
contains 14 blank rows for each seat that was never claimed. These are removed by exclusion 1 below.

**Participant-level exclusions.** Within the confirmatory dataset, exclude a participant **only if**:

1. the participant did **not complete all 14 trials** (an oTree room pre-creates a participant slot for
   every seat, so unused slots and partway dropouts both appear in the export; the design is
   within-subjects and the Latin square balances conditions only over the full set of 14); or
2. the participant **fails the instructed-response attention check**.

**There is no duplicate-participation exclusion.** Recruitment uses a single open, anonymous link with no
identifier and no compensation; the same person may take the study more than once, and such repeats
**cannot be detected**. The `duplicate_id` field is therefore always 0 and carries no information. We
neither restrict nor attempt to detect repeat participation, and we do not claim to. Because there is no
payment, the incentive to repeat is low; any residual repeats are treated as an acknowledged limitation
rather than as an exclusion.

**No minimum-time exclusion** — fast responders are kept. The comprehension check is pre-selected and is
**not** an exclusion; **confidence-straightlining is NOT an exclusion** (excluding on a DV biases effects).
Total time and straightlining are recorded for description only. Excluded participants are replaced up to
the recruitment cap; report N excluded by rule.

## 9. Analysis plan

- **PRIMARY (confirmatory) = the two behavioral accept contrasts on UNDERSPECIFIED items:** GEE logistic
  regression, exchangeable working correlation, clustered on participant, item fixed effects,
  **Mancl–DeRouen bias-reduced covariance**. Contrasts H-U1a (fake vs single), H-U2a (dep vs fake),
  directional one-sided, **Holm** over the 2 at family-wise α = 0.05. This is the frozen engine and matches
  the power simulation (§10). A crossed-random-intercept GLMM is a sensitivity check.
- **Calibration safeguard:** GEE is mildly liberal in small samples (FWER ≈ 0.07 in the N=65 null
  simulation), so a **cluster-permutation test** (shuffling condition labels within participant) is
  pre-registered as the calibrated sensitivity analysis, and is reported alongside the GEE result for both
  confirmatory contrasts.
- **SECONDARY:** confidence contrasts H-U1b/H-U2b (GEE Gaussian, same structure; the 1–5 rating treated as
  approximately interval, with an ordinal mixed model as sensitivity); **discrimination** (condition ×
  completeness interaction on accept, over all 14 items). Reported descriptively / with uncorrected
  one-sided p, **not** in the Holm family.
- **EXPLORATORY:** first-exposure; gap-identification (see §7 for why it is exploratory); age /
  AI-literacy moderation. Reported descriptively only.
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
guards against the mild liberality. **Smallest effects of interest (pre-registered):** fake−single ≥ **8 pp**
on accept; dep−fake ≥ **6 pp**.

## 11. Instrument diagnostics: the pre-freeze pilot, and the interim check

### 11.1 Pre-freeze pilot (completed; data excluded)

A design-validation pilot was run on the live app in session `9loic7o5` (2026-08-07 to 2026-08-09):
6 participants started, **5 completed all 14 trials, 4 passed the attention check**. It fell well short of
the intended n ≈ 20, and the instrument has since been corrected (three item texts and the bilingual
interface copy), so **the pilot ran on an earlier version of the instrument and its data are excluded from
the confirmatory dataset (§8)**. Its results are recorded here as diagnostics, not as a passed gate:

| Diagnostic | Criterion | Observed (n = 4) | Verdict |
|---|---|---|---|
| Ceiling/floor: accept(single, underspecified) | ∈ [0.35, 0.75] | 0.667 | pass |
| Manipulation: accept(fake) − accept(single) | ≥ +5 pp | +0.000 | not interpretable at n = 4 |
| Gap-ID informativeness: GOLD accuracy | < 0.90 | 1.000 (13 flagged trials) | fail |
| Suspicion funnel | < 40% name the hypothesis | not measured | no probe field implemented |

The gap-ID result is a **property of the option set rather than a sampling outcome**: on every
underspecified item the GOLD option is the only substantive one and all three distractors concern
formatting, so anyone who flags for a substantive reason selects GOLD. Rather than rewrite the option sets
immediately before launch, gap identification is **demoted to exploratory** (§7, §9) and the reason is
stated. The manipulation diagnostic is uninformative at n = 4 and is carried forward to §11.2.

### 11.2 Interim instrument check (pre-registered, at the first 20 completers)

Because the pre-freeze pilot is neither large enough nor run on the current instrument, the go/no-go
function is relocated **inside** the confirmatory collection. When the confirmatory dataset first reaches
**20 analyzable completers** (§8), a single interim check is run:

- **I1 Ceiling/floor:** accept(single, underspecified) ∈ **[0.35, 0.75]**.
- **I2 Data integrity:** condition assignment is balanced as designed, and completion, language, and
  response-time distributions contain no pathology (e.g. mass straightlining).

**If I1 fails, collection stops**, the instrument is revised, the revision is appended to §12, and a new
confirmatory dataset is started; the pre-revision data are then reported as exploratory only. If I1 holds,
collection continues uninterrupted to the target N (§10).

**Hard constraint — no contrast is examined at the interim.** The interim check is restricted to
single-condition descriptive quantities and design integrity. The confirmatory contrasts
(fake vs single, dep vs fake) and the confidence contrasts **are not computed, viewed, or reported at the
interim, and the decision to continue does not depend on them**. Because no test of a confirmatory
hypothesis occurs at the interim, this is a manipulation/instrument check rather than an interim analysis,
the fixed-N stopping rule of §4 is preserved, and **no alpha adjustment is required**. Examining a contrast
at the interim would constitute optional stopping and is explicitly prohibited.

These 20 participants are **not discarded**: they are part of the confirmatory dataset and count toward N.

## 12. Deviations log
(Empty at freeze. Any post-freeze change is appended with date + reason; it does not alter the confirmatory
analysis.)

## 13. Ethics

- **IRB:** approval obtained before launch; the protocol number is added to the public record and to the
  paper at submission.
- **Consent:** a recorded affirmative-consent control before any stimulus, stating the withheld purpose,
  voluntariness, and a decline path (see `ethics/consent.md` and the deployed consent screen).
- **All ages eligible;** minors participate under the guardian-consent procedure of the approved protocol.
- **Deception (mild):** the multi-model "agreement" displays are curated and the items are intentionally
  underspecified; a **full debrief** discloses both and the study aim.
- **Data:** no direct identifiers; anonymous oTree participant codes only; stored de-identified and
  retained per the approved protocol; aggregate/anonymized results may be shared with the paper (OSF).
  Because recruitment uses a single open anonymous link, repeat participation is neither restricted nor
  detectable (§8).

### Decisions recorded at freeze
All previously open items are settled as follows: all ages eligible (no 18+ gate); no payment;
team/local recruitment channel; **1–5 star** confidence rather than a 0–100 slider; **real** model-name
chips rather than generic labels; the comprehension check remains pre-selected and is not an exclusion;
no duplicate-participation exclusion (§8); smallest effects of interest fixed at 8 pp and 6 pp (§10);
gap identification demoted to exploratory (§7, §11.1); the go/no-go pilot replaced by the §11.2 interim
check. Nothing in this document is subject to further change; later changes go to §12.
