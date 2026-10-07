# PHASE-2 ARCHITECTURE AND PRIORITIZATION REPORT

Status: Analysis only. No production code changes.

---

## 1. EVALUATION VALIDITY

### 1a. Known artifacts still present

| Artifact | Impact | Severity | Recommendation |
|----------|--------|----------|----------------|
| 17 left/right rename collisions | Contaminates FN count for binary_search and two_pointers detectors | Low | Filter these variants out or count separately |
| 149 syntax errors in generated variants | Filtered by harness (good) | None | No action needed |
| 552 "no function def" variants | False alarm: class-based variants have methods, not top-level functions | None | No action needed |
| Variant generation does not produce for/while where both use same variable update pattern | Some loop-form mutations produce broken code | Low | Acceptable; broken variants are filtered |

### 1b. Seed-variant linking correctness

The deep failure analysis correctly links variants to their seed via the
seed_case_id field. The classification logic is:
- Seed fails + variant fails = inherited
- Seed passes + variant fails = true variant failure

This classification is sound. The 17 left/right collisions could inflate
the "true naming" count by up to 17 cases, but these are scattered across
detectors and do not materially change the ranking.

### 1c. Overall assessment

The evaluation corpus is trustworthy for ranking purposes. The metrics
are reliable for relative comparisons between detectors. The absolute
FN count may be inflated by 5-10% due to variant-generation artifacts,
but this does not affect the prioritization.

---

## 2. SEED FAILURE TABLE

Sorted by cascading impact (highest first):

| Rank | Detector | Seed | Root Cause | Cascade | Fix Type | Est. Recovery |
|------|----------|------|-----------|---------|----------|---------------|
| 1 | two_pointers_same | happy_number_ptrs | Heuristic: requires +=1/+=2 differential but seed uses function calls | 6 | Improve heuristic | 6 |
| 2 | sliding_window_fixed | fixed_window_set | Requires ast.For; seed uses for but detector checks window.remove() not -= | 6 | Broaden evidence check | 6 |
| 3 | bfs_shortest_path | 01_matrix | Distance check: ast.Name("dist") but code uses ast.Subscript("dist[i][j]") | 6 | Fix distance check | 6 |
| 4 | binary_search_rotated | rotated_min | Condition check fails on specific comparison form | 6 | Broaden condition check | 6 |
| 5 | dp_1d_forward | decode_ways | Confidence 0.70 but detected=False; needs 0.80 threshold OR more evidence | 6 | Add evidence OR lower threshold | 6 |
| 6 | two_pointers_same | slow_fast_differential | Same as #1: requires differential step sizes | 5 | Improve heuristic | 5 |
| 7 | two_pointers_same | slow_reset_pattern | Same as #1: uses reset pattern not covered | 5 | Add reset pattern | 5 |
| 8 | sliding_window_fixed | fixed_window_product | Same as #2: window operation not recognized | 4 | Broaden evidence check | 4 |
| 9 | monotonic_stack | maximal_rectangle | Detector expects specific stack pattern not present | 4 | Improve heuristic | 4 |
| 10 | linked_list_reversal | reverse_between_92 | Partial reversal not detected (only full reversal) | 4 | Add partial reversal | 4 |
| 11 | bfs_shortest_path | rotten_oranges | Same as #3: distance check fails on subscript | 4 | Fix distance check | 4 |
| 12 | binary_search_tree | bst_lca | Only bst_comparison evidence (0.30); needs more | 4 | Add traversal evidence | 4 |
| 13 | binary_search_tree | bst_floor_ceiling | Same as #12 | 4 | Add traversal evidence | 4 |
| 14 | backtracking_permutation | permutations | Nested function pattern not recognized | 4 | Add nested function support | 4 |
| 15 | backtracking_permutation | n_queens_style | Same as #14 | 4 | Add nested function support | 4 |
| 16 | dp_knapsack | partition_equal_subset_sum | 1D dp array not recognized as knapsack | 4 | Add 1D knapsack support | 4 |
| 17 | dp_knapsack | coin_change | Same as #16 | 4 | Add 1D knapsack support | 4 |
| 18 | greedy_interval | insert_interval | No greedy evidence detected | 3 | Improve heuristic | 3 |
| 19 | prefix_sum | pivot_index | Prefix sum pattern not detected (no running variable) | 2 | Improve heuristic | 2 |
| 20 | binary_search_answer | kth_smallest_distance | Answer-space check requires function call | 2 | Add inline comparison | 2 |
| 21 | linked_list_reversal | reverse_between_alternative | Same as #10 | 2 | Add partial reversal | 2 |
| 22 | binary_search_answer | gas_station | Answer-space check requires function call | 0* | Add inline comparison | 0 |
| 23 | dp_1d_sequence | LIS_with_BS | Sequence pattern not detected | 0* | Improve heuristic | 0 |

*Seeds 22-23 have 0 cascading variants in the current corpus.

### Summary by fix type

| Fix Type | Seeds | Total Cascade | Combined Recovery |
|----------|-------|--------------|-------------------|
| Improve heuristic (specific) | 8 | 36 | 36 |
| Broaden evidence check | 4 | 22 | 22 |
| Fix distance/subscript check | 2 | 10 | 10 |
| Add new detection path | 4 | 16 | 16 |
| Add inline comparison support | 2 | 2 | 2 |
| Lower confidence threshold | 1 | 6 | 6 |

---

## 3. LOOP-FORM ANALYSIS

### 3a. Failure clusters

| Cluster | Count | Detectors | Root Cause |
|---------|-------|-----------|------------|
| for-in-collection -> while-with-index | 26 | array_traversal(12), hash_map_lookup(5), prefix_sum(5), hash_map_frequency(3), two_pointers_same(1) | Detector checks for ast.For with iter=Name, but while version uses ast.While with ast.Subscript |
| for-range -> while | 7 | array_traversal(0), prefix_sum(0), others(7) | Detector checks for ast.For with iter=Call(range), but while version uses ast.While |

### 3b. Which detectors check for ast.For vs ast.While?

| Detector | Checks For | Checks While | Loop-Form FN |
|----------|-----------|-------------|-------------|
| array_traversal | ast.For | No | 12 |
| hash_map_lookup | ast.For | No | 5 |
| prefix_sum | ast.For | No | 5 |
| hash_map_frequency | ast.For | No | 3 |
| monotonic_stack | ast.For | No | 2 |
| monotonic_deque | ast.For | No | 2 |
| heap_top_k | ast.For | No | 2 |
| two_pointers_same | ast.While | Yes | 2 (different cause) |

### 3c. Can a shared abstraction help?

**Option A: Shared loop abstraction**

A utility that normalizes for/while loops into a common representation.
Detectors would call `get_loop_type(node)` instead of checking
`isinstance(node, ast.For)`.

| Metric | Assessment |
|--------|-----------|
| Detectors affected | 7 (array_traversal, hash_map_lookup, prefix_sum, hash_map_frequency, monotonic_stack, monotonic_deque, heap_top_k) |
| FN recovered | 33 |
| FP risk | Low (normalization is syntactic, not semantic) |
| Complexity | Medium (need to handle for-range, for-in, while with counter) |
| False positive risk | Low if limited to simple patterns |

**Option B: Per-detector loop recognition**

Each detector adds while-loop support independently.

| Metric | Assessment |
|--------|-----------|
| Detectors affected | 7 (same) |
| FN recovered | 33 |
| FP risk | Low |
| Complexity | Low per detector, but duplicated across 7 detectors |
| Maintainability | Worse (7 copies of similar logic) |

**Recommendation: Option A (shared abstraction)** is justified here because:
1. 7 detectors need the same capability
2. The normalization is syntactic and mathematically safe
3. The logic is simple: detect for-range/for-in patterns and extract iterator/bounds

### 3d. Proposed abstraction

```python
def classify_loop(node):
    """Classify a loop node into a canonical form.
    
    Returns LoopInfo with:
    - type: 'for_range', 'for_in', 'while_with_counter', 'while_other'
    - iterator_var: the loop variable name (for loops) or counter name
    - bound_expr: the bound expression (len(x), range(n), etc.)
    - body: the loop body
    """
```

This is a small, focused utility. It does NOT attempt to normalize
all loop semantics -- just the structural classification needed by
the 7 affected detectors.

---

## 4. EXPRESSION-FORM ANALYSIS

### 4a. Failure clusters

| Cluster | Count | Detectors | Root Cause |
|---------|-------|-----------|------------|
| Negated comparison in while condition | 22 | two_pointers_opposite(8), binary_search_answer(8), binary_search_standard(4), binary_search_tree(1), binary_search_rotated(1) | while-condition check expects ast.Compare but gets ast.UnaryOp(Not, Compare) |
| Midpoint variant | 9 | binary_search_answer(8), binary_search_rotated(1) | Midpoint calculation uses different AST shape |

### 4b. Negated comparison analysis

The variant generator transforms `while a < b` into `while not (a >= b)`.

AST difference:
- Normal: `ast.While(test=ast.Compare(left=a, ops=[Lt], comparators=[b]))`
- Negated: `ast.While(test=ast.UnaryOp(op=Not, operand=ast.Compare(left=a, ops=[GtE], comparators=[b])))`

**Mathematical equivalence**: `not (a >= b)` is exactly `a < b`.

**Detectors affected**: 5 detectors, 22 FN total.

**Fix**: A small utility function:

```python
def unwrap_negated_compare(test):
    """If test is `not (a >= b)`, return the equivalent `ast.Compare(a, [Lt], [b])`.
    Otherwise return test unchanged.
    """
```

This is mathematically safe and cannot create false positives.

### 4c. Midpoint variant analysis

The variant transforms `(left + right) // 2` into `left + (right - left) // 2`.

AST difference:
- Normal: `BinOp(BinOp(left, Add, right), FloorDiv, 2)`
- Variant: `BinOp(left, Add, BinOp(BinOp(right, Sub, left), FloorDiv, 2))`

**Mathematical equivalence**: `(a + b) // 2` equals `a + (b - a) // 2` for integers.

**Detectors affected**: 2 detectors, 9 FN total.

**Fix**: The midpoint check in `binary_search_classic.py` and
`binary_search_answer.py` already handles both forms (checks for
`isinstance(val.left, ast.BinOp) and isinstance(val.left.op, ast.Sub)`).
The 9 failures may be from other structural differences in the variant.

### 4d. Proposed normalization primitives

| Primitive | FN Recovered | FP Risk | Complexity |
|-----------|-------------|---------|------------|
| `unwrap_negated_compare(test)` | 22 | None (mathematical equivalence) | Low |
| Verify midpoint variant handling | 9 | None | Low (audit existing code) |

The negated-comparison normalizer is the single highest-value,
lowest-risk fix in the entire expression category.

---

## 5. DETECTOR-SPECIFIC FAILURE ANALYSIS

### 5a. two_pointers_same (3 seeds, 16 cascading)

**Root cause**: The detector's `_detect_slow_fast_differential` requires
two variables incremented by DIFFERENT step sizes (e.g., +=1 and +=2).
The failing seeds use:
- `happy_number_ptrs`: function calls (`slow = sum(...)`, `fast = sum(...)`)
- `slow_fast_differential`: same step size (`slow += 1`, `fast += 1`)
- `slow_reset_pattern`: reset pattern not covered

**Fix options**:
1. Add a "differential update" detection path (any two variables updated
   differently in a while loop)
2. Add "function call update" detection (slow = f(slow), fast = f(f(fast)))

**Recommendation**: Option 1 is simpler and covers more cases. Option 2
is more general but higher risk.

### 5b. sliding_window_fixed (2 seeds, 10 cascading)

**Root cause**: The detector checks for `window.remove(nums[left])` or
`window -= arr[left]` but the seeds use:
- `fixed_window_set`: `window.remove(nums[left])` -- this IS an `ast.Call`,
  not an `ast.AugAssign`. The detector only checks for `ast.AugAssign`
  with `ast.Sub`.
- `fixed_window_product`: similar issue

**Fix**: Add `ast.Call` with `attr="remove"` as a window-shrink signal.

### 5c. bfs_shortest_path (2 seeds, 10 cascading)

**Root cause**: `_find_distance_tracking` checks for `ast.Name` with
keywords like "dist", "step", "level". But the seeds use
`dist[i][j] = dist[r][c] + 1`, which is `ast.Subscript`, not `ast.Name`.

**Fix**: Extend distance tracking to also check `ast.Subscript` targets.

### 5d. backtracking_permutation (2 seeds, 8 cascading)

**Root cause**: The seeds use nested functions (`def backtrack(path,
remaining)`) but the detector expects a specific backtracking structure
that doesn't account for this indirection.

**Fix**: Add detection for nested function calls with recursive patterns.

### 5e. dp_knapsack (2 seeds, 8 cascading)

**Root cause**: The seeds use 1D DP arrays (`dp = [False] * (target + 1)`)
but the detector's `max_min_recurrence` check expects 2D patterns or
specific recurrence shapes.

**Fix**: Add 1D knapsack pattern recognition.

### 5f. binary_search_rotated (1 seed, 6 cascading)

**Root cause**: The seed `rotated_min` has confidence=0.80 but
detected=False. The detector requires specific evidence that isn't
produced.

**Fix**: Investigate which evidence is missing and add it.

---

## 6. GROUND-TRUTH MULTI-SOLUTION ARCHITECTURE

### 6a. Current flow

```
LLM prompt: "identify the algorithmic patterns required to solve it"
    |
    v
LLM response: {"patterns": ["dfs", "bfs"], "confidence": {"dfs": 0.9}}
    |
    v
_store_ground_truth: flat JSON array in problem_ground_truth.patterns
    |
    v
_load_ground_truth: wraps ALL patterns into single group_0
    |
    v
MatchingEngine: receives [["dfs", "bfs"]] (one AND group)
```

**Problem**: 42.7% of problems have multiple valid approaches. All are
collapsed into one AND-required group. A user who solves with only DFS
gets a false negative because the group requires both DFS and BFS.

### 6b. Proposed minimal change

**Step 1: Modify LLM prompt** to request explicit solution groups:

```
For each distinct optimal approach, return a separate group.
Example:
{
  "solution_groups": [
    {"patterns": ["dfs_recursive"], "confidence": 0.9},
    {"patterns": ["bfs_level_order"], "confidence": 0.8}
  ]
}
```

**Step 2: Add `solution_groups` column** to `problem_ground_truth`:

```sql
ALTER TABLE problem_ground_truth
ADD COLUMN solution_groups TEXT DEFAULT NULL;
```

This column stores the full multi-group structure. The existing
`patterns` column is kept for backward compatibility.

**Step 3: Modify `_load_ground_truth`** to use `solution_groups` if
available, falling back to the single-group behavior.

**Step 4: MatchingEngine already supports multi-group OR.** No changes needed.

### 6c. Database migration

| Change | Risk | Rollback |
|--------|------|----------|
| Add `solution_groups` column | None (nullable) | DROP COLUMN |
| Populate for existing problems | Medium (LLM call) | UPDATE NULL |
| Switch `_load_ground_truth` | Low | Revert code |

### 6d. LLM reliability handling

| Scenario | Handling |
|----------|----------|
| LLM returns valid groups | Store and use |
| LLM returns flat list (legacy) | Wrap in single group (current behavior) |
| LLM returns invalid patterns | Filter to ALL_PATTERNS (current behavior) |
| LLM returns empty groups | Use single group with raw patterns |
| LLM unavailable | Use cached result (current behavior) |

---

## 7. PROPOSED PHASE-2 EXPERIMENTS

### Experiment 2A: Fix highest-impact seed detector failures

**Hypothesis**: Fixing the top 5 seed detectors (by cascade) recovers
~40-50 FN.

**Files likely affected**:
- `src/ast_detection/detectors/two_pointers_same.py`
- `src/ast_detection/detectors/sliding_window_fixed.py`
- `src/ast_detection/detectors/bfs_shortest_path.py`
- `src/ast_detection/detectors/backtracking_permutation.py`
- `src/ast_detection/detectors/dp_knapsack.py`

**Benchmark**: Run adversarial evaluation corpus.

**Success metric**: Recall improves from 83.9% toward 88%+.

**Precision guardrail**: FP must remain <= 2.

**Rollback**: Revert individual detector changes.

**Priority**: HIGH (highest ROI per line of code changed)

### Experiment 2B: Test loop-form improvements

**Hypothesis**: A shared loop classification utility recovers 20-30 FN.

**Files likely affected**:
- `src/ast_detection/detectors/base.py` (add utility)
- `src/ast_detection/detectors/array_traversal.py`
- `src/ast_detection/detectors/hash_map_lookup.py`
- `src/ast_detection/detectors/prefix_sum.py`
- `src/ast_detection/detectors/hash_map_frequency.py`
- `src/ast_detection/detectors/monotonic_stack.py`
- `src/ast_detection/detectors/monotonic_deque.py`
- `src/ast_detection/detectors/heap_top_k.py`

**Benchmark**: Adversarial corpus, loop-form variant subset.

**Success metric**: Loop-form FN drops from 33 to <10.

**Precision guardrail**: FP must remain <= 2.

**Rollback**: Revert utility and detector changes.

**Priority**: MEDIUM (good ROI but more detectors affected)

### Experiment 2C: Test minimal expression normalization

**Hypothesis**: An `unwrap_negated_compare` utility recovers 15-22 FN.

**Files likely affected**:
- `src/ast_detection/detectors/base.py` (add utility)
- `src/ast_detection/detectors/two_pointers_opposite.py`
- `src/ast_detection/detectors/binary_search_answer.py`
- `src/ast_detection/detectors/binary_search_classic.py`
- `src/ast_detection/detectors/binary_search_rotated.py`
- `src/ast_detection/detectors/binary_search_tree.py`

**Benchmark**: Adversarial corpus, expression variant subset.

**Success metric**: Expression FN drops from 31 to <10.

**Precision guardrail**: FP must remain <= 2.

**Rollback**: Revert utility and detector changes.

**Priority**: HIGH (mathematically safe, high FN recovery, low complexity)

### Experiment 2D: Evaluate multi-solution ground truth

**Hypothesis**: Explicit solution groups reduce ground-truth false negatives.

**Files likely affected**:
- `pathforge/llm/openrouter_client.py` (prompt change)
- `pathforge/services/ground_truth_builder.py` (store groups)
- `pathforge/services/problem_resolver.py` (load groups)
- `pathforge/db/schema_pg.sql` (add column)

**Benchmark**: 300-problem CSV with known multi-solution problems.

**Success metric**: Problems with multiple valid approaches no longer
produce false negatives when user uses one approach.

**Precision guardrail**: N/A (ground truth change, not detector change).

**Rollback**: Revert prompt and loading code; drop column.

**Priority**: MEDIUM (important but separate from AST robustness)

---

## 8. PRIORITY MATRIX

| Change | Impact (FN recovered) | Confidence (will work) | Complexity | Priority Score |
|--------|----------------------|----------------------|------------|---------------|
| Negated comparison normalizer | 22 | High | Low | **22** |
| Fix bfs_shortest_path distance check | 10 | High | Low | **10** |
| Fix sliding_window_fixed evidence | 10 | High | Low | **10** |
| Fix backtracking_permutation nested fn | 8 | Medium | Medium | **4** |
| Fix dp_knapsack 1D support | 8 | Medium | Medium | **4** |
| Fix two_pointers_same heuristic | 16 | Medium | Medium | **5** |
| Loop classification utility | 33 | Medium | Medium | **11** |
| Fix binary_search_rotated | 6 | Medium | Medium | **2** |
| Fix monotonic_stack seed | 4 | Medium | Low | **4** |
| Fix linked_list_reversal partial | 6 | Medium | Medium | **2** |
| Fix greedy_interval seed | 3 | Low | Medium | **1** |
| Multi-solution ground truth | ~30 (ground truth FN) | Medium | High | **5** |
| Fix prefix_sum seed | 2 | Low | Low | **2** |

**Priority Score = Impact x Confidence / Complexity** (simplified)

**Top 5 by priority**:
1. Negated comparison normalizer (22 FN, high confidence, low complexity)
2. Loop classification utility (33 FN, medium confidence, medium complexity)
3. Fix bfs_shortest_path distance check (10 FN, high confidence, low complexity)
4. Fix sliding_window_fixed evidence (10 FN, high confidence, low complexity)
5. Fix two_pointers_same heuristic (16 FN, medium confidence, medium complexity)

---

## 9. RECOMMENDED IMPLEMENTATION ORDER

### Phase 2A: Expression normalization (highest ROI, lowest risk)

1. Add `unwrap_negated_compare()` utility to `base.py`
2. Apply to `two_pointers_opposite.py`
3. Apply to `binary_search_classic.py`
4. Apply to `binary_search_answer.py`
5. Apply to `binary_search_rotated.py`
6. Apply to `binary_search_tree.py`
7. Run adversarial corpus
8. Expected: 15-22 FN recovered, FP unchanged

### Phase 2B: Seed detector fixes (highest cascade impact)

1. Fix `bfs_shortest_path.py` distance check (subscript support)
2. Fix `sliding_window_fixed.py` evidence check (remove() support)
3. Fix `backtracking_permutation.py` nested function support
4. Fix `dp_knapsack.py` 1D array support
5. Fix `two_pointers_same.py` heuristic broadening
6. Run adversarial corpus
7. Expected: 30-40 FN recovered (including cascading)

### Phase 2C: Loop-form improvements

1. Add `classify_loop()` utility to `base.py`
2. Update `array_traversal.py` to use it
3. Update `hash_map_lookup.py` to use it
4. Update `prefix_sum.py` to use it
5. Update remaining 4 detectors
6. Run adversarial corpus
7. Expected: 20-30 FN recovered

### Phase 2D: Ground-truth multi-solution (separate track)

1. Modify LLM prompt in `openrouter_client.py`
2. Add `solution_groups` column to schema
3. Update `ground_truth_builder.py` to store groups
4. Update `problem_resolver.py` to load groups
5. Test with 30-problem multi-solution subset
6. Expected: Ground-truth FN reduced for multi-solution problems

### Estimated combined impact

| Phase | Cumulative FN Recovered | Estimated Recall |
|-------|------------------------|-----------------|
| Baseline | 0 | 83.9% |
| + Phase 2A | +15-22 | 85.2-85.6% |
| + Phase 2B | +30-40 (total) | 86.3-87.1% |
| + Phase 2C | +50-70 (total) | 87.9-89.4% |
| + Phase 2D | (ground truth) | N/A (different metric) |

**Note**: These phases are cumulative. Phase 2B builds on 2A's
normalization. Phase 2C is independent.

**Conservative ceiling after all Phase-2 experiments: ~89-90% recall**
with zero FP increase.

---

*End of Phase-2 Architecture and Prioritization Report*
