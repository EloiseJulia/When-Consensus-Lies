# Phase 1 · Slice S2 · `data_analysis` — Delivery Report

**Branch:** `slice/phase1-S2-data_analysis`
**Constructor:** Claude (Anthropic) family · **Auditor:** GPT (OpenAI) family — provenance separation (hard law 6) satisfied.
**Status:** Cross-family re-audit **YES / 0 BLOCKER / 0 MAJOR**. Awaiting **human spot-check gate** (10 tasks). NOT merged.

## What this domain is
Executable-gold coding tasks over small datasets (mean / variance / median / filter / group-by). Deleting a
requirement *class* opens a genuine, plausibly-defaulted alternative reading, so the correct output changes by
interpretation. Gold checkers RUN the candidate in an isolated subprocess (temp-file verdict, hard ~5 s timeout);
deterministic, **no LLM**.

- 5 base problems, each with a **single** ambiguity axis → 10 tasks, distribution `{0:5, 1:5}` (k=0 controls + k=1
  variants). Single-axis (no k≥2) is an accepted MVP scope limitation for this domain; code_spec covers k up to 3.
- `python -m bench.validate --domain data_analysis` → **10/10 (100%) distinguishable**.
- `python -m pytest -q` → **90 passed** (~30 s).
- key_questions invariant holds for all tasks: `len(key_questions) == ambiguity_level == len(interpretations) - 1`;
  k=0 controls have `[]`.

## Targets (each = the natural default a reasonable unaware solver assumes)
| Problem | TARGET (I0) | Alternative (opened by deletion) |
| --- | --- | --- |
| compute_mean | skip missing (None) values | propagate None (return None if any) |
| compute_variance | population variance (÷n) — prompt frames a *complete population* | sample variance (÷n-1) |
| compute_median | even-length → average the two middle | even-length → lower middle |
| filter_records | inclusive `>=` — prompt says *meets a minimum threshold* | exclusive `>` |
| group_by_key | preserve within-group insertion order | sort values within each group |

## Audit history (PASS/FAIL)
| Round | Auditor (family) | Verdict | Findings |
| --- | --- | --- | --- |
| 1 | GPT `gpt-5.4` | **NO** | 1 BLOCKER + 3 MAJOR + 1 MINOR |
| 2 (re-audit) | GPT `gpt-5.4` | **YES** | 0 BLOCKER/MAJOR; 1 new MINOR (fixed) |

### Round-1 findings and fixes
- **[BLOCKER] median gold accepted a plain-mean impl.** Test data had `mean == median` on every case. → Added
  asymmetric cases `[1,1,100]`, `[1,2,3,100]` (mean ≠ median) to both median checkers; the mean-impostor now fails.
- **[MAJOR] mean prompt hid a `None` input domain.** Prompt said "list of numbers" but the checker injected `None`. →
  `prompt_core` now discloses "may contain missing entries represented as None"; target stays skip-missing.
- **[MAJOR] variance target (sample) was not the natural default.** No universal default (numpy=population,
  statistics=sample). → Reframed the scenario as a *complete population of measurements* and flipped the target to
  **population (÷n)**; sample (÷n-1) is the delusion.
- **[MAJOR] filter axis was a straw** ("greater than" is unambiguously `>`). → Reworded to *meets a minimum
  threshold* and flipped the target to **inclusive `>=`**; exclusive `>` is now the plausible alternative.
- **[MINOR] runner rebinds a wrongly-named function.** `_resolve_entrypoint` fell back to the lone user function. →
  Now requires the **exact** entrypoint name (helpers still allowed); a mis-named candidate fails resolution.

### Round-2 finding and fix
- **[MINOR] `test_near_miss_foils_present` had a vacuous assertion** (`near_miss >= 0`) whose docstring promised an
  exactly-one-match near-miss the mean foils don't provide. → Replaced with the real enforced invariant (every foil
  matches **at most one** checker) and corrected the docstring; zero-match near-misses are legitimate boundary probes.

## Commits
- `d622cb1` initial implementation
- `385ef72` fix round-1 audit findings (fairness + gold validity)
- `4ece45b` fix round-2 MINOR (vacuous near-miss assertion)

## Human spot-check
See `files/data_analysis-SPOTCHECK.md` (session artifact) — all 10 tasks with prompt, key_questions, interpretations,
target, and a discriminating input→output example. **Merge is gated on your per-task approval.**
