#!/usr/bin/env python3
"""
Part 2: Add reference implementations, test cases, and foils to code_spec module.
"""

import sys

# Append to the existing file
continuation = '''

# ============================================================================
# REFERENCE IMPLEMENTATIONS - One per interpretation per problem
# ============================================================================

REFERENCE_IMPLEMENTATIONS = {
    # Sort records
    "sort_asc_stable": """
def sort_func(records):
    return sorted(records, key=lambda r: r['age'])
""",
    "sort_desc_stable": """
def sort_func(records):
    return sorted(records, key=lambda r: r['age'], reverse=True)
""",
    "sort_asc_name": """
def sort_func(records):
    return sorted(records, key=lambda r: (r['age'], r['name']))
""",
    
    # String join
    "join_space_keep": """
def join_func(words):
    return ' '.join(words)
""",
    "join_concat_keep": """
def join_func(words):
    return ''.join(words)
""",
    "join_space_skip": """
def join_func(words):
    return ' '.join(w for w in words if w)
""",
    
    # Parse CSV
    "csv_strip_empty": """
def csv_func(line):
    fields = line.split(',')
    return [f.strip('"').strip("'") if f else '' for f in fields]
""",
    "csv_keep_empty": """
def csv_func(line):
    fields = line.split(',')
    return [f if f else '' for f in fields]
""",
    "csv_strip_none": """
def csv_func(line):
    fields = line.split(',')
    result = []
    for f in fields:
        f = f.strip('"').strip("'")
        result.append(None if not f else f)
    return result
""",
    
    # Count occurrences
    "count_case_nonoverlap": """
def count_func(text, substring):
    return text.count(substring)
""",
    "count_nocase_nonoverlap": """
def count_func(text, substring):
    return text.lower().count(substring.lower())
""",
    "count_case_overlap": """
def count_func(text, substring):
    count = 0
    start = 0
    while True:
        pos = text.find(substring, start)
        if pos == -1:
            break
        count += 1
        start = pos + 1
    return count
""",
    
    # Format number - MAJOR 2 FIX: true half-up using Decimal
    "format_2dec_halfup_noplus": """
def format_func(number):
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(str(number))
    rounded = d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f"{rounded:.2f}"
""",
    "format_1dec_halfup_noplus": """
def format_func(number):
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(str(number))
    rounded = d.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
    return f"{rounded:.1f}"
""",
    "format_2dec_trunc_noplus": """
def format_func(number):
    truncated = int(number * 100) / 100
    return f"{truncated:.2f}"
""",
    "format_2dec_halfup_plus": """
def format_func(number):
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(str(number))
    rounded = d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    sign = '+' if number >= 0 else ''
    return f"{sign}{rounded:.2f}"
""",
}


# ============================================================================
# TEST CASES - Input/output pairs for each interpretation
# MAJOR 2 FIX: Added tie-breaking cases for rounding (2.675, 1.005, etc.)
# ============================================================================

TEST_CASES = {
    # Sort records - test cases must produce DIFFERENT outputs for each interpretation
    "sort_asc_stable": [
        (
            [{'name': 'Charlie', 'age': 30}, {'name': 'Bob', 'age': 25}, {'name': 'Alice', 'age': 30}],
            [{'name': 'Bob', 'age': 25}, {'name': 'Charlie', 'age': 30}, {'name': 'Alice', 'age': 30}]
        ),
    ],
    "sort_desc_stable": [
        (
            [{'name': 'Charlie', 'age': 30}, {'name': 'Bob', 'age': 25}, {'name': 'Alice', 'age': 30}],
            [{'name': 'Charlie', 'age': 30}, {'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}]
        ),
    ],
    "sort_asc_name": [
        (
            [{'name': 'Charlie', 'age': 30}, {'name': 'Bob', 'age': 25}, {'name': 'Alice', 'age': 30}],
            [{'name': 'Bob', 'age': 25}, {'name': 'Alice', 'age': 30}, {'name': 'Charlie', 'age': 30}]
        ),
    ],
    
    # String join
    "join_space_keep": [
        (['hello', 'world'], 'hello world'),
        (['a', '', 'b'], 'a  b'),
    ],
    "join_concat_keep": [
        (['hello', 'world'], 'helloworld'),
        (['a', '', 'b'], 'ab'),
    ],
    "join_space_skip": [
        (['hello', 'world'], 'hello world'),
        (['a', '', 'b'], 'a b'),
    ],
    
    # Parse CSV
    "csv_strip_empty": [
        ('"a","b","c"', ['a', 'b', 'c']),
        ('x,,z', ['x', '', 'z']),
    ],
    "csv_keep_empty": [
        ('"a","b","c"', ['"a"', '"b"', '"c"']),
        ('x,,z', ['x', '', 'z']),
    ],
    "csv_strip_none": [
        ('"a","b","c"', ['a', 'b', 'c']),
        ('x,,z', ['x', None, 'z']),
    ],
    
    # Count occurrences - show case-sensitive vs overlapping differences
    "count_case_nonoverlap": [
        (('HELLO', 'l'), 0),  # Case-sensitive: 'l' not in 'HELLO'
        (('aaa', 'aa'), 1),  # Non-overlapping: count('aa') = 1
    ],
    "count_nocase_nonoverlap": [
        (('HELLO', 'l'), 2),  # Case-insensitive: finds 'l' in 'HELLO'
        (('aaa', 'aa'), 1),  # Non-overlapping: count('aa') = 1
    ],
    "count_case_overlap": [
        (('aaa', 'aa'), 2),  # Overlapping: finds 2
        (('HELLO', 'l'), 0),  # Case-sensitive: 'l' not in 'HELLO'
    ],
    
    # Format number - MAJOR 2 FIX: tie-breaking cases where half-up != Python default
    "format_2dec_halfup_noplus": [
        (3.456, '3.46'),  # Half-up rounding
        (2.675, '2.68'),  # TIE-BREAKER: true half-up gives .68, Python f-string gives .67
        (1.005, '1.01'),  # TIE-BREAKER: true half-up gives .01, default may give .00
        (2.5, '2.50'),
    ],
    "format_1dec_halfup_noplus": [
        (3.456, '3.5'),  # 1 decimal
        (2.675, '2.7'),
        (2.5, '2.5'),
    ],
    "format_2dec_trunc_noplus": [
        (3.456, '3.45'),  # Truncate: .456 → .45 (different from half-up .46)
        (2.675, '2.67'),  # Truncate gives .67
        (2.5, '2.50'),
    ],
    "format_2dec_halfup_plus": [
        (3.456, '+3.46'),  # With plus sign
        (2.675, '+2.68'),
        (-1.5, '-1.50'),  # Negative has minus sign
    ],
}


# ============================================================================
# CHECKERS REGISTRY
# ============================================================================

CHECKERS = {}
ENTRYPOINTS = {
    # Map checker IDs to their entrypoint function names
    "sort_asc_stable": "sort_func",
    "sort_desc_stable": "sort_func",
    "sort_asc_name": "sort_func",
    "join_space_keep": "join_func",
    "join_concat_keep": "join_func",
    "join_space_skip": "join_func",
    "csv_strip_empty": "csv_func",
    "csv_keep_empty": "csv_func",
    "csv_strip_none": "csv_func",
    "count_case_nonoverlap": "count_func",
    "count_nocase_nonoverlap": "count_func",
    "count_case_overlap": "count_func",
    "format_2dec_halfup_noplus": "format_func",
    "format_1dec_halfup_noplus": "format_func",
    "format_2dec_trunc_noplus": "format_func",
    "format_2dec_halfup_plus": "format_func",
}

for check_id, test_cases in TEST_CASES.items():
    entrypoint = ENTRYPOINTS[check_id]
    CHECKERS[check_id] = CodeChecker(test_cases, entrypoint=entrypoint, description=check_id)


# ============================================================================
# TASK GENERATION
# ============================================================================

def generate_tasks() -> List[Task]:
    """Generate all code_spec tasks with multiple deletion patterns."""
    
    # BLOCKER 2 FIX: Only include problems with genuine ambiguity
    problems = [
        problem_sort_records(),
        problem_string_join(),
        problem_parse_csv_line(),
        problem_count_occurrences(),
        problem_format_number(),
    ]
    
    tasks = []
    
    for base_spec in problems:
        base_id = base_spec.task_id
        n_req = len(base_spec.requirement_classes)
        
        # k=0 CONTROL: unambiguous
        task_k0 = assemble_task(base_spec, k=0, classes_to_delete=[])
        task_k0.id = f"{base_id}_k0"
        tasks.append(task_k0)
        
        # k=1: delete each requirement individually
        for i, req_class in enumerate(base_spec.requirement_classes):
            spec_copy = FullSpec(
                domain=base_spec.domain,
                task_id=f"{base_id}_k1_{req_class.id}",
                prompt_core=base_spec.prompt_core,
                requirement_classes=base_spec.requirement_classes[:],
                interpretations=base_spec.interpretations[:],
                key_questions=base_spec.key_questions[:]
            )
            task = assemble_task(spec_copy, k=1, classes_to_delete=[req_class.id])
            tasks.append(task)
        
        # k=2: delete all requirements (if there are exactly 2)
        if n_req == 2:
            req_ids = [rc.id for rc in base_spec.requirement_classes]
            spec_copy = FullSpec(
                domain=base_spec.domain,
                task_id=f"{base_id}_k2_all",
                prompt_core=base_spec.prompt_core,
                requirement_classes=base_spec.requirement_classes[:],
                interpretations=base_spec.interpretations[:],
                key_questions=base_spec.key_questions[:]
            )
            task = assemble_task(spec_copy, k=2, classes_to_delete=req_ids)
            tasks.append(task)
        
        # k=3: delete all requirements (if there are exactly 3)
        if n_req == 3:
            req_ids = [rc.id for rc in base_spec.requirement_classes]
            spec_copy = FullSpec(
                domain=base_spec.domain,
                task_id=f"{base_id}_k3_all",
                prompt_core=base_spec.prompt_core,
                requirement_classes=base_spec.requirement_classes[:],
                interpretations=base_spec.interpretations[:],
                key_questions=base_spec.key_questions[:]
            )
            task = assemble_task(spec_copy, k=3, classes_to_delete=req_ids)
            tasks.append(task)
    
    return tasks


# ============================================================================
# VALIDATION LOADER
# MAJOR 3 FIX: Task-specific near-miss foils for each problem
# ============================================================================

def get_task_specific_foils(task_id_base: str) -> List[str]:
    """Generate task-specific near-miss foils that test checker boundaries.
    
    MAJOR 3 FIX: Each task gets plausible near-miss foils that might match
    multiple interpretations if checkers aren't truly disjoint.
    """
    
    if "code_sort" in task_id_base:
        return [
            # Near-miss: ascending but breaks ties by reverse name (boundary between I0 and I2)
            """
def sort_func(records):
    return sorted(records, key=lambda r: (r['age'], -ord(r['name'][0])))
""",
            # Near-miss: descending but with dict iteration (tests I1 boundary)
            """
def sort_func(records):
    return sorted(records, key=lambda r: -r['age'])
""",
            # Always-fail foil
            """
def sort_func(records):
    raise ValueError("not implemented")
""",
        ]
    
    elif "code_string" in task_id_base:
        return [
            # Near-miss: joins with space but adds extra spaces (boundary test)
            """
def join_func(words):
    return '  '.join(words)
""",
            # Near-miss: filters empty but uses different method (boundary for I2)
            """
def join_func(words):
    return ' '.join([w for w in words if len(w) > 0])
""",
            # Wrong behavior
            """
def join_func(words):
    return ','.join(words)
""",
        ]
    
    elif "code_csv" in task_id_base:
        return [
            # Near-miss: strips only double quotes, not single (boundary test)
            """
def csv_func(line):
    fields = line.split(',')
    return [f.strip('"') if f else '' for f in fields]
""",
            # Near-miss: represents empty as empty list instead of None or ''
            """
def csv_func(line):
    return [f if f else [] for f in line.split(',')]
""",
            # Wrong split character
            """
def csv_func(line):
    return line.split(';')
""",
        ]
    
    elif "code_count" in task_id_base:
        return [
            # Near-miss: case-insensitive but uses different method
            """
def count_func(text, substring):
    import re
    return len(re.findall(substring, text, re.IGNORECASE))
""",
            # Near-miss: overlapping but off-by-one in start position
            """
def count_func(text, substring):
    count = 0
    start = 0
    while start < len(text):
        pos = text.find(substring, start)
        if pos == -1:
            break
        count += 1
        start = pos + 2  # off-by-one: should be +1 for overlap
    return count
""",
            # Wrong: returns boolean
            """
def count_func(text, substring):
    return substring in text
""",
        ]
    
    elif "code_format" in task_id_base:
        return [
            # Near-miss: naive f-string (MAJOR 2 FIX: this MUST fail half-up checker on ties)
            """
def format_func(number):
    return f"{number:.2f}"
""",
            # Near-miss: uses round() which is half-to-even, not half-up
            """
def format_func(number):
    return f"{round(number, 2):.2f}"
""",
            # Near-miss: correct half-up but wrong precision
            """
def format_func(number):
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(str(number))
    rounded = d.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
    return f"{rounded:.2f}"
""",
            # Wrong: returns number instead of string
            """
def format_func(number):
    return number
""",
        ]
    
    else:
        # Fallback generic foils
        return [
            "def func(): raise NotImplementedError()",
            "x = 42",
            "def func(): return None",
        ]


def get_checkers_and_candidates(domain: str, task: Task) -> Tuple[
    Dict[str, GoldChecker], Dict[str, Any], List[Any]
]:
    """Provide checkers, reference candidates, and adversarial foils.
    
    Returns a 3-tuple (checkers, candidates, foils). Foils are candidates that
    must match AT MOST ONE checker; they probe checker disjointness beyond the
    reference candidates.
    """
    
    # Build checkers for this task's interpretations
    checkers = {}
    candidates = {}
    
    for interp in task.interpretations:
        check_id = interp.gold_check
        if check_id not in CHECKERS:
            raise ValueError(f"Unknown checker: {check_id}")
        checkers[interp.id] = CHECKERS[check_id]
        candidates[interp.id] = REFERENCE_IMPLEMENTATIONS[check_id]
    
    # MAJOR 3 FIX: Task-specific near-miss foils
    # Extract base task ID (before _k0, _k1, etc.)
    task_id_base = task.id.split('_k')[0] if '_k' in task.id else task.id
    foils = get_task_specific_foils(task_id_base)
    
    # MAJOR 1 FIX test cases: Add foils that test timeout and import blocking
    foils.extend([
        # Test timeout: infinite loop
        """
def func(*args):
    while True:
        pass
""",
        # Test import blocking: try to import os
        """
def func(*args):
    import os
    return os.getcwd()
""",
        # Test import blocking: try to import socket
        """
def func(*args):
    import socket
    return "bad"
""",
    ])
    
    return checkers, candidates, foils


# ============================================================================
# MAIN: Generate data file
# ============================================================================

if __name__ == "__main__":
    from pathlib import Path
    
    tasks = generate_tasks()
    output_path = Path(__file__).parent.parent / "data" / "code_spec.jsonl"
    output_path.parent.mkdir(exist_ok=True)
    save_tasks(tasks, str(output_path))
    
    print(f"Generated {len(tasks)} code_spec tasks -> {output_path}")
    levels = {k: sum(1 for t in tasks if t.ambiguity_level == k) for k in range(4)}
    print(f"Ambiguity distribution: {levels}")
    print("\\nFixed issues:")
    print("  ✓ BLOCKER 1: Entrypoint resolution (allows helpers + imports)")
    print("  ✓ BLOCKER 2: Removed straw ambiguities (filter/sum/max)")
    print("  ✓ MAJOR 1: Sandboxing + timeout")
    print("  ✓ MAJOR 2: Tie-breaking tests for rounding")
    print("  ✓ MAJOR 3: Task-specific near-miss foils")
'''

print("Writing part 2 of corrected code...")
with open("bench/code_spec/__init__.py", "a", encoding="utf-8") as f:
    f.write(continuation)

print("Done - file complete!")
sys.exit(0)
