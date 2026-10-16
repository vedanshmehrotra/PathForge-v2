# Sliding Window Detection Failure — Root Cause Analysis

**Date:** 2026-08-28
**Problem studied:** LeetCode 2958 — "Length of Longest Subarray With at Most K Frequency"
**Pipeline traced:** source code → AST → structural facts → techniques → strategies → match outcome

---

## 1. Current Behavior

| System | Result | Confidence |
|--------|--------|-----------|
| Production (legacy) | `sliding_window_variable` detected | ~55% |
| Shadow | `UNRESOLVED` | 0% — no strategy detected |

The shadow pipeline produces **zero** techniques and **zero** strategies for the submitted code. The entire variable sliding-window pattern is invisible to the fact extractor.

---

## 2. Full Execution Trace

### 2.1 Source code (Problem 2958)

```python
def maxSubarrayLength(nums, k):
    freq = {}
    left = 0
    max_len = 0
    for right in range(len(nums)):
        freq[nums[right]] = freq.get(nums[right], 0) + 1
        while freq[nums[right]] > k:        # ← inner shrink loop
            freq[nums[left]] -= 1
            left += 1
        max_len = max(max_len, right - left + 1)
    return max_len
```

### 2.2 Structural facts produced

| fact_id | fact_type | attributes |
|---------|-----------|------------|
| fact_000 | `for_loop_iteration` | `right`, is_range=True |
| fact_001 | `indexed_write` | structure=`freq` |
| fact_002 | `indexed_write` | structure=`freq` |
| fact_003 | `accumulator_update` | variable=`left`, operator=Add |
| fact_004 | `accumulator_update` | variable=`max_len` |
| fact_005 | `early_termination` | return |

**Missing facts (should be present but are not):**

| Expected fact | Why it's missing |
|---------------|-----------------|
| `while_loop_comparison` | Inner while: `while freq[nums[right]] > k` |
| `conditional_index_update` | `left += 1` inside while body |
| `variable_use_in_loop_body` | `right - left + 1` after while loop |

### 2.3 Techniques produced

**None.** Zero techniques detected.

- `loop_state_tracking` requires: `while_loop_comparison` OR `for_loop_iteration` + `conditional_index_update` — neither fires for the while loop.
- `loop_state_tracking` requires a def-use chain where the conditionally-updated variable appears in a later fact's attributes — no such chain exists.

### 2.4 Strategies produced

**None.** Zero strategies detected.

- `sliding_window` (variable path) requires: `loop_state_tracking` technique + `variable_use_in_loop_body` fact — neither present.

### 2.5 Match outcome

`UNRESOLVED` — the shadow evaluator has no strategy evidence to compare against solution groups.

---

## 3. Root Cause

### ROOT CAUSE 1: While-comparison detection requires same-variable overlap

**Location:** `fact_extractor.py:_detect_while_comparison()` (via `_emit_while_comparison_from_compares`)

**The detector computes:**
```python
comp_names = {'k', 'right', 'nums', 'freq'}  # names in the comparison
modified_names = {'left'}                       # variables modified in loop body
intersection = comp_names & modified_names      # EMPTY SET
```

**The rule:** `while_loop_comparison` fires ONLY when `comp_names ∩ modified_names ≠ ∅`.

**The problem:** In variable sliding windows, the while condition compares a *computed expression* (e.g., `freq[nums[right]]`, `right - left + 1`, `total`), while the body modifies a *different variable* (typically `left` or `right`). The intersection is always empty when:
- The compared expression involves a dict/list subscript lookup
- The modified variable is a simple pointer (left/right)

**This is the PRIMARY root cause.** It affects all implementations where the shrink condition uses a dict lookup or compound expression.

### ROOT CAUSE 2: `variable_use_in_loop_body` only checks statements after if-statements in the for-loop body

**Location:** `fact_extractor.py:_detect_variable_use_in_loop_body_for()`

**The detector only finds def-use chains of this form:**
```
for ...
    ... (non-if statement)
    if condition:
        <modify variable>
    <statement using variable>  ← only checked here
```

**It does NOT detect:**
```
for ...
    ... (non-if statements)
    while condition:
        <modify variable>      ← while body not scanned for later use
    <statement using variable> ← this path works, but only if the 
                                 while_loop_comparison fires first
```

For the `maxFreq` case (`while right - left + 1 > minSize:`), `while_loop_comparison` DOES fire (because `left` is in both comp_names and modified_names). But `variable_use_in_loop_body` still fails because the for-loop body has no non-if statement after the while loop that uses `left`.

### ROOT CAUSE 3: `conditional_index_update` is only emitted for `if` statements, not `while` statements

**Location:** `fact_extractor.py:_detect_loop_body_conditional_updates()`

The detector iterates over `node.body` and checks `if isinstance(stmt, ast.If)`. While loops containing conditional pointer updates (like `while cond: left += 1`) are never checked for this fact.

---

## 4. Affected Implementations

Tested 6 sliding-window implementations. Results:

| Implementation | Pattern | while_detected | cond_update | var_use | loop_state | sliding_window |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **2958** (dict freq + while) | `while freq[nums[right]] > k` | ❌ | ❌ | ❌ | ❌ | ❌ |
| **3** (set membership + while) | `while s[right] in char_set` | ❌ | ❌ | ❌ | ❌ | ❌ |
| **424** (Counter + if shrink) | `if ... > k:` | ❌ | ✅ | ❌ | ❌ | ❌ |
| **209** (accumulator + while) | `while total >= target` | ✅ | ❌ | ❌ | ❌ | ❌ |
| **maxFreq** (Counter + while) | `while right-left+1 > minSize` | ✅ | ✅ | ❌ | ❌ | ❌ |
| **76/minWindow** (Counter + while missing==0) | `while missing == 0` | ✅ | ✅ | ✅ | ✅ | ✅ |

**Only 1 out of 6 implementations detected (17%).**

### Why each fails

| Implementation | Failure point | Root cause |
|---|---|---|
| **2958** | While loop invisible | Root cause 1: `freq[nums[right]]` compared, `left` modified — no overlap |
| **3** | While loop invisible | Root cause 1: `s[right] in char_set` — `in` operator names don't overlap with `left` |
| **424** | `var_use` missing | Root cause 2: `left` modified in `if`, but no subsequent non-if statement uses `left` in the for-loop body |
| **209** | Misdetected as `two_pointers_opposite` | Root cause 1 variant: `total` is both compared AND modified → `while_loop_comparison` fires. But `left` is also modified → `opposite_direction_updates` fires → sliding window excluded by absence constraint |
| **maxFreq** | `var_use` missing | Root cause 2: `left` modified inside while body, but `while` is the last statement in for-loop body — no subsequent non-if statement |
| **76/minWindow** | ✅ Works | `missing` is a simple scalar: both compared in while condition and modified in while body. Intersection non-empty. `missing` is also conditionally updated in an outer `if`, and used in the `while` condition — creating a valid def-use chain |

---

## 5. The Three Failure Modes

### Mode A: "Invisible While Loop" (Root cause 1)
**Affects:** 2958, 3, and all dict/set/subscript-based shrink conditions

The inner while loop produces NO `while_loop_comparison` fact because the compared expression names don't overlap with the modified variable names.

**Example:** `while freq[nums[right]] > k: left += 1`
- `comp_names = {'freq', 'nums', 'right', 'k'}`
- `modified = {'left'}`
- `intersection = ∅`

### Mode B: "No Def-Use Chain" (Root cause 2)
**Affects:** 424, maxFreq, and any implementation where the modified variable is used inside the shrink block or after it in the for-loop body

`conditional_index_update` fires (for `if` statements) but `variable_use_in_loop_body` doesn't because the conditionally-updated variable doesn't appear in any subsequent non-if statement within the for-loop body.

**Example:** `if condition: left += 1` (last statement in for-loop body)
- `conditional_index_update` fires ✓
- But no statement after the `if` uses `left`
- `variable_use_in_loop_body` → ✗

### Mode C: "Misclassification as Two-Pointers" (Absence constraint)
**Affects:** 209 and accumulator-based windows where `total` (or similar accumulator) is both compared and modified

When the compared variable IS also the modified variable, `while_loop_comparison` fires correctly. But if another variable (like `left`) is also modified in the same loop body, `opposite_direction_updates` fires (one incremented, one decremented). The sliding-window strategy has an absence constraint: "must NOT have `opposite_direction_updates`" — causing misclassification as `two_pointers_opposite`.

**Example:** `while total >= target: total -= nums[left]; left += 1`
- `while_loop_comparison` ✓ (total compared and modified)
- `opposite_direction_updates` ✓ (left incremented, total decremented)
- `two_pointers_opposite` wins, `sliding_window` excluded

---

## 6. Why Only `minWindow` (76) Works

The `minWindow` implementation happens to satisfy all three fragile conditions simultaneously:

1. **While loop detected:** `while missing == 0` — `missing` is a simple scalar compared in the while condition AND modified in the while body (`missing += 1`). The intersection `{'missing'} ∩ {'missing', ...}` is non-empty.

2. **Def-use chain detected:** The outer `if need[s[right]] > 0: missing -= 1` creates a `conditional_index_update` where `missing` is the updated variable. Then `while missing == 0:` is a non-if statement that uses `missing`. The intersection `{missing} ∩ {missing}` is non-empty.

3. **No misclassification:** `missing` is only incremented, not decremented alongside another variable incrementing — `opposite_direction_updates` doesn't fire because `left` is only incremented (not decremented).

This is a **coincidental** match of the detector's assumptions, not a general detection of the sliding-window pattern.

---

## 7. Evidence of Broader Systematic Problem

The fact extractor's `_detect_while_comparison` was designed primarily for:
- **Two-pointer loops:** `while left < right:` — same variable compared and modified
- **Binary search loops:** `while low <= high:` — same variable compared and modified

It was NOT designed for:
- **Sliding window shrink loops:** `while condition_violated:` where the condition checks a different variable (dict lookup, accumulator, set membership) from the pointer being advanced

This is not a narrow bug — it is a **design gap** in the structural fact extractor's while-loop model. The extractor assumes a "compare-and-modify-the-same-variable" paradigm, which covers two-pointers and binary search but misses the "compare-state, modify-pointer" paradigm used by sliding windows.

---

## 8. Minimal Safe Fix

### Fix 1: Widen while-comparison detection (Root cause 1)

**CURRENT:** `while_loop_comparison` fires only when `comp_names ∩ modified_names ≠ ∅`

**PROPOSED:** Also emit `while_loop_comparison` when the while body contains an `AugAssign` or `Assign` to ANY variable, regardless of whether that variable appears in the comparison. Add a `cross_variable: true` attribute to distinguish this case.

**WHY:** A while loop with a comparison and a modified variable in its body is structurally significant even when the compared and modified variables differ. The cross-variable flag preserves the ability to distinguish same-variable (two-pointer) from cross-variable (sliding-window shrink) patterns.

**FILES:** `pathforge/ast_analysis/shadow/fact_extractor.py:_emit_while_comparison_from_compares()`

**EXPECTED EFFECT:** Implementations 2958, 3, and all subscript-based shrink conditions will now produce `while_loop_comparison`. This enables `conditional_index_update` and `variable_use_in_loop_body` detection for these cases.

### Fix 2: Add `conditional_index_update` for while-loop bodies (Root cause 3)

**CURRENT:** `_detect_loop_body_conditional_updates` only checks `if isinstance(stmt, ast.If)` in the for-loop body.

**PROPOSED:** Also check `while` statements in the for-loop body. When a while loop modifies variables in its body, emit `conditional_index_update` with `branch: "while"`.

**WHY:** The shrink phase of a sliding window is often a while loop, not an if. The "conditional" in "conditional_index_update" means "updated only when the condition holds" — a while loop's condition creates exactly this pattern.

**FILES:** `pathforge/ast_analysis/shadow/fact_extractor.py:_detect_loop_body_conditional_updates()` and `_detect_conditional_index_update_in_for()`

### Fix 3: Check while-loop body for def-use chains (Root cause 2)

**CURRENT:** `_detect_variable_use_in_loop_body` (and its `_for` variant) only checks non-if statements in the for-loop body AFTER the if-statement.

**PROPOSED:** When a while loop is encountered in the for-loop body, check whether variables modified inside the while body are used in the while condition itself or in any subsequent statement. This captures the pattern: `while total >= target: total -= nums[left]` where `total` is both modified and used in the condition.

**FILES:** `pathforge/ast_analysis/shadow/fact_extractor.py:_detect_variable_use_in_loop_body_for()`

### Expected side effects

| Implementation | Before | After Fix 1+2+3 |
|---|---|---|
| 2958 (dict freq) | ❌ | ✅ `while_loop_comparison` (cross_variable) + `conditional_index_update` (while) + `variable_use_in_loop_body` |
| 3 (set membership) | ❌ | ✅ Same pattern as 2958 |
| 424 (if shrink) | ❌ | ✅ `conditional_index_update` (if) + `variable_use_in_loop_body` (while-loop body check or return statement) |
| 209 (accumulator) | ❌ (misclassified as two_pointers) | ✅ Depends on whether absence constraint is refined — may need `opposite_direction_updates` to allow sliding_window when a valid window def-use chain also exists |
| maxFreq (Counter+while) | ❌ | ✅ `while_loop_comparison` + `conditional_index_update` (while) |
| 76/minWindow | ✅ | ✅ No change |

**Regression risk:** Low. The changes only ADD new facts — they don't remove existing ones. The technique detectors and strategy evaluators already handle the new facts correctly. The one risk is `opposite_direction_updates` causing false exclusions (Mode C for 209), but this is handled by the existing sliding-window evaluator only requiring EITHER `loop_state_tracking` OR `fixed_window_maintenance`.

---

## 9. Regression Tests Required

| Test | Purpose |
|------|---------|
| Problem 2958 sliding window detection | Verify `while_loop_comparison` fires with `cross_variable=true` |
| Problem 3 longest substring | Verify set-membership while loop detected |
| Problem 424 replacement chars | Verify if-shrink produces `variable_use_in_loop_body` |
| Problem 76 min window | Verify existing detection is UNCHANGED (regression) |
| Problem 209 min subarray | Verify no longer misclassified as two-pointers when sliding-window evidence is also present |
| maxFreq counter window | Verify while-shrink with Counter detected |
| Two-pointers detection unchanged | Verify `bidirectional_index_scan` still works for genuine two-pointer cases |
| Binary search detection unchanged | Verify midpoint-based detection unaffected |

---

## 10. Should This Fix Be Implemented Now?

**YES.**

Reasons:
1. The failure is **systematic** — affects 83% of sliding-window implementations tested
2. The root causes are **narrow, well-understood** changes to the fact extractor
3. The fixes are **additive** — only add new facts, don't modify existing detection
4. Sliding window is one of the **highest-value strategies** in the research taxonomy
5. Production detection (55% confidence) already works — the shadow pipeline should match or exceed it
6. No architecture changes required — only fact extractor improvements

The fix addresses the #1 most impactful gap in the shadow analysis pipeline's code-analysis capability.

---

## Summary

| Item | Detail |
|------|--------|
| **Root cause** | Fact extractor's while-comparison detector requires compared and modified variables to overlap; sliding windows compare a state expression but modify a pointer |
| **Affected implementations** | 5 out of 6 tested (83%) |
| **Systematic?** | YES — design gap in while-loop model, not a narrow bug |
| **Smallest safe fix** | 3 additive changes to `fact_extractor.py` (while-comparison widening, while-body conditional_index_update, while-body def-use chain) |
| **Regression risk** | Low — additive facts only |
| **Should fix now?** | YES — blocking shadow analysis for the highest-value strategies |
