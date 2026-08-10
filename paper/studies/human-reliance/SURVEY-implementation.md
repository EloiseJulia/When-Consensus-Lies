# Survey implementation spec — human-reliance study

Serves the implemented oTree app in `otree/reliance/` and exports the schema consumed by
`analysis/preregistered_analysis.py`. The code is the source of truth.

---

## 1. Platform and deployment

**Platform: oTree 6 (Python).** The app implements the within-subject Latin square, randomized
trial and option orders, deterministic gap scoring, bilingual UI, and one-row-per-trial export.

Participants use **one stable room link**. The first in-page screen asks them to choose **English** or
**简体中文**, after which every page uses that language; separate language links are not needed.
Deploy on free-tier **Render** (web service + Postgres) or **Fly.io**. See `otree/DEPLOY.md`.
Recruitment is team-run (for example, email, WeChat, or a participant pool), not Prolific-gated:
all ages are eligible subject to the approved consent/guardian-consent procedure for minors.

## 2. Assignment and randomization

- There are **14 items**: 9 underspecified (U1–U9) and 5 complete controls (C1–C5).
- Conditions are `CONDITIONS = [single, fake, dep]`. Participant group
  `g = (id_in_subsession - 1) % 3`; for item index `i`:
  ```
  condition(g, i) = CONDITIONS[(i + g) % 3]
  ```
  This balanced Latin square assigns every participant every item once and balances each item across
  the three conditions. With 14 items, individual condition counts differ by at most one.
- Trial order is shuffled per participant. The four clarification options are shuffled per trial.
  `order_index` and `group_g` are exported.

## 3. Flow, timing, and quality gates (~11 min)

1. In-page language choice.
2. Consent.
3. Instructions: some tasks show one AI and some show five; some answers are fine to use.
4. Non-scored worked example. It illustrates the task but **does not state an answer key**.
5. Comprehension check. Its correct option is pre-selected; it is recorded but **not an exclusion**.
6. Fourteen trials.
7. An instructed-response attention screen after round 8 (“choose Disagree”).
8. Age bracket (including **Under 18**) and AI-use frequency.
9. Debrief: the agreement displays were researcher-curated illustrations, not live model outputs.

The target completion time is about **11 minutes**. Participants are excluded only for a failed
attention check or a duplicate ID. Fast completion and uniform confidence ratings are retained;
`total_time_sec` and `straightline_confidence` are descriptive fields only.

## 4. Trial screen and measures

Every trial uses one consistent card:

```
[ Situation ]       scenario
[ What's being asked ] task
[ AI answer card ]   condition-specific source framing + identical answer text
----------------------------------------------------------------
Is this answer ready to use, or is important information missing?
  ( ) Ready to use as-is                  -> accept = 1
  ( ) Important information is missing    -> accept = 0
If missing: choose the most important clarification (four randomized options)
How confident are you that the displayed AI answer itself is correct and ready to use?  1 ★ ... 5 ★
```

`accept` is the behavioral decision. On U1–U9, FLAG is appropriate and the selected decisive
clarification produces deterministic `gap_correct`; C1–C5 are fully specified, so ACCEPT is
appropriate and their generic clarification options are not scored. Confidence refers specifically
to the **displayed AI answer**, not to the participant's decision or chosen clarification. It is a
required **1–5-star** rating, not a 0–100 slider. Response time is recorded in seconds in export.

## 5. Display conditions

The answer text is identical across the three conditions. Model chips use real names:
**ChatGPT, Gemini, Claude, Copilot, DeepSeek**.

| Condition | Card content |
|---|---|
| `single` | One real-name model chip and its answer. |
| `fake` | All five real-name chips display the same answer, plus the neutral note: five different AI models were each asked and all five gave it. |
| `dep` | The same five-chip agreement display, plus a neutral **mechanism** disclosure: all five received the **same prompt**, which did not specify one needed detail, and each model filled that gap on its own. |

The dependence disclosure is not a verdict and does not reveal the correct convention or answer. It
explains the shared-input mechanism; styling remains neutral. The apparently unanimous displays are
curated illustrations and are disclosed in the debrief.

## 6. Export schema

`custom_export` produces one row per trial:

```text
participant_id, label, item_id, condition, complete, accept, confidence, gap_correct,
rt_sec, order_index, group_g, lang, passed_comprehension, passed_attention,
total_time_sec, straightline_confidence, duplicate_id, age_group, ai_use
```

`complete` is 0 for U1–U9 and 1 for C1–C5. `gap_correct` is blank when the participant accepts or
when the item is complete. The exported CSV feeds directly into the frozen analysis script.
