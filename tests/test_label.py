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
