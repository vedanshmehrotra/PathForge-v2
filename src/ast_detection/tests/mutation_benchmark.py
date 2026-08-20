"""Deterministic Mutation Benchmark for AST Detectors.

Tests semantic-preserving mutations across detectors to measure robustness.
"""

import ast
from collections import defaultdict
from src.ast_detection.registry import get_all_detectors

# ============================================================================
# MUTATION DEFINITIONS
# ============================================================================

# (detector_id, category, mutation_name, code, expected_detected)
MUTATIONS = [
    # === NAMING MUTATIONS ===
    ('binary_search_standard', 'naming', 'left_right_to_start_end', '''
start, end = 0, len(nums) - 1
while start <= end:
    mid = (start + end) // 2
    if nums[mid] == target:
        return mid
    elif nums[mid] < target:
        start = mid + 1
    else:
        end = mid - 1
return -1
''', True),

    ('binary_search_standard', 'naming', 'left_right_to_a_b', '''
a, b = 0, len(nums) - 1
while a <= b:
    m = (a + b) // 2
    if nums[m] == target:
        return m
    elif nums[m] < target:
        a = m + 1
    else:
        b = m - 1
return -1
''', True),

    ('binary_search_standard', 'naming', 'mid_to_middle', '''
left, right = 0, len(nums) - 1
while left <= right:
    middle = (left + right) // 2
    if nums[middle] == target:
        return middle
    elif nums[middle] < target:
        left = middle + 1
    else:
        right = middle - 1
return -1
''', True),

    ('two_pointers_opposite', 'naming', 'left_right_to_lo_hi', '''
lo, hi = 0, len(arr) - 1
while lo < hi:
    if arr[lo] + arr[hi] == target:
        return [lo, hi]
    elif arr[lo] + arr[hi] < target:
        lo += 1
    else:
        hi -= 1
''', True),

    ('two_pointers_opposite', 'naming', 'left_right_to_i_j', '''
i, j = 0, len(arr) - 1
while i < j:
    if arr[i] + arr[j] == target:
        return [i, j]
    elif arr[i] + arr[j] < target:
        i += 1
    else:
        j -= 1
''', True),

    ('sliding_window_fixed', 'naming', 'window_sum_to_ws', '''
ws = 0
l = 0
for r in range(len(nums)):
    ws += nums[r]
    if r >= k - 1:
        result = max(result, ws / k)
        ws -= nums[l]
        l += 1
''', True),

    ('dfs_recursive', 'naming', 'graph_dfs_seen_name', '''
def solve(node, g, seen):
    if node in seen:
        return
    seen.add(node)
    for nb in g[node]:
        solve(nb, g, seen)
''', True),

    ('hash_map_lookup', 'naming', 'seen_to_lookup', '''
lookup = {}
for i, n in enumerate(nums):
    diff = target - n
    if diff in lookup:
        return [lookup[diff], i]
    lookup[n] = i
''', True),

    ('dp_1d_forward', 'naming', 'dp_to_table', '''
def climb(n):
    table = [0] * (n + 1)
    table[1] = 1
    table[2] = 2
    for i in range(3, n + 1):
        table[i] = table[i-1] + table[i-2]
    return table[n]
''', True),

    ('dp_1d_forward', 'naming', 'dp_to_memo', '''
def climb(n):
    memo = [0] * (n + 1)
    memo[1] = 1
    memo[2] = 2
    for i in range(3, n + 1):
        memo[i] = memo[i-1] + memo[i-2]
    return memo[n]
''', True),

    ('topological_sort', 'naming', 'indeg_to_count', '''
from collections import deque
count = [0] * n
for u in range(n):
    for v in adj[u]:
        count[v] += 1
q = deque([i for i in range(n) if count[i] == 0])
result = []
while q:
    u = q.popleft()
    result.append(u)
    for v in adj[u]:
        count[v] -= 1
        if count[v] == 0:
            q.append(v)
''', True),

    ('union_find', 'structural', 'functional_uf', '''
parent = list(range(n))
rank = [0] * n

def find(x):
    if parent[x] != x:
        parent[x] = find(parent[x])
    return parent[x]

def union(x, y):
    rx, ry = find(x), find(y)
    if rx == ry: return
    if rank[rx] < rank[ry]:
        parent[rx] = ry
    elif rank[rx] > rank[ry]:
        parent[ry] = rx
    else:
        parent[ry] = rx
        rank[rx] += 1
''', True),

    ('dp_2d_grid', 'naming', 'dp_to_grid', '''
def minPath(grid):
    m, n = len(grid), len(grid[0])
    g = [[0]*n for _ in range(m)]
    g[0][0] = grid[0][0]
    for i in range(1, m): g[i][0] = g[i-1][0] + grid[i][0]
    for j in range(1, n): g[0][j] = g[0][j-1] + grid[0][j]
    for i in range(1, m):
        for j in range(1, n):
            g[i][j] = min(g[i-1][j], g[i][j-1]) + grid[i][j]
    return g[m-1][n-1]
''', True),

    ('greedy_local', 'naming', 'best_to_mv', '''
def maxSubArray(nums):
    cur = 0
    mv = float('-inf')
    for x in nums:
        cur = max(x, cur + x)
        mv = max(mv, cur)
    return mv
''', True),

    ('linked_list_reversal', 'naming', 'prev_to_p_curr_to_c', '''
def reverse(head):
    p = None
    c = head
    while c:
        n = c.next
        c.next = p
        p = c
        c = n
    return p
''', True),

    # === EXPRESSION MUTATIONS ===
    ('binary_search_standard', 'expression', 'midpoint_alt', '''
left, right = 0, len(nums) - 1
while left <= right:
    mid = left + (right - left) // 2
    if nums[mid] == target:
        return mid
    elif nums[mid] < target:
        left = mid + 1
    else:
        right = mid - 1
return -1
''', True),

    ('binary_search_standard', 'expression', 'while_not_gt', '''
left, right = 0, len(nums) - 1
while not left > right:
    mid = (left + right) // 2
    if nums[mid] == target:
        return mid
    elif nums[mid] < target:
        left = mid + 1
    else:
        right = mid - 1
return -1
''', True),

    ('two_pointers_opposite', 'expression', 'while_not_ge', '''
left, right = 0, len(arr) - 1
while not left >= right:
    if arr[left] + arr[right] == target:
        return [left, right]
    elif arr[left] + arr[right] < target:
        left += 1
    else:
        right -= 1
''', True),

    # === STRUCTURAL MUTATIONS ===
    ('two_pointers_opposite', 'structural', 'while_with_break', '''
left, right = 0, len(arr) - 1
while True:
    if left >= right:
        break
    if arr[left] + arr[right] == target:
        return [left, right]
    elif arr[left] + arr[right] < target:
        left += 1
    else:
        right -= 1
''', True),

    ('bfs_level_order', 'structural', 'list_as_queue', '''
def levelOrder(root):
    if not root:
        return []
    result = []
    queue = [root]
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.pop(0)
            level.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        result.append(level)
    return result
''', True),

    ('dfs_recursive', 'structural', 'with_helper', '''
def countIslands(grid):
    count = 0
    for i in range(len(grid)):
        for j in range(len(grid[0])):
            if grid[i][j] == '1':
                _dfs(grid, i, j)
                count += 1
    return count

def _dfs(grid, i, j):
    if i < 0 or j < 0 or i >= len(grid) or j >= len(grid[0]):
        return
    if grid[i][j] != '1':
        return
    grid[i][j] = '0'
    _dfs(grid, i+1, j)
    _dfs(grid, i-1, j)
    _dfs(grid, i, j+1)
    _dfs(grid, i, j-1)
''', True),

    # === VARIANT MUTATIONS ===
    ('binary_search_standard', 'variant', 'class_based', '''
class BinarySearch:
    def search(self, nums, target):
        left, right = 0, len(nums) - 1
        while left <= right:
            mid = (left + right) // 2
            if nums[mid] == target:
                return mid
            elif nums[mid] < target:
                left = mid + 1
            else:
                right = mid - 1
        return -1
''', True),

    ('hash_map_lookup', 'variant', 'class_based', '''
class TwoSum:
    def twoSum(self, nums, target):
        seen = {}
        for i, n in enumerate(nums):
            diff = target - n
            if diff in seen:
                return [seen[diff], i]
            seen[n] = i
''', True),

    ('dp_1d_forward', 'variant', 'class_based', '''
class Solution:
    def climbStairs(self, n):
        if n <= 2:
            return n
        dp = [0] * (n + 1)
        dp[1] = 1
        dp[2] = 2
        for i in range(3, n + 1):
            dp[i] = dp[i-1] + dp[i-2]
        return dp[n]
''', True),

    ('greedy_local', 'variant', 'class_based', '''
class Solution:
    def maxSubArray(self, nums):
        current = 0
        best = float('-inf')
        for num in nums:
            current = max(num, current + num)
            best = max(best, current)
        return best
''', True),

    ('bfs_level_order', 'variant', 'class_based', '''
from collections import deque
class Solution:
    def levelOrder(self, root):
        if not root:
            return []
        result = []
        queue = deque([root])
        while queue:
            level = []
            for _ in range(len(queue)):
                node = queue.popleft()
                level.append(node.val)
                if node.left:
                    queue.append(node.left)
                if node.right:
                    queue.append(node.right)
            result.append(level)
        return result
''', True),
]


def run_mutation_benchmark():
    all_detectors = {d.pattern_id: d for d in get_all_detectors()}

    print('=' * 80)
    print('  MUTATION BENCHMARK RESULTS')
    print('=' * 80)
    print()

    total = 0
    full_pass = 0
    partial_pass = 0
    fail = 0

    results_by_category = defaultdict(lambda: {'pass': 0, 'partial': 0, 'fail': 0, 'total': 0})
    results_by_detector = defaultdict(lambda: {'pass': 0, 'partial': 0, 'fail': 0, 'total': 0})
    failures = []

    for det_id, category, mut_name, code, expected_detected in MUTATIONS:
        detector = all_detectors[det_id]
        try:
            tree = ast.parse(code)
            result = detector.detect(tree)
            total += 1

            detected = result.detected
            conf = result.confidence

            if detected and expected_detected:
                if conf >= 0.5:
                    status = 'PASS'
                    full_pass += 1
                else:
                    status = 'PARTIAL'
                    partial_pass += 1
            elif not detected and not expected_detected:
                status = 'PASS'
                full_pass += 1
            elif detected and not expected_detected:
                status = 'UNEXPECTED'
                fail += 1
            else:
                status = 'FAIL'
                fail += 1
                failures.append((det_id, mut_name, conf))

            results_by_category[category][status.lower().replace('unexpected', 'fail')] += 1
            results_by_category[category]['total'] += 1
            results_by_detector[det_id][status.lower().replace('unexpected', 'fail')] += 1
            results_by_detector[det_id]['total'] += 1

            print(f'  {status:<12} {det_id:<25} {category:<12} {mut_name:<40} conf={conf:.2f}')
        except Exception as e:
            total += 1
            fail += 1
            failures.append((det_id, mut_name, 0.0))
            results_by_category[category]['fail'] += 1
            results_by_category[category]['total'] += 1
            results_by_detector[det_id]['fail'] += 1
            results_by_detector[det_id]['total'] += 1
            print(f'  ERROR      {det_id:<25} {category:<12} {mut_name:<40} {e}')

    print()
    print('=' * 80)
    print('  MUTATION BENCHMARK SUMMARY')
    print('=' * 80)
    print()
    print(f'  Total mutations:         {total}')
    print(f'  Full pass (conf>=0.5):   {full_pass} ({full_pass / total * 100:.1f}%)')
    print(f'  Partial pass (conf<0.5): {partial_pass} ({partial_pass / total * 100:.1f}%)')
    print(f'  Complete fail:           {fail} ({fail / total * 100:.1f}%)')
    print()
    print('  By category:')
    for cat in sorted(results_by_category.keys()):
        r = results_by_category[cat]
        print(f'    {cat:<15} {r["total"]:>3} mutations: {r["pass"]} pass, {r["partial"]} partial, {r["fail"]} fail')
    print()
    print('  By detector:')
    for det_id in sorted(results_by_detector.keys()):
        r = results_by_detector[det_id]
        if r['total'] > 0:
            print(f'    {det_id:<28} {r["pass"]:>2}/{r["total"]} pass, {r["partial"]:>2} partial, {r["fail"]:>2} fail')
    print()
    if failures:
        print('  Failures:')
        for det, mut, conf in failures:
            print(f'    {det} / {mut} (conf={conf:.2f})')


if __name__ == '__main__':
    run_mutation_benchmark()
