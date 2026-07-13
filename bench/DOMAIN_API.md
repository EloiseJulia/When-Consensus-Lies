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
4. **Adversarial Foils** (REQUIRED): candidates that must match AT MOST ONE checker.
   Foils probe checker disjointness beyond the reference candidates — they are
   the real defense against overlapping checkers that certify 100% while a
   plausible answer secretly matches two interpretations.
5. **get_checkers_and_candidates(domain, task)**: Function returning
   `(checkers_dict, candidates_dict, foils_list)` (3-tuple; a 2-tuple without
   foils is accepted for back-compat but discouraged).

## Key API Signatures

```python
from bench.build import FullSpec, RequirementClass, InterpretationBranch, assemble_task
from bench.gold.base import GoldChecker, CheckResult

# Define full spec
spec = FullSpec(
    domain="...", task_id="...", prompt_core="...",
    requirement_classes=[RequirementClass(id="...", description="...", clauses=[...])],
    interpretations=[
        InterpretationBranch(id="I0", is_target=True, gold_check="..."),          # target: opened_by omitted
        InterpretationBranch(id="I1", is_target=False, gold_check="...", opened_by="req_id"),  # non-target MUST set opened_by
    ],
    key_questions=["..."]
)

# Generate task
task = assemble_task(spec, k=1, classes_to_delete=["req_id"])

# Implement checker
class MyChecker(GoldChecker):
    def check(self, candidate: Any) -> CheckResult:
        passed = ... # your deterministic logic
        return CheckResult(passed=passed, details="...")

# Validation loader (3-tuple)
def get_checkers_and_candidates(domain, task):
    return checkers_by_interp_id, candidates_by_interp_id, foils_list
```

## Constraints (enforced by build.py / validate.py — violations RAISE or FAIL)

- **Exactly one** target interpretation (is_target=True, id "I0") per task.
- Every **non-target** interpretation MUST declare `opened_by` = an existing
  requirement class id (clear provenance; keeps controls clean).
- Deletion is validated: class ids must exist, be distinct, and number exactly
  k; `0 <= k <= len(requirement_classes)`.
- **k=0 = unambiguous CONTROL**: prompt == latent_spec, only I0 present
  (valuable for Phase 3's false-surfacing-rate metric).
- **k>=1**: the prompt must become strictly less specified than latent_spec,
  AND at least one non-target interpretation must be opened.
- Checkers MUST be mutually distinguishing: each reference candidate passes
  ONLY its own checker, and every foil matches AT MOST ONE checker.
- NO LLM in gold checkers (use pytest, numeric assertions, keyword rubrics).
- Labeling is deterministic: `bench.validate.assign_label(candidate, checkers)`
  returns the unique interp id / `I_perp`, and RAISES `AmbiguousLabelError` on
  >1 match (ambiguity is never silent).

Run: `python -m bench.validate --domain <domain>` → must show 100% distinguishable
