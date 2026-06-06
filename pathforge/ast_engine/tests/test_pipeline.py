from pathforge.ast_engine import sanitize_code, extract_features, classify_pattern
from pathforge.ast_engine.patterns import (
    DFS_RECURSIVE,
    HASH_MAP_LOOKUP,
    HASH_MAP_FREQUENCY,
    DP_1D_FORWARD,
    GREEDY_LOCAL
)

def run_pipeline(code):
    is_safe, errors, root = sanitize_code(code)
    if not is_safe:
        raise ValueError(f"Code rejected: {errors}")
    features = extract_features(root)
    scores = classify_pattern(features)
    return scores

def test_pipeline_dfs():
    dfs_code = """
def dfs(node):
    if not node:
        return
    dfs(node.left)
    dfs(node.right)
"""
    scores = run_pipeline(dfs_code)
    # The highest pattern score should be DFS_RECURSIVE
    sorted_patterns = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    assert sorted_patterns[0][0] == DFS_RECURSIVE
    assert sorted_patterns[0][1] >= 0.8

def test_pipeline_hashmap_lookup():
    lookup_code = """
def find_pairs(nums, target):
    lookup = set(nums)
    for x in nums:
        if (target - x) in lookup:
            return True
    return False
"""
    scores = run_pipeline(lookup_code)
    sorted_patterns = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    assert sorted_patterns[0][0] == HASH_MAP_LOOKUP
    assert sorted_patterns[0][1] >= 0.8

def test_pipeline_dp_1d():
    dp_code = """
def fibonacci(n):
    table = [0] * (n + 1)
    table[1] = 1
    for idx in range(2, n + 1):
        table[idx] = table[idx - 1] + table[idx - 2]
    return table[n]
"""
    scores = run_pipeline(dp_code)
    sorted_patterns = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    assert sorted_patterns[0][0] == DP_1D_FORWARD
    assert sorted_patterns[0][1] >= 0.9

def test_pipeline_greedy():
    greedy_code = """
def kadane(nums):
    current = 0
    best = float('-inf')
    for num in nums:
        current = max(num, current + num)
        best = max(best, current)
    return best
"""
    scores = run_pipeline(greedy_code)
    sorted_patterns = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    assert sorted_patterns[0][0] == GREEDY_LOCAL
    assert sorted_patterns[0][1] >= 0.9
