"""Mixed-effects models and statistical tests.

Phase 6: Analyze convergent-delusion vs ambiguity, heterogeneity effects.
"""


def fit_mixed_effects_model(data, formula) -> dict:
    """Fit mixed-effects logistic regression.
    
    [PHASE 6]
    
    Args:
        data: DataFrame with task, config, model, outcome
        formula: Model formula (e.g., "delusion ~ ambiguity + (1|task)")
    
    Returns:
        Dict with 'coefficients', 'p_values', 'confidence_intervals'
    """
    raise NotImplementedError("Phase 6: mixed-effects modeling")


def bootstrap_confidence_intervals(metric_fn, data, n_bootstrap=1000) -> tuple:
    """Compute bootstrap CIs for a metric.
    
    [PHASE 6]
    """
    raise NotImplementedError("Phase 6: bootstrap confidence intervals")
