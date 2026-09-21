"""Authored reference implementations for the GT-architecture POC.

These are hand-written references contributed by the project author
(``source_type = "authored"``).  Nothing here is scraped or copied from a
third-party source.

Deliberate composition: each problem is given 2–3 *materially different*
implementations plus, where relevant, a deliberately different algorithm family
and/or a brute-force version.  This exists so the deterministic grouping stage
has real structure to find — and so the POC can show what it does with a
brute-force family (spec §10: quarantined as its own family, never discarded).

No code here is tuned to make any grouping or validation result look better.
"""

# problem_id -> list of (local_key, code_text)
AUTHORED_SOLUTIONS = {
    # ------------------------------------------------------------------ LC 1
    1: [
        (
            "two_sum_two_pass",
            """def two_sum_two_pass(nums, target):
    index_of = {}
    for i, value in enumerate(nums):
        index_of[value] = i
    for i, value in enumerate(nums):
        complement = target - value
        if complement in index_of and index_of[complement] != i:
            return [i, index_of[complement]]
    return []
""",
        ),
        (
            "two_sum_sorted_two_pointer",
            """def two_sum_sorted_two_pointer(nums, target):
    ordered = sorted(range(len(nums)), key=lambda i: nums[i])
    lo = 0
    hi = len(ordered) - 1
    while lo < hi:
        total = nums[ordered[lo]] + nums[ordered[hi]]
        if total == target:
            return [ordered[lo], ordered[hi]]
        if total < target:
            lo += 1
        else:
            hi -= 1
    return []
""",
        ),
        (
            "two_sum_brute_force",
            """def two_sum_brute_force(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
""",
        ),
    ],
    # ----------------------------------------------------------------- LC 21
    21: [
        (
            "merge_recursive",
            """def merge_recursive(l1, l2):
    if l1 is None:
        return l2
    if l2 is None:
        return l1
    if l1.val <= l2.val:
        l1.next = merge_recursive(l1.next, l2)
        return l1
    l2.next = merge_recursive(l1, l2.next)
    return l2
""",
        ),
        (
            "merge_iter_dummy",
            """def merge_iter_dummy(head_a, head_b):
    dummy = ListNode(0)
    tail = dummy
    while head_a is not None and head_b is not None:
        if head_a.val < head_b.val:
            tail.next = head_a
            head_a = head_a.next
        else:
            tail.next = head_b
            head_b = head_b.next
        tail = tail.next
    if head_a is not None:
        tail.next = head_a
    else:
        tail.next = head_b
    return dummy.next
""",
        ),
        (
            "merge_collect_sort",
            """def merge_collect_sort(head_a, head_b):
    values = []
    while head_a is not None:
        values.append(head_a.val)
        head_a = head_a.next
    while head_b is not None:
        values.append(head_b.val)
        head_b = head_b.next
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
            "merge_sentinel_swap",
            """def merge_sentinel_swap(a, b):
    if a is None:
        return b
    if b is None:
        return a
    head = a if a.val <= b.val else b
    previous = None
    while a is not None and b is not None:
        if a.val <= b.val:
            chosen = a
            a = a.next
        else:
            chosen = b
            b = b.next
        if previous is not None:
            previous.next = chosen
        previous = chosen
    previous.next = a if a is not None else b
    return head
""",
        ),
    ],
    # ---------------------------------------------------------------- LC 125
    125: [
        (
            "pal_filter_slice",
            """def pal_filter_slice(s):
    cleaned = [c.lower() for c in s if c.isalnum()]
    return cleaned == cleaned[::-1]
""",
        ),
        (
            "pal_two_ptr_manual",
            """def pal_two_ptr_manual(text):
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
            "pal_recursive",
            """def pal_recursive(s):
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
            "pal_regex_two_ptr",
            """import re


def pal_regex_two_ptr(s):
    letters = re.sub(r"[^a-zA-Z0-9]", "", s).lower()
    left = 0
    right = len(letters) - 1
    while left < right:
        if letters[left] != letters[right]:
            return False
        left += 1
        right -= 1
    return True
""",
        ),
    ],
    # ---------------------------------------------------------------- LC 209
    209: [
        (
            "min_subarray_prefix_bs",
            """import bisect


def min_subarray_prefix_bs(target, nums):
    prefix = [0]
    for value in nums:
        prefix.append(prefix[-1] + value)
    best = len(nums) + 1
    for i in range(len(nums)):
        wanted = prefix[i] + target
        j = bisect.bisect_left(prefix, wanted, i + 1)
        if j <= len(nums):
            best = min(best, j - i)
    return 0 if best == len(nums) + 1 else best
""",
        ),
        (
            "min_subarray_prefix_nested",
            """def min_subarray_prefix_nested(target, nums):
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
            """def min_subarray_brute(target, nums):
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
    # ---------------------------------------------------------------- LC 242
    242: [
        (
            "anagram_counter",
            """from collections import Counter


def anagram_counter(s, t):
    return Counter(s) == Counter(t)
""",
        ),
        (
            "anagram_manual_dict",
            """def anagram_manual_dict(s, t):
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
            "anagram_array26",
            """def anagram_array26(s, t):
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
            "anagram_sorted",
            """def anagram_sorted(s, t):
    return sorted(s) == sorted(t)
""",
        ),
        (
            "anagram_set_count",
            """def anagram_set_count(s, t):
    if len(s) != len(t):
        return False
    for ch in set(s):
        if s.count(ch) != t.count(ch):
            return False
    return True
""",
        ),
    ],
    # ---------------------------------------------------------------- LC 560
    560: [
        (
            "subarray_prefix_get",
            """def subarray_prefix_get(nums, k):
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
            "subarray_prefix_defaultdict",
            """from collections import defaultdict


def subarray_prefix_defaultdict(nums, k):
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
            "subarray_prefix_array_nested",
            """def subarray_prefix_array_nested(nums, k):
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
            """def subarray_brute(nums, k):
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
            "subarray_prefix_ifelse",
            """def subarray_prefix_ifelse(nums, k):
    seen = {0: 1}
    total = 0
    count = 0
    for value in nums:
        total += value
        target = total - k
        if target in seen:
            count += seen[target]
        if total in seen:
            seen[total] += 1
        else:
            seen[total] = 1
    return count
""",
        ),
    ],
    # ---------------------------------------------------------------- LC 704
    704: [
        (
            "bs_recursive",
            """def bs_recursive(nums, target):
    def search(lo, hi):
        if lo > hi:
            return -1
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            return search(mid + 1, hi)
        return search(lo, mid - 1)

    return search(0, len(nums) - 1)
""",
        ),
        (
            "bs_lo_hi",
            """def bs_lo_hi(nums, target):
    lo = 0
    hi = len(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    if lo < len(nums) and nums[lo] == target:
        return lo
    return -1
""",
        ),
        (
            "bs_bisect",
            """import bisect


def bs_bisect(nums, target):
    position = bisect.bisect_left(nums, target)
    if position < len(nums) and nums[position] == target:
        return position
    return -1
""",
        ),
        (
            "bs_mid_variant",
            """def bs_mid_variant(nums, target):
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
    ],
    # --------------------------------------------------------------- LC 3236
    3236: [
        (
            "missing_prefix_array",
            """def missing_prefix_array(nums):
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
            "missing_set_based",
            """def missing_set_based(nums):
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
}
