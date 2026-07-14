"""Isolated candidate-execution runner for the data_analysis domain.

Reads a JSON job from stdin, executes the candidate code in THIS separate
process, runs the test cases, and writes a JSON verdict to the file named by
``sys.argv[1]``. The verdict does NOT travel over stdout: the parent
(`DataChecker`) discards this process's stdout/stderr (DEVNULL), so (a) benign
candidate print()s can never corrupt the verdict, and (b) a candidate that
spawns a grandchild process cannot keep the parent blocked past the timeout by
inheriting an open stdout pipe. Because it runs as a child process, the parent
can enforce a HARD timeout by killing it — an infinite-loop candidate is
actually terminated, not merely abandoned on a daemon thread.

THREAT MODEL (important, and deliberately scoped): candidates are ordinary
model-generated solutions to data analysis prompts, NOT adversaries trying to
escape a sandbox. This runner therefore provides *isolation + a hard timeout*
(so a bad candidate cannot hang or corrupt the parent harness), NOT a security
sandbox. We do not attempt to defeat Python introspection escapes; that is out
of scope for a benchmark of non-adversarial code. The scientific guarantee we
need is deterministic, correct labeling of realistic candidates plus robustness
against crashes/hangs — both of which this provides.

Job schema (stdin, one JSON object):
    {
      "candidate": "<python source string>",
      "entrypoint": "compute_mean",
      "test_cases": [
        {"multi": false, "input": <json>, "expected": <json>},
        {"multi": true,  "input": [<arg1>, <arg2>], "expected": <json>}
      ]
    }

Verdict (written to argv[1], one JSON object):
    {"status": "pass"|"fail"|"error", "message": "..."}
"""

import json
import sys


FLOAT_TOL = 1e-9


def _emit(path, status, message):
    """Write the single JSON verdict to the dedicated verdict file."""
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
    3. None is distinct from 0/False/[].
    """
    if isinstance(expected, bool):
        return isinstance(result, bool) and result == expected
    if isinstance(result, bool):
        return False
    if expected is None:
        return result is None
    if result is None:
        return False
    if isinstance(expected, float):
        try:
            return abs(result - expected) < FLOAT_TOL
        except Exception:
            return False
    return result == expected


def _resolve_entrypoint(namespace, entrypoint):
    """Resolve the entrypoint by its EXACT name. Helper functions are allowed,
    but a candidate that does not define the required entrypoint fails
    resolution (no lone-function fallback, so a differently-named function
    cannot be silently rebound and scored as correct)."""
    fn = namespace.get(entrypoint)
    if callable(fn) and not isinstance(fn, type):
        return fn, None
    return None, (
        f"Candidate does not define required entrypoint '{entrypoint}'."
    )


def main():
    if len(sys.argv) < 2:
        # No verdict path -> nothing we can report back through; fail loudly.
        sys.stderr.write("runner: missing verdict path argument\n")
        return
    verdict_path = sys.argv[1]

    try:
        job = json.loads(sys.stdin.read())
    except Exception as exc:  # noqa: BLE001
        _emit(verdict_path, "error", f"bad job: {exc}")
        return

    candidate = job["candidate"]
    entrypoint = job["entrypoint"]
    test_cases = job["test_cases"]

    namespace = {"__name__": "__main__"}
    try:
        exec(candidate, namespace)  # noqa: S102 - benchmark candidate execution
    except Exception as exc:  # noqa: BLE001
        _emit(verdict_path, "error", f"Execution error: {exc}")
        return

    func, err = _resolve_entrypoint(namespace, entrypoint)
    if func is None:
        _emit(verdict_path, "error", err)
        return

    for i, tc in enumerate(test_cases):
        inp = tc["input"]
        expected = tc["expected"]
        try:
            if tc["multi"]:
                result = func(*inp)
            else:
                result = func(inp)
        except Exception as exc:  # noqa: BLE001
            _emit(verdict_path, "fail", f"Test {i + 1} raised: {exc}")
            return

        if not _compare(result, expected):
            _emit(verdict_path, "fail",
                  f"Test {i + 1} failed: input={inp!r}, "
                  f"expected={expected!r}, got={result!r}")
            return

    _emit(verdict_path, "pass", f"All {len(test_cases)} tests passed")


if __name__ == "__main__":
    main()
