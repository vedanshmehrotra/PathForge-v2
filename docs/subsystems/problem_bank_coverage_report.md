# PathForge Problem Bank Coverage Report

**Total problems:** 300
**Date:** 2026-06-17
**Source:** pathforge/data/pathforge_problems_fixed.csv

---

## Difficulty Distribution

| Difficulty | Count | Percentage |
|------------|-------|------------|
| Easy | 100 | 33.3% |
| Medium | 150 | 50.0% |
| Hard | 50 | 16.7% |
| **Total** | **300** | **100%** |

---

## Patterns With Zero Problems (Primary)

These 6 canonical patterns have **no** problems where they are the primary pattern:

- sliding_window_fixed (Fixed Sliding Window)
- topological_sort (Topological Sort)
- union_find (Union-Find)
- binary_search_tree (Binary Search Tree)
- dp_interval (Interval DP)
- dp_state_machine (State Machine DP)

These patterns exist in the taxonomy and in user topic_profiles, but _select_problem() can never find a problem for them. Rotation to these topics produces a 	opic_hint with no actionable problem.

---

## Patterns With Fewer Than 5 Problems (Primary)

| Pattern | Human Name | Count | Difficulty Mix |
|---------|------------|-------|----------------|
| sliding_window_variable | Sliding Window | 1 | Easy=1 |
| monotonic_deque | Monotonic Deque | 1 | Hard=1 |
| linked_list_reversal | Linked List Reversal | 2 | Easy=1, Medium=1 |
| binary_search_rotated | Binary Search Rotated | 2 | Medium=2 |
| dp_knapsack | Knapsack DP | 2 | Medium=2 |
| dp_1d_sequence | 1D DP Sequence | 3 | Easy=1, Hard=2 |
| greedy_interval | Greedy Interval | 3 | Medium=3 |
| backtracking_permutation | Backtracking Permutation | 3 | Medium=2, Hard=1 |
| heap_top_k | Heap / Top K | 4 | Easy=2, Hard=2 |

---

## Full Pattern Distribution (Primary)

| Pattern | Human Name | Count |
|---------|------------|-------|
| greedy_local | Greedy Local | 32 |
| bfs_level_order | BFS Level Order | 26 |
| hash_map_frequency | Hash Map Frequency | 25 |
| dfs_recursive | DFS Recursive | 25 |
| dp_1d_forward | 1D DP Forward | 21 |
| hash_map_lookup | Hash Map Lookup | 20 |
| binary_search_answer | Binary Search on Answer | 19 |
| backtracking_subset | Backtracking Subset | 17 |
| two_pointers_same | Two Pointers (Same Direction) | 16 |
| two_pointers_opposite | Two Pointers (Opposite) | 14 |
| monotonic_stack | Monotonic Stack | 12 |
| binary_search_standard | Binary Search Standard | 10 |
| dp_2d_string | 2D String DP | 10 |
| bfs_shortest_path | BFS Shortest Path | 8 |
| dp_2d_grid | 2D Grid DP | 8 |
| dfs_iterative | DFS Iterative | 6 |
| fast_slow_pointers | Fast & Slow Pointers | 5 |
| prefix_sum | Prefix Sum | 5 |
| heap_top_k | Heap / Top K | 4 |
| dp_1d_sequence | 1D DP Sequence | 3 |
| greedy_interval | Greedy Interval | 3 |
| backtracking_permutation | Backtracking Permutation | 3 |
| linked_list_reversal | Linked List Reversal | 2 |
| binary_search_rotated | Binary Search Rotated | 2 |
| dp_knapsack | Knapsack DP | 2 |
| sliding_window_variable | Sliding Window | 1 |
| monotonic_deque | Monotonic Deque | 1 |

| _(zero)_ | _(6 patterns with 0 problems)_ | 0 |

---

## Patterns Missing From Taxonomy

All patterns in the CSV are within the 33-pattern taxonomy.

---

## Summary of Recommendations

| Issue | Impact | Severity |
|-------|--------|----------|
| 6 patterns with 0 problems | Rotation dead-ends; un-practiceable topics | Critical |
| 9 patterns with <5 problems | Topic exhaustion after a few solves | High |
| Only 50 Hard problems (16.7%) | Advanced users plateau; limited options above 1300 Elo | Medium |
| Heavy skew to hash_map/dfs/two_pointers/greedy | Users cycle through same pattern families | Low |