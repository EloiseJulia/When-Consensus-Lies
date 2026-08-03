# Stimulus set v2 (audited) — 12 lay-readable underspecified items

**Study:** human-reliance (Phase 8). **Population:** general Prolific.
**Provenance (Law 6):** authored by an Anthropic-family model (Opus), independently audited by a
GPT-family model (gpt-5.6-terra) for construct validity, fixes applied here. **Still requires final
owner sign-off before the pre-registration is frozen.**

**What changed from v1 (all 12 audited REVISE):**
- **Item 07 replaced** — v1 had no divergent answer ($4,200 was below both $5,000 and $5,000,000). New
  version diverges. *(Residual note: the "$5 literal" pole is the less plausible one; owner may swap to a
  hundreds-vs-thousands straddle if preferred.)*
- **Item 08 replaced** — v1 was an objectively-wrong arithmetic trap (compounding), not a missing-convention
  item. New version is a genuine "percentage-points vs relative-%" convention ambiguity.
- **All items:** the three non-GOLD clarifying options are now **cosmetic / non-decisive** (formatting,
  wording, rounding-of-display) so **exactly one** option names the decisive gap (clean objective scoring).

**Runtime note:** the 4 options are listed here with the GOLD as (a) for readability, but option **order
must be randomized per trial** in the survey so the correct option's position varies.

## Shared trial structure
Handoff scenario + task + AI answer (identical text across single / fake / dep display conditions).
Per trial: **Accept-as-is vs Flag-missing-info** (primary); if Flag → pick most important clarifying
question (4 options, one GOLD = objective gap-ID); **Confidence** 0–100. Appropriate response = **Flag**.

---

### Item 01 — fiscal-year start
- **Scenario:** A colleague messages before leave: "Pull our **Q1 revenue** for the board deck."
- **AI answer:** "Q1 revenue (January–March) was **$2.4M**."
- **Divergent values:** fiscal year starts Jan → Q1 = Jan–Mar = $2.4M; starts Apr → Q1 = Apr–Jun = a different figure.
- **Options:** a. *Which months count as Q1 — does the fiscal year start in January or another month?* **[GOLD]**  ·  b. Should the number be rounded to the nearest $10,000?  ·  c. Should the answer use a dollar sign?  ·  d. Should the deck use a chart or a table?

### Item 02 — rounding / remainder
- **Scenario:** Handoff note: "Split the **$100.00** bonus pool **equally among the 3** and tell me each amount."
- **AI answer:** "Each person gets **$33.33**."
- **Divergent values:** leave the leftover cent unallocated → $33.33 each; assign it to one person → one gets $33.34.
- **Options:** a. *How should the leftover cent be handled — round each share, or give the remainder to one person?* **[GOLD]**  ·  b. Should the amounts be listed or written in a sentence?  ·  c. Should each amount include a dollar sign?  ·  d. Should the names be listed alphabetically?

### Item 03 — inclusive / exclusive date range
- **Scenario:** "Give me total sales for **the first week of March** (March 1 to March 7)."
- **AI answer:** "Total sales March 1–7 were **$18,200**."
- **Divergent values:** March 7 included → $18,200; range stops at end of March 6 → a lower total.
- **Options:** a. *Is March 7 itself included, or does the range stop at the end of March 6?* **[GOLD]**  ·  b. Should the total be rounded to the nearest $100?  ·  c. Should the answer include a dollar sign?  ·  d. Should the answer be a sentence or a table?

### Item 04 — deduplication rule
- **Scenario:** "How many **unique customers** did we serve last month? Here's the order log."
- **AI answer:** "You served **1,240 unique customers** last month."
- **Divergent values:** dedup by email → 1,240; dedup by name+phone → a different count.
- **Options:** a. *What identifies a unique customer — email, name, or name+phone?* **[GOLD]**  ·  b. Should the count be rounded to a whole number?  ·  c. Should the answer say "customers" or "people"?  ·  d. Should the answer be a sentence or a table?

### Item 05 — off-by-one / "top N" tie
- **Scenario:** "Send me the **top 10** sales reps by revenue this quarter."
- **AI answer:** "Here are the **top 10 reps** [list]." *(the reps ranked 10 and 11 are tied on revenue)*
- **Divergent values:** include both tied reps → 11 names; require exactly ten → 10 names.
- **Options:** a. *Two reps are tied at #10 — include both, or exactly ten names?* **[GOLD]**  ·  b. Should the names be numbered?  ·  c. Should the list be alphabetical or by rank?  ·  d. Should the list be sent by email or chat?

### Item 06 — timezone
- **Scenario:** "How many orders came in **before midnight on Friday**?"
- **AI answer:** "**312 orders** came in before midnight Friday."
- **Divergent values:** midnight in UTC/server time → 312; midnight in company/local time → a different count.
- **Options:** a. *"Before midnight Friday" in which timezone — UTC/server time or local time?* **[GOLD]**  ·  b. Should the count be rounded to a whole number?  ·  c. Should the answer say "orders" or "purchases"?  ·  d. Should the answer be a full sentence?

### Item 07 — unit / scale  *(replaced)*
- **Scenario:** A budget tracker shows this team's budget as "**5**"; the column's unit label (dollars, or thousands of dollars) is missing. "Is our **$4,200** spend within budget?"
- **AI answer:** "Yes — **$4,200 is within the $5,000 budget**."
- **Divergent values:** "5" means $5 → **not** within budget; "5" means 5 thousand = $5,000 → within budget.
- **Options:** a. *Is the budget "5" in dollars, or in thousands of dollars?* **[GOLD]**  ·  b. Should the answer include a dollar sign?  ·  c. Should the answer be a full sentence?  ·  d. Should the result be bolded?

### Item 08 — percentage base  *(replaced)*
- **Scenario:** "Customer satisfaction was **60%** last month. A report says it **'increased 20%'** this month. What's this month's score?"
- **AI answer:** "Satisfaction is now **80%**."
- **Divergent values:** "increased 20%" = +20 percentage points → 80%; = a 20% relative rise from 60% → 72%.
- **Options:** a. *Does "increased 20%" mean 20 percentage points, or a 20% rise from 60%?* **[GOLD]**  ·  b. Should the answer include the word "satisfaction"?  ·  c. Should the answer be rounded to a whole percent?  ·  d. Should the result be shown in bold?

### Item 09 — mean vs median
- **Scenario:** "What's the **average response time** for support tickets this week?" *(a few tickets took hours; most took minutes)*
- **AI answer:** "The **average response time was 47 minutes**."
- **Divergent values:** mean → 47 minutes (pulled up by outliers); median → ~9 minutes.
- **Options:** a. *By "average" do you want the mean or the median — a few long tickets skew the mean?* **[GOLD]**  ·  b. Should the answer be rounded to whole minutes?  ·  c. Should the answer include the word "minutes"?  ·  d. Should the answer be a sentence or a table?

### Item 10 — business vs calendar days
- **Scenario:** "The SLA says reply **within 2 days**. A ticket arrived **Friday 4pm**. When is it due?"
- **AI answer:** "It's due by **Sunday 4pm**."
- **Divergent values:** calendar days → Sunday 4pm; business days (skip weekend) → Tuesday 4pm.
- **Options:** a. *Does "2 days" mean calendar days or business days (excluding the weekend)?* **[GOLD]**  ·  b. Should the due time be written with "am" or "pm"?  ·  c. Should the answer include the weekday name?  ·  d. Should the answer be a full sentence?

### Item 11 — sort tie-break
- **Scenario:** "Rank these regions by growth and tell me **who's #1**." *(two regions are tied on growth)*
- **AI answer:** "**North** is #1 by growth." *(North and West are tied)*
- **Divergent values:** shared first place → North and West both #1; tie broken by revenue → North alone.
- **Options:** a. *North and West are tied on growth — how should the tie be broken (e.g., by revenue)?* **[GOLD]**  ·  b. Should the answer include both region names?  ·  c. Should we show percentages or ranks?  ·  d. Should the answer be presented in bold?

### Item 12 — null / blank handling
- **Scenario:** "What's the **average satisfaction score** from this survey?" *(several respondents left the score blank)*
- **AI answer:** "The **average satisfaction score was 4.1** out of 5."
- **Divergent values:** exclude blanks → 4.1/5; count blanks as 0 → a lower average.
- **Options:** a. *Should blank scores be left out of the average, or counted as zero?* **[GOLD]**  ·  b. Should the answer be rounded to one decimal place?  ·  c. Should the answer include "out of 5"?  ·  d. Should the answer be a sentence or a table?

---

## Convention-type coverage (12 distinct, maintained)
01 fiscal-year start · 02 rounding/remainder · 03 inclusive/exclusive range · 04 dedup · 05 top-N tie ·
06 timezone · 07 unit/scale · 08 percentage base · 09 mean vs median · 10 business vs calendar days ·
11 sort tie-break · 12 null/blank handling.

## Remaining checks before freeze
- Owner sign-off on the two replaced items (07 scale, 08 percentage base) and on Item 07's plausibility.
- Set the exact numeric "other-value" answers per item (only the committed answer is shown to participants;
  the divergent alternative is documented for scoring/debrief, not displayed).
- Randomize option order per trial; embed 1 instructed-response attention check among the option lists.
- Confirm reading level ≤ ~45 words/item; localize currency/date formats to the sample.
