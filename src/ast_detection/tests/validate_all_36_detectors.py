"""Complete validation corpus for ALL 36 detectors.

Reuses existing validation data for the 17 covered detectors and adds
systematic positive/negative cases for the 19 previously uncovered detectors.

Usage:
    python -m src.ast_detection.tests.validate_all_36_detectors
"""

import ast
from collections import defaultdict

# ============================================================================
# EXISTING VALIDATION DATA (reused from previous scripts)
# ============================================================================

from src.ast_detection.tests.test_validation import (
    HASH_MAP_LOOKUP_POSITIVE, HASH_MAP_LOOKUP_NEGATIVE,
    ARRAY_TRAVERSAL_POSITIVE, ARRAY_TRAVERSAL_NEGATIVE,
    SORTING_POSITIVE, SORTING_NEGATIVE,
    BRUTE_FORCE_POSITIVE, BRUTE_FORCE_NEGATIVE,
    FREQUENCY_COUNTING_POSITIVE, FREQUENCY_COUNTING_NEGATIVE,
)
from src.ast_detection.tests.validate_all_detectors import (
    TWO_POINTERS_SAME_POSITIVE, TWO_POINTERS_SAME_NEGATIVE,
    TWO_POINTERS_OPPOSITE_POSITIVE, TWO_POINTERS_OPPOSITE_NEGATIVE,
    SLIDING_WINDOW_FIXED_POSITIVE, SLIDING_WINDOW_FIXED_NEGATIVE,
    SLIDING_WINDOW_VARIABLE_POSITIVE, SLIDING_WINDOW_VARIABLE_NEGATIVE,
    PREFIX_SUM_POSITIVE, PREFIX_SUM_NEGATIVE,
    BINARY_SEARCH_CLASSIC_POSITIVE, BINARY_SEARCH_CLASSIC_NEGATIVE,
    BINARY_SEARCH_ANSWER_POSITIVE, BINARY_SEARCH_ANSWER_NEGATIVE,
    HEAP_PRIORITY_QUEUE_POSITIVE, HEAP_PRIORITY_QUEUE_NEGATIVE,
    MONOTONIC_STACK_POSITIVE, MONOTONIC_STACK_NEGATIVE,
    MONOTONIC_DEQUE_POSITIVE, MONOTONIC_DEQUE_NEGATIVE,
)
from src.ast_detection.tests.validate_17_detectors import (
    FAST_SLOW_POINTERS_POSITIVE, FAST_SLOW_POINTERS_NEGATIVE,
    LINKED_LIST_REVERSAL_POSITIVE, LINKED_LIST_REVERSAL_NEGATIVE,
)

# ============================================================================
# NEW VALIDATION DATA — 19 previously uncovered detectors
# ============================================================================

# --- dfs_recursive ---

DFS_RECURSIVE_POSITIVE = [
    ("graph_dfs_visited", """
def dfs(node, graph, visited):
    if node in visited:
        return
    visited.add(node)
    for neighbor in graph[node]:
        dfs(neighbor, graph, visited)
"""),
    ("tree_preorder", """
def preorder(node):
    if not node:
        return []
    return [node.val] + preorder(node.left) + preorder(node.right)
"""),
    ("number_of_islands", """
def numIslands(grid):
    count = 0
    for i in range(len(grid)):
        for j in range(len(grid[0])):
            if grid[i][j] == '1':
                dfs(grid, i, j)
                count += 1
    return count

def dfs(grid, i, j):
    if i < 0 or j < 0 or i >= len(grid) or j >= len(grid[0]):
        return
    if grid[i][j] != '1':
        return
    grid[i][j] = '0'
    dfs(grid, i+1, j)
    dfs(grid, i-1, j)
    dfs(grid, i, j+1)
    dfs(grid, i, j-1)
"""),
    ("binary_tree_depth", """
def maxDepth(node):
    if not node:
        return 0
    return 1 + max(maxDepth(node.left), maxDepth(node.right))
"""),
    ("connected_components", """
def countComponents(n, edges):
    adj = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    visited = set()
    def dfs(node):
        visited.add(node)
        for nb in adj[node]:
            if nb not in visited:
                dfs(nb)
    count = 0
    for i in range(n):
        if i not in visited:
            dfs(i)
            count += 1
    return count
"""),
    ("path_sum", """
def hasPathSum(root, targetSum):
    if not root:
        return False
    if not root.left and not root.right:
        return targetSum == root.val
    return (hasPathSum(root.left, targetSum - root.val) or
            hasPathSum(root.right, targetSum - root.val))
"""),
    ("all_paths_source_target", """
def allPathsSourceTarget(graph):
    result = []
    def dfs(node, path):
        if node == len(graph) - 1:
            result.append(path[:])
            return
        for nb in graph[node]:
            path.append(nb)
            dfs(nb, path)
            path.pop()
    dfs(0, [0])
    return result
"""),
    ("clone_graph", """
def cloneGraph(node):
    if not node:
        return None
    visited = {}
    def dfs(n):
        if n in visited:
            return visited[n]
        copy = Node(n.val)
        visited[n] = copy
        for nb in n.neighbors:
            copy.neighbors.append(dfs(nb))
        return copy
    return dfs(node)
"""),
    ("loodsum_exists", """
def pathSum(root, targetSum):
    if not root:
        return False
    if not root.left and not root.right:
        return root.val == targetSum
    remaining = targetSum - root.val
    return pathSum(root.left, remaining) or pathSum(root.right, remaining)
"""),
    ("permutations_recursive", """
def permute(nums):
    if len(nums) <= 1:
        return [nums]
    result = []
    for i in range(len(nums)):
        rest = permute(nums[:i] + nums[i+1:])
        for p in rest:
            result.append([nums[i]] + p)
    return result
"""),
]

DFS_RECURSIVE_NEGATIVE = [
    ("no_code", "x = 1"),
    ("simple_function", "def foo(x): return x + 1"),
    ("no_recursion", """
def traverse(arr):
    for x in arr:
        print(x)
"""),
    ("linear_recursion", """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""),
    ("iterative_dfs", """
stack = [root]
visited = set()
while stack:
    node = stack.pop()
    if node not in visited:
        visited.add(node)
        for nb in graph[node]:
            stack.append(nb)
"""),
    ("bfs_queue", """
from collections import deque
queue = deque([root])
while queue:
    node = queue.popleft()
    for nb in graph[node]:
        queue.append(nb)
"""),
    ("binary_search", """
left, right = 0, len(nums) - 1
while left <= right:
    mid = (left + right) // 2
    if nums[mid] == target:
        return mid
    left = mid + 1
"""),
    ("sorting", "arr.sort()"),
    ("hash_map_lookup", """
seen = {}
for x in nums:
    if x in seen:
        return True
    seen[x] = True
"""),
]

# --- dfs_iterative ---

DFS_ITERATIVE_POSITIVE = [
    ("graph_dfs_iterative", """
def dfs_iterative(graph, start):
    stack = [start]
    visited = set()
    while stack:
        node = stack.pop()
        if node not in visited:
            visited.add(node)
            for nb in graph[node]:
                stack.append(nb)
    return visited
"""),
    ("tree_preorder_iterative", """
def preorder(root):
    if not root:
        return []
    stack = [root]
    result = []
    while stack:
        node = stack.pop()
        result.append(node.val)
        if node.right:
            stack.append(node.right)
        if node.left:
            stack.append(node.left)
    return result
"""),
    ("inorder_iterative", """
def inorder(root):
    stack = []
    result = []
    curr = root
    while curr or stack:
        while curr:
            stack.append(curr)
            curr = curr.left
        curr = stack.pop()
        result.append(curr.val)
        curr = curr.right
    return result
"""),
    ("maze_dfs", """
def hasPath(maze, start, destination):
    stack = [start]
    visited = set()
    while stack:
        x, y = stack.pop()
        if (x, y) == tuple(destination):
            return True
        if (x, y) in visited:
            continue
        visited.add((x, y))
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx, ny = x, y
            while 0 <= nx+dx < len(maze) and 0 <= ny+dy < len(maze[0]) and maze[nx+dx][ny+dy] == 0:
                nx += dx
                ny += dy
            stack.append((nx, ny))
    return False
"""),
    ("binary_tree_postorder_iterative", """
def postorder(root):
    if not root:
        return []
    stack = [root]
    result = []
    while stack:
        node = stack.pop()
        result.append(node.val)
        if node.left:
            stack.append(node.left)
        if node.right:
            stack.append(node.right)
    return result[::-1]
"""),
]

DFS_ITERATIVE_NEGATIVE = [
    ("no_code", "x = 1"),
    ("recursive_dfs", """
def dfs(node, visited):
    visited.add(node)
    for nb in graph[node]:
        if nb not in visited:
            dfs(nb, visited)
"""),
    ("bfs_queue", """
from collections import deque
queue = deque([root])
while queue:
    node = queue.popleft()
    print(node.val)
"""),
    ("stack_no_traversal", """
stack = [1, 2, 3]
x = stack.pop()
"""),
    ("queue_fifo", """
q = []
q.append(1)
q.append(2)
x = q.pop(0)
"""),
    ("binary_search", """
left, right = 0, n
while left < right:
    mid = (left + right) // 2
    left = mid + 1
"""),
]

# --- bfs_level_order ---

BFS_LEVEL_ORDER_POSITIVE = [
    ("binary_tree_level_order", """
from collections import deque
def levelOrder(root):
    if not root:
        return []
    result = []
    queue = deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        result.append(level)
    return result
"""),
    ("nary_tree_level_order", """
from collections import deque
def levelOrder(root):
    if not root:
        return []
    result = []
    queue = deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            for child in node.children:
                queue.append(child)
        result.append(level)
    return result
"""),
    ("zigzag_level_order", """
from collections import deque
def zigzagLevelOrder(root):
    if not root:
        return []
    result = []
    queue = deque([root])
    left_to_right = True
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            if left_to_right:
                level.append(node.val)
            else:
                level.insert(0, node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        result.append(level)
        left_to_right = not left_to_right
    return result
"""),
    ("level_order_as_queue", """
def levelOrder(root):
    if not root:
        return []
    result = []
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
        result.append(level)
    return result
"""),
    ("right_side_view", """
from collections import deque
def rightSideView(root):
    if not root:
        return []
    result = []
    queue = deque([root])
    while queue:
        level_size = len(queue)
        for i in range(level_size):
            node = queue.popleft()
            if i == level_size - 1:
                result.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
    return result
"""),
]

BFS_LEVEL_ORDER_NEGATIVE = [
    ("no_code", "x = 1"),
    ("recursive_dfs", """
def dfs(node):
    if not node:
        return
    print(node.val)
    dfs(node.left)
    dfs(node.right)
"""),
    ("iterative_dfs_stack", """
stack = [root]
while stack:
    node = stack.pop()
    print(node.val)
    if node.right:
        stack.append(node.right)
    if node.left:
        stack.append(node.left)
"""),
    ("monotonic_deque", """
from collections import deque
dq = deque()
for i in range(len(nums)):
    while dq and nums[dq[-1]] < nums[i]:
        dq.pop()
    dq.append(i)
"""),
    ("simple_queue", """
q = []
for item in items:
    q.append(item)
while q:
    x = q.pop(0)
    print(x)
"""),
]

# --- bfs_shortest_path ---

BFS_SHORTEST_PATH_POSITIVE = [
    ("shortest_path_graph", """
from collections import deque
def shortestPath(graph, start, end):
    queue = deque([(start, 0)])
    visited = {start}
    while queue:
        node, dist = queue.popleft()
        if node == end:
            return dist
        for nb in graph[node]:
            if nb not in visited:
                visited.add(nb)
                queue.append((nb, dist + 1))
    return -1
"""),
    ("word_ladder", """
from collections import deque
def ladderLength(beginWord, endWord, wordList):
    wordSet = set(wordList)
    queue = deque([(beginWord, 1)])
    visited = {beginWord}
    while queue:
        word, steps = queue.popleft()
        if word == endWord:
            return steps
        for i in range(len(word)):
            for c in 'abcdefghijklmnopqrstuvwxyz':
                new_word = word[:i] + c + word[i+1:]
                if new_word in wordSet and new_word not in visited:
                    visited.add(new_word)
                    queue.append((new_word, steps + 1))
    return 0
"""),
    ("rotten_oranges", """
from collections import deque
def orangesRotting(grid):
    queue = deque()
    fresh = 0
    for i in range(len(grid)):
        for j in range(len(grid[0])):
            if grid[i][j] == 2:
                queue.append((i, j, 0))
            elif grid[i][j] == 1:
                fresh += 1
    minutes = 0
    while queue:
        x, y, t = queue.popleft()
        minutes = max(minutes, t)
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]) and grid[nx][ny] == 1:
                grid[nx][ny] = 2
                fresh -= 1
                queue.append((nx, ny, t + 1))
    return minutes if fresh == 0 else -1
"""),
    ("01_matrix", """
from collections import deque
def updateMatrix(mat):
    m, n = len(mat), len(mat[0])
    queue = deque()
    for i in range(m):
        for j in range(n):
            if mat[i][j] == 0:
                queue.append((i, j))
            else:
                mat[i][j] = float('inf')
    while queue:
        x, y = queue.popleft()
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < m and 0 <= ny < n and mat[nx][ny] > mat[x][y] + 1:
                mat[nx][ny] = mat[x][y] + 1
                queue.append((nx, ny))
    return mat
"""),
]

BFS_SHORTEST_PATH_NEGATIVE = [
    ("no_code", "x = 1"),
    ("bfs_level_order_no_distance", """
from collections import deque
def levelOrder(root):
    if not root:
        return []
    result = []
    queue = deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        result.append(level)
    return result
"""),
    ("iterative_dfs", """
stack = [start]
visited = set()
while stack:
    node = stack.pop()
    visited.add(node)
"""),
    ("dijkstra", """
import heapq
heap = [(0, start)]
while heap:
    dist, node = heapq.heappop(heap)
"""),
]

# --- binary_search_tree ---

BINARY_SEARCH_TREE_POSITIVE = [
    ("bst_search", """
def search(root, val):
    if not root or root.val == val:
        return root
    if val < root.val:
        return search(root.left, val)
    return search(root.right, val)
"""),
    ("bst_insert", """
def insert(root, val):
    if not root:
        return TreeNode(val)
    if val < root.val:
        root.left = insert(root.left, val)
    elif val > root.val:
        root.right = insert(root.right, val)
    return root
"""),
    ("bst_validate", """
def isValidBST(root):
    def validate(node, low, high):
        if not node:
            return True
        if node.val <= low or node.val >= high:
            return False
        return validate(node.left, low, node.val) and validate(node.right, node.val, high)
    return validate(root, float('-inf'), float('inf'))
"""),
    ("bst_lca", """
def lowestCommonAncestor(root, p, q):
    while root:
        if p.val < root.val and q.val < root.val:
            root = root.left
        elif p.val > root.val and q.val > root.val:
            root = root.right
        else:
            return root
"""),
    ("bst_floor_ceiling", """
def floorCeil(root, key):
    floor = None
    ceil = None
    while root:
        if root.val == key:
            return root.val, root.val
        elif root.val < key:
            floor = root.val
            root = root.right
        else:
            ceil = root.val
            root = root.left
    return floor, ceil
"""),
    ("bst_validate_chained", """
def isValidBST(root):
    def helper(node, min_val, max_val):
        if not node:
            return True
        if not (min_val < node.val < max_val):
            return False
        return helper(node.left, min_val, node.val) and helper(node.right, node.val, max_val)
    return helper(root, float('-inf'), float('inf'))
"""),
    ("bst_validate_unaryop", """
def isValidBST(root):
    def check(node, lo, hi):
        if node is None:
            return True
        if node.val <= lo or node.val >= hi:
            return False
        return check(node.left, lo, node.val) and check(node.right, node.val, hi)
    return check(root, float('-inf'), float('inf'))
"""),
    ("bst_delete", """
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
        successor = root.right
        while successor.left:
            successor = successor.left
        root.val = successor.val
        root.right = deleteNode(root.right, successor.val)
    return root
"""),
]

BINARY_SEARCH_TREE_NEGATIVE = [
    ("no_code", "x = 1"),
    ("binary_search_array", """
left, right = 0, len(nums) - 1
while left <= right:
    mid = (left + right) // 2
    if nums[mid] == target:
        return mid
    left = mid + 1
"""),
    ("two_pointers", """
left, right = 0, len(arr) - 1
while left < right:
    if arr[left] + arr[right] == target:
        return [left, right]
    left += 1
"""),
    ("hash_map_lookup", """
seen = {}
for x in nums:
    if x in seen:
        return True
    seen[x] = True
"""),
    ("linked_list_traversal", """
curr = head
while curr:
    print(curr.val)
    curr = curr.next
"""),
]

# --- topological_sort ---

TOPOLOGICAL_SORT_POSITIVE = [
    ("course_schedule_kahn", """
from collections import deque
def canFinish(numCourses, prerequisites):
    adj = [[] for _ in range(numCourses)]
    indegree = [0] * numCourses
    for dest, src in prerequisites:
        adj[src].append(dest)
        indegree[dest] += 1
    queue = deque([i for i in range(numCourses) if indegree[i] == 0])
    count = 0
    while queue:
        node = queue.popleft()
        count += 1
        for nb in adj[node]:
            indegree[nb] -= 1
            if indegree[nb] == 0:
                queue.append(nb)
    return count == numCourses
"""),
    ("course_schedule_ii", """
from collections import deque
def findOrder(numCourses, prerequisites):
    adj = [[] for _ in range(numCourses)]
    indegree = [0] * numCourses
    for dest, src in prerequisites:
        adj[src].append(dest)
        indegree[dest] += 1
    queue = deque([i for i in range(numCourses) if indegree[i] == 0])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for nb in adj[node]:
            indegree[nb] -= 1
            if indegree[nb] == 0:
                queue.append(nb)
    return order if len(order) == numCourses else []
"""),
    ("alien_dictionary", """
from collections import deque
def alienOrder(words):
    adj = {c: set() for w in words for c in w}
    indegree = {c: 0 for c in adj}
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i+1]
        for j in range(min(len(w1), len(w2))):
            if w1[j] != w2[j]:
                if w2[j] not in adj[w1[j]]:
                    adj[w1[j]].add(w2[j])
                    indegree[w2[j]] += 1
                break
    queue = deque([c for c in indegree if indegree[c] == 0])
    result = []
    while queue:
        c = queue.popleft()
        result.append(c)
        for nb in adj[c]:
            indegree[nb] -= 1
            if indegree[nb] == 0:
                queue.append(nb)
    return ''.join(result) if len(result) == len(adj) else ''
"""),
    ("course_schedule_with_list_queue", """
from collections import deque
def canFinish(numCourses, prerequisites):
    adj = [[] for _ in range(numCourses)]
    indeg = [0] * numCourses
    for dest, src in prerequisites:
        adj[src].append(dest)
        indeg[dest] += 1
    q = deque([i for i in range(numCourses) if indeg[i] == 0])
    processed = 0
    while q:
        node = q.popleft()
        processed += 1
        for nb in adj[node]:
            indeg[nb] -= 1
            if indeg[nb] == 0:
                q.append(nb)
    return processed == numCourses
"""),
]

TOPOLOGICAL_SORT_NEGATIVE = [
    ("no_code", "x = 1"),
    ("bfs_no_indegree", """
from collections import deque
def bfs(graph, start):
    queue = deque([start])
    visited = {start}
    while queue:
        node = queue.popleft()
        for nb in graph[node]:
            if nb not in visited:
                visited.add(nb)
                queue.append(nb)
"""),
    ("dfs_recursive", """
def dfs(node, visited):
    visited.add(node)
    for nb in graph[node]:
        if nb not in visited:
            dfs(nb, visited)
"""),
    ("binary_search", """
left, right = 0, n
while left < right:
    mid = (left + right) // 2
"""),
    ("sort_list", "arr.sort()"),
]

# --- union_find ---

UNION_FIND_POSITIVE = [
    ("uf_classic", """
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False
        if self.rank[rx] < self.rank[ry]:
            self.parent[rx] = ry
        elif self.rank[rx] > self.rank[ry]:
            self.parent[ry] = rx
        else:
            self.parent[ry] = rx
            self.rank[rx] += 1
        return True
"""),
    ("uf_no_rank", """
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self.parent[rx] = ry
"""),
    ("uf_quick_find", """
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
    def find(self, x):
        return self.parent[x]
    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px != py:
            for i in range(len(self.parent)):
                if self.parent[i] == px:
                    self.parent[i] = py
"""),
    ("islands_uf", """
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
        self.count = 0
    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self.rank[rx] < self.rank[ry]:
            self.parent[rx] = ry
        elif self.rank[rx] > self.rank[ry]:
            self.parent[ry] = rx
        else:
            self.parent[ry] = rx
            self.rank[rx] += 1
        self.count -= 1
"""),
    ("uf_connected_components", """
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            if self.rank[rx] < self.rank[ry]:
                rx, ry = ry, rx
            self.parent[ry] = rx
            if self.rank[rx] == self.rank[ry]:
                self.rank[rx] += 1
"""),
]

UNION_FIND_NEGATIVE = [
    ("no_code", "x = 1"),
    ("linked_list", """
curr = head
while curr:
    curr = curr.next
"""),
    ("binary_search", """
left, right = 0, n
while left <= right:
    mid = (left + right) // 2
"""),
    ("hash_map", """
d = {}
for x in nums:
    d[x] = True
"""),
    ("simple_array", """
arr = list(range(n))
"""),
    ("tree_traversal", """
def traverse(node):
    if not node:
        return
    traverse(node.left)
    traverse(node.right)
"""),
]

# --- binary_search_rotated ---

BINARY_SEARCH_ROTATED_POSITIVE = [
    ("rotated_search_basic", """
def search(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            return mid
        if nums[left] <= nums[mid]:
            if nums[left] <= target < nums[mid]:
                right = mid - 1
            else:
                left = mid + 1
        else:
            if nums[mid] < target <= nums[right]:
                left = mid + 1
            else:
                right = mid - 1
    return -1
"""),
    ("rotated_min", """
def findMin(nums):
    left, right = 0, len(nums) - 1
    while left < right:
        mid = (left + right) // 2
        if nums[mid] > nums[right]:
            left = mid + 1
        else:
            right = mid
    return nums[left]
"""),
    ("rotated_search_ii", """
def search(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            return True
        while left < mid and nums[left] == nums[mid]:
            left += 1
        while mid < right and nums[right] == nums[mid]:
            right -= 1
        if nums[left] <= nums[mid]:
            if nums[left] <= target < nums[mid]:
                right = mid - 1
            else:
                left = mid + 1
        else:
            if nums[mid] < target <= nums[right]:
                left = mid + 1
            else:
                right = mid - 1
    return False
"""),
]

BINARY_SEARCH_ROTATED_NEGATIVE = [
    ("no_code", "x = 1"),
    ("classic_bs", """
left, right = 0, len(nums) - 1
while left <= right:
    mid = (left + right) // 2
    if nums[mid] == target:
        return mid
    left = mid + 1
"""),
    ("two_pointers", """
left, right = 0, len(arr) - 1
while left < right:
    left += 1
    right -= 1
"""),
    ("linear_search", """
for i in range(len(nums)):
    if nums[i] == target:
        return i
"""),
]

# --- greedy_local ---

GREEDY_LOCAL_POSITIVE = [
    ("kadane_max_subarray", """
def maxSubArray(nums):
    current = 0
    best = float('-inf')
    for num in nums:
        current = max(num, current + num)
        best = max(best, current)
    return best
"""),
    ("best_time_buy_sell", """
def maxProfit(prices):
    min_price = float('inf')
    max_profit = 0
    for price in prices:
        min_price = min(min_price, price)
        max_profit = max(max_profit, price - min_price)
    return max_profit
"""),
    ("jump_game", """
def canJump(nums):
    max_reach = 0
    for i in range(len(nums)):
        if i > max_reach:
            return False
        max_reach = max(max_reach, i + nums[i])
    return True
"""),
    ("candy_greedy", """
def candy(ratings):
    n = len(ratings)
    candies = [1] * n
    for i in range(1, n):
        if ratings[i] > ratings[i-1]:
            candies[i] = candies[i-1] + 1
    for i in range(n-2, -1, -1):
        if ratings[i] > ratings[i+1]:
            candies[i] = max(candies[i], candies[i+1] + 1)
    return sum(candies)
"""),
    ("max_profit_greedy", """
def maxProfit(prices):
    profit = 0
    for i in range(1, len(prices)):
        if prices[i] > prices[i-1]:
            profit += prices[i] - prices[i-1]
    return profit
"""),
]

GREEDY_LOCAL_NEGATIVE = [
    ("no_code", "x = 1"),
    ("dp_1d", """
dp = [0] * (n + 1)
dp[1] = 1
for i in range(2, n + 1):
    dp[i] = dp[i-1] + dp[i-2]
"""),
    ("binary_search", """
left, right = 0, n
while left < right:
    mid = (left + right) // 2
"""),
    ("hash_map_lookup", """
seen = {}
for x in nums:
    if x in seen:
        return True
    seen[x] = True
"""),
    ("sorting_only", "arr.sort()"),
    ("nested_loops", """
for i in range(n):
    for j in range(n):
        print(i, j)
"""),
]

# --- greedy_interval ---

GREEDY_INTERVAL_POSITIVE = [
    ("merge_intervals", """
def merge(intervals):
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
"""),
    ("non_overlapping_intervals", """
def eraseOverlapIntervals(intervals):
    intervals.sort(key=lambda x: x[1])
    count = 0
    prev_end = float('-inf')
    for start, end in intervals:
        if start >= prev_end:
            prev_end = end
        else:
            count += 1
    return count
"""),
    ("min_arrows_burst_balloons", """
def findMinArrowShots(points):
    points.sort(key=lambda x: x[1])
    arrows = 1
    prev_end = points[0][1]
    for start, end in points[1:]:
        if start > prev_end:
            arrows += 1
            prev_end = end
    return arrows
"""),
    ("insert_interval", """
def insert(intervals, newInterval):
    result = []
    for start, end in intervals:
        if end < newInterval[0]:
            result.append([start, end])
        elif start > newInterval[1]:
            result.append(newInterval)
            newInterval = [start, end]
        else:
            newInterval = [min(start, newInterval[0]), max(end, newInterval[1])]
    result.append(newInterval)
    return result
"""),
    ("meeting_rooms_ii", """
import heapq
def minMeetingRooms(intervals):
    intervals.sort(key=lambda x: x[0])
    heap = []
    for start, end in intervals:
        if heap and heap[0] <= start:
            heapq.heapreplace(heap, end)
        else:
            heapq.heappush(heap, end)
    return len(heap)
"""),
]

GREEDY_INTERVAL_NEGATIVE = [
    ("no_code", "x = 1"),
    ("dp_2d", """
dp = [[0]*n for _ in range(m)]
for i in range(1, m):
    for j in range(1, n):
        dp[i][j] = min(dp[i-1][j], dp[i][j-1]) + grid[i][j]
"""),
    ("binary_search", """
left, right = 0, n
while left < right:
    mid = (left + right) // 2
"""),
    ("hash_map", """
seen = {}
for x in nums:
    seen[x] = True
"""),
    ("simple_sort", "arr.sort()"),
    ("nested_loops", """
for i in range(n):
    for j in range(i+1, n):
        if arr[i] + arr[j] == target:
            return [i, j]
"""),
]

# --- backtracking_subset ---

BACKTRACKING_SUBSET_POSITIVE = [
    ("subsets", """
def subsets(nums):
    result = []
    def backtrack(start, path):
        result.append(path[:])
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()
    backtrack(0, [])
    return result
"""),
    ("combination_sum", """
def combinationSum(candidates, target):
    result = []
    def backtrack(start, path, remaining):
        if remaining == 0:
            result.append(path[:])
            return
        for i in range(start, len(candidates)):
            if candidates[i] <= remaining:
                path.append(candidates[i])
                backtrack(i, path, remaining - candidates[i])
                path.pop()
    backtrack(0, [], target)
    return result
"""),
    ("combinations", """
def combine(n, k):
    result = []
    def backtrack(start, path):
        if len(path) == k:
            result.append(path[:])
            return
        for i in range(start, n + 1):
            path.append(i)
            backtrack(i + 1, path)
            path.pop()
    backtrack(1, [])
    return result
"""),
    ("subset_ii", """
def subsetsWithDup(nums):
    nums.sort()
    result = []
    def backtrack(start, path):
        result.append(path[:])
        for i in range(start, len(nums)):
            if i > start and nums[i] == nums[i-1]:
                continue
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()
    backtrack(0, [])
    return result
"""),
    ("letter_combinations", """
def letterCombinations(digits):
    if not digits:
        return []
    mapping = {'2': 'abc', '3': 'def', '4': 'ghi', '5': 'jkl',
               '6': 'mno', '7': 'pqrs', '8': 'tuv', '9': 'wxyz'}
    result = []
    def backtrack(index, path):
        if index == len(digits):
            result.append(''.join(path))
            return
        for char in mapping[digits[index]]:
            path.append(char)
            backtrack(index + 1, path)
            path.pop()
    backtrack(0, [])
    return result
"""),
]

BACKTRACKING_SUBSET_NEGATIVE = [
    ("no_code", "x = 1"),
    ("iterative_subsets", """
result = [[]]
for num in nums:
    result += [subset + [num] for subset in result]
"""),
    ("nested_loops", """
for i in range(n):
    for j in range(n):
        print(i, j)
"""),
    ("binary_search", """
left, right = 0, n
while left <= right:
    mid = (left + right) // 2
"""),
    ("sort", "arr.sort()"),
]

# --- backtracking_permutation ---

BACKTRACKING_PERMUTATION_POSITIVE = [
    ("permutations", """
def permute(nums):
    result = []
    def backtrack(path, remaining):
        if not remaining:
            result.append(path[:])
            return
        for i in range(len(remaining)):
            path.append(remaining[i])
            backtrack(path, remaining[:i] + remaining[i+1:])
            path.pop()
    backtrack([], nums)
    return result
"""),
    ("permutations_swap", """
def permute(nums):
    result = []
    def backtrack(start):
        if start == len(nums):
            result.append(nums[:])
            return
        for i in range(start, len(nums)):
            nums[start], nums[i] = nums[i], nums[start]
            backtrack(start + 1)
            nums[start], nums[i] = nums[i], nums[start]
    backtrack(0)
    return result
"""),
    ("permutations_visited", """
def permute(nums):
    result = []
    def backtrack(path, visited):
        if len(path) == len(nums):
            result.append(path[:])
            return
        for i in range(len(nums)):
            if not visited[i]:
                visited[i] = True
                path.append(nums[i])
                backtrack(path, visited)
                path.pop()
                visited[i] = False
    backtrack([], [False] * len(nums))
    return result
"""),
    ("permutations_ii", """
def permuteUnique(nums):
    nums.sort()
    result = []
    def backtrack(path, visited):
        if len(path) == len(nums):
            result.append(path[:])
            return
        for i in range(len(nums)):
            if visited[i]:
                continue
            if i > 0 and nums[i] == nums[i-1] and not visited[i-1]:
                continue
            visited[i] = True
            path.append(nums[i])
            backtrack(path, visited)
            path.pop()
            visited[i] = False
    backtrack([], [False] * len(nums))
    return result
"""),
    ("n_queens_style", """
def solveNQueens(n):
    result = []
    def backtrack(queens, diag1, diag2, col):
        if len(queens) == n:
            result.append(queens[:])
            return
        for c in range(n):
            if c in col or len(queens) - c in diag1 or len(queens) + c in diag2:
                continue
            queens.append(c)
            diag1.add(len(queens) - 1 - c)
            diag2.add(len(queens) - 1 + c)
            col.add(c)
            backtrack(queens, diag1, diag2, col)
            queens.pop()
            diag1.discard(len(queens) - c)
            diag2.discard(len(queens) + c)
            col.discard(c)
    backtrack([], set(), set(), set())
    return result
"""),
]

BACKTRACKING_PERMUTATION_NEGATIVE = [
    ("no_code", "x = 1"),
    ("iterative_permutations", """
from itertools import permutations
return list(permutations(nums))
"""),
    ("nested_loops", """
for i in range(n):
    for j in range(n):
        print(i, j)
"""),
    ("sort", "arr.sort()"),
    ("binary_search", """
left, right = 0, n
while left <= right:
    mid = (left + right) // 2
"""),
]

# --- dp_1d_forward ---

DP_1D_FORWARD_POSITIVE = [
    ("climbing_stairs_tabulation", """
def climbStairs(n):
    if n <= 2:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    dp[2] = 2
    for i in range(3, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
    return dp[n]
"""),
    ("house_robber", """
def rob(nums):
    if not nums:
        return 0
    if len(nums) == 1:
        return nums[0]
    dp = [0] * len(nums)
    dp[0] = nums[0]
    dp[1] = max(nums[0], nums[1])
    for i in range(2, len(nums)):
        dp[i] = max(dp[i-1], dp[i-2] + nums[i])
    return dp[-1]
"""),
    ("min_cost_climbing", """
def minCostClimbingStairs(cost):
    n = len(cost)
    dp = [0] * (n + 1)
    for i in range(2, n + 1):
        dp[i] = min(dp[i-1] + cost[i-1], dp[i-2] + cost[i-2])
    return dp[n]
"""),
    ("fibonacci_memoized", """
def fib(n):
    memo = [0] * (n + 1)
    memo[1] = 1
    for i in range(2, n + 1):
        memo[i] = memo[i-1] + memo[i-2]
    return memo[n]
"""),
    ("house_robber_cyclic", """
def rob(nums):
    if len(nums) == 1:
        return nums[0]
    def helper(arr):
        n = len(arr)
        if n == 0:
            return 0
        dp = [0] * n
        dp[0] = arr[0]
        if n > 1:
            dp[1] = max(arr[0], arr[1])
        for i in range(2, n):
            dp[i] = max(dp[i-1], dp[i-2] + arr[i])
        return dp[-1]
    return max(helper(nums[1:]), helper(nums[:-1]))
"""),
    ("decode_ways", """
def numDecodings(s):
    if not s or s[0] == '0':
        return 0
    n = len(s)
    dp = [0] * (n + 1)
    dp[0] = 1
    dp[1] = 1
    for i in range(2, n + 1):
        if s[i-1] != '0':
            dp[i] += dp[i-1]
        if 10 <= int(s[i-2:i]) <= 26:
            dp[i] += dp[i-2]
    return dp[n]
"""),
]

DP_1D_FORWARD_NEGATIVE = [
    ("no_code", "x = 1"),
    ("simple_recursion", """
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)
"""),
    ("linear_scan", """
max_val = arr[0]
for x in arr:
    max_val = max(max_val, x)
"""),
    ("hash_map", """
seen = {}
for x in nums:
    seen[x] = True
"""),
    ("sorting", "arr.sort()"),
    ("binary_search", """
left, right = 0, n
while left <= right:
    mid = (left + right) // 2
"""),
]

# --- dp_state_machine ---

DP_STATE_MACHINE_POSITIVE = [
    ("stock_with_cooldown", """
def maxProfit(prices):
    if not prices:
        return 0
    n = len(prices)
    hold = [0] * n
    sold = [0] * n
    rest = [0] * n
    hold[0] = -prices[0]
    for i in range(1, n):
        hold[i] = max(hold[i-1], rest[i-1] - prices[i])
        sold[i] = hold[i-1] + prices[i]
        rest[i] = max(rest[i-1], sold[i-1])
    return max(sold[-1], rest[-1])
"""),
    ("house_robber_state", """
def rob(nums):
    if not nums:
        return 0
    n = len(nums)
    dp = [[0, 0] for _ in range(n)]
    dp[0][1] = nums[0]
    for i in range(1, n):
        dp[i][0] = max(dp[i-1][0], dp[i-1][1])
        dp[i][1] = dp[i-1][0] + nums[i]
    return max(dp[-1][0], dp[-1][1])
"""),
    ("house_robber_optimized", """
def rob(nums):
    prev_no = 0
    prev_yes = 0
    for num in nums:
        temp = prev_no
        prev_no = max(prev_no, prev_yes)
        prev_yes = temp + num
    return max(prev_no, prev_yes)
"""),
    ("paint_house", """
def minCost(costs):
    if not costs:
        return 0
    n = len(costs)
    dp = [[0]*3 for _ in range(n)]
    dp[0] = costs[0][:]
    for i in range(1, n):
        dp[i][0] = costs[i][0] + min(dp[i-1][1], dp[i-1][2])
        dp[i][1] = costs[i][1] + min(dp[i-1][0], dp[i-1][2])
        dp[i][2] = costs[i][2] + min(dp[i-1][0], dp[i-1][1])
    return min(dp[-1])
"""),
]

DP_STATE_MACHINE_NEGATIVE = [
    ("no_code", "x = 1"),
    ("dp_1d", """
dp = [0] * (n + 1)
dp[1] = 1
for i in range(2, n + 1):
    dp[i] = dp[i-1] + dp[i-2]
"""),
    ("greedy", """
best = float('-inf')
current = 0
for x in nums:
    current = max(x, current + x)
    best = max(best, current)
"""),
    ("binary_search", """
left, right = 0, n
while left <= right:
    mid = (left + right) // 2
"""),
]

# --- dp_1d_sequence ---

DP_1D_SEQUENCE_POSITIVE = [
    ("lis_tabulation", """
def lengthOfLIS(nums):
    n = len(nums)
    dp = [1] * n
    for i in range(1, n):
        for j in range(i):
            if nums[j] < nums[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)
"""),
    ("russian_doll", """
def maxEnvelopes(envelopes):
    envelopes.sort(key=lambda x: (x[0], -x[1]))
    heights = [e[1] for e in envelopes]
    dp = [1] * len(heights)
    for i in range(1, len(heights)):
        for j in range(i):
            if heights[j] < heights[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)
"""),
    ("longest_increasing_subsequence_with_binary_search", """
import bisect
def lengthOfLIS(nums):
    tails = []
    for num in nums:
        pos = bisect.bisect_left(tails, num)
        if pos == len(tails):
            tails.append(num)
        else:
            tails[pos] = num
    return len(tails)
"""),
]

DP_1D_SEQUENCE_NEGATIVE = [
    ("no_code", "x = 1"),
    ("dp_1d_forward", """
dp = [0] * (n + 1)
dp[1] = 1
for i in range(2, n + 1):
    dp[i] = dp[i-1] + dp[i-2]
"""),
    ("greedy", """
best = float('-inf')
for x in nums:
    best = max(best, x)
"""),
    ("sort", "arr.sort()"),
]

# --- dp_2d_grid ---

DP_2D_GRID_POSITIVE = [
    ("min_path_sum", """
def minPathSum(grid):
    m, n = len(grid), len(grid[0])
    dp = [[0]*n for _ in range(m)]
    dp[0][0] = grid[0][0]
    for i in range(1, m):
        dp[i][0] = dp[i-1][0] + grid[i][0]
    for j in range(1, n):
        dp[0][j] = dp[0][j-1] + grid[0][j]
    for i in range(1, m):
        for j in range(1, n):
            dp[i][j] = min(dp[i-1][j], dp[i][j-1]) + grid[i][j]
    return dp[m-1][n-1]
"""),
    ("unique_paths", """
def uniquePaths(m, n):
    dp = [[1]*n for _ in range(m)]
    for i in range(1, m):
        for j in range(1, n):
            dp[i][j] = dp[i-1][j] + dp[i][j-1]
    return dp[m-1][n-1]
"""),
    ("maximal_square", """
def maximalSquare(matrix):
    if not matrix:
        return 0
    m, n = len(matrix), len(matrix[0])
    dp = [[0]*n for _ in range(m)]
    max_side = 0
    for i in range(m):
        for j in range(n):
            if matrix[i][j] == '1':
                if i == 0 or j == 0:
                    dp[i][j] = 1
                else:
                    dp[i][j] = min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]) + 1
                max_side = max(max_side, dp[i][j])
    return max_side * max_side
"""),
]

DP_2D_GRID_NEGATIVE = [
    ("no_code", "x = 1"),
    ("dp_1d", """
dp = [0] * (n + 1)
dp[1] = 1
for i in range(2, n + 1):
    dp[i] = dp[i-1] + dp[i-2]
"""),
    ("nested_loops_no_dp", """
for i in range(m):
    for j in range(n):
        print(matrix[i][j])
"""),
    ("greedy", """
best = float('-inf')
for x in nums:
    best = max(best, x)
"""),
]

# --- dp_2d_string ---

DP_2D_STRING_POSITIVE = [
    ("longest_common_subsequence", """
def longestCommonSubsequence(text1, text2):
    m, n = len(text1), len(text2)
    dp = [[0]*(n+1) for _ in range(m+1)]
    for i in range(1, m+1):
        for j in range(1, n+1):
            if text1[i-1] == text2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[m][n]
"""),
    ("edit_distance", """
def minDistance(word1, word2):
    m, n = len(word1), len(word2)
    dp = [[0]*(n+1) for _ in range(m+1)]
    for i in range(m+1):
        dp[i][0] = i
    for j in range(n+1):
        dp[0][j] = j
    for i in range(1, m+1):
        for j in range(1, n+1):
            if word1[i-1] == word2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    return dp[m][n]
"""),
    ("distinct_subsequences", """
def numDistinct(s, t):
    m, n = len(s), len(t)
    dp = [[0]*(n+1) for _ in range(m+1)]
    for i in range(m+1):
        dp[i][0] = 1
    for i in range(1, m+1):
        for j in range(1, n+1):
            if s[i-1] == t[j-1]:
                dp[i][j] = dp[i-1][j-1] + dp[i-1][j]
            else:
                dp[i][j] = dp[i-1][j]
    return dp[m][n]
"""),
]

DP_2D_STRING_NEGATIVE = [
    ("no_code", "x = 1"),
    ("hash_map", """
seen = {}
for x in s:
    seen[x] = True
"""),
    ("two_pointers", """
i, j = 0, len(s) - 1
while i < j:
    i += 1
    j -= 1
"""),
    ("sorting", "arr.sort()"),
]

# --- dp_knapsack ---

DP_KNAPSACK_POSITIVE = [
    ("knapsack_01", """
def knapsack(W, wt, val, n):
    dp = [[0]*(W+1) for _ in range(n+1)]
    for i in range(1, n+1):
        for w in range(1, W+1):
            if wt[i-1] <= w:
                dp[i][w] = max(dp[i-1][w], dp[i-1][w-wt[i-1]] + val[i-1])
            else:
                dp[i][w] = dp[i-1][w]
    return dp[n][W]
"""),
    ("partition_equal_subset_sum", """
def canPartition(nums):
    total = sum(nums)
    if total % 2 != 0:
        return False
    target = total // 2
    dp = [False] * (target + 1)
    dp[0] = True
    for num in nums:
        for j in range(target, num - 1, -1):
            dp[j] = dp[j] or dp[j - num]
    return dp[target]
"""),
    ("coin_change", """
def coinChange(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for coin in coins:
        for i in range(coin, amount + 1):
            dp[i] = min(dp[i], dp[i - coin] + 1)
    return dp[amount] if dp[amount] != float('inf') else -1
"""),
]

DP_KNAPSACK_NEGATIVE = [
    ("no_code", "x = 1"),
    ("greedy", """
for coin in coins:
    while amount >= coin:
        amount -= coin
        count += 1
"""),
    ("sort", "arr.sort()"),
    ("linear_scan", """
max_val = arr[0]
for x in arr:
    max_val = max(max_val, x)
"""),
]

# --- dp_interval ---

DP_INTERVAL_POSITIVE = [
    ("matrix_chain", """
def matrixChainOrder(dims):
    n = len(dims) - 1
    dp = [[0]*n for _ in range(n)]
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            dp[i][j] = float('inf')
            for k in range(i, j):
                cost = dp[i][k] + dp[k+1][j] + dims[i] * dims[k+1] * dims[j+1]
                dp[i][j] = min(dp[i][j], cost)
    return dp[0][n-1]
"""),
    ("palindrome_partitioning", """
def minCuts(s):
    n = len(s)
    is_palindrome = [[False]*n for _ in range(n)]
    for i in range(n):
        is_palindrome[i][i] = True
    for length in range(2, n+1):
        for i in range(n-length+1):
            j = i + length - 1
            if s[i] == s[j]:
                is_palindrome[i][j] = length == 2 or is_palindrome[i+1][j-1]
    dp = [0] * n
    for i in range(n):
        if is_palindrome[0][i]:
            dp[i] = 0
        else:
            dp[i] = i
            for j in range(1, i+1):
                if is_palindrome[j][i]:
                    dp[i] = min(dp[i], dp[j-1] + 1)
    return dp[n-1]
"""),
    ("longest_palindromic_subsequence", """
def longestPalindromeSubseq(s):
    n = len(s)
    dp = [[0]*n for _ in range(n)]
    for i in range(n):
        dp[i][i] = 1
    for length in range(2, n+1):
        for i in range(n-length+1):
            j = i + length - 1
            if s[i] == s[j]:
                dp[i][j] = dp[i+1][j-1] + 2
            else:
                dp[i][j] = max(dp[i+1][j], dp[i][j-1])
    return dp[0][n-1]
"""),
]

DP_INTERVAL_NEGATIVE = [
    ("no_code", "x = 1"),
    ("dp_1d", """
dp = [0] * (n + 1)
dp[1] = 1
for i in range(2, n + 1):
    dp[i] = dp[i-1] + dp[i-2]
"""),
    ("sort", "arr.sort()"),
    ("greedy", """
best = float('-inf')
for x in nums:
    best = max(best, x)
"""),
]

# ============================================================================
# VALIDATION CORPUS ASSEMBLY
# ============================================================================

VALIDATION_CORPUS = {
    # Existing 17 detectors
    'hash_map_lookup': (HASH_MAP_LOOKUP_POSITIVE, HASH_MAP_LOOKUP_NEGATIVE),
    'array_traversal': (ARRAY_TRAVERSAL_POSITIVE, ARRAY_TRAVERSAL_NEGATIVE),
    'sorting': (SORTING_POSITIVE, SORTING_NEGATIVE),
    'brute_force': (BRUTE_FORCE_POSITIVE, BRUTE_FORCE_NEGATIVE),
    'hash_map_frequency': (FREQUENCY_COUNTING_POSITIVE, FREQUENCY_COUNTING_NEGATIVE),
    'two_pointers_same': (TWO_POINTERS_SAME_POSITIVE, TWO_POINTERS_SAME_NEGATIVE),
    'two_pointers_opposite': (TWO_POINTERS_OPPOSITE_POSITIVE, TWO_POINTERS_OPPOSITE_NEGATIVE),
    'sliding_window_fixed': (SLIDING_WINDOW_FIXED_POSITIVE, SLIDING_WINDOW_FIXED_NEGATIVE),
    'sliding_window_variable': (SLIDING_WINDOW_VARIABLE_POSITIVE, SLIDING_WINDOW_VARIABLE_NEGATIVE),
    'prefix_sum': (PREFIX_SUM_POSITIVE, PREFIX_SUM_NEGATIVE),
    'binary_search_standard': (BINARY_SEARCH_CLASSIC_POSITIVE, BINARY_SEARCH_CLASSIC_NEGATIVE),
    'binary_search_answer': (BINARY_SEARCH_ANSWER_POSITIVE, BINARY_SEARCH_ANSWER_NEGATIVE),
    'heap_top_k': (HEAP_PRIORITY_QUEUE_POSITIVE, HEAP_PRIORITY_QUEUE_NEGATIVE),
    'monotonic_stack': (MONOTONIC_STACK_POSITIVE, MONOTONIC_STACK_NEGATIVE),
    'monotonic_deque': (MONOTONIC_DEQUE_POSITIVE, MONOTONIC_DEQUE_NEGATIVE),
    'fast_slow_pointers': (FAST_SLOW_POINTERS_POSITIVE, FAST_SLOW_POINTERS_NEGATIVE),
    'linked_list_reversal': (LINKED_LIST_REVERSAL_POSITIVE, LINKED_LIST_REVERSAL_NEGATIVE),
    # New 19 detectors
    'dfs_recursive': (DFS_RECURSIVE_POSITIVE, DFS_RECURSIVE_NEGATIVE),
    'dfs_iterative': (DFS_ITERATIVE_POSITIVE, DFS_ITERATIVE_NEGATIVE),
    'bfs_level_order': (BFS_LEVEL_ORDER_POSITIVE, BFS_LEVEL_ORDER_NEGATIVE),
    'bfs_shortest_path': (BFS_SHORTEST_PATH_POSITIVE, BFS_SHORTEST_PATH_NEGATIVE),
    'binary_search_tree': (BINARY_SEARCH_TREE_POSITIVE, BINARY_SEARCH_TREE_NEGATIVE),
    'topological_sort': (TOPOLOGICAL_SORT_POSITIVE, TOPOLOGICAL_SORT_NEGATIVE),
    'union_find': (UNION_FIND_POSITIVE, UNION_FIND_NEGATIVE),
    'binary_search_rotated': (BINARY_SEARCH_ROTATED_POSITIVE, BINARY_SEARCH_ROTATED_NEGATIVE),
    'greedy_local': (GREEDY_LOCAL_POSITIVE, GREEDY_LOCAL_NEGATIVE),
    'greedy_interval': (GREEDY_INTERVAL_POSITIVE, GREEDY_INTERVAL_NEGATIVE),
    'backtracking_subset': (BACKTRACKING_SUBSET_POSITIVE, BACKTRACKING_SUBSET_NEGATIVE),
    'backtracking_permutation': (BACKTRACKING_PERMUTATION_POSITIVE, BACKTRACKING_PERMUTATION_NEGATIVE),
    'dp_1d_forward': (DP_1D_FORWARD_POSITIVE, DP_1D_FORWARD_NEGATIVE),
    'dp_state_machine': (DP_STATE_MACHINE_POSITIVE, DP_STATE_MACHINE_NEGATIVE),
    'dp_1d_sequence': (DP_1D_SEQUENCE_POSITIVE, DP_1D_SEQUENCE_NEGATIVE),
    'dp_2d_grid': (DP_2D_GRID_POSITIVE, DP_2D_GRID_NEGATIVE),
    'dp_2d_string': (DP_2D_STRING_POSITIVE, DP_2D_STRING_NEGATIVE),
    'dp_knapsack': (DP_KNAPSACK_POSITIVE, DP_KNAPSACK_NEGATIVE),
    'dp_interval': (DP_INTERVAL_POSITIVE, DP_INTERVAL_NEGATIVE),
}


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_all_validations():
    from src.ast_detection.registry import get_all_detectors
    
    all_detectors = {d.pattern_id: d for d in get_all_detectors()}
    
    all_tp = all_fn = all_fp = all_tn = 0
    all_confidences = []
    detector_results = {}
    
    missing_detectors = []
    
    for det_id in sorted(all_detectors.keys()):
        if det_id not in VALIDATION_CORPUS:
            missing_detectors.append(det_id)
            continue
        
        positives, negatives = VALIDATION_CORPUS[det_id]
        detector = all_detectors[det_id]
        
        tp = fn = fp = tn = 0
        confidences = []
        false_negatives = []
        false_positives = []
        
        for name, code in positives:
            try:
                tree = ast.parse(code)
                result = detector.detect(tree)
                if result.detected:
                    tp += 1
                    confidences.append(result.confidence)
                else:
                    fn += 1
                    false_negatives.append((name, result.confidence))
            except Exception as e:
                fn += 1
                false_negatives.append((name, 0.0))
        
        for name, code in negatives:
            try:
                tree = ast.parse(code)
                result = detector.detect(tree)
                if result.detected:
                    fp += 1
                    false_positives.append((name, result.confidence))
                else:
                    tn += 1
            except Exception as e:
                tn += 1
        
        prec = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        
        detector_results[det_id] = {
            'tp': tp, 'fn': fn, 'fp': fp, 'tn': tn,
            'prec': prec, 'rec': rec, 'f1': f1,
            'avg_conf': avg_conf,
            'false_negatives': false_negatives,
            'false_positives': false_positives,
        }
        
        all_tp += tp; all_fn += fn; all_fp += fp; all_tn += tn
        all_confidences.extend(confidences)
    
    # Print results
    print("=" * 80)
    print("  COMPLETE 36-DETECTOR VALIDATION")
    print("=" * 80)
    print()
    
    print(f"  {'Detector':<28} {'TP':>3} {'FN':>3} {'FP':>3} {'TN':>3} {'Prec':>6} {'Rec':>6} {'F1':>6} {'AvgC':>5}")
    print(f"  {'-'*28} {'-'*3} {'-'*3} {'-'*3} {'-'*3} {'-'*6} {'-'*6} {'-'*6} {'-'*5}")
    
    for det_id in sorted(detector_results.keys()):
        r = detector_results[det_id]
        marker = ""
        if r['fn'] > 0:
            marker += " FN"
        if r['fp'] > 0:
            marker += " FP"
        print(f"  {det_id:<28} {r['tp']:>3} {r['fn']:>3} {r['fp']:>3} {r['tn']:>3} "
              f"{r['prec']:>6.4f} {r['rec']:>6.4f} {r['f1']:>6.4f} {r['avg_conf']:>5.3f}{marker}")
    
    print(f"  {'-'*28} {'-'*3} {'-'*3} {'-'*3} {'-'*3} {'-'*6} {'-'*6} {'-'*6} {'-'*5}")
    
    overall_prec = all_tp / (all_tp + all_fp) if (all_tp + all_fp) > 0 else 0
    overall_rec = all_tp / (all_tp + all_fn) if (all_tp + all_fn) > 0 else 0
    overall_f1 = 2 * overall_prec * overall_rec / (overall_prec + overall_rec) if (overall_prec + overall_rec) > 0 else 0
    overall_avg = sum(all_confidences) / len(all_confidences) if all_confidences else 0
    
    print(f"  {'TOTAL':<28} {all_tp:>3} {all_fn:>3} {all_fp:>3} {all_tn:>3} "
          f"{overall_prec:>6.4f} {overall_rec:>6.4f} {overall_f1:>6.4f} {overall_avg:>5.3f}")
    
    print(f"\\n  Total test cases: {all_tp + all_fn + all_fp + all_tn}")
    print(f"  Detectors with data: {len(detector_results)}/{len(all_detectors)}")
    
    if missing_detectors:
        print(f"\\n  WARNING: No validation data for: {', '.join(missing_detectors)}")
    
    # Print false negative details
    print("\\n" + "=" * 80)
    print("  FALSE NEGATIVE DETAILS")
    print("=" * 80)
    
    for det_id in sorted(detector_results.keys()):
        fns = detector_results[det_id]['false_negatives']
        if fns:
            print(f"\\n  {det_id}:")
            for name, conf in fns:
                print(f"    - {name} (conf={conf:.2f})")
    
    # Print false positive details
    print("\\n" + "=" * 80)
    print("  FALSE POSITIVE DETAILS")
    print("=" * 80)
    
    for det_id in sorted(detector_results.keys()):
        fps = detector_results[det_id]['false_positives']
        if fps:
            print(f"\\n  {det_id}:")
            for name, conf in fps:
                print(f"    - {name} (conf={conf:.2f})")
    
    return detector_results


if __name__ == "__main__":
    run_all_validations()
