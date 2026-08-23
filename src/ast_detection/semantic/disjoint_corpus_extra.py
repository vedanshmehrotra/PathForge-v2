"""Additional disjoint corpus cases to reach 300+ total.

These supplement the base 74 cases in disjoint_corpus.py.
"""
from .disjoint_corpus import DisjointCase


def build_additional_cases():
    """Build additional cases for the disjoint corpus."""
    cases = []

    # ================================================================
    # More prefix_sum positives (different implementations)
    # ================================================================

    cases.append(DisjointCase(
        name="ps_running_product",
        code="""
def running_product(nums):
    products = []
    current = 1
    for n in nums:
        current *= n
        products.append(current)
    return products
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    cases.append(DisjointCase(
        name="ps_range_sum_2d",
        code="""
def get_sum(matrix, row1, col1, row2, col2):
    prefix = [[0] * (len(matrix[0]) + 1) for _ in range(len(matrix) + 1)]
    for i in range(len(matrix)):
        for j in range(len(matrix[0])):
            prefix[i+1][j+1] = matrix[i][j] + prefix[i][j+1] + prefix[i+1][j] - prefix[i][j]
    return prefix[row2+1][col2+1] - prefix[row1][col2+1] - prefix[row2+1][col1] + prefix[row1][col1]
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    cases.append(DisjointCase(
        name="ps_running_max",
        code="""
def running_max(nums):
    result = []
    current_max = float('-inf')
    for n in nums:
        current_max = max(current_max, n)
        result.append(current_max)
    return result
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    cases.append(DisjointCase(
        name="ps_prefix_xor",
        code="""
def prefix_xor(nums):
    result = [0]
    for n in nums:
        result.append(result[-1] ^ n)
    return result
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    cases.append(DisjointCase(
        name="ps_running_count",
        code="""
def count_prefix(arr, threshold):
    counts = []
    current = 0
    for val in arr:
        if val > threshold:
            current += 1
        counts.append(current)
    return counts
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    cases.append(DisjointCase(
        name="ps_cumulative_bool",
        code="""
def cumulative_satisfied(arr, pred):
    result = []
    total = 0
    for item in arr:
        total += 1 if pred(item) else 0
        result.append(total)
    return result
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    cases.append(DisjointCase(
        name="ps_running_min",
        code="""
def running_min(nums):
    mins = []
    current = float('inf')
    for n in nums:
        current = min(current, n)
        mins.append(current)
    return mins
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    cases.append(DisjointCase(
        name="ps_subarray_divisible_k",
        code="""
def subarrays_div_by_k(nums, k):
    count = 0
    prefix = 0
    remainder_map = {0: 1}
    for num in nums:
        prefix += num
        rem = prefix % k
        if rem in remainder_map:
            count += remainder_map[rem]
        remainder_map[rem] = remainder_map.get(rem, 0) + 1
    return count
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_hash_interaction",
    ))

    cases.append(DisjointCase(
        name="ps_difference_array",
        code="""
def difference_array(n, operations):
    diff = [0] * (n + 1)
    for start, end, val in operations:
        diff[start] += val
        if end + 1 <= n:
            diff[end + 1] -= val
    result = []
    current = 0
    for i in range(n):
        current += diff[i]
        result.append(current)
    return result
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    cases.append(DisjointCase(
        name="ps_running_balance",
        code="""
def running_balance(transactions):
    balance = 0
    history = []
    for amount in transactions:
        balance += amount
        history.append(balance)
    return history
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    # ================================================================
    # More hash_map_lookup positives
    # ================================================================

    cases.append(DisjointCase(
        name="hm_valid_anagram",
        code="""
def is_anagram(s, t):
    if len(s) != len(t):
        return False
    count = {}
    for ch in s:
        count[ch] = count.get(ch, 0) + 1
    for ch in t:
        if ch not in count:
            return False
        count[ch] -= 1
        if count[ch] < 0:
            return False
    return True
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="hm_ransom_note",
        code="""
def can_construct(ransom_note, magazine):
    freq = {}
    for ch in magazine:
        freq[ch] = freq.get(ch, 0) + 1
    for ch in ransom_note:
        if ch not in freq or freq[ch] == 0:
            return False
        freq[ch] -= 1
    return True
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="hm_intersection_two_arrays",
        code="""
def intersection(nums1, nums2):
    set1 = set(nums1)
    result = set()
    for num in nums2:
        if num in set1:
            result.add(num)
    return list(result)
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="hm_happy_number",
        code="""
def is_happy(n):
    seen = set()
    while n != 1 and n not in seen:
        seen.add(n)
        n = sum(int(d) ** 2 for d in str(n))
    return n == 1
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="hm_jewels_stones",
        code="""
def num_jewels_in_stones(jewels, stones):
    jewel_set = set(jewels)
    count = 0
    for ch in stones:
        if ch in jewel_set:
            count += 1
    return count
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="hm_lexicographic_sort",
        code="""
def frequency_sort(s):
    freq = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    sorted_chars = sorted(freq.keys(), key=lambda x: -freq[x])
    return ''.join(ch * freq[ch] for ch in sorted_chars)
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="hm_contains_nearby_duplicate",
        code="""
def contains_nearby_duplicate(nums, k):
    index_map = {}
    for i, num in enumerate(nums):
        if num in index_map and i - index_map[num] <= k:
            return True
        index_map[num] = i
    return False
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="hm_single_number",
        code="""
def single_number(nums):
    freq = {}
    for num in nums:
        freq[num] = freq.get(num, 0) + 1
    for num, count in freq.items():
        if count == 1:
            return num
    return -1
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="hm_sort Characters_by_freq",
        code="""
def frequency_sort_string(s):
    counts = {}
    for c in s:
        counts[c] = counts.get(c, 0) + 1
    result = []
    for c, count in sorted(counts.items(), key=lambda x: -x[1]):
        result.append(c * count)
    return ''.join(result)
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="hm_two_sum_sorted",
        code="""
def two_sum_sorted(numbers, target):
    seen = {}
    for i, num in enumerate(numbers):
        complement = target - num
        if complement in seen:
            return [seen[complement] + 1, i + 1]
        seen[num] = i
    return []
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    # ================================================================
    # More two_pointers_opposite positives
    # ================================================================

    cases.append(DisjointCase(
        name="tp_merge_sorted_arrays",
        code="""
def merge(a, b):
    result = []
    i, j = 0, 0
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
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        family="tp_genuine",
    ))

    cases.append(DisjointCase(
        name="tp_remove_element",
        code="""
def remove_element(nums, val):
    left = 0
    for right in range(len(nums)):
        if nums[right] != val:
            nums[left] = nums[right]
            left += 1
    return left
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        family="tp_vs_sw",
        notes="Single-direction scan — NOT opposite pointers",
    ))

    cases.append(DisjointCase(
        name="tp_move_zeroes",
        code="""
def move_zeroes(nums):
    left = 0
    for right in range(len(nums)):
        if nums[right] != 0:
            nums[left], nums[right] = nums[right], nums[left]
            left += 1
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        family="tp_vs_sw",
        notes="Single-direction scan with swaps",
    ))

    cases.append(DisjointCase(
        name="tp_reverse_words",
        code="""
def reverse_words(s):
    words = s.split()
    left, right = 0, len(words) - 1
    while left < right:
        words[left], words[right] = words[right], words[left]
        left += 1
        right -= 1
    return ' '.join(words)
""",
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        family="tp_genuine",
    ))

    cases.append(DisjointCase(
        name="tp_reverse_vowels",
        code="""
def reverse_vowels(s):
    chars = list(s)
    vowels = set('aeiouAEIOU')
    left, right = 0, len(chars) - 1
    while left < right:
        while left < right and chars[left] not in vowels:
            left += 1
        while left < right and chars[right] not in vowels:
            right -= 1
        chars[left], chars[right] = chars[right], chars[left]
        left += 1
        right -= 1
    return ''.join(chars)
""",
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        family="tp_genuine",
    ))

    cases.append(DisjointCase(
        name="tp_compress_string",
        code="""
def compress(chars):
    write = 0
    read = 0
    while read < len(chars):
        char = chars[read]
        count = 0
        while read < len(chars) and chars[read] == char:
            read += 1
            count += 1
        chars[write] = char
        write += 1
        if count > 1:
            for digit in str(count):
                chars[write] = digit
                write += 1
    return write
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        family="tp_vs_sw",
        notes="Single-direction read/write — NOT opposite pointers",
    ))

    cases.append(DisjointCase(
        name="tp_separate_positives_negatives",
        code="""
def separate(nums):
    left, right = 0, len(nums) - 1
    while left < right:
        if nums[left] < 0:
            left += 1
        elif nums[right] >= 0:
            right -= 1
        else:
            nums[left], nums[right] = nums[right], nums[left]
            left += 1
            right -= 1
    return nums
""",
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        family="tp_genuine",
    ))

    # ================================================================
    # More negative cases for hash_map (BFS/DFS/visited)
    # ================================================================

    cases.append(DisjointCase(
        name="dfs_all_paths",
        code="""
def all_paths(graph, start, end, path=[]):
    path = path + [start]
    if start == end:
        return [path]
    paths = []
    for node in graph[start]:
        if node not in path:
            new_paths = all_paths(graph, node, end, path)
            paths.extend(new_paths)
    return paths
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        family="hash_vs_bfs",
    ))

    cases.append(DisjointCase(
        name="bfs_word_ladder",
        code="""
from collections import deque
def ladder_length(begin_word, end_word, word_list):
    word_set = set(word_list)
    queue = deque([(begin_word, 1)])
    visited = {begin_word}
    while queue:
        word, length = queue.popleft()
        for i in range(len(word)):
            for c in 'abcdefghijklmnopqrstuvwxyz':
                new_word = word[:i] + c + word[i+1:]
                if new_word == end_word:
                    return length + 1
                if new_word in word_set and new_word not in visited:
                    visited.add(new_word)
                    queue.append((new_word, length + 1))
    return 0
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        family="hash_vs_bfs",
        notes="BFS with set for visited — set is incidental to the BFS strategy",
    ))

    cases.append(DisjointCase(
        name="dfs_clone_graph",
        code="""
def clone_graph(node):
    if not node:
        return None
    clones = {}
    def dfs(n):
        if n in clones:
            return clones[n]
        clone = Node(n.val)
        clones[n] = clone
        for neighbor in n.neighbors:
            clone.neighbors.append(dfs(neighbor))
        return clone
    return dfs(node)
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        family="hash_vs_bfs",
        notes="DFS with memoization — the dict is a cache, not the algorithm",
    ))

    cases.append(DisjointCase(
        name="bfs_bot_right_tree",
        code="""
from collections import deque
def find_bottom_left_value(root):
    queue = deque([root])
    while queue:
        node = queue.popleft()
        if node.right:
            queue.append(node.right)
        if node.left:
            queue.append(node.left)
    return node.val
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        family="hash_vs_bfs",
    ))

    cases.append(DisjointCase(
        name="dfs_max_depth",
        code="""
def max_depth(root):
    if not root:
        return 0
    left_depth = max_depth(root.left)
    right_depth = max_depth(root.right)
    return max(left_depth, right_depth) + 1
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        family="hash_vs_bfs",
    ))

    # ================================================================
    # More negative cases for array_traversal
    # ================================================================

    cases.append(DisjointCase(
        name="sort_quick",
        code="""
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
""",
        expected_pattern="array_traversal",
        is_positive=False,
        family="at_vs_sort",
    ))

    cases.append(DisjointCase(
        name="dp_fibonacci",
        code="""
def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
""",
        expected_pattern="array_traversal",
        is_positive=False,
        family="at_vs_dp",
    ))

    cases.append(DisjointCase(
        name="dp_climb_stairs",
        code="""
def climb_stairs(n):
    if n <= 2:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    dp[2] = 2
    for i in range(3, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
    return dp[n]
""",
        expected_pattern="array_traversal",
        is_positive=False,
        family="at_vs_dp",
    ))

    cases.append(DisjointCase(
        name="dp_triangle",
        code="""
def minimum_total(triangle):
    n = len(triangle)
    dp = triangle[-1][:]
    for i in range(n - 2, -1, -1):
        for j in range(len(triangle[i])):
            dp[j] = triangle[i][j] + min(dp[j], dp[j+1])
    return dp[0]
""",
        expected_pattern="array_traversal",
        is_positive=False,
        family="at_vs_dp",
    ))

    cases.append(DisjointCase(
        name="bs_rotated_search",
        code="""
def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[lo] <= nums[mid]:
            if nums[lo] <= target < nums[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:
            if nums[mid] < target <= nums[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1
""",
        expected_pattern="array_traversal",
        is_positive=False,
        family="at_vs_bs",
    ))

    cases.append(DisjointCase(
        name="greedy_activity_selection",
        code="""
def max_activities(start, finish):
    activities = sorted(zip(start, finish), key=lambda x: x[1])
    count = 1
    last_finish = activities[0][1]
    for i in range(1, len(activities)):
        if activities[i][0] >= last_finish:
            count += 1
            last_finish = activities[i][1]
    return count
""",
        expected_pattern="array_traversal",
        is_positive=False,
        family="at_vs_greedy",
    ))

    cases.append(DisjointCase(
        name="bs_peak_element",
        code="""
def find_peak_element(nums):
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] < nums[mid + 1]:
            lo = mid + 1
        else:
            hi = mid
    return lo
""",
        expected_pattern="array_traversal",
        is_positive=False,
        family="at_vs_bs",
    ))

    # ================================================================
    # More negative cases for prefix_sum
    # ================================================================

    cases.append(DisjointCase(
        name="sort_bubble",
        code="""
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        family="ps_vs_generic",
    ))

    cases.append(DisjointCase(
        name="dp_max_subarray",
        code="""
def max_subarray(nums):
    max_so_far = nums[0]
    current_max = nums[0]
    for i in range(1, len(nums)):
        current_max = max(nums[i], current_max + nums[i])
        max_so_far = max(max_so_far, current_max)
    return max_so_far
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        family="ps_vs_generic",
        notes="Kadane's algorithm — uses accumulation but NOT prefix sum",
    ))

    cases.append(DisjointCase(
        name="bs_first_bad_version",
        code="""
def first_bad_version(n):
    lo, hi = 1, n
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if is_bad_version(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        family="ps_vs_generic",
    ))

    cases.append(DisjointCase(
        name="greedy_lemonade",
        code="""
def lemonade_change(bills):
    five = ten = 0
    for bill in bills:
        if bill == 5:
            five += 1
        elif bill == 10:
            five -= 1
            ten += 1
        else:
            if ten > 0:
                ten -= 1
                five -= 1
            else:
                five -= 3
        if five < 0:
            return False
    return True
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        family="ps_vs_generic",
    ))

    cases.append(DisjointCase(
        name="stack_valid_parens",
        code="""
def is_valid(s):
    stack = []
    mapping = {'(': ')', '{': '}', '[': ']'}
    for char in s:
        if char in mapping:
            stack.append(mapping[char])
        elif not stack or stack.pop() != char:
            return False
    return not stack
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        family="ps_vs_generic",
    ))

    cases.append(DisjointCase(
        name="recursion_fibonacci",
        code="""
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        family="ps_vs_generic",
    ))

    cases.append(DisjointCase(
        name="greedy_jump_game2",
        code="""
def jump(nums):
    jumps = 0
    current_end = 0
    farthest = 0
    for i in range(len(nums) - 1):
        farthest = max(farthest, i + nums[i])
        if i == current_end:
            jumps += 1
            current_end = farthest
    return jumps
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        family="ps_vs_generic",
    ))

    cases.append(DisjointCase(
        name="stack_daily_temperatures",
        code="""
def daily_temperatures(temperatures):
    n = len(temperatures)
    result = [0] * n
    stack = []
    for i in range(n):
        while stack and temperatures[stack[-1]] < temperatures[i]:
            idx = stack.pop()
            result[idx] = i - idx
        stack.append(i)
    return result
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        family="ps_vs_generic",
    ))

    cases.append(DisjointCase(
        name="linked_list_merge",
        code="""
def merge_two_lists(l1, l2):
    dummy = ListNode(0)
    current = dummy
    while l1 and l2:
        if l1.val <= l2.val:
            current.next = l1
            l1 = l1.next
        else:
            current.next = l2
            l2 = l2.next
        current = current.next
    current.next = l1 or l2
    return dummy.next
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        family="ps_vs_generic",
    ))

    # ================================================================
    # More negative cases for two_pointers (sliding window)
    # ================================================================

    cases.append(DisjointCase(
        name="sw_longest_unique",
        code="""
def length_of_longest_substring(s):
    char_index = {}
    max_len = 0
    start = 0
    for end in range(len(s)):
        if s[end] in char_index and char_index[s[end]] >= start:
            start = char_index[s[end]] + 1
        char_index[s[end]] = end
        max_len = max(max_len, end - start + 1)
    return max_len
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        family="tp_vs_sw",
    ))

    cases.append(DisjointCase(
        name="sw_permutation_in_string",
        code="""
def check_inclusion(s1, s2):
    if len(s1) > len(s2):
        return False
    s1_count = [0] * 26
    s2_count = [0] * 26
    for i in range(len(s1)):
        s1_count[ord(s1[i]) - ord('a')] += 1
        s2_count[ord(s2[i]) - ord('a')] += 1
    if s1_count == s2_count:
        return True
    for i in range(len(s1), len(s2)):
        s2_count[ord(s2[i]) - ord('a')] += 1
        s2_count[ord(s2[i - len(s1)]) - ord('a')] -= 1
        if s1_count == s2_count:
            return True
    return False
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        family="tp_vs_sw",
    ))

    cases.append(DisjointCase(
        name="sw_fruits_into_baskets",
        code="""
def total_fruit(fruits):
    from collections import defaultdict
    basket = defaultdict(int)
    left = 0
    max_fruits = 0
    for right in range(len(fruits)):
        basket[fruits[right]] += 1
        while len(basket) > 2:
            basket[fruits[left]] -= 1
            if basket[fruits[left]] == 0:
                del basket[fruits[left]]
            left += 1
        max_fruits = max(max_fruits, right - left + 1)
    return max_fruits
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        family="tp_vs_sw",
    ))

    cases.append(DisjointCase(
        name="sw_subarray_product_k",
        code="""
def num_subarray_product_less_than_k(nums, k):
    if k <= 1:
        return 0
    count = 0
    product = 1
    left = 0
    for right in range(len(nums)):
        product *= nums[right]
        while product >= k:
            product //= nums[left]
            left += 1
        count += right - left + 1
    return count
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        family="tp_vs_sw",
    ))

    # ================================================================
    # Additional renamed variants
    # ================================================================

    cases.append(DisjointCase(
        name="ps_rename_sum_range",
        code="""
class NumArray:
    def __init__(self, input_nums):
        self.prefix_totals = [0]
        for value in input_nums:
            self.prefix_totals.append(self.prefix_totals[-1] + value)

    def range_sum(self, left_idx, right_idx):
        return self.prefix_totals[right_idx + 1] - self.prefix_totals[left_idx]
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    cases.append(DisjointCase(
        name="hm_rename_group_anagrams",
        code="""
def group_anagrams(strings):
    groups = {}
    for s in strings:
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
        name="tp_rename_reverse_string",
        code="""
def reverse_in_place(s):
    start_ptr = 0
    end_ptr = len(s) - 1
    while start_ptr < end_ptr:
        s[start_ptr], s[end_ptr] = s[end_ptr], s[start_ptr]
        start_ptr += 1
        end_ptr -= 1
""",
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        family="tp_genuine",
    ))

    cases.append(DisjointCase(
        name="hm_while_valid_sudoku",
        code="""
def is_valid_sudoku(board):
    rows = [set() for _ in range(9)]
    cols = [set() for _ in range(9)]
    boxes = [set() for _ in range(9)]
    for i in range(9):
        for j in range(9):
            val = board[i][j]
            if val == '.':
                continue
            box_idx = (i // 3) * 3 + j // 3
            if val in rows[i] or val in cols[j] or val in boxes[box_idx]:
                return False
            rows[i].add(val)
            cols[j].add(val)
            boxes[box_idx].add(val)
    return True
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="ps_while_running_avg",
        code="""
def running_average_stream(data, window_size):
    result = []
    window_sum = 0
    idx = 0
    while idx < len(data):
        window_sum += data[idx]
        if idx >= window_size:
            window_sum -= data[idx - window_size]
        result.append(window_sum / min(idx + 1, window_size))
        idx += 1
    return result
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    cases.append(DisjointCase(
        name="tp_while_merge_sorted",
        code="""
def merge_sorted_while(a, b):
    merged = []
    i = 0
    j = 0
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            merged.append(a[i])
            i += 1
        else:
            merged.append(b[j])
            j += 1
    while i < len(a):
        merged.append(a[i])
        i += 1
    while j < len(b):
        merged.append(b[j])
        j += 1
    return merged
""",
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        family="tp_genuine",
    ))

    return cases
