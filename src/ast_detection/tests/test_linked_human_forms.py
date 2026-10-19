"""Authored syntax/relationship controls from the original-submission assessment.

These are pattern tests: sources are parsed, never executed. Judge acceptance,
functional correctness and optimality are deliberately not inferred.
"""
import ast
from textwrap import dedent

import pytest

from pathforge.api.services.analysis import run_analysis
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis


WINDOW = '''
def f(items, limit):
    counts = Counter()
    best = 0
    start = 0
    for end in range(len(items)):
        counts[items[end]] += 1
        while counts[items[end]] > limit:
            counts[items[start]] -= 1
            start += 1
        best = max(best, end-start+1)
    return best
'''
RANK = '''
def f(items):
    ranks = {}
    ordered = sorted(set(items))
    for index in range(len(ordered)):
        ranks.update({ordered[index]: index+1})
    answer = []
    for value in items:
        answer.append(ranks[value])
    return answer
'''
ROLLING = '''
def f(length):
    first = 1
    second = 1
    for position in range(length):
        first, second = second, first+second
    return first
'''
ENUMERATION = '''
def f(items):
    answer = 0
    for start in range(len(items)):
        distinct = set()
        for end in range(start, len(items)):
            distinct.add(items[end])
            answer += len(distinct)**2
    return answer
'''
SCAN_CHOICE = '''
def f(first, second, budget):
    while budget > 0:
        best = 0
        chosen = 0
        for index in range(len(first)):
            difference = abs(first[index]-second[index])
            if difference > best:
                best = difference
                chosen = index
        if best == 0:
            break
        if first[chosen] > second[chosen]:
            first[chosen] -= 1
        else:
            second[chosen] -= 1
        budget -= 1
    return first
'''
REACH = '''
def f(items):
    frontier = 0
    for index in range(len(items)):
        if frontier < index:
            return False
        frontier = max(frontier, index+items[index])
    return True
'''


def rename(source):
    tree = ast.parse(dedent(source))
    local = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    local |= {n.arg for n in ast.walk(tree) if isinstance(n, ast.arg)}
    names = {name: f'local_{i}' for i, name in enumerate(sorted(local))}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            node.id = names.get(node.id, node.id)
        elif isinstance(node, ast.arg):
            node.arg = names.get(node.arg, node.arg)
    return ast.unparse(tree)


def check(source, pattern, expected):
    result = run_analysis(dedent(source), accepted_solution_groups=[{'patterns': [pattern]}])
    assert 'error' not in result
    present = {p['pattern_id'] for p in result['ast']['detected_patterns']}
    assert (pattern in present) is expected
    assert (result['match_result']['match_result'] == 'FULL_MATCH') is expected
    assert all(0 <= p['confidence'] <= 1 for p in result['ast']['detected_patterns'])
    return result


@pytest.mark.parametrize('source,pattern', [
    (WINDOW, 'hash_map_frequency'), (RANK, 'hash_map_lookup'),
    (ROLLING, 'dp_1d_forward'), (ENUMERATION, 'brute_force'),
    (SCAN_CHOICE, 'greedy_local'), (WINDOW, 'sliding_window_variable'),
], ids=['counter-counts', 'rank-read', 'rolling-recurrence', 'subarray-set', 'scan-choice', 'window'])
@pytest.mark.parametrize('renamed', [False, True])
def test_linked_forms_reach_analysis_and_matching(source, pattern, renamed):
    check(rename(source) if renamed else source, pattern, True)


@pytest.mark.parametrize('source,pattern', [
    (REACH, 'sliding_window_variable'),
    ('def f(items):\n    unused={}\n    for item in items:\n        if item in [0,1]:\n            return True', 'hash_map_lookup'),
    ('def config():\n    unused={}\n    return unused\ndef f(items):\n    for item in items:\n        if item in [0,1]:\n            return True', 'hash_map_lookup'),
    (RANK.replace('ranks[value]', 'items[value]'), 'hash_map_lookup'),
    (RANK.replace('for value in items:', 'ranks = []\n    for value in items:'), 'hash_map_lookup'),
    (RANK.replace('for value in items:', 'consume(ranks)\n    for value in items:'), 'hash_map_lookup'),
    (RANK.replace('ranks.update({ordered[index]: index+1})', 'ranks.clear()'), 'hash_map_lookup'),
    (WINDOW.replace('    counts = Counter()', '    Counter = callback\n    counts = Counter()'), 'hash_map_frequency'),
    (WINDOW.replace('    counts = Counter()', '    counts = []'), 'hash_map_frequency'),
    (WINDOW.replace('        counts[items[end]] += 1', '        counts = other\n        counts[items[end]] += 1'), 'hash_map_frequency'),
    (WINDOW.replace('counts[items[start]] -= 1', 'unrelated -= tax'), 'sliding_window_variable'),
    (WINDOW.replace('        counts[items[end]] += 1', '        counts[other[end]] += 1'), 'sliding_window_variable'),
    (ROLLING.replace('second, first+second', 'second, second+1'), 'dp_1d_forward'),
    (ROLLING.replace('        first, second', '        first = 0\n        first, second'), 'dp_1d_forward'),
    (ROLLING.replace('second, first+second', 'second, callback(first,second)'), 'dp_1d_forward'),
    (ROLLING.replace('    return first', '    return length'), 'dp_1d_forward'),
    (ENUMERATION.replace('distinct.add(items[end])', 'distinct.add(items[0])'), 'brute_force'),
    (ENUMERATION.replace('        distinct = set()', '        distinct = set()').replace('answer += len(distinct)**2', 'answer += 1'), 'brute_force'),
    (ENUMERATION.replace('distinct.add(items[end])', 'distinct.add(items[end])\n            distinct.clear()'), 'brute_force'),
    (SCAN_CHOICE.replace('first[chosen] -= 1', 'first[0] -= 1').replace('second[chosen] -= 1', 'second[0] -= 1'), 'greedy_local'),
    (SCAN_CHOICE.replace('        if best == 0:', '        chosen = 0\n        if best == 0:'), 'greedy_local'),
    (SCAN_CHOICE.replace('chosen = index', 'chosen = 0'), 'greedy_local'),
], ids=['reach-is-not-window', 'unrelated-container', 'separate-scopes', 'other-map-read',
        'map-rebound', 'map-escaped', 'no-population', 'counter-rebound', 'list-not-counter',
        'count-state-rebound', 'scalar-tax', 'other-sequence', 'one-way-total', 'rolling-reset',
        'opaque-recurrence', 'unconsumed-recurrence', 'constant-subarray-read', 'unconsumed-set',
        'set-reset', 'unselected-mutation', 'choice-reset', 'unlinked-choice'])
@pytest.mark.parametrize('renamed', [False, True])
def test_disconnected_evidence_abstains(source, pattern, renamed):
    check(rename(source) if renamed else source, pattern, False)


def test_wrong_answer_window_still_contains_window_technique():
    # Omitting the last item is a correctness defect, not absence of a window.
    check(WINDOW.replace('range(len(items))', 'range(len(items)-1)'), 'sliding_window_variable', True)


def test_product_window_preserves_non_subtractive_maintenance():
    check('''
def f(items, limit):
    start = 0
    product = 1
    for end in range(len(items)):
        product *= items[end]
        while product >= limit:
            product //= items[start]
            start += 1
    return product
''', 'sliding_window_variable', True)


def test_enumerated_window_and_last_seen_jump_keep_element_link():
    source = WINDOW.replace('for end in range(len(items)):', 'for end, value in enumerate(items):').replace('counts[items[end]]', 'counts[value]')
    check(source, 'sliding_window_variable', True)
    check('''
def f(items):
    start = 0
    positions = {}
    best = 0
    for end, value in enumerate(items):
        if value in positions:
            start = max(start, positions[value]+1)
        positions[value] = end
        best = max(best, end-start+1)
    return best
''', 'sliding_window_variable', True)


def test_rolling_initial_state_cannot_survive_an_earlier_loop_rebinding():
    source = ROLLING.replace('    for position', '    for value in other:\n        first = callback(value)\n    for position')
    check(source, 'dp_1d_forward', False)


@pytest.mark.parametrize('replacement', ['import other as Counter', 'from other import Counter', 'Counter = callback'])
def test_nonstandard_counter_binding_is_not_an_ambient_standard_constructor(replacement):
    check(WINDOW.replace('    counts = Counter()', f'    {replacement}\n    counts = Counter()'), 'hash_map_frequency', False)


def test_shadowed_range_does_not_establish_window_driver():
    check(WINDOW.replace('def f(items, limit):', 'def f(items, limit, range):'), 'sliding_window_variable', False)


@pytest.mark.parametrize('escape', ['consume(counts)', 'alias = counts\n        alias.clear()'])
def test_unknown_window_state_escape_cannot_supply_maintenance(escape):
    check(WINDOW.replace('        counts[items[end]] += 1', f'        {escape}\n        counts[items[end]] += 1'), 'sliding_window_variable', False)


@pytest.mark.parametrize('escape', ['consume(distinct)', 'alias = distinct\n        alias.add(0)'])
def test_subarray_state_cannot_escape_between_initialization_and_enumeration(escape):
    source = ENUMERATION.replace('        for end', f'        {escape}\n        for end')
    check(source, 'brute_force', False)


@pytest.mark.parametrize('source', [WINDOW, RANK, ROLLING, ENUMERATION, SCAN_CHOICE])
def test_detection_preserves_submitted_ast(source):
    from src.ast_detection.detector_manager import DetectorManager
    tree = ast.parse(dedent(source))
    before = ast.dump(tree, include_attributes=True)
    DetectorManager().detect_all(tree)
    assert ast.dump(tree, include_attributes=True) == before


def test_correct_linked_set_membership_and_keyerror_lookup_survive():
    check('''
def f(items):
    seen = set()
    for item in items:
        if item in seen:
            return True
        seen.add(item)
''', 'hash_map_lookup', True)
    check('''
def f(items):
    ranks = {}
    for item in items:
        try:
            return ranks[item]
        except KeyError:
            ranks[item] = 1
''', 'hash_map_lookup', True)


@pytest.mark.parametrize('source', [REACH, RANK, ROLLING, ENUMERATION, SCAN_CHOICE])
def test_no_borrowed_canonical_window_or_search_conclusion(source):
    result = run_shadow_analysis(dedent(source))
    assert result is not None
    selected = result['strategy_selection']['submission']['selected']
    assert selected not in {'sliding_window', 'binary_search'}
