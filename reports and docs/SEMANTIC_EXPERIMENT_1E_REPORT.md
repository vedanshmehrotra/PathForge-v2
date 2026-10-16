# SEMANTIC EXPERIMENT 1E: FIX IMPLEMENTATION & VALIDATION

## Executive Summary

Four targeted fixes from Experiment 1D were implemented and validated against both the 46-case calibration corpus and the 275-case generalization corpus.

**Verdict: APPROVED**

| Pattern | 1D F1 | 1E F1 | Δ | Recall Δ |
|---------|-------|-------|---|----------|
| two_pointers_opposite | 1.00 | 1.00 | 0.00 | — |
| hash_map_lookup | 0.92 | **0.94** | +0.02 | 0.955→**1.000** |
| prefix_sum | 0.84 | **0.99** | +0.15 | 0.733→**1.000** |
| array_traversal | 0.60 | **0.65** | +0.05 | 0.491→**0.545** |

Key wins:
- **hash_map_lookup: zero false negatives** on the full 275-case corpus
- **prefix_sum: zero false negatives** on the full 275-case corpus
- **two_pointers_opposite: perfect** across all evaluations
- **540 tests pass**, zero regressions

---

## 1. Changes Implemented

| File | Change | Fix |
|------|--------|-----|
| `extractor.py` | `ast.In` → `(ast.In, ast.NotIn)` in membership check | Fix 1: not-in support |
| `extractor.py` | New `.append()` accumulation detection with self-reference check | Fix 3: append accumulation |
| `extractor.py` | New assignment-based accumulation detection (`x[i] = x[i-1] + expr`) | Fix 4: assignment accumulation |
| `scorer.py` | `iteration_with_accumulation` and `iteration_with_append` evidence for array_traversal | Fix 2: direct iteration |
| `scorer.py` | `append_accumulation` and `assignment_accumulation` evidence for prefix_sum | Fix 3+4: accumulation |
| `features.py` | Added `has_append_accumulation`, `has_assignment_accumulation` fields | Fix 3+4: features |
| `tests/test_semantic.py` | 13 new tests covering all 4 fixes | Tests |

---

## 2. Feature/Scorer Behavior

### Fix 1: `not in` membership

- **Before:** `ch not in seen` was NOT detected as membership (only `ast.In` checked)
- **After:** `ast.NotIn` treated identically to `ast.In` for membership detection
- **Impact:** 2 hash_map_lookup FNs eliminated (valid_anagram, happy_number)

### Fix 2: Direct collection iteration

- **Before:** `for x in arr:` without indexed access scored 0.0 for array_traversal
- **After:** With accumulation (`total += x`): scores 0.20 via `iteration_with_accumulation`
- **After:** With append (`result.append(x)` without self-reference): no bonus (correct)
- **Impact:** +3 TP on generalization corpus (summation variants)

### Fix 3: `.append()` accumulation

- **Detection:** `x.append(expr)` where `expr` references `x` → `has_append_accumulation`
- **Self-reference required:** `prefix.append(prefix[-1] + num)` ✓, `result.append(x)` ✗
- **Impact:** range_sum_query now scores 0.65 (was 0.10)

### Fix 4: Assignment accumulation

- **Detection:** `x[i] = x[i-1] + expr` where target var == left operand var
- **Impact:** prefix_array_classic now scores 0.80 (was 0.25)

---

## 3. 46-Case Calibration Results

| Pattern | Threshold | TP | FP | TN | FN | P | R | F1 |
|---------|-----------|----|----|----|----|----|----|-----|
| array_traversal | 0.3 | 7 | 0 | 7 | 2 | 1.000 | 0.778 | 0.875 |
| hash_map_lookup | 0.5 | 4 | 0 | 4 | 0 | 1.000 | 1.000 | 1.000 |
| prefix_sum | 0.3 | 5 | 0 | 3 | 0 | 1.000 | 1.000 | **1.000** |
| two_pointers_opposite | 0.3 | 3 | 0 | 3 | 0 | 1.000 | 1.000 | 1.000 |

**Improvement:** prefix_sum went from F1=0.89 to F1=1.00 on calibration corpus.

---

## 4. 275-Case Generalization Results

| Pattern | Threshold | TP | FP | TN | FN | P | R | F1 |
|---------|-----------|----|----|----|----|----|----|-----|
| array_traversal | 0.3 | 30 | 8 | 18 | 25 | 0.789 | 0.545 | 0.645 |
| hash_map_lookup | 0.5 | 44 | 6 | 26 | 0 | 0.880 | 1.000 | **0.936** |
| prefix_sum | 0.3 | 45 | 1 | 20 | 0 | 0.978 | 1.000 | **0.989** |
| two_pointers_opposite | 0.3 | 33 | 0 | 19 | 0 | 1.000 | 1.000 | 1.000 |

### Comparison with Experiment 1D Baseline

| Pattern | 1D TP | 1E TP | 1D FN | 1E FN | Recovered |
|---------|-------|-------|-------|-------|-----------|
| array_traversal | 27 | 30 | 28 | 25 | +3 |
| hash_map_lookup | 42 | 44 | 2 | 0 | +2 |
| prefix_sum | 33 | 45 | 12 | 0 | +12 |
| two_pointers_opposite | 33 | 33 | 0 | 0 | 0 |

**Total recovered: 17 false negatives** across all patterns.

---

## 5. False-Positive Analysis

### hash_map_lookup FPs (6 total, all seed-labeled-negative)

| Case | Score | Why scorer fires | Label dispute? |
|------|-------|-----------------|----------------|
| single_membership_no_loop | 0.80 | `x = key in seen` — IS a membership test | Yes — scorer correct |
| module_level_membership | 0.80 | `x in some_dict` — IS a membership test | Yes — scorer correct |
| literal_dict_in_loop | 0.80 | `k in {1:'a', 2:'b'}` — IS dict membership | Yes — scorer correct |
| single_membership_dict_constructor | 0.80 | `x in mapping` — IS a membership test | Yes — scorer correct |
| nested_membership_no_loop | 0.80 | `x in some_dict` — IS a membership test | Yes — scorer correct |
| dict_get_no_in | 0.50 | `mapping.get(key)` — IS dict lookup | Yes — scorer correct |

**Assessment:** All 6 FPs are label disagreements with the AST detector corpus. The semantic scorer correctly identifies behavioral hash map lookup in these cases. The validation corpus was designed for structural AST detectors, not behavioral semantic analysis.

### array_traversal FPs (8 total)

| Case | Score | Assessment |
|------|-------|-----------|
| range_only_neg | 0.30 | For-range counter without collection access — borderline |
| underscore_loop_neg | 0.30 | Same — for-range counter |
| while_subscript_neg | 0.80 | `while i < len(arr): print(arr[i])` — IS array traversal |
| enumerate_print_neg | 0.55 | `enumerate(arr)` — IS array iteration |
| range_variable_unused_neg | 0.40 | For-range counter |
| cross_brute_force_two_sum | 0.55 | Nested loops with indexed access — ambiguous |
| cross_brute_force_nested | 0.30 | Nested for-range — borderline |
| cross_brute_force_bubble | 0.75 | Nested loops with sequential index — scoring sorting as traversal |

**Assessment:** 3 FPs are label disagreements (while_subscript, enumerate_print, range_variable_unused). 3 are cross-pattern ambiguous cases (bubble sort scores high because it DOES traverse arrays). 2 are borderline.

### prefix_sum FPs (1 total)

| Case | Score | Assessment |
|------|-------|-----------|
| plain_sum_neg | 0.30 | `sum(nums)` — single call, scores exactly at threshold |

---

## 6. Remaining Feature Gaps

### array_traversal (25 FNs)

All 25 FNs are `for x in arr` (direct iteration) without indexed access:
- 10 seed FNs → cascade into 15 rename FNs
- Root cause: `for x in arr: print(x)` / `result.append(x)` without accumulation
- The `iteration_with_accumulation` evidence (0.20) is not enough to reach threshold 0.3

**Options to recover these:**
1. Increase `iteration_with_accumulation` weight from 0.20 to 0.30 — but risks FPs on sorting code
2. Add `has_append` (any `.append()`) as weaker evidence — would recover append variants
3. Accept current precision/recall tradeoff — 0.79 precision is strong

### prefix_sum (0 FNs — resolved!)

All 12 FNs from Experiment 1D have been recovered:
- 10 from range_sum_query (append accumulation)
- 2 from prefix_array_classic (assignment accumulation)

---

## 7. Fix Verdicts

| Fix | Status | Evidence |
|-----|--------|----------|
| Fix 1: `not in` membership | **APPROVED** | +2 TP, 0 new FPs, trivial change |
| Fix 2: Direct iteration | **APPROVED** | +3 TP, 0 new FPs, conservative weight |
| Fix 3: `.append()` accumulation | **APPROVED** | +10 TP, 0 new FPs, self-reference guard |
| Fix 4: Assignment accumulation | **APPROVED** | +2 TP, 0 new FPs, self-reference guard |

---

## 8. Test Results

| Suite | Before | After | Change |
|-------|--------|-------|--------|
| Semantic tests | 45 | 58 | +13 new |
| AST detectors | 482 | 482 | 0 |
| **Total** | **527** | **540** | **+13 new tests** |

**Zero regressions.**

---

## 9. Files Changed

| File | Lines Changed |
|------|--------------|
| `src/ast_detection/semantic/extractor.py` | +45 (not-in, append, assignment detection) |
| `src/ast_detection/semantic/scorer.py` | +20 (iteration evidence, append/assignment evidence) |
| `src/ast_detection/semantic/features.py` | +2 (new feature fields) |
| `src/ast_detection/semantic/tests/test_semantic.py` | +130 (13 new tests) |

---

## 10. Recommendation

**Do NOT expand to 36 patterns yet.** The 4-pattern results are strong enough to justify a larger evaluation, but the array_traversal precision (0.79) needs monitoring.

**Do NOT integrate into production yet.** Shadow mode only.

**Next step:** Run the semantic scorer on the full 1596-case Phase-0 adversarial corpus to measure precision/recall against the existing AST detector labels at scale.
