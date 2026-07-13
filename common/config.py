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
      1. constructor / judge / code_reviewer use pairwise-distinct families
         (the three "meta" roles must never collapse into one family).
      2. None of constructor / judge / code_reviewer shares a family with the
         HOMOGENEOUS tested pool. The homogeneous pool is the shared-prior ρ
         baseline; if a meta role shared its family it could inherit the same
         blind spot and turn ρ / labels / reviews into an artifact.
      3. constructor does not appear anywhere in tested_agents at all (it must
         not have authored the priors of any subject it constructs tasks for).

    Intentional NON-constraint (documented so future audits don't re-flag it):
      The HETEROGENEOUS tested pool is deliberately broad (spans many families)
      to model real heterogeneous multi-agent systems. judge / code_reviewer are
      allowed to share a family with the heterogeneous pool because per-item
      separation is enforced at RUN TIME (Phase 2): a judge never scores, and a
      reviewer never reviews, an output produced by its own family on that item.

    Raises:
        AssertionError: if any enforced invariant above is violated.
    """
    if config is None:
        config = load_config()

    constructor_family = config["roles"]["constructor"]["family"]
    judge_family = config["roles"]["judge"]["family"]
    code_reviewer_family = config["roles"]["code_reviewer"]["family"]

    tested = config["roles"]["tested_agents"]

    def _families(group: str) -> set:
        return {m["family"] for m in tested.get(group, [])}

    homogeneous_families = _families("homogeneous")
    all_tested_families = set()
    for group in ["homogeneous", "heterogeneous", "reasoning"]:
        all_tested_families |= _families(group)

    meta_roles = {
        "constructor": constructor_family,
        "judge": judge_family,
        "code_reviewer": code_reviewer_family,
    }

    # (1) meta roles pairwise-distinct
    families = list(meta_roles.values())
    if len(families) != len(set(families)):
        raise AssertionError(
            "Provenance separation violated: constructor/judge/code_reviewer must "
            f"use distinct families. Got: {meta_roles}"
        )

    # (2) no meta role shares the shared-prior (homogeneous) baseline family
    for role, fam in meta_roles.items():
        if fam in homogeneous_families:
            raise AssertionError(
                f"Provenance separation violated: {role} family '{fam}' overlaps the "
                f"homogeneous shared-prior tested pool {sorted(homogeneous_families)}"
            )

    # (3) constructor must not appear anywhere in tested_agents
    if constructor_family in all_tested_families:
        raise AssertionError(
            f"Provenance separation violated: constructor family "
            f"'{constructor_family}' appears in tested_agents"
        )
