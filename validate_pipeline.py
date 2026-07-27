#!/usr/bin/env python3
"""
Pipeline Validation Script
Tests the complete AST + Matching Engine pipeline against representative
LeetCode problems across all pattern categories.

Usage: python validate_pipeline.py
"""

import json
import sys
import os

# Force UTF-8 output encoding to avoid UnicodeEncodeError on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ast_detection.run_analysis import ASTAnalysisEngine
from src.matching_engine.matching_engine import MatchingEngine

_ast_engine = ASTAnalysisEngine()
_matching_engine = MatchingEngine()

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"

results = []
errors = []


def run_problem(name: str, code: str, expected_groups: list, notes: str = ""):
    """Run AST analysis + matching engine and record results."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"  Expected groups: {expected_groups}")
    print(f"  Notes: {notes}")
    print(f"{'='*60}")

    # Step 1: AST analysis
    try:
        ast_output = _ast_engine.analyze(code)
    except Exception as e:
        errors.append({"problem": name, "stage": "AST", "error": str(e)})
        print(f"  {FAIL} AST analysis failed: {e}")
        results.append({
            "name": name,
            "expected_groups": expected_groups,
            "status": "AST_ERROR",
            "error": str(e),
            "detected": [],
            "verdict": "N/A",
            "confidence": 0.0,
            "unmatched": [],
        })
        return

    detected = ast_output.get("detected_patterns", [])
    print(f"\n  Detected patterns ({len(detected)}):")
    for dp in detected:
        pid = dp.get("pattern_id", "?")
        conf = dp.get("confidence", 0.0)
        evidence = dp.get("evidence", [])
        print(f"    {pid}: conf={conf:.4f}, evidence={len(evidence)} items")

    # Step 2: Build matching engine input
    ast_for_matching = [
        {
            "pattern_id": entry.get("pattern_id", ""),
            "confidence": entry.get("confidence", 0.0),
        }
        for entry in detected
    ]

    # Normalize expected groups — accept both dict ({"patterns": [...]}) and list ([...])
    normalized_groups = []
    for g in expected_groups:
        if isinstance(g, dict):
            group_list = g.get("patterns", [])
        else:
            group_list = g
        normalized_groups.append(group_list)

    llm_input = {
        "accepted_solution_groups": normalized_groups
    }

    # Step 3: Matching engine
    try:
        match_result = _matching_engine.match(llm_input, ast_for_matching)
    except Exception as e:
        errors.append({"problem": name, "stage": "MATCHING", "error": str(e)})
        print(f"  {FAIL} Matching engine failed: {e}")
        results.append({
            "name": name,
            "expected_groups": expected_groups,
            "status": "MATCHING_ERROR",
            "error": str(e),
            "detected": [d["pattern_id"] for d in detected],
            "verdict": "N/A",
            "confidence": 0.0,
            "unmatched": [],
        })
        return

    verdict = match_result["match_result"]
    confidence = match_result["confidence_score"]
    unmatched = match_result["unmatched_patterns"]
    matched_groups = match_result["matched_groups"]
    signals = match_result.get("reasoning_signals", [])

    print(f"\n  Results:")
    print(f"    Verdict:       {verdict}")
    print(f"    Confidence:    {confidence:.4f}")
    print(f"    Matched groups: {matched_groups}")
    print(f"    Unmatched:     {unmatched}")
    for s in signals:
        print(f"    Signal: {s}")

    # Determine status and flags
    all_expected = set()
    for g in normalized_groups:
        for p in g:
            all_expected.add(p)

    detected_ids = set(d["pattern_id"] for d in detected)
    expected_present = all_expected.issubset(detected_ids) if all_expected else False

    status = "PASS"
    flags = []

    # Flag: NO_MATCH despite all expected patterns present
    if verdict == "NO_MATCH" and expected_present:
        flags.append(f"{FAIL} Correct solution produced NO_MATCH (all expected patterns detected but no group fully matched)")
        status = "FAIL"
    elif verdict == "NO_MATCH":
        flags.append(f"{WARN} NO_MATCH — expected patterns not fully detected")

    # Flag: low confidence
    if confidence < 0.5 and verdict == "FULL_MATCH":
        flags.append(f"{WARN} Low confidence ({confidence:.2f}) despite FULL_MATCH")
    elif confidence < 0.3 and verdict not in ("N/A",):
        flags.append(f"{WARN} Very low confidence ({confidence:.2f})")

    # Flag: FULL_MATCH with near-zero confidence
    if verdict == "FULL_MATCH" and confidence < 0.1:
        flags.append(f"{FAIL} FULL_MATCH with near-zero confidence ({confidence:.4f})")

    print(f"    Status:        {status}")
    for f in flags:
        print(f"    {f}")

    results.append({
        "name": name,
        "expected_groups": expected_groups,
        "status": status,
        "flags": flags,
        "detected": [d["pattern_id"] for d in detected],
        "detected_with_conf": {d["pattern_id"]: d["confidence"] for d in detected},
        "verdict": verdict,
        "confidence": confidence,
        "unmatched": unmatched,
        "matched_groups": matched_groups,
    })


def print_summary():
    """Print the final validation report."""
    print(f"\n\n{'='*70}")
    print(f"  VALIDATION REPORT")
    print(f"{'='*70}")

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    print(f"\n  Total:  {total}")
    print(f"  Passed: {PASS} {passed}")
    print(f"  Failed: {FAIL} {failed}")

    # Group results by verdict
    verdicts = {}
    for r in results:
        v = r["verdict"]
        if v not in verdicts:
            verdicts[v] = []
        verdicts[v].append(r)

    print(f"\n  Results by verdict:")
    for v in ["FULL_MATCH", "PARTIAL_MATCH", "NO_MATCH"]:
        items = verdicts.get(v, [])
        status_counts = {}
        for r in items:
            s = r["status"]
            status_counts[s] = status_counts.get(s, 0) + 1
        print(f"    {v}: {len(items)} problems {status_counts}")

    print(f"\n  {'='*60}")
    for r in results:
        icon = PASS if r["status"] == "PASS" else FAIL
        detected_str = ", ".join(f"{p}({r['detected_with_conf'].get(p, 0):.2f})" for p in r["detected"])
        print(f"  {icon} {r['name']}")
        print(f"       Verdict: {r['verdict']} | Conf: {r['confidence']:.2f} | Unmatched: {r['unmatched']}")
        print(f"       Detected: {detected_str}")
        for f in r.get("flags", []):
            print(f"       {f}")


# =============================================================================
# TEST CASES
# Note: expected groups use the DETECTOR's pattern_id, not the file name.
# For example, binary_search_classic.py has pattern_id="binary_search_standard".
# =============================================================================

test_problems = []

# --- 1. ARRAYS ---
test_problems.append(("Arrays: Two Sum (hash_map)", """
def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
""", [{"patterns": ["hash_map_lookup"]}], "Classic hash map lookup"))

# --- 2. TWO POINTERS ---
test_problems.append(("Two Pointers: 3Sum (two_pointers_opposite)", """
def threeSum(nums):
    nums.sort()
    result = []
    n = len(nums)
    for i in range(n - 2):
        if i > 0 and nums[i] == nums[i - 1]:
            continue
        left, right = i + 1, n - 1
        while left < right:
            total = nums[i] + nums[left] + nums[right]
            if total < 0:
                left += 1
            elif total > 0:
                right -= 1
            else:
                result.append([nums[i], nums[left], nums[right]])
                while left < right and nums[left] == nums[left + 1]:
                    left += 1
                while left < right and nums[right] == nums[right - 1]:
                    right -= 1
                left += 1
                right -= 1
    return result
""", [{"patterns": ["two_pointers_opposite"]}], "Sort + two-pointer with BoolOp condition"))

# --- 3. SLIDING WINDOW ---
test_problems.append(("Sliding Window: Longest Substring (variable)", """
def lengthOfLongestSubstring(s):
    char_set = set()
    left = 0
    max_len = 0
    for right in range(len(s)):
        while s[right] in char_set:
            char_set.remove(s[left])
            left += 1
        char_set.add(s[right])
        max_len = max(max_len, right - left + 1)
    return max_len
""", [{"patterns": ["sliding_window_variable"]}], "Variable sliding window with set"))

# --- 4. BINARY SEARCH ---
test_problems.append(("Binary Search: Classic (binary_search_standard)", """
def binarySearch(nums, target):
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
""", [{"patterns": ["binary_search_standard"]}], "Note: detector's pattern_id is binary_search_standard"))

# --- 5. DFS ---
test_problems.append(("DFS: Binary Tree Inorder (dfs_recursive)", """
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def inorderTraversal(root):
    result = []
    def dfs(node):
        if not node:
            return
        dfs(node.left)
        result.append(node.val)
        dfs(node.right)
    dfs(root)
    return result
""", [{"patterns": ["dfs_recursive"]}], "Recursive DFS on binary tree"))

# --- 6. BFS ---
test_problems.append(("BFS: Level Order (bfs_level_order)", """
from collections import deque

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

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
""", [{"patterns": ["bfs_level_order"]}], "BFS with deque"))

# --- 7. TREE ---
test_problems.append(("Tree: Validate BST (binary_search_tree)", """
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def isValidBST(root):
    def validate(node, low, high):
        if not node:
            return True
        if not (low < node.val < high):
            return False
        return validate(node.left, low, node.val) and validate(node.right, node.val, high)
    return validate(root, float('-inf'), float('inf'))
""", [{"patterns": ["binary_search_tree"]}], "BST validation with range check"))

# --- 8. GRAPH ---
test_problems.append(("Graph: Number of Islands (dfs_recursive)", """
def numIslands(grid):
    if not grid:
        return 0
    rows, cols = len(grid), len(grid[0])
    count = 0

    def dfs(r, c):
        if r < 0 or r >= rows or c < 0 or c >= cols or grid[r][c] == '0':
            return
        grid[r][c] = '0'
        dfs(r + 1, c)
        dfs(r - 1, c)
        dfs(r, c + 1)
        dfs(r, c - 1)

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '1':
                count += 1
                dfs(r, c)
    return count
""", [{"patterns": ["dfs_recursive"]}], "Grid DFS (4-dir)"))

# --- 9. DYNAMIC PROGRAMMING ---
test_problems.append(("DP: Climbing Stairs (dp_1d_forward)", """
def climbStairs(n):
    if n <= 2:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    dp[2] = 2
    for i in range(3, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]
""", [{"patterns": ["dp_1d_forward"]}], "Classic 1D DP tabulation"))

test_problems.append(("DP: House Robber (multi-group)", """
def rob(nums):
    if not nums:
        return 0
    n = len(nums)
    if n == 1:
        return nums[0]
    dp = [0] * n
    dp[0] = nums[0]
    dp[1] = max(nums[0], nums[1])
    for i in range(2, n):
        dp[i] = max(dp[i - 1], dp[i - 2] + nums[i])
    return dp[n - 1]
""", [{"patterns": ["dp_1d_forward"]}, {"patterns": ["dp_state_machine"]}], "Two accepted groups (OR semantics)"))

test_problems.append(("DP: LIS (dp_1d_sequence)", """
def lengthOfLIS(nums):
    n = len(nums)
    dp = [1] * n
    for i in range(n):
        for j in range(i):
            if nums[i] > nums[j]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)
""", [{"patterns": ["dp_1d_sequence"]}], "1D sequence DP"))

test_problems.append(("DP: Edit Distance (dp_2d_string)", """
def minDistance(word1, word2):
    m, n = len(word1), len(word2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if word1[i - 1] == word2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]) + 1
    return dp[m][n]
""", [{"patterns": ["dp_2d_string"]}], "2D string DP"))

# --- 10. GREEDY ---
test_problems.append(("Greedy: Jump Game (greedy_local)", """
def canJump(nums):
    max_reach = 0
    for i in range(len(nums)):
        if i > max_reach:
            return False
        max_reach = max(max_reach, i + nums[i])
    return True
""", [{"patterns": ["greedy_local"]}], "Greedy max reach"))

# --- 11. BACKTRACKING ---
test_problems.append(("Backtracking: Subsets (backtracking_subset)", """
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
""", [{"patterns": ["backtracking_subset"]}], "Subset backtracking"))

test_problems.append(("Backtracking: Permutations (backtracking_permutation)", """
def permute(nums):
    result = []
    def backtrack(path, used):
        if len(path) == len(nums):
            result.append(path[:])
            return
        for i in range(len(nums)):
            if not used[i]:
                used[i] = True
                path.append(nums[i])
                backtrack(path, used)
                path.pop()
                used[i] = False
    backtrack([], [False] * len(nums))
    return result
""", [{"patterns": ["backtracking_permutation"]}], "Permutation backtracking"))

# --- 12. HEAP ---
test_problems.append(("Heap: Kth Largest (heap_priority_queue)", """
import heapq

def findKthLargest(nums, k):
    heap = []
    for num in nums:
        heapq.heappush(heap, num)
        if len(heap) > k:
            heapq.heappop(heap)
    return heap[0]
""", [{"patterns": ["heap_priority_queue"]}], "Min-heap of size k"))

# --- 13. PREFIX SUM ---
test_problems.append(("Prefix Sum: Range Sum (prefix_sum)", """
class NumArray:
    def __init__(self, nums):
        self.prefix = [0]
        for num in nums:
            self.prefix.append(self.prefix[-1] + num)

    def sumRange(self, left, right):
        return self.prefix[right + 1] - self.prefix[left]
""", [{"patterns": ["prefix_sum"]}], "Prefix sum array"))

# --- 14. HASH MAP ---
test_problems.append(("Hash Map: Contains Duplicate (frequency_counting)", """
def containsDuplicate(nums):
    seen = set()
    for num in nums:
        if num in seen:
            return True
        seen.add(num)
    return False
""", [{"patterns": ["frequency_counting"]}], "Set-based duplicate detection"))

# --- 15. STACK ---
test_problems.append(("Stack: Valid Parentheses", """
def isValid(s):
    stack = []
    pairs = {')': '(', ']': '[', '}': '{'}
    for ch in s:
        if ch in pairs:
            if not stack or stack[-1] != pairs[ch]:
                return False
            stack.pop()
        else:
            stack.append(ch)
    return not stack
""", [{"patterns": ["hash_map_lookup"]}], "Stack-based matching (dict lookup)"))

# --- 16. QUEUE ---
test_problems.append(("Queue: BFS Shortest Path (bfs_shortest_path)", """
from collections import deque

def shortestPathBinaryMatrix(grid):
    n = len(grid)
    if grid[0][0] == 1 or grid[n-1][n-1] == 1:
        return -1
    q = deque([(0, 0, 1)])
    visited = set([(0, 0)])
    dirs = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
    while q:
        r, c, dist = q.popleft()
        if (r, c) == (n-1, n-1):
            return dist
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < n and grid[nr][nc] == 0 and (nr, nc) not in visited:
                visited.add((nr, nc))
                q.append((nr, nc, dist + 1))
    return -1
""", [{"patterns": ["bfs_shortest_path"]}], "BFS with visited set"))


# =============================================================================
# Run all tests
# =============================================================================

if __name__ == "__main__":
    print(f"Pipeline Validation — {len(test_problems)} test cases")
    print(f"Detectors registered: {_ast_engine.get_detector_count()}")
    print(f"Python: {sys.version}")

    for name, code, expected, notes in test_problems:
        run_problem(name, code, expected, notes)

    print_summary()

    # Print errors
    if errors:
        print(f"\n\n{'='*70}")
        print(f"  ERRORS ({len(errors)})")
        print(f"{'='*70}")
        for e in errors:
            print(f"  {FAIL} {e['problem']} @ {e['stage']}: {e['error']}")

    # Summary line
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed_count = sum(1 for r in results if r["status"] == "FAIL")
    print(f"\n{'='*70}")
    icon = PASS if failed_count == 0 else FAIL
    print(f"  RESULT: {icon} {passed}/{total} passed, {failed_count} failed")
    print(f"{'='*70}")
