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
    
    Priority order (to handle multi-step reasoning with intermediate values):
    1. STRUCTURED JSON: {"amount": X} or {"answer": X} takes precedence
    2. ANSWER-CUE preference: Search for explicit final-answer markers and take
       the amount after the LAST such marker. Markers: "final answer", "the answer is",
       "answer:", "answer is", "total is", "total:", "gross pay is", "final ... is",
       or "= $X" patterns.
    3. FALLBACK: If no cues, return the LAST parseable dollar/decimal amount
       (final answers appear last in multi-step reasoning).
    
    This priority fixes mislabeling when answers show work (e.g., "base is $1000,
    after fee the answer is $900" correctly extracts 900, not 1000).
    """
    # 1. Try JSON parsing first (most structured)
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
    
    # Pattern for dollar amounts or plain decimal numbers
    # Matches: $1,234.56, $950.00, 950.00, $950, 1234.56
    # CRITICAL: Must contain at least one digit (bare commas never match)
    amount_pattern = r'\$\s*[\d,]+(?:\.\d{1,2})?|(?<!\d)[\d,]+\.\d{1,2}(?!\d)'
    
    # 2. Search for answer-cue markers and extract amount after the LAST marker
    # Markers indicate final answer (case-insensitive)
    answer_cues = [
        r'final\s+answer\s*:?\s*',
        r'the\s+answer\s+is\s*:?\s*',
        r'answer\s*:\s*',
        r'answer\s+is\s*:?\s*',
        r'total\s+is\s*:?\s*',
        r'total\s*:\s*',
        r'gross\s+pay\s+is\s*:?\s*',
        r'final\s+\w+\s+is\s*:?\s*',  # "final <anything> is"
        r'=\s*',  # "= $X" pattern
    ]
    
    # Find all cue positions and their associated amounts
    cue_amounts = []
    for cue_pattern in answer_cues:
        # Find all matches of this cue pattern (case-insensitive)
        for cue_match in re.finditer(cue_pattern, output, re.IGNORECASE):
            cue_end = cue_match.end()
            # Look for an amount immediately after this cue (within next 50 chars)
            remainder = output[cue_end:cue_end + 50]
            amount_match = re.search(amount_pattern, remainder)
            if amount_match:
                try:
                    cleaned = amount_match.group().replace('$', '').replace(' ', '').replace(',', '')
                    if cleaned and any(c.isdigit() for c in cleaned):
                        amount = float(cleaned)
                        # Store (cue_position, amount) to find the LAST cue
                        cue_amounts.append((cue_end, amount))
                except ValueError:
                    continue
    
    # If we found cue-associated amounts, return the one from the LAST cue
    if cue_amounts:
        # Sort by position and take the last one
        cue_amounts.sort(key=lambda x: x[0])
        return cue_amounts[-1][1]
    
    # 3. FALLBACK: No cues found, return the LAST parseable amount in the text
    # (final answers typically appear last in multi-step reasoning)
    matches = re.findall(amount_pattern, output)
    
    # Scan matches in REVERSE order (last to first) to prefer final amounts
    for match in reversed(matches):
        try:
            cleaned = match.replace('$', '').replace(' ', '').replace(',', '')
            if cleaned and any(c.isdigit() for c in cleaned):
                return float(cleaned)
        except ValueError:
            continue
    
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
