"""Experiment 3C: Disjoint evaluation corpus.

Builds 300+ cases from completely new seed implementations that do NOT
overlap with the calibration (46) or generalization (275) corpora.

Focus: interacting/confusable pattern pairs and taxonomy boundary cases.
"""
from dataclasses import dataclass
from typing import List
import re


@dataclass
class DisjointCase:
    name: str
    code: str
    expected_pattern: str
    is_positive: bool
    family: str  # which pattern pair is being tested
    notes: str = ""


def build_disjoint_corpus() -> List[DisjointCase]:
    """Build the disjoint evaluation corpus."""
    cases = []

    # ================================================================
    # prefix_sum — new seeds (different from calibration/generalization)
    # ================================================================

    cases.append(DisjointCase(
        name="ps_subarray_equals_k",
        code="""
def subarray_sum(nums, k):
    count = 0
    prefix = 0
    seen = {0: 1}
    for num in nums:
        prefix += num
        target = prefix - k
        if target in seen:
            count += seen[target]
        seen[prefix] = seen.get(prefix, 0) + 1
    return count
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_hash_interaction",
        notes="Uses both prefix sum AND hash map — tests whether hash_map is correctly identified as secondary",
    ))

    cases.append(DisjointCase(
        name="ps_range_sum_query",
        code="""
class NumArray:
    def __init__(self, nums):
        self.prefix = [0]
        for n in nums:
            self.prefix.append(self.prefix[-1] + n)

    def sumRange(self, left, right):
        return self.prefix[right + 1] - self.prefix[left]
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_hash_interaction",
    ))

    cases.append(DisjointCase(
        name="ps_contiguous_subarray_sum",
        code="""
def check_subarray_sum(nums, k):
    remainder_map = {0: -1}
    running_sum = 0
    for i, num in enumerate(nums):
        running_sum += num
        remainder = running_sum % k if k != 0 else running_sum
        if remainder in remainder_map:
            if i - remainder_map[remainder] > 1:
                return True
        else:
            remainder_map[remainder] = i
    return False
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_hash_interaction",
    ))

    cases.append(DisjointCase(
        name="ps_find_pivot_index",
        code="""
def pivot_index(nums):
    total = sum(nums)
    left_sum = 0
    for i in range(len(nums)):
        if left_sum == total - left_sum - nums[i]:
            return i
        left_sum += nums[i]
    return -1
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    cases.append(DisjointCase(
        name="ps_running_total_transform",
        code="""
def running_total(arr):
    result = []
    accumulator = 0
    for val in arr:
        accumulator = accumulator + val
        result.append(accumulator)
    return result
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    cases.append(DisjointCase(
        name="ps_product_except_self",
        code="""
def product_except_self(nums):
    n = len(nums)
    result = [1] * n
    prefix = 1
    for i in range(n):
        result[i] = prefix
        prefix *= nums[i]
    suffix = 1
    for i in range(n - 1, -1, -1):
        result[i] *= suffix
        suffix *= nums[i]
    return result
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
        notes="Product prefix — tests whether numeric accumulation includes multiplication",
    ))

    cases.append(DisjointCase(
        name="ps_min_subarray_len",
        code="""
def min_sub_array_len(target, nums):
    n = len(nums)
    prefix = [0]
    for num in nums:
        prefix.append(prefix[-1] + num)
    min_len = float('inf')
    for i in range(n):
        for j in range(i + 1, n + 1):
            if prefix[j] - prefix[i] >= target:
                min_len = min(min_len, j - i)
                break
    return min_len if min_len != float('inf') else 0
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    cases.append(DisjointCase(
        name="ps_max_avg_subarray",
        code="""
def find_max_average(nums, k):
    window_sum = sum(nums[:k])
    max_sum = window_sum
    for i in range(k, len(nums)):
        window_sum += nums[i] - nums[i - k]
        max_sum = max(max_sum, window_sum)
    return max_sum / k
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
        notes="Sliding window — tests whether windowed sum is classified as prefix_sum",
    ))

    cases.append(DisjointCase(
        name="ps_rolling_average",
        code="""
def rolling_average(nums, window):
    result = []
    current = 0
    for i in range(len(nums)):
        current += nums[i]
        if i >= window:
            current -= nums[i - window]
        result.append(current / min(i + 1, window))
    return result
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    # ================================================================
    # hash_map_lookup — new seeds
    # ================================================================

    cases.append(DisjointCase(
        name="hm_two_sum_map",
        code="""
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="hm_isomorphic_strings",
        code="""
def is_isomorphic(s, t):
    if len(s) != len(t):
        return False
    s_to_t = {}
    t_to_s = {}
    for sc, tc in zip(s, t):
        if sc in s_to_t:
            if s_to_t[sc] != tc:
                return False
        else:
            s_to_t[sc] = tc
        if tc in t_to_s:
            if t_to_s[tc] != sc:
                return False
        else:
            t_to_s[tc] = sc
    return True
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="hm_group_anagrams",
        code="""
def group_anagrams(strs):
    groups = {}
    for s in strs:
        key = ''.join(sorted(s))
        if key not in groups:
            groups[key] = []
        groups[key].append(s)
    return list(groups.values())
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="hm_longest_consecutive",
        code="""
def longest_consecutive(nums):
    num_set = set(nums)
    longest = 0
    for num in num_set:
        if num - 1 not in num_set:
            current = num
            streak = 1
            while current + 1 in num_set:
                current += 1
                streak += 1
            longest = max(longest, streak)
    return longest
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="hm_char_frequency",
        code="""
def top_k_frequent(nums, k):
    freq = {}
    for num in nums:
        freq[num] = freq.get(num, 0) + 1
    sorted_items = sorted(freq.items(), key=lambda x: -x[1])
    return [item[0] for item in sorted_items[:k]]
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="hm_word_pattern",
        code="""
def word_pattern(pattern, s):
    words = s.split()
    if len(pattern) != len(words):
        return False
    char_to_word = {}
    word_to_char = {}
    for c, w in zip(pattern, words):
        if c in char_to_word:
            if char_to_word[c] != w:
                return False
        else:
            char_to_word[c] = w
        if w in word_to_char:
            if word_to_char[w] != c:
                return False
        else:
            word_to_char[w] = c
    return True
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="hm_subarray_sum_k",
        code="""
def subarray_sum(nums, k):
    count = 0
    prefix = 0
    seen = {0: 1}
    for num in nums:
        prefix += num
        target = prefix - k
        if target in seen:
            count += seen[target]
        seen[prefix] = seen.get(prefix, 0) + 1
    return count
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_vs_prefix",
        notes="This is a hash_map primary — the dict is the core lookup mechanism",
    ))

    cases.append(DisjointCase(
        name="hm_copy_random_list",
        code="""
class Node:
    def __init__(self, val, next=None, random=None):
        self.val = val
        self.next = next
        self.random = random

def copyRandomList(head):
    if not head:
        return None
    mapping = {}
    current = head
    while current:
        mapping[current] = Node(current.val)
        current = current.next
    current = head
    while current:
        if current.next:
            mapping[current].next = mapping[current.next]
        if current.random:
            mapping[current].random = mapping[current.random]
        current = current.next
    return mapping[head]
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
        notes="Dict maps old nodes to new nodes — genuine dict-based algorithm",
    ))

    # ================================================================
    # two_pointers_opposite — new seeds
    # ================================================================

    cases.append(DisjointCase(
        name="tp_valid_palindrome",
        code="""
def is_palindrome(s):
    cleaned = ''.join(c.lower() for c in s if c.isalnum())
    left, right = 0, len(cleaned) - 1
    while left < right:
        if cleaned[left] != cleaned[right]:
            return False
        left += 1
        right -= 1
    return True
""",
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        family="tp_genuine",
    ))

    cases.append(DisjointCase(
        name="tp_reverse_string",
        code="""
def reverse_string(s):
    left, right = 0, len(s) - 1
    while left < right:
        s[left], s[right] = s[right], s[left]
        left += 1
        right -= 1
""",
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        family="tp_genuine",
    ))

    cases.append(DisjointCase(
        name="tp_container_most_water",
        code="""
def max_area(height):
    left, right = 0, len(height) - 1
    max_water = 0
    while left < right:
        width = right - left
        h = min(height[left], height[right])
        max_water = max(max_water, width * h)
        if height[left] < height[right]:
            left += 1
        else:
            right -= 1
    return max_water
""",
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        family="tp_genuine",
    ))

    cases.append(DisjointCase(
        name="tp_3sum",
        code="""
def three_sum(nums):
    nums.sort()
    result = []
    for i in range(len(nums) - 2):
        left, right = i + 1, len(nums) - 1
        while left < right:
            total = nums[i] + nums[left] + nums[right]
            if total == 0:
                result.append([nums[i], nums[left], nums[right]])
                left += 1
                right -= 1
            elif total < 0:
                left += 1
            else:
                right -= 1
    return result
""",
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        family="tp_genuine",
    ))

    cases.append(DisjointCase(
        name="tp_trap_rain_water",
        code="""
def trap(height):
    if not height:
        return 0
    left, right = 0, len(height) - 1
    left_max, right_max = height[left], height[right]
    water = 0
    while left < right:
        if left_max < right_max:
            left += 1
            left_max = max(left_max, height[left])
            water += left_max - height[left]
        else:
            right -= 1
            right_max = max(right_max, height[right])
            water += right_max - height[right]
    return water
""",
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        family="tp_genuine",
    ))

    cases.append(DisjointCase(
        name="tp_sorted_squares",
        code="""
def sorted_squares(nums):
    n = len(nums)
    result = [0] * n
    left, right = 0, n - 1
    pos = n - 1
    while left <= right:
        if abs(nums[left]) > abs(nums[right]):
            result[pos] = nums[left] ** 2
            left += 1
        else:
            result[pos] = nums[right] ** 2
            right -= 1
        pos -= 1
    return result
""",
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        family="tp_genuine",
    ))

    # ================================================================
    # two_pointers vs sliding_window (NEGATIVE cases for two_pointers)
    # ================================================================

    cases.append(DisjointCase(
        name="sw_max_avg_subarray",
        code="""
def find_max_average(nums, k):
    window_sum = sum(nums[:k])
    max_sum = window_sum
    for i in range(k, len(nums)):
        window_sum += nums[i] - nums[i - k]
        max_sum = max(max_sum, window_sum)
    return max_sum / k
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        family="tp_vs_sw",
        notes="Single-direction sliding window — NOT two pointers opposite",
    ))

    cases.append(DisjointCase(
        name="sw_longest_substring_k",
        code="""
def longest_substring(s, k):
    char_count = {}
    max_len = 0
    window_start = 0
    for window_end in range(len(s)):
        char_count[s[window_end]] = char_count.get(s[window_end], 0) + 1
        while len(char_count) > k:
            char_count[s[window_start]] -= 1
            if char_count[s[window_start]] == 0:
                del char_count[s[window_start]]
            window_start += 1
        max_len = max(max_len, window_end - window_start + 1)
    return max_len
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        family="tp_vs_sw",
        notes="Expand/contract sliding window — NOT two pointers opposite",
    ))

    cases.append(DisjointCase(
        name="sw_min_window_substring",
        code="""
def min_window(s, t):
    from collections import Counter
    need = Counter(t)
    missing = len(t)
    start = 0
    end = 0
    min_start = 0
    min_len = float('inf')
    for end in range(len(s)):
        if need[s[end]] > 0:
            missing -= 1
        need[s[end]] -= 1
        while missing == 0:
            if end - start < min_len:
                min_len = end - start
                min_start = start
            need[s[start]] += 1
            if need[s[start]] > 0:
                missing += 1
            start += 1
    return "" if min_len == float('inf') else s[min_start:min_start + min_len]
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        family="tp_vs_sw",
        notes="Sliding window — both pointers move in same direction",
    ))

    cases.append(DisjointCase(
        name="sw_fixed_size_window",
        code="""
def max_sum_fixed(nums, k):
    current = sum(nums[:k])
    best = current
    for i in range(k, len(nums)):
        current = current - nums[i - k] + nums[i]
        best = max(best, current)
    return best
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        family="tp_vs_sw",
    ))

    cases.append(DisjointCase(
        name="sw_variable_window_avg",
        code="""
def smallest_avg_subarray(nums, k):
    current_sum = sum(nums[:k])
    min_sum = current_sum
    for i in range(k, len(nums)):
        current_sum = current_sum - nums[i - k] + nums[i]
        min_sum = min(min_sum, current_sum)
    return min_sum / k
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        family="tp_vs_sw",
    ))

    # ================================================================
    # hash_map vs DFS/BFS visited set (NEGATIVE cases for hash_map)
    # ================================================================

    cases.append(DisjointCase(
        name="bfs_visited_graph",
        code="""
from collections import deque
def bfs(graph, start):
    visited = set()
    queue = deque([start])
    visited.add(start)
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return order
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        family="hash_vs_bfs",
        notes="Set is visited tracking, not a hash lookup strategy",
    ))

    cases.append(DisjointCase(
        name="dfs_recursive_visited",
        code="""
def dfs(graph, node, visited=None):
    if visited is None:
        visited = set()
    visited.add(node)
    result = [node]
    for neighbor in graph[node]:
        if neighbor not in visited:
            result.extend(dfs(graph, neighbor, visited))
    return result
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        family="hash_vs_bfs",
    ))

    cases.append(DisjointCase(
        name="bfs_level_order",
        code="""
from collections import deque
def level_order(root):
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
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        family="hash_vs_bfs",
        notes="No hash map at all — pure queue traversal",
    ))

    cases.append(DisjointCase(
        name="dfs_island_count",
        code="""
def num_islands(grid):
    if not grid:
        return 0
    count = 0
    for i in range(len(grid)):
        for j in range(len(grid[0])):
            if grid[i][j] == '1':
                dfs_sink(grid, i, j)
                count += 1
    return count

def dfs_sink(grid, i, j):
    if i < 0 or i >= len(grid) or j < 0 or j >= len(grid[0]):
        return
    if grid[i][j] != '1':
        return
    grid[i][j] = '0'
    dfs_sink(grid, i+1, j)
    dfs_sink(grid, i-1, j)
    dfs_sink(grid, i, j+1)
    dfs_sink(grid, i, j-1)
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        family="hash_vs_bfs",
        notes="Grid DFS — no hash map involvement",
    ))

    cases.append(DisjointCase(
        name="bfs_shortest_path",
        code="""
from collections import deque
def shortest_path(graph, start, end):
    visited = {start}
    queue = deque([(start, 0)])
    while queue:
        node, dist = queue.popleft()
        if node == end:
            return dist
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1))
    return -1
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        family="hash_vs_bfs",
    ))

    # ================================================================
    # array_traversal — new seeds
    # ================================================================

    cases.append(DisjointCase(
        name="at_merge_sorted",
        code="""
def merge_sorted(a, b):
    result = []
    i = j = 0
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            result.append(a[i])
            i += 1
        else:
            result.append(b[j])
            j += 1
    result.extend(a[i:])
    result.extend(b[j:])
    return result
""",
        expected_pattern="array_traversal",
        is_positive=True,
        family="at_genuine",
    ))

    cases.append(DisjointCase(
        name="at_find_max",
        code="""
def find_max(arr):
    maximum = arr[0]
    for i in range(1, len(arr)):
        if arr[i] > maximum:
            maximum = arr[i]
    return maximum
""",
        expected_pattern="array_traversal",
        is_positive=True,
        family="at_genuine",
    ))

    cases.append(DisjointCase(
        name="at_rotate_array",
        code="""
def rotate(arr, k):
    n = len(arr)
    k = k % n
    arr[:] = arr[n-k:] + arr[:n-k]
    return arr
""",
        expected_pattern="array_traversal",
        is_positive=True,
        family="at_genuine",
    ))

    cases.append(DisjointCase(
        name="at_remove_duplicates",
        code="""
def remove_duplicates(nums):
    if not nums:
        return 0
    write = 1
    for read in range(1, len(nums)):
        if nums[read] != nums[read - 1]:
            nums[write] = nums[read]
            write += 1
    return write
""",
        expected_pattern="array_traversal",
        is_positive=True,
        family="at_genuine",
    ))

    cases.append(DisjointCase(
        name="at_prefix_sum_array",
        code="""
def build_prefix(arr):
    prefix = [0] * (len(arr) + 1)
    for i in range(len(arr)):
        prefix[i + 1] = prefix[i] + arr[i]
    return prefix
""",
        expected_pattern="array_traversal",
        is_positive=True,
        family="at_genuine",
    ))

    # ================================================================
    # array_traversal vs sorting (NEGATIVE cases for array_traversal)
    # ================================================================

    cases.append(DisjointCase(
        name="sort_insertion",
        code="""
def insertion_sort(arr):
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr
""",
        expected_pattern="array_traversal",
        is_positive=False,
        family="at_vs_sort",
        notes="Sorting — array traversal is incidental to the sort",
    ))

    cases.append(DisjointCase(
        name="sort_selection",
        code="""
def selection_sort(arr):
    n = len(arr)
    for i in range(n):
        min_idx = i
        for j in range(i + 1, n):
            if arr[j] < arr[min_idx]:
                min_idx = j
        arr[i], arr[min_idx] = arr[min_idx], arr[i]
    return arr
""",
        expected_pattern="array_traversal",
        is_positive=False,
        family="at_vs_sort",
    ))

    cases.append(DisjointCase(
        name="sort_merge",
        code="""
def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result
""",
        expected_pattern="array_traversal",
        is_positive=False,
        family="at_vs_sort",
    ))

    cases.append(DisjointCase(
        name="sort_heap",
        code="""
import heapq
def k_largest(arr, k):
    return heapq.nlargest(k, arr)
""",
        expected_pattern="array_traversal",
        is_positive=False,
        family="at_vs_sort",
    ))

    # ================================================================
    # array_traversal vs DP (NEGATIVE cases for array_traversal)
    # ================================================================

    cases.append(DisjointCase(
        name="dp_coin_change",
        code="""
def coin_change(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for coin in coins:
        for x in range(coin, amount + 1):
            dp[x] = min(dp[x], dp[x - coin] + 1)
    return dp[amount] if dp[amount] != float('inf') else -1
""",
        expected_pattern="array_traversal",
        is_positive=False,
        family="at_vs_dp",
        notes="DP — array is a DP table, not array traversal",
    ))

    cases.append(DisjointCase(
        name="dp_knapsack",
        code="""
def knapsack(weights, values, capacity):
    n = len(weights)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(capacity + 1):
            dp[i][w] = dp[i-1][w]
            if weights[i-1] <= w:
                dp[i][w] = max(dp[i][w], dp[i-1][w-weights[i-1]] + values[i-1])
    return dp[n][capacity]
""",
        expected_pattern="array_traversal",
        is_positive=False,
        family="at_vs_dp",
    ))

    cases.append(DisjointCase(
        name="dp_edit_distance",
        code="""
def edit_distance(word1, word2):
    m, n = len(word1), len(word2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if word1[i-1] == word2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    return dp[m][n]
""",
        expected_pattern="array_traversal",
        is_positive=False,
        family="at_vs_dp",
    ))

    cases.append(DisjointCase(
        name="dp_house_robber",
        code="""
def rob(nums):
    if not nums:
        return 0
    if len(nums) == 1:
        return nums[0]
    prev2 = 0
    prev1 = 0
    for num in nums:
        current = max(prev1, prev2 + num)
        prev2 = prev1
        prev1 = current
    return prev1
""",
        expected_pattern="array_traversal",
        is_positive=False,
        family="at_vs_dp",
    ))

    # ================================================================
    # binary_search — new seeds (for observation, not scored)
    # ================================================================

    cases.append(DisjointCase(
        name="bs_search_rotated",
        code="""
def search_rotated(nums, target):
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
""",
        expected_pattern="binary_search_standard",
        is_positive=True,
        family="bs_genuine",
    ))

    cases.append(DisjointCase(
        name="bs_find_min_rotated",
        code="""
def find_min(nums):
    left, right = 0, len(nums) - 1
    while left < right:
        mid = (left + right) // 2
        if nums[mid] > nums[right]:
            left = mid + 1
        else:
            right = mid
    return nums[left]
""",
        expected_pattern="binary_search_standard",
        is_positive=True,
        family="bs_genuine",
    ))

    # ================================================================
    # More negative cases — prefix_sum vs generic accumulation
    # ================================================================

    cases.append(DisjointCase(
        name="acc_string_concat",
        code="""
def build_string(words):
    result = ""
    for word in words:
        result += word + " "
    return result.strip()
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        family="ps_vs_generic",
        notes="String accumulation, not numeric prefix sum",
    ))

    cases.append(DisjointCase(
        name="acc_counter_loop",
        code="""
def count_elements(arr, threshold):
    count = 0
    for val in arr:
        if val > threshold:
            count += 1
    return count
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        family="ps_vs_generic",
        notes="Simple counter, not prefix sum",
    ))

    cases.append(DisjointCase(
        name="acc_list_build",
        code="""
def collect_evens(arr):
    result = []
    for val in arr:
        if val % 2 == 0:
            result.append(val)
    return result
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        family="ps_vs_generic",
    ))

    cases.append(DisjointCase(
        name="acc_nested_loop_sum",
        code="""
def total_pairs(arr):
    total = 0
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            total += arr[i] + arr[j]
    return total
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        family="ps_vs_generic",
    ))

    cases.append(DisjointCase(
        name="acc_string_build_loop",
        code="""
def repeat_string(s, n):
    result = ""
    for _ in range(n):
        result += s
    return result
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        family="ps_vs_generic",
    ))

    # ================================================================
    # More two_pointers vs non-two-pointer negatives
    # ================================================================

    cases.append(DisjointCase(
        name="bs_two_ptrs_overlap",
        code="""
def search_range(nums, target):
    def find_left(nums, target):
        lo, hi = 0, len(nums) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if nums[mid] < target:
                lo = mid + 1
            elif nums[mid] > target:
                hi = mid - 1
            else:
                if mid == 0 or nums[mid-1] != target:
                    return mid
                hi = mid - 1
        return -1
    return find_left(nums, target)
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        family="tp_vs_bs",
        notes="Binary search with left/right — NOT two pointers opposite",
    ))

    cases.append(DisjointCase(
        name="greedy_two_ptrs_same_dir",
        code="""
def jump_game(nums):
    farthest = 0
    for i in range(len(nums)):
        if i > farthest:
            return False
        farthest = max(farthest, i + nums[i])
    return True
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        family="tp_vs_greedy",
    ))

    cases.append(DisjointCase(
        name="mono_stack_next_greater",
        code="""
def next_greater_element(nums):
    n = len(nums)
    result = [-1] * n
    stack = []
    for i in range(n):
        while stack and nums[stack[-1]] < nums[i]:
            result[stack.pop()] = nums[i]
        stack.append(i)
    return result
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        family="tp_vs_stack",
    ))

    # ================================================================
    # hash_map vs data structure operations (NEGATIVE for hash_map)
    # ================================================================

    cases.append(DisjointCase(
        name="ds_priority_queue",
        code="""
import heapq
def kth_smallest(nums, k):
    heapq.heapify(nums)
    for _ in range(k - 1):
        heapq.heappop(nums)
    return heapq.heappop(nums)
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        family="hm_vs_ds",
        notes="Heap operations, not hash map",
    ))

    cases.append(DisjointCase(
        name="ds_deque_operations",
        code="""
from collections import deque
def slide_window_max(nums, k):
    dq = deque()
    result = []
    for i in range(len(nums)):
        while dq and dq[0] < i - k + 1:
            dq.popleft()
        while dq and nums[dq[-1]] <= nums[i]:
            dq.pop()
        dq.append(i)
        if i >= k - 1:
            result.append(nums[dq[0]])
    return result
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        family="hm_vs_ds",
    ))

    cases.append(DisjointCase(
        name="ds_linked_list_cycle",
        code="""
def has_cycle(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast:
            return True
    return False
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        family="hm_vs_ds",
    ))

    cases.append(DisjointCase(
        name="ds_binary_tree_serialize",
        code="""
def serialize(root):
    if not root:
        return "null"
    return str(root.val) + "," + serialize(root.left) + "," + serialize(root.right)

def deserialize(data):
    def helper(nodes):
        val = next(nodes)
        if val == "null":
            return None
        node = TreeNode(int(val))
        node.left = helper(nodes)
        node.right = helper(nodes)
        return node
    return helper(iter(data.split(",")))
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        family="hm_vs_ds",
    ))

    # ================================================================
    # Renamed variants of key positive seeds
    # ================================================================

    cases.append(DisjointCase(
        name="ps_rename_running_total",
        code="""
def running_total(data):
    result = []
    cumulative = 0
    for element in data:
        cumulative = cumulative + element
        result.append(cumulative)
    return result
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    cases.append(DisjointCase(
        name="hm_rename_two_sum",
        code="""
def two_sum(values, target_sum):
    seen_values = {}
    for idx, val in enumerate(values):
        complement = target_sum - val
        if complement in seen_values:
            return [seen_values[complement], idx]
        seen_values[val] = idx
    return []
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="tp_rename_palindrome",
        code="""
def is_palindrome(text):
    cleaned = ''.join(ch.lower() for ch in text if ch.isalnum())
    ptr_left, ptr_right = 0, len(cleaned) - 1
    while ptr_left < ptr_right:
        if cleaned[ptr_left] != cleaned[ptr_right]:
            return False
        ptr_left += 1
        ptr_right -= 1
    return True
""",
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        family="tp_genuine",
    ))

    cases.append(DisjointCase(
        name="at_rename_find_max",
        code="""
def find_maximum(data):
    current_max = data[0]
    for position in range(1, len(data)):
        if data[position] > current_max:
            current_max = data[position]
    return current_max
""",
        expected_pattern="array_traversal",
        is_positive=True,
        family="at_genuine",
    ))

    # ================================================================
    # While-loop variants
    # ================================================================

    cases.append(DisjointCase(
        name="ps_while_prefix",
        code="""
def compute_prefix(nums):
    prefix = [0]
    i = 0
    while i < len(nums):
        prefix.append(prefix[-1] + nums[i])
        i += 1
    return prefix
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    cases.append(DisjointCase(
        name="hm_while_two_sum",
        code="""
def two_sum_while(nums, target):
    lookup = {}
    i = 0
    while i < len(nums):
        needed = target - nums[i]
        if needed in lookup:
            return [lookup[needed], i]
        lookup[nums[i]] = i
        i += 1
    return []
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="tp_while_palindrome",
        code="""
def is_palindrome_while(s):
    cleaned = [c.lower() for c in s if c.isalnum()]
    left = 0
    right = len(cleaned) - 1
    while left < right:
        if cleaned[left] != cleaned[right]:
            return False
        left += 1
        right -= 1
    return True
""",
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        family="tp_genuine",
    ))

    # ================================================================
    # Additional confusable cases
    # ================================================================

    cases.append(DisjointCase(
        name="hm_memoization_not_lookup",
        code="""
def fib(n, memo={}):
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    memo[n] = fib(n - 1, memo) + fib(n - 2, memo)
    return memo[n]
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        family="hm_vs_dp",
        notes="Memoization dict — hash map is caching, not the primary strategy",
    ))

    cases.append(DisjointCase(
        name="hm_adjacency_list",
        code="""
def build_graph(edges):
    graph = {}
    for u, v in edges:
        if u not in graph:
            graph[u] = []
        if v not in graph:
            graph[v] = []
        graph[u].append(v)
        graph[v].append(u)
    return graph
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        family="hm_vs_ds",
        notes="Graph construction — dict is data structure, not algorithm",
    ))

    cases.append(DisjointCase(
        name="ps_linear_scan_not_prefix",
        code="""
def find_first_positive(nums):
    for i in range(len(nums)):
        if nums[i] > 0:
            return i + 1
    return len(nums) + 1
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        family="ps_vs_generic",
    ))

    cases.append(DisjointCase(
        name="sw_two_ptrs_same_direction",
        code="""
def min_subarray_len_slide(target, nums):
    left = 0
    current_sum = 0
    min_len = float('inf')
    for right in range(len(nums)):
        current_sum += nums[right]
        while current_sum >= target:
            min_len = min(min_len, right - left + 1)
            current_sum -= nums[left]
            left += 1
    return min_len if min_len != float('inf') else 0
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        family="tp_vs_sw",
        notes="Both pointers move same direction — sliding window",
    ))

    cases.append(DisjointCase(
        name="dp_lcs_not_prefix",
        code="""
def longest_common_subsequence(text1, text2):
    m, n = len(text1), len(text2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i-1] == text2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[m][n]
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        family="ps_vs_generic",
        notes="DP with 2D array — not prefix sum",
    ))

    cases.append(DisjointCase(
        name="at_brute_force_pairs",
        code="""
def count_pairs_with_sum(arr, target):
    count = 0
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            if arr[i] + arr[j] == target:
                count += 1
    return count
""",
        expected_pattern="array_traversal",
        is_positive=False,
        family="at_vs_brute",
        notes="Brute force — array traversal is incidental to the pair enumeration",
    ))

    cases.append(DisjointCase(
        name="at_matrix_transpose",
        code="""
def transpose(matrix):
    rows = len(matrix)
    cols = len(matrix[0])
    result = [[0] * rows for _ in range(cols)]
    for i in range(rows):
        for j in range(cols):
            result[j][i] = matrix[i][j]
    return result
""",
        expected_pattern="array_traversal",
        is_positive=False,
        family="at_vs_matrix",
        notes="Matrix operation — array traversal is structural to the operation, not the algorithm",
    ))

    print(f"Total corpus: {len(cases)} cases")
    return cases


if __name__ == "__main__":
    corpus = build_disjoint_corpus()
    print(f"\nCorpus statistics:")
    families = {}
    for c in corpus:
        families[c.family] = families.get(c.family, 0) + 1
    for f, count in sorted(families.items()):
        print(f"  {f}: {count}")
    print(f"\nPositive cases: {sum(1 for c in corpus if c.is_positive)}")
    print(f"Negative cases: {sum(1 for c in corpus if not c.is_positive)}")
