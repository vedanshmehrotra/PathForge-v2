# SEMANTIC EXPERIMENT 3A: Primary-Role Gated Scorer

## Objective

Determine whether adding PRIMARY-ROLE features (data-flow centrality, return-value dependency, bookkeeping detection) can reduce cross-pattern false positives from the semantic scorer without destroying recall.

## What Was Built

### New Files
- `src/ast_detection/semantic/primary_role.py` — Feature extractor for primary-role evidence
- `src/ast_detection/semantic/primary_scorer.py` — Gated scorer that multiplies structural score × role gate

### Modified Files
- `src/ast_detection/semantic/features.py` — Added `PrimaryRoleFeatures` dataclass
- `src/ast_detection/semantic/analyzer.py` — Integrated primary-role extraction and scoring

### Architecture
```
Code → AST → Structural Features → Structural Score
                                 ↘ Primary-Role Features → Role Gate → Final Score
```

The gate is a multiplier [0.0, 1.0] applied to the structural score:
- `final_score = structural_score × gate`
- Gate < 0.5 → pattern classified as "incidental" → suppressed below threshold

### Primary-Role Features
- Return value dependency (does the result depend on candidate state?)
- Control-flow influence (do candidate vars drive conditions/branches?)
- Bookkeeping detection (visited set, frequency counting)
- Competing pattern detection (binary search, sorting)
- Result-dependency tracking

## Evaluation Corpus

321 cases from calibration (46) + generalization (275) corpora.
Cross-pattern evaluation: every case tested against ALL 4 target patterns.

## Results

### Cross-Pattern Comparison: AST vs Hybrid (Primary-Role Gated)

| Pattern | AST P | AST R | AST F1 | Hybrid P | Hybrid R | Hybrid F1 | Delta F1 |
|---------|-------|-------|--------|----------|----------|-----------|----------|
| two_pointers_opposite | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | +0.000 |
| prefix_sum | 0.827 | 0.860 | 0.843 | 0.833 | 1.000 | **0.909** | **+0.066** |
| hash_map_lookup | 0.979 | 0.958 | 0.968 | 0.687 | 0.958 | 0.800 | -0.168 |
| array_traversal | 0.302 | 0.891 | 0.451 | 0.256 | 0.984 | 0.406 | -0.044 |

### Primary-Role Gate Effectiveness

| Pattern | Ungated FPs | Gated FPs | FPs Eliminated | Gate Effectiveness |
|---------|-------------|-----------|----------------|-------------------|
| two_pointers_opposite | 0 | 0 | 0 | N/A (already perfect) |
| prefix_sum | 15 | 10 | **5 eliminated** | ✅ Effective |
| hash_map_lookup | 30 | 21 | **9 eliminated** | ⚠️ Partial |
| array_traversal | 183 | 183 | 0 | ❌ Not effective |

### Pattern-Specific Analysis

#### two_pointers_opposite ✅
- AST already at 1.0 F1 on this corpus
- Semantic layer provides no additional value on this corpus
- Primary-role gate: no false positives to eliminate
- **Classification: NO CHANGE NEEDED**

#### prefix_sum ✅ BEST IMPROVEMENT
- **7 AST false negatives recovered** (while-loop accumulation, renamed indices)
- Only **+1 cross-pattern FP** added
- Primary-role gate eliminates 5 prefix_sum FPs (code with `+=` that isn't prefix sum)
- **Classification: STRONG CANDIDATE FOR PRODUCTION**

#### hash_map_lookup ❌ WORSE THAN AST
- 20 cross-pattern FPs remain (all are prefix_sum cases with membership tests)
- Primary-role gate eliminates 9 FPs (visited sets, frequency maps)
- But 21 FPs still remain, vs AST's 1 FP
- The problem: prefix_sum code often uses `in nums` for validation, which the scorer interprets as hash_map evidence
- **Classification: NOT SAFE FOR PRODUCTION** — semantic layer cannot distinguish "membership as part of prefix_sum" from "membership as primary lookup strategy"

#### array_traversal ❌ FUNDAMENTALLY TOO BROAD
- 183 cross-pattern FPs (vs AST's 132)
- Primary-role gate eliminates 0 FPs — array iteration is too generic
- Semantic layer correctly identifies structural traversal but can't distinguish primary vs incidental
- **Classification: KEEP AST-ONLY** — array_traversal should remain a structural-only concept

### False-Positive Taxonomy

#### hash_map_lookup FPs (20 remaining)
All are prefix_sum cases that use `x in nums` or `x in collection` for validation:
- `prefix_sum_subarray_sum_k` — uses `sum(nums[i:j]) == target` (structural FP from `in` usage)
- `prefix_sum_contiguous_array` — uses `running_sum in seen`
- `prefix_sum_prefix_sum_string` — uses `prefix[i] in arr`

Root cause: The semantic scorer cannot distinguish "membership test as part of prefix_sum logic" from "membership test as the primary algorithmic strategy." Both have:
- membership test detected
- result depends on membership
- membership drives control flow

The only difference is which algorithm owns the membership. This requires cross-pattern competition analysis.

#### array_traversal FPs (183 remaining)
All are code that iterates arrays as part of other algorithms:
- Sorting: `for i in range(n): for j in range(n-i-1):`
- BFS/DFS: `for neighbor in graph[node]:`
- DP: `for i in range(1, n): dp[i] = ...`
- Binary search: `while left <= right: mid = ...`

Root cause: Array traversal is structurally present in nearly every algorithm. The semantic scorer correctly detects this, but "array traversal" is not a meaningful primary pattern label for most code.

### Primary-Role Gate Classification

| Pattern | Primary-Role Classifiable? | Evidence |
|---------|---------------------------|----------|
| two_pointers_opposite | ✅ YES | Bidirectional movement is highly distinctive; result dependency check works |
| prefix_sum | ✅ YES | Accumulation centrality check works; can distinguish accumulation from counters |
| hash_map_lookup | ⚠️ PARTIAL | Bookkeeping detection works, but can't distinguish "lookup as part of another algorithm" |
| array_traversal | ❌ NO | Too structurally generic; cannot determine primary role from static analysis alone |

## Experiment 3A Assessment

### What Worked
1. **Bookkeeping detection**: Visited sets and frequency maps correctly suppressed (hash_map_lookup gate = 0.18 on DFS code)
2. **Prefix-sum centrality**: Simple counters correctly distinguished from genuine prefix-sum logic
3. **Competing pattern detection**: Binary search detected and flagged
4. **Zero regressions**: All 556 existing tests pass

### What Didn't Work
1. **hash_map_lookup cross-pattern suppression**: The gate cannot distinguish "membership as part of prefix_sum" from "membership as primary strategy" — both have identical structural and centrality signals
2. **array_traversal classification**: The concept is too broad; any iteration of a collection is structurally "array traversal," making primary-role classification impossible
3. **Suffix pattern FP elimination**: The 183 array_traversal FPs are inherent to the concept, not fixable by gating

### Architectural Conclusion

The primary-role model can reduce cross-pattern false positives when:
- The incidental usage has clearly bookkeeping-like characteristics (visited set, frequency map)
- The pattern is highly distinctive (two pointers, prefix sum)

It cannot reduce cross-pattern false positives when:
- The incidental behavior is structurally identical to the primary behavior (membership test in prefix_sum code)
- The pattern concept is too broad (array traversal)

## Recommendation: PARTIAL APPROVE

The primary-role gated scorer should be kept as an OBSERVATIONAL module only. It provides valuable diagnostics but is NOT safe for authoritative classification due to:
1. 20 hash_map_lookup FPs (vs AST's 1 FP)
2. 183 array_traversal FPs (vs AST's 132)
3. The semantic layer's fundamental limitation: structural behavior ≠ algorithmic role

### Safe to use for:
- Shadow-mode diagnostics (as already deployed)
- Research and development of better primary-role features
- Identifying which patterns have strong enough structural signals for authoritative classification

### NOT safe for:
- Production scoring
- ELO updates
- Gap generation
- Recommendation generation
- Any authoritative downstream behavior

## Files Created/Modified

```
src/ast_detection/semantic/
├── primary_role.py        # NEW: Primary-role feature extractor
├── primary_scorer.py      # NEW: Gated scorer with role evidence
├── features.py            # MODIFIED: Added PrimaryRoleFeatures
├── analyzer.py            # MODIFIED: Integrated primary-role analysis
```

## Test Results

- 556/556 AST tests pass ✅
- 74/74 semantic tests pass ✅
- 0 regressions ✅
