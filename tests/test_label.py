"""Golden tests for executable-signal labeling (NO LLM judge).

Tests EACH of the three domains with synthetic outputs that deterministically
satisfy specific interpretation gold checkers. Verifies:
1. Correct interpretation assignment when output matches one interpretation
2. I_perp assignment when output is garbage/matches none
3. No network required (offline deterministic)
"""

import pytest
from common.schema import AgentRun, Interpretation, Task
from harness.label import label_run
from bench.build import load_tasks


@pytest.fixture(autouse=True)
def clear_domain_caches():
    """Clear domain result caches before each test to avoid pollution."""
    try:
        from bench.data_analysis import _RESULT_CACHE as data_cache
        data_cache.clear()
    except ImportError:
        pass
    try:
        from bench.code_spec import _RESULT_CACHE as code_cache
        code_cache.clear()
    except ImportError:
        pass
    yield


# ============================================================================
# CODE_SPEC DOMAIN TESTS
# ============================================================================

def test_label_code_spec_i0_match():
    """code_spec: Reference I0 solution should label as I0."""
    # Load a real code_spec task
    tasks = load_tasks("bench/data/code_spec.jsonl")
    # Pick the first k=1 task (has I0 and I1)
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Get the canonical I0 reference from domain
    from bench.code_spec import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_code = candidates["I0"]
    
    # Create a run with I0 code in a code fence
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=f"```python\n{i0_code}\n```",
        label="",  # Will be assigned by label_run
        verbalized_conf=0.9,
        logit_conf=None,
        seed=42
    )
    
    # Label should be I0
    label = label_run(run, task)
    assert label == "I0", f"Expected I0, got {label}"


def test_label_code_spec_i1_match():
    """code_spec: Reference I1 solution should label as I1."""
    # Load a real code_spec task
    tasks = load_tasks("bench/data/code_spec.jsonl")
    # Pick the first k=1 task (has I0 and I1)
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Get the canonical I1 reference from domain
    from bench.code_spec import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i1_code = candidates["I1"]
    
    # Create a run with I1 code in a code fence
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=f"```python\n{i1_code}\n```",
        label="",
        verbalized_conf=0.85,
        logit_conf=None,
        seed=43
    )
    
    # Label should be I1
    label = label_run(run, task)
    assert label == "I1", f"Expected I1, got {label}"


def test_label_code_spec_i_perp_garbage():
    """code_spec: Garbage output should label as I_perp."""
    # Load a real code_spec task
    tasks = load_tasks("bench/data/code_spec.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Create a run with garbage code
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output="```python\ndef broken():\n    this is not valid python\n```",
        label="",
        verbalized_conf=0.3,
        logit_conf=None,
        seed=44
    )
    
    # Label should be I_perp (execution fails)
    label = label_run(run, task)
    assert label == "I_perp", f"Expected I_perp for garbage, got {label}"


def test_label_code_spec_i_perp_no_code():
    """code_spec: Prose output with no code should label as I_perp."""
    # Load a real code_spec task
    tasks = load_tasks("bench/data/code_spec.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Create a run with prose only (no code)
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output="I think you should sort the records by age in ascending order, "
               "but I'm not sure about the tiebreak. Here's my reasoning: ...",
        label="",
        verbalized_conf=0.5,
        logit_conf=None,
        seed=45
    )
    
    # Label should be I_perp (no code found)
    label = label_run(run, task)
    assert label == "I_perp", f"Expected I_perp for no code, got {label}"


def test_label_code_spec_raw_code():
    """code_spec: Raw code (no fence) should be extracted and labeled."""
    # Load a real code_spec task
    tasks = load_tasks("bench/data/code_spec.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Get the canonical I0 reference from domain
    from bench.code_spec import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_code = candidates["I0"]
    
    # Create a run with raw code (no fence)
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=i0_code,  # Raw code, no fence
        label="",
        verbalized_conf=0.9,
        logit_conf=None,
        seed=46
    )
    
    # Label should be I0 (raw code extracted)
    label = label_run(run, task)
    assert label == "I0", f"Expected I0 for raw code, got {label}"


# ============================================================================
# DATA_ANALYSIS DOMAIN TESTS
# ============================================================================

def test_label_data_analysis_i0_match():
    """data_analysis: Reference I0 solution should label as I0."""
    # CRITICAL: Clear cache first to avoid pollution from test_data_analysis.py
    try:
        from bench.data_analysis import _RESULT_CACHE
        _RESULT_CACHE.clear()
    except ImportError:
        pass
    
    # Load a real data_analysis task
    tasks = load_tasks("bench/data/data_analysis.jsonl")
    # Pick the first k=1 task (has I0 and I1)
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Get the canonical I0 reference from domain
    from bench.data_analysis import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_code = candidates["I0"]
    
    # Create a run with I0 code in a code fence
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=f"```python\n{i0_code}\n```",
        label="",
        verbalized_conf=0.9,
        logit_conf=None,
        seed=50
    )
    
    # Label should be I0
    label = label_run(run, task)
    assert label == "I0", f"Expected I0, got {label}"


def test_label_data_analysis_i1_match():
    """data_analysis: Reference I1 solution should label as I1."""
    # CRITICAL: Clear cache first to avoid pollution from test_data_analysis.py
    try:
        from bench.data_analysis import _RESULT_CACHE
        _RESULT_CACHE.clear()
    except ImportError:
        pass
    
    # Load a real data_analysis task
    tasks = load_tasks("bench/data/data_analysis.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Get the canonical I1 reference from domain
    from bench.data_analysis import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i1_code = candidates["I1"]
    
    # Create a run with I1 code in a code fence
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=f"```python\n{i1_code}\n```",
        label="",
        verbalized_conf=0.85,
        logit_conf=None,
        seed=51
    )
    
    # Label should be I1
    label = label_run(run, task)
    assert label == "I1", f"Expected I1, got {label}"


def test_label_data_analysis_i_perp_garbage():
    """data_analysis: Garbage output should label as I_perp."""
    # Load a real data_analysis task
    tasks = load_tasks("bench/data/data_analysis.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Create a run with garbage code
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output="```python\ndef compute():\n    return 'wrong type'\n```",
        label="",
        verbalized_conf=0.3,
        logit_conf=None,
        seed=52
    )
    
    # Label should be I_perp (wrong output type or value)
    label = label_run(run, task)
    assert label == "I_perp", f"Expected I_perp for garbage, got {label}"


def test_label_data_analysis_i_perp_no_code():
    """data_analysis: Prose output with no code should label as I_perp."""
    # Load a real data_analysis task
    tasks = load_tasks("bench/data/data_analysis.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Create a run with prose only
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output="To compute the average, you should sum all values and divide by count. "
               "Make sure to handle missing values appropriately.",
        label="",
        verbalized_conf=0.5,
        logit_conf=None,
        seed=53
    )
    
    # Label should be I_perp (no code found)
    label = label_run(run, task)
    assert label == "I_perp", f"Expected I_perp for no code, got {label}"


# ============================================================================
# POLICY_QA DOMAIN TESTS
# ============================================================================

def test_label_policy_qa_i0_match():
    """policy_qa: Exact I0 answer (as JSON) should label as I0."""
    # Load a real policy_qa task
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    # Pick the first k=1 task (has I0 and I1)
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Get the canonical I0 reference from domain
    from bench.policy_qa import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_answer = candidates["I0"]
    
    # Create a run with I0 answer as JSON
    import json
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=json.dumps(i0_answer),
        label="",
        verbalized_conf=0.9,
        logit_conf=None,
        seed=60
    )
    
    # Label should be I0
    label = label_run(run, task)
    assert label == "I0", f"Expected I0, got {label}"


def test_label_policy_qa_i1_match():
    """policy_qa: Exact I1 answer (as dollar amount) should label as I1."""
    # Load a real policy_qa task
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Get the canonical I1 reference from domain
    from bench.policy_qa import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i1_answer = candidates["I1"]
    
    # Create a run with I1 answer as dollar amount
    amount = i1_answer["amount"]
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=f"The answer is ${amount:.2f}",
        label="",
        verbalized_conf=0.85,
        logit_conf=None,
        seed=61
    )
    
    # Label should be I1
    label = label_run(run, task)
    assert label == "I1", f"Expected I1, got {label}"


def test_label_policy_qa_i_perp_wrong_amount():
    """policy_qa: Wrong amount (not matching any interpretation) should label as I_perp."""
    # Load a real policy_qa task
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Create a run with a clearly wrong amount
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output="The answer is $999999.99",
        label="",
        verbalized_conf=0.3,
        logit_conf=None,
        seed=62
    )
    
    # Label should be I_perp (amount doesn't match any interpretation)
    label = label_run(run, task)
    assert label == "I_perp", f"Expected I_perp for wrong amount, got {label}"


def test_label_policy_qa_i_perp_no_number():
    """policy_qa: Output with no number should label as I_perp."""
    # Load a real policy_qa task
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Create a run with prose only (no number)
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output="I'm not sure how to calculate this. The policy is ambiguous.",
        label="",
        verbalized_conf=0.5,
        logit_conf=None,
        seed=63
    )
    
    # Label should be I_perp (no numeric answer found)
    label = label_run(run, task)
    assert label == "I_perp", f"Expected I_perp for no number, got {label}"


def test_label_policy_qa_json_format():
    """policy_qa: JSON-formatted answer should be parsed correctly."""
    # Load a real policy_qa task
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Get the canonical I0 reference from domain
    from bench.policy_qa import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_answer = candidates["I0"]
    
    # Create a run with JSON answer
    import json
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=json.dumps(i0_answer),
        label="",
        verbalized_conf=0.9,
        logit_conf=None,
        seed=64
    )
    
    # Label should be I0
    label = label_run(run, task)
    assert label == "I0", f"Expected I0 for JSON format, got {label}"


# ============================================================================
# FALLBACK TESTS
# ============================================================================

def test_label_unknown_domain_fallback():
    """Unknown domain should fall back to deterministic mock."""
    # Create a task with an unknown domain
    task = Task(
        id="unknown_test_001",
        domain="unknown_domain",
        prompt="Test prompt",
        latent_spec="Full spec",
        interpretations=[
            Interpretation(id="I0", is_target=True, gold_check="test_i0"),
            Interpretation(id="I1", is_target=False, gold_check="test_i1"),
        ],
        ambiguity_level=1,
        key_questions=["Test question"]
    )
    
    # Create a run
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output="Some output",
        label="",
        verbalized_conf=0.8,
        logit_conf=None,
        seed=70
    )
    
    # Label should be deterministic (one of I0 or I1)
    label = label_run(run, task)
    assert label in ["I0", "I1"], f"Expected I0 or I1 for fallback, got {label}"
    
    # Verify determinism: same output → same label
    run2 = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output="Some output",  # Same output
        label="",
        verbalized_conf=0.8,
        logit_conf=None,
        seed=71  # Different seed (doesn't affect output hash)
    )
    label2 = label_run(run2, task)
    assert label == label2, f"Fallback should be deterministic on output"


# ============================================================================
# ROBUSTNESS TESTS
# ============================================================================

def test_label_code_fence_variations():
    """code_spec: Various code fence formats should be extracted correctly."""
    # Load a real code_spec task
    tasks = load_tasks("bench/data/code_spec.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Get the canonical I0 reference from domain
    from bench.code_spec import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_code = candidates["I0"]
    
    # Test different fence formats
    fence_formats = [
        f"```python\n{i0_code}\n```",
        f"```\n{i0_code}\n```",
        f"Here's the solution:\n```python\n{i0_code}\n```\nHope this helps!",
    ]
    
    for fence_format in fence_formats:
        run = AgentRun(
            task_id=task.id,
            config="single",
            model_role="tested_agents",
            model_id="test-model",
            output=fence_format,
            label="",
            verbalized_conf=0.9,
            logit_conf=None,
            seed=80
        )
        
        label = label_run(run, task)
        assert label == "I0", f"Expected I0 for fence format {fence_format[:30]}, got {label}"


def test_label_determinism():
    """Labeling should be deterministic (same input → same label)."""
    # Load a real code_spec task
    tasks = load_tasks("bench/data/code_spec.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Get the canonical I0 reference from domain
    from bench.code_spec import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_code = candidates["I0"]
    
    # Create two runs with identical output
    run1 = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=f"```python\n{i0_code}\n```",
        label="",
        verbalized_conf=0.9,
        logit_conf=None,
        seed=90
    )
    
    run2 = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=f"```python\n{i0_code}\n```",  # Same output
        label="",
        verbalized_conf=0.9,
        logit_conf=None,
        seed=91  # Different seed
    )
    
    # Labels should be identical
    label1 = label_run(run1, task)
    label2 = label_run(run2, task)
    assert label1 == label2, f"Labeling should be deterministic: {label1} vs {label2}"
    assert label1 == "I0", f"Expected I0, got {label1}"


# ============================================================================
# AUDIT FIX TESTS (Cross-family GPT audit findings)
# ============================================================================

def test_policy_qa_numeric_extraction_with_prose():
    """BLOCKER FIX: policy_qa numeric extraction should handle leading prose.
    
    The audit found that "After calculation, the answer is $950.00." was
    mislabeled as I_perp because the regex matched a prose comma before the
    number. The fix scans ALL matches and requires at least one digit.
    """
    # Load a real policy_qa task
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Get the canonical I0 reference to know the expected amount
    from bench.policy_qa import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_amount = candidates["I0"]["amount"]
    
    # Test cases that should all extract the number correctly
    test_cases = [
        # (output_string, description)
        (f"${i0_amount:.2f}", "bare dollar amount"),
        (f"The answer is ${i0_amount:.2f}", "simple prose prefix"),
        (f"After calculation, the answer is ${i0_amount:.2f}.", "realistic prose with comma"),
        (f"The total is ${i0_amount:,.2f} due today.", "thousands separator with prose"),
        (f'{{"amount": {i0_amount}}}', "JSON format"),
    ]
    
    for output, description in test_cases:
        run = AgentRun(
            task_id=task.id,
            config="single",
            model_role="tested_agents",
            model_id="test-model",
            output=output,
            label="",
            verbalized_conf=0.9,
            logit_conf=None,
            seed=100
        )
        label = label_run(run, task)
        assert label == "I0", f"Failed for {description}: expected I0, got {label} for output: {output}"


def test_policy_qa_numeric_extraction_no_number():
    """BLOCKER FIX: policy_qa should return I_perp when no number is present."""
    # Load a real policy_qa task
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Prose-only output with no number
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output="The policy is ambiguous and I cannot provide a specific amount.",
        label="",
        verbalized_conf=0.3,
        logit_conf=None,
        seed=101
    )
    
    label = label_run(run, task)
    assert label == "I_perp", f"Expected I_perp for no-number prose, got {label}"


def test_real_domain_checker_loading_failure_fails_loud():
    """MAJOR FIX: Real domains with unavailable checkers should raise, not silently mock-label.
    
    The audit found that checker-loading failures for real domains (code_spec,
    data_analysis, policy_qa) silently fell back to mock hash labeling, which
    would corrupt labels. The fix raises RuntimeError instead.
    """
    # Create a task with a real domain but non-existent checker
    task = Task(
        id="code_spec_test_001",
        domain="code_spec",
        prompt="Test prompt",
        latent_spec="Full spec",
        interpretations=[
            Interpretation(id="I0", is_target=True, gold_check="nonexistent_checker_xyz"),
            Interpretation(id="I1", is_target=False, gold_check="another_missing_checker"),
        ],
        ambiguity_level=1,
        key_questions=["Test question"]
    )
    
    # Create a run
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output="```python\ndef solution(): return 42\n```",
        label="",
        verbalized_conf=0.8,
        logit_conf=None,
        seed=102
    )
    
    # Should raise RuntimeError, NOT return a mock label
    try:
        label = label_run(run, task)
        # If we get here, the test fails
        assert False, f"Expected RuntimeError for missing checkers, but got label: {label}"
    except RuntimeError as e:
        # Expected: should contain "gold checkers unavailable"
        assert "gold checkers unavailable" in str(e).lower(), \
            f"Expected 'gold checkers unavailable' in error, got: {e}"
        assert "code_spec" in str(e), f"Expected domain 'code_spec' in error, got: {e}"


def test_policy_qa_multi_step_extraction_case1():
    """RE-AUDIT FIX: Multi-step reasoning with base → final (should extract final).
    
    Case: "Step 1: base is $1000, after 10% fee the answer is $900.00"
    Should extract 900 (final), not 1000 (intermediate).
    """
    # Load a real policy_qa task where I0=$900 (or close)
    # We'll use a task and verify it extracts the LAST cued amount
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # We need to know what 900.00 maps to. For this test, let's just verify
    # that the extraction prefers the "answer is" cue over the earlier amount.
    # We'll construct output with canonical I0 as the final answer.
    from bench.policy_qa import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_amount = candidates["I0"]["amount"]
    
    # Construct output: intermediate $1000, then "answer is" with I0's amount
    output = f"Step 1: base is $1000, after 10% fee the answer is ${i0_amount:.2f}"
    
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=output,
        label="",
        verbalized_conf=0.9,
        logit_conf=None,
        seed=110
    )
    
    label = label_run(run, task)
    # Should label as I0 (the final answer with cue), not mislabel from 1000
    assert label == "I0", f"Expected I0 for multi-step with answer cue, got {label}"


def test_policy_qa_multi_step_extraction_case2():
    """RE-AUDIT FIX: Multiple intermediate values → final (should extract final).
    
    Case: "Regular pay is $800.00 and overtime is $150.00, so the answer is $950.00."
    Should extract 950 (final with cue), not 800 (first intermediate).
    """
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    from bench.policy_qa import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_amount = candidates["I0"]["amount"]
    
    # Construct: two intermediates, then "answer is" with I0
    output = f"Regular pay is $800.00 and overtime is $150.00, so the answer is ${i0_amount:.2f}."
    
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=output,
        label="",
        verbalized_conf=0.9,
        logit_conf=None,
        seed=111
    )
    
    label = label_run(run, task)
    assert label == "I0", f"Expected I0 for multi-intermediate with answer cue, got {label}"


def test_policy_qa_multi_step_extraction_case3():
    """RE-AUDIT FIX: Hypothetical alternative → final (should extract final).
    
    Case: "Using double overtime would be $1000.00, but the final answer is $950.00."
    Should extract 950 (with "final answer" cue), not 1000 (hypothetical).
    """
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    from bench.policy_qa import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_amount = candidates["I0"]["amount"]
    
    # Construct: hypothetical, then "final answer is" with I0
    output = f"Using double overtime would be $1000.00, but the final answer is ${i0_amount:.2f}."
    
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=output,
        label="",
        verbalized_conf=0.9,
        logit_conf=None,
        seed=112
    )
    
    label = label_run(run, task)
    assert label == "I0", f"Expected I0 for hypothetical → final answer cue, got {label}"


def test_policy_qa_multi_step_extraction_case4():
    """RE-AUDIT FIX: Preliminary calc → final (should extract final with cue).
    
    Case: "A preliminary calculation gives 910.00, but the final answer is $950.00."
    Should extract 950 (with "final answer" cue), not 910 (preliminary).
    """
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    from bench.policy_qa import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_amount = candidates["I0"]["amount"]
    
    # Construct: preliminary (no $), then "final answer is" with I0
    output = f"A preliminary calculation gives 910.00, but the final answer is ${i0_amount:.2f}."
    
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=output,
        label="",
        verbalized_conf=0.9,
        logit_conf=None,
        seed=113
    )
    
    label = label_run(run, task)
    assert label == "I0", f"Expected I0 for preliminary → final answer cue, got {label}"


def test_policy_qa_multi_step_extraction_case5():
    """RE-AUDIT FIX: Multiple inputs → final (should extract final with cue).
    
    Case: "There are 45 hours and $20.00/hour; final gross pay is $950.00."
    Should extract 950 (with "gross pay is" cue), not 20 (rate input).
    """
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    from bench.policy_qa import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_amount = candidates["I0"]["amount"]
    
    # Construct: inputs (20/hour), then "gross pay is" with I0
    output = f"There are 45 hours and $20.00/hour; final gross pay is ${i0_amount:.2f}."
    
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=output,
        label="",
        verbalized_conf=0.9,
        logit_conf=None,
        seed=114
    )
    
    label = label_run(run, task)
    assert label == "I0", f"Expected I0 for inputs → gross pay cue, got {label}"


def test_policy_qa_json_overrides_prose():
    """RE-AUDIT: JSON amount should win even if prose has other numbers."""
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    from bench.policy_qa import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_amount = candidates["I0"]["amount"]
    
    # Prose with wrong number, but JSON has correct I0
    import json
    output = f"I calculated $800.00 initially. {json.dumps({'amount': i0_amount})}"
    
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=output,
        label="",
        verbalized_conf=0.9,
        logit_conf=None,
        seed=115
    )
    
    label = label_run(run, task)
    # JSON should win
    assert label == "I0", f"Expected I0 (JSON should override prose), got {label}"


def test_policy_qa_single_amount_still_works():
    """RE-AUDIT: Single-amount answer should still work (fallback to last)."""
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    from bench.policy_qa import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_amount = candidates["I0"]["amount"]
    
    # Just one amount, no cues
    output = f"${i0_amount:.2f}"
    
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=output,
        label="",
        verbalized_conf=0.9,
        logit_conf=None,
        seed=116
    )
    
    label = label_run(run, task)
    assert label == "I0", f"Expected I0 for single amount, got {label}"


def test_policy_qa_garbage_no_number_i_perp():
    """RE-AUDIT: Pure garbage with no number should still → I_perp."""
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    output = "This is confusing and I cannot provide a numerical answer to this question."
    
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=output,
        label="",
        verbalized_conf=0.3,
        logit_conf=None,
        seed=117
    )
    
    label = label_run(run, task)
    assert label == "I_perp", f"Expected I_perp for no-number garbage, got {label}"
