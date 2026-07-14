"""Isolated candidate-execution runner for the code_spec domain.

SECURITY FIX (3-level architecture with pipe-based verdict): Complete isolation.

Architecture:
1. Supervisor (this script, no args): Holds gold/expected outputs. Spawns ONE 
   candidate worker per test case. Writes verdict to STDOUT with sentinel.
2. Candidate worker (this script with input_file, output_file args): Receives 
   ONLY test input, execs candidate code, calls entrypoint, writes output to 
   file. NEVER sees expected outputs.

The candidate cannot forge a passing verdict because:
- It never sees expected outputs (gold) - supervisor holds them
- It only writes its own answer to output_file, which supervisor then checks
- Verdict travels over CodeChecker→Supervisor pipe (supervisor's stdout)
- Candidate worker's stdout is separate pipe to supervisor, NOT to CodeChecker
- Candidate cannot write to supervisor's stdout pipe (not inherited)

THREAT MODEL (important, and deliberately scoped): candidates are ordinary
model-generated solutions to coding prompts, NOT adversaries trying to escape a
sandbox. This runner therefore provides *isolation + a hard timeout* (so a bad
candidate cannot hang or corrupt the parent harness), NOT a security sandbox.
We do not attempt to defeat Python introspection escapes; that is out of scope
for a benchmark of non-adversarial code. The scientific guarantee we need is
deterministic, correct labeling of realistic candidates plus robustness against
crashes/hangs — both of which this provides.

Supervisor job schema (stdin, one JSON object):
    {
      "candidate": "<python source string>",
      "entrypoint": "sort_func",
      "test_cases": [
        {"multi": false, "input": <json>, "expected": <json>},
        {"multi": true,  "input": [<arg1>, <arg2>], "expected": <json>}
      ]
    }

Candidate worker input file (JSON):
    {"candidate": "<code>", "entrypoint": "func_name", "input": <test_input>, "multi": bool}

Candidate worker output file (JSON):
    {"status": "ok", "result": <value>}
    OR {"status": "error", "message": "..."}

Verdict (written by supervisor to STDOUT with sentinel):
    __CODESPEC_VERDICT__ {"status": "pass"|"fail"|"error", "message": "..."}
"""

import json
import os
import signal
import subprocess
import sys
import tempfile


FLOAT_TOL = 1e-9
TIMEOUT_SECONDS = 5.0


def _emit_verdict(status, message):
    """Write the verdict to stdout with sentinel prefix (supervisor only).
    
    BLOCKER FIX: Verdict delivered over parent-owned pipe (stdout), NOT a
    shared temp file. The sentinel prefix allows CodeChecker to parse the
    verdict from stdout reliably.
    """
    verdict = {"status": status, "message": message}
    print(f"__CODESPEC_VERDICT__ {json.dumps(verdict)}", flush=True)


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


def candidate_worker_main(input_file, output_file):
    """CANDIDATE WORKER: Execute candidate code with ONLY test input.
    
    This process NEVER sees expected outputs. It receives only:
    - candidate code
    - entrypoint name  
    - test input
    
    It writes only its computed result to output_file. The supervisor compares
    this result to the expected output (which the candidate never sees).
    """
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            job = json.load(f)
    except Exception as exc:  # noqa: BLE001
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(json.dumps({"status": "error", "message": f"bad input: {exc}"}))
        except OSError:
            pass
        return

    candidate = job["candidate"]
    entrypoint = job["entrypoint"]
    test_input = job["input"]
    multi = job["multi"]

    namespace = {"__name__": "__main__"}
    try:
        exec(candidate, namespace)  # noqa: S102 - benchmark candidate execution
    except Exception as exc:  # noqa: BLE001
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(json.dumps({"status": "error", "message": f"Execution error: {exc}"}))
        except OSError:
            pass
        return

    func, err = _resolve_entrypoint(namespace, entrypoint)
    if func is None:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(json.dumps({"status": "error", "message": err}))
        except OSError:
            pass
        return

    # Execute the test case
    try:
        if multi:
            result = func(*test_input)
        else:
            result = func(test_input)
        
        # Write the candidate's answer to output file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(json.dumps({"status": "ok", "result": result}))
    except Exception as exc:  # noqa: BLE001
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(json.dumps({"status": "error", "message": f"Test raised: {exc}"}))
        except OSError:
            pass


def _kill_process_tree(pid):
    """Kill a process and all its descendants.
    
    MAJOR FIX #3: Kill the entire process tree, not just the parent.
    """
    if sys.platform == "win32":
        # Windows: Use taskkill /F /T to kill tree
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
        except Exception:
            pass
    else:
        # Unix: Kill process group
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except Exception:
            pass


def supervisor_main():
    """SUPERVISOR: Spawn candidate workers, compare outputs to gold, write verdict.
    
    The supervisor holds the expected outputs (gold). For each test case, it 
    spawns a candidate worker that receives ONLY the input, gets back only the 
    candidate's output, and compares that to gold.
    
    Verdict is written to STDOUT with sentinel (parent-owned pipe), NOT a file.
    
    The candidate never sees expected outputs, so it cannot forge a pass by
    reading them or by printing forged results.
    """
    try:
        job = json.loads(sys.stdin.read())
    except Exception as exc:  # noqa: BLE001
        _emit_verdict("error", f"bad job: {exc}")
        return

    candidate = job["candidate"]
    entrypoint = job["entrypoint"]
    test_cases = job["test_cases"]

    # Run ONE candidate worker per test case (no multiplexing)
    for test_num, tc in enumerate(test_cases, 1):
        # Create temp files for input/output communication
        fd_in, input_file = tempfile.mkstemp(prefix=f"codespec_input_{test_num}_", suffix=".json")
        os.close(fd_in)
        fd_out, output_file = tempfile.mkstemp(prefix=f"codespec_output_{test_num}_", suffix=".json")
        os.close(fd_out)
        
        try:
            # Write input for this test case (NO expected output!)
            worker_input = {
                "candidate": candidate,
                "entrypoint": entrypoint,
                "input": tc["input"],
                "multi": tc["multi"],
            }
            with open(input_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(worker_input))
            
            # Spawn candidate worker subprocess
            # MAJOR FIX #3: Put candidate in process group for tree killing
            # BLOCKER FIX: Worker's stdout is separate from supervisor's stdout
            try:
                if sys.platform == "win32":
                    CREATE_NEW_PROCESS_GROUP = 0x00000200
                    process = subprocess.Popen(
                        [sys.executable, __file__, input_file, output_file],
                        creationflags=CREATE_NEW_PROCESS_GROUP,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    process = subprocess.Popen(
                        [sys.executable, __file__, input_file, output_file],
                        start_new_session=True,  # New process group
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                
                # Wait with timeout
                try:
                    process.wait(timeout=TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    # Kill the entire process tree
                    _kill_process_tree(process.pid)
                    try:
                        process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        pass
                    _emit_verdict("fail", 
                                f"Test {test_num} timeout (infinite loop or too slow)")
                    return
                
            except Exception as exc:  # noqa: BLE001
                _emit_verdict("error", f"Worker spawn failed: {exc}")
                return
            
            # Read candidate's output
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    output = json.load(f)
            except Exception as exc:  # noqa: BLE001
                _emit_verdict("error", 
                            f"Test {test_num}: No/invalid output: {exc}")
                return
            
            if output.get("status") == "error":
                _emit_verdict("error", 
                            f"Test {test_num}: {output.get('message', 'Unknown error')}")
                return
            
            if output.get("status") != "ok":
                _emit_verdict("error", 
                            f"Test {test_num}: Invalid output status")
                return
            
            # Compare candidate's result to expected (SUPERVISOR DECIDES)
            result = output.get("result")
            expected = tc["expected"]
            
            if not _compare(result, expected):
                _emit_verdict("fail",
                            f"Test {test_num} failed: input={tc['input']!r}, "
                            f"expected={expected!r}, got={result!r}")
                return
                
        finally:
            # Clean up temp files
            try:
                os.unlink(input_file)
            except OSError:
                pass
            try:
                os.unlink(output_file)
            except OSError:
                pass
    
    # All tests passed
    _emit_verdict("pass", f"All {len(test_cases)} tests passed")


def main():
    # Candidate worker mode: input_file output_file args
    if len(sys.argv) == 3:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        candidate_worker_main(input_file, output_file)
        return

    # Supervisor mode: no args (reads job from stdin, writes verdict to stdout)
    supervisor_main()


if __name__ == "__main__":
    main()
