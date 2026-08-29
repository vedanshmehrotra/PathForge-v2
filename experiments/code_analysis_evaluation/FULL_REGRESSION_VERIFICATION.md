# Full Regression Verification Report

**Date:** 2026-08-29  
**Branch:** `architecture/strategy-evidence-spike`  
**Change verified:** Monotonic-stack false-confirmation fix + opposite_direction_updates refinement (16 lines total in `strategies.py`)  
**Method:** Complete test suite execution across all test directories

---

## 1. Test Suite Results

### Backend (pathforge/)

| Suite | Passed | Failed | Total |
|-------|:------:|:------:|:-----:|
| `pathforge/ast_analysis/shadow/tests/` | 417 | 0 | 417 |
| `pathforge/ast_engine/tests/` | 69 | 0 | 69 |
| `pathforge/db/tests/` | 7 | 0 | 7 |
| `pathforge/tests/` | 100 | 0 | 100 |
| **Backend Total** | **593** | **0** | **593** |

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
| **All suites** | **1230** | **1** | **1231** |

---

## 2. Comparison With Previous Baseline

| Metric | Previous Baseline | Current Result | Status |
|--------|:-----------------:|:--------------:|:------:|
| Shadow tests | 391 | 417 (+26 new) | ✅ All pass |
| Backend (pathforge/tests/) | 100 | 100 | ✅ All pass |
| AST engine | 69 | 69 | ✅ All pass |
| DB tests | 7 | 7 | ✅ All pass |
| Frontend | 32 | 32 | ✅ All pass |
| Legacy AST detection | 482 | 482 (1 pre-existing fail) | ✅ No new failures |
| Legacy semantic | 74 | 74 | ✅ All pass |
| Matching engine | 50 | 50 | ✅ All pass |

**Net change: +26 tests (all new, all passing)**

---

## 3. Pre-Existing Failure (NOT caused by this change)

**Test:** `src/ast_detection/tests/test_detectors_batch2.py::TestPrefixSumDetector::test_detected_product_except_self`

**Status:** Pre-existing failure — verified by running on clean codebase (git stash):
- Clean codebase: **FAILED**
- With both fixes applied: **FAILED** (same failure)

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

### 4.1b LC 209 accumulator-shrink sliding window (NEWLY FIXED)

| Case | `sliding_window` | `two_pointers_opposite` | Status |
|------|:-----------------:|:-----------------------:|:------:|
| `minSubArrayLen` (LC 209) | ✅ detected | ❌ not detected | **NEWLY FIXED** |
| `minSubArrayLen` modulo-style variant | ✅ detected | ❌ not detected | **NEWLY FIXED** |

### 4.2 Genuine sliding-window cases (no regressions)

| Case | `sliding_window` | SW group match | Status |
|------|:-----------------:|:--------------:|:------:|
| `3/longestSubstring` | ✅ detected | CONFIRMED | **No regression** |
| `2958/maxSubarrayLength` | ✅ detected | CONFIRMED | **No regression** |
| `424/characterReplacement` (while-shrink) | ✅ detected | CONFIRMED | **No regression** |
| `maxFreq` | ✅ detected | CONFIRMED | **No regression** |
| `76/minWindow` | ⚠️ blocked (pre-existing) | — | **Pre-existing limitation** |

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

### What changed (Fix 1: Monotonic-stack exclusion)

The sliding-window strategy evaluator (`_evaluate_sliding_window()` in `strategies.py`) now refuses to fire when all three monotonic-stack-specific facts are present simultaneously:
- `stack_operation`
- `monotonic_comparison`
- `conditional_pop`

### What changed (Fix 2: opposite_direction_updates refinement)

The `opposite_direction_updates` exclusion is now refined: instead of blanket-blocking sliding_window whenever opposite direction updates exist, it only blocks when a `while_loop_comparison` has `compared_variables ⊆ modified_variables` (genuine two-pointer pattern). In sliding-window shrink loops, the while condition compares a state expression against a threshold, so at least one compared variable is NOT modified.

### What did NOT change

- **Fact extractor:** No changes. All structural observations remain identical.
- **Technique detection:** `loop_state_tracking` still fires for monotonic stack code (correctly).
- **Matching layer:** No changes. Solution-group matching evaluates all strategies the same way.
- **Ground truth builder:** No changes. Solution groups are generated the same way.
- **Frontend:** No changes.
- **Database:** No changes.
- **ELO/recommendations:** No changes.
- **Legacy AST detection:** No changes.

### Why both fixes are safe

1. **Verified no overlap:** No genuine sliding-window implementation has all three stack facts. Tested on representative implementations.
2. **Narrowly scoped:** The monotonic-stack exclusion only fires when ALL THREE stack-specific facts are present simultaneously.
3. **Same pattern as existing constraints:** Follows the exact same pattern as `midpoint_calculation` exclusions.
4. **No technique-level changes:** `loop_state_tracking` remains valid for both sliding window and monotonic stack.
5. **opposite_direction refinement uses existing structural facts:** The `while_loop_comparison` fact already carries `compared_variables` and `modified_variables`; no new fact types added.
6. **Structural distinction is genuine:** Two-pointer loops modify ALL compared variables; sliding-window shrink loops modify only the state variable (not the threshold).

---

## 6. Summary

| Metric | Before Fixes | After Fixes | Delta |
|--------|:----------:|:---------:|:-----:|
| Total tests | 1205 | 1231 | +26 (all new) |
| Test failures | 1 | 1 | 0 (pre-existing) |
| Monotonic-stack FP | 7 | **0** | **-7** |
| LC 209 FP (SW blocked) | 1 | **0** | **-1** |
| Genuine SW detection | 4/5 | 4/5 | 0 |
| False positives (non-SW as SW) | 10 | **3** | **-7** |

**Conclusion: Both fixes are verified safe. Zero regressions. Zero new failures. All 7 harmful monotonic-stack false confirmations eliminated. LC 209 accumulator-shrink sliding window now correctly detected.**
