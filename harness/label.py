"""Label assignment via executable signals — NOT LLM judge.

Phase 2: EXECUTABLE-SIGNAL labeling via domain gold checkers.
Each domain uses deterministic gold checkers (NO LLM) to assign labels.
"""

import hashlib
import json
import re
from typing import Dict, Optional
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


def _extract_numeric_from_output(output: str) -> Optional[float]:
    """Extract a numeric answer from agent output (policy_qa domain).
    
    STRUCTURED FINAL-ANSWER CONTRACT (owner-approved, pre-registered):
    Tested agents are instructed to end with a structured final answer:
      - JSON: {"amount": N} or {"answer": N}
      - FINAL ANSWER marker: "FINAL ANSWER: $<amount>" (or variants)
    
    Labeling relies on this contract. Unparseable free-text is conservatively
    I_perp (not guessed) to avoid systematic mislabeling of unstructured outputs.
    
    Priority order:
    1. JSON amount field: Pure, embedded, or fenced JSON with numeric "amount"
       or "answer" field.
    2. FINAL ANSWER marker: A line/segment matching "FINAL ANSWER:" (case-insensitive,
       also accept "Final answer:" / "FINAL ANSWER =") followed by an amount.
       Amount may be: $950.00, $950, 950.00, 950, or 950 dollars/USD.
       Use the amount after the LAST such marker.
    3. If NEITHER JSON NOR FINAL ANSWER marker present -> return None -> I_perp.
       Do NOT fall back to guessing from free prose (owner-approved contract).
    """
    # 1a. Try JSON parsing first (pure JSON output)
    try:
        data = json.loads(output.strip())
        if isinstance(data, dict):
            # Accept "amount" or "answer" field
            if 'amount' in data:
                return float(data['amount'])
            elif 'answer' in data:
                return float(data['answer'])
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    
    # 1b. Search for EMBEDDED structured amount in prose or code fences
    # Pattern: "amount": <number> or "answer": <number> (NUMERIC value, not quoted string)
    # Examples: {"amount": 950.0}, "amount": 950, "answer":123.45
    # Must match ONLY numeric values (not "amount": "950" which is a string)
    embedded_amount_patterns = [
        r'"amount"\s*:\s*(-?\d+(?:\.\d+)?)',  # "amount": 950.0
        r'"answer"\s*:\s*(-?\d+(?:\.\d+)?)',  # "answer": 123.45
    ]
    
    for pattern in embedded_amount_patterns:
        match = re.search(pattern, output)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    
    # 2. Search for FINAL ANSWER marker (case-insensitive)
    # Matches: "FINAL ANSWER:", "Final answer:", "FINAL ANSWER =", etc.
    # Followed by: $950.00, $950, 950.00, 950, 950 dollars, 950 USD
    final_answer_pattern = r'FINAL\s+ANSWER\s*[:\s=]\s*'
    
    # Amount pattern (with optional $, thousands separators, cents, trailing units)
    # Matches: $1,234.56, $950.00, $950, 950.00, 950, also allows "dollars"/"USD" suffix
    amount_pattern = r'\$?\s*[\d,]+(?:\.\d{1,2})?\s*(?:dollars|USD)?'
    
    # Find all FINAL ANSWER markers and their associated amounts
    final_amounts = []
    for marker_match in re.finditer(final_answer_pattern, output, re.IGNORECASE):
        marker_end = marker_match.end()
        # Look for an amount immediately after this marker (within next 50 chars)
        remainder = output[marker_end:marker_end + 50]
        amount_match = re.search(amount_pattern, remainder, re.IGNORECASE)
        if amount_match:
            try:
                # Clean the matched amount string
                amount_str = amount_match.group()
                # Remove $, whitespace, commas, and trailing units
                cleaned = (amount_str.replace('$', '').replace(' ', '').replace(',', '')
                          .replace('dollars', '').replace('USD', '').strip())
                # Must contain at least one digit
                if cleaned and any(c.isdigit() for c in cleaned):
                    amount = float(cleaned)
                    # Store (marker_position, amount) to find the LAST marker
                    final_amounts.append((marker_end, amount))
            except ValueError:
                continue
    
    # If we found FINAL ANSWER markers, return the amount from the LAST one
    if final_amounts:
        # Sort by position and take the last one
        final_amounts.sort(key=lambda x: x[0])
        return final_amounts[-1][1]
    
    # 3. NO structured format found -> return None (conservative I_perp by contract)
    # Do NOT fall back to guessing from free prose
    return None


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
