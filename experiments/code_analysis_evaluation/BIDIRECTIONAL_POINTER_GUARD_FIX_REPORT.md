# Bidirectional Pointer Guard Fix Report

**Date:** 2026-08-28
**Change:** One-line guard refinement in `pathforge/ast_analysis/shadow/techniques.py`

---

## 1. Exact Change

**File:** `pathforge/ast_analysis/shadow/techniques.py`, line 175

**Before:**
```python
if not (inc.issubset(index_vars) and dec.issubset(index_vars)):
    return None
```

**After:**
```python
if not (bool(inc & index_vars) and bool(dec & index_vars)):
    return None
```

**Semantic change:** From "every incremented/decremented variable must be a subscript index" to "at least one incremented AND at least one decremented variable must be a subscript index."

---

## 2. Before/After: tp_trapping_rain

| Metric | Before | After |
|---|---|---|
| `bidirectional_index_scan` | NOT detected | **Detected** |
| `two_pointers_opposite` | NOT detected | **Detected** |
| Match outcome | UNRESOLVED | CONFIRMED (against TP group) |

**Root cause of previous failure:** The increment list was `['left', 'water']`. `water` is an accumulator, not a subscript index. The old `issubset` check required ALL variables to be indices. The new `bool(inc & index_vars)` check only requires at least one.

---

## 3. Two-Pointer Detection Rate

| Metric | Before (old guard) | After (new guard) |
|---|:---:|:---:|
| Two-pointer cases tested | 14 | 14 |
| Correctly detected | 11 | **12** |
| Detection rate | 78.6% | **85.7%** |
| False negatives | 1 (tp_trapping_rain) | **0 from guard** |
| Pre-existing failures | 2 | 2 (unchanged) |

The 2 remaining failures are pre-existing and unrelated to the guard:
- `tp_interval_intersection`: no `opposite_direction_updates` (both pointers only increment)
- `tp_two_pointer_while_true`: no `while_loop_comparison` fact generated

---

## 4. Negative-Case Results

| Category | Tested | Correctly NOT two_pointers | Rate |
|---|:---:|:---:|:---:|
| Accumulator windows | 3 | 3 | 100% |
| Monotonic stack | 1 | 1 | 100% |
| Binary search | 1 | 1 | 100% |
| **Total negatives** | **5** | **5** | **100%** |

**Zero false positives introduced.**

---

## 5. Tests Added/Updated

| Test | Purpose |
|------|---------|
| `test_two_pointers_with_accumulator` | tp_trapping_rain: two pointers + water accumulator |
| `test_two_pointers_without_accumulator` | Genuine two-pointers with only pointer variables |
| `test_two_pointers_renamed_variables` | Two-pointers with renamed variables (front/back) |
| `test_accumulator_window_still_rejected` | Accumulator window NOT two_pointers_opposite |
| `test_monotonic_stack_not_two_pointers` | Monotonic stack NOT two_pointers_opposite |
| `test_binary_search_not_two_pointers` | Binary search NOT two_pointers_opposite |

---

## 6. Test Totals

| Suite | Before | After | Change |
|---|:---:|:---:|:---:|
| Backend (pathforge/) | 640 | 651 | +11 |
| Shadow (pathforge/ast_analysis/shadow/) | 385 | 391 | +6 |
| Frontend (vitest) | 32 | 32 | 0 |
| **Total** | **1057** | **1074** | **+17** |

All 1074 tests pass. Zero failures. Zero regressions.

---

## 7. Summary

| Metric | Value |
|---|:---:|
| Lines changed | 1 |
| tp_trapping_rain fixed | ✅ |
| Two-pointer detection rate | 85.7% (12/14) |
| False positives on negatives | 0 |
| New regressions | 0 |
| Total tests | 1074 |
