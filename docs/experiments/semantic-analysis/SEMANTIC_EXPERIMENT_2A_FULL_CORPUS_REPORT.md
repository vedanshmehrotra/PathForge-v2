# SEMANTIC EXPERIMENT 2A: FULL CORPUS EVALUATION

## Executive Summary

The semantic scorer was evaluated against the full Phase-0 adversarial corpus (1160 cases for the 4 target patterns: 54 seed cases, 174 adversarial variants, 888 cross-pattern negatives).

**Verdict: MODIFY FEATURES AND RE-RUN**

The semantic scorer does NOT generalize well at PathForge scale for `array_traversal` (P=0.243) due to catastrophic false-positive rates on cross-pattern code. However, it shows genuine strength for `prefix_sum` (F1=0.857, +recall over AST), `hash_map_lookup` (F1=0.800), and `two_pointers_opposite` (F1=0.905, +recall over AST).

The core problem is that `array_traversal` as a semantic concept is indistinguishable from "any code that iterates a collection." The semantic scorer correctly identifies collection iteration behavior, but this behavior is present in sorting, brute force, DFS, BFS, and many other patterns.

---

## 1. Full Corpus Statistics

| Component | Count | Description |
|-----------|-------|-------------|
| Seed positive | 48 | Existing detector-positive cases for 4 patterns |
| Seed negative | 50 | Existing detector-negative cases for 4 patterns |
| Adversarial variants | 174 | Naming, loop-form, expression, class-wrap variants |
| Cross-pattern negatives | 888 | Code from 32 other detectors tested against 4 targets |
| **Total** | **1160** | |

### Pattern Breakdown

| Pattern | Seeds (pos/neg) | Variants | Cross-neg | Total |
|---------|----------------|----------|-----------|-------|
| array_traversal | 15/14 | 48 | 264 | 341 |
| hash_map_lookup | 14/20 | 30 | 275 | 339 |
| prefix_sum | 10/9 | 34 | 212 | 265 |
| two_pointers_opposite | 9/7 | 24 | 233 | 273 |

---

## 2. Per-Pattern Metrics

### array_traversal (threshold=0.3)

| Metric | Semantic | AST Detector | Delta |
|--------|----------|-------------|-------|
| TP | 36 | 42 | -6 |
| FP | 112 | 0 | +112 |
| TN | 124 | 264 | -140 |
| FN | 18 | 12 | +6 |
| **Precision** | **0.243** | **1.000** | **-0.757** |
| **Recall** | **0.667** | **0.778** | **-0.111** |
| **F1** | **0.356** | **0.875** | **-0.519** |

**Verdict: REJECT for array_traversal.** 112 false positives make this unusable.

### hash_map_lookup (threshold=0.5)

| Metric | Semantic | AST Detector | Delta |
|--------|----------|-------------|-------|
| TP | 66 | 64 | +2 |
| FP | 30 | 0 | +30 |
| TN | 212 | 275 | -63 |
| FN | 3 | 5 | -2 |
| **Precision** | **0.688** | **1.000** | **-0.312** |
| **Recall** | **0.957** | **0.928** | **+0.029** |
| **F1** | **0.800** | **0.962** | **-0.162** |

**Verdict: MIXED.** Higher recall (+2 TP recovered) but 30 FPs from cross-pattern code.

### prefix_sum (threshold=0.3)

| Metric | Semantic | AST Detector | Delta |
|--------|----------|-------------|-------|
| TP | 48 | 40 | +8 |
| FP | 14 | 0 | +14 |
| TN | 217 | 225 | -8 |
| FN | 2 | 10 | -8 |
| **Precision** | **0.774** | **1.000** | **-0.226** |
| **Recall** | **0.960** | **0.800** | **+0.160** |
| **F1** | **0.857** | **0.889** | **-0.032** |

**Verdict: PROMISING.** Best recall improvement (+16%) with manageable precision cost.

### two_pointers_opposite (threshold=0.3)

| Metric | Semantic | AST Detector | Delta |
|--------|----------|-------------|-------|
| TP | 43 | 35 | +8 |
| FP | 3 | 0 | +3 |
| TN | 226 | 233 | -7 |
| FN | 6 | 14 | -8 |
| **Precision** | **0.935** | **1.000** | **-0.065** |
| **Recall** | **0.878** | **0.714** | **+0.163** |
| **F1** | **0.905** | **0.833** | **+0.072** |

**Verdict: STRONG.** Best F1 improvement (+0.072) with only 3 FPs.

---

## 3. Recovered False Negatives (semantic catches, AST misses)

| Pattern | Recovered | Example | Why AST misses |
|---------|-----------|---------|----------------|
| hash_map_lookup | 2 | `ch not in seen` (set membership) | AST checks only `in`, not `not in` |
| prefix_sum | 8 | `prefix.append(prefix[-1] + num)` | AST doesn't detect append accumulation |
| two_pointers_opposite | 8 | Various bidirectional patterns | AST misses renamed/increment variants |
| array_traversal | 0 | — | Semantic has fewer TP than AST |

**Total recovered: 18 cases** across 3 patterns.

---

## 4. New False Positives (semantic fires, AST doesn't)

### array_traversal: 112 FPs

| Source | Count | Example | Why semantic fires |
|--------|-------|---------|-------------------|
| cross_pattern (sorting) | ~30 | bubble_sort, merge_sort | Nested loops with indexed access |
| cross_pattern (brute force) | ~25 | brute_force_two_sum | For-range counter + indexed access |
| cross_pattern (DFS/BFS) | ~20 | dfs_recursive, bfs_level_order | Collection iteration + accumulation |
| cross_pattern (DP) | ~15 | dp_1d_forward, dp_2d_grid | Indexed access in loops |
| cross_pattern (other) | ~17 | heap, greedy, backtracking | Various collection operations |
| seed | 5 | range_only, underscore_loop | For-range counter without collection |

**Root cause:** The `for i in range(len(arr))` counter detection fires on ANY for-range loop, and `iteration_with_accumulation` fires on ANY loop with `+=`. These features are too generic.

### hash_map_lookup: 30 FPs

| Source | Count | Example | Why semantic fires |
|--------|-------|---------|-------------------|
| cross_pattern (sliding_window) | 12 | anagram detection | Uses dict for frequency counting |
| cross_pattern (DFS/BFS) | 8 | graph traversal | Uses `visited` set |
| cross_pattern (heap) | 4 | top_k_frequent | Uses dict for frequency |
| cross_pattern (other) | 6 | Various | Uses membership tests |
| seed | 6 | single_membership_no_loop | Membership without loop |

**Root cause:** Many algorithms use dict/set as implementation details. The scorer correctly identifies membership behavior but can't distinguish "primary pattern" from "incidental usage."

### prefix_sum: 14 FPs

| Source | Count | Example | Why semantic fires |
|--------|-------|---------|-------------------|
| cross_pattern | 13 | Various | Numeric accumulation in loops |
| seed | 1 | plain_sum_neg | `sum(nums)` single call |

### two_pointers_opposite: 3 FPs

| Source | Count | Example | Why semantic fires |
|--------|-------|---------|-------------------|
| cross_pattern | 3 | sliding_window, binary_search | Bidirectional movement in loops |

---

## 5. Label Disagreements

Cases where the semantic scorer's behavior is arguably correct but the corpus label says otherwise:

| Pattern | Case | Semantic Score | Corpus Label | Assessment |
|---------|------|---------------|-------------|-----------|
| array_traversal | while_subscript | 0.80 | negative | Scorer correct — IS array traversal |
| array_traversal | enumerate_print | 0.55 | negative | Borderline — IS array iteration |
| hash_map_lookup | single_membership_no_loop | 0.80 | negative | Scorer correct — IS membership test |
| hash_map_lookup | literal_dict_in_loop | 0.80 | negative | Scorer correct — IS dict membership |
| hash_map_lookup | dict_get_no_in | 0.50 | negative | Scorer correct — IS dict lookup |

**Total label disagreements: ~10 cases.** These are NOT scorer errors.

---

## 6. Failure Taxonomy

### array_traversal failures

| Category | Count | Description |
|----------|-------|-------------|
| Cross-pattern FP (sorting) | ~30 | Sorting code iterates arrays |
| Cross-pattern FP (brute force) | ~25 | Nested loops with indexed access |
| Cross-pattern FP (DFS/BFS) | ~20 | Graph algorithms iterate collections |
| Cross-pattern FP (DP) | ~15 | DP uses indexed access |
| Direct iteration FN | 18 | `for x in arr` without indexing |
| Seed FP (range-only) | 5 | For-range without collection access |

### hash_map_lookup failures

| Category | Count | Description |
|----------|-------|-------------|
| Cross-pattern FP (sliding window) | 12 | Frequency counting with dict |
| Cross-pattern FP (DFS/BFS) | 8 | Visited set tracking |
| Cross-pattern FP (heap/other) | 10 | Dict as implementation detail |
| Seed FP (no loop) | 6 | Membership without iteration |
| Seed FN (not-in fixed) | 0 | All resolved by Fix 1 |

### prefix_sum failures

| Category | Count | Description |
|----------|-------|-------------|
| Cross-pattern FP (numeric acc) | 13 | Generic `+=` in loops |
| Seed FN (append fixed) | 0 | All resolved by Fix 3 |
| Seed FN (assignment fixed) | 0 | All resolved by Fix 4 |

### two_pointers_opposite failures

| Category | Count | Description |
|----------|-------|-------------|
| Cross-pattern FP | 3 | Sliding window/binary search |
| Expr variant FN | 6 | Increment changed to `= x + 1` |

---

## 7. Naming Robustness

| Pattern | Naming variants tested | Naming FNs | Naming sensitivity |
|---------|----------------------|------------|-------------------|
| array_traversal | 38 | 18 | 47% (inherited from parent seed failures) |
| hash_map_lookup | 30 | 0 | 0% |
| prefix_sum | 34 | 0 | 0% |
| two_pointers_opposite | 24 | 0 | 0% |

**Finding:** The semantic scorer is fully name-invariant for hash_map_lookup, prefix_sum, and two_pointers_opposite. The 18 array_traversal naming FNs are inherited from parent seeds that already fail (all `for x in arr` cases).

---

## 8. Structural Robustness

| Pattern | Loop variants tested | Loop FNs | Structural sensitivity |
|---------|---------------------|----------|----------------------|
| array_traversal | 2 | 0 | 0% |
| hash_map_lookup | 0 | 0 | N/A |
| prefix_sum | 1 | 0 | 0% |
| two_pointers_opposite | 0 | 0 | N/A |

**Finding:** The for→while conversion variants all pass. The semantic scorer handles loop form changes correctly.

---

## 9. Precision/Recall Trade-offs

### Optimal thresholds at scale

| Pattern | Best F1 Threshold | F1 | Precision | Recall | Notes |
|---------|------------------|-----|-----------|--------|-------|
| array_traversal | 0.5 | 0.375 | 0.270 | 0.611 | Still terrible precision |
| hash_map_lookup | 0.6 | 0.892 | 0.835 | 0.957 | Good at higher threshold |
| prefix_sum | 0.3 | 0.857 | 0.774 | 0.960 | Best balance |
| two_pointers_opposite | 0.3-0.5 | 0.905 | 0.935 | 0.878 | Stable across thresholds |

### Key insight

The `array_traversal` pattern has NO threshold that achieves acceptable precision. The FP scores (0.30-0.85) overlap almost completely with TP scores (0.35-0.90). This is a fundamental conceptual problem, not a threshold tuning problem.

---

## 10. Is the Semantic Layer Better Than Current Detectors?

| Pattern | AST F1 | Semantic F1 | Better? | Why/Why not |
|---------|--------|-------------|---------|-------------|
| array_traversal | 0.875 | 0.356 | **NO** | 112 FPs destroy precision |
| hash_map_lookup | 0.962 | 0.800 | **NO** | 30 FPs from cross-pattern code |
| prefix_sum | 0.889 | 0.857 | **MARGINAL** | +16% recall, -23% precision |
| two_pointers_opposite | 0.833 | 0.905 | **YES** | +16% recall, only 3 FPs |

**Overall:** The semantic layer is NOT a drop-in replacement for the AST detectors. It excels at `two_pointers_opposite` and shows promise for `prefix_sum`, but fails catastrophically for `array_traversal` due to cross-pattern false positives.

---

## 11. Root Cause Analysis

### Why array_traversal fails

The semantic scorer detects "code that iterates a collection." But `array_traversal` in the AST taxonomy means "the primary algorithmic strategy is traversing an array." These are different concepts:

- `for i in range(len(arr)): arr[i] = arr[i] * 2` → array_traversal ✓
- `for i in range(len(arr)): for j in range(i+1, len(arr)): swap(arr, i, j)` → sorting, NOT array_traversal
- `for x in arr: total += x` → could be array_traversal OR prefix_sum OR just accumulation

The semantic scorer cannot distinguish "primary pattern" from "incidental behavior" without understanding the algorithm's purpose.

### Why hash_map_lookup partially fails

Many algorithms use dict/set as implementation details (sliding window frequency counting, DFS visited tracking). The scorer correctly identifies membership behavior but can't distinguish "hash map lookup is the primary pattern" from "hash map is used internally."

### Why prefix_sum works better

Prefix sum has a more distinctive semantic signature: accumulation where the accumulated value depends on prior state AND the source is a collection element. The `.append()` and assignment patterns provide stronger evidence.

### Why two_pointers_opposite works best

Bidirectional pointer movement is a highly distinctive semantic pattern. Very few non-two-pointer algorithms move two variables in opposite directions.

---

## 12. Recommendation

**MODIFY FEATURES AND RE-RUN**

The semantic layer shows genuine value for `two_pointers_opposite` and `prefix_sum`, but needs significant feature refinement before it can complement (not replace) the AST detectors.

### Required changes before re-run:

1. **array_traversal:** Remove or heavily penalize cross-pattern FP features. The for-range counter and iteration+accumulation features are too generic. Consider requiring MULTIPLE evidence signals (counter + indexed access + accumulation) instead of any single signal.

2. **hash_map_lookup:** Add a "primary pattern" gate. Membership on a dict/set should only score high when the dict/set is CONSTRUCTED in the same function, not when it's a parameter or global.

3. **prefix_sum:** The 14 FPs need investigation — likely generic `+=` in loops from cross-pattern code.

4. **two_pointers_opposite:** The 6 FNs are all `expr_increment_variant` (increment changed to `= x + 1`). The pointer feature extractor should detect this pattern.

### What NOT to change:

- The `not in` fix (Fix 1) — working correctly
- The append/assignment accumulation (Fix 3+4) — working correctly
- The name-invariance — working correctly across all patterns

---

## 13. Test Results

| Suite | Tests | Result |
|-------|-------|--------|
| Semantic tests | 58 | 58 passed |
| AST detectors | 482 | 482 passed |
| **Total** | **540** | **540 passed** |

Zero regressions. No production code was modified.
