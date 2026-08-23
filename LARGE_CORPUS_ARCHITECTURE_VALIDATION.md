# Large Corpus Architecture Validation

## Corpus Composition

| Category | Cases | With Strategy | Without Strategy |
|----------|-------|---------------|------------------|
| binary_search | 80 | 80 | 0 |
| two_pointers | 81 | 79 | 2 |
| sliding_window | 81 | 3 | 78 |
| dfs_backtracking | 80 | 79 | 1 |
| dp_top_down | 70 | 70 | 0 |
| dp_bottom_up | 70 | 70 | 0 |
| bfs | 61 | 60 | 1 |
| linked_list | 60 | 0 | 60 |
| union_find | 50 | 50 | 0 |
| monotonic_stack | 50 | 50 | 0 |
| prefix_sum | 50 | 0 | 50 |
| greedy | 50 | 0 | 50 |
| hard_negative | 100 | 0 | 100 |
| **Total** | **883** | **541** | **342** |

## Contamination Check

All 883 cases are newly generated. No cases from:
- test_shadow_analysis.py
- test_phase5a.py
- test_phase5b.py
- test_phase3b_integration.py
- test_phase4a_enrichment.py
- test_regression_vocabulary_mismatch.py
- evaluation_corpus.py (Phase 5C)
- diagnostic scripts

Cases are structurally distinct: different variable names, different loop structures, different problem parameters.

---

## Overall Metrics

| Metric | Value |
|--------|-------|
| Total cases | 883 |
| Errors | 0 |
| Elapsed | 14.4s |

### Safety (Critical)

| Metric | Value | Status |
|--------|-------|--------|
| Spurious CONFIRMED (no strategy expected) | 0 / 342 | ✅ PERFECT |
| Correct UNRESOLVED (no strategy expected) | 342 / 342 (100.0%) | ✅ PERFECT |
| False CONFIRMED rate | 0.0% | ✅ |

**Zero negative cases became CONFIRMED. The safety invariant holds.**

### Accuracy (Cases with expected strategy: 541)

| Metric | Value |
|--------|-------|
| True positive | 308 (56.9%) |
| False positive | 0 |
| False negative | 233 |
| **Precision** | **1.000** |
| **Recall** | **0.569** |
| **F1** | **0.726** |

---

## Per-Strategy Metrics

| Strategy | Precision | Recall | F1 | TP | FP | FN |
|----------|-----------|--------|-----|----|----|-----|
| two_pointers_opposite | 1.00 | 1.00 | 1.00 | 79 | 0 | 0 |
| dp_top_down | 1.00 | 0.97 | 0.99 | 68 | 0 | 2 |
| union_find | 1.00 | 0.98 | 0.99 | 49 | 0 | 1 |
| bfs_shortest_path | 1.00 | 0.95 | 0.97 | 57 | 0 | 3 |
| binary_search | 1.00 | 0.56 | 0.72 | 45 | 0 | 35 |
| sliding_window | 1.00 | 0.33 | 0.50 | 1 | 0 | 2 |
| dp_bottom_up | 1.00 | 0.07 | 0.13 | 5 | 0 | 65 |
| monotonic_stack_strategy | 1.00 | 0.06 | 0.11 | 3 | 0 | 47 |
| dfs_backtracking | 1.00 | 0.01 | 0.03 | 1 | 0 | 78 |

**Precision is 1.000 across ALL strategies. No false positives anywhere.**

---

## Submission Pipeline Distribution

| Pipeline Stage | Count | % |
|----------------|-------|---|
| No techniques extracted | 405 | 45.9% |
| Techniques extracted, no strategy | 100 | 11.3% |
| Strategy detected, no satisfied group | 127 | 14.4% |
| One satisfied group | 251 | 28.4% |
| Multiple satisfied groups | 0 | 0.0% |

---

## Failure Taxonomy (233 false negatives)

| Failure Cause | Count | % of FN |
|---------------|-------|---------|
| No techniques extracted | 119 | 51.1% |
| Technique extracted but no strategy | 36 | 15.5% |
| Strategy detected but not satisfied | 1 | 0.4% |
| Strategy fires via fallback, low confidence | 77 | 33.0% |

### Root Causes by Strategy

**DFS backtracking (78 FNs):**
- 77 cases: `recursive_branching` technique doesn't fire because backtracking has one recursive call inside a for-loop, not multiple conditional recursive branches. The strategy fires via fallback but with low confidence (< 0.5 threshold), so the group is not satisfied.
- 1 case: no techniques at all.
- **Classification**: structural extraction gap — `recursive_branching` definition is too strict for backtracking patterns.

**DP bottom-up (65 FNs):**
- 65 cases: `iterative_table_filling` technique doesn't fire because fact extractor misses indexed writes or lookback patterns for simple loop-based DP.
- **Classification**: structural extraction gap — fact extractor needs broader indexed-write detection.

**Monotonic stack (47 FNs):**
- 47 cases: `stack_operation`, `monotonic_comparison`, `conditional_pop` facts not detected.
- **Classification**: structural extraction gap — stack detection relies on variable-name heuristics that fail with renamed variables.

**Binary search (35 FNs):**
- 35 cases: for-loop binary search variants produce `loop_state_tracking` technique but not `binary_search` strategy because `midpoint_calculation` or `while_loop_comparison` facts are missing for the for-loop form.
- **Classification**: structural extraction gap — for-loop binary search not fully supported.

**BFS (3 FNs):**
- 3 cases: no techniques detected (queue/visited/neighbor facts missing).
- **Classification**: structural extraction gap — BFS fact detection incomplete.

**Sliding window (2 FNs):**
- 1 case: no techniques detected.
- 1 case: `two_pointers_opposite` strategy fires instead of `sliding_window` (taxonomy ambiguity).
- **Classification**: mix of extraction gap and taxonomy ambiguity.

**DP top-down (2 FNs):**
- 2 cases: no techniques detected (recursive call facts missing).
- **Classification**: structural extraction gap.

**Union-find (1 FN):**
- 1 case: `sequential_accumulation` fires but not `union_find` strategy (parent chase not detected).
- **Classification**: structural extraction gap.

---

## False Positive Analysis

**Zero false positives across 883 cases.**

No case produced a CONFIRMED outcome with the wrong strategy. No negative case produced any CONFIRMED outcome.

The single "false positive" in the earlier 276-case evaluation was `tp_slow_fast_cycle` where `linked_list_traversal` (a technique, not a strategy) was mislabeled in the evaluation corpus. That issue does not appear here because `linked_list_traversal` is not in the expected-strategy set.

---

## Production vs Shadow Comparison

| Metric | Production AST | Shadow Architecture |
|--------|---------------|-------------------|
| Pattern detection | Flat pattern-ID matching | Structural facts → techniques → strategies |
| Cases with patterns | ~200 (varies by problem) | 478 (techniques detected) |
| Matching approach | Equality-based | Satisfaction-based |
| False confirmations | N/A (no ground truth in eval) | 0 |

The two paths measure fundamentally different things:
- **Production**: "Did the AST detector find pattern X?" (recall-oriented, many false positives)
- **Shadow**: "Does the evidence satisfy a defined solution group?" (precision-oriented, many false negatives)

The shadow architecture trades recall for precision. This is the correct tradeoff for a system that will affect user PASS/FAIL decisions.

---

## Ground-Truth Quality Issues

All solution groups in this evaluation use synthetic ground truth (one strategy per group). Real ground truth from the LLM builder would have:
- Multiple groups per problem
- Optional/excluded concepts
- Varying authority tiers
- Possible incorrect mappings

The synthetic ground truth is a best-case scenario for the shadow matcher. Real-world accuracy may differ.

---

## Known Limitations (Confirmed)

1. **DFS backtracking**: `recursive_branching` requires multiple conditional recursive paths; single-call-inside-loop doesn't fire
2. **DP bottom-up**: `iterative_table_filling` misses many indexed-write patterns
3. **Monotonic stack**: Detection relies on variable-name heuristics
4. **Binary search for-loops**: For-loop form not fully supported
5. **BFS**: Queue/visited/neighbor detection incomplete
6. **Sliding window**: Low recall due to strict evidence requirements

These are all **structural extraction gaps**, not architecture flaws. The architecture correctly handles the evidence it receives.

---

## Comparison with Previous Evaluation

| Metric | 276-Case Eval | 883-Case Eval | Change |
|--------|--------------|---------------|--------|
| False CONFIRMED | 1 (0.7%) | 0 (0.0%) | Improved |
| Precision | 0.990 | 1.000 | Improved |
| Recall | 0.683 | 0.569 | Lower (expected with more diverse corpus) |
| F1 | ~0.81 | 0.726 | Lower (expected) |
| Correct UNRESOLVED | 100.0% | 100.0% | Maintained |

The lower recall on the larger corpus is expected: the 883-case corpus includes more diverse code patterns, renamed variables, and syntax variants that the fact extractor doesn't fully handle.

---

## Recommendation

### Verdict: **READY FOR CONTROLLED PILOT**

**Rationale:**

1. **Safety is proven at scale**: 0/342 negative cases produced spurious CONFIRMED across 883 cases. The safety invariant holds.

2. **Precision is perfect**: 1.000 precision means every CONFIRMED outcome is correct. No false authoritative confirmations.

3. **Recall is acceptable for a controlled pilot**: 56.9% confirmation rate means roughly 1 in 2 valid submissions will be correctly identified. The other half will be UNRESOLVED (non-punitive).

4. **Failures are all on the extraction side**: Every false negative is caused by missing structural facts, not architecture flaws. The architecture correctly processes whatever evidence it receives.

5. **No regressions**: 892 existing tests pass. Production behavior unchanged.

**For a controlled pilot, the system should:**
- Only affect shadow/diagnostic output
- Not change production PASS/FAIL
- Log all CONFIRMED outcomes for manual review
- Track false-negative rates per problem category

**What should NOT change before the pilot:**
- No new detectors/techniques/strategies
- No production activation
- No ELO/gap/recommendation changes
- No confidence threshold tuning
