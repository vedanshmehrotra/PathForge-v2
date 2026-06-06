from pathforge.ast_engine.patterns import ALL_PATTERNS

LEETCODE_TAGS = {
    "hash_map_lookup": "hash-table",
    "hash_map_frequency": "hash-table",
    "prefix_sum": "prefix-sum",
    "sliding_window_fixed": "sliding-window",
    "sliding_window_variable": "sliding-window",
    "two_pointers_opposite": "two-pointers",
    "two_pointers_same": "two-pointers",
    "dfs_recursive": "depth-first-search",
    "dfs_iterative": "depth-first-search",
    "bfs_level_order": "breadth-first-search",
    "bfs_shortest_path": "breadth-first-search",
    "topological_sort": "topological-sort",
    "union_find": "union-find",
    "binary_search_tree": "binary-search-tree",
    "dp_1d_forward": "dynamic-programming",
    "dp_1d_sequence": "dynamic-programming",
    "dp_2d_grid": "dynamic-programming",
    "dp_2d_string": "dynamic-programming",
    "dp_knapsack": "dynamic-programming",
    "dp_interval": "dynamic-programming",
    "dp_state_machine": "dynamic-programming",
    "fast_slow_pointers": "linked-list",
    "linked_list_reversal": "linked-list",
    "monotonic_stack": "monotonic-stack",
    "monotonic_deque": "queue",
    "binary_search_standard": "binary-search",
    "binary_search_rotated": "binary-search",
    "binary_search_answer": "binary-search",
    "heap_top_k": "heap-priority-queue",
    "greedy_local": "greedy",
    "greedy_interval": "greedy",
    "backtracking_permutation": "backtracking",
    "backtracking_subset": "backtracking",
}


def leetcode_url(pattern, difficulty):
    """Return a LeetCode problemset URL for a PathForge pattern and difficulty."""
    tag = LEETCODE_TAGS.get(pattern, "algorithms")
    return f"https://leetcode.com/problemset/?topicSlugs={tag}&difficulty={difficulty.upper()}"


def pattern_options():
    """Return pattern options for UI dropdowns."""
    return [{"pattern": pattern, "label": pattern.replace("_", " ")} for pattern in sorted(ALL_PATTERNS)]
