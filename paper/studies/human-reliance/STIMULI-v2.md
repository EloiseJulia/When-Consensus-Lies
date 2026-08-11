# Stimulus set v2 (current implementation) — 14 workplace items

**Study:** human-reliance (Phase 8). **Population:** team-recruited participants of all ages
(with guardian consent for minors where required by the approved protocol).

This document describes the implemented set in `otree/reliance/stimuli.py`. It replaces prior
12-item descriptions. Each item is bilingual (English / 简体中文), lay-readable, and shown with the
same scenario, task, and answer text in every display condition.

## Design and provenance

The set has **14 items**:

| Item class | IDs | Design | Appropriate response |
|---|---|---|---|
| **Underspecified** | U1–U9 (9) | The answer silently adopts an **unstated** convention. | **Flag** important missing information and identify the decisive gap. |
| **Complete** | C1–C5 (5) | The corresponding convention is explicitly stated and the answer is correct. | **Accept** the answer as ready to use. |

The complete controls prevent an “always flag” strategy (and therefore an accept baseline at floor)
and enable the pre-registered discrimination check. For underspecified items, the answer text has
been stripped of wording that would itself disclose the missing convention. The accept/flag decision
and confidence are committed **before** clarification choices appear. If a participant flags an
underspecified item, the second page contains four randomized substantive options—one decisive
**GOLD** option and three non-decisive distractors—plus a fixed **Other** option. Complete items use
four generic options plus Other and have no scored GOLD question.

**C5 is intentionally a complete control, not an ambiguity item:** it explicitly asks for the median
and supplies the middle value. Its correct behavior is therefore direct acceptance; the ambiguity
contrast is tested by U7.

**Provenance (Law 6).** The predecessor set was drafted by an Anthropic-family model and independently
reviewed by a GPT-family model. The review-driven redesign removed defective/mathematical-trap
materials, tightened distractors, then added the five fully specified controls after review identified
the risk of an all-flagging design. The current code, not the predecessor draft, is authoritative.

## Underspecified items (U1–U9)

| ID | Workplace request | Unstated convention / decisive clarification | Answer silently assumes |
|---|---|---|
| U1 | Report Q1 (**the company’s first fiscal quarter**) revenue for a board deck. | Fiscal-year start: which months count as Q1? | Q1 revenue was $2.4M. |
| U2 | Split a $100.00 bonus equally among three people. | Rounding/remainder: how should the leftover cent be assigned? | Each person gets $33.33. |
| U3 | Use an attached daily-sales table to total March 1 to March 7. | Inclusive/exclusive range: is March 7 included? | Total sales were $18,200. |
| U4 | Count unique customers from an order log. | Deduplication: what identifies a unique customer? | 1,240 unique customers. |
| U5 | Use timestamped order-system records to count orders before Friday midnight. | Timezone: which clock defines Friday midnight? | 312 orders. |
| U6 | Calculate a satisfaction score after it “increased 20%.” | Percentage base: percentage points or relative percent? | 80%. |
| U7 | Use a table of ticket response times to report one number representing the **typical** response time. | “Typical” as arithmetic mean versus median. | 47 minutes. |
| U8 | Set the due time under a service-level agreement (**SLA**) requiring a reply “within 2 days.” | Business versus calendar days: does the weekend count? | Sunday 4pm. |
| U9 | Average survey satisfaction with blank responses. | Null/blank handling: exclude blanks or treat them as zero? | 4.1 out of 5. |

All nine require **FLAG**, not because the displayed number is necessarily false, but because the
request does not establish the convention needed to determine whether it is safe to use.

## Complete items (C1–C5)

| ID | Workplace request | Stated convention / information | Correct answer |
|---|---|---|
| C1 | Name the Q1 (first fiscal quarter) months. | Fiscal year starts in January. | Q1 is January–March. |
| C2 | Count days from March 1 to March 5. | Both March 1 and March 5 are included. | 5 days. |
| C3 | Split a $60 gift card among four people. | It divides evenly. | $15 each. |
| C4 | State the delivery day after Monday shipment. | Delivery is within two **calendar** days. | Wednesday. |
| C5 | Use the **median** to represent the typical response time from a supplied table. | The requested statistic is explicitly the median; its middle value is supplied. | 9 minutes. |

All five require **ACCEPT**. A participant may still flag and select a generic clarification option,
but `gap_correct` is intentionally blank for complete items.

## Runtime presentation

- Each participant receives all 14 items once.
- The three display conditions are assigned by balanced Latin square; item and clarification-option
  order are randomized at runtime.
- The visible answer is unchanged across conditions. Only the source framing changes: one model
  (`single`), five apparently agreeing models (`fake`), or the same five-model display plus a neutral
  explanation that the common prompt omitted a needed detail (`dep`).
- The five-model displays use the real-name chips **ChatGPT, Gemini, Claude, Copilot, DeepSeek**.

See `SURVEY-implementation.md` for the interface and `otree/reliance/stimuli.py` for the exact
bilingual wording and scoring keys.
