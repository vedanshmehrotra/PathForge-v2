import ast
import pytest
from pathforge.ast_engine.sanitizer import sanitize_code
from pathforge.ast_engine.extractor import extract_features
from pathforge.ast_engine.classifier import classify_pattern
from pathforge.ast_engine.patterns import BFS_LEVEL_ORDER, BFS_SHORTEST_PATH, DFS_ITERATIVE, DFS_RECURSIVE, TOPOLOGICAL_SORT

def run_classifier(code_string):
    is_safe, errors, root = sanitize_code(code_string)
    assert is_safe, f"Sanitization failed: {errors}"
    features = extract_features(root)
    scores = classify_pattern(features)
    return scores

def test_clean_tree_dfs():
    code = """
def maxDepth(root):
    if not root:
        return 0
    left = maxDepth(root.left)
    right = maxDepth(root.right)
    return max(left, right) + 1
"""
    scores = run_classifier(code)
    # Recursion (0.5) + Conditional (0.1) + Return (0.1) + no DP (0.1) = 0.8
    assert scores[DFS_RECURSIVE] >= 0.8

def test_nested_helper_dfs():
    code = """
class Solution:
    def numIslands(self, grid: list[list[str]]) -> int:
        if not grid:
            return 0
            
        m, n = len(grid), len(grid[0])
        islands = 0
        
        def dfs(r, c):
            if r < 0 or c < 0 or r >= m or c >= n or grid[r][c] == '0':
                return
            grid[r][c] = '0'
            dfs(r+1, c)
            dfs(r-1, c)
            dfs(r, c+1)
            dfs(r, c-1)
            
        for r in range(m):
            for c in range(n):
                if grid[r][c] == '1':
                    islands += 1
                    dfs(r, c)
        return islands
"""
    scores = run_classifier(code)
    # Recursion (0.5) + Helper (0.2) + Conditional (0.1) + Return (0.1) + no DP (0.1) = 1.0
    assert scores[DFS_RECURSIVE] >= 0.9

def test_messy_dfs():
    code = """
# Disorganized solution with random variable naming and prints
class MessySolution:
    def solve_graph_dfs(self, adj_list, src_node, dest_node):
        print("Starting messy search...")
        visited_nodes_set = set()
        
        def traverse_nested_helper_call(curr_loc):
            if curr_loc == dest_node:
                print("Found match!")
                return True
            visited_nodes_set.add(curr_loc)
            for neighbor_val in adj_list[curr_loc]:
                if neighbor_val not in visited_nodes_set:
                    # Renamed variables and print calls
                    ret_bool = traverse_nested_helper_call(neighbor_val)
                    if ret_bool is True:
                        return True
            return False
            
        res_output = traverse_nested_helper_call(src_node)
        print("Finished traverse with result:", res_output)
        return res_output
"""
    scores = run_classifier(code)
    # Recursion (0.5) + Helper (0.2) + Conditional (0.1) + Return (0.1) + no DP (0.1) = 1.0
    assert scores[DFS_RECURSIVE] >= 0.9


@pytest.mark.parametrize("pattern,code", [
    (DFS_ITERATIVE, "def f(g,s):\n st=[s]; seen=set()\n while st:\n  x=st.pop()\n  if x in seen: continue\n  seen.add(x)\n  for y in g[x]: st.append(y)\n return seen\n"),
    (DFS_ITERATIVE, "def f(adj,start):\n bag=[start]\n while bag:\n  cur=bag[-1]; bag.pop()\n  for nxt in adj[cur]: bag.append(nxt)\n return True\n"),
    (BFS_LEVEL_ORDER, "from collections import deque\ndef f(root):\n q=deque([root]); level=0\n while q:\n  node=q.popleft(); level+=1\n  if node.left: q.append(node.left)\n return level\n"),
    (BFS_LEVEL_ORDER, "from collections import deque\ndef f(items):\n todo=deque(items)\n while todo:\n  thing=todo.popleft()\n  if thing.right: todo.append(thing.right)\n return []\n"),
    (BFS_SHORTEST_PATH, "from collections import deque\ndef f(g,s):\n q=deque([s]); dist={s:0}\n while q:\n  x=q.popleft()\n  for y in g[x]:\n   if y not in dist: dist[y]=dist[x]+1; q.append(y)\n return dist\n"),
    (BFS_SHORTEST_PATH, "from collections import deque\ndef f(edges,start):\n queue=deque([start]); distance={start:0}\n while queue:\n  cur=queue.popleft()\n  for nxt in edges[cur]: distance[nxt]=distance[cur]+1; queue.append(nxt)\n return distance\n"),
    (TOPOLOGICAL_SORT, "from collections import deque\ndef f(graph, indegree):\n q=deque()\n for n in range(len(indegree)):\n  if indegree[n]==0: q.append(n)\n while q:\n  x=q.popleft()\n  for y in graph[x]: indegree[y]-=1\n return indegree\n"),
    (TOPOLOGICAL_SORT, "from collections import deque\ndef f(adj, degree):\n ready=deque()\n for i in range(len(degree)):\n  if degree[i]==0: ready.append(i)\n while ready:\n  node=ready.popleft()\n  for nxt in adj[node]: degree[nxt]-=1\n return degree\n"),
])
def test_expanded_graph_patterns(pattern, code):
    assert run_classifier(code)[pattern] >= 0.55
