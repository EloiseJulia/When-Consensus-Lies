"""Test provenance separation (HARD LAW 6)."""

from common.config import load_config, assert_provenance_separation
import pytest


def test_provenance_separation_passes():
    """Verify current config has distinct families for critical roles."""
    config = load_config()
    
    # Should not raise
    assert_provenance_separation(config)
    
    # Manually verify key separations
    constructor_family = config["roles"]["constructor"]["family"]
    judge_family = config["roles"]["judge"]["family"]
    code_reviewer_family = config["roles"]["code_reviewer"]["family"]
    
    assert constructor_family != judge_family
    assert constructor_family != code_reviewer_family
    assert judge_family != code_reviewer_family


def test_provenance_separation_fails_on_duplicate():
    """Verify assert_provenance_separation raises on same-family config."""
    
    # Create a config with constructor = judge (violation)
    bad_config = {
        "roles": {
            "constructor": {"family": "openai", "model": "gpt-4"},
            "judge": {"family": "openai", "model": "gpt-4"},  # SAME as constructor
            "code_reviewer": {"family": "anthropic", "model": "claude"},
            "tested_agents": {
                "homogeneous": [{"family": "anthropic", "model": "claude"}],
                "heterogeneous": [],
                "reasoning": []
            }
        },
        "seeds": {"global": 123}
    }
    
    with pytest.raises(AssertionError, match="Provenance separation violated"):
        assert_provenance_separation(bad_config)


def test_constructor_not_in_tested_agents():
    """Verify constructor family doesn't appear in tested_agents."""
    config = load_config()
    
    constructor_family = config["roles"]["constructor"]["family"]
    
    # Extract all tested_agents families
    tested = config["roles"]["tested_agents"]
    tested_families = set()
    for group in ["homogeneous", "heterogeneous", "reasoning"]:
        for model_info in tested.get(group, []):
            tested_families.add(model_info["family"])
    
    assert constructor_family not in tested_families, (
        f"Constructor family '{constructor_family}' must not appear in tested_agents"
    )
