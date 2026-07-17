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
    """Assert provenance separation (HARD LAW 6).

    Enforced invariants (the ones that actually protect the science):
      1. constructor ∉ all tested_agents families (including the new ``weak`` group).
         This is the CRITICAL scientific constraint: the constructor must not share a
         family with any agent under test, so the benchmark cannot have inherent bias
         toward any tested family (R2 construction control).
      2. judge ∉ all tested_agents families (including ``weak``). Protects labeling
         integrity: the LLM judge must not share a family with any tested agent so its
         labels cannot reflect that family's inherent bias.

    Intentional NON-constraints (documented to prevent re-flagging by future audits):
      * constructor and judge MAY share the same family (e.g., both microsoft for the
        Amendment-06 frontier roster). Both are outside the tested pool, so the scientific
        constraint is fully satisfied. Pairwise distinctness between meta roles is NOT
        required for experimental validity.
      * code_reviewer MAY share a family with the homogeneous tested pool. The code
        reviewer performs CODE-AUDIT routing, which is orthogonal to the experiment's
        provenance requirements. Per-item family separation is enforced at run time
        (Phase 2): a reviewer never reviews output produced by its own family on that
        item.
      * The HETEROGENEOUS tested pool is deliberately broad (spans many families) to
        model real heterogeneous multi-agent systems. Meta roles are allowed to share a
        family with the heterogeneous pool, subject to the run-time separation above.

    Raises:
        AssertionError: if constructor or judge appears in the tested_agents families.
    """
    if config is None:
        config = load_config()

    constructor_family = config["roles"]["constructor"]["family"]
    judge_family = config["roles"]["judge"]["family"]

    tested = config["roles"]["tested_agents"]

    def _families(group: str) -> set:
        return {m["family"] for m in tested.get(group, [])}

    # Collect all tested families across ALL sub-roles (including new ``weak`` group).
    all_tested_families: set = set()
    for group in ["homogeneous", "heterogeneous", "reasoning", "weak"]:
        all_tested_families |= _families(group)

    # (1) constructor ∉ tested families
    if constructor_family in all_tested_families:
        raise AssertionError(
            f"Provenance separation violated: constructor family "
            f"'{constructor_family}' appears in tested_agents "
            f"{sorted(all_tested_families)}"
        )

    # (2) judge ∉ tested families
    if judge_family in all_tested_families:
        raise AssertionError(
            f"Provenance separation violated: judge family "
            f"'{judge_family}' appears in tested_agents "
            f"{sorted(all_tested_families)}"
        )
