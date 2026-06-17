import csv, json
from collections import defaultdict

with open('pathforge/data/pathforge_problems_fixed.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

# Problem ID needs to match what DB uses. Let me see what IDs the CSV has
print('First 5 rows key columns:')
for r in rows[:5]:
    pats = json.loads(r['pattern'])
    print(f"  id={r['ID']} title={r['Title'][:40]} diff={r['Difficulty']} pattern={pats[0]}")

print(f'\nID range: {rows[0]["ID"]} to {rows[-1]["ID"]}')
print(f'Total rows: {len(rows)}')

# Group by difficulty + pattern
by_pat_diff = defaultdict(list)
for r in rows:
    pats = json.loads(r['pattern'])
    primary = pats[0]
    key = (primary, r['Difficulty'])
    by_pat_diff[key].append(r['ID'])

print(f'\nSample IDs for key pattern+difficulty combos:')
for (pat, diff), ids in sorted(by_pat_diff.items()):
    if len(ids) > 0:
        print(f'  {pat} / {diff}: IDs {ids[:3]}')
