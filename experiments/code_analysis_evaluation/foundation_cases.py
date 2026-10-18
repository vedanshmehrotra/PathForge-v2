"""Frozen, source-justified fixtures. Sources are parsed, never executed.

Corpus names locate code only: labels in evaluation_corpus are not imported.
Expectations below describe visible invariants, not functional-correctness grades.
The final five problem families are held out from implementation decisions.
"""
import ast
from pathlib import Path
import textwrap


def corpus_sources(names):
    path = Path(__file__).resolve().parents[2] / 'pathforge/ast_analysis/shadow/tests/evaluation_corpus.py'
    found = {}
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'add':
            name = ast.literal_eval(node.args[0])
            if name in names:
                found[name] = ast.literal_eval(node.args[1])
    if set(found) != set(names):
        raise ValueError(f'Missing source fixtures: {set(names) - set(found)}')
    return found


def renamed(code):
    """Rename locally bound identifiers consistently; preserve builtins/attributes."""
    tree = ast.parse(code)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    names.update(n.arg for n in ast.walk(tree) if isinstance(n, ast.arg))
    names.update(n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    mapping = {name: f'v_{i}' for i, name in enumerate(sorted(names - {'self', 'cls'}))}

    class Rename(ast.NodeTransformer):
        def visit_Name(self, node):
            node.id = mapping.get(node.id, node.id)
            return node

        def visit_arg(self, node):
            node.arg = mapping.get(node.arg, node.arg)
            return node

        def visit_FunctionDef(self, node):
            node.name = mapping.get(node.name, node.name)
            return self.generic_visit(node)

    return ast.unparse(Rename().visit(tree)) + '\n'


def cases():
    specs = [
        ('two_sum', 'hash_two_sum(self)', ['hash_map_lookup'], None,
         'Complement membership and original-index lookup share the dictionary.'),
        ('fixed_maximum_sum', 'fw_max_sum_k', ['sliding_window_fixed'], 'sliding_window',
         'One accumulator adds nums[i] and removes nums[i-k] at constant k.'),
        ('minimum_positive_sum', '''
def minimum_length(target, values):
    left = total = 0
    best = len(values) + 1
    for right in range(len(values)):
        total += values[right]
        while total >= target:
            best = min(best, right-left+1)
            total -= values[left]
            left += 1
    return best if best <= len(values) else 0
''', ['sliding_window_variable'], 'sliding_window',
         'For positive values, the inner guard shrinks the same content-maintained interval.'),
        ('unique_substring', 'sw_longest_substring', ['sliding_window_variable'], 'sliding_window',
         'Last-seen positions guard a monotone left jump; duplicates define window membership.'),
        ('classic_search', 'bs_renamed_vars', ['binary_search_standard'], 'binary_search',
         'Ordered arr[midpoint] comparison narrows that same interval by midpoint +/- 1.'),
        ('search_insertion', 'bs_find_insert', ['binary_search_standard'], 'binary_search',
         'Ordered indexed comparison narrows the interval; the final left bound is insertion position.'),
        ('ceiling_budget_search', 'bs_answer_space', ['binary_search_answer'], 'binary_search',
         'The local helper returns ceiling-sum <= budget for the actual midpoint candidate; positive piles/budget assumed.'),
        ('component_merging', 'uf_classic', ['union_find'], 'union_find',
         'Root traversal/path compression and representative linking share parent and find calls.'),
        ('bracket_matching', '''
def valid_brackets(text):
    stack = []
    pairs = {')': '(', ']': '[', '}': '{'}
    for char in text:
        if char in '([{':
            stack.append(char)
        elif not stack or stack.pop() != pairs[char]:
            return False
    return not stack
''', ['monotonic_stack'], None,
         'Ordinary LIFO pairing for bracket-only input, not ordered monotonic popping; stored monotonic expectation is intentionally unsuitable.'),
        ('nesting_depth', '''
def remove_outer(text):
    answer = ''
    depth = 0
    for char in text:
        if char == '(':
            if depth > 0:
                answer += char
            depth += 1
        else:
            depth -= 1
            if depth > 0:
                answer += char
    return answer
''', ['sliding_window_fixed'], None,
         'Nesting depth gates output; no incoming/outgoing interval maintenance. Stored window expectation is intentionally unsuitable.'),
        ('subarray_sum_counts', 'ps_subarray_sum_k', ['prefix_sum', 'hash_map_frequency'], None,
         'Cumulative sum and frequencies of prior totals are complementary components of one approach.'),
        ('top_k_frequency', '''
from collections import Counter
import heapq
def top_k(values, k):
    counts = Counter(values)
    heap = []
    for value, count in counts.items():
        heapq.heappush(heap, (count, value))
        if len(heap) > k:
            heapq.heappop(heap)
    return [value for count, value in heap]
''', ['hash_map_frequency', 'heap_top_k'], None,
         'Counter frequencies and a size-k min heap cooperate; frequency is not optional.'),
        ('tree_levels', 'bfs_level_order', ['bfs_level_order'], None,
         'A deque is drained one saved queue-length batch per tree depth; no shortest-path claim.'),
        ('permutations', '''
def permutations(values):
    result = []
    def visit(path, used):
        if len(path) == len(values):
            result.append(path[:])
            return
        for index in range(len(values)):
            if index not in used:
                used.add(index)
                path.append(values[index])
                visit(path, used)
                path.pop()
                used.remove(index)
    visit([], set())
    return result
''', ['backtracking_permutation'], None,
         'Recursive choice, used-index tracking and symmetric append/pop undo enumerate permutations.'),
        ('climbing_stairs', 'dp_climbing_stairs_bottomup', ['dp_1d_forward'], None,
         'A stored one-dimensional recurrence reads the previous two states, not just a running sum.'),
    ]
    corpus = corpus_sources({source for _, source, *_ in specs if '\n' not in source})
    result = []
    for index, (name, source, patterns, strategy, reason) in enumerate(specs):
        code = textwrap.dedent(corpus.get(source, source)).strip() + '\n'
        unsupported = name in {'bracket_matching', 'nesting_depth'}
        for suffix, variant in (('', code), ('_renamed', renamed(code))):
            result.append(dict(id=name + suffix, problem=name, code=variant, patterns=patterns,
                               expected_present=[] if unsupported else patterns,
                               expected_absent=patterns if unsupported else [],
                               expected_strategy=strategy, forbidden_strategies=['sliding_window'] if name == 'nesting_depth' else [],
                               expectation_reason=reason, split='held_out' if index >= 10 else 'development',
                               provenance='source inspection; corpus source only' if source in corpus else 'locally authored source fixture'))
    negatives = {
        'scalar_tax': ('''def running(values, tax):
    total = 0
    for i in range(len(values)):
        total += values[i]
        total -= tax
    return total
''', 'sliding_window_fixed', 'sliding_window', 'Unrelated scalar subtraction cannot maintain outgoing sequence content.'),
        'arbitrary_ready': ('''def scan(nums, target, ready):
    left, right = 0, len(nums)-1
    while left <= right:
        mid = (left+right)//2
        if ready or nums[mid] < target:
            left = mid+1
        else:
            right = mid-1
    return left
''', 'binary_search_standard', 'binary_search', 'The independent OR clause can decide narrowing without the indexed predicate.'),
        'parent_walk': ('''def ancestors(parent, node):
    while parent[node] != node:
        node = parent[node]
    return node
''', 'union_find', 'union_find', 'Parent traversal alone has no representative-based merge operation.'),
    }
    for name, (code, pattern, strategy, reason) in negatives.items():
        for suffix, variant in (('', code), ('_renamed', renamed(code))):
            result.append(dict(id=name + suffix, problem=name, code=variant, patterns=[pattern],
                               expected_present=[], expected_absent=[pattern], expected_strategy=None,
                               forbidden_strategies=[strategy], expectation_reason=reason,
                               split='negative', provenance='locally authored near miss'))
    return result
