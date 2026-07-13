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


# --- Fixes locked by the core audit (BLOCKER 1/2, MAJOR 3/4) ---


def _two_class_spec():
    """A spec with two requirement classes each opening one non-target interp."""
    return FullSpec(
        domain="test",
        task_id="test_fix",
        prompt_core="Core.",
        requirement_classes=[
            RequirementClass(id="a", description="A", clauses=["Clause A text."]),
            RequirementClass(id="b", description="B", clauses=["Clause B text."]),
        ],
        interpretations=[
            InterpretationBranch(id="I0", description="target", is_target=True, gold_check="c0"),
            InterpretationBranch(id="I1", description="alt-a", is_target=False, gold_check="c1", opened_by="a"),
            InterpretationBranch(id="I2", description="alt-b", is_target=False, gold_check="c2", opened_by="b"),
        ],
        key_questions=["Qa", "Qb"],
    )


def test_delete_rejects_unknown_class():
    """BLOCKER 1: deleting a non-existent class id must raise."""
    spec = _two_class_spec()
    with pytest.raises(ValueError, match="Unknown requirement class"):
        delete_requirements(spec, k=1, classes_to_delete=["does_not_exist"])


def test_delete_rejects_k_out_of_range():
    """BLOCKER 1: k larger than available classes must raise."""
    spec = _two_class_spec()
    with pytest.raises(ValueError, match=r"k must be in"):
        assemble_task(spec, k=3)


def test_delete_rejects_count_mismatch():
    """BLOCKER 1: classes_to_delete length must equal k."""
    spec = _two_class_spec()
    with pytest.raises(ValueError, match="exactly k"):
        delete_requirements(spec, k=2, classes_to_delete=["a"])


def test_k0_control_prompt_equals_latent():
    """BLOCKER 1: k=0 control leaves prompt == latent_spec, only target present."""
    spec = _two_class_spec()
    task = assemble_task(spec, k=0, classes_to_delete=[])
    assert task.prompt == task.latent_spec
    assert task.ambiguity_level == 0
    assert [i.id for i in task.interpretations] == ["I0"]


def test_deletion_makes_prompt_strictly_shorter():
    """BLOCKER 1: k>=1 must strictly reduce the prompt vs latent_spec."""
    spec = _two_class_spec()
    task = assemble_task(spec, k=1, classes_to_delete=["a"])
    assert len(task.prompt) < len(task.latent_spec)
    assert "Clause A text." not in task.prompt
    assert "Clause A text." in task.latent_spec


def test_spec_multi_target_rejected():
    """MAJOR 3: a spec with two targets must raise at validation."""
    spec = _two_class_spec()
    spec.interpretations[1].is_target = True  # now two targets
    with pytest.raises(ValueError, match="exactly one target"):
        assemble_task(spec, k=1, classes_to_delete=["a"])


def test_nontarget_requires_opened_by():
    """MAJOR 3: a non-target without opened_by must raise."""
    spec = _two_class_spec()
    spec.interpretations[1].opened_by = None
    with pytest.raises(ValueError, match="must declare opened_by"):
        assemble_task(spec, k=1, classes_to_delete=["a"])


def test_validate_task_rejects_two_targets():
    """MAJOR 3: validator flags a task with two target interpretations."""
    task = Task(
        id="t", domain="test", prompt="p", latent_spec="p spec",
        interpretations=[
            Interpretation(id="I0", is_target=True, gold_check="c0"),
            Interpretation(id="I1", is_target=True, gold_check="c1"),
        ],
        ambiguity_level=1, key_questions=["Q"],
    )
    checkers = {"I0": AlwaysPassChecker(), "I1": AlwaysFailChecker()}
    candidates = {"I0": "x", "I1": "y"}
    result = validate_task(task, checkers, candidates)
    assert result["distinguishable"] is False
    assert any("exactly one target" in e for e in result["errors"])


def test_validate_task_ambiguity_without_alternative():
    """Benchmark-validity: ambiguity_level>=1 with no non-target is rejected."""
    task = Task(
        id="t", domain="test", prompt="p", latent_spec="p spec",
        interpretations=[Interpretation(id="I0", is_target=True, gold_check="c0")],
        ambiguity_level=2, key_questions=["Q"],
    )
    checkers = {"I0": AlwaysPassChecker()}
    candidates = {"I0": "x"}
    result = validate_task(task, checkers, candidates)
    assert result["distinguishable"] is False
    assert any("no non-target" in e for e in result["errors"])


def test_foils_catch_overlapping_checkers():
    """BLOCKER 2: a foil matching multiple checkers fails validation even when
    reference candidates alone look distinguishable."""
    task = Task(
        id="t", domain="test", prompt="p", latent_spec="p spec",
        interpretations=[
            Interpretation(id="I0", is_target=True, gold_check="c0"),
            Interpretation(id="I1", is_target=False, gold_check="c1"),
        ],
        ambiguity_level=1, key_questions=["Q"],
    )

    class StartsWithA(GoldChecker):
        def check(self, candidate) -> CheckResult:
            return CheckResult(passed=str(candidate).startswith("a"))

    class EndsWithZ(GoldChecker):
        def check(self, candidate) -> CheckResult:
            return CheckResult(passed=str(candidate).endswith("z"))

    checkers = {"I0": StartsWithA(), "I1": EndsWithZ()}
    candidates = {"I0": "apple", "I1": "buzz"}
    # Reference candidates alone are distinguishable...
    ok = validate_task(task, checkers, candidates)
    assert ok["distinguishable"] is True
    # ...but a foil that both starts with 'a' and ends with 'z' exposes overlap.
    bad = validate_task(task, checkers, candidates, foils=["az"])
    assert bad["distinguishable"] is False
    assert any("Foil" in e and "MULTIPLE" in e for e in bad["errors"])


def test_target_must_be_i0():
    """MAJOR: the sole target must carry the canonical id 'I0'."""
    spec = _two_class_spec()
    spec.interpretations[0].id = "TARGET"  # target no longer I0
    with pytest.raises(ValueError, match="id 'I0'"):
        assemble_task(spec, k=1, classes_to_delete=["a"])


def test_validate_task_rejects_noncanonical_target():
    """MAJOR: validate_task flags a task whose target id != 'I0'."""
    task = Task(
        id="t", domain="test", prompt="p", latent_spec="p spec",
        interpretations=[
            Interpretation(id="TARGET", is_target=True, gold_check="c0"),
            Interpretation(id="I1", is_target=False, gold_check="c1"),
        ],
        ambiguity_level=1, key_questions=["Q"],
    )
    checkers = {"TARGET": AlwaysPassChecker(), "I1": AlwaysFailChecker()}
    candidates = {"TARGET": "x", "I1": "y"}
    result = validate_task(task, checkers, candidates, foils=["z"])
    assert result["distinguishable"] is False
    assert any("id 'I0'" in e for e in result["errors"])


def test_deleted_classes_order_is_deterministic():
    """MINOR: deleted_classes preserves caller order (not hash-seeded set order)."""
    spec = _two_class_spec()
    res = delete_requirements(spec, k=2, classes_to_delete=["b", "a"])
    assert res["deleted_classes"] == ["b", "a"]


def test_certification_fails_closed_without_foils(tmp_path):
    """BLOCKER: validate_domain (certification) marks tasks with no foils as
    NOT distinguishable, even if reference candidates look separable."""
    spec = _two_class_spec()
    task = assemble_task(spec, k=1, classes_to_delete=["a"])
    filepath = tmp_path / "nf.jsonl"
    save_tasks([task], str(filepath))

    class C0(GoldChecker):
        def check(self, candidate) -> CheckResult:
            return CheckResult(passed=(candidate == 0))

    class C1(GoldChecker):
        def check(self, candidate) -> CheckResult:
            return CheckResult(passed=(candidate == 1))

    # 2-tuple loader (no foils) -> certification must fail closed.
    def loader(domain, t):
        return {"I0": C0(), "I1": C1()}, {"I0": 0, "I1": 1}

    summary = validate_domain("nf", data_path=filepath, checker_loader=loader)
    assert summary["distinguishable_pct"] == 0.0
    assert summary["failed_tasks"]
    assert any(
        "foil" in e.lower()
        for f in summary["failed_tasks"] for e in f["errors"]
    )


def test_assign_label_raises_on_ambiguous():
    """assign_label returns a unique id / I_perp, and RAISES on >1 match."""
    from bench.validate import AmbiguousLabelError, assign_label

    class StartsWithA(GoldChecker):
        def check(self, candidate) -> CheckResult:
            return CheckResult(passed=str(candidate).startswith("a"))

    class EndsWithZ(GoldChecker):
        def check(self, candidate) -> CheckResult:
            return CheckResult(passed=str(candidate).endswith("z"))

    checkers = {"I0": StartsWithA(), "I1": EndsWithZ()}
    assert assign_label("apple", checkers) == "I0"
    assert assign_label("buzz", checkers) == "I1"
    assert assign_label("hello", checkers) == "I_perp"
    with pytest.raises(AmbiguousLabelError):
        assign_label("az", checkers)
