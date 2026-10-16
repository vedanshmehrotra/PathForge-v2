# PathForge Research Dataset Specification

## Version: 2.0.0
## Date: August 27, 2026
## Status: SPECIFICATION — Resolves all contradictions from V1 audit
## Changelog: v2.0.0 — Resolved 8 contradictions, rewrote negative-set specification, added per-strategy examples

---

## 1. Purpose

This document specifies the evaluation dataset for the PathForge research project. The dataset will be used to evaluate whether compositional code analysis (structural facts → techniques → strategies) can reliably identify algorithmic concepts in student code.

**This is a specification, not a dataset.** No synthetic labels are generated here. The actual dataset will be assembled by collecting real student submissions and labeling them through a dual-reviewer protocol.

---

## 2. Research Taxonomy (15 Strategies)

The following 15 strategies form the target vocabulary. Each is defined in `RESEARCH_TAXONOMY_REVIEW.md`.

| ID | Strategy | Abstraction Level |
|----|----------|:-----------------:|
| S01 | binary_search | Strategy |
| S02 | sliding_window | Strategy |
| S03 | two_pointers_opposite | Strategy |
| S04 | dfs_backtracking | Strategy |
| S05 | dp_top_down | Strategy |
| S06 | dp_bottom_up | Strategy (includes dp_2d as specialization) |
| S07 | bfs_shortest_path | Strategy |
| S08 | union_find | Strategy |
| S09 | monotonic_stack | Strategy |
| S10 | topological_sort | Strategy |
| S11 | linked_list_reversal | Strategy |
| S12 | fast_slow_pointers | Strategy |
| S13 | greedy_interval | Strategy |
| S14 | heap_selection | Strategy |
| S15 | dp_2d | Strategy (specialization of dp_bottom_up) |

### 2.1 Strategy Hierarchy

`dp_2d` is a **specialization** of `dp_bottom_up`. Both represent iterative tabular DP. The distinction:
- `dp_bottom_up`: 1D state table (e.g., `dp[i]`)
- `dp_2d`: 2D state table (e.g., `dp[i][j]`)

When a submission fills a 2D table, label as `dp_2d`. When a submission fills a 1D table, label as `dp_bottom_up`. Both are bottom-up DP strategies.

---

## 3. Abstraction Levels — Definitions

### 3.1 Strategy

A **strategy** is a complete algorithmic approach that a student chose to solve a problem. It is identifiable by structural code patterns and represents a decision about HOW to solve, not just WHAT data structure to use.

### 3.2 Technique

A **technique** is a reusable building block within a strategy. It is not a complete algorithmic approach — it is a component that appears across multiple strategies.

### 3.3 Implementation Variant

An **implementation variant** is a syntactic or structural variation of the same strategy. It does NOT change the algorithmic approach. Examples: variable renaming, while vs for, augmented vs non-augmented assignment.

### 3.4 Key Principle

**Semantically equivalent implementations of the same strategy MUST be labeled with the same primary strategy.** Implementation variants are NEVER negatives for the target strategy.

---

## 4. Minimum Dataset Requirements

### 4.1 Aggregate Minimums

| Metric | Minimum | Target |
|--------|:-------:|:------:|
| Total positive submissions | 194 | 250 |
| Total negative/cross-pattern submissions | 194 | 250 |
| Distinct problems | 95 | 120 |
| Distinct implementation variants | 55 | 75 |
| Total submissions | 388 | 500 |

### 4.2 Per-Strategy Distribution

Each strategy must meet its minimum requirements independently. A submission counted as positive for one strategy may serve as a negative for others.

| Strategy | Min Positive | Min Negative | Min Problems | Min Variants |
|----------|:------------:|:------------:|:------------:|:------------:|
| S01 binary_search | 20 | 20 | 10 | 5 |
| S02 sliding_window | 20 | 20 | 10 | 5 |
| S03 two_pointers_opposite | 15 | 15 | 8 | 4 |
| S04 dfs_backtracking | 15 | 15 | 8 | 4 |
| S05 dp_top_down | 15 | 15 | 8 | 3 |
| S06 dp_bottom_up | 15 | 15 | 8 | 5 |
| S07 bfs_shortest_path | 10 | 10 | 5 | 3 |
| S08 union_find | 10 | 10 | 5 | 2 |
| S09 monotonic_stack | 10 | 10 | 5 | 3 |
| S10 topological_sort | 8 | 8 | 4 | 2 |
| S11 linked_list_reversal | 10 | 10 | 5 | 2 |
| S12 fast_slow_pointers | 10 | 10 | 5 | 2 |
| S13 greedy_interval | 8 | 8 | 4 | 2 |
| S14 heap_selection | 8 | 8 | 4 | 2 |
| S15 dp_2d | 10 | 10 | 5 | 3 |

### 4.3 Problem-Level Requirements

For each strategy, problems must satisfy:

1. **Minimum 2 distinct problems per strategy** in the test set
2. **Minimum 1 problem per strategy that appears ONLY in the test set**
3. **Problems must span difficulty levels**: at least 1 Easy, 1 Medium, 1 Hard per strategy (where available)
4. **No more than 40% of problems for any single strategy may come from the same LeetCode contest/batch**

### 4.4 Implementation Variant Requirements

For each strategy, implementation variants must include at least 3 of these 5 types:

1. **Variable renaming**: different variable names for the same structural pattern
2. **Loop form variation**: while vs for, augmented vs non-augmented assignment
3. **Control flow variation**: if/elif/else vs nested if, early return vs flag
4. **Structural variation**: helper functions, different data structure choices
5. **Style variation**: one-liner vs verbose, recursive vs iterative (where applicable)

**These are ALL positive variants.** They do not change the primary strategy label.

---

## 5. Negative Set Specification

### 5.1 Core Principle

**A negative is code whose algorithmic strategy is GENUINELY DIFFERENT from the target strategy, despite possible superficial structural similarity.**

A negative is NEVER:
- A semantically equivalent implementation of the target strategy
- An implementation variant of the target strategy
- Code that uses the target strategy as its primary approach

A negative IS:
- Code that implements a different strategy entirely
- Code that uses a technique (building block) without the target strategy
- Code that has structural overlap but different algorithmic intent

### 5.2 Negative Categories

Every negative submission must be labeled with one or more negative categories:

| Category | Definition | Example |
|----------|-----------|---------|
| **confusable_strategy** | A different strategy that shares structural features with the target | binary_search vs two_pointers_opposite (both have while-loop with index updates) |
| **structural_overlap** | Code that contains structural facts matching the target strategy but is not primarily that strategy | A BFS solution that happens to have a midpoint calculation |
| **technique_only** | Uses a technique associated with the strategy but not as the primary algorithm | Uses a hash map (technique) but the primary strategy is DFS |
| **unrelated** | A different strategy with no structural overlap | union_find is unrelated to sliding_window |

### 5.3 IMPORTANT: implementation_variant Is Removed

The previous `implementation_variant` negative category has been REMOVED. It was contradictory — it classified semantically equivalent implementations as negatives.

**Implementation variants are always POSITIVE for the target strategy.** They are never negatives.

### 5.4 Required Negative Mix

For each strategy, the negative set must include:

| Negative Category | Minimum Count | Purpose |
|-------------------|:-------------:|---------|
| confusable_strategy | 5 | Tests discriminative power against similar strategies |
| structural_overlap | 3 | Tests robustness to incidental feature overlap |
| technique_only | 2 | Tests ability to distinguish technique from strategy |
| unrelated | 7 | Tests specificity (not firing on unrelated code) |

### 5.5 Specific Negative Pairings

| Strategy A | Strategy B | Shared Structural Feature | Distinguishing Feature |
|-----------|-----------|--------------------------|----------------------|
| binary_search | two_pointers_opposite | while-loop with index updates | midpoint calculation |
| binary_search | dp_bottom_up | indexed access in loop | midpoint vs lookback recurrence |
| sliding_window | two_pointers_opposite | two index variables | window state vs convergence |
| sliding_window | prefix_sum | accumulator in loop | window boundaries vs running total |
| dfs_backtracking | dp_top_down | recursive with branching | state restoration vs cache |
| dp_bottom_up | prefix_sum | indexed write in loop | lookback recurrence vs accumulation |
| bfs_shortest_path | topological_sort | queue-based processing | neighbor traversal vs in-degree |
| monotonic_stack | dfs_iterative | stack operations | monotonic comparison vs LIFO |
| linked_list_reversal | fast_slow_pointers | linked structure traversal | pointer rewiring vs differential speed |

---

## 6. Per-Strategy Positive/Negative/NOT-Negative Examples

### S01: binary_search

**Definition**: Divide-and-conquer search that halves the search space each iteration.

**POSITIVE variants** (all labeled `binary_search`):
- Standard while-loop: `while left <= right: mid = (l+r)//2`
- Overflow-safe: `mid = l + (r-l)//2`
- Bitshift: `mid = (l+r) >> 1`
- Recursive: function calls itself with narrowed bounds
- Rotated array: binary search with additional sorted-half check
- Answer space: binary search on answer value, not array index
- Variable renaming: `lo/hi`, `start/end`, `i/j`

**NEGATIVE examples** (NOT binary_search):
- two_pointers_opposite: while-loop with two variables converging, no midpoint
- dp_bottom_up: while-loop filling a table with lookback recurrence
- sliding_window: for-loop maintaining window state

**NOT valid negatives** (these ARE binary_search):
- Recursive binary search (variant, not negative)
- Binary search on rotated array (variant, not negative)
- Binary search on answer space (variant, not negative)

### S02: sliding_window

**Definition**: Maintain a contiguous subsequence (window) over the input, adjusting boundaries based on a condition.

**POSITIVE variants** (all labeled `sliding_window`):
- Fixed window: `for i in range(k, n): window += arr[i] - arr[i-k]`
- Variable window: `while condition: left += 1`
- With helper function: window logic extracted to a function
- With set/dict for frequency: `seen = set()` inside window
- Min/max window: tracking best window seen

**NEGATIVE examples** (NOT sliding_window):
- two_pointers_opposite: converging pointers, no window state
- prefix_sum: running total without window boundaries
- dp_bottom_up: iterative table filling

**NOT valid negatives** (these ARE sliding_window):
- Fixed window (variant, not negative)
- Variable window (variant, not negative)
- For-loop vs while-loop window (variant, not negative)

### S03: two_pointers_opposite

**Definition**: Two indices starting at opposite ends, moving toward each other.

**POSITIVE variants** (all labeled `two_pointers_opposite`):
- Classic palindrome: `left=0, right=n-1, while left < right`
- Container water: `while l < r: water = min(h[l], h[r]) * (r-l)`
- Sorted array sum: `while l < r: curr = nums[l] + nums[r]`
- `not left >= right` form
- `left = left + 1` (non-augmented) form

**NEGATIVE examples** (NOT two_pointers_opposite):
- binary_search: while-loop with midpoint calculation
- sliding_window: window state maintained across iterations
- two_pointers_same: both pointers move forward (fast/slow)

**NOT valid negatives** (these ARE two_pointers_opposite):
- Renamed variables (variant, not negative)
- Non-augmented assignment (variant, not negative)
- Negated comparison form (variant, not negative)

### S04: dfs_backtracking

**Definition**: Explore solution space recursively with state mutation before recursion and restoration after.

**POSITIVE variants** (all labeled `dfs_backtracking`):
- Permutation: `path.append(x); backtrack(); path.pop()`
- Subset: `path.append(nums[i]); backtrack(i+1); path.pop()`
- Used-array: `used[i] = True; backtrack(); used[i] = False`
- Remaining-list: `explore(current, remaining[:i] + remaining[i+1:])`
- N-Queens: `board[row] = col; backtrack(row+1); board[row] = -1`

**NEGATIVE examples** (NOT dfs_backtracking):
- dp_top_down: recursive with cache, no state restoration
- dfs_recursive: recursive without state restoration (tree traversal)
- plain recursion: linear recursion, no branching

**NOT valid negatives** (these ARE dfs_backtracking):
- Different state mutation mechanism (variant, not negative)
- Different base case structure (variant, not negative)

### S05: dp_top_down

**Definition**: Solve subproblems recursively with cache to avoid recomputation.

**POSITIVE variants** (all labeled `dp_top_down`):
- `@lru_cache` decorator
- Manual memo dict: `if n in memo: return memo[n]`
- `functools.lru_cache`
- With early return for base case
- With dictionary vs array cache

**NEGATIVE examples** (NOT dp_top_down):
- dfs_backtracking: recursive with state restoration, no cache
- dfs_recursive: recursive without cache
- dp_bottom_up: iterative, not recursive

**NOT valid negatives** (these ARE dp_top_down):
- Dictionary vs array cache (variant, not negative)
- Different base case structure (variant, not negative)

### S06: dp_bottom_up

**Definition**: Fill a table iteratively using recurrence relation.

**POSITIVE variants** (all labeled `dp_bottom_up`):
- Standard 1D: `dp = [0]*(n+1); for i in range(1,n+1): dp[i] = dp[i-1] + ...`
- Space-optimized: `prev2, prev1 = 1, 2; for i in range(3,n+1): curr = prev1+prev2`
- Dictionary-based: `dp = {}; for i in range(n): dp[i] = ...`
- Knapsack pattern: `for w in range(capacity+1): dp[i][w] = max(...)`
- Coin change: `for coin in coins: for i in range(coin, amount+1): ...`

**NEGATIVE examples** (NOT dp_bottom_up):
- prefix_sum: running total without lookback recurrence
- sliding_window: window maintenance, not table filling
- dp_top_down: recursive, not iterative
- binary_search: search, not table filling

**NOT valid negatives** (these ARE dp_bottom_up):
- Space-optimized DP (variant, not negative — this is the SAME algorithmic approach)
- Dictionary-based DP (variant, not negative)
- Knapsack pattern (variant, not negative)
- 1D vs different indexing patterns (variant, not negative)

### S07: bfs_shortest_path

**Definition**: Traverse graph/tree level by level using a queue.

**POSITIVE variants** (all labeled `bfs_shortest_path`):
- Level-order with `for _ in range(len(queue))`
- Shortest path with distance tracking
- Rotting oranges: multi-source BFS
- With visited set
- Without visited set (tree BFS)

**NEGATIVE examples** (NOT bfs_shortest_path):
- topological_sort: queue-based but uses in-degree, not neighbor traversal
- dfs_iterative: stack-based, not queue-based
- dfs_recursive: recursive, not queue-based

**NOT valid negatives** (these ARE bfs_shortest_path):
- Level-order vs shortest-path (variant, not negative)
- With vs without visited set (variant, not negative)
- `deque` vs list as queue (variant, not negative)

### S08: union_find

**Definition**: Disjoint set data structure with path compression and union.

**POSITIVE variants** (all labeled `union_find`):
- Path compression: `parent[x] = find(parent[x])`
- Union by rank
- Union without rank
- Iterative find
- Recursive find

**NEGATIVE examples** (NOT union_find):
- dp_bottom_up: array-based iteration without parent-pointer chase
- graph traversal: adjacency-based, not parent-pointer based
- linked_list_traversal: .next traversal, not parent-pointer chase

**NOT valid negatives** (these ARE union_find):
- Path compression vs without (variant, not negative)
- Rank vs without rank (variant, not negative)

### S09: monotonic_stack

**Definition**: Stack that maintains monotonic order, popping elements that violate monotonicity.

**POSITIVE variants** (all labeled `monotonic_stack`):
- Daily temperatures: `while stack and temps[i] > temps[stack[-1]]`
- Next greater element
- Histogram: `while stack and heights[i] < heights[stack[-1]]`
- With `len(stack) > 0` check
- With renamed variables (`stk`, `indices`)

**NEGATIVE examples** (NOT monotonic_stack):
- dfs_iterative: stack used for LIFO traversal, no monotonic comparison
- plain_stack: stack without monotonic comparison
- binary_search: while-loop with comparison but no stack

**NOT valid negatives** (these ARE monotonic_stack):
- Different variable names (variant, not negative)
- `len(stack) > 0` vs `while stack` (variant, not negative)
- Decreasing vs increasing monotonic (variant, not negative)

### S10: topological_sort

**Definition**: Order DAG nodes by in-degree processing.

**POSITIVE variants** (all labeled `topological_sort`):
- Kahn's algorithm: in-degree + queue
- DFS-based: post-order reversal
- With cycle detection
- Without cycle detection

**NEGATIVE examples** (NOT topological_sort):
- bfs_shortest_path: queue-based but no in-degree computation
- dfs_recursive: recursive without in-degree
- heap_selection: priority-based, not in-degree based

**NOT valid negatives** (these ARE topological_sort):
- Kahn's vs DFS-based (variant, not negative)
- With vs without cycle detection (variant, not negative)

### S11: linked_list_reversal

**Definition**: In-place reversal of linked-list pointers.

**POSITIVE variants** (all labeled `linked_list_reversal`):
- Iterative: `prev=None; while curr: next=curr.next; curr.next=prev; prev=curr; curr=next`
- Recursive: `rest = reverseList(head.next); head.next.next = head`
- With renamed variables

**NEGATIVE examples** (NOT linked_list_reversal):
- fast_slow_pointers: traversal without rewiring
- linked_list_traversal: traversal without pointer manipulation
- dfs_iterative: stack-based, not pointer rewiring

**NOT valid negatives** (these ARE linked_list_reversal):
- Iterative vs recursive (variant, not negative)
- Different variable names (variant, not negative)

### S12: fast_slow_pointers

**Definition**: Two pointers at different speeds to detect cycles or find middle.

**POSITIVE variants** (all labeled `fast_slow_pointers`):
- Cycle detection: `slow != fast` meeting point
- Middle finder: `fast.next is None`
- With `slow = slow.next; fast = fast.next.next`
- With different initial positions

**NEGATIVE examples** (NOT fast_slow_pointers):
- linked_list_reversal: pointer rewiring, not differential speed
- two_pointers_opposite: converging, not differential speed
- dfs_iterative: stack-based traversal

**NOT valid negatives** (these ARE fast_slow_pointers):
- Cycle detection vs middle finding (variant, not negative)
- Different initial positions (variant, not negative)

### S13: greedy_interval

**Definition**: Sort intervals by start/end, then iterate making locally optimal choices.

**POSITIVE variants** (all labeled `greedy_interval`):
- Merge intervals: `intervals.sort(); for start, end in intervals[1:]`
- Meeting rooms: `intervals.sort(key=lambda x: x[1])`
- Non-overlapping intervals: count removals
- With different sort keys

**NEGATIVE examples** (NOT greedy_interval):
- sorting: just sort, no interval comparison
- dp_bottom_up: iterative table filling
- two_pointers_opposite: converging indices on array

**NOT valid negatives** (these ARE greedy_interval):
- Different sort key (variant, not negative)
- Merge vs non-overlapping (variant, not negative)

### S14: heap_selection

**Definition**: Use priority queue to select top-K or process by priority.

**POSITIVE variants** (all labeled `heap_selection`):
- `heapq.nlargest`
- `heapq.heappush` / `heapq.heappop`
- Min-heap for top-K
- Max-heap (negated values)

**NEGATIVE examples** (NOT heap_selection):
- sorting: comparison-based sort, not heap
- monotonic_stack: stack-based, not heap-based
- dp_bottom_up: iterative, not heap-based

**NOT valid negatives** (these ARE heap_selection):
- Min-heap vs max-heap (variant, not negative)
- nlargest vs heappush/heappop (variant, not negative)

### S15: dp_2d

**Definition**: Fill a 2D table using recurrence on neighboring cells. (Specialization of dp_bottom_up.)

**POSITIVE variants** (all labeled `dp_2d`):
- Grid paths: `dp[i][j] = dp[i-1][j] + dp[i][j-1]`
- LCS: `dp[i][j] = dp[i-1][j-1] + 1` or `max(...)`
- Edit distance
- Different iteration orders

**NEGATIVE examples** (NOT dp_2d):
- dp_bottom_up 1D: single-index table
- prefix_sum: running total
- sliding_window: window maintenance

**NOT valid negatives** (these ARE dp_2d):
- Different iteration order (variant, not negative)
- Different neighbor pattern (variant, not negative)

---

## 7. Submission Sources

### 7.1 Primary Source

LeetCode accepted and incorrect submissions from public discussions and contest submissions.

### 7.2 Source Requirements

| Requirement | Detail |
|------------|--------|
| Language | Python 3 only |
| Code format | Single function body |
| Minimum code length | 5 lines (excluding blanks/comments) |
| Maximum code length | 100 lines |
| Correctness | Must pass visible test cases OR flagged as incorrect |
| Attribution | Problem ID required; author anonymous |

### 7.3 Prohibited Sources

- AI-generated solutions
- Editorial/reference solutions
- Paid contest archive solutions
- Obfuscated or intentionally misleading code

---

## 8. Problem-Disjoint Evaluation

### 8.1 Split Strategy

| Split | Purpose | Problem Overlap | Submission Overlap |
|-------|---------|:---------------:|:------------------:|
| **development** | Detector development, rule tuning | None with validation or test | None with validation or test |
| **validation** | Mid-training evaluation, early stopping | None with dev or test | None with dev or test |
| **test** | Final evaluation, frozen before tuning | None with dev or validation | None with dev or validation |

### 8.2 Split Ratios

| Split | Percentage | Min Problems | Min Submissions |
|-------|:----------:|:------------:|:---------------:|
| development | 40% | 38 | 155 |
| validation | 20% | 19 | 78 |
| test | 40% | 38 | 155 |

### 8.3 Split Rules

1. **All submissions for a given problem go to the same split.**
2. **At least 2 problems per strategy must be in the test set.**
3. **At least 1 problem per strategy must be test-only.**
4. **Split assignment is deterministic.**
5. **The test split is frozen before any detector development begins.**
6. **Development, validation, and test problems must be COMPLETELY DISJOINT.** No problem may appear in more than one split. There is no overlap between dev and validation.

### 8.4 Anti-Tuning Controls

1. **No test-set metrics may be reported during development.**
2. **Any hyperparameter change motivated by test-set performance requires re-splitting.**
3. **The final evaluation must be run exactly once** on the frozen test set.
4. **All code changes between the first and final test evaluation must be documented.**

---

## 9. Labeling Protocol

### 9.1 Labels Per Submission

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `primary_strategy` | enum(15 strategies) or `none` | Yes | The single strategy most central to the algorithm |
| `secondary_strategies` | list(enum) | Yes | Other strategies present but not primary (may be empty) |
| `secondary_techniques` | list(enum) | Yes | Building-block techniques present (may be empty) |
| `ambiguity_flag` | boolean | Yes | True if submission could reasonably be primary for multiple strategies |
| `ambiguity_reasoning` | string | If flag=true | Why the label is ambiguous |
| `evidence` | string | Yes | Brief structural evidence supporting the label |
| `correctness` | enum(correct, incorrect, unverifiable) | Yes | Whether the solution solves the problem |
| `incorrect_reason` | string | If incorrect | Description of the bug |
| `implementation_variant` | enum | Yes | Which variant category this submission represents |
| `reviewer_id` | string | Yes | Reviewer identifier |
| `confidence` | float [0,1] | Yes | Reviewer's confidence in their label |

### 9.2 Primary Strategy Labeling Rules

1. **One primary strategy per submission.**
2. **Label the algorithmic approach, not the implementation detail.**
3. **Label what the code DOES, not what the problem REQUIRES.**
4. **If no strategy applies, label as `none`.**
5. **If multiple strategies are equally primary, flag as ambiguous.**

### 9.3 Secondary Strategy vs Secondary Technique — Key Distinction

| Field | What goes here | Examples |
|-------|---------------|----------|
| `secondary_strategies` | Other strategies from the 15-strategy vocabulary that are present but not primary | A solution uses BFS for level-order traversal AND DP for memoization → primary: `bfs_shortest_path`, secondary_strategies: [`dp_top_down`] |
| `secondary_techniques` | Building-block techniques from the demoted vocabulary that appear within any strategy | A BFS solution uses a hash map for visited tracking → primary: `bfs_shortest_path`, secondary_techniques: [`hash_map_lookup`] |

**Strategy variants are NEVER secondary techniques.** `binary_search_rotated` is NOT a technique — it IS the `binary_search` strategy. It goes in `implementation_variant`, not `secondary_techniques`.

### 9.4 Secondary Technique Vocabulary

These are genuine building blocks (techniques), NOT strategy variants:

| Technique | Definition |
|-----------|-----------|
| hash_map_lookup | Dictionary/set membership check or key lookup |
| hash_map_frequency | Frequency counting with dict or Counter |
| prefix_sum | Running cumulative sum |
| sorting | Comparison-based sort (as preprocessing) |
| heap_operations | heapq push/pop operations |
| linked_list_traversal | .next pointer traversal without rewiring |
| in_degree_tracking | Computing in-degree for graph nodes |
| visited_tracking | Maintaining a visited/seen set |

**Removed from secondary techniques** (these are strategy variants, not techniques):
- ~~sliding_window_fixed~~ → tracked as `implementation_variant` of sliding_window
- ~~sliding_window_variable~~ → tracked as `implementation_variant` of sliding_window
- ~~backtracking_permutation~~ → tracked as `implementation_variant` of dfs_backtracking
- ~~backtracking_subset~~ → tracked as `implementation_variant` of dfs_backtracking
- ~~binary_search_rotated~~ → tracked as `implementation_variant` of binary_search
- ~~binary_search_answer~~ → tracked as `implementation_variant` of binary_search
- ~~dfs_recursive~~ → tracked as `implementation_variant` of dfs_backtracking or as `secondary_strategies`
- ~~dfs_iterative~~ → tracked as `secondary_strategies` (when used within another strategy)
- ~~bfs_level_order~~ → tracked as `implementation_variant` of bfs_shortest_path
- ~~monotonic_deque~~ → tracked as `implementation_variant` of monotonic_stack
- ~~dp_knapsack~~ → tracked as `implementation_variant` of dp_bottom_up
- ~~dp_1d_forward~~ → tracked as `implementation_variant` of dp_bottom_up
- ~~dp_1d_sequence~~ → tracked as `implementation_variant` of dp_bottom_up
- ~~dp_interval~~ → tracked as `implementation_variant` of dp_bottom_up
- ~~dp_state_machine~~ → tracked as `implementation_variant` of dp_bottom_up
- ~~binary_search_tree~~ → tracked as `secondary_strategies` (data structure traversal strategy)

### 9.5 Ambiguity Protocol

#### When to Flag as Ambiguous

1. **Two strategies are equally plausible.** Example: BFS + DFS in different parts with roughly equal weight.
2. **The primary strategy depends on problem interpretation.** Example: Could be `dp_bottom_up` or `prefix_sum` depending on whether accumulator is used for queries or recurrence.
3. **The code structure matches multiple strategies but algorithmic intent is unclear.**

#### When NOT to Flag as Ambiguous

1. **One strategy is clearly primary.** Even if secondary techniques are present.
2. **The implementation variant is unusual but the strategy is clear.** Example: Space-optimized DP is still `dp_bottom_up`. Recursive binary search is still `binary_search`.
3. **The code is incorrect but the intended strategy is clear.**

### 9.6 Multi-Strategy Solutions

1. **Identify the DOMINANT strategy.** Label as primary.
2. **Label other strategies in `secondary_strategies`.** NOT as secondary techniques.
3. **If no strategy dominates, flag as ambiguous.**

### 9.7 Hybrid Algorithms

A hybrid algorithm uses preprocessing + a core procedure.

| Preprocessing | Core Procedure | Primary Strategy | Secondary |
|--------------|---------------|:----------------:|-----------|
| sort | binary search | `binary_search` | secondary_techniques: [`sorting`] |
| sort | two pointers | `two_pointers_opposite` | secondary_techniques: [`sorting`] |
| sort | interval scan & merge | `greedy_interval` | secondary_techniques: [] (sort+scan IS the strategy) |
| sort | heap selection | `heap_selection` | secondary_techniques: [`sorting`] |
| BFS | DP memoization | `bfs_shortest_path` | secondary_strategies: [`dp_top_down`] |

**Rule**: The preprocessing is the core algorithm when the COMBINATION defines a recognized strategy (e.g., greedy_interval = sort + interval scan). Otherwise, the post-preprocessing strategy is primary and the preprocessing is a secondary technique.

### 9.8 Incomplete Code

1. **If intended strategy is clear**, label with `correctness = incorrect` and the intended primary strategy.
2. **If intended strategy is unclear**, label as `none` and flag as ambiguous.
3. **If code cannot be parsed**, exclude from dataset.

### 9.9 Incorrect Solutions

1. **Label the primary strategy based on what the code ATTEMPTS to do**, not what it achieves.
2. **Set correctness = incorrect.**
3. **Describe the bug in incorrect_reason.**
4. **Include in the dataset.**
5. **Evaluate correctness detection separately.**

**Critical**: A buggy binary search is still `binary_search` as the primary strategy. The bug does not change the algorithmic approach. `primary_strategy` and `correctness` are INDEPENDENT labels.

### 9.10 Technique-Without-Strategy

1. **Label the strategy as primary.**
2. **Label the building block as secondary technique.**
3. **Do NOT label the technique as primary.**

---

## 10. Reviewer Protocol

### 10.1 Reviewer Requirements

| Requirement | Detail |
|------------|--------|
| Number of reviewers | 2 independent reviewers per submission |
| Qualifications | Familiar with algorithms; 50+ LeetCode problems solved |
| Training | Complete 10-hour calibration exercise |

### 10.2 Calibration Exercise

1. Each reviewer independently labels 50 pre-labeled submissions.
2. Compute agreement on primary strategy.
3. If agreement < 80%, conduct discussion session.
4. If agreement >= 80%, proceed to production labeling.

### 10.3 Production Labeling Process

1. Each submission independently labeled by both reviewers.
2. Reviewers do NOT see each other's labels during first pass.
3. System computes agreement.
4. Disagreements go to third reviewer.

### 10.4 Decision Tree — Reviewer Aid, Not Mandatory Classifier

The decision tree in Appendix A is a **GUIDE** for reviewers, not a mandatory rule.

**Reviewers may override the decision tree** when the structural evidence clearly supports a different label.

**Override requirements**:
1. Document the override in the `evidence` field.
2. Explain why the decision tree was overridden.
3. Provide the structural evidence that supports the alternative label.
4. Overrides are tracked and reviewed for consistency.

**The decision tree does NOT determine the label.** The reviewer's judgment, supported by structural evidence, determines the label.

### 10.5 Inter-Rater Agreement Metrics

Compute agreement separately for:

1. **Primary strategy**: Cohen's kappa across the 15 strategies ONLY (exclude `none` class from kappa computation)
2. **`none` agreement**: Report the percentage of submissions where both reviewers agree on `none` SEPARATELY from the kappa computation
3. **Secondary strategies**: Multi-label F1
4. **Secondary techniques**: Multi-label F1
5. **Ambiguity flag**: Cohen's kappa on the boolean flag
6. **Correctness**: Cohen's kappa on the correctness enum

**Target thresholds**:

| Metric | Minimum Acceptable | Target |
|--------|:------------------:|:------:|
| Primary strategy kappa (15 strategies) | >= 0.65 | >= 0.75 |
| none agreement | >= 80% | >= 90% |
| Secondary strategies F1 | >= 0.70 | >= 0.80 |
| Secondary techniques F1 | >= 0.70 | >= 0.80 |
| Ambiguity flag kappa | >= 0.60 | >= 0.70 |
| Correctness kappa | >= 0.80 | >= 0.85 |

### 10.6 Agreement Monitoring

1. Compute agreement every 100 submissions.
2. If agreement drops below thresholds, pause and discuss.
3. Record all discussion outcomes.

---

## 11. Machine-Readable Schema

### 11.1 Submission Schema

```json
{
  "problem_id": "string — LeetCode problem ID",
  "submission_id": "string — Unique identifier",
  "source": "string — Source URL or collection ID",
  "language": "python3",
  "code": "string — Complete function body",
  "code_length": "integer",

  "primary_strategy": "enum: S01-S15 | none",
  "secondary_strategies": ["array of strategy IDs — empty if none"],
  "secondary_techniques": ["array of technique IDs — empty if none"],
  "ambiguity_flag": "boolean",
  "ambiguity_reasoning": "string | null",
  "evidence": "string",
  "correctness": "enum: correct | incorrect | unverifiable",
  "incorrect_reason": "string | null",
  "implementation_variant": "enum: standard | renamed_vars | loop_form | control_flow | structural | style | recursive | space_optimized",

  "problem_split": "enum: development | validation | test",
  "problem_difficulty": "enum: easy | medium | hard",
  "problem_tags": ["array of LeetCode tags"],

  "reviewers": {
    "reviewer_a": {
      "reviewer_id": "string",
      "primary_strategy": "enum",
      "secondary_strategies": ["array"],
      "secondary_techniques": ["array"],
      "ambiguity_flag": "boolean",
      "evidence": "string",
      "confidence": "float [0,1]",
      "tree_overridden": "boolean",
      "override_reasoning": "string | null",
      "timestamp": "ISO 8601"
    },
    "reviewer_b": {
      "reviewer_id": "string",
      "primary_strategy": "enum",
      "secondary_strategies": ["array"],
      "secondary_techniques": ["array"],
      "ambiguity_flag": "boolean",
      "evidence": "string",
      "confidence": "float [0,1]",
      "tree_overridden": "boolean",
      "override_reasoning": "string | null",
      "timestamp": "ISO 8601"
    },
    "third_reviewer": {
      "reviewer_id": "string | null",
      "primary_strategy": "enum | null",
      "secondary_strategies": ["array | null"],
      "secondary_techniques": ["array | null"],
      "ambiguity_flag": "boolean | null",
      "evidence": "string | null",
      "adjudication_reasoning": "string | null",
      "timestamp": "ISO 8601 | null"
    }
  },

  "final_label": {
    "primary_strategy": "enum",
    "secondary_strategies": ["array"],
    "secondary_techniques": ["array"],
    "ambiguity_flag": "boolean",
    "correctness": "enum",
    "label_source": "enum: reviewer_a | reviewer_b | third_reviewer | agreement"
  },

  "metadata": {
    "created_at": "ISO 8601",
    "updated_at": "ISO 8601",
    "labeling_round": "integer",
    "frozen": "boolean"
  }
}
```

### 11.2 Dataset-Level Metadata

```json
{
  "dataset_version": "string",
  "created_at": "ISO 8601",
  "frozen_at": "ISO 8601 | null",
  "total_submissions": "integer",
  "total_problems": "integer",
  "total_positive": "integer",
  "total_negative": "integer",
  "split_distribution": {
    "development": { "problems": "integer", "submissions": "integer" },
    "validation": { "problems": "integer", "submissions": "integer" },
    "test": { "problems": "integer", "submissions": "integer" }
  },
  "strategy_distribution": {
    "S01": { "positive": "integer", "negative": "integer", "problems": "integer" }
  },
  "agreement_metrics": {
    "primary_strategy_kappa_15": "float — kappa across 15 strategies only",
    "none_agreement_pct": "float — percentage agreeing on none",
    "secondary_strategies_f1": "float",
    "secondary_techniques_f1": "float",
    "ambiguity_flag_kappa": "float",
    "correctness_kappa": "float",
    "total_adjudicated": "integer",
    "total_agreed": "integer"
  },
  "reviewers": ["array of reviewer IDs"],
  "labeling_guidelines_version": "string",
  "freeze_hash": "string — SHA-256"
}
```

---

## 12. Dataset Freeze Protocol

### 12.1 Freeze Criteria

ALL of the following must be true:

1. All submissions dual-labeled.
2. All disagreements adjudicated.
3. Minimum requirements met.
4. Inter-rater agreement meets thresholds.
5. Problem-disjoint splits verified.
6. No test-set leakage.
7. Freeze hash computed.

### 12.2 Post-Freeze Rules

1. No modifications.
2. No re-labeling.
3. No re-splitting.
4. New submissions only in future versions.

---

## 13. Quality Assurance

### 13.1 Spot Checks

1. Randomly select 10% after dual-labeling.
2. Project lead independently reviews.
3. If error rate > 5%, re-label affected strategy.

### 13.2 Negative Set Validation

1. For each strategy, verify every negative is genuinely negative.
2. Check that no negative is actually a positive (variant).
3. If a negative is found to be positive, relabel and add replacement.

---

## Appendix A: Decision Tree for Primary Strategy

**This is a REVIEWER AID, not a mandatory classifier. Reviewers may override with documented reasoning.**

```
Does the code use a while-loop (or recursion) with midpoint calculation?
  → YES: Is there conditional index update without opposite updates?
    → YES: primary_strategy = binary_search
    → NO: Check two_pointers_opposite or other
  → NO: Continue

Does the code maintain a contiguous window over the input?
  → YES: Is the window state used in later computation?
    → YES: primary_strategy = sliding_window
    → NO: Check two_pointers or other
  → NO: Continue

Does the code use two indices converging from opposite ends?
  → YES: Is there no midpoint calculation?
    → YES: primary_strategy = two_pointers_opposite
    → NO: Check binary_search
  → NO: Continue

Does the code recurse with state mutation and restoration?
  → YES: Is there no cache lookup/write?
    → YES: primary_strategy = dfs_backtracking
    → NO: Check dp_top_down
  → NO: Continue

Does the code recurse with cache lookup and write?
  → YES: Is there no state restoration?
    → YES: primary_strategy = dp_top_down
    → NO: Check dfs_backtracking
  → NO: Continue

Does the code fill a 2D table with recurrence on neighbors?
  → YES: primary_strategy = dp_2d
  → NO: Continue

Does the code fill a table iteratively with lookback recurrence?
  → YES: Is there no recursion?
    → YES: primary_strategy = dp_bottom_up
    → NO: Check dp_top_down
  → NO: Continue

Does the code use a queue with neighbor/tree traversal?
  → YES: Is there no recursion?
    → YES: primary_strategy = bfs_shortest_path
    → NO: Check dfs
  → NO: Continue

Does the code use parent-pointer chase and merge?
  → YES: primary_strategy = union_find
  → NO: Continue

Does the code use stack with monotonic comparison and conditional pop?
  → YES: primary_strategy = monotonic_stack
  → NO: Continue

Does the code compute DAG ordering with in-degree tracking?
  → YES: primary_strategy = topological_sort
  → NO: Continue

Does the code reverse linked-list pointers (next = prev)?
  → YES: primary_strategy = linked_list_reversal
  → NO: Continue

Does the code use differential-speed pointer traversal (next vs next.next)?
  → YES: primary_strategy = fast_slow_pointers
  → NO: Continue

Does the code sort intervals and greedily select?
  → YES: primary_strategy = greedy_interval
  → NO: Continue

Does the code use heapq for priority-based selection?
  → YES: primary_strategy = heap_selection
  → NO: Continue

None of the above?
  → primary_strategy = none
  → Flag for review
```

**Override protocol**: If the tree gives a result but the reviewer believes the evidence supports a different label, the reviewer MUST:
1. Document the override in `evidence`
2. Set `tree_overridden = true`
3. Explain the structural evidence for the alternative label in `override_reasoning`
