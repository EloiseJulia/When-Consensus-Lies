"""Quick manual test of key audit fixes."""

from bench.code_spec import CHECKERS

print("Testing key audit fixes...")
print("="*60)

# Test BLOCKER 1: helper function
print("\n1. BLOCKER 1 (helper function):")
candidate_helper = """
def helper(x):
    return x * 2

def sort_func(records):
    return sorted(records, key=lambda r: r['age'])
"""

checker = CHECKERS['sort_asc_stable']
result = checker.check(candidate_helper)
print(f"   Result: {'✓ PASS' if result.passed else '✗ FAIL'}")
print(f"   Details: {result.details}")

# Test BLOCKER 1: decimal import
print("\n2. BLOCKER 1 (decimal import):")
candidate_import = """
from decimal import Decimal, ROUND_HALF_UP

def format_func(number):
    d = Decimal(str(number))
    rounded = d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f"{rounded:.2f}"
"""

checker2 = CHECKERS['format_2dec_halfup_noplus']
result2 = checker2.check(candidate_import)
print(f"   Result: {'✓ PASS' if result2.passed else '✗ FAIL'}")
print(f"   Details: {result2.details}")

# Test MAJOR 1: timeout
print("\n3. MAJOR 1 (infinite loop timeout):")
candidate_infinite = """
def sort_func(records):
    while True:
        pass
    return records
"""

result3 = checker.check(candidate_infinite)
expected = not result3.passed and ('timeout' in result3.details.lower() or 'infinite' in result3.details.lower())
print(f"   Result: {'✓ PASS (rejected)' if expected else '✗ FAIL'}")
print(f"   Details: {result3.details}")

# Test MAJOR 1: import blocking
print("\n4. MAJOR 1 (import os blocked):")
candidate_os = """
def sort_func(records):
    import os
    return os.listdir('.')
"""

result4 = checker.check(candidate_os)
expected = not result4.passed and ('not allowed' in result4.details.lower() or 'importerror' in result4.details.lower())
print(f"   Result: {'✓ PASS (blocked)' if expected else '✗ FAIL'}")
print(f"   Details: {result4.details}")

# Test MAJOR 2: naive f-string rejected
print("\n5. MAJOR 2 (naive f-string rejected by half-up):")
candidate_naive = """
def format_func(number):
    return f"{number:.2f}"
"""

result5 = checker2.check(candidate_naive)
print(f"   Result: {'✓ PASS (rejected)' if not result5.passed else '✗ FAIL (should reject)'}")
print(f"   Details: {result5.details}")

print("\n" + "="*60)
print("Quick test complete!")
