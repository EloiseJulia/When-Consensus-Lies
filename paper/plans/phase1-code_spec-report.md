# Phase 1 — `code_spec` domain delivery report (TEMPLATE domain)

Branch: `slice/phase1-S1-code_spec` (off `topic/phase1-benchmark`) · **NOT merged** (awaiting human spot-check).
This is the FIRST of three Phase 1 domains, built fully as a template before fan-out to `data_analysis` + `policy_qa`.

## What was built
- `bench/code_spec/__init__.py` — 5 base coding problems (sort_records, string_join, parse_csv_line,
  count_occurrences, format_number). Deleting requirement *classes* yields genuine ambiguity; each
  interpretation is a real reference implementation checked by an **executable-gold** `CodeChecker`.
- `bench/code_spec/_runner.py` — isolated subprocess runner (hard kill-on-timeout, verdict via dedicated
  temp file, deterministic `_compare` that rejects bool-for-int and tolerances floats).
- `tests/test_code_spec.py` — lock-in tests for every fixed finding.
- `bench/data/code_spec.jsonl` — 21 generated tasks, ambiguity distribution `{0:5, 1:11, 2:4, 3:1}`.

## Verification (real artifact, not just tests)
| Check | Command | Result |
|---|---|---|
| Data generation | `python bench/code_spec/__init__.py` | 21 tasks generated |
| Distinguishability | `python -m bench.validate --domain code_spec` | **21/21 (100%)** in ~11s |
| Unit tests | `python -m pytest -q` | **68 passed** in ~16s |
| Infinite-loop killed | runner timeout | passed=False in ~5.0s |
| Grandchild-spawn candidate | robustness repro | passed in 0.14s (no hang) |
| Noisy-stdout candidate | transport repro | passed (verdict uncorrupted) |
| Boolean count predicate | science repro | rejected by all 3 count checkers |

## Audit trail (provenance separation — law 6)
Implementer/fixers: **Claude (Anthropic)** family. Auditor: **GPT (OpenAI)** family, hostile, fresh sessions.

| Round | Verdict | Findings | Resolution |
|---|---|---|---|
| Audit 1 | NO | 2 BLOCKER (callable-count rejects helpers; ~5 straw tasks) + 3 MAJOR | fixed: entrypoint-by-name, removed 3 straw problems, timeout+foils |
| Audit 2 | NO | CRITICAL sandbox-escape, HIGH thread-not-killed, HIGH count bool false-accept, MINOR stale backup | see below |
| Audit 3 | NO | MAJOR timeout-not-hard (grandchild pipe), MINOR stdout corrupts transport | fixed: DEVNULL + temp-file verdict channel |
| Audit 4 | **YES** | **0 issues** | template cross-family clean |
| Human spot-check | APPROVED w/ 2 fixes | sort/string/csv/count ✓; fix key_questions + format | see below |
| Audit 5 (post-fix) | **YES** | **0 issues** | approved to fan out |

### Human spot-check fixes (applied, re-audited clean)
1. **Per-variant `key_questions`** — `assemble_task` copied the *full* base-problem question set into every
   variant, so the k=0 control and partially-resolved k=1 variants listed already-answered axes.
   Since `key_questions` is the gold for the Direction-B (false-surfacing) detector, stale questions
   invert that metric and destroy the control. Fixed in the domain layer (frozen `build.py` untouched):
   `generate_tasks` now emits only the deleted axes' questions. Golden test enforces
   `len(key_questions) == ambiguity_level == len(interpretations) - 1`; k=0 → empty. Deterministic, no LLM.
2. **Fair `format` domain** — "2 decimal places" is not a natural default and "round half-up" ≠ Python's
   default (round-half-to-even), so the obvious `f"{x:.2f}"` was wrongly labeled a delusion. Reworked:
   decimals fixed in the core prompt; axes = rounding / sign / grouping, each with a clear Python-native
   default; **TARGET I0 == `f"{x:.2f}"`** (half-even, no sign, no grouping). Non-targets deviate on exactly
   one axis (half-up / `+` sign / thousands separators). k=3 coverage preserved. Verified: natural default
   passes only `format_halfeven`; the four format checkers are perfectly disjoint (identity matrix).

### Scope decision (documented, defended, accepted by auditor)
The sandbox-escape finding (Python introspection) was **scoped OUT**: candidates are non-adversarial
model outputs, so a perfect pure-Python sandbox is unwinnable and off-topic. The defensible guarantee is
**isolation + hard kill-on-timeout + honest docs (no "security sandbox" claim)** — which fixes the real
robustness need (a model may emit an infinite loop). The GPT auditor accepted this scoping in rounds 3–4.

## Known caveats for human spot-check
- `key_questions` currently lists *all* axes of the base problem even when a k-variant has already
  resolved one in the prompt (e.g. a k=1 task states "ascending" yet still asks "ascending or
  descending?"). Confirm whether that is desired (full clarifying set) or should be pruned to only the
  still-ambiguous axes.
- Validation spawns one subprocess per (checker, candidate); `_RESULT_CACHE` keeps it ~11s. Watch this
  cost when the same runner pattern is reused for the other two domains.

## Status
- [x] Built, audited clean cross-family (5 rounds, 0 BLOCKER/MAJOR), 100% distinguishable, 69 tests green.
- [x] **Human spot-check APPROVED** (sort/string/csv/count); the 2 required fixes applied + re-audited clean.
- [ ] NOT merged — awaiting the other two domains so the whole Phase 1 benchmark merges together.
- [→] **Fan-out APPROVED**: building `data_analysis` + `policy_qa` (parallel) with the SAME construction
      rules, each cross-family audited then human spot-checked (10 tasks) before merge.
