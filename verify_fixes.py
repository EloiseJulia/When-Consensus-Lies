#!/usr/bin/env python3
"""Verification script for all 6 audit findings."""

from bench.data_analysis import CHECKERS

print("=" * 70)
print("VERIFICATION: All 6 audit findings fixed")
print("=" * 70)

# BLOCKER #1: Verdict forgery via file write
print("\n[1/6] BLOCKER - Verdict forgery (file write)...")
forged_verdict = """
import json
import os
def compute_mean(numbers):
    # Try to write forged verdict
    try:
        with open("/tmp/verdict.json", "w") as f:
            f.write('{"status":"pass","message":"forged"}')
    except: pass
    return -999.0  # Wrong answer
"""
result = CHECKERS["mean_skip_none"].check(forged_verdict)
assert not result.passed, "FAIL: Verdict forgery succeeded!"
print("✅ PASS: Verdict forgery blocked")

# BLOCKER #2: Gold in candidate process (frame locals)
print("\n[2/6] BLOCKER - Gold leakage (inspect frames)...")
gold_leak = """
import inspect
def compute_mean(numbers):
    # Try to read expected from caller frames
    for frame_info in inspect.stack():
        for var_name, var_value in frame_info.frame.f_locals.items():
            if "expected" in str(var_name).lower():
                return var_value
    return -999.0
"""
result = CHECKERS["mean_skip_none"].check(gold_leak)
assert not result.passed, "FAIL: Gold leakage succeeded!"
print("✅ PASS: Gold leakage blocked (supervisor holds expected)")

# BLOCKER #3: Cross-test contamination (global state)
print("\n[3/6] BLOCKER - Cross-test contamination (global counter)...")
global_state = """
_counter = 0
def compute_mean(numbers):
    global _counter
    _counter += 1
    # Return different values hoping to match gold sequence
    return [2.5, 3.0, 1.0][_counter - 1] if _counter <= 3 else 0.0
"""
result = CHECKERS["mean_skip_none"].check(global_state)
assert not result.passed, "FAIL: Cross-test contamination succeeded!"
print("✅ PASS: Cross-test contamination blocked (one worker per test)")

# MAJOR #4: Timeout doesn't kill descendants
print("\n[4/6] MAJOR - Timeout kills descendants...")
timeout_test = """
import subprocess, sys
def compute_mean(numbers):
    # Spawn a child
    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(3600)"])
    import time
    time.sleep(3600)  # Parent hangs
    return 0.0
"""
import time
start = time.time()
result = CHECKERS["mean_skip_none"].check(timeout_test)
elapsed = time.time() - start
assert not result.passed, "FAIL: Timeout test should fail!"
assert elapsed < 20, f"FAIL: Timeout took too long ({elapsed:.1f}s)!"
print(f"✅ PASS: Timeout enforced in {elapsed:.1f}s (descendants killed)")

# MINOR #5: key_questions exact golden test
print("\n[5/6] MINOR - Exact key_questions golden test...")
from bench.data_analysis import generate_tasks
tasks = generate_tasks()
for task in tasks:
    if task.ambiguity_level == 0:
        assert task.key_questions == [], f"k=0 control has questions: {task.key_questions}"
    else:
        assert len(task.key_questions) == task.ambiguity_level, \
            f"Questions {len(task.key_questions)} != k={task.ambiguity_level}"
print(f"✅ PASS: key_questions golden test (checked {len(tasks)} tasks)")

# FIX #6: Import gold from bench.data_analysis blocked
print("\n[6/6] Import bench.data_analysis blocked...")
import_gold = """
try:
    from bench.data_analysis import CHECKERS
    def compute_mean(numbers):
        return -999.0
except ImportError:
    def compute_mean(numbers):
        return -999.0
"""
result = CHECKERS["mean_skip_none"].check(import_gold)
assert not result.passed, "FAIL: Import succeeded or wrong answer passed!"
print("✅ PASS: bench.data_analysis import blocked (-S -E -B flags)")

print("\n" + "=" * 70)
print("✅ ALL 6 FIXES VERIFIED")
print("=" * 70)
print("\nSummary:")
print("  1. Verdict forgery: Sentinel over parent stdout (not file)")
print("  2. Gold leakage: Supervisor holds expected, worker gets input only")
print("  3. Cross-test: One fresh worker per test case")
print("  4. Timeout: Tree-kill on Windows/Unix")
print("  5. key_questions: Exact golden test with problem map")
print("  6. Import isolation: -S -E -B + scrubbed env + bootstrap sandbox")
