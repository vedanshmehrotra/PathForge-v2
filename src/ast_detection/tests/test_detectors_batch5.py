"""Tests for detector implementations in Batch 5 (Graphs & Trees patterns)."""

import ast
from src.ast_detection.detectors.dfs_recursive import DFSRecursiveDetector
from src.ast_detection.detectors.dfs_iterative import DFSIterativeDetector
from src.ast_detection.detectors.bfs_level_order import BFSLevelOrderDetector
from src.ast_detection.detectors.bfs_shortest_path import BFSShortestPathDetector
from src.ast_detection.detectors.binary_search_tree import BinarySearchTreeDetector
from src.ast_detection.detector_interface import DetectionResult


class TestDFSRecursiveDetector:
    def setup_method(self):
        self.detector = DFSRecursiveDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "dfs_recursive"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_recursion(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_fibonacci(self):
        code = """
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_factorial(self):
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_linked_list_traversal(self):
        code = """
def traverse(head):
    if not head:
        return
    print(head.val)
    traverse(head.next)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_binary_search(self):
        code = """
def bs(arr, target, lo, hi):
    if lo > hi:
        return -1
    mid = (lo + hi) // 2
    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        return bs(arr, target, mid + 1, hi)
    else:
        return bs(arr, target, lo, mid - 1)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_graph_dfs(self):
        code = """
def dfs(node, visited):
    if node is None:
        return
    visited.add(node)
    for neighbor in node.neighbors:
        if neighbor not in visited:
            dfs(neighbor, visited)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "recursive_call" for e in result.evidence)
        assert any(e.type == "graph_traversal" for e in result.evidence)
        assert any(e.type == "visited_tracking" for e in result.evidence)
        assert any(e.type == "base_case" for e in result.evidence)

    def test_detected_binary_tree_preorder(self):
        code = """
def dfs(root):
    if not root:
        return
    print(root.val)
    dfs(root.left)
    dfs(root.right)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "recursive_call" for e in result.evidence)
        assert any(e.type == "child_recursion" for e in result.evidence)

    def test_detected_number_of_islands(self):
        code = """
def dfs(grid, i, j):
    if i < 0 or i >= len(grid) or j < 0 or j >= len(grid[0]) or grid[i][j] == '0':
        return
    grid[i][j] = '0'
    dfs(grid, i + 1, j)
    dfs(grid, i - 1, j)
    dfs(grid, i, j + 1)
    dfs(grid, i, j - 1)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "recursive_call" for e in result.evidence)
        assert any(e.type == "grid_expansion" for e in result.evidence)

    def test_detected_max_depth_of_binary_tree(self):
        code = """
def maxDepth(root):
    if not root:
        return 0
    return 1 + max(maxDepth(root.left), maxDepth(root.right))
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "child_recursion" for e in result.evidence)

    def test_detected_adjacency_list_dfs(self):
        code = """
def dfs(node, visited, adj):
    visited.add(node)
    for n in adj[node]:
        if n not in visited:
            dfs(n, visited, adj)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "graph_traversal" for e in result.evidence)

    def test_detected_connected_components(self):
        code = """
def dfs(u, visited, graph):
    visited.add(u)
    for v in graph[u]:
        if v not in visited:
            dfs(v, visited, graph)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "graph_traversal" for e in result.evidence)

    def test_detected_has_path_sum(self):
        code = """
def hasPathSum(root, targetSum):
    if not root:
        return False
    if not root.left and not root.right:
        return root.val == targetSum
    return hasPathSum(root.left, targetSum - root.val) or hasPathSum(root.right, targetSum - root.val)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "child_recursion" for e in result.evidence)
        assert any(e.type == "base_case" for e in result.evidence)

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestDFSIterativeDetector:
    def setup_method(self):
        self.detector = DFSIterativeDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "dfs_iterative"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_loop(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_simple_stack_usage(self):
        code = """
stack = []
stack.append(1)
x = stack.pop()
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_monotonic_stack(self):
        code = """
stack = []
for i in range(len(arr)):
    while stack and arr[stack[-1]] < arr[i]:
        idx = stack.pop()
        result[idx] = arr[i]
    stack.append(i)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_bfs_queue(self):
        code = """
from collections import deque
q = deque([root])
while q:
    node = q.popleft()
    print(node.val)
    if node.left:
        q.append(node.left)
    if node.right:
        q.append(node.right)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_graph_dfs_iterative(self):
        code = """
def dfs_iterative(start, graph):
    stack = [start]
    visited = set()
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                stack.append(neighbor)
    return visited
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "explicit_stack" for e in result.evidence)
        assert any(e.type == "visited_tracking" for e in result.evidence)
        assert any(e.type == "child_push" for e in result.evidence)

    def test_detected_tree_dfs_preorder_iterative(self):
        code = """
def preorder(root):
    stack = [root]
    result = []
    while stack:
        node = stack.pop()
        if node:
            result.append(node.val)
            if node.right:
                stack.append(node.right)
            if node.left:
                stack.append(node.left)
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "explicit_stack" for e in result.evidence)
        assert any(e.type == "child_push" for e in result.evidence)

    def test_detected_inorder_iterative(self):
        code = """
def inorder(root):
    stack = []
    curr = root
    result = []
    while stack or curr:
        while curr:
            stack.append(curr)
            curr = curr.left
        curr = stack.pop()
        result.append(curr.val)
        curr = curr.right
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "explicit_stack" for e in result.evidence)
        assert any(e.type == "stack_traversal" for e in result.evidence)

    def test_detected_maze_dfs(self):
        code = """
def solve_maze(start, maze):
    stack = [start]
    visited = set()
    while stack:
        r, c = stack.pop()
        if (r, c) in visited:
            continue
        visited.add((r, c))
        for dr, dc in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < len(maze) and 0 <= nc < len(maze[0]) and maze[nr][nc] != '#':
                stack.append((nr, nc))
    return visited
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "visited_tracking" for e in result.evidence)

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestBFSLevelOrderDetector:
    def setup_method(self):
        self.detector = BFSLevelOrderDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "bfs_level_order"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_loop(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_simple_deque(self):
        code = """
from collections import deque
dq = deque()
dq.append(1)
x = dq.popleft()
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_monotonic_deque(self):
        code = """
from collections import deque
dq = deque()
for i in range(len(nums)):
    while dq and nums[dq[-1]] < nums[i]:
        dq.pop()
    dq.append(i)
    if dq[0] < i - k + 1:
        dq.popleft()
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_shortest_path_bfs(self):
        code = """
from collections import deque
def shortest(graph, start, end):
    q = deque([start])
    visited = {start}
    dist = 0
    while q:
        for _ in range(len(q)):
            node = q.popleft()
            if node == end:
                return dist
            for neighbor in graph[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    q.append(neighbor)
        dist += 1
    return -1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_binary_tree_level_order(self):
        code = """
from collections import deque
def levelOrder(root):
    if not root:
        return []
    result = []
    q = deque([root])
    while q:
        level_size = len(q)
        level = []
        for _ in range(level_size):
            node = q.popleft()
            level.append(node.val)
            if node.left:
                q.append(node.left)
            if node.right:
                q.append(node.right)
        result.append(level)
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "queue_popleft" for e in result.evidence)
        assert any(e.type == "child_enqueue" for e in result.evidence)
        assert any(e.type == "level_tracking" for e in result.evidence)
        assert any(e.type == "deque_import" for e in result.evidence)

    def test_detected_nary_level_order(self):
        code = """
from collections import deque
def levelOrder(root):
    if not root:
        return []
    result = []
    q = deque([root])
    while q:
        level = []
        for _ in range(len(q)):
            node = q.popleft()
            level.append(node.val)
            for child in node.children:
                q.append(child)
        result.append(level)
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "child_enqueue" for e in result.evidence)
        assert any(e.type == "level_tracking" for e in result.evidence)

    def test_detected_zigzag_level_order(self):
        code = """
from collections import deque
def zigzagLevelOrder(root):
    if not root:
        return []
    result = []
    q = deque([root])
    left_to_right = True
    while q:
        level = []
        for _ in range(len(q)):
            node = q.popleft()
            level.append(node.val)
            if node.left:
                q.append(node.left)
            if node.right:
                q.append(node.right)
        if not left_to_right:
            level.reverse()
        result.append(level)
        left_to_right = not left_to_right
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "queue_popleft" for e in result.evidence)
        assert any(e.type == "child_enqueue" for e in result.evidence)
        assert any(e.type == "level_tracking" for e in result.evidence)

    def test_detected_level_order_list_as_queue(self):
        code = """
def levelOrder(root):
    if not root:
        return []
    result = []
    q = [root]
    while q:
        level = []
        for _ in range(len(q)):
            node = q.pop(0)
            level.append(node.val)
            if node.left:
                q.append(node.left)
            if node.right:
                q.append(node.right)
        result.append(level)
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "queue_popleft" for e in result.evidence) or any(e.type == "child_enqueue" for e in result.evidence)

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestBFSShortestPathDetector:
    def setup_method(self):
        self.detector = BFSShortestPathDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "bfs_shortest_path"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_loop(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_plain_while(self):
        code = """
q = [1, 2]
while q:
    x = q.pop(0)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_tree_level_order(self):
        code = """
from collections import deque
def levelOrder(root):
    if not root:
        return []
    result = []
    q = deque([root])
    while q:
        level = []
        for _ in range(len(q)):
            node = q.popleft()
            level.append(node.val)
            if node.left:
                q.append(node.left)
            if node.right:
                q.append(node.right)
        result.append(level)
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_shortest_path_graph(self):
        code = """
from collections import deque
def shortestPath(graph, start, end):
    q = deque([start])
    visited = {start}
    distance = 0
    while q:
        for _ in range(len(q)):
            node = q.popleft()
            if node == end:
                return distance
            for neighbor in graph[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    q.append(neighbor)
        distance += 1
    return -1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "queue_traversal" for e in result.evidence)
        assert any(e.type == "distance_tracking" for e in result.evidence)
        assert any(e.type == "visited_set" for e in result.evidence)
        assert any(e.type == "neighbor_expansion" for e in result.evidence)

    def test_detected_word_ladder(self):
        code = """
from collections import deque
def ladderLength(beginWord, endWord, wordList):
    wordSet = set(wordList)
    if endWord not in wordSet:
        return 0
    q = deque([(beginWord, 1)])
    visited = {beginWord}
    while q:
        word, length = q.popleft()
        if word == endWord:
            return length
        for i in range(len(word)):
            for c in 'abcdefghijklmnopqrstuvwxyz':
                next_word = word[:i] + c + word[i+1:]
                if next_word in wordSet and next_word not in visited:
                    visited.add(next_word)
                    q.append((next_word, length + 1))
    return 0
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "queue_traversal" for e in result.evidence)
        assert any(e.type == "visited_set" for e in result.evidence)

    def test_detected_rotten_oranges(self):
        code = """
from collections import deque
def orangesRotting(grid):
    rows, cols = len(grid), len(grid[0])
    q = deque()
    fresh = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 1:
                fresh += 1
            elif grid[r][c] == 2:
                q.append((r, c))
    minutes = 0
    while q and fresh > 0:
        for _ in range(len(q)):
            r, c = q.popleft()
            for dr, dc in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 1:
                    grid[nr][nc] = 2
                    fresh -= 1
                    q.append((nr, nc))
        minutes += 1
    return minutes if fresh == 0 else -1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "distance_tracking" for e in result.evidence)
        assert any(e.type == "level_for_loop" for e in result.evidence)

    def test_detected_minimum_knight_moves(self):
        code = """
from collections import deque
def minKnightMoves(x, y):
    target = (x, y)
    q = deque([(0, 0, 0)])
    visited = {(0, 0)}
    moves = [(2, 1), (1, 2), (-1, 2), (-2, 1), (-2, -1), (-1, -2), (1, -2), (2, -1)]
    while q:
        cx, cy, dist = q.popleft()
        if (cx, cy) == target:
            return dist
        for dx, dy in moves:
            nx, ny = cx + dx, cy + dy
            if (nx, ny) not in visited:
                visited.add((nx, ny))
                q.append((nx, ny, dist + 1))
    return -1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "queue_traversal" for e in result.evidence)
        assert any(e.type == "visited_set" for e in result.evidence)

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestBinarySearchTreeDetector:
    def setup_method(self):
        self.detector = BinarySearchTreeDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "binary_search_tree"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_tree(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_binary_tree_traversal_inorder(self):
        code = """
def inorder(root):
    if not root:
        return
    inorder(root.left)
    print(root.val)
    inorder(root.right)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_binary_tree_traversal_preorder(self):
        code = """
def preorder(root):
    if not root:
        return
    print(root.val)
    preorder(root.left)
    preorder(root.right)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_linked_list(self):
        code = """
def searchLinkedList(head, val):
    curr = head
    while curr:
        if curr.val == val:
            return True
        curr = curr.next
    return False
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_array_binary_search(self):
        code = """
def binarySearch(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_bst_search(self):
        code = """
def searchBST(root, val):
    if not root or root.val == val:
        return root
    if val < root.val:
        return searchBST(root.left, val)
    return searchBST(root.right, val)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "bst_comparison" for e in result.evidence)
        assert any(e.type == "bst_recursion" for e in result.evidence)
        assert any(e.type == "bst_operation" for e in result.evidence)

    def test_detected_bst_insert(self):
        code = """
def insertIntoBST(root, val):
    if not root:
        return TreeNode(val)
    if val < root.val:
        root.left = insertIntoBST(root.left, val)
    else:
        root.right = insertIntoBST(root.right, val)
    return root
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "bst_comparison" for e in result.evidence)
        assert any(e.type == "bst_recursion" for e in result.evidence)

    def test_detected_bst_delete(self):
        code = """
def deleteNode(root, key):
    if not root:
        return None
    if key < root.val:
        root.left = deleteNode(root.left, key)
    elif key > root.val:
        root.right = deleteNode(root.right, key)
    else:
        if not root.left:
            return root.right
        if not root.right:
            return root.left
        min_node = findMin(root.right)
        root.val = min_node.val
        root.right = deleteNode(root.right, min_node.val)
    return root
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "bst_comparison" for e in result.evidence)
        assert any(e.type == "bst_recursion" for e in result.evidence)

    def test_detected_bst_validation(self):
        code = """
def isValidBST(root, min_val=float('-inf'), max_val=float('inf')):
    if not root:
        return True
    if root.val <= min_val or root.val >= max_val:
        return False
    return isValidBST(root.left, min_val, root.val) and isValidBST(root.right, root.val, max_val)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "bst_comparison" for e in result.evidence)
        assert any(e.type == "min_max_constraint" for e in result.evidence)

    def test_detected_bst_lowest_common_ancestor(self):
        code = """
def lowestCommonAncestor(root, p, q):
    if p.val < root.val and q.val < root.val:
        return lowestCommonAncestor(root.left, p, q)
    if p.val > root.val and q.val > root.val:
        return lowestCommonAncestor(root.right, p, q)
    return root
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "bst_comparison" for e in result.evidence)
        assert any(e.type == "bst_recursion" for e in result.evidence)

    def test_detected_bst_floor_ceiling(self):
        code = """
def floor(root, key):
    if not root:
        return None
    if root.val == key:
        return root
    if key < root.val:
        return floor(root.left, key)
    res = floor(root.right, key)
    return res if res else root
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "bst_comparison" for e in result.evidence)
        assert any(e.type == "bst_recursion" for e in result.evidence)

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected
