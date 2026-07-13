"""Configuration loader and provenance separation enforcement."""

import yaml
from pathlib import Path
from typing import Dict, Any


def load_config() -> Dict[str, Any]:
    """Load config.yaml from the common/ directory."""
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def model_for_role(role: str, config: Dict[str, Any] = None) -> Dict[str, str]:
    """Resolve model info for a given role.
    
    Args:
        role: One of 'constructor', 'judge', 'code_reviewer', or 'tested_agents'
        config: Optional pre-loaded config dict
    
    Returns:
        Dict with 'family' and 'model' keys
    """
    if config is None:
        config = load_config()
    
    role_config = config["roles"].get(role)
    if not role_config:
        raise ValueError(f"Unknown role: {role}")
    
    # For tested_agents, return the first homogeneous model by default
    if role == "tested_agents":
        return role_config["homogeneous"][0]
    
    return {"family": role_config["family"], "model": role_config["model"]}


def assert_provenance_separation(config: Dict[str, Any] = None) -> None:
    """Assert that constructor/tested/judge/code_reviewer use distinct families.
    
    HARD LAW 6: provenance separation is inviolable.
    
    Raises:
        AssertionError: If any two critical roles share a model family
    """
    if config is None:
        config = load_config()
    
    # Extract families
    constructor_family = config["roles"]["constructor"]["family"]
    judge_family = config["roles"]["judge"]["family"]
    code_reviewer_family = config["roles"]["code_reviewer"]["family"]
    
    # Tested agents: extract all families from all groups
    tested = config["roles"]["tested_agents"]
    tested_families = set()
    for group in ["homogeneous", "heterogeneous", "reasoning"]:
        for model_info in tested.get(group, []):
            tested_families.add(model_info["family"])
    
    # Check pairwise distinctness for critical roles
    critical_roles = {
        "constructor": constructor_family,
        "judge": judge_family,
        "code_reviewer": code_reviewer_family,
    }
    
    # Constructor vs judge vs code_reviewer must be mutually distinct
    families = list(critical_roles.values())
    if len(families) != len(set(families)):
        raise AssertionError(
            f"Provenance separation violated: constructor/judge/code_reviewer must use "
            f"distinct families. Got: {critical_roles}"
        )
    
    # Tested agents should not overlap with constructor (strict separation)
    if constructor_family in tested_families:
        raise AssertionError(
            f"Provenance separation violated: constructor family '{constructor_family}' "
            f"appears in tested_agents"
        )
