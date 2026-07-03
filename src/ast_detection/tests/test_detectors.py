"""Tests for detector implementations in Batch 1."""

import ast
from src.ast_detection.detectors.hash_map_lookup import HashMapLookupDetector
from src.ast_detection.detectors.array_traversal import ArrayTraversalDetector
from src.ast_detection.detectors.sorting import SortingDetector
from src.ast_detection.detectors.brute_force import BruteForceDetector
from src.ast_detection.detectors.frequency_counting import FrequencyCountingDetector
from src.ast_detection.detector_interface import DetectionResult


class TestHashMapLookupDetector:
    def setup_method(self):
        self.detector = HashMapLookupDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "hash_map_lookup"

    def test_detect_returns_detection_result(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert isinstance(result, DetectionResult)

    def test_not_detected_no_dict(self):
        ast_root = ast.parse("x = 1")
        result = self.detector.detect(ast_root)
        assert result.detected == False

    def test_not_detected_config_dict(self):
        code = "config = {'key': 'value'}"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_membership_no_loop(self):
        code = "seen = {}\nx = 1 in y"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_dict_membership_loop(self):
        code = """
seen = {}
for item in items:
    if item in seen:
        print(item)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert len(result.evidence) >= 3

    def test_detected_set_creation(self):
        code = """
seen = set()
for item in items:
    if item in seen:
        print(item)
    seen.add(item)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detected_with_dict(self):
        code = """
seen = dict()
for item in items:
    if item not in seen:
        seen[item] = True
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_not_detected_set_no_loop(self):
        code = "seen = set()\nx = 1 in seen"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_dict_loop_no_membership(self):
        code = """
seen = {}
for item in items:
    seen[item] = True
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_literal_dict_loop_membership(self):
        code = """
d = {1: 'a', 2: 'b'}
for k in keys:
    if k in d:
        print(k)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_list_comp_membership(self):
        code = """
seen = set(nums1)
result = [x for x in nums2 if x in seen]
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detected_dict_comp_membership(self):
        code = """
lookup = {x: i for i, x in enumerate(nums1)}
result = {k: lookup[k] for k in nums2 if k in lookup}
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_not_detected_set_comp_no_membership(self):
        code = "seen = {x for x in items}"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_list_comp_no_membership(self):
        code = "result = [x for x in items if x > 0]"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
        assert result1.detected == result2.detected


class TestArrayTraversalDetector:
    def setup_method(self):
        self.detector = ArrayTraversalDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "array_traversal"

    def test_not_detected_no_loop(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_range_loop_only(self):
        code = "for i in range(10):\n    print(i)"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_for_loop_no_subscript(self):
        code = "for x in items:\n    pass"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_traversal_with_subscript(self):
        code = "for i in range(len(arr)):\n    print(arr[i])"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detected_with_element_update(self):
        code = """
for i in range(n):
    arr[i] = arr[i] * 2
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detected_collection_loop_with_subscript(self):
        code = """
for i in range(len(arr)):
    if arr[i] > 0:
        result.append(arr[i])
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence


    def test_not_detected_while_loop_subscript(self):
        code = """
i = 0
while i < len(arr):
    print(arr[i])
    i += 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_enumerate_no_subscript(self):
        code = "for i, x in enumerate(arr):\n    print(x)"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_subscript_no_loop(self):
        code = "x = arr[0]"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_element_usage_sum(self):
        code = """
total = 0
for num in nums:
    total += num
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detected_element_usage_append(self):
        code = """
result = []
for x in arr:
    result.append(x)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detected_element_usage_filter(self):
        code = """
result = []
for x in arr:
    if x > 0:
        result.append(x)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detected_enumerate_subscript(self):
        code = """
for i, val in enumerate(arr):
    result[i] = val * 2
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_not_detected_loop_variable_unused_body(self):
        code = "for x in items:\n    pass"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_enumerate_element_unused(self):
        code = "for i, x in enumerate(arr):\n    pass"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False


class TestSortingDetector:
    def setup_method(self):
        self.detector = SortingDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "sorting"

    def test_not_detected_no_sort(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_detected_sort_method(self):
        code = "arr.sort()"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence >= 0.40
        assert any(e.type == "sort_method_call" for e in result.evidence)

    def test_detected_sorted_function(self):
        code = "result = sorted(arr)"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence >= 0.40
        assert any(e.type == "sorted_function_call" for e in result.evidence)

    def test_detected_sort_with_key(self):
        code = "arr.sort(key=lambda x: x[1])"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence >= 0.60
        assert any(e.type == "custom_sort_key" for e in result.evidence)

    def test_detected_multiple_signals(self):
        code = "result = sorted(arr, key=lambda x: len(x))"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence >= 0.60

    def test_detected_sorted_inside_comprehension(self):
        code = "result = [sorted(x) for x in data]"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence


class TestBruteForceDetector:
    def setup_method(self):
        self.detector = BruteForceDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "brute_force"

    def test_not_detected_simple_code(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_single_loop(self):
        code = "for i in range(10):\n    print(i)"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_just_range(self):
        code = "for i in range(len(arr)):\n    print(arr[i])"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_nested_loops(self):
        code = """
for i in range(n):
    for j in range(n):
        print(i, j)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "nested_loops" for e in result.evidence)

    def test_detected_nested_with_pair_check(self):
        code = """
for i in range(n):
    for j in range(i + 1, n):
        if arr[i] == arr[j]:
            print(i, j)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence >= 0.40

    def test_detected_recursive_branching(self):
        code = """
def solve(arr):
    if len(arr) == 1:
        return arr
    results = []
    for i in range(len(arr)):
        sub = solve(arr[:i] + arr[i+1:])
        for s in sub:
            results.append([arr[i]] + s)
    return results
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_not_detected_single_recursion(self):
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_two_sequential_loops(self):
        code = """
for i in range(n):
    print(i)
for j in range(m):
    print(j)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_recursive_with_loop(self):
        code = """
def solve(n):
    if n <= 1:
        return n
    total = 0
    for i in range(n):
        total += solve(i)
    return total
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detected_recursive_nested_function(self):
        code = """
def outer():
    def backtrack(start, path):
        result.append(path[:])
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()
    backtrack(0, [])
    return result
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence


    def test_not_detected_reversed(self):
        code = "result = list(reversed(arr))"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False


class TestFrequencyCountingDetector:
    def setup_method(self):
        self.detector = FrequencyCountingDetector()

    def test_pattern_id(self):
        assert self.detector.pattern_id == "hash_map_frequency"

    def test_not_detected_no_counting(self):
        result = self.detector.detect(ast.parse("x = 1"))
        assert result.detected == False

    def test_not_detected_static_dict(self):
        code = "config = {'key': 'value'}"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_empty_dict_no_loop(self):
        code = "counts = {}"
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detected_increment_pattern(self):
        code = """
counts = {}
for item in items:
    counts[item] = counts.get(item, 0) + 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0
        assert any(e.type == "frequency_increment" for e in result.evidence)

    def test_detected_counter_import(self):
        code = """
from collections import Counter
data = [1, 2, 2, 3]
counts = Counter(data)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert any(e.type == "counter_import" for e in result.evidence)

    def test_not_detected_lookup_without_counting(self):
        code = """
seen = {}
for item in items:
    if item in seen:
        print('found')
"""
        result = self.detector.detect(ast.parse(code))
        # This has dict creation + loop but no frequency increment, so
        # it should NOT match frequency_counting (it's hash_map_lookup territory)
        assert result.detected == False

    def test_detected_defaultdict(self):
        code = """
from collections import defaultdict
counts = defaultdict(int)
for item in items:
    counts[item] += 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True

    def test_detected_dict_loop_increment(self):
        code = """
counts = dict()
for x in data:
    counts[x] = counts.get(x, 0) + 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == True
        assert result.confidence > 0.0

    def test_not_detected_dict_get_no_increment(self):
        code = """
counts = {}
for item in items:
    val = counts.get(item)
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_counter_as_lookup(self):
        code = """
from collections import Counter
data = Counter()
x = data.get('key')
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_not_detected_augmented_assign_no_dict(self):
        code = """
x = 0
for item in items:
    x += 1
"""
        result = self.detector.detect(ast.parse(code))
        assert result.detected == False

    def test_detect_is_deterministic(self):
        ast_root = ast.parse("x = 1")
        result1 = self.detector.detect(ast_root)
        result2 = self.detector.detect(ast_root)
        assert result1.confidence == result2.confidence
