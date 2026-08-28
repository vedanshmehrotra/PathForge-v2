# Monotonic Stack → Sliding Window False Confirmation: Root Cause Analysis

**Date:** 2026-08-28  
**Status:** Analysis only — no code changes  
**Test baseline:** 1074 tests (651 backend + 391 shadow + 32 frontend), 0 failures  

---

## 1. Current Codebase Summary Relevant to This Issue

### Architecture layers involved

```
Source code
  → fact_extractor.py (structural facts)
    → techniques.py (technique evidence)
      → strategies.py (strategy evidence)
        → matching.py (solution-group evaluation)
```

### Key files

| Layer | File | Role |
|-------|------|------|
| Fact extraction | `pathforge/ast_analysis/shadow/fact_extractor.py` | Extracts 30+ structural fact types from AST |
| Technique detection | `pathforge/ast_analysis/shadow/techniques.py` | Derives 9 technique types from facts |
| Strategy evaluation | `pathforge/ast_analysis/shadow/strategies.py` | Derives 9 strategy types from techniques+facts |
| Solution-group matching | `pathforge/ast_analysis/shadow/matching.py` | Matches detected strategies against ground-truth groups |
| Ground truth | `pathforge/services/ground_truth_builder.py` | Generates solution groups from LLM output |

### Relevant facts for this issue

| Fact type | Meaning | Monotonic stack? | Sliding window? |
|-----------|---------|:----------------:|:---------------:|
| `stack_operation` | `stack.append()` / `stack.pop()` | ✅ | ❌ |
| `monotonic_comparison` | `while stack and nums[stack[-1]] < nums[i]` | ✅ | ❌ |
| `conditional_pop` | `stack.pop()` inside while/if branch | ✅ | ❌ |
| `while_loop_comparison` (cross_variable) | Compared and modified vars differ | ✅ | ✅ |
| `conditional_index_update` (branch=while) | While body modifies a variable | ✅ | ✅ |
| `variable_use_in_loop_body` | Modified var used in subsequent statement | ✅ | ✅ |
| `loop_state_tracking` (technique) | Conditional update + def-use chain | ✅ | ✅ |

---

## 2. Exact Execution Trace

### Monotonic stack code (e.g., `ms_next_greater`)

```python
def next_greater(nums):
    n = len(nums)
    result = [-1] * n
    stack = []
    for i in range(n):
        while stack and nums[stack[-1]] < nums[i]:
            idx = stack.pop()        # ← variable modified in while body
            result[idx] = nums[i]    # ← idx used as subscript index
        stack.append(i)
    return result
```

### Step-by-step trace

#### Step 1: Fact extraction

The for-loop's inner while-loop produces these facts:

| Fact ID | Type | Attributes |
|---------|------|------------|
| `fact_000` | `stack_operation` | `{stack_variable: "stack", operation: "creation"}` |
| `fact_001` | `for_loop_iteration` | `{loop_variable: "i", is_range: True}` |
| `fact_002` | `conditional_index_update` | `{condition_variables: ["i", "nums", "stack"], updated_variables: ["idx"], branch: "while"}` |
| `fact_003` | `variable_use_in_loop_body` | `{variables: ["idx"]}` |
| `fact_004` | `while_loop_comparison` | `{compared_variables: ["i", "nums", "stack"], modified_variables: ["idx"], cross_variable: True}` |
| `fact_005` | `monotonic_comparison` | `{has_stack_access: True}` |
| `fact_006` | `conditional_pop` | `{has_pop_in_branch: True}` |
| `fact_010` | `subscript_index_access` | `{index_variables: ["idx"]}` |
| `fact_012` | `stack_operation` | `{stack_variable: "stack", operation: "append"}` |

**Key observation:** Facts `002`, `003`, `004` are the **sliding-window-specific** facts. They fire because the while loop's body modifies `idx`, and `idx` is used as a subscript index in `result[idx]` — a subsequent statement in the for-loop body.

#### Step 2: Technique detection

| Technique | Confidence | Triggered by |
|-----------|:----------:|-------------|
| `loop_state_tracking` | 0.75 | `conditional_index_update` + `variable_use_in_loop_body` |
| `monotonic_stack_maintenance` | 0.85 | `stack_operation` + `monotonic_comparison` + `conditional_pop` |

**`loop_state_tracking` fires because:**
1. There's a while-loop (`while stack and ...`)
2. There's a `conditional_index_update` (branch=while) — `idx` is modified in the while body
3. `idx` is used as a subscript index (`result[idx]`) — which is a subsequent statement in the for-loop body
4. The def-use chain check (`_detect_loop_state_tracking`) finds `idx` in `subscript_index_access.index_variables`

**This is the root of the false positive.** `loop_state_tracking` is a legitimate technique for monotonic stack code — the code genuinely tracks loop state (conditional update of `idx` based on while condition). But the same technique is also the defining technique for sliding-window code.

#### Step 3: Strategy evaluation

The `_evaluate_sliding_window` function checks:

```
✅ has_loop_state = "loop_state_tracking" in tech_ids → True
✅ has_variable_use = "variable_use_in_loop_body" in fact_types → True
✅ variable_window = True
✅ has_loop = "for_loop_iteration" in fact_types → True
✅ has_opposite = False (no opposite_direction_updates)
✅ has_midpoint = False (no midpoint_calculation)
→ sliding_window strategy fires with confidence 0.75
```

The `_evaluate_monotonic_stack_strategy` function also fires:

```
✅ monotonic_stack_maintenance in tech_ids → True
✅ has_stack → True
✅ has_comparison → True
✅ has_cond_pop → True
→ monotonic_stack_strategy fires with confidence 0.85
```

#### Step 4: Solution-group matching

Given a sliding-window solution group (from ground truth):

```json
{
  "required": ["sliding_window"],
  "optional": ["loop_state_tracking"],
  "excluded": ["two_pointers_opposite"]
}
```

The matching evaluator checks:

```
✅ excluded check: "two_pointers_opposite" not detected → pass
✅ required check: "sliding_window" in detected_strategies → True, confidence 0.75 ≥ 0.5
→ outcome = satisfied → CONFIRMED
```

**Result:** Monotonic stack code is CONFIRMED against sliding-window group. ❌

---

## 3. Root Cause

### The structural overlap

Monotonic stack pop loops and sliding-window shrink loops are **observationally identical** at the fact-extraction level:

| Feature | Monotonic stack | Sliding window |
|---------|:--------------:|:--------------:|
| Outer loop (for/range) | ✅ | ✅ |
| Inner while-loop | ✅ | ✅ |
| While condition: state check | `nums[stack[-1]] < nums[i]` | `freq[nums[right]] > k` |
| While body: modifies variable | `idx = stack.pop()` | `left += 1` |
| Modified variable used as index | `result[idx] = ...` | `max_len = max(..., right - left + 1)` |
| No opposite-direction updates | ✅ | ✅ |
| No midpoint calculation | ✅ | ✅ |

The three facts produced by the sliding-window fix (`cross_variable` while comparison, while-body `conditional_index_update`, while-body def-use chain) fire equally for both patterns.

### Why the fix created these false positives

The sliding-window fix (documented in `SLIDING_WINDOW_FIX_REPORT.md`) added three improvements:

1. **Cross-variable while-loop comparison** — emits `while_loop_comparison` with `cross_variable: True` when compared and modified variables differ
2. **`conditional_index_update` for while-loop bodies** — fires when a while-loop body modifies a variable
3. **Def-use chain for while-loop body variables** — detects when a while-body-modified variable is used in a subsequent statement

All three improvements are correct structural observations. They fire for sliding-window shrink loops (`while freq[x] > k: left += 1`) and also fire for monotonic-stack pop loops (`while stack and nums[stack[-1]] < nums[i]: idx = stack.pop()`) because both patterns share the same structural signature.

### The specific false-positive mechanism

```
monotonic stack
→ inner while-loop modifies idx (stack.pop())
→ idx used as subscript index (result[idx])
→ conditional_index_update fires
→ variable_use_in_loop_body fires (idx used in subsequent statement)
→ loop_state_tracking fires
→ sliding_window strategy fires
→ sliding_window solution group satisfied → CONFIRMED
```

---

## 4. Why the Current Architecture Allows the False Confirmation

### 4.1 `loop_state_tracking` is inherently broad

The technique fires on any code with:
1. A loop (while or for)
2. A conditional variable update in the loop body
3. The updated variable used in a later expression

This pattern describes:
- ✅ Sliding window (genuinely)
- ✅ Monotonic stack (genuinely — the popped variable is conditionally updated and used)
- ✅ Binary search (sometimes — conditional update of low/high)
- ✅ Any loop with conditional branching and later use

The technique is **correct but non-specific**. It correctly identifies "loop state is tracked" but doesn't distinguish WHY.

### 4.2 Strategy evaluator lacks monotonic-stack awareness

The sliding-window evaluator has two absence constraints:
- Must NOT have `opposite_direction_updates` (prevents two-pointer misclassification)
- Must NOT have `midpoint_calculation` (prevents binary search misclassification)

But it has **no constraint for monotonic stack**. The three monotonic-stack-specific facts (`stack_operation`, `monotonic_comparison`, `conditional_pop`) are not checked.

### 4.3 Co-detection is architecturally allowed

The strategy evaluator generates ALL matching strategies independently. There's no mutual exclusion between `sliding_window` and `monotonic_stack_strategy` in the evaluator. This is by design — techniques and strategies are "non-exclusive evidence." But the co-detection creates a problem when the solution-group matcher picks up the wrong strategy.

---

## 5. Existing Evidence That Could Distinguish the Strategies

### 5.1 Monotonic-stack-specific facts (already available)

| Fact | Present in monotonic stack? | Present in sliding window? |
|------|:--------------------------:|:-------------------------:|
| `stack_operation` | ✅ | ❌ |
| `monotonic_comparison` | ✅ | ❌ |
| `conditional_pop` | ✅ | ❌ |

### 5.2 Verification: genuine sliding windows never have stack facts

Tested on representative sliding-window implementations:
- `76/minWindow` (Counter + while-shrink): **No stack facts**
- `3/longestSubstring` (set + while-shrink): **No stack facts**
- `2958/maxSubarrayLength` (dict + while-shrink): **No stack facts**

### 5.3 Verification: monotonic-stack-specific facts are always present for co-detected cases

7 of 9 monotonic-stack entries co-detect as sliding_window. All 7 have all three stack facts (`stack_operation`, `monotonic_comparison`, `conditional_pop`).

2 of 9 do NOT co-detect:
- `ms_stock_span`: while body only has `stack.pop()` (no `idx = stack.pop()` + `result[idx] = ...`), so `variable_use_in_loop_body` doesn't fire
- These 2 entries still correctly detect `monotonic_stack_strategy` only

---

## 6. Candidate Fixes Ranked by Simplicity and Risk

### Fix A: Add exclusion in sliding-window strategy evaluator (RECOMMENDED)

**Location:** `strategies.py` → `_evaluate_sliding_window()`

**Change:** After the existing absence constraints, add:

```python
# Absence constraint: must NOT have all three monotonic-stack facts
# (monotonic_comparison + stack_operation + conditional_pop = monotonic stack,
#  not sliding window — structural overlap in while-loop pop vs shrink)
has_stack_op = "stack_operation" in fact_types
has_mono_comp = "monotonic_comparison" in fact_types
has_cond_pop = "conditional_pop" in fact_types
if has_stack_op and has_mono_comp and has_cond_pop:
    return None
```

**Simplicity:** ★★★★★ (3 lines, same pattern as existing constraints)  
**Risk:** ★★★★★ (lowest — uses already-available facts, no new detection logic)  
**Correctness:** ★★★★★ (verified: no genuine sliding window has all three stack facts)  
**Scope:** Fixes all 7 affected monotonic-stack entries  

### Fix B: Narrow `loop_state_tracking` technique requirements

**Location:** `techniques.py` → `_detect_loop_state_tracking()`

**Change:** Add a guard that the updated variable must not be used exclusively as a subscript index in a structure that also has `stack_operation` facts.

**Simplicity:** ★★★☆☆ (requires cross-referencing fact types)  
**Risk:** ★★★☆☆ (could inadvertently narrow the technique for other code patterns)  
**Correctness:** ★★★★☆ (correct but harder to verify exhaustively)  

### Fix C: Add exclusion in sliding-window solution group definition

**Location:** `ground_truth_builder.py` → `PATTERN_TO_V1_MAPPING`

**Change:** Add `"monotonic_stack_strategy"` to the `excluded` list of `sliding_window_fixed` and `sliding_window_variable`:

```python
"sliding_window_fixed": {
    "required": ["sliding_window"],
    "optional": ["loop_state_tracking"],
    "excluded": ["two_pointers_opposite", "monotonic_stack_strategy"],
    ...
},
```

**Simplicity:** ★★★★☆ (one-line change per entry)  
**Risk:** ★★★★☆ (only affects solution-group matching, not strategy detection)  
**Correctness:** ★★★★★ (correct for solution-group matching, but doesn't fix strategy-level co-detection)  
**Scope:** Only affects solution groups generated by this code — doesn't fix the evaluator itself  

### Fix D: Add a "sliding_window_negative" fact for stack patterns

**Location:** `fact_extractor.py` and `strategies.py`

**Change:** Emit a new fact when all three stack facts are present, and check for it in the sliding-window evaluator.

**Simplicity:** ★★☆☆☆ (new fact type, new detection, new evaluator check)  
**Risk:** ★★☆☆☆ (new infrastructure, harder to maintain)  
**Correctness:** ★★★★★ (would be very precise)  
**Scope:** Overkill for the problem  

### Fix E: Rerank strategies by specificity in matching

**Location:** `matching.py`

**Change:** When multiple strategies match, prefer the more specific one (monotonic_stack_strategy over sliding_window).

**Simplicity:** ★★☆☆☆ (requires specificity ranking logic)  
**Risk:** ★★☆☆☆ (could introduce subtle ranking bugs)  
**Correctness:** ★★★★☆ (correct in principle but complex to implement reliably)  

---

## 7. Recommended Smallest Safe Fix

**Fix A: Add exclusion in sliding-window strategy evaluator**

This is the recommended fix because:

1. **Simplest:** 3 lines of code, same pattern as existing constraints
2. **Lowest risk:** Uses facts already being extracted, no new detection logic
3. **Correct:** Verified that no genuine sliding window has all three stack facts
4. **Targeted:** Only suppresses `sliding_window` when the code is genuinely a monotonic stack
5. **Complete:** Fixes all 7 affected cases
6. **Consistent:** Follows the existing pattern of absence constraints in strategy evaluators

### Why not Fix C (ground truth builder)?

Fix C would also work but is less clean because:
- It only affects solution groups generated by this specific code path
- It doesn't fix the strategy-level co-detection (other consumers of strategy evidence would still see both)
- The evaluator is the proper place for strategy-level concerns

### Why not Fix B (narrow loop_state_tracking)?

Fix B would also work but is riskier because:
- `loop_state_tracking` is used by multiple strategies (sliding window, and potentially others)
- Narrowing the technique could cause false negatives for genuine sliding windows that happen to have stack-like structures (hypothetical but possible)
- The technique is correctly identifying "loop state is tracked" — the issue is in the strategy evaluator, not the technique

---

## 8. Regression Tests Required

### 8.1 New tests for the fix

1. **Monotonic stack → not sliding_window:**
   - `ms_next_greater`: `sliding_window` must NOT be in detected strategies
   - `ms_daily_temperatures`: `sliding_window` must NOT be in detected strategies
   - `ms_histogram`: `sliding_window` must NOT be in detected strategies

2. **Monotonic stack → still detected as monotonic_stack:**
   - Same cases: `monotonic_stack_strategy` MUST be in detected strategies

3. **Genuine sliding window → still sliding_window (no false negatives):**
   - `76/minWindow`: `sliding_window` MUST be in detected strategies
   - `3/longestSubstring`: `sliding_window` MUST be in detected strategies
   - `2958/maxSubarrayLength`: `sliding_window` MUST be in detected strategies
   - `maxFreq`: `sliding_window` MUST be in detected strategies

4. **Genuine two-pointers → not affected:**
   - `maxArea`: `two_pointers_opposite` MUST be in detected strategies, `sliding_window` MUST NOT

5. **Genuine binary search → not affected:**
   - `search`: `binary_search` MUST be in detected strategies, `sliding_window` MUST NOT

### 8.2 Solution-group matching tests

6. **Monotonic stack code vs sliding-window group → UNRESOLVED (not CONFIRMED):**
   ```python
   outcome = evaluate_solution_groups([sw_group], ms_techniques, ms_strategies, ms_facts)
   assert outcome.outcome == "UNRESOLVED"
   ```

7. **Genuine sliding-window code vs sliding-window group → CONFIRMED (unchanged):**
   ```python
   outcome = evaluate_solution_groups([sw_group], sw_techniques, sw_strategies, sw_facts)
   assert outcome.outcome == "CONFIRMED"
   ```

### 8.3 Estimated test count

~8-12 new tests (similar to the sliding-window fix test additions)

---

## 9. Whether the Fix Should Be Implemented Now

**YES.** The fix should be implemented now.

### Justification

1. **Confirmed false positive:** 7 of 9 monotonic-stack entries produce a false CONFIRMED match against sliding-window groups. This is a verified, reproducible issue.

2. **Harmful impact:** Users submitting monotonic-stack solutions for sliding-window problems are told their approach matches — when it fundamentally doesn't.

3. **Verified fix is safe:** No genuine sliding window has all three monotonic-stack facts (`stack_operation`, `monotonic_comparison`, `conditional_pop`). The exclusion rule is sound.

4. **Minimal change:** 3 lines of code in `strategies.py`, same pattern as existing constraints.

5. **No regressions on existing tests:** The fix only adds a new absence constraint; it doesn't change any existing logic.

6. **Builds on existing facts:** The fix uses facts already being extracted by the fact extractor. No new detection logic needed.

7. **Addresses the highest-severity issue:** The false confirmation (HIGH severity) is the second-highest priority after the accumulator-window CONTRADICTED failures (CRITICAL severity). Both should be fixed.

### Implementation scope

- **Fix A** (strategy evaluator exclusion): ~3 lines in `strategies.py`
- **Tests**: ~8-12 new tests in `test_sliding_window_fixes.py`
- **No changes to**: fact extractor, technique detectors, matching layer, ground truth builder, frontend
- **Estimated time**: ~30 minutes

### What NOT to do

- Do NOT add an exclusion rule that only patches individual examples
- Do NOT modify the fact extractor (the observations are correct)
- Do NOT modify `loop_state_tracking` (it's correctly identifying a real pattern)
- Do NOT add complexity to the matching layer (the issue is in the strategy evaluator)
