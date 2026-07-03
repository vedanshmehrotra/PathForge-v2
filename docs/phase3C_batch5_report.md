# Phase 3C Batch 5 Report — Graphs & Trees Detectors

## Summary

Batch 5 implements 5 tree and graph traversal detectors for the V2 AST
Analysis Engine, covering all Graphs & Trees patterns from the taxonomy
except `topological_sort` and `union_find` (which are deferred to later
batches due to their unique structural requirements).

| Detector | Pattern ID | File | Lines |
|----------|-----------|------|-------|
| Recursive DFS | `dfs_recursive` | `detectors/dfs_recursive.py` | 195 |
| Iterative DFS | `dfs_iterative` | `detectors/dfs_iterative.py` | 186 |
| BFS Level-Order | `bfs_level_order` | `detectors/bfs_level_order.py` | 192 |
| BFS Shortest Path | `bfs_shortest_path` | `detectors/bfs_shortest_path.py` | 189 |
| Binary Search Tree | `binary_search_tree` | `detectors/binary_search_tree.py` | 155 |

## Evidence Strategy

Each detector uses positive-only evidence items with weighted confidence
(0.0–1.0, capped at 1.0) and gated detection to prevent false positives:

### `dfs_recursive`
- **Core gate**: recursive self-call AND (graph traversal OR child recursion OR
  grid expansion OR visited tracking)
- **Evidence types**: `recursive_call` (0.35), `graph_traversal` (0.30),
  `child_recursion` (0.25), `grid_expansion` (0.25), `visited_tracking` (0.20),
  `base_case` (0.20)
- **Negative tests**: Fibonacci, factorial, linked-list traversal, array
  binary search — all correctly rejected (recursion without traversal context)

### `dfs_iterative`
- **Core gate**: explicit stack initialized before while loop AND (pop +
  traversal OR child push OR visited tracking); explicitly excludes
  comparison-driven pop (monotonic stack)
- **Evidence types**: `explicit_stack` (0.35), `stack_traversal` (0.30),
  `child_push` (0.25), `visited_tracking` (0.20)
- **Negative tests**: monotonic stack (comparison-driven pop), BFS queue
  (popleft), simple stack — all correctly rejected

### `bfs_level_order`
- **Core gate**: popleft AND child enqueue; explicitly rejected when distance
  tracking or visited set is present (to avoid overlap with shortest-path BFS)
- **Evidence types**: `queue_popleft` (0.35), `child_enqueue` (0.30),
  `level_tracking` (0.25), `deque_import` (0.20)
- **Negative tests**: shortest-path BFS, monotonic deque, simple deque — all
  correctly rejected

### `bfs_shortest_path`
- **Core gate**: queue with popleft AND (distance tracking OR visited set)
- **Evidence types**: `queue_traversal` (0.30), `distance_tracking` (0.25),
  `visited_set` (0.20), `neighbor_expansion` (0.25), `level_for_loop` (0.20)
- **Negative tests**: tree level-order (no distance/visited) — correctly rejected

### `binary_search_tree`
- **Core gate**: BST comparison AND recursive left/right child traversal
- **Evidence types**: `bst_comparison` (0.30), `bst_recursion` (0.25),
  `min_max_constraint` (0.25), `bst_operation` (0.30)
- **Negative tests**: plain tree inorder/preorder (no BST comparisons),
  array binary search (no tree), linked list — all correctly rejected

## Key Design Decisions

1. **Grid DFS support**: `dfs_recursive` detects Number-of-Islands–style grid
   traversal via `_find_grid_expansion`, which identifies ≥3 recursive calls
   with direction offsets (`i+1`, `i-1`, `j+1`, `j-1`).

2. **Monotonic stack exclusion**: `dfs_iterative` checks for comparison-driven
   pop (`while stack and arr[stack[-1]] < arr[i]: stack.pop()`) and skips
   the while loop if detected, preventing overlap with `monotonic_stack`.

3. **BFS separation**: `bfs_level_order` and `bfs_shortest_path` are
   disambiguated by the presence of distance tracking or visited set. Tree
   level-order (which has neither) fires only the level-order detector.

4. **BST vs tree traversal**: `binary_search_tree` requires both value
   comparisons (`val < node.val`) AND recursive calls with `.left`/`.right`
   to fire. Plain tree traversals (inorder, preorder, postorder) have
   recursion but no comparisons, so they correctly do not trigger.

## Test Results

| Suite | Tests | Passed | Failed |
|-------|-------|--------|--------|
| Batch 5 (new) | 61 | 61 | 0 |
| Batch 1 + 2 + 3 + 4 (existing) | 269 | 269 | 0 |
| **Full suite** | **330** | **330** | **0** |

## Registry Impact

- 5 new detectors registered (22 total)
- All existing 17 detectors continue to pass unchanged
- Detector count updated in `test_output_pipeline.py` (17 → 22)

## Coverage Update

| Category | Previous | Batch 5 | Now |
|----------|----------|---------|-----|
| Graphs & Trees | 0/7 | +5 | 5/7 |
| **Total** | **17/33** | **+5** | **22/33** |
| Remaining | 16 | −5 | **11** |
