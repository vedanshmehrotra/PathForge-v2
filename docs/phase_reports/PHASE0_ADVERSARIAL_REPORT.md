# PATHFORGE PHASE-0 ADVERSARIAL EVALUATION REPORT

**Date:** August 19, 2026
**Scope:** AST detector accuracy, naming/structural sensitivity, ground-truth quality, taxonomy consistency
**Corpus:** 571 seed cases + 1025 adversarial variants = 1596 total test cases
**Method:** Programmatic variant generation from existing test seeds, run through production AST engine

---

## 1. EXECUTIVE FINDINGS

### What We Measured

| Metric | Value |
|--------|-------|
| Total test cases | 1596 |
| Seed cases (from existing tests) | 571 |
| Adversarial variants (generated) | 1025 |
| Overall precision | **99.8%** (1040 TP, 2 FP) |
| Overall recall | **80.3%** (1040 TP, 255 FN) |
| Overall F1 | **89.0%** |
| True negatives | 299 |
| False positives | 2 |
| False negatives | 255 |

### The Three Most Important Numbers

1. **80.3% recall under adversarial conditions.** The AST engine correctly detects patterns 80.3% of the time when variants include renamed variables, different loop forms, and equivalent expressions. This is significantly worse than the 93.9% recall measured on the original 17-detector validation suite (which used hand-crafted, name-optimized test cases).

2. **138 of 255 false negatives (54.1%) are caused by variable naming.** The AST engine's single largest weakness is dependence on specific variable names. Renaming `queue` to `q`, `visited` to `seen`, or `dp` to `table` causes detectors to fail.

3. **16.0% of problems have a single-group false-negative floor.** 48 of 300 problems in the CSV have multiple alternative approaches that are collapsed into one AND-group. Any user who solves with one valid approach gets PARTIAL_MATCH.

### Executive Conclusion

The AST engine is **precise but not robust.** It almost never produces false positives (99.8% precision), but it misses 19.7% of detections under realistic code variations. The weaknesses are concentrated in a small number of detectors and are caused by predictable, fixable issues (naming dependence, expression sensitivity, AST shape dependence). The ground-truth system has a structural flaw (single-group collapsing) that causes systematic false negatives for 16% of problems.

---

## 2. DETECTOR-BY-DETECTOR METRICS

### Ranked by Recall (Lowest = Highest Risk)

| Detector | Precision | Recall | F1 | Naming Sensitivity | Structural Sensitivity | Failure Causes |
|----------|-----------|--------|----|--------------------|----------------------|----------------|
| bfs_shortest_path | 100.0% | **23.5%** | 38.1% | 83.3% | 0.0% | naming:10, reasoning:2, expression:1 |
| dp_knapsack | 100.0% | **29.4%** | 45.5% | 71.4% | 0.0% | naming:10, reasoning:2 |
| binary_search_answer | 100.0% | **46.0%** | 63.0% | 0.0% | 0.0% | expression:18, reasoning:2 |
| dp_1d_sequence | 100.0% | **47.1%** | 64.0% | 57.1% | 0.0% | naming:8, reasoning:1 |
| binary_search_rotated | 100.0% | **47.6%** | 64.5% | 50.0% | 0.0% | naming:6, expression:4, reasoning:1 |
| dp_1d_forward | 100.0% | **48.7%** | 65.5% | 56.2% | 0.0% | naming:10, expression:4, reasoning:1 |
| backtracking_permutation | 100.0% | **61.5%** | 76.2% | 40.0% | 0.0% | naming:4, reasoning:2 |
| two_pointers_same | 100.0% | **62.9%** | 77.2% | 31.8% | 100.0% | naming:7, reasoning:1 |
| greedy_interval | 100.0% | **64.3%** | 78.3% | 50.0% | 0.0% | naming:2, reasoning:2 |
| linked_list_reversal | 100.0% | **66.7%** | 80.0% | 42.9% | 0.0% | naming:3, reasoning:1 |
| two_pointers_opposite | 100.0% | **71.4%** | 83.3% | 0.0% | 0.0% | reasoning:4 |
| fast_slow_pointers | 100.0% | **72.4%** | 84.0% | 34.8% | 0.0% | naming:8, reasoning:1 |
| sliding_window_fixed | 100.0% | **75.0%** | 85.7% | 25.0% | 0.0% | naming:1, reasoning:1 |
| binary_search_tree | 100.0% | **76.1%** | 86.4% | 25.0% | 0.0% | naming:2, reasoning:1 |
| array_traversal | 100.0% | **77.8%** | 87.5% | 0.0% | 100.0% | reasoning:6, shape:6 |
| dp_2d_grid | 100.0% | **77.8%** | 87.5% | 25.0% | 0.0% | naming:2, reasoning:1 |
| dp_2d_string | 100.0% | **77.8%** | 87.5% | 25.0% | 0.0% | naming:2, reasoning:1 |
| prefix_sum | 100.0% | **80.0%** | 88.9% | 6.2% | 100.0% | naming:1, reasoning:1, shape:5, expression:2 |
| monotonic_stack | 100.0% | **81.6%** | 89.9% | 7.7% | 100.0% | reasoning:3, shape:2 |
| binary_search_standard | 100.0% | **86.9%** | 93.0% | 10.5% | 0.0% | naming:2, reasoning:1 |
| hash_map_frequency | 100.0% | **88.9%** | 94.1% | 0.0% | 42.9% | reasoning:3, shape:3 |
| sliding_window_variable | 100.0% | **90.3%** | 94.9% | 0.0% | 0.0% | reasoning:3 |
| hash_map_lookup | 100.0% | **92.8%** | 96.2% | 0.0% | 100.0% | reasoning:4, shape:2 |
| monotonic_deque | 100.0% | **93.5%** | 96.7% | 0.0% | 100.0% | reasoning:2 |
| heap_top_k | 100.0% | **93.9%** | 96.9% | 0.0% | 33.3% | reasoning:4, shape:1 |
| dfs_recursive | 100.0% | **95.9%** | 97.9% | 5.6% | 0.0% | reasoning:2 |
| backtracking_subset | 100.0% | **100.0%** | 100.0% | 0.0% | 0.0% | — |
| bfs_level_order | 100.0% | **100.0%** | 100.0% | 0.0% | 0.0% | — |
| brute_force | 98.5% | **100.0%** | 99.3% | 0.0% | 0.0% | — |
| dfs_iterative | 100.0% | **100.0%** | 100.0% | 0.0% | 0.0% | — |
| dp_interval | 100.0% | **100.0%** | 100.0% | 0.0% | 0.0% | — |
| dp_state_machine | 100.0% | **100.0%** | 100.0% | 0.0% | 0.0% | — |
| greedy_local | 100.0% | **100.0%** | 100.0% | 0.0% | 0.0% | — |
| sorting | 96.8% | **100.0%** | 98.4% | 0.0% | 0.0% | — |
| topological_sort | 100.0% | **100.0%** | 100.0% | 0.0% | 0.0% | — |
| union_find | 100.0% | **100.0%** | 100.0% | 0.0% | 0.0% | — |

---

## 3. FALSE-NEGATIVE TAXONOMY

### Failure Cause Distribution

| Cause | Count | % of FN | Description |
|-------|-------|---------|-------------|
| naming_dependence | 138 | 54.1% | Detector requires specific variable names |
| expression_dependence | 59 | 23.1% | Detector requires specific comparison/midpoint expressions |
| ast_shape_dependence | 34 | 13.3% | Detector requires specific loop/control-flow structure |
| insufficient_structural_reasoning | 24 | 9.4% | Detector lacks ability to reason about semantic equivalence |

### Naming Dependence (138 failures)

**Root cause:** Detectors check for specific variable names as evidence signals. When variables are renamed, the evidence is not found and detection fails.

**Affected detectors (by failure count):**
- `dp_1d_forward`: 10 failures (checks for `dp` variable name)
- `dp_knapsack`: 10 failures (checks for `dp` variable name)
- `bfs_shortest_path`: 10 failures (checks for `queue`, `visited`, `node`, `dist`)
- `dp_1d_sequence`: 8 failures (checks for `dp` variable name)
- `fast_slow_pointers`: 8 failures (checks for `slow`, `fast` variable names)
- `binary_search_rotated`: 6 failures (checks for `left`, `right` variable names)

**Example:** `bfs_shortest_path` detector checks for evidence type `queue_traversal` which requires finding a `deque` import AND a variable named `queue`. Renaming `queue` to `q` eliminates the evidence.

### Expression Dependence (59 failures)

**Root cause:** Detectors check for specific expression patterns (midpoint calculations, comparison operators) that have multiple valid syntactic forms.

**Affected detectors:**
- `binary_search_answer`: 18 failures (requires `is_feasible(mid)` function call pattern; fails when feasibility check is inline)
- `binary_search_rotated`: 4 failures (requires specific midpoint expression `(left + right) // 2`; fails with `left + (right - left) // 2`)
- `dp_1d_forward`: 4 failures (requires specific recurrence expression patterns)
- `prefix_sum`: 2 failures (requires specific accumulation patterns)

**Example:** `binary_search_answer` requires a function call like `is_feasible(mid)` or `check(mid)`. When the feasibility check is written inline (`if arr[mid] < target`), the detector cannot recognize it.

### AST-Shape Dependence (34 failures)

**Root cause:** Detectors require specific control-flow structures (for-loop vs while-loop, specific nesting patterns).

**Affected detectors:**
- `array_traversal`: 6 failures (requires `for i in range(len(arr))` pattern; fails with while-loop equivalent)
- `prefix_sum`: 5 failures (requires specific loop structure for prefix accumulation)
- `monotonic_stack`: 2 failures (requires specific while-loop-within-for-loop structure)
- `hash_map_lookup`: 2 failures (requires specific loop structure)
- `monotonic_deque`: 1 failure

**Example:** `array_traversal` requires a `for` loop with `range(len(...))`. The equivalent `while` loop with manual index increment is not recognized.

### Insufficient Structural Reasoning (24 failures)

**Root cause:** The detector's heuristic does not capture the semantic essence of the pattern. The code implements the algorithm correctly but the detector's structural check is too narrow.

**Affected detectors:**
- `array_traversal`: 6 failures
- `bfs_shortest_path`: 2 failures
- `dp_knapsack`: 2 failures
- `binary_search_answer`: 2 failures
- `greedy_interval`: 2 failures
- Various others: 1-2 failures each

---

## 4. FALSE-POSITIVE TAXONOMY

### Total False Positives: 2

| Detector | Case | Description |
|----------|------|-------------|
| brute_force | test_not_detected_reversed | `list(reversed(arr))` triggered brute_force (nested function call detected as recursive branching) |
| sorting | (from unit tests) | Edge case where `sorted()` inside a comprehension triggered sorting |

**Assessment:** False positives are extremely rare (0.13% rate). The detector architecture is well-calibrated for specificity. The 2 false positives are edge cases, not systemic issues.

---

## 5. NAMING SENSITIVITY

### Most Name-Sensitive Detectors

| Detector | Naming Sensitivity | Failure Count | Critical Variable Names |
|----------|-------------------|---------------|------------------------|
| bfs_shortest_path | 83.3% | 10 | `queue`, `visited`, `node`, `dist` |
| dp_knapsack | 71.4% | 10 | `dp` |
| dp_1d_sequence | 57.1% | 8 | `dp` |
| dp_1d_forward | 56.2% | 10 | `dp` |
| binary_search_rotated | 50.0% | 6 | `left`, `right` |
| greedy_interval | 50.0% | 2 | `intervals` |
| backtracking_permutation | 40.0% | 4 | `path`, `result`, `visited` |
| fast_slow_pointers | 34.8% | 8 | `slow`, `fast` |
| two_pointers_same | 31.8% | 7 | `slow`, `fast` |
| sliding_window_fixed | 25.0% | 1 | `left`, `window_sum` |
| binary_search_tree | 25.0% | 2 | `root` |

### Key Insight

The `dp_*` detectors are the most name-sensitive group. They all check for a variable named `dp` (or `table`, `memo`, etc.) as primary evidence. Renaming `dp` to `f` or `state` or `cache` causes detection failure across 4 DP detectors simultaneously.

**This is a systemic issue, not a per-detector issue.** Fixing the DP detector naming convention would improve recall for ~30 problems at once.

---

## 6. STRUCTURAL SENSITIVITY

### Structural Variant Types Tested

| Variant Type | Count | Pass Rate | Notes |
|-------------|-------|-----------|-------|
| while-loop conversion | 72 | ~75% | for-range → while-loop conversion |
| for-in-collection → while | varies | ~80% | for x in arr → while idx < len(arr) |
| class-based wrapping | 0 | N/A | Generator produced 0 variants (regex limitation) |

### Key Finding

Structural sensitivity is lower than naming sensitivity. The for↔while conversion causes failures primarily in detectors that specifically check for `for` loop AST nodes (array_traversal, prefix_sum). Most other detectors are loop-form-agnostic.

---

## 7. GROUND-TRUTH ACCURACY

### CSV Dataset Analysis

| Metric | Value |
|--------|-------|
| Total problems | 300 |
| Single-pattern problems | 172 (57.3%) |
| Multi-pattern problems | 128 (42.7%) |
| Same-category (likely OR alternatives) | 48 (16.0% of total) |
| Different-category (likely AND/mixed) | 80 (26.7% of total) |
| CSV patterns covered by taxonomy | 30/30 (100%) |
| Problems with unsupported patterns | 0/300 (0%) |

### Single-Group Failure Rate

| Scenario | Count | Rate |
|----------|-------|------|
| Single-pattern (trivially correct) | 172 | 57.3% |
| Multi-pattern OR (incorrectly forced into AND) | 48 | **16.0%** |
| Multi-pattern AND/mixed (partially correct) | 80 | 26.7% |

**16.0% of problems have a guaranteed false-negative floor** due to the single-group collapsing. This is a structural flaw, not a detector flaw.

### LLM Ground-Truth Accuracy

**Not measured in this phase** (requires running the LLM against all 300 problems). This is deferred to Phase 6 validation.

---

## 8. MULTIPLE-SOLUTION FREQUENCY

### From CSV Data

| Pattern Combo | Count | Interpretation |
|--------------|-------|----------------|
| `bfs_level_order + dfs_recursive` | 12 | OR: either traversal works |
| `dfs_iterative + dfs_recursive` | 5 | OR: iterative or recursive DFS |
| `bfs_level_order + dfs_recursive + union_find` | 5 | OR: three alternatives |
| `hash_map_lookup + two_pointers_same` | 4 | OR: hashmap or two-pointer |
| `backtracking_subset + dfs_recursive` | 5 | AND: DFS within backtracking |
| `dp_1d_forward + greedy_local` | 3 | Mixed: DP + greedy |

### Assessment

**42.7% of problems have multiple patterns.** Of these, approximately 37.5% are same-category (likely OR alternatives) and 62.5% are different-category (likely AND/mixed). The single-group representation incorrectly handles all OR cases.

---

## 9. TAXONOMY INCONSISTENCIES

### Patterns in ALL_PATTERNS But Not in LLM Prompt

| Pattern | Has Detector | In CSV | In LLM Prompt |
|---------|-------------|--------|---------------|
| (none) | — | — | All 33 are in the prompt |

### Patterns With Detectors But Not in ALL_PATTERNS

| Pattern | Has Detector | In CSV | In ALL_PATTERNS |
|---------|-------------|--------|-----------------|
| array_traversal | Yes | Yes (in CSV) | **No** |
| brute_force | Yes | Yes (in CSV) | **No** |
| sorting | Yes | Yes (in CSV) | **No** |

**These 3 patterns have detectors and appear in the CSV, but are not in the canonical taxonomy.** This means:
1. The LLM cannot generate them as ground truth
2. `_normalize_patterns()` silently drops them
3. They cannot appear in ground truth
4. If a user's solution uses them, the matching engine will never expect them

### Taxonomy Orphan Rate

**3 of 36 detector patterns (8.3%) are orphaned from the taxonomy.** These are `array_traversal`, `brute_force`, and `sorting`.

---

## 10. HIGHEST-RISK DETECTORS

### Tier 1: Critical (recall < 50%)

| Detector | Recall | Primary Cause | Fix Complexity |
|----------|--------|---------------|----------------|
| bfs_shortest_path | 23.5% | Naming (queue/visited/node) | Medium — add alternative name sets |
| dp_knapsack | 29.4% | Naming (dp variable) | Low — add name alternatives for dp detectors |
| binary_search_answer | 46.0% | Expression (inline feasibility) | High — need semantic reasoning |
| dp_1d_sequence | 47.1% | Naming (dp variable) | Low — same fix as dp_knapsack |
| binary_search_rotated | 47.6% | Naming + expression | Medium — add name + expression alternatives |

### Tier 2: High Risk (recall 50-75%)

| Detector | Recall | Primary Cause |
|----------|--------|---------------|
| dp_1d_forward | 48.7% | Naming (dp variable) |
| backtracking_permutation | 61.5% | Naming (path/result) |
| two_pointers_same | 62.9% | Naming (slow/fast) |
| greedy_interval | 64.3% | Naming (intervals) |
| linked_list_reversal | 66.7% | Naming (prev/curr) |
| two_pointers_opposite | 71.4% | Structural reasoning |
| fast_slow_pointers | 72.4% | Naming (slow/fast) |

### Tier 3: Moderate Risk (recall 75-90%)

| Detector | Recall | Primary Cause |
|----------|--------|---------------|
| sliding_window_fixed | 75.0% | Naming |
| binary_search_tree | 76.1% | Naming |
| array_traversal | 77.8% | Structural |
| dp_2d_grid | 77.8% | Naming |
| dp_2d_string | 77.8% | Naming |
| prefix_sum | 80.0% | Structural + expression |
| monotonic_stack | 81.6% | Structural |
| binary_search_standard | 86.9% | Naming |
| hash_map_frequency | 88.9% | Structural |

### Tier 4: Low Risk (recall > 90%)

All remaining detectors (sliding_window_variable, hash_map_lookup, monotonic_deque, heap_top_k, dfs_recursive, and 11 detectors at 100%).

---

## 11. REPRESENTATIVE FAILURE EXAMPLES

### Example 1: bfs_shortest_path (naming)

**Original (detected):**
```python
from collections import deque
def shortestPath(graph, start, end):
    queue = deque([(start, 0)])
    visited = {start}
    while queue:
        node, dist = queue.popleft()
        if node == end:
            return dist
        for nb in graph[node]:
            if nb not in visited:
                visited.add(nb)
                queue.append((nb, dist + 1))
    return -1
```

**Renamed (NOT detected):**
```python
from collections import deque
def shortestPath(graph, start, end):
    q = deque([(start, 0)])
    seen = {start}
    while q:
        curr, d = q.popleft()
        if curr == end:
            return d
        for nb in graph[curr]:
            if nb not in seen:
                seen.add(nb)
                q.append((nb, d + 1))
    return -1
```

**Cause:** Detector checks for evidence type `queue_traversal` which requires finding `deque` import AND a variable named `queue`. Renaming `queue` to `q` eliminates the evidence.

### Example 2: binary_search_answer (expression)

**Original (detected):**
```python
low, high = 1, max_val
while low < high:
    mid = (low + high) // 2
    if is_feasible(mid):
        high = mid
    else:
        low = mid + 1
return low
```

**Inline feasibility (NOT detected):**
```python
low, high = 1, max_val
while low < high:
    mid = (low + high) // 2
    if arr[mid] < target:
        low = mid + 1
    else:
        high = mid
return low
```

**Cause:** Detector checks for evidence type `feasibility_check` which requires a function call like `is_feasible(mid)`. Inline comparison is not recognized as a feasibility check.

### Example 3: dp_1d_forward (naming)

**Original (detected):**
```python
dp = [0] * (n + 1)
dp[1] = 1
for i in range(2, n + 1):
    dp[i] = dp[i-1] + dp[i-2]
return dp[n]
```

**Renamed (NOT detected):**
```python
f = [0] * (n + 1)
f[1] = 1
for i in range(2, n + 1):
    f[i] = f[i-1] + f[i-2]
return f[n]
```

**Cause:** Detector checks for evidence type `dp_array_1d` which requires finding a variable named `dp` or `table` or `memo`. Renaming to `f` eliminates the evidence.

---

## 12. RECOMMENDED FIXES RANKED BY IMPACT

### Impact = (number of problems affected) × (fix reliability)

| Rank | Fix | Impact | Complexity | Problems Affected |
|------|-----|--------|------------|-------------------|
| 1 | **Add solution groups to ground truth** | VERY HIGH | Low | 48 problems (16%) |
| 2 | **Add alternative names for dp detectors** | HIGH | Low | ~30 problems |
| 3 | **Add alternative names for bfs detectors** | HIGH | Low | ~15 problems |
| 4 | **Add alternative names for binary_search detectors** | MEDIUM | Low | ~10 problems |
| 5 | **Add alternative names for backtracking detectors** | MEDIUM | Low | ~10 problems |
| 6 | **Add alternative names for two_pointers detectors** | MEDIUM | Low | ~10 problems |
| 7 | **Normalize comparison expressions** | MEDIUM | Medium | ~15 problems |
| 8 | **Add `array_traversal`, `brute_force`, `sorting` to ALL_PATTERNS** | LOW | Trivial | 0 (already detected) |
| 9 | **Improve binary_search_answer inline feasibility** | LOW | High | ~5 problems |
| 10 | **Improve while-loop recognition in array_traversal** | LOW | Medium | ~5 problems |

---

## 13. WHAT SHOULD NOT BE FIXED (Architectural Noise)

| Item | Why Not |
|------|---------|
| False positives (2 total) | 0.13% rate is excellent. Don't optimize for noise. |
| Detectors at 100% recall | 11 detectors already perfect. Don't touch them. |
| Class-based variant handling | The variant generator produced 0 class variants. This is a test infrastructure issue, not a detector issue. |
| Expression normalization for midpoints | Only affects 2 detectors. Low priority. |
| Helper-function extraction | Not tested (generator limitation). Defer to Phase 3. |

---

## 14. WHETHER THE PROPOSED FINAL ARCHITECTURE STILL MAKES SENSE

### Yes, with adjustments.

**The architecture's core claims are validated:**

1. **"The MatchingEngine's multi-group support is correct and should be used."** ✓ Confirmed. 16% of problems have OR alternatives that are incorrectly collapsed.

2. **"The LLM should be used minimally, primarily for problem-level ground-truth generation."** ✓ Confirmed. The AST engine is precise (99.8%) and only needs robustness improvements, not LLM augmentation.

3. **"Variable names must NOT become semantic truth."** ✓ Confirmed. 54.1% of false negatives are naming-dependent.

4. **"Analysis reliability should scale ELO updates."** ✓ Confirmed. Detectors with <50% recall would incorrectly penalize users without reliability scaling.

**Adjustments needed:**

1. **Phase 0 evaluation is more important than expected.** The 80.3% adversarial recall is significantly worse than the 93.9% measured on hand-crafted tests. This means Phase 3 (AST improvements) should be prioritized earlier.

2. **Naming fixes are higher priority than expected.** The DP detector naming convention (`dp` variable) is the single highest-impact fix. It affects 4 detectors and ~30 problems.

3. **The taxonomy orphan issue is trivial.** Adding 3 patterns to ALL_PATTERNS takes 5 minutes. Do this in Phase 1.

---

## 15. CHANGES TO THE ARCHITECTURE SPECIFICATION

### Changes

| Original | Revised | Reason |
|----------|---------|--------|
| Phase 3 (AST improvements) comes after Phase 2 | Phase 1 = taxonomy + naming fixes (merge with Phase 2) | Naming fixes are highest-impact, lowest-complexity |
| Phase 0 is "evaluation only" | Phase 0 includes naming sensitivity fixes for DP detectors | The fix is trivial and blocks accurate measurement |
| Ground truth representation is Phase 2 | Ground truth representation is Phase 1 | Structural flaw affects 16% of problems |

### Revised Phase Order

| Phase | Objective | Effort |
|-------|-----------|--------|
| Phase 0 | Evaluation harness + taxonomy alignment + DP naming fixes | 1-2 days |
| Phase 1 | Ground truth solution groups + versioning | 1-2 days |
| Phase 2 | BFS/backtracking/two-pointer naming fixes | 1 day |
| Phase 3 | Reliability scoring + ELO safety | 1-2 days |
| Phase 4 | Expression normalization (if measurements show it's needed) | 1-2 days |
| Phase 5 | LLM ground-truth validation | 2-3 days |

---

*End of Phase-0 Adversarial Evaluation Report*
