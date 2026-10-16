"""Disjoint evaluation corpus for Phase 5C.

This corpus was NOT used to design or tune any detectors.
It contains realistic user-style code with renamed variants,
syntax variants, and hard negatives.

Categories:
- binary_search (20+ cases)
- two_pointers (20+ cases)
- sliding_window (20+ cases)
- fixed_sliding_window (15+ cases)
- dfs_backtracking (20+ cases)
- dp_top_down (15+ cases)
- dp_bottom_up (20+ cases)
- bfs (15+ cases)
- union_find (10+ cases)
- linked_list (15+ cases)
- monotonic_stack (15+ cases)
- prefix_sums (10+ cases)
- generic_recursion (10+ cases)
- ordinary_stack (10+ cases)
- heap_usage (10+ cases)
- greedy (10+ cases)
- hash_map_usage (10+ cases)
- array_traversal (10+ cases)
- hard_negatives (20+ cases)
"""

# Each entry: (name, code, expected_strategy_or_None, expected_techniques_or_None)

CORPUS = []

def add(name, code, expected_strategy=None, expected_techniques=None):
    CORPUS.append({
        "name": name,
        "code": code,
        "expected_strategy": expected_strategy,
        "expected_techniques": expected_techniques or [],
    })


# ============================================================
# BINARY SEARCH (20 cases)
# ============================================================

add("bs_standard", """
def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
""", "binary_search")

add("bs_renamed_vars", """
def find_element(arr, val):
    start, end = 0, len(arr) - 1
    while start <= end:
        midpoint = (start + end) // 2
        if arr[midpoint] == val:
            return midpoint
        elif arr[midpoint] < val:
            start = midpoint + 1
        else:
            end = midpoint - 1
    return -1
""", "binary_search")

add("bs_overflow_safe", """
def search_safe(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = lo + (hi - lo) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
""", "binary_search")

add("bs_true_div", """
def search_div(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) / 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
""", "binary_search")

add("bs_rshift", """
def search_bit(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) >> 1
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
""", "binary_search")

add("bs_rotated", """
def search_rotated(nums, target):
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
""", "binary_search")

add("bs_answer_space", """
def min_eating_speed(piles, h):
    lo, hi = 1, max(piles)
    while lo < hi:
        mid = (lo + hi) // 2
        if can_finish(piles, mid, h):
            hi = mid
        else:
            lo = mid + 1
    return lo

def can_finish(piles, speed, h):
    return sum((p + speed - 1) // speed for p in piles) <= h
""", "binary_search")

add("bs_leftmost", """
def find_leftmost(nums, target):
    lo, hi = 0, len(nums) - 1
    result = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            result = mid
            hi = mid - 1
        elif nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return result
""", "binary_search")

add("bs_class_method", """
class Solution:
    def search(self, nums, target):
        l, r = 0, len(nums) - 1
        while l <= r:
            m = (l + r) // 2
            if nums[m] == target:
                return m
            if nums[m] < target:
                l = m + 1
            else:
                r = m - 1
        return -1
""", "binary_search")

add("bs_nested_if", """
def bs_nested(arr, val):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == val:
            return mid
        else:
            if arr[mid] < val:
                left = mid + 1
            else:
                right = mid - 1
    return -1
""", "binary_search")

add("bs_early_return", """
def bs_early(arr, target):
    i, j = 0, len(arr) - 1
    while i <= j:
        k = (i + j) // 2
        if arr[k] == target:
            return k
        if arr[k] > target:
            j = k - 1
        else:
            i = k + 1
    return -1
""", "binary_search")

add("bs_no_midpoint_two_pointers", """
def check_sorted(arr):
    i, j = 0, len(arr) - 1
    while i < j:
        if arr[i] + arr[j] == 0:
            return True
        elif arr[i] + arr[j] < 0:
            i += 1
        else:
            j -= 1
    return False
""", "two_pointers_opposite")

add("bs_while_without_midpoint", """
def linear_scan(arr, target):
    i, j = 0, len(arr) - 1
    while i <= j:
        if arr[i] == target:
            return i
        i += 1
    return -1
""", None)

add("bs_recursive", """
def bs_recursive(arr, target, lo, hi):
    if lo > hi:
        return -1
    mid = (lo + hi) // 2
    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        return bs_recursive(arr, target, mid + 1, hi)
    else:
        return bs_recursive(arr, target, lo, mid - 1)
""", None)

add("bs_three_conditions", """
def search3(arr, val):
    l, r = 0, len(arr) - 1
    while l <= r:
        m = (l + r) // 2
        if arr[m] < val:
            l = m + 1
        elif arr[m] > val:
            r = m - 1
        else:
            return m
    return -1
""", "binary_search")

add("bs_overflow_safe_renamed", """
def bsearch(collection, item):
    first, last = 0, len(collection) - 1
    while first <= last:
        midpt = first + (last - first) // 2
        if collection[midpt] == item:
            return midpt
        elif collection[midpt] < item:
            first = midpt + 1
        else:
            last = midpt - 1
    return -1
""", "binary_search")

add("bs_alternate_condition", """
def bs_alt(nums, target):
    lo, hi = 0, len(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] >= target:
            hi = mid
        else:
            lo = mid + 1
    return lo if lo < len(nums) and nums[lo] == target else -1
""", "binary_search")

add("bs_find_insert", """
def search_insert(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        center = (left + right) // 2
        if nums[center] == target:
            return center
        elif nums[center] < target:
            left = center + 1
        else:
            right = center - 1
    return left
""", "binary_search")

add("bs_min_in_rotated", """
def find_min(nums):
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] > nums[hi]:
            lo = mid + 1
        else:
            hi = mid
    return nums[lo]
""", "binary_search")

add("bs_peak_element", """
def find_peak(nums):
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] < nums[mid + 1]:
            lo = mid + 1
        else:
            hi = mid
    return lo
""", "binary_search")


# ============================================================
# TWO POINTERS (20 cases)
# ============================================================

add("tp_palindrome", """
def is_palindrome(s):
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True
""", "two_pointers_opposite")

add("tp_container_water", """
def max_area(height):
    left, right = 0, len(height) - 1
    max_w = 0
    while left < right:
        w = min(height[left], height[right]) * (right - left)
        max_w = max(max_w, w)
        if height[left] < height[right]:
            left += 1
        else:
            right -= 1
    return max_w
""", "two_pointers_opposite")

add("tp_3sum", """
def three_sum(nums):
    nums.sort()
    result = []
    for i in range(len(nums) - 2):
        lo, hi = i + 1, len(nums) - 1
        while lo < hi:
            s = nums[i] + nums[lo] + nums[hi]
            if s == 0:
                result.append([nums[i], nums[lo], nums[hi]])
                lo += 1
                hi -= 1
            elif s < 0:
                lo += 1
            else:
                hi -= 1
    return result
""", "two_pointers_opposite")

add("tp_two_sum_sorted", """
def two_sum_sorted(nums, target):
    left, right = 0, len(nums) - 1
    while left < right:
        curr = nums[left] + nums[right]
        if curr == target:
            return [left, right]
        elif curr < target:
            left += 1
        else:
            right -= 1
    return []
""", "two_pointers_opposite")

add("tp_trapping_rain", """
def trap(height):
    left, right = 0, len(height) - 1
    left_max = right_max = water = 0
    while left < right:
        if height[left] < height[right]:
            if height[left] >= left_max:
                left_max = height[left]
            else:
                water += left_max - height[left]
            left += 1
        else:
            if height[right] >= right_max:
                right_max = height[right]
            else:
                water += right_max - height[right]
            right -= 1
    return water
""", "two_pointers_opposite")

add("tp_remove_duplicates", """
def remove_duplicates(nums):
    if not nums:
        return 0
    slow = 0
    for fast in range(1, len(nums)):
        if nums[fast] != nums[slow]:
            slow += 1
            nums[slow] = nums[fast]
    return slow + 1
""", None)

add("tp_merge_sorted", """
def merge(arr1, m, arr2, n):
    i, j, k = m - 1, n - 1, m + n - 1
    while i >= 0 and j >= 0:
        if arr1[i] > arr2[j]:
            arr1[k] = arr1[i]
            i -= 1
        else:
            arr1[k] = arr2[j]
            j -= 1
        k -= 1
    while j >= 0:
        arr1[k] = arr2[j]
        j -= 1
        k -= 1
""", None)

add("tp_valid_mountain", """
def valid_mountain(arr):
    n = len(arr)
    i = 0
    while i + 1 < n and arr[i] < arr[i + 1]:
        i += 1
    if i == 0 or i == n - 1:
        return False
    while i + 1 < n and arr[i] > arr[i + 1]:
        i += 1
    return i == n - 1
""", None)

add("tp_pair_sum_sorted", """
def pair_sum(arr, target):
    i, j = 0, len(arr) - 1
    while i < j:
        s = arr[i] + arr[j]
        if s == target:
            return (i, j)
        elif s < target:
            i += 1
        else:
            j -= 1
    return None
""", "two_pointers_opposite")

add("tp_palindrome_renamed", """
def check_palindrome(string):
    front, back = 0, len(string) - 1
    while front < back:
        if string[front] != string[back]:
            return False
        front += 1
        back -= 1
    return True
""", "two_pointers_opposite")

add("tp_move_zeroes", """
def move_zeroes(nums):
    slow = 0
    for fast in range(len(nums)):
        if nums[fast] != 0:
            nums[slow], nums[fast] = nums[fast], nums[slow]
            slow += 1
""", None)

add("tp_reverse_string", """
def reverse_string(s):
    left, right = 0, len(s) - 1
    while left < right:
        s[left], s[right] = s[right], s[left]
        left += 1
        right -= 1
""", "two_pointers_opposite")

add("tp_sorted_squares", """
def sorted_squares(nums):
    result = [0] * len(nums)
    left, right = 0, len(nums) - 1
    idx = len(nums) - 1
    while left <= right:
        if abs(nums[left]) > abs(nums[right]):
            result[idx] = nums[left] ** 2
            left += 1
        else:
            result[idx] = nums[right] ** 2
            right -= 1
        idx -= 1
    return result
""", "two_pointers_opposite")

add("tp_interval_intersection", """
def interval_intersection(A, B):
    i = j = 0
    result = []
    while i < len(A) and j < len(B):
        lo = max(A[i][0], B[j][0])
        hi = min(A[i][1], B[j][1])
        if lo <= hi:
            result.append([lo, hi])
        if A[i][1] < B[j][1]:
            i += 1
        else:
            j += 1
    return result
""", "two_pointers_opposite")

add("tp_4sum", """
def four_sum(nums, target):
    nums.sort()
    result = []
    for i in range(len(nums) - 3):
        for j in range(i + 1, len(nums) - 2):
            lo, hi = j + 1, len(nums) - 1
            while lo < hi:
                s = nums[i] + nums[j] + nums[lo] + nums[hi]
                if s == target:
                    result.append([nums[i], nums[j], nums[lo], nums[hi]])
                    lo += 1
                    hi -= 1
                elif s < target:
                    lo += 1
                else:
                    hi -= 1
    return result
""", "two_pointers_opposite")

add("tp_slow_fast_cycle", """
def has_cycle(head):
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
""", "linked_list_traversal")

add("tp_two_pointer_while_true", """
def find_pair(arr, target):
    i, j = 0, len(arr) - 1
    while True:
        if i >= j:
            break
        s = arr[i] + arr[j]
        if s == target:
            return [i, j]
        elif s < target:
            i += 1
        else:
            j -= 1
    return []
""", "two_pointers_opposite")

add("tp_comparator_driven", """
def min_diff_pair(arr):
    arr.sort()
    min_d = float('inf')
    for i in range(len(arr) - 1):
        d = arr[i + 1] - arr[i]
        if d < min_d:
            min_d = d
    return min_d
""", None)

add("tp_partition", """
def partition(arr, lo, hi):
    pivot = arr[hi]
    i = lo - 1
    for j in range(lo, hi):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i + 1], arr[hi] = arr[hi], arr[i + 1]
    return i + 1
""", None)

add("tp_converge_with_state", """
def min_window(s, t):
    from collections import Counter
    need = Counter(t)
    missing = len(t)
    left = 0
    start, end = 0, float('inf')
    for right in range(len(s)):
        if need[s[right]] > 0:
            missing -= 1
        need[s[right]] -= 1
        while missing == 0:
            if right - left < end - start:
                start, end = left, right
            need[s[left]] += 1
            if need[s[left]] > 0:
                missing += 1
            left += 1
    return s[start:end + 1] if end < float('inf') else ""
""", "sliding_window")


# ============================================================
# SLIDING WINDOW - VARIABLE (20 cases)
# ============================================================

add("sw_longest_substring", """
def longest_substring(s):
    char_index = {}
    left = 0
    max_len = 0
    for right in range(len(s)):
        if s[right] in char_index:
            left = max(left, char_index[s[right]] + 1)
        char_index[s[right]] = right
        max_len = max(max_len, right - left + 1)
    return max_len
""", "sliding_window")

add("sw_max_avg_subarray", """
def find_max_average(nums, k):
    window_sum = sum(nums[:k])
    max_sum = window_sum
    for i in range(k, len(nums)):
        window_sum += nums[i] - nums[i - k]
        max_sum = max(max_sum, window_sum)
    return max_sum / k
""", "sliding_window")

add("sw_longest_ones(self)", """
def longest_ones(nums, k):
    left = 0
    max_len = 0
    zeros = 0
    for right in range(len(nums)):
        if nums[right] == 0:
            zeros += 1
        while zeros > k:
            if nums[left] == 0:
                zeros -= 1
            left += 1
        max_len = max(max_len, right - left + 1)
    return max_len
""", "sliding_window")

add("sw_min_window_substring", """
def min_window(s, t):
    from collections import Counter
    need = Counter(t)
    missing = len(t)
    left = 0
    start, end = 0, float('inf')
    for right in range(len(s)):
        if need[s[right]] > 0:
            missing -= 1
        need[s[right]] -= 1
        while missing == 0:
            if right - left < end - start:
                start, end = left, right
            need[s[left]] += 1
            if need[s[left]] > 0:
                missing += 1
            left += 1
    return s[start:end + 1] if end < float('inf') else ""
""", "sliding_window")

add("sw_max_consecutive_ones", """
def longest_oneness(nums, k):
    left = 0
    max_len = 0
    flips = 0
    for right in range(len(nums)):
        if nums[right] == 0:
            flips += 1
        while flips > k:
            if nums[left] == 0:
                flips -= 1
            left += 1
        max_len = max(max_len, right - left + 1)
    return max_len
""", "sliding_window")

add("sw_permutation_in_string", """
def check_inclusion(s1, s2):
    from collections import Counter
    need = Counter(s1)
    window = {}
    for right in range(len(s2)):
        window[s2[right]] = window.get(s2[right], 0) + 1
        if right >= len(s1):
            left_char = s2[right - len(s1)]
            if window[left_char] == 1:
                del window[left_char]
            else:
                window[left_char] -= 1
        if window == need:
            return True
    return False
""", "sliding_window")

add("sw_subarray_sum_k", """
def subarray_sum(nums, k):
    count = 0
    prefix_sum = 0
    seen = {0: 1}
    for num in nums:
        prefix_sum += num
        if prefix_sum - k in seen:
            count += seen[prefix_sum - k]
        seen[prefix_sum] = seen.get(prefix_sum, 0) + 1
    return count
""", None)

add("sw_renamed_window", """
def longest_without_repeat(string):
    char_pos = {}
    start = 0
    best = 0
    for end in range(len(string)):
        if string[end] in char_pos:
            start = max(start, char_pos[string[end]] + 1)
        char_pos[string[end]] = end
        best = max(best, end - start + 1)
    return best
""", "sliding_window")

add("sw_for_with_inner_while", """
def max_sum_subarray(nums, k):
    curr = sum(nums[:k])
    best = curr
    for i in range(k, len(nums)):
        curr += nums[i] - nums[i - k]
        best = max(best, curr)
    return best
""", "sliding_window")

add("sw_contains_nearby_duplicate", """
def contains_nearby_duplicate(nums, k):
    window = set()
    for i in range(len(nums)):
        if nums[i] in window:
            return True
        window.add(nums[i])
        if len(window) > k:
            window.remove(nums[i - k])
    return False
""", "sliding_window")

add("sw_grumpy_bookstore", """
def max_satisfied(customers, grumpy, minutes):
    total = sum(c for c, g in zip(customers, grumpy) if g == 0)
    extra = sum(c for c, g in zip(customers[:minutes], grumpy[:minutes]))
    max_extra = extra
    for i in range(minutes, len(customers)):
        extra += customers[i] * grumpy[i] - customers[i - minutes] * grumpy[i - minutes]
        max_extra = max(max_extra, extra)
    return total + max_extra
""", "sliding_window")

add("sw_longest_substring_k_distinct", """
def longest_substring_k(s, k):
    from collections import Counter
    counter = Counter()
    left = 0
    max_len = 0
    for right in range(len(s)):
        counter[s[right]] += 1
        while len(counter) > k:
            counter[s[left]] -= 1
            if counter[s[left]] == 0:
                del counter[s[left]]
            left += 1
        max_len = max(max_len, right - left + 1)
    return max_len
""", "sliding_window")

add("sw_max_points_from_cards", """
def max_score(cardPoints, k):
    n = len(cardPoints)
    window_size = n - k
    window_sum = sum(cardPoints[:window_size])
    min_sum = window_sum
    for i in range(window_size, n):
        window_sum += cardPoints[i] - cardPoints[i - window_size]
        min_sum = min(min_sum, window_sum)
    return sum(cardPoints) - min_sum
""", "sliding_window")

add("sw_fruits_into_baskets", """
def total_fruit(fruits):
    from collections import Counter
    basket = Counter()
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
""", "sliding_window")

add("sw_no_inner_while", """
def sliding_sum(nums, k):
    s = sum(nums[:k])
    result = [s]
    for i in range(k, len(nums)):
        s += nums[i] - nums[i - k]
        result.append(s)
    return result
""", "sliding_window")

add("sw_variable_renamed_complex", """
def longest_distinct substring):
    seen = {}
    start = 0
    best = 0
    for end in range(len(substring)):
        ch = substring[end]
        if ch in seen and seen[ch] >= start:
            start = seen[ch] + 1
        seen[ch] = end
        best = max(best, end - start + 1)
    return best
""", None)

add("sw_without_hash", """
def max_avg_subarray(nums, k):
    s = sum(nums[:k])
    mx = s
    for i in range(k, len(nums)):
        s += nums[i] - nums[i - k]
        mx = max(mx, s)
    return mx / k
""", "sliding_window")

add("sw_class_style", """
class Solution:
    def lengthOfLongestSubstring(self, s):
        char_map = {}
        left = 0
        max_len = 0
        for right in range(len(s)):
            if s[right] in char_map:
                left = max(left, char_map[s[right]] + 1)
            char_map[s[right]] = right
            max_len = max(max_len, right - left + 1)
        return max_len
""", "sliding_window")

add("sw_with_counter", """
def find_anagrams(s, p):
    from collections import Counter
    pc = Counter(p)
    sc = Counter()
    result = []
    for i in range(len(s)):
        sc[s[i]] += 1
        if i >= len(p):
            if sc[s[i - len(p)]] == 1:
                del sc[s[i - len(p)]]
            else:
                sc[s[i - len(p)]] -= 1
        if sc == pc:
            result.append(i - len(p) + 1)
    return result
""", "sliding_window")


# ============================================================
# FIXED SLIDING WINDOW (15 cases)
# ============================================================

add("fw_max_sum_k", """
def max_sum_subarray(nums, k):
    n = len(nums)
    window_sum = sum(nums[:k])
    max_sum = window_sum
    for i in range(k, n):
        window_sum += nums[i] - nums[i - k]
        max_sum = max(max_sum, window_sum)
    return max_sum
""", "sliding_window")

add("fw_average_k", """
def find_averages(arr, k):
    result = []
    window_sum = sum(arr[:k])
    result.append(window_sum / k)
    for i in range(k, len(arr)):
        window_sum += arr[i] - arr[i - k]
        result.append(window_sum / k)
    return result
""", "sliding_window")

add("fw_size_param", """
def max_avg(arr, size):
    n = len(arr)
    curr = sum(arr[:size])
    best = curr
    for idx in range(size, n):
        curr += arr[idx] - arr[idx - size]
        best = max(best, curr)
    return best / size
""", "sliding_window")

add("fw_const_offset", """
def fixed_max(nums, w):
    s = sum(nums[:w])
    mx = s
    for i in range(w, len(nums)):
        s += nums[i] - nums[i - w]
        mx = max(mx, s)
    return mx
""", "sliding_window")

add("fw_class_method", """
class Solution:
    def maxSubArray(self, nums, k):
        window = sum(nums[:k])
        best = window
        for i in range(k, len(nums)):
            window += nums[i] - nums[i - k]
            best = max(best, window)
        return best
""", "sliding_window")

add("fw_count_occurrences", """
def count_occurrences(text, pattern):
    if len(pattern) > len(text):
        return 0
    pat_hash = hash(pattern)
    win_hash = hash(text[:len(pattern)])
    count = 1 if win_hash == pat_hash else 0
    for i in range(len(pattern), len(text)):
        win_hash = hash(text[i - len(pattern) + 1:i + 1])
        if win_hash == pat_hash:
            count += 1
    return count
""", None)

add("fw_no_offset_different_code", """
def fixed_sum(nums, k):
    total = 0
    for i in range(k):
        total += nums[i]
    result = total
    for i in range(k, len(nums)):
        total = total + nums[i] - nums[i - k]
        result = max(result, total)
    return result
""", "sliding_window")

add("fw_with_helper", """
def process(nums, size):
    def window_sum(arr, start, sz):
        s = 0
        for j in range(start, start + sz):
            s += arr[j]
        return s
    best = window_sum(nums, 0, size)
    for i in range(1, len(nums) - size + 1):
        best = max(best, window_sum(nums, i, size))
    return best
""", None)

add("fw_max_sum_subarray_k_renamed", """
def greatest_sum_block(arr, block_size):
    n = len(arr)
    running = sum(arr[:block_size])
    answer = running
    for pos in range(block_size, n):
        running += arr[pos] - arr[pos - block_size]
        answer = max(answer, running)
    return answer
""", "sliding_window")

add("fw_negative_k", """
def max_avg_neg(nums, k):
    s = sum(nums[:k])
    mx = s
    for i in range(k, len(nums)):
        s += nums[i] - nums[i - k]
        mx = max(mx, s)
    return mx / k
""", "sliding_window")

add("fw_nested_loop_not_window", """
def count_pairs_with_sum(arr, k):
    count = 0
    for i in range(len(arr)):
        for j in range(i + 1, min(i + k + 1, len(arr))):
            if arr[i] + arr[j] == 0:
                count += 1
    return count
""", None)

add("fw_matrix_row", """
def max_row_sum(matrix, k):
    result = 0
    for row in matrix:
        s = sum(row[:k])
        mx = s
        for i in range(k, len(row)):
            s += row[i] - row[i - k]
            mx = max(mx, s)
        result = max(result, mx)
    return result
""", "sliding_window")

add("fw_different_structure", """
def sliding(nums, size):
    acc = 0
    for i in range(size):
        acc += nums[i]
    best = acc
    i = size
    while i < len(nums):
        acc += nums[i]
        acc -= nums[i - size]
        if acc > best:
            best = acc
        i += 1
    return best
""", "sliding_window")

add("fw_not_k_parameter", """
def constant_offset_demo(data):
    n = len(data)
    s = sum(data[:3])
    mx = s
    for i in range(3, n):
        s += data[i] - data[i - 3]
        mx = max(mx, s)
    return mx
""", "sliding_window")

add("fw_no_offset_at_all", """
def array_max(nums):
    mx = nums[0]
    for i in range(1, len(nums)):
        if nums[i] > mx:
            mx = nums[i]
    return mx
""", None)


# ============================================================
# DFS/BACKTRACKING (20 cases)
# ============================================================

add("dfs_subsets", """
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
""", "dfs_backtracking")

add("dfs_permutations", """
def permute(nums):
    result = []
    def backtrack(path, remaining):
        if not remaining:
            result.append(path[:])
            return
        for i in range(len(remaining)):
            path.append(remaining[i])
            backtrack(path, remaining[:i] + remaining[i + 1:])
            path.pop()
    backtrack([], nums)
    return result
""", "dfs_backtracking")

add("dfs_nqueens", """
def solve_nqueens(n):
    result = []
    def backtrack(row, cols, diag1, diag2, board):
        if row == n:
            result.append(["".join(r) for r in board])
            return
        for col in range(n):
            if col in cols or row - col in diag1 or row + col in diag2:
                continue
            board[row][col] = "Q"
            backtrack(row + 1, cols | {col}, diag1 | {row - col}, diag2 | {row + col}, board)
            board[row][col] = "."
    backtrack(0, set(), set(), set(), [["."] * n for _ in range(n)])
    return result
""", "dfs_backtracking")

add("dfs_combination_sum", """
def combination_sum(candidates, target):
    result = []
    def backtrack(start, path, remaining):
        if remaining == 0:
            result.append(path[:])
            return
        for i in range(start, len(candidates)):
            if candidates[i] > remaining:
                continue
            path.append(candidates[i])
            backtrack(i, path, remaining - candidates[i])
            path.pop()
    backtrack(0, [], target)
    return result
""", "dfs_backtracking")

add("dfs_word_search", """
def exist(board, word):
    rows, cols = len(board), len(board[0])
    def backtrack(r, c, idx):
        if idx == len(word):
            return True
        if r < 0 or r >= rows or c < 0 or c >= cols or board[r][c] != word[idx]:
            return False
        temp = board[r][c]
        board[r][c] = "#"
        found = (backtrack(r + 1, c, idx + 1) or backtrack(r - 1, c, idx + 1) or
                 backtrack(r, c + 1, idx + 1) or backtrack(r, c - 1, idx + 1))
        board[r][c] = temp
        return found
    for r in range(rows):
        for c in range(cols):
            if backtrack(r, c, 0):
                return True
    return False
""", "dfs_backtracking")

add("dfs_restore_ip", """
def restore_ip_addresses(s):
    result = []
    def backtrack(start, path):
        if len(path) == 4:
            if start == len(s):
                result.append(".".join(path))
            return
        for length in range(1, 4):
            if start + length > len(s):
                break
            segment = s[start:start + length]
            if len(segment) > 1 and segment[0] == "0":
                break
            if int(segment) > 255:
                break
            backtrack(start + length, path + [segment])
    backtrack(0, [])
    return result
""", "dfs_backtracking")

add("dfs_letter_combinations", """
def letter_combinations(digits):
    if not digits:
        return []
    mapping = {"2": "abc", "3": "def", "4": "ghi", "5": "jkl",
               "6": "mno", "7": "pqrs", "8": "tuv", "9": "wxyz"}
    result = []
    def backtrack(index, path):
        if index == len(digits):
            result.append(path)
            return
        for char in mapping[digits[index]]:
            backtrack(index + 1, path + char)
    backtrack(0, "")
    return result
""", "dfs_backtracking")

add("dfs_palindrome_partition", """
def partition_palindrome(s):
    result = []
    def backtrack(start, path):
        if start == len(s):
            result.append(path[:])
            return
        for end in range(start + 1, len(s) + 1):
            sub = s[start:end]
            if sub == sub[::-1]:
                path.append(sub)
                backtrack(end, path)
                path.pop()
    backtrack(0, [])
    return result
""", "dfs_backtracking")

add("dfs_combination_sum_2", """
def combination_sum2(candidates, target):
    result = []
    candidates.sort()
    def backtrack(start, path, remaining):
        if remaining == 0:
            result.append(path[:])
            return
        for i in range(start, len(candidates)):
            if i > start and candidates[i] == candidates[i - 1]:
                continue
            if candidates[i] > remaining:
                break
            path.append(candidates[i])
            backtrack(i + 1, path, remaining - candidates[i])
            path.pop()
    backtrack(0, [], target)
    return result
""", "dfs_backtracking")

add("dfs_gen_parentheses", """
def generate_parentheses(n):
    result = []
    def backtrack(path, open_count, close_count):
        if len(path) == 2 * n:
            result.append(path)
            return
        if open_count < n:
            backtrack(path + "(", open_count + 1, close_count)
        if close_count < open_count:
            backtrack(path + ")", open_count, close_count + 1)
    backtrack("", 0, 0)
    return result
""", "dfs_backtracking")

add("dfs_not_backtracking_linear", """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
""", None)

add("dfs_fibonacci(self)", """
def fib(n, memo={}):
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    memo[n] = fib(n - 1) + fib(n - 2)
    return memo[n]
""", "dp_top_down")

add("dfs_tree_traversal_no_backtrack", """
def tree_height(root):
    if not root:
        return 0
    left = tree_height(root.left)
    right = tree_height(root.right)
    return 1 + max(left, right)
""", None)

add("dfs_renamed_backtrack", """
def find_subsets(collection):
    output = []
    def explore(position, current):
        output.append(current[:])
        for idx in range(position, len(collection)):
            current.append(collection[idx])
            explore(idx + 1, current)
            current.pop()
    explore(0, [])
    return output
""", "dfs_backtracking")

add("dfs_class_style", """
class Solution:
    def subsets(self, nums):
        self.result = []
        def helper(start, path):
            self.result.append(path[:])
            for i in range(start, len(nums)):
                path.append(nums[i])
                helper(i + 1, path)
                path.pop()
        helper(0, [])
        return self.result
""", "dfs_backtracking")

add("dfs_maze_solver", """
def solve_maze(maze, start, end):
    rows, cols = len(maze), len(maze[0])
    visited = set()
    path = []
    def backtrack(r, c):
        if (r, c) == end:
            path.append((r, c))
            return True
        if r < 0 or r >= rows or c < 0 or c >= cols:
            return False
        if maze[r][c] == 1 or (r, c) in visited:
            return False
        visited.add((r, c))
        path.append((r, c))
        if (backtrack(r + 1, c) or backtrack(r - 1, c) or
            backtrack(r, c + 1) or backtrack(r, c - 1)):
            return True
        path.pop()
        return False
    backtrack(start[0], start[1])
    return path
""", "dfs_backtracking")

add("dfs_permute_unique", """
def permute_unique(nums):
    result = []
    nums.sort()
    def backtrack(path, used):
        if len(path) == len(nums):
            result.append(path[:])
            return
        for i in range(len(nums)):
            if used[i]:
                continue
            if i > 0 and nums[i] == nums[i - 1] and not used[i - 1]:
                continue
            used[i] = True
            path.append(nums[i])
            backtrack(path, used)
            path.pop()
            used[i] = False
    backtrack([], [False] * len(nums))
    return result
""", "dfs_backtracking")

add("dfs_nqueens_renamed", """
def solve_queens(n):
    solutions = []
    def place(row, cols, diags1, diags2, board):
        if row == n:
            solutions.append(["".join(r) for r in board])
            return
        for c in range(n):
            if c in cols or row - c in diags1 or row + c in diags2:
                continue
            board[row][c] = "Q"
            place(row + 1, cols | {c}, diags1 | {row - c}, diags2 | {row + c}, board)
            board[row][c] = "."
    place(0, set(), set(), set(), [["."] * n for _ in range(n)])
    return solutions
""", "dfs_backtracking")

add("dfs_graph_dfs_no_backtrack", """
def dfs_graph(graph, node, visited=None):
    if visited is None:
        visited = set()
    visited.add(node)
    for neighbor in graph.get(node, []):
        if neighbor not in visited:
            dfs_graph(graph, neighbor, visited)
    return visited
""", None)

add("dfs_sudoku_solver", """
def solve_sudoku(board):
    def is_valid(row, col, num):
        for i in range(9):
            if board[row][i] == num:
                return False
            if board[i][col] == num:
                return False
        box_r, box_c = 3 * (row // 3), 3 * (col // 3)
        for i in range(box_r, box_r + 3):
            for j in range(box_c, box_c + 3):
                if board[i][j] == num:
                    return False
        return True

    def backtrack():
        for r in range(9):
            for c in range(9):
                if board[r][c] == ".":
                    for num in "123456789":
                        if is_valid(r, c, num):
                            board[r][c] = num
                            if backtrack():
                                return True
                            board[r][c] = "."
                    return False
        return True
    backtrack()
""", "dfs_backtracking")


# ============================================================
# DP TOP-DOWN (15 cases)
# ============================================================

add("dp_memo_fib", """
def fib(n, memo={}):
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    memo[n] = fib(n - 1) + fib(n - 2)
    return memo[n]
""", "dp_top_down")

add("dp_climbing_stairs", """
def climb_stairs(n, memo={}):
    if n in memo:
        return memo[n]
    if n <= 2:
        return n
    memo[n] = climb_stairs(n - 1) + climb_stairs(n - 2)
    return memo[n]
""", "dp_top_down")

add("dp_coin_change_memo", """
def coin_change(coins, amount, memo={}):
    if amount in memo:
        return memo[amount]
    if amount == 0:
        return 0
    if amount < 0:
        return float('inf')
    result = float('inf')
    for coin in coins:
        result = min(result, 1 + coin_change(coins, amount - coin, memo))
    memo[amount] = result
    return result
""", "dp_top_down")

add("dp_renamed_memo", """
def decode_ways(s, pos, cache):
    if pos in cache:
        return cache[pos]
    if pos >= len(s):
        return 1
    if s[pos] == "0":
        return 0
    result = decode_ways(s, pos + 1, cache)
    if pos + 1 < len(s) and (s[pos] == "1" or (s[pos] == "2" and s[pos + 1] in "0123456")):
        result += decode_ways(s, pos + 2, cache)
    cache[pos] = result
    return result
""", "dp_top_down")

add("dp_house_robber_memo", """
def rob(nums, i, memo={}):
    if i in memo:
        return memo[i]
    if i < 0:
        return 0
    memo[i] = max(rob(nums, i - 2, memo) + nums[i], rob(nums, i - 1, memo))
    return memo[i]
""", "dp_top_down")

add("dp_grid_path_memo", """
def unique_paths(m, n, memo={}):
    if (m, n) in memo:
        return memo[(m, n)]
    if m == 1 or n == 1:
        return 1
    memo[(m, n)] = unique_paths(m - 1, n, memo) + unique_paths(m, n - 1, memo)
    return memo[(m, n)]
""", "dp_top_down")

add("dp_word_break_memo", """
def word_break(s, word_dict, memo={}):
    if s in memo:
        return memo[s]
    if not s:
        return True
    for word in word_dict:
        if s.startswith(word) and word_break(s[len(word):], word_dict, memo):
            memo[s] = True
            return True
    memo[s] = False
    return False
""", "dp_top_down")

add("dp_longest_common_subseq_memo", """
def lcs(s1, s2, i, j, memo={}):
    if (i, j) in memo:
        return memo[(i, j)]
    if i == len(s1) or j == len(s2):
        return 0
    if s1[i] == s2[j]:
        memo[(i, j)] = 1 + lcs(s1, s2, i + 1, j + 1, memo)
    else:
        memo[(i, j)] = max(lcs(s1, s2, i + 1, j, memo), lcs(s1, s2, i, j + 1, memo))
    return memo[(i, j)]
""", "dp_top_down")

add("dp_edit_distance_memo", """
def edit_distance(s1, s2, i, j, memo={}):
    if (i, j) in memo:
        return memo[(i, j)]
    if i == 0:
        return j
    if j == 0:
        return i
    if s1[i - 1] == s2[j - 1]:
        memo[(i, j)] = edit_distance(s1, s2, i - 1, j - 1, memo)
    else:
        memo[(i, j)] = 1 + min(
            edit_distance(s1, s2, i - 1, j, memo),
            edit_distance(s1, s2, i, j - 1, memo),
            edit_distance(s1, s2, i - 1, j - 1, memo)
        )
    return memo[(i, j)]
""", "dp_top_down")

add("dp_plain_recursion_not_dp", """
def sum_list(arr, idx):
    if idx >= len(arr):
        return 0
    return arr[idx] + sum_list(arr, idx + 1)
""", None)

add("dp_plain_recursion_fib_no_memo", """
def fib_no_memo(n):
    if n <= 1:
        return n
    return fib_no_memo(n - 1) + fib_no_memo(n - 2)
""", None)

add("dp_lru_cache_class", """
class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = {}
    def get(self, key):
        return self.cache.get(key, -1)
    def put(self, key, value):
        if len(self.cache) >= self.capacity:
            del next(iter(self.cache))
        self.cache[key] = value
""", None)

add("dp_memo_renamed", """
def count_ways(n, lookup={}):
    if n in lookup:
        return lookup[n]
    if n < 0:
        return 0
    if n == 0:
        return 1
    lookup[n] = count_ways(n - 1, lookup) + count_ways(n - 2, lookup) + count_ways(n - 3, lookup)
    return lookup[n]
""", "dp_top_down")

add("dp_with_lru_cache", """
from functools import lru_cache

@lru_cache(maxsize=None)
def min_coins(coins, amount):
    if amount == 0:
        return 0
    if amount < 0:
        return float('inf')
    return min(1 + min_coins(coins, amount - c) for c in coins)
""", "dp_top_down")

add("dp_maze_path_memo", """
def count_paths(grid, r, c, memo={}):
    if (r, c) in memo:
        return memo[(r, c)]
    if r < 0 or c < 0 or grid[r][c] == 1:
        return 0
    if r == 0 and c == 0:
        return 1
    memo[(r, c)] = count_paths(grid, r - 1, c, memo) + count_paths(grid, r, c - 1, memo)
    return memo[(r, c)]
""", "dp_top_down")


# ============================================================
# DP BOTTOM-UP (20 cases)
# ============================================================

add("dp_bottomup_fib", """
def fib(n):
    if n <= 1:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]
""", "dp_bottom_up")

add("dp_house_robber", """
def rob(nums):
    if not nums:
        return 0
    if len(nums) == 1:
        return nums[0]
    dp = [0] * len(nums)
    dp[0] = nums[0]
    dp[1] = max(nums[0], nums[1])
    for i in range(2, len(nums)):
        dp[i] = max(dp[i - 1], dp[i - 2] + nums[i])
    return dp[-1]
""", "dp_bottom_up")

add("dp_coin_change", """
def coin_change(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for i in range(1, amount + 1):
        for coin in coins:
            if coin <= i:
                dp[i] = min(dp[i], dp[i - coin] + 1)
    return dp[amount] if dp[amount] != float('inf') else -1
""", "dp_bottom_up")

add("dp_longest_increasing", """
def lis(nums):
    n = len(nums)
    dp = [1] * n
    for i in range(1, n):
        for j in range(i):
            if nums[j] < nums[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)
""", "dp_bottom_up")

add("dp_grid_unique_paths", """
def unique_paths(m, n):
    dp = [[1] * n for _ in range(m)]
    for i in range(1, m):
        for j in range(1, n):
            dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
    return dp[m - 1][n - 1]
""", "dp_bottom_up")

add("dp_knapsack", """
def knapsack(weights, values, capacity):
    n = len(weights)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(capacity + 1):
            dp[i][w] = dp[i - 1][w]
            if weights[i - 1] <= w:
                dp[i][w] = max(dp[i][w], dp[i - 1][w - weights[i - 1]] + values[i - 1])
    return dp[n][capacity]
""", "dp_bottom_up")

add("dp_lcs", """
def lcs(s1, s2):
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]
""", "dp_bottom_up")

add("dp_climbing_stairs_bottomup", """
def climb_stairs(n):
    if n <= 2:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    dp[2] = 2
    for i in range(3, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]
""", "dp_bottom_up")

add("dp_min_path_sum", """
def min_path_sum(grid):
    m, n = len(grid), len(grid[0])
    dp = [[0] * n for _ in range(m)]
    dp[0][0] = grid[0][0]
    for i in range(1, m):
        dp[i][0] = dp[i - 1][0] + grid[i][0]
    for j in range(1, n):
        dp[0][j] = dp[0][j - 1] + grid[0][j]
    for i in range(1, m):
        for j in range(1, n):
            dp[i][j] = grid[i][j] + min(dp[i - 1][j], dp[i][j - 1])
    return dp[m - 1][n - 1]
""", "dp_bottom_up")

add("dp_edit_distance", """
def edit_distance(s1, s2):
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[m][n]
""", "dp_bottom_up")

add("dp_egg_drop", """
def egg_drop(eggs, floors):
    dp = [[0] * (floors + 1) for _ in range(eggs + 1)]
    for j in range(1, floors + 1):
        dp[1][j] = j
    for i in range(2, eggs + 1):
        for j in range(1, floors + 1):
            dp[i][j] = j
            for k in range(1, j):
                dp[i][j] = min(dp[i][j], max(dp[i - 1][k - 1], dp[i][j - k]) + 1)
    return dp[eggs][floors]
""", "dp_bottom_up")

add("dp_word_break_bottomup", """
def word_break(s, word_dict):
    dp = [False] * (len(s) + 1)
    dp[0] = True
    for i in range(1, len(s) + 1):
        for word in word_dict:
            if i >= len(word) and dp[i - len(word)] and s[i - len(word):i] == word:
                dp[i] = True
                break
    return dp[len(s)]
""", "dp_bottom_up")

add("dp_renamed_bottomup", """
def longest_chain(nums):
    n = len(nums)
    table = [1] * n
    for i in range(1, n):
        for j in range(i):
            if nums[j] < nums[i]:
                table[i] = max(table[i], table[j] + 1)
    return max(table)
""", "dp_bottom_up")

add("dp_prefix_sum", """
def prefix_sums(nums):
    prefix = [0] * (len(nums) + 1)
    for i in range(len(nums)):
        prefix[i + 1] = prefix[i] + nums[i]
    return prefix
""", "dp_bottom_up")

add("dp_not_dp_generic_loop", """
def count_positives(nums):
    count = 0
    for x in nums:
        if x > 0:
            count += 1
    return count
""", None)

add("dp_generic_array_ops", """
def transform(arr):
    result = [0] * len(arr)
    for i in range(len(arr)):
        result[i] = arr[i] * 2
    return result
""", None)

add("dp_bottomup_renamed(self)", """
class Solution:
    def rob(self, nums):
        if not nums:
            return 0
        n = len(nums)
        table = [0] * n
        table[0] = nums[0]
        if n > 1:
            table[1] = max(nums[0], nums[1])
        for idx in range(2, n):
            table[idx] = max(table[idx - 1], table[idx - 2] + nums[idx])
        return table[-1]
""", "dp_bottom_up")

add("dp_house_robber_space_optimized", """
def rob(nums):
    if not nums:
        return 0
    prev2, prev1 = 0, 0
    for num in nums:
        prev2, prev1 = prev1, max(prev1, prev2 + num)
    return prev1
""", None)

add("dp_2d_grid_bottomup(self)", """
class Solution:
    def uniquePaths(self, m, n):
        dp = [[1] * n for _ in range(m)]
        for i in range(1, m):
            for j in range(1, n):
                dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
        return dp[m - 1][n - 1]
""", "dp_bottom_up")


# ============================================================
# BFS (15 cases)
# ============================================================

add("bfs_graph_shortest", """
from collections import deque

def bfs_shortest(graph, start):
    visited = {start}
    queue = deque([(start, 0)])
    distances = {start: 0}
    while queue:
        node, dist = queue.popleft()
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                distances[neighbor] = dist + 1
                queue.append((neighbor, dist + 1))
    return distances
""", "bfs_shortest_path")

add("bfs_level_order", """
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
""", "bfs_shortest_path")

add("bfs_word_ladder", """
from collections import deque

def word_ladder(begin, end, word_list):
    word_set = set(word_list)
    queue = deque([(begin, 1)])
    visited = {begin}
    while queue:
        word, steps = queue.popleft()
        if word == end:
            return steps
        for i in range(len(word)):
            for c in "abcdefghijklmnopqrstuvwxyz":
                next_word = word[:i] + c + word[i + 1:]
                if next_word in word_set and next_word not in visited:
                    visited.add(next_word)
                    queue.append((next_word, steps + 1))
    return 0
""", "bfs_shortest_path")

add("bfs_renamed", """
from collections import deque

def bfs_traversal(adj_list, source):
    seen = set([source])
    q = deque([source])
    order = []
    while q:
        vertex = q.popleft()
        order.append(vertex)
        for adj in adj_list[vertex]:
            if adj not in seen:
                seen.add(adj)
                q.append(adj)
    return order
""", "bfs_shortest_path")

add("bfs_islands(self)", """
from collections import deque

class Solution:
    def numIslands(self, grid):
        if not grid:
            return 0
        count = 0
        for i in range(len(grid)):
            for j in range(len(grid[0])):
                if grid[i][j] == "1":
                    count += 1
                    grid[i][j] = "0"
                    queue = deque([(i, j)])
                    while queue:
                        r, c = queue.popleft()
                        for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < len(grid) and 0 <= nc < len(grid[0]) and grid[nr][nc] == "1":
                                grid[nr][nc] = "0"
                                queue.append((nr, nc))
        return count
""", "bfs_shortest_path")

add("bfs_rotten_oranges", """
from collections import deque

def oranges_rotting(grid):
    queue = deque()
    for i in range(len(grid)):
        for j in range(len(grid[0])):
            if grid[i][j] == 2:
                queue.append((i, j))
    minutes = 0
    while queue:
        for _ in range(len(queue)):
            r, c = queue.popleft()
            for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < len(grid) and 0 <= nc < len(grid[0]) and grid[nr][nc] == 1:
                    grid[nr][nc] = 2
                    queue.append((nr, nc))
        if queue:
            minutes += 1
    return minutes
""", "bfs_shortest_path")

add("bfs_dfs_no_queue", """
def dfs_recursive(graph, node, visited=None):
    if visited is None:
        visited = set()
    visited.add(node)
    for neighbor in graph.get(node, []):
        if neighbor not in visited:
            dfs_recursive(graph, neighbor, visited)
    return visited
""", None)

add("bfs_not_shortest_path", """
from collections import deque

def process_with_queue(items):
    queue = deque(items)
    result = []
    while queue:
        item = queue.popleft()
        result.append(item * 2)
    return result
""", None)

add("bfs_grid_bfs_renamed", """
from collections import deque

def shortest_path_binary_matrix(grid):
    n = len(grid)
    if grid[0][0] == 1 or grid[n-1][n-1] == 1:
        return -1
    q = deque([(0, 0, 1)])
    visited = set([(0, 0)])
    while q:
        r, c, dist = q.popleft()
        if r == n - 1 and c == n - 1:
            return dist
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < n and grid[nr][nc] == 0 and (nr, nc) not in visited:
                    visited.add((nr, nc))
                    q.append((nr, nc, dist + 1))
    return -1
""", "bfs_shortest_path")

add("bfs_multi_source", """
from collections import deque

def multi_source_bfs(grid):
    n, m = len(grid), len(grid[0])
    queue = deque()
    for i in range(n):
        for j in range(m):
            if grid[i][j] == 0:
                queue.append((i, j))
    dist = [[-1] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            if grid[i][j] == 1:
                dist[i][j] = -1
            else:
                dist[i][j] = 0
    while queue:
        r, c = queue.popleft()
        for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < m and dist[nr][nc] == -1:
                dist[nr][nc] = dist[r][c] + 1
                queue.append((nr, nc))
    return dist
""", "bfs_shortest_path")

add("bfs_no_visited_tracking", """
from collections import deque

def traverse(graph, start):
    q = deque([start])
    result = []
    while q:
        node = q.popleft()
        result.append(node)
        for neighbor in graph.get(node, []):
            q.append(neighbor)
    return result
""", None)

add("bfs_with_level_count", """
from collections import deque

def count_levels(root):
    if not root:
        return 0
    q = deque([root])
    levels = 0
    while q:
        levels += 1
        for _ in range(len(q)):
            node = q.popleft()
            if node.left:
                q.append(node.left)
            if node.right:
                q.append(node.right)
    return levels
""", "bfs_shortest_path")

add("bfs_open_lock", """
from collections import deque

def open_lock(deadends, target):
    dead = set(deadends)
    if "0000" in dead:
        return -1
    queue = deque([("0000", 0)])
    visited = {"0000"}
    while queue:
        state, steps = queue.popleft()
        if state == target:
            return steps
        for i in range(4):
            for d in [-1, 1]:
                new_state = state[:i] + str((int(state[i]) + d) % 10) + state[i+1:]
                if new_state not in visited and new_state not in dead:
                    visited.add(new_state)
                    queue.append((new_state, steps + 1))
    return -1
""", "bfs_shortest_path")

add("bfs_sliding_puzzle", """
from collections import deque

def sliding_puzzle(board):
    target = "123450"
    start = "".join(str(x) for row in board for x in row)
    if start == target:
        return 0
    neighbors = {
        0: [1, 3], 1: [0, 2, 4], 2: [1, 5],
        3: [0, 4], 4: [1, 3, 5], 5: [2, 4]
    }
    queue = deque([(start, 0)])
    visited = {start}
    while queue:
        state, moves = queue.popleft()
        zero_pos = state.index("0")
        for next_pos in neighbors[zero_pos]:
            lst = list(state)
            lst[zero_pos], lst[next_pos] = lst[next_pos], lst[zero_pos]
            next_state = "".join(lst)
            if next_state == target:
                return moves + 1
            if next_state not in visited:
                visited.add(next_state)
                queue.append((next_state, moves + 1))
    return -1
""", "bfs_shortest_path")


# ============================================================
# UNION-FIND (10 cases)
# ============================================================

add("uf_classic", """
def find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

def union(parent, rank, x, y):
    px, py = find(parent, x), find(parent, y)
    if px == py:
        return False
    if rank[px] < rank[py]:
        px, py = py, px
    parent[py] = px
    if rank[px] == rank[py]:
        rank[px] += 1
    return True
""", "union_find")

add("uf_inline", """
def solve(graph):
    n = len(graph)
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
    for u, v in graph:
        union(u, v)
    return len(set(find(i) for i in range(n)))
""", "union_find")

add("uf_renamed(self)", """
class Solution:
    def findRedundantConnection(self, edges):
        parent = {}
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(x, y):
            px, py = find(x), find(y)
            if px == py:
                return False
            parent[px] = py
            return True
        for u, v in edges:
            if u not in parent:
                parent[u] = u
            if v not in parent:
                parent[v] = v
            if not union(u, v):
                return [u, v]
""", "union_find")

add("uf_no_rank", """
def connected_components(n, edges):
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x
    def union(x, y):
        parent[find(x)] = find(y)
    for u, v in edges:
        union(u, v)
    return len(set(find(i) for i in range(n)))
""", "union_find")

add("uf_with_size", """
def count_components(n, edges):
    parent = list(range(n))
    size = [1] * n
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        pa, pb = find(a), find(b)
        if pa == pb:
            return
        if size[pa] < size[pb]:
            pa, pb = pb, pa
        parent[pb] = pa
        size[pa] += size[pb]
    for u, v in edges:
        union(u, v)
    return len(set(find(i) for i in range(n)))
""", "union_find")

add("uf_accounts_merge", """
def accounts_merge(accounts):
    from collections import defaultdict
    parent = {}
    email_to_name = {}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    for account in accounts:
        name = account[0]
        for email in account[1:]:
            email_to_name[email] = name
            if email not in parent:
                parent[email] = email
            union(account[1], email)
    groups = defaultdict(list)
    for email in parent:
        groups[find(email)].append(email)
    return [[email_to_name[emails[0]]] + sorted(emails) for emails in groups.values()]
""", "union_find")

add("uf_not_union_find_parent_array", """
def find_max(arr):
    mx = arr[0]
    for i in range(1, len(arr)):
        if arr[i] > mx:
            mx = arr[i]
    return mx
""", None)

add("uf_not_union_find_tree(self)", """
class Solution:
    def maxDepth(self, root):
        if not root:
            return 0
        return 1 + max(self.maxDepth(root.left), self.maxDepth(root.right))
""", None)

add("uf_renamed_with_path_splitting", """
def merge_sets(n, pairs):
    root = list(range(n))
    def find(x):
        if root[x] != x:
            root[x] = find(root[x])
        return root[x]
    def unite(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            root[ra] = rb
    for a, b in pairs:
        unite(a, b)
    return len(set(find(i) for i in range(n)))
""", "union_find")

add("uf_weighted_union(self)", """
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x
    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return False
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1
        return True
""", "union_find")


# ============================================================
# LINKED LIST (15 cases)
# ============================================================

add("ll_reversal", """
class Solution:
    def reverseList(self, head):
        prev = None
        curr = head
        while curr:
            next_temp = curr.next
            curr.next = prev
            prev = curr
            curr = next_temp
        return prev
""", expected_techniques=["linked_list_traversal"])

add("ll_merge_two", """
class Solution:
    def mergeTwoLists(self, l1, l2):
        dummy = ListNode()
        curr = dummy
        while l1 and l2:
            if l1.val <= l2.val:
                curr.next = l1
                l1 = l1.next
            else:
                curr.next = l2
                l2 = l2.next
            curr = curr.next
        curr.next = l1 or l2
        return dummy.next
""", expected_techniques=["linked_list_traversal"])

add("ll_cycle_detection", """
class Solution:
    def hasCycle(self, head):
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
""", expected_techniques=["linked_list_traversal"])

add("ll_add_two_numbers", """
class Solution:
    def addTwoNumbers(self, l1, l2):
        dummy = ListNode()
        curr = dummy
        carry = 0
        while l1 or l2 or carry:
            val = (l1.val if l1 else 0) + (l2.val if l2 else 0) + carry
            carry, digit = divmod(val, 10)
            curr.next = ListNode(digit)
            curr = curr.next
            l1 = l1.next if l1 else None
            l2 = l2.next if l2 else None
        return dummy.next
""", None)

add("ll_reverse_pairs", """
def reverse_pairs(head):
    prev = None
    curr = head
    while curr:
        nxt = curr.next
        curr.next = prev
        prev = curr
        curr = nxt
    return prev
""", expected_techniques=["linked_list_traversal"])

add("ll_remove_nth(self)", """
class Solution:
    def removeNthFromEnd(self, head, n):
        dummy = ListNode(0)
        dummy.next = head
        fast = slow = dummy
        for _ in range(n + 1):
            fast = fast.next
        while fast:
            fast = fast.next
            slow = slow.next
        slow.next = slow.next.next
        return dummy.next
""", expected_techniques=["linked_list_traversal"])

add("ll_rotate_list(self)", """
class Solution:
    def rotateRight(self, head, k):
        if not head or not head.next:
            return head
        length = 1
        tail = head
        while tail.next:
            tail = tail.next
            length += 1
        k = k % length
        if k == 0:
            return head
        tail.next = head
        new_tail = head
        for _ in range(length - k - 1):
            new_tail = new_tail.next
        new_head = new_tail.next
        new_tail.next = None
        return new_head
""", expected_techniques=["linked_list_traversal"])

add("ll_swap_pairs", """
def swap_pairs(head):
    if not head or not head.next:
        return head
    first = head
    second = head.next
    first.next = swap_pairs(second.next)
    second.next = first
    return second
""", None)

add("ll_flatten(self)", """
class Solution:
    def flatten(self, head):
        if not head:
            return None
        stack = [head]
        prev = None
        while stack:
            curr = stack.pop()
            if prev:
                prev.next = curr
                curr.prev = prev
            if curr.next:
                stack.append(curr.next)
            if curr.down:
                stack.append(curr.down)
            prev = curr
        return head
""", expected_techniques=["linked_list_traversal"])

add("ll_simple_traversal_not_ll(self)", """
class Solution:
    def getDecimalValue(self, head):
        result = 0
        while head:
            result = result * 2 + head.val
            head = head.next
        return result
""", None)

add("ll_copy_random_list(self)", """
class Solution:
    def copyRandomList(self, head):
        if not head:
            return None
        mapping = {}
        curr = head
        while curr:
            mapping[curr] = Node(curr.val)
            curr = curr.next
        curr = head
        while curr:
            if curr.next:
                mapping[curr].next = mapping[curr.next]
            if curr.random:
                mapping[curr].random = mapping[curr.random]
            curr = curr.next
        return mapping[head]
""", expected_techniques=["linked_list_traversal"])

add("ll_reversed_between(self)", """
class Solution:
    def reverseBetween(self, head, left, right):
        if left == right:
            return head
        dummy = ListNode(0)
        dummy.next = head
        prev = dummy
        for _ in range(left - 1):
            prev = prev.next
        curr = prev.next
        for _ in range(right - left):
            nxt = curr.next
            curr.next = nxt.next
            nxt.next = prev.next
            prev.next = nxt
        return dummy.next
""", expected_techniques=["linked_list_traversal"])

add("ll_odd_even(self)", """
class Solution:
    def oddEvenList(self, head):
        if not head:
            return None
        odd = head
        even = head.next
        even_head = even
        while even and even.next:
            odd.next = even.next
            odd = odd.next
            even.next = odd.next
            even = even.next
        odd.next = even_head
        return head
""", expected_techniques=["linked_list_traversal"])

add("ll_palindrome(self)", """
class Solution:
    def isPalindrome(self, head):
        vals = []
        while head:
            vals.append(head.val)
            head = head.next
        return vals == vals[::-1]
""", None)

add("ll_partition(self)", """
class Solution:
    def partition(self, head, x):
        before = ListNode(0)
        after = ListNode(0)
        b, a = before, after
        while head:
            if head.val < x:
                b.next = head
                b = b.next
            else:
                a.next = head
                a = a.next
            head = head.next
        a.next = None
        b.next = after.next
        return before.next
""", expected_techniques=["linked_list_traversal"])


# ============================================================
# MONOTONIC STACK (15 cases)
# ============================================================

add("ms_next_greater", """
def next_greater_element(nums):
    n = len(nums)
    result = [-1] * n
    stack = []
    for i in range(n):
        while stack and nums[stack[-1]] < nums[i]:
            idx = stack.pop()
            result[idx] = nums[i]
        stack.append(i)
    return result
""", "monotonic_stack_strategy")

add("ms_daily_temperatures", """
def daily_temperatures(temps):
    n = len(temps)
    result = [0] * n
    stack = []
    for i in range(n):
        while stack and temps[stack[-1]] < temps[i]:
            idx = stack.pop()
            result[i - idx] = i - idx
        stack.append(i)
    return result
""", "monotonic_stack_strategy")

add("ms_histogram", """
def largest_rectangle_area(heights):
    stack = []
    max_area = 0
    for i, h in enumerate(heights):
        while stack and heights[stack[-1]] > h:
            height = heights[stack.pop()]
            width = i if not stack else i - stack[-1] - 1
            max_area = max(max_area, height * width)
        stack.append(i)
    while stack:
        height = heights[stack.pop()]
        width = len(heights) if not stack else len(heights) - stack[-1] - 1
        max_area = max(max_area, height * width)
    return max_area
""", "monotonic_stack_strategy")

add("ms_stock_span", """
def stock_span(prices):
    n = len(prices)
    result = [1] * n
    stack = []
    for i in range(n):
        while stack and prices[stack[-1]] <= prices[i]:
            result[i] += result[stack.pop()]
        stack.append(i)
    return result
""", "monotonic_stack_strategy")

add("ms_next_greater_renamed", """
def find_next_larger(arr):
    n = len(arr)
    output = [-1] * n
    stk = []
    for idx in range(n):
        while stk and arr[stk[-1]] < arr[idx]:
            i = stk.pop()
            output[i] = arr[idx]
        stk.append(idx)
    return output
""", "monotonic_stack_strategy")

add("ms_asteroid_collision", """
def asteroid_collision(asteroids):
    stack = []
    for a in asteroids:
        while stack and a < 0 and stack[-1] > 0:
            if abs(a) > stack[-1]:
                stack.pop()
            elif abs(a) == stack[-1]:
                stack.pop()
                break
            else:
                break
        else:
            stack.append(a)
    return stack
""", None)

add("ms_decode_string(self)", """
class Solution:
    def decodeString(self, s):
        stack = []
        num = 0
        curr = ""
        for ch in s:
            if ch.isdigit():
                num = num * 10 + int(ch)
            elif ch == "[":
                stack.append((curr, num))
                curr = ""
                num = 0
            elif ch == "]":
                prev, n = stack.pop()
                curr = prev + curr * n
            else:
                curr += ch
        return curr
""", None)

add("ms_min_stack(self)", """
class MinStack:
    def __init__(self):
        self.stack = []
        self.min_stack = []
    def push(self, val):
        self.stack.append(val)
        if not self.min_stack or val <= self.min_stack[-1]:
            self.min_stack.append(val)
    def pop(self):
        val = self.stack.pop()
        if val == self.min_stack[-1]:
            self.min_stack.pop()
        return val
    def top(self):
        return self.stack[-1]
    def getMin(self):
        return self.min_stack[-1]
""", None)

add("ms_valid_parentheses", """
def is_valid(s):
    stack = []
    mapping = {")": "(", "}": "{", "]": "["}
    for ch in s:
        if ch in mapping:
            if not stack or stack[-1] != mapping[ch]:
                return False
            stack.pop()
        else:
            stack.append(ch)
    return not stack
""", None)

add("ms_calculator(self)", """
class Solution:
    def calculate(self, s):
        stack = []
        num = 0
        op = "+"
        for i, ch in enumerate(s):
            if ch.isdigit():
                num = num * 10 + int(ch)
            if (not ch.isdigit() and ch != " ") or i == len(s) - 1:
                if op == "+":
                    stack.append(num)
                elif op == "-":
                    stack.append(-num)
                elif op == "*":
                    stack.append(stack.pop() * num)
                elif op == "/":
                    stack.append(int(stack.pop() / num))
                op = ch
                num = 0
        return sum(stack)
""", None)

add("ms_nested_iterator(self)", """
class NestedIterator:
    def __init__(self, nestedList):
        self.stack = list(reversed(nestedList))
    def next(self):
        return self.hasNext() and self._pop().getInteger()
    def hasNext(self):
        while self.stack:
            top = self.stack[-1]
            if top.isInteger():
                return True
            self.stack.pop()
            self.stack.extend(reversed(top.getList()))
        return False
""", None)

add("ms_largest_hist_renamed", """
def max_histogram_area(heights):
    stk = []
    best = 0
    for i, h in enumerate(heights):
        while stk and heights[stk[-1]] > h:
            height = heights[stk.pop()]
            width = i if not stk else i - stk[-1] - 1
            best = max(best, height * width)
        stk.append(i)
    while stk:
        height = heights[stk.pop()]
        width = len(heights) if not stk else len(heights) - stk[-1] - 1
        best = max(best, height * width)
    return best
""", "monotonic_stack_strategy")

add("ms_trap_rain_water_stack", """
def trap(height):
    stack = []
    water = 0
    for i, h in enumerate(height):
        while stack and height[stack[-1]] < h:
            bottom = stack.pop()
            if stack:
                width = i - stack[-1] - 1
                water += (min(h, height[stack[-1]]) - height[bottom]) * width
        stack.append(i)
    return water
""", None)

add("ms_next_greater_circular", """
def next_greater_circular(nums):
    n = len(nums)
    result = [-1] * n
    stack = []
    for i in range(2 * n):
        while stack and nums[stack[-1]] < nums[i % n]:
            result[stack.pop()] = nums[i % n]
        if i < n:
            stack.append(i)
    return result
""", "monotonic_stack_strategy")

add("ms_sum_subarray_mins(self)", """
class Solution:
    def sumSubarrayMins(self, arr):
        MOD = 10**9 + 7
        stack = []
        result = 0
        for i, a in enumerate(arr + [0]):
            while stack and arr[stack[-1]] > a:
                j = stack.pop()
                left = j - stack[-1] if stack else j + 1
                right = i - j
                result = (result + arr[j] * left * right) % MOD
            stack.append(i)
        return result
""", "monotonic_stack_strategy")


# ============================================================
# PREFIX SUMS (10 cases)
# ============================================================

add("ps_basic", """
def prefix_sum(nums):
    prefix = [0] * (len(nums) + 1)
    for i in range(len(nums)):
        prefix[i + 1] = prefix[i] + nums[i]
    return prefix
""", "dp_bottom_up")

add("ps_range_sum", """
def range_sum(nums, queries):
    prefix = [0]
    for num in nums:
        prefix.append(prefix[-1] + num)
    return [prefix[r + 1] - prefix[l] for l, r in queries]
""", "dp_bottom_up")

add("ps_subarray_sum_k", """
def subarray_sum_k(nums, k):
    count = 0
    prefix = 0
    seen = {0: 1}
    for num in nums:
        prefix += num
        count += seen.get(prefix - k, 0)
        seen[prefix] = seen.get(prefix, 0) + 1
    return count
""", None)

add("ps_running_total", """
def running_total(nums):
    total = 0
    result = []
    for num in nums:
        total += num
        result.append(total)
    return result
""", None)

add("ps_2d_prefix(self)", """
class NumMatrix:
    def __init__(self, matrix):
        m, n = len(matrix), len(matrix[0])
        self.prefix = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m):
            for j in range(n):
                self.prefix[i + 1][j + 1] = (matrix[i][j] + self.prefix[i][j + 1] +
                                              self.prefix[i + 1][j] - self.prefix[i][j])
    def sumRegion(self, r1, c1, r2, c2):
        return (self.prefix[r2 + 1][c2 + 1] - self.prefix[r1][c2 + 1] -
                self.prefix[r2 + 1][c1] + self.prefix[r1][c1])
""", "dp_bottom_up")

add("ps_cumulative_sum", """
def cumulative(arr):
    result = [arr[0]]
    for i in range(1, len(arr)):
        result.append(result[-1] + arr[i])
    return result
""", None)

add("ps_contiguous_subarrays", """
def count_subarrays(arr, k):
    count = 0
    prefix = 0
    seen = {0: 1}
    for a in arr:
        prefix += a
        count += seen.get(prefix - k, 0)
        seen[prefix] = seen.get(prefix, 0) + 1
    return count
""", None)

add("ps_not_prefix_just_sum", """
def total(nums):
    s = 0
    for x in nums:
        s += x
    return s
""", None)

add("ps_pivot_index", """
def pivot_index(nums):
    total = sum(nums)
    left_sum = 0
    for i in range(len(nums)):
        if left_sum == total - left_sum - nums[i]:
            return i
        left_sum += nums[i]
    return -1
""", None)

add("ps_product_except_self(self)", """
class Solution:
    def productExceptSelf(self, nums):
        n = len(nums)
        result = [1] * n
        left = 1
        for i in range(n):
            result[i] = left
            left *= nums[i]
        right = 1
        for i in range(n - 1, -1, -1):
            result[i] *= right
            right *= nums[i]
        return result
""", None)


# ============================================================
# GENERIC RECURSION (10 cases)
# ============================================================

add("rec_factorial", """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
""", None)

add("rec_fibonacci_no_memo", """
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
""", None)

add("rec_power(self)", """
class Solution:
    def myPow(self, x, n):
        if n == 0:
            return 1.0
        if n < 0:
            return 1.0 / self.myPow(x, -n)
        if n % 2 == 0:
            return self.myPow(x * x, n // 2)
        return x * self.myPow(x * x, n // 2)
""", None)

add("rec_sum_list", """
def sum_list(arr, i):
    if i >= len(arr):
        return 0
    return arr[i] + sum_list(arr, i + 1)
""", None)

add("rec_string_length(self)", """
class Solution:
    def lengthOfLastWord(self, s):
        words = s.split()
        return len(words[-1]) if words else 0
""", None)

add("rec_tower_of_hanoi(self)", """
class Solution:
    def hanoi(self, n, source, target, auxiliary):
        if n == 1:
            return [(source, target)]
        moves = self.hanoi(n - 1, source, auxiliary, target)
        moves.append((source, target))
        moves.extend(self.hanoi(n - 1, auxiliary, target, source))
        return moves
""", None)

add("rec_gcd", """
def gcd(a, b):
    if b == 0:
        return a
    return gcd(b, a % b)
""", None)

add("rec_reverse_string(self)", """
class Solution:
    def reverseString(self, s):
        def helper(left, right):
            if left >= right:
                return
            s[left], s[right] = s[right], s[left]
            helper(left + 1, right - 1)
        helper(0, len(s) - 1)
""", None)

add("rec_linear_search", """
def linear_search(arr, target, i=0):
    if i >= len(arr):
        return -1
    if arr[i] == target:
        return i
    return linear_search(arr, target, i + 1)
""", None)

add("rec_count_paths(self)", """
class Solution:
    def uniquePaths(self, m, n):
        if m == 1 or n == 1:
            return 1
        return self.uniquePaths(m - 1, n) + self.uniquePaths(m, n - 1)
""", None)


# ============================================================
# ORDINARY STACK (10 cases)
# ============================================================

add("stack_valid_parens", """
def is_valid(s):
    stack = []
    mapping = {")": "(", "}": "{", "]": "["}
    for ch in s:
        if ch in mapping:
            if not stack or stack[-1] != mapping[ch]:
                return False
            stack.pop()
        else:
            stack.append(ch)
    return not stack
""", None)

add("stack_eval_rpn(self)", """
class Solution:
    def evalRPN(self, tokens):
        stack = []
        for t in tokens:
            if t in "+-*/":
                b, a = stack.pop(), stack.pop()
                if t == "+":
                    stack.append(a + b)
                elif t == "-":
                    stack.append(a - b)
                elif t == "*":
                    stack.append(a * b)
                else:
                    stack.append(int(a / b))
            else:
                stack.append(int(t))
        return stack[0]
""", None)

add("stack_min_stack(self)", """
class MinStack:
    def __init__(self):
        self.s = []
        self.mins = []
    def push(self, val):
        self.s.append(val)
        if not self.mins or val <= self.mins[-1]:
            self.mins.append(val)
    def pop(self):
        val = self.s.pop()
        if val == self.mins[-1]:
            self.mins.pop()
    def top(self):
        return self.s[-1]
    def getMin(self):
        return self.mins[-1]
""", None)

add("stack_stock_span(self)", """
class StockSpanner:
    def __init__(self):
        self.stack = []
    def next(self, price):
        span = 1
        while self.stack and self.stack[-1][0] <= price:
            span += self.stack.pop()[1]
        self.stack.append((price, span))
        return span
""", None)

add("stack_nested_iterator(self)", """
class NestedIterator:
    def __init__(self, nestedList):
        self.stack = list(reversed(nestedList))
    def next(self):
        return self.hasNext() and self._pop().getInteger()
    def hasNext(self):
        while self.stack:
            top = self.stack[-1]
            if top.isInteger():
                return True
            self.stack.pop()
            self.stack.extend(reversed(top.getList()))
        return False
""", None)

add("stack_implement_queue(self)", """
class MyQueue:
    def __init__(self):
        self.in_stack = []
        self.out_stack = []
    def push(self, x):
        self.in_stack.append(x)
    def pop(self):
        self.peek()
        return self.out_stack.pop()
    def peek(self):
        if not self.out_stack:
            while self.in_stack:
                self.out_stack.append(self.in_stack.pop())
        return self.out_stack[-1]
    def empty(self):
        return not self.in_stack and not self.out_stack
""", None)

add("stack_balanced_parens(self)", """
class Solution:
    def isValid(self, s):
        stack = []
        pairs = {")": "(", "}": "{", "]": "["}
        for ch in s:
            if ch in pairs:
                if not stack or stack[-1] != pairs[ch]:
                    return False
                stack.pop()
            else:
                stack.append(ch)
        return len(stack) == 0
""", None)

add("stack_browser_history(self)", """
class BrowserHistory:
    def __init__(self, homepage):
        self.stack = [homepage]
        self.pos = 0
    def visit(self, url):
        self.stack = self.stack[:self.pos + 1]
        self.stack.append(url)
        self.pos += 1
    def back(self, steps):
        self.pos = max(0, self.pos - steps)
        return self.stack[self.pos]
    def forward(self, steps):
        self.pos = min(len(self.stack) - 1, self.pos + steps)
        return self.stack[self.pos]
""", None)

add("stack_baseball(self)", """
def cal_points(ops):
    stack = []
    for op in ops:
        if op == "+":
            stack.append(stack[-1] + stack[-2])
        elif op == "D":
            stack.append(2 * stack[-1])
        elif op == "C":
            stack.pop()
        else:
            stack.append(int(op))
    return sum(stack)
""", None)

add("stack_remove_duplicates(self)", """
class Solution:
    def removeDuplicates(self, s):
        stack = []
        for ch in s:
            if stack and stack[-1] == ch:
                stack.pop()
            else:
                stack.append(ch)
        return "".join(stack)
""", None)


# ============================================================
# HEAP (10 cases)
# ============================================================

add("heap_kth_largest(self)", """
class Solution:
    def findKthLargest(self, nums, k):
        import heapq
        return heapq.nlargest(k, nums)[-1]
""", None)

add("heap_top_k(self)", """
def top_k_frequent(nums, k):
    from collections import Counter
    import heapq
    return [x for x, _ in heapq.nlargest(k, Counter(nums).items(), key=lambda x: x[1])]
""", None)

add("heap_merge_k_sorted(self)", """
class Solution:
    def mergeKLists(self, lists):
        import heapq
        heap = []
        for i, l in enumerate(lists):
            if l:
                heapq.heappush(heap, (l.val, i, l))
        dummy = ListNode(0)
        curr = dummy
        while heap:
            val, i, node = heapq.heappop(heap)
            curr.next = node
            curr = curr.next
            if node.next:
                heapq.heappush(heap, (node.next.val, i, node.next))
        return dummy.next
""", None)

add("heap_median_finder(self)", """
class MedianFinder:
    def __init__(self):
        import heapq
        self.lo = []
        self.hi = []
    def addNum(self, num):
        import heapq
        heapq.heappush(self.lo, -num)
        heapq.heappush(self.hi, -heapq.heappop(self.lo))
        if len(self.hi) > len(self.lo):
            heapq.heappush(self.lo, -heapq.heappop(self.hi))
    def findMedian(self):
        if len(self.lo) > len(self.hi):
            return -self.lo[0]
        return (-self.lo[0] + self.hi[0]) / 2
""", None)

add("heap_last_stone(self)", """
class Solution:
    def lastStoneWeight(self, stones):
        import heapq
        stones = [-s for s in stones]
        heapq.heapify(stones)
        while len(stones) > 1:
            first = -heapq.heappop(stones)
            second = -heapq.heappop(stones)
            if first != second:
                heapq.heappush(stones, -(first - second))
        return -stones[0] if stones else 0
""", None)

add("heap_task_scheduler(self)", """
class Solution:
    def leastInterval(self, tasks, n):
        from collections import Counter
        import heapq
        counts = Counter(tasks)
        heap = [-c for c in counts.values()]
        heapq.heapify(heap)
        time = 0
        while heap:
            cycle = []
            for _ in range(n + 1):
                if heap:
                    cycle.append(heapq.heappop(heap))
            for cnt in cycle:
                if cnt + 1 < 0:
                    heapq.heappush(heap, cnt + 1)
            time += n + 1 if heap else len(cycle)
        return time
""", None)

add("heap_k_closest(self)", """
def k_closest(points, k):
    import heapq
    return heapq.nsmallest(k, points, key=lambda p: p[0]**2 + p[1]**2)
""", None)

add("heap_reorganize_string(self)", """
class Solution:
    def reorganizeString(self, s):
        from collections import Counter
        import heapq
        count = Counter(s)
        heap = [(-c, ch) for ch, c in count.items()]
        heapq.heapify(heap)
        result = []
        while heap:
            cnt, ch = heapq.heappop(heap)
            if not result or result[-1] != ch:
                result.append(ch)
                if cnt + 1 < 0:
                    heapq.heappush(heap, (cnt + 1, ch))
            else:
                if not heap:
                    return ""
                cnt2, ch2 = heapq.heappop(heap)
                result.append(ch2)
                if cnt2 + 1 < 0:
                    heapq.heappush(heap, (cnt2 + 1, ch2))
                heapq.heappush(heap, (cnt, ch))
        return "".join(result)
""", None)

add("heap_relative_ranks(self)", """
def find_relative_ranks(nums):
    import heapq
    sorted_nums = sorted(enumerate(nums), key=lambda x: -x[1])
    result = [""] * len(nums)
    for rank, (idx, _) in enumerate(sorted_nums):
        if rank == 0:
            result[idx] = "Gold Medal"
        elif rank == 1:
            result[idx] = "Silver Medal"
        elif rank == 2:
            result[idx] = "Bronze Medal"
        else:
            result[idx] = str(rank + 1)
    return result
""", None)


# ============================================================
# GREEDY (10 cases)
# ============================================================

add("greedy_activity_selection", """
def activity_selection(activities):
    activities.sort(key=lambda x: x[1])
    result = [activities[0]]
    for act in activities[1:]:
        if act[0] >= result[-1][1]:
            result.append(act)
    return result
""", None)

add("greedy_jump_game(self)", """
class Solution:
    def canJump(self, nums):
        max_reach = 0
        for i, jump in enumerate(nums):
            if i > max_reach:
                return False
            max_reach = max(max_reach, i + jump)
        return True
""", None)

add("greedy_best_time_to_buy(self)", """
class Solution:
    def maxProfit(self, prices):
        profit = 0
        for i in range(1, len(prices)):
            if prices[i] > prices[i - 1]:
                profit += prices[i] - prices[i - 1]
        return profit
""", None)

add("greedy_gas_station(self)", """
def can_complete_circuit(gas, cost):
    total_tank = 0
    curr_tank = 0
    start = 0
    for i in range(len(gas)):
        diff = gas[i] - cost[i]
        total_tank += diff
        curr_tank += diff
        if curr_tank < 0:
            start = i + 1
            curr_tank = 0
    return start if total_tank >= 0 else -1
""", None)

add("greedy_partition_labels(self)", """
class Solution:
    def partitionLabels(self, s):
        last = {c: i for i, c in enumerate(s)}
        result = []
        start = end = 0
        for i, c in enumerate(s):
            end = max(end, last[c])
            if i == end:
                result.append(end - start + 1)
                start = end + 1
        return result
""", None)

add("greedy_merge_intervals(self)", """
class Solution:
    def merge(self, intervals):
        intervals.sort()
        result = [intervals[0]]
        for start, end in intervals[1:]:
            if start <= result[-1][1]:
                result[-1][1] = max(result[-1][1], end)
            else:
                result.append([start, end])
        return result
""", None)

add("greedy_climb_stairs_not_dp(self)", """
class Solution:
    def minCostClimbingStairs(self, cost):
        n = len(cost)
        dp = [0] * (n + 1)
        for i in range(2, n + 1):
            dp[i] = min(dp[i-1] + cost[i-1], dp[i-2] + cost[i-2])
        return dp[n]
""", "dp_bottom_up")

add("greedy_assign_cookies(self)", """
class Solution:
    def findContentChildren(self, g, s):
        g.sort()
        s.sort()
        child = cookie = 0
        while child < len(g) and cookie < len(s):
            if s[cookie] >= g[child]:
                child += 1
            cookie += 1
        return child
""", None)

add("greedy_lecture_rooms(self)", """
def min_meeting_rooms(intervals):
    intervals.sort()
    rooms = []
    import heapq
    for start, end in intervals:
        if rooms and rooms[0] <= start:
            heapq.heapreplace(rooms, end)
        else:
            heapq.heappush(rooms, end)
    return len(rooms)
""", None)

add("greedy_not_greedy_array(self)", """
def find_max(arr):
    mx = arr[0]
    for i in range(1, len(arr)):
        if arr[i] > mx:
            mx = arr[i]
    return mx
""", None)


# ============================================================
# HASH MAP USAGE (10 cases)
# ============================================================

add("hash_two_sum(self)", """
class Solution:
    def twoSum(self, nums, target):
        seen = {}
        for i, num in enumerate(nums):
            complement = target - num
            if complement in seen:
                return [seen[complement], i]
            seen[num] = i
        return []
""", None)

add("hash_group_anagrams(self)", """
class Solution:
    def groupAnagrams(self, strs):
        from collections import defaultdict
        groups = defaultdict(list)
        for s in strs:
            key = tuple(sorted(s))
            groups[key].append(s)
        return list(groups.values())
""", None)

add("hash_contains_duplicate(self)", """
class Solution:
    def containsDuplicate(self, nums):
        return len(nums) != len(set(nums))
""", None)

add("hash_longest_consecutive(self)", """
class Solution:
    def longestConsecutive(self, nums):
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
""", None)

add("hash_ransom_note(self)", """
class Solution:
    def canConstruct(self, ransomNote, magazine):
        from collections import Counter
        return not Counter(ransomNote) - Counter(magazine)
""", None)

add("hash_isomorphic_strings(self)", """
class Solution:
    def isIsomorphic(self, s, t):
        if len(s) != len(t):
            return False
        s_to_t, t_to_s = {}, {}
        for a, b in zip(s, t):
            if a in s_to_t and s_to_t[a] != b:
                return False
            if b in t_to_s and t_to_s[b] != a:
                return False
            s_to_t[a] = b
            t_to_s[b] = a
        return True
""", None)

add("hash_valid_sudoku(self)", """
class Solution:
    def isValidSudoku(self, board):
        rows = [set() for _ in range(9)]
        cols = [set() for _ in range(9)]
        boxes = [set() for _ in range(9)]
        for i in range(9):
            for j in range(9):
                val = board[i][j]
                if val == ".":
                    continue
                box_idx = (i // 3) * 3 + j // 3
                if val in rows[i] or val in cols[j] or val in boxes[box_idx]:
                    return False
                rows[i].add(val)
                cols[j].add(val)
                boxes[box_idx].add(val)
        return True
""", None)

add("hash_subarray_sum_k(self)", """
class Solution:
    def subarraySum(self, nums, k):
        count = 0
        prefix = 0
        seen = {0: 1}
        for num in nums:
            prefix += num
            count += seen.get(prefix - k, 0)
            seen[prefix] = seen.get(prefix, 0) + 1
        return count
""", None)

add("hash_minimum_window(self)", """
class Solution:
    def minWindow(self, s, t):
        from collections import Counter
        need = Counter(t)
        missing = len(t)
        left = 0
        start, end = 0, float('inf')
        for right in range(len(s)):
            if need[s[right]] > 0:
                missing -= 1
            need[s[right]] -= 1
            while missing == 0:
                if right - left < end - start:
                    start, end = left, right
                need[s[left]] += 1
                if need[s[left]] > 0:
                    missing += 1
                left += 1
        return s[start:end + 1] if end < float('inf') else ""
""", "sliding_window")

add("hash_frequency_sort(self)", """
class Solution:
    def frequencySort(self, s):
        from collections import Counter
        count = Counter(s)
        return "".join(ch * freq for ch, freq in count.most_common())
""", None)


# ============================================================
# ARRAY TRAVERSAL (10 cases)
# ============================================================

add("arr_max_subarray(self)", """
class Solution:
    def maxSubArray(self, nums):
        max_sum = curr_sum = nums[0]
        for num in nums[1:]:
            curr_sum = max(num, curr_sum + num)
            max_sum = max(max_sum, curr_sum)
        return max_sum
""", None)

add("arr_best_time_buy(self)", """
class Solution:
    def maxProfit(self, prices):
        min_price = float('inf')
        max_profit = 0
        for price in prices:
            min_price = min(min_price, price)
            max_profit = max(max_profit, price - min_price)
        return max_profit
""", None)

add("arr_merge_sorted(self)", """
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
""", None)

add("arr_remove_duplicates(self)", """
class Solution:
    def removeDuplicates(self, nums):
        if not nums:
            return 0
        slow = 0
        for fast in range(1, len(nums)):
            if nums[fast] != nums[slow]:
                slow += 1
                nums[slow] = nums[fast]
        return slow + 1
""", None)

add("arr_product_except_self(self)", """
class Solution:
    def productExceptSelf(self, nums):
        n = len(nums)
        result = [1] * n
        left = 1
        for i in range(n):
            result[i] = left
            left *= nums[i]
        right = 1
        for i in range(n - 1, -1, -1):
            result[i] *= right
            right *= nums[i]
        return result
""", None)

add("arr_rotate_array(self)", """
class Solution:
    def rotate(self, nums, k):
        n = len(nums)
        k = k % n
        nums[:] = nums[-k:] + nums[:-k]
""", None)

add("arr_find_disappeared(self)", """
class Solution:
    def findDisappearedNumbers(self, nums):
        num_set = set(nums)
        return [i for i in range(1, len(nums) + 1) if i not in num_set]
""", None)

add("arr_contains_nearby_almost(self)", """
class Solution:
    def containsNearbyAlmostDuplicate(self, nums, k, t):
        if t == 0 and len(nums) == len(set(nums)):
            return False
        for i in range(len(nums)):
            for j in range(i + 1, min(i + k + 1, len(nums))):
                if abs(nums[i] - nums[j]) <= t:
                    return True
        return False
""", None)

add("arr_sort_colors(self)", """
class Solution:
    def sortColors(self, nums):
        low, mid, high = 0, 0, len(nums) - 1
        while mid <= high:
            if nums[mid] == 0:
                nums[low], nums[mid] = nums[mid], nums[low]
                low += 1
                mid += 1
            elif nums[mid] == 1:
                mid += 1
            else:
                nums[mid], nums[high] = nums[high], nums[mid]
                high -= 1
""", None)

add("arr_next_permutation(self)", """
class Solution:
    def nextPermutation(self, nums):
        n = len(nums)
        i = n - 2
        while i >= 0 and nums[i] >= nums[i + 1]:
            i -= 1
        if i >= 0:
            j = n - 1
            while nums[j] <= nums[i]:
                j -= 1
            nums[i], nums[j] = nums[j], nums[i]
        nums[i + 1:] = reversed(nums[i + 1:])
""", None)


# ============================================================
# HARD NEGATIVES (20 cases)
# ============================================================

add("neg_bfs_no_visited", """
from collections import deque

def traverse_without_visited(graph, start):
    queue = deque([start])
    result = []
    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbor in graph.get(node, []):
            queue.append(neighbor)
    return result
""", None)

add("neg_dfs_no_state_restore", """
def tree_depth(root):
    if not root:
        return 0
    left = tree_depth(root.left)
    right = tree_depth(root.right)
    return 1 + max(left, right)
""", None)

add("neg_stack_not_monotonic", """
def eval_rpn(tokens):
    stack = []
    for t in tokens:
        if t in "+-*/":
            b, a = stack.pop(), stack.pop()
            if t == "+":
                stack.append(a + b)
            elif t == "-":
                stack.append(a - b)
            elif t == "*":
                stack.append(a * b)
            else:
                stack.append(int(a / b))
        else:
            stack.append(int(t))
    return stack[0]
""", None)

add("neg_linked_not_manipulation", """
def sum_linked_list(head):
    total = 0
    while head:
        total += head.val
        head = head.next
    return total
""", None)

add("neg_dp_no_memo(self)", """
class Solution:
    def climbStairs(self, n):
        if n <= 2:
            return n
        return self.climbStairs(n - 1) + self.climbStairs(n - 2)
""", None)

add("neg_heap_not_strategy(self)", """
class Solution:
    def findKthLargest(self, nums, k):
        import heapq
        return heapq.nlargest(k, nums)[-1]
""", None)

add("neg_greedy_not_strategy(self)", """
def can_jump(nums):
    max_reach = 0
    for i, jump in enumerate(nums):
        if i > max_reach:
            return False
        max_reach = max(max_reach, i + jump)
    return True
""", None)

add("neg_hash_not_strategy(self)", """
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        if target - num in seen:
            return [seen[target - num], i]
        seen[num] = i
    return []
""", None)

add("neg_sorting_not_dp", """
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
""", None)

add("neg_linear_scan_not_bs", """
def find_element(arr, target):
    for i in range(len(arr)):
        if arr[i] == target:
            return i
    return -1
""", None)

add("neg_hash_not_binary_search", """
def contains_nearby_duplicate(nums, k):
    seen = set()
    for i in range(len(nums)):
        if nums[i] in seen:
            return True
        seen.add(nums[i])
        if len(seen) > k:
            seen.remove(nums[i - k])
    return False
""", None)

add("neg_two_pointer_not_opposite(self)", """
class Solution:
    def removeElement(self, nums, val):
        slow = 0
        for fast in range(len(nums)):
            if nums[fast] != val:
                nums[slow] = nums[fast]
                slow += 1
        return slow
""", None)

add("neg_dp_no_lookback", """
def running_sum(nums):
    result = [nums[0]]
    for i in range(1, len(nums)):
        result.append(result[-1] + nums[i])
    return result
""", None)

add("neg_backtrack_no_recursion", """
def subsets_iterative(nums):
    result = [[]]
    for num in nums:
        result.extend([subset + [num] for subset in result])
    return result
""", None)

add("neg_bfs_tree_no_queue(self)", """
class Solution:
    def levelOrder(self, root):
        if not root:
            return []
        result = []
        def dfs(node, level):
            if not node:
                return
            if level == len(result):
                result.append([])
            result[level].append(node.val)
            dfs(node.left, level + 1)
            dfs(node.right, level + 1)
        dfs(root, 0)
        return result
""", None)

add("neg_union_find_parent_only", """
def is_connected(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    visited = set()
    def dfs(node):
        visited.add(node)
        for neighbor in adj[node]:
            if neighbor not in visited:
                dfs(neighbor)
    dfs(0)
    return len(visited) == n
""", None)

add("neg_monotonic_not_stack", """
def increasing(arr):
    for i in range(len(arr) - 1):
        if arr[i] >= arr[i + 1]:
            return False
    return True
""", None)

add("neg_sliding_not_window(self)", """
class Solution:
    def maxArea(self, height):
        left, right = 0, len(height) - 1
        max_w = 0
        while left < right:
            w = min(height[left], height[right]) * (right - left)
            max_w = max(max_w, w)
            if height[left] < height[right]:
                left += 1
            else:
                right -= 1
        return max_w
""", "two_pointers_opposite")

add("neg_queue_not_bfs", """
from collections import deque

def level_average(root):
    if not root:
        return []
    result = []
    queue = deque([root])
    while queue:
        level_sum = 0
        level_size = len(queue)
        for _ in range(level_size):
            node = queue.popleft()
            level_sum += node.val
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        result.append(level_sum / level_size)
    return result
""", "bfs_shortest_path")

add("neg_mixed_not_any_strategy(self)", """
class Solution:
    def isValid(self, s):
        while "()" in s or "[]" in s or "{}" in s:
            s = s.replace("()", "").replace("[]", "").replace("{}", "")
        return len(s) == 0
""", None)


# ============================================================
# Additional edge cases
# ============================================================

add("edge_empty_code", "", None)
add("edge_single_return", "return 42", None)
add("edge_no_functions", "x = 5\ny = x + 1", None)
add("edge_nested_classes", """
class Outer:
    class Inner:
        def method(self):
            return 42
""", None)
add("edge_decorators", """
@decorator
def my_func():
    return 42
""", None)
