# SLIDING_WINDOW_209_FIX_REPORT.md

**Date:** 2026-08-29  
**Fix:** Refine `opposite_direction_updates` exclusion in sliding-window strategy evaluator

## Problem

LC 209 (Minimum Size Subarray Sum) is a legitimate variable-size sliding-window solution:

```python
while total >= target:
    total -= nums[left]
    left += 1
```

The shrink loop modifies `total` (decremented via `total -= nums[left]`) and `left` (incremented via `left += 1`). Both are bare Name AugAssign targets — one subtracts, one adds → `opposite_direction_updates` fires → blanket exclusion blocks `sliding_window`.

**Root cause:** The `opposite_direction_updates` constraint was designed to prevent generic loops from being classified as sliding-window, but it also catches legitimate sliding-window shrink loops where an accumulator and pointer move in opposite directions.

## Code Change

**File:** `pathforge/ast_analysis/shadow/strategies.py`  
**Method:** `_evaluate_sliding_window()`

### Before (blanket exclusion):
```python
has_opposite = "opposite_direction_updates" in fact_types
if has_opposite:
    return None
```

### After (refined exclusion):
```python
# Absence constraint: must NOT have opposite_direction_updates in a
# genuine two-pointer loop (where both compared variables are modified).
# In sliding-window shrink loops, the while condition compares a state
# expression against a threshold (e.g., while total >= target), so at
# least one compared variable (the threshold/constant) is NOT modified.
# The pointer update (left += 1) involves a variable NOT in the
# comparison — only the accumulator/state is modified.
if "opposite_direction_updates" in fact_types:
    has_genuine_opposite = False
    for wc in [f for f in facts if f.fact_type == "while_loop_comparison"]:
        compared = set(wc.attributes.get("compared_variables", []))
        modified = set(wc.attributes.get("modified_variables", []))
        if compared and compared <= modified:
            has_genuine_opposite = True
    if has_genuine_opposite:
        return None
```

**Logic:** Only block sliding-window when there exists a `while_loop_comparison` where `compared_variables ⊆ modified_variables`. In genuine two-pointer loops (e.g., `while left < right`), both `left` and `right` are compared AND both are modified. In sliding-window shrink loops (e.g., `while total >= target`), `total` is compared and modified, but `target` is only compared — so `compared ⊄ modified`, and the exclusion does not fire.

## Before/After Results

| Case | Before | After |
|------|--------|-------|
| LC 209 `minSubArrayLen` (accumulator shrink) | BLOCKED ❌ | DETECTED ✅ |
| LC 424 `characterReplacement` (counter shrink) | DETECTED ✅ | DETECTED ✅ |
| LC 3 `lengthOfLongestSubstring` (set membership) | DETECTED ✅ | DETECTED ✅ |
| LC 2958 `maxSubarrayLength` (dict freq) | DETECTED ✅ | DETECTED ✅ |
| LC 76 `minWindow` (nested while-in-if) | BLOCKED (pre-existing) | BLOCKED (pre-existing) |
| maxFreq (counter shrink) | DETECTED ✅ | DETECTED ✅ |
| Genuine two-pointers `twoSumSorted` | two_pointers_opposite ✅ | two_pointers_opposite ✅ |
| Genuine two-pointers `maxArea` | two_pointers_opposite ✅ | two_pointers_opposite ✅ |
| Binary search | binary_search ✅ | binary_search ✅ |
| Monotonic stack `nextGreater` | monotonic_stack ✅ | monotonic_stack ✅ |

### LC 209 Evidence

**Fact-level:**
- `while_loop_comparison`: compared=`{total, target}`, modified=`{total}`, cross_variable=True
- Since `{total, target} ⊄ {total}` → `compared ⊄ modified` → exclusion does NOT fire
- `opposite_direction_updates`: present (but now refined by comparison check)

**Technique-level:**
- `loop_state_tracking`: fires (accumulator modified in loop body, used in while condition)
- `variable_use_in_loop_body`: fires (`total` used in `while total >= target`)
- `conditional_index_update`: fires (branch="while", `left += 1`)

**Strategy-level:**
- Required: `loop_state_tracking` ✅, `variable_use_in_loop_body` ✅, loop ✅
- Exclusions: `midpoint_calculation` absent ✅, monotonic-stack facts absent ✅, genuine opposite NOT present ✅
- → `sliding_window` fires

## Test Results

| Suite | Passed | Failed | Total |
|-------|:------:|:------:|:-----:|
| Shadow (`pathforge/ast_analysis/shadow/`) | 417 | 0 | 417 |
| Backend (`pathforge/tests/`) | 100 | 0 | 100 |
| DB (`pathforge/db/tests/`) | 7 | 0 | 7 |
| Frontend (vitest) | 32 | 0 | 32 |
| Legacy AST (`src/ast_detection/tests/`) | 481 | 1* | 482 |
| Legacy Semantic | 74 | 0 | 74 |
| Matching Engine | 50 | 0 | 50 |
| **Overall** | **1161** | **1** | **1162** |

\* Pre-existing failure: `test_detected_product_except_self` — not caused by this change.

### New Regression Tests Added

13 new tests in `TestOppositeDirectionUpdatesRefinement`:
- `test_209_accumulator_shrink_detected` — LC 209 detected as sliding_window
- `test_209_modulo_style_detected` — LC 209 variant with renamed variables
- `test_209_loop_state_tracking_detected` — technique still fires
- `test_genuine_two_pointers_still_not_sliding_window` — twoSumSorted protected
- `test_genuine_two_pointers_max_area_still_not_sliding_window` — maxArea protected
- `test_binary_search_not_sliding_window` — binary search protected
- `test_monotonic_stack_not_sliding_window` — monotonic stack protected
- `test_424_counter_shrink_detected` — LC 424 still works
- `test_3_set_membership_detected` — LC 3 still works
- `test_2958_dict_freq_detected` — LC 2958 still works
- `test_643_fixed_window_detected` — fixed window not blocked
- `test_max_freq_counter_shrink_detected` — maxFreq still works
- `test_76_min_window_still_works` — LC 76 pre-existing limitation documented

### Updated Test

- `test_209_accumulator_not_two_pointers` — updated to assert `sliding_window` IS detected (was documenting as known limitation, now fixed)

## Verification

- ✅ All 7 previously-confirmed sliding-window detections remain confirmed
- ✅ All 7 monotonic-stack false confirmations remain fixed (from prior fix)
- ✅ Genuine two-pointer detection preserved
- ✅ Binary search detection preserved
- ✅ No new test failures
- ✅ Only `_evaluate_sliding_window()` modified (8 lines added)
- ✅ No fact extractor, technique, MatchingEngine, ground truth, ELO, frontend, or database changes

## Remaining Sliding-Window Limitations

1. **LC 76 (Minimum Window Substring):** The `while missing == 0:` loop is nested inside an `if` block. The `variable_use_in_loop_body` detector only fires for subsequent statements within the same loop body scope. Due to the deeply nested structure, the def-use chain does not capture `left` as a used variable. This is a pre-existing limitation of the fact extractor, not caused by this fix.

2. **LC 424 (if-shrink variant):** The if-based shrink pattern where the modified variable is only used in the return statement outside the for-loop body is not yet captured by the def-use chain detector. This is a known limitation (documented in `TestKnownLimitations`).

3. **Fixed-window detection:** Requires `fixed_window_maintenance` technique + `window_size_constant` fact. The 2-stage pipeline (for-loop + while-loop) for fixed windows is detected, but the initial sum computation pattern may not always fire. This is a Phase 1 limitation.
