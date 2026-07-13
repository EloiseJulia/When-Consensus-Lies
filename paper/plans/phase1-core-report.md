# Phase 1 — Benchmark Core Framework — Delivery Report

**Branch:** `slice/phase1-S0-core` → `topic/phase1-benchmark` · **Draft PR:** #2 (base `main`, DO NOT MERGE — human spot-check gate)
**HEAD:** `25fa6a4`

## What shipped
The SERIAL foundation for the deletion-based ambiguity benchmark, before the 3 domain slices fan out in parallel.

| File | Purpose |
|------|---------|
| `bench/build.py` | Validated deletion engine; `FullSpec`/`RequirementClass`/`InterpretationBranch`; `assemble_task`, `delete_requirements`, `validate_full_spec`. |
| `bench/validate.py` | Distinguishability validator; adversarial **foils** (fail-closed); `assign_label` (raises `AmbiguousLabelError` on >1 match); domain-agnostic CLI (dynamic import). |
| `bench/gold/base.py` | `GoldChecker` ABC, `CheckResult`, registry. |
| `bench/_example/` | Toy domain proving run→validate end-to-end (3 tasks, 100%). |
| `bench/DOMAIN_API.md` | Contract the 3 real domains implement. |

## Provenance separation (hard law 6)
- **Implementer / fixer:** Claude (Anthropic) family.
- **Hostile audit:** GPT (OpenAI) family, 3 independent rounds.

| Audit round | Findings | Resolution |
|-------------|----------|------------|
| 1 | 2 BLOCKER + 2 MAJOR | all fixed (`cacd357`) |
| 2 | 1 BLOCKER + 1 MAJOR + 1 MINOR | all fixed (`25fa6a4`) |
| 3 (final) | **0 issues — verdict YES** | fan-out approved |

## Guarantees (executable gold, no LLM-judge)
- Deletions validated: ids exist & distinct, `count == k`, `0 <= k <= n`; `k>=1` strictly reduces the prompt vs `latent_spec`; `k=0` is an unambiguous **control** (`prompt == latent_spec`) for Phase 3's false-surfacing metric.
- Exactly one target interpretation, canonical id **`I0`**; every non-target declares `opened_by`.
- **Certification fails closed** without adversarial foils — a domain cannot certify 100% distinguishable while shipping overlapping checkers.
- Labeling is deterministic and **never silently ambiguous**.
- No LLM anywhere in `bench/*`.

## Verification (PASS/FAIL)
| Check | Result |
|-------|--------|
| `pip install -e .` | PASS |
| `python -m pytest -q` | **51 passed** |
| `python -m bench.validate --domain _example` | **100% distinguishable**, ambiguity dist {0,1} |
| Cross-family final audit | **0 BLOCKER/MAJOR/MINOR** |

## Next (fan-out — gated on human spot-check)
3 parallel domain slices off `topic/phase1-benchmark`: `code_spec` ⟂ `data_analysis` ⟂ `policy_qa`, ~50 tasks each with executable gold + adversarial foils. Constructor content = Gemini (google, ≠ tested pool); implement = Claude; audit = GPT. Then STOP and deliver 10 sampled tasks/domain for human spot-check before any merge to `main`.
