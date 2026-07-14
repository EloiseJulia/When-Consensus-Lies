"""Label assignment via executable signals — NOT LLM judge.

Phase 2: EXECUTABLE-SIGNAL labeling via domain gold checkers.
Each domain uses deterministic gold checkers (NO LLM) to assign labels.
"""

import hashlib
import json
import math
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Dict, List, Optional
from common.schema import AgentRun, Task


def _stable_index(text: str, modulo: int) -> int:
    """Deterministic, cross-process-stable index from a string.

    Uses hashlib (NOT Python's builtin hash(), which is per-process salted and
    would make labeling non-reproducible across interpreter restarts).
    
    Used ONLY by _mock_label_fallback for unknown domains.
    """
    if modulo <= 0:
        raise ValueError("modulo must be positive")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest, 16) % modulo


def _mock_label_fallback(run: AgentRun, task: Task) -> str:
    """MOCK labeling for unknown domains only (NOT used for real domains).
    
    This is the Phase 0 deterministic hash mock, preserved for unknown domains.
    The three real domains (code_spec, data_analysis, policy_qa) use executable
    gold checkers instead.
    """
    label_idx = _stable_index(run.output, len(task.interpretations))
    return task.interpretations[label_idx].id


def _extract_code_from_output(output: str) -> Optional[str]:
    """Extract Python code from agent output (code fence or raw code).
    
    Strategy:
    1. Look for ```python ... ``` or ``` ... ``` code fences
    2. If no fence, treat entire output as code (agent may output raw code)
    3. Return the extracted code, or None if output is clearly not code
    """
    # Try to find code fence (```python or just ```)
    # Pattern: ```python? ... ``` (non-greedy, multiline, case-insensitive)
    # Need to handle both ``` and ```python
    fence_pattern = r'```(?:python)?\s*\n(.*?)\n```'
    match = re.search(fence_pattern, output, re.DOTALL | re.IGNORECASE)
    
    if match:
        return match.group(1).strip()
    
    # Try simpler fence without language specifier
    fence_pattern2 = r'```\s*\n?(.*?)\n?```'
    match2 = re.search(fence_pattern2, output, re.DOTALL | re.IGNORECASE)
    
    if match2:
        return match2.group(1).strip()
    
    # No fence found. Check if output looks like code (has 'def ' or common Python keywords)
    # If it's clearly prose (long sentences, no code structure), return None
    if 'def ' in output or 'return ' in output or 'import ' in output:
        # Looks like raw code
        return output.strip()
    
    # Check if it's very short and might be code
    if len(output.strip()) < 500 and ('=' in output or '(' in output):
        return output.strip()
    
    # Likely prose or explanation, not code
    return None


# ── Sentinel ──────────────────────────────────────────────────────────────────
# Distinguishes "found but invalid" from "not found" (None).
_INVALID_STRUCTURED = object()


# ── JSON helpers ───────────────────────────────────────────────────────────────

def _validate_decimal(d: Decimal):
    """
    Return *d* if it can be safely cent-quantized, else _INVALID_STRUCTURED.

    Guards against huge values (e.g. 1e308) whose Decimal representation is
    valid but too large for Decimal.quantize at default precision.
    """
    try:
        d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return d
    except (InvalidOperation, OverflowError):
        return _INVALID_STRUCTURED

def _collect_json_amounts(output: str) -> list:
    """
    Collect parse results for EVERY JSON object with an 'amount' key in *output*.

    Uses json.JSONDecoder.raw_decode to scan forward through the text.  This is
    natively string/escape-aware: braces inside JSON string values are handled
    correctly (e.g. {"amount":950,"note":"}"} is parsed as a single object).

    Exception safety guarantee — this function NEVER raises:
      - json.JSONDecodeError / ValueError  → skip that candidate, advance 1 char
      - RecursionError (deeply nested JSON) → append _INVALID_STRUCTURED, stop scan
      - Any other exception                → skip that candidate, advance 1 char

    Returns a list where each element is either:
      Decimal              – a valid, range-safe finite amount
      _INVALID_STRUCTURED  – an 'amount' value that is non-finite, non-numeric,
                             out-of-range, deeply nested, or otherwise malformed

    JSON objects that lack an 'amount' key are silently skipped.
    Extra keys alongside a valid 'amount' are accepted (manager ruling).
    An empty list means no JSON structured-answer was present.
    """
    decoder = json.JSONDecoder()
    results: list = []
    idx = 0
    length = len(output)
    while idx < length:
        brace_pos = output.find('{', idx)
        if brace_pos == -1:
            break
        try:
            data, end_pos = decoder.raw_decode(output, brace_pos)
        except (json.JSONDecodeError, ValueError):
            idx = brace_pos + 1
            continue
        except RecursionError:
            # Deeply nested JSON hit Python's recursion limit → malformed
            results.append(_INVALID_STRUCTURED)
            break   # Don't re-scan deeper levels; one error is enough
        except Exception:
            idx = brace_pos + 1
            continue
        if not isinstance(data, dict) or 'amount' not in data:
            idx = end_pos
            continue
        # Found a JSON object with 'amount' key — validate its value
        val = data['amount']
        if not isinstance(val, (int, float)):
            results.append(_INVALID_STRUCTURED)
        else:
            try:
                fval = float(val)
            except (ValueError, OverflowError):
                results.append(_INVALID_STRUCTURED)
            else:
                if not math.isfinite(fval):
                    results.append(_INVALID_STRUCTURED)
                else:
                    try:
                        d = Decimal(str(fval))
                    except InvalidOperation:
                        results.append(_INVALID_STRUCTURED)
                    else:
                        results.append(_validate_decimal(d))
        idx = end_pos
    return results


# ── FINAL ANSWER helpers ───────────────────────────────────────────────────────

# Header: "FINAL ANSWER:" or "FINAL ANSWER =" (case-insensitive, flexible spacing).
# Tail uses a negative lookahead to stop at the NEXT "FINAL ANSWER" occurrence
# within the same line, so two adjacent markers on one line are each captured
# independently (the greedy [^\n]* approach swallowed the second marker).
_FA_HEADER_RE = re.compile(
    r'FINAL\s+ANSWER\s*[:=]\s*(?P<tail>(?:(?!FINAL\s+ANSWER)[^\n])*)',
    re.IGNORECASE,
)

# Anchored signed-money grammar — the ENTIRE tail (stripped) must match.
# Compiled with re.ASCII so \d matches only 0-9 (rejects Unicode digits).
# Thousands grouping is validated: either well-formed \d{1,3}(,\d{3})+ or
# plain \d+ (no commas at all).  Bad grouping like $,1000 or $10,00 is rejected.
_MONEY_FULL_RE = re.compile(
    r'^(?P<s1>-?)\s*\$?\s*(?P<s2>-?)\s*'
    r'(?P<digits>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?)'
    r'\s*(?:dollars?|USD)?\s*$',
    re.IGNORECASE | re.ASCII,
)


def _parse_money_tail(tail: str):
    """
    Parse the text following 'FINAL ANSWER:' as a signed money amount.

    Returns:
      Decimal              – parsed successfully and within safe range
      _INVALID_STRUCTURED  – non-empty tail that is NOT a valid/safe money token
      None                 – empty tail (no token; marker effectively absent)
    """
    tail = tail.strip()
    if not tail:
        # A bare "FINAL ANSWER:" with nothing after it is a malformed structured
        # answer (the agent signalled a final answer but provided no value).
        return _INVALID_STRUCTURED
    m = _MONEY_FULL_RE.match(tail)
    if not m:
        return _INVALID_STRUCTURED
    # XOR the two optional sign captures to determine net sign
    negative = (m.group('s1') == '-') != (m.group('s2') == '-')
    digits_str = m.group('digits').replace(',', '')
    try:
        value = Decimal(('-' if negative else '') + digits_str)
    except InvalidOperation:
        return _INVALID_STRUCTURED
    return _validate_decimal(value)


def _find_final_answer_amounts(output: str) -> list:
    """
    Return a parse result for every FINAL ANSWER marker found in *output*.

    Each element is either a Decimal (valid signed amount) or
    _INVALID_STRUCTURED (marker present but amount token is invalid/out-of-range,
    OR the marker is bare with no token — e.g. bare 'FINAL ANSWER:').
    """
    results: list = []
    for m in _FA_HEADER_RE.finditer(output):
        result = _parse_money_tail(m.group('tail'))
        if result is not None:
            results.append(result)
    return results


# ── Cent comparison helper ─────────────────────────────────────────────────────

def _amount_cents(d: Decimal) -> int:
    """Return a cent-exact integer for conflict comparison.

    All Decimals reaching this function have already passed _validate_decimal,
    so quantize should not raise; the try/except is a last-resort safety net.
    """
    return int(d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) * 100)


def _extract_numeric_from_output(output: str) -> Optional[float]:
    """Extract a numeric answer from agent output (policy_qa domain).

    STRUCTURED FINAL-ANSWER CONTRACT (owner-approved, pre-registered):
    Accepts ONLY:
      (a) A genuine JSON object (whole output, code-fenced, or standalone
          JSON block embedded in the output) with key exactly 'amount' and a
          FINITE, range-safe numeric value.  Extra keys in the JSON object are
          accepted (a single unambiguous amount is not ambiguous).
      (b) A FINAL ANSWER line with an anchored signed-money grammar immediately
          following the header marker; no trailing prose allowed.

    Returns None (→ I_perp) when:
      - No structured answer is present.
      - Any structured answer is recognised but invalid (non-finite/out-of-range
        value, non-money token after FINAL ANSWER:, wrong type, malformed JSON).
      - Multiple structured answers (JSON + markers) have DIFFERENT cent values.

    There is NO fallback heuristic: no first-number / last-number / prose
    scraping, no regex-scraped "amount": N without surrounding {}.
    """
    results: List[Decimal] = []

    # ── (a) JSON path — collect ALL JSON objects with 'amount' ────────────────
    for json_result in _collect_json_amounts(output):
        if json_result is _INVALID_STRUCTURED:
            return None      # Recognised but invalid JSON amount → I_perp
        results.append(json_result)  # type: ignore[arg-type]

    # ── (b) FINAL ANSWER path ─────────────────────────────────────────────────
    for fa_result in _find_final_answer_amounts(output):
        if fa_result is _INVALID_STRUCTURED:
            return None      # Recognised marker but invalid token → I_perp
        results.append(fa_result)   # type: ignore[arg-type]

    if not results:
        return None          # No structured answer found → I_perp

    # Conflict check: all valid amounts must agree to the cent
    try:
        unique_cents = {_amount_cents(r) for r in results}
    except (InvalidOperation, OverflowError, ValueError):
        return None          # Defensive: unexpected out-of-range → I_perp
    if len(unique_cents) > 1:
        return None          # Conflicting structured answers → I_perp

    return float(results[0])


def label_code_domain(run: AgentRun, task: Task) -> str:
    """Extract label from code execution signals via CodeChecker.
    
    Strategy:
        1. Extract Python code from run.output (code fence or raw)
        2. Run extracted code through EACH interpretation's gold checker
        3. Return the interpretation ID whose checker UNIQUELY passes
        4. Return I_perp if none pass or multiple pass
    
    Uses the hardened CodeChecker runner (no sandbox added, per owner-approved
    threat model: candidates are cooperative LLM outputs).
    """
    from bench.code_spec import get_checkers_and_candidates
    
    # Extract code from output
    candidate_code = _extract_code_from_output(run.output)
    if candidate_code is None:
        # No code found, label as I_perp
        return "I_perp"
    
    # Get checkers for this task's interpretations
    # For real domains, checker-loading failure is FATAL (fail loud, not silent mock)
    try:
        checkers, _, _ = get_checkers_and_candidates(task.domain, task)
    except (ValueError, KeyError) as e:
        # Real domain with unavailable checkers → FATAL ERROR (do not silently mock-label)
        raise RuntimeError(
            f"label: gold checkers unavailable for code_spec task {task.id}: {e}"
        ) from e
    
    # Run candidate through each checker
    passed_interps = []
    for interp in task.interpretations:
        if interp.id == "I_perp":
            continue  # Skip I_perp (it's the default)
        
        checker = checkers.get(interp.id)
        if checker is None:
            continue
        
        result = checker.check(candidate_code)
        if result.passed:
            passed_interps.append(interp.id)
    
    # Unique match?
    if len(passed_interps) == 1:
        return passed_interps[0]
    elif len(passed_interps) == 0:
        return "I_perp"
    else:
        # Multiple matches (should not happen with 100% distinguishability)
        # Return I_perp to be conservative
        return "I_perp"


def label_data_domain(run: AgentRun, task: Task) -> str:
    """Extract label from data analysis code via DataChecker.
    
    Strategy:
        1. Extract Python code from run.output (code fence or raw)
        2. Run extracted code through EACH interpretation's gold checker
        3. Return the interpretation ID whose checker UNIQUELY passes
        4. Return I_perp if none pass or multiple pass
    
    Uses the hardened DataChecker runner (same isolation as CodeChecker).
    """
    from bench.data_analysis import get_checkers_and_candidates
    
    # Extract code from output
    candidate_code = _extract_code_from_output(run.output)
    if candidate_code is None:
        # No code found, label as I_perp
        return "I_perp"
    
    # Get checkers for this task's interpretations
    # For real domains, checker-loading failure is FATAL (fail loud, not silent mock)
    try:
        checkers, _, _ = get_checkers_and_candidates(task.domain, task)
    except (ValueError, KeyError) as e:
        # Real domain with unavailable checkers → FATAL ERROR (do not silently mock-label)
        raise RuntimeError(
            f"label: gold checkers unavailable for data_analysis task {task.id}: {e}"
        ) from e
    
    # Run candidate through each checker
    passed_interps = []
    for interp in task.interpretations:
        if interp.id == "I_perp":
            continue  # Skip I_perp (it's the default)
        
        checker = checkers.get(interp.id)
        if checker is None:
            continue
        
        result = checker.check(candidate_code)
        if result.passed:
            passed_interps.append(interp.id)
    
    # Unique match?
    if len(passed_interps) == 1:
        return passed_interps[0]
    elif len(passed_interps) == 0:
        return "I_perp"
    else:
        # Multiple matches (should not happen with 100% distinguishability)
        # Return I_perp to be conservative
        return "I_perp"


def label_policy_domain(run: AgentRun, task: Task) -> str:
    """Extract label from policy numeric answer via StructuredAnswerChecker.
    
    Strategy:
        1. Extract numeric answer from run.output (JSON or dollar amount)
        2. Convert to {"amount": <float>} format
        3. Check against EACH interpretation's gold checker (cent-precision)
        4. Return the interpretation ID whose checker UNIQUELY passes
        5. Return I_perp if none pass or multiple pass
    
    Uses the deterministic StructuredAnswerChecker (NO LLM).
    """
    from bench.policy_qa import get_checkers_and_candidates
    
    # Extract numeric answer from output
    amount = _extract_numeric_from_output(run.output)
    if amount is None:
        # No clear numeric answer found
        return "I_perp"
    
    # Format as structured answer
    candidate_answer = {"amount": amount}
    
    # Get checkers for this task's interpretations
    # For real domains, checker-loading failure is FATAL (fail loud, not silent mock)
    try:
        checkers, _, _ = get_checkers_and_candidates(task.domain, task)
    except (ValueError, KeyError) as e:
        # Real domain with unavailable checkers → FATAL ERROR (do not silently mock-label)
        raise RuntimeError(
            f"label: gold checkers unavailable for policy_qa task {task.id}: {e}"
        ) from e
    
    # Run candidate through each checker
    passed_interps = []
    for interp in task.interpretations:
        if interp.id == "I_perp":
            continue  # Skip I_perp (it's the default)
        
        checker = checkers.get(interp.id)
        if checker is None:
            continue
        
        result = checker.check(candidate_answer)
        if result.passed:
            passed_interps.append(interp.id)
    
    # Unique match?
    if len(passed_interps) == 1:
        return passed_interps[0]
    elif len(passed_interps) == 0:
        return "I_perp"
    else:
        # Multiple matches (should not happen with 100% distinguishability)
        # Return I_perp to be conservative
        return "I_perp"


def label_run(run: AgentRun, task: Task) -> str:
    """Assign interpretation label to an agent run via executable signal.
    
    Phase 2 IMPLEMENTATION: Dispatches by task.domain to domain-specific
    labelers that use EXECUTABLE gold checkers (NEVER an LLM judge).
    
    Each domain labeler:
    1. Extracts the candidate answer from run.output robustly
    2. Runs it through EACH interpretation's gold checker
    3. Returns the interpretation ID that UNIQUELY passes
    4. Returns "I_perp" if none pass or multiple pass (ambiguous)
    
    For unknown domains, falls back to the Phase 0 deterministic mock.
    
    Args:
        run: AgentRun with output field
        task: Task with interpretations and domain
    
    Returns:
        Label string (one of task.interpretation.id values or "I_perp")
    """
    # Dispatch by domain to the appropriate labeler
    if task.domain == "code_spec":
        return label_code_domain(run, task)
    elif task.domain == "data_analysis":
        return label_data_domain(run, task)
    elif task.domain == "policy_qa":
        return label_policy_domain(run, task)
    else:
        # Unknown domain: fall back to deterministic mock
        return _mock_label_fallback(run, task)
