# LC 209 vs LC 424: Sliding-Window Detection Analysis

## 1. Current Codebase Summary

The shadow analysis pipeline has three layers between source code and strategy detection:

1. **Fact Extractor** (`fact_extractor.py`): Walks the AST and emits `StructuralFact` objects
2. **Technique Detector** (`techniques.py`): Groups structural facts into technique evidence
3. **Strategy Evaluator** (`strategies.py`): Combines techniques + absence constraints → strategy evidence

The sliding-window strategy (`_evaluate_sliding_window`) requires:
- **Variable window path**: `loop_state_tracking` technique + `variable_use_in_loop_body` fact
- **Fixed window path**: `fixed_window_maintenance` technique + `window_size_constant` fact
- Plus: a loop (while/for)
- **Absence constraints**: no `opposite_direction_updates`, no `midpoint_calculation`, no monotonic-stack trio

## 2. Exact Execution Trace for LC 209

### Source structure
```
for right in range(len(nums)):       # outer for-loop
    total += nums[right]             # expand accumulator
    while total >= target:           # shrink while-loop
        min_len = min(min_len, right - left + 1)
        total -= nums[left]          # <-- NAME decrement of accumulator
        left += 1                    # <-- NAME increment of pointer
```

### Facts extracted
| Fact Type | Attributes | Source |
|-----------|-----------|--------|
| `for_loop_iteration` | loop_variable=right | for-loop |
| `accumulator_update` | variable=total, op=Add | `total += nums[right]` |
| `while_loop_comparison` | compared=[target, total], modified=[total] | `while total >= target` |
| `conditional_index_update` | condition=[target, total], updated=[left, min_len, total], branch=while | nested while |
| `variable_use_in_loop_body` | variables=[total] | total used in while condition |
| `accumulator_update` | variable=total, op=Sub | `total -= nums[left]` |
| `accumulator_update` | variable=left, op=Add | `left += 1` |
| **`opposite_direction_updates`** | **incremented=[left], decremented=[total]** | while body has both += and -= on Names |

### Techniques detected
- `sequential_accumulation` ✓ (while-loop + accumulator)
- `loop_state_tracking` ✓ (conditional update + def-use chain)

### Strategy evaluation
- `sliding_window`: **BLOCKED** by `opposite_direction_updates` absence constraint ← THE BUG
- No other strategy fires

### Why `opposite_direction_updates` fires
`_detect_opposite_updates_in_loop` calls `_collect_body_augmented_directions` on the while-loop body. The body has:
- `total -= nums[left]` → AugAssign(Name(total), Sub) → `decremented: total`
- `left += 1` → AugAssign(Name(left), Add) → `incremented: left`

Both targets are simple `Name` nodes, so both are collected. Since one is `inc` and one is `dec`, the fact fires.

## 3. Exact Execution Trace for LC 424

### Source structure
```
for right in range(len(s)):                      # outer for-loop
    count[s[right]] = count.get(s[right], 0) + 1 # expand
    max_freq = max(max_freq, count[s[right]])     # update state
    while (right - left + 1) - max_freq > k:     # shrink while-loop
        count[s[left]] -= 1                       # <-- SUBSCRIPT decrement
        left += 1                                 # <-- NAME increment
```

### Facts extracted
| Fact Type | Attributes | Source |
|-----------|-----------|--------|
| `for_loop_iteration` | loop_variable=right | for-loop |
| `conditional_index_update` | condition=[k, left, max_freq, right], updated=[left], branch=while | nested while |
| `variable_use_in_loop_body` | variables=[left] | left used in result expr |
| `indexed_write` | structure=count | `count[s[left]] -= 1` |
| `accumulator_update` | variable=left, op=Add | `left += 1` |
| `while_loop_comparison` | compared=[k, left, max_freq, right], modified=[left] | while condition |
| **NO `opposite_direction_updates`** | | `count[s[left]] -= 1` target is Subscript, not Name |

### Techniques detected
- `sequential_accumulation` ✓
- `loop_state_tracking` ✓

### Strategy evaluation
- `sliding_window`: **FIRES** ✓ (no absence constraint violated)

## 4. Root Cause: Why the Difference Exists

### The exact mechanism

The `opposite_direction_updates` fact is emitted by `_detect_opposite_updates_in_loop`, which calls `_collect_body_augmented_directions(body)`. This method walks the while-loop body and collects `AugAssign` nodes where the target is a **bare `Name`**.

| Statement | AST Target | Collected? |
|-----------|-----------|-----------|
| `total -= nums[left]` (LC 209) | `Name(id='total')` | **Yes** → `dec: total` |
| `left += 1` (both) | `Name(id='left')` | **Yes** → `inc: left` |
| `count[s[left]] -= 1` (LC 424) | `Subscript(value=Name('count'), slice=...)` | **No** — not a bare Name |

LC 209's while body has **two** bare-Name AugAssign targets (`total` and `left`) in opposite directions → fact fires → sliding_window blocked.

LC 424's while body has only **one** bare-Name AugAssign target (`left`); the decrement targets a dict subscript → no opposite directions → sliding_window allowed.

### The architectural flaw

The `opposite_direction_updates` absence constraint in `_evaluate_sliding_window` was designed to exclude **genuine two-pointer** loops (where both `left` and `right` are compared and both are modified). But it is a **flat fact-type check** — it doesn't consider *which loop* the fact came from or *what variables* are being compared.

In a sliding-window shrink loop:
- `left += 1` (pointer advance) — a bare Name
- `total -= nums[left]` (accumulator reduction) — also a bare Name

The fact extractor correctly observes these are "two variables updated in opposite directions." But the semantic meaning is entirely different from two-pointers: one is a pointer, the other is an accumulator state variable.

## 5. Existing Evidence That Could Distinguish the Strategies

The `while_loop_comparison` fact already carries both `compared_variables` and `modified_variables`:

| Case | `compared_variables` | `modified_variables` | `compared ⊆ modified`? |
|------|---------------------|---------------------|----------------------|
| Two-pointers (palindrome) | [left, right] | [left, right] | **True** ← both compared vars modified |
| Two-pointers (sortedSq) | [left, right] | [left, right] | **True** |
| Sliding window 209 | [target, total] | [total] | **False** ← `target` not modified |
| Sliding window 424 | [k, left, max_freq, right] | [left] | **False** |
| Sliding window 3 | [char_set, right, s] | [left] | **False** |
| Binary search | [left, right] | [left, right] | **True** |
| Monotonic stack | [i, nums, stack] | [idx] | **False** |

**Key insight**: In genuine two-pointer loops, **both compared variables appear in `modified_variables`** because both pointers are updated by the loop. In sliding-window shrink loops, **only one compared variable** (the state expression) appears in `modified_variables`; the other updates (`left`) involve variables not in the while condition.

## 6. Candidate Fixes (Ranked)

### Fix A: Refine the `opposite_direction_updates` exclusion (RECOMMENDED)

**Change**: In `_evaluate_sliding_window()`, replace the blanket `if has_opposite: return None` with a check that only blocks when the while-loop comparison involves variables that are ALL modified.

```python
if 'opposite_direction_updates' in fact_types:
    # Check whether the opposite updates are in a genuine two-pointer loop
    # (both compared variables are modified) vs a sliding-window shrink
    # (only one compared variable is modified, the other is a pointer update
    # on a variable not in the comparison).
    has_genuine_opposite = False
    for wc in [f for f in facts if f.fact_type == 'while_loop_comparison']:
        compared = set(wc.attributes.get('compared_variables', []))
        modified = set(wc.attributes.get('modified_variables', []))
        if compared and compared <= modified:
            has_genuine_opposite = True
    if has_genuine_opposite:
        return None
```

**Pros**: 
- 6 lines of code
- Uses existing `while_loop_comparison` fact (no new facts needed)
- Correctly distinguishes the structural difference
- Verified: all 7 test cases pass (LC 209 fixed, two-pointers/binary-search/monotonic-stack unaffected)

**Cons**:
- Depends on `while_loop_comparison` being accurate (it is — already verified)
- If `modified_variables` captures non-intentional modifications, could cause false negatives (unlikely given current detection)

### Fix B: Add a `shrink_loop_accumulator_decrement` fact

Add a new fact type that specifically identifies when a while-loop body decrements an accumulator variable while incrementing a pointer. This would be more precise but requires fact extractor changes.

**Pros**: Very precise
**Cons**: More invasive, requires new fact type + extractor changes

### Fix C: Add `pointer_update_in_shrink_loop` fact

Detect when a while-loop body has only a pointer increment (no accumulator decrement), which is the "clean" sliding-window shrink pattern.

**Pros**: Captures the ideal pattern
**Cons**: Would miss LC 209-style solutions (which are valid sliding windows)

### Fix D: Modify `_collect_body_augmented_directions` to exclude subscript targets

Change the fact extractor to not count `count[s[left]] -= 1` type decrements. This would prevent the `opposite_direction_updates` from firing in more cases.

**Pros**: More correct fact extraction
**Cons**: Would need careful analysis of all callers; might break other fact types

## 7. Recommended Smallest Safe Fix

**Fix A** is the smallest, safest fix:
- Changes only `_evaluate_sliding_window()` in `strategies.py`
- No changes to fact extraction
- No changes to technique detection
- No new fact types
- Uses existing `while_loop_comparison` attributes that are already verified accurate

**Exact change**: Replace lines in `_evaluate_sliding_window()`:
```python
# BEFORE:
has_opposite = "opposite_direction_updates" in fact_types
if has_opposite:
    return None

# AFTER:
has_opposite = "opposite_direction_updates" in fact_types
if has_opposite:
    # Refine: only block if the while-loop comparison involves variables
    # that are ALL modified (genuine two-pointers). In sliding-window shrink
    # loops, the compared state expression includes non-modified variables
    # (constants, thresholds) while only the pointer is updated.
    has_genuine_opposite = False
    for wc in [f for f in facts if f.fact_type == 'while_loop_comparison']:
        compared = set(wc.attributes.get('compared_variables', []))
        modified = set(wc.attributes.get('modified_variables', []))
        if compared and compared <= modified:
            has_genuine_opposite = True
    if has_genuine_opposite:
        return None
```

## 8. Regression Test Matrix

| Test Case | Before | After | Correct? |
|-----------|--------|-------|----------|
| LC 209 (shrink with `total -= nums[left]`) | UNRESOLVED | SLIDING_WINDOW | ✓ Fixed |
| LC 209 modulo-style (same pattern) | UNRESOLVED | SLIDING_WINDOW | ✓ Fixed |
| LC 424 (shrink with dict decrement) | SLIDING_WINDOW | SLIDING_WINDOW | ✓ No change |
| LC 3 (shrink with set.remove) | SLIDING_WINDOW | SLIDING_WINDOW | ✓ No change |
| LC 76 (Minimum Window Substring) | SLIDING_WINDOW | SLIDING_WINDOW | ✓ No change |
| LC 2958 (maxSubarrayLength) | SLIDING_WINDOW | SLIDING_WINDOW | ✓ No change |
| Two-pointer palindrome | TWO_POINTERS | TWO_POINTERS | ✓ No change |
| Two-pointer sortedSquares | TWO_POINTERS | TWO_POINTERS | ✓ No change |
| Binary search | BINARY_SEARCH | BINARY_SEARCH | ✓ No change |
| Monotonic stack | MONOTONIC_STACK | MONOTONIC_STACK | ✓ No change |
| Fixed-window 643 | SLIDING_WINDOW | SLIDING_WINDOW | ✓ No change |

## 9. LC 438 Analysis

LC 438 (Find All Anagrams) is a **fixed-size** sliding window. It has two common implementations:

**If-variant** (LC 438):
```python
if right - left + 1 > len(p):
    s_count[s[left]] -= 1
    left += 1
```
- The `if`-based shrink doesn't produce `while_loop_comparison` or `variable_use_in_loop_body`
- `loop_state_tracking` fires (via def-use on `left` through `subscript_index_access`)
- But `sliding_window` strategy doesn't fire because `variable_use_in_loop_body` is missing
- This is a **separate issue**: the `variable_use_in_loop_body` detector only runs on While/For nodes, not If nodes

**While-variant** (deployed code):
```python
while right - left + 1 > len(p):
    s_count[s[left]] -= 1
    left += 1
```
- Produces `while_loop_comparison`, `variable_use_in_loop_body`, `conditional_index_update`
- `loop_state_tracking` fires ✓
- `sliding_window` fires ✓
- No `opposite_direction_updates` (dict subscript decrement)

**Verdict**: LC 438 is the **same family** of issue as LC 209 — it's a sliding window that should be detected. The if-variant has a separate extraction gap (`variable_use_in_loop_body` doesn't fire on If-statement shrink phases), but this is a different bug from the `opposite_direction_updates` blocker. The while-variant works correctly.

## 10. Summary

| Question | Answer |
|----------|--------|
| **Exact reason 209 fails** | Shrink while-loop body has `total -= nums[left]` (Name target) + `left += 1` (Name target) → `opposite_direction_updates` fires → blanket absence constraint blocks `sliding_window` |
| **Why 424 succeeds** | Shrink while-loop body has `count[s[left]] -= 1` (Subscript target, NOT a Name) → only one bare-Name AugAssign → no `opposite_direction_updates` |
| **Should they use the same strategy?** | **Yes.** Both are variable-size sliding windows with `for right` + `while shrink` + pointer advance. The structural distinction (`compared ⊆ modified`) correctly separates them from two-pointers |
| **Is 438 the same family?** | **Partially.** The while-variant works correctly. The if-variant has a separate extraction gap where `variable_use_in_loop_body` doesn't fire on If-statement shrink phases |
| **Smallest safe fix** | Refine the `opposite_direction_updates` exclusion in `_evaluate_sliding_window()` to only block when all compared variables are also modified (genuine two-pointer pattern). ~6 lines, no fact extractor changes. |
