import csv, json
from collections import Counter, defaultdict

with open('pathforge/data/pathforge_problems_fixed.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

print(f'Total problems: {len(rows)}')

by_pattern = defaultdict(list)
for r in rows:
    pats = json.loads(r['pattern'])
    primary = pats[0] if pats else 'unknown'
    by_pattern[primary].append(r['Difficulty'])

print(f'\nPatterns with problems: {len(by_pattern)}')
print(f'\nPattern distribution by difficulty:')
for pat in sorted(by_pattern.keys()):
    diffs = Counter(by_pattern[pat])
    total = len(by_pattern[pat])
    items = ', '.join(f'{d}={c}' for d,c in sorted(diffs.items()))
    print(f'  {pat}: {total} total [{items}]')

zero_pat = ['binary_search_tree','dp_interval','dp_state_machine','sliding_window_fixed','topological_sort','union_find']
print(f'\nPatterns with zero problems:')
for p in zero_pat:
    if p not in by_pattern:
        print(f'  {p}')
