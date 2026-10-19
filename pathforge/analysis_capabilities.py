"""Shared preparation/component capabilities, separate from rated skills.

The existing canonical mappings below are unchanged. Observational components
may be compared in an explicit proposed approach, but are never inserted into
canonical required concepts or the rated ALL_PATTERNS taxonomy. No detector,
B1 concept class, Shadow strategy rule or authority is inferred here.
"""
from pathforge.ast_engine.patterns import ALL_PATTERNS

OBSERVATION_PATTERN_IDS = frozenset({"array_traversal", "sorting", "brute_force"})
PREPARATION_PATTERN_IDS = frozenset(ALL_PATTERNS) | OBSERVATION_PATTERN_IDS

# Component definitions constrain proposals; they do not claim detector accuracy
# or that this list covers every valid solution to a problem.
PATTERN_DESCRIPTIONS = {
    "array_traversal": "Visiting sequence elements; broad structural observation only.",
    "sorting": "An explicit sorting operation; structural observation, not a strategy conclusion.",
    "brute_force": "Enumerating and checking candidate solutions, not merely nested loops; may be appropriate for required exhaustive output.",
    "hash_map_lookup": "Key-to-value lookup or membership in a mapping, not a recursion memo.",
    "hash_map_frequency": "Counting occurrences by key; ordinary indexing is insufficient.",
    "prefix_sum": "Additive prefix accumulation; not prefix products or an arbitrary running counter.",
    "sliding_window_fixed": "Maintain contents/state of a contiguous window at a fixed width with linked incoming/outgoing positions.",
    "sliding_window_variable": "Maintain a contiguous window with content-dependent boundary changes and corresponding state maintenance.",
    "two_pointers_opposite": "Two linked positions scanning toward one another.",
    "two_pointers_same": "Two linked positions advancing in the same direction.",
    "dfs_recursive": "Recursive depth-first traversal of connected nodes or child structure.",
    "dfs_iterative": "Depth-first traversal using an explicit stack; not an ordinary bracket stack.",
    "bfs_level_order": "Queue-based traversal organized by successive levels.",
    "bfs_shortest_path": "Breadth-first exploration of unweighted paths for distance or reachability.",
    "topological_sort": "Dependency ordering, such as indegree-based ready-node processing.",
    "union_find": "Linked representative lookup and root union over a shared parent structure.",
    "binary_search_tree": "Operations on ordered tree nodes, not merely a binary tree.",
    "dp_1d_forward": "Fill one-dimensional states using earlier states; a scalar update alone is insufficient.",
    "dp_1d_sequence": "Dynamic programming over sequence states and transitions.",
    "dp_2d_grid": "Dynamic programming over grid coordinates and predecessor states.",
    "dp_2d_string": "Dynamic programming over two string/sequence positions.",
    "dp_knapsack": "Capacity/choice dynamic programming with item-dependent transitions.",
    "dp_interval": "Dynamic programming over subinterval boundaries and smaller intervals.",
    "dp_state_machine": "Distinct dynamic-programming states with linked transitions, not arbitrary assignments.",
    "fast_slow_pointers": "Linked traversal at different advancement rates.",
    "linked_list_reversal": "Rewire next pointers to reverse a linked structure.",
    "monotonic_stack": "Maintain value ordering in a stack; ordinary bracket matching is not monotonic-stack maintenance.",
    "monotonic_deque": "Maintain ordered candidates in a deque with removals appropriate to a moving range.",
    "binary_search_standard": "A sequence interval, midpoint comparison and linked midpoint-based narrowing.",
    "binary_search_rotated": "Midpoint-based search over a rotated ordered sequence with partition decisions.",
    "binary_search_answer": "Midpoint-based narrowing of a candidate interval using a monotone feasibility decision; repeated doubling/subtraction alone is not binary search.",
    "heap_top_k": "Heap/priority-queue operations for ranked candidates; not arbitrary comparisons.",
    "greedy_local": "A local candidate-selection rule; not an arbitrary max/min expression.",
    "greedy_interval": "Interval ordering and selection/merging with linked interval comparisons.",
    "backtracking_permutation": "Enumerate arrangements with choice, recursive exploration and restoration.",
    "backtracking_subset": "Enumerate subsets/combinations with branch choices and state restoration.",
}


def prompt_pattern_vocabulary():
    """The same IDs accepted by preparation, with their actual component roles."""
    return "\n".join(f"- {name}: {PATTERN_DESCRIPTIONS[name]}" for name in sorted(PREPARATION_PATTERN_IDS))

# Maps legacy flat pattern IDs to V1 technique/strategy concepts.
# Each mapping produces required/optional/excluded lists.
# If a pattern cannot be mapped, it is preserved in diagnostic metadata.
PATTERN_TO_V1_MAPPING = {
    # Arrays & Hashing
    "hash_map_lookup": {
        "required": ["hash_lookup"],
        "optional": [],
        "excluded": ["recursive_branching"],
        "note": (
            "Key->value mapping lookup maps to hash_lookup. recursion is "
            "excluded: a dict used as a recursion memo has the same "
            "construction + membership shape but belongs to "
            "recursive_branching, not lookup."
        ),
    },
    "hash_map_frequency": {
        "required": ["frequency_counting"],
        "optional": ["hash_lookup"],
        "excluded": ["recursive_branching"],
        "note": (
            "Occurrence tallying maps to frequency_counting, with a mapping "
            "lookup as optional support. recursion is excluded: a dict used as "
            "a memo has the same construction shape but is not a tally."
        ),
    },
    "prefix_sum": {
        "required": ["sequential_accumulation"],
        "optional": ["iterative_table_filling"],
        "excluded": [],
        "note": "Prefix sum maps to sequential accumulation + optional table filling",
    },
    "sliding_window_fixed": {
        "required": ["sliding_window"],
        "optional": ["loop_state_tracking"],
        "excluded": ["two_pointers_opposite"],
        "note": "Fixed sliding window maps to sliding_window strategy",
    },
    "sliding_window_variable": {
        "required": ["sliding_window"],
        "optional": ["loop_state_tracking"],
        "excluded": ["two_pointers_opposite"],
        "note": "Variable sliding window maps to sliding_window strategy",
    },
    "two_pointers_opposite": {
        "required": ["two_pointers_opposite"],
        "optional": ["bidirectional_index_scan"],
        "excluded": ["binary_search"],
        "note": "Maps directly to two_pointers_opposite strategy",
    },
    "two_pointers_same": {
        "required": ["forward_pointer_advance"],
        "optional": [],
        "excluded": ["two_pointers_opposite"],
        "note": (
            "Same-direction two pointers map to forward_pointer_advance. "
            "bidirectional_index_scan is reserved for opposite-direction scans "
            "(it requires opposite_direction_updates) and cannot be produced "
            "by a same-direction implementation."
        ),
    },
    # Graphs & Trees
    "dfs_recursive": {
        "required": ["recursive_branching"],
        "optional": ["dfs_backtracking"],
        "excluded": ["bfs_shortest_path"],
        "note": "Recursive DFS maps to recursive_branching technique",
    },
    "dfs_iterative": {
        "required": [],
        "optional": [],
        "excluded": ["recursive_branching"],
        "note": "Iterative DFS has no direct V1 technique equivalent",
    },
    "bfs_level_order": {
        "required": ["bfs_shortest_path"],
        "optional": ["loop_state_tracking"],
        "excluded": ["recursive_branching"],
        "note": "Level-order BFS maps to bfs_shortest_path strategy",
    },
    "bfs_shortest_path": {
        "required": ["bfs_shortest_path"],
        "optional": [],
        "excluded": ["recursive_branching"],
        "note": "Maps directly to bfs_shortest_path strategy",
    },
    "topological_sort": {
        "required": [],
        "optional": ["bfs_shortest_path"],
        "excluded": [],
        "note": "No direct V1 technique; uses BFS-like traversal",
    },
    "union_find": {
        "required": ["union_find"],
        "optional": [],
        "excluded": [],
        "note": "Maps directly to union_find strategy",
    },
    "binary_search_tree": {
        "required": ["binary_search"],
        "optional": [],
        "excluded": ["two_pointers_opposite"],
        "note": "BST operations map to binary_search strategy",
    },
    # Dynamic Programming
    "dp_1d_forward": {
        "required": ["dp_bottom_up"],
        "optional": ["iterative_table_filling"],
        "excluded": ["recursive_branching"],
        "note": "1D forward DP maps to dp_bottom_up strategy",
    },
    "dp_1d_sequence": {
        "required": ["dp_bottom_up"],
        "optional": ["iterative_table_filling"],
        "excluded": ["recursive_branching"],
        "note": "1D sequence DP maps to dp_bottom_up strategy",
    },
    "dp_2d_grid": {
        "required": ["dp_bottom_up"],
        "optional": ["iterative_table_filling"],
        "excluded": ["recursive_branching"],
        "note": "2D grid DP maps to dp_bottom_up strategy",
    },
    "dp_2d_string": {
        "required": ["dp_bottom_up"],
        "optional": ["iterative_table_filling"],
        "excluded": ["recursive_branching"],
        "note": "2D string DP maps to dp_bottom_up strategy",
    },
    "dp_knapsack": {
        "required": ["dp_bottom_up"],
        "optional": ["iterative_table_filling"],
        "excluded": ["recursive_branching"],
        "note": "Knapsack DP maps to dp_bottom_up strategy",
    },
    "dp_interval": {
        "required": ["dp_bottom_up"],
        "optional": ["iterative_table_filling"],
        "excluded": ["recursive_branching"],
        "note": "Interval DP maps to dp_bottom_up strategy",
    },
    "dp_state_machine": {
        "required": ["dp_bottom_up"],
        "optional": ["iterative_table_filling"],
        "excluded": ["recursive_branching"],
        "note": "State machine DP maps to dp_bottom_up strategy",
    },
    # Linked Lists & Stack
    "fast_slow_pointers": {
        "required": ["forward_pointer_advance"],
        "optional": [],
        "excluded": [],
        "note": (
            "Fast/slow pointers are same-direction progression and map to "
            "forward_pointer_advance (multiple_pointer_traversal evidence)."
        ),
    },
    "linked_list_reversal": {
        "required": ["linked_list_traversal"],
        "optional": [],
        "excluded": ["two_pointers_opposite"],
        "note": "Linked-list reversal maps to linked_list_traversal technique (requires pointer manipulation)",
    },
    "monotonic_stack": {
        "required": ["monotonic_stack_maintenance"],
        "optional": [],
        "excluded": [],
        "note": "Monotonic stack maps to monotonic_stack_maintenance technique",
    },
    "monotonic_deque": {
        "required": ["monotonic_stack_maintenance"],
        "optional": [],
        "excluded": [],
        "note": "Monotonic deque maps to monotonic_stack_maintenance technique (deque = stack variant)",
    },
    # Binary Search
    "binary_search_standard": {
        "required": ["binary_search"],
        "optional": ["bidirectional_index_scan"],
        "excluded": ["two_pointers_opposite"],
        "note": "Maps directly to binary_search strategy",
    },
    "binary_search_rotated": {
        "required": ["binary_search"],
        "optional": ["bidirectional_index_scan"],
        "excluded": ["two_pointers_opposite"],
        "note": "Maps to binary_search strategy (rotated variant)",
    },
    "binary_search_answer": {
        "required": ["binary_search"],
        "optional": ["bidirectional_index_scan"],
        "excluded": ["two_pointers_opposite"],
        "note": "Maps to binary_search strategy (answer-space variant)",
    },
    # Heap / Greedy / Backtracking
    "heap_top_k": {
        "required": [],
        "optional": [],
        "excluded": [],
        "note": "No direct V1 technique for heap operations",
    },
    "greedy_local": {
        "required": ["candidate_selection"],
        "optional": ["sequential_accumulation"],
        "excluded": ["sliding_window"],
        "note": (
            "Vocabulary Layer 2: greedy local decisions map to the "
            "candidate_selection technique, which has two structural forms: "
            "(1) loop + conditional branch + scalar candidate replacement, "
            "non-index participating; (2) sorting_operation + bounded read "
            "of the same sequence (extremum_access). sliding_window is "
            "excluded: conditionally-updated window state participates as a "
            "subscript index and is not candidate selection."
        ),
    },
    "greedy_interval": {
        "required": [],
        "optional": [],
        "excluded": [],
        "note": "No direct V1 technique for interval greedy",
    },
    "backtracking_permutation": {
        "required": ["dfs_backtracking"],
        "optional": ["recursive_branching"],
        "excluded": ["dp_top_down"],
        "note": "Maps to dfs_backtracking strategy",
    },
    "backtracking_subset": {
        "required": ["dfs_backtracking"],
        "optional": ["recursive_branching"],
        "excluded": ["dp_top_down"],
        "note": "Maps to dfs_backtracking strategy",
    },
}

CANONICAL_UNMAPPED_PATTERN_IDS = frozenset(
    pattern for pattern in PREPARATION_PATTERN_IDS
    if not PATTERN_TO_V1_MAPPING.get(pattern, {}).get("required")
)


def has_pattern_only_coverage(group):
    """Recognize a known canonical gap, never an unknown or conflicting gap.

    This permits only a listed-pattern comparison. It does not make the group
    canonically matchable or eligible to update skills.
    """
    patterns = group.get("patterns")
    missing = group.get("unmapped_patterns")
    if (not isinstance(patterns, list) or not patterns
            or not all(isinstance(p, str) for p in patterns)
            or not isinstance(missing, list) or not all(isinstance(p, str) for p in missing)
            or type(group.get("matchable")) is not bool):
        return False
    declared = set(patterns)
    known_gaps = declared & CANONICAL_UNMAPPED_PATTERN_IDS
    return bool(known_gaps) and declared <= PREPARATION_PATTERN_IDS and set(missing) == known_gaps
