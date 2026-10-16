# Sliding Window Fact-Extraction Fix Report

**Date:** 2026-08-28
**Scope:** Shadow structural fact extractor only
**Files changed:** 1 (`pathforge/ast_analysis/shadow/fact_extractor.py`)
**Tests added:** 1 (`pathforge/ast_analysis/shadow/tests/test_sliding_window_fixes.py` — 20 tests)

---

## 1. Files Changed

| File | Lines changed | Nature |
|------|:------------:|--------|
| `pathforge/ast_analysis/shadow/fact_extractor.py` | ~60 lines added/modified | Three detection improvements |

No other production files were modified. No strategy rules, no technique rules, no database changes, no frontend changes.

---

## 2. Exact Changes

### Fix 1: Cross-variable while-loop comparison (`_emit_while_comparison_from_compares`)

**Before:** `while_loop_comparison` fired only when `comp_names ∩ modified_names ≠ ∅`. If the compared variables and modified variables had no overlap, no fact was emitted — making the entire while loop invisible.

**After:** When `comp_names ∩ modified_names` is empty but `modified_names` is non-empty, emits `while_loop_comparison` with `cross_variable: True` attribute. This captures sliding-window shrink loops where the compared state expression (dict lookup, set membership) differs from the pointer being advanced.

**Preserved:** Same-variable path (two-pointers, binary search) is completely unchanged.

### Fix 2: `conditional_index_update` for while-loop bodies

**Before:** `_detect_conditional_index_update_in_for` and `_detect_loop_body_conditional_updates` only checked `if` statements. While-loop shrink bodies were never scanned.

**After:** Both methods also check `elif isinstance(stmt, ast.While)` and emit `conditional_index_update` with `branch: "while"` when variables are augmented in the while body. This captures `while cond: left += 1` as a conditional update.

### Fix 3: Def-use chain for while-loop body variables

**Before:** `_detect_variable_use_in_loop_body` and `_detect_variable_use_in_loop_body_for` only collected conditionally-updated variables from `if` statements, and only checked non-if statements after the if for variable use.

**After:** Both methods also collect variables augmented inside `while`-loop bodies and check:
- The while condition itself (e.g., `total` used in `while total >= target`)
- Subsequent statements in the enclosing loop

---

## 3. Before/After Evidence for Six Sliding-Window Implementations

| Implementation | Before | After | Key change |
|---|---|---|---|
| **2958** (dict freq + while) | ❌ no facts | ✅ `sliding_window` detected | Fix 1: `cross_variable` while comparison |
| **3** (set membership + while) | ❌ no facts | ✅ `sliding_window` detected | Fix 1: `cross_variable` while comparison |
| **424** (Counter + if shrink) | ❌ no var_use | ❌ still not detected | Known limitation: `left` only used in return outside for-loop |
| **209** (accumulator + while) | ❌ misclassified two_pointers | ❌ still two_pointers | Known limitation: absence constraint in strategy evaluator |
| **maxFreq** (Counter + while) | ❌ no var_use | ✅ `sliding_window` detected | Fix 2+3: while-body conditional update + def-use in condition |
| **76/minWindow** (Counter + while missing==0) | ✅ detected | ✅ detected (unchanged) | No regression |

### Detailed Before/After

#### Problem 2958 (dict freq + while)

**Before:**
```
facts: [for_loop_iteration, indexed_write×2, accumulator_update×2, early_termination]
techniques: []
strategies: []
```

**After:**
```
facts: [for_loop_iteration, indexed_write×2, accumulator_update×3, early_termination,
        while_loop_comparison(cross_variable=True), conditional_index_update(branch=while),
        variable_use_in_loop_body]
techniques: [sequential_accumulation, loop_state_tracking]
strategies: [sliding_window]
```

#### Problem 3 (set membership + while)

**Before:**
```
facts: [for_loop_iteration, accumulator_update×2, early_termination]
techniques: []
strategies: []
```

**After:**
```
facts: [for_loop_iteration, accumulator_update×2, early_termination,
        while_loop_comparison(cross_variable=True), conditional_index_update(branch=while),
        variable_use_in_loop_body]
techniques: [sequential_accumulation, loop_state_tracking]
strategies: [sliding_window]
```

#### maxFreq (Counter + while)

**Before:**
```
facts: [for_loop_iteration, conditional_index_update(branch=if), indexed_write×2,
        accumulator_update×2, early_termination, while_loop_comparison]
techniques: [sequential_accumulation]
strategies: []
```

**After:**
```
facts: [for_loop_iteration, conditional_index_update(branch=if, branch=while),
        indexed_write×2, accumulator_update×2, early_termination,
        while_loop_comparison, variable_use_in_loop_body]
techniques: [sequential_accumulation, loop_state_tracking]
strategies: [sliding_window]
```

#### 76/minWindow (no change)

```
Before: strategies: [sliding_window]  →  After: strategies: [sliding_window]
```

---

## 4. Regression Results for Binary Search and Two-Pointers

| Algorithm | Before | After | Status |
|---|---|---|---|
| Binary search | `binary_search` ✅ | `binary_search` ✅ | No regression |
| Two-pointers opposite | `two_pointers_opposite` ✅ | `two_pointers_opposite` ✅ | No regression |
| DP bottom-up | `dp_bottom_up` ✅ | `dp_bottom_up` ✅ | No regression |
| DFS backtracking | `dfs_backtracking` ✅ | `dfs_backtracking` ✅ | No regression |
| BFS level-order | `bfs_shortest_path` ✅ | `bfs_shortest_path` ✅ | No regression |
| Linked-list cycle | `linked_list_traversal` ✅ | `linked_list_traversal` ✅ | No regression |

**No false positives introduced.** The `cross_variable` attribute distinguishes cross-variable while comparisons (sliding-window shrink) from same-variable while comparisons (two-pointers, binary search).

---

## 5. New False Positives

**None.** The changes only add new facts when:
- A while loop has a comparison but the compared and modified variables differ (Fix 1)
- A while loop modifies variables in its body (Fix 2)
- Variables modified in a while body are used in the while condition (Fix 3)

These are all structurally meaningful observations that were previously missing. The `cross_variable` flag provides clean separation from existing same-variable patterns.

---

## 6. Known Limitations (Not Regressions)

| Limitation | Affected | Root cause | Fix scope |
|---|---|---|---|
| **424 if-shrink not detected** | Problem 424 | `left` only used in `return` outside the for-loop; def-use chain checks within loop body only | Would require checking enclosing function's return — out of scope |
| **209 misclassified as two_pointers** | Problem 209 | `total` both compared and modified → same-variable path fires; `left` increments while `total` decrements → `opposite_direction_updates` → sliding_window excluded by absence constraint | Would require strategy evaluator changes — out of scope |

Both limitations are documented in the regression test file as `TestKnownLimitations`.

---

## 7. Test Totals

| Suite | Before | After | Change |
|-------|:------:|:-----:|:------:|
| Backend (pathforge/) | 620 | 620 | 0 |
| Shadow (pathforge/ast_analysis/shadow/) | 360 | 380 | +20 |
| Frontend (vitest) | 32 | 32 | 0 |
| **Total** | **1012** | **1032** | **+20** |

All 1032 tests pass. Zero failures. Zero regressions.

---

## 8. Whether the Fix Should Remain in the Shadow Pipeline

**YES.** The fix should remain.

Justification:
1. **Impact:** Sliding window is one of the highest-value strategies. Detection improved from 1/6 to 4/6 implementations (17% → 67%)
2. **Safety:** All existing tests pass. No false positives introduced. Non-sliding-window algorithms unaffected
3. **Correctness:** The three facts added (`cross_variable` while comparison, while-body `conditional_index_update`, while-body def-use chain) are genuine structural observations that were previously missed
4. **Minimal scope:** Only the shadow fact extractor was modified. No strategy rules, no production code, no architecture changes
5. **Known limitations documented:** The 2 remaining undetected implementations have clear, documented root causes that require separate fixes (def-use chain scope expansion, strategy evaluator absence constraint)
