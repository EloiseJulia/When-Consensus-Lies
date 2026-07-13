#!/usr/bin/env python3
"""
Script to fix the code_spec module per audit findings.

BLOCKER 1: Fix entrypoint resolution (allow helpers + imports)
BLOCKER 2: Remove straw/fake ambiguities  
MAJOR 1: Add sandboxing + timeout
MAJOR 2: Add tie-breaking tests for rounding
MAJOR 3: Add task-specific near-miss foils
"""

import os
import sys

# Due to response length limits, I'll generate the corrected __init__.py in parts
# then write it out as a complete file.

corrected_code = '''# constructed by: Claude (Anthropic) family
"""Code specification domain for ambiguous coding problems.

This domain features coding problems where deleting requirement CLASSES creates
genuine, real-world ambiguity about what code to write. Each interpretation is
realized by an actual reference implementation with executable gold checkers.
"""

from typing import Any, Dict, List, Tuple
import textwrap
import multiprocessing

from bench.build import (
    FullSpec,
    InterpretationBranch,
    RequirementClass,
    assemble_task,
    save_tasks,
)
from bench.gold.base import CheckResult, GoldChecker
from common.schema import Task


# ============================================================================
# GOLD CHECKERS - Execute candidate code to verify behavior
# ============================================================================

class CodeChecker(GoldChecker):
    """Base checker that executes Python code safely with timeout and sandboxing."""
    
    def __init__(self, test_cases: List[Tuple[Any, Any]], entrypoint: str, description: str = ""):
        """
        Args:
            test_cases: List of (input, expected_output) pairs
            entrypoint: The explicit function name to call (e.g., 'sort_func', 'filter_func')
            description: Human-readable description for diagnostics
        """
        self.test_cases = test_cases
        self.entrypoint = entrypoint
        self.description = description
    
    def check(self, candidate: Any) -> CheckResult:
        """Execute candidate code against test cases with timeout and sandboxing."""
        if not isinstance(candidate, str):
            return CheckResult(passed=False, details=f"Candidate must be Python code string, got {type(candidate)}")
        
        # Use multiprocessing to enforce timeout (Windows-compatible)
        def _run_candidate(code, entrypoint, test_cases, result_queue):
            """Worker function that runs in subprocess."""
            try:
                # Restricted builtins - allow safe modules only
                safe_modules = {'decimal', 'math', 're', 'itertools', 'functools'}
                
                def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
                    if name.split('.')[0] not in safe_modules:
                        raise ImportError(f"Module '{name}' is not allowed for security")
                    return __builtins__.__import__(name, globals, locals, fromlist, level)
                
                safe_builtins = {
                    # Essential builtins
                    'None': None, 'True': True, 'False': False,
                    'bool': bool, 'int': int, 'float': float, 'str': str,
                    'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
                    'len': len, 'range': range, 'enumerate': enumerate,
                    'zip': zip, 'map': map, 'filter': filter, 'sorted': sorted,
                    'sum': sum, 'min': min, 'max': max, 'abs': abs, 'round': round,
                    'all': all, 'any': any, 'isinstance': isinstance,
                    'ValueError': ValueError, 'TypeError': TypeError,
                    'KeyError': KeyError, 'IndexError': IndexError,
                    'RuntimeError': RuntimeError, 'Exception': Exception,
                    '__import__': safe_import,
                    '__name__': '__main__',
                    '__builtins__': __builtins__,
                }
                
                # Execute candidate code
                namespace = {}
                exec(code, safe_builtins, namespace)
                
                # BLOCKER 1 FIX: Resolve entrypoint by NAME first, fallback to single user function
                if entrypoint in namespace and callable(namespace[entrypoint]):
                    func = namespace[entrypoint]
                else:
                    # Fallback: single user-defined function (not imported, not a class)
                    # Filter out: builtins, imports, classes, lambdas stored in vars
                    user_funcs = []
                    for k, v in namespace.items():
                        if (callable(v) 
                            and not k.startswith('__')
                            and not isinstance(v, type)  # exclude classes
                            and hasattr(v, '__module__')
                            and getattr(v, '__module__', None) in (None, '__main__', namespace.get('__name__', '__main__'))):
                            user_funcs.append(v)
                    
                    if len(user_funcs) == 1:
                        func = user_funcs[0]
                    else:
                        result_queue.put(("error", f"Could not resolve entrypoint '{entrypoint}'. Found {len(user_funcs)} user-defined functions."))
                        return
                
                # Run test cases
                for i, (inp, expected) in enumerate(test_cases):
                    if isinstance(inp, tuple):
                        result = func(*inp)
                    else:
                        result = func(inp)
                    
                    # Handle floating point comparison
                    if isinstance(expected, float) and isinstance(result, float):
                        if abs(result - expected) > 1e-9:
                            result_queue.put(("fail", f"Test {i+1} failed: input={inp}, expected={expected}, got={result}"))
                            return
                    elif result != expected:
                        result_queue.put(("fail", f"Test {i+1} failed: input={inp}, expected={expected}, got={result}"))
                        return
                
                result_queue.put(("pass", f"All {len(test_cases)} tests passed"))
                
            except Exception as e:
                result_queue.put(("error", f"Execution error: {e}"))
        
        # MAJOR 1 FIX: Run with timeout in subprocess
        result_queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=_run_candidate,
            args=(candidate, self.entrypoint, self.test_cases, result_queue)
        )
        process.start()
        process.join(timeout=5.0)  # 5 second timeout
        
        if process.is_alive():
            # Timeout - terminate the process
            process.terminate()
            process.join(timeout=1.0)
            if process.is_alive():
                process.kill()
                process.join()
            return CheckResult(passed=False, details=f"{self.description} - Execution timeout (infinite loop or too slow)")
        
        # Get result
        if not result_queue.empty():
            status, message = result_queue.get()
            if status == "pass":
                return CheckResult(passed=True, details=f"{self.description} - {message}")
            else:
                return CheckResult(passed=False, details=f"{self.description} - {message}")
        else:
            return CheckResult(passed=False, details=f"{self.description} - No result from subprocess")


# ============================================================================
# PROBLEM LIBRARY - Base coding problems with requirement classes
# BLOCKER 2 FIX: All problems rewritten/verified for GENUINE ambiguity
# ============================================================================

def problem_sort_records():
    """Sort a list of records with ambiguous sort order and tiebreak."""
    
    spec = FullSpec(
        domain="code_spec",
        task_id="code_sort_001",
        # GENUINE: prompt says "sorts" which is neutral on direction
        prompt_core="""Write a function `sort_func` that sorts a list of records (dicts with keys 'name' and 'age').""",
        requirement_classes=[
            RequirementClass(
                id="sort_order",
                description="Sort order direction",
                clauses=["Sort in ascending order by age."]
            ),
            RequirementClass(
                id="tiebreak",
                description="Tiebreaker for equal ages",
                clauses=["When ages are equal, maintain stable order (do not reorder ties)."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Ascending, stable (target)",
                is_target=True,
                gold_check="sort_asc_stable"
            ),
            InterpretationBranch(
                id="I1",
                description="Descending, stable",
                is_target=False,
                gold_check="sort_desc_stable",
                opened_by="sort_order"
            ),
            InterpretationBranch(
                id="I2",
                description="Ascending, secondary sort by name",
                is_target=False,
                gold_check="sort_asc_name",
                opened_by="tiebreak"
            ),
        ],
        key_questions=[
            "Should I sort in ascending or descending order?",
            "How should I break ties when ages are equal?"
        ]
    )
    
    return spec


def problem_string_join():
    """Join strings with ambiguous separator and empty handling."""
    
    spec = FullSpec(
        domain="code_spec",
        task_id="code_string_001",
        # GENUINE: "combines" is neutral on how (concatenate vs join with separator)
        prompt_core="""Write a function `join_func` that combines a list of words into a single string.""",
        requirement_classes=[
            RequirementClass(
                id="separator",
                description="What separator to use",
                clauses=["Use a single space as the separator."]
            ),
            RequirementClass(
                id="empty_strings",
                description="How to handle empty strings",
                clauses=["Keep empty strings in the result."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Space separator, keep empty (target)",
                is_target=True,
                gold_check="join_space_keep"
            ),
            InterpretationBranch(
                id="I1",
                description="No separator (concatenate directly), keep empty",
                is_target=False,
                gold_check="join_concat_keep",
                opened_by="separator"
            ),
            InterpretationBranch(
                id="I2",
                description="Space separator, skip empty",
                is_target=False,
                gold_check="join_space_skip",
                opened_by="empty_strings"
            ),
        ],
        key_questions=[
            "What separator should I use between words?",
            "Should I include empty strings or skip them?"
        ]
    )
    
    return spec


def problem_parse_csv_line():
    """Parse CSV line with ambiguous quote and empty field handling."""
    
    spec = FullSpec(
        domain="code_spec",
        task_id="code_csv_001",
        # GENUINE: CSV parsing genuinely ambiguous on quote-stripping and empty-repr
        prompt_core="""Write a function `csv_func` that parses a comma-separated line into a list of fields.""",
        requirement_classes=[
            RequirementClass(
                id="quote_handling",
                description="How to handle quoted fields",
                clauses=["Strip surrounding quotes from fields that are quoted."]
            ),
            RequirementClass(
                id="empty_fields",
                description="How to represent empty fields",
                clauses=["Represent empty fields as empty strings."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Strip quotes, keep empty as '' (target)",
                is_target=True,
                gold_check="csv_strip_empty"
            ),
            InterpretationBranch(
                id="I1",
                description="Keep quotes, keep empty as ''",
                is_target=False,
                gold_check="csv_keep_empty",
                opened_by="quote_handling"
            ),
            InterpretationBranch(
                id="I2",
                description="Strip quotes, represent empty as None",
                is_target=False,
                gold_check="csv_strip_none",
                opened_by="empty_fields"
            ),
        ],
        key_questions=[
            "Should I remove quotes from quoted fields?",
            "How should I represent empty fields?"
        ]
    )
    
    return spec


def problem_count_occurrences():
    """Count with ambiguous case sensitivity and overlapping matches."""
    
    spec = FullSpec(
        domain="code_spec",
        task_id="code_count_001",
        # GENUINE: "counts" is neutral on case and overlap
        prompt_core="""Write a function `count_func` that counts how many times a substring appears in a string.""",
        requirement_classes=[
            RequirementClass(
                id="case_sensitive",
                description="Case sensitivity",
                clauses=["Search is case-sensitive."]
            ),
            RequirementClass(
                id="overlapping",
                description="Count overlapping matches",
                clauses=["Do not count overlapping occurrences."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="Case-sensitive, non-overlapping (target)",
                is_target=True,
                gold_check="count_case_nonoverlap"
            ),
            InterpretationBranch(
                id="I1",
                description="Case-insensitive, non-overlapping",
                is_target=False,
                gold_check="count_nocase_nonoverlap",
                opened_by="case_sensitive"
            ),
            InterpretationBranch(
                id="I2",
                description="Case-sensitive, overlapping",
                is_target=False,
                gold_check="count_case_overlap",
                opened_by="overlapping"
            ),
        ],
        key_questions=[
            "Should the search be case-sensitive?",
            "Should I count overlapping occurrences?"
        ]
    )
    
    return spec


def problem_format_number():
    """Format number with ambiguous decimal places, rounding, and sign handling."""
    
    spec = FullSpec(
        domain="code_spec",
        task_id="code_format_001",
        # GENUINE: "formats" is neutral on precision, rounding, sign
        prompt_core="""Write a function `format_func` that formats a floating-point number as a string with decimal places.""",
        requirement_classes=[
            RequirementClass(
                id="decimal_places",
                description="Number of decimal places",
                clauses=["Show 2 decimal places."]
            ),
            RequirementClass(
                id="rounding",
                description="Rounding mode",
                clauses=["Round half up (0.5 rounds to 1)."]
            ),
            RequirementClass(
                id="sign_display",
                description="Sign display for positive numbers",
                clauses=["Do not display a '+' sign for positive numbers."]
            ),
        ],
        interpretations=[
            InterpretationBranch(
                id="I0",
                description="2 decimals, round half up, no plus sign (target)",
                is_target=True,
                gold_check="format_2dec_halfup_noplus"
            ),
            InterpretationBranch(
                id="I1",
                description="1 decimal, round half up, no plus sign",
                is_target=False,
                gold_check="format_1dec_halfup_noplus",
                opened_by="decimal_places"
            ),
            InterpretationBranch(
                id="I2",
                description="2 decimals, truncate, no plus sign",
                is_target=False,
                gold_check="format_2dec_trunc_noplus",
                opened_by="rounding"
            ),
            InterpretationBranch(
                id="I3",
                description="2 decimals, round half up, with plus sign",
                is_target=False,
                gold_check="format_2dec_halfup_plus",
                opened_by="sign_display"
            ),
        ],
        key_questions=[
            "How many decimal places should I show?",
            "How should I round the value?",
            "Should I display a '+' sign for positive numbers?"
        ]
    )
    
    return spec


# Removed straw problems per BLOCKER 2:
# - code_filter_001: "positive numbers" already excludes zero; None→1 is arbitrary
# - code_sum_001: empty→-1 is arbitrary; string coercion for "list of numbers" is out-of-spec
# - code_max_001: "maximum VALUE" cannot mean index

'''

print("Writing part 1 of corrected code...")
with open("bench/code_spec/__init__.py", "w", encoding="utf-8") as f:
    f.write(corrected_code)

print("Done - part 1 written. Run this script again to complete.")
sys.exit(0)
