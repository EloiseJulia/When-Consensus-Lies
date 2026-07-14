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
   `(checkers_dict, candidates_dict, foils_list)` (3-tuple). Foils are
   **MANDATORY for domain certification** — `validate_domain` fails closed
   (marks the task NOT distinguishable) if a task has no foils. A 2-tuple is
   accepted only by the low-level `validate_task` primitive, never by
   certification.

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

- **Exactly one** target interpretation, and it MUST have the canonical id
  `"I0"`; `"I0"` is reserved for the target (non-targets use I1, I2, ...).
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


## Security Threat Model for Gold Checkers

When a domain implements a gold checker that executes candidate code (e.g., `code_spec`), the harness provides the following **GUARANTEES**:

1. **No forged verdicts**: Candidates CANNOT write/influence the final pass/fail verdict. The verdict travels over a parent-owned pipe that the candidate process tree cannot reach.
2. **No incidental gold leakage**: Expected outputs (gold) are NEVER in the candidate's process memory or file system access. Only the supervisor holds gold; the candidate receives only inputs.
3. **No cross-test contamination**: Each test case runs in an isolated worker process. One test's candidate code cannot affect another's.
4. **Timeout enforcement**: If a candidate exceeds the time limit, the ENTIRE process tree (including grandchildren) is killed.

The harness is **EXPLICITLY NOT**:

- A security sandbox against deliberately malicious code
- A defense against filesystem/interpreter introspection to exfiltrate gold
- Proof against candidates that derive the repository path and read source files

**Scope**: Candidates in this study are cooperative LLM-generated spec-solutions, **not adversaries**. The harness defends against bugs (e.g., accidental early exit, forged output) and incidental leakage, not against a candidate that deliberately performs `open(<absolute_repo_path>)`.

**Future work**: OS-level sandboxing (container, restricted user with repo unreadable) is noted for production deployments where candidate code is untrusted.
