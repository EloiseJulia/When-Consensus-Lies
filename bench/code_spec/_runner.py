"""Isolated candidate-execution runner for the code_spec domain.

SECURITY FIX: The candidate code now runs in a worker process that NEVER
receives the verdict path. The worker returns test results over stdout, and the
supervisor (this script when called with a verdict path) compares results to
expected values and writes the verdict. This prevents candidates from forging a
passing verdict by writing to the verdict file or monkey-patching json.dumps.

Two modes:
- Worker mode (no args): Execute candidate, emit results to stdout as JSON
- Supervisor mode (verdict_path arg): Spawn worker, compare results, write verdict

THREAT MODEL (important, and deliberately scoped): candidates are ordinary
model-generated solutions to coding prompts, NOT adversaries trying to escape a
sandbox. This runner therefore provides *isolation + a hard timeout* (so a bad
candidate cannot hang or corrupt the parent harness), NOT a security sandbox.
We do not attempt to defeat Python introspection escapes; that is out of scope
for a benchmark of non-adversarial code. The scientific guarantee we need is
deterministic, correct labeling of realistic candidates plus robustness against
crashes/hangs — both of which this provides.

Job schema (stdin, one JSON object):
    {
      "candidate": "<python source string>",
      "entrypoint": "sort_func",
      "test_cases": [
        {"multi": false, "input": <json>, "expected": <json>},
        {"multi": true,  "input": [<arg1>, <arg2>], "expected": <json>}
      ]
    }

Worker output (stdout, JSON):
    {"status": "results", "results": [{"test": 1, "result": <val>, "input": <val>}, ...]}
    OR {"status": "error", "message": "..."}

Verdict (written by supervisor to verdict_path, one JSON object):
    {"status": "pass"|"fail"|"error", "message": "..."}
"""

import json
import subprocess
import sys


FLOAT_TOL = 1e-9
TIMEOUT_SECONDS = 5.0


def _emit_verdict(path, status, message):
    """Write the single JSON verdict to the dedicated verdict file (supervisor only)."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"status": status, "message": message}))
    except OSError:
        pass


def _compare(result, expected):
    """Deterministic equality with two guards that matter scientifically.

    1. A bool result where a non-bool is expected is a TYPE MISMATCH (Python's
       ``True == 1`` / ``False == 0`` would otherwise let a boolean predicate
       masquerade as an integer count).
    2. Floats compare within a tolerance.
    """
    if isinstance(expected, bool):
        return isinstance(result, bool) and result == expected
    if isinstance(result, bool):
        return False
    if isinstance(expected, float):
        try:
            return abs(result - expected) < FLOAT_TOL
        except Exception:
            return False
    return result == expected


def _resolve_entrypoint(namespace, entrypoint):
    """Resolve the entrypoint by NAME; fall back to a single user-defined
    function, ignoring imported callables and classes."""
    fn = namespace.get(entrypoint)
    if callable(fn) and not isinstance(fn, type):
        return fn, None

    user_funcs = []
    for name, value in namespace.items():
        if name.startswith("__"):
            continue
        if not callable(value) or isinstance(value, type):
            continue
        # Only functions actually defined by the candidate (module __main__),
        # not imported callables.
        if getattr(value, "__module__", None) in (None, "__main__"):
            user_funcs.append(value)

    if len(user_funcs) == 1:
        return user_funcs[0], None
    return None, (
        f"Could not resolve entrypoint '{entrypoint}'. "
        f"Found {len(user_funcs)} user-defined functions."
    )


def worker_main():
    """WORKER MODE: execute candidate code and emit test results to stdout.
    
    The worker NEVER receives the verdict path. It only executes the candidate
    and outputs test results. The supervisor compares results to expected values
    and makes the pass/fail decision.
    """
    try:
        job = json.loads(sys.stdin.read())
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "error", "message": f"bad job: {exc}"}))
        return

    candidate = job["candidate"]
    entrypoint = job["entrypoint"]
    test_cases = job["test_cases"]

    namespace = {"__name__": "__main__"}
    try:
        exec(candidate, namespace)  # noqa: S102 - benchmark candidate execution
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "error", "message": f"Execution error: {exc}"}))
        return

    func, err = _resolve_entrypoint(namespace, entrypoint)
    if func is None:
        print(json.dumps({"status": "error", "message": err}))
        return

    # Execute all test cases and collect results
    results = []
    for i, tc in enumerate(test_cases):
        inp = tc["input"]
        try:
            if tc["multi"]:
                result = func(*inp)
            else:
                result = func(inp)
            # Convert result to JSON-serializable form
            results.append({"test": i + 1, "result": result, "input": inp})
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({
                "status": "error",
                "message": f"Test {i + 1} raised: {exc}",
                "test": i + 1
            }))
            return

    # Return all test results for the supervisor to judge
    print(json.dumps({"status": "results", "results": results}))


def supervisor_main(verdict_path):
    """SUPERVISOR MODE: spawn worker, compare results to gold, write verdict.
    
    The supervisor makes the pass/fail decision and is the ONLY code that
    writes to the verdict file. The candidate code never sees the verdict path.
    """
    try:
        job_input = sys.stdin.read()
        job = json.loads(job_input)
    except Exception as exc:  # noqa: BLE001
        _emit_verdict(verdict_path, "error", f"bad job: {exc}")
        return

    test_cases = job["test_cases"]

    # Spawn worker subprocess (no verdict path in args!)
    try:
        result = subprocess.run(
            [sys.executable, __file__],  # Worker mode (no args)
            input=job_input,
            text=True,
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        _emit_verdict(verdict_path, "fail", "Execution timeout (infinite loop or too slow)")
        return
    except Exception as exc:  # noqa: BLE001
        _emit_verdict(verdict_path, "error", f"Worker subprocess failed: {exc}")
        return

    # Parse worker output
    try:
        worker_result = json.loads(result.stdout)
    except Exception as exc:  # noqa: BLE001
        _emit_verdict(verdict_path, "error", f"Invalid worker output: {exc}")
        return

    if worker_result.get("status") == "error":
        _emit_verdict(verdict_path, "error", worker_result.get("message", "Unknown error"))
        return

    if worker_result.get("status") != "results":
        _emit_verdict(verdict_path, "error", "Worker did not return results")
        return

    # Compare worker results to expected values (SUPERVISOR DECIDES, not worker)
    results = worker_result.get("results", [])
    if len(results) != len(test_cases):
        _emit_verdict(verdict_path, "error",
                     f"Expected {len(test_cases)} results, got {len(results)}")
        return

    for i, (res, tc) in enumerate(zip(results, test_cases)):
        expected = tc["expected"]
        actual = res["result"]
        
        if not _compare(actual, expected):
            _emit_verdict(verdict_path, "fail",
                         f"Test {i + 1} failed: input={res['input']!r}, "
                         f"expected={expected!r}, got={actual!r}")
            return

    _emit_verdict(verdict_path, "pass", f"All {len(test_cases)} tests passed")


def main():
    # Worker mode: no command-line args (spawned by supervisor)
    if len(sys.argv) == 1:
        worker_main()
        return

    # Supervisor mode: verdict path provided
    if len(sys.argv) < 2:
        sys.stderr.write("runner: missing verdict path argument\n")
        return
    
    verdict_path = sys.argv[1]
    supervisor_main(verdict_path)


if __name__ == "__main__":
    main()
