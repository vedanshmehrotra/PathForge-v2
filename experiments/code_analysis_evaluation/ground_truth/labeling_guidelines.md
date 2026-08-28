# Ground Truth Labeling Guidelines

## Overview

This document defines what counts as evidence for each algorithmic concept in PathForge's evaluation benchmark. Labels must be based on the **actual submitted code**, not problem tags or editorial solutions.

## Core Principles

1. **Code-first**: Label what the code actually does, not what the problem "requires"
2. **Conservative**: If a concept is ambiguous, mark it as `uncertain`
3. **Structural evidence only**: Require structural/code evidence, not just variable names
4. **Multiple valid solutions**: A problem may have multiple correct approaches; label the submitted code, not the "expected" approach

## Concept Definitions

### hash_map_lookup
**Present when**: Code uses a dictionary (`dict`) or `defaultdict` to store values, then checks `key in dict` or `dict.get(key)` or `dict[key]` for lookup.

**NOT present when**: Dictionary is used only for counting (→ `hash_map_frequency`), or the lookup is incidental to the main algorithm.

**Evidence**: 
- `seen[x]` or `x in seen` pattern
- `cache = {}` followed by lookup
- `collections.defaultdict` used for value storage and retrieval

### hash_map_frequency
**Present when**: Code counts occurrences using a dictionary, `collections.Counter`, or `defaultdict(int)`.

**NOT present when**: Dictionary is used for lookup without counting pattern.

**Evidence**:
- `freq[char] += 1` or equivalent
- `Counter(some_list)`
- `defaultdict(int)` with increment pattern

### prefix_sum
**Present when**: Code maintains a running sum that accumulates over iterations, typically `prefix += nums[i]` or `running_sum += nums[i]`.

**NOT present when**: Sum is just a total (not used for prefix-style queries), or sum is computed but never queried.

**Evidence**:
- Accumulator variable updated in loop with `+=`
- Running sum used to compute subarray sums: `sum[j] - sum[i]`
- Variable named like `prefix`, `running_sum`, `total` that tracks cumulative sum

### sliding_window_fixed
**Present when**: Code uses a for-loop with constant offset index access (e.g., `arr[i+k]` or `arr[i]` and `arr[i-w]` together), maintaining a fixed-size window.

**NOT present when**: Variable-length window (→ `sliding_window_variable`), or simple array iteration without window concept.

**Evidence**:
- `for i in range(n)` with `arr[i]` and `arr[i-k]` access
- Window state maintained across iterations with fixed size
- Subarray/substring of fixed length being processed

### sliding_window_variable
**Present when**: Code maintains a window that expands and contracts based on a condition (usually `while` loop with `left` pointer adjustment).

**NOT present when**: Fixed window (→ `sliding_window_fixed`), or binary search pattern.

**Evidence**:
- `left` pointer that conditionally moves forward
- Window size changes based on condition
- `max_len` or similar tracking of best window seen

### two_pointers_opposite
**Present when**: Two index variables start at opposite ends (e.g., `left=0, right=n-1`) and converge toward each other.

**NOT present when**: Pointers move in same direction (→ `two_pointers_same`), or this is binary search (has midpoint calculation).

**Evidence**:
- `left < right` or `i < j` in while condition
- `left += 1` or `right -= 1` (opposite directions)
- No midpoint calculation (`(left+right)//2`) present

### two_pointers_same
**Present when**: Two pointers both move in the same direction, typically at different speeds (fast/slow) or for different purposes.

**NOT present when**: Opposite-direction convergence (→ `two_pointers_opposite`).

**Evidence**:
- Two index variables both incrementing
- One pointer advances faster than the other
- Used for cycle detection or merging sorted sequences

### dfs_recursive
**Present when**: Function calls itself (recursion) without state restoration after the recursive call, exploring paths depth-first.

**NOT present when**: State restoration pattern (→ backtracking), or memoization pattern (→ dp_top_down).

**Evidence**:
- Function defined with `def f(...)`
- Function calls itself within its body
- No `add()/append()` before call AND `remove()/pop()` after call pattern
- No cache lookup/write pattern

### dfs_iterative
**Present when**: Stack data structure used to simulate DFS traversal.

**Evidence**:
- `stack.append(node)` and `node = stack.pop()`
- LIFO processing order
- No queue usage

### bfs_level_order
**Present when**: Queue (deque) used to traverse graph/tree level by level.

**Evidence**:
- `deque` created, `queue.append()` and `queue.popleft()`
- Level-size tracking for level-order processing
- No `visited` set (if tree, not graph)

### bfs_shortest_path
**Present when**: BFS on a graph with distance/level tracking, typically for shortest path.

**Evidence**:
- `deque` for queue
- `visited` set to track explored nodes
- Distance tracking: `dist[neighbor] = dist[node] + 1`
- Graph adjacency structure

### topological_sort
**Present when**: Code computes ordering of DAG nodes, using in-degree tracking or DFS post-order.

**Evidence**:
- `in_degree` computation
- Processing nodes with `in_degree == 0`
- Result is an ordering list

### union_find
**Present when**: Disjoint set data structure with parent array and union/find operations.

**Evidence**:
- `parent[i] = i` initialization
- `while parent[x] != x: x = parent[x]` (path chasing)
- `parent[a] = b` (union)
- Optional: `rank` or `size` array

### dp_1d_forward
**Present when**: 1D array `dp` where `dp[i]` depends on earlier entries, filled left to right.

**Evidence**:
- `dp = [0] * (n+1)` or similar initialization
- `dp[i] = ... dp[i-1] ...` or `dp[i] = ... dp[j] ...` for j < i
- Linear iteration filling the array

### dp_1d_sequence
**Present when**: 1D DP on a sequence (not necessarily left-to-right filling).

**Evidence**:
- Array-based DP
- Recurrence relation visible in code

### dp_2d_grid
**Present when**: 2D array `dp[i][j]` where each cell depends on neighbors, used for grid path problems.

**Evidence**:
- `dp = [[0]*m for _ in range(n)]` or similar
- Nested loops over `i` and `j`
- `dp[i][j] = ... dp[i-1][j] ... dp[i][j-1] ...` or similar

### dp_2d_string
**Present when**: 2D DP on string characters, for LCS, edit distance, etc.

**Evidence**:
- `dp[i][j]` where `i` and `j` index into strings
- String-specific operations: `s[i] == t[j]`, `s1[i-1]`

### dp_knapsack
**Present when**: 0/1 knapsack or unbounded knapsack pattern.

**Evidence**:
- Nested loop: outer over items, inner over capacity
- `dp[j] = max(dp[j], dp[j-w] + v)` or similar
- Weight/value variables

### dp_interval
**Present when**: DP on intervals `dp[i][j]` where interval length increases.

**Evidence**:
- `for length in range(1, n+1): for i in range(n-length+1):`
- `dp[i][j]` depends on `dp[i+1][j-1]` or similar

### dp_state_machine
**Present when**: DP with explicit states (e.g., hold/sold for stock problems).

**Evidence**:
- Named state variables: `hold`, `sold`, `cooldown`
- State transitions between iterations
- `max()` choosing between states

### fast_slow_pointers
**Present when**: Two pointers moving at different speeds, typically for cycle detection.

**Evidence**:
- `slow = slow.next` and `fast = fast.next.next`
- While loop with `slow != fast`
- Linked list traversal

### linked_list_reversal
**Present when**: In-place reversal of linked list pointers.

**Evidence**:
- Three pointers: `prev`, `curr`, `next`
- `curr.next = prev` pattern
- `prev = curr; curr = next` advancement

### monotonic_stack
**Present when**: Stack that maintains monotonic order, popping elements that violate monotonicity.

**Evidence**:
- Stack with `append`/`pop`
- While loop comparing with `stack[-1]`
- Elements popped based on comparison with current element

### monotonic_deque
**Present when**: Deque maintaining monotonic order for sliding window max/min.

**Evidence**:
- `deque` with `append`/`popleft`
- Back elements removed to maintain monotonicity
- Front element gives current window max/min

### binary_search_standard
**Present when**: Standard binary search on sorted array or search space.

**Evidence**:
- `left`, `right` pointers
- `mid = (left + right) // 2`
- Conditional narrowing: `if arr[mid] < target: left = mid + 1`

### binary_search_rotated
**Present when**: Binary search on rotated sorted array.

**Evidence**:
- Binary search structure
- Additional condition checking which half is sorted
- `if nums[left] <= nums[mid]` type logic

### binary_search_answer
**Present when**: Binary search on answer space (not array indices).

**Evidence**:
- `left`, `right` represent answer bounds
- `check(mid)` or `is_valid(mid)` function
- Answer is the boundary value

### heap_top_k
**Present when**: Priority queue / heap used for top-K or similar.

**Evidence**:
- `heapq.heappush` / `heapq.heappop`
- `heapq.nlargest` / `heapq.nsmallest`
- Min/max heap operations

### greedy_local
**Present when**: Local optimal choice at each step, without backtracking.

**Evidence**:
- Sort then iterate making local best choice
- No recursion or dynamic programming
- `if/else` making choice based on local information

### greedy_interval
**Present when**: Interval scheduling, activity selection, or merge intervals.

**Evidence**:
- Sort by start/end time
- Iterate comparing current interval with previous
- `intervals.sort(key=lambda x: x[1])` type pattern

### backtracking_permutation
**Present when**: Generate all permutations using recursion with state restoration.

**Evidence**:
- `path.append(x)` before recursive call
- `path.pop()` after recursive call
- `if not path` base case
- Permutations of all elements

### backtracking_subset
**Present when**: Generate all subsets using recursion with state restoration.

**Evidence**:
- `path.append(x)` before recursive call
- `path.pop()` after recursive call
- Decision: include or exclude each element
- `start` parameter to avoid duplicates

## Uncertain Cases

When a concept is present but ambiguous, mark as `uncertain` and provide reasoning:

- **Multiple interpretations**: Code could be interpreted as multiple concepts
- **Incidental presence**: Concept appears but isn't central to the algorithm
- **Non-standard implementation**: Implementation doesn't match typical patterns

## Label Format

```json
{
  "submission_id": "...",
  "present": ["concept1", "concept2"],
  "absent": ["concept3", "concept4"],
  "uncertain": ["concept5"],
  "reasoning": {
    "concept1": "Brief explanation of evidence found",
    "concept5": "Why this is ambiguous"
  },
  "solution_correctness": "correct|incorrect|unknown",
  "primary_algorithm": "The main algorithmic approach used",
  "code_style_notes": "Any notable style characteristics"
}
```
