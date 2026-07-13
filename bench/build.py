"""Deletion-based ambiguity generation for benchmark tasks.

Phase 1: Full spec → delete 1/2/3 requirement classes → ambiguous prompt.
"""


def generate_ambiguous_task(full_spec: str, ambiguity_level: int) -> dict:
    """Generate underdetermined task by deleting requirement classes.
    
    [PHASE 1]
    
    Args:
        full_spec: Complete specification with all requirements
        ambiguity_level: 1/2/3 (number of requirement classes to delete)
    
    Returns:
        Dict with 'prompt' (ambiguous), 'latent_spec' (full), 'interpretations'
    """
    raise NotImplementedError("Phase 1: deletion-based ambiguity generation")


def generate_gold_checker(interpretation: str, domain: str) -> str:
    """Generate executable checker for an interpretation.
    
    [PHASE 1]
    
    Args:
        interpretation: Interpretation description
        domain: code_spec | data_analysis | policy_qa
    
    Returns:
        Path to checker file or function name
    """
    raise NotImplementedError("Phase 1: executable gold checker generation")
