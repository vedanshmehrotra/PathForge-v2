"""Additional 200+ cases to reach 300+ total."""
from .disjoint_corpus import DisjointCase


def build_more_cases():
    cases = []

    # ================================================================
    # prefix_sum: more positive seeds (various implementations)
    # ================================================================

    for i, (name, code) in enumerate([
        ("ps_running_sum_generic",
         "def running_sum(nums):\n    result = []\n    s = 0\n    for n in nums:\n        s += n\n        result.append(s)\n    return result"),
        ("ps_prefix_sum_manual",
         "def prefix_sums(arr):\n    out = [0] * (len(arr) + 1)\n    for i in range(len(arr)):\n        out[i+1] = out[i] + arr[i]\n    return out"),
        ("ps_cumulative_sum",
         "def cumulative(arr):\n    acc = 0\n    res = []\n    for x in arr:\n        acc += x\n        res.append(acc)\n    return res"),
        ("ps_range_query_build",
         "def build_rqs(arr):\n    prefix = [0]\n    for x in arr:\n        prefix.append(prefix[-1] + x)\n    return prefix"),
        ("ps_subarray_count_k",
         "def count_subarrays(nums, k):\n    prefix = 0\n    seen = {0: 1}\n    count = 0\n    for n in nums:\n        prefix += n\n        if prefix - k in seen:\n            count += seen[prefix - k]\n        seen[prefix] = seen.get(prefix, 0) + 1\n    return count"),
        ("ps_zero_sum_subarrays",
         "def zero_sum_subarrays(nums):\n    prefix = 0\n    seen = {0: [-1]}\n    for i, n in enumerate(nums):\n        prefix += n\n        if prefix in seen:\n            seen[prefix].append(i)\n        else:\n            seen[prefix] = [i]\n    return seen"),
        ("ps_max_subarray_len",
         "def max_len_subarray(nums, k):\n    prefix = 0\n    first_occurrence = {0: 0}\n    max_len = 0\n    for i, n in enumerate(nums):\n        prefix += n\n        target = prefix - k\n        if target in first_occurrence:\n            max_len = max(max_len, i + 1 - first_occurrence[target])\n        if prefix not in first_occurrence:\n            first_occurrence[prefix] = i + 1\n    return max_len"),
        ("ps_running_diff",
         "def running_differences(arr):\n    result = []\n    prev = 0\n    for x in arr:\n        result.append(x - prev)\n        prev = x\n    return result"),
        ("ps_range_sum_queries",
         "class RangeSum:\n    def __init__(self, nums):\n        self.prefix = [0]\n        for n in nums:\n            self.prefix.append(self.prefix[-1] + n)\n    def query(self, l, r):\n        return self.prefix[r+1] - self.prefix[l]"),
        ("ps_suffix_sum",
         "def suffix_sums(arr):\n    n = len(arr)\n    result = [0] * n\n    result[n-1] = arr[n-1]\n    for i in range(n-2, -1, -1):\n        result[i] = arr[i] + result[i+1]\n    return result"),
        ("ps_running_count_even",
         "def count_evens_prefix(arr):\n    result = []\n    count = 0\n    for x in arr:\n        if x % 2 == 0:\n            count += 1\n        result.append(count)\n    return result"),
        ("ps_running_max_subarray",
         "def max_prefix(nums):\n    best = nums[0]\n    running = nums[0]\n    for i in range(1, len(nums)):\n        running += nums[i]\n        best = max(best, running)\n    return best"),
        ("ps_min_prefix",
         "def min_prefix(nums):\n    best = nums[0]\n    running = nums[0]\n    for i in range(1, len(nums)):\n        running += nums[i]\n        best = min(best, running)\n    return best"),
        ("ps_two_prefix_arrays",
         "def combined_prefix(a, b):\n    pa, pb = [0], [0]\n    for x, y in zip(a, b):\n        pa.append(pa[-1] + x)\n        pb.append(pb[-1] + y)\n    return pa, pb"),
        ("ps_running_prod_prefix",
         "def running_prod(arr):\n    result = [1]\n    for x in arr:\n        result.append(result[-1] * x)\n    return result"),
        ("ps_range_update_diff",
         "def apply_updates(n, updates):\n    diff = [0] * (n + 1)\n    for l, r, v in updates:\n        diff[l] += v\n        diff[r+1] -= v\n    result = [0] * n\n    cur = 0\n    for i in range(n):\n        cur += diff[i]\n        result[i] = cur\n    return result"),
    ]):
        cases.append(DisjointCase(
            name=name, code=code, expected_pattern="prefix_sum",
            is_positive=True, family="prefix_generic_accum"))

    # ================================================================
    # hash_map: more positive seeds
    # ================================================================

    for name, code in [
        ("hm_two_sum_brute_to_map",
         "def two_sum(nums, target):\n    lookup = {}\n    for i, n in enumerate(nums):\n        complement = target - n\n        if complement in lookup:\n            return [lookup[complement], i]\n        lookup[n] = i\n    return []"),
        ("hm_longestSubstring_no_repeat",
         "def longest_unique(s):\n    last_seen = {}\n    max_len = 0\n    start = 0\n    for end, ch in enumerate(s):\n        if ch in last_seen and last_seen[ch] >= start:\n            start = last_seen[ch] + 1\n        last_seen[ch] = end\n        max_len = max(max_len, end - start + 1)\n    return max_len"),
        ("hm_max_points_line",
         "from collections import Counter\nfrom math import gcd\nfrom fractions import Fraction\n\ndef max_points(points):\n    if len(points) <= 2:\n        return len(points)\n    best = 0\n    for i in range(len(points)):\n        slopes = Counter()\n        x1, y1 = points[i]\n        for j in range(i+1, len(points)):\n            x2, y2 = points[j]\n            dx, dy = x2 - x1, y2 - y1\n            g = gcd(dx, dy)\n            dx, dy = dx // g, dy // g\n            slopes[(dx, dy)] += 1\n        best = max(best, max(slopes.values(), default=0) + 1)\n    return best"),
        ("hm_subarray_sum_k_v2",
         "def subarray_sum(nums, k):\n    count = 0\n    prefix = 0\n    seen = {0: 1}\n    for num in nums:\n        prefix += num\n        if prefix - k in seen:\n            count += seen[prefix - k]\n        seen[prefix] = seen.get(prefix, 0) + 1\n    return count"),
        ("hm_is_isomorphic",
         "def is_isomorphic(s, t):\n    s_to_t, t_to_s = {}, {}\n    for a, b in zip(s, t):\n        if a in s_to_t:\n            if s_to_t[a] != b: return False\n        else: s_to_t[a] = b\n        if b in t_to_s:\n            if t_to_s[b] != a: return False\n        else: t_to_s[b] = a\n    return True"),
        ("hm_word_break",
         "def word_break(s, word_dict):\n    words = set(word_dict)\n    dp = [False] * (len(s) + 1)\n    dp[0] = True\n    for i in range(1, len(s) + 1):\n        for j in range(i):\n            if dp[j] and s[j:i] in words:\n                dp[i] = True\n                break\n    return dp[len(s)]"),
        ("hm_4sum_count",
         "def four_sum_count(a, b, c, d):\n    ab_sum = {}\n    for x in a:\n        for y in b:\n            s = x + y\n            ab_sum[s] = ab_sum.get(s, 0) + 1\n    count = 0\n    for x in c:\n        for y in d:\n            target = -(x + y)\n            count += ab_sum.get(target, 0)\n    return count"),
        ("hm_group_strings",
         "def group_strings(strings):\n    groups = {}\n    for s in strings:\n        key = tuple((ord(c) - ord(s[0])) % 26 for c in s)\n        if key not in groups:\n            groups[key] = []\n        groups[key].append(s)\n    return list(groups.values())"),
        ("hm_longest_consecutive_seq",
         "def longest_consecutive(nums):\n    num_set = set(nums)\n    best = 0\n    for n in num_set:\n        if n - 1 not in num_set:\n            curr = n\n            streak = 1\n            while curr + 1 in num_set:\n                curr += 1\n                streak += 1\n            best = max(best, streak)\n    return best"),
        ("hm_top_k_freq",
         "def top_k_frequent(nums, k):\n    freq = {}\n    for n in nums:\n        freq[n] = freq.get(n, 0) + 1\n    import heapq\n    return heapq.nlargest(k, freq.keys(), key=lambda x: freq[x])"),
        ("hm_set_intersection",
         "def intersection(nums1, nums2):\n    s1 = set(nums1)\n    return [x for x in set(nums2) if x in s1]"),
        ("hm_char_replacement",
         "def character_replacement(s, k):\n    from collections import Counter\n    freq = Counter()\n    max_len = 0\n    left = 0\n    max_freq = 0\n    for right in range(len(s)):\n        freq[s[right]] += 1\n        max_freq = max(max_freq, freq[s[right]])\n        while (right - left + 1) - max_freq > k:\n            freq[s[left]] -= 1\n            left += 1\n        max_len = max(max_len, right - left + 1)\n    return max_len"),
    ]:
        cases.append(DisjointCase(
            name=name, code=code, expected_pattern="hash_map_lookup",
            is_positive=True, family="hash_genuine"))

    # ================================================================
    # two_pointers_opposite: more positive seeds
    # ================================================================

    for name, code in [
        ("tp_is_palindrome_simple",
         "def is_palindrome(s):\n    cleaned = ''.join(c.lower() for c in s if c.isalnum())\n    l, r = 0, len(cleaned) - 1\n    while l < r:\n        if cleaned[l] != cleaned[r]: return False\n        l += 1\n        r -= 1\n    return True"),
        ("tp_reverse_words_inplace",
         "def reverse_words(s):\n    words = s.split()\n    l, r = 0, len(words) - 1\n    while l < r:\n        words[l], words[r] = words[r], words[l]\n        l += 1\n        r -= 1\n    return ' '.join(words)"),
        ("tp_two_sum_sorted",
         "def two_sum_sorted(numbers, target):\n    l, r = 0, len(numbers) - 1\n    while l < r:\n        total = numbers[l] + numbers[r]\n        if total == target: return [l+1, r+1]\n        elif total < target: l += 1\n        else: r -= 1\n    return []"),
        ("tp_interval_intersection",
         "def interval_intersection(A, B):\n    i, j = 0, 0\n    result = []\n    while i < len(A) and j < len(B):\n        lo = max(A[i][0], B[j][0])\n        hi = min(A[i][1], B[j][1])\n        if lo <= hi:\n            result.append([lo, hi])\n        if A[i][1] < B[j][1]: i += 1\n        else: j += 1\n    return result"),
        ("tp_sorted_squared_array",
         "def sorted_squares(nums):\n    n = len(nums)\n    res = [0] * n\n    l, r = 0, n - 1\n    pos = n - 1\n    while l <= r:\n        if abs(nums[l]) > abs(nums[r]):\n            res[pos] = nums[l] ** 2\n            l += 1\n        else:\n            res[pos] = nums[r] ** 2\n            r -= 1\n        pos -= 1\n    return res"),
        ("tp_reverse_string_chars",
         "def reverse_chars(arr):\n    l, r = 0, len(arr) - 1\n    while l < r:\n        arr[l], arr[r] = arr[r], arr[l]\n        l += 1\n        r -= 1"),
        ("tp_valid_palindrome2",
         "def valid_palindrome(s):\n    def check(l, r):\n        while l < r:\n            if s[l] != s[r]: return False\n            l += 1\n            r -= 1\n        return True\n    l, r = 0, len(s) - 1\n    while l < r:\n        if s[l] != s[r]:\n            return check(l+1, r) or check(l, r-1)\n        l += 1\n        r -= 1\n    return True"),
        ("tp_separate_neg_pos",
         "def separate(nums):\n    l, r = 0, len(nums) - 1\n    while l < r:\n        while l < r and nums[l] < 0: l += 1\n        while l < r and nums[r] >= 0: r -= 1\n        if l < r:\n            nums[l], nums[r] = nums[r], nums[l]\n            l += 1\n            r -= 1\n    return nums"),
        ("tp_reverse_array_range",
         "def reverse_range(arr, start, end):\n    while start < end:\n        arr[start], arr[end] = arr[end], arr[start]\n        start += 1\n        end -= 1"),
        ("tp_move_zeroes_end",
         "def move_zeroes(nums):\n    l = 0\n    for r in range(len(nums)):\n        if nums[r] != 0:\n            nums[l], nums[r] = nums[r], nums[l]\n            l += 1"),
    ]:
        cases.append(DisjointCase(
            name=name, code=code, expected_pattern="two_pointers_opposite",
            is_positive=True, family="tp_genuine"))

    # ================================================================
    # array_traversal: more positive seeds
    # ================================================================

    for name, code in [
        ("at_linear_search",
         "def linear_search(arr, target):\n    for i in range(len(arr)):\n        if arr[i] == target:\n            return i\n    return -1"),
        ("at_find_second_largest",
         "def second_largest(arr):\n    first = second = float('-inf')\n    for x in arr:\n        if x > first:\n            second = first\n            first = x\n        elif x > second and x != first:\n            second = x\n    return second"),
        ("at_sum_array",
         "def array_sum(arr):\n    total = 0\n    for i in range(len(arr)):\n        total += arr[i]\n    return total"),
        ("at_count_occurrences",
         "def count_occurrences(arr, target):\n    count = 0\n    for i in range(len(arr)):\n        if arr[i] == target:\n            count += 1\n    return count"),
        ("at_reverse_array",
         "def reverse_arr(arr):\n    n = len(arr)\n    for i in range(n // 2):\n        arr[i], arr[n-1-i] = arr[n-1-i], arr[i]\n    return arr"),
        ("at_remove_duplicates_sorted",
         "def remove_dup(nums):\n    if not nums: return 0\n    write = 1\n    for read in range(1, len(nums)):\n        if nums[read] != nums[write-1]:\n            nums[write] = nums[read]\n            write += 1\n    return write"),
        ("at_prefix_sum_build",
         "def build_prefix(arr):\n    prefix = [0]\n    for x in arr:\n        prefix.append(prefix[-1] + x)\n    return prefix"),
        ("at_find_min",
         "def find_min(arr):\n    minimum = arr[0]\n    for i in range(1, len(arr)):\n        if arr[i] < minimum:\n            minimum = arr[i]\n    return minimum"),
        ("at_rotate_k",
         "def rotate(arr, k):\n    n = len(arr)\n    k = k % n\n    result = [0] * n\n    for i in range(n):\n        result[(i + k) % n] = arr[i]\n    return result"),
        ("at_max_subarray_brute",
         "def max_subarray_brute(arr):\n    best = arr[0]\n    for i in range(len(arr)):\n        s = 0\n        for j in range(i, len(arr)):\n            s += arr[j]\n            best = max(best, s)\n    return best"),
    ]:
        cases.append(DisjointCase(
            name=name, code=code, expected_pattern="array_traversal",
            is_positive=True, family="at_genuine"))

    # ================================================================
    # More NEGATIVE cases
    # ================================================================

    for name, code, pattern, family, notes in [
        # hash_map vs BFS/DFS negatives
        ("bfs_all_nodes_level", "from collections import deque\ndef all_levels(root):\n    if not root: return []\n    result = []\n    queue = deque([root])\n    while queue:\n        level = []\n        for _ in range(len(queue)):\n            node = queue.popleft()\n            level.append(node.val)\n            if node.left: queue.append(node.left)\n            if node.right: queue.append(node.right)\n        result.append(level)\n    return result", "hash_map_lookup", "hash_vs_bfs", ""),
        ("dfs_inorder", "def inorder(root):\n    result = []\n    def traverse(node):\n        if not node: return\n        traverse(node.left)\n        result.append(node.val)\n        traverse(node.right)\n    traverse(root)\n    return result", "hash_map_lookup", "hash_vs_bfs", ""),
        ("bfs_graph_connected", "from collections import deque\ndef is_connected(graph):\n    visited = set()\n    queue = deque([0])\n    visited.add(0)\n    while queue:\n        node = queue.popleft()\n        for neighbor in graph[node]:\n            if neighbor not in visited:\n                visited.add(neighbor)\n                queue.append(neighbor)\n    return len(visited) == len(graph)", "hash_map_lookup", "hash_vs_bfs", "Set is visited tracking"),

        # array_traversal vs sorting negatives
        ("sort_shell", "def shell_sort(arr):\n    n = len(arr)\n    gap = n // 2\n    while gap > 0:\n        for i in range(gap, n):\n            temp = arr[i]\n            j = i\n            while j >= gap and arr[j-gap] > temp:\n                arr[j] = arr[j-gap]\n                j -= gap\n            arr[j] = temp\n        gap //= 2\n    return arr", "array_traversal", "at_vs_sort", ""),
        ("sort_tim", "def tim_sort(arr):\n    return sorted(arr)", "array_traversal", "at_vs_sort", ""),
        ("sort_odd_even", "def sort_by_parity(arr):\n    lo, hi = 0, len(arr) - 1\n    while lo < hi:\n        if arr[lo] % 2 > arr[hi] % 2:\n            arr[lo], arr[hi] = arr[hi], arr[lo]\n        if arr[lo] % 2 == 0: lo += 1\n        if arr[hi] % 2 == 1: hi -= 1\n    return arr", "array_traversal", "at_vs_sort", ""),

        # array_traversal vs DP negatives
        ("dp_ugly_number", "def nth_ugly(n):\n    ugly = [1]\n    i2 = i3 = i5 = 0\n    while len(ugly) < n:\n        next2 = ugly[i2] * 2\n        next3 = ugly[i3] * 3\n        next5 = ugly[i5] * 5\n        nxt = min(next2, next3, next5)\n        ugly.append(nxt)\n        if nxt == next2: i2 += 1\n        if nxt == next3: i3 += 1\n        if nxt == next5: i5 += 1\n    return ugly[-1]", "array_traversal", "at_vs_dp", ""),
        ("dp_unique_paths", "def unique_paths(m, n):\n    dp = [[1]*n for _ in range(m)]\n    for i in range(1, m):\n        for j in range(1, n):\n            dp[i][j] = dp[i-1][j] + dp[i][j-1]\n    return dp[m-1][n-1]", "array_traversal", "at_vs_dp", ""),

        # prefix_sum vs generic accumulation negatives
        ("count_vowels", "def count_vowels(s):\n    vowels = set('aeiou')\n    return sum(1 for c in s.lower() if c in vowels)", "prefix_sum", "ps_vs_generic", ""),
        ("factorial_loop", "def factorial(n):\n    result = 1\n    for i in range(2, n+1):\n        result *= i\n    return result", "prefix_sum", "ps_vs_generic", ""),
        ("string_join_words", "def join_words(words):\n    result = ''\n    for w in words:\n        result += w + ' '\n    return result.strip()", "prefix_sum", "ps_vs_generic", ""),
        ("count_negative", "def count_negatives(grid):\n    count = 0\n    for row in grid:\n        for val in row:\n            if val < 0:\n                count += 1\n    return count", "prefix_sum", "ps_vs_generic", ""),
        ("matrix_multiply", "def mat_mult(A, B):\n    n = len(A)\n    C = [[0]*n for _ in range(n)]\n    for i in range(n):\n        for j in range(n):\n            for k in range(n):\n                C[i][j] += A[i][k] * B[k][j]\n    return C", "prefix_sum", "ps_vs_generic", ""),
        ("stack_min_stack", "class MinStack:\n    def __init__(self):\n        self.stack = []\n        self.min_stack = []\n    def push(self, val):\n        self.stack.append(val)\n        if not self.min_stack or val <= self.min_stack[-1]:\n            self.min_stack.append(val)\n    def pop(self):\n        val = self.stack.pop()\n        if val == self.min_stack[-1]:\n            self.min_stack.pop()\n        return val\n    def get_min(self):\n        return self.min_stack[-1]", "prefix_sum", "ps_vs_generic", ""),

        # two_pointers vs sliding_window negatives
        ("sw_longest_repeating", "def longest_repeating(s, k):\n    from collections import Counter\n    freq = Counter()\n    max_len = 0\n    left = 0\n    max_count = 0\n    for right in range(len(s)):\n        freq[s[right]] += 1\n        max_count = max(max_count, freq[s[right]])\n        while (right - left + 1) - max_count > k:\n            freq[s[left]] -= 1\n            left += 1\n        max_len = max(max_len, right - left + 1)\n    return max_len", "two_pointers_opposite", "tp_vs_sw", "Sliding window — same direction"),
        ("sw_longest_ones", "def longest_ones(nums, k):\n    left = 0\n    zeros = 0\n    max_len = 0\n    for right in range(len(nums)):\n        if nums[right] == 0:\n            zeros += 1\n        while zeros > k:\n            if nums[left] == 0:\n                zeros -= 1\n            left += 1\n        max_len = max(max_len, right - left + 1)\n    return max_len", "two_pointers_opposite", "tp_vs_sw", ""),
        ("sw_subarray_sum_k_slide", "def subarray_sum_k(nums, k):\n    left = 0\n    current = 0\n    count = 0\n    for right in range(len(nums)):\n        current += nums[right]\n        while current > k and left <= right:\n            current -= nums[left]\n            left += 1\n        if current == k:\n            count += 1\n    return count", "two_pointers_opposite", "tp_vs_sw", ""),

        # hash_map vs memoization/dp negatives
        ("dp_memo_fib", "def fib_memo(n, memo={}):\n    if n in memo: return memo[n]\n    if n <= 1: return n\n    memo[n] = fib_memo(n-1) + fib_memo(n-2)\n    return memo[n]", "hash_map_lookup", "hm_vs_dp", "Dict is memoization cache"),
        ("dp_memo_climb", "def climb(n, memo={}):\n    if n in memo: return memo[n]\n    if n <= 2: return n\n    memo[n] = climb(n-1) + climb(n-2)\n    return memo[n]", "hash_map_lookup", "hm_vs_dp", ""),
    ]:
        cases.append(DisjointCase(
            name=name, code=code, expected_pattern=pattern,
            is_positive=False, family=family, notes=notes))

    # ================================================================
    # More cross-pattern confusable pairs
    # ================================================================

    for name, code, pattern, family, notes in [
        # hash_map genuine vs false cases
        ("hm_two_sum_class", "class TwoSum:\n    def __init__(self):\n        self.nums = {}\n    def add(self, num):\n        self.nums[num] = self.nums.get(num, 0) + 1\n    def find(self, val):\n        for num in self.nums:\n            complement = val - num\n            if complement in self.nums:\n                if complement != num or self.nums[num] > 1:\n                    return True\n        return False", "hash_map_lookup", "hash_genuine", ""),
        ("hm_lru_cache", "class LRUCache:\n    def __init__(self, capacity):\n        from collections import OrderedDict\n        self.cache = OrderedDict()\n        self.capacity = capacity\n    def get(self, key):\n        if key in self.cache:\n            self.cache.move_to_end(key)\n            return self.cache[key]\n        return -1\n    def put(self, key, value):\n        if key in self.cache:\n            self.cache.move_to_end(key)\n        self.cache[key] = value\n        if len(self.cache) > self.capacity:\n            self.cache.popitem(last=False)", "hash_map_lookup", "hash_genuine", "OrderedDict is the core mechanism"),
        ("hm_encode_decode", "class Codec:\n    def encode(self, strs):\n        mapping = {}\n        result = []\n        for i, s in enumerate(strs):\n            key = f'_{i}_'\n            mapping[key] = s\n            result.append(key)\n        import json\n        return json.dumps(result), mapping\n    def decode(self, s, mapping):\n        import json\n        return [mapping[k] for k in json.loads(s)]", "hash_map_lookup", "hash_genuine", ""),

        # prefix_sum genuine (more variants)
        ("ps_2d_prefix", "def build_2d_prefix(grid):\n    m, n = len(grid), len(grid[0])\n    prefix = [[0]*(n+1) for _ in range(m+1)]\n    for i in range(m):\n        for j in range(n):\n            prefix[i+1][j+1] = grid[i][j] + prefix[i][j+1] + prefix[i+1][j] - prefix[i][j]\n    return prefix", "prefix_sum", "prefix_generic_accum", ""),
        ("ps_running_xor", "def prefix_xor(nums):\n    prefix = [0]\n    for n in nums:\n        prefix.append(prefix[-1] ^ n)\n    return prefix", "prefix_sum", "prefix_generic_accum", ""),
        ("ps_running_bitcount", "def prefix_popcount(nums):\n    prefix = [0]\n    for n in nums:\n        prefix.append(prefix[-1] + bin(n).count('1'))\n    return prefix", "prefix_sum", "prefix_generic_accum", ""),

        # two pointers opposite (more variants)
        ("tp_reverse_sentence", "def reverse_sentence(words):\n    arr = words.split()\n    l, r = 0, len(arr) - 1\n    while l < r:\n        arr[l], arr[r] = arr[r], arr[l]\n        l += 1\n        r -= 1\n    return ' '.join(arr)", "two_pointers_opposite", "tp_genuine", ""),
        ("tp_is_symmetric_tree", "def is_symmetric(root):\n    def check(left, right):\n        if not left and not right: return True\n        if not left or not right: return False\n        return (left.val == right.val and\n                check(left.left, right.right) and\n                check(left.right, right.left))\n    return check(root.left, root.right)", "two_pointers_opposite", "tp_genuine", ""),

        # array_traversal genuine (more variants)
        ("at_matrix_diagonal", "def diagonal_sum(mat):\n    n = len(mat)\n    total = 0\n    for i in range(n):\n        total += mat[i][i]\n        total += mat[i][n-1-i]\n    if n % 2 == 1:\n        total -= mat[n//2][n//2]\n    return total", "array_traversal", "at_genuine", ""),
        ("at_flatten_array", "def flatten(arr):\n    result = []\n    for item in arr:\n        if isinstance(item, list):\n            result.extend(flatten(item))\n        else:\n            result.append(item)\n    return result", "array_traversal", "at_genuine", ""),
    ]:
        cases.append(DisjointCase(
            name=name, code=code, expected_pattern=pattern,
            is_positive=True, family=family, notes=notes))

    # ================================================================
    # Critical confusable boundary cases
    # ================================================================

    for name, code, pattern, family, notes in [
        # prefix_sum that SHOULD be hash_map (the dict is primary)
        ("hm_freq_counter_primary", "def top_k_freq(nums, k):\n    freq = {}\n    for n in nums:\n        freq[n] = freq.get(n, 0) + 1\n    return sorted(freq.keys(), key=lambda x: -freq[x])[:k]", "hash_map_lookup", "hash_genuine", "Dict is the core mechanism"),
        ("hm_group_by_key", "def group_by(items, key_fn):\n    groups = {}\n    for item in items:\n        key = key_fn(item)\n        if key not in groups:\n            groups[key] = []\n        groups[key].append(item)\n    return groups", "hash_map_lookup", "hash_genuine", ""),
        ("hm_count_freq_chars", "def char_freq(s):\n    freq = {}\n    for c in s:\n        freq[c] = freq.get(c, 0) + 1\n    return freq", "hash_map_lookup", "hash_genuine", ""),
        ("hm_deduplicate", "def deduplicate(arr):\n    seen = set()\n    result = []\n    for x in arr:\n        if x not in seen:\n            seen.add(x)\n            result.append(x)\n    return result", "hash_map_lookup", "hash_genuine", "Set is primary lookup strategy"),
        ("hm_char_map_string", "def canConstruct(note, mag):\n    counts = {}\n    for c in mag:\n        counts[c] = counts.get(c, 0) + 1\n    for c in note:\n        if counts.get(c, 0) == 0:\n            return False\n        counts[c] -= 1\n    return True", "hash_map_lookup", "hash_genuine", ""),
        # prefix_sum genuine
        ("ps_running_diff_prefix", "def prefix_diffs(arr):\n    prefix = [0]\n    for x in arr:\n        prefix.append(prefix[-1] + x)\n    diffs = []\n    for i in range(1, len(prefix)):\n        diffs.append(prefix[i] - prefix[i-1])\n    return diffs", "prefix_sum", "prefix_generic_accum", ""),
    ]:
        cases.append(DisjointCase(
            name=name, code=code, expected_pattern=pattern,
            is_positive=True, family=family, notes=notes))

    return cases
