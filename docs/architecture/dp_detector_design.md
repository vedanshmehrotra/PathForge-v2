# Dynamic Programming Detector Design

## Phase 3C.2.8A — Design Specification

---

## Table of Contents

1. [Common DP Detection Philosophy](#1-common-dp-detection-philosophy)
2. [Detector Specifications](#2-detector-specifications)
   - [dp_1d_forward](#21-dp_1d_forward)
   - [dp_1d_sequence](#22-dp_1d_sequence)
   - [dp_2d_grid](#23-dp_2d_grid)
   - [dp_2d_string](#24-dp_2d_string)
   - [dp_knapsack](#25-dp_knapsack)
   - [dp_interval](#26-dp_interval)
   - [dp_state_machine](#27-dp_state_machine)
3. [Evidence Table](#3-evidence-table)
4. [Detector Comparison Matrix](#4-detector-comparison-matrix)
5. [Gate Rule Reference](#5-gate-rule-reference)
6. [Known Ambiguities and Mitigations](#6-known-ambiguities-and-mitigations)
7. [Implementation Order Recommendation](#7-implementation-order-recommendation)

---

## 1. Common DP Detection Philosophy

### 1.1 Definition of DP for Detection Purposes

A code fragment exhibits Dynamic Programming when it satisfies **all three** of:

1. **Structured computation**: Results are computed incrementally and stored in a data structure (table, array, dict, or cache) for reuse.
2. **Subproblem decomposition**: The computation of each cell/element depends on previously computed values via a recurrence relation.
3. **Deterministic order**: The computation proceeds in a well-defined order (forward iteration, nested loops, recursive with memoization).

A code fragment is **not** DP if:
- It uses brute-force recursion without memoization (no storage for computed results).
- It uses only simple accumulation without subproblem structure (single running variable).
- It uses greedy local decisions without a table of states.
- It uses divide-and-conquer without overlapping subproblems.

### 1.2 Two Detection Paths: Tabulation and Memoization

Every DP detector must support **two structural paths**:

#### Path A: Tabulation (Iterative DP)

Structural signature:
- Array/list creation: `dp = [0] * (n + 1)` or `dp = [[0] * n for _ in range(m)]`
- Loop filling: `for i in range(...): dp[i] = f(dp[i-1], dp[i-2], ...)`
- Index lookback: Subscript reads with `[i-1]`, `[i-2]`, `[i-w]`, `[r-1][c-1]`
- Return of final cell: `return dp[n]` or `return dp[-1][-1]`

#### Path B: Memoization (Recursive DP)

**Important: Memoization alone does NOT imply DP.** Cached recursion without evidence of actual subproblem recurrence or state transitions must not classify as DP. For a memoized function to be DP, there must be:

- A recurrence relation combining results from smaller subproblems (e.g., `max(left, right)`, `left + right`, `min(a, b) + cost`)
- Overlapping subproblems where the same subproblem is solved multiple times
- State transitions that depend on previously computed values

A function with `@cache` that simply traverses a tree without combining subproblem results (e.g., DFS that caches visited nodes) is caching, not DP.

Structural signature:
- Recursive function with overlapping subproblems
- Cache decorator: `@cache`, `@lru_cache`, `@lru_cache(maxsize=None)`
- Manual memo dict: `if key in memo: return memo[key]` + `memo[key] = result`
- Table as closure variable: `dp = {}` or `dp = [...]` used across recursive calls
- **Recurrence expression** combining multiple subproblem results (required for classification)

### 1.3 Common Evidence Signals

These signals are shared across multiple DP detectors. Each detector selects a subset.

DP arrays (1D or 2D) are strong supporting evidence but are NOT mandatory. Space-optimized DP patterns using rolling variables, rolling arrays, O(1) state transitions, or memoized recursion are valid DP implementations that may lack explicit array creation.

| Evidence Type | Weight | Detection Method | Applies To |
|---|---|---|---|
| `dp_array_1d` | 0.25 | List multiplication `[0] * (n+1)`, `[1] * n`, or list comprehension of fixed size | All tabulation DP |
| `dp_array_2d` | 0.30 | Nested list comprehension `[[0]*m for _ in range(n)]` | Grid, String, Knapsack, Interval |
| `table_fill_loop` | 0.20 | For-loop iterating over DP array indices, writing to `dp[i]` | All tabulation DP |
| `index_lookback` | 0.25 | Subscript read `dp[i-1]`, `dp[i-2]`, `dp[i-w]` in same scope as write | Forward, Sequence, Knapsack |
| `grid_lookback` | 0.25 | Subscript read `dp[r-1][c]`, `dp[r][c-1]`, `dp[i-1][j-1]` | Grid, String |
| `recurrence_expression` | 0.20 | `max(...)`, `min(...)`, `+`, `||` combining multiple lookback terms | All DP |
| `cache_decorator` | 0.30 | `@cache`, `@lru_cache`, `@lru_cache(maxsize=...)` on function | Memoization DP |
| `manual_memo_check` | 0.25 | `if key in memo: return memo[key]` or `memo.get(key)` pattern | Memoization DP |
| `manual_memo_store` | 0.20 | `memo[key] = result` assignment | Memoization DP |
| `base_case_return` | 0.15 | Conditional return for `n <= 1`, `i == 0`, `r == 0`, `c == 0` | All DP |
| `result_aggregation` | 0.15 | `max(dp)`, `min(dp)`, `dp[-1][-1]` at end | All DP |

### 1.4 Anti-Signals (Negative Evidence)

These reduce confidence and are checked by every DP detector:

| Anti-Signal | Rationale |
|---|---|
| No array/cache storage | Without storage, it is not DP |
| Recursion without memoization (`@cache` or manual memo check) | Brute-force recursion without subproblem reuse |
| Single variable accumulation only | Greedy or simple iteration, not DP |
| Pure sorting with no lookback | Sorting pattern, not DP |
| Prefix sum only with no recurrence | Prefix sum pattern, not DP |

### 1.5 Base-Case Detection (Shared Helper)

All DP detectors share a `_find_base_case` method that detects:

- `if n <= 1: return n` or `return 1`
- `if i == 0: dp[i] = initial_value`
- `if r == 0 or c == 0: dp[r][c] = grid[r][c]`
- `if not s1 or not s2: return 0`
- Boundary initialization: `dp[0] = 0`, `dp[0][0] = grid[0][0]`

Detected as `EvidenceItem(type="base_case", weight=0.15)`

### 1.6 Table Initialization Detection (Shared Helper)

Detects initialization patterns:

- `dp = [0] * (n + 1)` or `dp = [0] * n` — list multiplication with integer
- `dp = [0.0] * (n + 1)` — list multiplication with float
- `dp = [1] * n` or `dp = [1] * len(nums)` — ones initialization
- `dp = [[0] * cols for _ in range(rows)]` — nested comprehension for 2D
- `dp = [[float('inf')] * n for _ in range(m)]` — inf initialization
- `dp = defaultdict(int)` or `dp = {}` — dict-based memo

Detected as `EvidenceItem(type="dp_array_1d", weight=0.25)` or `EvidenceItem(type="dp_array_2d", weight=0.30)`

### 1.7 Cache Detection (Shared Helper)

Detects memoization patterns:

- `from functools import lru_cache` or `from functools import cache`
- `@lru_cache(maxsize=None)` or `@cache` decorator on function definition
- `if n in memo: return memo[n]` — manual memo check
- `memo[n] = result` — manual memo store
- `dp = {}` or `dp = dict()` used for memo in recursive context

Detected as `EvidenceItem(type="cache_decorator", weight=0.30)` or paired items `manual_memo_check` (0.25) + `manual_memo_store` (0.20)

### 1.8 State Transition Identification (Shared Helper)

Detects recurrence expressions:

- `dp[i] = dp[i-1] + dp[i-2]` — addition recurrence
- `dp[i] = max(dp[i-1], dp[i-2] + nums[i])` — max recurrence
- `dp[i] = min(dp[i], dp[j] + 1)` — min recurrence
- `dp[r][c] = grid[r][c] + min(dp[r-1][c], dp[r][c-1])` — grid recurrence
- `dp[i][w] = max(dp[i-1][w], dp[i-1][w-weight[i]] + value[i])` — knapsack recurrence
- Any `BinOp` combining lookback subscripts

Detected as `EvidenceItem(type="recurrence_expression", weight=0.20)`

### 1.9 Confidence Calculation

Standard formula, identical to all existing detectors:

```python
confidence = min(sum(item.weight for item in evidence), 1.0)
```

Gating ensures confidence is zero when the core signal is absent.

### 1.10 Determinism and Isolation

All rules from DETECTOR_INTERFACE.md apply:
- Stateless: no mutable class-level state
- Deterministic: same AST → same result
- Isolated: no inter-detector calls
- Safe: no I/O, no network, no filesystem

---

## 2. Detector Specifications

---

### 2.1 dp_1d_forward

#### Purpose

Detect 1D forward DP where a single array is filled left-to-right using a recurrence that depends on a fixed number of previous elements. Characteristic of Climbing Stairs, House Robber, Fibonacci-style DP, and 1D cost/min-path problems.

#### Evidence Signals

| Evidence Type | Weight | Detection |
|---|---|---|
| `dp_array_1d` | 0.25 | `dp = [0] * (n+1)` or `dp = [0] * n` |
| `table_fill_loop` | 0.20 | For-loop iterating over dp indices (single loop, depth 1) |
| `index_lookback` | 0.30 | `dp[i-1]`, `dp[i-2]` read during table fill |
| `recurrence_expression` | 0.20 | Addition or max combining lookback terms |
| `base_case_return` | 0.15 | `if n <= 2: return n` or boundary assignments `dp[0]=0, dp[1]=1` |
| `result_aggregation` | 0.15 | `return dp[n]` or `return dp[-1]` |

#### Gating Rules

**Core gate (mandatory):** `index_lookback`

**Secondary (at least two of):** `dp_array_1d`, `table_fill_loop`, `cache_decorator`. Array creation is strong evidence but not mandatory — space-optimized DP (rolling variables, O(1) state transitions) is valid.

**Anti-gate:** If `max_loop_depth >= 2`, do NOT detect (belongs to sequence or 2D). If `has_swap_recurse_swap` or `has_append_pop` pattern, skip.

#### False-Positive Prevention

| Risk | Mitigation |
|---|---|
| Prefix sum | Require lookback index > 1 level deep or non-trivial recurrence (not just `dp[i]=dp[i-1]+val`). Prefix sum uses contiguous accumulation without branching recurrence. |
| Simple iteration | Require at least one `max()`/`min()` in recurrence OR lookback of at least 2 levels (`dp[i-1]` and `dp[i-2]`). |
| Greedy with array | Require array WRITES inside loop (greedy assigns to scalar, not array). |
| Kadane's algorithm | Kadane uses single running variable `max_ending_here`, not array indexing. Check for subscript write target. |

#### Similar Detectors and Distinction

| Detector | Distinction |
|---|---|
| dp_1d_sequence | Sequence uses nested loops (depth >= 2). Forward uses single loop. |
| dp_knapsack | Knapsack uses 2D array or weight-indexed loop. Forward uses 1D single loop. |
| Greedy local | Greedy writes to scalar variables, not array elements. |
| Prefix sum | Prefix sum uses `dp[i] = dp[i-1] + arr[i]` without max/min or branching. |

#### Known Limitations

- Cannot distinguish between Fibonacci-style (additive) and min-cost variants — both look identical structurally.
- Cannot detect non-array memoization (e.g., `@cache` on standalone recursive function without explicit `dp` array variable).
- May miss DP where the array is named unconventionally (e.g., `states = [0] * n` vs `dp = [0] * n`). Mitigation: detect any list multiplication with size derived from input + integer.

---

### 2.2 dp_1d_sequence

#### Purpose

Detect 1D sequence DP with nested loops, where each position `i` depends on all (or a range of) previous positions `j < i`. Characteristic of Longest Increasing Subsequence (LIS), Russian Doll Envelopes, and sequence partitioning.

#### Evidence Signals

| Evidence Type | Weight | Detection |
|---|---|---|
| `dp_array_1d` | 0.25 | `dp = [1] * n` or `dp = [0] * n` |
| `nested_fill_loops` | 0.25 | Two-level nested loop `for i in ...: for j in range(i):` |
| `inner_lookback` | 0.25 | `dp[j]` read inside inner loop, comparing or combining with `dp[i]` |
| `recurrence_expression` | 0.20 | `max(dp[i], dp[j] + 1)` or `min(dp[i], dp[j] + cost)` |
| `result_aggregation` | 0.20 | `return max(dp)` or `return max(dp)` — aggregation over whole array |

#### Gating Rules

**Core gate (mandatory):** `nested_fill_loops` AND `inner_lookback`

**Secondary (at least one of):** `dp_array_1d`, `recurrence_expression`, `result_aggregation`. Array creation is strong evidence but not mandatory — rolling array sequence DP is valid.

**Anti-gate:** If table is 2D (`dp_array_2d`), skip (belongs to 2D, knapsack, or interval).

#### False-Positive Prevention

| Risk | Mitigation |
|---|---|
| Brute-force nested loops | Require DP array WRITE inside inner loop AND lookback read of `dp[j]`. Brute force reads `nums[j]` not `dp[j]`. |
| Simple pair comparison | Require assignment to `dp[i]` inside inner loop, not just comparison. |
| Sorting + single loop | Require nested loop depth >= 2. |

#### Similar Detectors and Distinction

| Detector | Distinction |
|---|---|
| dp_1d_forward | Forward uses single loop with fixed lookback. Sequence uses nested loop with variable lookback. |
| dp_2d_grid | Grid uses 2D array with row/col lookback. Sequence uses 1D array. |
| Brute force | Brute force nested loops read raw data, not dp array. Sequence reads `dp[j]` in inner loop. |

#### Known Limitations

- Cannot distinguish LIS from Longest Bitonic Subsequence or similar variants — all use same nested-loop structure.
- May fire on O(n^2) comparison-based algorithms that happen to use `dp` as variable name. Mitigation: require `max()`/`min()` in recurrence.
- Cannot detect sequence DP using binary search optimization (patience sorting) — that variant does not use nested loops.

---

### 2.3 dp_2d_grid

#### Purpose

Detect 2D grid DP where a table is filled row-by-row or column-by-column, with each cell depending on neighbors above, left, or diagonal. Characteristic of Minimum Path Sum, Unique Paths, Maximal Square, Dungeon Game.

#### Evidence Signals

| Evidence Type | Weight | Detection |
|---|---|---|
| `dp_array_2d` | 0.30 | `dp = [[0]*cols for _ in range(rows)]` |
| `nested_fill_loops` | 0.20 | Two-level loop `for r in range(rows): for c in range(cols):` |
| `grid_lookback` | 0.30 | `dp[r-1][c]`, `dp[r][c-1]`, `dp[r-1][c-1]` within loop body |
| `recurrence_expression` | 0.20 | `min(dp[r-1][c], dp[r][c-1]) + grid[r][c]` or similar |
| `result_aggregation` | 0.15 | `return dp[-1][-1]` or `return dp[m-1][n-1]` |
| `base_case_return` | 0.15 | Boundary initialization `dp[0][0] = grid[0][0]` or `dp[0][c] = ...` |

#### Gating Rules

**Core gate (mandatory):** `grid_lookback` AND `nested_fill_loops`

**Secondary (at least one of):** `dp_array_2d`, `recurrence_expression`, `result_aggregation`. 2D array creation is strong evidence but not mandatory — rolling array grid DP is valid.

**Anti-gate:** If `has_string_compare` (detected via `in` or `==` on string variables in loop), skip (belongs to dp_2d_string). If DP array is 1D, skip.

#### False-Positive Prevention

| Risk | Mitigation |
|---|---|
| 2D array creation without DP | Require lookback reads AND recurrence expression. |
| Image processing nested loops | Require DP-typed variable name patterns (`dp`, `table`, `memo`) or multiplication initialization pattern. |
| Matrix traversal without DP | Require `min()`/`max()` in recurrence, not just addition. |

#### Similar Detectors and Distinction

| Detector | Distinction |
|---|---|
| dp_2d_string | String uses character comparison (`s1[i]==s2[j]`) in recurrence. Grid uses numeric grid access. |
| dp_knapsack | Knapsack uses capacity-bound inner loop (`for c in range(cap+1)`) and weight comparison. |
| dp_interval | Interval uses length-based outer loop and pair-based inner loop. |

#### Known Limitations

- Cannot distinguish minimum-path-sum from unique-paths — both use same structural pattern with different operators.
- 2D array creation via `[[0]*cols]*rows` creates reference aliasing, but this is a Python bug, not a detection concern. Both forms should be detected.
- May miss DP where grid dimensions are computed differently (e.g., `len(matrix)`, `len(matrix[0])`).

---

### 2.4 dp_2d_string

#### Purpose

Detect 2D string DP where a table is filled based on character comparison between two strings. Characteristic of Edit Distance (Levenshtein), Longest Common Subsequence (LCS), Wildcard Matching, Regular Expression Matching, and Distinct Subsequences.

#### Evidence Signals

| Evidence Type | Weight | Detection |
|---|---|---|
| `dp_array_2d` | 0.25 | `dp = [[0]*(n+1) for _ in range(m+1)]` |
| `nested_fill_loops` | 0.20 | Two-level loop over string indices |
| `string_compare` | 0.30 | `s1[i-1] == s2[j-1]` or `s[i] == c` or `s[i] in set` inside loop |
| `grid_lookback` | 0.25 | `dp[i-1][j-1]`, `dp[i-1][j]`, `dp[i][j-1]` in recurrence |
| `recurrence_expression` | 0.20 | `min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]) + cost` or `max(dp[i-1][j], dp[i][j-1])` |
| `base_case_return` | 0.15 | `if i == 0: dp[0][j] = j` or `dp[i][0] = i` — base row/col initialization |

#### Gating Rules

**Core gate (mandatory):** `string_compare` AND `grid_lookback`

**Secondary (at least one of):** `dp_array_2d`, `nested_fill_loops`, `recurrence_expression`, `base_case_return`. 2D array creation is strong evidence but not mandatory.

**Anti-gate:** If no string comparison detected, skip (belongs to dp_2d_grid).

#### False-Positive Prevention

| Risk | Mitigation |
|---|---|
| Grid DP with string variables | Require explicit character comparison (`s1[i] == s2[j]` or `word1[i-1] == word2[j-1]`). |
| General 2D DP | String compare is the core differentiator. Without it, the pattern is grid DP. |
| Fuzzy matching without DP table | Require dp_array_2d. Simple string iteration without table is not DP. |

#### Similar Detectors and Distinction

| Detector | Distinction |
|---|---|
| dp_2d_grid | No string comparison. Numeric/coordinate grid access. |
| dp_knapsack | No string comparison. Capacity-weight comparison instead. |
| dp_interval | No string comparison. Interval pair comparison instead. |

#### Known Limitations

- Cannot distinguish between different string DP variants (LCS vs Edit Distance) — all have same structural signature.
- `max()` vs `min()` in recurrence would hint at LCS vs Edit Distance but is not a reliable differentiator (variations exist).
- Requires string variable identification, which may be ambiguous in dynamically typed Python.

---

### 2.5 dp_knapsack

#### Purpose

Detect knapsack-style DP where a 2D table is filled with capacity as one dimension and items as the other. Characteristic of 0/1 Knapsack, Unbounded Knapsack, Partition Equal Subset Sum, Coin Change (as knapsack), Target Sum.

#### Evidence Signals

| Evidence Type | Weight | Detection |
|---|---|---|
| `dp_array_2d` | 0.25 | `dp = [[0]*(cap+1) for _ in range(n)]` |
| `nested_fill_loops` | 0.20 | Two-level loop: item outer, capacity inner |
| `capacity_compare` | 0.30 | `if c >= weight[i]:` or `if w >= weights[i-1]:` — compare capacity against item weight |
| `max_min_recurrence` | 0.25 | `max(dp[i-1][c], dp[i-1][c-w[i]] + val[i])` or `min(dp[i-1][c], dp[i-1][c-w[i]] + 1)` |
| `grid_lookback` | 0.20 | `dp[i-1][c]`, `dp[i-1][c-w[i]]` |
| `result_aggregation` | 0.15 | `return dp[-1][cap]` or `return dp[n][W]` |

#### Gating Rules

**Core gate (mandatory):** `capacity_compare` AND `max_min_recurrence`

**Secondary (at least one of):** `dp_array_2d`, `nested_fill_loops`, `grid_lookback`. 2D array creation is strong evidence but not mandatory — 1D space-optimized knapsack is valid.

**Anti-gate:** If no capacity-weight comparison, skip (belongs to grid or interval). If `has_string_compare`, skip (belongs to string DP).

#### False-Positive Prevention

| Risk | Mitigation |
|---|---|
| Grid DP with value lookup | Require explicit capacity comparison: `c >= weight[i]` or `w >= weights[j]`. Grid DP does not have this. |
| Interval DP with length variable | Interval uses length-based pairs, not capacity. |
| General 2D array filling | Capacity comparison is the unique structural signal. |

#### Similar Detectors and Distinction

| Detector | Distinction |
|---|---|
| dp_2d_grid | No capacity comparison. No weight/value indexing. |
| dp_2d_string | No capacity comparison. Has string character comparison. |
| dp_interval | Interval uses non-grid pair-based table. No weight-indexed inner loop. |

#### Known Limitations

- 1D space-optimized knapsack (`dp = [0] * (cap+1)` with single loop backward) will be confused with dp_1d_forward. Mitigation: detect reverse inner loop (`for c in range(cap, w-1, -1)`) as a knapsack signal.
- Cannot distinguish 0/1 from unbounded knapsack (the difference is iteration direction of inner loop).
- May miss knapsack where variable names don't include "weight" or "capacity". Use structural detection (subscript with variable-slice) instead.

---

### 2.6 dp_interval

#### Purpose

Detect interval DP where a 2D table is filled over subarray/substring intervals of increasing length. Characteristic of Matrix Chain Multiplication, Palindrome Partitioning II, Burst Balloons, Longest Palindromic Subsequence, and Stone Game.

#### Evidence Signals

| Evidence Type | Weight | Detection |
|---|---|---|
| `dp_array_2d` | 0.25 | `dp = [[0]*n for _ in range(n)]` |
| `length_based_loop` | 0.35 | Outer loop over `length` or `gap` variable: `for length in range(2, n+1)` — **primary structural signal** |
| `pair_loop` | 0.25 | Inner loop over interval start: `for i in range(n-length+1)` with `j = i+length-1` |
| `grid_lookback` | 0.25 | `dp[i][k] + dp[k+1][j]` or `dp[i+1][j]`, `dp[i][j-1]` — partition lookback |
| `recurrence_expression` | 0.25 | `max(dp[i][k] + dp[k+1][j] + cost)` or `min(dp[i][j], dp[i][k] + dp[k+1][j])` |
| `result_aggregation` | 0.15 | `return dp[0][n-1]` or `return dp[0][-1]` |

#### Gating Rules

**Core gate (mandatory):** `length_based_loop`

**Secondary (at least two):** `dp_array_2d` OR `pair_loop` OR `grid_lookback` OR `recurrence_expression` — at least two of these supporting signals must be present.

**Anti-gate:** If loops iterate over row/col indices (not length-based), skip (belongs to grid or string). If `capacity_compare`, skip (belongs to knapsack). If `string_compare`, skip (belongs to dp_2d_string).

#### False-Positive Prevention

| Risk | Mitigation |
|---|---|
| Grid DP with square matrix | Require length-based outer loop (`for l in range(2, n+1)` or `for gap in range(1, n)`). Grid uses row/col loops. |
| String DP with intervals | Require no string comparison. String DP uses char compare. |
| General pair iteration | Require 2D DP array. Pair iteration without DP table is not interval DP. |

#### Similar Detectors and Distinction

| Detector | Distinction |
|---|---|
| dp_2d_grid | Grid uses row/col loops. Interval uses length-based loops. |
| dp_2d_string | String uses char comparison. Interval uses pair cost calculation. |
| dp_knapsack | Knapsack uses capacity comparison. Interval has no weight concept. |

#### Known Limitations

- The length-based outer loop is the strongest structural signal, but its variable name (`length`, `gap`, `len`) is not reliable. The detection must look at how the loop variable is used (as a size, not an index).
- Cannot distinguish between minimize (palindrome partition) and maximize (matrix chain) variants.
- May miss interval DP where the outer loop iterates differently (e.g., decreasing length).

---

### 2.7 dp_state_machine

#### Purpose

Detect state-machine DP where a fixed, small number of states (typically 2-4) are tracked across iterations. Characteristic of Best Time to Buy/Sell Stock with Cooldown, House Robber (cyclic or with constraints), and Paint House.

#### Evidence Signals

| Evidence Type | Weight | Detection |
|---|---|---|
| `dp_array_1d` | 0.20 | Small fixed-size array: `dp = [0] * 2` or `dp = [0] * 3` |
| `state_variables` | 0.30 | Multiple scalar state variables: `hold`, `sold`, `rest` or `prev0`, `prev1`, `curr0`, `curr1` |
| `state_transition` | 0.30 | `max(prev_hold, prev_sold + price)` or `max(prev0, prev1 + val)` |
| `table_fill_loop` | 0.20 | Single loop iterating over input, updating states |
| `result_aggregation` | 0.20 | `return max(hold, sold)` or `return max(states)` |

#### Gating Rules

**Core gate (mandatory):** `state_variables` AND `state_transition`

**Secondary (at least one of):** `dp_array_1d`, `table_fill_loop`, `cache_decorator`. Array creation is strong evidence but not mandatory — pure state variable transitions are valid.

**Anti-gate:** If array size > 4 or tied to input size (not fixed), skip (belongs to 1D forward). If `has_nested_loops`, skip.

#### False-Positive Prevention

| Risk | Mitigation |
|---|---|
| Greedy stock trading | Greedy uses single variable (`max_profit`). State machine uses multiple state variables + max transitions. |
| 1D forward DP | Forward uses array indexed by input. State machine uses fixed small array (< 5) OR named state variables. |
| Simple iteration with two variables | Require max/min transition between at least 3 states or named state variables. |

#### Similar Detectors and Distinction

| Detector | Distinction |
|---|---|
| dp_1d_forward | Forward uses O(n) array indexed by input. State machine uses O(1) fixed states or named variables. |
| Greedy local | Greedy uses single running optimum. State machine uses multiple competing states. |

#### Known Limitations

- Detecting state machines without explicit `dp` array is difficult because the variables (`hold`, `sold`, `rest`) may not follow naming conventions.
- 2-state DP (House Robber) is structurally similar to simple iteration with two variables. The distinguishing signal is the presence of `max()`/`min()` transitions between states.
- Cannot detect state machines where states are represented as tuple assignments (e.g., `hold, sold = max(hold, sold - price), max(sold, hold + price)`). This is a valid Pythonic pattern but hard to distinguish from tuple-based swaps.

---

## 3. Evidence Table

### 3.1 Complete Evidence Signal Catalog

| ID | Evidence Type | Default Weight | Detection Method |
|---|---|---|---|
| E01 | `dp_array_1d` | 0.25 | List multiplication `[v] * (n+1)` or list comprehension of fixed size |
| E02 | `dp_array_2d` | 0.30 | Nested list comprehension `[[v]*m for _ in range(n)]` |
| E03 | `table_fill_loop` | 0.20 | For-loop iterating over DP array indices with write to `dp[i]` |
| E04 | `nested_fill_loops` | 0.25 | Two-level nested loop where inner writes to 2D or sequence DP |
| E05 | `index_lookback` | 0.30 | Subscript read `dp[i-1]`, `dp[i-2]`, `dp[i-k]` |
| E06 | `grid_lookback` | 0.25 | Subscript read `dp[r-1][c]`, `dp[r][c-1]`, `dp[r-1][c-1]` |
| E07 | `inner_lookback` | 0.25 | Read of `dp[j]` inside nested inner loop (sequence DP) |
| E08 | `recurrence_expression` | 0.20 | `max()`, `min()`, `+`, `or` combining multiple lookback terms |
| E09 | `max_min_recurrence` | 0.25 | `max()` or `min()` with DP lookback terms as arguments |
| E10 | `string_compare` | 0.30 | `s1[i] == s2[j]` or `s[i] == c` inside nested loop |
| E11 | `capacity_compare` | 0.30 | `if c >= weight[i]:` or capacity vs weight comparison |
| E12 | `length_based_loop` | 0.25 | Outer loop over `length` or `gap`: `for l in range(2, n+1)` |
| E13 | `pair_loop` | 0.20 | Inner loop with `i` and `j = i + length - 1` interval pair |
| E14 | `state_variables` | 0.30 | Multiple named state variables: `hold`, `sold`, `rest` or similar |
| E15 | `state_transition` | 0.30 | `max(state1, state2 + value)` updating state variables |
| E16 | `cache_decorator` | 0.30 | `@cache`, `@lru_cache` on function def |
| E17 | `manual_memo_check` | 0.25 | `if key in memo: return memo[key]` |
| E18 | `manual_memo_store` | 0.20 | `memo[key] = result` assignment |
| E19 | `base_case_return` | 0.15 | Conditional return for terminal subproblem |
| E20 | `result_aggregation` | 0.15 | `max(dp)`, `min(dp)`, `return dp[-1][-1]` |

### 3.2 Evidence Signal by Detector

| Detector | Core Signals | Supporting Signals | Optional Signals |
|---|---|---|---|
| dp_1d_forward | E05 (core) | E01, E03, E08, E16, E19, E20 | — |
| dp_1d_sequence | E04, E07 (core) | E01, E08, E09, E20 | — |
| dp_2d_grid | E04, E06 (core) | E02, E08, E19, E20 | — |
| dp_2d_string | E06, E10 (core) | E02, E04, E08, E19, E20 | — |
| dp_knapsack | E09, E11 (core) | E02, E04, E06, E08, E20 | — |
| dp_interval | E12 (primary core) | E02, E06, E08, E09, E13, E20 | — |
| dp_state_machine | E14, E15 (core) | E01, E03, E08, E16, E20 | — |

### 3.3 Weight Distribution Rules

- No single evidence item may exceed weight 0.30 (keeps detection distributed).
- The confidence cap is 1.0 (standard across all detectors).
- Evidence total must exceed 0.0 for detection (gated).
- Multiple occurrences of the same evidence type do not stack (binary: present or absent).

---

## 4. Detector Comparison Matrix

### 4.1 Structural Differentiators

| Feature | 1D Forward | 1D Sequence | 2D Grid | 2D String | Knapsack | Interval | State Machine |
|---|---|---|---|---|---|---|---|
| DP array dim | 1D | 1D | 2D | 2D | 2D | 2D | 1D or scalar |
| Loop depth | 1 | 2 | 2 | 2 | 2 | 2 | 1 |
| Loop type | Range | Nested | Row/Col | Row/Col | Item/Cap | Length/Pair | Single |
| Lookback type | `[i-1]` | `[j]` | `[r-1][c-1]` | `[i-1][j-1]` | `[i-1][c-w]` | `[i][k]+[k+1][j]` | Named vars |
| Recurrence op | + | max/min | min/max/+ | min/max/+ | max/min | max/min | max |
| Special signal | — | — | — | Char compare | Capacity comp | Length loop | State vars |

### 4.2 Anti-Signal Matrix

Each cell indicates: pattern on left should NOT detect if the column feature is present.

| Detector | 2D array | String compare | Capacity compare | Length loop | State vars | Nested loops |
|---|---|---|---|---|---|---|---|
| dp_1d_forward | — | — | — | — | — | BLOCK |
| dp_1d_sequence | BLOCK | — | — | — | — | REQUIRE |
| dp_2d_grid | — | BLOCK | BLOCK | BLOCK | — | REQUIRE |
| dp_2d_string | — | REQUIRE | BLOCK | BLOCK | — | REQUIRE |
| dp_knapsack | — | BLOCK | REQUIRE | — | — | REQUIRE |
| dp_interval | — | BLOCK | BLOCK | REQUIRE | — | REQUIRE |
| dp_state_machine | — | — | — | — | REQUIRE | BLOCK |

### 4.3 Overlap With Existing Detectors

| Existing Detector | Overlapping DP Pattern | Distinction |
|---|---|---|
| `brute_force` | Recursive Fibonacci (unmemoized) | Brute force fires on branching recursion. DP requires memo or table. |
| `dfs_recursive` | Tree path sum DP | DFS requires tree traversal + recursive call. DP requires table/cache. |
| `greedy_local` | Kadane's max subarray | Greedy uses single variable. DP_1D uses array and lookback. |
| `greedy_local` | Best time to buy/sell stock (single) | Greedy uses running min + max. State machine uses multiple hold/sold states. |
| `prefix_sum` | Contiguous sum | Prefix sum uses `dp[i] = dp[i-1] + arr[i]`. DP_1D forward requires lookback > 1 or max/min. |
| `backtracking_subset` | Subset sum DP | Backtracking uses append/pop recursion. DP uses table. |
| `sorting` | Sorting-based sequence | Sorting uses `.sort()` or `sorted()`. Sequence DP uses nested loops. |

---

## 5. Gate Rule Reference

### 5.1 Implementation Pattern

Every DP detector follows this implementation skeleton:

```python
def detect(self, ast_root: ast.AST) -> DetectionResult:
    evidence = []
    self._detect_dp_pattern(ast_root, evidence)

    confidence = self._calculate_confidence(evidence)

    has_core_a = any(e.type == "core_signal_a" for e in evidence)
    has_core_b = any(e.type == "core_signal_b" for e in evidence)
    has_secondary = any(e.type in ("signal_x", "signal_y") for e in evidence)

    # Gate: core AND secondary
    detected = (has_core_a and has_core_b) and has_secondary

    return DetectionResult(
        pattern_id=self.pattern_id,
        confidence=confidence,
        evidence=evidence,
        detected=detected,
    )
```

### 5.2 Gate Rules Summary

| Detector | Gate Condition |
|---|---|
| dp_1d_forward | `index_lookback` AND (`dp_array_1d` OR `table_fill_loop` OR `cache_decorator`) — at least two supporting signals. Array is strong but not mandatory. |
| dp_1d_sequence | `nested_fill_loops` AND `inner_lookback` AND (`dp_array_1d` OR `recurrence_expression` OR `result_aggregation`) — at least one of the supporting signals with nested loops as core. |
| dp_2d_grid | `grid_lookback` AND `nested_fill_loops` AND (`dp_array_2d` OR `recurrence_expression` OR `result_aggregation`) — at least one supporting signal. |
| dp_2d_string | `string_compare` AND `grid_lookback` AND (`dp_array_2d` OR `nested_fill_loops` OR `recurrence_expression` OR `base_case_return`) — at least one supporting signal. |
| dp_knapsack | `capacity_compare` AND `max_min_recurrence` AND (`dp_array_2d` OR `nested_fill_loops` OR `grid_lookback`) — at least one supporting signal. |
| dp_interval | `length_based_loop` AND at least two of: `dp_array_2d`, `pair_loop`, `grid_lookback`, `recurrence_expression`. Length-based loop is the primary structural signal. |
| dp_state_machine | `state_variables` AND `state_transition` AND (`dp_array_1d` OR `table_fill_loop` OR `cache_decorator`) — at least one supporting signal. | |

### 5.3 Confidence Thresholds

| Confidence | Meaning |
|---|---|
| 0.00 | Not detected (gate not passed or no evidence) |
| 0.01–0.39 | Below threshold — treated as not detected |
| 0.40–0.79 | Medium confidence — some signals present |
| 0.80–1.00 | High confidence — multiple strong signals |

Matching engine (MATCHING_ENGINE.md) only uses High confidence (>= 0.80) for pattern matching.

---

## 6. Known Ambiguities and Mitigations

### 6.1 Ambiguity: 1D Forward vs Prefix Sum

**Risk:** Both create a 1D array and fill it left-to-right.

**Mitigation:** Prefix sum fills `dp[i] = dp[i-1] + arr[i]` with NO branching (no max/min, no if-else). Forward DP requires either:
- Lookback of at least 2 levels (`dp[i-1]` AND `dp[i-2]`), OR
- `max()` or `min()` in the recurrence, OR
- A conditional in the recurrence

**Resolution:** Gate requires either multi-level lookback OR branching recurrence.

### 6.2 Ambiguity: 1D Forward vs Greedy Local

**Risk:** Kadane's algorithm uses `max()` and a loop.

**Mitigation:** Greedy local writes to scalar variables (`max_sum`, `curr_sum`). Forward DP writes to array elements (`dp[i]`). Check subscript write target.

**Resolution:** Gate requires subscript write (`dp[i] = ...`) rather than scalar assignment.

### 6.3 Ambiguity: 1D Forward vs 1D Sequence

**Risk:** Both use 1D array. Forward uses single loop. Sequence uses nested loops.

**Mitigation:** Check loop depth. If nested loops (depth >= 2), assign to sequence. If single loop, assign to forward.

**Resolution:** `nested_fill_loops` is a core signal for sequence but an anti-signal for forward.

### 6.4 Ambiguity: 2D Grid vs 2D String

**Risk:** Both use 2D array with nested loops and lookback.

**Mitigation:** Check for string comparison operators (`==` between character subscripts, `s1[i] == s2[j]`). Grid DP accesses numeric values.

**Resolution:** `string_compare` is a core signal for string DP and an anti-signal for grid DP.

### 6.5 Ambiguity: 2D Knapsack vs 2D Grid

**Risk:** Both use 2D array with nested loops and lookback.

**Mitigation:** Check for capacity comparison (`c >= weight[i]` or `w >= weights[j]`). Grid DP does not compare against a weight/capacity.

**Resolution:** `capacity_compare` is a core signal for knapsack and an anti-signal for grid.

### 6.6 Ambiguity: 2D Interval vs 2D Grid

**Risk:** Both use 2D array with nested loops.

**Mitigation:** Check outer loop structure. Interval uses length-based loop (`for length in range(2, n+1)`). Grid uses row/col index loops.

**Resolution:** `length_based_loop` is a core signal for interval and an anti-signal for grid.

### 6.7 Ambiguity: State Machine vs Greedy Stock

**Risk:** Best Time to Buy/Sell Stock can be solved greedily or with state machine.

**Mitigation:** Greedy uses single running max/min variable. State machine uses 2+ state variables with transition logic (`max(hold, sold + price)`).

**Resolution:** Require at least 2 named state variables OR fixed-size array of size 2-4. Single variable = greedy.

### 6.8 Ambiguity: Memoized DFS vs DP

**Risk:** DFS with `@cache` is mathematically DP but structurally looks like DFS.

**Mitigation:** If `@cache` or `@lru_cache` decorator is present AND the function has recursive calls AND the function returns a computation (not void), classify as memoized DP. If no cache decorator, classify as DFS.

**Resolution:** `cache_decorator` OR (`manual_memo_check` AND `manual_memo_store`) pushes classification toward DP.

### 6.9 Ambiguity: Space-Optimized 2D DP (1D Array)

**Risk:** Many 2D DP solutions use a 1D rolling array to save space (e.g., `dp = [0] * cols` with `dp[j] = f(dp[j], dp[j-1])`).

**Mitigation:** These will be structurally similar to 1D forward DP with lookback. The distinction is:
- The 1D array is sized to one dimension of a 2D problem (often `cols` of a grid).
- The recurrence uses `dp[j-1]` (horizontal lookback) and lookback to `dp[j]` from previous row (implicit).
- The outer loop iterates over rows.

**Resolution:** Space-optimized 2D DP is a known false-negative risk. The design acknowledges this will NOT be detected as 2D DP — it will fall into dp_1d_forward or be missed entirely. This is acceptable precision-over-recall behavior.

### 6.10 Ambiguity: `@cache` on Fibonacci vs dp_1d_forward

**Risk:** `@cache` on recursive Fibonacci will match memoization evidence but may also trigger DFS.

**Mitigation:** Gate on dp_array_1d OR (cache_decorator AND base_case_return) ensures cache-only code is detected if it has base cases. DFS requires traversal context (graph, tree, grid). Fibonacci has no traversal context.

**Resolution:** Fibonacci with `@cache` is correctly classified as dp_1d_forward (it IS DP — overlapping subproblems, optimal substructure).

---

## 7. Implementation Order Recommendation

The recommended implementation order minimizes ambiguity and maximizes test coverage:

| Order | Detector | Rationale |
|---|---|---|
| 1 | `dp_1d_forward` | Simplest DP pattern. Single loop, 1D array. Foundation for other DP detectors. |
| 2 | `dp_state_machine` | Also single loop, but with named state variables. Easy to implement after forward. |
| 3 | `dp_1d_sequence` | Introduces nested loops. Builds on forward detection infrastructure. |
| 4 | `dp_2d_grid` | Introduces 2D array detection. Most common 2D pattern. |
| 5 | `dp_2d_string` | Adds string comparison to grid infrastructure. Small delta from grid. |
| 6 | `dp_knapsack` | Adds capacity comparison. Distinct structural signal. |
| 7 | `dp_interval` | Most complex. Length-based loops, pair-based intervals, partition lookback. |

---

## Appendix: V1 Feature Mapping

The following mapping shows how V1 extractor features (used in classifier.py) map to V2 evidence signals. This ensures backward compatibility of detection philosophy.

| V1 Feature | V2 Evidence Signal | Notes |
|---|---|---|
| `has_dp_array` | `dp_array_1d` | V1 detects list multiplication `[0]*(n+1)` and list comprehension |
| `has_2d_array` | `dp_array_2d` | V1 detects nested list comprehension |
| `has_index_lookback` | `index_lookback` | V1 detects subscript read with `-` in index |
| `has_grid_lookback` | `grid_lookback` | V1 detects nested subscript read with `[r-1][c-1]` |
| `has_string_compare` | `string_compare` | V1 detects string variables with equality comparison |
| `has_capacity_compare` | `capacity_compare` | V1 detects capacity vs weight comparison in if-statement |
| `has_math_max_min` | `recurrence_expression` | V1 detects `max()`/`min()` calls |
| `max_loop_depth` | `nested_fill_loops` | V1 counts loop nesting depth |
| (new) | `length_based_loop` | Not in V1. New for interval DP. |
| (new) | `state_variables` | Not in V1. New for state machine. |
| (new) | `state_transition` | Not in V1. New for state machine. |
| (new) | `cache_decorator` | Not in V1. New for memoization. |
| (new) | `manual_memo_check` | Not in V1. New for memoization. |
| (new) | `manual_memo_store` | Not in V1. New for memoization. |
