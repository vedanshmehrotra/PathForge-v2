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
| 12 | `topological_sort` | 6 | Implemented | `TopologicalSortDetector` |
| 13 | `union_find` | 6 | Implemented | `UnionFindDetector` |
| 14 | `binary_search_tree` | 5 | Implemented | `BinarySearchTreeDetector` |
| 15 | `dp_1d_forward` | 8 | Implemented | `DP1DForwardDetector` |
| 16 | `dp_1d_sequence` | 8 | Implemented | `DP1DSequenceDetector` |
| 17 | `dp_2d_grid` | 8 | Implemented | `DP2DGridDetector` |
| 18 | `dp_2d_string` | 8 | Implemented | `DP2DStringDetector` |
| 19 | `dp_knapsack` | 8 | Implemented | `DPKnapsackDetector` |
| 20 | `dp_interval` | 8 | Implemented | `DPIntervalDetector` |
| 21 | `dp_state_machine` | 8 | Implemented | `DPStateMachineDetector` |
| 22 | `fast_slow_pointers` | 4 | Implemented | `FastSlowPointersDetector` |
| 23 | `linked_list_reversal` | 4 | Implemented | `LinkedListReversalDetector` |
| 24 | `monotonic_stack` | 3 | Implemented | `MonotonicStackDetector` |
| 25 | `monotonic_deque` | 3 | Implemented | `MonotonicQueueDetector` |
| 26 | `binary_search_standard` | 3 | Implemented | `BinarySearchClassicDetector` |
| 27 | `binary_search_rotated` | 6 | Implemented | `BinarySearchRotatedDetector` |
| 28 | `binary_search_answer` | 3 | Implemented | `BinarySearchAnswerDetector` |
| 29 | `heap_top_k` | 3 | Implemented | `HeapPriorityQueueDetector` |
| 30 | `greedy_local` | 7 | Implemented | `GreedyLocalDetector` |
| 31 | `greedy_interval` | 7 | Implemented | `GreedyIntervalDetector` |
| 32 | `backtracking_permutation` | 7 | Implemented | `BacktrackingPermutationDetector` |
| 33 | `backtracking_subset` | 7 | Implemented | `BacktrackingSubsetDetector` |

## Validation Status

All 36 implemented detectors validated against LeetCode-inspired code patterns.

| Metric | Value |
|--------|-------|
| Total Tests | 900+ |
| True Positives | 350+ |
| False Negatives | 9 |
| True Negatives | 450+ |
| False Positives | 2 (borderline) |
| Precision | 0.9943 |
| Recall | 0.9749 |
| F1 Score | 0.9845 |
| Avg Confidence | 0.7812 |
| Detector Overlap | 0.0% (perfect separation) |
| Unit Tests | All passing |

## Summary

| Category | Count |
|----------|-------|
| Total Taxonomy Patterns | 33 |
| Implemented (Batch 1) | 5 |
| Implemented (Batch 2) | 5 |
| Implemented (Batch 3) | 5 |
| Implemented (Batch 4) | 2 |
| Implemented (Batch 5) | 5 |
| Implemented (Batch 6) | 3 |
| Implemented (Batch 7) | 4 |
| Implemented (Batch 8) | 7 |
| **Total Implemented** | **36** |
| **Remaining** | **0** |

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

## Batch 6 Detectors

| Pattern ID | Evidence Strategy | Core Gated Signal |
|-----------|------------------|-------------------|
| `topological_sort` | `indegree_array` (0.30), `indegree_increment` (0.20), `indegree_decrement` (0.20), `zero_indegree_queue` (0.30), `conditional_enqueue` (0.25) | Indegree array + queue processing (zero-indegree queue init or conditional enqueue on indegree == 0) |
| `union_find` | `parent_array` (0.30), `find_path_compression` (0.35), `union_operation` (0.25), `connected_check` (0.20), `rank_size` (0.15) | `self.parent` array initialization + `find()` with path compression or `union()` method |
| `binary_search_rotated` | `sorted_half_comparison` (0.30), `target_range_check` (0.25), `midpoint_calculation` (0.20), `boundary_update` (0.20) | Sorted-half comparison AND target-range check within same iteration (excludes classic BS, answer-space BS, find-min) |

## Batch 7 Detectors

| Pattern ID | Evidence Strategy | Core Gated Signal |
|-----------|------------------|-------------------|
| `greedy_local` | `local_optimum_selection` (0.35), `immediate_decision` (0.30), `forward_progress` (0.25) | Local optimum selection via max/min, OR immediate decision + forward progress (excludes ordinary iteration) |
| `greedy_interval` | `interval_sorting` (0.30), `interval_comparison` (0.25), `interval_merge_scheduling` (0.30), `greedy_selection` (0.25) | Interval sorting + interval comparison OR merge/scheduling (excludes ordinary sorting) |
| `backtracking_subset` | `choose_recurse_unchoose` (0.35), `recursive_branching` (0.30), `state_restoration` (0.25), `subset_generation` (0.20) | Choose/recurse/unchoose (append + recuse + pop), OR recursive branching + state restoration (excludes ordinary recursion) |
| `backtracking_permutation` | `swap_recurse_swap` (0.35), `visited_array` (0.25), `permutation_generation` (0.30), `recursive_exploration` (0.20) | Swap/recurse/swap, OR visited array + permutation generation (excludes subset generation) |

## Coverage by Algorithmic Category

| Category | Total | Implemented | Missing |
|----------|-------|-------------|---------|
| Arrays & Hashing | 7 | 7 | 0 |
| Graphs & Trees | 7 | 7 | 0 |
| Dynamic Programming | 7 | 7 | 0 |
| Linked Lists & Stack | 4 | 4 | 0 |
| Binary Search | 3 | 3 | 0 |
| Heap / Greedy / Backtracking | 5 | 5 | 0 |
| **Total** | **33** | **33** | **0** |
