"""Calibration corpus for semantic analyzer validation.

Contains 50+ test cases with known positive/negative labels for
pattern calibration.
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CalibrationCase:
    """A single calibration case."""
    name: str
    code: str
    expected_pattern: str
    is_positive: bool  # True = pattern should be detected
    source: str  # where the case came from
    notes: str = ""


def get_calibration_corpus() -> List[CalibrationCase]:
    """Return the calibration corpus."""
    cases = []

    # ============================================================
    # ARRAY TRAVERSAL - POSITIVE CASES
    # ============================================================

    cases.append(CalibrationCase(
        name="array_traversal_for_loop",
        code="""
def traverse(arr):
    result = []
    for i in range(len(arr)):
        result.append(arr[i] * 2)
    return result
""",
        expected_pattern="array_traversal",
        is_positive=True,
        source="handwritten",
        notes="Basic for-loop with indexed access",
    ))

    cases.append(CalibrationCase(
        name="array_traversal_while_loop",
        code="""
def traverse(arr):
    i = 0
    while i < len(arr):
        print(arr[i])
        i += 1
""",
        expected_pattern="array_traversal",
        is_positive=True,
        source="handwritten",
        notes="While-loop with counter and indexed access",
    ))

    cases.append(CalibrationCase(
        name="array_traversal_while_len_compare",
        code="""
def find_max(arr):
    max_val = arr[0]
    i = 1
    while i < len(arr):
        if arr[i] > max_val:
            max_val = arr[i]
        i += 1
    return max_val
""",
        expected_pattern="array_traversal",
        is_positive=True,
        source="handwritten",
        notes="While-loop comparing to len()",
    ))

    cases.append(CalibrationCase(
        name="array_traversal_different_names",
        code="""
def process(data):
    idx = 0
    while idx < len(data):
        item = data[idx]
        idx += 1
""",
        expected_pattern="array_traversal",
        is_positive=True,
        source="handwritten",
        notes="Different variable names (idx, data)",
    ))

    cases.append(CalibrationCase(
        name="array_traversal_enumerate",
        code="""
def traverse(arr):
    for idx, val in enumerate(arr):
        arr[idx] = val * 2
""",
        expected_pattern="array_traversal",
        is_positive=True,
        source="handwritten",
        notes="Using enumerate",
    ))

    cases.append(CalibrationCase(
        name="array_traversal_nested",
        code="""
def process(matrix):
    for i in range(len(matrix)):
        for j in range(len(matrix[0])):
            matrix[i][j] = matrix[i][j] * 2
""",
        expected_pattern="array_traversal",
        is_positive=True,
        source="handwritten",
        notes="Nested loops with indexed access",
    ))

    # ============================================================
    # ARRAY TRAVERSAL - NEGATIVE CASES
    # ============================================================

    cases.append(CalibrationCase(
        name="not_array_traversal_simple_function",
        code="""
def add(a, b):
    return a + b
""",
        expected_pattern="array_traversal",
        is_positive=False,
        source="handwritten",
        notes="No loops, no array access",
    ))

    cases.append(CalibrationCase(
        name="not_array_traversal_string_ops",
        code="""
def process(s):
    return s.upper().strip()
""",
        expected_pattern="array_traversal",
        is_positive=False,
        source="handwritten",
        notes="String operations, no array traversal",
    ))

    cases.append(CalibrationCase(
        name="not_array_traversal_dict_only",
        code="""
def count_freq(items):
    freq = {}
    for item in items:
        freq[item] = freq.get(item, 0) + 1
    return freq
""",
        expected_pattern="array_traversal",
        is_positive=False,
        source="handwritten",
        notes="Dict operations, not array traversal",
    ))

    # ============================================================
    # HASH MAP LOOKUP - POSITIVE CASES
    # ============================================================

    cases.append(CalibrationCase(
        name="hashmap_two_sum",
        code="""
def twoSum(nums, target):
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
        source="leetcode",
        notes="Classic two-sum with dict",
    ))

    cases.append(CalibrationCase(
        name="hashmap_set_membership",
        code="""
def has_common(nums1, nums2):
    seen = set(nums1)
    for num in nums2:
        if num in seen:
            return True
    return False
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        source="handwritten",
        notes="Set membership test",
    ))

    cases.append(CalibrationCase(
        name="hashmap_dict_lookup",
        code="""
def translate(text, dict_map):
    result = []
    for word in text.split():
        if word in dict_map:
            result.append(dict_map[word])
        else:
            result.append(word)
    return result
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        source="handwritten",
        notes="Dict lookup in loop",
    ))

    cases.append(CalibrationCase(
        name="hashmap_frequency_count",
        code="""
def frequency(s):
    freq = {}
    for char in s:
        freq[char] = freq.get(char, 0) + 1
    return freq
""",
        expected_pattern="hash_map_lookup",
        is_positive=True,
        source="handwritten",
        notes="Frequency counting with dict",
    ))

    # ============================================================
    # HASH MAP LOOKUP - NEGATIVE CASES
    # ============================================================

    cases.append(CalibrationCase(
        name="not_hashmap_list_membership",
        code="""
def find_in_list(arr, target):
    for x in arr:
        if x == target:
            return True
    return False
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        source="handwritten",
        notes="Linear search in list, not hash lookup",
    ))

    cases.append(CalibrationCase(
        name="not_hashmap_no_membership",
        code="""
def process(items):
    seen = {}
    for item in items:
        seen[item] = True
    return seen
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        source="handwritten",
        notes="Dict creation but no membership test",
    ))

    cases.append(CalibrationCase(
        name="not_hashmap_class_method",
        code="""
class Container:
    def __init__(self):
        self.data = []
    def contains(self, item):
        return item in self.data
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        source="handwritten",
        notes="Membership in class method, not algorithmic",
    ))

    # ============================================================
    # PREFIX SUM - POSITIVE CASES
    # ============================================================

    cases.append(CalibrationCase(
        name="prefixsum_running_total",
        code="""
def runningSum(nums):
    result = []
    total = 0
    for num in nums:
        total += num
        result.append(total)
    return result
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        source="leetcode",
        notes="Running total accumulation",
    ))

    cases.append(CalibrationCase(
        name="prefixsum_cumulative",
        code="""
def cumulative_sum(arr):
    prefix = [0] * (len(arr) + 1)
    for i in range(len(arr)):
        prefix[i+1] = prefix[i] + arr[i]
    return prefix
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        source="handwritten",
        notes="Classic prefix sum array",
    ))

    cases.append(CalibrationCase(
        name="prefixsum_subarray_sum",
        code="""
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
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        source="leetcode",
        notes="Prefix sum with hash map",
    ))

    # ============================================================
    # PREFIX SUM - NEGATIVE CASES
    # ============================================================

    cases.append(CalibrationCase(
        name="not_prefixsum_simple_accumulator",
        code="""
def count_positive(nums):
    count = 0
    for num in nums:
        if num > 0:
            count += 1
    return count
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        source="handwritten",
        notes="Simple counter, not prefix sum",
    ))

    cases.append(CalibrationCase(
        name="not_prefixsum_max_accumulator",
        code="""
def find_max(arr):
    max_val = arr[0]
    for num in arr:
        if num > max_val:
            max_val = num
    return max_val
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        source="handwritten",
        notes="Max finding, not accumulation",
    ))

    cases.append(CalibrationCase(
        name="not_prefixsum_string_concat",
        code="""
def join_words(words):
    result = ""
    for word in words:
        result += word + " "
    return result.strip()
""",
        expected_pattern="prefix_sum",
        is_positive=False,
        source="handwritten",
        notes="String concatenation, not numeric prefix sum",
    ))

    # ============================================================
    # TWO POINTERS OPPOSITE - POSITIVE CASES
    # ============================================================

    cases.append(CalibrationCase(
        name="twopointers_palindrome",
        code="""
def isPalindrome(s):
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True
""",
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        source="leetcode",
        notes="Classic palindrome check",
    ))

    cases.append(CalibrationCase(
        name="twopointers_container_water",
        code="""
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
""",
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        source="leetcode",
        notes="Container with most water",
    ))

    cases.append(CalibrationCase(
        name="twopointers_sorted_squared",
        code="""
def sortedSquares(nums):
    n = len(nums)
    result = [0] * n
    left, right = 0, n - 1
    idx = n - 1
    while left <= right:
        if abs(nums[left]) > abs(nums[right]):
            result[idx] = nums[left] ** 2
            left += 1
        else:
            result[idx] = nums[right] ** 2
            right -= 1
        idx -= 1
    return result
""",
        expected_pattern="two_pointers_opposite",
        is_positive=True,
        source="leetcode",
        notes="Squares of sorted array",
    ))

    # ============================================================
    # TWO POINTERS OPPOSITE - NEGATIVE CASES
    # ============================================================

    cases.append(CalibrationCase(
        name="not_twopointers_single_counter",
        code="""
def traverse(arr):
    i = 0
    while i < len(arr):
        print(arr[i])
        i += 1
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        source="handwritten",
        notes="Single counter, not two pointers",
    ))

    cases.append(CalibrationCase(
        name="not_twopointers_same_direction",
        code="""
def find_common(arr1, arr2):
    i, j = 0, 0
    result = []
    while i < len(arr1) and j < len(arr2):
        if arr1[i] == arr2[j]:
            result.append(arr1[i])
            i += 1
            j += 1
        elif arr1[i] < arr2[j]:
            i += 1
        else:
            j += 1
    return result
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        source="handwritten",
        notes="Two pointers but same direction",
    ))

    cases.append(CalibrationCase(
        name="not_twopointers_for_loop",
        code="""
def sum_pairs(arr, target):
    for i in range(len(arr)):
        for j in range(i+1, len(arr)):
            if arr[i] + arr[j] == target:
                return [i, j]
    return []
""",
        expected_pattern="two_pointers_opposite",
        is_positive=False,
        source="handwritten",
        notes="Nested for loops, not two pointers",
    ))

    # ============================================================
    # BINARY SEARCH - POSITIVE CASES
    # ============================================================

    cases.append(CalibrationCase(
        name="binarysearch_classic",
        code="""
def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
""",
        expected_pattern="binary_search_standard",
        is_positive=True,
        source="handwritten",
        notes="Classic binary search",
    ))

    cases.append(CalibrationCase(
        name="binarysearch_first_bad_version",
        code="""
def firstBadVersion(n):
    lo, hi = 1, n
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if isBadVersion(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo
""",
        expected_pattern="binary_search_answer",
        is_positive=True,
        source="leetcode",
        notes="Binary search on answer space",
    ))

    cases.append(CalibrationCase(
        name="binarysearch_rotated",
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
        expected_pattern="binary_search_rotated",
        is_positive=True,
        source="leetcode",
        notes="Search in rotated sorted array",
    ))

    # ============================================================
    # BINARY SEARCH - NEGATIVE CASES
    # ============================================================

    cases.append(CalibrationCase(
        name="not_binarysearch_linear",
        code="""
def find(arr, target):
    for i in range(len(arr)):
        if arr[i] == target:
            return i
    return -1
""",
        expected_pattern="binary_search_standard",
        is_positive=False,
        source="handwritten",
        notes="Linear search, not binary search",
    ))

    cases.append(CalibrationCase(
        name="not_binarysearch_no_midpoint",
        code="""
def check(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo < hi:
        if arr[lo] == target:
            return lo
        lo += 1
    return -1
""",
        expected_pattern="binary_search_standard",
        is_positive=False,
        source="handwritten",
        notes="Has lo/hi but no midpoint calculation",
    ))

    # ============================================================
    # MIXED/ADVERSARIAL CASES
    # ============================================================

    cases.append(CalibrationCase(
        name="adversarial_while_membership",
        code="""
def find_missing(nums):
    i = 1
    while i in nums:
        i += 1
    return i
""",
        expected_pattern="array_traversal",
        is_positive=True,
        source="adversarial",
        notes="While loop with membership, should detect traversal",
    ))

    cases.append(CalibrationCase(
        name="adversarial_while_accumulation",
        code="""
def prefix_sum(nums):
    total = 0
    i = 0
    while i < len(nums):
        total += nums[i]
        i += 1
    return total
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        source="adversarial",
        notes="While loop with accumulation",
    ))

    cases.append(CalibrationCase(
        name="adversarial_class_traversal",
        code="""
class Solution:
    def method(self, arr):
        result = []
        for x in arr:
            result.append(x * 2)
        return result
""",
        expected_pattern="array_traversal",
        is_positive=True,
        source="adversarial",
        notes="Class method with for-loop traversal",
    ))

    cases.append(CalibrationCase(
        name="adversarial_list_comprehension",
        code="""
def double(arr):
    return [x * 2 for x in arr]
""",
        expected_pattern="array_traversal",
        is_positive=True,
        source="adversarial",
        notes="List comprehension (iteration over collection)",
    ))

    cases.append(CalibrationCase(
        name="adversarial_dict_comprehension",
        code="""
def invert(d):
    return {v: k for k, v in d.items()}
""",
        expected_pattern="hash_map_lookup",
        is_positive=False,
        source="adversarial",
        notes="Dict comprehension, not hash map lookup pattern",
    ))

    cases.append(CalibrationCase(
        name="adversarial_lambda",
        code="""
process = lambda x: x * 2
""",
        expected_pattern="array_traversal",
        is_positive=False,
        source="adversarial",
        notes="Lambda, no iteration",
    ))

    cases.append(CalibrationCase(
        name="adversarial_recursion",
        code="""
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
""",
        expected_pattern="array_traversal",
        is_positive=False,
        source="adversarial",
        notes="Recursion, not iteration",
    ))

    cases.append(CalibrationCase(
        name="adversarial_mixed_accumulator",
        code="""
def product_except_self(nums):
    result = [1] * len(nums)
    prefix = 1
    for i in range(len(nums)):
        result[i] = prefix
        prefix *= nums[i]
    return result
""",
        expected_pattern="prefix_sum",
        is_positive=True,
        source="leetcode",
        notes="Product prefix (multiplicative accumulator)",
    ))

    cases.append(CalibrationCase(
        name="adversarial_two_ptrs_same_direction",
        code="""
def remove_duplicates(nums):
    if not nums:
        return 0
    slow = 0
    for fast in range(1, len(nums)):
        if nums[fast] != nums[slow]:
            slow += 1
            nums[slow] = nums[fast]
    return slow + 1
""",
        expected_pattern="two_pointers_same",
        is_positive=True,
        source="leetcode",
        notes="Fast/slow pointers same direction",
    ))

    cases.append(CalibrationCase(
        name="adversarial_greedy",
        code="""
def max_coins(piles):
    piles.sort()
    result = 0
    n = len(piles)
    for i in range(n // 3, n, 2):
        result += piles[i]
    return result
""",
        expected_pattern="greedy_local",
        is_positive=True,
        source="leetcode",
        notes="Greedy with sorting",
    ))

    cases.append(CalibrationCase(
        name="adversarial_stack",
        code="""
def isValid(s):
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}
    for char in s:
        if char in mapping:
            if not stack or stack[-1] != mapping[char]:
                return False
            stack.pop()
        else:
            stack.append(char)
    return len(stack) == 0
""",
        expected_pattern="monotonic_stack",
        is_positive=True,
        source="leetcode",
        notes="Stack-based validation",
    ))

    cases.append(CalibrationCase(
        name="adversarial_empty",
        code="""
def empty():
    pass
""",
        expected_pattern="array_traversal",
        is_positive=False,
        source="handwritten",
        notes="Empty function",
    ))

    cases.append(CalibrationCase(
        name="adversarial_single_line",
        code="""
return x + 1
""",
        expected_pattern="array_traversal",
        is_positive=False,
        source="handwritten",
        notes="Single return statement",
    ))

    return cases


def get_corpus_stats(cases: List[CalibrationCase]) -> dict:
    """Get statistics about the corpus."""
    patterns = {}
    for case in cases:
        if case.expected_pattern not in patterns:
            patterns[case.expected_pattern] = {"positive": 0, "negative": 0}
        if case.is_positive:
            patterns[case.expected_pattern]["positive"] += 1
        else:
            patterns[case.expected_pattern]["negative"] += 1

    return {
        "total_cases": len(cases),
        "patterns": patterns,
    }
