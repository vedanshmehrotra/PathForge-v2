# PathForge Technique & Strategy Vocabulary v1

**Date:** August 22, 2026
**Status:** Updated to match Phase 2B audited implementation
**Depends on:** `PATHFORGE_ANALYSIS_ARCHITECTURE_V1.md` (frozen), `PATHFORGE_ARCHITECTURE_FEASIBILITY_AUDIT.md`

---

## 1. Design Principles

### 1.1 Technique admission rule (from architecture §5.1)

A concept is admitted as a technique **only if** all four conditions hold:

1. **Multi-fact composition.** It is composed from at least two lower-level structural facts.
2. **Cross-context recurrence.** It genuinely recurs across more than one strategy or problem context.
3. **Non-implication.** Its presence does not, by itself, imply one unique algorithmic strategy.
4. **Bounded specificity.** Its evidentiary specificity is understood and bounded.

Additional guardrails from the user's task specification:

- A technique must NOT depend on variable naming.
- A technique must NOT depend on one exact AST shape.
- A technique must NOT smuggle algorithmic intent into the structural-fact layer.
- A technique must be writable as explicit, testable conditions.

### 1.2 What a technique is NOT

- **Not a generic primitive.** A single structural fact (e.g., `membership_check`) is not a technique.
- **Not a synonym for a strategy.** If the name is interchangeable with a strategy name (e.g., `prefix_sum` as a technique when it is the strategy itself), it is rejected.
- **Not a problem-specific idiom.** If it only appears in one problem type, it is rejected.
- **Not an implementation detail.** If it describes how rather than what (e.g., `visited_tracking` as a data-structure choice), it is rejected.

### 1.3 Strategy rule (from architecture §6.1)

A strategy must be defined by:

- A combination of technique evidence (at least one technique).
- Required structural constraints (facts about the code shape).
- Optional supporting evidence.
- Relevant problem context when necessary (but kept minimal for V1).

A single technique must not be sufficient to classify a strategy.

---

## 2. Structural Facts Assumed

The following structural facts from architecture §4.1 are assumed to be extractable. These are the primitives that techniques compose from.

### 2.1 Fact vocabulary (from architecture)

| Fact ID | Meaning |
|---|---|
| `loop_shape` | `for` / `while`, nesting depth, boundedness where mechanically decidable |
| `constant_step_update` | Variable changed by a literal constant step (`i += 1`, `i = i + 1`) |
| `indexed_access` | Variable used in collection indexing (`arr[i]`) |
| `linked_structure_traversal` | Explicit `.next`, `.left`, `.right` attribute access |
| `membership_check` | `in` / `not in` comparison |
| `container_type_observation` | list/dict/set/heap/queue where statically knowable |
| `container_operation` | lookup, insert, delete, push, pop, etc. |
| `accumulator_update` | Variable updated from its prior value through a recognized operator |
| `self_recursive_call` | Function directly calls itself |
| `early_termination` | Loop/function exits before ordinary completion (break, return in loop) |
| `control_dependency` | A value influences a branch/loop condition |
| `return_dependency` | A value contributes to returned output |
| `comparison_operation` | Comparison operators (`<`, `>`, `<=`, `>=`, `==`, `!=`) |
| `augmented_assignment` | `+=`, `-=`, `*=`, etc. on a variable |

### 2.2 Additional facts needed for technique detection

These are not in the architecture's initial fact vocabulary but are needed to detect the techniques defined below. They are all deterministic and mechanically decidable.

| Fact ID | Meaning | Why needed |
|---|---|---|
| `comparison_in_loop_condition` | A while-loop condition contains a comparison expression | Boundary narrowing, bidirectional scan |
| `index_variable_in_comparison` | A variable used in a loop condition is also modified in the loop body | Boundary narrowing, bidirectional scan |
| `opposite_direction_updates` | Two variables in the same loop body are updated in opposite directions (one +=, one -=) | Bidirectional index scan |
| `conditional_index_update` | An index/pointer variable is updated inside a conditional branch (`if`/`else`) within a loop | Loop-state tracking, bidirectional scan |
| `recursive_call_in_conditional` | A self-recursive call appears inside a conditional branch | Recursive branching |
| `multiple_recursive_paths` | A function has two or more recursive call sites with different arguments | Recursive branching |
| `node_attribute_access` | `.next`, `.left`, `.right` attribute access on a variable | Carry propagation |
| `accumulator_in_loop` | A variable is updated by `+=` (or similar) inside a loop body, and that variable is read on the right side of the update | Sequential accumulation |
| `loop_variable_in_update` | The loop iteration variable (or an index derived from it) appears in the expression that updates an accumulator | Sequential accumulation |

---

## 3. Final Technique Vocabulary

### 3.1 T1: `sequential_accumulation`

**Name:** Sequential Accumulation
**Category:** Control-flow / data-flow composite

**Definition:**
A loop iterates over a sequence, and a running accumulator variable is updated each iteration by combining its prior value with the current element or an index-derived value.

**Required structural facts:**
1. `loop_shape` — a `for` or `while` loop exists
2. `accumulator_update` — a variable is updated via `x = x + ...` or `x += ...`
3. `loop_variable_in_update` — the loop variable or a value derived from it appears in the accumulator's update expression

**Optional supporting facts:**
- `indexed_access` — the loop uses index-based access to a collection
- `comparison_operation` — a conditional determines whether the accumulation happens

**Negative / exclusion conditions:**
- The accumulator must be read on the right side of its own update (self-referential). A simple `total += value` where `total` is not otherwise used does NOT qualify if `total` is only written.
- If the accumulator update involves a subscript lookback on an array (e.g., `prefix[i] = prefix[i-1] + nums[i]`), this is `iterative_table_filling` (a strategy), not this technique.

**What it DOES imply:**
- The code builds a running result from sequential input
- The computation has sequential data dependency

**What it DOES NOT imply:**
- Any specific algorithm (not prefix sum, not DP, not binary search)
- Hash-based lookup
- Two-pointer movement
- Any specific data structure

**Example problems / strategies where it recurs:**
- Prefix sum arrays (as part of the `dp_bottom_up` strategy)
- Running maximum / minimum tracking (as part of greedy strategies)
- Sequential sum with early exit (as part of `sliding_window`)
- Problem 2996 first loop: `summ += nums[i]` while elements are consecutive
- Any problem that builds a running aggregate

**Confidence / specificity assessment:**
- **Low specificity.** This is a common idiom. By itself, it implies very little about the algorithm.
- **High reliability.** The three required facts are all mechanically detectable from AST.
- **Cross-context recurrence: HIGH.** Appears in DP, greedy, sliding window, prefix sum, and ad-hoc accumulation.

**False-positive concern:**
A simple `for x in arr: total += x` without any conditional would fire. This is correct — it IS sequential accumulation. The technique does not claim to identify an algorithm; it claims to identify a computational pattern.

---

### 3.2 T2: `boundary_narrowing`

**Name:** Boundary Narrowing
**Category:** Control-flow / comparison composite

**Definition:**
A while-loop condition compares two index or pointer variables, and at least one of those variables is updated in the loop body to narrow the range between them.

**Required structural facts:**
1. `loop_shape` — a `while` loop exists
2. `comparison_in_loop_condition` — the while condition contains a comparison (`<`, `<=`, `>`, `>=`)
3. `index_variable_in_comparison` — at least one variable in the comparison is modified in the loop body

**Optional supporting facts:**
- `constant_step_update` — the update is a constant step (e.g., `mid = (lo + hi) // 2`)
- `conditional_index_update` — the update is inside a conditional branch

**Negative / exclusion conditions:**
- The comparison must involve at least one variable that is also updated. A `while len(arr) > 0` where `len(arr)` is never modified does NOT qualify.
- The comparison must be between two variables (or a variable and a bound), not a constant check like `while i < 10` where `i` is not updated.

**What it DOES imply:**
- The loop progressively narrows a search range or convergence region
- The termination depends on the relationship between two bounded quantities

**What it DOES NOT imply:**
- Any specific algorithm (not binary search, not two-pointers, not sliding window specifically)
- That the narrowing is by a fixed step
- That the search is for a specific value

**Example problems / strategies where it recurs:**
- Binary search (as part of `binary_search` strategy)
- Sliding window (as part of `sliding_window` strategy, where left/right converge or diverge)
- Two pointers opposite (as part of `two_pointers_opposite` strategy)
- Any loop that terminates when two indices meet or cross

**Confidence / specificity assessment:**
- **Medium specificity.** More specific than generic loop, but appears in multiple distinct strategies.
- **High reliability.** The while-loop + comparison + variable-update pattern is mechanically detectable.
- **Cross-context recurrence: HIGH.** Binary search, sliding window, and two-pointer strategies all use this.

**False-positive concern:**
A `while left < right` in a two-pointer problem fires. This is correct — it IS boundary narrowing. The two-pointer strategy will be identified by the additional `opposite_direction_updates` fact.

---

### 3.3 T3: `bidirectional_index_scan`

**Name:** Bidirectional Index Scan
**Category:** Control-flow / pointer-direction composite

**Definition:**
Within a single loop, two index or pointer variables are updated in opposite directions — one advances (increment) while the other retreats (decrement). The loop condition compares these two variables.

**Required structural facts:**
1. `loop_shape` — a `while` or `for` loop exists
2. `comparison_in_loop_condition` — the loop condition compares two variables
3. `opposite_direction_updates` — one variable is incremented (`+= 1` or `= ... + 1`) while another is decremented (`-= 1` or `= ... - 1`) within the same loop body or its branches

**Optional supporting facts:**
- `conditional_index_update` — the updates are in if/else branches (typical of two-pointers and binary search)
- `constant_step_update` — the step is exactly ±1

**Negative / exclusion conditions:**
- Both variables must be updated. If only one variable moves, this does NOT fire (that is `boundary_narrowing` alone).
- The updates must be in opposite directions. Two increments (e.g., slow/fast pointers) do NOT qualify.

**What it DOES imply:**
- The code scans a range from both ends or narrows from both sides
- The two indices converge toward each other

**What it DOES NOT imply:**
- Any specific algorithm (not binary search specifically, not two-pointers specifically)
- That the convergence is symmetric
- That the comparison is `<` vs `<=` vs `!=`

**Example problems / strategies where it recurs:**
- Two pointers opposite direction (as part of `two_pointers_opposite` strategy)
- Binary search (left/right convergence — as part of `binary_search` strategy)
- Container with most water, valid palindrome, 3Sum, etc.

**Confidence / specificity assessment:**
- **Medium-high specificity.** Requires three specific structural facts.
- **High reliability.** The opposite-direction update pattern is mechanically detectable from augmented assignment operators.
- **Cross-context recurrence: MEDIUM.** Appears in binary search and two-pointers, which are distinct strategies. The additional strategy constraints (midpoint calculation, comparison structure) differentiate them.

**False-positive concern:**
Binary search with `left = mid + 1` and `right = mid - 1` fires. This is correct. The `binary_search` strategy requires the additional `midpoint_calculation` structural fact to distinguish from two-pointers-opposite.

---

### 3.4 T4: `recursive_branching`

**Name:** Recursive Branching
**Category:** Control-flow / recursion composite

**Definition:**
A function calls itself (direct recursion), and the recursive calls appear in at least two distinct code paths — either through conditional branching (`if`/`else`) or through multiple call sites with different arguments.

**Required structural facts:**
1. `self_recursive_call` — the function calls itself
2. `recursive_call_in_conditional` OR `multiple_recursive_paths` — the recursive calls are not all in a single unconditional path

**Optional supporting facts:**
- `early_termination` — base-case checks that prevent infinite recursion
- `container_operation` — state is saved/restored around recursive calls (backtracking)
- `control_dependency` — the branching decision depends on a value from the input

**Negative / exclusion conditions:**
- Simple linear recursion (one call site, no branching) does NOT qualify. Example: `def f(n): return n * f(n-1)` — this is tail recursion, not branching.
- Mutual recursion (A calls B calls A) does NOT qualify for this technique — that is a different structural pattern.

**What it DOES imply:**
- The computation explores multiple paths or subproblems
- The algorithm has a tree-shaped call structure

**What it DOES NOT imply:**
- Any specific algorithm (not DFS, not backtracking, not DP specifically)
- That the recursion terminates (base cases are optional supporting facts)
- That the recursion is depth-first

**Example problems / strategies where it recurs:**
- DFS backtracking (as part of `dfs_backtracking` strategy)
- DP top-down memoization (as part of `dp_top_down` strategy)
- N-queens, permutations, subsets, combination sum
- Any problem with a decision tree

**Confidence / specificity assessment:**
- **Medium specificity.** Appears in both backtracking and DP strategies.
- **High reliability.** Recursive calls and branching are mechanically detectable.
- **Cross-context recurrence: HIGH.** DFS backtracking and DP top-down both use this.

**False-positive concern:**
A Fibonacci implementation with `return f(n-1) + f(n-2)` fires. This is correct — it IS recursive branching. The `dp_top_down` strategy requires additional facts (cache/memoization, base case) to classify it as DP.

---

### 3.5 T5: `carry_propagation`

**Name:** Carry / State Propagation
**Category:** Data-flow / structure composite

**Definition:**
A loop traverses a linked structure (via `.next`, `.left`, `.right` attribute access) while simultaneously updating a carry, state, or accumulator variable that propagates across iterations.

**Required structural facts:**
1. `linked_structure_traversal` — `.next`, `.left`, or `.right` attribute access exists
2. `accumulator_update` — a variable is updated across iterations via `+=` or assignment
3. `loop_shape` — the traversal is inside a loop

**Optional supporting facts:**
- `control_dependency` — the carry/state influences a conditional (e.g., `carry > 0`)
- `container_operation` — new nodes or containers are constructed during traversal
- `early_termination` — traversal stops before the end of the structure

**Negative / exclusion conditions:**
- Pure linked-list traversal without carry/state does NOT qualify (e.g., just printing values).
- Pointer rewiring (e.g., `node.next = prev`) does NOT qualify — that is `linked_list_reversal`, not carry propagation.

**What it DOES imply:**
- The code traverses a linked structure while maintaining running state
- The state carries information from one node to the next

**What it DOES NOT imply:**
- Linked list reversal
- Any specific algorithm (not add-two-numbers specifically)
- That the structure is a linked list (could be a tree)

**Example problems / strategies where it recurs:**
- Add Two Numbers (carry propagation through linked list)
- Add two numbers represented as linked lists
- Merge two sorted linked lists (state = comparison result)
- Flatten a multilevel doubly linked list

**Confidence / specificity assessment:**
- **High specificity.** Requires linked structure traversal AND state accumulation together.
- **Medium reliability.** The `.next`/`.left`/`.right` detection is reliable; carry detection needs care to distinguish from simple accumulation.
- **Cross-context recurrence: MEDIUM.** Appears in multiple linked-list problems but not in array/graph problems.

**False-positive concern:**
Iterating through a tree with `.left`/`.right` and accumulating a sum fires. This is correct — it IS carry/state propagation through a linked structure. The technique does not claim to identify the specific problem.

---

### 3.6 T6: `loop_state_tracking`

**Name:** Loop-State Tracking
**Category:** Control-flow / state composite

**Definition:**
Within a loop, at least one state variable is updated based on a condition that involves the loop variable, an index derived from it, or another state variable. The state variable's value affects subsequent iterations (e.g., it controls an inner loop, a conditional update, or the outer loop's termination).

**Required structural facts:**
1. `loop_shape` — a loop exists
2. `conditional_index_update` — a variable is updated inside a conditional branch within the loop
3. `control_dependency` — the conditional depends on the loop variable, an index, or another loop-varying value

**Optional supporting facts:**
- `indexed_access` — the state variable is used to index into a collection
- `membership_check` — the state is checked against a collection
- `comparison_operation` — the state influences a comparison

**Negative / exclusion conditions:**
- A simple `if x > threshold: result += 1` where `result` is not reused does NOT qualify — the state must affect subsequent computation.
- The state must be updated conditionally based on the loop variable or an index. Unconditional updates do NOT qualify.

**What it DOES imply:**
- The loop maintains mutable state that adapts based on what it has seen
- The algorithm has a "window" or "running context" that evolves

**What it DOES NOT imply:**
- Any specific algorithm (not sliding window, not two-pointers specifically)
- That the state is a data structure (could be a simple variable)
- That the state is always updated (could be updated conditionally)

**Example problems / strategies where it recurs:**
- Sliding window (as part of `sliding_window` strategy — left pointer tracks window boundary)
- Two pointers (as part of `two_pointers_opposite` strategy — both pointers are state)
- BFS with distance tracking (distance is updated per level)
- Any problem where a loop variable controls which state variables change

**Confidence / specificity assessment:**
- **Medium specificity.** Appears in sliding window, two-pointers, and BFS.
- **Medium reliability.** The conditional-update + control-dependency pattern requires careful detection.
- **Cross-context recurrence: HIGH.** Multiple distinct strategies use this.

**False-positive concern:**
A sliding window where `left += 1` inside `if window_sum > target` fires. This is correct — it IS loop-state tracking. The `sliding_window` strategy requires the additional `sequential_accumulation` technique and specific window operations to classify it.

---

### 3.7 T7: `iterative_table_filling`

**Name:** Iterative Table Filling
**Category:** Control-flow / data-structure composite

**Definition:**
A loop iterates over index ranges, and a data structure (array or table) is built by writing values that depend on previously computed entries via index lookback (accessing earlier indices of the same structure).

**Required structural facts:**
1. `loop_shape` — a `for` or `while` loop exists (often nested)
2. `indexed_access` — the code reads from a data structure using index expressions
3. `accumulator_update` — values are written to the structure based on read values
4. `loop_variable_in_update` — the loop index or a derived value is used in the subscript expressions

**Optional supporting facts:**
- `comparison_operation` — conditions determine which recurrence is applied
- `container_type_observation` — a list or 2D array is created before the loop

**Negative / exclusion conditions:**
- Simple prefix sum (`prefix[i] = prefix[i-1] + nums[i]`) is a borderline case. It IS iterative table filling. The `dp_bottom_up` strategy can claim it, but if the table is only 1D and has no branching, it may be more accurately described as `sequential_accumulation` with indexed access.
- Hash-map-based prefix sum (using a dict for lookback) is NOT iterative table filling — that is `frequency_counting`-adjacent.

**What it DOES imply:**
- The code builds a solution table from smaller subproblems
- There is data dependency between table entries

**What it DOES NOT imply:**
- Any specific DP variant (top-down vs bottom-up)
- That the table is 2D
- That the problem is "dynamic programming" (the label)

**Example problems / strategies where it recurs:**
- DP bottom-up (as the core of `dp_bottom_up` strategy)
- Coin change, house robber, longest increasing subsequence
- Any problem with overlapping subproblems solved iteratively

**Confidence / specificity assessment:**
- **High specificity.** Requires four structural facts.
- **Medium-high reliability.** Indexed access + accumulator + loop variable is detectable.
- **Cross-context recurrence: MEDIUM.** Primarily in DP, but also in prefix sum construction.

**False-positive concern:**
Building a prefix sum array fires. This is correct — it IS iterative table filling. The `dp_bottom_up` strategy requires additional facts (nested loops, branching, or 2D structure) to distinguish from simple sequential accumulation.

---

## 4. Rejected Technique Candidates

| Candidate | Reason for rejection |
|---|---|
| `array_traversal` | Generic primitive (§2.1 fact `loop_shape` + `indexed_access`). Not a composite technique. Would match almost every loop. |
| `hash_map_lookup` | Describes data-structure behavior, not a reusable technique. The architecture explicitly says this is "reusable data-structure behavior rather than one algorithmic strategy" (§2.3). |
| `prefix_sum_accumulation` | The architecture says "prefix sum is better treated as a reusable technique" (§2.3) but this is really the `dp_bottom_up` strategy in its simplest form. It is too specific — it implies a particular data structure (prefix array). `sequential_accumulation` covers the general case. |
| `visited_tracking` | Single fact (container operation with a "visited" semantic). Does not compose multiple facts. The architecture says "DFS/BFS may use a visited set without being a hash-map algorithm" (§2.2) — the visited set is an implementation detail, not a technique. |
| `frequency_counting` | Single fact (container operation + increment). Too specific to hash-map problems. Would be a synonym for a strategy. |
| `memoization` | Synonym for DP top-down strategy. The technique is `recursive_branching` + caching (which is a structural fact, not a separate technique). |
| `backtracking_state_restore` | Implementation detail (copy + restore). Only appears in one strategy (backtracking). Too narrow. |
| `heap_order_maintenance` | Only appears in heap/priority-queue strategies. Too narrow for V1. Can be added later if needed. |
| `monotonic_structure_maintenance` | Only appears in monotonic stack/deque strategies. Too narrow. The monotonic comparison fact already exists in the fact layer. |
| `two_pointer_scan` | This is the `two_pointers_opposite` strategy itself, not a technique. The technique is `bidirectional_index_scan`. |
| `sliding_window_maintenance` | This is the `sliding_window` strategy itself, not a technique. The techniques are `loop_state_tracking` + `boundary_narrowing`. |
| `boundary_narrowing` (as standalone) | Already defined as T2. The architecture's candidate list is validated. |

---

## 5. Final Strategy Vocabulary

### 5.1 S1: `binary_search`

**Name:** Binary Search
**Definition:**
A search strategy that repeatedly halves a search range by comparing a midpoint value against a target, narrowing the range based on the comparison result.

**Required techniques:**
- None required (uses structural facts directly)

**Required structural constraints:**
- `midpoint_calculation` fact — `(lo + hi) // 2` or `lo + (hi - lo) // 2` or equivalent
- `while_loop_comparison` fact — while-loop with comparison on index variables
- `conditional_index_update` fact — if/elif/else branches updating indices

**Absence constraints:**
- Must NOT have `opposite_direction_updates` (distinguishes from two-pointers)

**Optional techniques:**
- `bidirectional_index_scan` (T3) — left/right convergence with opposite updates

**Relevant problem-context tags:**
- `sorted_input` (confirmed) — strengthens the evidence but is NOT required

**Known confusing strategies:**
- `two_pointers_opposite` — both use boundary narrowing with two indices. The distinguishing constraint is the midpoint calculation: binary search computes a midpoint; two-pointers-opposite does not.
- `sliding_window` — both use boundary narrowing. The distinguishing constraint is that binary search uses a while-loop with index comparison; sliding window typically uses a for-loop with an inner while.

**Why the combination is distinctive:**
Midpoint calculation + while-loop comparison + conditional index update is the structural signature of binary search. No other strategy computes a midpoint to divide a range.

**Implementation note:**
Binary search uses structural facts directly (midpoint_calculation + while_loop_comparison + conditional_index_update) rather than the `boundary_narrowing` technique. The `boundary_narrowing` concept is captured by the fact combination.

---

### 5.2 S2: `sliding_window`

**Name:** Sliding Window
**Definition:**
A strategy that maintains a contiguous subsequence (window) of a collection, expanding the right boundary and conditionally contracting the left boundary based on a state condition.

**Required techniques:**
- `loop_state_tracking` (T6) — the left boundary or window state is conditionally updated

**Required structural constraints:**
- `variable_use_in_loop_body` fact — the conditionally-updated variable is used in a later expression within the same loop
- A loop (while or for) with conditional index update

**Absence constraints:**
- Must NOT have `opposite_direction_updates` (distinguishes from two-pointers)
- Must NOT have `midpoint_calculation` (distinguishes from binary search)

**Optional techniques:**
- `boundary_narrowing` (T2) — if an inner while-loop contracts the window

**Relevant problem-context tags:**
- None required for V1 (detectable from code structure alone)

**Known confusing strategies:**
- `two_pointers_opposite` — both involve two indices and conditional updates. The distinguishing constraint is that sliding window uses a for-loop with the right pointer advancing every iteration; two-pointers-opposite uses a while-loop with both pointers moving conditionally.
- `binary_search` — both narrow boundaries. Sliding window maintains a window; binary search halves a range.

**Why the combination is distinctive:**
Conditional state tracking + variable use in later expression is the structural signature of sliding window. The right pointer always advances (sequential), while the left pointer adjusts based on a condition (state tracking). This asymmetric advance-and-adjust pattern is unique to sliding window.

**Implementation note:**
Sliding window uses `loop_state_tracking` technique + `variable_use_in_loop_body` fact rather than requiring `sequential_accumulation` technique. The `variable_use_in_loop_body` fact captures the def-use chain where the updated variable appears in a later expression (e.g., `max(max_len, right - left + 1)`).

---

### 5.3 S3: `two_pointers_opposite`

**Name:** Two Pointers (Opposite Direction)
**Definition:**
A strategy where two indices start at opposite ends of a range and converge toward each other, with each index moving based on a comparison of the values at the two positions.

**Required techniques:**
- `bidirectional_index_scan` (T3) — two indices updated in opposite directions

**Required structural constraints:**
- While-loop with comparison on the two index variables
- The loop body updates one or both indices conditionally based on the comparison

**Optional techniques:**
- `boundary_narrowing` (T2) — the while-loop condition narrows the range

**Relevant problem-context tags:**
- None required for V1

**Known confusing strategies:**
- `binary_search` — both converge two indices. The distinguishing constraint is that two-pointers-opposite does NOT compute a midpoint; binary search DOES.
- `sliding_window` — both use two indices. Two-pointers-opposite starts at opposite ends and converges; sliding window starts at the same end and expands/contracts.

**Why the combination is distinctive:**
Bidirectional index scan + convergence without midpoint calculation is unique to two-pointers-opposite. The absence of midpoint computation and the presence of value-dependent conditional updates distinguish it from binary search.

---

### 5.4 S4: `dfs_backtracking`

**Name:** DFS / Backtracking
**Definition:**
A strategy that explores a decision tree by making a choice, recursing into subproblems, and restoring state before exploring alternative choices.

**Required techniques:**
- `recursive_branching` (T4) — preferred, but NOT strictly required

**Required structural constraints:**
- `self_recursive_call` fact — function calls itself
- `early_termination` fact — base case (return or conditional stop)
- `state_restoration` fact — state is modified before recursion (add/append) and restored after (remove/pop)

**Absence constraints:**
- Must NOT have `cache_lookup` or `cache_write` (cache = DP, not backtracking)

**Optional techniques:**
- `loop_state_tracking` (T6) — if the recursion explores a set of candidates via iteration

**Relevant problem-context tags:**
- None required for V1

**Known confusing strategies:**
- `dp_top_down` — both use recursive branching. The distinguishing constraint is that DFS/backtracking does NOT use memoization; DP top-down DOES.
- `bfs_traversal` — both explore graphs/trees. DFS uses recursion (or explicit stack); BFS uses a queue.

**Why the combination is distinctive:**
Self-recursive call + state restoration (no memoization) is the structural signature of backtracking. The absence of a cache/memo structure distinguishes it from DP top-down.

**Implementation note (V1 fallback path):**
The `recursive_branching` technique fires only for functions with multiple recursive call sites or conditional branching around recursion. Standard backtracking (single recursive call inside a for-loop) does NOT trigger `recursive_branching`. The implementation uses a fallback path: `self_recursive_call + early_termination + state_restoration` (facts directly) when `recursive_branching` is not detected. This is architecturally valid per §6.1, which allows strategies to combine techniques AND structural constraints.

---

### 5.5 S5: `bfs_shortest_path`

**Name:** BFS / Shortest Path
**Definition:**
A strategy that explores a graph or tree level by level using a queue, tracking distance from the source to find shortest paths.

**Required techniques:**
- None of the seven techniques are required (BFS uses queue operations, which are structural facts, not techniques)

**Required structural constraints:**
- Queue creation (deque, Queue, or list used as queue)
- Dequeue operation (popleft or equivalent)
- Level or distance tracking variable that increments per level
- Visited tracking (set or array)

**Optional techniques:**
- `loop_state_tracking` (T6) — if distance is updated conditionally

**Relevant problem-context tags:**
- `graph_structure` (confirmed) — if the input is an adjacency list or matrix

**Known confusing strategies:**
- `dfs_backtracking` — both traverse graphs. BFS uses a queue and processes level-by-level; DFS uses recursion or a stack and goes depth-first.
- `topological_sort` — both use queues and in-degree tracking. Topological sort has in-degree computation and produces an ordering; BFS shortest path has distance tracking.

**Why the combination is distinctive:**
Queue + level tracking + visited set is the structural signature of BFS. The queue-based traversal with level-by-level processing is unique among the strategies.

---

### 5.6 S6: `dp_top_down`

**Name:** Dynamic Programming (Top-Down / Memoized)
**Definition:**
A strategy that solves subproblems recursively with memoization, caching results to avoid redundant computation.

**Required techniques:**
- `recursive_branching` (T4) — function calls itself in multiple paths

**Required structural constraints:**
- Memoization structure: dict, array, or `@lru_cache` decorator
- Base case(s) that return without recursion
- Recursive calls read from and write to the memo structure

**Optional techniques:**
- `loop_state_tracking` (T6) — if the memo is accessed conditionally

**Relevant problem-context tags:**
- None required for V1

**Known confusing strategies:**
- `dfs_backtracking` — both use recursive branching. DP top-down has memoization; DFS backtracking does not.
- `dp_bottom_up` — both solve overlapping subproblems. Top-down uses recursion + cache; bottom-up uses iteration + table.

**Why the combination is distinctive:**
Recursive branching + memoization is the structural signature of top-down DP. The presence of a cache that is consulted before recursing distinguishes it from plain backtracking.

---

### 5.7 S7: `dp_bottom_up`

**Name:** Dynamic Programming (Bottom-Up / Tabulation)
**Definition:**
A strategy that solves subproblems iteratively by filling a table from base cases upward, where each entry depends on previously computed entries.

**Required techniques:**
- `iterative_table_filling` (T7) — loop + indexed access + accumulator + lookback

**Required structural constraints:**
- A data structure (array or 2D table) is created before the loop
- The loop fills the structure using index-based lookback to prior entries
- Base cases are initialized before the main loop

**Optional techniques:**
- `sequential_accumulation` (T1) — if the table is 1D and filled sequentially

**Relevant problem-context tags:**
- None required for V1

**Known confusing strategies:**
- `dp_top_down` — both solve overlapping subproblems. Bottom-up uses iteration + table; top-down uses recursion + cache.
- `prefix_sum` — both fill arrays iteratively. DP bottom-up has branching/recurrence; prefix sum is a single accumulation formula.

**Why the combination is distinctive:**
Iterative table filling with index lookback is the structural signature of bottom-up DP. The combination of nested loops (often), table initialization, and recurrence-based filling distinguishes it from simple sequential accumulation.

---

### 5.8 S8: `union_find`

**Name:** Union-Find / Disjoint Set
**Definition:**
A strategy that maintains a collection of disjoint sets using parent pointers and union operations, with path compression or rank optimization.

**Required techniques:**
- None of the seven techniques are required (union-find uses specific structural patterns)

**Required structural constraints:**
- Parent array or dictionary: `parent = list(range(n))` or equivalent
- Find function (recursive or iterative) that follows parent pointers
- Union operation that merges two sets
- Optional: rank or size array for optimization

**Optional techniques:**
- `recursive_branching` (T4) — if find is implemented recursively

**Relevant problem-context tags:**
- None required for V1

**Known confusing strategies:**
- `dfs_backtracking` — both can traverse structures recursively. Union-find uses parent pointers and union; DFS uses adjacency and visited sets.
- `bfs_shortest_path` — both track connectivity. Union-find merges sets; BFS explores paths.

**Why the combination is distinctive:**
Parent array + find + union operations are the structural signature of union-find. No other strategy uses this specific combination of parent-pointer traversal and set merging.

---

## 6. Problem-Context Tags

For V1, only the following tags are defined. Each tag has three states: `confirmed`, `absent`, `unknown`.

| Tag | Meaning | When confirmed | When absent | When unknown |
|---|---|---|---|---|
| `sorted_input` | The input array/string is sorted (or can be assumed sorted) | Explicit sort call, or problem statement says sorted | No sort, and problem says "unsorted" | No information |
| `graph_structure` | The input is a graph (adjacency list, edge list, or matrix) | Graph variable names, adjacency iteration | Input is a flat array | No information |
| `bounded_range` | Input values are bounded (e.g., 1 ≤ nums[i] ≤ 100) | Explicit range check or constraint | No constraint | No information |

**Design rationale:**
- `sorted_input` is needed for binary search (but NOT required — binary search can be detected from code alone).
- `graph_structure` is needed for BFS/union-find context.
- `bounded_range` is a placeholder for future use.
- Other tags from the architecture (`uniqueness_guaranteed`, `duplicates_allowed`, `complexity_hint`) are **deferred** — they are not needed for V1 strategy definitions.

---

## 7. Known Limitations (V1 Implementation)

The following limitations are documented based on the Phase 2B audit.

### 7.1 Name-Based Heuristics

The fact extractor uses variable-name heuristics for several detections. These are documented as heuristics, not hard requirements, consistent with architecture §4.4 ("limited, intraprocedural type inference").

| Detection | Heuristic | Risk | Mitigation |
|---|---|---|---|
| `carry_propagation` | `CARRY_LIKE_NAMES` set ("carry", "c", "sum", etc.) | False negative for unusual carry variable names | Works for common names; documented as heuristic |
| `cache_lookup` / `cache_write` | `cache_like` set ("cache", "memo", "dp", "table") | False negative for non-standard cache names | Add structural fallback in V2 if needed |
| `neighbor_traversal` | `graph_like` set ("graph", "adj", "edges") | False negative for non-standard graph variable names | Add structural fallback in V2 if needed |
| `queue_dequeue` creation | `queue_like` set ("queue", "q") | False negative for non-standard queue names | Add structural fallback in V2 if needed |
| `visited_tracking` | `visited_like` set ("visited", "seen", "vis") | False negative for non-standard visited names | Add structural fallback in V2 if needed |

**Phase 3 risk:** These heuristics may cause false negatives in production if users use unusual variable names. Monitor false negatives and add structural fallbacks in V2.

### 7.2 Prefix Sums Classified as dp_bottom_up

Simple prefix-sum implementations are classified as `dp_bottom_up` because they satisfy `iterative_table_filling` (indexed_write + index_lookback). The current fact model cannot distinguish single-step lookback (prefix sum) from multi-step recurrence (DP).

**Phase 3 risk:** Low. If solution groups require distinguishing DP from prefix sums, add a `recurrence_branching` fact in V2.

### 7.3 Tree BFS Not Detected

Level-order tree traversal uses `node.left`/`node.right` (linked attribute access), not `graph[node]` (neighbor traversal). The BFS strategy requires `neighbor_traversal` which is graph-subscript specific.

**Phase 3 risk:** Low. If tree problems need BFS detection, add `linked_attribute_traversal` as an alternative in V2.

---

## 8. Add Two Numbers Validation

### 9.1 Code under analysis

```python
def addTwoNumbers(l1, l2):
    dummy = ListNode()
    curr = dummy
    carry = 0

    while l1 or l2 or carry:
        val = (l1.val if l1 else 0) + (l2.val if l2 else 0) + carry
        carry, digit = divmod(val, 10)
        curr.next = ListNode(digit)
        curr = curr.next
        l1 = l1.next if l1 else None
        l2 = l2.next if l2 else None

    return dummy.next
```

### 9.2 Structural facts extracted

| Fact | Evidence in code |
|---|---|
| `loop_shape` | `while l1 or l2 or carry` — while loop |
| `linked_structure_traversal` | `l1.val`, `l1.next`, `l2.val`, `l2.next`, `curr.next` — `.val` and `.next` attribute access |
| `accumulator_update` | `carry, digit = divmod(val, 10)` — carry is updated from its prior value |
| `control_dependency` | `l1 or l2 or carry` in loop condition — carry influences loop termination |
| `container_operation` | `ListNode(digit)` — node construction |
| `early_termination` | Implicit when `l1` and `l2` are both None and carry is 0 |
| `comparison_operation` | `if l1 else 0` — None check (implicit comparison) |
| `constant_step_update` | `l1 = l1.next` — pointer advancement (constant step in the traversal sense) |

### 9.3 Techniques detected

| Technique | Required facts present? | Notes |
|---|---|---|
| T1: `sequential_accumulation` | `loop_shape` ✓, `accumulator_update` ✓ (carry), `loop_variable_in_update` — **PARTIAL**: the loop variable is `l1`/`l2`, and `carry` is updated, but `carry`'s update depends on `val` which depends on `l1.val`/`l2.val`. The loop variable is involved but indirectly. | **BORDERLINE.** The carry update depends on values derived from the loop variables (`l1.val`, `l2.val`), not directly on the loop variable itself. Strict interpretation: does NOT fire. Relaxed interpretation: fires with low confidence. **Decision: DOES NOT FIRE** — the carry update depends on dereferenced values, not the loop index. |
| T2: `boundary_narrowing` | `loop_shape` ✓, `comparison_in_loop_condition` — the condition is `l1 or l2 or carry`, which is a truthiness check, not a comparison of two index variables. | **DOES NOT FIRE** — no comparison of two index variables. |
| T3: `bidirectional_index_scan` | `opposite_direction_updates` — `l1 = l1.next` and `l2 = l2.next` are both forward movements, not opposite. | **DOES NOT FIRE** — both pointers move forward. |
| T4: `recursive_branching` | No recursive calls. | **DOES NOT FIRE** |
| T5: `carry_propagation` | `linked_structure_traversal` ✓, `accumulator_update` ✓ (carry), `loop_shape` ✓ | **FIRES** ✓ |
| T6: `loop_state_tracking` | `conditional_index_update` — `l1 = l1.next if l1 else None` is a conditional update. `control_dependency` — the carry influences the loop condition. | **FIRES** ✓ — the conditional pointer updates and carry-dependent loop condition satisfy this. |
| T7: `iterative_table_filling` | No table/array being filled. | **DOES NOT FIRE** |

### 9.4 Strategy evaluation

| Strategy | Required techniques present? | Required constraints present? | Result |
|---|---|---|---|
| S1: `binary_search` | `boundary_narrowing` ✗ | No midpoint calculation | **NOT MATCHED** |
| S2: `sliding_window` | `sequential_accumulation` ✗ (borderline), `loop_state_tracking` ✓ | No for-loop with right pointer advancing | **NOT MATCHED** |
| S3: `two_pointers_opposite` | `bidirectional_index_scan` ✗ | No opposite-direction updates | **NOT MATCHED** |
| S4: `dfs_backtracking` | `recursive_branching` ✗ | No recursion | **NOT MATCHED** |
| S5: `bfs_shortest_path` | N/A | No queue, no level tracking | **NOT MATCHED** |
| S6: `dp_top_down` | `recursive_branching` ✗ | No recursion | **NOT MATCHED** |
| S7: `dp_bottom_up` | `iterative_table_filling` ✗ | No table filling | **NOT MATCHED** |
| S8: `union_find` | N/A | No parent array, no find/union | **NOT MATCHED** |

### 9.5 Match outcome

```
Techniques detected: [carry_propagation, loop_state_tracking]
Strategies matched: none
Solution groups satisfied: none
Outcome: UNRESOLVED
```

### 9.6 Verification

**Is this correct?** YES.

- The structural facts are preserved: linked_structure_traversal, carry update, node construction, conditional pointer updates.
- No false classification occurred.
- No false contradiction with old `linked_list_reversal` ground truth (because the new matching does not use pattern-ID equality).
- `UNRESOLVED` is the safe, non-punitive outcome.
- The stored facts remain available for future strategy definitions.

**What would need to change to CONFIRMED?**
A future strategy definition could be created: `linked_list_arithmetic` requiring `carry_propagation` + `linked_structure_traversal` + `node_construction`. This is a valid future extension but is NOT needed for V1.

---

## 9. Problem 2996 Validation

### 9.1 Code under analysis

```python
class Solution:
    def missingInteger(self, nums: List[int]) -> int:
        i = 1
        summ = nums[0]

        while i <= len(nums)-1 and nums[i] == nums[i-1]+1:
            summ += nums[i]
            i += 1

        while summ in nums:
            summ += 1

        return summ
```

### 9.2 Structural facts extracted

| Fact | Evidence in code |
|---|---|
| `loop_shape` | Two while loops |
| `constant_step_update` | `i += 1` |
| `indexed_access` | `nums[i]`, `nums[i-1]`, `nums[0]` |
| `accumulator_update` | `summ += nums[i]` (first loop), `summ += 1` (second loop) |
| `membership_check` | `summ in nums` |
| `comparison_operation` | `nums[i] == nums[i-1]+1`, `i <= len(nums)-1` |
| `control_dependency` | `i <= len(nums)-1 and nums[i] == nums[i-1]+1` — two conditions control loop termination |
| `early_termination` | First loop terminates when consecutive sequence breaks |

### 9.3 Techniques detected

| Technique | Required facts present? | Notes |
|---|---|---|
| T1: `sequential_accumulation` | `loop_shape` ✓, `accumulator_update` ✓ (`summ += nums[i]`), `loop_variable_in_update` ✓ (`nums[i]` uses loop variable `i`) | **FIRES** ✓ (first loop) |
| T2: `boundary_narrowing` | `loop_shape` ✓, `comparison_in_loop_condition` ✓ (`i <= len(nums)-1`), `index_variable_in_comparison` ✓ (`i` is in the comparison and is updated via `i += 1`) | **FIRES** ✓ (first loop) |
| T3: `bidirectional_index_scan` | `opposite_direction_updates` — `i += 1` is the only index update. No second index moving in opposite direction. | **DOES NOT FIRE** |
| T4: `recursive_branching` | No recursive calls. | **DOES NOT FIRE** |
| T5: `carry_propagation` | No linked structure traversal. | **DOES NOT FIRE** |
| T6: `loop_state_tracking` | `conditional_index_update` — `summ += nums[i]` is inside the while condition guard (implicit conditional). `control_dependency` — `summ` is updated only when `nums[i] == nums[i-1]+1`. | **FIRES** ✓ (first loop: summ updated conditionally based on comparison) |
| T7: `iterative_table_filling` | No table being filled (summ is a scalar accumulator, not a data structure). | **DOES NOT FIRE** |

### 9.4 Strategy evaluation

| Strategy | Required techniques present? | Required constraints present? | Result |
|---|---|---|---|
| S1: `binary_search` | `boundary_narrowing` ✓ | No midpoint calculation | **NOT MATCHED** — boundary_narrowing is present, but the required midpoint constraint is missing |
| S2: `sliding_window` | `sequential_accumulation` ✓, `loop_state_tracking` ✓ | No for-loop with right pointer advancing; no window state (left boundary). The `summ` variable is not a window boundary. | **NOT MATCHED** — the structural constraints (for-loop, right pointer, left boundary) are not satisfied |
| S3: `two_pointers_opposite` | `bidirectional_index_scan` ✗ | No opposite-direction updates | **NOT MATCHED** |
| S4–S8 | N/A | N/A | **NOT MATCHED** |

### 9.5 Match outcome

```
Techniques detected: [sequential_accumulation, boundary_narrowing, loop_state_tracking]
Strategies matched: none
Solution groups satisfied: none
Outcome: UNRESOLVED
```

### 9.6 Verification

**Is this correct?** YES.

- The structural facts are preserved: indexed traversal, sequential accumulation with consecutive-element guard, membership check, linear search.
- `boundary_narrowing` fires on the first loop (correct — the loop narrows the search range of consecutive elements), but `binary_search` is NOT matched because no midpoint is computed. This is the correct distinction.
- `sequential_accumulation` fires correctly.
- `loop_state_tracking` fires correctly (summ is conditionally updated).
- No false classification into `hash_map_lookup` (membership check is a single fact, not a technique).
- No false classification into `binary_search` (no midpoint).
- No false classification into `prefix_sum` (no prefix array, no subscript lookback).
- `UNRESOLVED` is the safe, non-punitive outcome.

**What would need to change to CONFIRMED?**
A future strategy definition could be created: `sequential_prefix_accumulation` requiring `sequential_accumulation` + `boundary_narrowing` with the constraint that the accumulation guard involves consecutive-element comparison. This is a valid future extension but is NOT needed for V1.

---

## 10. False-Positive Stress Tests

### 9.1 Visited set inside BFS should NOT become hash-based strategy

**Code pattern:**
```python
queue = deque([start])
visited = {start}
while queue:
    node = queue.popleft()
    for neighbor in graph[node]:
        if neighbor not in visited:
            visited.add(neighbor)
            queue.append(neighbor)
```

**Analysis:**
- `visited_tracking` is NOT a technique (rejected — single fact).
- `membership_check` (`neighbor not in visited`) is a single structural fact, not a technique.
- `frequency_counting` is NOT a technique (rejected).
- **Techniques detected:** None of the 7 techniques fire on this code alone (no accumulator_update, no recursive_branching, no linked_structure_traversal).
- **Strategy matched:** `bfs_shortest_path` fires via structural constraints (queue, popleft, visited set, level tracking).
- **Result:** Correct. The visited set does NOT produce any hash-based technique or strategy.

### 9.2 Accumulation inside DP should NOT automatically become prefix sum

**Code pattern (House Robber):**
```python
dp = [0] * len(nums)
dp[0] = nums[0]
dp[1] = max(nums[0], nums[1])
for i in range(2, len(nums)):
    dp[i] = max(dp[i-1], dp[i-2] + nums[i])
return dp[-1]
```

**Analysis:**
- `sequential_accumulation` — fires? `dp[i] = max(...)` is an update, but `dp` is being filled, not accumulated in the running-sum sense. The update expression does not read `dp[i]` on the right side (it reads `dp[i-1]` and `dp[i-2]`). **DOES NOT FIRE** (the accumulator is not self-referential in the sequential sense).
- `iterative_table_filling` — fires? `dp` is a table, indexed access (`dp[i-1]`, `dp[i-2]`), accumulator update (`dp[i] = ...`), loop variable in update (`i` is used in subscripts). **FIRES** ✓.
- **Strategy matched:** `dp_bottom_up` (iterative_table_filling + nested loop + recurrence).
- **Result:** Correct. The accumulation in DP does NOT become prefix sum.

### 9.3 Two moving indices inside sliding window should NOT become opposite-direction two pointers

**Code pattern (Longest Substring Without Repeating Characters):**
```python
char_index = {}
left = 0
max_len = 0
for right in range(len(s)):
    if s[right] in char_index:
        left = max(left, char_index[s[right]] + 1)
    char_index[s[right]] = right
    max_len = max(max_len, right - left + 1)
```

**Analysis:**
- `sequential_accumulation` — fires? `max_len = max(...)` updates, but `max_len` is not self-referential (it reads `right - left + 1`, not its own prior value). **DOES NOT FIRE**.
- `loop_state_tracking` — fires? `left = max(left, ...)` is a conditional update to a state variable, and `left` influences the `max_len` computation. **FIRES** ✓.
- `bidirectional_index_scan` — fires? `right` increments, but `left` is assigned (not decremented). No opposite-direction updates. **DOES NOT FIRE**.
- **Strategy matched:** `sliding_window` (sequential_accumulation ✗ — borderline, but `loop_state_tracking` ✓ + for-loop + conditional left update). Wait, `sequential_accumulation` does not fire because `max_len` is not self-referential. But `sliding_window` requires `sequential_accumulation` as a required technique. Let me reconsider...

Actually, `sequential_accumulation` requires the accumulator to be self-referential. In this code, `max_len = max(max_len, right - left + 1)` IS self-referential (reads `max_len` on the right side). So `sequential_accumulation` FIRES ✓.

- **Strategy matched:** `sliding_window` (sequential_accumulation ✓ + loop_state_tracking ✓ + for-loop + conditional left update).
- **Result:** Correct. The two moving indices do NOT become opposite-direction two pointers.

### 9.4 Array iteration inside sorting should NOT become array_traversal

**Code pattern:**
```python
def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)
```

**Analysis:**
- `recursive_branching` — fires? The function calls itself twice with different arguments (`arr[:mid]` and `arr[mid:]`). **FIRES** ✓.
- **Strategy matched:** `dfs_backtracking`? No — there is no state restoration (no backtracking). `dp_top_down`? No — there is no memoization. No strategy is matched.
- **Result:** Correct. The recursive sort does NOT become `array_traversal` or any misclassified strategy. **UNRESOLVED**.

### 9.5 Linked-list .next traversal should NOT become linked-list reversal

**Code pattern (Add Two Numbers — the validation case):**
```python
while l1 or l2 or carry:
    val = (l1.val if l1 else 0) + (l2.val if l2 else 0) + carry
    carry, digit = divmod(val, 10)
    curr.next = ListNode(digit)
    curr = curr.next
    l1 = l1.next if l1 else None
    l2 = l2.next if l2 else None
```

**Analysis:**
- `carry_propagation` fires (linked_structure_traversal + accumulator_update + loop).
- `linked_list_reversal` would require `pointer_rewiring` (e.g., `node.next = prev` where value is a variable, not a constructor). The code has `curr.next = ListNode(digit)` — this is node CONSTRUCTION, not rewiring. The old `linked_list_reversal` detector would NOT fire (it checks for `curr.next = prev` pattern).
- **Result:** Correct. The linked-list traversal does NOT become linked-list reversal.

### 9.6 Generic `+=` should NOT become prefix_sum

**Code pattern (Running Total):**
```python
total = 0
for num in nums:
    total += num
```

**Analysis:**
- `sequential_accumulation` — fires? `total += num` is self-referential, `num` is the loop variable. **FIRES** ✓.
- `iterative_table_filling` — fires? No table being filled, no indexed access. **DOES NOT FIRE**.
- **Strategy matched:** None. No strategy requires only `sequential_accumulation`.
- **Result:** Correct. The generic `+=` does NOT become prefix_sum.

### 9.7 Generic pointer movement should NOT become two-pointers

**Code pattern (Linked List Length):**
```python
count = 0
curr = head
while curr:
    count += 1
    curr = curr.next
```

**Analysis:**
- `carry_propagation` — fires? `linked_structure_traversal` ✓, `accumulator_update` ✓ (`count += 1`), `loop_shape` ✓. **FIRES** ✓.
- But `count += 1` is not a carry/state in the meaningful sense — it's just counting. However, the technique definition requires `accumulator_update` + `linked_structure_traversal` + `loop_shape`, and all three are present. The technique fires.
- `bidirectional_index_scan` — fires? Only one pointer moving. **DOES NOT FIRE**.
- **Strategy matched:** None.
- **Result:** The technique fires but no strategy is matched. **UNRESOLVED**. This is acceptable — the technique fires with low centrality (the carry is not meaningful in this context), and no strategy claims it.

### 9.8 List membership must NOT automatically imply hash-based lookup

**Code pattern (Problem 2996 — second loop):**
```python
while summ in nums:
    summ += 1
```

**Analysis:**
- `membership_check` (`summ in nums`) is a single structural fact, not a technique.
- `frequency_counting` is NOT a technique (rejected).
- No technique fires on this code fragment alone.
- **Result:** Correct. The list membership does NOT imply hash-based lookup.

---

## 10. Ambiguous / Unresolved Cases

### 10.1 Topological Sort

**Observation:** Topological sort uses queue-based traversal with in-degree tracking. It is structurally similar to BFS but with in-degree computation.

**Assessment:** For V1, topological sort is NOT given its own strategy. It would be detected as `bfs_shortest_path` (queue + level tracking) with low confidence, or more likely UNRESOLVED (no distance tracking, in-degree is a different structural pattern). This is acceptable — the structural facts (in-degree computation, queue processing, conditional enqueue) are preserved and available for future strategy definitions.

**Recommendation:** Add a `topological_sort` strategy in V2 if needed, requiring in-degree computation + queue processing + conditional enqueue.

### 10.2 Greedy with Sorting

**Observation:** Many greedy strategies sort the input first, then iterate. The sorting is a preprocessing step, not the core technique.

**Assessment:** For V1, greedy strategies are NOT given their own technique. The sorting fact (`sortedness_fact`) is preserved, and the iteration technique (`sequential_accumulation` or `loop_state_tracking`) may fire. No strategy would match because greedy lacks a distinctive structural signature.

**Recommendation:** Defer greedy strategy to V2. The structural facts are sufficient.

### 10.3 Union-Find Without Explicit Function Definitions

**Observation:** Some union-find implementations inline the find/union logic without separate functions.

**Assessment:** The `union_find` strategy requires parent array + find + union as structural constraints. If the logic is inlined, the parent array pattern is still detectable, but the find/union patterns may be harder to identify. This is acceptable — the strategy fires with lower confidence, and UNRESOLVED is a safe fallback.

### 10.4 Iterative DFS vs Recursive DFS

**Observation:** Iterative DFS uses an explicit stack; recursive DFS uses the call stack. Both explore depth-first.

**Assessment:** For V1, only `dfs_backtracking` (recursive) is defined as a strategy. Iterative DFS would be UNRESOLVED (no recursive branching technique fires). This is acceptable — the structural facts (explicit stack, push/pop, visited set) are preserved.

**Recommendation:** Add `dfs_iterative` strategy in V2 if needed.

---

## 11. Versioning Considerations

### 11.1 Technique versioning

Each technique definition is versioned. When a technique's definition changes (e.g., adding a new required fact, changing a threshold), a new version is introduced.

**Version format:** `MAJOR.MINOR`
- MAJOR: Semantic change (e.g., removing a required fact, changing the technique's meaning)
- MINOR: Tuning change (e.g., adjusting confidence thresholds, adding optional facts)

**Initial version:** All techniques start at `1.0`.

### 11.2 Strategy versioning

Each strategy definition is versioned independently.

**Initial version:** All strategies start at `1.0`.

### 11.3 Re-derivation

When a technique or strategy definition changes, all submissions that were analyzed with the old version can be re-derived from persisted structural facts. This is a core architecture invariant (§12).

### 11.4 Backward compatibility

Historical submissions analyzed with the old flat pattern taxonomy remain valid. The old pattern IDs are preserved in `detected_patterns_json`. New submissions use the technique/strategy vocabulary. The two systems coexist via the persistence adapter.

---

## 12. Deferred Concepts

The following are explicitly NOT part of V1:

| Concept | Reason for deferral |
|---|---|
| `heap_order_maintenance` technique | Too narrow (only heap strategies). Add in V2 if needed. |
| `monotonic_structure_maintenance` technique | Too narrow (only monotonic stack/deque). Add in V2 if needed. |
| `backtracking_state_restore` technique | Implementation detail, not a general technique. |
| `visited_tracking` technique | Single fact, not a multi-fact composite. |
| `frequency_counting` technique | Single fact, too specific to hash-map problems. |
| `prefix_sum` as a technique | Better covered by `sequential_accumulation` + `iterative_table_filling`. |
| `greedy` strategy | Lacks distinctive structural signature for V1. |
| `topological_sort` strategy | Structurally similar to BFS. Defer to V2. |
| `dfs_iterative` strategy | Only recursive DFS is defined for V1. |
| `sliding_window_fixed` vs `sliding_window_variable` distinction | Both are captured by the single `sliding_window` strategy. |
| Problem-context tags beyond the three defined | Not needed for V1 strategy definitions. |
| OR/disjunction in solution groups | Explicitly deferred by architecture §8.3. |
| Group inheritance | Explicitly deferred by architecture §8.3. |

---

## 13. Recommended Implementation Order

### Phase 1: Easiest techniques (reliable detection, high recurrence)

1. **T1: `sequential_accumulation`** — Loop + `+=` + loop variable in update. Simplest to detect. Appears in many contexts.
2. **T3: `bidirectional_index_scan`** — While-loop + comparison + opposite `+=`/`-=`. Mechanically detectable from augmented assignment operators.

### Phase 2: Medium techniques

3. **T4: `recursive_branching`** — Self-recursive call + conditional branching. Detection is straightforward from AST.
4. **T2: `boundary_narrowing`** — While-loop + comparison + index variable updated. Needs careful detection of which variables in the comparison are also updated.
5. **T5: `carry_propagation`** — Linked structure traversal + accumulator update + loop. Detection of `.next`/`.left`/`.right` is reliable.

### Phase 3: Harder techniques

6. **T6: `loop_state_tracking`** — Conditional index update + control dependency. Needs data-flow analysis to detect that the state variable influences subsequent iterations.
7. **T7: `iterative_table_filling`** — Loop + indexed access + accumulator + lookback. Needs subscript analysis to detect lookback patterns.

### Phase 4: Strategies (after all techniques are implemented)

8. **S1: `binary_search`** — boundary_narrowing + midpoint calculation
9. **S3: `two_pointers_opposite`** — bidirectional_index_scan + convergence
10. **S2: `sliding_window`** — sequential_accumulation + loop_state_tracking
11. **S4: `dfs_backtracking`** — recursive_branching + state restoration
12. **S7: `dp_bottom_up`** — iterative_table_filling
13. **S6: `dp_top_down`** — recursive_branching + memoization
14. **S5: `bfs_shortest_path`** — queue + level tracking + visited
15. **S8: `union_find`** — parent array + find + union

### Phase 5: Integration

16. Solution group definitions using the vocabulary
17. Matching engine refactor (satisfaction-based)
18. Tri-state outcome propagation
19. Persistence updates

---

## 14. Summary

| Layer | Count | Items |
|---|---|---|
| Structural facts | 15 + 9 additional | From architecture §4.1 + technique-detection needs |
| Techniques | 7 | T1–T7 as defined above |
| Strategies | 8 | S1–S8 as defined above |
| Problem-context tags | 3 | sorted_input, graph_structure, bounded_range |
| Rejected candidates | 12 | Listed in §4 |
| Validation cases | 2 | Both produce UNRESOLVED (correct) |
| False-positive stress tests | 8 | All pass correctly |

**Final assessment:** The vocabulary is small, defensible, and consistent with the architecture. It correctly handles both validation cases (UNRESOLVED with preserved structural facts). It avoids all identified false-positive pitfalls. The techniques are composable, the strategies are distinctive, and the vocabulary is extensible for future versions.
