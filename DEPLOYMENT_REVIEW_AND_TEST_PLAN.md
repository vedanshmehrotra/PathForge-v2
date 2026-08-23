# Deployment Review & Manual Testing Plan
## Branch: `architecture/strategy-evidence-spike`

---

## A. Summary of What Changed

### The branch adds ONE commit on top of master:
```
13eaf32 spike:evaluate strategy evidence matching
```

### Production files modified (5 files):

| File | Change | Risk |
|---|---|---|
| `pathforge/api/routes/analyze.py` | +84 lines — adds `shadow_analysis` and `hybrid_analysis` fields to API response; runs shadow analysis in try/except after production path | LOW — all wrapped in try/except, production path untouched |
| `pathforge/services/ground_truth_builder.py` | +591 lines — V1 vocabulary mapping, multi-group generation, structural validation, coherence checks | MEDIUM — modifies how solution groups are built |
| `pathforge/services/problem_resolver.py` | +22 lines — dual-format group loading (legacy `patterns` + new V1 `required/optional/excluded`) | LOW — backward compatible |
| `pathforge/db/schema_pg.sql` | +12 lines — 7 new JSONB columns on `submissions` table (shadow persistence) | LOW — `ADD COLUMN IF NOT EXISTS` is idempotent |
| `pathforge/api/services/shadow_observability.py` | NEW — in-memory counters for shadow analysis monitoring | LOW — observational only |

### New modules added (entirely new code, no existing files deleted):

| Module | Lines | Purpose |
|---|---|---|
| `pathforge/ast_analysis/shadow/fact_extractor.py` | 1488 | Structural fact extraction from AST |
| `pathforge/ast_analysis/shadow/techniques.py` | 503 | 10 technique detectors |
| `pathforge/ast_analysis/shadow/strategies.py` | 644 | 9 strategy evaluators |
| `pathforge/ast_analysis/shadow/matching.py` | 194 | Solution-group satisfaction matching |
| `pathforge/ast_analysis/shadow/shadow_runner.py` | 128 | Orchestrator for shadow path |
| `pathforge/ast_analysis/shadow/data_structures.py` | 68 | Canonical evidence contracts |
| `pathforge/ast_analysis/shadow/persistence.py` | 334 | Shadow evidence serialization/DB persistence |
| `pathforge/ast_analysis/shadow/coherence.py` | 173 | Strategy compatibility metadata |
| `pathforge/ast_analysis/shadow/authority.py` | 208 | Authority upgrade metadata infrastructure |
| `src/ast_detection/semantic/` (8 files) | ~3000 | Earlier hybrid detector experiment (pre-existing in branch history) |

### Test files added (no existing tests modified):

- 336 shadow tests across 8 test files
- 482 existing AST detection tests: UNCHANGED and PASSING

### Key architectural properties verified:

1. **Production path is untouched** — the `analyze_endpoint` function runs the existing analysis first, then shadow analysis in a separate try/except block
2. **Shadow results are ADDITIVE** — they appear as new optional fields (`shadow_analysis`, `hybrid_analysis`) in the response; they don't replace or modify existing fields
3. **Graceful degradation** — if shadow analysis fails (any exception), the response still returns normally with `shadow_analysis: null`
4. **No new dependencies** — `requirements.txt` is unchanged
5. **No frontend changes** — `pathforge-frontend/` is unchanged
6. **No config/env changes** — `.env`, `config.py` unchanged

---

## B. Deployment Risks & Blockers

### Blockers: NONE

The branch can be deployed as an isolated test environment.

### Risks:

| Risk | Severity | Mitigation |
|---|---|---|
| DB schema migration must run before app starts | LOW | `ADD COLUMN IF NOT EXISTS` is safe and idempotent |
| Shadow analysis adds ~1-4ms latency per request | LOW | Wrapped in try/except, doesn't affect production path |
| In-memory observability counters reset on restart | COSMETIC | By design — counters are aggregate metrics only |
| New JSONB columns increase row size slightly | LOW | Shadow data is optional per submission |
| `ground_truth_builder.py` changes affect how NEW ground truth is generated | MEDIUM | See test plan below — must verify existing problems still work |

### Deployment infrastructure requirements:

| Requirement | Needed? | Notes |
|---|---|---|
| Separate Render service | YES | Deploy to a separate Render service to isolate from production |
| Separate PostgreSQL database | YES | New columns must be added via migration |
| Separate env vars | NO | Same env vars work; shadow analysis uses no new external services |
| Separate Vercel deployment | NO | Frontend is unchanged; can share deployment |
| Database migrations | YES | Run `schema_pg.sql` additions (the 7 ALTER TABLE statements) |

---

## C. Manual Testing Plan (Numbered)

### Phase 1: Smoke Tests (Do First)

**Test 1: Basic analysis still works**
- Problem: Any known problem (e.g., "Add Two Numbers")
- Submit any valid Python solution
- **Expected:** Full production analysis returned with `ast`, `match_result`, `verdict`, `verdict_type`, `elo_updates`, `persisted` — all identical to master behavior
- **Monitor:** API response status 200, all existing fields present

**Test 2: Shadow analysis field appears**
- Same submission as Test 1
- **Expected:** `shadow_analysis` field is present in response with:
  - `structural_facts`: list of extracted facts
  - `technique_evidence`: list of detected techniques
  - `strategy_evidence`: list of detected strategies
  - `match_outcome`: `{outcome: "UNRESOLVED" | "CONFIRMED" | "CONTRADICTED", ...}`
  - `extractor_version`: "1.0.0"
  - `elapsed_ms`: ~1-4ms

**Test 3: Production isolation**
- Submit a solution that produces `verdict: "PASS"`
- **Expected:** `shadow_analysis.match_outcome` does NOT change the production `verdict`
- **Monitor:** `verdict`, `verdict_type`, `elo_updates` remain identical to master

### Phase 2: Validation Case Tests

**Test 4: Add Two Numbers — carry_propagation detection**
```python
def addTwoNumbers(l1, l2):
    dummy = ListNode()
    curr = dummy
    carry = 0
    while l1 or l2 or carry:
        val = (l1.val if l1 else 0) + (l2.val if l2 else 0) + carry
        carry, digit = divmod(val, 10)
        curr.next = ListNode(digit)
        curr = curr.next
        l1 = l1.next if l1 else None
        l2 = l2.next if l2 else None
    return dummy.next
```
- **Expected:**
  - `carry_propagation` technique detected ✅
  - NO `linked_list_traversal` technique ✅
  - NO `linked_list_reversal` ✅
  - `two_pointers_opposite` must NOT fire ✅
  - `match_outcome.outcome`: `UNRESOLVED` (no matching solution group)
  - Production verdict: unchanged

**Test 5: Palindrome — two-pointers detection**
```python
def is_palindrome(s):
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True
```
- **Expected:**
  - `bidirectional_index_scan` technique detected ✅
  - `two_pointers_opposite` strategy detected ✅
  - NO `binary_search` ✅
  - `match_outcome.outcome`: `UNRESOLVED` (no matching solution group)

**Test 6: Problem 2996 — unresolved with honest evidence**
```python
def missingInteger(nums):
    i = 1
    summ = nums[0]
    while i <= len(nums)-1 and nums[i] == nums[i-1]+1:
        summ += nums[i]
        i += 1
    while summ in nums:
        summ += 1
    return summ
```
- **Expected:**
  - `sequential_accumulation` technique detected ✅
  - NO `hash_map_lookup` ✅
  - NO `binary_search` ✅
  - NO fake strategy forced ✅
  - `match_outcome.outcome`: `UNRESOLVED` (no V1 strategy represents this solution)

**Test 7: Binary search**
```python
def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
```
- **Expected:**
  - `midpoint_calculation` fact detected ✅
  - `binary_search` strategy detected ✅
  - NO `two_pointers_opposite` ✅

**Test 8: Fixed sliding window**
```python
def max_sum_subarray(nums, k):
    window_sum = sum(nums[:k])
    max_sum = window_sum
    for i in range(k, len(nums)):
        window_sum += nums[i] - nums[i - k]
        max_sum = max(max_sum, window_sum)
    return max_sum
```
- **Expected:**
  - `fixed_window_maintenance` technique detected ✅
  - `sliding_window` strategy detected ✅

**Test 9: Monotonic stack — next greater element**
```python
def next_greater_element(nums):
    n = len(nums)
    result = [-1] * n
    stack = []
    for i in range(n):
        while stack and nums[stack[-1]] < nums[i]:
            idx = stack.pop()
            result[idx] = nums[i]
        stack.append(i)
    return result
```
- **Expected:**
  - `monotonic_stack_maintenance` technique detected ✅
  - `monotonic_stack_strategy` strategy detected ✅

### Phase 3: False Positive / False Negative Tests

**Test 10: Two-pointers MUST NOT be binary search**
- Submit the palindrome code (Test 5)
- **Expected:** `binary_search` strategy NOT present

**Test 11: Two-pointers MUST NOT be sliding window**
- Submit the palindrome code (Test 5)
- **Expected:** `sliding_window` strategy NOT present

**Test 12: Binary search MUST NOT be two-pointers**
- Submit the binary search code (Test 7)
- **Expected:** `two_pointers_opposite` strategy NOT present

**Test 13: Sliding window MUST NOT be two-pointers**
- Submit the fixed window code (Test 8)
- **Expected:** `two_pointers_opposite` strategy NOT present

**Test 14: DFS must NOT be DP without memoization**
```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
```
- **Expected:**
  - `recursive_branching` technique detected
  - NO `dp_top_down` (no cache)
  - NO `dfs_backtracking` (no state restoration)

**Test 15: DFS with state restoration IS backtracking**
```python
def subsets(nums):
    result = []
    def backtrack(start, path):
        result.append(path[:])
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()
    backtrack(0, [])
    return result
```
- **Expected:**
  - `state_restoration` fact detected (append/pop pattern)
  - `dfs_backtracking` strategy detected
  - NO `dp_top_down` ✅

**Test 16: DP with memoization is NOT backtracking**
```python
def fib_memo(n, memo={}):
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    memo[n] = fib_memo(n-1, memo) + fib_memo(n-2, memo)
    return memo[n]
```
- **Expected:**
  - `cache_lookup` and `cache_write` facts detected
  - `dp_top_down` strategy detected
  - NO `dfs_backtracking` ✅

### Phase 4: Variable Renaming Robustness

**Test 17: Renamed two-pointers**
```python
def is_palindrome(s):
    a, b = 0, len(s) - 1
    while a < b:
        if s[a] != s[b]:
            return False
        a += 1
        b -= 1
    return True
```
- **Expected:** `two_pointers_opposite` still detected (structure is the same)

**Test 18: Renamed binary search**
```python
def search(nums, target):
    left_boundary, right_boundary = 0, len(nums) - 1
    while left_boundary <= right_boundary:
        mid_point = (left_boundary + right_boundary) // 2
        if nums[mid_point] == target:
            return mid_point
        elif nums[mid_point] < target:
            left_boundary = mid_point + 1
        else:
            right_boundary = mid_point - 1
    return -1
```
- **Expected:** `binary_search` still detected

**Test 19: Renamed stack variables**
```python
def next_greater(nums):
    result = [-1] * len(nums)
    my_stack = []
    for i in range(len(nums)):
        while my_stack and nums[my_stack[-1]] < nums[i]:
            idx = my_stack.pop()
            result[idx] = nums[i]
        my_stack.append(i)
    return result
```
- **Expected:** `monotonic_stack_strategy` still detected (structure is the same)

### Phase 5: Edge Cases

**Test 20: Empty code / invalid Python**
- Submit: `this is not valid python`
- **Expected:** Production analysis handles error normally; `shadow_analysis` is `null`

**Test 21: Simple solution with no shadow match**
```python
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        if target - num in seen:
            return [seen[target - num], i]
        seen[num] = i
    return []
```
- **Expected:**
  - `match_outcome.outcome`: `UNRESOLVED`
  - No false strategy classification

**Test 22: Very long code**
- Submit a 200+ line solution
- **Expected:** Shadow analysis completes within reasonable time (<50ms), no timeout

### Phase 6: Multiple Solution Approaches

**Test 23: Problem with multiple valid approaches (if solution groups exist)**
- If a problem has multiple solution groups in the DB (e.g., both `two_pointers_opposite` and `binary_search` groups)
- Submit a solution matching group A only
- **Expected:** `match_outcome.outcome` = `CONFIRMED`, `satisfied_group_ids` contains group A

### Phase 7: Regression / Authority Safety

**Test 24: Existing production verdict unchanged**
- Submit a solution to a problem where the production system says `PASS`
- **Expected:** `verdict` = `PASS`, `verdict_type` = same as master, `elo_updates` unchanged

**Test 25: ELO not affected by shadow analysis**
- Submit two different solutions to the same problem
- **Expected:** ELO changes are identical to master; shadow analysis has no effect

**Test 26: Topic profiles unchanged**
- Check user's topic profile after submission
- **Expected:** Topic profile updates are identical to master

**Test 27: Recommendations unchanged**
- Check recommendations after submission
- **Expected:** Recommendations are identical to master

**Test 28: Gaps unchanged**
- Check gap analysis after submission
- **Expected:** Gap analysis is identical to master

### Phase 8: Authority Behavior

**Test 29: Bootstrap/LLM-proposed groups produce UNRESOLVED contradictions**
- If a problem has `llm_proposed` solution groups and the submission doesn't match
- **Expected:** `match_outcome.outcome` = `UNRESOLVED` (NOT `CONTRADICTED`)

**Test 30: Authoritative groups CAN produce CONTRADICTED**
- If a problem has `structurally_observed` or `editorial` solution groups and the submission contradicts
- **Expected:** `match_outcome.outcome` may be `CONTRADICTED` (but this does NOT affect production verdict)

---

## D. Expected Results Summary

| Test | Expected Outcome | Safety Critical? |
|---|---|---|
| 1-3 | Production behavior identical to master | ✅ YES |
| 4 | carry_propagation, no linked_list_traversal | ✅ YES |
| 5 | two_pointers_opposite | ✅ YES |
| 6 | UNRESOLVED, no fake strategy | ✅ YES |
| 7 | binary_search | ✅ YES |
| 8 | sliding_window | ✅ YES |
| 9 | monotonic_stack_strategy | ✅ YES |
| 10-13 | No cross-strategy confusion | ✅ YES |
| 14-16 | DFS vs DP correctly separated | ✅ YES |
| 17-19 | Renaming doesn't break detection | ✅ YES |
| 20-22 | Edge cases handled gracefully | ✅ YES |
| 23 | Multi-group matching works | ✅ YES |
| 24-28 | Production completely isolated | ✅ YES |
| 29-30 | Authority rules correct | ✅ YES |

---

## E. PASS/FAIL Criteria

### PASS if:
1. ✅ All 30 tests produce expected results
2. ✅ Zero production behavior changes (tests 1-3, 24-28)
3. ✅ Zero false authoritative confirmations (no solution falsely marked CONFIRMED)
4. ✅ Zero false contradictions (no solution marked CONTRADICTED when it shouldn't be)
5. ✅ Shadow analysis latency <50ms for any single submission
6. ✅ No crashes or unhandled exceptions in the `/analyze` endpoint
7. ✅ Frontend continues to work normally (new fields are additive, not replacing)
8. ✅ All 482 existing AST detection tests still pass
9. ✅ All 336 shadow tests still pass

### FAIL if:
1. ❌ Any production field (`verdict`, `verdict_type`, `elo_updates`, `topic_profiles`, `gaps`, `recommendations`) changes behavior compared to master
2. ❌ Any solution is falsely CONFIRMED when it shouldn't be
3. ❌ Any solution is falsely CONTRADICTED
4. ❌ Shadow analysis causes a crash or timeout in the `/analyze` endpoint
5. ❌ Database migration fails or corrupts existing data
6. ❌ Frontend breaks or shows incorrect data

### CONDITIONAL PASS (continue experiment):
- If 80%+ of tests pass but some strategy detection is imperfect
- If false negatives are high but false positives are zero
- If latency is higher than expected but <100ms
- These are tuning issues, not architectural blockers

---

## F. Infrastructure Checklist

Before deploying:

- [ ] Create separate Render service (e.g., `pathforge-spike`)
- [ ] Create separate PostgreSQL database (or use same DB with new columns)
- [ ] Run migration: the 7 ALTER TABLE statements from `schema_pg.sql`
- [ ] Verify existing data is unaffected by new columns
- [ ] Deploy backend to separate Render service
- [ ] Frontend can share existing deployment (no changes)
- [ ] Verify API health endpoint works
- [ ] Verify no new env vars needed
- [ ] Set up basic monitoring for shadow analysis latency
