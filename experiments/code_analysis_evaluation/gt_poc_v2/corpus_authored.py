"""Authored reference implementations for the V2 GT-architecture POC.

Hand-written references contributed by the project author
(``source_type = "authored"``).  Nothing is scraped or copied from a
third-party source.

Deliberate composition (spec V2 §8.2 / §12.2):

* 8 solutions per problem, spanning 2–3 genuinely different solution families;
* family members are structural near-variants so the PEC/profile contract is
  exercised rather than the analyzer's incidental noise;
* **D1 duplicates**: several local keys intentionally repeat a byte-identical
  code text (``*_dup`` keys);
* **D2 syntax variants**: several ``*_renamed`` keys are the same algorithm with
  renamed user identifiers (identical name-normalized AST, different raw text);
* **ZERO_EVIDENCE** solutions are included (``Counter == Counter``,
  ``sorted == sorted``, rolling-variable DP, iterative list insertion) so the
  first-class zero-evidence path is exercised.

No code here is tuned to make any grouping or validation result look better.
The reference solutions are *references*, not oracle verdicts.
"""

# problem_id -> list of (local_key, code_text)
AUTHORED_SOLUTIONS = {
    # ================================================================== LC 1
    1: [
        (
            "two_sum_dict_variant",
            """def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
""",
        ),
        (
            "two_sum_brute_range",
            """def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
""",
        ),
        (
            "two_sum_brute_renamed",
            """def two_sum(values, goal):
    for a in range(len(values)):
        for b in range(a + 1, len(values)):
            if values[a] + values[b] == goal:
                return [a, b]
    return []
""",
        ),
        (
            "two_sum_brute_while",
            """def two_sum(values, goal):
    a = 0
    while a < len(values):
        b = a + 1
        while b < len(values):
            if values[a] + values[b] == goal:
                return [a, b]
            b += 1
        a += 1
    return []
""",
        ),
        (
            "two_sum_sort_two_pointer",
            """def two_sum(nums, target):
    order = sorted(range(len(nums)), key=lambda i: nums[i])
    lo = 0
    hi = len(order) - 1
    while lo < hi:
        total = nums[order[lo]] + nums[order[hi]]
        if total == target:
            return [order[lo], order[hi]]
        if total < target:
            lo += 1
        else:
            hi -= 1
    return []
""",
        ),
        (
            "two_sum_sort_two_pointer_renamed",
            """def two_sum(values, goal):
    ranking = sorted(range(len(values)), key=lambda z: values[z])
    start = 0
    end = len(ranking) - 1
    while start < end:
        s = values[ranking[start]] + values[ranking[end]]
        if s == goal:
            return [ranking[start], ranking[end]]
        if s < goal:
            start += 1
        else:
            end -= 1
    return []
""",
        ),
    ],
    # ================================================================= LC 21
    21: [
        (
            "merge_iter_dummy",
            """def merge(list1, list2):
    dummy = ListNode(0)
    tail = dummy
    while list1 and list2:
        if list1.val < list2.val:
            tail.next = list1
            list1 = list1.next
        else:
            tail.next = list2
            list2 = list2.next
        tail = tail.next
    tail.next = list1 if list1 else list2
    return dummy.next
""",
        ),
        (
            "merge_iter_renamed",
            """def merge(a, b):
    head = ListNode(0)
    cursor = head
    while a and b:
        if a.val < b.val:
            cursor.next = a
            a = a.next
        else:
            cursor.next = b
            b = b.next
        cursor = cursor.next
    cursor.next = a if a else b
    return head.next
""",
        ),
        (
            "merge_recursive",
            """def merge(list1, list2):
    if list1 is None:
        return list2
    if list2 is None:
        return list1
    if list1.val <= list2.val:
        list1.next = merge(list1.next, list2)
        return list1
    list2.next = merge(list1, list2.next)
    return list2
""",
        ),
        (
            "merge_recursive_alt",
            """def merge(a, b):
    if not a:
        return b
    if not b:
        return a
    if a.val <= b.val:
        a.next = merge(a.next, b)
        return a
    b.next = merge(a, b.next)
    return b
""",
        ),
        (
            "merge_recursive_renamed",
            """def merge(first, second):
    if first is None:
        return second
    if second is None:
        return first
    if first.val <= second.val:
        first.next = merge(first.next, second)
        return first
    second.next = merge(first, second.next)
    return second
""",
        ),
        (
            "merge_collect_sort",
            """def merge(list1, list2):
    values = []
    while list1 is not None:
        values.append(list1.val)
        list1 = list1.next
    while list2 is not None:
        values.append(list2.val)
        list2 = list2.next
    values.sort()
    dummy = ListNode(0)
    tail = dummy
    for value in values:
        tail.next = ListNode(value)
        tail = tail.next
    return dummy.next
""",
        ),
        (
            "merge_collect_sort_alt",
            """def merge(a, b):
    collected = []
    while a is not None:
        collected.append(a.val)
        a = a.next
    while b is not None:
        collected.append(b.val)
        b = b.next
    collected.sort()
    head = ListNode(0)
    cursor = head
    for item in collected:
        cursor.next = ListNode(item)
        cursor = cursor.next
    return head.next
""",
        ),
    ],
    # ================================================================ LC 125
    125: [
        (
            "pal_two_ptr_manual",
            """def is_palindrome(text):
    i = 0
    j = len(text) - 1
    while i < j:
        while i < j and not text[i].isalnum():
            i += 1
        while i < j and not text[j].isalnum():
            j -= 1
        if text[i].lower() != text[j].lower():
            return False
        i += 1
        j -= 1
    return True
""",
        ),
        (
            "pal_two_ptr_renamed",
            """def is_palindrome(word):
    left = 0
    right = len(word) - 1
    while left < right:
        while left < right and not word[left].isalnum():
            left += 1
        while left < right and not word[right].isalnum():
            right -= 1
        if word[left].lower() != word[right].lower():
            return False
        left += 1
        right -= 1
    return True
""",
        ),
        (
            "pal_filter_slice",
            """def is_palindrome(s):
    cleaned = [c.lower() for c in s if c.isalnum()]
    return cleaned == cleaned[::-1]
""",
        ),
        (
            "pal_filter_slice_simple",
            """def is_palindrome(s):
    kept = [c.lower() for c in s if c.isalnum()]
    return kept == kept[::-1]
""",
        ),
        (
            "pal_recursive",
            """def is_palindrome(s):
    cleaned = [c.lower() for c in s if c.isalnum()]

    def check(lo, hi):
        if lo >= hi:
            return True
        if cleaned[lo] != cleaned[hi]:
            return False
        return check(lo + 1, hi - 1)

    return check(0, len(cleaned) - 1)
""",
        ),
        (
            "pal_recursive_alt",
            """def is_palindrome(s):
    letters = [c.lower() for c in s if c.isalnum()]

    def verify(low, high):
        if low >= high:
            return True
        if letters[low] != letters[high]:
            return False
        return verify(low + 1, high - 1)

    return verify(0, len(letters) - 1)
""",
        ),
        (
            "pal_recursive_renamed",
            """def is_palindrome(t):
    cleaned = [c.lower() for c in t if c.isalnum()]

    def check(lo, hi):
        if lo >= hi:
            return True
        if cleaned[lo] != cleaned[hi]:
            return False
        return check(lo + 1, hi - 1)

    return check(0, len(cleaned) - 1)
""",
        ),
    ],
    # ================================================================ LC 209
    209: [
        (
            "min_subarray_slide",
            """def min_sub_array_len(target, nums):
    left = 0
    summ = 0
    ans = len(nums) + 1
    for right in range(len(nums)):
        summ += nums[right]
        while summ >= target:
            ans = min(ans, right - left + 1)
            summ -= nums[left]
            left += 1
    return 0 if ans == len(nums) + 1 else ans
""",
        ),
        (
            "min_subarray_slide_renamed",
            """def min_sub_array_len(goal, values):
    start = 0
    running = 0
    best = len(values) + 1
    for end in range(len(values)):
        running += values[end]
        while running >= goal:
            best = min(best, end - start + 1)
            running -= values[start]
            start += 1
    return 0 if best == len(values) + 1 else best
""",
        ),
        (
            "min_subarray_prefix_nested",
            """def min_sub_array_len(target, nums):
    prefix = [0]
    for value in nums:
        prefix.append(prefix[-1] + value)
    best = len(nums) + 1
    for i in range(len(nums)):
        for j in range(i + 1, len(nums) + 1):
            if prefix[j] - prefix[i] >= target:
                best = min(best, j - i)
                break
    return 0 if best == len(nums) + 1 else best
""",
        ),
        (
            "min_subarray_prefix_nested_dup",
            """def min_sub_array_len(target, nums):
    prefix = [0]
    for value in nums:
        prefix.append(prefix[-1] + value)
    best = len(nums) + 1
    for i in range(len(nums)):
        for j in range(i + 1, len(nums) + 1):
            if prefix[j] - prefix[i] >= target:
                best = min(best, j - i)
                break
    return 0 if best == len(nums) + 1 else best
""",
        ),
        (
            "min_subarray_brute",
            """def min_sub_array_len(target, nums):
    best = len(nums) + 1
    for i in range(len(nums)):
        total = 0
        for j in range(i, len(nums)):
            total += nums[j]
            if total >= target:
                best = min(best, j - i + 1)
                break
    return 0 if best == len(nums) + 1 else best
""",
        ),
        (
            "min_subarray_brute_dup",
            """def min_sub_array_len(target, nums):
    best = len(nums) + 1
    for i in range(len(nums)):
        total = 0
        for j in range(i, len(nums)):
            total += nums[j]
            if total >= target:
                best = min(best, j - i + 1)
                break
    return 0 if best == len(nums) + 1 else best
""",
        ),
    ],
    # ================================================================ LC 242
    242: [
        (
            "anagram_manual_dict",
            """def is_anagram(s, t):
    if len(s) != len(t):
        return False
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    for ch in t:
        if ch not in counts:
            return False
        counts[ch] -= 1
        if counts[ch] < 0:
            return False
    return True
""",
        ),
        (
            "anagram_manual_dict_renamed",
            """def is_anagram(a, b):
    if len(a) != len(b):
        return False
    tally = {}
    for ch in a:
        tally[ch] = tally.get(ch, 0) + 1
    for ch in b:
        if ch not in tally:
            return False
        tally[ch] -= 1
        if tally[ch] < 0:
            return False
    return True
""",
        ),
        (
            "anagram_manual_ifelse",
            """def is_anagram(s, t):
    if len(s) != len(t):
        return False
    counts = {}
    for ch in s:
        if ch in counts:
            counts[ch] += 1
        else:
            counts[ch] = 1
    for ch in t:
        if ch not in counts:
            return False
        counts[ch] -= 1
    return all(v == 0 for v in counts.values())
""",
        ),
        (
            "anagram_array26",
            """def is_anagram(s, t):
    if len(s) != len(t):
        return False
    slots = [0] * 26
    for ch in s:
        slots[ord(ch) - ord("a")] += 1
    for ch in t:
        slots[ord(ch) - ord("a")] -= 1
    return all(v == 0 for v in slots)
""",
        ),
        (
            "anagram_array26_alt",
            """def is_anagram(s, t):
    if len(s) != len(t):
        return False
    buckets = [0] * 26
    for ch in s:
        buckets[ord(ch) - ord("a")] += 1
    for ch in t:
        buckets[ord(ch) - ord("a")] -= 1
    return all(v == 0 for v in buckets)
""",
        ),
        (
            "anagram_array26_renamed",
            """def is_anagram(x, y):
    if len(x) != len(y):
        return False
    slots = [0] * 26
    for ch in x:
        slots[ord(ch) - ord("a")] += 1
    for ch in y:
        slots[ord(ch) - ord("a")] -= 1
    return all(v == 0 for v in slots)
""",
        ),
        (
            "anagram_counter_eq",
            """from collections import Counter


def is_anagram(s, t):
    return Counter(s) == Counter(t)
""",
        ),
        (
            "anagram_sorted_eq",
            """def is_anagram(s, t):
    return sorted(s) == sorted(t)
""",
        ),
    ],
    # ================================================================ LC 560
    560: [
        (
            "subarray_get_form",
            """def subarray_sum(nums, k):
    seen = {0: 1}
    total = 0
    count = 0
    for value in nums:
        total += value
        count += seen.get(total - k, 0)
        seen[total] = seen.get(total, 0) + 1
    return count
""",
        ),
        (
            "subarray_get_renamed",
            """def subarray_sum(values, goal):
    lookup = {0: 1}
    running = 0
    hits = 0
    for item in values:
        running += item
        hits += lookup.get(running - goal, 0)
        lookup[running] = lookup.get(running, 0) + 1
    return hits
""",
        ),
        (
            "subarray_defaultdict",
            """from collections import defaultdict


def subarray_sum(nums, k):
    seen = defaultdict(int)
    seen[0] = 1
    total = 0
    count = 0
    for value in nums:
        total += value
        count += seen[total - k]
        seen[total] += 1
    return count
""",
        ),
        (
            "subarray_defaultdict_alt",
            """from collections import defaultdict


def subarray_sum(values, goal):
    lookup = defaultdict(int)
    lookup[0] = 1
    running = 0
    hits = 0
    for item in values:
        running += item
        hits += lookup[running - goal]
        lookup[running] += 1
    return hits
""",
        ),
        (
            "subarray_prefix_nested",
            """def subarray_sum(nums, k):
    prefix = [0]
    for value in nums:
        prefix.append(prefix[-1] + value)
    count = 0
    for i in range(len(nums)):
        for j in range(i + 1, len(nums) + 1):
            if prefix[j] - prefix[i] == k:
                count += 1
    return count
""",
        ),
        (
            "subarray_prefix_nested_dup",
            """def subarray_sum(nums, k):
    prefix = [0]
    for value in nums:
        prefix.append(prefix[-1] + value)
    count = 0
    for i in range(len(nums)):
        for j in range(i + 1, len(nums) + 1):
            if prefix[j] - prefix[i] == k:
                count += 1
    return count
""",
        ),
        (
            "subarray_brute",
            """def subarray_sum(nums, k):
    count = 0
    for i in range(len(nums)):
        total = 0
        for j in range(i, len(nums)):
            total += nums[j]
            if total == k:
                count += 1
    return count
""",
        ),
        (
            "subarray_brute_dup",
            """def subarray_sum(nums, k):
    count = 0
    for i in range(len(nums)):
        total = 0
        for j in range(i, len(nums)):
            total += nums[j]
            if total == k:
                count += 1
    return count
""",
        ),
    ],
    # ================================================================ LC 704
    704: [
        (
            "bs_lo_hi",
            """def search(nums, target):
    lo = 0
    hi = len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
""",
        ),
        (
            "bs_lo_hi_renamed",
            """def search(values, goal):
    left = 0
    right = len(values) - 1
    while left <= right:
        pivot = (left + right) // 2
        if values[pivot] == goal:
            return pivot
        if values[pivot] < goal:
            left = pivot + 1
        else:
            right = pivot - 1
    return -1
""",
        ),
        (
            "bs_mid_variant",
            """def search(nums, target):
    left = 0
    right = len(nums) - 1
    while left <= right:
        middle = left + (right - left) // 2
        value = nums[middle]
        if value == target:
            return middle
        if value < target:
            left = middle + 1
        else:
            right = middle - 1
    return -1
""",
        ),
        (
            "bs_recursive",
            """def search(nums, target):
    def lookup(lo, hi):
        if lo > hi:
            return -1
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            return lookup(mid + 1, hi)
        return lookup(lo, mid - 1)

    return lookup(0, len(nums) - 1)
""",
        ),
        (
            "bs_recursive_alt",
            """def search(nums, target):
    def probe(low, high):
        if low > high:
            return -1
        pivot = (low + high) // 2
        if nums[pivot] == target:
            return pivot
        if nums[pivot] < target:
            return probe(pivot + 1, high)
        return probe(low, pivot - 1)

    return probe(0, len(nums) - 1)
""",
        ),
        (
            "bs_recursive_renamed",
            """def search(values, goal):
    def lookup(lo, hi):
        if lo > hi:
            return -1
        mid = (lo + hi) // 2
        if values[mid] == goal:
            return mid
        if values[mid] < goal:
            return lookup(mid + 1, hi)
        return lookup(lo, mid - 1)

    return lookup(0, len(values) - 1)
""",
        ),
        (
            "bs_bisect",
            """import bisect


def search(nums, target):
    position = bisect.bisect_left(nums, target)
    if position < len(nums) and nums[position] == target:
        return position
    return -1
""",
        ),
    ],
    # =============================================================== LC 3236
    3236: [
        (
            "missing_prefix_array",
            """def missing_integer(nums):
    n = len(nums)
    prefix = [nums[0]]
    j = 1
    while j < n and nums[j] == nums[j - 1] + 1:
        prefix.append(prefix[-1] + nums[j])
        j += 1
    candidate = prefix[-1]
    present = set(nums)
    while candidate in present:
        candidate += 1
    return candidate
""",
        ),
        (
            "missing_scalar",
            """def missing_integer(nums):
    total = nums[0]
    i = 1
    while i < len(nums) and nums[i] == nums[i - 1] + 1:
        total += nums[i]
        i += 1
    present = set(nums)
    while total in present:
        total += 1
    return total
""",
        ),
        (
            "missing_scalar_renamed",
            """def missing_integer(values):
    running = values[0]
    k = 1
    while k < len(values) and values[k] == values[k - 1] + 1:
        running += values[k]
        k += 1
    present = set(values)
    while running in present:
        running += 1
    return running
""",
        ),
        (
            "missing_scalar_alt",
            """def missing_integer(nums):
    acc = nums[0]
    pos = 1
    while pos < len(nums):
        if nums[pos] != nums[pos - 1] + 1:
            break
        acc += nums[pos]
        pos += 1
    known = set(nums)
    while acc in known:
        acc += 1
    return acc
""",
        ),
        (
            "missing_set_scalar",
            """def missing_integer(nums):
    present = set(nums)
    total = nums[0]
    i = 1
    while i < len(nums) and nums[i] == nums[i - 1] + 1:
        total += nums[i]
        i += 1
    while total in present:
        total += 1
    return total
""",
        ),
    ],
    # ================================================================ LC 102
    102: [
        (
            "level_order_deque",
            """from collections import deque


def level_order(root):
    if not root:
        return []
    out = []
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
        out.append(level)
    return out
""",
        ),
        (
            "level_order_deque_renamed",
            """from collections import deque


def level_order(start):
    if not start:
        return []
    levels = []
    pending = deque([start])
    while pending:
        row = []
        for _ in range(len(pending)):
            item = pending.popleft()
            row.append(item.val)
            if item.left:
                pending.append(item.left)
            if item.right:
                pending.append(item.right)
        levels.append(row)
    return levels
""",
        ),
        (
            "level_order_list_queue",
            """def level_order(root):
    if not root:
        return []
    out = []
    queue = [root]
    while queue:
        vals = []
        for _ in range(len(queue)):
            node = queue.pop(0)
            vals.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        out.append(vals)
    return out
""",
        ),
        (
            "level_order_list_queue_dup",
            """def level_order(root):
    if not root:
        return []
    out = []
    queue = [root]
    while queue:
        vals = []
        for _ in range(len(queue)):
            node = queue.pop(0)
            vals.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        out.append(vals)
    return out
""",
        ),
        (
            "level_order_dfs",
            """def level_order(root):
    levels = []

    def walk(node, depth):
        if not node:
            return
        if depth == len(levels):
            levels.append([])
        levels[depth].append(node.val)
        walk(node.left, depth + 1)
        walk(node.right, depth + 1)

    walk(root, 0)
    return levels
""",
        ),
        (
            "level_order_dfs_alt",
            """def level_order(root):
    rows = []

    def visit(node, depth):
        if node is None:
            return
        if depth == len(rows):
            rows.append([])
        rows[depth].append(node.val)
        visit(node.left, depth + 1)
        visit(node.right, depth + 1)

    visit(root, 0)
    return rows
""",
        ),
        (
            "level_order_dfs_renamed",
            """def level_order(start):
    levels = []

    def walk(node, depth):
        if not node:
            return
        if depth == len(levels):
            levels.append([])
        levels[depth].append(node.val)
        walk(node.left, depth + 1)
        walk(node.right, depth + 1)

    walk(start, 0)
    return levels
""",
        ),
        (
            "level_order_dfs_dup",
            """def level_order(root):
    levels = []

    def walk(node, depth):
        if not node:
            return
        if depth == len(levels):
            levels.append([])
        levels[depth].append(node.val)
        walk(node.left, depth + 1)
        walk(node.right, depth + 1)

    walk(root, 0)
    return levels
""",
        ),
    ],
    # ================================================================= LC 70
    70: [
        (
            "climb_dp_array",
            """def climb_stairs(n):
    if n <= 2:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    dp[2] = 2
    for i in range(3, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]
""",
        ),
        (
            "climb_dp_array_renamed",
            """def climb_stairs(steps):
    if steps <= 2:
        return steps
    table = [0] * (steps + 1)
    table[1] = 1
    table[2] = 2
    for k in range(3, steps + 1):
        table[k] = table[k - 1] + table[k - 2]
    return table[steps]
""",
        ),
        (
            "climb_dp_array_dup",
            """def climb_stairs(n):
    if n <= 2:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    dp[2] = 2
    for i in range(3, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]
""",
        ),
        (
            "climb_rolling",
            """def climb_stairs(n):
    if n <= 2:
        return n
    a, b = 1, 2
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b
""",
        ),
        (
            "climb_rolling_renamed",
            """def climb_stairs(steps):
    if steps <= 2:
        return steps
    first, second = 1, 2
    for _ in range(3, steps + 1):
        first, second = second, first + second
    return second
""",
        ),
        (
            "climb_memo",
            """def climb_stairs(n):
    memo = {}

    def go(k):
        if k <= 2:
            return k
        if k in memo:
            return memo[k]
        memo[k] = go(k - 1) + go(k - 2)
        return memo[k]

    return go(n)
""",
        ),
        (
            "climb_memo_alt",
            """def climb_stairs(n):
    cache = {}

    def solve(k):
        if k <= 2:
            return k
        if k in cache:
            return cache[k]
        cache[k] = solve(k - 1) + solve(k - 2)
        return cache[k]

    return solve(n)
""",
        ),
        (
            "climb_memo_renamed",
            """def climb_stairs(steps):
    memo = {}

    def go(k):
        if k <= 2:
            return k
        if k in memo:
            return memo[k]
        memo[k] = go(k - 1) + go(k - 2)
        return memo[k]

    return go(steps)
""",
        ),
    ],
    # ================================================================= LC 46
    46: [
        (
            "permute_used",
            """def permute(nums):
    out = []
    used = [False] * len(nums)

    def backtrack(path):
        if len(path) == len(nums):
            out.append(path[:])
            return
        for i in range(len(nums)):
            if used[i]:
                continue
            used[i] = True
            path.append(nums[i])
            backtrack(path)
            path.pop()
            used[i] = False

    backtrack([])
    return out
""",
        ),
        (
            "permute_used_dup",
            """def permute(nums):
    out = []
    used = [False] * len(nums)

    def backtrack(path):
        if len(path) == len(nums):
            out.append(path[:])
            return
        for i in range(len(nums)):
            if used[i]:
                continue
            used[i] = True
            path.append(nums[i])
            backtrack(path)
            path.pop()
            used[i] = False

    backtrack([])
    return out
""",
        ),
        (
            "permute_used_renamed",
            """def permute(values):
    result = []
    taken = [False] * len(values)

    def backtrack(path):
        if len(path) == len(values):
            result.append(path[:])
            return
        for i in range(len(values)):
            if taken[i]:
                continue
            taken[i] = True
            path.append(values[i])
            backtrack(path)
            path.pop()
            taken[i] = False

    backtrack([])
    return result
""",
        ),
        (
            "permute_path_membership",
            """def permute(nums):
    out = []

    def backtrack(path):
        if len(path) == len(nums):
            out.append(list(path))
            return
        for x in nums:
            if x in path:
                continue
            path.append(x)
            backtrack(path)
            path.pop()

    backtrack([])
    return out
""",
        ),
        (
            "permute_path_membership_alt",
            """def permute(nums):
    result = []

    def build(path):
        if len(path) == len(nums):
            result.append(list(path))
            return
        for value in nums:
            if value in path:
                continue
            path.append(value)
            build(path)
            path.pop()

    build([])
    return result
""",
        ),
        (
            "permute_insert",
            """def permute(nums):
    result = [[]]
    for x in nums:
        nxt = []
        for p in result:
            for i in range(len(p) + 1):
                nxt.append(p[:i] + [x] + p[i:])
        result = nxt
    return result
""",
        ),
        (
            "permute_insert_alt",
            """def permute(nums):
    partial = [[]]
    for value in nums:
        grown = []
        for perm in partial:
            for pos in range(len(perm) + 1):
                grown.append(perm[:pos] + [value] + perm[pos:])
        partial = grown
    return partial
""",
        ),
        (
            "permute_insert_renamed",
            """def permute(values):
    result = [[]]
    for x in values:
        nxt = []
        for p in result:
            for i in range(len(p) + 1):
                nxt.append(p[:i] + [x] + p[i:])
        result = nxt
    return result
""",
        ),
    ],
    # ================================================================ LC 547
    547: [
        (
            "provinces_union_find",
            """def find_circle_num(is_connected):
    n = len(is_connected)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    count = n
    for i in range(n):
        for j in range(i + 1, n):
            if is_connected[i][j]:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj
                    count -= 1
    return count
""",
        ),
        (
            "provinces_union_find_renamed",
            """def find_circle_num(matrix):
    n = len(matrix)
    roots = list(range(n))

    def find(x):
        while roots[x] != x:
            roots[x] = roots[roots[x]]
            x = roots[x]
        return x

    total = n
    for a in range(n):
        for b in range(a + 1, n):
            if matrix[a][b]:
                ra, rb = find(a), find(b)
                if ra != rb:
                    roots[ra] = rb
                    total -= 1
    return total
""",
        ),
        (
            "provinces_union_find_alt",
            """def find_circle_num(is_connected):
    n = len(is_connected)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    groups = n
    for i in range(n):
        for j in range(i + 1, n):
            if is_connected[i][j]:
                a, b = find(i), find(j)
                if a != b:
                    parent[a] = b
                    groups -= 1
    return groups
""",
        ),
        (
            "provinces_dfs",
            """def find_circle_num(is_connected):
    n = len(is_connected)
    seen = [False] * n

    def dfs(i):
        seen[i] = True
        for j in range(n):
            if is_connected[i][j] and not seen[j]:
                dfs(j)

    count = 0
    for i in range(n):
        if not seen[i]:
            count += 1
            dfs(i)
    return count
""",
        ),
        (
            "provinces_dfs_alt",
            """def find_circle_num(is_connected):
    n = len(is_connected)
    visited = [False] * n

    def explore(node):
        visited[node] = True
        for neighbor in range(n):
            if is_connected[node][neighbor] and not visited[neighbor]:
                explore(neighbor)

    groups = 0
    for i in range(n):
        if not visited[i]:
            groups += 1
            explore(i)
    return groups
""",
        ),
        (
            "provinces_dfs_renamed",
            """def find_circle_num(matrix):
    n = len(matrix)
    seen = [False] * n

    def dfs(i):
        seen[i] = True
        for j in range(n):
            if matrix[i][j] and not seen[j]:
                dfs(j)

    count = 0
    for i in range(n):
        if not seen[i]:
            count += 1
            dfs(i)
    return count
""",
        ),
        (
            "provinces_bfs",
            """from collections import deque


def find_circle_num(is_connected):
    n = len(is_connected)
    seen = [False] * n
    count = 0
    for i in range(n):
        if seen[i]:
            continue
        count += 1
        queue = deque([i])
        seen[i] = True
        while queue:
            node = queue.popleft()
            for j in range(n):
                if is_connected[node][j] and not seen[j]:
                    seen[j] = True
                    queue.append(j)
    return count
""",
        ),
        (
            "provinces_bfs_alt",
            """from collections import deque


def find_circle_num(is_connected):
    n = len(is_connected)
    visited = [False] * n
    groups = 0
    for start in range(n):
        if visited[start]:
            continue
        groups += 1
        pending = deque([start])
        visited[start] = True
        while pending:
            current = pending.popleft()
            for neighbor in range(n):
                if is_connected[current][neighbor] and not visited[neighbor]:
                    visited[neighbor] = True
                    pending.append(neighbor)
    return groups
""",
        ),
    ],
}

# DB snapshot solutions to include, by problem: (DB_ASSIGNMENT[pid] = [sub ids])
DB_ASSIGNMENT = {
    1: [11, 39],
    21: [252],
    125: [233],
    209: [190, 231],
    242: [],
    560: [],
    704: [235],
    3236: [49, 51, 194],
    102: [],
    70: [],
    46: [],
    547: [],
}
