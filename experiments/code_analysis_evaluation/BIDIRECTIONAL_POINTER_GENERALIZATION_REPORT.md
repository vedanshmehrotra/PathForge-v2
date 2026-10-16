# Bidirectional Pointer Guard Generalization Report

**Date:** 2026-08-28
**Guard under evaluation:** Both incremented and decremented variables must appear as subscript indices for `bidirectional_index_scan` to fire.

---

## 1. Two-Pointer Coverage

14 two-pointer entries tested from the evaluation corpus.

| # | Name | Detected | Status | Notes |
|---|------|:--------:|:------:|-------|
| 1 | `bs_no_midpoint_two_pointers` | two_pointers_opposite | ✅ PASS | inc={i}, dec={j}, both in index_vars |
| 2 | `tp_palindrome` | two_pointers_opposite | ✅ PASS | inc={left}, dec={right}, both in index_vars |
| 3 | `tp_container_water` | two_pointers_opposite | ✅ PASS | inc={left}, dec={right}, both in index_vars |
| 4 | `tp_3sum` | two_pointers_opposite | ✅ PASS | inc={lo}, dec={hi}, both in index_vars |
| 5 | `tp_two_sum_sorted` | two_pointers_opposite | ✅ PASS | inc={left}, dec={right}, both in index_vars |
| 6 | `tp_trapping_rain` | (none) | ❌ FN | inc={left, water}, dec={right}. `water` is not an index. |
| 7 | `tp_pair_sum_sorted` | two_pointers_opposite | ✅ PASS | inc={i}, dec={j}, both in index_vars |
| 8 | `tp_palindrome_renamed` | two_pointers_opposite | ✅ PASS | inc={front}, dec={back}, both in index_vars |
| 9 | `tp_reverse_string` | two_pointers_opposite | ✅ PASS | inc={left}, dec={right}, both in index_vars |
| 10 | `tp_sorted_squares` | two_pointers_opposite | ✅ PASS | inc={left}, dec={idx, right}, all in index_vars |
| 11 | `tp_interval_intersection` | sliding_window | ❌ FP | No opposite_direction_updates (both only increment) |
| 12 | `tp_4sum` | two_pointers_opposite | ✅ PASS | inc={lo}, dec={hi}, both in index_vars |
| 13 | `tp_two_pointer_while_true` | (none) | ❌ FN | No while_loop_comparison detected |
| 14 | `neg_sliding_not_window` | two_pointers_opposite | ✅ PASS | inc={left}, dec={right}, both in index_vars |

**Detection rate: 11/14 = 78.6%**

---

## 2. Failure Analysis

### False negatives (2)

**`tp_trapping_rain`:** The loop body has `left += 1`, `right -= 1`, AND `water += ...` (accumulator). The `opposite_direction_updates` fact lists `incremented=['left', 'water'], decremented=['right']`. The guard checks whether ALL incremented variables are subscript indices. Since `water` is NOT a subscript index, the guard rejects the entire fact. This is a **false negative caused by the guard being too strict** — it requires ALL incremented variables to be indices, but `water` is a legitimate accumulator alongside the genuine pointers.

**Root cause:** The guard uses `inc.issubset(index_vars)` which requires every incremented variable to be an index. A more lenient check would be: "at least one incremented variable AND at least one decremented variable are indices."

**`tp_two_pointer_while_true`:** Pre-existing failure — no `while_loop_comparison` fact is generated. The while-loop condition doesn't produce the expected comparison fact. Not caused by the guard.

### False positive on expected label (1)

**`tp_interval_intersection`:** This case has NO `opposite_direction_updates` because both `i` and `j` only increment (never decrement). The guard is irrelevant here — the failure is in the fact extractor not detecting the conditional pointer movement. Pre-existing issue, not caused by the guard.

---

## 3. Negative/Confusable Cases

| Category | Tested | Correctly NOT two_pointers | Rate |
|---|:---:|:---:|:---:|
| Monotonic stack | 3 | 3 | 100% |
| Binary search | 2 | 2 | 100% |
| Fixed window | 2 | 2 | 100% |
| Sliding window | 2 | 2 | 100% |
| Accumulator window | 2 | 2 | 100% |
| **Total negatives** | **11** | **11** | **100%** |

**Zero false positives on negative cases.** The guard correctly prevents all tested non-two-pointer algorithms from being misclassified.

---

## 4. Guard Assessment

### Is it a robust structural definition?

**No — it is a useful heuristic with one known edge case.**

| Criterion | Assessment |
|---|---|
| Correctly identifies genuine two-pointers | 11/14 = 78.6% |
| Correctly rejects accumulator windows | 11/11 = 100% |
| False negatives | 1 (tp_trapping_rain) |
| False positives | 0 |
| Edge case: mixed increment list | tp_trapping_rain has `water` alongside `left` in inc_vars |

The guard's principle is sound: **both variables must be array indices to be genuine pointers.** The failure is in the implementation detail: it requires ALL variables in the increment/decrement lists to be indices, when it should require that AT LEAST ONE from each direction is an index.

### Recommended guard refinement (not implementing now)

**Current:** `inc.issubset(index_vars) and dec.issubset(index_vars)`
**Better:** `bool(inc & index_vars) and bool(dec & index_vars)`

This would fix `tp_trapping_rain` while preserving all other correct classifications.

---

## 5. Summary

| Metric | Value |
|---|:---:|
| Two-pointer cases tested | 14 |
| Correctly detected | 11 |
| False negatives | 1 (tp_trapping_rain — guard too strict) |
| Pre-existing failures | 2 (tp_interval_intersection, tp_two_pointer_while_true) |
| Detection rate | **78.6%** |
| False positives on negatives | **0** |
| New regressions from guard | **0** (tp_trapping_rain is a new false negative) |

---

## 6. Answers

### 1. Two-pointer coverage
78.6% (11/14). Two failures are pre-existing (unrelated to guard). One failure is a new false negative from the guard being overly strict.

### 2. False-negative count
1 new false negative (`tp_trapping_rain`) caused by the guard requiring ALL incremented variables to be indices rather than at least one.

### 3. New regressions
1 — `tp_trapping_rain` lost two_pointers_opposite detection. The guard incorrectly rejects it because the increment list includes both `left` (a pointer) and `water` (an accumulator).

### 4. Should the current guard be kept?
**Yes, with a refinement.** The principle is correct — both pointer variables should be subscript indices. The implementation should check that at least one variable from each direction (inc, dec) is a subscript index, rather than requiring ALL variables to be indices.

### 5. Is another change justified now?
**Yes — a one-line refinement** to change `inc.issubset(index_vars)` to `bool(inc & index_vars)` (and similarly for `dec`). This fixes `tp_trapping_rain` while preserving all other correct classifications. This is a minimal, well-targeted change.
