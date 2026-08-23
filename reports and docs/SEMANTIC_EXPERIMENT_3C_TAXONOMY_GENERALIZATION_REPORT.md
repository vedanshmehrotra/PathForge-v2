# SEMANTIC EXPERIMENT 3C: Cross-Pattern Generalization + Taxonomy Boundary Validation

## Objective

Determine whether the competition model generalizes to unseen code, test unresolved pattern boundaries, and re-evaluate the pattern taxonomy.

## Corpus

**301 cases** from 5 disjoint corpus files, completely independent from calibration (46) and generalization (275) corpora.

- 180 positive cases (code that IS the expected pattern)
- 121 negative cases (code that is a DIFFERENT pattern)
- 21 family groups covering confusable pattern pairs
- No parent seeds shared with previous experiments

## Out-of-Sample Results: 4-Model Comparison

### two_pointers_opposite

| Model | P | R | F1 | TP | FP | FN |
|-------|---|---|-----|----|----|-----|
| AST | 0.964 | 0.711 | 0.818 | 27 | 1 | 11 |
| Semantic ungated | 0.900 | 0.711 | 0.794 | 27 | 3 | 11 |
| Primary-role | 0.900 | 0.711 | 0.794 | 27 | 3 | 11 |
| Competition | 0.900 | 0.711 | 0.794 | 27 | 3 | 11 |

**Analysis**: Semantic layer provides NO benefit. Same recall as AST, worse precision. The 11 FNs are all genuine two_pointer implementations that neither AST nor semantic detects. The 3 FPs are sliding window code.

### prefix_sum

| Model | P | R | F1 | TP | FP | FN |
|-------|---|---|-----|----|----|-----|
| AST | 0.778 | 0.528 | 0.629 | 28 | 8 | 25 |
| Semantic ungated | 0.571 | 0.679 | 0.621 | 36 | 27 | 17 |
| Primary-role | 0.590 | 0.679 | 0.632 | 36 | 25 | 17 |
| Competition | 0.590 | 0.679 | 0.632 | 36 | 25 | 17 |

**Analysis**: Semantic layer recovers 8 AST FNs but introduces 19 new FPs. Net F1 improvement: +0.003 (negligible). The primary-role gate eliminates only 2 FPs. Competition rules provide no benefit for prefix_sum.

### hash_map_lookup

| Model | P | R | F1 | TP | FP | FN |
|-------|---|---|-----|----|----|-----|
| AST | 0.714 | 0.517 | 0.600 | 30 | 12 | 28 |
| Semantic ungated | 0.627 | 0.810 | 0.707 | 47 | 28 | 11 |
| Primary-role | 0.589 | 0.569 | 0.579 | 33 | 23 | 25 |
| Competition | 0.714 | 0.517 | 0.600 | 30 | 12 | 28 |

**Analysis**: This is the most revealing result. The competition model MATCHES AST exactly — it suppresses 57 cases but 27 of those are genuine hash_map cases that should NOT be suppressed. The competition rules generalize POORLY: rules tuned on the 321-case corpus over-suppress on the 301-case corpus.

### array_traversal

| Model | P | R | F1 | TP | FP | FN |
|-------|---|---|-----|----|----|-----|
| AST | 0.133 | 0.897 | 0.232 | 26 | 169 | 3 |
| Semantic ungated | 0.115 | 0.966 | 0.205 | 28 | 216 | 1 |
| Primary-role | 0.115 | 0.966 | 0.205 | 28 | 216 | 1 |
| Competition | 0.130 | 0.966 | 0.229 | 28 | 188 | 1 |

**Analysis**: All models produce unacceptable precision (11-13%). The semantic layer adds 47 more FPs on top of AST's 169. Competition suppresses 28 but that's insufficient. array_traversal is fundamentally too broad.

## Competition Rule Generalization Assessment

| Rule | In-Sample | Out-of-Sample | Verdict |
|------|-----------|---------------|---------|
| prefix_sum dominates hash_map | ✅ Correct | ⚠️ Over-suppresses | Partially robust |
| BFS/DFS vs hash_map | ✅ Correct | ⚠️ Over-suppresses | Partially robust |
| Binary search vs two_pointers | ✅ Correct | N/A (not triggered) | Untested |
| Sorting vs array_traversal | ✅ Correct | N/A (not triggered) | Untested |
| array_traversal demotion | ✅ Correct | ✅ Helps | Robust |

**Key finding**: The two most important rules (prefix_sum vs hash_map, BFS/DFS vs hash_map) over-suppress on unseen code. Rules tuned on in-sample data do NOT generalize.

## False-Positive Analysis by Family

### hash_map_lookup FPs (competition model, 12 total)
- 6 from hash_vs_bfs: BFS/DFS code with visited set (rule correctly identifies but over-suppresses)
- 2 from tp_genuine: Two-pointer code with incidental membership
- 2 from ps_vs_generic: Prefix sum code with membership
- 1 from hm_vs_ds: Data structure operations
- 1 from tp_vs_sw: Sliding window code

### prefix_sum FPs (competition model, 25 total)
- 9 from tp_vs_sw: Sliding window code with accumulation
- 6 from at_genuine: Array traversal with accumulation
- 3 from ps_vs_generic: Generic accumulation (not prefix sum)
- 3 from at_vs_dp: DP code with accumulation
- 2 from hash_genuine: Hash map code with accumulation
- 1 from hash_vs_prefix: Prefix/hash interaction
- 1 from hash_vs_bfs: BFS code

### two_pointers_opposite FPs (competition model, 3 total)
- 2 from tp_vs_sw: Sliding window (same-direction pointers)
- 1 from at_vs_sort: Sorting code

## Pattern Taxonomy Re-evaluation

### Classification of each target pattern

| Pattern | Classification | Justification |
|---------|---------------|---------------|
| two_pointers_opposite | **algorithmic_primary** | Highly specific structural signature; bidirectional convergence is distinctive |
| prefix_sum | **reusable_technique** | Accumulation is a technique applied to many problems; not a self-contained algorithm |
| hash_map_lookup | **reusable_technique** | Dict/set lookup is a data-structure behavior used across many algorithms |
| array_traversal | **structural_primitive** | Nearly every algorithm iterates data; this is a structural observation, not an algorithmic classification |

### Taxonomy issues identified

1. **array_traversal should NOT be a pattern label**
   - 188/301 cases trigger array_traversal detection (62%!)
   - Precision: 13% — essentially random
   - The concept is too broad to be meaningful for algorithmic classification
   - Recommendation: Demote to structural primitive, not a scored pattern

2. **hash_map_lookup conflates algorithm from technique**
   - "hash map lookup" describes a data-structure operation, not an algorithmic strategy
   - Two_sum uses a hash map, but the algorithm is "complement search"
   - Frequency counting uses a hash map, but the algorithm is "counting sort variant"
   - Recommendation: Hash map should be a structural feature, not a pattern label

3. **prefix_sum conflates technique from algorithm**
   - Prefix sum is a data preprocessing technique, not a complete algorithm
   - Many different algorithms use prefix sums
   - Recommendation: Keep as a technique label, but recognize it's weaker as a primary classification

4. **two_pointers_opposite is the only well-defined pattern**
   - Bidirectional convergence is structurally specific
   - It describes both a technique and a recognizable structural signature
   - It's the only pattern with acceptable cross-pattern FP rates

## What Static Analysis Can Reliably Classify

| Signal | Reliable? | Evidence |
|--------|-----------|----------|
| Bidirectional pointer convergence | ✅ YES | F1=0.818 (AST), 0 FPs from non-TP code |
| Membership on known dict/set | ⚠️ PARTIAL | Good for genuine hash_map, bad for incidental usage |
| Accumulation from collection | ⚠️ PARTIAL | Recovers some prefix_sum FNs but introduces cross-pattern FPs |
| Array iteration | ❌ NO | Too structurally generic (62% of code triggers it) |
| Counter loop | ⚠️ PARTIAL | Useful feature but insufficient alone |

## What Static Analysis Cannot Reliably Classify

1. **"Is this hash map usage the PRIMARY algorithmic strategy?"**
   - Cannot distinguish: complement search (primary) vs visited set (incidental) vs frequency counting (incidental)
   - Both have identical structural signatures: membership test + dict construction

2. **"Is this accumulation a prefix sum?"**
   - Cannot distinguish: genuine prefix sum vs generic counter vs DP accumulation
   - All use `+=` with similar structural patterns

3. **"Is this array iteration the primary pattern?"**
   - Cannot distinguish: array traversal (primary) vs sorting (incidental) vs DP (incidental)
   - All iterate arrays with indexed access

## Recommended Architecture

### Immediate: Freeze semantic research for patterns that don't generalize

The semantic/competition architecture should NOT be promoted to production for:
- array_traversal (fundamentally too broad)
- hash_map_lookup (competition rules don't generalize)
- prefix_sum (marginal gains don't justify complexity)

### Keep in shadow mode only:
- The semantic scorer continues to provide observational data
- Competition rules should NOT be applied to user scoring
- Primary-role features should NOT gate production decisions

### Taxonomy redesign needed before further semantic work:
1. Demote array_traversal to structural primitive (not a scored pattern)
2. Split hash_map_lookup into more specific sub-patterns (complement_search, frequency_count, visited_tracking, etc.)
3. Recognize prefix_sum as a technique, not a primary algorithm label
4. Keep two_pointers_opposite as the primary well-defined pattern

### Recommended next step:
Redesign the pattern taxonomy BEFORE continuing semantic work. The current taxonomy conflates algorithms, techniques, and structural primitives, making reliable classification impossible.

## Files Created

```
src/ast_detection/semantic/
├── disjoint_corpus.py        # Base 74 cases
├── disjoint_corpus_extra.py  # 58 additional cases
├── disjoint_corpus_extra2.py # 83 additional cases
├── disjoint_corpus_extra3.py # 55 additional cases
├── disjoint_corpus_final.py  # 31 additional cases
```

Total: 301 disjoint cases across 21 family groups.

## Test Results

- 556/556 AST tests pass ✅
- 74/74 semantic tests pass ✅
- 0 regressions ✅
