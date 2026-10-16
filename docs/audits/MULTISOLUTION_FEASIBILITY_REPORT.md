# MULTI-SOLUTION GROUND TRUTH FEASIBILITY REPORT

Date: August 20, 2026
Model: openai/gpt-4o-mini via OpenRouter (free tier)
Temperature: 0.1
Trials per problem: 3
Corpus: 14 problems across 5 categories

---

## EXECUTIVE SUMMARY

**Conclusion: Usable only as a candidate generator.**

The free gpt-4o-mini model improves strategy recall when explicitly asked
to identify multiple solution groups (76.2% vs 59.5%), but introduces
significant hallucination (46 vs 8 patterns), loses consistency across
runs (50% vs 85.7%), and sometimes produces non-canonical pattern names.

The model cannot be the sole generator of ground truth without
deterministic validation constraints. It is a useful candidate generator
that must be filtered, validated, and potentially human-reviewed for
edge cases.

---

## 1. PIPELINE INSPECTION

### Current flow

1. LLM prompt: "identify the algorithmic patterns required to solve it"
2. Model: gpt-4o-mini, temperature 0.1, max_tokens 500
3. Response: {"patterns": [...], "confidence": {...}}
4. _normalize_patterns: filters to ALL_PATTERNS (33 canonical names)
5. _store_ground_truth: flat JSON array in problem_ground_truth
6. _load_ground_truth: wraps ALL patterns into single group_0
7. MatchingEngine: receives one AND group

### Key limitation

The prompt asks for "patterns required to solve it" (singular strategy).
The response format is a flat list. There is no instruction to identify
alternative approaches. The system assumes one optimal strategy.

---

## 2. EXPERIMENTAL RESULTS

### 2a. Aggregate metrics

| Metric | Prompt A (flat) | Prompt B (multi-group) | Change |
|--------|----------------|----------------------|--------|
| Strategy recall | 59.5% | 76.2% | +16.7pp |
| Hallucinated patterns | 8 | 46 | +475% |
| Taxonomy violations | 0 | 6 | +6 |
| Correct group structure | 14/42 (33%) | 24/42 (57%) | +24pp |
| Consistent across trials | 36/42 (86%) | 21/42 (50%) | -36pp |
| Parse success | 42/42 (100%) | 42/42 (100%) | 0 |

### 2b. Strategy recall by category

| Category | Prompt A | Prompt B | Improvement |
|----------|----------|----------|-------------|
| Single approach (control) | 50.0% | 50.0% | 0 |
| Two distinct approaches | 47.2% | 80.6% | +33.4pp |
| Three+ approaches | 75.0% | 100.0% | +25.0pp |
| Same pattern, different impl | 100.0% | 83.3% | -16.7pp |
| Different patterns | 50.0% | 58.3% | +8.3pp |

**Key finding**: Prompt B significantly improves recall for problems with
truly distinct approaches (two_approaches: +33pp, three_plus: +25pp).
It slightly hurts recall for same-pattern-different-implementation problems
because it over-separates implementations that belong to the same pattern.

### 2c. Problem-by-problem analysis

**Problems where Prompt B excels:**
- binary_tree_level_order: 50% -> 100% (correctly identifies BFS and DFS)
- clone_graph: 50% -> 100% (correctly identifies DFS and BFS with hashmap)
- number_of_islands: 50% -> 100% (correctly identifies DFS and BFS)
- course_schedule: 50% -> 100% (correctly identifies toposort and DFS)
- climbing_stairs: 50% -> 100% (correctly identifies DP and fibonacci)

**Problems where Prompt B fails:**
- valid_parentheses: 0% -> 0% (returns "stack" which is not canonical)
- word_ladder: 50% -> 0% (returns bfs_level_order instead of bfs_shortest_path)
- max_subarray: 50% -> 50% (misses greedy_local, adds dp_1d_sequence)
- meeting_rooms_ii: 0% -> 50% (returns greedy_interval instead of expected patterns)

**Problems where Prompt B hallucinates:**
- two_sum: adds two_pointers_opposite (not a distinct approach)
- combination_sum: adds dp_1d_forward (not a valid approach for this problem)
- reverse_linked_list: adds dfs_recursive (not a distinct approach)
- valid_anagram: adds sorting (O(n log n), not optimal)

---

## 3. FAILURE MODE ANALYSIS

### 3a. Taxonomy violations (6 total)

The model returns pattern names not in the canonical list:
- "stack" (3 times) - should be "monotonic_stack"
- "sorting" (3 times) - not in taxonomy at all

**Root cause**: The model knows general algorithmic concepts but sometimes
doesn't map them to PathForge's specific taxonomy.

**Impact**: These would be silently dropped by _normalize_patterns().
Not harmful but indicates incomplete taxonomy awareness.

### 3b. Hallucinated strategies (46 total)

The model invents approaches that are either:
1. Not actually distinct from existing approaches (e.g., adding
   two_pointers_opposite to two_sum when hash_map_lookup already covers it)
2. Not actually valid (e.g., adding dp_1d_forward to combination_sum)
3. Suboptimal (e.g., adding sorting to valid_anagram when O(n) exists)

**Root cause**: The model is prompted to "identify ALL distinct optimal
approaches" and over-generates to be thorough.

**Impact**: Inflates ground truth with incorrect patterns. If stored,
this would cause false negatives (user uses correct approach but ground
truth requires additional patterns).

### 3c. Inconsistent group structure (50% consistency)

Across 3 trials with temperature 0.1:
- Some problems produce different group structures each run
- clone_graph: sometimes 2 groups, sometimes 3
- reverse_linked_list: sometimes 1 group, sometimes 3
- number_of_islands: sometimes 2 groups, sometimes 3

**Root cause**: The model's grouping decisions are not deterministic
even at low temperature.

**Impact**: Ground truth would differ between runs. If cached after
first run, subsequent runs might produce different results.

### 3d. Merged vs split approaches

The model sometimes:
- Merges distinct approaches into one group (e.g., course_schedule puts
  toposort and DFS in separate groups with toposort in both)
- Splits a single approach into multiple groups (e.g., reverse_linked_list
  creates 3 groups for what is one pattern)

**Root cause**: The model doesn't have a clear mental model of what
constitutes a "distinct approach" vs "variant of the same approach."

**Impact**: Incorrect group structure leads to incorrect matching.

---

## 4. COMPARISON: PROMPT A vs PROMPT B

### Where Prompt A is better

| Aspect | Prompt A | Prompt B |
|--------|----------|----------|
| Consistency | 86% | 50% |
| Hallucination | 8 | 46 |
| Taxonomy compliance | 100% | 86% |
| Simplicity | Simple flat list | Complex group structure |

### Where Prompt B is better

| Aspect | Prompt A | Prompt B |
|--------|----------|----------|
| Multi-approach recall | 47% | 81% |
| Three+ approach recall | 75% | 100% |
| Group structure | N/A (always 1 group) | 57% correct |

### Net assessment

Prompt B is better for problems with multiple distinct approaches but
worse for consistency and hallucination. The tradeoff is:
- +16.7pp strategy recall
- +475% hallucination
- -36pp consistency

This tradeoff is NOT acceptable for direct use without validation.

---

## 5. DETERMINISTIC VALIDATION CONSTRAINTS

If Prompt B is used as a candidate generator, the following validation
constraints would be needed:

### 5a. Pattern name validation

Filter all patterns against ALL_PATTERNS (already exists in
_normalize_patterns). This catches "stack" and "sorting" violations.

### 5b. Group structure validation

- Require at least 1 group
- Require at most 5 groups (practical limit)
- Require at least 1 pattern per group
- Reject groups with duplicate patterns

### 5c. Cross-group deduplication

If the same pattern appears in multiple groups, it likely means the
model didn't understand the OR semantics. Consolidate into one group.

### 5d. Confidence threshold

Require minimum confidence (e.g., 0.5) for each pattern. Low-confidence
patterns are likely hallucinated.

### 5e. Stability check

Run the LLM 3 times and only accept results that are consistent across
at least 2/3 runs. Inconsistent results go to human review.

### 5f. Estimated validation effectiveness

| Validation | Catches | Misses |
|-----------|---------|--------|
| Pattern name filter | Taxonomy violations (6) | None |
| Group structure check | Malformed groups | None |
| Cross-group dedup | Merged approaches | Split approaches |
| Confidence threshold | Low-confidence hallucinations | High-confidence hallucinations |
| Stability check | Nondeterministic results | Consistent hallucinations |

**Estimated post-validation accuracy**: ~70-80% of ground truth would
be correct after all validations. The remaining 20-30% would need
human review or deterministic AST validation.

---

## 6. ARCHITECTURAL DECISION

### Is the free model reliable enough?

**Option A: Reliable enough for direct use.**
NO. Too much hallucination (46 patterns), too low consistency (50%),
and taxonomy violations.

**Option B: Usable with deterministic validation constraints.**
PARTIALLY. Validation can catch taxonomy violations and malformed
structures, but cannot verify whether a strategy is actually valid
or distinct. Estimated 70-80% post-validation accuracy.

**Option C: Usable only as a candidate generator.**
YES. This is the correct answer. The model generates candidate
ground truth that must be validated by:
1. Deterministic filters (pattern names, group structure)
2. AST-based validation (does the pattern actually match known implementations?)
3. Optional human review for edge cases

**Option D: Not reliable enough.**
NO. The model is useful as a starting point. It correctly identifies
the dominant approach in most cases and sometimes identifies secondary
approaches. The failure modes are predictable and filterable.

### Recommended architecture

```
Problem description
    |
    v
LLM generates candidate solution groups (Prompt B)
    |
    v
Deterministic validation:
    - Pattern name filtering
    - Group structure validation
    - Cross-group deduplication
    - Confidence threshold
    |
    v
Stability check (3 runs, accept consistent results)
    |
    v
Candidate ground truth (marked as "unvalidated")
    |
    v
Optional: AST validation against reference implementations
    |
    v
Activated ground truth (marked as "validated")
```

### What this means for PathForge

1. The LLM should use Prompt B (multi-solution) instead of Prompt A
2. Results must go through deterministic validation before storage
3. Ground truth should have a validation_status field
4. The MatchingEngine already supports multi-group OR (no changes needed)
5. The database needs a solution_groups column (schema change)
6. The LLM should be re-run when confidence is low or results are inconsistent

---

## 7. RISKS AND LIMITATIONS

### 7a. Corpus size

Only 14 problems were tested. A larger corpus (50-100 problems) would
give more reliable statistics. However, the failure modes observed are
structural (hallucination, inconsistency, taxonomy violations) and are
unlikely to disappear with more data.

### 7b. Model version

gpt-4o-mini is the current free model. Future model changes could
improve or degrade performance. The evaluation should be re-run when
the model changes.

### 7c. Temperature sensitivity

Temperature 0.1 was used. Higher temperature might improve recall but
worsen consistency. Lower temperature might improve consistency but
worsen recall. This tradeoff should be explored.

### 7d. Prompt engineering

The prompts used are basic. More sophisticated prompts (e.g., few-shot
examples, chain-of-thought reasoning) might improve performance. This
was not explored.

### 7e. Taxonomy completeness

Some expected patterns (e.g., "bidirectional_search") are not in the
canonical taxonomy. The model cannot return patterns that don't exist.
This is a taxonomy limitation, not a model limitation.

---

## 8. FINAL ANSWER

**The currently available free OpenRouter model (gpt-4o-mini) is usable
only as a candidate generator for multi-solution ground truth.**

It cannot be the sole generator without deterministic validation.
The model correctly identifies multiple approaches in ~76% of cases
but introduces significant hallucination and inconsistency.

**Recommended next steps:**
1. Continue Phase 2 AST improvements (separate track)
2. When ready for ground truth changes:
   a. Modify prompt to Prompt B (multi-solution)
   b. Add solution_groups column to database
   c. Implement deterministic validation filters
   d. Add validation_status field to ground truth
   e. Run stability check (3 trials, accept consistent)
   f. Test on 50-problem corpus before production deployment

---

*End of Feasibility Report*
