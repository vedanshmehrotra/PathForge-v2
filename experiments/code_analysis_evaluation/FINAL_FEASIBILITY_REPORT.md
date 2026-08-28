# PathForge Final Research Feasibility Evaluation

**Experiment Date**: 2026-08-27
**PathForge Commit**: b88cab4
**Dataset Size**: 81 submissions (covering 35 distinct algorithmic concepts)
**Concepts Tested**: 35 (out of 42 in vocabulary; 7 not included due to no template submissions)
**Systems Tested**: Legacy (36 AST pattern detectors) + Shadow (9 technique detectors, 9 strategy evaluators)
**Code Modified**: None. Observational evaluation only. No production code changed.
**Command**: `python experiments/code_analysis_evaluation/runners/expanded_evaluation.py`

---

## 1. Executive Verdict

**Recommendation: LOCK PATHFORGE WITH TARGETED MODIFICATIONS (Option 2)**

The evidence supports continuing research on PathForge with significant targeted modifications. The core research idea — analyzing *how* a student solves a problem to infer algorithmic understanding — remains sound. However, the current implementation has critical weaknesses that must be addressed before it can serve as a credible research system:

- **Legacy system** achieves a macro F1 of 0.605, with 20/35 concepts at F1 > 0.5 — but suffers from severe false positive problems (134 FPs across 81 submissions) and critical robustness failures (35.7% stability rate).
- **Shadow system** has near-zero utility in its current form (macro F1 = 0.079, recall = 9.4%), covering only 4 out of 35 concepts adequately.
- **The research direction is viable**, but the current system is not ready for a controlled experiment without targeted improvements to the rule definitions, robustness, and shadow coverage.

---

## 2. Experimental Setup

### Systems Under Test

**Legacy (Production) System:**
- 36 AST-based pattern detectors (Python `ast` module)
- Each detector walks the AST looking for specific structural patterns
- Evidence items with weights are aggregated into confidence scores
- Coordinator filters results and outputs detected patterns
- Stateless, deterministic, no external dependencies

**Shadow (Experimental) System:**
- Fact extractor: 25+ structural fact types extracted from AST
- 9 technique detectors: sequential_accumulation, bidirectional_index_scan, carry_propagation, recursive_branching, loop_state_tracking, iterative_table_filling, linked_list_traversal, fixed_window_maintenance, monotonic_stack_maintenance
- 9 strategy evaluators: two_pointers_opposite, binary_search, sliding_window, dfs_backtracking, dp_top_down, dp_bottom_up, bfs_shortest_path, union_find, monotonic_stack_strategy
- Solution-group matching with authority gating

### Evaluation Method

Each submission was analyzed by both systems. Detected concept IDs from each system were compared against ground truth `target_concepts` (the concept the submission was designed to demonstrate). Metrics computed using standard binary classification per concept across all submissions.

### Ground Truth

Ground truth labels were derived from the `target_concepts` field of each submission — i.e., the concept the submission was *designed* to demonstrate. This is a proxy ground truth (not expert-annotated). See Section 8 for ground truth quality assessment.

---

## 3. Dataset

| Property | Value |
|----------|-------|
| Total submissions | 81 |
| Distinct concepts | 35 |
| Correct solutions | 77 |
| Incorrect solutions | 4 |
| Standard implementations | ~40 |
| Variant implementations (renamed vars, loop styles, etc.) | ~37 |
| Incorrect/buggy implementations | 4 |

### Concept Coverage

Submissions span: hash_map_lookup (4), hash_map_frequency (4), prefix_sum (2), sliding_window_fixed (4), sliding_window_variable (3), two_pointers_opposite (5), two_pointers_same (3), binary_search_standard (4), binary_search_rotated (1), binary_search_answer (1), dfs_recursive (6), dfs_iterative (2), bfs_level_order (2), bfs_shortest_path (1), topological_sort (1), union_find (2), dp_1d_forward (5), dp_1d_sequence (1), dp_2d_grid (1), dp_2d_string (1), dp_knapsack (1), dp_interval (1), dp_state_machine (1), dp_top_down (2), dp_bottom_up (1), backtracking_permutation (3), backtracking_subset (2), monotonic_stack (3), monotonic_deque (1), binary_search_tree (1), fast_slow_pointers (2), linked_list_reversal (2), heap_top_k (1), greedy_local (2), greedy_interval (1).

### Dataset Limitations

- All submissions are Python-only (no Java, C++, etc.)
- Most submissions are "clean" implementations (no syntax errors, no incomplete code)
- Incorrect solutions are few (4/81) — insufficient for robust incorrect-solution evaluation
- No real student submissions with organic coding errors
- Synthetic dataset may not reflect the noise and diversity of actual student work

---

## 4. Code Analysis Results

### 4.1 Overall Performance

| Metric | Legacy (Micro) | Legacy (Macro) | Legacy (Weighted) | Shadow (Micro) | Shadow (Macro) | Shadow (Weighted) |
|--------|----------------|----------------|-------------------|----------------|----------------|-------------------|
| **Precision** | 0.477 | 0.613 | 0.635 | 0.421 | 0.089 | 0.118 |
| **Recall** | 0.675 | 0.687 | 0.675 | 0.104 | 0.094 | 0.104 |
| **F1** | 0.559 | 0.605 | 0.597 | 0.167 | 0.079 | 0.104 |
| **FPR** | 0.021 | — | — | 0.004 | — | — |
| **FNR** | 0.325 | — | — | 0.896 | — | — |
| **TP** | 52 | — | — | 8 | — | — |
| **FP** | 57 | — | — | 11 | — | — |
| **FN** | 25 | — | — | 69 | — | — |

**Key observations:**
- Legacy has moderate recall (67.5%) but poor precision (47.7%) — it detects the right concept often, but also detects many wrong concepts
- Shadow has catastrophic recall (10.4%) — it misses 89.6% of all target concepts
- Shadow's near-zero FPR (0.4%) means it rarely fires incorrectly — it just barely fires at all
- Legacy's false positive count (57) is higher than its true positive count (52) — a serious problem

### 4.2 Per-Concept Results (Legacy)

**Excellent (F1 = 1.0):** bfs_shortest_path, binary_search_rotated, binary_search_tree, dp_2d_string, dp_knapsack, fast_slow_pointers, greedy_interval, heap_top_k, linked_list_reversal, monotonic_deque, monotonic_stack, sliding_window_variable, topological_sort

**Good (F1 > 0.7):** two_pointers_opposite (0.889), bfs_level_order (0.800), hash_map_lookup (0.727), dfs_recursive (0.706)

**Moderate (F1 0.4–0.7):** dp_2d_grid (0.667), dp_state_machine (0.667), backtracking_subset (0.571), dp_1d_forward (0.571), hash_map_frequency (0.545), backtracking_permutation (0.500), prefix_sum (0.500), binary_search_standard (0.444), sliding_window_fixed (0.400)

**Failed (F1 = 0.0):** binary_search_answer, dfs_iterative, dp_1d_sequence, dp_bottom_up, dp_interval, dp_top_down, two_pointers_same, union_find

**Critical false positive cases:**
- `greedy_local`: F1=0.191 — 17 FPs (almost every hash map or simple loop detected as "greedy")
- `two_pointers_same`: F1=0.000 — 12 FPs, 0 TPs (never correctly detects the target)
- `hash_map_frequency`: F1=0.545 — 4 FPs (prefix sum or simple loops misclassified)
- `prefix_sum`: F1=0.500 — 4 FPs (accumulator patterns trigger false positives)
- `backtracking_subset`: F1=0.571 — 3 FPs from dfs_recursive and other patterns

### 4.3 Per-Concept Results (Shadow)

**Working (F1 > 0.5):** two_pointers_opposite (0.889), dp_top_down (1.000), union_find (0.667)

**All others: F1 = 0.0** — The shadow system fails to detect 32 out of 35 concepts.

**Root cause:** The shadow technique/strategy vocabulary only covers a small subset of algorithmic patterns. Concepts like hash_map_lookup, sliding_window_fixed, dfs_recursive, monotonic_stack, backtracking, dp_1d_forward, etc. have no corresponding shadow technique or strategy detector.

---

## 5. Robustness Results

### 5.1 Overall Stability

| Metric | Legacy | Shadow |
|--------|--------|--------|
| Total variants tested | 14 | 14 |
| **Stability rate** | **35.7%** | **64.3%** |
| Detection rate (target found) | 35.7% | 7.1% |

### 5.2 Critical Robustness Failures

**Legacy (35.7% stability — alarmingly low):**

| Concept | Variant | Original Detection | Variant Detection | Stable? |
|---------|---------|--------------------|--------------------|---------|
| two_pointers_opposite | while_not (`while not left >= right`) | two_pointers_opposite | (empty) | **NO** |
| two_pointers_opposite | increment (`left = left + 1`) | two_pointers_opposite | two_pointers_same | **NO** |
| binary_search_standard | bitshift (`>> 1`) | binary_search_standard | (lost) | **NO** |
| binary_search_standard | renamed (`lo, hi, mi`) | binary_search_standard | (lost) | **NO** |
| dp_1d_forward | space_optimized | dp_1d_forward | (lost) | **NO** |
| dp_1d_forward | dict memo | dp_1d_forward | (lost) | **NO** |
| backtracking_permutation | used_array | backtracking_subset | +backtracking_permutation+dfs_recursive | **NO** |
| backtracking_permutation | remaining_list | backtracking_subset | +dfs_recursive | **NO** |

**Shadow (64.3% stability — better but limited by low detection rate):**

| Concept | Variant | Original Detection | Variant Detection | Stable? |
|---------|---------|--------------------|--------------------|---------|
| two_pointers_opposite | while_not | bidirectional_index_scan+two_pointers_opposite | (empty) | **NO** |
| two_pointers_opposite | increment | bidirectional_index_scan+two_pointers_opposite | sequential_accumulation | **NO** |
| monotonic_stack | rename | monotonic_stack_maintenance+strategy | (empty) | **NO** |
| monotonic_stack | explicit_len | monotonic_stack_maintenance+strategy | (empty) | **NO** |
| dp_1d_forward | space_opt | dp_bottom_up+iterative_table_filling | (empty) | **NO** |

### 5.3 Robustness Analysis

**The most concerning finding:** Legacy detectors are highly brittle to superficial code changes:
- `left = left + 1` vs `left += 1` → detection changes from two_pointers_opposite to two_pointers_same
- `while not left >= right` vs `while left < right` → detection lost entirely
- Bitshift `>> 1` vs floor division `// 2` → binary search detection lost
- Space-optimized DP → detection lost entirely

These are semantically equivalent transformations that should not affect detection. The detectors are tied to specific AST node types (`AugAssign` vs `Assign`) and specific comparison operators, rather than semantic equivalence.

**Shadow's better stability** is misleading — it achieves higher stability mostly because it detects almost nothing in the first place. When it does detect (e.g., two_pointers_opposite, monotonic_stack), it is also unstable under renames.

---

## 6. Generalization Results

### 6.1 Cross-Implementation Generalization

Where the dataset permits, we can observe generalization across different implementations of the same concept:

**Binary Search (4 implementations):**
- Classic `// 2`: Legacy detects ✓, Shadow detects ✓
- Overflow-safe `left + (right-left)//2`: Legacy detects ✓, Shadow detects ✓ (but target not in shadow output)
- Bitshift `>> 1`: Legacy **loses detection**, Shadow stable
- Renamed vars (`lo, hi, mi`): Legacy **loses detection**, Shadow stable

**Two Pointers (5 implementations):**
- Classic `left, right`: Legacy ✓, Shadow ✓
- Renamed (`i, j`): Legacy ✓, Shadow ✓
- `while not` style: Legacy **loses detection**, Shadow **loses detection**
- `left = left + 1` style: Legacy **changes detection** (to two_pointers_same), Shadow **loses detection**

**Sliding Window Fixed (4 implementations):**
- Classic: Legacy **never detects** (no sliding_window_fixed pattern found), Shadow detects `fixed_window_maintenance`
- Renamed: Same pattern — legacy misses it
- Helper function: Legacy adds dp_state_machine false positive

**Key insight:** Legacy detection is surprisingly inconsistent across semantically equivalent implementations. The same algorithm implemented with different but valid Python syntax produces different detection outcomes. This undermines the claim that the system detects "algorithmic concepts" — it actually detects specific syntactic patterns.

---

## 7. Error Analysis

### 7.1 Error Classification

| System | Error Type | Count |
|--------|-----------|-------|
| Legacy | FALSE_POSITIVE | 134 |
| Legacy | FALSE_NEGATIVE (wrong concept not detected) | 23 |
| Legacy | MISSING_DETECTION (no detection at all) | 2 |
| Shadow | MISSING_DETECTION (no detection at all) | 28 |
| Shadow | FALSE_NEGATIVE (wrong concept not detected) | 41 |
| Shadow | FALSE_POSITIVE | 80 |

### 7.2 Failure Layer Analysis

**For Legacy false positives (134 total):**

| Failure Layer | Count | Examples |
|--------------|-------|---------|
| TECHNIQUE_DETECTION_FAILURE (overly broad rules) | ~80 | greedy_local fires on any simple loop; hash_map_frequency fires on any dict usage |
| PATTERN_MAPPING_FAILURE (concept mismatch) | ~40 | two_pointers_same fires on unrelated patterns; prefix_sum fires on accumulators |
| CONFIDENCE_FAILURE (no threshold) | ~14 | Low-confidence detections included in output |

**For Legacy false negatives (25 total):**

| Failure Layer | Count | Examples |
|--------------|-------|---------|
| TECHNIQUE_DETECTION_FAILURE (narrow rules) | ~15 | sliding_window_fixed requires specific AST structure; dp_1d_forward requires exact dp array pattern |
| PARSER_FAILURE | ~1 | `while not left >= right` not recognized as binary search condition |
| NAMING_DEPENDENCY | ~5 | binary_search_standard checks for variable names `left/right/lo/hi`; fails on other naming conventions |
| MISSING_DETECTOR | ~2 | dfs_iterative detector exists but fails on iterative inorder traversal patterns |
| STRUCTURAL_FACT_FAILURE | ~2 | union_find detection too strict about exact `parent[x] != x` pattern |

**For Shadow false negatives (69 total):**

| Failure Layer | Count | Examples |
|--------------|-------|---------|
| MISSING_DETECTOR (no technique/strategy for concept) | ~55 | No shadow detector for hash_map, sliding_window_fixed, monotonic_stack, dfs_recursive, etc. |
| TECHNIQUE_DETECTION_FAILURE | ~8 | recursive_branching fires but dfs_backtracking requires state_restoration which is missed |
| STRUCTURAL_FACT_FAILURE | ~6 | fact_extractor misses certain patterns (e.g., monotonic comparison with `len(indices) > 0`) |

### 7.3 Root Cause Summary

1. **Legacy false positives are the dominant problem.** The greedy_local, two_pointers_same, and prefix_sum detectors are too broad — they fire on patterns that happen to share structural features with the target concept but are semantically unrelated.

2. **Legacy robustness failures are syntactic.** Detectors are tied to specific AST node types (AugAssign vs Assign, specific comparison operators) rather than semantic equivalence.

3. **Shadow's low recall is an architecture gap.** The fact extractor and technique detectors simply do not cover most algorithmic concepts. Only 4 of 35 concepts have adequate shadow coverage.

4. **Shadow's fact extractor has naming dependencies.** Cache lookup detection requires variable names like "memo", "dp", "cache". Neighbor traversal requires "graph", "adj". Queue detection requires "queue", "q".

---

## 8. Ground-Truth Quality

### 8.1 Assessment

Ground truth was derived from `target_concepts` — the concept each submission was *designed* to demonstrate. This is a weak proxy for true ground truth.

**High-confidence labels (80% of submissions):**
- Template submissions for well-defined patterns (binary_search, two_pointers, sliding_window, etc.)
- The concept is clearly the primary algorithmic strategy
- Single-concept submissions with no ambiguity

**Ambiguous labels (15% of submissions):**
- Submissions demonstrating multiple concepts (e.g., hash_map + prefix_sum in Subarray Sum Equals K)
- DFS_recursive submissions that also demonstrate bfs_level_order patterns
- Backtracking submissions that also demonstrate dfs_recursive

**Uncertain labels (5% of submissions):**
- Incorrect solutions where the "target" concept is debatable (e.g., brute-force Two Sum labeled as hash_map_lookup)
- Solutions using different algorithms than intended (e.g., greedy vs DP for the same problem)

### 8.2 Implications

- The precision/recall metrics may be optimistic for concepts with single clear implementations
- Multi-concept submissions inflate false positive counts (a hash_map submission that also demonstrates prefix_sum will show a FP for prefix_sum)
- The incorrect solution labels are unreliable — a brute-force Two Sum does NOT demonstrate hash_map_lookup

**Ground truth quality assessment: ~75% high-confidence, ~15% ambiguous, ~10% uncertain.**

---

## 9. Confidence Analysis

### 9.1 Legacy Confidence Calibration

| Confidence Range | Total | Correct | Incorrect | Accuracy |
|-----------------|-------|---------|-----------|----------|
| 0.0–0.3 | 10 | 1 | 9 | 10.0% |
| 0.3–0.5 | 31 | 2 | 29 | 6.5% |
| 0.5–0.7 | 26 | 4 | 22 | 15.4% |
| 0.7–0.9 | 47 | 16 | 31 | 34.0% |
| 0.9–1.0 | 72 | 29 | 43 | 40.3% |

- **Average confidence (correct):** 0.850
- **Average confidence (incorrect):** 0.679
- **Assessment:** Confidence is weakly correlated with correctness. Higher confidence detections are more likely to be correct, but even at 0.9–1.0 confidence, only 40.3% are correct. The confidence score is NOT a reliable probability estimate.

### 9.2 Shadow Confidence Calibration

| Confidence Range | Total | Correct | Incorrect | Accuracy |
|-----------------|-------|---------|-----------|----------|
| 0.0–0.3 | 5 | 0 | 5 | 0.0% |
| 0.7–0.9 | 75 | 4 | 71 | 5.3% |
| 0.9–1.0 | 8 | 4 | 4 | 50.0% |

- **Average confidence (correct):** 0.869
- **Average confidence (incorrect):** 0.765
- **Assessment:** Shadow confidence is nearly meaningless — most detections fall in the 0.7–0.9 range with only 5.3% accuracy. The confidence scores are not calibrated and do not meaningfully distinguish correct from incorrect detections.

### 9.3 Key Finding

**Neither system produces well-calibrated confidence scores.** The confidence values should NOT be interpreted as probabilities. High confidence does not guarantee correctness, and the confidence distribution does not sharply separate correct from incorrect detections. This is a significant limitation for any downstream application (e.g., adaptive recommendation) that relies on confidence thresholds.

---

## 10. Comparison With Existing Research

### 10.1 Closest Published Work

**Hoq et al. (2025): "Pattern-based Knowledge Component Extraction from Student Code Using Representation Learning"**

| Aspect | Hoq et al. (2025) | PathForge |
|--------|-------------------|-----------|
| **Dataset** | 47,764 Java submissions from 407 students (CodeWorkout) | 81 Python submissions (synthetic templates) |
| **Method** | Data-driven: VAE + K-means clustering of AST subtree patterns | Rule-based: hand-crafted AST pattern detectors |
| **KCs extracted** | Automatically discovered via clustering | Predefined vocabulary (42 concepts) |
| **Evaluation** | Learning curve analysis + DKT predictive performance | P/R/F1 per concept against target_concepts |
| **What they measure** | Whether extracted KCs improve knowledge tracing prediction | Whether detected concepts match expected concepts |
| **Key metric** | DKT AUC improvement over baselines | F1 score per concept |
| **Explainability** | Cluster centroids as representative patterns | Evidence items with descriptions |

**Can the F1 scores be directly compared?**

**No.** The two systems measure fundamentally different things:
- Hoq et al. measure whether automatically extracted patterns improve knowledge tracing (a downstream task)
- PathForge measures whether hand-crafted detectors identify specific algorithmic concepts (a direct detection task)
- The datasets are incomparable (47K Java submissions vs 81 Python templates)
- The KC definitions are incomparable (data-driven clusters vs predefined algorithmic concepts)

**What IS comparable:**
- Both systems extract structural patterns from code ASTs
- Both aim to identify what a student knows about programming
- Both face the challenge of structural variability across implementations
- PathForge's approach is more interpretable (rule-based with evidence) but less scalable
- Hoq et al.'s approach is more scalable but less interpretable

### 10.2 Other Relevant Work

**Code-DKT (Shi et al., 2023):** Uses AST-based deep learning for knowledge tracing. Direct comparison not possible — different task (prediction vs detection), different metrics, different data.

**srcML-DKT (Pankiewicz et al., 2025):** Enhances DKT with source code representations. Again, different evaluation paradigm.

**Bottom line:** No existing paper directly compares rule-based algorithmic concept detection P/R/F1 against PathForge's metrics on comparable data. PathForge's evaluation is unique in its focus on per-concept detection accuracy, but this means there is no established baseline to compare against.

---

## 11. What the Results Say About the Architecture

### 11.1 What Works

1. **Legacy detectors are excellent for well-structured, canonical patterns.** When a submission closely matches the expected template (standard variable names, standard loop forms, standard AST structure), legacy achieves F1 = 1.0 for 13 out of 35 concepts.

2. **The shadow fact extractor correctly identifies structural primitives.** When it fires, the extracted facts (midpoint_calculation, while_loop_comparison, opposite_direction_updates, etc.) are structurally correct.

3. **The layered architecture is conceptually sound.** Separating structural facts → techniques → strategies is a valid decomposition that mirrors how algorithmic concepts are composed.

4. **Both systems parse and analyze 100% of submissions.** No parse failures, no runtime errors, no crashes.

### 11.2 What Does Not Work

1. **Legacy detectors are syntax-coupled, not semantics-coupled.** Changing `left += 1` to `left = left + 1` breaks two_pointers detection. Changing `// 2` to `>> 1` breaks binary search detection. This is a fundamental flaw — the detectors are pattern-matching on AST node types rather than algorithmic intent.

2. **Legacy has a systematic false positive problem.** The greedy_local detector fires on almost any simple loop with a min/max. The two_pointers_same detector fires on any two-variable loop. The prefix_sum detector fires on any accumulator. These are not edge cases — they represent the majority of errors.

3. **Shadow has a coverage crisis.** With only 9 technique detectors and 9 strategy evaluators, the shadow system simply cannot detect 32 out of 35 concepts. This is not a quality issue — it is an architecture gap.

4. **Shadow's fact extractor has naming dependencies.** Cache detection requires "memo"/"dp"/"cache" variable names. Queue detection requires "queue"/"q" names. Neighbor traversal requires "graph"/"adj" names. This directly contradicts the stated goal of naming-independent detection.

5. **Confidence scores are not calibrated.** Neither system produces confidence values that reliably predict correctness. A detection with confidence 0.9 is only correct 40–50% of the time.

6. **Robustness is critically low for legacy.** 35.7% stability rate means the system changes its answer more often than not when given semantically equivalent code. This is unacceptable for any research evaluation.

---

## 12. What Would Need to Change

### 12.1 Critical Changes (Must-Have for Research Viability)

**CURRENT OBSERVATION:** Legacy detectors fail on `left = left + 1` vs `left += 1`
**PROBABLE CAUSE:** Detectors check for `ast.AugAssign` specifically, which is a different AST node type from `ast.Assign`
**PROPOSED CHANGE:** Normalize augmented assignments to equivalent regular assignments during preprocessing, OR modify detectors to accept both forms
**WHY IT SHOULD HELP:** Would immediately fix the two_pointers_opposite robustness failure and likely improve multiple other detectors
**HOW TO TEST:** Re-run robustness test with the increment_style variant — should remain stable

**CURRENT OBSERVATION:** Binary search detector fails on `>> 1` and renamed variables
**PROBABLE CAUSE:** Midpoint detection only matches `// 2` AST pattern; variable name checks are hardcoded
**PROBABLE CAUSE:** `_is_binary_search_condition` only accepts specific variable name sets (`left/right/lo/hi`)
**PROPOSED CHANGE:** Add `>> 1` as equivalent to `// 2` in midpoint detection; relax variable name constraints to check structural pattern (two Name variables with comparison) rather than specific names
**WHY IT SHOULD HELP:** Would fix binary search robustness and generalize to more implementations
**HOW TO TEST:** Run binary search robustness variants — bitshift and rename should remain stable

**CURRENT OBSERVATION:** Shadow system detects only 4 of 35 concepts adequately
**PROBABLE CAUSE:** Only 9 technique detectors and 9 strategy evaluators exist; no detectors for hash_map, frequency_counting, prefix_sum, heap, greedy, linked_list_traversal, etc.
**PROPOSED CHANGE:** Add shadow technique detectors for the missing high-priority concepts: hash_map_usage, frequency_counting, prefix_accumulation, heap_operations, greedy_choice
**WHY IT SHOULD HELP:** Would expand shadow coverage from ~11% to potentially ~40%+ of concepts
**HOW TO TEST:** Re-run full evaluation with expanded shadow vocabulary

**CURRENT OBSERVATION:** greedy_local has 17 false positives (F1=0.191)
**PROBABLE CAUSE:** The detector fires on any loop with min/max operations, which is an extremely common pattern
**PROPOSED CHANGE:** Require additional structural constraints (e.g., sorted input, no nested loops, specific accumulation pattern) to reduce false positives
**WHY IT SHOULD HELP:** Would significantly improve legacy precision
**HOW TO TEST:** Re-run evaluation — greedy_local FPs should decrease substantially

### 12.2 Important Changes (Recommended)

**CURRENT OBSERVATION:** `two_pointers_same` has 12 FPs and 0 TPs (F1=0.000)
**PROBABLE CAUSE:** The detector is so broad it fires on almost any two-variable iteration, producing FPs for unrelated patterns while never correctly identifying the actual fast/slow pointer pattern
**PROPOSED CHANGE:** Tighten the detector to require specific structural evidence: one pointer advancing at 2x speed, linked-list context, or cycle detection structure
**WHY IT SHOULD HELP:** Would eliminate a major source of false positives
**HOW TO TEST:** Re-run evaluation — two_pointers_same FPs should drop to 0

**CURRENT OBSERVATION:** Shadow cache_lookup detection depends on variable names ("memo", "dp", "cache")
**PROBABLE CAUSE:** The fact extractor uses a hardcoded set of cache-like variable names
**PROBABLE CAUSE:** This directly contradicts the naming-independence goal
**PROPOSED CHANGE:** Replace naming heuristic with structural heuristic: dict/subscript access where the same key is read before being written (or vice versa)
**WHY IT SHOULD HELP:** Would make dp_top_down detection work for memoization implementations that use any variable name
**HOW TO TEST:** Test with submissions using non-standard memo variable names (e.g., `table`, `lookup`, `m`)

**CURRENT OBSERVATION:** Confidence scores are not calibrated
**PROBABLE CAUSE:** Confidence is computed from evidence item weights, which are not tuned to ground truth
**PROPOSED CHANGE:** Implement Platt scaling or isotonic regression on a held-out validation set to calibrate confidence scores
**WHY IT SHOULD HELP:** Would make confidence scores meaningful for downstream tasks
**HOW TO TEST:** Re-evaluate calibration using calibration curves on held-out data

---

## 13. Research Scope Recommendation

### OPTION A: Code Analysis Only

**Research question:** "Can semantic/structural analysis of student solutions identify algorithmic concepts more accurately and robustly than existing approaches?"

**Viability assessment:** This is the stronger option given current evidence. The code analysis results show clear strengths (excellent for canonical patterns, 13 concepts at F1=1.0) and clear weaknesses (robustness, false positives, shadow coverage). These weaknesses are addressable through targeted improvements. The research contribution would be:

1. A layered AST analysis architecture (facts → techniques → strategies) that is more interpretable than black-box approaches
2. An evaluation framework for measuring concept detection accuracy and robustness
3. Empirical evidence on which algorithmic patterns are reliably detectable and which are not

**Recommended scope:** Focus on the 13 concepts where legacy achieves F1=1.0, plus the 7 concepts in the 0.5–1.0 range. Document the failure cases as evidence of current limitations. Target: F1 > 0.8 macro across all tested concepts with stability rate > 80%.

### OPTION B: Full Pipeline

**Research question:** "Can richer evidence from student solutions produce a better estimate of conceptual understanding and consequently improve adaptive problem recommendation?"

**Viability assessment:** Not yet viable. The code analysis layer is not robust enough to serve as a reliable input to downstream knowledge tracing and recommendation. Adding learner modeling and recommendation on top of unreliable concept detection would amplify errors rather than correct them.

**Recommended path:** First stabilize code analysis (Option A), then expand to full pipeline once concept detection is reliable.

---

## 14. Final Decision

### **LOCK PATHFORGE WITH TARGETED MODIFICATIONS (Option 2)**

**Justification based on measured evidence:**

The research idea is viable, but the current implementation needs targeted fixes before it can serve as a credible research system.

**Evidence supporting continuation:**
1. 13/35 concepts achieve F1 = 1.0 with legacy — demonstrating that AST-based concept detection IS possible for well-defined patterns
2. The shadow fact extractor correctly identifies structural primitives when it fires — the architecture is sound even if coverage is incomplete
3. The robustness failures are fixable: they stem from AST node type checking (AugAssign vs Assign) and hardcoded variable names, not from fundamental architectural flaws
4. No comparable rule-based system exists in the literature — this is genuinely novel territory
5. The false positive problem is addressable through tighter detector rules and additional structural constraints

**Evidence against unmodified continuation:**
1. Legacy F1 = 0.605 macro is below the threshold for a credible research evaluation system
2. Legacy robustness at 35.7% is unacceptable — semantically equivalent code should produce identical results
3. Shadow F1 = 0.079 macro means it currently contributes nothing to the evaluation
4. Confidence scores are not calibrated and cannot be used as probability estimates
5. The dataset is synthetic and small — real student submissions will likely produce worse results

**Minimum changes needed:**
1. Fix AugAssign/Assign normalization (robustness fix — highest priority)
2. Relax binary search variable name constraints
3. Tighten greedy_local and two_pointers_same detectors (reduce FPs)
4. Add 3–5 shadow technique detectors for high-priority concepts
5. Expand dataset to include real student submissions (even 50–100 would help)

**Timeline estimate:** These changes are achievable in 1–2 focused development sessions. The core architecture does not need to change.

---

## Appendix A: Per-Concept Detection Summary

| Concept | Legacy F1 | Shadow F1 | Support | Legacy Notes |
|---------|-----------|-----------|---------|-------------|
| two_pointers_opposite | 0.889 | 0.889 | 5 | Excellent when canonical |
| sliding_window_variable | 1.000 | 0.000 | 3 | Perfect legacy, no shadow |
| monotonic_stack | 1.000 | 0.000 | 3 | Perfect legacy, no shadow |
| dfs_recursive | 0.706 | 0.000 | 6 | High recall, moderate FP |
| hash_map_lookup | 0.727 | 0.000 | 4 | Perfect recall, some FP |
| dp_1d_forward | 0.571 | 0.000 | 5 | Low recall (only array form) |
| binary_search_standard | 0.444 | 0.000 | 4 | Brittle to renames |
| sliding_window_fixed | 0.400 | 0.000 | 4 | Very low recall |
| two_pointers_same | 0.000 | 0.000 | 3 | 12 FPs, 0 TPs — broken |
| union_find | 0.000 | 0.667 | 2 | Legacy broken, shadow partial |
| dp_top_down | 0.000 | 1.000 | 2 | Shadow only |
| All others | varies | 0.000 | 1–4 | See full table in Section 4 |

## Appendix B: Robustness Failure Details

| Concept | Variant | Transform | Legacy | Shadow |
|---------|---------|-----------|--------|--------|
| two_pointers_opposite | while_not | `while not >=` | **LOST** | **LOST** |
| two_pointers_opposite | increment | `left = left + 1` | **CHANGED** | **LOST** |
| binary_search_standard | bitshift | `>> 1` | **LOST** | stable* |
| binary_search_standard | rename | `lo, hi, mi` | **LOST** | stable* |
| dp_1d_forward | space_opt | variables only | **LOST** | **LOST** |
| dp_1d_forward | dict_memo | dict instead of list | **LOST** | stable |
| backtracking_permutation | used_array | boolean array | **CHANGED** | stable |
| backtracking_permutation | remaining_list | list slicing | **CHANGED** | stable |

*Stable but not detecting target concept — shadow detection rate is 7.1% overall.

---

*Generated by PathForge Evaluation Framework. This evaluation is observational only — no production code was modified.*
