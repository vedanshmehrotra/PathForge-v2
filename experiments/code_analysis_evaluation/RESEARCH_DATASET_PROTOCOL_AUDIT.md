# Research Dataset Protocol Audit

## Date: August 27, 2026
## Source: RESEARCH_DATASET_SPECIFICATION.md v1.0.0
## Scope: Internal contradictions in labeling rules, negative set definition, and strategy/technique boundary

---

## 1. Contradictions Found

### CONTRADICTION 1: Space-optimized DP — Positive or Negative?

**Rule A** (Section 7.4, "When NOT to Flag as Ambiguous", Rule 2):
> "Space-optimized DP is still `dp_bottom_up` even though it eliminates the table."

**Rule B** (Section 4.1, "implementation_variant" negative category):
> "A variant of the target strategy that should NOT be classified as the target. Example: Space-optimized DP that eliminates the table (should not be dp_bottom_up)."

**Why they conflict**: Rule A says space-optimized DP IS dp_bottom_up (label as positive). Rule B says space-optimized DP should NOT be classified as dp_bottom_up (label as negative). These are mutually exclusive. A reviewer following Rule A labels it as a positive example; a reviewer following Rule B labels it as a negative example. This will destroy inter-rater agreement for dp_bottom_up.

**Proposed Resolution**: Choose one rule and delete the other. Given that the taxonomy review's principle is "label algorithmic intent, not implementation form," **Rule A is correct**: space-optimized DP is still dp_bottom_up. Rule B's example should be changed to a genuinely different pattern (e.g., a prefix sum that looks like DP but isn't).

---

### CONTRADICTION 2: Recursive Binary Search — Not Handled by Decision Tree

**Rule A** (Section 14, Decision Tree, first check):
> "Does the code use a while-loop with midpoint calculation?" → YES → binary_search

**Rule B** (Section 3.4, Implementation Variant Requirements, Rule 5):
> "recursive vs iterative (where applicable)" is a required variant type.

**Rule C** (Section 7.2, Rule 2):
> "Label the algorithmic approach, not the implementation detail."

**Why they conflict**: The decision tree requires a while-loop for binary search. Recursive binary search uses recursion, not a while-loop. A recursive binary search would fail the first check and fall through to "None of the above → primary_strategy = none." But Rule C says to label the algorithmic approach (binary search), not the implementation detail (recursion vs iteration). The decision tree contradicts the labeling principle.

**Proposed Resolution**: Add a second path in the decision tree: "Does the code recurse with midpoint calculation and conditional branching (no state restoration, no cache)?" → YES → binary_search. This handles recursive binary search without misclassifying it as dfs_backtracking or dp_top_down.

---

### CONTRADICTION 3: Strategy Variants Labeled as Secondary Techniques

**Rule A** (Section 2, Strategy Definitions):
> `binary_search`, `sliding_window`, `dfs_backtracking`, `bfs_shortest_path` are strategy-level concepts.

**Rule B** (Section 7.3, Secondary Technique Vocabulary):
> `binary_search_rotated`, `binary_search_answer`, `backtracking_permutation`, `backtracking_subset`, `sliding_window_fixed`, `sliding_window_variable`, `bfs_level_order`, `dfs_recursive`, `dfs_iterative` are listed as secondary techniques.

**Why they conflict**: These "secondary techniques" are actually variants of the strategies in Rule A. `binary_search_rotated` IS binary search — it's the same algorithmic approach applied to a rotated array. Labeling it as a "secondary technique" is like labeling "recursive quicksort" as a secondary technique of "sorting." The taxonomy review said to "demote" these to techniques, but the demotion was meant to remove them from the primary strategy vocabulary, not to recategorize them as building blocks.

The practical problem: if a student's code implements `binary_search_rotated`, the reviewer labels `binary_search` as primary strategy AND `binary_search_rotated` as a secondary technique. This is semantically incoherent — the "technique" IS the strategy.

**Proposed Resolution**: Remove strategy variants from the secondary technique vocabulary. The secondary technique vocabulary should contain only genuine building blocks:
- hash_map_lookup
- hash_map_frequency
- prefix_sum
- heap_operations
- sorting
- linked_list_traversal
- monotonic_deque
- in_degree_tracking

Strategy variants (binary_search_rotated, backtracking_permutation, etc.) should be tracked as `implementation_variant` in the schema, not as secondary techniques.

---

### CONTRADICTION 4: sliding_window_fixed/variable Are the Strategy, Not Techniques

**Rule A** (Section 2, Strategy S02):
> `sliding_window` is a strategy with two implementation paths: variable window and fixed window.

**Rule B** (Section 7.3, Secondary Technique Vocabulary):
> `sliding_window_fixed` and `sliding_window_variable` are listed as secondary techniques.

**Why they conflict**: `sliding_window_fixed` IS `sliding_window` — it's one of the two structural paths to detect the sliding_window strategy. Labeling it as a "secondary technique" of itself is circular. If a student uses a fixed window, the primary strategy is `sliding_window` and there is no separate "sliding_window_fixed" technique to list.

**Proposed Resolution**: Remove `sliding_window_fixed` and `sliding_window_variable` from the secondary technique vocabulary. These are implementation paths within the strategy, not separate techniques.

---

### CONTRADICTION 5: Multi-Strategy Rule Demotes Strategies to Techniques

**Rule A** (Section 7.5, Rule 2):
> "Label the other strategy as secondary technique. If present in the code."

**Rule B** (Section 7.3):
> "Techniques are building blocks, not the primary algorithm."

**Why they conflict**: If a solution uses both BFS and DP (two strategies), Rule 2 says to label BFS as a "secondary technique." But BFS is a strategy, not a technique. The secondary technique vocabulary doesn't include BFS. The schema expects `secondary_techniques` to contain technique IDs, not strategy IDs. This creates a categorization error.

**Proposed Resolution**: Add a `secondary_strategies` field to the schema for multi-strategy solutions. When a solution uses two strategies, the dominant one is primary, and the other goes in `secondary_strategies`. This preserves the strategy/technique distinction.

---

### CONTRADICTION 6: Decision Tree Is Structural but Rule 7.8 Says Label by Intent

**Rule A** (Section 14, Decision Tree):
> Checks structural features: midpoint calculation, window state, pointer rewiring, etc.

**Rule B** (Section 7.8, Rule 1):
> "Label the primary strategy based on what the code ATTEMPTS to do, not what it achieves."

**Why they conflict**: The decision tree matches on structural features. An incorrect solution might have broken structural features (e.g., binary search with the midpoint calculation syntactically wrong). The decision tree would fail to match it, but Rule B says to label based on intent. The decision tree cannot determine intent — it can only match patterns.

**Proposed Resolution**: Add an explicit instruction to the decision tree: "If the code has a clear bug but the intended strategy is recognizable from context (e.g., the variable names, the problem type, the partial structure), label the intended strategy and mark correctness = incorrect. Do NOT force the label to 'none' just because a structural check fails due to a bug."

---

### CONTRADICTION 7: Hybrid Preprocessing — When Is Sort the Core Algorithm?

**Rule A** (Section 7.6, Rule 1):
> "Label the strategy that solves the core problem as primary. If the sort is just preprocessing, the primary strategy is what comes after."

**Rule B** (Section 7.6, Rule 3):
> "If the preprocessing IS the core algorithm (e.g., greedy interval = sort + scan), label the combined approach as primary."

**Why they conflict**: Rule 1 says sort is a secondary technique. Rule 3 says sometimes sort IS the core algorithm. But the decision tree has no check for "sort + scan" — it only checks "sort intervals and greedily select" for greedy_interval. What about sort + binary search? Or sort + two-pointer? The rules don't clearly define when preprocessing crosses the line into being the core algorithm.

**Proposed Resolution**: Add a clarifying rule: "The preprocessing is the core algorithm when the combination of preprocessing + scan is itself a recognized strategy (e.g., greedy_interval = sort + interval scan). If the preprocessing enables a different strategy (e.g., sort + binary search), the post-preprocessing strategy is primary and sorting is a secondary technique."

---

### CONTRADICTION 8: dp_2d vs dp_bottom_up Overlap

**Rule A** (Section 2, Strategy S06):
> `dp_bottom_up` is "fill a table iteratively using recurrence relation."

**Rule B** (Section 2, Strategy S15):
> `dp_2d` is "fill a 2D table using recurrence on neighboring cells."

**Why they conflict**: `dp_2d` IS a form of `dp_bottom_up` — it fills a table iteratively with a recurrence. The only difference is the dimensionality (1D vs 2D). But the taxonomy review merged dp_2d_grid and dp_2d_string into dp_2d, and separately kept dp_bottom_up. This means a 2D DP solution could be labeled as either dp_2d or dp_bottom_up, depending on whether the reviewer focuses on the dimensionality or the iterative filling.

The decision tree checks "2D table" before "iteratively with lookback recurrence," so dp_2d would be caught first. But this means 2D DP is NOT dp_bottom_up, which contradicts the principle that dp_bottom_up includes all iterative table-filling approaches.

**Proposed Resolution**: Either (a) merge dp_2d into dp_bottom_up (renaming it to `dp_iterative` to be dimension-agnostic), or (b) explicitly define dp_2d as a specialization of dp_bottom_up with the rule: "If the code fills a 2D table, label as dp_2d. If the code fills a 1D table, label as dp_bottom_up." Option (b) is cleaner because it gives reviewers a clear decision rule.

---

## 2. Negative Set Issue: Accidental Exclusion of Variants

### The Problem

Section 4.1 defines `implementation_variant` as a negative category:
> "A variant of the target strategy that should NOT be classified as the target."

But the only example given is "Space-optimized DP that eliminates the table (should not be dp_bottom_up)," which contradicts the ambiguity rules (Contradiction 1 above).

More critically, the `implementation_variant` negative category is underspecified. Without clear examples of which variants are negatives, reviewers will inconsistently apply it. Some possible consequences:

1. **Recursive binary search labeled as negative for binary_search** — but recursive binary search IS binary search.
2. **Dictionary-based dp_top_down labeled as negative for dp_bottom_up** — but dictionary-based DP is still dp_bottom_up if it iterates.
3. **For-loop sliding window labeled as negative for sliding_window** — but for-loop sliding window IS sliding_window.

### The Risk

If `implementation_variant` negatives include genuine variants of the target strategy, the negative set becomes polluted with false negatives. A detector that correctly classifies these as the target strategy would be penalized for "false positives" that are actually correct detections.

### Required Clarification

The specification must provide an explicit list of which variants are NEGATIVES (should NOT be classified as the target) vs. which are POSITIVES (should be classified as the target). Without this, the `implementation_variant` category is undefined.

---

## 3. Additional Issues

### ISSUE 1: Secondary Technique Vocabulary Includes Non-Techniques

The secondary technique vocabulary (Section 7.3) includes `dp_knapsack`, `dp_1d_forward`, `dp_1d_sequence`, `dp_interval`, `dp_state_machine`. These are all dp_bottom_up variants, not techniques. A technique is a building block (hash map, prefix sum). These are strategy variants.

### ISSUE 2: "none" Strategy Count in Agreement Metrics

Section 8.4 says Cohen's kappa is computed on "15-strategy + none taxonomy" — that's 16 classes. But the `none` class is structurally different from the 15 strategies (it means "no strategy applies"). Including it in kappa computation inflates the apparent agreement because most submissions will NOT be `none`, creating a class imbalance.

### ISSUE 3: Validation Split Overlap Rule

Section 6.1 says validation "may overlap with dev" for problems. This means a problem can appear in both dev and validation. If a detector sees the same problem in dev and validation, the validation metrics are contaminated. This undermines the purpose of having a validation split.

---

## 4. Summary

### BLOCKING CONTRADICTIONS

These contradictions will produce invalid ground-truth labels if not resolved before labeling begins:

1. **Contradiction 1** (space-optimized DP) — positive in one rule, negative in another. Will cause systematic disagreement for dp_bottom_up.
2. **Contradiction 3** (strategy variants as techniques) — binary_search_rotated, backtracking_permutation, etc. cannot be both a strategy variant and a secondary technique. Reviewers will not know how to label these.
3. **Contradiction 5** (multi-strategy demotion) — no `secondary_strategies` field exists in the schema. Multi-strategy solutions cannot be correctly labeled.

### NON-BLOCKING ISSUES

These should be resolved but won't immediately invalidate labels:

4. **Contradiction 2** (recursive binary search) — affects a small number of submissions but creates an edge case gap.
5. **Contradiction 6** (decision tree vs intent) — reviewers can override the tree, but the override process is not clearly defined.
6. **Contradiction 7** (hybrid preprocessing) — affects a small number of submissions.
7. **Contradiction 8** (dp_2d vs dp_bottom_up) — affects submissions that use 2D DP.
8. **Issue 1** (non-techniques in secondary vocabulary) — confusing but not label-breaking.
9. **Issue 2** (kappa inflation from `none` class) — affects metric computation, not labels.
10. **Issue 3** (validation overlap) — affects validation metric reliability.

### REQUIRED CLARIFICATIONS BEFORE LABELING

1. **Explicitly define which implementation variants are positive vs. negative** for each strategy. Without this, the `implementation_variant` negative category is undefined.
2. **Remove strategy variants from the secondary technique vocabulary.** Add a `secondary_strategies` field to the schema.
3. **Add recursive binary search handling** to the decision tree.
4. **Resolve the dp_2d / dp_bottom_up boundary** with a clear decision rule.
5. **Clarify the validation split overlap rule** — either no overlap with dev, or document why overlap is acceptable.
6. **Define the override process** for when reviewers disagree with the decision tree.
7. **Remove `none` from the kappa computation** or compute kappa separately for the 15-strategy subset.

### VERDICT: NOT READY FOR DATA COLLECTION

The specification contains 3 blocking contradictions that will produce invalid labels if labeling begins without resolution. The negative set definition is underspecified in a way that risks polluting negatives with false negatives. The secondary technique vocabulary conflates strategy variants with building blocks. These issues must be resolved before any labeling work begins.

**Recommended next step**: Resolve the 3 blocking contradictions and 7 required clarifications, then re-audit before starting data collection.
