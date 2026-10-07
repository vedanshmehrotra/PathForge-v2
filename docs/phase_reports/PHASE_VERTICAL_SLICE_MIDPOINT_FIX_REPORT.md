# Phase Vertical Slice — Midpoint Fix Report

**Date:** August 22, 2026
**Status:** COMPLETE — All 52 shadow tests + 551 existing tests pass

---

## Files Changed

| File | Change |
|---|---|
| `pathforge/ast_analysis/shadow/fact_extractor.py` | Added `visit_BinOp` handler, `_detect_midpoint_calculation` method, and 5 helper functions |
| `pathforge/ast_analysis/shadow/tests/test_shadow_analysis.py` | Added 11 new tests (7 fact extraction + 4 strategy interaction) |

**No production files modified.** No existing behavior changed.

---

## Structural Fact Definition

**Fact type:** `midpoint_calculation`

**Attributes:**
- `form`: Human-readable label (e.g., `(lo + hi) // 2`, `lo + (overflow-safe // 2)`)

**Version:** Uses existing `EXTRACTOR_VERSION = "1.0.0"` from `data_structures.py`

---

## Supported Forms

| Form | Example | AST Pattern |
|---|---|---|
| Standard floor-div | `(lo + hi) // 2` | `BinOp(FloorDiv, BinOp(Add, Name, Name), Const(2))` |
| Standard true-div | `(lo + hi) / 2` | `BinOp(Div, BinOp(Add, Name, Name), Const(2))` |
| Standard rshift | `(lo + hi) >> 1` | `BinOp(RShift, BinOp(Add, Name, Name), Const(1))` |
| Overflow-safe floor-div | `lo + (hi - lo) // 2` | `BinOp(Add, Name, BinOp(FloorDiv, BinOp(Sub, Name, Name), Const(2)))` |
| Overflow-safe true-div | `lo + (hi - lo) / 2` | `BinOp(Add, Name, BinOp(Div, BinOp(Sub, Name, Name), Const(2)))` |
| Overflow-safe rshift | `lo + (hi - lo) >> 1` | `BinOp(Add, Name, BinOp(RShift, BinOp(Sub, Name, Name), Const(1)))` |

**Key constraint:** The two variables in the inner Add/Sub must be distinct Name nodes. This prevents false positives on:
- `len(arr) // 2` — left is a `Call`, not a `Name`
- `total // 2` — left is a single `Name`, not a `BinOp(Add, ...)`
- `width // 2` — same as above

---

## False-Positive Cases Tested

| Code | Expected | Result |
|---|---|---|
| `len(arr) // 2` | NOT midpoint | ✅ Correct (left is `Call`, not `Name`) |
| `total // 2` | NOT midpoint | ✅ Correct (left is single `Name`, not `BinOp(Add, ...)`) |
| `n // 2` | NOT midpoint | ✅ Correct (single variable) |
| `width // 2` | NOT midpoint | ✅ Correct (single variable) |

---

## Binary Search Result

**Input:** Standard binary search with `(lo + hi) // 2`

```
Structural facts:
  - while_loop_comparison (lo <= hi, both modified)
  - midpoint_calculation ((lo + hi) // 2)
  - conditional_index_update (lo/hi updated in if/else)
  - early_termination (return)

Techniques detected:
  - bidirectional_index_scan (confidence: 0.9)

Strategies detected: none
  (two_pointers_opposite blocked by midpoint_calculation absence constraint)

Outcome: UNRESOLVED (no solution groups)
```

**Verification:**
- ✅ `midpoint_calculation` present
- ✅ `bidirectional_index_scan` present (both indices compared and updated)
- ✅ `two_pointers_opposite` NOT selected (absence constraint fires)

---

## Two-Pointer Result

**Input:** Palindrome check with `left += 1` / `right -= 1`

```
Structural facts:
  - while_loop_comparison (left < right, both modified)
  - opposite_direction_updates (left incremented, right decremented)
  - accumulator_update (left += 1, right -= 1)
  - early_termination (return False)

Techniques detected:
  - bidirectional_index_scan (confidence: 0.9)

Strategies detected:
  - two_pointers_opposite (confidence: 0.9)
  (midpoint_calculation absent → absence constraint passes)

Outcome: UNRESOLVED (no solution groups)
         → CONFIRMED when solution group requiring bidirectional_index_scan is provided
```

**Verification:**
- ✅ `midpoint_calculation` absent
- ✅ `bidirectional_index_scan` present
- ✅ `two_pointers_opposite` still selected

---

## Complete Test Results

### Shadow tests (52 total)

```
52 passed in 0.65s
```

| Category | Tests | Status |
|---|---|---|
| Fact extraction | 9 | ✅ All pass |
| Technique detection | 5 | ✅ All pass |
| Strategy detection | 5 | ✅ All pass |
| Matching | 5 | ✅ All pass |
| Authority gating | 3 | ✅ All pass |
| Shadow runner integration | 6 | ✅ All pass |
| Syntax normalization | 2 | ✅ All pass |
| Naming independence | 2 | ✅ All pass |
| Regression: membership | 1 | ✅ All pass |
| Graceful failure | 3 | ✅ All pass |
| Midpoint calculation | 7 | ✅ All pass |
| Midpoint strategy interaction | 4 | ✅ All pass |

### Existing tests (551 total)

```
551 passed in 1.88s
```

All existing detector tests, AST engine tests, and pipeline tests pass unchanged.

---

## Production Behavior Confirmation

| Check | Status |
|---|---|
| Existing `/analyze` endpoint behavior | ✅ UNCHANGED |
| Existing `verdict` / `verdict_type` | ✅ UNCHANGED |
| Existing ELO / topic profiles / gaps / recommendations | ✅ UNCHANGED |
| Existing AST detector output | ✅ UNCHANGED |
| Existing MatchingEngine output | ✅ UNCHANGED |
| Shadow analysis is observational only | ✅ CONFIRMED |

---

## Summary

The midpoint detection gap identified in the audit is now closed:

1. `midpoint_calculation` is a genuine structural fact — it observes a division-by-2 pattern on two distinct variables, without classifying it as any algorithm.
2. The `two_pointers_opposite` strategy's absence constraint now actually works — binary search is correctly excluded.
3. All 6 supported midpoint forms are detected (standard + overflow-safe × floor-div/true-div/rshift).
4. False-positive cases (`len(arr) // 2`, `total // 2`) are correctly rejected.
5. No production behavior changed.
