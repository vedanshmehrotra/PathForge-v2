# Recommender Hardening Report

**Date:** 2026-06-17
**Change:** `get_recommendable_patterns()` helper + `get_weakest_topics()` filtering

---

## Patterns Excluded from Recommendation Flow

These 6 patterns have **zero** primary problems and are excluded from recommendation:

| Pattern | Human Name | Broad Topic | Found as Secondary? |
|---------|------------|-------------|---------------------|
| `sliding_window_fixed` | Fixed Sliding Window | arrays | Yes |
| `topological_sort` | Topological Sort | trees_graphs | Yes |
| `union_find` | Union-Find | trees_graphs | Yes |
| `binary_search_tree` | Binary Search Tree | trees_graphs | No |
| `dp_interval` | Interval DP | dp | No |
| `dp_state_machine` | State Machine DP | dp | No |

### Reason for exclusion

`get_recommendable_patterns()` executes:

```sql
SELECT DISTINCT json_extract(p.pattern, '$[0]') AS pattern
FROM problems p
WHERE json_extract(p.pattern, '$[0]') IS NOT NULL
```

Patterns not in the result set have no problem claiming them as primary.
`_select_problem()` would never return a problem for them, so any rotation to
these patterns produces a non-actionable `topic_hint` recommendation.

---

## Patterns Remaining (Recommendable)

These 27 patterns have at least 1 primary problem and remain in the flow:

| Pattern | Human Name | Primary Problems |
|---------|------------|------------------|
| `backtracking_permutation` | Backtracking Permutation | 3 |
| `backtracking_subset` | Backtracking Subset | 17 |
| `bfs_level_order` | BFS Level Order | 26 |
| `bfs_shortest_path` | BFS Shortest Path | 8 |
| `binary_search_answer` | Binary Search on Answer | 19 |
| `binary_search_rotated` | Binary Search Rotated | 2 |
| `binary_search_standard` | Binary Search Standard | 10 |
| `dfs_iterative` | DFS Iterative | 6 |
| `dfs_recursive` | DFS Recursive | 25 |
| `dp_1d_forward` | 1D DP Forward | 21 |
| `dp_1d_sequence` | 1D DP Sequence | 3 |
| `dp_2d_grid` | 2D Grid DP | 8 |
| `dp_2d_string` | 2D String DP | 10 |
| `dp_knapsack` | Knapsack DP | 2 |
| `fast_slow_pointers` | Fast & Slow Pointers | 5 |
| `greedy_interval` | Greedy Interval | 3 |
| `greedy_local` | Greedy Local | 32 |
| `hash_map_frequency` | Hash Map Frequency | 25 |
| `hash_map_lookup` | Hash Map Lookup | 20 |
| `heap_top_k` | Heap / Top K | 4 |
| `linked_list_reversal` | Linked List Reversal | 2 |
| `monotonic_deque` | Monotonic Deque | 1 |
| `monotonic_stack` | Monotonic Stack | 12 |
| `prefix_sum` | Prefix Sum | 5 |
| `sliding_window_variable` | Sliding Window | 1 |
| `two_pointers_opposite` | Two Pointers (Opposite) | 14 |
| `two_pointers_same` | Two Pointers (Same Direction) | 16 |
| **Total** | **27 patterns** | **300** |

---

## User-Facing Impact

| Area | Before | After |
|------|--------|-------|
| Dashboard "Needs Practice" | Shows 5 weakest among 33 patterns. Un-practiceable patterns (e.g. `dp_state_machine`) appear but can never be recommended. | Shows 5 weakest among 27 recommendable patterns. Every listed pattern has at least 1 available problem. |
| Topic rotation | `_rotate_topic()` iterates weakest, often lands on `binary_search_tree` (0 problems). Returns `topic_hint` dead-end. | Iterates only recommendable patterns. Every candidate has at least 1 problem in the bank. |
| Standalone recommendation (`GET /api/recommend`) | Picks from all 33 patterns. May suggest un-practiceable topic. | Picks from 27 patterns. Always picks a topic with available problems. |
| Topic profiles in DB | All 33 rows exist. Elo tracked for dead patterns. | Unchanged. Excluded patterns still have profiles. Filtering is at recommendation time only. |
| Taxonomy / onboarding | User can select confident areas mapping to excluded patterns. | Unchanged. Confident areas still give +150 Elo bonus. No change to seeding. |

### Edge cases handled

- **Empty problem bank:** `get_recommendable_patterns()` returns empty set -> `get_weakest_topics()` returns `[]` gracefully.
- **User solved all problems** in a pattern: `_select_problem()` returns None, `_rotate_topic()` skips it. Existing behavior, unchanged.
- **Excluded pattern is current topic:** User can still practice it. Only rotation *to* excluded patterns is blocked.

---

## Files Modified

| File | Change |
|------|--------|
| `pathforge/db/profile_manager.py` | Added `get_recommendable_patterns()`. Modified `get_weakest_topics()` to filter by recommendable patterns. |
| `pathforge/db/tests/test_elo.py` | Updated test to use canonical pattern names and seed matching problems. |
| `pathforge/tests/test_pipeline.py` | Updated `seed_base`, `fake_submission`, `insert_submission` to use canonical pattern names. |

## Tests

13/13 tests pass (including the 2 that required test data alignment).