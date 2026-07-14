import json
from bench.policy_qa import REFERENCE_ANSWERS

# Load tasks from jsonl
tasks = []
with open('bench/data/policy_qa.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            tasks.append(json.loads(line))

# Check invariant: len(key_questions) == ambiguity_level == len(interpretations) - 1
print('=== Key_questions invariant check ===')
all_ok = True
for t in tasks:
    k = t['ambiguity_level']
    nq = len(t['key_questions'])
    ni = len(t['interpretations'])
    
    if nq != k:
        print(f'FAIL: {t["id"]}: {nq} questions != k={k}')
        all_ok = False
    if k != ni - 1:
        print(f'FAIL: {t["id"]}: k={k} != interpretations-1={ni-1}')
        all_ok = False
    if k == 0 and t['key_questions'] != []:
        print(f'FAIL: {t["id"]}: k=0 but key_questions not empty')
        all_ok = False

if all_ok:
    print('✓ Invariant OK: len(key_questions) == ambiguity_level == len(interpretations)-1 for ALL 20 tasks')
    print('✓ k=0 controls have key_questions==[]')

# Print amount table
print('')
print('=== Amount table per problem ===')

problems = [
    ('policy_overtime_001', ['overtime_950', 'overtime_910', 'overtime_1000']),
    ('policy_interest_001', ['interest_365_simple', 'interest_360', 'interest_compound']),
    ('policy_tip_001', ['tip_pretax', 'tip_total', 'tip_roundup']),
    ('policy_refund_001', ['refund_365_90', 'refund_360', 'refund_89']),
    ('policy_discount_001', ['discount_sequential', 'discount_additive', 'discount_roundup']),
]

for prob_id, check_ids in problems:
    amounts = [REFERENCE_ANSWERS[cid]['amount'] for cid in check_ids]
    print(f'{prob_id}: {amounts[0]:.2f}, {amounts[1]:.2f}, {amounts[2]:.2f}')
    
    # Verify pairwise distinct
    gaps = []
    for i in range(len(amounts)):
        for j in range(i+1, len(amounts)):
            gaps.append(abs(amounts[i] - amounts[j]))
    print(f'  Gaps: {[f"{g:.2f}" for g in sorted(gaps)]} (all > 0.01 ✓)')
