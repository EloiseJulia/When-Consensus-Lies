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
    run_diverse
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
    
    # Verify count (n_candidates + 1 verifier)
    assert len(runs) == n_candidates + 1
    assert all(isinstance(r, AgentRun) for r in runs)
    
    # Verify fields
    assert all(r.task_id == mock_task.id for r in runs)
    assert all(r.config == "verifier" for r in runs)
    assert all(r.model_role == "tested_agents" for r in runs)
    assert all(r.label == "" for r in runs)
    
    # Verify unique seeds
    seeds = [r.seed for r in runs]
    assert len(set(seeds)) == n_candidates + 1, "Seeds must be unique"
    
    # Verify identity keys are unique
    identity_keys = [
        (r.task_id, r.config, r.model_role, r.model_id, r.seed)
        for r in runs
    ]
    assert len(set(identity_keys)) == n_candidates + 1, "Identity keys must be unique"
    
    # Verify determinism
    runs2 = run_verifier(mock_task, client, n_candidates=n_candidates)
    for r1, r2 in zip(runs, runs2):
        assert r1.output == r2.output
        assert r1.seed == r2.seed


def test_interpretation_diverse_config(mock_task, client):
    """Test interpretation-diverse config."""
    runs = run_diverse(mock_task, client)
    
    # Verify count (5 diverse hints)
    assert len(runs) == 5
    assert all(isinstance(r, AgentRun) for r in runs)
    
    # Verify fields
    assert all(r.task_id == mock_task.id for r in runs)
    assert all(r.config == "interpretation-diverse" for r in runs)
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
    
    # Test verifier
    verifier_runs = run_task(mock_task, "verifier", client, n_candidates=3)
    assert len(verifier_runs) == 4  # 3 candidates + 1 verifier
    assert all(r.config == "verifier" for r in verifier_runs)
    
    # Test interpretation-diverse
    diverse_runs = run_task(mock_task, "interpretation-diverse", client)
    assert len(diverse_runs) == 5
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
