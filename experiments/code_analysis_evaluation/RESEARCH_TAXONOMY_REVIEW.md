# PathForge Research Taxonomy Review

## Date: August 27, 2026
## Scope: Classification of all 42 concepts, evaluation of suitability for research, proposal of Research Taxonomy V1

---

## 1. Current Vocabulary Inventory (42 Concepts)

### By Abstraction Level

| Level | Count | Concepts |
|-------|:-----:|----------|
| **Algorithmic Strategy** | 12 | binary_search_standard, binary_search_rotated, binary_search_answer, sliding_window_fixed, sliding_window_variable, two_pointers_opposite, two_pointers_same, backtracking_permutation, backtracking_subset, dfs_recursive, dfs_iterative, topological_sort |
| **Reusable Technique** | 9 | monotonic_stack, monotonic_deque, hash_map_lookup, hash_map_frequency, prefix_sum, fast_slow_pointers, linked_list_reversal, heap_top_k, bfs_level_order |
| **Data Structure Pattern** | 4 | bfs_shortest_path, union_find, binary_search_tree, greedy_interval |
| **DP Variant** | 8 | dp_1d_forward, dp_1d_sequence, dp_2d_grid, dp_2d_string, dp_knapsack, dp_interval, dp_state_machine, dp_top_down, dp_bottom_up |
| **Shadow Technique** | 8 | sequential_accumulation, carry_propagation, recursive_branching, loop_state_tracking, iterative_table_filling, linked_list_traversal, fixed_window_maintenance, monotonic_stack_maintenance |
| **Structural Primitive** | 2 | array_traversal, brute_force |
| **Greedy** | 1 | greedy_local |

---

## 2. Explicit Evaluation of Flagged Concepts

### 2.1 `array_traversal`

**Definition**: A for-loop or while-loop that iterates over array elements.

**Evidence from evaluation**: 44 false positives — the single largest FP source in legacy. Fires on every loop-based algorithm.

**Assessment**: 
- **Not algorithmically distinctive**. Almost every algorithm traverses an array.
- **Not a strategy**. It's a structural primitive — the presence of a loop over indices.
- **Should be REMOVED from authoritative classification**. It provides zero discrimination power. Its presence is assumed by virtually every algorithm that operates on arrays.

**Verdict**: Remove. Keep as internal fact if needed, but never as a labeled concept.

### 2.2 `brute_force`

**Definition**: Nested loops performing exhaustive search over all pairs/triples.

**Evidence from evaluation**: 34 false positives — second largest FP source. Fires on any nested loop, including legitimate O(n²) algorithms.

**Assessment**:
- **Too broad to be meaningful**. The boundary between "brute force" and "nested iteration" is subjective.
- **Not a strategy**. It describes what an algorithm ISN'T, not what it DOES.
- **Generates massive false positives** because many legitimate algorithms use nested loops (DP, graph traversal).
- **Should be REMOVED from authoritative classification**.

**Verdict**: Remove. This is a judgment call about efficiency, not a structural pattern.

### 2.3 `hash_map_lookup`

**Definition**: Using a dictionary for O(1) key lookup.

**Evidence from evaluation**: Legacy F1=0.727 (4 TP, 3 FP). Shadow F1=0.0.

**Assessment**:
- **This is a technique, not a strategy**. Using a hash map is a data structure choice, not an algorithmic strategy.
- The 3 FPs come from `hash_map_frequency` being classified as `hash_map_lookup` (they both use dicts).
- The concept is well-defined but too low-level to be a research target. A student using a hash map could be doing anything from two-sum to BFS to DP.
- **Should be DEMOTED to technique**. It's a building block, not a research-level concept.

**Verdict**: Demote to technique. Useful for internal evidence, not as a research label.

### 2.4 `prefix_sum`

**Definition**: Running cumulative sum with optional dictionary lookup.

**Evidence from evaluation**: Legacy F1=0.5 (1 TP, 1 FP, 1 FN). Shadow F1=0.0.

**Assessment**:
- **Ambiguous boundary with DP**. A prefix sum `prefix[i] = prefix[i-1] + arr[i-1]` is structurally identical to a 1D DP recurrence. The only difference is whether the accumulator is used for subarray queries (prefix sum) or as a recurrence (DP).
- The labeling guidelines say: "NOT present when: Sum is just a total (not used for prefix-style queries)." But this requires understanding the algorithm's PURPOSE, not just its structure.
- **Should be DEMOTED to technique** or **merged into dp_bottom_up**. The distinction requires problem context, not structural evidence.

**Verdict**: Demote to technique. The prefix-sum/DP boundary cannot be reliably drawn from code structure alone.

### 2.5 `two_pointers_same`

**Definition**: Two pointers moving in the same direction at different speeds.

**Evidence from evaluation**: Legacy F1=0.0 (0 TP, 4 FP, 3 FN). Shadow F1=0.0. 4 false positives even after structural fixes.

**Assessment**:
- **Fundamentally ill-defined as a standalone concept**. "Two pointers same direction" encompasses:
  - Fast/slow pointer (cycle detection) — which is already `fast_slow_pointers`
  - Merge two sorted arrays — which is an implementation detail
  - Remove duplicates (write pointer / read pointer) — which is an implementation detail
- The concept conflates multiple unrelated algorithmic patterns under one structural umbrella.
- The legacy detector is broken (0 TP, 4 FP). The shadow system doesn't even try to detect it.
- **Should be REMOVED from authoritative classification**. The useful sub-concepts (`fast_slow_pointers`) already exist.

**Verdict**: Remove. Redundant with `fast_slow_pointers` for the only well-defined sub-case.

### 2.6 `greedy_local`

**Definition**: Making locally optimal choices at each step.

**Evidence from evaluation**: Legacy F1=0.191 (2 TP, 17 FP). Shadow F1=0.0. 17 false positives.

**Assessment**:
- **Not structurally detectable**. "Greedy" is an algorithmic paradigm, not a code pattern. Any loop with `max()` or `min()` gets classified as greedy.
- The definition in the labeling guidelines says: "Sort then iterate making local best choice." But the detector fires on any max/min call, which is ubiquitous.
- **Cannot be reliably distinguished from DP, sliding window, or even simple accumulation** using only structural evidence.
- **Should be REMOVED from authoritative classification**. Greedy algorithms exist, but they cannot be detected from code structure alone.

**Verdict**: Remove. Not structurally distinguishable.

---

## 3. Classification of All 42 Concepts

### 3.1 Concepts to KEEP as Research Strategies (15)

These are algorithmically meaningful, structurally distinguishable, and suitable for empirical study:

| # | Concept | Type | Structural Evidence | Why a Strategy |
|---|---------|------|--------------------:|----------------|
| 1 | **binary_search** | Strategy | while_loop + midpoint_calculation + conditional_index_update | Distinctive algorithmic approach: divide search space by half. Different from two-pointers (no midpoint) and DP (no table). |
| 2 | **sliding_window** | Strategy | loop + conditional_index_update + variable_use_in_loop_body OR fixed_window_maintenance | Distinctive: maintains a window over a contiguous subsequence. Different from two-pointers (window has size concept) and prefix-sum (window is local). |
| 3 | **two_pointers_opposite** | Strategy | while_loop + opposite_direction_updates + no midpoint | Distinctive: converging pointers. Different from binary search (no midpoint) and sliding window (no window state). |
| 4 | **dfs_backtracking** | Strategy | recursive_branching + state_restoration + no cache | Distinctive: explore-and-undo pattern. Different from plain recursion (has state restoration) and DP (no cache). |
| 5 | **dp_top_down** | Strategy | recursive_branching + cache_lookup + cache_write + no state_restoration | Distinctive: recursive with memoization. Different from backtracking (has cache, no state restoration) and plain recursion (has cache). |
| 6 | **dp_bottom_up** | Strategy | iterative_table_filling + indexed_write + index_lookback + no recursion | Distinctive: iterative table filling. Different from prefix-sum (has lookback recurrence) and simple accumulation (has indexed write). |
| 7 | **bfs_shortest_path** | Strategy | queue_dequeue + neighbor_traversal + loop + no recursion | Distinctive: level-by-level traversal. Different from DFS (has queue, no recursion) and graph search (has visited tracking). |
| 8 | **union_find** | Strategy | parent_pointer_chase + parent_root_merge | Distinctive: disjoint set operations. Purely structural — no names required. |
| 9 | **monotonic_stack** | Strategy | stack_operation + monotonic_comparison + conditional_pop | Distinctive: stack with order maintenance. Different from plain stack (has comparison-based pop). |
| 10 | **topological_sort** | Strategy | in_degree_tracking + processing_zero_in_degree_nodes | Distinctive: DAG ordering. Different from BFS (has in-degree computation). |
| 11 | **heap_selection** | Strategy | heapq operations + nlargest/nsmallest | Distinctive: priority-based selection. Different from sorting (uses heap, not comparison sort). |
| 12 | **fast_slow_pointers** | Strategy | linked_traversal + differential_speed (next vs next.next) | Distinctive: cycle detection. Different from linked list reversal (no pointer rewiring). |
| 13 | **linked_list_reversal** | Strategy | pointer_rewiring (next = prev pattern) | Distinctive: in-place reversal. Different from traversal (rewires pointers). |
| 14 | **dp_2d** | Strategy | nested_for_loop + indexed_write[i][j] + lookback from neighbors | Distinctive: 2D recurrence. Different from 1D DP (2D indexing). |
| 15 | **greedy_interval** | Strategy | sort + iterate + interval_comparison | Distinctive: interval scheduling. Different from general greedy (requires sort + interval structure). |

### 3.2 Concepts to DEMOTE to Techniques (14)

These are useful building blocks but not research-level strategies:

| # | Concept | Why Technique, Not Strategy |
|---|---------|----------------------------|
| 1 | hash_map_lookup | Data structure usage, not algorithmic strategy |
| 2 | hash_map_frequency | Data structure usage, not algorithmic strategy |
| 3 | prefix_sum | Structurally identical to 1D DP; distinction requires problem context |
| 4 | sliding_window_fixed | Implementation variant of sliding_window strategy |
| 5 | sliding_window_variable | Implementation variant of sliding_window strategy |
| 6 | backtracking_permutation | Implementation variant of dfs_backtracking strategy |
| 7 | backtracking_subset | Implementation variant of dfs_backtracking strategy |
| 8 | binary_search_rotated | Implementation variant of binary_search strategy |
| 9 | binary_search_answer | Implementation variant of binary_search strategy |
| 10 | dfs_recursive | Implementation variant of recursive exploration (may or may not be backtracking) |
| 11 | dfs_iterative | Implementation technique (stack-based), not a strategy |
| 12 | bfs_level_order | Implementation variant of BFS strategy |
| 13 | monotonic_deque | Implementation variant of monotonic stack strategy |
| 14 | binary_search_tree | Data structure, not algorithmic strategy |

### 3.3 Concepts to REMOVE from Authoritative Classification (8)

These are not suitable as research labels:

| # | Concept | Reason for Removal |
|---|---------|-------------------|
| 1 | array_traversal | Structural primitive — not algorithmically distinctive. 44 FPs. |
| 2 | brute_force | Judgment about efficiency, not a structural pattern. 34 FPs. |
| 3 | two_pointers_same | Ill-defined: conflates unrelated patterns. 0 TP, 4 FP. |
| 4 | greedy_local | Not structurally detectable. 2 TP, 17 FP. |
| 5 | dp_1d_forward | Redundant with dp_bottom_up (both are iterative 1D DP) |
| 6 | dp_1d_sequence | Too vague — overlaps with dp_1d_forward and other DP |
| 7 | dp_interval | Implementation variant, not a distinct strategy |
| 8 | dp_state_machine | Implementation variant, not a distinct strategy |

### 3.4 Concepts to MERGE into Higher-Level Strategies (5)

| # | Merge Into | Reason |
|---|-----------|--------|
| 1 | dp_knapsack → dp_bottom_up | Knapsack is a canonical problem, not a strategy. It's dp_bottom_up with a specific recurrence. |
| 2 | dp_2d_grid → dp_2d | Both are 2D DP; the grid/string distinction is problem-dependent, not strategy-dependent |
| 3 | dp_2d_string → dp_2d | Same as above |
| 4 | hash_map_frequency → (keep as technique) | Useful internal evidence but not a strategy |
| 5 | heap_top_k → heap_selection | Renamed to be strategy-focused |

### 3.5 Shadow-Only Concepts to KEEP as Internal Techniques

| Concept | Role |
|---------|------|
| sequential_accumulation | Evidence for sliding_window and DP |
| recursive_branching | Evidence for backtracking, DP, DFS |
| carry_propagation | Evidence for linked list algorithms |
| loop_state_tracking | Evidence for sliding_window |
| iterative_table_filling | Evidence for dp_bottom_up |
| linked_list_traversal | Evidence for fast_slow_pointers, linked_list_reversal |
| fixed_window_maintenance | Evidence for sliding_window |
| monotonic_stack_maintenance | Evidence for monotonic_stack |

---

## 4. Explicit Evaluation of the 6 Flagged Concepts

### 4.1 `array_traversal` — VERDICT: REMOVE

**Evidence**: 44 false positives in 81 submissions. The detector fires on every loop that iterates over an array, which includes virtually every algorithm. 

**Why it fails**: A for-loop over array indices is not an algorithmic concept — it's a programming construct. The concept provides zero discrimination power because its prevalence approaches 100% in array-based problems.

**Comparison with research literature**: No published work treats "array traversal" as a knowledge component. It's universally assumed as prerequisite knowledge, not a target concept.

### 4.2 `brute_force` — VERDICT: REMOVE

**Evidence**: 34 false positives. Fires on any nested loop, including legitimate O(n²) DP solutions, graph traversal with adjacency matrix, etc.

**Why it fails**: "Brute force" is a characterization of efficiency, not a structural pattern. The same nested-loop structure can be brute force (O(n³) subarray sum) or optimal (O(n²) DP). The detector cannot distinguish these because the distinction is about algorithmic analysis, not code structure.

**Comparison with research literature**: No published work treats "brute force" as a detectable pattern. It's a post-hoc classification, not a structural feature.

### 4.3 `hash_map_lookup` — VERDICT: DEMOTE TO TECHNIQUE

**Evidence**: Legacy F1=0.727 (good precision/recall). Shadow F1=0.0 (no shadow implementation).

**Why it's not a strategy**: Using a hash map is a data structure choice, not an algorithmic strategy. A student using `dict` could be implementing two-sum (hash_map_lookup), BFS (visited tracking), DP (memoization), or frequency counting. The hash map itself tells us nothing about the algorithmic approach.

**Comparison with research literature**: Pattern-based KC work (e.g., KC-DKT) treats data structure usage as a feature, not a knowledge component. The knowledge component is the algorithm, not the data structure.

### 4.4 `prefix_sum` — VERDICT: DEMOTE TO TECHNIQUE

**Evidence**: Legacy F1=0.5. Shadow F1=0.0. The concept is structurally indistinguishable from 1D DP.

**Why it's problematic**: A prefix sum `prefix[i] = prefix[i-1] + arr[i-1]` is structurally identical to a DP recurrence `dp[i] = dp[i-1] + cost[i-1]`. The only difference is whether the result is used for subarray queries (prefix sum) or as a recurrence solution (DP). This distinction requires understanding the problem context, not the code structure.

**Comparison with research literature**: In educational data mining, prefix sums are sometimes treated as a technique within DP, not a separate strategy.

### 4.5 `two_pointers_same` — VERDICT: REMOVE

**Evidence**: Legacy F1=0.0 (0 TP, 4 FP, 3 FN). Shadow F1=0.0. Even after structural fixes, the concept produces more false positives than true positives.

**Why it fails**: The concept conflates multiple unrelated patterns:
- Fast/slow pointer for cycle detection → already covered by `fast_slow_pointers`
- Write pointer / read pointer for in-place modification → an implementation detail, not a strategy
- Merge sorted arrays → an implementation detail

The concept is not "two pointers same direction" — it's a grab-bag of unrelated patterns that happen to use two variables.

**Comparison with research literature**: Cycle detection (Floyd's algorithm) is studied as a specific algorithm, not as a "two pointers same direction" pattern.

### 4.6 `greedy_local` — VERDICT: REMOVE

**Evidence**: Legacy F1=0.191 (2 TP, 17 FP). Shadow F1=0.0. 17 false positives — third highest FP source.

**Why it fails**: "Greedy" is an algorithmic paradigm, not a code pattern. The detector fires on any `max()` or `min()` call in a loop, which is ubiquitous. The structural evidence (max/min + loop + index update) does not distinguish greedy from DP, sliding window, or simple accumulation.

**Comparison with research literature**: Greedy algorithms are studied as problem-specific solutions (activity selection, Huffman coding), not as detectable code patterns. The "greedy choice property" is a mathematical property of the problem, not a structural feature of the code.

---

## 5. Ground-Truth Methodology Discrepancy

### The Discrepancy

The **feasibility evaluation** (earlier report) identified "ambiguous/uncertain labels" in the ground truth. The **latest improvement report** claimed "0% ambiguity rate."

### Analysis

These are using **different definitions of ambiguity**:

1. **Feasibility evaluation definition**: A label is ambiguous if the *concept itself* is poorly defined or if the *same code* could reasonably be labeled as multiple concepts. Under this definition, concepts like `greedy_local`, `array_traversal`, and `brute_force` are ambiguous because their definitions overlap with other concepts and with common code patterns.

2. **Improvement report definition**: A label is ambiguous if the *specific submission* has unclear evidence for its assigned concept. Under this definition, every submission in the 81-entry dataset was hand-labeled with clear structural evidence, so there's 0% ambiguity at the submission level.

### Resolution

**Both are correct under their respective definitions.** The improvement report's 0% claim applies to submission-level label clarity (every label has clear evidence). The feasibility evaluation's ambiguity concern applies to concept-level definition clarity (some concepts are poorly defined or overlap with others).

**The correct interpretation**: The ground truth labels are clear for what they claim, but some of the concepts themselves are not well-defined enough to serve as research targets. This is a taxonomy problem, not a labeling problem.

### Recommended Ground-Truth Methodology

For the research taxonomy, ground truth should be established using:

1. **Concept-level validation**: Before labeling, verify that each concept has a clear, non-overlapping definition with structural evidence requirements
2. **Submission-level labeling**: For each submission, identify ALL applicable concepts (a submission can be multi-labeled)
3. **Primary concept designation**: Each submission gets a "primary" concept — the one most central to the algorithm
4. **Ambiguity flags**: If a submission could reasonably be primary for multiple concepts, flag it
5. **Human review**: At least 2 independent reviewers with disagreement resolution

---

## 6. Research Taxonomy V1 — 15 Strategy-Level Concepts

### Definitions and Structural Evidence

#### R1: Binary Search
- **Definition**: Divide-and-conquer search that halves the search space each iteration
- **Why strategy, not technique**: It's a complete algorithmic approach — the student decided to solve the problem by halving a search space, not by scanning, DP, or graph traversal
- **Required structural evidence**: `while_loop_comparison` + `midpoint_calculation` + `conditional_index_update` + absence of `opposite_direction_updates`
- **Common incidental evidence that must NOT count**: Variable named "mid" without actual midpoint calculation; for-loop with midpoint-like expression
- **Likely confusable strategies**: `two_pointers_opposite` (both have while-loop with index updates, but binary search has midpoint)
- **Suitability**: ✅ Excellent. Structurally distinctive, multiple implementation styles, widely studied

#### R2: Sliding Window
- **Definition**: Maintain a contiguous subsequence (window) over the input, adjusting boundaries based on a condition
- **Why strategy, not technique**: The student chose to solve the problem by maintaining a window — this is a complete algorithmic approach
- **Required structural evidence**: (a) `loop_state_tracking` + `variable_use_in_loop_body` (variable window), OR (b) `fixed_window_maintenance` + `window_size_constant` (fixed window). Plus absence of `opposite_direction_updates` and `midpoint_calculation`
- **Common incidental evidence that must NOT count**: Any loop with a max() call (not a window); hash-map lookup with constant offset (prefix sum pattern, not window)
- **Likely confusable strategies**: `two_pointers_opposite` (window has two boundaries but maintains size; two-pointers converge)
- **Suitability**: ✅ Excellent. Well-defined, structurally detectable, common in problems

#### R3: Two Pointers (Converging)
- **Definition**: Two indices starting at opposite ends, moving toward each other
- **Why strategy, not technique**: Complete algorithmic approach — the student chose to solve by scanning from both ends
- **Required structural evidence**: `while_loop_comparison` + `opposite_direction_updates` + absence of `midpoint_calculation`
- **Common incidental evidence that must NOT count**: Binary search (has midpoint); sliding window (has window state)
- **Likely confusable strategies**: `binary_search` (both use while-loop with index updates)
- **Suitability**: ✅ Excellent. Distinctive, well-defined, structurally clear

#### R4: DFS / Backtracking
- **Definition**: Explore solution space recursively with state mutation before recursion and restoration after
- **Why strategy, not technique**: Complete algorithmic approach — the student chose to explore by recursing and undoing
- **Required structural evidence**: `recursive_branching` OR (`self_recursive_call` + `early_termination`) + `state_restoration` + absence of `cache_lookup`/`cache_write`
- **Common incidental evidence that must NOT count**: Plain recursion without state restoration (DFS without backtracking); memoization (has cache, not state restoration)
- **Likely confusable strategies**: `dp_top_down` (both recursive, but backtracking has state restoration, DP has cache)
- **Suitability**: ✅ Excellent. Structurally distinctive, well-studied

#### R5: DP Top-Down (Memoization)
- **Definition**: Solve subproblems recursively with cache to avoid recomputation
- **Why strategy, not technique**: Complete algorithmic approach — the student chose to use recursion with memoization
- **Required structural evidence**: `recursive_branching` + `cache_lookup` + `cache_write` + absence of `state_restoration`
- **Common incidental evidence that must NOT count**: Backtracking (has state restoration, not cache); plain recursion (no cache)
- **Likely confusable strategies**: `dfs_backtracking` (both recursive, but DP has cache, backtracking has state restoration)
- **Suitability**: ✅ Excellent. Structurally distinctive, well-studied

#### R6: DP Bottom-Up (Tabulation)
- **Definition**: Fill a table iteratively using recurrence relation
- **Why strategy, not technique**: Complete algorithmic approach — the student chose to build solutions from subproblems iteratively
- **Required structural evidence**: `iterative_table_filling` + `indexed_write` + `index_lookback` + absence of `recursive_branching`
- **Common incidental evidence that must NOT count**: Prefix sum (no lookback recurrence); simple accumulation (no indexed write); space-optimized DP (no table)
- **Likely confusable strategies**: `prefix_sum` (both accumulate, but DP has lookback recurrence)
- **Suitability**: ✅ Excellent. Structurally distinctive, well-studied

#### R7: BFS (Level-by-Level Traversal)
- **Definition**: Traverse graph/tree level by level using a queue
- **Why strategy, not technique**: Complete algorithmic approach — the student chose to traverse by levels
- **Required structural evidence**: `queue_dequeue` + (`neighbor_traversal` OR `linked_structure_traversal`) + loop + absence of `recursive_branching`
- **Common incidental evidence that must NOT count**: Queue used for non-BFS purposes (topological sort, sliding window with deque)
- **Likely confusable strategies**: `topological_sort` (both use queue + in-degree, but BFS has neighbor traversal)
- **Suitability**: ✅ Good. Structurally detectable with queue + neighbor access

#### R8: Union-Find
- **Definition**: Disjoint set data structure with path compression and union by rank
- **Why strategy, not technique**: Complete algorithmic approach — the student chose to solve connectivity problems using union-find
- **Required structural evidence**: `parent_pointer_chase` + `parent_root_merge` (purely structural, no names required)
- **Common incidental evidence that must NOT count**: Array indexing in DP; tree traversal
- **Likely confusable strategies**: None — uniquely identifiable by parent-pointer chase pattern
- **Suitability**: ✅ Excellent. Purely structural, uniquely identifiable

#### R9: Monotonic Stack
- **Definition**: Stack that maintains monotonic order, popping elements that violate monotonicity
- **Why strategy, not technique**: Complete algorithmic approach — the student chose to solve by maintaining a monotonic stack
- **Required structural evidence**: `stack_operation` + `monotonic_comparison` + `conditional_pop`
- **Common incidental evidence that must NOT count**: Plain stack usage (no monotonic comparison); DFS stack (no conditional pop)
- **Likely confusable strategies**: None — uniquely identifiable by monotonic comparison with stack top
- **Suitability**: ✅ Excellent. Structurally distinctive, well-studied

#### R10: Topological Sort
- **Definition**: Order DAG nodes by in-degree processing
- **Why strategy, not technique**: Complete algorithmic approach — the student chose to solve by ordering dependencies
- **Required structural evidence**: `in_degree_tracking` + processing nodes with zero in-degree
- **Common incidental evidence that must NOT count**: BFS without in-degree (regular graph traversal)
- **Likely confusable strategies**: `bfs_shortest_path` (both use queue, but topological sort has in-degree computation)
- **Suitability**: ✅ Good. Structurally detectable

#### R11: Linked-List Reversal
- **Definition**: In-place reversal of linked-list pointers
- **Why strategy, not technique**: Complete algorithmic approach — the student chose to reverse pointers in-place
- **Required structural evidence**: `pointer_rewiring` (next = prev pattern) + linked structure traversal
- **Common incidental evidence that must NOT count**: Simple traversal (no rewiring); cycle detection (no rewiring)
- **Likely confusable strategies**: `fast_slow_pointers` (both traverse linked lists, but reversal rewires pointers)
- **Suitability**: ✅ Good. Structurally distinctive

#### R12: Fast/Slow Pointers (Cycle Detection)
- **Definition**: Two pointers at different speeds to detect cycles or find middle
- **Why strategy, not technique**: Complete algorithmic approach — the student chose to detect cycles using differential speed
- **Required structural evidence**: linked_structure_traversal + differential speed (next vs next.next)
- **Common incidental evidence that must NOT count**: Two-pointers opposite (both use while-loop with two variables, but different structure)
- **Likely confusable strategies**: `linked_list_reversal` (both traverse linked lists)
- **Suitability**: ✅ Good. Structurally distinctive

#### R13: Greedy Interval
- **Definition**: Sort intervals by start/end, then iterate making locally optimal choices
- **Why strategy, not technique**: Complete algorithmic approach — the student chose to sort and greedily select
- **Required structural evidence**: sort + iterate + interval comparison (merged[-1][1] >= start)
- **Common incidental evidence that must NOT count**: Simple sorting (no interval comparison); general greedy (no interval structure)
- **Likely confusable strategies**: None — requires both sort and interval structure
- **Suitability**: ✅ Good. Structurally detectable

#### R14: Heap / Priority Selection
- **Definition**: Use priority queue to select top-K or process by priority
- **Why strategy, not technique**: Complete algorithmic approach — the student chose to use a heap for selection
- **Required structural evidence**: heapq operations (heappush/heappop or nlargest/nsmallest)
- **Common incidental evidence that must NOT count**: Sorting (different data structure)
- **Likely confusable strategies**: None — uniquely identifiable by heapq usage
- **Suitability**: ✅ Good. Structurally distinctive

#### R15: 2D Dynamic Programming
- **Definition**: Fill a 2D table using recurrence on neighboring cells
- **Why strategy, not technique**: Complete algorithmic approach — the student chose to solve using 2D DP
- **Required structural evidence**: nested_for_loop + indexed_write[i][j] + lookback from neighbors (i-1, j-1, etc.)
- **Common incidental evidence that must NOT count**: 1D DP (single index); grid traversal without DP (no lookback recurrence)
- **Likely confusable strategies**: `dp_bottom_up` (both fill tables, but 2D has nested indices)
- **Suitability**: ✅ Good. Structurally distinctive

---

## 7. Minimum Dataset Requirements

| Concept | Min Positive | Min Negative | Min Distinct Problems | Min Variant Implementations |
|---------|:------------:|:------------:|:---------------------:|:--------------------------:|
| binary_search | 20 | 20 | 10 | 5 (standard, overflow-safe, bitshift, rotated, answer) |
| sliding_window | 20 | 20 | 10 | 5 (fixed, variable, min_window, with helper, dict-based) |
| two_pointers_opposite | 15 | 15 | 8 | 4 (palindrome, container, sorted-array, rename) |
| dfs_backtracking | 15 | 15 | 8 | 4 (permutation, subset, combination, used-array) |
| dp_top_down | 15 | 15 | 8 | 3 (fib, climbing, coin-change) |
| dp_bottom_up | 15 | 15 | 8 | 5 (1d, 2d, knapsack, interval, state-machine) |
| bfs_shortest_path | 10 | 10 | 5 | 3 (level-order, shortest-path, rotting-oranges) |
| union_find | 10 | 10 | 5 | 2 (path-compression, union-by-rank) |
| monotonic_stack | 10 | 10 | 5 | 3 (daily-temps, next-greater, histogram) |
| topological_sort | 8 | 8 | 4 | 2 (kahn, dfs-based) |
| linked_list_reversal | 10 | 10 | 5 | 2 (iterative, recursive) |
| fast_slow_pointers | 10 | 10 | 5 | 2 (cycle-detect, middle-finder) |
| greedy_interval | 8 | 8 | 4 | 2 (merge, meeting-rooms) |
| heap_selection | 8 | 8 | 4 | 2 (top-k, median-stream) |
| dp_2d | 10 | 10 | 5 | 3 (grid-path, lcs, edit-distance) |
| **TOTAL** | **194** | **194** | **95** | **55** |

---

## 8. Recommendations

### A. Recommended Research Taxonomy (15 Concepts)

1. binary_search
2. sliding_window
3. two_pointers_opposite
4. dfs_backtracking
5. dp_top_down
6. dp_bottom_up
7. bfs_shortest_path
8. union_find
9. monotonic_stack
10. topological_sort
11. linked_list_reversal
12. fast_slow_pointers
13. greedy_interval
14. heap_selection
15. dp_2d

### B. Concepts to Keep as Strategies

All 15 listed above. These are algorithmically meaningful, structurally distinguishable, and suitable for empirical study.

### C. Concepts to Demote to Techniques

1. hash_map_lookup
2. hash_map_frequency
3. prefix_sum
4. sliding_window_fixed (→ sliding_window)
5. sliding_window_variable (→ sliding_window)
6. backtracking_permutation (→ dfs_backtracking)
7. backtracking_subset (→ dfs_backtracking)
8. binary_search_rotated (→ binary_search)
9. binary_search_answer (→ binary_search)
10. dfs_recursive (→ dfs_backtracking or dp_top_down depending on context)
11. dfs_iterative (→ implementation variant)
12. bfs_level_order (→ bfs_shortest_path)
13. monotonic_deque (→ monotonic_stack)
14. binary_search_tree (→ data structure, not strategy)
15. dp_knapsack (→ dp_bottom_up)
16. dp_1d_forward (→ dp_bottom_up)
17. dp_1d_sequence (→ dp_bottom_up)
18. dp_interval (→ dp_bottom_up)
19. dp_state_machine (→ dp_bottom_up)

### D. Concepts to Remove from Authoritative Classification

1. array_traversal — structural primitive, not algorithmically distinctive
2. brute_force — judgment about efficiency, not a structural pattern
3. two_pointers_same — ill-defined, conflates unrelated patterns
4. greedy_local — not structurally detectable

### E. Ground-Truth Methodology

Use a **two-level labeling system**:

1. **Strategy labels** (primary): One primary strategy per submission, representing the core algorithmic approach. These are the 15 research concepts.

2. **Technique labels** (secondary): Multiple techniques per submission, representing building blocks used. These are the demoted concepts.

**Labeling protocol**:
- Label the strategy FIRST (what algorithmic approach does this code use?)
- Then label techniques (what data structures and patterns are present?)
- If ambiguous, flag for human review
- Maintain an "uncertain" category with reasoning

**Validation**:
- 2 independent reviewers per submission
- Inter-annotator agreement target: Cohen's kappa >= 0.7
- Disagreements resolved by third reviewer

### F. Recommended Next Implementation Phase

1. **Restructure vocabulary**: Implement the 15-strategy taxonomy in the shadow system
2. **Demote techniques**: Move demoted concepts to internal evidence layer only
3. **Remove primitives**: Remove array_traversal, brute_force, two_pointers_same, greedy_local from authoritative output
4. **Expand shadow vocabulary**: Add technique detectors for hash_map, prefix_sum, dfs_recursive, linked_list
5. **Build evaluation dataset**: Collect 200+ submissions across 15 strategy concepts with minimum requirements above
6. **Validate ground truth**: Run dual-reviewer labeling with kappa >= 0.7
7. **Run baseline evaluation**: Measure the 15-strategy taxonomy on the validated dataset
8. **Begin confidence calibration**: Once baseline is established, calibrate confidence scores
