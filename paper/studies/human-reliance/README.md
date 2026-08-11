# Human-reliance study — *When Consensus Lies*

**Do people over-rely on an apparently unanimous multi-model AI answer, and can a disclosure of
shared-input dependence reduce that reliance?**

This folder contains the current implementation and documentation for a bilingual, online,
pre-registered human study accompanying *When Consensus Lies: Fake Redundancy in Multi-Model AI
Systems*. The runnable oTree code is the source of truth.

> **Status:** redesigned implementation complete; do not collect data until the owned
> pre-registration is frozen and the required ethics/IRB determination and consent procedures are in
> place.

## 1. Why this study

The system work shows that multiple model outputs can look like independent corroboration even when
they arise from the same underspecified input. This study tests the human-reliance link: whether an
interface saying that five AI models agree increases acceptance of an answer that silently fills a
missing convention, and whether explaining the shared-prompt mechanism reduces this effect.

The study is deliberately narrow. It tests decisions about the displayed answers in controlled
workplace-style tasks; it does not claim that all AI agreement or all AI reliance is inappropriate.

## 2. Confirmatory hypotheses

The confirmatory outcomes are the two behavioral `accept` contrasts **on underspecified items**:

| ID | Prediction |
|---|---|
| **H-U1a** | `accept(fake) > accept(single)` |
| **H-U2a** | `accept(dep) < accept(fake)` |

Here, `accept=1` means “ready to use as-is.” On an underspecified item, the appropriate response is
to flag the missing convention. The two directional, one-sided tests use GEE logistic models with
participant clustering, item fixed effects, and Mancl–DeRouen bias-reduced covariance; Holm corrects
these two tests at family-wise α=.05.

Pre-registered secondary analyses (not in the Holm family) are the corresponding 1–5-star
confidence contrasts, the condition × completeness discrimination interaction on `accept`, a
first-exposure between-subjects read, and objective gap identification. The interaction asks whether
the fake-consensus display shrinks the accept gap between complete and underspecified items, and
whether the dependence disclosure restores it.

## 3. Design

- **Online, within-subjects**, about **11 minutes**.
- **14 items:** 9 underspecified items (U1–U9) and 5 complete controls (C1–C5).
- **3 display conditions:** `single`, `fake`, `dep`.
- Every participant sees every item once. A balanced Latin square assigns
  `condition(g, i) = CONDITIONS[(i + g) % 3]`, with arrival-round-robin `g ∈ {0,1,2}`.
- Participant trial order and each trial’s four substantive clarification-option order are randomized;
  a fixed fifth **Other** option is appended.
- One stable participant link serves both **English and 简体中文**; language is selected on the first
  in-page screen.

The 9 underspecified items omit a decisive convention—fiscal-year start, rounding/remainder,
range inclusiveness, deduplication, timezone, percentage base, mean versus median, business versus
calendar days, or null/blank handling. Their answers silently assume one convention, so FLAG is
appropriate. The 5 complete items state the needed convention and have answers that should be
ACCEPTED. These controls stop an “always flag” strategy from forcing the accept baseline to floor and
support the discrimination check.

## 4. Display conditions

Scenario, task, and answer text are identical across conditions. All answers appear in a consistent
card; only their source framing differs.

| Condition | Display |
|---|---|
| `single` | One chip carrying one real model name: ChatGPT, Gemini, Claude, Copilot, or DeepSeek. |
| `fake` | Five real-name chips—ChatGPT, Gemini, Claude, Copilot, DeepSeek—all show the same answer, with a neutral note that five different models were asked. |
| `dep` | The same five-chip agreement display, plus a neutral mechanism disclosure: all five received the **same prompt**, which omitted one needed detail, and each filled that gap on its own. |

The `dep` text is not a verdict and does not identify the omitted convention or correct answer. The
agreement displays are researcher-curated illustrations rather than live model outputs; this mild
deception is disclosed at debrief.

## 5. Participant experience and measures

Participants complete language selection → consent → instructions → a non-scored worked example →
a comprehension check → 14 trials → an attention screen after round 8 → demographics → debrief.
Instructions announce that some trials show one AI and some show five, and that some answers are fine
to use. The worked example does not state an answer key. The comprehension check’s correct option is
pre-selected and is recorded, but is not used as an exclusion.

Each trial uses one page. Participants choose:

- **Ready to use as-is** (`accept=1`), or
- **Important information is missing** (`accept=0`).

They then provide a required **1–5-star confidence** rating in the displayed AI answer itself
(not in their own decision or selected clarification). The clarification section is initially hidden.
The first click on Confirm commits the decision and confidence client-side, locks them, and reveals
the clarification section below the Back and Confirm buttons. A second click submits the item;
Flag requires a clarification choice, including the fixed **Other** option. A real previous-page control can
return to the instructions or an earlier trial; earlier
responses may be edited and the revised values are retained. On underspecified
trials only, the single decisive clarification is scored deterministically as `gap_correct`; complete trials have
generic options and no gap score. Response time, language, age bracket (including Under 18), and
AI-use frequency are retained.

## 6. Data quality and exclusions

The implemented, functional participant-level exclusions are:

1. failed instructed-response attention check;
2. duplicate ID.

Comprehension is not excluded because its correct response is pre-selected. Fast completion and
uniform confidence ratings are retained; `total_time_sec` and `straightline_confidence` are descriptive
fields rather than exclusion rules.

## 7. Sample, calibration, and pilot gate

The archived simulation in `analysis/power_analysis.py` supports a target of approximately
**55–65 analyzable participants**, recruited with a buffer. Under the expected effect, power for
both behavioral contrasts is about .93 at N=50 and .95 at N=65. Under a
conservative/smaller effect it is about .49 at N=65 and .76 at N=90; recruit about **90** if such
smaller effects are plausible.

| Scenario | N | Power for both accept contrasts |
|---|---:|---:|
| Expected effect | 50 | ~.93 |
| Expected effect | 65 | ~.95 |
| Conservative/smaller effect | 65 | ~.49 |
| Conservative/smaller effect | 90 | ~.76 |

At N=65, simulated null calibration was approximately .047 per test and .07 FWER, indicating mildly
liberal small-sample GEE behavior. A permutation sensitivity analysis is pre-registered and
calibration is re-checked at pilot.

Before launch, run and discard a mandatory **n≈20 go/no-go pilot**. Proceed only if single-condition
underspecified acceptance is ~.35–.75; fake minus single acceptance is at least +5 percentage points
in the predicted direction; gap-identification accuracy is below .90 (otherwise harden distractors);
and fewer than 40% of participants correctly guess the hypothesis.

## 8. Implementation and deployment

`otree/` contains the runnable oTree 6 app. It supplies the one-link language choice, Latin-square
assignment, option randomization, real-name model chips, star confidence rating, quality fields, and
trial-level custom export. Deploy a persistent web service and Postgres database on free-tier
**Render** or **Fly.io**, then share the stable oTree room participant URL. See `otree/README.md` and
`otree/DEPLOY.md`.

## 9. Export and analysis

One CSV row is produced per trial:

```text
session_code,participant_id,label,item_id,condition,complete,accept,confidence,gap_choice,gap_correct,rt_sec,
order_index,group_g,lang,passed_comprehension,passed_attention,total_time_sec,
straightline_confidence,duplicate_id,age_group,ai_use
```

`analysis/preregistered_analysis.py` consumes this schema. Its frozen confirmatory models and
secondary analyses are described in `analysis/README.md`; run it with:

```bash
python analysis/preregistered_analysis.py --data reliance_custom.csv
```

## 10. Directory map

```text
README.md                     study overview (this file)
STIMULI-v2.md                 current 14-item design and provenance
SURVEY-implementation.md      platform, flow, randomization, displays, export
analysis/
  preregistered_analysis.py   frozen analysis pipeline
  power_analysis.py           archived power and calibration simulation
  README.md                   analysis instructions and schema
otree/
  reliance/stimuli.py         authoritative exact bilingual items and `complete` flags
  reliance/content.py         authoritative UI copy
  reliance/__init__.py        assignment, page logic, and custom export
  README.md, DEPLOY.md        run and deployment instructions
PREREGISTRATION.md            owned pre-registration document (not edited here)
ethics/                       owned ethics materials (not edited here)
```
