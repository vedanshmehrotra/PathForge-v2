# SEMANTIC EXPERIMENT 1C REPORT

## Summary

Three targeted fixes were implemented and validated against the 46-case calibration corpus.

**Verdict: APPROVED**

All three fixes demonstrate measurable improvement with zero precision regressions.

---

## Files Changed

| File | What Changed |
|------|-------------|
| `src/ast_detection/semantic/features.py` | Added `has_for_counter_loop`, `has_enumerate_iteration`, `has_dict_get_lookup`, `membership_collections`, `has_numeric_accumulation`, `accumulator_is_from_collection` |
| `src/ast_detection/semantic/extractor.py` | For-loop counter detection, enumerate support, dict/set construction tracking, `.get()` tracking, numeric accumulation checks, two-pass access feature extraction |
| `src/ast_detection/semantic/scorer.py` | For-loop counter evidence, collection iteration evidence, dict membership scoring, `.get()` lookup scoring, numeric vs non-numeric accumulation |
| `src/ast_detection/semantic/tests/test_semantic.py` | 45 tests (up from 19) covering all three fixes |

---

## Fix 1: For-Loop Counter Detection (array_traversal)

### Problem
- `for i in range(len(arr))` was NOT detected as a counter loop
- `enumerate(arr)` was NOT recognized
- Direct collection iteration (`for x in arr`) had no evidence path

### Solution
- Detect `range()` calls as counter loops (equivalent to while-loop counters)
- Detect `enumerate()` as collection iteration with counter
- Track `has_for_counter_loop` and `has_enumerate_iteration` features
- Direct collection iteration only credited when combined with indexed access

### Result
| Threshold | Before P | Before R | Before F1 | After P | After R | After F1 |
|-----------|----------|----------|-----------|---------|---------|----------|
| 0.3       | 1.00     | 0.44     | 0.62      | 1.00    | 0.78    | 0.88     |

**Recall improved from 44% → 78%** with zero precision loss.

### Remaining FNs (expected limitations)
- `adversarial_class_traversal` (0.00): `for x in arr` in class method — no indexed access
- `adversarial_list_comprehension` (0.00): List comprehension not a regular for loop

### Verdict: APPROVED

---

## Fix 2: Dict/Set Construction Detection (hash_map_lookup)

### Problem
- `freq = {}` with `freq[item] = ...` was NOT tracked as dict
- `word in dict_map` where `dict_map` is a parameter was NOT recognized
- `freq.get(char, 0)` was NOT recognized as a hash lookup
- List membership (`x in list`) was not distinguished from dict membership

### Solution
- Track `dict()`, `{}`, `set()` construction
- Track `x[key] = value` (subscript store) as dict usage
- Track `.get()`, `.items()`, `.keys()` method calls as dict signals
- Two-pass access extraction: first collect membership collections, then infer dicts from subscript reads on those collections
- `.get()` specifically tracked as `has_dict_get_lookup`
- Membership collection type determined from tracked dict/set vars

### Result
| Threshold | Before P | Before R | Before F1 | After P | After R | After F1 |
|-----------|----------|----------|-----------|---------|---------|----------|
| 0.3       | 0.50     | 0.25     | 0.33      | 1.00    | 1.00    | 1.00     |

**Precision improved from 50% → 100%. Recall improved from 25% → 100%.**

### Key improvements
- `hashmap_frequency_count`: `.get()` detection → TP (was FN)
- `hashmap_dict_lookup`: Parameter dict membership → TP (was FN)
- `hashmap_set_membership`: Set construction → TP (was TP, maintained)
- `not_hashmap_list_membership`: List penalty → TN (was TN, maintained)
- `not_hashmap_no_membership`: No membership → TN (was FP, fixed)
- `adversarial_dict_comprehension`: No membership test → TN (was FP, fixed)

### Verdict: APPROVED

---

## Fix 3: Numeric Accumulation Checks (prefix_sum)

### Problem
- `count += 1` (simple counter) was treated as prefix_sum evidence
- `result += word + " "` (string concatenation) was treated as prefix_sum evidence

### Solution
- `_is_numeric_accumulation()`: Reject `+= 1` (simple counter) and `+= "string"` (string literal)
- `_contains_string_literal()`: Detect string constants in binary operations
- Track `accumulator_is_from_collection` for stronger evidence
- Non-numeric accumulation gives zero evidence weight

### Result
| Threshold | Before P | Before R | Before F1 | After P | After R | After F1 |
|-----------|----------|----------|-----------|---------|---------|----------|
| 0.3       | 0.67     | 0.80     | 0.73      | 1.00    | 0.80    | 0.89     |

**Precision improved from 67% → 100%** with same recall.

### Key improvements
- `not_prefixsum_simple_accumulator`: `count += 1` → TN (was FP, fixed)
- `not_prefixsum_string_concat`: String concat → TN (was FP, fixed)
- `prefixsum_running_total`: `total += num` → TP (was TP, maintained)
- `prefixsum_cumulative`: `prefix[i+1] = prefix[i] + arr[i]` → FN (assignment, not augmented assignment — expected limitation)

### Verdict: APPROVED

---

## Two-Pointers (no changes needed)

| Threshold | P | R | F1 |
|-----------|---|---|-----|
| 0.3-0.5   | 1.00 | 1.00 | 1.00 |

Perfect calibration maintained.

---

## Recommended Thresholds

| Pattern | Threshold | Precision | Recall | F1 |
|---------|-----------|-----------|--------|-----|
| array_traversal | 0.3 | 1.00 | 0.78 | 0.88 |
| hash_map_lookup | 0.5 | 1.00 | 1.00 | 1.00 |
| prefix_sum | 0.3 | 1.00 | 0.80 | 0.89 |
| two_pointers_opposite | 0.3 | 1.00 | 1.00 | 1.00 |

---

## Test Results

| Suite | Before | After | Change |
|-------|--------|-------|--------|
| Semantic tests | 19 | 45 | +26 |
| AST detectors | 482 | 482 | 0 |
| **Total** | **501** | **527** | **+26 new tests** |

**Zero regressions.**

---

## Remaining Limitations (not addressed by this experiment)

1. **List comprehensions** not detected as loops → `adversarial_list_comprehension` FN
2. **Class method direct iteration** (`for x in arr`) without indexing → `adversarial_class_traversal` FN
3. **Assignment-based accumulation** (`prefix[i+1] = prefix[i] + arr[i]`) not detected → `prefixsum_cumulative` FN
4. **Function parameter dict tracking** limited — only works when parameter is subscripted AND used in membership test

These are architectural limitations that require broader feature expansion, not fixes within the current scope.

---

## What Should NOT Be Expanded Yet

1. Do NOT expand to all 36 patterns — calibration must be validated on more patterns first
2. Do NOT integrate semantic scores into production — shadow mode only
3. Do NOT tune thresholds against the full 1596-case corpus — this calibration is on 46 cases
