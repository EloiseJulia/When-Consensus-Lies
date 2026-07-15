"""Tests for Phase 2 execution configs (harness/run.py).

Each config must produce:
- Correct number/shape of AgentRuns
- Deterministic outputs (same seeds → identical results)
- Correct config/model_role/model_id/seed fields
- Unique identity keys within a config's output
- For MAD: expected number of rounds/agents
"""

import pytest
from common.schema import Interpretation, Task, AgentRun
from common.config import load_config
from common.llm import LLMClient
from harness.run import (
    run_task,
    run_single,
    run_self_consistency,
    run_mad,
    run_verifier,
    run_diverse,
    answer_format_instruction,
)


@pytest.fixture
def mock_task():
    """Fixture providing a mock task for testing."""
    return Task(
        id="test_task_001",
        domain="code_spec",
        prompt="Write a function to sort a list.",
        latent_spec="Full spec with all requirements...",
        interpretations=[
            Interpretation(id="I0", is_target=True, gold_check="test_gold_i0"),
            Interpretation(id="I1", is_target=False, gold_check="test_gold_i1"),
            Interpretation(id="I2", is_target=False, gold_check="test_gold_i2"),
        ],
        ambiguity_level=2,
        key_questions=["What order should the list be sorted in?"]
    )


@pytest.fixture
def client():
    """Fixture providing an offline LLMClient."""
    config = load_config()
    return LLMClient(config, offline=True)


def test_single_config(mock_task, client):
    """Test single-agent config."""
    run = run_single(mock_task, client)
    
    # Verify single run returned
    assert isinstance(run, AgentRun)
    
    # Verify fields
    assert run.task_id == mock_task.id
    assert run.config == "single"
    assert run.model_role == "tested_agents"
    assert run.model_id  # Should have a model ID
    assert run.output  # Should have output
    assert run.label == ""  # Unlabeled
    assert 0.0 <= run.verbalized_conf <= 1.0
    assert run.seed is not None
    
    # Verify determinism
    run2 = run_single(mock_task, client)
    assert run.output == run2.output
    assert run.seed == run2.seed
    assert run.model_id == run2.model_id


def test_sc_config_k5(mock_task, client):
    """Test self-consistency config with k=5."""
    runs = run_self_consistency(mock_task, client, k=5)
    
    # Verify count
    assert len(runs) == 5
    assert all(isinstance(r, AgentRun) for r in runs)
    
    # Verify fields
    assert all(r.task_id == mock_task.id for r in runs)
    assert all(r.config == "sc" for r in runs)
    assert all(r.model_role == "tested_agents" for r in runs)
    assert all(r.label == "" for r in runs)
    
    # Verify unique seeds
    seeds = [r.seed for r in runs]
    assert len(set(seeds)) == 5, "Seeds must be unique"
    
    # Verify identity keys are unique
    identity_keys = [
        (r.task_id, r.config, r.model_role, r.model_id, r.seed)
        for r in runs
    ]
    assert len(set(identity_keys)) == 5, "Identity keys must be unique"
    
    # Verify determinism
    runs2 = run_self_consistency(mock_task, client, k=5)
    for r1, r2 in zip(runs, runs2):
        assert r1.output == r2.output
        assert r1.seed == r2.seed


def test_sc_config_k10(mock_task, client):
    """Test self-consistency config with k=10."""
    runs = run_self_consistency(mock_task, client, k=10)
    
    # Verify count
    assert len(runs) == 10
    
    # Verify unique seeds
    seeds = [r.seed for r in runs]
    assert len(set(seeds)) == 10, "Seeds must be unique"


def test_homogeneous_mad_config(mock_task, client):
    """Test homogeneous MAD config."""
    n_agents = 3
    rounds = 3
    runs = run_mad(mock_task, client, homogeneous=True, n_agents=n_agents, rounds=rounds)
    
    # Verify count (one run per agent)
    assert len(runs) == n_agents
    assert all(isinstance(r, AgentRun) for r in runs)
    
    # Verify fields
    assert all(r.task_id == mock_task.id for r in runs)
    assert all(r.config == "homogeneous-MAD" for r in runs)
    assert all(r.model_role == "tested_agents" for r in runs)
    assert all(r.label == "" for r in runs)
    
    # Verify unique seeds (each agent in final round has different seed)
    seeds = [r.seed for r in runs]
    assert len(set(seeds)) == n_agents, "Seeds must be unique per agent"
    
    # Verify identity keys are unique
    identity_keys = [
        (r.task_id, r.config, r.model_role, r.model_id, r.seed)
        for r in runs
    ]
    assert len(set(identity_keys)) == n_agents, "Identity keys must be unique"
    
    # Verify determinism
    runs2 = run_mad(mock_task, client, homogeneous=True, n_agents=n_agents, rounds=rounds)
    for r1, r2 in zip(runs, runs2):
        assert r1.output == r2.output
        assert r1.seed == r2.seed


def test_heterogeneous_mad_config(mock_task, client):
    """Test heterogeneous MAD config."""
    n_agents = 4
    rounds = 3
    runs = run_mad(mock_task, client, homogeneous=False, n_agents=n_agents, rounds=rounds)
    
    # Verify count
    assert len(runs) == n_agents
    
    # Verify fields
    assert all(r.config == "heterogeneous-MAD" for r in runs)
    assert all(r.task_id == mock_task.id for r in runs)
    
    # Verify unique seeds
    seeds = [r.seed for r in runs]
    assert len(set(seeds)) == n_agents, "Seeds must be unique per agent"
    
    # Verify identity keys are unique
    identity_keys = [
        (r.task_id, r.config, r.model_role, r.model_id, r.seed)
        for r in runs
    ]
    assert len(set(identity_keys)) == n_agents, "Identity keys must be unique"


def test_verifier_config(mock_task, client):
    """Test verifier config."""
    n_candidates = 3
    runs = run_verifier(mock_task, client, n_candidates=n_candidates)
    
    # FIX BUG 3: Verifier now returns ONLY the selection (1 run with selected answer)
    assert len(runs) == 1
    assert all(isinstance(r, AgentRun) for r in runs)
    
    # Verify fields
    assert all(r.task_id == mock_task.id for r in runs)
    assert all(r.config == "verifier" for r in runs)
    assert all(r.model_role == "tested_agents" for r in runs)
    assert all(r.label == "" for r in runs)
    
    # Verify the output is an actual candidate answer, not "Candidate N"
    # (deterministic selection should pick a valid candidate)
    verifier_run = runs[0]
    assert verifier_run.output.startswith("MOCK_OUTPUT_")  # Actual answer, not selection text
    assert "Candidate" not in verifier_run.output or verifier_run.output.startswith("MOCK_OUTPUT_")
    
    # Verify determinism
    runs2 = run_verifier(mock_task, client, n_candidates=n_candidates)
    assert runs[0].output == runs2[0].output
    assert runs[0].seed == runs2[0].seed


def test_interpretation_diverse_config(mock_task, client):
    """Test interpretation-diverse config."""
    runs = run_diverse(mock_task, client)
    
    # FIX BUG 4: Now returns len(task.interpretations) runs (not fixed 5)
    expected_count = len(mock_task.interpretations)
    assert len(runs) == expected_count
    assert all(isinstance(r, AgentRun) for r in runs)
    
    # Verify fields
    assert all(r.task_id == mock_task.id for r in runs)
    assert all(r.config == "interpretation-diverse" for r in runs)
    assert all(r.model_role == "tested_agents" for r in runs)
    assert all(r.label == "" for r in runs)
    
    # Verify unique seeds
    seeds = [r.seed for r in runs]
    assert len(set(seeds)) == expected_count, "Seeds must be unique"
    
    # Verify identity keys are unique
    identity_keys = [
        (r.task_id, r.config, r.model_role, r.model_id, r.seed)
        for r in runs
    ]
    assert len(set(identity_keys)) == expected_count, "Identity keys must be unique"
    
    # Verify determinism
    runs2 = run_diverse(mock_task, client)
    for r1, r2 in zip(runs, runs2):
        assert r1.output == r2.output
        assert r1.seed == r2.seed


def test_run_task_dispatcher(mock_task, client):
    """Test run_task dispatcher routes to correct implementations."""
    # Test single
    single_runs = run_task(mock_task, "single", client)
    assert isinstance(single_runs, list)
    assert len(single_runs) == 1
    assert single_runs[0].config == "single"
    
    # Test sc with k=5
    sc_runs = run_task(mock_task, "sc", client, k=5)
    assert len(sc_runs) == 5
    assert all(r.config == "sc" for r in sc_runs)
    
    # Test sc with k=10
    sc_runs_10 = run_task(mock_task, "sc", client, k=10)
    assert len(sc_runs_10) == 10
    
    # Test homogeneous-MAD
    hmad_runs = run_task(mock_task, "homogeneous-MAD", client, n_agents=3, rounds=3)
    assert len(hmad_runs) == 3
    assert all(r.config == "homogeneous-MAD" for r in hmad_runs)
    
    # Test heterogeneous-MAD
    het_mad_runs = run_task(mock_task, "heterogeneous-MAD", client, n_agents=4, rounds=3)
    assert len(het_mad_runs) == 4
    assert all(r.config == "heterogeneous-MAD" for r in het_mad_runs)
    
    # Test verifier (FIX BUG 3: now returns 1, not n+1)
    verifier_runs = run_task(mock_task, "verifier", client, n_candidates=3)
    assert len(verifier_runs) == 1
    assert all(r.config == "verifier" for r in verifier_runs)
    
    # Test interpretation-diverse (FIX BUG 4: now returns len(interpretations))
    diverse_runs = run_task(mock_task, "interpretation-diverse", client)
    assert len(diverse_runs) == len(mock_task.interpretations)
    assert all(r.config == "interpretation-diverse" for r in diverse_runs)
    
    # Test unknown config
    with pytest.raises(ValueError, match="Unknown config"):
        run_task(mock_task, "unknown_config", client)


def test_mad_preserves_round_structure(mock_task, client):
    """Test that MAD runs the expected number of rounds."""
    # We can't directly observe rounds, but we can verify determinism
    # which requires rounds to execute identically
    n_agents = 3
    rounds = 4
    
    runs1 = run_mad(mock_task, client, homogeneous=True, n_agents=n_agents, rounds=rounds)
    runs2 = run_mad(mock_task, client, homogeneous=True, n_agents=n_agents, rounds=rounds)
    
    # If rounds weren't being run, outputs would be the same as rounds=1
    runs_1round = run_mad(mock_task, client, homogeneous=True, n_agents=n_agents, rounds=1)
    
    # Verify 4-round runs are deterministic
    for r1, r2 in zip(runs1, runs2):
        assert r1.output == r2.output
    
    # Verify 4-round seeds differ from 1-round seeds (due to round-based seed offset)
    seeds_4round = {r.seed for r in runs1}
    seeds_1round = {r.seed for r in runs_1round}
    assert seeds_4round != seeds_1round, "Different rounds should use different seeds"


def test_offline_no_network(mock_task, client):
    """Verify all configs work offline with no network."""
    # All these should succeed without network
    run_task(mock_task, "single", client)
    run_task(mock_task, "sc", client, k=5)
    run_task(mock_task, "homogeneous-MAD", client, n_agents=3, rounds=2)
    run_task(mock_task, "heterogeneous-MAD", client, n_agents=4, rounds=2)
    run_task(mock_task, "verifier", client, n_candidates=3)
    run_task(mock_task, "interpretation-diverse", client)
    
    # All succeeded without raising NotImplementedError or network errors
    assert True


def test_all_configs_leave_labels_empty(mock_task, client):
    """Verify no config pre-assigns labels (labeling is separate stage)."""
    configs_to_test = [
        ("single", {}),
        ("sc", {"k": 5}),
        ("homogeneous-MAD", {"n_agents": 3, "rounds": 2}),
        ("heterogeneous-MAD", {"n_agents": 4, "rounds": 2}),
        ("verifier", {"n_candidates": 3}),
        ("interpretation-diverse", {}),
    ]
    
    for config_name, kwargs in configs_to_test:
        runs = run_task(mock_task, config_name, client, **kwargs)
        assert all(r.label == "" for r in runs), \
            f"Config {config_name} must not pre-assign labels"


def test_identity_key_uniqueness_across_configs(mock_task, client):
    """Verify identity keys don't collide across different configs."""
    all_runs = []
    
    # Collect runs from all configs
    all_runs.extend(run_task(mock_task, "single", client))
    all_runs.extend(run_task(mock_task, "sc", client, k=3))
    all_runs.extend(run_task(mock_task, "homogeneous-MAD", client, n_agents=2, rounds=2))
    
    # Extract identity keys
    identity_keys = [
        (r.task_id, r.config, r.model_role, r.model_id, r.seed)
        for r in all_runs
    ]
    
    # Verify all unique (no collisions across configs)
    assert len(identity_keys) == len(set(identity_keys)), \
        "Identity keys must be unique across all configs"


def test_heterogeneous_mad_real_provenance(mock_task, client):
    """FIX BUG 1: Verify heterogeneous agents produce different outputs (real provenance).
    
    Before fix: all agents used the same homogeneous model, so outputs were identical.
    After fix: different models → different hash inputs → different outputs.
    """
    n_agents = 4
    runs = run_mad(mock_task, client, homogeneous=False, n_agents=n_agents, rounds=2)
    
    # Get the heterogeneous model pool
    het_pool = client.config["roles"]["tested_agents"]["heterogeneous"]
    
    # Verify each agent has the correct model assignment
    for i, run in enumerate(runs):
        expected_model = het_pool[i % len(het_pool)]["model"]
        assert run.model_id == expected_model, \
            f"Agent {i} should use model {expected_model}, got {run.model_id}"
    
    # Verify outputs are different (different models → different outputs)
    # If they were all using the same model (the bug), outputs would be identical
    outputs = [r.output for r in runs]
    unique_outputs = set(outputs)
    
    # At least 2 unique outputs (since we have 4 agents with different models)
    assert len(unique_outputs) >= 2, \
        "Heterogeneous agents must produce different outputs (different models)"
    
    # Verify this differs from homogeneous
    homo_runs = run_mad(mock_task, client, homogeneous=True, n_agents=n_agents, rounds=2)
    homo_outputs = {r.output for r in homo_runs}
    
    # Heterogeneous and homogeneous should produce different output sets
    assert outputs != [r.output for r in homo_runs], \
        "Heterogeneous vs homogeneous must yield different outputs"


def test_mad_round_snapshot_order_independent(mock_task, client):
    """FIX BUG 2: Verify MAD uses round r-1 snapshot (not order-dependent round r).
    
    Before fix: later agents saw earlier agents' current-round answers (order-dependent).
    After fix: all agents in round r condition on frozen round r-1 snapshot.
    """
    n_agents = 3
    rounds = 3
    
    # Run twice with identical params
    runs1 = run_mad(mock_task, client, homogeneous=True, n_agents=n_agents, rounds=rounds)
    runs2 = run_mad(mock_task, client, homogeneous=True, n_agents=n_agents, rounds=rounds)
    
    # Verify identical outputs (determinism ensures snapshot is used correctly)
    for r1, r2 in zip(runs1, runs2):
        assert r1.output == r2.output
        assert r1.seed == r2.seed
    
    # Indirectly verify snapshot: agents with same seed produce same output
    # (if they saw different conditioning info due to order, outputs would vary)
    # This is guaranteed by the fact that our mock is deterministic on (model, prompt, seed)


def test_mad_peer_answer_order_canonical(mock_task, client):
    """MAJOR FIX: Verify MAD peer-answer block is canonicalized (sorted by agent idx).
    
    The same set of round r-1 answers must produce the same round r output for a
    given agent, regardless of iteration order. Before fix: peer answers appeared
    in iteration order, so byte-for-byte hash changed with order → different outputs.
    After fix: peer answers sorted by agent idx → canonical prompt text → deterministic.
    """
    # This test is implicit in the determinism tests above, but we can verify
    # explicitly by checking that the implementation sorts the snapshot.
    # Since we can't directly manipulate agent iteration order in the public API,
    # we verify via determinism: identical calls → identical outputs.
    
    n_agents = 3
    rounds = 3
    
    # Multiple runs with identical params
    outputs_run1 = [r.output for r in run_mad(mock_task, client, homogeneous=True, n_agents=n_agents, rounds=rounds)]
    outputs_run2 = [r.output for r in run_mad(mock_task, client, homogeneous=True, n_agents=n_agents, rounds=rounds)]
    outputs_run3 = [r.output for r in run_mad(mock_task, client, homogeneous=True, n_agents=n_agents, rounds=rounds)]
    
    # All runs must produce identical outputs (canonical order guarantees this)
    assert outputs_run1 == outputs_run2 == outputs_run3, \
        "MAD must produce identical outputs across runs (peer answers canonically ordered)"


def test_verifier_output_is_candidate_answer(mock_task, client):
    """FIX BUG 3: Verify verifier output is the selected candidate's answer.
    
    Before fix: verifier output was raw "Candidate N" text.
    After fix: verifier output is the actual selected candidate's answer text.
    """
    runs = run_verifier(mock_task, client, n_candidates=3)
    
    assert len(runs) == 1
    verifier_run = runs[0]
    
    # Output must be an actual answer (starts with MOCK_OUTPUT_), not selection text
    assert verifier_run.output.startswith("MOCK_OUTPUT_"), \
        "Verifier output must be the selected candidate's answer, not 'Candidate N'"
    
    # Verify it doesn't contain the selection phrase
    assert not verifier_run.output.lower().startswith("candidate "), \
        "Verifier output should be the answer text, not the selection directive"


def test_interpretation_diverse_uses_task_interpretations(mock_task, client):
    """FIX BUG 4: Verify interpretation-diverse binds to task interpretations.
    
    Before fix: used 5 fixed generic hints, ignoring task.interpretations.
    After fix: creates one agent per task interpretation.
    """
    runs = run_diverse(mock_task, client)
    
    # Count must match task.interpretations
    assert len(runs) == len(mock_task.interpretations), \
        "interpretation-diverse must create one run per task interpretation"
    
    # With a different task (different interpretation count), get different count
    task2 = Task(
        id="task2",
        domain="code_spec",
        prompt="Another task",
        latent_spec="spec",
        interpretations=[
            Interpretation(id="I0", is_target=True, gold_check="g0"),
            Interpretation(id="I1", is_target=False, gold_check="g1"),
        ],
        ambiguity_level=1,
        key_questions=[]
    )
    
    runs2 = run_diverse(task2, client)
    assert len(runs2) == len(task2.interpretations)
    assert len(runs2) != len(runs), \
        "Different tasks with different interpretation counts should yield different run counts"


# ═══════════════════════════════════════════════════════════════════════════════
# S2e: Answer-format instruction tests
# ═══════════════════════════════════════════════════════════════════════════════

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def policy_task():
    """policy_qa domain task for format-instruction tests."""
    return Task(
        id="policy_test_001",
        domain="policy_qa",
        prompt="What is the maximum insurance payout under clause 3B?",
        latent_spec="Policy spec for clause 3B...",
        interpretations=[
            Interpretation(id="I0", is_target=True, gold_check="amount_i0"),
            Interpretation(id="I1", is_target=False, gold_check="amount_i1"),
        ],
        ambiguity_level=1,
        key_questions=["Which sub-clause applies?"]
    )


@pytest.fixture
def data_task():
    """data_analysis domain task for format-instruction tests."""
    return Task(
        id="data_test_001",
        domain="data_analysis",
        prompt="Write Python code to compute the mean of a dataset.",
        latent_spec="Data analysis spec...",
        interpretations=[
            Interpretation(id="I0", is_target=True, gold_check="mean_i0"),
            Interpretation(id="I1", is_target=False, gold_check="mean_i1"),
        ],
        ambiguity_level=1,
        key_questions=["Which mean formula applies?"]
    )


def _capture_prompts(client):
    """Monkey-patch client.complete to capture all prompt strings.

    Returns a list that accumulates every prompt argument passed to complete()
    for the duration of the test. The underlying real .complete() is still
    invoked so shape/determinism tests remain valid.
    """
    captured = []
    original = client.complete

    def capturing(role, prompt, seed=None, **kwargs):
        captured.append(prompt)
        return original(role, prompt, seed=seed, **kwargs)

    client.complete = capturing
    return captured


# ── Direct helper tests ───────────────────────────────────────────────────────

def test_answer_format_instruction_policy_qa():
    """policy_qa instruction must contain FINAL ANSWER: marker and JSON amount key."""
    inst = answer_format_instruction("policy_qa")
    assert "FINAL ANSWER:" in inst, "policy_qa instruction must contain 'FINAL ANSWER:'"
    assert '"amount":' in inst, 'policy_qa instruction must contain \'"amount":\' for JSON path'


def test_answer_format_instruction_code_spec():
    """code_spec instruction must contain ```python fence directive."""
    inst = answer_format_instruction("code_spec")
    assert "```python" in inst, "code_spec instruction must contain '```python' fence directive"


def test_answer_format_instruction_data_analysis():
    """data_analysis instruction must contain ```python fence directive."""
    inst = answer_format_instruction("data_analysis")
    assert "```python" in inst, "data_analysis instruction must contain '```python' fence directive"


def test_answer_format_instruction_unknown_domain_no_crash():
    """Unknown domain must return a non-empty string fallback (never crash)."""
    inst = answer_format_instruction("unknown_weird_domain_xyz")
    assert isinstance(inst, str) and len(inst) > 0, \
        "Unknown domain must return non-empty fallback string"


# ── All 6 configs × policy_qa ─────────────────────────────────────────────────

@pytest.mark.parametrize("config,kwargs", [
    ("single", {}),
    ("sc", {"k": 2}),
    ("homogeneous-MAD", {"n_agents": 2, "rounds": 2}),
    ("heterogeneous-MAD", {"n_agents": 2, "rounds": 2}),
    ("verifier", {"n_candidates": 2}),
    ("interpretation-diverse", {}),
])
def test_all_configs_policy_qa_prompts_contain_final_answer(policy_task, client, config, kwargs):
    """Every prompt emitted by every config for policy_qa must contain 'FINAL ANSWER:'."""
    captured = _capture_prompts(client)
    run_task(policy_task, config, client, **kwargs)
    assert len(captured) > 0, f"Config {config} emitted no prompts"
    for prompt in captured:
        assert "FINAL ANSWER:" in prompt, (
            f"Config '{config}' prompt missing 'FINAL ANSWER:' instruction "
            f"for policy_qa domain.\nPrompt start: {prompt[:200]}"
        )


# ── All 6 configs × code_spec ─────────────────────────────────────────────────

@pytest.mark.parametrize("config,kwargs", [
    ("single", {}),
    ("sc", {"k": 2}),
    ("homogeneous-MAD", {"n_agents": 2, "rounds": 2}),
    ("heterogeneous-MAD", {"n_agents": 2, "rounds": 2}),
    ("verifier", {"n_candidates": 2}),
    ("interpretation-diverse", {}),
])
def test_all_configs_code_spec_prompts_contain_python_fence(mock_task, client, config, kwargs):
    """Every prompt emitted by every config for code_spec must contain '```python'."""
    captured = _capture_prompts(client)
    run_task(mock_task, config, client, **kwargs)
    assert len(captured) > 0, f"Config {config} emitted no prompts"
    for prompt in captured:
        assert "```python" in prompt, (
            f"Config '{config}' prompt missing '```python' fence instruction "
            f"for code_spec domain.\nPrompt start: {prompt[:200]}"
        )


# ── All 6 configs × data_analysis ────────────────────────────────────────────

@pytest.mark.parametrize("config,kwargs", [
    ("single", {}),
    ("sc", {"k": 2}),
    ("homogeneous-MAD", {"n_agents": 2, "rounds": 2}),
    ("heterogeneous-MAD", {"n_agents": 2, "rounds": 2}),
    ("verifier", {"n_candidates": 2}),
    ("interpretation-diverse", {}),
])
def test_all_configs_data_analysis_prompts_contain_python_fence(data_task, client, config, kwargs):
    """Every prompt emitted by every config for data_analysis must contain '```python'."""
    captured = _capture_prompts(client)
    run_task(data_task, config, client, **kwargs)
    assert len(captured) > 0, f"Config {config} emitted no prompts"
    for prompt in captured:
        assert "```python" in prompt, (
            f"Config '{config}' prompt missing '```python' fence instruction "
            f"for data_analysis domain.\nPrompt start: {prompt[:200]}"
        )


# ── MAD both phases (initial round AND subsequent rounds) ─────────────────────

def test_mad_initial_round_prompt_contains_format_instruction(policy_task, client):
    """MAD initial-round prompts (round 0) must contain the format instruction."""
    captured = _capture_prompts(client)
    run_mad(policy_task, client, homogeneous=True, n_agents=2, rounds=2)

    # Initial round prompts don't contain "Previous round answers"
    initial_prompts = [p for p in captured if "Previous round answers from all agents" not in p]
    assert initial_prompts, "Should have at least one initial-round MAD prompt"
    for p in initial_prompts:
        assert "FINAL ANSWER:" in p, \
            f"MAD initial-round prompt missing format instruction.\nPrompt: {p[:300]}"


def test_mad_subsequent_round_prompt_contains_format_instruction(policy_task, client):
    """MAD subsequent-round prompts (round > 0) must contain the format instruction."""
    captured = _capture_prompts(client)
    run_mad(policy_task, client, homogeneous=True, n_agents=2, rounds=2)

    # Subsequent round prompts contain "Previous round answers"
    round_prompts = [p for p in captured if "Previous round answers from all agents" in p]
    assert round_prompts, "Should have at least one subsequent-round MAD prompt"
    for p in round_prompts:
        assert "FINAL ANSWER:" in p, \
            f"MAD round prompt missing format instruction.\nPrompt: {p[:300]}"


# ── Verifier both phases (candidate generation AND selection) ─────────────────

def test_verifier_candidate_prompt_contains_format_instruction(policy_task, client):
    """Verifier candidate-generation prompts must contain the format instruction."""
    captured = _capture_prompts(client)
    run_verifier(policy_task, client, n_candidates=2)

    # Candidate prompts don't contain "As a verifier"
    candidate_prompts = [p for p in captured if "As a verifier" not in p]
    assert candidate_prompts, "Should have candidate generation prompts"
    for p in candidate_prompts:
        assert "FINAL ANSWER:" in p, \
            f"Verifier candidate prompt missing format instruction.\nPrompt: {p[:300]}"


def test_verifier_select_prompt_contains_format_instruction(policy_task, client):
    """Verifier selection prompt must contain the format instruction."""
    captured = _capture_prompts(client)
    run_verifier(policy_task, client, n_candidates=2)

    # Selection prompt contains "As a verifier"
    select_prompts = [p for p in captured if "As a verifier" in p]
    assert select_prompts, "Should have a verifier selection prompt"
    for p in select_prompts:
        assert "FINAL ANSWER:" in p, \
            f"Verifier selection prompt missing format instruction.\nPrompt: {p[:300]}"


# ═══════════════════════════════════════════════════════════════════════════════
# Fix 1 — Temperature threading tests (offline; no network)
# ═══════════════════════════════════════════════════════════════════════════════

def _capture_temperature(client):
    """Monkey-patch client.complete to capture all temperature kwargs.

    Returns a list of temperature values (including None) passed to each
    complete() call.  The real .complete() is still invoked so all existing
    shape/determinism invariants remain valid.
    """
    temps: list = []
    original = client.complete

    def capturing(role, prompt, seed=None, temperature=None, **kwargs):
        temps.append(temperature)
        return original(role, prompt, seed=seed, temperature=temperature, **kwargs)

    client.complete = capturing
    return temps


def test_single_config_passes_temperature_zero(mock_task, client):
    """run_single must pass temperature=0.0 (deterministic) to client.complete."""
    temps = _capture_temperature(client)
    run_single(mock_task, client)
    assert temps, "run_single must call client.complete at least once"
    assert all(t == 0.0 for t in temps), (
        f"run_single must use temperature=0.0 for determinism, got {temps}"
    )


@pytest.mark.parametrize("config,kwargs", [
    ("sc", {"k": 3}),
    ("homogeneous-MAD", {"n_agents": 2, "rounds": 2}),
    ("heterogeneous-MAD", {"n_agents": 2, "rounds": 2}),
    ("verifier", {"n_candidates": 2}),
    ("interpretation-diverse", {}),
])
def test_sampling_configs_default_temperature_is_0_7(mock_task, client, config, kwargs):
    """Sampling configs must default to temperature=0.7 for ensemble diversity."""
    temps = _capture_temperature(client)
    run_task(mock_task, config, client, **kwargs)
    assert temps, f"Config {config} must call client.complete at least once"
    assert all(t == 0.7 for t in temps), (
        f"Config '{config}' must default to temperature=0.7, got {temps}"
    )


def test_temperature_override_in_run_task_single(mock_task, client):
    """Passing temperature= via run_task kwargs overrides run_single default."""
    temps = _capture_temperature(client)
    run_task(mock_task, "single", client, temperature=0.3)
    assert all(t == 0.3 for t in temps), (
        f"temperature kwarg override must propagate through run_task, got {temps}"
    )


@pytest.mark.parametrize("override_temp", [0.0, 0.3, 1.0])
def test_temperature_override_propagates_to_all_sampling_configs(
    mock_task, client, override_temp
):
    """Ablation sweep: temperature override propagates to every sampling config."""
    for config, kwargs in [
        ("sc", {"k": 2}),
        ("homogeneous-MAD", {"n_agents": 2, "rounds": 1}),
        ("interpretation-diverse", {}),
    ]:
        temps = _capture_temperature(client)
        run_task(mock_task, config, client, temperature=override_temp, **kwargs)
        assert all(t == override_temp for t in temps), (
            f"Config '{config}': override temperature {override_temp} must reach "
            f"all complete() calls, got {temps}"
        )


def test_single_determinism_preserved_with_temperature_zero(mock_task, client):
    """run_single with temperature=0.0 must still be fully deterministic."""
    run1 = run_single(mock_task, client)
    run2 = run_single(mock_task, client)
    assert run1.output == run2.output, "run_single must remain deterministic with temperature=0.0"
    assert run1.seed == run2.seed


def test_different_temperatures_produce_different_offline_outputs(mock_task, client):
    """Offline mock must produce different outputs for different temperatures.

    This validates that temperature is folded into the mock hash, making the
    offline mode temperature-aware even without a real API.
    """
    runs_low = run_self_consistency(mock_task, client, k=2, temperature=0.0)
    runs_high = run_self_consistency(mock_task, client, k=2, temperature=1.0)
    # All outputs at temp=0.0 vs temp=1.0 should differ (different hash inputs)
    outputs_low = {r.output for r in runs_low}
    outputs_high = {r.output for r in runs_high}
    assert outputs_low != outputs_high, (
        "Different temperatures must produce different offline mock outputs "
        "(temperature is not folded into the hash)"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# _FamilyClient compatibility — regression guard for MAJOR (scripts/mini_pilot.py)
#
# The _FamilyClient wrapper in scripts/mini_pilot.py overrides complete() to
# inject explicit family/model. After the temperature threading fix, run_*
# functions forward temperature= to complete(). If _FamilyClient.complete()
# doesn't accept temperature, every run_* call raises TypeError before any HTTP.
# These tests reproduce the _FamilyClient pattern inline (offline; no network).
# ═══════════════════════════════════════════════════════════════════════════════

from common.llm import LLMClient as _LLMClientBase


def _make_family_client(cfg, fam: str, slug: str, tmp_path):
    """Reproduce the _FamilyClient wrapper exactly as written in mini_pilot.py."""

    class _FamilyClient(_LLMClientBase):
        _family: str = fam
        _slug: str = slug

        def complete(self, role, prompt, seed=None, max_retries=3,
                     family=None, model=None, temperature=None):
            return super().complete(
                role=role,
                prompt=prompt,
                seed=seed,
                max_retries=max_retries,
                family=self._family,
                model=self._slug,
                temperature=temperature,
            )

    return _FamilyClient(cfg, cache_dir=str(tmp_path / "fam_cache"), offline=True)


def test_family_client_run_single_no_typeerror(mock_task, tmp_path):
    """_FamilyClient must not raise TypeError when run_single forwards temperature."""
    from common.config import load_config
    cfg = load_config()
    fc = _make_family_client(cfg, fam="openai", slug="openai/gpt-4o-mini", tmp_path=tmp_path)
    # run_single passes temperature=0.0 — must reach _FamilyClient.complete without TypeError
    result = run_single(mock_task, fc)
    assert result is not None
    assert result.config == "single"


def test_family_client_run_sc_no_typeerror(mock_task, tmp_path):
    """_FamilyClient must not raise TypeError when run_self_consistency forwards temperature."""
    from common.config import load_config
    cfg = load_config()
    fc = _make_family_client(cfg, fam="meta", slug="meta/llama-3.3-70b-instruct", tmp_path=tmp_path)
    # run_self_consistency passes temperature=0.7 — must reach _FamilyClient.complete
    runs = run_self_consistency(mock_task, fc, k=3)
    assert len(runs) == 3
    assert all(r.config == "sc" for r in runs)


def test_family_client_temperature_override_no_typeerror(mock_task, tmp_path):
    """Explicit temperature override via run_task must also reach _FamilyClient without TypeError."""
    from common.config import load_config
    cfg = load_config()
    fc = _make_family_client(cfg, fam="openai", slug="openai/gpt-4o-mini", tmp_path=tmp_path)
    # Ablation-style override: temperature passed through run_task → run_single
    runs = run_task(mock_task, "single", fc, temperature=0.3)
    assert len(runs) == 1
    runs_sc = run_task(mock_task, "sc", fc, k=2, temperature=0.0)
    assert len(runs_sc) == 2


def test_family_client_preserves_family_model_override(mock_task, tmp_path):
    """_FamilyClient family/model override behavior must be intact after the fix."""
    from common.config import load_config
    cfg = load_config()
    slug = "openai/gpt-4o-mini"
    fc = _make_family_client(cfg, fam="openai", slug=slug, tmp_path=tmp_path)
    run = run_single(mock_task, fc)
    # The wrapper forces model=slug regardless of role routing
    assert run.model_id == slug, (
        f"_FamilyClient must override model_id to {slug!r}, got {run.model_id!r}"
    )
