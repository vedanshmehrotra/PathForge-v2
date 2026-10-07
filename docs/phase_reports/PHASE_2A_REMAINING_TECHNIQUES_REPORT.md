# Phase 2A — Remaining Techniques Implementation Report

**Date:** August 22, 2026
**Status:** COMPLETE — 80 shadow tests + 551 existing tests pass

---

## 1. Structural Facts Added

| Fact Type | Added In | Purpose |
|---|---|---|
| `recursive_call_in_conditional` | `fact_extractor.py` | Self-recursive call inside an if/else branch |
| `multiple_recursive_paths` | `fact_extractor.py` | Function has 2+ self-recursive call sites with different arguments |
| `self_recursive_call` (function context) | `fact_extractor.py` | Self-recursive call anywhere in function body (not just loops) |
| `for_loop_iteration` | `fact_extractor.py` | For-loop with range() or iterable iteration |
| `indexed_write` | `fact_extractor.py` | Subscript assignment: arr[i] = value |
| `index_lookback` | `fact_extractor.py` | Subscript access with lookback: arr[i-1], arr[i-coin] |

**All facts are:**
- Deterministic (same code → same facts)
- Versioned (extractor_version = "1.0.0")
- Traceable (ast_ref with line:col)
- Variable-name independent
- No strategy/algorithm labels

---

## 2. Technique Definitions Implemented

### T4: recursive_branching

**Required facts:**
- `self_recursive_call` — function calls itself
- `recursive_call_in_conditional` OR `multiple_recursive_paths` — recursion across distinct branches

**Does NOT fire for:**
- Linear recursion (one call site, no branching)
- Mutual recursion (A calls B calls A)

**Confidence:** 0.75 (conditional) / 0.85 (multiple paths)
**Centrality:** 0.65 (conditional) / 0.80 (multiple paths)

### T6: loop_state_tracking

**Required facts:**
- `while_loop_comparison` OR `for_loop_iteration` — any loop
- `conditional_index_update` — variable conditionally updated inside loop
- Updated variable appears in another fact's attributes (def-use check)

**Does NOT fire for:**
- Simple counters (`count += 1` inside `if`)
- State that is assigned but never reused
- Unconditional updates

**Confidence:** 0.75
**Centrality:** 0.70

**Known limitation:** For for-loops where the updated variable doesn't appear in other facts (e.g., sliding window with `left` updated but only used in a non-fact expression), `loop_state_tracking` does NOT fire. This is documented in the test suite.

### T7: iterative_table_filling

**Required facts:**
- `while_loop_comparison` OR `for_loop_iteration` — any loop
- `indexed_write` — value written into indexed structure
- `index_lookback` — write depends on earlier entries

**Does NOT fire for:**
- Arbitrary indexed assignment without lookback (`arr[i] = i * 2`)
- Simple sums without indexed writes
- Hash-map operations

**Confidence:** 0.80
**Centrality:** 0.75

---

## 3. Tests Added

| Category | Tests | Status |
|---|---|---|
| Recursive Branching | 9 | ✅ All pass |
| Loop-State Tracking | 6 | ✅ All pass |
| Iterative Table Filling | 9 | ✅ All pass |
| Cross-Pattern Regression | 4 | ✅ All pass |
| **Total new** | **28** | ✅ All pass |
| **Total shadow** | **80** | ✅ All pass |
| **Existing** | **551** | ✅ All pass |

---

## 4. Cross-Pattern False-Positive Analysis

| Check | Result |
|---|---|
| recursive_branching must NOT automatically imply DFS | ✅ No DFS strategy detected |
| recursive_branching must NOT automatically imply DP | ✅ No DP strategy detected |
| loop_state_tracking must NOT automatically imply sliding_window | ✅ No sliding_window strategy detected |
| iterative_table_filling must NOT automatically imply DP | ✅ No DP strategy detected |
| generic accumulation must NOT automatically imply prefix_sum | ✅ No prefix_sum strategy detected |
| indexed mutation must NOT automatically imply table filling | ✅ `arr[i] = i * 2` does NOT fire |

---

## 5. False Negatives

| Case | Expected | Actual | Reason |
|---|---|---|---|
| Sliding window `left` update | loop_state_tracking | NOT detected | `left` doesn't appear in other facts' attributes (for-loop, not while) |
| Generic counter `count += 1` | NOT loop_state_tracking | ✅ Correct | Simple counter, not state tracking |
| State never reused `temp = x * 2` | NOT loop_state_tracking | ✅ Correct | Assigned but never used |

**The sliding window false negative is a known V1 limitation.** The fact vocabulary doesn't capture variable uses in non-fact expressions (like `max(max_len, right - left + 1)`). A future improvement could add `variable_use` facts.

---

## 6. Confidence/Centrality Behavior

| Technique | Confidence | Centrality | Notes |
|---|---|---|---|
| recursive_branching (conditional) | 0.75 | 0.65 | Lower because single conditional branch |
| recursive_branching (multiple paths) | 0.85 | 0.80 | Higher because multiple distinct call signatures |
| loop_state_tracking | 0.75 | 0.70 | Medium — depends on def-use chain quality |
| iterative_table_filling | 0.80 | 0.75 | High — indexed write + lookback is strong signal |

**No arbitrary tuning.** Values are set based on the strength of the structural evidence.

---

## 7. Results for Add Two Numbers

```
Techniques: ['carry_propagation']
Facts: linked_structure_traversal, carry_propagation, node_constructor, ...
No recursive_branching (no recursion)
No iterative_table_filling (no indexed writes)
Outcome: UNRESOLVED (no solution groups)
```

---

## 8. Results for 2996

```
Techniques: ['sequential_accumulation']
Facts: while_loop_comparison, accumulator_update, ...
No recursive_branching (no recursion)
No iterative_table_filling (no indexed writes with lookback)
Outcome: UNRESOLVED (no solution groups)
```

---

## 9. Results for Recursive Cases

| Case | Techniques | Facts |
|---|---|---|
| Fibonacci | recursive_branching | self_recursive_call, multiple_recursive_paths |
| Factorial (linear) | (none) | self_recursive_call (no branching) |
| Tree traversal | recursive_branching | self_recursive_call, multiple_recursive_paths |
| Mutual recursion | (none) | No self_recursive_call (different function names) |

---

## 10. Results for Table-Filling Cases

| Case | Techniques | Facts |
|---|---|---|
| House Robber | iterative_table_filling | indexed_write, index_lookback, for_loop_iteration |
| Fibonacci bottom-up | iterative_table_filling | indexed_write, index_lookback, for_loop_iteration |
| Coin Change | iterative_table_filling | indexed_write, index_lookback, for_loop_iteration |
| Prefix array | iterative_table_filling | indexed_write, index_lookback, for_loop_iteration |
| Arbitrary assignment | (none) | indexed_write (no lookback) |
| Simple sum | (none) | No indexed_write |

---

## 11. Full Test Results

```
80 passed in 0.87s (shadow tests)
551 passed in 1.86s (existing tests)
Total: 631 tests passing
```

---

## 12. Known Limitations

1. **Sliding window `loop_state_tracking`**: For for-loops where the updated variable doesn't appear in other facts' attributes, `loop_state_tracking` does NOT fire. This affects sliding-window-style patterns where `left` is conditionally updated but only used in non-fact expressions.

2. **`index_lookback` with complex expressions**: Only detects simple patterns like `arr[i-1]`, `arr[i+1]`, `arr[i-coin]`. More complex index expressions (e.g., `arr[i // 2]`) are not detected.

3. **No 2D table filling detection**: The current `indexed_write` + `index_lookback` detection works for 1D cases. 2D cases (e.g., `dp[i][j] = ...`) would need additional subscript walk logic.

4. **`recursive_call_in_conditional` only checks direct if/else**: Nested conditionals (if inside if) are not checked. This is acceptable for V1.

---

## 13. Phase 2A Verdict

**APPROVED**

Phase 2A is complete. All three techniques are implemented, tested, and verified:
- `recursive_branching` correctly detects branching recursion and rejects linear/mutual recursion
- `loop_state_tracking` correctly detects conditional state updates in while-loops (with known limitation for for-loops)
- `iterative_table_filling` correctly detects indexed writes with lookback and rejects arbitrary assignment

All 80 shadow tests pass. All 551 existing tests pass. No production behavior changed.

**Ready for Phase 2B** (remaining strategies: binary_search, sliding_window, dfs_backtracking, dp_top_down, dp_bottom_up, bfs_shortest_path, union_find).
