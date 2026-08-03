# Stimulus set (DRAFT) — 12 lay-readable underspecified items

**Study:** human-reliance (Phase 8). **Population:** general Prolific (option b).
**Status:** AI-authored FIRST DRAFT. Needs (1) owner scientific review and (2) a **cross-family
construct-validity audit** before freeze — auditor (different model family than the author) checks,
per item: (i) the task genuinely hinges on **exactly one** decision-relevant *unstated* convention;
(ii) the displayed answer silently commits to one value of it; (iii) **exactly one** clarifying option
names that decisive gap (the GOLD), and the other three are plausible-but-non-decisive (do not change
the given answer); (iv) at least two plausible values of the convention yield **different** answers.

## Shared trial structure
- Each item shows: a one-line **handoff scenario**, a **task**, and an **AI answer** (identical text
  across the three display conditions — only the source framing single/fake/dep differs).
- DVs per trial: **Accept-as-is vs Flag-missing-info** (primary behavioral); if Flag → pick the most
  important clarifying question from the 4 options (**objective gap-ID**, GOLD marked); **Confidence**
  0–100.
- Appropriate behavior = **Flag** (information is genuinely missing); Accept = over-reliance.

## Convention-type coverage (1 per item)
1 fiscal-year start · 2 rounding/remainder · 3 inclusive/exclusive date range · 4 dedup rule ·
5 off-by-one / "top N" tie · 6 timezone · 7 unit/currency scale · 8 percentage base ·
9 mean vs median · 10 business vs calendar days · 11 sort tie-break · 12 null/blank handling.

---

### Item 01 — fiscal-year start
- **Scenario:** A colleague messages before going on leave: "Pull our **Q1 revenue** for the board deck."
- **Task:** Report Q1 revenue.
- **AI answer:** "Q1 revenue (January–March) was **$2.4M**."
- **Hidden convention:** whether the company's fiscal year starts in January (then Q1 = Jan–Mar) or
  another month (e.g., fiscal Q1 = Apr–Jun) → different figure.
- **Clarifying options:**
  - a. *Which months count as Q1 — does the fiscal year start in January or another month?* **[GOLD]**
  - b. Should revenue be gross or net of refunds?
  - c. Should the figure be in USD or another currency?
  - d. Should the deck use a chart or a table?

### Item 02 — rounding / remainder
- **Scenario:** Handoff note: "Split the **$100.00** bonus pool **equally among the 3** of them and tell
  me each amount."
- **Task:** Give each person's amount.
- **AI answer:** "Each person gets **$33.33**."
- **Hidden convention:** how to handle the leftover cent ($100 ≠ 3 × $33.33); options change a share.
- **Clarifying options:**
  - a. *How should the leftover cent be handled — round each share, or give the remainder to one person?* **[GOLD]**
  - b. Are all three people eligible for an equal share?
  - c. Should the amounts be shown before or after tax?
  - d. Should I pay it this month or next?

### Item 03 — inclusive/exclusive date range
- **Scenario:** "Give me total sales for **the first week of March** (March 1 to March 7)."
- **Task:** Total sales for that range.
- **AI answer:** "Total sales March 1–7 were **$18,200**."
- **Hidden convention:** is **March 7 included** (inclusive) or is the range up-to-but-not-including
  March 7? → different total.
- **Clarifying options:**
  - a. *Is March 7 itself included in the range, or does it stop at the end of March 6?* **[GOLD]**
  - b. Should returns be subtracted from sales?
  - c. Should this be in units or dollars?
  - d. Which product categories should be included?  *(only if they meant "all"; keep as distractor)*

### Item 04 — deduplication rule
- **Scenario:** "How many **unique customers** did we serve last month? Here's the order log."
- **Task:** Count unique customers.
- **AI answer:** "You served **1,240 unique customers** last month."
- **Hidden convention:** what defines "unique" — dedup by email, by name, or by name+phone? → different count.
- **Clarifying options:**
  - a. *What identifies a unique customer — email, name, or name+phone (in case of duplicates)?* **[GOLD]**
  - b. Should we count only completed (not cancelled) orders?
  - c. Does "last month" mean the calendar month or the last 30 days?  *(decisive too — see note)*
  - d. Should business and individual customers be reported separately?

> ⚠ Item 04 distractor (c) is itself a second unstated convention; audit should replace it so the item
> hinges on a single decisive gap.

### Item 05 — off-by-one / "top N" tie
- **Scenario:** "Send me the **top 10** sales reps by revenue this quarter."
- **Task:** List the top 10.
- **AI answer:** "Here are the **top 10 reps** [list]."  *(reps ranked 10 and 11 are tied on revenue)*
- **Hidden convention:** with a tie at rank 10, does "top 10" include both tied reps (→ 11 names) or
  cut arbitrarily at 10?
- **Clarifying options:**
  - a. *Two reps are tied at #10 — should the list include both, or exactly ten names?* **[GOLD]**
  - b. Should revenue be booked or collected revenue?
  - c. Should the list be alphabetical or by rank?
  - d. Should it cover this quarter only or year-to-date?  *(decisive-ish; audit)*

### Item 06 — timezone
- **Scenario:** "How many orders came in **before midnight on Friday**?"
- **Task:** Count Friday's pre-midnight orders.
- **AI answer:** "**312 orders** came in before midnight Friday."
- **Hidden convention:** midnight in **which timezone** — server/UTC vs the customer's or company's
  local time? → boundary orders shift.
- **Clarifying options:**
  - a. *"Before midnight Friday" in which timezone — UTC/server time or local time?* **[GOLD]**
  - b. Should cancelled orders be excluded?
  - c. Should this include only paid orders?
  - d. Do you want the count or the revenue?

### Item 07 — unit / currency scale
- **Scenario:** A shared sheet cell is labeled "**Budget: 5,000**." "Is our **$4,200** spend within budget?"
- **Task:** Say whether spend is within budget.
- **AI answer:** "Yes — **$4,200 is within the $5,000 budget**."
- **Hidden convention:** is the budget figure in **dollars** or in **thousands** (a common sheet
  convention, "5,000" = $5,000 vs the column is in $000s)? → changes the comparison entirely.
- **Clarifying options:**
  - a. *Is the budget "5,000" in dollars, or is the sheet in thousands (so 5,000 = $5,000,000)?* **[GOLD]**
  - b. Does the spend figure include tax?
  - c. Is this month-to-date or full-month budget?  *(decisive-ish; audit)*
  - d. Should committed-but-unpaid spend be counted?

### Item 08 — percentage base
- **Scenario:** "A product went **up 20%** in the morning and **down 20%** in the afternoon. What's the
  **net change** vs the start?"
- **Task:** Net percentage change.
- **AI answer:** "**No net change** — up 20% then down 20% cancels out."
- **Hidden convention:** each % applies to a **different base** (the second 20% is of the higher price),
  so net = −4%. The answer assumes a shared base. *(Here the answer is simply wrong; the "gap" is the
  base each percentage applies to.)*
- **Clarifying options:**
  - a. *Does each 20% apply to the same starting price, or does the afternoon 20% apply to the raised price?* **[GOLD]**
  - b. Should the change be shown in dollars instead of percent?
  - c. Over what time window are we measuring?
  - d. Should we account for currency effects?

### Item 09 — mean vs median
- **Scenario:** "What's the **average response time** for support tickets this week?" (a few tickets took
  many hours; most were minutes.)
- **Task:** Report the average.
- **AI answer:** "The **average response time was 47 minutes**."  *(mean, pulled up by a few outliers)*
- **Hidden convention:** "average" = **mean** (47 min, skewed by outliers) or **median** (e.g., 9 min)?
  → very different headline number.
- **Clarifying options:**
  - a. *By "average" do you want the mean or the median — a few long tickets skew the mean upward?* **[GOLD]**
  - b. Should we include tickets that are still open?
  - c. Should weekends be included in "this week"?  *(decisive-ish; audit)*
  - d. Should this be per-agent or overall?

### Item 10 — business vs calendar days
- **Scenario:** "The SLA says we reply **within 2 days**. A ticket arrived **Friday 4pm**. When is it due?"
- **Task:** Give the due time.
- **AI answer:** "It's due by **Sunday 4pm**."
- **Hidden convention:** "2 days" = **calendar days** (Sunday) or **business days** (Tuesday)? → different due date.
- **Clarifying options:**
  - a. *Does "2 days" mean calendar days or business days (excluding the weekend)?* **[GOLD]**
  - b. Is the SLA clock based on arrival time or first business hour?  *(decisive-ish; audit)*
  - c. Should auto-replies count as a reply?
  - d. Is this SLA for all tickets or only priority ones?

### Item 11 — sort tie-break
- **Scenario:** "Rank these regions by growth and tell me **who's #1**." (Two regions have identical growth.)
- **Task:** Name the #1 region.
- **AI answer:** "**North** is #1 by growth." *(North and West are tied on growth)*
- **Hidden convention:** how to break the tie — by absolute revenue, alphabetical, prior rank? The answer
  picks one silently.
- **Clarifying options:**
  - a. *North and West are tied on growth — how should the tie be broken (e.g., by revenue size)?* **[GOLD]**
  - b. Should growth be year-over-year or quarter-over-quarter?  *(decisive-ish; audit)*
  - c. Should we show percentages or ranks?
  - d. Should inactive regions be excluded?

### Item 12 — null / blank handling
- **Scenario:** "What's the **average satisfaction score** from this survey?" (Several respondents left the
  score **blank**.)
- **Task:** Report the average score.
- **AI answer:** "The **average satisfaction score was 4.1** out of 5."
- **Hidden convention:** are **blank responses excluded** from the average, or **counted as 0**? → very
  different average.
- **Clarifying options:**
  - a. *Should blank scores be left out of the average, or counted as zero?* **[GOLD]**
  - b. Should we weight by respondent type?
  - c. Is the scale 1–5 or 0–5?  *(decisive-ish; audit)*
  - d. Should partial survey completions be included?

---

## Notes for the construct-validity audit
- Several distractor options flagged *(decisive-ish; audit)* are themselves plausible second gaps.
  The audit must ensure **exactly one** GOLD gap per item; either weaken those distractors to clearly
  non-decisive framing, or narrow the scenario so only the intended convention is unresolved.
- Confirm each AI answer is *reasonable on its face* (so accepting is tempting) yet *contingent* on the
  hidden convention (so flagging is the appropriate response).
- Item 08 is the one "objectively wrong" arithmetic item (net = −4%); the rest are "unverifiable
  without the convention." Keep at most 1–2 objectively-wrong items so the task isn't a math test.
- Keep reading level lay; strip jargon; each item ≤ ~45 words including the answer.
