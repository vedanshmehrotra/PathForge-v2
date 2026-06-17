from pathforge.ast_engine.patterns import ALL_PATTERNS

HUMAN_READABLE_PATTERNS = {
    "hash_map_lookup": "Hash Map Lookup",
    "hash_map_frequency": "Hash Map Frequency",
    "prefix_sum": "Prefix Sum",
    "sliding_window_fixed": "Fixed Sliding Window",
    "sliding_window_variable": "Sliding Window",
    "two_pointers_opposite": "Two Pointers",
    "two_pointers_same": "Two Pointers (Same Direction)",
    "dfs_recursive": "Depth-First Search",
    "dfs_iterative": "Depth-First Search (Iterative)",
    "bfs_level_order": "Breadth-First Search",
    "bfs_shortest_path": "Breadth-First Search (Shortest Path)",
    "topological_sort": "Topological Sort",
    "union_find": "Union-Find",
    "binary_search_tree": "Binary Search Tree",
    "dp_1d_forward": "1D Dynamic Programming",
    "dp_1d_sequence": "1D Sequence DP",
    "dp_2d_grid": "2D Grid DP",
    "dp_2d_string": "2D String DP",
    "dp_knapsack": "Knapsack DP",
    "dp_interval": "Interval DP",
    "dp_state_machine": "State Machine DP",
    "fast_slow_pointers": "Fast & Slow Pointers",
    "linked_list_reversal": "Linked List Reversal",
    "monotonic_stack": "Monotonic Stack",
    "monotonic_deque": "Monotonic Deque",
    "binary_search_standard": "Binary Search",
    "binary_search_rotated": "Binary Search (Rotated)",
    "binary_search_answer": "Binary Search on Answer",
    "heap_top_k": "Heap / Top K",
    "greedy_local": "Greedy",
    "greedy_interval": "Greedy (Intervals)",
    "backtracking_permutation": "Backtracking (Permutations)",
    "backtracking_subset": "Backtracking (Subsets)",
}


def humanize_pattern(pattern):
    return HUMAN_READABLE_PATTERNS.get(pattern, pattern.replace("_", " ").title())


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
