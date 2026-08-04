# Pre-registration (DRAFT — not yet frozen)

**Study:** Do people over-rely on unanimous multi-model AI consensus, and does surfacing
evidential dependence reduce it?
**Paper:** *When Consensus Lies: Fake Redundancy in Multi-Model AI Systems* — human-validation study.
**Status:** DRAFT for owner review. **Do NOT collect data until this is frozen on OSF/AsPredicted.**
**Provenance note (Law 7):** hypotheses, conditions, primary DVs, exclusions, and the analysis
script must be frozen *before* the first non-pilot participant. No metric redefinition afterward.

> ⚠️ **CONFIRM-BEFORE-FREEZE** items are flagged inline with `‹CONFIRM›`.

---

## 1. Background & why this study (kept tight to two gaps)

The paper establishes, as **system properties** (no humans needed):
- **A** — five same-prompt agents supply ≈ one independent judgment (n_eff = 1.10, ICC = 0.89,
  same-item ΔCD = 0.82): *fake redundancy*.
- **B** — current product UIs render this as independent corroboration ("N/N agree").

Two claims the paper currently **borrows from the literature** rather than measures:
- **C** — users read unanimity as reliability and under-account for source non-independence
  (*correlation / system neglect*: Budescu & Yu 2007; Enke & Zimmermann 2019; Levy et al. 2022).
- **D** — surfacing *evidential dependence* would reduce that over-reliance (the demoted §9 design
  implication + the abstract's normative "should").

This study **measures C and D directly**. It is *not* logically required (the loop already closes on
system properties); its purpose is to convert borrowed→measured and restore human-in-the-loop CSCW
fit. Scope is deliberately limited to C and D — no additional defensive arms.

## 2. Hypotheses (directional, pre-registered)

Let **single** = one-model answer, **fake** = "5/5 models agree" unanimity, **dep** =
dependence-disclosed display.

- **H-U1 (C, over-reliance from fake consensus):**
  - H-U1a: P(accept-as-is | **fake**) > P(accept-as-is | **single**)
  - H-U1b: confidence(**fake**) > confidence(**single**)
- **H-U2 (D, dependence disclosure corrects it):**
  - H-U2a: P(accept-as-is | **dep**) < P(accept-as-is | **fake**)
  - H-U2b: confidence(**dep**) < confidence(**fake**)

Exploratory (not confirmatory): dep vs single; gap-identification accuracy across conditions;
effect moderation by AI-literacy / domain.

## 3. Design

- Online, **within-subjects**, single session, **3 display conditions × 12 items**, **Latin square**:
  each participant sees each item exactly once; conditions balanced within participant
  (4 trials/condition); item×condition rotation counterbalanced across participants.
- Participants do **not** hold the missing convention (matches the lost-handoff scenario, §8.4):
  the decisive disambiguator is *outside* the shown prompt (H1_external family).
- Trial order randomized per participant.

## 4. Participants

- **Bilingual** (English / Simplified Chinese, chosen on the first page). Delivered as a single
  participant link (oTree room / session-wide link), **team-recruited** (Prolific or a local pool /
  WeChat / university subject pool).
- **All ages are eligible** (no 18+ gate): we deliberately want variation across age. **Minors (<18)
  require guardian consent per IRB — confirm the consent/assent procedure before recruiting minors.**
- **Target N = 55 analyzable; recruit ≈ 65** (≈15% expected exclusions).
- Payment ≈ ‹CONFIRM› $2 (Prolific) or local-equivalent, for ~10 min.
- Stopping rule: fixed-N (recruit to the pre-set number); no optional stopping / peeking.
- Power basis (§10) assumes this N.

## 5. Materials

**5.1 Items (12).** Lay-readable underspecified workplace queries (general-population sample), each
anchored to one of the paper's H1_external **convention types** (fiscal-year start, rounding/remainder,
inclusive/exclusive date range, dedup, top-N tie, timezone, unit/scale, percentage base,
mean-vs-median, business-vs-calendar days, sort tie-break, null/blank handling) — one type per item.
Each is 2–3 sentences (~30–45 s), contains exactly one decision-relevant **unstated convention** whose
plausible values yield different answers, and the displayed AI answer silently commits to one reading.
Items are **bilingual** and identical across the three display conditions; authored by one model family
and **audited for construct validity by a different family** (`STIMULI-v2.md`). A verbatim expert
replication on the benchmark's own items is a possible follow-up.

**5.2 Display conditions (the only manipulation).** The scenario/task/answer text is identical across
conditions; only the *evidence framing* differs, shown in a **consistent card** with **real model-name
chips** (ChatGPT, Gemini, Claude, Copilot, DeepSeek). The "agreement" displays are **curated
illustrations**, disclosed at debrief.
- **single:** one AI model's answer (1 model chip).
- **fake:** 5 AI models were asked and all 5 agree (5 chips) + a length-matched neutral note.
- **dep:** the same 5-model agreement **plus a dependence disclosure that reveals NON-independence,
  not the correct value**: "⚠ these five answers are not independent — all five made the same single
  unstated assumption, so together they count as about **one** independent check, not five."
- **dependence-only (decided):** `dep` discloses non-independence **without naming which convention is
  correct** — this operationalizes claim D ("surface evidential *dependence*"); a premise-surfaced
  variant would conflate D with handing over the answer.
- **Caveat (real names):** real brand names add realism but introduce a possible brand-trust confound;
  the 1-vs-5 count remains the manipulation, and brand exposure is balanced across items.

## 6. Procedure (~10 min)

1. **Language choice** (English / 简体中文) → Consent (§12).
2. Instructions (which pre-announce that some tasks show 1 AI model, others 5) + a non-scored
   **worked example** + one **comprehension check** (correct option pre-selected; ≤2 attempts).
3. **12 trials.** Each trial: short query + AI answer in the assigned display condition, then:
   - **Primary behavioral DV — Accept vs Flag** (forced choice):
     "Would you (a) **use this answer as-is**, or (b) **flag that key information is missing / ask a
     clarifying question first**?"
   - If (b): pick which clarifying question is most important from ‹4› options, exactly one of which
     targets the true missing convention (**objective gap-identification** measure).
   - **Primary subjective DV — Confidence:** a **1–5 star** rating (1 = not at all sure,
     5 = completely sure): "How confident are you this answer is correct?"
   - ≤ ~40 s/trial → ≤ ~8 min for 12 trials.
4. Brief demographics (**age bracket**, incl. "Under 18") + single AI-literacy item (exploratory).
5. **Debrief** (§12): the "AI consensus" displays were curated illustrations and the answers were
   intentionally underspecified; explain the study aim.

## 7. Measures

- **Primary:** (i) accept-as-is (binary, per trial); (ii) confidence (**1–5 star** rating, per trial).
- **Objective gold (no LLM judge):** gap-identification = picked the clarifying question that names
  the true missing convention (deterministic scoring against the item key).
- **Secondary/exploratory:** clarifying-question choice distribution; per-condition RT; moderators.

## 8. Exclusion criteria (pre-specified, applied before analysis)

Exclude a participant if any: fails the comprehension check twice; fails an embedded
**instructed-response attention check**; total time < ‹CONFIRM: 120 s› or implausibly fast;
straight-lines the star rating (zero variance across all 12 trials); duplicate IP/Prolific ID.
Excluded participants are replaced up to the recruitment cap. Report N excluded per rule.

## 9. Analysis plan

- **Accept (binary) [confirmatory]:** GEE logistic regression, exchangeable working correlation,
  clustered on participant, with item as fixed-effect covariates (`accept ~ fake + dep + item`).
  This is the frozen confirmatory engine and matches the power simulation (§10). Primary contrasts:
  fake−single (H-U1a), dep−fake (H-U2a). A crossed-random-intercept GLMM (participant + item) is
  reported only as a **sensitivity** check.
- **Confidence (1–5 stars):** linear mixed model (rating treated as approximately interval; an ordinal
  mixed model is a sensitivity check), same random-effects structure. Contrasts: fake−single (H-U1b),
  dep−fake (H-U2b).
- **Fitting:** Python `statsmodels`, in the frozen script `analysis/preregistered_analysis.py`
  (accept → GEE, confidence → `MixedLM`). An R `lme4`/`glmmTMB` GLMM may additionally be reported as a
  sensitivity check. The script is validated on simulated data (rejects all 4 under the pre-registered
  effect; rejects ~none under the null) and is frozen together with this document.
- **Multiplicity:** Holm correction across the **four** primary contrasts; one-sided at the
  directional hypotheses; α = 0.05 family-wise. Report adjusted p, effect sizes (odds ratios /
  mean diffs), and 95% CIs.
- **Confirmatory vs exploratory** strictly separated in reporting.
- The analysis script is written against **simulated** data and frozen with this document; only the
  input data file changes at run time.

## 10. Power analysis

Simulation-based (GEE logistic, participant- and item-level random intercepts; 400 sims/point).
Assumptions: p(accept | single)=0.55, **fake=0.72** (correlation-neglect effect ≈ +17 pp),
**dep=0.56** (disclosure ≈ restores to single), SD_participant=0.6, SD_item=0.5 (logit),
one-sided α=0.025 per family.

| items | N | power H-U1 (fake>single) | power H-U2 (dep<fake) | **both** |
|---|---|---|---|---|
| 9  | 50 | 0.80 | 0.76 | 0.66 |
| **12** | **50** | **0.93** | **0.90** | **0.85** |
| 12 | 60 | 0.94 | 0.93 | 0.90 |
| 12 | 50 (conservative: fake=.68, dep=.58) | 0.71 | 0.53 | 0.43 |

**Decision:** **12 items, recruit ≈65 → ≈55 analyzable.** H-U2 (D) is the power-limiting arm; if the
disclosure effect is weak the study is underpowered for D, so the **dep** manipulation should be made
maximally salient. **Smallest effect of interest (pre-registered):** fake−single ≥ ‹CONFIRM: 10 pp›
on accept-rate; dep−fake ≥ ‹CONFIRM: 8 pp›. Effects below these are treated as "not detected," not
"absent." (The power table concerns the behavioral accept DV; the confidence DV — a 1–5 star rating —
is an additional secondary safeguard.)

## 11. Deviations log

(Empty at freeze. Any post-freeze change is appended here with date + reason; it does not alter the
confirmatory analysis.)

## 12. Ethics

- IRB / exemption: ‹CONFIRM: Chang'an University route›. Do not launch before determination.
- Informed consent before any stimulus; voluntary; withdraw anytime.
- **Deception:** mild — displays are curated and answers intentionally underspecified; **full debrief**
  at the end explains this and the aim. No sensitive data collected.
- Data: anonymous platform IDs only; store de-identified; no free-text PII requested.
- Fair pay (≈ $12/hr).

---

### Open items to confirm with owner before freezing
1. Platform (Prolific) + budget/payment.
2. `dep` = dependence-only (recommended) vs premise-surfaced.
3. The 12 items: domains + exact convention per item (needs a separate stimulus spec).
4. Exclusion thresholds (min time, comprehension attempts).
5. Smallest-effect-of-interest values.
6. IRB route at Chang'an University.
7. Analysis toolchain (R lme4 vs Python).
