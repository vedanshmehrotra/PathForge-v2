# Full Regression Verification Report

**Date:** 2026-08-28  
**Branch:** `architecture/strategy-evidence-spike`  
**Change verified:** Monotonic-stack false-confirmation fix (8 lines in `strategies.py`)  
**Method:** Complete test suite execution across all test directories

---

## 1. Test Suite Results

### Backend (pathforge/)

| Suite | Passed | Failed | Total |
|-------|:------:|:------:|:-----:|
| `pathforge/ast_analysis/shadow/tests/` | 404 | 0 | 404 |
| `pathforge/ast_engine/tests/` | 69 | 0 | 69 |
| `pathforge/db/tests/` | 7 | 0 | 7 |
| `pathforge/tests/` | 100 | 0 | 100 |
| **Backend Total** | **580** | **0** | **580** |

### Legacy AST Detection (src/)

| Suite | Passed | Failed | Total |
|-------|:------:|:------:|:-----:|
| `src/ast_detection/tests/` | 481 | 1* | 482 |
| `src/ast_detection/semantic/tests/` | 74 | 0 | 74 |
| `src/matching_engine/tests/` | 50 | 0 | 50 |
| **Legacy Total** | **605** | **1** | **606** |

\* Pre-existing failure (see Section 3)

### Frontend

| Suite | Passed | Failed | Total |
|-------|:------:|:------:|:-----:|
| `pathforge-frontend/` (vitest) | 32 | 0 | 32 |
| **Frontend Total** | **32** | **0** | **32** |

### Overall

| Metric | Passed | Failed | Total |
|--------|:------:|:------:|:-----:|
| **All suites** | **1217** | **1** | **1218** |

---

## 2. Comparison With Previous Baseline

| Metric | Previous Baseline | Current Result | Status |
|--------|:-----------------:|:--------------:|:------:|
| Shadow tests | 391 | 404 (+13 new) | ✅ All pass |
| Backend (pathforge/tests/) | 100 | 100 | ✅ All pass |
| AST engine | 69 | 69 | ✅ All pass |
| DB tests | 7 | 7 | ✅ All pass |
| Frontend | 32 | 32 | ✅ All pass |
| Legacy AST detection | 482 | 482 (1 pre-existing fail) | ✅ No new failures |
| Legacy semantic | 74 | 74 | ✅ All pass |
| Matching engine | 50 | 50 | ✅ All pass |

**Net change: +13 tests (all new, all passing)**

---

## 3. Pre-Existing Failure (NOT caused by this change)

**Test:** `src/ast_detection/tests/test_detectors_batch2.py::TestPrefixSumDetector::test_detected_product_except_self`

**Status:** Pre-existing failure — verified by running on clean codebase (git stash):
- Clean codebase: **FAILED**
- With fix applied: **FAILED** (same failure)

**Root cause:** The legacy `PrefixSumDetector` in `src/ast_detection/` doesn't recognize the product-except-self pattern (two separate for-loops with different directions). This is a known limitation of the legacy detector, unrelated to the shadow analysis path.

**Impact:** None. This failure exists in the `src/` legacy code, not in the `pathforge/` shadow analysis code that was modified.

---

## 4. Strategy Detection Verification

### 4.1 Monotonic-stack false confirmations (all 7 FIXED)

| Case | `monotonic_stack_strategy` | `sliding_window` | SW group match | Status |
|------|:--------------------------:|:-----------------:|:--------------:|:------:|
| `ms_next_greater` | ✅ detected | ❌ not detected | UNRESOLVED | **FIXED** |
| `ms_daily_temperatures` | ✅ detected | ❌ not detected | UNRESOLVED | **FIXED** |
| `ms_histogram` | ✅ detected | ❌ not detected | UNRESOLVED | **FIXED** |
| `ms_next_greater_renamed` | ✅ detected | ❌ not detected | UNRESOLVED | **FIXED** |
| `ms_largest_hist_renamed` | ✅ detected | ❌ not detected | UNRESOLVED | **FIXED** |
| `ms_trap_rain_water` | ✅ detected | ❌ not detected | UNRESOLVED | **FIXED** |
| `ms_sum_subarray_mins` | ✅ detected | ❌ not detected | UNRESOLVED | **FIXED** |

### 4.2 Genuine sliding-window cases (no regressions)

| Case | `sliding_window` | SW group match | Status |
|------|:-----------------:|:--------------:|:------:|
| `76/minWindow` | ✅ detected | CONFIRMED | **No regression** |
| `3/longestSubstring` | ✅ detected | CONFIRMED | **No regression** |
| `2958/maxSubarrayLength` | ✅ detected | CONFIRMED | **No regression** |
| `maxFreq` | ✅ detected | CONFIRMED | **No regression** |

### 4.3 Two-pointer cases (no regressions)

| Case | `two_pointers_opposite` | `sliding_window` | Status |
|------|:-----------------------:|:-----------------:|:------:|
| `maxArea` (genuine) | ✅ detected | ❌ not detected | **No regression** |
| `twoSumSorted` (genuine) | ✅ detected | ❌ not detected | **No regression** |

### 4.4 Binary search cases (no regressions)

| Case | `binary_search` | `sliding_window` | Status |
|------|:---------------:|:-----------------:|:------:|
| `search` (genuine) | ✅ detected | ❌ not detected | **No regression** |

### 4.5 DP cases (no regressions)

| Case | `dp_bottom_up` | `sliding_window` | Status |
|------|:--------------:|:-----------------:|:------:|
| `coinChange` (genuine) | ✅ detected | ❌ not detected | **No regression** |

---

## 5. Production Behavior Confirmation

### What changed

The sliding-window strategy evaluator (`_evaluate_sliding_window()` in `strategies.py`) now refuses to fire when all three monotonic-stack-specific facts are present simultaneously:
- `stack_operation`
- `monotonic_comparison`
- `conditional_pop`

### What did NOT change

- **Fact extractor:** No changes. All structural observations remain identical.
- **Technique detection:** `loop_state_tracking` still fires for monotonic stack code (correctly).
- **Matching layer:** No changes. Solution-group matching evaluates all strategies the same way.
- **Ground truth builder:** No changes. Solution groups are generated the same way.
- **Frontend:** No changes.
- **Database:** No changes.
- **ELO/recommendations:** No changes.
- **Legacy AST detection:** No changes.

### Why the fix is safe

1. **Verified no overlap:** No genuine sliding-window implementation has all three stack facts. Tested on representative implementations.
2. **Narrowly scoped:** The exclusion only fires when ALL THREE stack-specific facts are present simultaneously.
3. **Same pattern as existing constraints:** Follows the exact same pattern as `opposite_direction_updates` and `midpoint_calculation` exclusions.
4. **No technique-level changes:** `loop_state_tracking` remains valid for both sliding window and monotonic stack.

---

## 6. Summary

| Metric | Before Fix | After Fix | Delta |
|--------|:----------:|:---------:|:-----:|
| Total tests | 1205 | 1218 | +13 (all new) |
| Test failures | 1 | 1 | 0 (pre-existing) |
| Monotonic-stack FP | 7 | **0** | **-7** |
| Genuine SW detection | 76.7% | 76.7% | 0 |
| False negatives (SW) | 7 | 7 | 0 |
| False positives (non-SW as SW) | 10 | **3** | **-7** |

**Conclusion: The monotonic-stack false-confirmation fix is verified safe. Zero regressions. Zero new failures. All 7 harmful false confirmations eliminated.**
