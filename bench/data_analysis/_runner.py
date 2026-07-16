"""Isolated candidate-execution runner for the data_analysis domain.

SECURITY ARCHITECTURE (3-level isolation with scrubbed worker environment):

1. Supervisor (this script, no args): Holds gold/expected outputs. Spawns ONE 
   candidate worker per test case. Writes verdict to STDOUT with sentinel.
2. Candidate worker (bootstrap script in isolated sandbox): Receives ONLY test 
   input, execs candidate code, calls entrypoint, writes output to file. NEVER 
   sees expected outputs.

THREAT MODEL (deliberate scope):

GUARANTEES (enforced by this harness):
- No forged verdicts: Verdict travels over parent-owned pipe, candidate cannot write it
- No incidental gold leakage: Expected outputs never passed to candidate process
- No cross-test contamination: One isolated worker per test case
- Timeout enforcement: Runaway candidates are killed with their entire process tree
- Import path isolation: Editable-install repo not on candidate's import path

NOT GUARANTEED (accepted limitations for non-adversarial candidates):
- This is NOT a security sandbox against deliberately malicious code
- A candidate performing filesystem/interpreter introspection CAN exfiltrate gold
  (e.g., absolute-path open() to read repo source files if it derives the path)
- Candidates in this study are cooperative LLM spec-solutions, not adversaries
- OS-level sandboxing (container, chroot, restricted user with repo unreadable)
  is noted as FUTURE WORK for adversarial evaluation

The harness provides isolation + timeout for cooperative candidates and prevents
incidental/accidental leakage, NOT security against deliberate exfiltration.

Supervisor job schema (stdin, one JSON object):
    {
      "candidate": "<python source string>",
      "entrypoint": "compute_mean",
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
    __DATA_ANALYSIS_VERDICT__ {"status": "pass"|"fail"|"error", "message": "..."}
"""

import json
import os
import signal
import subprocess
import sys
import tempfile


FLOAT_TOL = 1e-9
TIMEOUT_SECONDS = 5.0


# Bootstrap script template for candidate worker
# This runs in the sandbox temp dir, so sys.argv[0] and __main__.__file__
# point to the sandbox, NOT the repo. This stops trivial path discovery.
CANDIDATE_BOOTSTRAP = """
import json
import sys
import os

# Best-effort hardening: clean up import hooks to raise the bar against
# re-enabling the editable install (not airtight, but stops trivial attacks)
try:
    # Remove repo paths and site-packages from sys.path
    original_path = sys.path[:]
    sys.path[:] = [p for p in sys.path if not any(x in p.lower() for x in ['site-packages', 'bench', 'common', 'consensus-lies'])]
    
    # Remove editable install finders from sys.meta_path
    if hasattr(sys, 'meta_path'):
        sys.meta_path[:] = [f for f in sys.meta_path if not any(x in str(type(f)).lower() for x in ['editable', 'pathfinder'])]
    
    # Remove bench/common from sys.modules if present
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith(('bench', 'common')):
            del sys.modules[mod_name]
except Exception:
    pass  # Best effort

FLOAT_TOL = 1e-9

def _resolve_entrypoint(namespace, entrypoint):
    fn = namespace.get(entrypoint)
    if callable(fn) and not isinstance(fn, type):
        return fn, None
    
    user_funcs = []
    for name, value in namespace.items():
        if name.startswith("__"):
            continue
        if not callable(value) or isinstance(value, type):
            continue
        if getattr(value, "__module__", None) in (None, "__main__"):
            user_funcs.append(value)
    
    if len(user_funcs) == 1:
        return user_funcs[0], None
    return None, f"Could not resolve entrypoint '{entrypoint}'. Found {len(user_funcs)} user-defined functions."

# Main worker logic
if len(sys.argv) != 3:
    sys.exit(1)

input_file = sys.argv[1]
output_file = sys.argv[2]

try:
    with open(input_file, "r", encoding="utf-8") as f:
        job = json.load(f)
except Exception as exc:
    try:
        # FLAKINESS FIX C: flush+fsync output_file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(json.dumps({"status": "error", "message": f"bad input: {exc}"}))
            f.flush()
            os.fsync(f.fileno())
    except OSError:
        pass
    sys.exit(1)

candidate = job["candidate"]
entrypoint = job["entrypoint"]
test_input = job["input"]
multi = job["multi"]

# Clean namespace: __file__ points to this bootstrap in sandbox, __name__ is __main__
namespace = {
    "__name__": "__main__",
    "__file__": __file__,  # Points to bootstrap in sandbox, not repo
}

try:
    exec(candidate, namespace)  # noqa: S102 - benchmark candidate execution
except Exception as exc:
    try:
        # FLAKINESS FIX C: flush+fsync output_file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(json.dumps({"status": "error", "message": f"Execution error: {exc}"}))
            f.flush()
            os.fsync(f.fileno())
    except OSError:
        pass
    sys.exit(1)

func, err = _resolve_entrypoint(namespace, entrypoint)
if func is None:
    try:
        # FLAKINESS FIX C: flush+fsync output_file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(json.dumps({"status": "error", "message": err}))
            f.flush()
            os.fsync(f.fileno())
    except OSError:
        pass
    sys.exit(1)

try:
    if multi:
        result = func(*test_input)
    else:
        result = func(test_input)
    
    # FLAKINESS FIX C: flush+fsync output_file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(json.dumps({"status": "ok", "result": result}))
        f.flush()
        os.fsync(f.fileno())
except Exception as exc:
    try:
        # FLAKINESS FIX C: flush+fsync output_file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(json.dumps({"status": "error", "message": f"Test raised: {exc}"}))
            f.flush()
            os.fsync(f.fileno())
    except OSError:
        pass
    sys.exit(1)
"""


def _emit_verdict(status, message):
    """Write the verdict to stdout with sentinel prefix (supervisor only).
    
    BLOCKER FIX: Verdict delivered over parent-owned pipe (stdout), NOT a
    shared temp file. The sentinel prefix allows DataChecker to parse the
    verdict from stdout reliably.
    """
    verdict = {"status": status, "message": message}
    print(f"__DATA_ANALYSIS_VERDICT__ {json.dumps(verdict)}", flush=True)


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
        # Create isolated sandbox directory for worker cwd
        sandbox_dir = tempfile.mkdtemp(prefix="dachk_sbx_")

        # Create temp files for input/output communication.
        # ISOLATION FIX: use an opaque prefix ("dachk_") that does NOT contain
        # "data_analysis" or "verdict". A candidate may spawn a *detached*
        # descendant that globs the shared temp root for "*data_analysis*" /
        # "*verdict*" files and overwrites them with a forged payload; such a
        # descendant can outlive its own worker (it is only tree-killed on the
        # timeout path). Opaque, non-matching names ensure it can never target a
        # LATER worker's result file, eliminating cross-test contamination. The
        # primary forgery defense (stdout verdict + strict status=="ok" check) is
        # unchanged; this only fixes test isolation.
        fd_in, input_file = tempfile.mkstemp(prefix=f"dachk_in_{test_num}_", suffix=".json")
        os.close(fd_in)
        fd_out, output_file = tempfile.mkstemp(prefix=f"dachk_out_{test_num}_", suffix=".json")
        os.close(fd_out)
        
        try:
            # Write input for this test case (NO expected output!)
            worker_input = {
                "candidate": candidate,
                "entrypoint": entrypoint,
                "input": tc["input"],
                "multi": tc["multi"],
            }
            # FLAKINESS FIX C: flush+fsync to ensure worker sees complete file
            with open(input_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(worker_input))
                f.flush()
                os.fsync(f.fileno())
            
            # Write bootstrap script into sandbox
            bootstrap_path = os.path.join(sandbox_dir, "_candidate_bootstrap.py")
            with open(bootstrap_path, "w", encoding="utf-8") as f:
                f.write(CANDIDATE_BOOTSTRAP)
            
            # Spawn candidate worker subprocess
            # MAJOR FIX #3: Put candidate in process group for tree killing
            # BLOCKER FIX: Worker's stdout is separate from supervisor's stdout
            # BLOCKER FIX: Worker runs with scrubbed environment (repo off import path)
            # CHEAP HARDENING: Bootstrap in sandbox means sys.argv[0] and __main__.__file__
            # point to sandbox, not repo - stops trivial path discovery
            
            try:
                try:
                    # Scrub environment: remove PYTHONPATH and other Python env vars
                    clean_env = {}
                    for key, value in os.environ.items():
                        # Keep essential system variables, exclude Python-specific ones
                        if not key.startswith('PYTHON') and key not in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'):
                            clean_env[key] = value
                    
                    # Build worker command with -S -E -B flags
                    # Launch the bootstrap script in the sandbox
                    worker_cmd = [
                        sys.executable,
                        '-S',  # No site-packages
                        '-E',  # No PYTHON* env vars
                        '-B',  # No .pyc
                        bootstrap_path,  # Bootstrap in sandbox, not repo _runner.py
                        input_file,
                        output_file,
                    ]
                    
                    if sys.platform == "win32":
                        CREATE_NEW_PROCESS_GROUP = 0x00000200
                        process = subprocess.Popen(
                            worker_cmd,
                            creationflags=CREATE_NEW_PROCESS_GROUP,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            env=clean_env,
                            cwd=sandbox_dir,  # Isolated cwd, not in repo
                        )
                    else:
                        process = subprocess.Popen(
                            worker_cmd,
                            start_new_session=True,  # New process group
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            env=clean_env,
                            cwd=sandbox_dir,  # Isolated cwd, not in repo
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
            finally:
                # Clean up sandbox directory and bootstrap
                try:
                    bootstrap_to_clean = os.path.join(sandbox_dir, "_candidate_bootstrap.py")
                    if os.path.exists(bootstrap_to_clean):
                        os.unlink(bootstrap_to_clean)
                except OSError:
                    pass
                try:
                    os.rmdir(sandbox_dir)
                except OSError:
                    pass
            
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
    # Supervisor mode: no args (reads job from stdin, writes verdict to stdout)
    # The candidate worker is now launched via bootstrap script in sandbox
    supervisor_main()


if __name__ == "__main__":
    main()
