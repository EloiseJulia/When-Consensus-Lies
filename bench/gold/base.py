"""Abstract interface for executable gold checkers.

Checkers provide deterministic, LLM-free verification that a candidate
matches a specific interpretation. For a well-formed benchmark, checkers
must be MUTUALLY DISTINGUISHING: each interpretation's reference candidate
passes only that interpretation's checker.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class CheckResult:
    """Result of running a gold checker."""
    passed: bool
    details: Optional[str] = None  # Diagnostic info for debugging


class GoldChecker(ABC):
    """Abstract base for interpretation-specific gold checkers.
    
    Subclasses implement deterministic verification logic (no LLM calls).
    Examples:
    - Code spec: run pytest on candidate implementation
    - Data analysis: assert exact numeric result or DataFrame equality
    - Policy QA: (weakened) keyword/structure rubric match
    """
    
    @abstractmethod
    def check(self, candidate: Any) -> CheckResult:
        """Check if candidate satisfies this interpretation's requirements.
        
        Args:
            candidate: The artifact to check (type varies by domain:
                      code string, DataFrame, answer dict, etc.)
        
        Returns:
            CheckResult with pass/fail and optional diagnostics
        """
        pass


class CheckerRegistry:
    """Registry to look up checkers by interpretation gold_check id."""
    
    def __init__(self):
        self._checkers: Dict[str, GoldChecker] = {}
    
    def register(self, check_id: str, checker: GoldChecker) -> None:
        """Register a checker under the given id."""
        self._checkers[check_id] = checker
    
    def get(self, check_id: str) -> Optional[GoldChecker]:
        """Retrieve a checker by id, or None if not found."""
        return self._checkers.get(check_id)
    
    def get_required(self, check_id: str) -> GoldChecker:
        """Retrieve a checker by id, raising if not found."""
        checker = self.get(check_id)
        if checker is None:
            raise KeyError(f"No checker registered for id: {check_id}")
        return checker


# Global registry instance for convenience
_global_registry = CheckerRegistry()


def register_checker(check_id: str, checker: GoldChecker) -> None:
    """Register a checker in the global registry."""
    _global_registry.register(check_id, checker)


def get_checker(check_id: str) -> Optional[GoldChecker]:
    """Get a checker from the global registry."""
    return _global_registry.get(check_id)


def get_checker_required(check_id: str) -> GoldChecker:
    """Get a checker from the global registry, raising if not found."""
    return _global_registry.get_required(check_id)
