"""Run validation and show results."""

from pathlib import Path
from bench.build import load_tasks
from bench.code_spec import get_checkers_and_candidates
from bench.validate import validate_domain

# Run validation
summary = validate_domain('code_spec', Path('bench/data/code_spec.jsonl'), get_checkers_and_candidates)

print('=== Validation Summary ===')
print(f'Tasks: {summary["total_tasks"]}')
print(f'Distinguishable: {summary["distinguishable_count"]} / {summary["total_tasks"]} ({summary["distinguishable_pct"]:.1f}%)')
print(f'Ambiguity distribution: {summary["ambiguity_distribution"]}')

if summary['failed_tasks']:
    print(f'\nFailed tasks: {len(summary["failed_tasks"])}')
    for failed in summary['failed_tasks']:
        print(f'  - {failed["task_id"]}: {failed["reason"]}')
else:
    print('\n✓ All tasks passed validation!')
