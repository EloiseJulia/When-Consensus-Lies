# Domain API — What Domain Slices Must Implement

See bench/_example/ for a complete working example.

## Core Framework Provides

- **Deletion engine** (bench.build): delete_requirements(), assemble_task()
- **Gold checker interface** (bench.gold.base): GoldChecker, CheckResult, CheckerRegistry
- **Validation** (bench.validate): validate_task(), validate_domain()

## Domain Slices Must Provide

1. **FullSpec with RequirementClasses**: Full specification with tagged requirement classes
2. **Gold Checkers**: Subclass GoldChecker with deterministic check() method (NO LLM)
3. **Reference Candidates**: One per interpretation for validation
4. **get_checkers_and_candidates(domain, task)**: Function returning (checkers_dict, candidates_dict)

## Key API Signatures

```python
from bench.build import FullSpec, RequirementClass, InterpretationBranch, assemble_task
from bench.gold.base import GoldChecker, CheckResult

# Define full spec
spec = FullSpec(
    domain="...", task_id="...", prompt_core="...",
    requirement_classes=[RequirementClass(id="...", description="...", clauses=[...])],
    interpretations=[InterpretationBranch(id="I0", is_target=True, gold_check="...", opened_by=None)],
    key_questions=["..."]
)

# Generate task
task = assemble_task(spec, k=1, classes_to_delete=["req_id"])

# Implement checker
class MyChecker(GoldChecker):
    def check(self, candidate: Any) -> CheckResult:
        passed = ... # your deterministic logic
        return CheckResult(passed=passed, details="...")

# Validation loader
def get_checkers_and_candidates(domain, task) -> (Dict[str,GoldChecker], Dict[str,Any]):
    return checkers_by_interp_id, candidates_by_interp_id
```

## Constraints

- Checkers MUST be mutually distinguishing (each candidate passes ONLY its own checker)
- NO LLM in gold checkers (use pytest, numeric assertions, keyword rubrics)
- Exactly one I0 (is_target=True) per task
- k ∈ {1,2,3} (ambiguity level)

Run: `python -m bench.validate --domain <domain>` → must show 100% distinguishable
