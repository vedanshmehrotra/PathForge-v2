"""Independent human-source relationships, not function-name/label oracles.

Sources are pinned in the fixture. Inputs are parsed, never executed. The
external full-corpus benchmark retains all unsupported/missed expectations.
"""
import ast
import json
from pathlib import Path

import pytest

from pathforge.api.services.analysis import run_analysis


CASES = json.loads((Path(__file__).parent / 'fixtures/relationship_forms.json').read_text())


@pytest.fixture(autouse=True)
def no_suppressed_detector_failures(caplog):
    yield
    assert not [r for r in caplog.records if r.name == 'src.ast_detection.detector_manager' and r.levelname == 'ERROR']


def renamed(source):
    tree = ast.parse(source)
    local = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    local |= {n.arg for n in ast.walk(tree) if isinstance(n, ast.arg)}
    aliases = {name: f'binding_{i}' for i, name in enumerate(sorted(local))}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            node.id = aliases.get(node.id, node.id)
        elif isinstance(node, ast.arg):
            node.arg = aliases.get(node.arg, node.arg)
        elif isinstance(node, (ast.Nonlocal, ast.Global)):
            node.names = [aliases.get(n, n) for n in node.names]
    return ast.unparse(tree)


def scores(code):
    result = run_analysis(code)
    assert 'error' not in result
    return {p['pattern_id']: p['confidence'] for p in result['ast']['detected_patterns']}


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
def test_relationships_are_invariant_to_identifier_renaming(case):
    assert scores(case['code']) == scores(renamed(case['code']))


@pytest.mark.parametrize('rename', [False, True])
@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
def test_source_relationships_reach_real_matching(case, rename):
    source = renamed(case['code']) if rename else case['code']
    observed = scores(source)
    assert set(case['expected_present']) <= observed.keys()
    assert not set(case['expected_absent']) & observed.keys()
    for pattern in case['expected_present']:
        result = run_analysis(source, accepted_solution_groups=[{'patterns': [pattern]}])
        assert result['match_result']['match_result'] == 'FULL_MATCH'


@pytest.mark.parametrize('code,pattern', [
    ('def solve(items):\n for k in range(1, len(items)):\n  items[k] = items[k-1] + items[k-2]\n return items', 'prefix_sum'),
    ('def solve(items):\n out=[]\n for x in items:\n  out.append(items[-1]+x)\n return out', 'prefix_sum'),
    ('def solve(a,b):\n while a < b:\n  def unrelated():\n   a.next\n  a += 1\n  if a == b: return True', 'fast_slow_pointers'),
    ('def solve(a,b):\n while a < b:\n  a += 1\n  count = 2\n  count -= 1', 'two_pointers_opposite'),
    ('def solve(a,b):\n while a < b:\n  a += 1\n  def unrelated():\n   b -= 1', 'two_pointers_opposite'),
    ('def visit(node, graph):\n for other in graph[node]:\n  pass\n return visit(node, graph)', 'dfs_recursive'),
    ('def visit(node, seen):\n seen.add(node)\n return visit(node, seen)', 'dfs_recursive'),
    ('def solve(a,b):\n while a and a.next:\n  if ready:\n   a = a.next.next\n  else:\n   b = b.next', 'fast_slow_pointers'),
])
def test_disconnected_and_borrowed_evidence_stays_negative(code, pattern):
    assert pattern not in scores(code)


@pytest.mark.parametrize('code', [
    'def solve(a):\n p=q=a[0]\n while True:\n  p=a[p]\n  q=a[a[q]]\n  if p == q: break\n return p',
    'def solve(head):\n p=q=head\n while q and q.next:\n  p=p.next\n  q=q.next.next\n return p',
])
def test_floyd_successor_forms_remain_supported(code):
    assert 'fast_slow_pointers' in scores(code)
    assert scores(code) == scores(renamed(code))


@pytest.mark.parametrize('code,pattern', [
    ('def solve(items,k):\n left=total=best=0\n for right in range(len(items)):\n  total += items[right]\n  while total > k:\n   total -= items[left]\n   left += 1\n  best=max(best,right-left+1)\n return best', 'sliding_window_variable'),
    ('def solve(items,k):\n n=len(items)\n total=sum(items[:n-k])\n for i in range(n-k,n):\n  total += items[i]\n  total -= items[i-(n-k)]\n return total', 'sliding_window_fixed'),
    ('class Solution:\n def solve(self,items):\n  result=[]\n  stack=[]\n  for item in items:\n   while stack and stack[-1] < item:\n    result.append(stack.pop())\n   stack.append(item)\n  return result', 'monotonic_stack'),
])
def test_equivalent_initialization_and_nested_expression_forms(code, pattern):
    assert pattern in scores(code)
    assert scores(code) == scores(renamed(code))


@pytest.mark.parametrize('code,pattern', [
    ('def solve(items):\n total=0\n for item in items:\n  total += item\n  if other.get(key): pass\n return total', 'prefix_sum'),
    ('def solve(items):\n totals=[0]*len(items)\n for i in range(1,len(items)):\n  totals=[0]*len(items)\n  totals[i]=totals[i-1]+items[i]\n return totals', 'prefix_sum'),
    ('def solve(n):\n table=[1]*n\n table=unknown\n for i in range(n):\n  for j in range(i):\n   table[i]=max(table[i],table[j]+1)\n return max(table)', 'dp_1d_sequence'),
    ('def solve(n):\n row=[1]*n\n row=unknown\n for i in range(n):\n  for j in range(1,n):\n   row[j]=row[j]+row[j-1]\n return row', 'dp_2d_grid'),
    ('def solve():\n queue=[0]\n count=0\n while queue:\n  for _ in range(len(queue)):\n   node=queue.pop(0)\n   for i in range(3): queue.append(i)\n  count += 1\n return count', 'bfs_shortest_path'),
])
def test_state_rebinding_and_unrelated_helpers_do_not_supply_links(code, pattern):
    assert pattern not in scores(code)


@pytest.mark.parametrize('mutation', [
    lambda code: code.replace('if nums[left] <= nums[mid]:', 'if ready or nums[left] <= nums[mid]:'),
    lambda code: code.replace('if nums[left] <= target < nums[mid]:', 'if ready or nums[left] <= target < nums[mid]:'),
    lambda code: code.replace('if nums[mid] == target:', 'mid = 0\n            if nums[mid] == target:'),
    lambda code: code.replace('right = mid - 1', 'right = other - 1').replace('left = mid + 1', 'left = other + 1'),
])
def test_rotated_search_does_not_borrow_unlinked_decisions(mutation):
    case = next(c for c in CASES if c['id'].startswith('81-'))
    assert 'binary_search_rotated' not in scores(mutation(case['code']))
