# Phase 3C — Batch 2 Implementation Report

## Summary

Implemented 5 new pattern detectors (Batch 2) following the validated Batch 1 methodology. Total detectors: 10 (5 Batch 1 + 5 Batch 2). All 199 tests pass (67 Batch 1 detector tests + 51 Batch 2 detector tests + 81 infrastructure tests).

## New Detectors

### 1. Two Pointers Same Direction (`two_pointers_same`)
- **File**: `detectors/two_pointers_same.py`
- **Class**: `TwoPointersSameDetector`
- **Evidence Strategy**:
  - `slow_fast_differential` (0.40): While loop where >= 2 variables are incremented by different step sizes (e.g., `slow += 1; fast += 2`). Core gated signal.
  - `offset_pointer_assignment` (0.30): While loop with >= 2 pointer variables assigned in body, >= 1 referenced in condition. Linked-list style (`.next` attribute access).
- **Known Limitations**:
  - Does not detect offset-pointer setup without a while loop (e.g., `for` loop with two advancing indices at different rates)
  - Does not detect `n`-pointer patterns (3+ pointers) unless they exhibit the differential speed signal
  - Linked list detection requires `.next` attribute or multiple assigned variables in loop body

### 2. Two Pointers Opposite Direction (`two_pointers_opposite`)
- **File**: `detectors/two_pointers_opposite.py`
- **Class**: `TwoPointersOppositeDetector`
- **Evidence Strategy**:
  - `convergence_loop` (0.40): While loop with `left < right` or `left <= right` convergence condition. Core gated signal.
  - `left_pointer_increment` (0.25): `left += 1` in one branch of if/elif/else.
  - `right_pointer_decrement` (0.25): `right -= 1` in another branch.
- **Handles**: if/elif/else chains via `_flatten_branches()` which recursively processes nested `If` nodes in `orelse`.
- **Known Limitations**:
  - Requires both `left += 1` and `right -= 1` in the same while body
  - Requires specific `left < right` condition pattern (does not detect `while i <= j:` generically unless both sides are Name nodes)

### 3. Sliding Window Fixed (`sliding_window_fixed`)
- **File**: `detectors/sliding_window_fixed.py`
- **Class**: `SlidingWindowFixedDetector`
- **Evidence Strategy**:
  - `window_size_check` (0.30): For loop with if-condition checking window boundary (involving the loop variable). Core gated signal.
  - `window_expand` (0.20): For loop advancing right pointer.
  - `window_shrink_fixed` (0.35): Element removal (`window_sum -= arr[left]`) and/or left pointer advancement (`left += 1`) inside the bound check.
- **Handles**: Variable-name checks via `_contains_name()` for complex expressions like `right >= len(p) - 1`.
- **Known Limitations**:
  - Requires for loop with if-boundary-check and element removal in the if body
  - Does not detect window patterns without explicit `window_sum -=` or `.pop()` operations

### 4. Sliding Window Variable (`sliding_window_variable`)
- **File**: `detectors/sliding_window_variable.py`
- **Class**: `SlidingWindowVariableDetector`
- **Evidence Strategy**:
  - **While-loop variant** (standard):
    - `window_shrink_variable` (0.40): Inner while loop with `left_ptr++` for window contraction. Core gated signal.
    - `window_expand` (0.20): For loop with right pointer advancing.
    - `window_validity_check` (0.30): While condition contains window state operations (`.get()`, comparison with non-pointer variables).
  - **If-assignment variant** (e.g., Longest Substring):
    - `window_shrink_variable` (0.35): For loop with assignment to left pointer inside if-condition.
    - `window_expand` (0.20): For loop with right pointer advancing.
- **Known Limitations**:
  - Does not detect variable window without a left pointer initialized to 0 before the loop
  - The if-assignment variant requires a left pointer reassignment inside a conditional within the loop body

### 5. Prefix Sum (`prefix_sum`)
- **File**: `detectors/prefix_sum.py`
- **Class**: `PrefixSumDetector`
- **Evidence Strategy**:
  - `prefix_array_construction` (0.40): For loop building cumulative array via subscript formula or `.append()` with cumulative operation. Core gated signal.
  - `prefix_accumulator` (0.30): Cumulative `+=`, `*=`, or `-=` operation in loop body.
  - `running_sum_update` (0.30): Running sum variable updated with `+=` in loop.
  - `dictionary_prefix_lookup` (0.35): Prefix sums stored in dict for O(1) lookup.
- **Patterns Detected**:
  - Classic prefix array: `prefix[i] = prefix[i-1] + arr[i-1]`
  - Append-based: `prefix.append(prefix[-1] + num)`
  - Running sum + dict: `running_sum += num; seen[running_sum] = index`
  - Cumulative product: `prefix *= nums[i]` (Product of Array Except Self)
- **Known Limitations**:
  - May miss prefix patterns where accumulation and storage are spread across multiple loops
  - The dictionary lookup pattern requires both accumulate-and-store and dictionary-lookup patterns in the same loop

## Implementation Notes

### Coding Conventions
- Follows Batch 1 style exactly: module-level docstring, `BaseDetector` subclass with `@register_detector`, `pattern_id` class attribute, `detect()` method returning `DetectionResult`, private `_detect_*` methods for each signal type, `_calculate_confidence()` with `min(total, 1.0)`.
- All detectors use the same import pattern: `from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem`.
- No external dependencies beyond `ast` module.

### False Positive Prevention
- Each detector gates on core structural signals:
  - `two_pointers_same`: Requires differential increment rates in while loop body
  - `two_pointers_opposite`: Requires both `left += 1` and `right -= 1` in same while body
  - `sliding_window_fixed`: Requires element removal in the bound-check if body
  - `sliding_window_variable`: Requires left pointer increment/assignment inside inner while/if
  - `prefix_sum`: Requires prefix formula or dictionary lookup with running sum update

### Deterministic Behavior
All detectors are deterministic — same code always produces same confidence and detected status for all test cases.

## Registry Status

```python
_detector_registry.list_pattern_ids() == [
    'brute_force', 'array_traversal', 'sorting',
    'hash_map_lookup', 'hash_map_frequency',
    'two_pointers_same', 'two_pointers_opposite',
    'sliding_window_fixed', 'sliding_window_variable',
    'prefix_sum'
]
count = 10
```

## Test Coverage

| Detector | Tests | Status |
|----------|-------|--------|
| TwoPointersSame | 12 | All pass |
| TwoPointersOpposite | 8 | All pass |
| SlidingWindowFixed | 8 | All pass |
| SlidingWindowVariable | 8 | All pass |
| PrefixSum | 9 | All pass |
| Infrastructure regression | 6 | All pass |
| **Total new** | **51** | **All pass** |

## Next Steps

1. **Phase 3C.2.3**: Implement Batch 3 (binary search, monotonic stack, heap)
2. **Real-code validation**: Run all 10 detectors against the 146 LeetCode-inspired patterns
3. **Phase 3D**: Matching Engine implementation
