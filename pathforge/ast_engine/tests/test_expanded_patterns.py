from pathforge.ast_engine import classify_pattern, extract_features, sanitize_code
from pathforge.ast_engine.patterns import (
    ALL_PATTERNS,
    BINARY_SEARCH_STANDARD,
    DFS_ITERATIVE,
    FAST_SLOW_POINTERS,
    HEAP_TOP_K,
    PREFIX_SUM,
    TOPOLOGICAL_SORT,
)


def run_classifier(code_string):
    is_safe, errors, root = sanitize_code(code_string)
    assert is_safe, f"Sanitization failed: {errors}"
    return classify_pattern(extract_features(root))


def top_pattern(scores):
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)[0]


def test_classifier_returns_exact_taxonomy_keys():
    scores = run_classifier("def solve(nums):\n    return len(nums)\n")
    assert set(scores) == ALL_PATTERNS


def test_prefix_sum_uses_cumulative_array_not_frequency_proxy():
    code = """
def build_prefix(nums):
    pref = [0] * len(nums)
    pref[0] = nums[0]
    for i in range(1, len(nums)):
        pref[i] = pref[i - 1] + nums[i]
    return pref
"""
    scores = run_classifier(code)
    assert top_pattern(scores)[0] == PREFIX_SUM
    assert scores[PREFIX_SUM] >= 0.8


def test_iterative_dfs_uses_list_stack_ops():
    code = """
def reaches(graph, start, target):
    stack = [start]
    seen = set()
    while stack:
        node = stack.pop()
        if node == target:
            return True
        if node in seen:
            continue
        seen.add(node)
        for nxt in graph[node]:
            stack.append(nxt)
    return False
"""
    scores = run_classifier(code)
    assert top_pattern(scores)[0] == DFS_ITERATIVE
    assert scores[DFS_ITERATIVE] >= 0.8


def test_topological_sort_detects_indegree_queue_and_adjacency():
    code = """
from collections import deque

def can_finish(graph, indegree):
    q = deque()
    for node in range(len(indegree)):
        if indegree[node] == 0:
            q.append(node)
    order = []
    while q:
        node = q.popleft()
        order.append(node)
        for nxt in graph[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                q.append(nxt)
    return order
"""
    scores = run_classifier(code)
    assert top_pattern(scores)[0] == TOPOLOGICAL_SORT
    assert scores[TOPOLOGICAL_SORT] >= 0.8


def test_binary_search_standard():
    code = """
def search(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
"""
    scores = run_classifier(code)
    assert top_pattern(scores)[0] == BINARY_SEARCH_STANDARD
    assert scores[BINARY_SEARCH_STANDARD] >= 0.8


def test_heap_top_k():
    code = """
from heapq import heappush, heappop

def top_k(nums, k):
    heap = []
    for num in nums:
        heappush(heap, num)
        if len(heap) > k:
            heappop(heap)
    return heap
"""
    scores = run_classifier(code)
    assert top_pattern(scores)[0] == HEAP_TOP_K
    assert scores[HEAP_TOP_K] >= 0.8


def test_fast_slow_pointers():
    code = """
def has_cycle(head):
    slow = head
    fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast:
            return True
    return False
"""
    scores = run_classifier(code)
    assert top_pattern(scores)[0] == FAST_SLOW_POINTERS
    assert scores[FAST_SLOW_POINTERS] >= 0.8
