"""Tests for detector implementations in Batch 2."""

import ast
from src.ast_detection.detectors.two_pointers_same import TwoPointersSameDetector
from src.ast_detection.detectors.two_pointers_opposite import TwoPointersOppositeDetector
from src.ast_detection.detectors.sliding_window_fixed import SlidingWindowFixedDetector
from src.ast_detection.detectors.sliding_window_variable import SlidingWindowVariableDetector
from src.ast_detection.detectors.prefix_sum import PrefixSumDetector
from src.ast_detection.detector_interface import DetectionResult


class TestTwoPointersSameDetector:
    def setup_method(self):
        self.detector = TwoPointersSameDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "two_pointers_same"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_loop(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_single_pointer_while(self):
        code = """
i = 0
while i < 10:
    print(i)
    i += 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_same_increment_while(self):
        code = """
i = 0
j = 1
while i < 10:
    print(i, j)
    i += 1
    j += 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_slow_fast_differential(self):
        code = """
slow = 0
fast = 0
while fast < len(arr):
    print(arr[slow], arr[fast])
    slow += 1
    fast += 2
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_detected_offset_pointer_loop(self):
        code = """
slow = head
fast = head
while fast and fast.next:
    slow = slow.next
    fast = fast.next.next
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_detected_cycle_detection(self):
        code = """
slow = head
fast = head
while fast and fast.next:
    slow = slow.next
    fast = fast.next.next
    if slow == fast:
        return True
return False
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_not_detected_for_loop(self):
        code = "for i in range(10):\n    print(i)"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_normal_for_loop(self):
        code = """
for i in range(len(arr)):
    print(arr[i])
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_while_single_increment(self):
        code = """
i = 0
while i < len(arr):
    print(arr[i])
    i += 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestTwoPointersOppositeDetector:
    def setup_method(self):
        self.detector = TwoPointersOppositeDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "two_pointers_opposite"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_loop(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_detected_left_right_convergence(self):
        code = """
left = 0
right = len(arr) - 1
while left < right:
    if arr[left] < arr[right]:
        left += 1
    else:
        right -= 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_detected_two_sum_sorted(self):
        code = """
left = 0
right = len(numbers) - 1
while left < right:
    total = numbers[left] + numbers[right]
    if total == target:
        return [left + 1, right + 1]
    elif total < target:
        left += 1
    else:
        right -= 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_detected_container_with_most_water(self):
        code = """
left = 0
right = len(height) - 1
max_area = 0
while left < right:
    area = min(height[left], height[right]) * (right - left)
    max_area = max(max_area, area)
    if height[left] < height[right]:
        left += 1
    else:
        right -= 1
return max_area
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_not_detected_while_same_direction(self):
        code = """
i = 0
j = 1
while i < len(arr):
    print(arr[i], arr[j])
    i += 1
    j += 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_single_pointer_while(self):
        code = """
i = 0
while i < len(arr):
    print(arr[i])
    i += 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_for_loop(self):
        code = "for i in range(10):\n    print(i)"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestSlidingWindowFixedDetector:
    def setup_method(self):
        self.detector = SlidingWindowFixedDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "sliding_window_fixed"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_loop(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_detected_fixed_window_sum(self):
        code = """
window_sum = 0
left = 0
for right in range(len(arr)):
    window_sum += arr[right]
    if right >= k - 1:
        max_sum = max(max_sum, window_sum)
        window_sum -= arr[left]
        left += 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_detected_anagram_window(self):
        code = """
left = 0
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
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_detected_max_average_window(self):
        code = """
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
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_not_detected_no_boundary_check(self):
        code = """
total = 0
for right in range(len(arr)):
    total += arr[right]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_regular_for_loop(self):
        code = "for i in range(10):\n    print(i)"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestSlidingWindowVariableDetector:
    def setup_method(self):
        self.detector = SlidingWindowVariableDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "sliding_window_variable"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_loop(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_detected_longest_substring(self):
        code = """
left = 0
char_set = {}
max_len = 0
for right in range(len(s)):
    if s[right] in char_set:
        left = max(left, char_set[s[right]] + 1)
    char_set[s[right]] = right
    max_len = max(max_len, right - left + 1)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_detected_min_window_substring(self):
        code = """
left = 0
min_len = float('inf')
for right in range(len(s)):
    if s[right] in t_counts:
        t_counts[s[right]] -= 1
        if t_counts[s[right]] >= 0:
            formed += 1
    while formed == required and left <= right:
        if right - left + 1 < min_len:
            min_len = right - left + 1
            result = (left, right)
        if s[left] in t_counts:
            t_counts[s[left]] += 1
            if t_counts[s[left]] > 0:
                formed -= 1
        left += 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_detected_longest_repeating_char(self):
        code = """
left = 0
max_count = 0
max_len = 0
count = {}
for right in range(len(s)):
    count[s[right]] = count.get(s[right], 0) + 1
    max_count = max(max_count, count[s[right]])
    while (right - left + 1) - max_count > k:
        count[s[left]] -= 1
        left += 1
    max_len = max(max_len, right - left + 1)
return max_len
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_not_detected_no_left_pointer(self):
        code = """
for right in range(len(arr)):
    print(arr[right])
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_for_loop_only(self):
        code = "for i in range(10):\n    print(i)"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestPrefixSumDetector:
    def setup_method(self):
        self.detector = PrefixSumDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "prefix_sum"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_loop(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_detected_prefix_array_construction(self):
        code = """
n = len(arr)
prefix = [0] * (n + 1)
for i in range(1, n + 1):
    prefix[i] = prefix[i - 1] + arr[i - 1]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_detected_running_sum_dict(self):
        code = """
running_sum = 0
count = 0
prefix_sums = {0: 1}
for num in nums:
    running_sum += num
    if running_sum - k in prefix_sums:
        count += prefix_sums[running_sum - k]
    prefix_sums[running_sum] = prefix_sums.get(running_sum, 0) + 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_detected_range_sum_query(self):
        code = """
prefix = [0]
for num in nums:
    prefix.append(prefix[-1] + num)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_detected_product_except_self(self):
        code = """
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
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_not_detected_plain_loop(self):
        code = """
total = 0
for num in arr:
    total += num
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_for_loop(self):
        code = "for i in range(10):\n    print(i)"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_no_accumulation(self):
        code = """
x = 0
for i in range(n):
    print(i)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected
