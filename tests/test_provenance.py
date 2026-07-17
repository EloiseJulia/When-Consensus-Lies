"""Test provenance separation (HARD LAW 6).

Amendment-06 frontier roster notes:
  - constructor and judge are both 'microsoft' (mai-code-1-flash-picker). This is
    intentionally allowed: both are outside the tested pool {openai, anthropic, google},
    so the critical scientific constraint is satisfied. Pairwise-distinctness of meta
    roles is NOT required — see common/config.py assert_provenance_separation docstring.
  - code_reviewer is 'openai' (gpt-5.6-sol), which shares a family with the homogeneous
    tested pool. This is also intentionally allowed for code-audit purposes.

The enforced constraints (see common/config.py) are:
  1. constructor ∉ all tested_agents families (including weak).
  2. judge ∉ all tested_agents families (including weak).
"""

from common.config import load_config, assert_provenance_separation
import pytest


def test_provenance_separation_passes():
    """Verify current config passes the enforced Hard Law 6 constraints."""
    config = load_config()

    # Should not raise under the Amendment-06 config.
    assert_provenance_separation(config)

    # Manually verify: constructor and judge are both 'microsoft' — allowed.
    constructor_family = config["roles"]["constructor"]["family"]
    judge_family = config["roles"]["judge"]["family"]
    assert constructor_family == "microsoft"
    assert judge_family == "microsoft"

    # Critical constraint: neither constructor nor judge is in the tested pool.
    tested = config["roles"]["tested_agents"]
    tested_families = set()
    for group in ["homogeneous", "heterogeneous", "reasoning", "weak"]:
        for m in tested.get(group, []):
            tested_families.add(m["family"])
    assert constructor_family not in tested_families, (
        f"Constructor family '{constructor_family}' must not appear in tested_agents"
    )
    assert judge_family not in tested_families, (
        f"Judge family '{judge_family}' must not appear in tested_agents"
    )


def test_provenance_separation_fails_when_constructor_in_tested():
    """assert_provenance_separation raises when constructor is in the tested pool."""
    bad_config = {
        "roles": {
            "constructor": {"family": "openai", "model": "gpt-4"},
            "judge": {"family": "microsoft", "model": "phi"},
            "code_reviewer": {"family": "anthropic", "model": "claude"},
            "tested_agents": {
                "homogeneous": [{"family": "openai", "model": "gpt-4o-mini"}],
                "heterogeneous": [],
                "reasoning": [],
                "weak": [],
            },
        },
        "seeds": {"global": 123},
    }
    with pytest.raises(AssertionError, match="Provenance separation violated"):
        assert_provenance_separation(bad_config)


def test_provenance_separation_fails_when_judge_in_tested():
    """assert_provenance_separation raises when judge is in the tested pool."""
    bad_config = {
        "roles": {
            "constructor": {"family": "microsoft", "model": "phi"},
            "judge": {"family": "anthropic", "model": "claude"},
            "code_reviewer": {"family": "google", "model": "gemini"},
            "tested_agents": {
                "homogeneous": [],
                "heterogeneous": [],
                "reasoning": [],
                "weak": [{"family": "anthropic", "model": "claude-haiku"}],
            },
        },
        "seeds": {"global": 123},
    }
    with pytest.raises(AssertionError, match="Provenance separation violated"):
        assert_provenance_separation(bad_config)


def test_provenance_separation_allows_constructor_equals_judge():
    """constructor == judge family is allowed when both are outside the tested pool."""
    # Amendment-06 pattern: both microsoft, tested is {openai, anthropic, google}.
    ok_config = {
        "roles": {
            "constructor": {"family": "microsoft", "model": "phi"},
            "judge": {"family": "microsoft", "model": "phi"},
            "code_reviewer": {"family": "openai", "model": "gpt-4"},
            "tested_agents": {
                "homogeneous": [{"family": "openai", "model": "gpt-4o-mini"}],
                "heterogeneous": [{"family": "anthropic", "model": "claude"}],
                "reasoning": [{"family": "google", "model": "gemini"}],
                "weak": [{"family": "openai", "model": "gpt-mini"}],
            },
        },
        "seeds": {"global": 123},
    }
    # Should NOT raise.
    assert_provenance_separation(ok_config)


def test_constructor_not_in_tested_agents():
    """Verify constructor family doesn't appear in any tested_agents group."""
    config = load_config()

    constructor_family = config["roles"]["constructor"]["family"]

    # Check ALL groups including new 'weak' sub-role.
    tested = config["roles"]["tested_agents"]
    tested_families = set()
    for group in ["homogeneous", "heterogeneous", "reasoning", "weak"]:
        for model_info in tested.get(group, []):
            tested_families.add(model_info["family"])

    assert constructor_family not in tested_families, (
        f"Constructor family '{constructor_family}' must not appear in tested_agents"
    )


def test_judge_not_in_tested_agents():
    """Verify judge family doesn't appear in any tested_agents group."""
    config = load_config()

    judge_family = config["roles"]["judge"]["family"]

    tested = config["roles"]["tested_agents"]
    tested_families = set()
    for group in ["homogeneous", "heterogeneous", "reasoning", "weak"]:
        for model_info in tested.get(group, []):
            tested_families.add(model_info["family"])

    assert judge_family not in tested_families, (
        f"Judge family '{judge_family}' must not appear in tested_agents"
    )


def test_weak_group_present_in_config():
    """Config has the new 'weak' tested_agents sub-role (Amendment-06)."""
    config = load_config()
    weak = config["roles"]["tested_agents"].get("weak", [])
    assert len(weak) >= 1, "tested_agents.weak must have at least one entry"
    slugs = {m["model"] for m in weak}
    # Per Amendment-06 verified roster
    expected = {"gpt-4o-mini", "gemini-3.5-flash", "claude-haiku-4.5"}
    assert expected <= slugs, f"Missing weak slugs: {expected - slugs}"

