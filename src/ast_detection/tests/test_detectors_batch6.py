"""Tests for detector implementations in Batch 6 (Topo Sort, Union-Find, Rotated BS)."""

import ast
from src.ast_detection.detectors.topological_sort import TopologicalSortDetector
from src.ast_detection.detectors.union_find import UnionFindDetector
from src.ast_detection.detectors.binary_search_rotated import BinarySearchRotatedDetector
from src.ast_detection.detector_interface import DetectionResult


class TestTopologicalSortDetector:
    def setup_method(self):
        self.detector = TopologicalSortDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "topological_sort"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_indegree(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_plain_bfs(self):
        code = """
def bfs(start, graph):
    q = [start]
    visited = set()
    while q:
        node = q.pop(0)
        visited.add(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                q.append(neighbor)
    return visited
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_plain_dfs(self):
        code = """
def dfs(node, visited):
    visited.add(node)
    for neighbor in node.neighbors:
        if neighbor not in visited:
            dfs(neighbor, visited)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_frequency_count_as_indegree(self):
        code = """
freq = {}
for num in nums:
    freq[num] = freq.get(num, 0) + 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_course_schedule_kahn(self):
        code = """
from collections import deque
def canFinish(numCourses, prerequisites):
    graph = [[] for _ in range(numCourses)]
    indegree = [0] * numCourses
    for u, v in prerequisites:
        graph[v].append(u)
        indegree[u] += 1
    q = deque([i for i in range(numCourses) if indegree[i] == 0])
    count = 0
    while q:
        u = q.popleft()
        count += 1
        for v in graph[u]:
            indegree[v] -= 1
            if indegree[v] == 0:
                q.append(v)
    return count == numCourses
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "indegree_array" for e in result.evidence)
        assert any(e.type == "indegree_increment" for e in result.evidence)
        assert any(e.type == "indegree_decrement" for e in result.evidence)
        assert any(e.type == "zero_indegree_queue" for e in result.evidence)
        assert any(e.type == "conditional_enqueue" for e in result.evidence)

    def test_detected_course_schedule_ii(self):
        code = """
from collections import deque
def findOrder(numCourses, prerequisites):
    graph = [[] for _ in range(numCourses)]
    indegree = [0] * numCourses
    for u, v in prerequisites:
        graph[v].append(u)
        indegree[u] += 1
    q = deque([i for i in range(numCourses) if indegree[i] == 0])
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in graph[u]:
            indegree[v] -= 1
            if indegree[v] == 0:
                q.append(v)
    return order if len(order) == numCourses else []
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "indegree_array" for e in result.evidence)

    def test_detected_alien_dictionary(self):
        code = """
from collections import deque
def alienOrder(words):
    graph = {c: [] for word in words for c in word}
    indegree = {c: 0 for word in words for c in word}
    for i in range(len(words) - 1):
        for a, b in zip(words[i], words[i+1]):
            if a != b:
                graph[a].append(b)
                indegree[b] = indegree.get(b, 0) + 1
                break
    q = deque([c for c in indegree if indegree[c] == 0])
    result = []
    while q:
        c = q.popleft()
        result.append(c)
        for n in graph[c]:
            indegree[n] -= 1
            if indegree[n] == 0:
                q.append(n)
    return "".join(result) if len(result) == len(indegree) else ""
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "indegree_array" for e in result.evidence)

    def test_detected_list_queue_no_deque(self):
        code = """
def canFinish(numCourses, prerequisites):
    indegree = [0] * numCourses
    for u, v in prerequisites:
        indegree[u] += 1
    q = [i for i in range(numCourses) if indegree[i] == 0]
    count = 0
    while q:
        u = q.pop(0)
        count += 1
        for v in range(numCourses):
            pass
    return count == numCourses
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "zero_indegree_queue" for e in result.evidence)

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestUnionFindDetector:
    def setup_method(self):
        self.detector = UnionFindDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "union_find"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_parent(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_ordinary_list(self):
        code = """
class MyClass:
    def __init__(self, n):
        self.data = list(range(n))
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_tree_traversal(self):
        code = """
def inorder(root):
    if root:
        inorder(root.left)
        print(root.val)
        inorder(root.right)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_union_find_classic(self):
        code = """
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x == root_y:
            return False
        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1
        return True

    def connected(self, x, y):
        return self.find(x) == self.find(y)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "parent_array" for e in result.evidence)
        assert any(e.type == "find_recursive" for e in result.evidence)
        assert any(e.type == "union_operation" for e in result.evidence)
        assert any(e.type == "rank_optimization" for e in result.evidence)

    def test_detected_union_find_no_rank(self):
        code = """
class DSU:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x, y):
        self.parent[self.find(x)] = self.find(y)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "parent_array" for e in result.evidence)
        assert any(e.type == "find_iterative" for e in result.evidence)
        assert any(e.type == "union_operation" for e in result.evidence)

    def test_detected_union_find_quick_find(self):
        code = """
class QuickFind:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        return self.parent[x]

    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return
        for i in range(len(self.parent)):
            if self.parent[i] == px:
                self.parent[i] = py
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "parent_array" for e in result.evidence)
        assert any(e.type == "union_operation" for e in result.evidence)

    def test_not_detected_union_find_functional(self):
        code = """
def find(parent, x):
    if parent[x] != x:
        parent[x] = find(parent, parent[x])
    return parent[x]

def union(parent, rank, x, y):
    px, py = find(parent, x), find(parent, y)
    if px == py:
        return
    if rank[px] < rank[py]:
        parent[px] = py
    elif rank[px] > rank[py]:
        parent[py] = px
    else:
        parent[py] = px
        rank[px] += 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_number_of_islands_union_find(self):
        code = """
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.count = n

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        self.parent[rx] = ry
        self.count -= 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "find_recursive" for e in result.evidence)
        assert any(e.type == "union_operation" for e in result.evidence)

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestBinarySearchRotatedDetector:
    def setup_method(self):
        self.detector = BinarySearchRotatedDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "binary_search_rotated"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_loop(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_plain_loop(self):
        code = "for i in range(10):\n    print(i)"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_classic_binary_search(self):
        code = """
left, right = 0, len(nums) - 1
while left <= right:
    mid = (left + right) // 2
    if nums[mid] == target:
        return mid
    elif nums[mid] < target:
        left = mid + 1
    else:
        right = mid - 1
return -1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_answer_space_bs(self):
        code = """
low, high = 1, max_val
while low < high:
    mid = (low + high) // 2
    if is_feasible(mid):
        high = mid
    else:
        low = mid + 1
return low
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_find_min_rotated(self):
        code = """
def findMin(nums):
    left, right = 0, len(nums) - 1
    while left < right:
        mid = (left + right) // 2
        if nums[mid] > nums[right]:
            left = mid + 1
        else:
            right = mid
    return nums[left]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_left_bound_branch(self):
        code = """
left, right = 0, len(nums) - 1
while left <= right:
    mid = (left + right) // 2
    if nums[left] <= nums[mid]:
        left = mid + 1
    else:
        right = mid - 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_rotated_search_basic(self):
        code = """
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
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "sorted_half_comparison" for e in result.evidence)
        assert any(e.type == "target_range_check" for e in result.evidence)
        assert any(e.type == "rotated_midpoint" for e in result.evidence)

    def test_detected_rotated_search_alternative(self):
        code = """
def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] <= nums[hi]:
            if nums[mid] < target <= nums[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
        else:
            if nums[lo] <= target < nums[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
    return -1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "sorted_half_comparison" for e in result.evidence)
        assert any(e.type == "target_range_check" for e in result.evidence)

    def test_detected_rotated_search_ii_with_duplicates(self):
        code = """
def search(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            return True
        if nums[left] < nums[mid]:
            if nums[left] <= target < nums[mid]:
                right = mid - 1
            else:
                left = mid + 1
        elif nums[left] > nums[mid]:
            if nums[mid] < target <= nums[right]:
                left = mid + 1
            else:
                right = mid - 1
        else:
            left += 1
    return False
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "sorted_half_comparison" for e in result.evidence)
        assert any(e.type == "target_range_check" for e in result.evidence)

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected
