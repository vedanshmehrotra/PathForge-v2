"""Final 40+ cases to reach 300+."""
from .disjoint_corpus import DisjointCase


def build_last_batch():
    cases = []

    # More hash_map genuine
    for name, code in [
        ("hm_array_pair_sum", "def array_pair_sum(nums):\n    freq = {}\n    for n in nums:\n        freq[n] = freq.get(n, 0) + 1\n    result = 0\n    for n in sorted(freq.keys()):\n        while freq[n] >= 2:\n            result += n\n            freq[n] -= 2\n    return result"),
        ("hm_count_consistent", "def count_consistent(allowed, word):\n    allowed_set = set(allowed)\n    for c in word:\n        if c not in allowed_set:\n            return 0\n    return 1"),
        ("hm_uniqueOccurrences", "def unique_occurrences(arr):\n    freq = {}\n    for n in arr:\n        freq[n] = freq.get(n, 0) + 1\n    seen = set()\n    for count in freq.values():\n        if count in seen:\n            return False\n        seen.add(count)\n    return True"),
        ("hm_num_jewels", "def num_jewels(jewels, stones):\n    jset = set(jewels)\n    return sum(1 for c in stones if c in jset)"),
        ("hm_max_freq_char", "def max_freq_char(s):\n    freq = {}\n    for c in s:\n        freq[c] = freq.get(c, 0) + 1\n    return max(freq, key=freq.get)"),
    ]:
        cases.append(DisjointCase(name=name, code=code, expected_pattern="hash_map_lookup",
                                  is_positive=True, family="hash_genuine"))

    # More prefix_sum
    for name, code in [
        ("ps_running_count_true", "def prefix_true_count(bools):\n    result = []\n    count = 0\n    for b in bools:\n        if b: count += 1\n        result.append(count)\n    return result"),
        ("ps_prefix_ones", "def prefix_ones(arr):\n    result = []\n    total = 0\n    for x in arr:\n        if x == 1:\n            total += 1\n        result.append(total)\n    return result"),
        ("ps_sum_range_queries", "class SumQuery:\n    def __init__(self, nums):\n        self.p = [0]\n        for n in nums:\n            self.p.append(self.p[-1] + n)\n    def query(self, l, r):\n        return self.p[r+1] - self.p[l]"),
    ]:
        cases.append(DisjointCase(name=name, code=code, expected_pattern="prefix_sum",
                                  is_positive=True, family="prefix_generic_accum"))

    # More two_pointers
    for name, code in [
        ("tp_reverse_string_simple", "def rev(s):\n    s = list(s)\n    l, r = 0, len(s)-1\n    while l < r:\n        s[l], s[r] = s[r], s[l]\n        l += 1\n        r -= 1\n    return ''.join(s)"),
        ("tp_is_palindrome_simple2", "def pal(s):\n    s = ''.join(c for c in s if c.isalnum()).lower()\n    return s == s[::-1]"),
        ("tp_reverse_array", "def rev_arr(a):\n    l, r = 0, len(a)-1\n    while l < r:\n        a[l], a[r] = a[r], a[l]\n        l += 1\n        r -= 1\n    return a"),
    ]:
        cases.append(DisjointCase(name=name, code=code, expected_pattern="two_pointers_opposite",
                                  is_positive=True, family="tp_genuine"))

    # More array_traversal
    for name, code in [
        ("at_find_max_index", "def argmax(arr):\n    best_idx = 0\n    for i in range(1, len(arr)):\n        if arr[i] > arr[best_idx]:\n            best_idx = i\n    return best_idx"),
        ("at_all_positive", "def all_positive(arr):\n    for x in arr:\n        if x <= 0:\n            return False\n    return True"),
        ("at_any_negative", "def any_negative(arr):\n    for x in arr:\n        if x < 0:\n            return True\n    return False"),
        ("at_apply_function", "def apply_all(arr, fn):\n    return [fn(x) for x in arr]"),
    ]:
        cases.append(DisjointCase(name=name, code=code, expected_pattern="array_traversal",
                                  is_positive=True, family="at_genuine"))

    # More negatives for each pattern
    for name, code, pattern, family, notes in [
        # hash_map negatives
        ("bfs_level_order_bt", "from collections import deque\ndef level_order(root):\n    if not root: return []\n    result = []\n    q = deque([root])\n    while q:\n        level = []\n        for _ in range(len(q)):\n            n = q.popleft()\n            level.append(n.val)\n            if n.left: q.append(n.left)\n            if n.right: q.append(n.right)\n        result.append(level)\n    return result", "hash_map_lookup", "hash_vs_bfs", ""),
        ("dfs_serialize", "def serialize(root):\n    if not root: return 'null'\n    return str(root.val)+','+serialize(root.left)+','+serialize(root.right)", "hash_map_lookup", "hash_vs_bfs", ""),

        # prefix_sum negatives
        ("stack_min_queue", "class MinQueue:\n    def __init__(self):\n        self.q = []\n    def push(self, val):\n        self.q.append(val)\n    def pop(self):\n        return self.q.pop(0)\n    def get_min(self):\n        return min(self.q)", "prefix_sum", "ps_vs_generic", ""),
        ("greedy_assign_cookies", "def find_content_children(g, s):\n    g.sort()\n    s.sort()\n    child = cookie = 0\n    while child < len(g) and cookie < len(s):\n        if s[cookie] >= g[child]:\n            child += 1\n        cookie += 1\n    return child", "prefix_sum", "ps_vs_generic", ""),

        # two_pointers negatives
        ("sliding_max_avg", "def max_avg(nums, k):\n    s = sum(nums[:k])\n    mx = s\n    for i in range(k, len(nums)):\n        s += nums[i] - nums[i-k]\n        mx = max(mx, s)\n    return mx/k", "two_pointers_opposite", "tp_vs_sw", ""),
        ("sw_subarray_k_avg", "def subarray_avg(nums, k):\n    curr = sum(nums[:k])\n    best = curr\n    for i in range(k, len(nums)):\n        curr += nums[i] - nums[i-k]\n        best = max(best, curr)\n    return best/k", "two_pointers_opposite", "tp_vs_sw", ""),

        # array_traversal negatives
        ("dp_decode_ways", "def num_decodings(s):\n    if not s: return 0\n    n = len(s)\n    dp = [0] * (n + 1)\n    dp[0] = 1\n    dp[1] = 1 if s[0] != '0' else 0\n    for i in range(2, n + 1):\n        if s[i-1] != '0':\n            dp[i] += dp[i-1]\n        if 10 <= int(s[i-2:i]) <= 26:\n            dp[i] += dp[i-2]\n    return dp[n]", "array_traversal", "at_vs_dp", ""),
        ("bs_guess_number", "def guess_number(n):\n    lo, hi = 1, n\n    while lo <= hi:\n        mid = lo + (hi - lo) // 2\n        res = guess(mid)\n        if res == 0: return mid\n        elif res == -1: hi = mid - 1\n        else: lo = mid + 1\n    return -1", "array_traversal", "at_vs_bs", ""),

        # hash_map vs dp negatives
        ("dp_fib_memo", "def fib(n, memo={}):\n    if n in memo: return memo[n]\n    if n <= 1: return n\n    memo[n] = fib(n-1) + fib(n-2)\n    return memo[n]", "hash_map_lookup", "hm_vs_dp", ""),
        ("dp_climb_memo", "def climb(n, memo={}):\n    if n in memo: return memo[n]\n    if n <= 2: return n\n    memo[n] = climb(n-1) + climb(n-2)\n    return memo[n]", "hash_map_lookup", "hm_vs_dp", ""),

        # array_traversal vs sorting negatives
        ("sort_insertion_opt", "def insert_sort(a):\n    for i in range(1, len(a)):\n        key = a[i]\n        j = i-1\n        while j >= 0 and a[j] > key:\n            a[j+1] = a[j]\n            j -= 1\n        a[j+1] = key\n    return a", "array_traversal", "at_vs_sort", ""),
    ]:
        cases.append(DisjointCase(name=name, code=code, expected_pattern=pattern,
                                  is_positive=False, family=family, notes=notes))

    # Final 5 cases to hit 300+
    cases.append(DisjointCase(
        name="ps_cumulative_count",
        code="""def cumulative_count(arr, pred):
    result = []
    count = 0
    for x in arr:
        if pred(x):
            count += 1
        result.append(count)
    return result""",
        expected_pattern="prefix_sum",
        is_positive=True,
        family="prefix_generic_accum",
    ))

    cases.append(DisjointCase(
        name="hm_frequency_sort_v2",
        code="""def freq_sort(s):
    freq = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    return ''.join(sorted(s, key=lambda c: -freq[c]))""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        family="hash_genuine",
    ))

    cases.append(DisjointCase(
        name="tp_reverse_sentence_v2",
        code="""def reverse_words(s):
    words = s.split()
    left, right = 0, len(words) - 1
    while left < right:
        words[left], words[right] = words[right], words[left]
        left += 1
        right -= 1
    return ' '.join(words)""",
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        family="tp_genuine",
    ))

    cases.append(DisjointCase(
        name="at_linear_search_v2",
        code="""def linear_search(arr, target):
    for i in range(len(arr)):
        if arr[i] == target:
            return i
    return -1""",
        expected_pattern="array_traversal",
        is_positive=True,
        family="at_genuine",
    ))

    cases.append(DisjointCase(
        name="sw_min_subarray_v2",
        code="""def min_subarray(target, nums):
    left = 0
    total = 0
    min_len = float('inf')
    for right in range(len(nums)):
        total += nums[right]
        while total >= target:
            min_len = min(min_len, right - left + 1)
            total -= nums[left]
            left += 1
    return 0 if min_len == float('inf') else min_len""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        family="tp_vs_sw",
        notes="Sliding window — same direction",
    ))

    return cases
