"""Test basic imports."""


def test_import_common():
    """Test common package imports."""
    import common
    from common.schema import Interpretation, Task, AgentRun
    from common.config import load_config, model_for_role, assert_provenance_separation
    from common.llm import LLMClient
    
    assert common.__version__


def test_import_bench():
    """Test bench package imports."""
    import bench
    from bench.build import generate_ambiguous_task, generate_gold_checker
    
    assert bench.__version__


def test_import_harness():
    """Test harness package imports."""
    import harness
    from harness.metrics import false_consensus_rate, convergent_delusion, marginal_rho, a_maj, ece
    from harness.run import run_task
    from harness.label import label_run
    
    assert harness.__version__


def test_import_detector():
    """Test detector package imports."""
    import detector
    from detector.surface import surface_latent_assumptions, compute_divergence_score
    
    assert detector.__version__


def test_import_sim_users():
    """Test sim_users package imports."""
    import sim_users
    from sim_users.study import run_simulated_study, inject_automation_bias
    
    assert sim_users.__version__


def test_import_analysis():
    """Test analysis package imports."""
    import analysis
    from analysis.stats import fit_mixed_effects_model, bootstrap_confidence_intervals
    
    assert analysis.__version__
