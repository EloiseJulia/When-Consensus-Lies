"""Test end-to-end smoke pipeline with mock task."""

from common.schema import Interpretation, Task, AgentRun
from common.config import load_config
from common.llm import LLMClient
from harness.run import run_task
from harness.label import label_run
from harness.metrics import false_consensus_rate


def test_smoke_pipeline():
    """End-to-end: mock Task → run → label → metrics, NO network."""
    
    # Build a mock task
    task = Task(
        id="smoke_test_001",
        domain="code_spec",
        prompt="Write a function to process data.",
        latent_spec="Full spec with all requirements...",
        interpretations=[
            Interpretation(id="I0", is_target=True, gold_check="test_gold_i0"),
            Interpretation(id="I1", is_target=False, gold_check="test_gold_i1"),
            Interpretation(id="I2", is_target=False, gold_check="test_gold_i2"),
        ],
        ambiguity_level=2,
        key_questions=["How should edge cases be handled?"]
    )
    
    # Initialize offline client
    config = load_config()
    client = LLMClient(config, offline=True)
    
    # Run task with sc config (k=5 samples)
    runs = run_task(task, config="sc", client=client, k=5)
    
    # Verify runs were generated
    assert len(runs) == 5
    assert all(isinstance(run, AgentRun) for run in runs)
    assert all(run.task_id == task.id for run in runs)

    # run_task must NOT pre-assign labels: labeling is a separate pipeline stage.
    assert all(run.label == "" for run in runs)

    # Identity dimensions must be distinct per run (seed differentiates them).
    assert len({run.seed for run in runs}) == 5
    
    # Label runs (mock deterministic)
    labels = [label_run(run, task) for run in runs]
    
    # Verify labels are valid
    valid_labels = {interp.id for interp in task.interpretations}
    assert all(label in valid_labels for label in labels)
    
    # Compute convergent_delusion
    result = false_consensus_rate(labels, target="I0")
    
    # Verify it's a valid probability
    assert 0.0 <= result <= 1.0
    assert isinstance(result, float)
    
    print(f"Smoke test passed: generated {len(runs)} runs, "
          f"labels={labels}, convergent_delusion={result:.2f}")


def test_offline_mode_no_network():
    """Verify LLMClient works with no API key or network."""
    config = load_config()
    client = LLMClient(config, offline=True)
    
    # Make a completion (should work offline)
    completion = client.complete(
        role="tested_agents",
        prompt="test prompt",
        seed=42
    )
    
    assert completion.text.startswith("MOCK_OUTPUT_")
    assert completion.cost_usd == 0.0
    assert completion.model  # Should have a model name
    
    # Verify determinism: same inputs → same output
    completion2 = client.complete(
        role="tested_agents",
        prompt="test prompt",
        seed=42
    )
    
    assert completion.text == completion2.text
