# PathForge Pattern Taxonomy — single source of truth
# Exactly 33 patterns, matching pathforge_problems_fixed.csv

# ── Arrays & Hashing ─────────────────────────────────────────────────────────
HASH_MAP_LOOKUP          = "hash_map_lookup"
HASH_MAP_FREQUENCY       = "hash_map_frequency"
PREFIX_SUM               = "prefix_sum"
SLIDING_WINDOW_FIXED     = "sliding_window_fixed"
SLIDING_WINDOW_VARIABLE  = "sliding_window_variable"
TWO_POINTERS_OPPOSITE    = "two_pointers_opposite"
TWO_POINTERS_SAME        = "two_pointers_same"

# ── Graphs & Trees ────────────────────────────────────────────────────────────
DFS_RECURSIVE            = "dfs_recursive"
DFS_ITERATIVE            = "dfs_iterative"
BFS_LEVEL_ORDER          = "bfs_level_order"
BFS_SHORTEST_PATH        = "bfs_shortest_path"
TOPOLOGICAL_SORT         = "topological_sort"
UNION_FIND               = "union_find"
BINARY_SEARCH_TREE       = "binary_search_tree"

# ── Dynamic Programming ───────────────────────────────────────────────────────
DP_1D_FORWARD            = "dp_1d_forward"
DP_1D_SEQUENCE           = "dp_1d_sequence"
DP_2D_GRID               = "dp_2d_grid"
DP_2D_STRING             = "dp_2d_string"
DP_KNAPSACK              = "dp_knapsack"
DP_INTERVAL              = "dp_interval"
DP_STATE_MACHINE         = "dp_state_machine"

# ── Linked Lists & Stack ──────────────────────────────────────────────────────
FAST_SLOW_POINTERS       = "fast_slow_pointers"
LINKED_LIST_REVERSAL     = "linked_list_reversal"
MONOTONIC_STACK          = "monotonic_stack"
MONOTONIC_DEQUE          = "monotonic_deque"

# ── Binary Search ─────────────────────────────────────────────────────────────
BINARY_SEARCH_STANDARD   = "binary_search_standard"
BINARY_SEARCH_ROTATED    = "binary_search_rotated"
BINARY_SEARCH_ANSWER     = "binary_search_answer"

# ── Heap / Greedy / Backtracking ──────────────────────────────────────────────
HEAP_TOP_K               = "heap_top_k"
GREEDY_LOCAL             = "greedy_local"
GREEDY_INTERVAL          = "greedy_interval"
BACKTRACKING_PERMUTATION = "backtracking_permutation"
BACKTRACKING_SUBSET      = "backtracking_subset"

# ── Master set (used by validate_dataset.py) ──────────────────────────────────
ALL_PATTERNS = {
    HASH_MAP_LOOKUP, HASH_MAP_FREQUENCY, PREFIX_SUM,
    SLIDING_WINDOW_FIXED, SLIDING_WINDOW_VARIABLE,
    TWO_POINTERS_OPPOSITE, TWO_POINTERS_SAME,

    DFS_RECURSIVE, DFS_ITERATIVE,
    BFS_LEVEL_ORDER, BFS_SHORTEST_PATH,
    TOPOLOGICAL_SORT, UNION_FIND, BINARY_SEARCH_TREE,

    DP_1D_FORWARD, DP_1D_SEQUENCE,
    DP_2D_GRID, DP_2D_STRING, DP_KNAPSACK,
    DP_INTERVAL, DP_STATE_MACHINE,

    FAST_SLOW_POINTERS, LINKED_LIST_REVERSAL,
    MONOTONIC_STACK, MONOTONIC_DEQUE,

    BINARY_SEARCH_STANDARD, BINARY_SEARCH_ROTATED, BINARY_SEARCH_ANSWER,

    HEAP_TOP_K, GREEDY_LOCAL, GREEDY_INTERVAL,
    BACKTRACKING_PERMUTATION, BACKTRACKING_SUBSET,
}
