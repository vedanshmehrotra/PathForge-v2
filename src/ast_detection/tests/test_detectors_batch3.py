"""Tests for detector implementations in Batch 3."""

import ast
from src.ast_detection.detectors.binary_search_classic import BinarySearchClassicDetector
from src.ast_detection.detectors.binary_search_answer import BinarySearchAnswerDetector
from src.ast_detection.detectors.heap_priority_queue import HeapPriorityQueueDetector
from src.ast_detection.detectors.monotonic_stack import MonotonicStackDetector
from src.ast_detection.detectors.monotonic_queue import MonotonicQueueDetector
from src.ast_detection.detector_interface import DetectionResult


class TestBinarySearchClassicDetector:
    def setup_method(self):
        self.detector = BinarySearchClassicDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "binary_search_standard"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_loop(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_plain_loop(self):
        code = "for i in range(10):\n    print(i)"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_classic_binary_search(self):
        code = """
left, right = 0, len(arr) - 1
while left <= right:
    mid = (left + right) // 2
    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        left = mid + 1
    else:
        right = mid - 1
return -1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "binary_midpoint" for e in result.evidence)
        assert any(e.type == "boundary_update" for e in result.evidence)

    def test_detected_left_vs_right(self):
        code = """
lo, hi = 0, n - 1
while lo <= hi:
    mid = (lo + hi) // 2
    if nums[mid] == x:
        return mid
    elif nums[mid] < x:
        lo = mid + 1
    else:
        hi = mid - 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_detected_with_mid_comparison(self):
        code = """
left = 0
right = len(arr) - 1
while left <= right:
    mid = left + (right - left) // 2
    if arr[mid] > target:
        right = mid - 1
    else:
        left = mid + 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "mid_comparison" for e in result.evidence)

    def test_not_detected_while_no_midpoint(self):
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
        assert result.detected == False

    def test_not_detected_answer_space_bs(self):
        code = """
low, high = 1, max_val
while low < high:
    mid = (low + high) // 2
    if is_feasible(mid):
        high = mid
    else:
        low = mid + 1
return low
"""
        result = self.detector.detect(ast.parse(code))
        # Single-sided narrowing (high = mid) is distinctive of answer-space,
        # not classic. The boundary_update check requires mid+1 or mid-1 patterns.
        assert result.detected == False

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestBinarySearchAnswerDetector:
    def setup_method(self):
        self.detector = BinarySearchAnswerDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "binary_search_answer"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_loop(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_plain_while(self):
        code = "i = 0\nwhile i < 10:\n    i += 1"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_answer_space_feasibility(self):
        code = """
low, high = 1, max_val
while low < high:
    mid = (low + high) // 2
    if is_feasible(mid):
        high = mid
    else:
        low = mid + 1
return low
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "feasibility_check" for e in result.evidence)
        assert any(e.type == "answer_midpoint" for e in result.evidence)

    def test_detected_with_check_function(self):
        code = """
lo, hi = 0, n
while lo < hi:
    mid = (lo + hi) // 2
    if check(mid):
        hi = mid
    else:
        lo = mid + 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_detected_with_can_place_function(self):
        code = """
l, r = 1, 10**9
while l < r:
    m = (l + r) // 2
    if can_place(m):
        r = m
    else:
        l = m + 1
return l
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detected_with_not_feasible(self):
        code = """
low, high = 1, max_val
while low < high:
    mid = (low + high) // 2
    if not possible(mid):
        low = mid + 1
    else:
        high = mid
return high
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_not_detected_classic_bs(self):
        code = """
left, right = 0, len(arr) - 1
while left <= right:
    mid = (left + right) // 2
    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        left = mid + 1
    else:
        right = mid - 1
"""
        result = self.detector.detect(ast.parse(code))
        # Classic BS compares arr[mid] == target, not a feasibility function call
        assert result.detected == False

    def test_not_detected_no_feasibility_call(self):
        code = """
low, high = 0, n
while low < high:
    mid = (low + high) // 2
    if arr[mid] < target:
        low = mid + 1
    else:
        high = mid
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestHeapPriorityQueueDetector:
    def setup_method(self):
        self.detector = HeapPriorityQueueDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "heap_top_k"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_heap(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_ordinary_list(self):
        code = "arr = [3, 1, 2]\narr.sort()"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_heappush(self):
        code = """
import heapq
heap = []
heapq.heappush(heap, 5)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "heap_push" for e in result.evidence)

    def test_detected_heappop(self):
        code = """
import heapq
val = heapq.heappop(heap)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "heap_pop" for e in result.evidence)

    def test_detected_heapify(self):
        code = """
import heapq
heapq.heapify(arr)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "heapify_call" for e in result.evidence)

    def test_detected_top_k_via_heappushpop(self):
        code = """
import heapq
heap = []
for num in nums:
    heapq.heappush(heap, num)
    if len(heap) > k:
        heapq.heappop(heap)
return heap
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence >= 0.60

    def test_detected_from_heapq_import(self):
        code = """
from heapq import heappush, heappop
heap = []
heappush(heap, 5)
val = heappop(heap)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence >= 0.60

    def test_detected_nlargest(self):
        code = """
import heapq
result = heapq.nlargest(3, arr)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "nlargest_nsmallest" for e in result.evidence)

    def test_not_detected_sort_as_heap(self):
        code = "result = sorted(arr)[:k]"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestMonotonicStackDetector:
    def setup_method(self):
        self.detector = MonotonicStackDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "monotonic_stack"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_loop(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_empty_stack_no_ops(self):
        code = """
stack = []
x = stack.pop()
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_ordinary_push_pop(self):
        code = """
stack = []
stack.append(1)
stack.pop()
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_daily_temperatures(self):
        code = """
stack = []
result = [0] * len(temperatures)
for i in range(len(temperatures)):
    while stack and temperatures[stack[-1]] < temperatures[i]:
        idx = stack.pop()
        result[idx] = i - idx
    stack.append(i)
return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "monotonic_pop" for e in result.evidence)
        assert any(e.type == "stack_push" for e in result.evidence)

    def test_detected_next_greater_element(self):
        code = """
stack = []
result = [-1] * len(nums)
for i in range(len(nums)):
    while stack and nums[stack[-1]] < nums[i]:
        idx = stack.pop()
        result[idx] = nums[i]
    stack.append(i)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_detected_stock_span(self):
        code = """
stack = []
result = []
for i in range(len(prices)):
    while stack and prices[stack[-1]] <= prices[i]:
        stack.pop()
    result.append(i - stack[-1] if stack else i + 1)
    stack.append(i)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

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


class TestMonotonicQueueDetector:
    def setup_method(self):
        self.detector = MonotonicQueueDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "monotonic_deque"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_loop(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_ordinary_deque(self):
        code = """
from collections import deque
dq = deque()
dq.append(1)
x = dq.popleft()
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_sliding_window_maximum(self):
        code = """
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
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "monotonic_pop" for e in result.evidence)
        assert any(e.type == "queue_append" for e in result.evidence)

    def test_detected_sliding_window_minimum(self):
        code = """
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
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_detected_deque_count_bits(self):
        code = """
from collections import deque
q = deque()
for i in range(n):
    while q and condition:
        q.pop()
    q.append(i)
    q.popleft()
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_not_detected_for_loop_only(self):
        code = "for i in range(10):\n    print(i)"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_stack_pattern(self):
        code = """
stack = []
for i in range(len(arr)):
    while stack and arr[stack[-1]] < arr[i]:
        stack.pop()
    stack.append(i)
"""
        result = self.detector.detect(ast.parse(code))
        # This is a stack, not a deque -- should not trigger monotonic queue
        assert result.detected == False

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected
