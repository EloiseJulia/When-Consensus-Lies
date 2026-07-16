# Labeler format-fix — plan & diagnosis (Claude/Anthropic implement sub-agent)

Branch: `slice/labeler-format-fix`. Auditor family: GPT (non-Claude). Offline only.

## STEP 1 — Diagnosis (from real cached diagnostic outputs, `.llm_cache_default_check`)

I ran the actual labeler (`label_run`, task `code_invoice_001_k3_all`) over every cached
`format_invoice_line` output and executed each extracted candidate against the two gold
test inputs. Findings PER FAILURE MODE:

### (b) GENUINE off-axis — mistral-small-2503 code_invoice "all-I_perp"
- Extraction SUCCEEDS for **every** mistral invoice output (`extracted=True`).
- The executed candidates produce genuinely off-axis / buggy results, e.g.:
  - `Q2 05/15/2024 0.12` + `Q1 01/10/2024 (0.12)` = half-even rounding **mixed with**
    GAAP paren sign — matches NEITHER `cal_us_halfeven` (wants `-0.12`) NOR
    `cal_us_gaap` (wants `0.13`). A convention **mix** that is not one of the 8 interps.
  - `Decimal.abs` `AttributeError`, `0.15`/`0` wrong values, etc. → buggy code.
- **Verdict: I_perp is CORRECT.** This is NOT a labeler/extraction bug. The weak model
  genuinely fails to converge (real CDenumerated=0). → Task-difficulty finding for the
  Manager, NOT fixable by extraction hardening. **No change made for this mode.**

### (b) TRUNCATION / no-answer — deepseek-r1 code_invoice I_perp
- All deepseek invoice I_perp outputs are `<think>…` reasoning that was **truncated**
  (unclosed `<think>`, ~15k chars, `num ``` == 0`) — the model NEVER emitted a final
  code block. There is **no answer to recover**.
- Cache-wide: 0 outputs have a fence *inside* `<think>`, 0 have >1 python fence; 10/21
  think outputs have NO code fence at all. So the real cache has **no** "wrapped-but-
  present" recoverable answer.
- Current extractor bug exposed: with no fence it returned the **entire reasoning prose**
  as "code" (because it contains the words `def`/`return`) → `SyntaxError` → I_perp by
  accident. Fragile (could false-match) — hardened below, though label stays I_perp.

### (a) FIXABLE extraction — latent, demonstrated on faithful synthetic reproductions
The current `_extract_code_from_output` has real latent (a)-bugs that WILL mislabel a
reasoning model that DOES emit a correct final block:
1. No `<think>…</think>` stripping → reasoning prose leaks into extraction.
2. `re.search` grabs the **FIRST** fence → an illustrative in-reasoning snippet wins over
   the final answer block.
3. Fallback returns whole output as "code" on a naive `'def '`/`'return '` substring
   check → executes prose.

## STEP 2 — Fix scope (pure extraction robustness; gold semantics UNCHANGED)
`harness/label.py`:
- `_strip_reasoning()`: remove closed `<think>/<thinking>` blocks; drop a dangling
  unclosed trailing `<think>` (truncated → correctly empty, not prose-as-code).
- `_extract_code_from_output()`: strip reasoning first; take the **LAST** fenced
  ```python``` block; ast-validated raw-code fallback (parses AND has a code construct).
- Apply `_strip_reasoning` in `label_policy_domain` before numeric extraction (removes
  in-`<think>` illustrative numbers that cause false conflict→I_perp). Contract grammar
  UNCHANGED. **FLAGGED** (touches pre-registered policy path — pre-processing only).
`harness/run.py`:
- `answer_format_instruction`: add a reasoning-model clause ("if you show reasoning, end
  with your final answer"). Reinforces placement only; format unchanged. **FLAGGED.**

Gold checkers, `_extract_numeric_from_output` grammar, and exact-match semantics are
untouched — I only recover answers that were present-but-unparsed and prevent prose→code.

## STEP 3 — Offline tests
`tests/test_label_format_robustness.py`: synthetic deepseek `<think>`-wrapped correct
block (recovered), first-vs-last fence, prose+code_invoice, truncated think (stays
I_perp), and a genuine mixed-convention off-axis output (stays I_perp — no false
recovery). Plus a cache-backed regression assertion that the fix doesn't relabel the real
mistral off-axis outputs.
