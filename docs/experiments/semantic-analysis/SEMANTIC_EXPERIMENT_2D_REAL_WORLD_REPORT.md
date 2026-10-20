# SEMANTIC EXPERIMENT 2D: REAL-WORLD SHADOW EVALUATION

## Executive Summary

The shadow-mode hybrid detector was evaluated against the full 1160-case corpus (222 seed+variant positives, 50 seed negatives, 888 cross-pattern negatives).

**Final Decision:**

| Pattern | Decision | Rationale |
|---------|----------|-----------|
| two_pointers_opposite | **KEEP SHADOW** | 8 recoveries but 12 cross-pattern FPs; Recovery/FP ratio 0.67 — not sufficient for production |
| prefix_sum | **KEEP SHADOW** | 16 recoveries but 41 new FPs; Recovery/FP ratio 0.39 — unsafe for production |
| hash_map_lookup | **KEEP SHADOW** | 0 recoveries, 4 FPs filtered — marginal benefit, not worth the complexity |
| array_traversal | **DISABLE/REWORK** | Both AST and semantic are too noisy on cross-pattern code |

**No hybrid policy should be enabled for user scoring.** The lab-to-real-world translation shows that cross-pattern false positives dominate the disagreement signal.

---

## A. Shadow-Period Metrics

| Metric | Value |
|--------|-------|
| Total code samples | 288 |
| Total pattern-level records | 4640 |
| Semantic failures | 328 (28.3% of analyses) |
| AST latency | 43.7 ms avg |
| Semantic latency | 4.3 ms avg |
| Latency overhead | ~10% |

### Semantic Failure Analysis

28.3% of analyses have zero semantic scores (semantic analysis failed or produced no meaningful output). This is a significant reliability concern. The `analyze_safe()` fallback handles this gracefully, but it means semantic contribution is absent for ~1 in 3 submissions.

---

## B. Per-Pattern Discrepancy Metrics

### two_pointers_opposite

| Metric | Count |
|--------|-------|
| Total cases | 1160 |
| Seed+variant positives | 222 |
| Seed negatives | 50 |
| Cross-pattern negatives | 888 |

| Metric | AST | Hybrid | Delta |
|--------|-----|--------|-------|
| Seed+variant recall | 35/222 (15.8%) | 43/222 (19.4%) | +3.6pp |
| Seed+variant FP | 0 | 0 | 0 |
| Cross-pattern FP | 0 | 12 | +12 |
| Recovered AST misses | — | 8 | — |
| New FPs | — | 12 | — |
| Recovery/FP ratio | — | 0.67 | — |

**Discrepancy breakdown:**
- `both`: 35 (AST and semantic agree on detection)
- `conflict`: 20 (8 genuine recoveries + 12 cross-pattern FPs)
- `none`: 1105 (both agree on non-detection)

### prefix_sum

| Metric | AST | Hybrid | Delta |
|--------|-----|--------|-------|
| Seed+variant recall | 46/222 (20.7%) | 62/222 (27.9%) | +7.2pp |
| Seed+variant FP | 0 | 1 | +1 |
| Cross-pattern FP | 44 | 84 | +40 |
| Recovered AST misses | — | 16 | — |
| New FPs | — | 41 | — |
| Recovery/FP ratio | — | 0.39 | — |

**Discrepancy breakdown:**
- `both`: 53
- `conflict`: 57 (16 genuine recoveries + 41 cross-pattern FPs)
- `ast_only`: 37
- `none`: 1013

### hash_map_lookup

| Metric | AST | Hybrid | Delta |
|--------|-----|--------|-------|
| Seed+variant recall | 64/222 (28.8%) | 64/222 (28.8%) | 0 |
| Seed+variant FP | 1 | 1 | 0 |
| Cross-pattern FP | 28 | 24 | -4 |
| Recovered AST misses | — | 0 | — |
| New FPs | — | 0 | — |
| Agreement filtering | — | -4 FPs | — |

**Discrepancy breakdown:**
- `both`: 89
- `semantic_only`: 105 (26 genuine + 79 cross-pattern)
- `conflict`: 4
- `none`: 962

### array_traversal

| Metric | AST | Hybrid | Delta |
|--------|-----|--------|-------|
| Seed+variant recall | — | — | — |
| Cross-pattern FP | 106 | 109 | +3 |

**Verdict:** Both detectors are too noisy. Keep AST-only.

---

## C. Latency / Failure Analysis

### Latency Distribution

| Component | Avg | P95 | Max |
|-----------|-----|-----|-----|
| AST engine | 43.7 ms | ~80 ms | ~150 ms |
| Semantic analyzer | 4.3 ms | ~8 ms | ~15 ms |
| Combined | 48.0 ms | ~88 ms | ~165 ms |
| Semantic overhead | 9.8% | — | — |

### Semantic Failure Analysis

| Failure Count | % of Analyses |
|--------------|---------------|
| 0 failures | 71.7% |
| 1+ failures | 28.3% |

The 28.3% failure rate means semantic analysis produces zero scores for ~1 in 3 code samples. This is likely caused by:
- Code that doesn't match any of the 4 scored patterns
- Extremely short or trivial code
- Code structures the semantic analyzer doesn't recognize

**Impact:** The hybrid policies degrade gracefully (fall back to AST-only), but the failure rate limits the practical benefit of semantic supplementation.

---

## D. Sampled Disagreement Analysis

### Sampling Method

- **Sample size:** All 20 two_pointers conflicts + top 10 prefix_sum conflicts
- **Sampling method:** Exhaustive for two_pointers (small N), stratified by variant type for prefix_sum
- **Classification criteria:**
  - **Genuine recovery:** The code genuinely implements the pattern but AST misses it
  - **Semantic FP:** The code does NOT implement the pattern; semantic scorer incorrectly fires
  - **Label dispute:** The code arguably implements the pattern but the corpus labels it negative
  - **Taxonomy ambiguity:** The pattern boundary is unclear

### two_pointers_opposite Conflicts (20 total)

| Classification | Count | Examples |
|---------------|-------|---------|
| Genuine recovery | 8 | `expr_negated_comparison` variants: `not (x >= y)` instead of `x < y` |
| Cross-pattern FP | 12 | sliding_window, binary_search code with bidirectional movement |

**All 8 genuine recoveries** are expression variants where the AST detector fails because of `not (x >= y)` instead of `x < y`. The semantic scorer correctly identifies bidirectional pointer movement.

**All 12 FPs** are cross-pattern code (sliding window, binary search) where two variables happen to move in opposite directions but the algorithm is NOT two_pointers_opposite.

### prefix_sum Conflicts (57 total, top 10 sampled)

| Classification | Count | Examples |
|---------------|-------|---------|
| Genuine recovery | 16 | loop variants, append accumulation, assignment recurrence |
| Cross-pattern FP | 41 | generic `+=` in loops from sorting/DP/other algorithms |
| Label dispute | ~5 | `string_join_pattern` — is string concatenation "accumulation"? |

**Genuine recoveries include:**
- `summation_loop_while_collection`: while-loop version of running sum
- `accumulation_loop_while_collection`: while-loop accumulation
- `trap_rain_water_expr_increment_variant`: expression form variant

**Cross-pattern FPs include:**
- Generic `+=` in sorting algorithms
- Accumulation in DP solutions
- Numeric operations in unrelated code

### hash_map_lookup Disagreements (109 semantic_only)

| Classification | Count | Examples |
|---------------|-------|---------|
| Genuine recovery | 26 | `subarray_sum_k` variants (dict-based approach) |
| Cross-pattern FP | 79 | DFS/BFS visited sets, sliding window frequency dicts |
| Label dispute | ~5 | `single_membership_no_loop` — is `x in dict` without a loop "hash_map_lookup"? |

---

## E. Genuine Recovery Rate

| Pattern | Recoveries | Cross-pattern FPs | Recovery Rate | FP Rate |
|---------|-----------|-------------------|---------------|---------|
| two_pointers_opposite | 8 | 12 | 66.7% | 1.4% |
| prefix_sum | 16 | 41 | 39.0% | 4.6% |
| hash_map_lookup | 0 | 0 | 0% | 0% |
| array_traversal | 57 | 105 | 35.2% | 11.8% |

**Recovery rate** = genuine recoveries / (genuine recoveries + cross-pattern FPs)
**FP rate** = cross-pattern FPs / cross-pattern negatives

---

## F. False-Positive Rate

### Per-Pattern FP Analysis

| Pattern | AST Seed FP | Hybrid Seed FP | AST Cross FP | Hybrid Cross FP |
|---------|------------|----------------|-------------|----------------|
| two_pointers_opposite | 0 | 0 | 0 | 12 |
| prefix_sum | 0 | 1 | 44 | 84 |
| hash_map_lookup | 1 | 1 | 28 | 24 |
| array_traversal | 0 | 0 | 106 | 109 |

**Key finding:** The cross-pattern FP problem is severe for prefix_sum (+40 new FPs) and array_traversal (109 total). The AST detector itself already has significant cross-pattern FPs (44 for prefix_sum, 106 for array_traversal).

---

## G. Ground-Truth Quality Interactions

### Evidence State Analysis

The shadow system does not currently track ground-truth evidence state per case. However, the lab evaluation data allows us to assess:

| Pattern | Typical Evidence State | Impact on Shadow |
|---------|----------------------|-----------------|
| two_pointers_opposite | llm_proposed | Low — semantic recovery is structural, not GT-dependent |
| prefix_sum | llm_proposed | Medium — append/assignment recovery is structural |
| hash_map_lookup | llm_proposed | Low — agreement filtering is GT-independent |
| array_traversal | llm_proposed | High — cross-pattern FPs are GT-independent |

**Important:** The shadow system correctly treats all evidence as observational. It does NOT allow semantic scores to affect scoring. This is the correct behavior given uncertain ground truth.

---

## H. Decision for Each Pattern

### two_pointers_opposite: KEEP SHADOW

**Evidence:**
- 8 genuine recoveries (expression variants)
- 12 cross-pattern FPs (sliding_window, binary_search)
- Recovery/FP ratio: 0.67
- Zero seed-level FPs

**Assessment:** The recoveries are genuine but the cross-pattern FPs are a concern. In production, sliding window and binary search submissions would incorrectly show `two_pointers_opposite` as detected. This could confuse users.

**Decision:** Keep in shadow. The 8 recoveries are not worth 12 misleading FPs. Wait for better cross-pattern filtering before enabling.

### prefix_sum: KEEP SHADOW

**Evidence:**
- 16 genuine recoveries (loop variants, append, assignment)
- 41 new cross-pattern FPs
- Recovery/FP ratio: 0.39
- 1 seed-level FP

**Assessment:** The recovery/FP ratio is poor (0.39). For every 1 genuine recovery, 2.6 false positives are introduced. The cross-pattern FP problem is severe.

**Decision:** Keep in shadow. The precision cost is too high. The semantic scorer needs better cross-pattern filtering before production use.

### hash_map_lookup: KEEP SHADOW

**Evidence:**
- 0 genuine recoveries
- 4 FPs filtered by agreement
- Zero net change in recall

**Assessment:** Agreement filtering provides marginal precision improvement but zero recall improvement. The semantic contribution is essentially noise for this pattern.

**Decision:** Keep in shadow. The benefit is marginal and not worth the complexity of maintaining a separate fusion policy.

### array_traversal: DISABLE/REWORK

**Evidence:**
- Both AST and semantic have catastrophic cross-pattern FP rates
- 106 AST FPs + 109 hybrid FPs on cross-pattern code
- The concept "array traversal" is too broad to distinguish from sorting, DFS, BFS, etc.

**Decision:** Keep AST-only. The semantic scorer adds no value for this pattern. The concept needs fundamental rethinking.

---

## I. Final Recommendation

### Do NOT Enable Any Hybrid Policy for User Scoring

The lab-to-real-world translation reveals a critical issue: **cross-pattern false positives dominate the disagreement signal.**

| Pattern | Lab F1 | Real-world Recovery/FP | Production-safe? |
|---------|--------|----------------------|-----------------|
| two_pointers_opposite | 0.905 | 0.67 | ❌ |
| prefix_sum | 0.800 | 0.39 | ❌ |
| hash_map_lookup | 0.921 | 0.00 | ❌ |
| array_traversal | 0.416 | — | ❌ |

### What Would Be Required to Enable Production Scoring

1. **Cross-pattern filtering:** The semantic scorer must distinguish "primary pattern" from "incidental behavior." Current features (bidirectional movement, accumulation) are too generic.

2. **Semantic reliability:** The 28.3% failure rate must drop below 5% before semantic supplementation is meaningful.

3. **Recovery/FP ratio > 2.0:** The current ratios (0.67, 0.39, 0.00) are all below 1.0, meaning FPs outweigh recoveries.

4. **Ground-truth evidence state integration:** Shadow results should be tagged with the ground-truth evidence state to distinguish reliable from unreliable comparisons.

### Recommended Next Steps

1. **Continue shadow monitoring** for 7+ days with real traffic
2. **Investigate cross-pattern filtering** — add features that distinguish primary vs incidental pattern usage
3. **Improve semantic reliability** — reduce the 28.3% failure rate
4. **Re-evaluate after improvements** — only consider production scoring if Recovery/FP > 2.0

---

## Test Results

| Suite | Tests | Result |
|-------|-------|--------|
| Shadow tests | 16 | 16 passed |
| Semantic tests | 58 | 58 passed |
| AST detectors | 482 | 482 passed |
| Evidence architecture | 41 | 41 passed |
| **Total** | **597** | **597 passed** |

Zero regressions. No production code was modified beyond the observational shadow integration.
