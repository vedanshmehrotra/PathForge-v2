"""Qualification, not name/label matching. Submitted code is parsed, never run.

Published snippets retain provenance in the fixture and the adjacent MIT notices.
Other cases are explicitly synthetic. Expected abstention means insufficient
supported evidence, not a proof that the submitted algorithm is incorrect.
"""
import ast
import hashlib
import json
from pathlib import Path

import pytest

from pathforge.api.services.analysis import run_analysis
from src.ast_detection.detectors.brute_force import BruteForceDetector
from src.ast_detection.detectors.dp_state_machine import DPStateMachineDetector
from src.ast_detection.detectors.greedy_local import GreedyLocalDetector


CASES = json.loads((Path(__file__).parent / 'fixtures/qualification_cases.json').read_text())
DETECTORS = {'brute_force': BruteForceDetector, 'dp_state_machine': DPStateMachineDetector,
             'greedy_local': GreedyLocalDetector}


def renamed(code):
    tree = ast.parse(code)
    builtin_names = {'range', 'len', 'max', 'min', 'float', 'print', 'sum', 'set', 'list'}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} - builtin_names
    names |= {n.arg for n in ast.walk(tree) if isinstance(n, ast.arg)}
    names |= {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    methods = {n.name for cls in ast.walk(tree) if isinstance(cls, ast.ClassDef)
               for n in cls.body if isinstance(n, ast.FunctionDef)}
    aliases = {name: f'v_{i}' for i, name in enumerate(sorted(names))}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            node.id = aliases.get(node.id, node.id)
        elif isinstance(node, ast.arg):
            node.arg = aliases[node.arg]
        elif isinstance(node, ast.FunctionDef):
            node.name = aliases[node.name]
        elif isinstance(node, ast.Attribute) and node.attr in methods:
            node.attr = aliases[node.attr]
    return ast.unparse(tree)


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
@pytest.mark.parametrize('rename', [False, True], ids=['source', 'renamed'])
def test_qualified_claim_reaches_real_analysis_and_matching(case, rename):
    assert hashlib.sha256(case['code'].encode()).hexdigest() == case['code_sha256']
    code = renamed(case['code']) if rename else case['code']
    tree = ast.parse(code)
    before = ast.dump(tree, include_attributes=True)
    result = DETECTORS[case['pattern']]().detect(tree)
    assert ast.dump(tree, include_attributes=True) == before, 'Submitted AST was mutated'
    assert result.detected is case['expected']
    actual = run_analysis(code, accepted_solution_groups=[{'patterns': [case['pattern']]}])
    assert 'error' not in actual
    found = {p['pattern_id'] for p in actual['ast']['detected_patterns']}
    assert (case['pattern'] in found) is case['expected']
    assert (actual['match_result']['match_result'] == 'FULL_MATCH') is case['expected']


@pytest.mark.parametrize('pattern', DETECTORS)
def test_disconnected_functions_cannot_pool_qualification(pattern):
    code = '''
def loop(values):
    total = 0
    for item in values:
        total += item
    return total
def report(values):
    return max(values)
'''
    assert not DETECTORS[pattern]().detect(ast.parse(code)).detected


@pytest.mark.parametrize('after', [
    'states.clear()',
    'del states[0]',
    'states = [0, 0]',
    'consume(states)',
    'alias = states\n        alias.clear()',
])
def test_state_recurrence_cannot_survive_an_unknown_mutation_or_reset(after):
    code = f'''
def f(values):
    states = [0, 0]
    for value in values:
        states[0], states[1] = max(states[0], states[1] + value), max(states[1], states[0] - value)
        {after}
    return states[0]
'''
    assert not DPStateMachineDetector().detect(ast.parse(code)).detected


def test_prefix_choice_reward_survives_local_aliases_and_renaming():
    code = '''
def f(values):
    least = values[0]
    record = 0
    for i in range(1, len(values)):
        if values[i] < least:
            least = values[i]
        else:
            difference = values[i] - least
            if difference > record:
                record = difference
    return record
'''
    for source in (code, renamed(code)):
        assert GreedyLocalDetector().detect(ast.parse(source)).detected


@pytest.mark.parametrize('reward', ['opaque(values[i], least)', 'unrelated'])
def test_opaque_or_disconnected_reward_cannot_supply_local_choice(reward):
    code = f'''
def f(values):
    least = values[0]
    record = 0
    for i in range(1, len(values)):
        least = min(least, values[i])
        difference = {reward}
        record = max(record, difference)
    return record
'''
    assert not GreedyLocalDetector().detect(ast.parse(code)).detected


def test_iterative_candidate_construction_is_exhaustive_output_not_a_penalty():
    code = '''
def f(values):
    results = [[]]
    for i in range(len(values)):
        count = len(results)
        for j in range(count):
            candidate = list(results[j])
            candidate.append(values[i])
            results.append(candidate)
    return results
'''
    for source in (code, renamed(code)):
        result = run_analysis(source, accepted_solution_groups=[{'patterns': ['brute_force']}])
        assert result['match_result']['match_result'] == 'FULL_MATCH'


@pytest.mark.parametrize('invalidate', [
    'candidate.clear()',
    'other = candidate\n            other.clear()',
    'if ready:\n                candidate.clear()',
])
def test_constructed_candidate_cannot_borrow_content_after_invalidation(invalidate):
    code = f'''
def f(values, ready):
    results = [[]]
    for i in range(len(values)):
        count = len(results)
        for j in range(count):
            candidate = list(results[j])
            candidate.append(values[i])
            {invalidate}
            results.append(candidate)
    return results
'''
    assert not BruteForceDetector().detect(ast.parse(code)).detected


@pytest.mark.parametrize('pattern,source', [
    ('greedy_local', '''
def f(values, max):
    current = values[0]
    for i in range(1, len(values)):
        current = max(values[i], current + values[i])
    return current
'''),
    ('brute_force', '''
def f(values, range):
    for i in range(len(values)):
        for j in range(len(values)):
            print(i, j)
'''),
])
def test_shadowed_builtins_do_not_establish_qualification(pattern, source):
    assert not DETECTORS[pattern]().detect(ast.parse(source)).detected
