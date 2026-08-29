# Full Ground-Truth Audit Report

## Overview

End-to-end validation of all 15 seeded ground-truth problems through the shadow pipeline:
facts → techniques → strategies → solution-group matching.

## Problems Tested

| LC | Title | Family | CSV Pattern | Expected Strategy | Shadow Result | Status |
|----|-------|--------|-------------|-------------------|---------------|--------|
| 3 | Longest Substring Without Repeating Characters | Sliding Window | sliding_window_variable | sliding_window | CONFIRMED | ✅ |
| 209 | Minimum Size Subarray Sum | Sliding Window | sliding_window_variable | sliding_window | CONFIRMED | ✅ |
| 2958 | Max Subarray Length of Length K | Sliding Window | sliding_window_variable | sliding_window | CONFIRMED | ✅ |
| 11 | Container With Most Water | Two Pointers | two_pointers_opposite | two_pointers_opposite | CONFIRMED | ✅ |
| 125 | Valid Palindrome | Two Pointers | two_pointers_opposite | two_pointers_opposite | CONFIRMED | ✅ |
| 15 | 3Sum | Two Pointers | two_pointers_opposite | two_pointers_opposite | CONFIRMED | ✅ |
| 704 | Binary Search | Binary Search | binary_search_standard | binary_search | CONFIRMED | ✅ |
| 35 | Search Insert Position | Binary Search | binary_search_standard | binary_search | CONFIRMED | ✅ |
| 70 | Climbing Stairs (bottom-up) | DP Bottom-Up | dp_1d_forward | dp_bottom_up | CONFIRMED | ✅ |
| 322 | Coin Change (bottom-up) | DP Bottom-Up | dp_1d_forward | dp_bottom_up | CONFIRMED (seeded) | ✅ |
| 62 | Unique Paths | DP Bottom-Up | dp_2d_grid | dp_bottom_up | CONFIRMED | ✅ |
| 46 | Permutations | DFS/Backtracking | backtracking_permutation | dfs_backtracking | CONFIRMED | ✅ |
| 78 | Subsets | DFS/Backtracking | backtracking_subset | dfs_backtracking | CONFIRMED | ✅ |
| 102 | Binary Tree Level Order | BFS | bfs_level_order | bfs_shortest_path | CONFIRMED | ✅ |
| 496 | Next Greater Element I | Monotonic Stack | monotonic_stack | monotonic_stack_strategy | CONFIRMED | ✅ |
| 200 | Number of Islands (BFS version) | BFS/Union-Find | bfs, dfs, uf | bfs_shortest_path | UNRESOLVED* | ⚠️ |

*LC 200 is a **known fact-extraction limitation**: grid neighbor traversal via coordinate deltas doesn't produce `neighbor_traversal` fact. This requires a new fact type, not a strategy fix.

## Issues Found and Fixed

### Issue 1: Nested-function DP not detected (LC 322 top-down, LC 70 top-down)

**Category:** Technique detection  
**Root cause:** `_detect_recursive_branching()` required `recursive_call_in_conditional` OR `multiple_recursive_paths`, but nested `def dfs()` with for-loop recursion doesn't produce either fact.  
**Fix:** Extended `_detect_recursive_branching()` to also accept `self_recursive_call` with `context=nested_function` as evidence.  
**File:** `pathforge/ast_analysis/shadow/techniques.py` — 10 lines added.  
**Before:** LC 322 nested dfs → no strategy detected.  
**After:** LC 322 nested dfs → `dp_top_down` (0.85).  
**No regression:** N-Queens, Fibonacci, factorial, direct recursive DP all still correct.

### Issue 2: CSV multi-pattern fallback creates self-contradictory groups (LC 200, LC 322)

**Category:** Ground truth mapping  
**Root cause:** `_load_ground_truth()` fallback path union-merged all CSV patterns into a single group. When patterns represent ALTERNATIVE approaches (e.g., `["bfs_shortest_path", "dp_1d_forward"]`), this required ALL strategies simultaneously, creating unsatisfiable or self-contradictory groups.  
**Fix:** Added `_split_csv_patterns_to_groups()` that splits multi-pattern CSV entries into per-strategy groups.  
**File:** `pathforge/services/problem_resolver.py` — ~50 lines added.  
**Before:** LC 200 CSV → single group with required=["bfs","recursive_branching","union_find"] AND excluded=["bfs","recursive_branching"] (self-contradictory).  
**After:** LC 200 CSV → 3 separate groups: BFS, DFS, Union-Find.  
**Before:** LC 322 CSV → single group with required=["bfs","dp_bottom_up"].  
**After:** LC 322 CSV → 2 separate groups: BFS, DP.

## Additional Investigation Results

### LC 438 (Find All Anagrams) — known limitation

Fixed sliding window with if-guard (`if right - left + 1 > len(p)`) doesn't produce `variable_use_in_loop_body` because the updated variable (`left`) is only used within the same if-block. This is a fact-extraction limitation, not a regression.

### LC 496 (Next Greater Element I) — no issue

CSV has `["hash_map_lookup", "monotonic_stack"]`. The seeded group requires `monotonic_stack_maintenance`, which the shadow pipeline correctly detects and CONFIRMs. The `hash_map_lookup` pattern maps to empty required (generic data-structure behavior), so it doesn't interfere.

### Permutations (LC 46) — no issue

The backtracking evaluator correctly detects `dfs_backtracking` via the fallback path (`self_recursive_call` + `early_termination` + `state_restoration`). Fix A now also fires `recursive_branching` (0.85), which is correct but doesn't change the strategy outcome.

### Number of Islands (LC 200) — fact-extraction limitation

The BFS version uses grid coordinate deltas (`for dx, dy in [(0,1),(1,0),(0,-1),(-1,0)]`), which doesn't produce `neighbor_traversal` (requires graph adjacency access or linked-structure traversal). The DFS version produces `recursive_branching` but not `dfs_backtracking` (no `state_restoration` because grid mutation is subscript-based). The Union-Find version produces neither `parent_pointer_chase` nor `parent_root_merge` because the `find()` method uses path compression which the fact extractor doesn't recognize.

**This is NOT fixable without adding new fact types.** The BFS/DFS/UF detection all require structural facts that the current fact extractor doesn't produce for grid-based code.

## Failures by Category

| Category | Count | Issues |
|----------|:-----:|--------|
| Technique detection | 1 (FIXED) | nested-function DP → recursive_branching |
| Ground truth mapping | 2 (FIXED) | CSV multi-pattern union-merge |
| Fact extraction (limitation) | 3 | grid neighbor traversal, if-guard fixed window, grid union-find |
| Strategy detection | 0 | — |
| Matching engine | 0 | — |
| No issues | 10 | All other seeded problems |

## Systemic Fixes Made

### Fix A: Nested-function recursive_branching acceptance

**What:** `_detect_recursive_branching()` now fires when `self_recursive_call` has `context=nested_function`.  
**Why:** Memoized top-down DP commonly uses nested `def dfs()` with for-loop recursion, not if-else recursion. The old requirement (`recursive_call_in_conditional`) missed this pattern.  
**Scope:** Only affects technique detection. Strategy evaluators still require additional facts (cache for DP, state_restoration for backtracking) to prevent false positives.  
**Tests:** 5 new tests covering nested DP, nested backtracking, nested helper without recursion, and direct recursive DP.

### Fix B: CSV multi-pattern group splitting

**What:** `_load_ground_truth()` fallback path now calls `_split_csv_patterns_to_groups()` instead of union-merging all patterns into a single group.  
**Why:** CSV patterns like `["bfs_shortest_path", "dp_1d_forward"]` represent alternative approaches, not all-required. The old code required ALL strategies simultaneously, creating unsatisfiable groups.  
**Scope:** Only affects the fallback path (no solution_groups column). Problems with seeded groups are unaffected.  
**Tests:** 5 new tests covering multi-pattern splitting, single-pattern preservation, same-strategy merging, and self-contradiction prevention.

## Complete Test Results

| Suite | Passed | Failed | Total |
|-------|:------:|:------:|:-----:|
| Shadow (`pathforge/ast_analysis/shadow/tests/`) | 436 | 0 | 436 |
| Backend GT reconciliation (`pathforge/tests/test_ground_truth_reconciliation.py`) | 21 | 0 | 21 |
| DB + Engine (`pathforge/db/tests/` + `pathforge/ast_engine/tests/`) | 76 | 0 | 76 |
| Frontend (vitest) | 32 | 0 | 32 |
| **Total verified** | **565** | **0** | **565** |

+10 new regression tests added, 0 regressions.

## Remaining Known Limitations

1. **Grid neighbor traversal** (LC 200 BFS): Grid coordinate-based neighbor access doesn't produce `neighbor_traversal` fact. Requires a new `grid_neighbor_access` fact type.
2. **If-guard fixed window** (LC 438): Fixed sliding window with `if` condition instead of `while` loop doesn't produce `variable_use_in_loop_body`. The variable is only used within the same if-block.
3. **Grid Union-Find** (LC 200 UF): Path-compression `find()` with while-loop parent chase not recognized as `parent_pointer_chase`.
4. **Brute-force hash map** (LC 496 variant): O(n²) nested loop without stack doesn't produce monotonic-stack facts.

## What Should NOT Be Fixed

- Adding one-off rules for individual LeetCode problems
- Modifying fact extraction to recognize specific variable names
- Adding exclusion rules based on problem IDs
- Creating a separate detection path for grid-based algorithms (would over-engineer the project)
