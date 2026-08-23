"""Final batch of cases to reach 300+ total."""
from .disjoint_corpus import DisjointCase


def build_final_cases():
    cases = []

    # More hash_map genuine positives (different algorithms)
    for name, code in [
        ("hm_valid_sudoku_board",
         "def is_valid(board):\n    rows = [set() for _ in range(9)]\n    cols = [set() for _ in range(9)]\n    boxes = [set() for _ in range(9)]\n    for i in range(9):\n        for j in range(9):\n            v = board[i][j]\n            if v == '.': continue\n            b = (i//3)*3 + j//3\n            if v in rows[i] or v in cols[j] or v in boxes[b]:\n                return False\n            rows[i].add(v)\n            cols[j].add(v)\n            boxes[b].add(v)\n    return True"),
        ("hm_flashcard_game",
         "def min_operations(cards):\n    seen = set()\n    ops = 0\n    for c in cards:\n        if c not in seen:\n            ops += 1\n            seen.add(c)\n    return ops"),
        ("hm_memoize_expensive",
         "cache = {}\ndef expensive(n):\n    if n in cache: return cache[n]\n    result = sum(i*i for i in range(n))\n    cache[n] = result\n    return result"),
        ("hm_check_permutation",
         "def check_permutation(s1, s2):\n    if len(s1) != len(s2): return False\n    freq = {}\n    for c in s1:\n        freq[c] = freq.get(c, 0) + 1\n    for c in s2:\n        if c not in freq: return False\n        freq[c] -= 1\n        if freq[c] < 0: return False\n    return True"),
        ("hm_custom_sort_freq",
         "def frequency_sort(s):\n    freq = {}\n    for c in s:\n        freq[c] = freq.get(c, 0) + 1\n    return ''.join(sorted(s, key=lambda x: (-freq[x], x)))"),
        ("hm_stock_price_tracker",
         "class StockPrice:\n    def __init__(self):\n        self.prices = {}\n        self.max_price = 0\n    def update(self, timestamp, price):\n        self.prices[timestamp] = price\n        self.max_price = max(self.max_price, price)\n    def current(self):\n        return max(self.prices.values())"),
        ("hm_find_duplicates",
         "def find_duplicates(nums):\n    freq = {}\n    result = []\n    for n in nums:\n        freq[n] = freq.get(n, 0) + 1\n    for n, count in freq.items():\n        if count > 1:\n            result.append(n)\n    return result"),
        ("hm_roman_to_int",
         "def romanToInt(s):\n    vals = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}\n    total = 0\n    for i in range(len(s)):\n        if i+1 < len(s) and vals[s[i]] < vals[s[i+1]]:\n            total -= vals[s[i]]\n        else:\n            total += vals[s[i]]\n    return total"),
        ("hm_count_distinct",
         "def count_distinct(arr):\n    seen = set()\n    for x in arr:\n        seen.add(x)\n    return len(seen)"),
        ("hm_map_pair_sum",
         "def pair_sum(nums, target):\n    visited = {}\n    for i, n in enumerate(nums):\n        comp = target - n\n        if comp in visited:\n            return (visited[comp], i)\n        visited[n] = i\n    return None"),
    ]:
        cases.append(DisjointCase(name=name, code=code, expected_pattern="hash_map_lookup",
                                  is_positive=True, family="hash_genuine"))

    # More two_pointers opposite positives
    for name, code in [
        ("tp_reverse_linked_list",
         "def reverse_list(head):\n    prev, curr = None, head\n    while curr:\n        nxt = curr.next\n        curr.next = prev\n        prev = curr\n        curr = nxt\n    return prev"),
        ("tp_palindrome_linked_list",
         "def is_palindrome_list(head):\n    vals = []\n    while head:\n        vals.append(head.val)\n        head = head.next\n    l, r = 0, len(vals) - 1\n    while l < r:\n        if vals[l] != vals[r]: return False\n        l += 1\n        r -= 1\n    return True"),
        ("tp_167_two_sum_ii",
         "def two_sum_ii(numbers, target):\n    l, r = 0, len(numbers) - 1\n    while l < r:\n        s = numbers[l] + numbers[r]\n        if s == target: return [l+1, r+1]\n        elif s < target: l += 1\n        else: r -= 1\n    return []"),
        ("tp_reverse_vowels_str",
         "def reverse_vowels(s):\n    s = list(s)\n    vowels = set('aeiouAEIOU')\n    l, r = 0, len(s) - 1\n    while l < r:\n        while l < r and s[l] not in vowels: l += 1\n        while l < r and s[r] not in vowels: r -= 1\n        s[l], s[r] = s[r], s[l]\n        l += 1\n        r -= 1\n    return ''.join(s)"),
        ("tp_merge_intervals",
         "def merge_intervals(intervals):\n    intervals.sort()\n    merged = [intervals[0]]\n    for start, end in intervals[1:]:\n        if start <= merged[-1][1]:\n            merged[-1][1] = max(merged[-1][1], end)\n        else:\n            merged.append([start, end])\n    return merged"),
        ("tp_count_mountains",
         "def count_mountains(arr):\n    count = 0\n    for i in range(1, len(arr)-1):\n        if arr[i] > arr[i-1] and arr[i] > arr[i+1]:\n            count += 1\n    return count"),
        ("tp_check_non_decreasing",
         "def is_non_decreasing(nums):\n    l = 0\n    for r in range(1, len(nums)):\n        if nums[r] < nums[l]:\n            return False\n        l = r\n    return True"),
        ("tp_reverse_between",
         "def reverse_between(head, left, right):\n    if not head or left == right: return head\n    dummy = ListNode(0, head)\n    prev = dummy\n    for _ in range(left - 1):\n        prev = prev.next\n    curr = prev.next\n    for _ in range(right - left):\n        nxt = curr.next\n        curr.next = nxt.next\n        nxt.next = prev.next\n        prev.next = nxt\n    return dummy.next"),
    ]:
        cases.append(DisjointCase(name=name, code=code, expected_pattern="two_pointers_opposite",
                                  is_positive=True, family="tp_genuine"))

    # More prefix_sum positives
    for name, code in [
        ("ps_running_total_simple",
         "def running_total(nums):\n    total = 0\n    result = []\n    for n in nums:\n        total += n\n        result.append(total)\n    return result"),
        ("ps_prefix_max",
         "def prefix_maxes(arr):\n    prefix = []\n    current_max = float('-inf')\n    for x in arr:\n        current_max = max(current_max, x)\n        prefix.append(current_max)\n    return prefix"),
        ("ps_range_sum_class",
         "class NumArray:\n    def __init__(self, nums):\n        self.p = [0]\n        for n in nums:\n            self.p.append(self.p[-1] + n)\n    def sumRange(self, l, r):\n        return self.p[r+1] - self.p[l]"),
        ("ps_cumulative_product",
         "def cumulative_product(nums):\n    result = []\n    prod = 1\n    for n in nums:\n        prod *= n\n        result.append(prod)\n    return result"),
        ("ps_prefix_count_positive",
         "def prefix_positives(arr):\n    result = []\n    count = 0\n    for x in arr:\n        if x > 0:\n            count += 1\n        result.append(count)\n    return result"),
        ("ps_prefix_count_negative",
         "def prefix_negatives(arr):\n    result = []\n    count = 0\n    for x in arr:\n        if x < 0:\n            count += 1\n        result.append(count)\n    return result"),
    ]:
        cases.append(DisjointCase(name=name, code=code, expected_pattern="prefix_sum",
                                  is_positive=True, family="prefix_generic_accum"))

    # More array_traversal positives
    for name, code in [
        ("at_sum_all",
         "def sum_arr(arr):\n    s = 0\n    for x in arr:\n        s += x\n    return s"),
        ("at_contains_element",
         "def contains(arr, target):\n    for x in arr:\n        if x == target:\n            return True\n    return False"),
        ("at_count_positive",
         "def count_positives(arr):\n    count = 0\n    for x in arr:\n        if x > 0:\n            count += 1\n    return count"),
        ("at_find_index",
         "def find_index(arr, val):\n    for i in range(len(arr)):\n        if arr[i] == val:\n            return i\n    return -1"),
        ("at_filter_positive",
         "def filter_positives(arr):\n    result = []\n    for x in arr:\n        if x > 0:\n            result.append(x)\n    return result"),
        ("at_map_double",
         "def double_all(arr):\n    result = []\n    for x in arr:\n        result.append(x * 2)\n    return result"),
    ]:
        cases.append(DisjointCase(name=name, code=code, expected_pattern="array_traversal",
                                  is_positive=True, family="at_genuine"))

    # More cross-pattern NEGATIVES
    for name, code, pattern, family, notes in [
        # BFS/DFS (not hash_map)
        ("bfs_shortest_unweighted", "from collections import deque\ndef bfs_shortest(graph, src, dst):\n    visited = {src}\n    q = deque([(src, 0)])\n    while q:\n        node, dist = q.popleft()\n        if node == dst: return dist\n        for nb in graph[node]:\n            if nb not in visited:\n                visited.add(nb)\n                q.append((nb, dist+1))\n    return -1", "hash_map_lookup", "hash_vs_bfs", ""),
        ("dfs_connected_components", "def components(graph):\n    visited = set()\n    count = 0\n    for node in graph:\n        if node not in visited:\n            dfs(graph, node, visited)\n            count += 1\n    return count", "hash_map_lookup", "hash_vs_bfs", ""),
        ("bfs_topological", "from collections import deque\ndef topo_sort(graph):\n    in_degree = {n: 0 for n in graph}\n    for n in graph:\n        for nb in graph[n]:\n            in_degree[nb] = in_degree.get(nb, 0) + 1\n    q = deque([n for n in in_degree if in_degree[n] == 0])\n    result = []\n    while q:\n        node = q.popleft()\n        result.append(node)\n        for nb in graph.get(node, []):\n            in_degree[nb] -= 1\n            if in_degree[nb] == 0:\n                q.append(nb)\n    return result", "hash_map_lookup", "hash_vs_bfs", "Dict is structural, not the algorithm"),
        ("dfs_paths", "def all_paths(graph, start, end, path=[]):\n    path = path + [start]\n    if start == end: return [path]\n    paths = []\n    for node in graph[start]:\n        if node not in path:\n            paths.extend(all_paths(graph, node, end, path))\n    return paths", "hash_map_lookup", "hash_vs_bfs", ""),

        # Sorting (not array_traversal)
        ("sort_tim_sort_py", "def tim_sort(arr):\n    return sorted(arr)", "array_traversal", "at_vs_sort", ""),
        ("sort_bucket", "def bucket_sort(arr):\n    if not arr: return []\n    buckets = [[] for _ in range(max(arr) + 1)]\n    for x in arr:\n        buckets[x].append(x)\n    result = []\n    for bucket in buckets:\n        result.extend(sorted(bucket))\n    return result", "array_traversal", "at_vs_sort", ""),
        ("sort_counting", "def counting_sort(arr):\n    if not arr: return []\n    max_val = max(arr)\n    count = [0] * (max_val + 1)\n    for x in arr:\n        count[x] += 1\n    result = []\n    for i, c in enumerate(count):\n        result.extend([i] * c)\n    return result", "array_traversal", "at_vs_sort", ""),

        # DP (not array_traversal or prefix_sum)
        ("dp_stocks_ii", "def max_profit(prices):\n    profit = 0\n    for i in range(1, len(prices)):\n        if prices[i] > prices[i-1]:\n            profit += prices[i] - prices[i-1]\n    return profit", "array_traversal", "at_vs_dp", ""),
        ("dp_max_profit_1", "def max_profit_1(prices):\n    min_price = float('inf')\n    max_profit = 0\n    for p in prices:\n        min_price = min(min_price, p)\n        max_profit = max(max_profit, p - min_price)\n    return max_profit", "prefix_sum", "ps_vs_generic", ""),
        ("dp_word_break_2", "def word_break(s, word_dict):\n    words = set(word_dict)\n    n = len(s)\n    dp = [False] * (n + 1)\n    dp[0] = True\n    for i in range(1, n+1):\n        for j in range(i):\n            if dp[j] and s[j:i] in words:\n                dp[i] = True\n                break\n    return dp[n]", "prefix_sum", "ps_vs_generic", ""),

        # Sliding window (not two_pointers)
        ("sw_min_size_subarray", "def min_sub_len(target, nums):\n    left = 0\n    total = 0\n    min_len = float('inf')\n    for right in range(len(nums)):\n        total += nums[right]\n        while total >= target:\n            min_len = min(min_len, right - left + 1)\n            total -= nums[left]\n            left += 1\n    return 0 if min_len == float('inf') else min_len", "two_pointers_opposite", "tp_vs_sw", ""),
        ("sw_longest_subarray_ones", "def longest_ones(nums, k):\n    left = 0\n    zeros = 0\n    best = 0\n    for right in range(len(nums)):\n        if nums[right] == 0:\n            zeros += 1\n        while zeros > k:\n            if nums[left] == 0:\n                zeros -= 1\n            left += 1\n        best = max(best, right - left + 1)\n    return best", "two_pointers_opposite", "tp_vs_sw", ""),
        ("sw_fixed_k_sum", "def max_sum_k(nums, k):\n    curr = sum(nums[:k])\n    best = curr\n    for i in range(k, len(nums)):\n        curr = curr - nums[i-k] + nums[i]\n        best = max(best, curr)\n    return best", "two_pointers_opposite", "tp_vs_sw", ""),
        ("sw_longest_k_distinct", "def longest_k_distinct(s, k):\n    from collections import Counter\n    freq = Counter()\n    left = 0\n    best = 0\n    for right in range(len(s)):\n        freq[s[right]] += 1\n        while len(freq) > k:\n            freq[s[left]] -= 1\n            if freq[s[left]] == 0:\n                del freq[s[left]]\n            left += 1\n        best = max(best, right - left + 1)\n    return best", "two_pointers_opposite", "tp_vs_sw", ""),
        ("sw_permutation_string", "def check_inclusion(s1, s2):\n    if len(s1) > len(s2): return False\n    from collections import Counter\n    need = Counter(s1)\n    have = Counter(s2[:len(s1)])\n    if need == have: return True\n    for i in range(len(s1), len(s2)):\n        have[s2[i]] += 1\n        old = s2[i - len(s1)]\n        have[old] -= 1\n        if have[old] == 0: del have[old]\n        if need == have: return True\n    return False", "two_pointers_opposite", "tp_vs_sw", ""),

        # Binary search (not two_pointers)
        ("bs_first_bad", "def first_bad(n):\n    lo, hi = 1, n\n    while lo < hi:\n        mid = lo + (hi - lo) // 2\n        if is_bad(mid): hi = mid\n        else: lo = mid + 1\n    return lo", "two_pointers_opposite", "tp_vs_bs", ""),
        ("bs_sqrt_int", "def sqrt_int(x):\n    lo, hi = 0, x\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if mid * mid == x: return mid\n        elif mid * mid < x: lo = mid + 1\n        else: hi = mid - 1\n    return hi", "two_pointers_opposite", "tp_vs_bs", ""),

        # Stack-based (not hash_map or two_pointers)
        ("stack_largest_rect", "def largest_rectangle(heights):\n    stack = []\n    max_area = 0\n    for i, h in enumerate(heights):\n        start = i\n        while stack and stack[-1][1] > h:\n            idx, height = stack.pop()\n            max_area = max(max_area, height * (i - idx))\n            start = idx\n        stack.append((start, h))\n    for idx, height in stack:\n        max_area = max(max_area, height * (len(heights) - idx))\n    return max_area", "hash_map_lookup", "hm_vs_ds", ""),
        ("stack_next_greater", "def next_greater(nums):\n    n = len(nums)\n    result = [-1] * n\n    stack = []\n    for i in range(n):\n        while stack and nums[stack[-1]] < nums[i]:\n            result[stack.pop()] = nums[i]\n        stack.append(i)\n    return result", "hash_map_lookup", "hm_vs_ds", ""),

        # Greedy (not prefix_sum)
        ("greedy_candy", "def candy(ratings):\n    n = len(ratings)\n    candies = [1] * n\n    for i in range(1, n):\n        if ratings[i] > ratings[i-1]:\n            candies[i] = candies[i-1] + 1\n    for i in range(n-2, -1, -1):\n        if ratings[i] > ratings[i+1]:\n            candies[i] = max(candies[i], candies[i+1] + 1)\n    return sum(candies)", "prefix_sum", "ps_vs_generic", "Greedy, not prefix sum"),
        ("greedy_task_scheduler", "def least_interval(tasks, n):\n    from collections import Counter\n    freq = Counter(tasks)\n    max_freq = max(freq.values())\n    max_count = sum(1 for v in freq.values() if v == max_freq)\n    return max(len(tasks), (max_freq - 1) * (n + 1) + max_count)", "prefix_sum", "ps_vs_generic", ""),

        # Linked list (not two_pointers)
        ("ll_cycle_detect", "def has_cycle(head):\n    slow = fast = head\n    while fast and fast.next:\n        slow = slow.next\n        fast = fast.next.next\n        if slow == fast: return True\n    return False", "two_pointers_opposite", "tp_vs_sw", "Floyd's cycle — not opposite pointers"),
        ("ll_merge_sorted", "def merge_lists(l1, l2):\n    dummy = ListNode(0)\n    curr = dummy\n    while l1 and l2:\n        if l1.val <= l2.val:\n            curr.next = l1\n            l1 = l1.next\n        else:\n            curr.next = l2\n            l2 = l2.next\n        curr = curr.next\n    curr.next = l1 or l2\n    return dummy.next", "two_pointers_opposite", "tp_vs_sw", ""),

        # Recursion (not any pattern)
        ("rec_power", "def power(base, exp):\n    if exp == 0: return 1\n    if exp % 2 == 0:\n        half = power(base, exp // 2)\n        return half * half\n    return base * power(base, exp - 1)", "prefix_sum", "ps_vs_generic", ""),
        ("rec_tower_hanoi", "def hanoi(n, src, dst, aux):\n    if n == 1:\n        print(f'Move disk 1 from {src} to {dst}')\n        return\n    hanoi(n-1, src, aux, dst)\n    print(f'Move disk {n} from {src} to {dst}')\n    hanoi(n-1, aux, dst, src)", "array_traversal", "at_vs_dp", ""),
    ]:
        cases.append(DisjointCase(name=name, code=code, expected_pattern=pattern,
                                  is_positive=False, family=family, notes=notes))

    return cases
