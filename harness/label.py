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
    
    Strategy:
    1. Look for JSON like {"amount": 123.45}
    2. Look for dollar amounts like $123.45 or 123.45
    3. Return the numeric value as float, or None if no clear number found
    """
    # Try JSON parsing first (most structured)
    try:
        data = json.loads(output.strip())
        if isinstance(data, dict) and 'amount' in data:
            return float(data['amount'])
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    
    # Try to find dollar amounts or plain numbers
    # Pattern: optional $, digits, optional decimal and cents
    # Match things like: $1234.56, 1234.56, $1,234.56
    amount_pattern = r'\$?\s*([\d,]+(?:\.\d{1,2})?)'
    matches = re.findall(amount_pattern, output)
    
    if matches:
        # Take the first match and remove commas
        try:
            amount_str = matches[0].replace(',', '')
            return float(amount_str)
        except ValueError:
            pass
    
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
    try:
        checkers, _, _ = get_checkers_and_candidates(task.domain, task)
    except (ValueError, KeyError):
        # If checkers don't exist (e.g. mock task), fall back to mock labeling
        return _mock_label_fallback(run, task)
    
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
    try:
        checkers, _, _ = get_checkers_and_candidates(task.domain, task)
    except (ValueError, KeyError):
        # If checkers don't exist (e.g. mock task), fall back to mock labeling
        return _mock_label_fallback(run, task)
    
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
    try:
        checkers, _, _ = get_checkers_and_candidates(task.domain, task)
    except (ValueError, KeyError):
        # If checkers don't exist (e.g. mock task), fall back to mock labeling
        return _mock_label_fallback(run, task)
    
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
