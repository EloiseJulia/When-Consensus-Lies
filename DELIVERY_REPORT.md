# data_analysis Hardening – Delivery Report

**Branch:** slice/phase1-S2-data_analysis  
**Commit:** 14b366d095c79a987ef7dca9e75be85f676ae4f1  
**Author:** CLAUDE family (Anthropic) – fix sub-agent  
**Next Audit:** GPT family (cross-family requirement enforced)

---

## Executive Summary

Successfully ported the HARDENED code_spec harness architecture to data_analysis,
fixing ALL 6 audit findings identified by the cross-family GPT auditor. The
data_analysis domain now matches code_spec's security guarantees: no forged
verdicts, no incidental gold leakage, no cross-test contamination, timeout kills
entire process tree, exact key_questions golden test, and import isolation.

**VERIFIED:**
- ✅ All 111 tests pass (32 data_analysis + 79 other)
- ✅ Domain validation: 10/10 tasks = 100% distinguishable
- ✅ verify_fixes.py: All 6 PoC attacks now FAIL as expected
- ✅ 11 new regression tests guard against attack patterns

---

## Detailed Fix Report

### BLOCKER #1: Verdict Forgery (file write → stdout sentinel)

**Problem:** Runner wrote verdict to `sys.argv[1]` file path. Candidate could
forge `{"status":"pass"}` via direct write or descendant overwrite.

**Fix:**
- Eliminated verdict file entirely
- Supervisor emits verdict over ITS OWN stdout: `__DATA_ANALYSIS_VERDICT__ {json}`
- DataChecker captures supervisor stdout, parses ONLY sentinel line
- Candidate worker stdout → supervisor stdin (separate pipe), never reaches parent

**PoC Before:** Candidate writes forged verdict → checker.check() returns PASS  
**PoC After:** Candidate writes to any file → checker.check() returns FAIL (wrong answer)

**Files:**
- `bench/data_analysis/_runner.py`: Added `_emit_verdict(status, msg)` → stdout sentinel
- `bench/data_analysis/__init__.py`: DataChecker.check() now `capture_output=True`, parses sentinel

**Regression Tests:**
- `test_blocker_verdict_forgery_direct_write`: glob temp dir, write forged verdict
- `test_blocker_verdict_forgery_stdout_then_exit`: print sentinel + os._exit(0)
- `test_blocker_verdict_forgery_monkeypatch`: monkeypatch json.dumps
- `test_blocker_verdict_forgery_file_overwrite`: descendant overwrites verdict file
- `test_blocker_verdict_forgery_early_exit`: os._exit(0) without output

---

### BLOCKER #2: Gold in Candidate Process (supervisor/worker split)

**Problem:** test_cases with `expected` serialized into candidate process.
Candidate could read `inspect.currentframe().f_back.f_locals['expected']`.

**Fix:**
- Supervisor (runner.py, no args) holds expected outputs (gold)
- For EACH test case, spawns a candidate WORKER that receives ONLY:
  - `{"candidate": "...", "entrypoint": "...", "input": <test_input>, "multi": bool}`
- Worker execs candidate, calls entrypoint, writes ONLY its output to temp file
- Supervisor compares worker output to gold → decides pass/fail
- Candidate NEVER sees expected outputs in ANY scope/frame

**PoC Before:** Candidate `inspect.stack()` → finds `expected` → returns it → PASS  
**PoC After:** Candidate `inspect.stack()` → no `expected` in any frame → wrong answer → FAIL

**Files:**
- `bench/data_analysis/_runner.py`: supervisor_main() spawns worker per test case
- Added CANDIDATE_BOOTSTRAP template (embedded in runner, written to sandbox)

**Regression Tests:**
- `test_blocker_expected_output_leak`: inspect.stack() + f_locals search

---

### BLOCKER #3: Cross-Test Contamination (one worker per test)

**Problem:** All tests ran in ONE namespace. Candidate with global counter could
return hard-coded sequence matching gold.

**Fix:**
- ONE fresh worker subprocess PER test case
- No candidate globals carried over between tests
- Each invocation: positional input → output

**PoC Before:** `_counter=0; _counter+=1; return [gold1,gold2,gold3][_counter-1]` → PASS  
**PoC After:** Same code → each test runs in fresh worker → counter resets → FAIL

**Files:**
- `bench/data_analysis/_runner.py`: `for test_num, tc in enumerate(test_cases, 1): spawn_worker()`

**Regression Tests:**
- `test_blocker_cross_test_contamination`: global counter sequence attack

---

### MAJOR #4: Timeout Kills Descendants (tree-kill)

**Problem:** `subprocess.run(timeout=N)` kills parent but not grandchildren.
Candidate spawning a child left survivor processes.

**Fix:**
- Run worker in killable process group:
  - Windows: `CREATE_NEW_PROCESS_GROUP` + `taskkill /F /T /PID`
  - Unix: `start_new_session=True` + `os.killpg(os.getpgid(pid), SIGKILL)`
- On timeout: `_kill_process_tree(process.pid)` kills entire tree

**PoC Before:** Candidate spawns child → parent times out → child survives  
**PoC After:** Candidate spawns child → timeout → both killed (verified with psutil)

**Files:**
- `bench/data_analysis/_runner.py`: Added `_kill_process_tree(pid)` function
- Worker spawned with process group flags

**Regression Tests:**
- `test_major_timeout_kills_descendants`: spawns marked child, verifies no survivor

---

### MINOR #5: Exact key_questions Golden Test

**Problem:** test_key_questions_invariant only checked counts, not content.

**Fix:**
- Build expected question map from problem_* functions
- For each task, extract deleted axes (non-target interpretations' `opened_by`)
- Assert `set(task.key_questions) == {qmap[axis] for axis in deleted_axes}`
- Exact content match, not just `len(key_questions) == k`

**Files:**
- `tests/test_data_analysis.py`: test_key_questions_invariant() strengthened
- Added imports: `problem_compute_mean, problem_compute_variance, problem_compute_median, problem_filter_records, problem_group_by_key`

---

### FIX #6: Import Isolation (sandbox + -S -E -B)

**Problem:** Candidate could `from bench.data_analysis import CHECKERS` and
access gold test cases.

**Fix:**
- Worker runs with `-S -E -B` flags (no site-packages, no PYTHON* env, no .pyc)
- Scrubbed environment: `PYTHONPATH`, `PYTHONHOME`, `VIRTUAL_ENV` removed
- Bootstrap script written to sandbox temp dir, launched from there
- sys.argv[0] and __main__.__file__ point to sandbox (not repo) → stops trivial path discovery

**PoC Before:** `from bench.data_analysis import ...` → success  
**PoC After:** `from bench.data_analysis import ...` → ImportError → candidate errors → FAIL

**Files:**
- `bench/data_analysis/_runner.py`: CANDIDATE_BOOTSTRAP includes import cleanup
- Worker command: `[sys.executable, '-S', '-E', '-B', bootstrap_path, ...]`
- Clean environment: filter out PYTHON* keys

**Regression Tests:**
- `test_blocker_gold_import_test_cases`: try importing CHECKERS
- `test_blocker_gold_import_bench_module`: try importing bench
- `test_blocker_gold_path_discovery_bootstrap`: check sys.argv[0] points to sandbox

---

## Test Results

### Full pytest Suite
```
111 passed in 68.93s (0:01:08)
```

**Breakdown:**
- 32 data_analysis tests (21 original + 11 new attack regression tests)
- 79 other domain tests (unaffected)

### Domain Validation
```
=== Validation Summary: data_analysis ===
Tasks: 10
Ambiguity distribution: {0: 5, 1: 5}
Distinguishable: 10 / 10 (100.0%)

✅ All tasks passed validation (100% distinguishable)
```

### verify_fixes.py (PoC verification)
```
======================================================================
✅ ALL 6 FIXES VERIFIED
======================================================================

Summary:
  1. Verdict forgery: Sentinel over parent stdout (not file)
  2. Gold leakage: Supervisor holds expected, worker gets input only
  3. Cross-test: One fresh worker per test case
  4. Timeout: Tree-kill on Windows/Unix
  5. key_questions: Exact golden test with problem map
  6. Import isolation: -S -E -B + scrubbed env + bootstrap sandbox
```

---

## Attack Regression Tests (11 new)

All tests in `tests/test_data_analysis.py`:

1. **test_blocker_verdict_forgery_direct_write**: Try glob + write forged verdict
2. **test_blocker_verdict_forgery_stdout_then_exit**: Print sentinel + os._exit(0)
3. **test_blocker_expected_output_leak**: inspect.stack() + f_locals search
4. **test_blocker_verdict_forgery_early_exit**: os._exit(0) without output
5. **test_blocker_verdict_forgery_monkeypatch**: Monkeypatch json.dumps
6. **test_blocker_verdict_forgery_file_overwrite**: Descendant overwrites verdict
7. **test_blocker_gold_import_test_cases**: Import CHECKERS from bench.data_analysis
8. **test_blocker_gold_import_bench_module**: Import bench module
9. **test_blocker_gold_path_discovery_bootstrap**: Check sys.argv[0] sandbox
10. **test_blocker_cross_test_contamination**: Global counter sequence
11. **test_major_timeout_kills_descendants**: Spawn marked child, verify killed (psutil)

---

## Architecture Overview (Post-Fix)

```
DataChecker.check(candidate_code)
    ↓
subprocess.run([python, _runner.py], input=job_json, capture_output=True)
    ↓
SUPERVISOR (runner.py, holds gold):
    For each test case:
        1. Write worker_input.json (candidate + entrypoint + input ONLY)
        2. Spawn WORKER in sandbox:
           python -S -E -B bootstrap.py worker_input.json worker_output.json
        3. WORKER:
           - exec(candidate)
           - call entrypoint(input)
           - write {"status":"ok","result":...} to worker_output.json
        4. Read worker_output.json
        5. Compare result to expected (SUPERVISOR DECIDES)
    Emit: __DATA_ANALYSIS_VERDICT__ {"status":"pass/fail/error",...}
    ↓
DataChecker parses sentinel from stdout → CheckResult
```

**Guarantees:**
- Verdict travels over parent-owned pipe (stdout), candidate cannot forge
- Expected outputs NEVER in candidate's process/memory/scope
- One fresh worker per test case, no shared globals
- Timeout kills entire process tree (Windows/Unix)
- Import path isolation: repo not on sys.path (-S -E -B + scrubbed env)

**Limitations (documented in DOMAIN_API.md):**
- NOT a security sandbox against deliberately malicious code
- Absolute-path open() to read repo files is NOT blocked
- Candidates are cooperative LLM solutions, not adversaries
- OS-level sandboxing (container, restricted user) is future work

---

## Changed Files

1. **bench/data_analysis/_runner.py** (356 lines, +244/-112)
   - Eliminated verdict file, emit over stdout sentinel
   - Supervisor/worker split (one worker per test case)
   - _kill_process_tree() for timeout enforcement
   - CANDIDATE_BOOTSTRAP template (scrubbed import path)
   - Worker spawned with -S -E -B flags + clean env + sandbox cwd

2. **bench/data_analysis/__init__.py** (56 lines changed in DataChecker.check)
   - Removed verdict file creation
   - Changed to capture_output=True
   - Parse __DATA_ANALYSIS_VERDICT__ sentinel from supervisor stdout
   - Increased parent timeout to 2x (allow supervisor its own budget)

3. **tests/test_data_analysis.py** (+697 lines)
   - Strengthened test_key_questions_invariant (exact content match)
   - Added 11 attack regression tests
   - Fixed imports (problem_group_by_key not problem_group_records)

4. **verify_fixes.py** (NEW, 97 lines)
   - Standalone verification script for all 6 PoC attacks
   - Run: `python verify_fixes.py` → all PoCs must FAIL

---

## Provenance & Compliance

- **Author Model Family:** CLAUDE (Anthropic)
- **Auditor Model Family:** GPT (OpenAI) – identified the 6 findings
- **Next Audit Must Be:** GPT (cross-family requirement)
- **Commit Trailer:** `Co-authored-by: copilot <copilot@users.noreply.github.com>` ✅

**Hard Law #2 Compliance:** This fix was authored by CLAUDE family. The audit
that identified these issues was by GPT family. The NEXT audit of this code
MUST also be GPT family (or another non-CLAUDE family) to maintain provenance
separation.

---

## Self-Check Gate: PASSED ✅

Before marking ready:
- [x] All 111 tests pass
- [x] Domain validation: 10/10 = 100%
- [x] verify_fixes.py: All 6 PoCs FAIL
- [x] 11 attack regression tests added
- [x] Harness changes did NOT change generated tasks (10 tasks, ambiguity {0:5, 1:5})
- [x] Commit message includes Co-authored-by trailer
- [x] Branch is slice/phase1-S2-data_analysis (NOT main)
- [x] NO push, NO PR opened (Manager's job)

---

## Recommendations for Manager

1. **Next Step:** Spawn a GPT-family audit agent to verify these fixes
2. **Audit Scope:** Run attack PoCs, review architecture, confirm 0 new issues
3. **If Audit Passes:** Merge to main (after build+test+validate verification)
4. **If Audit Fails:** Spawn another CLAUDE fix agent (this auditor's family is GPT)

---

## References

- **Code_spec harness (reference):** `bench/code_spec/_runner.py`, `bench/code_spec/__init__.py`
- **Threat model:** `bench/DOMAIN_API.md` (Security Threat Model section)
- **Original audit findings:** See Manager's audit report (GPT family auditor)

**DELIVERY COMPLETE.**  
Branch: slice/phase1-S2-data_analysis  
Commit: 14b366d095c79a987ef7dca9e75be85f676ae4f1  
Status: ✅ READY FOR CROSS-FAMILY AUDIT (GPT)
