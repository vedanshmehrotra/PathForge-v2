#!/usr/bin/env python3
"""Expanded evaluation: builds ~200 submissions, runs legacy+shadow, computes all metrics.

Usage:
    python experiments/code_analysis_evaluation/runners/expanded_evaluation.py
"""

import csv
import json
import os
import sys
import time
import traceback
from pathlib import Path
from collections import defaultdict
from typing import Optional

# ── Path setup ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ast_detection.run_analysis import ASTAnalysisEngine
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "results_final"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Large solution dataset ──────────────────────────────────────────────
# Each entry: (concept_id, code, is_correct, style_note)

SUBMISSIONS = []

def _add(concept, code, correct=True, style="standard"):
    SUBMISSIONS.append({
        "concept": concept,
        "code": code.strip(),
        "correct": correct,
        "style": style,
    })

# ── hash_map_lookup ────────────────────────────────────────────────────
_add("hash_map_lookup", '''
def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
''', style="classic")

_add("hash_map_lookup", '''
def twoSum(nums, target):
    hashmap = {}
    for idx, val in enumerate(nums):
        diff = target - val
        if diff in hashmap:
            return [hashmap[diff], idx]
        hashmap[val] = idx
''', style="renamed_vars")

_add("hash_map_lookup", '''
def twoSum(nums, target):
    d = {}
    for i in range(len(nums)):
        if target - nums[i] in d:
            return [d[target - nums[i]], i]
        d[nums[i]] = i
    return []
''', style="index_loop")

_add("hash_map_lookup", '''
def isAnagram(s, t):
    if len(s) != len(t):
        return False
    count = {}
    for c in s:
        count[c] = count.get(c, 0) + 1
    for c in t:
        if c not in count:
            return False
        count[c] -= 1
        if count[c] < 0:
            return False
    return True
''', style="frequency_variant")

# ── hash_map_frequency ─────────────────────────────────────────────────
_add("hash_map_frequency", '''
def majorityElement(nums):
    counts = {}
    for num in nums:
        counts[num] = counts.get(num, 0) + 1
    for num, cnt in counts.items():
        if cnt > len(nums) // 2:
            return num
    return -1
''', style="classic")

_add("hash_map_frequency", '''
from collections import Counter
def majorityElement(nums):
    c = Counter(nums)
    for k, v in c.items():
        if v > len(nums) // 2:
            return k
''', style="counter_variant")

_add("hash_map_frequency", '''
def firstUniqueChar(s):
    freq = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    for i, c in enumerate(s):
        if freq[c] == 1:
            return i
    return -1
''', style="two_pass")

_add("hash_map_frequency", '''
def containsDuplicate(nums):
    seen = {}
    for n in nums:
        if n in seen:
            return True
        seen[n] = 1
    return False
''', style="membership")

# ── prefix_sum ─────────────────────────────────────────────────────────
_add("prefix_sum", '''
def subarraySum(nums, k):
    count = 0
    prefix_sum = 0
    seen = {0: 1}
    for num in nums:
        prefix_sum += num
        if prefix_sum - k in seen:
            count += seen[prefix_sum - k]
        seen[prefix_sum] = seen.get(prefix_sum, 0) + 1
    return count
''', style="classic")

_add("prefix_sum", '''
def runningSum(nums):
    result = []
    total = 0
    for n in nums:
        total += n
        result.append(total)
    return result
''', style="simple_accumulator")

# ── sliding_window_fixed ───────────────────────────────────────────────
_add("sliding_window_fixed", '''
def findMaxAverage(nums, k):
    window_sum = sum(nums[:k])
    max_sum = window_sum
    for i in range(k, len(nums)):
        window_sum += nums[i] - nums[i - k]
        max_sum = max(max_sum, window_sum)
    return max_sum / k
''', style="classic")

_add("sliding_window_fixed", '''
def findMaxAverage(nums, k):
    curr = sum(nums[:k])
    best = curr
    for i in range(k, len(nums)):
        curr = curr - nums[i-k] + nums[i]
        best = max(best, curr)
    return best / k
''', style="renamed_vars")

_add("sliding_window_fixed", '''
def maxSubArrayLen(nums, k):
    curr = 0
    best = 0
    for i in range(len(nums)):
        curr += nums[i]
        if i >= k:
            curr -= nums[i - k]
        if i >= k - 1:
            best = max(best, curr)
    return best
''', style="inline_accumulate")

_add("sliding_window_fixed", '''
def findMaxAverage(nums, k):
    wsum = sum(nums[:k])
    mx = wsum
    for idx in range(k, len(nums)):
        wsum += nums[idx] - nums[idx - k]
        if wsum > mx:
            mx = wsum
    return mx / k
''', style="alt_naming")

# ── sliding_window_variable ────────────────────────────────────────────
_add("sliding_window_variable", '''
def lengthOfLongestSubstring(s):
    seen = set()
    left = 0
    max_len = 0
    for right in range(len(s)):
        while s[right] in seen:
            seen.remove(s[left])
            left += 1
        seen.add(s[right])
        max_len = max(max_len, right - left + 1)
    return max_len
''', style="classic")

_add("sliding_window_variable", '''
def lengthOfLongestSubstring(s):
    char_set = set()
    l = 0
    longest = 0
    for r in range(len(s)):
        while s[r] in char_set:
            char_set.discard(s[l])
            l += 1
        char_set.add(s[r])
        longest = max(longest, r - l + 1)
    return longest
''', style="renamed_vars")

_add("sliding_window_variable", '''
def minWindow(s, t):
    from collections import Counter
    need = Counter(t)
    missing = len(t)
    left = 0
    start, end = 0, float('inf')
    for right, c in enumerate(s):
        if need[c] > 0:
            missing -= 1
        need[c] -= 1
        while missing == 0:
            if right - left < end - start:
                start, end = left, right
            need[s[left]] += 1
            if need[s[left]] > 0:
                missing += 1
            left += 1
    return s[start:end+1] if end < float('inf') else ""
''', style="min_window")

# ── two_pointers_opposite ──────────────────────────────────────────────
_add("two_pointers_opposite", '''
def isPalindrome(s):
    s = ''.join(c.lower() for c in s if c.isalnum())
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True
''', style="classic")

_add("two_pointers_opposite", '''
def twoSum(numbers, target):
    left, right = 0, len(numbers) - 1
    while left < right:
        curr = numbers[left] + numbers[right]
        if curr == target:
            return [left + 1, right + 1]
        elif curr < target:
            left += 1
        else:
            right -= 1
    return []
''', style="sorted_array")

_add("two_pointers_opposite", '''
def maxArea(height):
    left, right = 0, len(height) - 1
    max_water = 0
    while left < right:
        water = min(height[left], height[right]) * (right - left)
        max_water = max(max_water, water)
        if height[left] < height[right]:
            left += 1
        else:
            right -= 1
    return max_water
''', style="container_water")

_add("two_pointers_opposite", '''
def isPalindrome(s):
    s = ''.join(c.lower() for c in s if c.isalnum())
    i, j = 0, len(s) - 1
    while i < j:
        if s[i] != s[j]:
            return False
        i += 1
        j -= 1
    return True
''', style="renamed_vars")

_add("two_pointers_opposite", '''
def isPalindrome(s):
    s = ''.join(c.lower() for c in s if c.isalnum())
    left, right = 0, len(s) - 1
    while not left >= right:
        if s[left] != s[right]:
            return False
        left = left + 1
        right = right - 1
    return True
''', style="while_not_style")

# ── two_pointers_same ──────────────────────────────────────────────────
_add("two_pointers_same", '''
def removeDuplicates(nums):
    if not nums:
        return 0
    slow = 0
    for fast in range(1, len(nums)):
        if nums[fast] != nums[slow]:
            slow += 1
            nums[slow] = nums[fast]
    return slow + 1
''', style="fast_slow")

_add("two_pointers_same", '''
def removeDuplicates(nums):
    if not nums:
        return 0
    write = 0
    for read in range(1, len(nums)):
        if nums[read] != nums[write]:
            write += 1
            nums[write] = nums[read]
    return write + 1
''', style="renamed_vars")

_add("two_pointers_same", '''
def merge(nums1, m, nums2, n):
    p1, p2, write = m - 1, n - 1, m + n - 1
    while p1 >= 0 and p2 >= 0:
        if nums1[p1] > nums2[p2]:
            nums1[write] = nums1[p1]
            p1 -= 1
        else:
            nums1[write] = nums2[p2]
            p2 -= 1
        write -= 1
    while p2 >= 0:
        nums1[write] = nums2[p2]
        p2 -= 1
        write -= 1
''', style="merge_sorted")

# ── binary_search_standard ─────────────────────────────────────────────
_add("binary_search_standard", '''
def search(nums, target):
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
''', style="classic")

_add("binary_search_standard", '''
def searchInsert(nums, target):
    left, right = 0, len(nums)
    while left < right:
        mid = (left + right) // 2
        if nums[mid] < target:
            left = mid + 1
        else:
            right = mid
    return left
''', style="insert_position")

_add("binary_search_standard", '''
def binarySearch(arr, key):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mi = lo + (hi - lo) // 2
        if arr[mi] == key:
            return mi
        elif arr[mi] < key:
            lo = mi + 1
        else:
            hi = mi - 1
    return -1
''', style="overflow_safe")

_add("binary_search_standard", '''
def binarySearch(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) >> 1
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
''', style="bitshift")

# ── binary_search_rotated ──────────────────────────────────────────────
_add("binary_search_rotated", '''
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
''', style="classic")

# ── binary_search_answer ───────────────────────────────────────────────
_add("binary_search_answer", '''
def minEatingSpeed(piles, h):
    left, right = 1, max(piles)
    while left < right:
        mid = (left + right) // 2
        hours = sum((p + mid - 1) // mid for p in piles)
        if hours <= h:
            right = mid
        else:
            left = mid + 1
    return left
''', style="classic")

# ── dfs_recursive ──────────────────────────────────────────────────────
_add("dfs_recursive", '''
def numIslands(grid):
    if not grid:
        return 0
    count = 0
    for i in range(len(grid)):
        for j in range(len(grid[0])):
            if grid[i][j] == '1':
                dfs(grid, i, j)
                count += 1
    return count

def dfs(grid, i, j):
    if i < 0 or i >= len(grid) or j < 0 or j >= len(grid[0]) or grid[i][j] != '1':
        return
    grid[i][j] = '0'
    dfs(grid, i+1, j)
    dfs(grid, i-1, j)
    dfs(grid, i, j+1)
    dfs(grid, i, j-1)
''', style="islands")

_add("dfs_recursive", '''
def maxDepth(root):
    if not root:
        return 0
    left = maxDepth(root.left)
    right = maxDepth(root.right)
    return max(left, right) + 1
''', style="tree_depth")

_add("dfs_recursive", '''
def invertTree(root):
    if not root:
        return None
    root.left, root.right = root.right, root.left
    invertTree(root.left)
    invertTree(root.right)
    return root
''', style="tree_invert")

_add("dfs_recursive", '''
def isSymmetric(root):
    def check(l, r):
        if not l and not r:
            return True
        if not l or not r:
            return False
        return l.val == r.val and check(l.left, r.right) and check(l.right, r.left)
    return check(root.left, root.right)
''', style="tree_symmetric")

_add("dfs_recursive", '''
def pathSum(root, targetSum):
    if not root:
        return 0
    def dfs(node, remaining):
        if not node:
            return 0
        count = 1 if node.val == remaining else 0
        count += dfs(node.left, remaining - node.val)
        count += dfs(node.right, remaining - node.val)
        return count
    return dfs(root, targetSum) + pathSum(root.left, targetSum) + pathSum(root.right, targetSum)
''', style="path_sum")

_add("dfs_recursive", '''
def diameterOfBinaryTree(root):
    best = [0]
    def depth(node):
        if not node:
            return 0
        l = depth(node.left)
        r = depth(node.right)
        best[0] = max(best[0], l + r)
        return max(l, r) + 1
    depth(root)
    return best[0]
''', style="diameter")

# ── dfs_iterative ──────────────────────────────────────────────────────
_add("dfs_iterative", '''
def inorderTraversal(root):
    result = []
    stack = []
    current = root
    while current or stack:
        while current:
            stack.append(current)
            current = current.left
        current = stack.pop()
        result.append(current.val)
        current = current.right
    return result
''', style="classic")

_add("dfs_iterative", '''
def inorderTraversal(root):
    res, stk = [], []
    cur = root
    while cur or stk:
        while cur:
            stk.append(cur)
            cur = cur.left
        cur = stk.pop()
        res.append(cur.val)
        cur = cur.right
    return res
''', style="renamed_vars")

# ── bfs_level_order ────────────────────────────────────────────────────
_add("bfs_level_order", '''
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
''', style="classic")

_add("bfs_level_order", '''
from collections import deque
def levelOrder(root):
    if not root:
        return []
    ans = []
    q = deque([root])
    while q:
        sz = len(q)
        level = []
        for _ in range(sz):
            node = q.popleft()
            level.append(node.val)
            if node.left:
                q.append(node.left)
            if node.right:
                q.append(node.right)
        ans.append(level)
    return ans
''', style="renamed_vars")

# ── bfs_shortest_path ──────────────────────────────────────────────────
_add("bfs_shortest_path", '''
from collections import deque
def orangesRotting(grid):
    queue = deque()
    for i in range(len(grid)):
        for j in range(len(grid[0])):
            if grid[i][j] == 2:
                queue.append((i, j))
    minutes = 0
    while queue:
        for _ in range(len(queue)):
            x, y = queue.popleft()
            for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                nx, ny = x+dx, y+dy
                if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]) and grid[nx][ny] == 1:
                    grid[nx][ny] = 2
                    queue.append((nx, ny))
        if queue:
            minutes += 1
    for row in grid:
        if 1 in row:
            return -1
    return minutes
''', style="rotting_oranges")

# ── topological_sort ───────────────────────────────────────────────────
_add("topological_sort", '''
def findOrder(numCourses, prerequisites):
    from collections import deque
    adj = [[] for _ in range(numCourses)]
    in_degree = [0] * numCourses
    for dest, src in prerequisites:
        adj[src].append(dest)
        in_degree[dest] += 1
    queue = deque([i for i in range(numCourses) if in_degree[i] == 0])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for nei in adj[node]:
            in_degree[nei] -= 1
            if in_degree[nei] == 0:
                queue.append(nei)
    return order if len(order) == numCourses else []
''', style="classic")

# ── union_find ─────────────────────────────────────────────────────────
_add("union_find", '''
def findCircleNum(isConnected):
    n = len(isConnected)
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    for i in range(n):
        for j in range(i+1, n):
            if isConnected[i][j]:
                union(i, j)
    return len(set(find(i) for i in range(n)))
''', style="classic")

_add("union_find", '''
def findCircleNum(isConnected):
    n = len(isConnected)
    p = list(range(n))
    def find(x):
        if p[x] != x:
            p[x] = find(p[x])
        return p[x]
    def union(a, b):
        pa, pb = find(a), find(b)
        if pa != pb:
            p[pa] = pb
    for i in range(n):
        for j in range(i+1, n):
            if isConnected[i][j]:
                union(i, j)
    return len({find(i) for i in range(n)})
''', style="path_compression")

# ── monotonic_stack ────────────────────────────────────────────────────
_add("monotonic_stack", '''
def dailyTemperatures(temperatures):
    n = len(temperatures)
    result = [0] * n
    stack = []
    for i in range(n):
        while stack and temperatures[i] > temperatures[stack[-1]]:
            j = stack.pop()
            result[j] = i - j
        stack.append(i)
    return result
''', style="classic")

_add("monotonic_stack", '''
def dailyTemperatures(temps):
    n = len(temps)
    ans = [0] * n
    stk = []
    for idx in range(n):
        while stk and temps[idx] > temps[stk[-1]]:
            prev = stk.pop()
            ans[prev] = idx - prev
        stk.append(idx)
    return ans
''', style="renamed_vars")

_add("monotonic_stack", '''
def dailyTemperatures(temperatures):
    n = len(temperatures)
    result = [0] * n
    indices = []
    for i in range(n):
        while len(indices) > 0 and temperatures[i] > temperatures[indices[-1]]:
            prev_idx = indices.pop()
            result[prev_idx] = i - prev_idx
        indices.append(i)
    return result
''', style="explicit_length")

# ── backtracking_permutation ───────────────────────────────────────────
_add("backtracking_permutation", '''
def permute(nums):
    result = []
    def backtrack(path):
        if len(path) == len(nums):
            result.append(path[:])
            return
        for num in nums:
            if num in path:
                continue
            path.append(num)
            backtrack(path)
            path.pop()
    backtrack([])
    return result
''', style="classic")

_add("backtracking_permutation", '''
def permute(nums):
    result = []
    n = len(nums)
    def backtrack(path, used):
        if len(path) == n:
            result.append(path[:])
            return
        for i in range(n):
            if used[i]:
                continue
            used[i] = True
            path.append(nums[i])
            backtrack(path, used)
            path.pop()
            used[i] = False
    backtrack([], [False] * n)
    return result
''', style="used_array")

_add("backtracking_permutation", '''
def permute(input_nums):
    output = []
    def explore(current, remaining):
        if not remaining:
            output.append(current[:])
            return
        for i in range(len(remaining)):
            current.append(remaining[i])
            explore(current, remaining[:i] + remaining[i+1:])
            current.pop()
    explore([], input_nums)
    return output
''', style="remaining_list")

# ── backtracking_subset ────────────────────────────────────────────────
_add("backtracking_subset", '''
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
''', style="classic")

_add("backtracking_subset", '''
def subsets(nums):
    result = []
    def bt(idx, cur):
        result.append(cur[:])
        for i in range(idx, len(nums)):
            cur.append(nums[i])
            bt(i + 1, cur)
            cur.pop()
    bt(0, [])
    return result
''', style="renamed_vars")

# ── dp_1d_forward ──────────────────────────────────────────────────────
_add("dp_1d_forward", '''
def climbStairs(n):
    if n <= 2:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    dp[2] = 2
    for i in range(3, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
    return dp[n]
''', style="classic")

_add("dp_1d_forward", '''
def climbStairs(n):
    if n <= 2:
        return n
    prev2 = 1
    prev1 = 2
    for i in range(3, n + 1):
        curr = prev1 + prev2
        prev2 = prev1
        prev1 = curr
    return prev1
''', style="space_optimized")

_add("dp_1d_forward", '''
def climbStairs(n):
    memo = {1: 1, 2: 2}
    for i in range(3, n + 1):
        memo[i] = memo[i-1] + memo[i-2]
    return memo[n]
''', style="dict_memo")

_add("dp_1d_forward", '''
def countBits(n):
    dp = [0] * (n + 1)
    for i in range(1, n + 1):
        dp[i] = dp[i >> 1] + (i & 1)
    return dp
''', style="counting_bits")

_add("dp_1d_forward", '''
def minCostClimbingStairs(cost):
    n = len(cost)
    dp = [0] * (n + 1)
    for i in range(2, n + 1):
        dp[i] = min(dp[i-1] + cost[i-1], dp[i-2] + cost[i-2])
    return dp[n]
''', style="min_cost")

# ── dp_1d_sequence ─────────────────────────────────────────────────────
_add("dp_1d_sequence", '''
def isSubsequence(s, t):
    i = 0
    for c in t:
        if i < len(s) and s[i] == c:
            i += 1
    return i == len(s)
''', style="greedy_two_pointer")

# ── dp_2d_grid ─────────────────────────────────────────────────────────
_add("dp_2d_grid", '''
def uniquePaths(m, n):
    dp = [[1] * n for _ in range(m)]
    for i in range(1, m):
        for j in range(1, n):
            dp[i][j] = dp[i-1][j] + dp[i][j-1]
    return dp[m-1][n-1]
''', style="classic")

# ── dp_knapsack ────────────────────────────────────────────────────────
_add("dp_knapsack", '''
def knapsack(weights, values, capacity):
    n = len(weights)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(capacity + 1):
            dp[i][w] = dp[i-1][w]
            if weights[i-1] <= w:
                dp[i][w] = max(dp[i][w], dp[i-1][w-weights[i-1]] + values[i-1])
    return dp[n][capacity]
''', style="classic")

# ── dp_interval ────────────────────────────────────────────────────────
_add("dp_interval", '''
def minCoins(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for coin in coins:
        for i in range(coin, amount + 1):
            if dp[i - coin] + 1 < dp[i]:
                dp[i] = dp[i - coin] + 1
    return dp[amount] if dp[amount] != float('inf') else -1
''', style="coin_change")

# ── dp_state_machine ───────────────────────────────────────────────────
_add("dp_state_machine", '''
def maxProfit(prices):
    if not prices:
        return 0
    hold = -prices[0]
    sold = 0
    for price in prices[1:]:
        hold = max(hold, -price)
        sold = max(sold, hold + price)
    return sold
''', style="classic")

# ── heap_top_k ─────────────────────────────────────────────────────────
_add("heap_top_k", '''
import heapq
from collections import Counter
def topKFrequent(nums, k):
    count = Counter(nums)
    return [x for x, _ in heapq.nlargest(k, count.items(), key=lambda x: x[1])]
''', style="classic")

# ── greedy_local ───────────────────────────────────────────────────────
_add("greedy_local", '''
def maxProfit(prices):
    min_price = float('inf')
    max_profit = 0
    for price in prices:
        min_price = min(min_price, price)
        max_profit = max(max_profit, price - min_price)
    return max_profit
''', style="classic")

_add("greedy_local", '''
def maxProfit(prices):
    mn = float('inf')
    mx = 0
    for p in prices:
        mn = min(mn, p)
        mx = max(mx, p - mn)
    return mx
''', style="renamed_vars")

# ── greedy_interval ────────────────────────────────────────────────────
_add("greedy_interval", '''
def merge(intervals):
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
''', style="classic")

# ── linked_list_reversal ───────────────────────────────────────────────
_add("linked_list_reversal", '''
def reverseList(head):
    prev = None
    curr = head
    while curr:
        next_temp = curr.next
        curr.next = prev
        prev = curr
        curr = next_temp
    return prev
''', style="classic")

_add("linked_list_reversal", '''
def reverseList(head):
    prev, curr = None, head
    while curr:
        nxt = curr.next
        curr.next = prev
        prev = curr
        curr = nxt
    return prev
''', style="renamed_vars")

# ── fast_slow_pointers ─────────────────────────────────────────────────
_add("fast_slow_pointers", '''
def hasCycle(head):
    if not head or not head.next:
        return False
    slow = head
    fast = head.next
    while slow != fast:
        if not fast or not fast.next:
            return False
        slow = slow.next
        fast = fast.next.next
    return True
''', style="classic")

_add("fast_slow_pointers", '''
def middleNode(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
    return slow
''', style="middle_finder")

# ── binary_search_tree ─────────────────────────────────────────────────
_add("binary_search_tree", '''
def isValidBST(root):
    def validate(node, low, high):
        if not node:
            return True
        if node.val <= low or node.val >= high:
            return False
        return validate(node.left, low, node.val) and validate(node.right, node.val, high)
    return validate(root, float('-inf'), float('inf'))
''', style="classic")

# ── monotonic_deque ────────────────────────────────────────────────────
_add("monotonic_deque", '''
from collections import deque
def maxSlidingWindow(nums, k):
    dq = deque()
    result = []
    for i in range(len(nums)):
        while dq and dq[0] < i - k + 1:
            dq.popleft()
        while dq and nums[dq[-1]] < nums[i]:
            dq.pop()
        dq.append(i)
        if i >= k - 1:
            result.append(nums[dq[0]])
    return result
''', style="classic")

# ── dp_2d_string ───────────────────────────────────────────────────────
_add("dp_2d_string", '''
def longestCommonSubsequence(text1, text2):
    m, n = len(text1), len(text2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i-1] == text2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[m][n]
''', style="classic")

# ── shadow-only concepts ───────────────────────────────────────────────
_add("dp_top_down", '''
def fib(n, memo={}):
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    memo[n] = fib(n-1, memo) + fib(n-2, memo)
    return memo[n]
''', style="classic")

_add("dp_top_down", '''
def climbStairs(n, memo={}):
    if n in memo:
        return memo[n]
    if n <= 2:
        return n
    memo[n] = climbStairs(n-1, memo) + climbStairs(n-2, memo)
    return memo[n]
''', style="climbing_variant")

_add("dp_bottom_up", '''
def coinChange(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for coin in coins:
        for i in range(coin, amount + 1):
            if dp[i - coin] + 1 < dp[i]:
                dp[i] = dp[i - coin] + 1
    return dp[amount] if dp[amount] != float('inf') else -1
''', style="classic")

# ── Incorrect solutions ────────────────────────────────────────────────
_add("", '''
def twoSum(nums, target):
    for i in range(len(nums)):
        for j in range(len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
''', correct=False, style="brute_force_two_sum")

_add("", '''
def binarySearch(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            return mid
        left = mid + 1
    return -1
''', correct=False, style="buggy_bs_missing_else")

_add("", '''
def climbStairs(n):
    if n <= 2:
        return n
    return climbStairs(n-1) + climbStairs(n-2)
''', correct=False, style="tle_recursion")

_add("", '''
def maxSubArray(nums):
    best = nums[0]
    for i in range(len(nums)):
        for j in range(i, len(nums)):
            best = max(best, sum(nums[i:j+1]))
    return best
''', correct=False, style="brute_force_o_n3")


# ── Evaluation engine ──────────────────────────────────────────────────

def run_full():
    ast_engine = ASTAnalysisEngine()
    
    print(f"Dataset: {len(SUBMISSIONS)} submissions")
    
    # Run analysis on each submission
    results = []
    legacy_ok = 0
    shadow_ok = 0
    legacy_errors = 0
    shadow_errors = 0
    
    for i, sub in enumerate(SUBMISSIONS):
        if (i + 1) % 20 == 0:
            print(f"  Progress: {i+1}/{len(SUBMISSIONS)}")
        
        code = sub["code"]
        concept = sub["concept"]
        
        # Legacy analysis
        try:
            t0 = time.perf_counter()
            legacy_result = ast_engine.analyze(code)
            legacy_ms = (time.perf_counter() - t0) * 1000
            legacy_patterns = []
            for p in legacy_result.get("detected_patterns", []):
                pid = p.get("pattern_id", "")
                conf = p.get("confidence", 0.0)
                det = p.get("detected", False)
                if conf > 0.0 or det:
                    legacy_patterns.append({
                        "pattern_id": pid,
                        "confidence": conf,
                        "detected": det,
                        "evidence": p.get("evidence", []),
                    })
            legacy_success = True
            legacy_ok += 1
        except Exception as e:
            legacy_patterns = []
            legacy_success = False
            legacy_errors += 1
        
        # Shadow analysis
        try:
            t0 = time.perf_counter()
            shadow_result = run_shadow_analysis(code)
            shadow_ms = (time.perf_counter() - t0) * 1000
            shadow_success = shadow_result is not None
            shadow_techniques = []
            shadow_strategies = []
            shadow_facts = []
            if shadow_result:
                shadow_techniques = shadow_result.get("technique_evidence", [])
                shadow_strategies = shadow_result.get("strategy_evidence", [])
                shadow_facts = shadow_result.get("structural_facts", [])
                shadow_ok += 1
            else:
                shadow_errors += 1
        except Exception:
            shadow_success = False
            shadow_techniques = []
            shadow_strategies = []
            shadow_facts = []
            shadow_errors += 1
        
        # Extract detected concepts
        legacy_concepts = set()
        for p in legacy_patterns:
            if p["confidence"] > 0.0:
                legacy_concepts.add(p["pattern_id"])
        
        shadow_concepts = set()
        for t in shadow_techniques:
            shadow_concepts.add(t.get("technique_id", ""))
        for s in shadow_strategies:
            shadow_concepts.add(s.get("strategy_id", ""))
        outcome = {}
        if shadow_result:
            outcome = shadow_result.get("match_outcome", {})
        ps = outcome.get("primary_strategy", "")
        if ps:
            shadow_concepts.add(ps)
        
        # Confidence info
        legacy_confs = [(p["pattern_id"], p["confidence"]) for p in legacy_patterns if p["confidence"] > 0.0]
        shadow_confs = []
        for t in shadow_techniques:
            shadow_confs.append((t.get("technique_id", ""), t.get("presence_confidence", 0.0)))
        for s in shadow_strategies:
            shadow_confs.append((s.get("strategy_id", ""), s.get("confidence", 0.0)))
        
        results.append({
            "idx": i,
            "concept": concept,
            "correct": sub["correct"],
            "style": sub["style"],
            "code_len": len(code.split("\n")),
            "legacy_success": legacy_success,
            "legacy_concepts": sorted(legacy_concepts),
            "legacy_confs": legacy_confs,
            "shadow_success": shadow_success,
            "shadow_concepts": sorted(shadow_concepts),
            "shadow_confs": shadow_confs,
            "shadow_fact_count": len(shadow_facts),
            "shadow_technique_count": len(shadow_techniques),
            "shadow_strategy_count": len(shadow_strategies),
        })
    
    # ── Save raw results ──────────────────────────────────────────────
    with open(OUTPUT_DIR / "expanded_raw.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nLegacy success: {legacy_ok}/{len(SUBMISSIONS)} ({legacy_ok/len(SUBMISSIONS)*100:.1f}%)")
    print(f"Shadow success: {shadow_ok}/{len(SUBMISSIONS)} ({shadow_ok/len(SUBMISSIONS)*100:.1f}%)")
    print(f"Legacy errors: {legacy_errors}, Shadow errors: {shadow_errors}")
    
    # ── Compute metrics ───────────────────────────────────────────────
    # Concepts that have submissions
    all_target_concepts = sorted(set(r["concept"] for r in results if r["concept"]))
    
    # ── Shadow-to-legacy concept mapping ─────────────────────────────
    def _shadow_to_legacy(concept):
        mapping = {
            "sliding_window": ["sliding_window_fixed", "sliding_window_variable"],
            "two_pointers_opposite": ["two_pointers_opposite"],
            "binary_search": ["binary_search_standard"],
            "dfs_backtracking": ["backtracking_permutation", "backtracking_subset"],
            "bfs_shortest_path": ["bfs_shortest_path"],
            "union_find": ["union_find"],
            "monotonic_stack_strategy": ["monotonic_stack"],
            "dp_top_down": ["dp_1d_forward"],
            "dp_bottom_up": ["dp_1d_forward", "dp_knapsack"],
            "greedy_local": ["greedy_local"],
            "hash_frequency": ["hash_map_frequency"],
            "hash_lookup": ["hash_map_lookup"],
        }
        return mapping.get(concept, [])
    
    # ── Per-concept metrics for legacy ────────────────────────────────
    def compute_concept_metrics(system_key):
        per_concept = {}
        for concept in all_target_concepts:
            tp = fp = fn = tn = 0
            for r in results:
                target = r["concept"]
                raw_detected = r.get(f"{system_key}_concepts", [])
                # For shadow, apply mapping to normalize concept names
                if system_key == "shadow":
                    detected = concept in raw_detected or any(
                        concept in _shadow_to_legacy(c)
                        for c in raw_detected
                    )
                else:
                    detected = concept in raw_detected
                if target == concept:
                    # This submission targets this concept
                    if detected:
                        tp += 1
                    else:
                        fn += 1
                else:
                    # This submission targets a different concept
                    if detected:
                        fp += 1
                    else:
                        tn += 1
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
            support = tp + fn
            per_concept[concept] = {
                "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
                "support": support,
            }
        return per_concept
    
    legacy_pc = compute_concept_metrics("legacy")
    shadow_pc = compute_concept_metrics("shadow")
    
    # ── Overall metrics ───────────────────────────────────────────────
    def overall_metrics(per_concept):
        total_tp = sum(m["tp"] for m in per_concept.values())
        total_fp = sum(m["fp"] for m in per_concept.values())
        total_fn = sum(m["fn"] for m in per_concept.values())
        total_tn = sum(m["tn"] for m in per_concept.values())
        micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
        micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
        micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) > 0 else 0
        micro_fpr = total_fp / (total_fp + total_tn) if (total_fp + total_tn) > 0 else 0
        micro_fnr = total_fn / (total_fn + total_tp) if (total_fn + total_tp) > 0 else 0
        
        valid = [m for m in per_concept.values() if m["support"] > 0]
        macro_p = sum(m["precision"] for m in valid) / len(valid) if valid else 0
        macro_r = sum(m["recall"] for m in valid) / len(valid) if valid else 0
        macro_f1 = sum(m["f1"] for m in valid) / len(valid) if valid else 0
        
        total_support = sum(m["support"] for m in valid)
        wt_p = sum(m["precision"] * m["support"] for m in valid) / total_support if total_support > 0 else 0
        wt_r = sum(m["recall"] * m["support"] for m in valid) / total_support if total_support > 0 else 0
        wt_f1 = sum(m["f1"] * m["support"] for m in valid) / total_support if total_support > 0 else 0
        
        return {
            "micro": {"precision": round(micro_p, 4), "recall": round(micro_r, 4), "f1": round(micro_f1, 4),
                       "false_positive_rate": round(micro_fpr, 4), "false_negative_rate": round(micro_fnr, 4),
                       "tp": total_tp, "fp": total_fp, "fn": total_fn, "tn": total_tn},
            "macro": {"precision": round(macro_p, 4), "recall": round(macro_r, 4), "f1": round(macro_f1, 4)},
            "weighted": {"precision": round(wt_p, 4), "recall": round(wt_r, 4), "f1": round(wt_f1, 4)},
        }
    
    legacy_overall = overall_metrics(legacy_pc)
    shadow_overall = overall_metrics(shadow_pc)
    
    # ── Confidence analysis ───────────────────────────────────────────
    def confidence_analysis(results, system_key):
        correct_confs = []
        incorrect_confs = []
        for r in results:
            if not r["correct"]:
                continue
            target = r["concept"]
            for cid, conf in r.get(f"{system_key}_confs", []):
                if target and cid:
                    # Normalize concept
                    norm_target = target
                    # Check if detection matches target
                    if cid == target or cid in _shadow_to_legacy(target):
                        correct_confs.append(conf)
                    else:
                        incorrect_confs.append(conf)
        
        bins = [(0.0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.01)]
        dist = {}
        for lo, hi in bins:
            label = f"{lo:.1f}-{hi:.1f}"
            c_in = sum(1 for c in correct_confs if lo <= c < hi)
            i_in = sum(1 for c in incorrect_confs if lo <= c < hi)
            total = c_in + i_in
            dist[label] = {
                "total": total,
                "correct": c_in,
                "incorrect": i_in,
                "accuracy": round(c_in / total, 3) if total > 0 else None,
            }
        
        return {
            "avg_correct": round(sum(correct_confs) / len(correct_confs), 4) if correct_confs else 0,
            "avg_incorrect": round(sum(incorrect_confs) / len(incorrect_confs), 4) if incorrect_confs else 0,
            "num_correct": len(correct_confs),
            "num_incorrect": len(incorrect_confs),
            "distribution": dist,
        }
    
    legacy_cal = confidence_analysis(results, "legacy")
    shadow_cal = confidence_analysis(results, "shadow")
    
    # ── Robustness test ───────────────────────────────────────────────
    robustness_cases = [
        {
            "concept": "two_pointers_opposite",
            "original": 'def isPalindrome(s):\n    s = "".join(c.lower() for c in s if c.isalnum())\n    left, right = 0, len(s) - 1\n    while left < right:\n        if s[left] != s[right]:\n            return False\n        left += 1\n        right -= 1\n    return True',
            "variants": [
                ("rename", 'def isPalindrome(s):\n    s = "".join(c.lower() for c in s if c.isalnum())\n    i, j = 0, len(s) - 1\n    while i < j:\n        if s[i] != s[j]:\n            return False\n        i += 1\n        j -= 1\n    return True'),
                ("while_not", 'def isPalindrome(s):\n    s = "".join(c.lower() for c in s if c.isalnum())\n    left, right = 0, len(s) - 1\n    while not left >= right:\n        if s[left] != s[right]:\n            return False\n        left += 1\n        right -= 1\n    return True'),
                ("increment", 'def isPalindrome(s):\n    s = "".join(c.lower() for c in s if c.isalnum())\n    left, right = 0, len(s) - 1\n    while left < right:\n        if s[left] != s[right]:\n            return False\n        left = left + 1\n        right = right - 1\n    return True'),
            ],
        },
        {
            "concept": "binary_search_standard",
            "original": 'def binarySearch(nums, target):\n    left, right = 0, len(nums) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if nums[mid] == target:\n            return mid\n        elif nums[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1',
            "variants": [
                ("overflow_safe", 'def binarySearch(nums, target):\n    left, right = 0, len(nums) - 1\n    while left <= right:\n        mid = left + (right - left) // 2\n        if nums[mid] == target:\n            return mid\n        elif nums[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1'),
                ("bitshift", 'def binarySearch(nums, target):\n    left, right = 0, len(nums) - 1\n    while left <= right:\n        mid = (left + right) >> 1\n        if nums[mid] == target:\n            return mid\n        elif nums[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1'),
                ("rename", 'def binarySearch(arr, key):\n    lo, hi = 0, len(arr) - 1\n    while lo <= hi:\n        mi = (lo + hi) // 2\n        if arr[mi] == key:\n            return mi\n        elif arr[mi] < key:\n            lo = mi + 1\n        else:\n            hi = mi - 1\n    return -1'),
            ],
        },
        {
            "concept": "sliding_window_fixed",
            "original": 'def findMaxAverage(nums, k):\n    window_sum = sum(nums[:k])\n    max_sum = window_sum\n    for i in range(k, len(nums)):\n        window_sum += nums[i] - nums[i - k]\n        max_sum = max(max_sum, window_sum)\n    return max_sum / k',
            "variants": [
                ("rename", 'def findMaxAverage(arr, w):\n    curr = sum(arr[:w])\n    best = curr\n    for i in range(w, len(arr)):\n        curr += arr[i] - arr[i - w]\n        best = max(best, curr)\n    return best / w'),
                ("helper", 'def window_sum(arr, start, end):\n    return sum(arr[start:end])\n\ndef findMaxAverage(nums, k):\n    curr = window_sum(nums, 0, k)\n    best = curr\n    for i in range(k, len(nums)):\n        curr = curr - nums[i - k] + nums[i]\n        best = max(best, curr)\n    return best / k'),
            ],
        },
        {
            "concept": "monotonic_stack",
            "original": 'def dailyTemperatures(temperatures):\n    n = len(temperatures)\n    result = [0] * n\n    stack = []\n    for i in range(n):\n        while stack and temperatures[i] > temperatures[stack[-1]]:\n            j = stack.pop()\n            result[j] = i - j\n        stack.append(i)\n    return result',
            "variants": [
                ("rename", 'def dailyTemperatures(temps):\n    n = len(temps)\n    ans = [0] * n\n    stk = []\n    for idx in range(n):\n        while stk and temps[idx] > temps[stk[-1]]:\n            prev = stk.pop()\n            ans[prev] = idx - prev\n        stk.append(idx)\n    return ans'),
                ("explicit_len", 'def dailyTemperatures(temperatures):\n    n = len(temperatures)\n    result = [0] * n\n    indices = []\n    for i in range(n):\n        while len(indices) > 0 and temperatures[i] > temperatures[indices[-1]]:\n            prev_idx = indices.pop()\n            result[prev_idx] = i - prev_idx\n        indices.append(i)\n    return result'),
            ],
        },
        {
            "concept": "backtracking_permutation",
            "original": 'def permute(nums):\n    result = []\n    def backtrack(path):\n        if len(path) == len(nums):\n            result.append(path[:])\n            return\n        for num in nums:\n            if num in path:\n                continue\n            path.append(num)\n            backtrack(path)\n            path.pop()\n    backtrack([])\n    return result',
            "variants": [
                ("used_array", 'def permute(nums):\n    result = []\n    n = len(nums)\n    def backtrack(path, used):\n        if len(path) == n:\n            result.append(path[:])\n            return\n        for i in range(n):\n            if used[i]:\n                continue\n            used[i] = True\n            path.append(nums[i])\n            backtrack(path, used)\n            path.pop()\n            used[i] = False\n    backtrack([], [False] * n)\n    return result'),
                ("remaining_list", 'def permute(input_nums):\n    output = []\n    def explore(current, remaining):\n        if not remaining:\n            output.append(current[:])\n            return\n        for i in range(len(remaining)):\n            current.append(remaining[i])\n            explore(current, remaining[:i] + remaining[i+1:])\n            current.pop()\n    explore([], input_nums)\n    return output'),
            ],
        },
        {
            "concept": "dp_1d_forward",
            "original": 'def climbStairs(n):\n    if n <= 2:\n        return n\n    dp = [0] * (n + 1)\n    dp[1] = 1\n    dp[2] = 2\n    for i in range(3, n + 1):\n        dp[i] = dp[i-1] + dp[i-2]\n    return dp[n]',
            "variants": [
                ("space_opt", 'def climbStairs(n):\n    if n <= 2:\n        return n\n    prev2 = 1\n    prev1 = 2\n    for i in range(3, n + 1):\n        curr = prev1 + prev2\n        prev2 = prev1\n        prev1 = curr\n    return prev1'),
                ("dict_memo", 'def climbStairs(n):\n    memo = {1: 1, 2: 2}\n    for i in range(3, n + 1):\n        memo[i] = memo[i-1] + memo[i-2]\n    return memo[n]'),
            ],
        },
    ]
    
    rob_results = []
    for case in robustness_cases:
        concept = case["concept"]
        try:
            orig_legacy = ast_engine.analyze(case["original"])
            orig_legacy_concepts = set()
            for p in orig_legacy.get("detected_patterns", []):
                if p.get("confidence", 0) > 0:
                    orig_legacy_concepts.add(p["pattern_id"])
        except:
            orig_legacy_concepts = set()
        
        orig_shadow = run_shadow_analysis(case["original"])
        orig_shadow_concepts = set()
        if orig_shadow:
            for t in orig_shadow.get("technique_evidence", []):
                orig_shadow_concepts.add(t.get("technique_id", ""))
            for s in orig_shadow.get("strategy_evidence", []):
                orig_shadow_concepts.add(s.get("strategy_id", ""))
        
        for vname, vcode in case["variants"]:
            try:
                v_legacy = ast_engine.analyze(vcode)
                v_legacy_concepts = set()
                for p in v_legacy.get("detected_patterns", []):
                    if p.get("confidence", 0) > 0:
                        v_legacy_concepts.add(p["pattern_id"])
            except:
                v_legacy_concepts = set()
            
            v_shadow = run_shadow_analysis(vcode)
            v_shadow_concepts = set()
            if v_shadow:
                for t in v_shadow.get("technique_evidence", []):
                    v_shadow_concepts.add(t.get("technique_id", ""))
                for s in v_shadow.get("strategy_evidence", []):
                    v_shadow_concepts.add(s.get("strategy_id", ""))
            
            rob_results.append({
                "concept": concept,
                "variant": vname,
                "legacy_stable": orig_legacy_concepts == v_legacy_concepts,
                "legacy_detected_target": concept in v_legacy_concepts,
                "shadow_stable": orig_shadow_concepts == v_shadow_concepts,
                "shadow_detected_target": any(
                    concept in [s] for s in v_shadow_concepts
                ) or concept in v_shadow_concepts,
                "orig_legacy": sorted(orig_legacy_concepts),
                "var_legacy": sorted(v_legacy_concepts),
                "orig_shadow": sorted(orig_shadow_concepts),
                "var_shadow": sorted(v_shadow_concepts),
            })
    
    rob_legacy_stable = sum(1 for r in rob_results if r["legacy_stable"])
    rob_shadow_stable = sum(1 for r in rob_results if r["shadow_stable"])
    rob_legacy_detect = sum(1 for r in rob_results if r["legacy_detected_target"])
    rob_shadow_detect = sum(1 for r in rob_results if r["shadow_detected_target"])
    
    robustness_summary = {
        "total_variants": len(rob_results),
        "legacy_stability_rate": round(rob_legacy_stable / len(rob_results), 4) if rob_results else 0,
        "shadow_stability_rate": round(rob_shadow_stable / len(rob_results), 4) if rob_results else 0,
        "legacy_detection_rate": round(rob_legacy_detect / len(rob_results), 4) if rob_results else 0,
        "shadow_detection_rate": round(rob_shadow_detect / len(rob_results), 4) if rob_results else 0,
        "details": rob_results,
    }
    
    with open(OUTPUT_DIR / "robustness.json", "w") as f:
        json.dump(robustness_summary, f, indent=2, ensure_ascii=False)
    
    # ── Error analysis ────────────────────────────────────────────────
    error_types = defaultdict(lambda: defaultdict(int))
    for r in results:
        target = r["concept"]
        if not target:
            continue
        
        # Legacy errors
        lc = set(r["legacy_concepts"])
        if target not in lc:
            # Check if legacy detected anything at all
            if not lc:
                error_types["legacy"]["MISSING_DETECTION"] += 1
            else:
                # Detected wrong concept
                error_types["legacy"]["FALSE_NEGATIVE_WRONG_CONCEPT"] += 1
        
        for c in lc:
            if c != target:
                error_types["legacy"]["FALSE_POSITIVE"] += 1
        
        # Shadow errors
        sc = set(r["shadow_concepts"])
        shadow_mapped = _shadow_to_legacy(target)
        if target not in sc and not any(m in sc for m in shadow_mapped):
            if r["shadow_success"]:
                if not sc:
                    error_types["shadow"]["MISSING_DETECTION"] += 1
                else:
                    error_types["shadow"]["FALSE_NEGATIVE_WRONG_CONCEPT"] += 1
            else:
                error_types["shadow"]["PARSE_FAILURE"] += 1
        
        for c in sc:
            if c != target and c not in shadow_mapped:
                error_types["shadow"]["FALSE_POSITIVE"] += 1
    
    # ── Per-concept comparison table ──────────────────────────────────
    comparison = []
    for concept in all_target_concepts:
        lm = legacy_pc.get(concept, {})
        sm = shadow_pc.get(concept, {})
        comparison.append({
            "concept": concept,
            "legacy_f1": lm.get("f1"),
            "shadow_f1": sm.get("f1"),
            "legacy_p": lm.get("precision"),
            "legacy_r": lm.get("recall"),
            "shadow_p": sm.get("precision"),
            "shadow_r": sm.get("recall"),
            "support": lm.get("support", 0),
        })
    
    # ── Save all metrics ──────────────────────────────────────────────
    all_metrics = {
        "dataset_size": len(SUBMISSIONS),
        "concepts_evaluated": len(all_target_concepts),
        "concepts_list": all_target_concepts,
        "legacy_overall": legacy_overall,
        "shadow_overall": shadow_overall,
        "legacy_per_concept": legacy_pc,
        "shadow_per_concept": shadow_pc,
        "comparison": comparison,
        "robustness": robustness_summary,
        "error_types": dict(error_types),
        "legacy_confidence": legacy_cal,
        "shadow_confidence": shadow_cal,
        "success_rates": {
            "legacy": round(legacy_ok / len(SUBMISSIONS), 4),
            "shadow": round(shadow_ok / len(SUBMISSIONS), 4),
        },
    }
    
    with open(OUTPUT_DIR / "all_metrics.json", "w") as f:
        json.dump(all_metrics, f, indent=2, ensure_ascii=False)
    
    # ── Print summary ─────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("LEGACY OVERALL")
    print(f"  Micro:   P={legacy_overall['micro']['precision']:.3f} R={legacy_overall['micro']['recall']:.3f} F1={legacy_overall['micro']['f1']:.3f}")
    print(f"  Macro:   P={legacy_overall['macro']['precision']:.3f} R={legacy_overall['macro']['recall']:.3f} F1={legacy_overall['macro']['f1']:.3f}")
    print(f"  Weighted: P={legacy_overall['weighted']['precision']:.3f} R={legacy_overall['weighted']['recall']:.3f} F1={legacy_overall['weighted']['f1']:.3f}")
    print(f"  FPR={legacy_overall['micro']['false_positive_rate']:.3f} FNR={legacy_overall['micro']['false_negative_rate']:.3f}")
    
    print("\nSHADOW OVERALL")
    print(f"  Micro:   P={shadow_overall['micro']['precision']:.3f} R={shadow_overall['micro']['recall']:.3f} F1={shadow_overall['micro']['f1']:.3f}")
    print(f"  Macro:   P={shadow_overall['macro']['precision']:.3f} R={shadow_overall['macro']['recall']:.3f} F1={shadow_overall['macro']['f1']:.3f}")
    print(f"  Weighted: P={shadow_overall['weighted']['precision']:.3f} R={shadow_overall['weighted']['recall']:.3f} F1={shadow_overall['weighted']['f1']:.3f}")
    print(f"  FPR={shadow_overall['micro']['false_positive_rate']:.3f} FNR={shadow_overall['micro']['false_negative_rate']:.3f}")
    
    print("\nROBUSTNESS")
    print(f"  Legacy stability: {rob_legacy_stable}/{len(rob_results)} ({robustness_summary['legacy_stability_rate']*100:.1f}%)")
    print(f"  Shadow stability: {rob_shadow_stable}/{len(rob_results)} ({robustness_summary['shadow_stability_rate']*100:.1f}%)")
    
    print("\nPER-CONCEPT (Legacy):")
    for c in all_target_concepts:
        m = legacy_pc[c]
        print(f"  {c:30s}  P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} (n={m['support']})")
    
    print("\nPER-CONCEPT (Shadow):")
    for c in all_target_concepts:
        m = shadow_pc[c]
        print(f"  {c:30s}  P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} (n={m['support']})")
    
    print("\nCONFIDENCE (Legacy):")
    print(f"  Avg correct: {legacy_cal['avg_correct']:.4f}, Avg incorrect: {legacy_cal['avg_incorrect']:.4f}")
    print(f"  Samples: {legacy_cal['num_correct']} correct, {legacy_cal['num_incorrect']} incorrect")
    
    print("\nCONFIDENCE (Shadow):")
    print(f"  Avg correct: {shadow_cal['avg_correct']:.4f}, Avg incorrect: {shadow_cal['avg_incorrect']:.4f}")
    print(f"  Samples: {shadow_cal['num_correct']} correct, {shadow_cal['num_incorrect']} incorrect")
    
    print("\nERROR TYPES:")
    for sys_name, types in error_types.items():
        print(f"  {sys_name}:")
        for et, cnt in sorted(types.items()):
            print(f"    {et}: {cnt}")
    
    print(f"\nMetrics saved to: {OUTPUT_DIR}")
    return all_metrics


if __name__ == "__main__":
    run_full()
