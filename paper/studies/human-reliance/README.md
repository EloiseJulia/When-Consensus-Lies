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

Here, `accept=1` means “the answer has enough information and can be used.” On an underspecified item, the appropriate response is
to flag the missing convention. The two directional, one-sided tests use GEE logistic models with
participant clustering, item fixed effects, and Mancl–DeRouen bias-reduced covariance; Holm corrects
these two tests at family-wise α=.05.

Pre-registered secondary analyses (not in the Holm family) are the corresponding 1–5-star
confidence contrasts and the condition × completeness discrimination interaction on `accept`. A
first-exposure read and objective gap identification are **exploratory** (`PREREGISTRATION.md` §7
explains why gap identification is not secondary). The interaction asks whether
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
| `single` | One chip carrying one real model name: ChatGPT, Gemini, Claude, MAI, or DeepSeek. |
| `fake` | Five real-name chips—ChatGPT, Gemini, Claude, MAI, DeepSeek—all show the same answer, with a neutral note that five different models were asked. |
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

- **The answer has enough information and can be used** (`accept=1`), or
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

The pre-specified participant-level exclusions are exactly two:

1. did not complete all 14 trials (an oTree room pre-creates a participant slot per seat, so unclaimed
   seats and partway dropouts both appear in the export);
2. failed the instructed-response attention check.

There is deliberately **no duplicate-participation exclusion**: recruitment uses a single open anonymous
link, one person may submit more than once, and repeats cannot be detected (`duplicate_id` is always 0).
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
liberal small-sample GEE behavior. A permutation sensitivity analysis is pre-registered and is reported
alongside the GEE result for both confirmatory contrasts.

A design-validation pilot was run before freeze (session `9loic7o5`, 5 completers, 4 after the attention
check) on an **earlier version of the instrument**; its data are excluded and its results are recorded as
diagnostics in `PREREGISTRATION.md` §11.1. Because that pilot was far below the intended n≈20 and predates
the current items and copy, the go/no-go function was moved **inside** the confirmatory collection: at the
first **20 analyzable completers** a single interim check verifies that single-condition underspecified
acceptance sits in ~.35–.75 and that assignment and response distributions are sound. **No condition
contrast is computed or examined at that interim**, so the fixed-N stopping rule is preserved and no alpha
adjustment is needed. Those 20 participants count toward the final N. See `PREREGISTRATION.md` §11.2.

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
