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
| 8 | `dfs_recursive` | | Pending | |
| 9 | `dfs_iterative` | | Pending | |
| 10 | `bfs_level_order` | | Pending | |
| 11 | `bfs_shortest_path` | | Pending | |
| 12 | `topological_sort` | | Pending | |
| 13 | `union_find` | | Pending | |
| 14 | `binary_search_tree` | | Pending | |
| 15 | `dp_1d_forward` | | Pending | |
| 16 | `dp_1d_sequence` | | Pending | |
| 17 | `dp_2d_grid` | | Pending | |
| 18 | `dp_2d_string` | | Pending | |
| 19 | `dp_knapsack` | | Pending | |
| 20 | `dp_interval` | | Pending | |
| 21 | `dp_state_machine` | | Pending | |
| 22 | `fast_slow_pointers` | | Pending | |
| 23 | `linked_list_reversal` | | Pending | |
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

## Summary

| Category | Count |
|----------|-------|
| Total Taxonomy Patterns | 33 |
| Implemented (Batch 1) | 5 |
| Implemented (Batch 2) | 5 |
| Implemented (Batch 3) | 5 |
| **Total Implemented** | **15** |
| **Remaining** | **18** |

## Batch 3 Detectors

| Pattern ID | Evidence Strategy | Core Gated Signal |
|-----------|------------------|-------------------|
| `binary_search_standard` | `binary_midpoint` (0.35), `boundary_update` (0.25), `mid_comparison` (0.30), `left_right_boundary` (0.20) | Midpoint calculation + boundary update, no feasibility function call |
| `binary_search_answer` | `feasibility_check` (0.40), `answer_midpoint` (0.30), `answer_boundary_update` (0.25), `feasibility_loop` (0.20) | Midpoint calculation + feasibility function call with mid argument |
| `heap_top_k` | `heap_push` (0.35), `heap_pop` (0.35), `heapify_call` (0.25), `nlargest_nsmallest` (0.25) | `heapq.heappush()` or `heapq.heappop()` call |
| `monotonic_stack` | `monotonic_pop` (0.40), `stack_push` (0.25), `comparison_loop` (0.30) | Empty list stack + inner while with comparison-driven pop + append |
| `monotonic_deque` | `monotonic_pop` (0.35), `queue_append` (0.20), `queue_popleft` (0.30), `deque_creation` (0.20) | `deque()` creation + inner while with comparison-driven pop + append |

## Coverage by Algorithmic Category

| Category | Total | Implemented | Missing |
|----------|-------|-------------|---------|
| Arrays & Hashing | 7 | 7 | 0 |
| Graphs & Trees | 7 | 0 | 7 |
| Dynamic Programming | 7 | 0 | 7 |
| Linked Lists & Stack | 4 | 2 | 2 |
| Binary Search | 3 | 3 | 0 |
| Heap / Greedy / Backtracking | 5 | 1 | 4 |
| **Total** | **33** | **15** | **18** |
