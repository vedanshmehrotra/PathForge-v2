# DP Detector Compliance Report — Phase 3C.2.8B

**Date:** 2026-07-04  
**Status:** COMPLETE  
**Reference:** DETECTOR_DECISION_RULE.md v1.0 (Frozen)

---

## Audit Scope

All 7 DP detectors audited and aligned with DETECTOR_DECISION_RULE.md.

| # | Detector | File |
|---|----------|------|
| 1 | dp_1d_forward | `src/ast_detection/detectors/dp_1d_forward.py` |
| 2 | dp_1d_sequence | `src/ast_detection/detectors/dp_1d_sequence.py` |
| 3 | dp_2d_grid | `src/ast_detection/detectors/dp_2d_grid.py` |
| 4 | dp_2d_string | `src/ast_detection/detectors/dp_2d_string.py` |
| 5 | dp_knapsack | `src/ast_detection/detectors/dp_knapsack.py` |
| 6 | dp_interval | `src/ast_detection/detectors/dp_interval.py` |
| 7 | dp_state_machine | `src/ast_detection/detectors/dp_state_machine.py` |

---

## Rules Verification

### Rule 2: detected != confidence threshold

All 7 detectors use explicit gating logic in `detect()` — `detected` is a boolean
computed from evidence combinations, NOT from `confidence > 0`.

**Result: COMPLIANT**

### Rule 3: Detection gating is explicit

Each detector has:
1. Evidence collection phase
2. Boolean gating from evidence types
3. Anti-signal override (post-gating)
4. DetectionResult constructed with explicit `detected` field

**Result: COMPLIANT**

### Rule 4: Anti-signal override confidence

Each detector now has `_has_anti_signals()` that runs AFTER gating.
When anti-signals fire, `detected` is forced to `False` regardless of confidence.

| Detector | Anti-signal rule |
|----------|-----------------|
| dp_1d_forward | Prefix-sum pattern (single lookback, no multi-level, no max/min, no conditional, no recursive) |
| dp_1d_sequence | Lookback-only evidence without array/recurrence/aggregation |
| dp_2d_grid | String comparison present (suggests string DP, not grid DP) |
| dp_2d_string | No string comparison evidence (contradicts string DP requirement) |
| dp_knapsack | Capacity comparison without max/min recurrence |
| dp_interval | String comparison present (suggests string DP, not interval DP) |
| dp_state_machine | State variables without state transition |

**Result: COMPLIANT**

### Rule 5: DP remains structural-only

Removed semantic naming inference:

- **dp_knapsack**: Removed `WEIGHT_VARS` class attribute. `_find_capacity_compare` now
  uses structural detection (comparison operators involving subscript access in nested
  loops) instead of variable-name matching.

- **dp_state_machine**: Removed `STATE_NAMES` class attribute. `_find_state_variables`
  and `_find_state_transition` now use structural detection:
  - Identifies state variables by intersecting loop-assigned variables with
    max/min argument variables
  - Handles tuple unpacking (e.g., `prev0, prev1 = curr0, curr1`)
  - Detects multi-state arrays (2+ distinct subscript writes to same base)
  - Detects state transitions by matching max/min calls to assignment targets

Remaining variable name matching (`dp` prefix for array variables) is structural
convention, not semantic inference.

**Result: COMPLIANT**

### Rule 6: Memoization not sufficient alone

Memoization (`cache_decorator`) is always combined with:
- `effective_lookback` in dp_1d_forward (recurrence structure)
- `state_transition` in dp_state_machine (state transition dependency)

No detector uses memoization as the sole signal for detection.

**Result: COMPLIANT**

### Rule 7: Confidence is ranking signal, not binary classifier

Confidence remains computed from evidence weights. It is never used as the
sole determinant of `detected`. Gating and anti-signals operate independently.

**Result: COMPLIANT**

### Rule 10: Default to NOT DETECTED

When no evidence exists or gating fails, `detected` defaults to `False` in all detectors.

**Result: COMPLIANT**

---

## Changes Summary

### dp_1d_forward.py
- Moved `not_prefix_sum` from gating condition to explicit `_has_anti_signals()` override
- Anti-signal fires when prefix-sum pattern detected (single lookback without multi-level/max-min/conditional/recursive)

### dp_1d_sequence.py
- Added `_has_anti_signals()` — overrides detection when only lookback evidence exists
  without array/recurrence/aggregation

### dp_2d_grid.py
- Added `_has_anti_signals()` — overrides detection when string comparison is present
  (to avoid overlap with string DP)

### dp_2d_string.py
- Added `_has_anti_signals()` — overrides detection when string comparison is absent
  (enforcement: string DP requires string comparison evidence)

### dp_knapsack.py
- Removed `WEIGHT_VARS` semantic class attribute
- `_find_capacity_compare()` now uses structural detection: comparison operators
  (>=, <=, >, <) on subscript access in loops
- Added `_has_anti_signals()` — overrides detection when capacity compare exists
  but no max/min recurrence

### dp_interval.py
- Moved `not has_string` from gating condition to `_has_anti_signals()` override
- Anti-signal fires when string comparison is present

### dp_state_machine.py
- Removed `STATE_NAMES` semantic class attribute
- `_find_state_variables()` now structurally detects state variables by:
  - Collecting loop-assigned variables (supporting tuple unpacking)
  - Collecting max/min argument variables
  - Computing intersection (2+ candidates → state machine)
  - Counting multi-subscript writes (2+ writes to same base → multi-state array)
- `_find_state_transition()` now structurally detects transitions by:
  - Linking max/min calls to state variable assignments
- `_find_result_aggregation()` uses structural name detection instead of STATE_NAMES
- Added `_has_anti_signals()` — overrides when state variables exist without transitions

---

## Regression Tests

All 472 tests pass across the entire test suite:

```
src/ast_detection/tests/test_detectors.py           (batch 1)
src/ast_detection/tests/test_detectors_batch2.py    (batch 2)
src/ast_detection/tests/test_detectors_batch3.py    (batch 3)
src/ast_detection/tests/test_detectors_batch4.py    (batch 4)
src/ast_detection/tests/test_detectors_batch5.py    (batch 5)
src/ast_detection/tests/test_detectors_batch6.py    (batch 6)
src/ast_detection/tests/test_detectors_batch7.py    (batch 7)
src/ast_detection/tests/test_detectors_batch8.py    (batch 8 - DP)
src/ast_detection/tests/test_detector_interface.py
src/ast_detection/tests/test_detector_manager.py
src/ast_detection/tests/test_output_pipeline.py
src/ast_detection/tests/test_parser.py
src/ast_detection/tests/test_registry.py
src/ast_detection/tests/test_run_analysis.py
```

**Result: 472/472 passed**

---

## Compliance Confirmation

| Rule | Requirement | Status |
|------|-------------|--------|
| 2 | detected != confidence threshold | COMPLIANT |
| 3 | At least one valid structural evidence | COMPLIANT |
| 3 | Detector-specific gating conditions | COMPLIANT |
| 4 | Anti-signals override confidence | COMPLIANT |
| 5 | No semantic inference as primary signal | COMPLIANT |
| 6 | Memoization not sufficient alone | COMPLIANT |
| 7 | Confidence is ranking signal only | COMPLIANT |
| 10 | Default to NOT DETECTED | COMPLIANT |

**All DP detectors are aligned with DETECTOR_DECISION_RULE.md.**

---

## Stop Condition

Phase 3C.2.8B compliance verification complete.  
Do NOT proceed to Phase 3D.
