"""Tests for Phase 1 benchmark core framework."""

import pytest
from bench.build import (
    FullSpec,
    InterpretationBranch,
    RequirementClass,
    assemble_task,
    delete_requirements,
    load_tasks,
    save_tasks,
    task_from_jsonl,
    task_to_jsonl,
)
from bench.gold.base import CheckResult, GoldChecker
from bench.validate import validate_domain, validate_task
from common.schema import Interpretation, Task


class AlwaysPassChecker(GoldChecker):
    """Test checker that always passes."""
    def check(self, candidate) -> CheckResult:
        return CheckResult(passed=True, details="Always passes")


class AlwaysFailChecker(GoldChecker):
    """Test checker that always fails."""
    def check(self, candidate) -> CheckResult:
        return CheckResult(passed=False, details="Always fails")


def test_deletion_engine_basic():
    """Test deletion engine creates proper ambiguity."""
    spec = FullSpec(
        domain="test",
        task_id="test_001",
        prompt_core="Do something.",
        requirement_classes=[
            RequirementClass(
                id="req1",
                description="First requirement",
                clauses=["Requirement 1 text."]
            ),
            RequirementClass(
                id="req2",
                description="Second requirement",
                clauses=["Requirement 2 text."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Target",
                is_target=True,
                gold_check="check_i0"
            ),
            InterpretationBranch(
                id="I1",
                description="Alternative",
                is_target=False,
                gold_check="check_i1",
                opened_by="req1"
            ),
        ],
        key_questions=["What about req1?"]
    )
    
    result = delete_requirements(spec, k=1, classes_to_delete=["req1"])
    
    assert "Requirement 1 text." not in result["underdetermined_prompt"]
    assert "Requirement 2 text." in result["underdetermined_prompt"]
    assert "Requirement 1 text." in result["latent_spec"]
    assert "Requirement 2 text." in result["latent_spec"]
    assert result["deleted_classes"] == ["req1"]
    assert len(result["opened_interpretations"]) == 2


def test_deletion_engine_ambiguity_level():
    """Test that k deletions yield ambiguity_level=k."""
    spec = FullSpec(
        domain="test",
        task_id="test_002",
        prompt_core="Core task.",
        requirement_classes=[
            RequirementClass(id=f"req{i}", description=f"Req {i}", clauses=[f"Clause {i}"])
            for i in range(3)
        ],
        interpretations=[
            InterpretationBranch(id="I0", description="Target", is_target=True, gold_check="c0")
        ],
        key_questions=["Q1", "Q2", "Q3"]
    )
    
    for k in [1, 2, 3]:
        task = assemble_task(spec, k=k)
        assert task.ambiguity_level == k
        assert len(task.prompt) < len(task.latent_spec)


def test_jsonl_roundtrip():
    """Test Task serialization and deserialization."""
    original = Task(
        id="test_003",
        domain="test",
        prompt="Do this.",
        latent_spec="Do this with requirement X.",
        interpretations=[
            Interpretation(id="I0", is_target=True, gold_check="check_i0"),
            Interpretation(id="I1", is_target=False, gold_check="check_i1"),
        ],
        ambiguity_level=1,
        key_questions=["What is X?"]
    )
    
    jsonl_str = task_to_jsonl(original)
    restored = task_from_jsonl(jsonl_str)
    
    assert restored.id == original.id
    assert restored.domain == original.domain
    assert restored.prompt == original.prompt
    assert restored.latent_spec == original.latent_spec
    assert restored.ambiguity_level == original.ambiguity_level
    assert len(restored.interpretations) == len(original.interpretations)
    assert restored.interpretations[0].id == original.interpretations[0].id
    assert restored.interpretations[0].is_target == original.interpretations[0].is_target
    assert restored.key_questions == original.key_questions


def test_example_domain_distinguishability():
    """Test that _example domain has 100% distinguishability."""
    from bench._example import get_checkers_and_candidates
    
    summary = validate_domain(
        "_example",
        checker_loader=get_checkers_and_candidates
    )
    
    assert summary["task_count"] == 3
    assert summary["distinguishable_pct"] == 100.0
    assert len(summary["failed_tasks"]) == 0
    assert 0 in summary["ambiguity_distribution"]
    assert 1 in summary["ambiguity_distribution"]


def test_validate_task_mutual_distinguishing():
    """Test that validation ensures mutual distinguishing."""
    task = Task(
        id="test_004",
        domain="test",
        prompt="Test prompt",
        latent_spec="Test spec",
        interpretations=[
            Interpretation(id="I0", is_target=True, gold_check="check_i0"),
            Interpretation(id="I1", is_target=False, gold_check="check_i1"),
        ],
        ambiguity_level=1,
        key_questions=["Q1"]
    )
    
    # Create checkers that distinguish based on candidate value
    class Checker0(GoldChecker):
        def check(self, candidate) -> CheckResult:
            return CheckResult(passed=(candidate == "candidate_0"))
    
    class Checker1(GoldChecker):
        def check(self, candidate) -> CheckResult:
            return CheckResult(passed=(candidate == "candidate_1"))
    
    checkers = {
        "I0": Checker0(),
        "I1": Checker1(),
    }
    candidates = {
        "I0": "candidate_0",
        "I1": "candidate_1",
    }
    
    result = validate_task(task, checkers, candidates)
    assert result["distinguishable"] is True
    assert len(result["errors"]) == 0


def test_validate_task_negative_case():
    """Test that validation FAILS when checkers are not distinguishing."""
    task = Task(
        id="test_005",
        domain="test",
        prompt="Test prompt",
        latent_spec="Test spec",
        interpretations=[
            Interpretation(id="I0", is_target=True, gold_check="check_i0"),
            Interpretation(id="I1", is_target=False, gold_check="check_i1"),
        ],
        ambiguity_level=1,
        key_questions=["Q1"]
    )
    
    # Both checkers always pass -> not distinguishing
    checkers = {
        "I0": AlwaysPassChecker(),
        "I1": AlwaysPassChecker(),
    }
    candidates = {
        "I0": "candidate_0",
        "I1": "candidate_1",
    }
    
    result = validate_task(task, checkers, candidates)
    assert result["distinguishable"] is False
    assert len(result["errors"]) > 0
    assert any("MULTIPLE" in err for err in result["errors"])


def test_file_io_roundtrip(tmp_path):
    """Test saving and loading tasks from file."""
    tasks = [
        Task(
            id=f"test_00{i}",
            domain="test",
            prompt=f"Prompt {i}",
            latent_spec=f"Spec {i}",
            interpretations=[
                Interpretation(id="I0", is_target=True, gold_check="c0")
            ],
            ambiguity_level=i,
            key_questions=[f"Q{i}"]
        )
        for i in range(3)
    ]
    
    filepath = tmp_path / "test.jsonl"
    save_tasks(tasks, str(filepath))
    
    loaded = load_tasks(str(filepath))
    
    assert len(loaded) == len(tasks)
    for orig, load in zip(tasks, loaded):
        assert orig.id == load.id
        assert orig.ambiguity_level == load.ambiguity_level
