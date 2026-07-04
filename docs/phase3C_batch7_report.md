# Phase 3C - Batch 7 Report: Greedy & Backtracking Detectors

## Overview

Batch 7 implements the four remaining Greedy and Backtracking detectors. These complete the Heap / Greedy / Backtracking category of the taxonomy.

| Pattern ID | Detector Class | Tests | Status |
|-----------|---------------|-------|--------|
| `greedy_local` | `GreedyLocalDetector` | 11 | Pass |
| `greedy_interval` | `GreedyIntervalDetector` | 10 | Pass |
| `backtracking_subset` | `BacktrackingSubsetDetector` | 10 | Pass |
| `backtracking_permutation` | `BacktrackingPermutationDetector` | 10 | Pass |
| **Total** | | **45** | **Pass** |

---

## 1. Greedy Local

### Target Pattern
Local greedy optimization where a locally optimal decision is made at each step. Characteristic of Maximum Subarray (Kadane's), Best Time to Buy/Sell Stock, Jump Game, and Candy distribution.

### Evidence Strategy

| Evidence Type | Weight | Detection Method |
|--------------|--------|-----------------|
| `local_optimum_selection` | 0.35 | `max()`/`min()` calls, running best variable assignment |
| `immediate_decision` | 0.30 | Conditional assignment committing to a locally optimal choice |
| `forward_progress` | 0.25 | Index/pointer advancing monotonically via `for`/`while` with `range()` |

### Gating Logic
Requires local optimum selection, OR immediate decision combined with forward progress.

### Disambiguation

| Similar Pattern | Key Differentiator |
|----------------|-------------------|
| Ordinary iteration | No max/min or running best variable |
| Dynamic programming | No state table or memoization |
| Divide and conquer | No splitting or merging |

### Test Cases (11 tests)

**Positive (5):** Kadane's max subarray, Best time to buy/sell stock, Jump game, Candy distribution, Greedy with running max.

**Negative (6):** No greedy code, ordinary for loop, plain sorting, Fibonacci recursion, empty code, non-greedy accumulation.

---

## 2. Greedy Interval

### Target Pattern
Interval-based greedy algorithms including interval scheduling (maximum non-overlapping), interval merging, and minimum arrows to burst balloons.

### Evidence Strategy

| Evidence Type | Weight | Detection Method |
|--------------|--------|-----------------|
| `interval_sorting` | 0.30 | `.sort(key=lambda x: x[0/1])` or `sorted(...key=lambda x: x[0/1])` |
| `interval_comparison` | 0.25 | Comparing `x[0]` or `x[1]` values in conditionals |
| `interval_merge_scheduling` | 0.30 | Overlap check with merge/assignment in if/else body |
| `greedy_selection` | 0.25 | Counting/greedy selection with subscript interval access |

### Gating Logic
Requires interval sorting AND at least one of: interval comparison or merge/scheduling.

### Disambiguation

| Similar Pattern | Key Differentiator |
|----------------|-------------------|
| Ordinary sorting | No key lambda accessing `[0]` or `[1]` on list elements |
| Non-interval algorithms | No interval subscript comparisons or merge operations |

### Test Cases (10 tests)

**Positive (5):** Merge intervals, non-overlapping intervals, min arrows to burst balloons, insert interval, interval scheduling.

**Negative (5):** No interval code, ordinary sort without lambda, plain iteration, sorting non-interval data (by `p[1]`), empty code.

---

## 3. Backtracking Subset

### Target Pattern
Recursive backtracking for subset/combination generation using choose/recurse/unchoose pattern. Characteristic of Subsets, Combinations, Combination Sum, Letter Combinations.

### Evidence Strategy

| Evidence Type | Weight | Detection Method |
|--------------|--------|-----------------|
| `choose_recurse_unchoose` | 0.35 | `append()` + recursive call + `pop()` sequence |
| `recursive_branching` | 0.30 | Multiple recursive self-calls (branching factor >= 2) |
| `state_restoration` | 0.25 | `.pop()` call or state restoration after recursion |
| `subset_generation` | 0.20 | Appending partial result to result list |

### Gating Logic
Requires choose/recurse/unchoose pattern, OR recursive branching with state restoration.

### Disambiguation

| Similar Pattern | Key Differentiator |
|----------------|-------------------|
| Fibonacci recursion | No append/pop pattern, no state restoration |
| Tree DFS recursion | No choose/unchoose pattern, no list mutation |
| Permutation | Uses swap or visited array, not append/pop for state |

### Test Cases (10 tests)

**Positive (6):** Subsets, Combination Sum, Combinations (n choose k), Subsets II (with duplicates), Letter Combinations of a Phone Number, combination with pruning.

**Negative (4):** No recursion, Fibonacci, factorial, binary tree DFS (no state restoration).

---

## 4. Backtracking Permutation

### Target Pattern
Recursive permutation generation using either swap/recurse/swap or visited-array tracking. Characteristic of Permutations, Permutations II, and N-Queens.

### Evidence Strategy

| Evidence Type | Weight | Detection Method |
|--------------|--------|-----------------|
| `swap_recurse_swap` | 0.35 | Tuple/list swap + recursive call + swap-back pattern |
| `visited_array` | 0.25 | Boolean array `[False] * n` for tracking used elements |
| `permutation_generation` | 0.30 | Appending to result list in permutation context |
| `recursive_exploration` | 0.20 | Recursive call with index increment |

### Gating Logic
Requires swap/recurse/swap OR visited array combined with permutation generation.

### Disambiguation

| Similar Pattern | Key Differentiator |
|----------------|-------------------|
| Subset generation | Uses append/pop, not swap/recurse/swap or visited array |
| Tree DFS | No permutation building or swap pattern |
| Ordinary recursion | No swap-back or visited tracking |

### Test Cases (10 tests)

**Positive (5):** Permutations (swap-based), Permutations (visited-array), Permutations II (duplicates), N-Queens style backtracking.

**Negative (5):** No recursion, Fibonacci, subset generation (cross-check: not detected as permutation), tree DFS, empty code.

---

## Full Suite Results

| Suite | Tests | Pass | Fail |
|-------|-------|------|------|
| Batch 7 standalone | 45 | 45 | 0 |
| Full merged suite | 409 | 409 | 0 |

---

## Taxonomy Update

| Metric | Before Batch 7 | After Batch 7 |
|--------|---------------|--------------|
| Total Implemented | 25 | 29 |
| Remaining | 8 | 4 |
| Heap / Greedy / Backtracking | 1/5 | 5/5 (complete) |
| Arrays & Hashing | 7/7 | 7/7 |
| Graphs & Trees | 7/7 | 7/7 |
| Linked Lists & Stack | 4/4 | 4/4 |
| Binary Search | 3/3 | 3/3 |
| Dynamic Programming | 0/7 | 0/7 |

## Next Phase

Remaining 4 patterns for implementation:
- **Dynamic Programming (7):** dp_1d_forward, dp_1d_sequence, dp_2d_grid, dp_2d_string, dp_knapsack, dp_interval, dp_state_machine
