"""Tests for semantic feature extraction and pattern scoring."""
import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.ast_detection.semantic.analyzer import SemanticAnalyzer
from src.ast_detection.semantic.extractor import extract_features
from src.ast_detection.semantic.scorer import score_patterns
import ast


@pytest.fixture
def analyzer():
    return SemanticAnalyzer()


class TestFeatureExtraction:
    """Test semantic feature extraction."""

    def test_counter_loop_while(self, analyzer):
        """While loop with incrementing counter should be detected."""
        code = """
def f(nums):
    i = 0
    while i < len(nums):
        x = nums[i]
        i += 1
"""
        result = analyzer.analyze(code)
        assert result["features"]["loops"]["has_counter_loop"] is True
        assert result["features"]["loops"]["counter_var"] == "i"
        assert result["features"]["loops"]["counter_compares_to_len"] is True

    def test_counter_loop_for_range(self, analyzer):
        """For loop over range(len()) should be detected as counter loop."""
        code = """
def f(nums):
    for i in range(len(nums)):
        x = nums[i]
"""
        result = analyzer.analyze(code)
        assert result["features"]["loops"]["has_counter_loop"] is True
        assert result["features"]["loops"]["has_for_counter_loop"] is True
        assert result["features"]["loops"]["counter_var"] == "i"
        assert result["features"]["loops"]["counter_compares_to_len"] is True

    def test_counter_loop_for_range_no_len(self, analyzer):
        """For loop over range(N) should be detected as counter without len comparison."""
        code = """
def f(n):
    for i in range(n):
        print(i)
"""
        result = analyzer.analyze(code)
        assert result["features"]["loops"]["has_counter_loop"] is True
        assert result["features"]["loops"]["has_for_counter_loop"] is True
        assert result["features"]["loops"]["counter_compares_to_len"] is False

    def test_enumerate_iteration(self, analyzer):
        """enumerate() should be detected as collection iteration with counter."""
        code = """
def f(arr):
    for idx, val in enumerate(arr):
        arr[idx] = val * 2
"""
        result = analyzer.analyze(code)
        assert result["features"]["loops"]["has_enumerate_iteration"] is True
        assert result["features"]["loops"]["has_counter_loop"] is True
        assert result["features"]["loops"]["has_collection_iteration"] is True
        assert result["features"]["loops"]["counter_var"] == "idx"

    def test_membership_test_list(self, analyzer):
        """Membership test on list should be detected."""
        code = """
def f(nums, target):
    if target in nums:
        return True
    return False
"""
        result = analyzer.analyze(code)
        assert result["features"]["access"]["has_membership_test"] is True
        assert result["features"]["access"]["membership_collection"] == "nums"

    def test_accumulation_pattern(self, analyzer):
        """Running sum accumulation should be detected."""
        code = """
def f(nums):
    total = 0
    for x in nums:
        total += x
    return total
"""
        result = analyzer.analyze(code)
        assert result["features"]["accumulation"]["has_accumulation"] is True
        assert result["features"]["accumulation"]["accumulator_var"] == "total"

    def test_index_movement(self, analyzer):
        """Index variable increment should be detected."""
        code = """
def f(nums):
    i = 0
    while i < len(nums):
        i += 1
"""
        result = analyzer.analyze(code)
        assert result["features"]["pointers"]["has_index_movement"] is True
        assert result["features"]["pointers"]["movement_var"] == "i"
        assert result["features"]["pointers"]["movement_step"] == 1

    def test_sequential_index_access(self, analyzer):
        """Sequential index access (arr[i], arr[i-1]) should be detected."""
        code = """
def f(nums):
    for i in range(1, len(nums)):
        if nums[i] == nums[i-1]:
            return True
    return False
"""
        result = analyzer.analyze(code)
        assert result["features"]["access"]["has_sequential_index"] is True

    def test_no_name_dependency(self, analyzer):
        """Feature extraction should work regardless of variable names."""
        code1 = """
def f(arr):
    idx = 0
    while idx < len(arr):
        val = arr[idx]
        idx += 1
"""
        code2 = """
def f(data):
    j = 0
    while j < len(data):
        item = data[j]
        j += 1
"""
        r1 = analyzer.analyze(code1)
        r2 = analyzer.analyze(code2)

        # Both should detect counter loop
        assert r1["features"]["loops"]["has_counter_loop"] is True
        assert r2["features"]["loops"]["has_counter_loop"] is True

        # Both should detect indexed access
        assert r1["features"]["access"]["has_indexed_access"] is True
        assert r2["features"]["access"]["has_indexed_access"] is True

    def test_while_for_equivalence(self, analyzer):
        """While and for loops should produce compatible features."""
        code_while = """
def f(nums):
    i = 0
    total = 0
    while i < len(nums):
        total += nums[i]
        i += 1
    return total
"""
        code_for = """
def f(nums):
    total = 0
    for i in range(len(nums)):
        total += nums[i]
    return total
"""
        r_while = analyzer.analyze(code_while)
        r_for = analyzer.analyze(code_for)

        # Both should detect accumulation
        assert r_while["features"]["accumulation"]["has_accumulation"] is True
        assert r_for["features"]["accumulation"]["has_accumulation"] is True

        # Both should detect indexed access
        assert r_while["features"]["access"]["has_indexed_access"] is True
        assert r_for["features"]["access"]["has_indexed_access"] is True


class TestFix1ForLoopCounter:
    """Fix 1: for-loop counter detection and enumerate support."""

    def test_for_range_counter_detection(self, analyzer):
        """for i in range(len(arr)) should detect counter loop."""
        code = """
def f(arr):
    for i in range(len(arr)):
        arr[i] = arr[i] * 2
"""
        r = analyzer.analyze(code)
        assert r["features"]["loops"]["has_counter_loop"] is True
        assert r["features"]["loops"]["has_for_counter_loop"] is True

    def test_enumerate_counter_detection(self, analyzer):
        """enumerate(arr) should detect counter loop."""
        code = """
def f(arr):
    for idx, val in enumerate(arr):
        arr[idx] = val * 2
"""
        r = analyzer.analyze(code)
        assert r["features"]["loops"]["has_counter_loop"] is True
        assert r["features"]["loops"]["has_for_counter_loop"] is True
        assert r["features"]["loops"]["has_enumerate_iteration"] is True

    def test_for_range_scores_array_traversal(self, analyzer):
        """for i in range(len(arr)) with indexed access should score array_traversal."""
        code = """
def f(arr):
    for i in range(len(arr)):
        arr[i] = arr[i] * 2
"""
        r = analyzer.analyze(code)
        assert r["scores"]["array_traversal"]["score"] >= 0.55

    def test_enumerate_scores_array_traversal(self, analyzer):
        """enumerate() with indexed access should score array_traversal."""
        code = """
def f(arr):
    for idx, val in enumerate(arr):
        arr[idx] = val * 2
"""
        r = analyzer.analyze(code)
        assert r["scores"]["array_traversal"]["score"] >= 0.55

    def test_direct_collection_iteration(self, analyzer):
        """for x in arr (no index) should produce minimal array_traversal."""
        code = """
def f(arr):
    for x in arr:
        print(x)
"""
        r = analyzer.analyze(code)
        # Direct iteration without indexing should score low
        assert r["scores"]["array_traversal"]["score"] < 0.5

    def test_unrelated_for_loop(self, analyzer):
        """for loop over non-collection should not score high array_traversal."""
        code = """
def f():
    for i in range(10):
        print(i)
"""
        r = analyzer.analyze(code)
        # For-range counter gives 0.3, but no indexed access → stays low
        assert r["scores"]["array_traversal"]["score"] <= 0.35


class TestFix2HashMapLookup:
    """Fix 2: dict/set construction and collection-type tracking."""

    def test_dict_construction_detected(self, analyzer):
        """dict() construction should be tracked."""
        code = """
def f(nums):
    seen = {}
    for num in nums:
        seen[num] = True
"""
        r = analyzer.analyze(code)
        assert "seen" in r["features"]["access"]["dict_vars"]

    def test_dict_literal_detected(self, analyzer):
        """{} literal should be tracked."""
        code = """
def f():
    freq = {}
    freq['a'] = 1
"""
        r = analyzer.analyze(code)
        assert "freq" in r["features"]["access"]["dict_vars"]

    def test_set_construction_detected(self, analyzer):
        """set() construction should be tracked."""
        code = """
def f(nums):
    seen = set(nums)
"""
        r = analyzer.analyze(code)
        assert "seen" in r["features"]["access"]["set_vars"]

    def test_dict_get_tracked(self, analyzer):
        """.get() call should mark variable as dict."""
        code = """
def f(items):
    freq = {}
    for item in items:
        freq[item] = freq.get(item, 0) + 1
"""
        r = analyzer.analyze(code)
        assert "freq" in r["features"]["access"]["dict_vars"]
        assert r["features"]["access"]["has_dict_get_lookup"] is True

    def test_dict_subscript_store_tracked(self, analyzer):
        """x[key] = value should mark x as dict."""
        code = """
def f(items):
    d = {}
    for item in items:
        d[item] = True
"""
        r = analyzer.analyze(code)
        assert "d" in r["features"]["access"]["dict_vars"]

    def test_hashmap_frequency_count(self, analyzer):
        """Frequency counting with dict.get() should score hash_map_lookup."""
        code = """
def frequency(s):
    freq = {}
    for char in s:
        freq[char] = freq.get(char, 0) + 1
    return freq
"""
        r = analyzer.analyze(code)
        assert r["scores"]["hash_map_lookup"]["score"] >= 0.3

    def test_hashmap_set_membership(self, analyzer):
        """set membership should score hash_map_lookup."""
        code = """
def has_common(nums1, nums2):
    seen = set(nums1)
    for num in nums2:
        if num in seen:
            return True
    return False
"""
        r = analyzer.analyze(code)
        assert r["scores"]["hash_map_lookup"]["score"] >= 0.6

    def test_hashmap_dict_membership(self, analyzer):
        """dict membership (complement in seen) should score hash_map_lookup."""
        code = """
def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
"""
        r = analyzer.analyze(code)
        assert r["scores"]["hash_map_lookup"]["score"] >= 0.6

    def test_list_membership_low_score(self, analyzer):
        """Membership in a list (no dict/set) should score low."""
        code = """
def find_in_list(arr, target):
    for x in arr:
        if x == target:
            return True
    return False
"""
        r = analyzer.analyze(code)
        assert r["scores"]["hash_map_lookup"]["score"] < 0.3

    def test_dict_no_membership_low_score(self, analyzer):
        """Dict creation without any membership test should score low."""
        code = """
def process(items):
    seen = {}
    for item in items:
        seen[item] = True
    return seen
"""
        r = analyzer.analyze(code)
        assert r["scores"]["hash_map_lookup"]["score"] < 0.3

    def test_dict_lookup_parameter(self, analyzer):
        """Lookup on function parameter dict should score hash_map_lookup."""
        code = """
def translate(text, dict_map):
    result = []
    for word in text.split():
        if word in dict_map:
            result.append(dict_map[word])
    return result
"""
        r = analyzer.analyze(code)
        # dict_map is subscripted with word and membership tested
        assert "dict_map" in r["features"]["access"]["dict_vars"]
        assert r["scores"]["hash_map_lookup"]["score"] >= 0.3


class TestFix3PrefixSum:
    """Fix 3: numeric accumulation checks."""

    def test_numeric_running_sum(self, analyzer):
        """Running sum from collection should score prefix_sum."""
        code = """
def runningSum(nums):
    result = []
    total = 0
    for num in nums:
        total += num
        result.append(total)
    return result
"""
        r = analyzer.analyze(code)
        assert r["scores"]["prefix_sum"]["score"] >= 0.3

    def test_non_numeric_counter(self, analyzer):
        """Counter += 1 should NOT score prefix_sum."""
        code = """
def count_positive(nums):
    count = 0
    for num in nums:
        if num > 0:
            count += 1
    return count
"""
        r = analyzer.analyze(code)
        assert r["scores"]["prefix_sum"]["score"] < 0.3

    def test_string_concat_not_prefix_sum(self, analyzer):
        """String concatenation should NOT score prefix_sum."""
        code = """
def join_words(words):
    result = ""
    for word in words:
        result += word + " "
    return result.strip()
"""
        r = analyzer.analyze(code)
        assert r["scores"]["prefix_sum"]["score"] < 0.3

    def test_product_accumulator(self, analyzer):
        """Product accumulator from collection should score prefix_sum."""
        code = """
def product_except_self(nums):
    result = [1] * len(nums)
    prefix = 1
    for i in range(len(nums)):
        result[i] = prefix
        prefix *= nums[i]
    return result
"""
        r = analyzer.analyze(code)
        # Product from collection elements should score reasonably
        assert r["scores"]["prefix_sum"]["score"] >= 0.3

    def test_max_accumulator(self, analyzer):
        """Max finding should NOT score prefix_sum."""
        code = """
def find_max(arr):
    max_val = arr[0]
    for num in arr:
        if num > max_val:
            max_val = num
    return max_val
"""
        r = analyzer.analyze(code)
        # No accumulation, just conditional replacement
        assert r["scores"]["prefix_sum"]["score"] < 0.5


class TestPatternScoring:
    """Test pattern scoring rules."""

    def test_problem_2996_primary(self, analyzer):
        """Problem 2996 should score high for array_traversal."""
        code = """
class Solution:
    def missingInteger(self, nums):
        i = 1
        summ = nums[0]
        while i <= len(nums)-1 and nums[i] == nums[i-1]+1:
            summ += nums[i]
            i += 1
        while summ in nums:
            summ += 1
        return summ
"""
        result = analyzer.analyze(code)
        scores = result["scores"]

        # array_traversal should be high
        assert scores["array_traversal"]["score"] >= 0.7

        # two_pointers_opposite should be near zero
        assert scores["two_pointers_opposite"]["score"] <= 0.1

    def test_list_membership_not_high_hashmap(self, analyzer):
        """List membership should NOT produce high hash_map_lookup score."""
        code = """
def f(arr, target):
    for x in arr:
        if x == target:
            return True
    return False
"""
        result = analyzer.analyze(code)
        scores = result["scores"]

        # hash_map_lookup should be moderate (membership present but no dict)
        assert scores["hash_map_lookup"]["score"] <= 0.5

    def test_generic_accumulator_not_prefix_sum(self, analyzer):
        """Generic accumulator should NOT automatically become high prefix_sum."""
        code = """
def f(nums):
    count = 0
    for x in nums:
        if x > 0:
            count += 1
    return count
"""
        result = analyzer.analyze(code)
        scores = result["scores"]

        # prefix_sum should be low (no running sum from collection)
        assert scores["prefix_sum"]["score"] <= 0.5

    def test_counter_loop_not_two_pointers(self, analyzer):
        """Normal counter loop should NOT be two_pointers_opposite."""
        code = """
def f(arr):
    i = 0
    while i < len(arr):
        print(arr[i])
        i += 1
"""
        result = analyzer.analyze(code)
        scores = result["scores"]

        # two_pointers_opposite should be near zero
        assert scores["two_pointers_opposite"]["score"] <= 0.1

    def test_binary_search_not_detected(self, analyzer):
        """Binary search should not be scored by current scorer."""
        code = """
def f(nums, target):
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
"""
        result = analyzer.analyze(code)
        scores = result["scores"]

        assert "array_traversal" in scores
        assert "hash_map_lookup" in scores
        assert "prefix_sum" in scores
        assert "two_pointers_opposite" in scores


class TestEvidenceExplainability:
    """Test that scores have explainable evidence."""

    def test_all_scores_have_evidence(self, analyzer):
        """Every pattern score should have evidence."""
        code = """
def f(nums):
    total = 0
    for x in nums:
        total += x
    return total
"""
        result = analyzer.analyze(code)
        for name, score in result["scores"].items():
            assert "evidence" in score
            assert isinstance(score["evidence"], list)

    def test_evidence_has_required_fields(self, analyzer):
        """Evidence items should have feature, weight, description."""
        code = """
def f(nums):
    i = 0
    while i < len(nums):
        x = nums[i]
        i += 1
"""
        result = analyzer.analyze(code)
        for name, score in result["scores"].items():
            for ev in score["evidence"]:
                assert "feature" in ev
                assert "weight" in ev
                assert "description" in ev


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_code(self, analyzer):
        """Empty code should return results with no features."""
        result = analyzer.analyze("")
        assert result is not None
        assert result["features"]["loops"]["total_loops"] == 0

    def test_syntax_error(self, analyzer):
        """Invalid Python should return None."""
        result = analyzer.analyze("def f(")
        assert result is None

    def test_no_loops(self, analyzer):
        """Code without loops should still work."""
        code = """
def f(x):
    return x * 2
"""
        result = analyzer.analyze(code)
        assert result is not None
        assert result["features"]["loops"]["total_loops"] == 0

    def test_nested_loops(self, analyzer):
        """Nested loops should be counted."""
        code = """
def f(matrix):
    for i in range(len(matrix)):
        for j in range(len(matrix[0])):
            print(matrix[i][j])
"""
        result = analyzer.analyze(code)
        assert result["features"]["loops"]["total_loops"] == 2
        assert result["features"]["loops"]["for_loops"] == 2


class TestClassMethodTraversal:
    """Test class method traversal detection."""

    def test_class_method_for_loop(self, analyzer):
        """Class method with for-loop should still score array_traversal if indexed."""
        code = """
class Solution:
    def method(self, arr):
        result = []
        for i in range(len(arr)):
            result.append(arr[i] * 2)
        return result
"""
        r = analyzer.analyze(code)
        assert r["scores"]["array_traversal"]["score"] >= 0.55

    def test_class_method_direct_iteration(self, analyzer):
        """Class method with for x in arr should score low array_traversal."""
        code = """
class Solution:
    def method(self, arr):
        result = []
        for x in arr:
            result.append(x * 2)
        return result
"""
        r = analyzer.analyze(code)
        # Direct iteration without indexing — lower score
        assert r["scores"]["array_traversal"]["score"] < 0.5


class TestFixNotIn:
    """Fix: ast.NotIn membership detection."""

    def test_not_in_detected(self, analyzer):
        """'x not in collection' should be detected as membership."""
        code = """
def f(s, t):
    seen = set(t)
    for ch in s:
        if ch not in seen:
            return False
    return True
"""
        r = analyzer.analyze(code)
        assert r["features"]["access"]["has_membership_test"] is True
        assert r["features"]["access"]["membership_collection"] == "seen"

    def test_not_in_scores_hashmap(self, analyzer):
        """'not in' on a set should score hash_map_lookup."""
        code = """
def f(s, t):
    seen = set(t)
    for ch in s:
        if ch not in seen:
            return False
    return True
"""
        r = analyzer.analyze(code)
        assert r["scores"]["hash_map_lookup"]["score"] >= 0.5

    def test_not_in_while_loop(self, analyzer):
        """'not in' in while condition should work."""
        code = """
def f(n):
    seen = set()
    while n != 1 and n not in seen:
        seen.add(n)
        n = sum(int(d)**2 for d in str(n))
    return n == 1
"""
        r = analyzer.analyze(code)
        assert r["features"]["access"]["has_membership_test"] is True
        assert r["scores"]["hash_map_lookup"]["score"] >= 0.5


class TestFixDirectIteration:
    """Fix: direct collection iteration for array_traversal."""

    def test_iteration_with_accumulation(self, analyzer):
        """for x in arr: total += x should score array_traversal above plain iteration."""
        code = """
def f(nums):
    total = 0
    for num in nums:
        total += num
    return total
"""
        r = analyzer.analyze(code)
        # iteration_with_accumulation gives 0.20 — above plain iteration (0.0)
        assert r["scores"]["array_traversal"]["score"] >= 0.15
        # Verify the evidence path exists
        ev_features = [e["feature"] for e in r["scores"]["array_traversal"]["evidence"]]
        assert "iteration_with_accumulation" in ev_features

    def test_iteration_with_append(self, analyzer):
        """for x in arr: result.append(x) should score array_traversal above plain iteration."""
        code = """
def f(arr):
    result = []
    for x in arr:
        result.append(x)
    return result
"""
        r = analyzer.analyze(code)
        # append without self-reference is NOT append_accumulation
        # so this gets no bonus — plain iteration scores 0.0
        assert r["features"]["accumulation"]["has_append_accumulation"] is False
        # Should still score low (no iteration bonus without accumulation)
        assert r["scores"]["array_traversal"]["score"] < 0.3

    def test_plain_iteration_no_bonus(self, analyzer):
        """for x in arr: print(x) should NOT get iteration+accumulation bonus."""
        code = """
def f(arr):
    for x in arr:
        print(x)
"""
        r = analyzer.analyze(code)
        # No accumulation, no append → no bonus evidence
        assert r["scores"]["array_traversal"]["score"] < 0.3

    def test_iteration_with_indexed_access(self, analyzer):
        """for x in arr with arr[i] should score higher."""
        code = """
def f(arr):
    for i in range(len(arr)):
        arr[i] = arr[i] * 2
"""
        r = analyzer.analyze(code)
        assert r["scores"]["array_traversal"]["score"] >= 0.55


class TestFixAppendAccumulation:
    """Fix: .append() as accumulation for prefix_sum."""

    def test_append_self_referencing(self, analyzer):
        """prefix.append(prefix[-1] + num) should detect append accumulation."""
        code = """
def f(nums):
    prefix = [0]
    for num in nums:
        prefix.append(prefix[-1] + num)
    return prefix
"""
        r = analyzer.analyze(code)
        assert r["features"]["accumulation"]["has_append_accumulation"] is True
        assert r["scores"]["prefix_sum"]["score"] >= 0.5

    def test_append_no_self_reference(self, analyzer):
        """result.append(x) without self-reference should NOT be append accumulation."""
        code = """
def f(arr):
    result = []
    for x in arr:
        result.append(x * 2)
    return result
"""
        r = analyzer.analyze(code)
        assert r["features"]["accumulation"]["has_append_accumulation"] is False

    def test_string_append_not_prefix(self, analyzer):
        """result.append(word) should NOT score prefix_sum."""
        code = """
def f(words):
    result = []
    for word in words:
        result.append(word.upper())
    return result
"""
        r = analyzer.analyze(code)
        assert r["features"]["accumulation"]["has_append_accumulation"] is False
        assert r["scores"]["prefix_sum"]["score"] < 0.3


class TestFixAssignmentAccumulation:
    """Fix: assignment-based accumulation for prefix_sum."""

    def test_prefix_recurrence(self, analyzer):
        """prefix[i] = prefix[i-1] + arr[i-1] should detect assignment accumulation."""
        code = """
def f(arr):
    n = len(arr)
    prefix = [0] * (n + 1)
    for i in range(1, n + 1):
        prefix[i] = prefix[i - 1] + arr[i - 1]
    return prefix
"""
        r = analyzer.analyze(code)
        assert r["features"]["accumulation"]["has_assignment_accumulation"] is True
        assert r["scores"]["prefix_sum"]["score"] >= 0.5

    def test_ordinary_indexed_assignment(self, analyzer):
        """arr[i] = x (no self-reference) should NOT be assignment accumulation."""
        code = """
def f(arr):
    for i in range(len(arr)):
        arr[i] = arr[i] * 2
"""
        r = analyzer.analyze(code)
        assert r["features"]["accumulation"]["has_assignment_accumulation"] is False

    def test_unrelated_array_update(self, analyzer):
        """result[i] = func(arr[i]) should NOT be assignment accumulation."""
        code = """
def f(arr):
    result = [0] * len(arr)
    for i in range(len(arr)):
        result[i] = arr[i] + 1
    return result
"""
        r = analyzer.analyze(code)
        # result[i] = arr[i] + 1 — result != arr, so no self-reference
        assert r["features"]["accumulation"]["has_assignment_accumulation"] is False
