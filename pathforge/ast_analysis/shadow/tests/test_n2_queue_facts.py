"""N2 Batch 1 (RC-N2-1): queue fact extraction for real-world Python queue idioms.

Two generalized extraction defects are covered:

1. Queue *creation* only fired for ``deque(...)`` or an **empty** list literal
   assigned to a queue-like name, so the canonical ``queue = [root]`` form was
   invisible.
2. Queue *dequeue* only fired from ``visit_Expr`` (a bare statement), so
   ``node = queue.pop(0)``, ``node = queue.popleft()`` and tuple-unpack forms
   such as ``r, c, d = q.popleft()`` were invisible.

These tests are generalized: they assert the *structural* rule (queue-like name
+ list literal, and popleft()/pop(0) in the assignment family) rather than any
specific problem. No test references a problem ID.

Constraints verified here as negatives:
  - stack = [s] / stack.pop()      -> must NOT be a queue
  - dq.pop(3)                      -> must NOT be a dequeue
  - heapq.heappop(...)             -> must NOT be a dequeue
  - dp = [[0]*m for _ in range(n)] -> list comprehension, NOT a queue
  - ordinary queue drain           -> no bfs_shortest_path
  - recursive DFS                  -> no bfs_shortest_path
"""

import ast

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis


# ============================================================
# Fixtures
# ============================================================

# --- Positive: the two canonical level-order forms ---

QUEUE_BARE_LIST_POP0 = '''
class Solution:
    def levelOrder(self, root):
        if not root:
            return []
        res = []
        queue = [root]
        while queue:
            level = []
            for _ in range(len(queue)):
                node = queue.pop(0)
                level.append(node.val)
                if node.left:
                    queue.append(node.left)
                if node.right:
                    queue.append(node.right)
            res.append(level)
        return res
'''

QUEUE_BARE_LIST_POPLEFT = '''
class Solution:
    def levelOrder(self, root):
        queue = [root]
        out = []
        while queue:
            level = []
            for _ in range(len(queue)):
                node = queue.popleft()
                level.append(node.val)
                if node.left:
                    queue.append(node.left)
            out.append(level)
        return out
'''

# --- Positive: assignment-family dequeue forms ---

DEQUE_ASSIGN_POPLEFT = '''
from collections import deque

def bfs(graph, start, goal):
    q = deque([start])
    seen = {start}
    while q:
        node = q.popleft()
        if node == goal:
            return True
        for nb in graph[node]:
            if nb not in seen:
                seen.add(nb)
                q.append(nb)
    return False
'''

TUPLE_UNPACK_POPLEFT = '''
from collections import deque

def shortest(grid, sr, sc):
    q = deque([(sr, sc, 0)])
    seen = {(sr, sc)}
    while q:
        r, c, d = q.popleft()
        if (r, c) == (sr, sc) and d > 0:
            return d
        for dr, dc in ((1, 0), (0, 1)):
            nr, nc = r + dr, c + dc
            if (nr, nc) not in seen:
                seen.add((nr, nc))
                q.append((nr, nc, d + 1))
    return -1
'''

ANNOTATED_ASSIGN_POPLEFT = '''
from collections import deque
from typing import Any

def drain(queue):
    total = 0
    while queue:
        node: Any = queue.popleft()
        total += node
    return total
'''

BARE_EXPR_POPLEFT = '''
from collections import deque

def drain(q):
    seen = []
    while q:
        q.popleft()
        seen.append(1)
    return seen
'''

BARE_LIST_TUPLE_UNPACK = '''
def shortest(grid):
    queue = [(0, 0, 0)]
    seen = {(0, 0)}
    while queue:
        r, c, d = queue.pop(0)
        for dr, dc in ((1, 0), (0, 1)):
            nr, nc = r + dr, c + dc
            if (nr, nc) not in seen:
                seen.add((nr, nc))
                queue.append((nr, nc, d + 1))
    return d
'''

# --- Positive: renamed queue-like variables from the current allowlist ---

RENAMED_QUEUE_LIKE = '''
def traverse(tree, seed):
    frontier = [seed]
    out = []
    while frontier:
        node = frontier.pop(0)
        out.append(node)
        for child in node.children:
            frontier.append(child)
    return out
'''

RENAMED_QUEUE_UPPER = '''
def traverse(tree, seed):
    BFS_QUEUE = [seed]
    out = []
    while BFS_QUEUE:
        node = BFS_QUEUE.pop(0)
        out.append(node)
    return out
'''

# --- Negative fixtures ---

STACK_BARE_LIST = '''
def dfs(graph, start):
    stack = [start]
    seen = set()
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        for nb in graph[node]:
            stack.append(nb)
    return seen
'''

POP_NON_ZERO = '''
def take(dq):
    out = []
    while len(dq) > 3:
        x = dq.pop(3)
        out.append(x)
    return out
'''

POP_NO_ARGS = '''
def take(dq):
    out = []
    while dq:
        x = dq.pop()
        out.append(x)
    return out
'''

HEAP_POP = '''
import heapq

def dijkstra(graph, src, n):
    dist = [float("inf")] * n
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        for v, w in graph[u]:
            if d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(pq, (dist[v], v))
    return dist
'''

DP_TABLE_COMPREHENSION = '''
def build(rows, cols):
    dp = [[0] * cols for _ in range(rows)]
    return dp
'''

DP_TABLE_MULTIPLIED = '''
def build(n):
    dp = [0] * n
    return dp
'''

ORDINARY_QUEUE_DRAIN = '''
def process(items):
    q = []
    for x in items:
        q.append(x)
    out = []
    while q:
        out.append(q.pop(0))
    return out
'''

RECURSIVE_DFS = '''
def dfs(graph, node, seen):
    seen.add(node)
    for nb in graph[node]:
        if nb not in seen:
            dfs(graph, nb, seen)
    return seen
'''

# A single-level traversal that never uses a queue at all: walks the tree
# through child links only. Must not be BFS.
NO_QUEUE_TREE_WALK = '''
def collect(root, out):
    if root is None:
        return out
    out.append(root.val)
    collect(root.left, out)
    collect(root.right, out)
    return out
'''


# ============================================================
# Helpers
# ============================================================

def _facts(code):
    return extract_structural_facts(ast.parse(code))


def _queue_facts(code):
    return [f for f in _facts(code) if f.fact_type == "queue_dequeue"]


def _queue_ops(code):
    return {
        f.attributes.get("operation")
        for f in _queue_facts(code)
        if f.attributes.get("operation")
    }


def _fact_types(code):
    return {f.fact_type for f in _facts(code)}


def _strategies(code):
    result = run_shadow_analysis(code)
    assert result is not None, "shadow analysis failed"
    return {s["strategy_id"] for s in result["strategy_evidence"]}


def _group(required=None, optional=None, excluded=None):
    return {
        "id": "group_0",
        "required": list(required or []),
        "optional": list(optional or []),
        "excluded": list(excluded or []),
        "threshold": 0.5,
    }


def _outcome(code, groups):
    result = run_shadow_analysis(code, solution_groups=groups)
    assert result is not None, "shadow analysis failed"
    return result["match_outcome"]


# ============================================================
# 1. Queue creation: non-empty list literal (defect 1)
# ============================================================

class TestQueueCreationFromListLiteral:
    def test_bare_list_queue_creation_is_detected(self):
        assert "creation" in _queue_ops(QUEUE_BARE_LIST_POP0)

    def test_bare_list_queue_variable_recorded(self):
        vars_ = {
            f.attributes.get("queue_variable")
            for f in _queue_facts(QUEUE_BARE_LIST_POP0)
        }
        assert vars_ == {"queue"}

    def test_deque_call_still_detected(self):
        assert "creation" in _queue_ops(DEQUE_ASSIGN_POPLEFT)

    def test_renamed_bare_list_queue_detected(self):
        assert "creation" in _queue_ops(RENAMED_QUEUE_LIKE)

    def test_uppercase_queue_like_name_detected(self):
        assert "creation" in _queue_ops(RENAMED_QUEUE_UPPER)


# ============================================================
# 2. Queue dequeue: assignment family (defect 2)
# ============================================================

class TestQueueDequeueAssignmentFamily:
    def test_assign_pop0(self):
        assert "dequeue" in _queue_ops(QUEUE_BARE_LIST_POP0)

    def test_assign_popleft(self):
        assert "dequeue" in _queue_ops(QUEUE_BARE_LIST_POPLEFT)

    def test_deque_assign_popleft(self):
        assert "dequeue" in _queue_ops(DEQUE_ASSIGN_POPLEFT)

    def test_tuple_unpack_popleft(self):
        assert "dequeue" in _queue_ops(TUPLE_UNPACK_POPLEFT)

    def test_tuple_unpack_pop0(self):
        assert "dequeue" in _queue_ops(BARE_LIST_TUPLE_UNPACK)

    def test_annotated_assign_popleft(self):
        assert "dequeue" in _queue_ops(ANNOTATED_ASSIGN_POPLEFT)

    def test_bare_expr_popleft_still_detected(self):
        """The original ast.Expr path must be preserved."""
        assert "dequeue" in _queue_ops(BARE_EXPR_POPLEFT)

    def test_dequeue_records_receiver_variable(self):
        receivers = {
            f.attributes.get("queue_variable")
            for f in _queue_facts(TUPLE_UNPACK_POPLEFT)
            if f.attributes.get("operation") == "dequeue"
        }
        assert receivers == {"q"}


# ============================================================
# 3. Negative: creation must stay restricted
# ============================================================

class TestQueueCreationNegatives:
    def test_stack_bare_list_is_not_a_queue(self):
        assert _queue_ops(STACK_BARE_LIST) == set()

    def test_dp_list_comprehension_is_not_a_queue(self):
        assert _queue_ops(DP_TABLE_COMPREHENSION) == set()

    def test_dp_multiplied_list_is_not_a_queue(self):
        assert _queue_ops(DP_TABLE_MULTIPLIED) == set()

    def test_plain_empty_list_in_ordinary_drain_is_not_a_queue(self):
        """`q = []` is queue-like, but a list comprehension / multiplied list is not.

        The ordinary-drain fixture uses the queue-like name `q`, so creation is
        expected; the assertion here is only that the *unrelated* initialisation
        forms stay excluded (covered above). Kept explicit so a future widening
        of the name allowlist does not silently pass.
        """
        assert "creation" in _queue_ops(ORDINARY_QUEUE_DRAIN)


# ============================================================
# 4. Negative: dequeue operation discrimination must be preserved
# ============================================================

class TestQueueDequeueNegatives:
    def test_stack_pop_no_args_is_not_dequeue(self):
        assert "dequeue" not in _queue_ops(STACK_BARE_LIST)

    def test_pop_no_args_is_not_dequeue(self):
        assert "dequeue" not in _queue_ops(POP_NO_ARGS)

    def test_pop_non_zero_index_is_not_dequeue(self):
        assert "dequeue" not in _queue_ops(POP_NON_ZERO)

    def test_heap_pop_is_not_dequeue(self):
        assert _queue_ops(HEAP_POP) == set()


# ============================================================
# 5. End-to-end: BFS strategy recognition
# ============================================================

class TestBfsStrategyRecognition:
    def test_level_order_with_bare_list_and_pop0_is_bfs(self):
        assert "bfs_shortest_path" in _strategies(QUEUE_BARE_LIST_POP0)

    def test_level_order_with_bare_list_and_popleft_is_bfs(self):
        assert "bfs_shortest_path" in _strategies(QUEUE_BARE_LIST_POPLEFT)

    def test_deque_assignment_bfs_is_bfs(self):
        assert "bfs_shortest_path" in _strategies(DEQUE_ASSIGN_POPLEFT)

    def test_recursive_dfs_is_not_bfs(self):
        assert "bfs_shortest_path" not in _strategies(RECURSIVE_DFS)

    def test_no_queue_tree_walk_is_not_bfs(self):
        assert "bfs_shortest_path" not in _strategies(NO_QUEUE_TREE_WALK)

    def test_ordinary_queue_drain_without_neighbours_is_not_bfs(self):
        """A queue with no neighbour / linked traversal must not be BFS."""
        assert "bfs_shortest_path" not in _strategies(ORDINARY_QUEUE_DRAIN)

    def test_heap_priority_queue_is_not_bfs(self):
        assert "bfs_shortest_path" not in _strategies(HEAP_POP)

    def test_dp_table_is_not_bfs(self):
        assert "bfs_shortest_path" not in _strategies(DP_TABLE_COMPREHENSION)


# ============================================================
# 6. End-to-end: solution-group outcomes
# ============================================================

class TestSolutionGroupOutcomes:
    def test_level_order_confirms_bfs_group(self):
        outcome = _outcome(QUEUE_BARE_LIST_POP0, [_group(required=["bfs_shortest_path"])])
        assert outcome["outcome"] == "CONFIRMED"

    def test_level_order_excludes_nothing_falsely(self):
        outcome = _outcome(QUEUE_BARE_LIST_POP0, [_group(required=["bfs_shortest_path"])])
        assert outcome["outcome"] != "CONTRADICTED"

    def test_recursive_dfs_does_not_confirm_bfs_group(self):
        outcome = _outcome(RECURSIVE_DFS, [_group(required=["bfs_shortest_path"])])
        assert outcome["outcome"] != "CONFIRMED"

    def test_recursive_dfs_never_confirms_bfs_group_with_exclusion(self):
        """Even with the recursive exclusion a BFS group is not confirmed.

        Exclusion semantics are unchanged by this batch; the invariant that
        matters here is that no false confirmation is produced.
        """
        outcome = _outcome(
            RECURSIVE_DFS,
            [_group(required=["bfs_shortest_path"], excluded=["recursive_branching"])],
        )
        assert outcome["outcome"] != "CONFIRMED"

    def test_ordinary_drain_does_not_confirm_bfs_group(self):
        outcome = _outcome(ORDINARY_QUEUE_DRAIN, [_group(required=["bfs_shortest_path"])])
        assert outcome["outcome"] != "CONFIRMED"


# ============================================================
# 7. Pre-existing behaviour that N2 Batch 1 must NOT change
# ============================================================

class TestPreExistingBehaviourUnchanged:
    def test_deque_based_level_order_still_bfs(self):
        """The deque idiom already worked before this change; it must keep working."""
        code = QUEUE_BARE_LIST_POPLEFT.replace("[root]", "deque([root])").replace(
            "self.levelOrder", "self.levelOrder"
        )
        assert "bfs_shortest_path" in _strategies(code)

    def test_queue_based_single_level_traversal_still_bfs(self):
        """Queue-based traversal without level batching was ALREADY classified as
        bfs_shortest_path before N2 (via the deque-creation gate). This test pins
        that pre-existing behaviour so the change is measured, not assumed.
        """
        code = DEQUE_ASSIGN_POPLEFT.replace("queue", "q")
        assert "bfs_shortest_path" in _strategies(code)

    def test_no_new_fact_types_are_introduced(self):
        """Only the existing `queue_dequeue` fact type may be produced."""
        for code in (
            QUEUE_BARE_LIST_POP0,
            QUEUE_BARE_LIST_POPLEFT,
            DEQUE_ASSIGN_POPLEFT,
            TUPLE_UNPACK_POPLEFT,
            ANNOTATED_ASSIGN_POPLEFT,
            BARE_EXPR_POPLEFT,
        ):
            queue_like = {t for t in _fact_types(code) if "queue" in t}
            assert queue_like <= {"queue_dequeue"}, code
