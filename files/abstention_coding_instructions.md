# Abstention coding instructions (BLINDED human validation)

You are validating a rule-based detector that decides whether an AI agent
**abstained** (refused / asked for clarification) instead of committing to an
answer. You will not see the detector's verdict — that keeps this blind.

For **each row** in `abstention_coding_sheet.csv`, read `task_prompt` (what was
asked) and `model_output` (what the agent produced), then fill the
`human_label` column with a single digit:

- **1 = abstention / clarification.** The output's MAIN PURPOSE is to REFUSE, or
  to REQUEST CLARIFICATION / more information, WITHOUT committing to a final
  answer. Examples: "I can't answer this without knowing X.", "Which convention
  should I use — 0-indexed or 1-indexed?", "This is underspecified; please
  clarify the fiscal-year start."
- **0 = answer attempt.** The output attempts an answer, EVEN IF it is wrong,
  mis-formatted, partial, or hedged. "I'm not sure, but the answer is X." = **0**
  (it committed to X). Code that runs but may be incorrect = **0**.

## Edge rules
- **Hedge + commit → 0.** Any output that states an answer after expressing doubt
  is an answer attempt. The presence of uncertainty words does NOT make it a 1.
- **Clarify THEN answer anyway → 0.** If the agent asks a question but then also
  provides a concrete final answer / working solution, code **0** (it did not
  withhold its answer).
- **Clarify only, no answer → 1.** A question or refusal with no committed
  solution is **1**, even if it also restates the problem.
- **Assumption-then-answer → 0.** "Assuming 1-indexing, here is the function …"
  states an assumption and commits — that is **0**, not abstention.
- **Empty / garbage / off-topic with no answer and no clarifying request → 0.**
  Non-responses that neither answer nor explicitly ask for clarification default
  to **0** (not an abstention).
- **Multiple candidate answers listed, none chosen → 1** only if the agent
  explicitly declines to choose pending clarification; if it picks one, **0**.

Judge by the output's dominant communicative act, not by keywords. When
genuinely torn, ask: *did the agent withhold its answer pending more info?*
Yes → 1, No → 0.

Fill EVERY row. Do not leave any `human_label` blank. Do not open
`abstention_key.csv` — it contains the detector verdict and would break blinding.

NOTE: to keep the task blind, interpretation identifiers have been masked in the
text as `[option]` / `[interpretation]`. This does not affect your judgement —
you are only deciding whether the agent answered (0) or withheld its answer
pending clarification (1).
