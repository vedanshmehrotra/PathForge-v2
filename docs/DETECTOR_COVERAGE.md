# Detector Coverage

This document tracks the implementation status of all 33 pattern detectors in the V2 AST Analysis Engine.

| # | Pattern ID | Batch | Status | Detector |
|---|-----------|-------|--------|----------|
| 1 | `hash_map_lookup` | 1 | Implemented | `HashMapLookupDetector` |
| 2 | `hash_map_frequency` | 1 | Implemented | `FrequencyCountingDetector` |
| 3 | `prefix_sum` | 2 | Implemented | `PrefixSumDetector` |
| 4 | `sliding_window_fixed` | 2 | Implemented | `SlidingWindowFixedDetector` |
| 5 | `sliding_window_variable` | 2 | Implemented | `SlidingWindowVariableDetector` |
| 6 | `two_pointers_opposite` | 2 | Implemented | `TwoPointersOppositeDetector` |
| 7 | `two_pointers_same` | 2 | Implemented | `TwoPointersSameDetector` |
| 8 | `dfs_recursive` | 5 | Implemented | `DFSRecursiveDetector` |
| 9 | `dfs_iterative` | 5 | Implemented | `DFSIterativeDetector` |
| 10 | `bfs_level_order` | 5 | Implemented | `BFSLevelOrderDetector` |
| 11 | `bfs_shortest_path` | 5 | Implemented | `BFSShortestPathDetector` |
| 12 | `topological_sort` | | Pending | |
| 13 | `union_find` | | Pending | |
| 14 | `binary_search_tree` | 5 | Implemented | `BinarySearchTreeDetector` |
| 15 | `dp_1d_forward` | | Pending | |
| 16 | `dp_1d_sequence` | | Pending | |
| 17 | `dp_2d_grid` | | Pending | |
| 18 | `dp_2d_string` | | Pending | |
| 19 | `dp_knapsack` | | Pending | |
| 20 | `dp_interval` | | Pending | |
| 21 | `dp_state_machine` | | Pending | |
| 22 | `fast_slow_pointers` | 4 | Implemented | `FastSlowPointersDetector` |
| 23 | `linked_list_reversal` | 4 | Implemented | `LinkedListReversalDetector` |
| 24 | `monotonic_stack` | 3 | Implemented | `MonotonicStackDetector` |
| 25 | `monotonic_deque` | 3 | Implemented | `MonotonicQueueDetector` |
| 26 | `binary_search_standard` | 3 | Implemented | `BinarySearchClassicDetector` |
| 27 | `binary_search_rotated` | | Pending | |
| 28 | `binary_search_answer` | 3 | Implemented | `BinarySearchAnswerDetector` |
| 29 | `heap_top_k` | 3 | Implemented | `HeapPriorityQueueDetector` |
| 30 | `greedy_local` | | Pending | |
| 31 | `greedy_interval` | | Pending | |
| 32 | `backtracking_permutation` | | Pending | |
| 33 | `backtracking_subset` | | Pending | |

## Validation Status

All 15 implemented detectors validated against 325 LeetCode-inspired code patterns.

| Metric | Value |
|--------|-------|
| Total Tests | 325 |
| True Positives | 150 |
| False Negatives | 9 |
| True Negatives | 164 |
| False Positives | 2 (borderline) |
| Precision | 0.9868 |
| Recall | 0.9434 |
| F1 Score | 0.9646 |
| Avg Confidence | 0.7727 |
| Detector Overlap | 0.0% (perfect separation) |
| Unit Tests | 252/252 passing |

## Summary

| Category | Count |
|----------|-------|
| Total Taxonomy Patterns | 33 |
| Implemented (Batch 1) | 5 |
| Implemented (Batch 2) | 5 |
| Implemented (Batch 3) | 5 |
| Implemented (Batch 4) | 2 |
| Implemented (Batch 5) | 5 |
| **Total Implemented** | **22** |
| **Remaining** | **11** |

## Batch 3 Detectors

| Pattern ID | Evidence Strategy | Core Gated Signal |
|-----------|------------------|-------------------|
| `binary_search_standard` | `binary_midpoint` (0.35), `boundary_update` (0.25), `mid_comparison` (0.30), `left_right_boundary` (0.20) | Midpoint calculation + boundary update, no feasibility function call |
| `binary_search_answer` | `feasibility_check` (0.40), `answer_midpoint` (0.30), `answer_boundary_update` (0.25), `feasibility_loop` (0.20) | Midpoint calculation + feasibility function call with mid argument |
| `heap_top_k` | `heap_push` (0.35), `heap_pop` (0.35), `heapify_call` (0.25), `nlargest_nsmallest` (0.25) | `heapq.heappush()` or `heapq.heappop()` call |
| `monotonic_stack` | `monotonic_pop` (0.40), `stack_push` (0.25), `comparison_loop` (0.30) | Empty list stack + inner while with comparison-driven pop + append |
| `monotonic_deque` | `monotonic_pop` (0.35), `queue_append` (0.20), `queue_popleft` (0.30), `deque_creation` (0.20) | `deque()` creation + inner while with comparison-driven pop + append |

## Batch 4 Detectors

| Pattern ID | Evidence Strategy | Core Gated Signal |
|-----------|------------------|-------------------|
| `fast_slow_pointers` | `floyd_traversal` (0.60), `cycle_check` (0.40), `pointer_names` (0.20) | While loop with `.next` traversal at ≥2 different advancement rates |
| `linked_list_reversal` | `pointer_rewiring` (0.50), `prev_curr_update` (0.30), `reversal_variable_names` (0.20) / `recursive_rewiring` (0.60), `recursive_call_with_next` (0.40) | `curr.next = prev` rewiring (iterative) or `head.next.next = head` rewiring (recursive) |

## Batch 5 Detectors

| Pattern ID | Evidence Strategy | Core Gated Signal |
|-----------|------------------|-------------------|
| `dfs_recursive` | `recursive_call` (0.35), `graph_traversal` (0.30), `child_recursion` (0.25), `grid_expansion` (0.25), `visited_tracking` (0.20), `base_case` (0.20) | Recursive self-call + graph traversal OR child recursion OR grid expansion OR visited tracking |
| `dfs_iterative` | `explicit_stack` (0.35), `stack_traversal` (0.30), `child_push` (0.25), `visited_tracking` (0.20) | Stack initialized before while + stack.pop() + child push or visited tracking (excludes comparison-driven pop) |
| `bfs_level_order` | `queue_popleft` (0.35), `child_enqueue` (0.30), `level_tracking` (0.25), `deque_import` (0.20) | Popleft + child enqueue (excludes distance tracking and visited set) |
| `bfs_shortest_path` | `queue_traversal` (0.30), `distance_tracking` (0.25), `visited_set` (0.20), `neighbor_expansion` (0.25), `level_for_loop` (0.20) | Queue traversal + distance tracking OR visited set |
| `binary_search_tree` | `bst_comparison` (0.30), `bst_recursion` (0.25), `min_max_constraint` (0.25), `bst_operation` (0.30) | BST comparison AND recursive left/right child traversal |

## Coverage by Algorithmic Category

| Category | Total | Implemented | Missing |
|----------|-------|-------------|---------|
| Arrays & Hashing | 7 | 7 | 0 |
| Graphs & Trees | 7 | 5 | 2 |
| Dynamic Programming | 7 | 0 | 7 |
| Linked Lists & Stack | 4 | 4 | 0 |
| Binary Search | 3 | 3 | 0 |
| Heap / Greedy / Backtracking | 5 | 1 | 4 |
| **Total** | **33** | **22** | **11** |
