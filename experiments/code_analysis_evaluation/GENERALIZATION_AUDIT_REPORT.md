# Generalization Audit Report

## Overview

Broad generalization audit of all 9 supported strategy families, testing multiple structurally different implementations for each. Focus: reusable structural patterns, not individual problem rules.

## Methodology

For each strategy family, tested 3-6 structurally different implementations covering:
- Variable naming variations
- for vs while loops
- Nested functions vs top-level
- Helper functions vs inline
- Alternate but valid implementations
- Accumulator/state variable patterns
- Equivalent control-flow structures

## Results by Family

### Sliding Window (5/6 correct)

| Variant | Status | Notes |
|---------|:------:|-------|
| for + while-shrink | ✅ TP | Standard pattern |
| for + if-shrink | ✅ TP | LC 424 variant |
| for + while-set-shrink | ✅ TP | LC 3 variant |
| while + for-neighbor | ✅ TP | LC 76 variant |
| for + result-check | ✅ TP | LC 424 with result |
| prefix-sum hash map | ✅ Correct negative | **Fixed in this session** |

**Fix applied:** Extended cache exclusion in `_evaluate_sliding_window()` to detect dict-like `indexed_write` patterns. Hash map lookups like `count[prefix - k]` no longer fire sliding_window.

### Two Pointers (6/6 correct)

| Variant | Status | Notes |
|---------|:------:|-------|
| palindrome | ✅ TP | Standard |
| container | ✅ TP | With computation |
| 3Sum | ✅ TP | Nested loop |
| sortedSquares | ✅ TP | With index write |
| moveZeroes | ✅ Correct negative | Same-direction, not opposite |
| removeDuplicates | ✅ Correct negative | Same-direction, not opposite |

### Binary Search (5/5 correct)

| Variant | Status | Notes |
|---------|:------:|-------|
| standard | ✅ TP | |
| insert position | ✅ TP | |
| first bad version | ✅ TP | left < right variant |
| answer space | ✅ TP | Binary search on answer |
| rotated array | ✅ TP | Complex conditionals |

### DP Bottom-Up (6/6 correct)

| Variant | Status | Notes |
|---------|:------:|-------|
| climbing stairs | ✅ TP | 1D array |
| coin change | ✅ TP | 1D with inner loop |
| unique paths | ✅ TP | 2D grid |
| knapsack | ✅ TP | 2D with choice |
| space-optimized | ✅ Correct negative | No table → no iterative_table_filling |
| dict-based DP | ✅ TP | Hash map as DP table |

### DP Top-Down (3/4 correct)

| Variant | Status | Notes |
|---------|:------:|-------|
| nested dfs memo | ✅ TP | **Fixed in previous session** |
| nested fib memo | ✅ TP | **Fixed in previous session** |
| direct recursion memo | ✅ TP | |
| @lru_cache | ❌ Missed | **Known limitation** — decorator hides cache facts |

### DFS/Backtracking (4/5 correct)

| Variant | Status | Notes |
|---------|:------:|-------|
| permutations (append/pop) | ✅ TP | |
| subsets | ✅ TP | |
| combination sum | ✅ TP | |
| permutations (used array) | ✅ TP | |
| N-Queens (set ops) | ❌ Missed | **Known limitation** — set ops not append/pop |

### BFS (3/3 correct)

| Variant | Status | Notes |
|---------|:------:|-------|
| tree level order | ✅ TP | |
| graph shortest path | ✅ TP | |
| tree level order (alt) | ✅ TP | |

### Monotonic Stack (3/3 correct)

| Variant | Status | Notes |
|---------|:------:|-------|
| next greater element | ✅ TP | |
| daily temperatures | ✅ TP | |
| largest rectangle | ✅ TP | |

### Union-Find (1/4 correct)

| Variant | Status | Notes |
|---------|:------:|-------|
| class with while-loop | ❌ Missed | **Known limitation** — self.parent[x] |
| class with rank | ❌ Missed | **Known limitation** — self.parent[x] |
| class with path compression | ❌ Missed | **Known limitation** — recursive find |
| function-based (no class) | ✅ TP | Works because uses plain variable |

## Summary

| Family | Correct | Total | FP | Wrong | Missed |
|--------|:-------:|:-----:|:--:|:-----:|:------:|
| Sliding Window | 6 | 6 | 0 | 0 | 0 |
| Two Pointers | 6 | 6 | 0 | 0 | 0 |
| Binary Search | 5 | 5 | 0 | 0 | 0 |
| DP Bottom-Up | 6 | 6 | 0 | 0 | 0 |
| DP Top-Down | 3 | 4 | 0 | 0 | 1 |
| DFS/Backtracking | 4 | 5 | 0 | 0 | 1 |
| BFS | 3 | 3 | 0 | 0 | 0 |
| Monotonic Stack | 3 | 3 | 0 | 0 | 0 |
| Union-Find | 1 | 4 | 0 | 0 | 3 |
| **Total** | **37** | **42** | **0** | **0** | **5** |

**Key metric: 0 false positives, 0 wrong strategy selections.**

All 5 failures are misses (code that should be detected but isn't), and all 5 are fact-extraction limitations, not strategy-evaluation errors.

## Fixes Applied

### Fix: Hash-map sliding-window false positive

**Problem:** Prefix sum patterns like `count[prefix - k]` produced `window_size_constant` fact and were falsely classified as `sliding_window`.

**Root cause:** The sliding-window strategy's cache exclusion check only used `cache_lookup`/`cache_write` facts, which don't fire for dict literal patterns.

**Fix:** Extended the exclusion to also check `indexed_write` with `index_type: 'Name'` (dict-like write pattern). When the same structure appears in both `window_size_constant` and `indexed_write` with a variable index, it's a hash map, not a sliding window.

**File:** `pathforge/ast_analysis/shadow/strategies.py` — 7 lines added.

**Before:** `count[prefix - k]` → sliding_window + dp_bottom_up (FP)
**After:** `count[prefix - k]` → dp_bottom_up only (sliding_window correctly excluded)

## Known Limitations (NOT to fix yet)

1. **@lru_cache decorator** — DP top-down with `@lru_cache` not detected because decorator hides cache facts
2. **Set-based state restoration** — N-Queens uses `cols | {col}` instead of `append`/`pop`
3. **Class-based Union-Find** — `self.parent[x]` not recognized as `parent_pointer_chase`
4. **Recursive path compression** — `self.parent[x] = self.find(self.parent[x])` not recognized
5. **Grid neighbor traversal** — Coordinate deltas not recognized as `neighbor_traversal`
6. **If-guard fixed window** — Fixed window with `if` condition instead of `while` loop

## Test Results

| Suite | Passed | Failed | Total |
|-------|:------:|:------:|:-----:|
| Shadow | 440 | 0 | 440 |
| Backend GT reconciliation | 21 | 0 | 21 |
| DB + Engine | 76 | 0 | 76 |
| Frontend | 32 | 0 | 32 |
| **Total verified** | **569** | **0** | **569** |

+4 new regression tests added, 0 regressions.

## What Was NOT Fixed

- @lru_cache detection (requires decorator-aware fact extraction)
- N-Queens set operations (requires immutable-state fact extraction)
- Class-based Union-Find (requires attribute-access fact extraction)
- Grid neighbor traversal (requires new fact type)
- If-guard fixed window (requires if-condition window detection)

These are all fact-extraction limitations that would require new fact types or detector logic. They are documented as known limitations and should be addressed in a future phase if the project needs them.
