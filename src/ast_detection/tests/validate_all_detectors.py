"""Phase 3C.2.3A — Comprehensive validation of all 15 detectors against LeetCode solution patterns.

Tests each detector against 12-28 positive and 8-20 negative examples
derived from real LeetCode Python solutions. Reports true/false
positives/negatives, confidence distribution, and detector overlap.

Usage:
    python -m src.ast_detection.tests.validate_all_detectors
"""

import ast
import itertools
from collections import defaultdict

# Batch 1
from src.ast_detection.detectors.hash_map_lookup import HashMapLookupDetector
from src.ast_detection.detectors.array_traversal import ArrayTraversalDetector
from src.ast_detection.detectors.sorting import SortingDetector
from src.ast_detection.detectors.brute_force import BruteForceDetector
from src.ast_detection.detectors.frequency_counting import FrequencyCountingDetector
# Batch 2
from src.ast_detection.detectors.two_pointers_same import TwoPointersSameDetector
from src.ast_detection.detectors.two_pointers_opposite import TwoPointersOppositeDetector
from src.ast_detection.detectors.sliding_window_fixed import SlidingWindowFixedDetector
from src.ast_detection.detectors.sliding_window_variable import SlidingWindowVariableDetector
from src.ast_detection.detectors.prefix_sum import PrefixSumDetector
# Batch 3
from src.ast_detection.detectors.binary_search_classic import BinarySearchClassicDetector
from src.ast_detection.detectors.binary_search_answer import BinarySearchAnswerDetector
from src.ast_detection.detectors.heap_priority_queue import HeapPriorityQueueDetector
from src.ast_detection.detectors.monotonic_stack import MonotonicStackDetector
from src.ast_detection.detectors.monotonic_queue import MonotonicQueueDetector

# Re-export Batch 1 data from test_validation for reuse
from src.ast_detection.tests.test_validation import (
    HASH_MAP_LOOKUP_POSITIVE,
    HASH_MAP_LOOKUP_NEGATIVE,
    ARRAY_TRAVERSAL_POSITIVE,
    ARRAY_TRAVERSAL_NEGATIVE,
    SORTING_POSITIVE,
    SORTING_NEGATIVE,
    BRUTE_FORCE_POSITIVE,
    BRUTE_FORCE_NEGATIVE,
    FREQUENCY_COUNTING_POSITIVE,
    FREQUENCY_COUNTING_NEGATIVE,
)


# ===================================================================
# two_pointers_same (slow/fast pointers, offset pointers)
# ===================================================================

TWO_POINTERS_SAME_POSITIVE = [
    # Linked List Cycle (LeetCode 141)
    ("ll_cycle", """
slow = fast = head
while fast and fast.next:
    slow = slow.next
    fast = fast.next.next
    if slow == fast:
        return True
return False
"""),
    # Middle of Linked List (LeetCode 876)
    ("middle_of_ll", """
slow = fast = head
while fast and fast.next:
    slow = slow.next
    fast = fast.next.next
return slow
"""),
    # Linked List Cycle II (LeetCode 142)
    ("ll_cycle_ii", """
slow = fast = head
while fast and fast.next:
    slow = slow.next
    fast = fast.next.next
    if slow == fast:
        slow = head
        while slow != fast:
            slow = slow.next
            fast = fast.next
        return slow
return None
"""),
    # Remove Nth Node From End (LeetCode 19)
    ("remove_nth_end", """
dummy = ListNode(0)
dummy.next = head
fast = slow = dummy
for _ in range(n):
    fast = fast.next
while fast.next:
    fast = fast.next
    slow = slow.next
slow.next = slow.next.next
return dummy.next
"""),
    # Happy Number (LeetCode 202)
    ("happy_number_ptrs", """
slow = fast = n
while True:
    slow = sum(int(d)**2 for d in str(slow))
    fast = sum(int(d)**2 for d in str(fast))
    fast = sum(int(d)**2 for d in str(fast))
    if slow == fast:
        break
return slow == 1
"""),
    # Intersection of Two Linked Lists (LeetCode 160)
    ("intersection_ll", """
pA, pB = headA, headB
while pA != pB:
    pA = pA.next if pA else headB
    pB = pB.next if pB else headA
return pA
"""),
    # Find Duplicate Number (LeetCode 287)
    ("find_duplicate_ptrs", """
slow = fast = nums[0]
while True:
    slow = nums[slow]
    fast = nums[nums[fast]]
    if slow == fast:
        break
slow = nums[0]
while slow != fast:
    slow = nums[slow]
    fast = nums[fast]
return slow
"""),
    # Slow/fast with array indices (generic)
    ("slow_fast_differential", """
slow = 0
fast = 0
while fast < len(arr):
    if arr[slow] != arr[fast]:
        slow += 1
        arr[slow] = arr[fast]
    fast += 1
return slow + 1
"""),
    # Find kth from end via offset pointers
    ("kth_from_end", """
fast = slow = head
for _ in range(k):
    fast = fast.next
while fast:
    fast = fast.next
    slow = slow.next
return slow.val
"""),
    # Delete Middle Node (offset + .next)
    ("delete_middle", """
slow = fast = head
prev = None
while fast and fast.next:
    prev = slow
    slow = slow.next
    fast = fast.next.next
prev.next = slow.next
return head
"""),
    # Slow pointer with conditional reset
    ("slow_reset_pattern", """
slow = fast = 0
while fast < len(nums):
    if condition:
        slow += 1
    else:
        slow = 0
    fast += 1
"""),
    # Reverse linked list (uses .next attributes, same-direction traversal)
    ("reverse_ll", """
prev = None
curr = head
while curr:
    next_node = curr.next
    curr.next = prev
    prev = curr
    curr = next_node
return prev
"""),
]

TWO_POINTERS_SAME_NEGATIVE = [
    ("no_loop", "x = 1"),
    ("single_pointer_while", """
i = 0
while i < 10:
    print(i)
    i += 1
"""),
    ("same_increment", """
i = 0
j = 1
while i < 10:
    i += 1
    j += 1
"""),
    ("for_loop_only", "for i in range(10):\n    print(i)"),
    ("no_differential", """
i = 0
while i < len(arr):
    print(arr[i])
    i += 1
"""),
    ("standard_for_loop", """
for i in range(len(arr)):
    print(arr[i])
"""),
    ("converging_pointers", """
l, r = 0, n - 1
while l < r:
    if arr[l] < arr[r]:
        l += 1
    else:
        r -= 1
"""),
    ("deque_fifo", """
from collections import deque
q = deque()
q.append(1)
x = q.popleft()
"""),
]


# ===================================================================
# two_pointers_opposite (converging pointers)
# ===================================================================

TWO_POINTERS_OPPOSITE_POSITIVE = [
    # Two Sum II (LeetCode 167)
    ("two_sum_sorted", """
left, right = 0, len(numbers) - 1
while left < right:
    total = numbers[left] + numbers[right]
    if total == target:
        return [left + 1, right + 1]
    elif total < target:
        left += 1
    else:
        right -= 1
"""),
    # Container With Most Water (LeetCode 11)
    ("most_water", """
left, right = 0, len(height) - 1
max_area = 0
while left < right:
    area = min(height[left], height[right]) * (right - left)
    max_area = max(max_area, area)
    if height[left] < height[right]:
        left += 1
    else:
        right -= 1
return max_area
"""),
    # 3Sum (LeetCode 15)
    ("three_sum", """
nums.sort()
result = []
for i in range(len(nums) - 2):
    if i > 0 and nums[i] == nums[i - 1]:
        continue
    l, r = i + 1, len(nums) - 1
    while l < r:
        total = nums[i] + nums[l] + nums[r]
        if total < 0:
            l += 1
        elif total > 0:
            r -= 1
        else:
            result.append([nums[i], nums[l], nums[r]])
            while l < r and nums[l] == nums[l + 1]:
                l += 1
            while l < r and nums[r] == nums[r - 1]:
                r -= 1
            l += 1
            r -= 1
return result
"""),
    # Valid Palindrome (LeetCode 125)
    ("valid_palindrome", """
l, r = 0, len(s) - 1
while l < r:
    while l < r and not s[l].isalnum():
        l += 1
    while l < r and not s[r].isalnum():
        r -= 1
    if s[l].lower() != s[r].lower():
        return False
    l += 1
    r -= 1
return True
"""),
    # Reverse String (LeetCode 344)
    ("reverse_string", """
l, r = 0, len(s) - 1
while l < r:
    s[l], s[r] = s[r], s[l]
    l += 1
    r -= 1
"""),
    # Trapping Rain Water - two pointer approach (LeetCode 42)
    ("trap_rain_water", """
l, r = 0, len(height) - 1
left_max = right_max = 0
water = 0
while l < r:
    if height[l] < height[r]:
        if height[l] >= left_max:
            left_max = height[l]
        else:
            water += left_max - height[l]
        l += 1
    else:
        if height[r] >= right_max:
            right_max = height[r]
        else:
            water += right_max - height[r]
        r -= 1
return water
"""),
    # 3Sum Closest (LeetCode 16)
    ("three_sum_closest", """
nums.sort()
closest = float('inf')
for i in range(len(nums) - 2):
    l, r = i + 1, len(nums) - 1
    while l < r:
        total = nums[i] + nums[l] + nums[r]
        if abs(total - target) < abs(closest - target):
            closest = total
        if total < target:
            l += 1
        elif total > target:
            r -= 1
        else:
            return target
return closest
"""),
    # Two-sum sorted variant with different var names
    ("two_sum_lo_hi", """
lo, hi = 0, len(arr) - 1
while lo < hi:
    s = arr[lo] + arr[hi]
    if s == t:
        return [lo, hi]
    if s < t:
        lo += 1
    else:
        hi -= 1
"""),
    # 4Sum - nested converging
    ("four_sum", """
nums.sort()
result = []
for i in range(len(nums) - 3):
    for j in range(i + 1, len(nums) - 2):
        l, r = j + 1, len(nums) - 1
        while l < r:
            total = nums[i] + nums[j] + nums[l] + nums[r]
            if total < target:
                l += 1
            elif total > target:
                r -= 1
            else:
                result.append([nums[i], nums[j], nums[l], nums[r]])
                l += 1
                r -= 1
return result
"""),
]

TWO_POINTERS_OPPOSITE_NEGATIVE = [
    ("no_loop", "x = 1"),
    ("same_direction_while", """
i = 0
j = 1
while i < len(arr):
    print(arr[i], arr[j])
    i += 1
    j += 1
"""),
    ("single_pointer_while", """
i = 0
while i < len(arr):
    print(arr[i])
    i += 1
"""),
    ("for_loop", "for i in range(10):\n    print(i)"),
    ("for_loop_range", """
for i in range(len(arr)):
    print(arr[i])
"""),
    ("nested_loops_not_pointers", """
for i in range(n):
    for j in range(i+1, n):
        if arr[i] + arr[j] == target:
            return [i, j]
"""),
    ("both_pointers_same_dir", """
slow = fast = 0
while fast < len(arr):
    if condition:
        slow += 1
    fast += 1
"""),
]


# ===================================================================
# sliding_window_fixed (fixed-size window)
# ===================================================================

SLIDING_WINDOW_FIXED_POSITIVE = [
    # Maximum Average Subarray I (LeetCode 643)
    ("max_avg_subarray", """
window_sum = 0
left = 0
max_avg = float('-inf')
for right in range(len(nums)):
    window_sum += nums[right]
    if right >= k - 1:
        max_avg = max(max_avg, window_sum / k)
        window_sum -= nums[left]
        left += 1
return max_avg
"""),
    # Find All Anagrams in String (LeetCode 438)
    ("find_anagrams", """
left = 0
result = []
window_counts = {}
for right in range(len(s)):
    window_counts[s[right]] = window_counts.get(s[right], 0) + 1
    if right >= len(p) - 1:
        if window_counts == p_counts:
            result.append(left)
        window_counts[s[left]] -= 1
        if window_counts[s[left]] == 0:
            del window_counts[s[left]]
        left += 1
return result
"""),
    # Permutation in String (LeetCode 567)
    ("permutation_in_string", """
left = 0
window_counts = {}
for right in range(len(s2)):
    window_counts[s2[right]] = window_counts.get(s2[right], 0) + 1
    if right >= len(s1) - 1:
        if window_counts == s1_counts:
            return True
        window_counts[s2[left]] -= 1
        if window_counts[s2[left]] == 0:
            del window_counts[s2[left]]
        left += 1
return False
"""),
    # Max Sum of Subarray of Size K (generic)
    ("max_sum_subarray_k", """
window_sum = 0
left = 0
max_sum = 0
for right in range(len(arr)):
    window_sum += arr[right]
    if right >= k - 1:
        max_sum = max(max_sum, window_sum)
        window_sum -= arr[left]
        left += 1
return max_sum
"""),
    # Number of Sub-arrays of Size K (LeetCode 1343)
    ("num_subarrays_k", """
window_sum = 0
left = 0
count = 0
for right in range(len(arr)):
    window_sum += arr[right]
    if right >= k - 1:
        if window_sum / k >= threshold:
            count += 1
        window_sum -= arr[left]
        left += 1
return count
"""),
    # Count Occurrences of Anagrams
    ("count_anagrams", """
left = 0
count = 0
window_counts = {}
for right in range(len(text)):
    window_counts[text[right]] = window_counts.get(text[right], 0) + 1
    if right >= len(pattern) - 1:
        if all(window_counts.get(ch, 0) == pattern_counts[ch] for ch in pattern_counts):
            count += 1
        window_counts[text[left]] -= 1
        if window_counts[text[left]] == 0:
            del window_counts[text[left]]
        left += 1
return count
"""),
    # Fixed window with set storage
    ("fixed_window_set", """
left = 0
result = []
for right in range(len(nums)):
    window.add(nums[right])
    if right >= k - 1:
        result.append(len(window))
        window.remove(nums[left])
        left += 1
return result
"""),
    # Fixed window with product
    ("fixed_window_product", """
product = 1
left = 0
for right in range(len(nums)):
    product *= nums[right]
    if right >= k - 1:
        max_product = max(max_product, product)
        product //= nums[left]
        left += 1
"""),
]

SLIDING_WINDOW_FIXED_NEGATIVE = [
    ("no_loop", "x = 1"),
    ("plain_sum_no_window", """
total = 0
for num in arr:
    total += num
"""),
    ("for_loop_only", "for i in range(10):\n    print(i)"),
    ("no_boundary_check", """
window_sum = 0
for right in range(len(arr)):
    window_sum += arr[right]
"""),
    ("no_left_pointer", """
for right in range(len(arr)):
    arr[right] *= 2
"""),
    ("variable_window", """
left = 0
for right in range(len(s)):
    if s[right] in char_set:
        left = max(left, char_set[s[right]] + 1)
    char_set[s[right]] = right
"""),
    ("while_loop_only", """
i = 0
while i < n:
    print(i)
    i += 1
"""),
    ("two_sum_pattern", """
seen = {}
for i, n in enumerate(nums):
    diff = target - n
    if diff in seen:
        return [seen[diff], i]
    seen[n] = i
"""),
    ("prefix_sum_pattern", """
prefix = [0]
for num in nums:
    prefix.append(prefix[-1] + num)
"""),
]


# ===================================================================
# sliding_window_variable (variable-size window)
# ===================================================================

SLIDING_WINDOW_VARIABLE_POSITIVE = [
    # Longest Substring Without Repeating Characters (LeetCode 3)
    ("longest_substring", """
left = 0
char_set = {}
max_len = 0
for right in range(len(s)):
    if s[right] in char_set:
        left = max(left, char_set[s[right]] + 1)
    char_set[s[right]] = right
    max_len = max(max_len, right - left + 1)
return max_len
"""),
    # Minimum Window Substring (LeetCode 76)
    ("min_window_substring", """
left = 0
min_len = float('inf')
result = ""
formed = 0
for right in range(len(s)):
    if s[right] in t_counts:
        t_counts[s[right]] -= 1
        if t_counts[s[right]] >= 0:
            formed += 1
    while formed == required and left <= right:
        if right - left + 1 < min_len:
            min_len = right - left + 1
            result = s[left:right + 1]
        if s[left] in t_counts:
            t_counts[s[left]] += 1
            if t_counts[s[left]] > 0:
                formed -= 1
        left += 1
return result
"""),
    # Longest Repeating Character Replacement (LeetCode 424)
    ("longest_repeating_char", """
left = 0
max_count = 0
count = {}
for right in range(len(s)):
    count[s[right]] = count.get(s[right], 0) + 1
    max_count = max(max_count, count[s[right]])
    while (right - left + 1) - max_count > k:
        count[s[left]] -= 1
        left += 1
    max_len = max(max_len, right - left + 1)
return max_len
"""),
    # Minimum Size Subarray Sum (LeetCode 209)
    ("min_size_subarray", """
left = 0
min_len = float('inf')
window_sum = 0
for right in range(len(nums)):
    window_sum += nums[right]
    while window_sum >= target:
        min_len = min(min_len, right - left + 1)
        window_sum -= nums[left]
        left += 1
return min_len if min_len != float('inf') else 0
"""),
    # Max Consecutive Ones III (LeetCode 1004)
    ("max_consecutive_ones", """
left = 0
zero_count = 0
max_len = 0
for right in range(len(nums)):
    if nums[right] == 0:
        zero_count += 1
    while zero_count > k:
        if nums[left] == 0:
            zero_count -= 1
        left += 1
    max_len = max(max_len, right - left + 1)
return max_len
"""),
    # Longest Substring with At Most K Distinct (LeetCode 340)
    ("longest_k_distinct", """
left = 0
char_count = {}
max_len = 0
for right in range(len(s)):
    char_count[s[right]] = char_count.get(s[right], 0) + 1
    while len(char_count) > k:
        char_count[s[left]] -= 1
        if char_count[s[left]] == 0:
            del char_count[s[left]]
        left += 1
    max_len = max(max_len, right - left + 1)
return max_len
"""),
    # Subarrays with K Distinct Integers (LeetCode 992)
    ("subarrays_k_distinct", """
left = 0
count = 0
freq = {}
for right in range(len(nums)):
    freq[nums[right]] = freq.get(nums[right], 0) + 1
    while len(freq) > k:
        freq[nums[left]] -= 1
        if freq[nums[left]] == 0:
            del freq[nums[left]]
        left += 1
    count += right - left + 1
return count
"""),
    # Fruit Into Baskets (LeetCode 904)
    ("fruit_into_baskets", """
left = 0
basket = {}
max_fruit = 0
for right in range(len(fruits)):
    basket[fruits[right]] = basket.get(fruits[right], 0) + 1
    while len(basket) > 2:
        basket[fruits[left]] -= 1
        if basket[fruits[left]] == 0:
            del basket[fruits[left]]
        left += 1
    max_fruit = max(max_fruit, right - left + 1)
return max_fruit
"""),
    # Variable window with product constraint
    ("product_less_than_k", """
left = 0
product = 1
count = 0
for right in range(len(nums)):
    product *= nums[right]
    while product >= k and left <= right:
        product //= nums[left]
        left += 1
    count += right - left + 1
return count
"""),
]

SLIDING_WINDOW_VARIABLE_NEGATIVE = [
    ("no_loop", "x = 1"),
    ("for_loop_no_left", """
for right in range(len(arr)):
    print(arr[right])
"""),
    ("for_loop_only", "for i in range(10):\n    print(i)"),
    ("fixed_window_pattern", """
left = 0
for right in range(len(arr)):
    if right >= k - 1:
        window_sum -= arr[left]
        left += 1
"""),
    ("left_not_zero", """
left = 5
for right in range(len(arr)):
    arr[right] += 1
"""),
    ("no_window_shrink", """
left = 0
for right in range(n):
    arr[right] *= 2
"""),
    ("two_sum", """
seen = {}
for i, n in enumerate(nums):
    diff = target - n
    if diff in seen:
        return [seen[diff], i]
    seen[n] = i
"""),
    ("prefix_sum", """
prefix = 0
counts = {0: 1}
for num in nums:
    prefix += num
    if prefix - k in counts:
        result += counts[prefix - k]
    counts[prefix] = counts.get(prefix, 0) + 1
"""),
    ("concat_strings", """
result = ""
for s in strings:
    result += s
"""),
]


# ===================================================================
# prefix_sum (running sum, subarray sum)
# ===================================================================

PREFIX_SUM_POSITIVE = [
    # Range Sum Query (LeetCode 303)
    ("range_sum_query", """
prefix = [0]
for num in nums:
    prefix.append(prefix[-1] + num)
return prefix[right + 1] - prefix[left]
"""),
    # Subarray Sum Equals K (LeetCode 560)
    ("subarray_sum_k", """
running_sum = 0
count = 0
prefix_sums = {0: 1}
for num in nums:
    running_sum += num
    if running_sum - k in prefix_sums:
        count += prefix_sums[running_sum - k]
    prefix_sums[running_sum] = prefix_sums.get(running_sum, 0) + 1
return count
"""),
    # Running Sum of 1d Array (LeetCode 1480)
    ("running_sum_1d", """
result = []
total = 0
for num in nums:
    total += num
    result.append(total)
return result
"""),
    # Find Pivot Index (LeetCode 724)
    ("pivot_index", """
total = sum(nums)
left_sum = 0
for i, num in enumerate(nums):
    if left_sum == total - left_sum - num:
        return i
    left_sum += num
return -1
"""),
    # Contiguous Array (LeetCode 525)
    ("contiguous_array", """
count = 0
first_occurrence = {0: -1}
max_len = 0
for i, num in enumerate(nums):
    count += 1 if num == 1 else -1
    if count in first_occurrence:
        max_len = max(max_len, i - first_occurrence[count])
    else:
        first_occurrence[count] = i
return max_len
"""),
    # Maximum Size Subarray Sum Equals k (LeetCode 325)
    ("max_size_subarray_k", """
prefix_sum = 0
max_len = 0
sum_index = {0: -1}
for i, num in enumerate(nums):
    prefix_sum += num
    if prefix_sum - k in sum_index:
        max_len = max(max_len, i - sum_index[prefix_sum - k])
    if prefix_sum not in sum_index:
        sum_index[prefix_sum] = i
return max_len
"""),
    # Product of Array Except Self (LeetCode 238) - prefix/suffix variant
    ("product_except_self", """
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
"""),
    # Prefix array construction (classic)
    ("prefix_array_classic", """
n = len(arr)
prefix = [0] * (n + 1)
for i in range(1, n + 1):
    prefix[i] = prefix[i - 1] + arr[i - 1]
"""),
    # Subarray sum divisible by K (LeetCode 974)
    ("subarray_divisible_k", """
prefix_sum = 0
count = 0
mod_map = {0: 1}
for num in nums:
    prefix_sum += num
    mod = prefix_sum % k
    if mod < 0:
        mod += k
    if mod in mod_map:
        count += mod_map[mod]
    mod_map[mod] = mod_map.get(mod, 0) + 1
return count
"""),
    # Prefix sum with string matching
    ("prefix_sum_string", """
running = 0
seen = {0: -1}
max_len = 0
for i, ch in enumerate(s):
    running += 1 if ch == 'a' else -1
    if running in seen:
        max_len = max(max_len, i - seen[running])
    else:
        seen[running] = i
return max_len
"""),
]

PREFIX_SUM_NEGATIVE = [
    ("no_loop", "x = 1"),
    ("plain_sum", """
total = 0
for num in arr:
    total += num
"""),
    ("for_loop_only", "for i in range(10):\n    print(i)"),
    ("non_accumulating_loop", """
for i in range(n):
    print(i)
"""),
    ("filter_loop", """
result = []
for x in arr:
    if x > 0:
        result.append(x)
"""),
    ("frequency_counting", """
freq = {}
for num in nums:
    freq[num] = freq.get(num, 0) + 1
"""),
    ("hash_map_lookup", """
seen = set()
for num in nums:
    if num in seen:
        return True
    seen.add(num)
"""),
    ("product_prefix_unused", """
result = [1] * n
for i in range(n):
    result[i] = result[i - 1] if i > 0 else 1
"""),
    ("nested_loop_matrix", """
for i in range(rows):
    for j in range(cols):
        print(matrix[i][j])
"""),
]


# ===================================================================
# binary_search_classic (index-based binary search)
# ===================================================================

BINARY_SEARCH_CLASSIC_POSITIVE = [
    # Classic Binary Search (LeetCode 704)
    ("binary_search_704", """
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
"""),
    # Search Insert Position (LeetCode 35)
    ("search_insert", """
left, right = 0, len(nums)
while left < right:
    mid = (left + right) // 2
    if nums[mid] < target:
        left = mid + 1
    else:
        right = mid
return left
"""),
    # Search in Rotated Sorted Array (LeetCode 33)
    ("rotated_array_search", """
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
"""),
    # Find Minimum in Rotated Sorted Array (LeetCode 153)
    ("rotated_min", """
left, right = 0, len(nums) - 1
while left < right:
    mid = (left + right) // 2
    if nums[mid] > nums[right]:
        left = mid + 1
    else:
        right = mid
return nums[left]
"""),
    # Find Peak Element (LeetCode 162)
    ("find_peak", """
left, right = 0, len(nums) - 1
while left < right:
    mid = (left + right) // 2
    if nums[mid] > nums[mid + 1]:
        right = mid
    else:
        left = mid + 1
return left
"""),
    # Find First and Last Position (LeetCode 34)
    ("first_last_position", """
def find_first(nums, target):
    left, right = 0, len(nums) - 1
    first = -1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            first = mid
            right = mid - 1
        elif nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return first
"""),
    # Search a 2D Matrix (LeetCode 74)
    ("search_2d_matrix", """
m, n = len(matrix), len(matrix[0])
left, right = 0, m * n - 1
while left <= right:
    mid = (left + right) // 2
    val = matrix[mid // n][mid % n]
    if val == target:
        return True
    elif val < target:
        left = mid + 1
    else:
        right = mid - 1
return False
"""),
    # Sqrt(x) (LeetCode 69)
    ("sqrt_x", """
left, right = 0, x
while left <= right:
    mid = (left + right) // 2
    if mid * mid == x:
        return mid
    elif mid * mid < x:
        left = mid + 1
    else:
        right = mid - 1
return right
"""),
    # Find smallest letter greater than target (LeetCode 744)
    ("smallest_greater", """
left, right = 0, len(letters)
while left < right:
    mid = (left + right) // 2
    if letters[mid] > target:
        right = mid
    else:
        left = mid + 1
return letters[left % len(letters)]
"""),
]

BINARY_SEARCH_CLASSIC_NEGATIVE = [
    ("no_loop", "x = 1"),
    ("plain_while", """
i = 0
while i < 10:
    i += 1
"""),
    ("no_midpoint", """
left, right = 0, len(arr) - 1
while left < right:
    if arr[left] < arr[right]:
        left += 1
    else:
        right -= 1
"""),
    ("answer_space_bs", """
low, high = 1, max_val
while low < high:
    mid = (low + high) // 2
    if is_feasible(mid):
        high = mid
    else:
        low = mid + 1
return low
"""),
    ("for_loop_only", "for i in range(10):\n    print(i)"),
    ("linear_scan", """
for i in range(len(arr)):
    if arr[i] == target:
        return i
return -1
"""),
    ("two_pointers_opposite", """
l, r = 0, n - 1
while l < r:
    if arr[l] < arr[r]:
        l += 1
    else:
        r -= 1
"""),
    ("no_comparison", """
left, right = 0, n - 1
while left < right:
    mid = (left + right) // 2
    left = mid + 1
"""),
    ("binary_search_answer", """
low, high = 1, len(piles)
while low < high:
    mid = (low + high) // 2
    if can_eat(mid):
        high = mid
    else:
        low = mid + 1
return low
"""),
]


# ===================================================================
# binary_search_answer (answer-space binary search)
# ===================================================================

BINARY_SEARCH_ANSWER_POSITIVE = [
    # Koko Eating Bananas (LeetCode 875)
    ("koko_eating", """
low, high = 1, max(piles)
while low < high:
    mid = (low + high) // 2
    if can_eat_all(piles, mid, h):
        high = mid
    else:
        low = mid + 1
return low
"""),
    # Capacity To Ship Packages (LeetCode 1011)
    ("ship_packages", """
low, high = max(weights), sum(weights)
while low < high:
    mid = (low + high) // 2
    if can_ship(weights, mid, days):
        high = mid
    else:
        low = mid + 1
return low
"""),
    # Split Array Largest Sum (LeetCode 410)
    ("split_array", """
low, high = max(nums), sum(nums)
while low < high:
    mid = (low + high) // 2
    if can_split(nums, mid, k):
        high = mid
    else:
        low = mid + 1
return low
"""),
    # Find Smallest Divisor (LeetCode 1283)
    ("smallest_divisor", """
low, high = 1, max(nums)
while low < high:
    mid = (low + high) // 2
    if feasible(nums, mid, threshold):
        high = mid
    else:
        low = mid + 1
return low
"""),
    # Minimize Max Distance to Gas Station (LeetCode 774)
    ("gas_station", """
low, high = 0, max(stations)
while high - low > 1e-6:
    mid = (low + high) / 2
    if is_possible(stations, mid, k):
        high = mid
    else:
        low = mid
return high
"""),
    # Kth Smallest in Multiplication Table (LeetCode 668)
    ("kth_smallest_table", """
low, high = 1, m * n
while low < high:
    mid = (low + high) // 2
    if enough(mid):
        high = mid
    else:
        low = mid + 1
return low
"""),
    # Kth Smallest Pair Distance (LeetCode 719)
    ("kth_smallest_distance", """
nums.sort()
low, high = 0, nums[-1] - nums[0]
while low < high:
    mid = (low + high) // 2
    if count_pairs(nums, mid) >= k:
        high = mid
    else:
        low = mid + 1
return low
"""),
    # Minimum Time to Complete Trips (LeetCode 2187)
    ("minimum_time_trips", """
low, high = 1, min(time) * totalTrips
while low < high:
    mid = (low + high) // 2
    if can_complete(time, mid, totalTrips):
        high = mid
    else:
        low = mid + 1
return low
"""),
    # Magnetic Force Between Balls (LeetCode 1552)
    ("magnetic_force", """
positions.sort()
low, high = 1, positions[-1] - positions[0]
while low < high:
    mid = (low + high + 1) // 2
    if can_place(positions, mid, m):
        low = mid
    else:
        high = mid - 1
return low
"""),
    # Find the Maximum Number of Marked Indices (LeetCode 2576)
    ("max_marked_indices", """
nums.sort()
low, high = 0, len(nums) // 2
while low < high:
    mid = (low + high + 1) // 2
    if can_match(nums, mid):
        low = mid
    else:
        high = mid - 1
return low
"""),
    # First Bad Version (LeetCode 278)
    ("first_bad_version", """
left, right = 1, n
while left < right:
    mid = (left + right) // 2
    if isBadVersion(mid):
        right = mid
    else:
        left = mid + 1
return left
"""),
]

BINARY_SEARCH_ANSWER_NEGATIVE = [
    ("no_loop", "x = 1"),
    ("plain_while", """
i = 0
while i < 10:
    i += 1
"""),
    ("classic_bs", """
left, right = 0, len(arr) - 1
while left <= right:
    mid = (left + right) // 2
    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        left = mid + 1
    else:
        right = mid - 1
"""),
    ("no_feasibility_call", """
low, high = 0, n
while low < high:
    mid = (low + high) // 2
    if arr[mid] < target:
        low = mid + 1
    else:
        high = mid
"""),
    ("for_loop_only", "for i in range(10):\n    print(i)"),
    ("two_pointers", """
l, r = 0, n - 1
while l < r:
    if arr[l] < arr[r]:
        l += 1
    else:
        r -= 1
"""),
    ("prefix_sum", """
prefix = [0]
for num in nums:
    prefix.append(prefix[-1] + num)
"""),
    ("linear_search", """
for i in range(len(arr)):
    if arr[i] == target:
        return i
"""),
]


# ===================================================================
# heap_priority_queue (heapq operations)
# ===================================================================

HEAP_PRIORITY_QUEUE_POSITIVE = [
    # Kth Largest Element (LeetCode 215)
    ("kth_largest", """
import heapq
heap = []
for num in nums:
    heapq.heappush(heap, num)
    if len(heap) > k:
        heapq.heappop(heap)
return heap[0]
"""),
    # Top K Frequent Elements (LeetCode 347)
    ("top_k_frequent_heap", """
import heapq
freq = {}
for num in nums:
    freq[num] = freq.get(num, 0) + 1
heap = []
for num, count in freq.items():
    heapq.heappush(heap, (count, num))
    if len(heap) > k:
        heapq.heappop(heap)
return [num for count, num in heap]
"""),
    # K Closest Points to Origin (LeetCode 973)
    ("k_closest_heap", """
import heapq
heap = []
for x, y in points:
    dist = x * x + y * y
    heapq.heappush(heap, (-dist, x, y))
    if len(heap) > k:
        heapq.heappop(heap)
return [[x, y] for d, x, y in heap]
"""),
    # Kth Largest in Stream (LeetCode 703)
    ("kth_largest_stream", """
import heapq
heap = []
for val in stream:
    heapq.heappush(heap, val)
    if len(heap) > k:
        heapq.heappop(heap)
return heap[0]
"""),
    # Merge k Sorted Lists (LeetCode 23)
    ("merge_k_sorted", """
import heapq
heap = []
for i, node in enumerate(lists):
    if node:
        heapq.heappush(heap, (node.val, i, node))
dummy = ListNode(0)
curr = dummy
while heap:
    val, i, node = heapq.heappop(heap)
    curr.next = ListNode(val)
    curr = curr.next
    if node.next:
        heapq.heappush(heap, (node.next.val, i, node.next))
return dummy.next
"""),
    # Top K Frequent Words (LeetCode 692)
    ("top_k_words", """
import heapq
freq = {}
for word in words:
    freq[word] = freq.get(word, 0) + 1
heap = []
for word, count in freq.items():
    heapq.heappush(heap, (-count, word))
result = []
for _ in range(k):
    result.append(heapq.heappop(heap)[1])
return result
"""),
    # Kth Smallest in Sorted Matrix (LeetCode 378)
    ("kth_smallest_matrix", """
import heapq
heap = []
for i in range(min(k, len(matrix))):
    heapq.heappush(heap, (matrix[i][0], i, 0))
count = 0
while heap:
    val, r, c = heapq.heappop(heap)
    count += 1
    if count == k:
        return val
    if c + 1 < len(matrix[0]):
        heapq.heappush(heap, (matrix[r][c + 1], r, c + 1))
"""),
    # Find Median from Data Stream (LeetCode 295)
    ("median_stream", """
import heapq
self.small = []
self.large = []
for num in nums:
    heapq.heappush(self.small, -num)
    if self.small and self.large and -self.small[0] > self.large[0]:
        val = -heapq.heappop(self.small)
        heapq.heappush(self.large, val)
    if len(self.small) > len(self.large) + 1:
        val = -heapq.heappop(self.small)
        heapq.heappush(self.large, val)
    if len(self.large) > len(self.small):
        val = heapq.heappop(self.large)
        heapq.heappush(self.small, -val)
"""),
    # Last Stone Weight (LeetCode 1046)
    ("last_stone_weight", """
import heapq
stones = [-s for s in stones]
heapq.heapify(stones)
while len(stones) > 1:
    y = -heapq.heappop(stones)
    x = -heapq.heappop(stones)
    if x != y:
        heapq.heappush(stones, -(y - x))
return -stones[0] if stones else 0
"""),
    # Furthest Building You Can Reach (LeetCode 1642)
    ("furthest_building", """
import heapq
heap = []
for i in range(len(heights) - 1):
    diff = heights[i + 1] - heights[i]
    if diff > 0:
        heapq.heappush(heap, diff)
        if len(heap) > bricks:
            ladder_use = heapq.heappop(heap)
            bricks -= ladder_use
        if bricks < 0:
            return i
return len(heights) - 1
"""),
]

HEAP_PRIORITY_QUEUE_NEGATIVE = [
    ("no_heap", "x = 1"),
    ("ordinary_list_sort", """
arr = [3, 1, 2]
arr.sort()
"""),
    ("sorted_function", "result = sorted(arr)"),
    ("heapq_import_only", "import heapq"),
    ("no_heap_ops", """
import heapq
heap = []
"""),
    ("list_operations", """
stack = []
stack.append(1)
stack.pop()
"""),
    ("for_loop_only", "for i in range(10):\n    print(i)"),
    ("sorting_as_top_k", "result = sorted(arr)[:k]"),
    ("dictionary_sort", """
freq = {}
for num in nums:
    freq[num] = freq.get(num, 0) + 1
sorted_items = sorted(freq.items(), key=lambda x: x[1])
"""),
    ("monotonic_stack", """
stack = []
for i in range(len(arr)):
    while stack and arr[stack[-1]] < arr[i]:
        stack.pop()
    stack.append(i)
"""),
]


# ===================================================================
# monotonic_stack (stack + comparison-driven pop)
# ===================================================================

MONOTONIC_STACK_POSITIVE = [
    # Daily Temperatures (LeetCode 739)
    ("daily_temperatures", """
stack = []
result = [0] * len(temperatures)
for i in range(len(temperatures)):
    while stack and temperatures[stack[-1]] < temperatures[i]:
        idx = stack.pop()
        result[idx] = i - idx
    stack.append(i)
return result
"""),
    # Next Greater Element I (LeetCode 496)
    ("next_greater_element", """
stack = []
next_greater = {}
for num in nums2:
    while stack and stack[-1] < num:
        val = stack.pop()
        next_greater[val] = num
    stack.append(num)
return [next_greater.get(num, -1) for num in nums1]
"""),
    # Next Greater Element II (LeetCode 503)
    ("next_greater_ii", """
n = len(nums)
result = [-1] * n
stack = []
for i in range(2 * n):
    idx = i % n
    while stack and nums[stack[-1]] < nums[idx]:
        result[stack.pop()] = nums[idx]
    stack.append(idx)
return result
"""),
    # Largest Rectangle in Histogram (LeetCode 84)
    ("largest_rectangle", """
stack = []
max_area = 0
heights.append(0)
for i in range(len(heights)):
    while stack and heights[stack[-1]] > heights[i]:
        h = heights[stack.pop()]
        w = i if not stack else i - stack[-1] - 1
        max_area = max(max_area, h * w)
    stack.append(i)
heights.pop()
return max_area
"""),
    # Stock Span (LeetCode 901)
    ("stock_span", """
stack = []
result = []
for i in range(len(prices)):
    while stack and prices[stack[-1]] <= prices[i]:
        stack.pop()
    span = i - stack[-1] if stack else i + 1
    result.append(span)
    stack.append(i)
return result
"""),
    # Trapping Rain Water (stack variant)
    ("trap_rain_stack", """
stack = []
water = 0
for i in range(len(height)):
    while stack and height[stack[-1]] < height[i]:
        bottom = stack.pop()
        if not stack:
            break
        left = stack[-1]
        width = i - left - 1
        h = min(height[left], height[i]) - height[bottom]
        water += width * h
    stack.append(i)
return water
"""),
    # Maximal Rectangle (LeetCode 85)
    ("maximal_rectangle", """
max_area = 0
heights = [0] * len(matrix[0])
for row in matrix:
    for i in range(len(row)):
        heights[i] = heights[i] + 1 if row[i] == '1' else 0
    stack = []
    for i in range(len(heights) + 1):
        h = heights[i] if i < len(heights) else 0
        while stack and heights[stack[-1]] > h:
            height = heights[stack.pop()]
            width = i if not stack else i - stack[-1] - 1
            max_area = max(max_area, height * width)
        stack.append(i)
return max_area
"""),
    # Smaller numbers to right (monotonic decreasing)
    ("smaller_right", """
stack = []
result = [0] * len(nums)
for i in range(len(nums) - 1, -1, -1):
    while stack and stack[-1] >= nums[i]:
        stack.pop()
    result[i] = stack[-1] if stack else -1
    stack.append(nums[i])
return result
"""),
]

MONOTONIC_STACK_NEGATIVE = [
    ("no_loop", "x = 1"),
    ("empty_stack_ops", """
stack = []
x = stack.pop()
"""),
    ("ordinary_push_pop", """
stack = []
stack.append(1)
stack.pop()
"""),
    ("no_comparison_pop", """
stack = []
for i in range(len(arr)):
    stack.pop()
    stack.append(i)
"""),
    ("for_loop_only", "for i in range(10):\n    print(i)"),
    ("heap_pattern", """
import heapq
heap = []
for num in nums:
    heapq.heappush(heap, num)
"""),
    ("deque_pattern", """
from collections import deque
dq = deque()
for i in range(len(nums)):
    while dq and nums[dq[-1]] < nums[i]:
        dq.pop()
    dq.append(i)
"""),
    ("simple_list_append", """
result = []
for x in items:
    result.append(x)
"""),
    ("queue_fifo", """
q = []
for item in items:
    q.append(item)
for item in q:
    print(item)
"""),
]


# ===================================================================
# monotonic_deque (deque-based monotonic queue)
# ===================================================================

MONOTONIC_DEQUE_POSITIVE = [
    # Sliding Window Maximum (LeetCode 239)
    ("sliding_window_max", """
from collections import deque
dq = deque()
result = []
for i in range(len(nums)):
    while dq and nums[dq[-1]] < nums[i]:
        dq.pop()
    dq.append(i)
    if dq[0] < i - k + 1:
        dq.popleft()
    if i >= k - 1:
        result.append(nums[dq[0]])
return result
"""),
    # Sliding Window Minimum
    ("sliding_window_min", """
from collections import deque
dq = deque()
result = []
for i in range(len(nums)):
    while dq and nums[dq[-1]] > nums[i]:
        dq.pop()
    dq.append(i)
    if dq[0] < i - k + 1:
        dq.popleft()
    if i >= k - 1:
        result.append(nums[dq[0]])
return result
"""),
    # Longest Contiguous Subarray Absolute Diff (LeetCode 1438)
    ("longest_abs_diff", """
from collections import deque
max_dq = deque()
min_dq = deque()
left = 0
for right in range(len(nums)):
    while max_dq and nums[max_dq[-1]] < nums[right]:
        max_dq.pop()
    max_dq.append(right)
    while min_dq and nums[min_dq[-1]] > nums[right]:
        min_dq.pop()
    min_dq.append(right)
    while nums[max_dq[0]] - nums[min_dq[0]] > limit:
        left += 1
        if max_dq[0] < left:
            max_dq.popleft()
        if min_dq[0] < left:
            min_dq.popleft()
    max_len = max(max_len, right - left + 1)
return max_len
"""),
    # Shortest Subarray with Sum at Least K (LeetCode 862)
    ("shortest_subarray_k", """
from collections import deque
dq = deque()
prefix = [0]
for num in nums:
    prefix.append(prefix[-1] + num)
result = float('inf')
for i in range(len(prefix)):
    while dq and prefix[i] - prefix[dq[0]] >= k:
        result = min(result, i - dq.popleft())
    while dq and prefix[i] <= prefix[dq[-1]]:
        dq.pop()
    dq.append(i)
return result if result != float('inf') else -1
"""),
    # Deque count bits pattern
    ("deque_count_bits", """
from collections import deque
q = deque()
for i in range(n):
    while q and condition:
        q.pop()
    q.append(i)
    q.popleft()
"""),
    # Deque with while-based monotonic maintenance
    ("deque_monotonic_maintenance", """
from collections import deque
dq = deque()
for i in range(len(arr)):
    while dq and arr[dq[-1]] <= arr[i]:
        dq.pop()
    dq.append(i)
    if dq[0] <= i - k:
        dq.popleft()
"""),
]

MONOTONIC_DEQUE_NEGATIVE = [
    ("no_loop", "x = 1"),
    ("ordinary_deque", """
from collections import deque
dq = deque()
dq.append(1)
x = dq.popleft()
"""),
    ("list_as_stack", """
stack = []
for i in range(len(arr)):
    while stack and arr[stack[-1]] < arr[i]:
        stack.pop()
    stack.append(i)
"""),
    ("for_loop_only", "for i in range(10):\n    print(i)"),
    ("deque_no_while", """
from collections import deque
dq = deque()
for i in range(n):
    dq.append(i)
    if len(dq) > k:
        dq.popleft()
"""),
    ("no_deque_import", """
dq = []
for i in range(n):
    dq.append(i)
    if len(dq) > k:
        dq.pop(0)
"""),
    ("heapq_usage", """
import heapq
heap = []
for num in nums:
    heapq.heappush(heap, -num)
"""),
    ("plain_queue", """
q = []
for item in items:
    q.append(item)
while q:
    q.pop(0)
"""),
    ("monotonic_stack", """
stack = []
for i in range(len(arr)):
    while stack and arr[stack[-1]] < arr[i]:
        stack.pop()
    stack.append(i)
"""),
]


# ===================================================================
# Test runner with overlap tracking
# ===================================================================


def run_detector_tests(detector, positives, negatives, detector_name,
                       all_results=None):
    tp, fn = 0, 0
    fp, tn = 0, 0
    false_negatives = []
    false_positives = []
    confidences = []

    for name, code in positives:
        tree = ast.parse(code)
        result = detector.detect(tree)
        if result.detected:
            tp += 1
            confidences.append(result.confidence)
        else:
            fn += 1
            false_negatives.append((name, code, result.confidence))
        if all_results is not None:
            all_results[detector_name].append((name, result))

    for name, code in negatives:
        tree = ast.parse(code)
        result = detector.detect(tree)
        if result.detected:
            fp += 1
            false_positives.append((name, code, result.confidence))
        else:
            tn += 1
        if all_results is not None:
            all_results[detector_name].append((name, result))

    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    min_conf = min(confidences) if confidences else 0.0

    print(f"\n{'='*60}")
    print(f"  {detector_name}")
    print(f"{'='*60}")
    print(f"  True Positives:  {tp:2d} / {len(positives)}  "
          f"(avg conf: {avg_conf:.3f}, min: {min_conf:.3f})")
    print(f"  False Negatives: {fn:2d} / {len(positives)}")
    print(f"  True Negatives:  {tn:2d} / {len(negatives)}")
    print(f"  False Positives: {fp:2d} / {len(negatives)}")

    if false_negatives:
        print(f"\n  --- False Negatives ---")
        for name, code, conf in false_negatives:
            first_line = code.strip().split('\n')[0][:50]
            print(f"    [{name}] conf={conf:.2f}: {first_line}")

    if false_positives:
        print(f"\n  --- False Positives ---")
        for name, code, conf in false_positives:
            first_line = code.strip().split('\n')[0][:50]
            print(f"    [{name}] conf={conf:.2f}: {first_line}")

    return tp, fn, fp, tn, confidences


def build_overlap_matrix(all_results, detector_names):
    print(f"\n{'='*60}")
    print(f"  DETECTOR OVERLAP MATRIX")
    print(f"{'='*60}")
    header = "                  " + "".join(f"{n[:12]:>12}" for n in detector_names)
    print(header)

    for d1 in detector_names:
        row = f"{d1[:18]:>18}"
        for d2 in detector_names:
            if d1 == d2:
                row += f"{'':>12}"
                continue
            overlap = 0
            total = 0
            for name1, r1 in all_results[d1]:
                for name2, r2 in all_results[d2]:
                    if name1 == name2 and r1.detected and r2.detected:
                        overlap += 1
                        break
                total += 1
            overlap_pct = overlap / total * 100 if total > 0 else 0
            row += f"{overlap_pct:>11.1f}%"
        print(row)


def main():
    print("Phase 3C.2.3A — Full Detector Validation (15 detectors)")
    print("Testing against comprehensive LeetCode-inspired solution patterns")
    print()

    all_results = defaultdict(list)

    all_tp = all_fn = all_fp = all_tn = 0
    all_confidences = []

    detectors = [
        # (detector_instance, positives, negatives, name)
        (HashMapLookupDetector(), HASH_MAP_LOOKUP_POSITIVE, HASH_MAP_LOOKUP_NEGATIVE, "hash_map_lookup"),
        (ArrayTraversalDetector(), ARRAY_TRAVERSAL_POSITIVE, ARRAY_TRAVERSAL_NEGATIVE, "array_traversal"),
        (SortingDetector(), SORTING_POSITIVE, SORTING_NEGATIVE, "sorting"),
        (BruteForceDetector(), BRUTE_FORCE_POSITIVE, BRUTE_FORCE_NEGATIVE, "brute_force"),
        (FrequencyCountingDetector(), FREQUENCY_COUNTING_POSITIVE, FREQUENCY_COUNTING_NEGATIVE, "hash_map_frequency"),
        (TwoPointersSameDetector(), TWO_POINTERS_SAME_POSITIVE, TWO_POINTERS_SAME_NEGATIVE, "two_pointers_same"),
        (TwoPointersOppositeDetector(), TWO_POINTERS_OPPOSITE_POSITIVE, TWO_POINTERS_OPPOSITE_NEGATIVE, "two_pointers_opposite"),
        (SlidingWindowFixedDetector(), SLIDING_WINDOW_FIXED_POSITIVE, SLIDING_WINDOW_FIXED_NEGATIVE, "sliding_window_fixed"),
        (SlidingWindowVariableDetector(), SLIDING_WINDOW_VARIABLE_POSITIVE, SLIDING_WINDOW_VARIABLE_NEGATIVE, "sliding_window_variable"),
        (PrefixSumDetector(), PREFIX_SUM_POSITIVE, PREFIX_SUM_NEGATIVE, "prefix_sum"),
        (BinarySearchClassicDetector(), BINARY_SEARCH_CLASSIC_POSITIVE, BINARY_SEARCH_CLASSIC_NEGATIVE, "binary_search_standard"),
        (BinarySearchAnswerDetector(), BINARY_SEARCH_ANSWER_POSITIVE, BINARY_SEARCH_ANSWER_NEGATIVE, "binary_search_answer"),
        (HeapPriorityQueueDetector(), HEAP_PRIORITY_QUEUE_POSITIVE, HEAP_PRIORITY_QUEUE_NEGATIVE, "heap_top_k"),
        (MonotonicStackDetector(), MONOTONIC_STACK_POSITIVE, MONOTONIC_STACK_NEGATIVE, "monotonic_stack"),
        (MonotonicQueueDetector(), MONOTONIC_DEQUE_POSITIVE, MONOTONIC_DEQUE_NEGATIVE, "monotonic_deque"),
    ]

    for det, pos, neg, name in detectors:
        tp, fn, fp, tn, confs = run_detector_tests(
            det, pos, neg, name, all_results
        )
        all_tp += tp
        all_fn += fn
        all_fp += fp
        all_tn += tn
        all_confidences.extend(confs)

    total = all_tp + all_fn + all_fp + all_tn
    precision = all_tp / (all_tp + all_fp) if (all_tp + all_fp) > 0 else 0
    recall = all_tp / (all_tp + all_fn) if (all_tp + all_fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    conf_avg = sum(all_confidences) / len(all_confidences) if all_confidences else 0

    print(f"\n{'='*60}")
    print(f"  OVERALL RESULTS ({len(detectors)} detectors)")
    print(f"{'='*60}")
    print(f"  Total tests:        {total}")
    print(f"  True Positives:     {all_tp}")
    print(f"  False Negatives:    {all_fn}")
    print(f"  True Negatives:     {all_tn}")
    print(f"  False Positives:    {all_fp}")
    print(f"  Precision:          {precision:.4f}")
    print(f"  Recall:             {recall:.4f}")
    print(f"  F1 Score:           {f1:.4f}")
    print(f"  Avg Confidence:     {conf_avg:.4f}")

    raw_dist = defaultdict(int)
    for c in all_confidences:
        bucket = round(c, 1)
        raw_dist[bucket] += 1
    print(f"\n  --- Confidence Distribution ---")
    for bucket in sorted(raw_dist):
        count = raw_dist[bucket]
        bar = "#" * (count // 2)
        print(f"    [{bucket:.1f}] {count:3d} {bar}")

    detector_names = [name for _, _, _, name in detectors]
    build_overlap_matrix(all_results, detector_names)

    print(f"\n{'='*60}")
    if all_fn == 0 and all_fp == 0:
        print(f"  VERDICT: All detectors pass validation perfectly.")
    elif all_fp == 0:
        print(f"  VERDICT: No false positives. {all_fn} false negatives found.")
    elif all_fn == 0:
        print(f"  VERDICT: No false negatives. {all_fp} false positives found.")
    else:
        print(f"  VERDICT: {all_fn} false negatives, {all_fp} false positives found.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
