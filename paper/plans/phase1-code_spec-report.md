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
| Audit 4 | **YES** | **0 issues** | ready for human spot-check |

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
- [x] Built, audited clean cross-family (0 BLOCKER/MAJOR), 100% distinguishable, 68 tests green.
- [ ] **Human spot-check of 10 sampled tasks (delivered separately).**
- [ ] NOT merged; other two domains NOT started — both gated on human approval of this template.
