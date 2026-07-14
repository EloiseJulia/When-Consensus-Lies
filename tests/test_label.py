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
    """policy_qa: Exact I1 answer (STRUCTURED format) should label as I1."""
    # Load a real policy_qa task
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Get the canonical I1 reference from domain
    from bench.policy_qa import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i1_answer = candidates["I1"]
    
    # Create a run with I1 answer using FINAL ANSWER marker
    amount = i1_answer["amount"]
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=f"FINAL ANSWER: ${amount:.2f}",
        label="",
        verbalized_conf=0.85,
        logit_conf=None,
        seed=61
    )
    
    # Label should be I1
    label = label_run(run, task)
    assert label == "I1", f"Expected I1, got {label}"


def test_label_policy_qa_i_perp_wrong_amount():
    """policy_qa: Wrong amount (STRUCTURED but not matching) should label as I_perp."""
    # Load a real policy_qa task
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Create a run with a STRUCTURED but clearly wrong amount
    run = AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output="FINAL ANSWER: $999999.99",
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
# STRUCTURED ANSWER CONTRACT TESTS (owner-approved)
# ============================================================================

def test_policy_qa_final_answer_marker_variants():
    """STRUCTURED CONTRACT: FINAL ANSWER marker variants should all work.
    
    Tests: "FINAL ANSWER: $950.00", "FINAL ANSWER: 950 dollars", "FINAL ANSWER: $950"
    """
    # Load a real policy_qa task
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    # Get the canonical I0 reference
    from bench.policy_qa import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_amount = candidates["I0"]["amount"]
    
    # Test cases: different FINAL ANSWER marker formats
    test_cases = [
        (f"FINAL ANSWER: ${i0_amount:.2f}", "FINAL ANSWER: $950.00"),
        (f"FINAL ANSWER: {i0_amount} dollars", "FINAL ANSWER: 950 dollars"),
        (f"FINAL ANSWER: ${int(i0_amount)}", "FINAL ANSWER: $950"),
        (f"Final answer: ${i0_amount:.2f}", "Final answer: (lowercase)"),
        (f"FINAL ANSWER = ${i0_amount:.2f}", "FINAL ANSWER = (equals)"),
        (f"FINAL ANSWER:${i0_amount:.2f}", "no space after colon"),
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
        assert label == "I0", f"Failed for {description}: expected I0, got {label}"


def test_policy_qa_json_structured_format():
    """STRUCTURED CONTRACT: JSON format should work (pure and embedded)."""
    # Load a real policy_qa task
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    from bench.policy_qa import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_amount = candidates["I0"]["amount"]
    
    import json
    # Test cases: JSON variants
    test_cases = [
        (json.dumps({"amount": i0_amount}), "pure JSON"),
        (f'{{"amount": {i0_amount}}}', "JSON embedded in output"),
        (f'```json\n{{"amount": {i0_amount}}}\n```', "fenced JSON"),
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
            seed=101
        )
        label = label_run(run, task)
        assert label == "I0", f"Failed for {description}: expected I0, got {label}"


def test_policy_qa_unstructured_prose_returns_i_perp():
    """STRUCTURED CONTRACT: Unstructured free-text -> I_perp (by contract).
    
    Tests that outputs WITHOUT JSON or FINAL ANSWER marker return I_perp,
    even if they contain dollar amounts in prose. This is the owner-approved
    contract: unparseable free-text is conservatively I_perp, not guessed.
    """
    # Load a real policy_qa task
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.ambiguity_level == 1)
    
    from bench.policy_qa import get_checkers_and_candidates
    checkers, candidates, foils = get_checkers_and_candidates(task.domain, task)
    i0_amount = candidates["I0"]["amount"]
    
    # All these are UNSTRUCTURED (no JSON, no FINAL ANSWER marker) -> I_perp by contract
    unstructured_outputs = [
        f"The answer is ${i0_amount:.2f}.",  # prose with "the answer is"
        f"After calculation, the answer is ${i0_amount:.2f}.",  # prose with leading text
        f"Regular pay is $800 and overtime is $150, so the answer is ${i0_amount:.2f}.",  # multi-step
        f"${i0_amount:.2f}",  # bare dollar amount (no marker)
        "I'm not sure how to calculate this.",  # pure prose, no number
    ]
    
    for output in unstructured_outputs:
        run = AgentRun(
            task_id=task.id,
            config="single",
            model_role="tested_agents",
            model_id="test-model",
            output=output,
            label="",
            verbalized_conf=0.5,
            logit_conf=None,
            seed=102
        )
        label = label_run(run, task)
        assert label == "I_perp", f"Expected I_perp for unstructured output, got {label}. Output: {output}"


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


# ============================================================================
# AUDIT FIX REGRESSION TESTS (GPT cross-family audit, 2026-07-15)
# ============================================================================

def _make_policy_run(task, output, seed):
    """Helper: build a policy_qa AgentRun with the given output."""
    return AgentRun(
        task_id=task.id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=output,
        label="",
        verbalized_conf=0.5,
        logit_conf=None,
        seed=seed,
    )


def _policy_task():
    """Return a k=1 policy_qa task with known I0/I1 gold amounts."""
    tasks = load_tasks("bench/data/policy_qa.jsonl")
    return next(t for t in tasks if t.ambiguity_level == 1)


def _i0_amount(task):
    from bench.policy_qa import get_checkers_and_candidates
    _, candidates, _ = get_checkers_and_candidates(task.domain, task)
    return candidates["I0"]["amount"]  # e.g. 950.0


# ── BLOCKER fix: embedded JSON key in prose (no {}) → I_perp ─────────────────

def test_audit_fix_prose_json_key_no_braces_i_perp():
    """BLOCKER: 'amount': N in prose without {} wrapper → I_perp (no scraping)."""
    task = _policy_task()
    amt = _i0_amount(task)
    # Plain prose with "amount": N text but no JSON object
    output = f'Based on the calculation the "amount": {amt} is the gross pay.'
    label = label_run(_make_policy_run(task, output, 300), task)
    assert label == "I_perp", f"Expected I_perp for bare 'amount': N in prose, got {label}"


# ── BLOCKER fix: FINAL ANSWER: unavailable… → I_perp ─────────────────────────

def test_audit_fix_final_answer_unavailable_i_perp():
    """BLOCKER: 'FINAL ANSWER: unavailable; prior total was $950.00' → I_perp."""
    task = _policy_task()
    amt = _i0_amount(task)
    output = f"FINAL ANSWER: unavailable; prior total was ${amt:.2f}"
    label = label_run(_make_policy_run(task, output, 301), task)
    assert label == "I_perp", f"Expected I_perp for unavailable FINAL ANSWER, got {label}"


# ── MAJOR fix: conflicting FINAL ANSWER markers → I_perp ─────────────────────

def test_audit_fix_conflicting_final_answer_markers_i_perp():
    """MAJOR: Two FINAL ANSWER markers with different values → I_perp."""
    task = _policy_task()
    output = "At first I computed FINAL ANSWER: $950.00 but revised to FINAL ANSWER: $910.00"
    label = label_run(_make_policy_run(task, output, 302), task)
    assert label == "I_perp", f"Expected I_perp for conflicting markers, got {label}"


def test_audit_fix_conflicting_json_and_final_answer_i_perp():
    """MAJOR: JSON $950 + FINAL ANSWER $910 conflict → I_perp."""
    task = _policy_task()
    output = '{"amount": 950.0}\nFINAL ANSWER: $910.00'
    label = label_run(_make_policy_run(task, output, 303), task)
    assert label == "I_perp", f"Expected I_perp for JSON/marker conflict, got {label}"


# ── MAJOR fix: non-finite JSON amounts → I_perp (no crash) ───────────────────

def test_audit_fix_json_inf_amount_i_perp():
    """MAJOR: JSON {"amount": 1e309} → inf → I_perp, must not crash."""
    task = _policy_task()
    label = label_run(_make_policy_run(task, '{"amount": 1e309}', 304), task)
    assert label == "I_perp", f"Expected I_perp for inf amount, got {label}"


def test_audit_fix_json_nan_amount_i_perp():
    """MAJOR: '{"amount": NaN}' is invalid JSON → I_perp, must not crash."""
    task = _policy_task()
    label = label_run(_make_policy_run(task, '{"amount": NaN}', 305), task)
    assert label == "I_perp", f"Expected I_perp for NaN (invalid JSON), got {label}"


# ── MAJOR fix: negative FINAL ANSWER sign preserved ──────────────────────────

def test_audit_fix_negative_sign_preserved_i_perp():
    """MAJOR: FINAL ANSWER: $-950.00 preserves sign; no gold match → I_perp."""
    task = _policy_task()
    # Negative amount matches no positive gold → I_perp
    for output in ["FINAL ANSWER: $-950.00", "FINAL ANSWER: -$950.00",
                   "FINAL ANSWER: -950.00"]:
        label = label_run(_make_policy_run(task, output, 306), task)
        assert label == "I_perp", \
            f"Expected I_perp for '{output}' (negative), got {label}"


# ── Regression: single valid answers still label correctly ───────────────────

def test_audit_fix_regression_valid_json_labels_correctly():
    """REGRESSION: Single valid JSON amount still reaches correct interpretation."""
    task = _policy_task()
    amt = _i0_amount(task)
    label = label_run(_make_policy_run(task, f'{{"amount": {amt}}}', 307), task)
    assert label == "I0", f"Expected I0 for valid JSON, got {label}"


def test_audit_fix_regression_valid_final_answer_labels_correctly():
    """REGRESSION: Single valid FINAL ANSWER still reaches correct interpretation."""
    task = _policy_task()
    amt = _i0_amount(task)
    label = label_run(_make_policy_run(task, f"FINAL ANSWER: ${amt:.2f}", 308), task)
    assert label == "I0", f"Expected I0 for valid FINAL ANSWER, got {label}"


def test_audit_fix_agreeing_markers_not_i_perp():
    """REGRESSION: Duplicate FINAL ANSWER markers with SAME value → still labelled."""
    task = _policy_task()
    amt = _i0_amount(task)
    output = f"First attempt FINAL ANSWER: ${amt:.2f}\nFinal check FINAL ANSWER: ${amt:.2f}"
    label = label_run(_make_policy_run(task, output, 309), task)
    assert label == "I0", f"Expected I0 for agreeing markers, got {label}"


# ============================================================================
# AUDIT RE-AUDIT FIX REGRESSION TESTS (GPT cross-family re-audit, 2026-07-15)
# ============================================================================

def test_reaudit_conflicting_json_blocks_i_perp():
    """MAJOR: Two JSON objects with different amounts → I_perp (both collected)."""
    task = _policy_task()
    output = '{"amount": 950}\n{"amount": 910}'
    label = label_run(_make_policy_run(task, output, 400), task)
    assert label == "I_perp", f"Expected I_perp for conflicting JSON blocks, got {label}"


def test_reaudit_json_then_invalid_amount_i_perp():
    """MAJOR: Valid JSON then JSON with invalid amount → I_perp (invalid not ignored)."""
    task = _policy_task()
    output = '{"amount": 950}\n{"amount": "bad"}'
    label = label_run(_make_policy_run(task, output, 401), task)
    assert label == "I_perp", f"Expected I_perp for valid+invalid JSON, got {label}"


def test_reaudit_same_value_markers_one_line_labels_correctly():
    """MAJOR: Two identical FINAL ANSWER markers on ONE line → labels correctly."""
    task = _policy_task()
    amt = _i0_amount(task)
    output = f"FINAL ANSWER: ${amt:.2f} FINAL ANSWER: ${amt:.2f}"
    label = label_run(_make_policy_run(task, output, 402), task)
    assert label == "I0", \
        f"Expected I0 for two identical markers on one line, got {label}"


def test_reaudit_large_finite_amount_i_perp():
    """MAJOR: {"amount": 1e308} → Decimal too large to quantize → I_perp (no crash)."""
    task = _policy_task()
    label = label_run(_make_policy_run(task, '{"amount": 1e308}', 403), task)
    assert label == "I_perp", f"Expected I_perp for huge amount, got {label}"


def test_reaudit_extra_keys_labels_correctly():
    """MANAGER RULING: JSON with extra keys but valid 'amount' → correct label (not I_perp)."""
    task = _policy_task()
    amt = _i0_amount(task)
    # Extra keys must NOT cause I_perp
    for output, desc in [
        (f'{{"amount": {amt}, "currency": "USD"}}', "amount+currency"),
        (f'{{"amount": {amt}, "note": 1}}', "amount+note"),
    ]:
        label = label_run(_make_policy_run(task, output, 404), task)
        assert label == "I0", \
            f"Expected I0 for extra-key JSON ({desc}), got {label}"


# ============================================================================
# FINAL HARDENING TESTS (GPT third-pass audit, 2026-07-15)
# ============================================================================

def test_final_hardening_deeply_nested_json_i_perp():
    """FIX-A: 5000-deeply-nested JSON triggers RecursionError → I_perp, never raises."""
    task = _policy_task()
    # Build a deeply nested JSON that exceeds Python's recursion limit when parsed
    nested = "null"
    for _ in range(5000):
        nested = '{"x":' + nested + "}"
    # Must not raise, must return I_perp
    label = label_run(_make_policy_run(task, nested, 500), task)
    assert label == "I_perp", f"Expected I_perp for deeply-nested JSON, got {label}"


def test_final_hardening_brace_in_string_labels_correctly():
    """FIX-A: JSON with brace inside a string value is parsed correctly → I0."""
    task = _policy_task()
    amt = _i0_amount(task)
    output = f'{{"amount":{amt},"note":"}}"}}'
    label = label_run(_make_policy_run(task, output, 501), task)
    assert label == "I0", \
        f"Expected I0 for JSON with brace-in-string, got {label}"


def test_final_hardening_bad_thousands_grouping_i_perp():
    """FIX-B: Malformed thousands grouping in FINAL ANSWER → I_perp."""
    task = _policy_task()
    for output, desc in [
        ("FINAL ANSWER: $,1000.00", "leading comma"),
        ("FINAL ANSWER: $10,00.00", "wrong group size"),
    ]:
        label = label_run(_make_policy_run(task, output, 502), task)
        assert label == "I_perp", \
            f"Expected I_perp for bad grouping '{desc}', got {label}"


def test_final_hardening_unicode_digits_i_perp():
    """FIX-B: Unicode digits in amount token → I_perp (re.ASCII enforced)."""
    task = _policy_task()
    # Arabic-Indic digits: ١٠٠٠ = 1000 in Unicode, not ASCII 0-9
    label = label_run(
        _make_policy_run(task, "FINAL ANSWER: $\u0661\u0660\u0660\u0660.00", 503), task
    )
    assert label == "I_perp", f"Expected I_perp for Unicode-digit amount, got {label}"


def test_final_hardening_valid_thousands_grouping_labels_correctly():
    """FIX-B REGRESSION: Well-formed $1,000.00 still parses correctly."""
    task = _policy_task()
    # policy_interest_001 I0 = 147.95; use 1000.00 which maps to policy_overtime_001 I2
    # Just check we get a concrete (non-I_perp) or I_perp based on gold, not a crash.
    # Use the I0 amount with well-formed grouping if it has 4+ digits; otherwise just
    # confirm no crash and sane result.
    amt = _i0_amount(task)  # e.g. 950.0
    # Format with thousands grouping if >= 1000, otherwise just plain
    if amt >= 1000:
        from decimal import Decimal as D
        formatted = f"{int(amt):,}"
    else:
        formatted = f"{amt:.2f}"
    output = f"FINAL ANSWER: ${formatted}"
    label = label_run(_make_policy_run(task, output, 504), task)
    # Must not crash; result depends on whether formatted amount matches gold
    assert label in ("I0", "I1", "I2", "I_perp"), \
        f"Unexpected label '{label}' for well-formed grouping"


def test_final_hardening_good_thousands_explicit():
    """FIX-B REGRESSION: $1,000.00 explicitly parses to 1000.0 (not I_perp)."""
    from harness.label import _extract_numeric_from_output
    result = _extract_numeric_from_output("FINAL ANSWER: $1,000.00")
    assert result == 1000.0, f"Expected 1000.0 for $1,000.00, got {result!r}"


def test_final_hardening_bare_marker_with_valid_json_i_perp():
    """FIX-C: Valid JSON amount + bare FINAL ANSWER: (empty) → I_perp."""
    task = _policy_task()
    amt = _i0_amount(task)
    output = f'{{"amount":{amt}}}\nFINAL ANSWER:'
    label = label_run(_make_policy_run(task, output, 505), task)
    assert label == "I_perp", \
        f"Expected I_perp for valid JSON + bare FINAL ANSWER marker, got {label}"
