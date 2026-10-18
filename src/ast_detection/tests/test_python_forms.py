"""Real published implementations and adversarial syntax variants; never execute submissions.

Fixture expectations were source-reviewed before the readiness assessment.
The author's labels/comments are not the oracle. See fixture provenance/licences.
"""
import ast
import json
from pathlib import Path
from textwrap import dedent

import pytest

from pathforge.api.services.analysis import run_analysis
from src.ast_detection.detectors.backtracking_permutation import BacktrackingPermutationDetector
from src.ast_detection.detectors.dfs_recursive import DFSRecursiveDetector
from src.ast_detection.detectors.hash_map_lookup import HashMapLookupDetector
from src.ast_detection.detectors.sliding_window_fixed import SlidingWindowFixedDetector


CASES = json.loads((Path(__file__).parent / 'fixtures/published_python_forms.json').read_text())
DETECTORS = {
    'dfs_recursive': DFSRecursiveDetector,
    'backtracking_permutation': BacktrackingPermutationDetector,
    'hash_map_lookup': HashMapLookupDetector,
    'sliding_window_fixed': SlidingWindowFixedDetector,
}


def check(code, pattern, expected=True):
    code = dedent(code)
    direct = DETECTORS[pattern]().detect(ast.parse(code))
    result = run_analysis(code, accepted_solution_groups=[{'patterns': [pattern]}])
    assert 'error' not in result
    present = {p['pattern_id'] for p in result['ast']['detected_patterns']}
    assert direct.detected is expected
    assert (pattern in present) is expected
    assert (result['match_result']['match_result'] == 'FULL_MATCH') is expected
    return direct


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
def test_published_forms_reach_actual_matching(case):
    check(case['code'], case['expected_present'][0])


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
def test_published_forms_are_invariant_to_local_renaming(case):
    tree = ast.parse(case['code'])
    # Builtins, attributes other than local methods, and function names stay bound.
    identifiers = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    parameters = {n.arg for n in ast.walk(tree) if isinstance(n, ast.arg)}
    local = parameters | {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    aliases = {name: f'v_{i}' for i, name in enumerate(sorted(local & (identifiers | parameters)))}
    methods = {n.name: f'helper_{i}' for i, n in enumerate(ast.walk(tree))
               if isinstance(n, ast.FunctionDef)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            node.id = aliases.get(node.id, node.id)
        elif isinstance(node, ast.arg):
            node.arg = aliases.get(node.arg, node.arg)
        elif isinstance(node, ast.FunctionDef):
            node.name = methods[node.name]
        elif isinstance(node, ast.Attribute):
            node.attr = methods.get(node.attr, node.attr)
    check(ast.unparse(tree), case['expected_present'][0])


WINDOW = '''
def solve(values, width):
    {initial}
    for cursor in range(width, len(values)):
        total += values[cursor] - values[cursor-width]
        best = max(best, total)
    return best
'''


@pytest.mark.parametrize('initial', [
    'best = total = sum(values[:width])',
    'best, total = 0, sum(values[:width])',
    '(best, [total]) = (0, [sum(values[:width])])',
    'total: int = sum(values[:width]); best = total',
])
def test_window_initialization_forms(initial):
    check(WINDOW.format(initial=initial), 'sliding_window_fixed')


@pytest.mark.parametrize('initial', [
    'total = total = sum(values[:width]); best = total',
    'values = total = sum(values[:width]); best = total',
    'width, total = 5, sum(values[:width]); best = total',
    'total, total = sum(values[:width]), 0; best = total',
    'total, best = values; best = total',
    'total = sum(values[:width]); total = 0; best = total',
])
def test_ambiguous_or_rebound_window_initialization_stays_negative(initial):
    check(WINDOW.format(initial=initial), 'sliding_window_fixed', False)


TREE = '''
class TreeWalk:
    def visit(this, node):
        if node is None:
            return 0
        return 1 + max(this.visit(node.left), this.visit(node.right))
'''


def test_ordinary_instance_tree_recursion():
    check(TREE, 'dfs_recursive')


@pytest.mark.parametrize('code', [
    TREE.replace('this.visit', 'other.visit'),
    TREE.replace('if node is None:', 'this = other\n        if node is None:'),
    TREE.replace('if node is None:', 'this.visit = callback\n        if node is None:'),
    TREE + '\nTreeWalk.visit = callback\n',
    TREE.replace('    def visit', '    @staticmethod\n    def visit'),
    '''
def visit(node, visit):
    return visit(node.left)
''',
    '''
def visit(node):
    def unrelated():
        return visit(node.left)
    return 1
''',
    '''
def visit(node):
    def visit(node):
        return node
    return visit(node.left)
''',
    TREE.replace('this.visit(node.left)', 'this.visit(node)').replace('this.visit(node.right)', 'this.visit(node)'),
])
def test_unlinked_calls_cannot_establish_recursive_traversal(code):
    check(code, 'dfs_recursive', False)


@pytest.mark.parametrize('extra', [
    '    def visit(this, node):\n        return 0\n',
    '    def replace(this):\n        this.visit = callback\n',
])
def test_rebound_class_member_cannot_supply_recursion(extra):
    check(TREE + extra, 'dfs_recursive', False)


def test_method_recursion_cannot_borrow_unrelated_neighbor_loop():
    check('''
class Visitor:
    def visit(self, node, graph):
        for neighbor in graph[node]:
            print(neighbor)
        return self.visit(node, graph)
''', 'dfs_recursive', False)


def test_method_graph_recursion_is_linked_to_iterated_neighbor():
    check('''
class Visitor:
    def visit(self, node, graph, visited):
        visited.add(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                self.visit(neighbor, graph, visited)
''', 'dfs_recursive')
    check('''
class Visit:
    def f(that, x, edges):
        for y in edges[x]:
            that.f(y, edges)
''', 'dfs_recursive')


def test_method_numeric_branching_is_not_grid_traversal():
    check('''
class Numbers:
    def f(self, n):
        if n <= 2:
            return 1
        return self.f(n - 1) + self.f(n - 1) + self.f(n + 1)
''', 'dfs_recursive', False)


PERMUTATION = '''
class Arrangements:
    def collect(this, values, first, output):
        if first == len(values):
            output.append(values[:])
            return
        for cursor in range(first, len(values)):
            values[first], values[cursor] = values[cursor], values[first]
            this.collect(values, first + 1, output)
            values[first], values[cursor] = values[cursor], values[first]
'''


@pytest.mark.parametrize('code', [
    PERMUTATION.replace('this.collect(values, first + 1, output)', 'other.collect(values, first + 1, output)'),
    PERMUTATION.replace('this.collect(values, first + 1, output)', 'this.collect(values, first, output)'),
    PERMUTATION.replace('this.collect(values, first + 1, output)', 'this.collect(values, first, first + 1)'),
    PERMUTATION.replace('values[first], values[cursor]', 'values[0], values[1]').replace('values[cursor], values[first]', 'values[1], values[0]'),
    PERMUTATION.replace('this.collect(values, first + 1, output)', 'this.collect = callback\n            this.collect(values, first + 1, output)'),
])
def test_swaps_need_linked_range_and_advancing_recursive_parameter(code):
    check(code, 'backtracking_permutation', False)


def test_permutation_branching_does_not_establish_graph_traversal():
    check(PERMUTATION, 'dfs_recursive', False)


def test_exhaustive_generation_is_not_a_wrong_approach_by_definition():
    # Every subset is requested, so exhaustive enumeration is appropriate.
    # Total output size is Theta(n * 2**n). This is source justification,
    # not an optimality conclusion inferred from the detector or a runtime test.
    code = '''
def subsets(values):
    output = []
    for mask in range(1 << len(values)):
        part = []
        for position in range(len(values)):
            if mask & (1 << position):
                part.append(values[position])
        output.append(part)
    return output
'''
    result = run_analysis(dedent(code), accepted_solution_groups=[{'patterns': ['brute_force']}])
    assert result['match_result']['match_result'] == 'FULL_MATCH'
    assert result['match_result']['unmatched_patterns'] == []


LOOKUP = '''
def solve(values):
    positions = {{}}
    for i, value in enumerate(values):
        {before}
        try:
            return positions[value]
        except {exception}:
            positions[value] = i
'''


def test_keyerror_lookup_is_a_dictionary_technique():
    check(LOOKUP.format(before='', exception='KeyError'), 'hash_map_lookup')


@pytest.mark.parametrize('code', [
    LOOKUP.format(before='positions = []', exception='KeyError'),
    LOOKUP.format(before='', exception='IndexError'),
    LOOKUP.format(before='', exception='Exception'),
    LOOKUP.format(before='KeyError = RuntimeError', exception='KeyError'),
    LOOKUP.format(before='', exception='KeyError').replace('positions[value]', 'elsewhere[value]'),
    LOOKUP.format(before='', exception='KeyError').replace('return positions[value]', 'return callback(value)'),
    '''
def prepare():
    positions = {}
def solve(values):
    for value in values:
        try:
            return positions[value]
        except KeyError:
            pass
''',
    '''
def solve(values):
    positions = {}
    for value in values:
        def unrelated():
            try:
                return positions[value]
            except KeyError:
                pass
''',
])
def test_exception_lookup_requires_same_dictionary_loop_and_scope(code):
    check(code, 'hash_map_lookup', False)


@pytest.mark.parametrize('code', [
    'dict = list\n' + LOOKUP.format(before='', exception='KeyError').replace('positions = {}', 'positions = dict()'),
    'def wrapper(KeyError):\n' + '\n'.join('    '+line for line in dedent(LOOKUP.format(before='', exception='KeyError')).splitlines()),
])
def test_exception_lookup_does_not_assume_shadowed_builtin_bindings(code):
    check(code, 'hash_map_lookup', False)
