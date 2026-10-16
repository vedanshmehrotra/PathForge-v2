"""Tests for shadow-mode hybrid detector (Experiment 2C)."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.ast_detection.semantic.shadow_detector import ShadowDetector, FUSION_POLICIES


@pytest.fixture
def shadow():
    return ShadowDetector()


class TestTwoPointersFusion:
    """two_pointers_opposite: semantic-primary policy."""

    def test_semantic_recovery_visible(self, shadow):
        """Semantic-only detection should appear in shadow output."""
        # Code that semantic detects but AST may miss (expression variant)
        code = """
def twoSum_sorted(nums, target):
    left = 0
    right = len(nums) - 1
    while left < right:
        total = nums[left] + nums[right]
        if total == target:
            return [left, right]
        elif total < target:
            left = left + 1
        else:
            right = right - 1
    return []
"""
        result = shadow.analyze_safe(code)
        assert result is not None
        # Check that semantic score is computed
        assert "two_pointers_opposite" in result.semantic_scores
        # Check hybrid detection
        assert "two_pointers_opposite" in result.hybrid_detections
        # Policy should be semantic_primary
        assert result.policy_summary.get("two_pointers_opposite") == "semantic_primary"

    def test_production_result_unchanged(self, shadow):
        """Shadow analysis must not modify the AST engine output."""
        code = """
def twoSum_sorted(nums, target):
    left, right = 0, len(nums) - 1
    while left < right:
        s = nums[left] + nums[right]
        if s == target:
            return [left, right]
        elif s < target:
            left += 1
        else:
            right -= 1
    return []
"""
        # Get production result first
        from src.ast_detection.run_analysis import ASTAnalysisEngine
        engine = ASTAnalysisEngine()
        prod_result = engine.analyze(code)

        # Run shadow
        shadow_result = shadow.analyze_safe(code)

        # Production detection results must be identical (ignore timestamp)
        assert prod_result["detected_patterns"] == shadow_result.ast_result["detected_patterns"]
        assert prod_result["patterns_detected"] == shadow_result.ast_result["patterns_detected"]

    def test_fusion_policy_applied(self, shadow):
        """Hybrid should use OR logic: sem_detected OR ast_detected."""
        code = """
def f(nums):
    left, right = 0, len(nums) - 1
    while left < right:
        if nums[left] + nums[right] == 0:
            return True
        left += 1
        right -= 1
    return False
"""
        result = shadow.analyze_safe(code)
        assert result is not None
        # At least one of AST or semantic should detect
        dp = [d for d in result.discrepancies if d.pattern_id == "two_pointers_opposite"][0]
        assert dp.fusion_policy == "semantic_primary"
        # Hybrid = sem OR ast
        expected = dp.sem_detected or dp.ast_detected
        assert result.hybrid_detections["two_pointers_opposite"] == expected


class TestPrefixSumFusion:
    """prefix_sum: AST-primary + semantic gaps policy."""

    def test_semantic_gap_visible(self, shadow):
        """Semantic gap detection should appear when AST is silent."""
        # Code with append-based prefix sum (AST may miss)
        code = """
def prefixSum(nums):
    prefix = [0]
    for num in nums:
        prefix.append(prefix[-1] + num)
    return prefix
"""
        result = shadow.analyze_safe(code)
        assert result is not None
        assert "prefix_sum" in result.semantic_scores
        dp = [d for d in result.discrepancies if d.pattern_id == "prefix_sum"][0]
        assert dp.fusion_policy == "ast_primary_semantic_gaps"

    def test_production_result_unchanged(self, shadow):
        """Shadow analysis must not modify production output."""
        code = """
def runningSum(nums):
    result = []
    total = 0
    for num in nums:
        total += num
        result.append(total)
    return result
"""
        from src.ast_detection.run_analysis import ASTAnalysisEngine
        engine = ASTAnalysisEngine()
        prod_result = engine.analyze(code)
        shadow_result = shadow.analyze_safe(code)
        assert prod_result["detected_patterns"] == shadow_result.ast_result["detected_patterns"]

    def test_fusion_logic(self, shadow):
        """Hybrid = ast_detected OR (sem_detected AND ast_confidence == 0)."""
        code = """
def prefix(arr):
    n = len(arr)
    prefix = [0] * (n + 1)
    for i in range(1, n + 1):
        prefix[i] = prefix[i - 1] + arr[i - 1]
    return prefix
"""
        result = shadow.analyze_safe(code)
        dp = [d for d in result.discrepancies if d.pattern_id == "prefix_sum"][0]
        expected = dp.ast_detected or (dp.sem_detected and dp.ast_confidence == 0)
        assert result.hybrid_detections["prefix_sum"] == expected


class TestHashMapLookupFusion:
    """hash_map_lookup: agreement policy."""

    def test_agreement_filtering_visible(self, shadow):
        """Agreement filtering should be visible in shadow output."""
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
        result = shadow.analyze_safe(code)
        dp = [d for d in result.discrepancies if d.pattern_id == "hash_map_lookup"][0]
        assert dp.fusion_policy == "agreement"

    def test_production_result_unchanged(self, shadow):
        """Shadow analysis must not modify production output."""
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
        from src.ast_detection.run_analysis import ASTAnalysisEngine
        engine = ASTAnalysisEngine()
        prod_result = engine.analyze(code)
        shadow_result = shadow.analyze_safe(code)
        assert prod_result["detected_patterns"] == shadow_result.ast_result["detected_patterns"]

    def test_fusion_logic(self, shadow):
        """Hybrid = ast_detected AND sem_detected."""
        code = """
def has_common(nums1, nums2):
    seen = set(nums1)
    for num in nums2:
        if num in seen:
            return True
    return False
"""
        result = shadow.analyze_safe(code)
        dp = [d for d in result.discrepancies if d.pattern_id == "hash_map_lookup"][0]
        expected = dp.ast_detected and dp.sem_detected
        assert result.hybrid_detections["hash_map_lookup"] == expected


class TestArrayTraversalFusion:
    """array_traversal: AST-only policy."""

    def test_hybrid_identical_to_ast(self, shadow):
        """Hybrid result must be identical to AST-only for array_traversal."""
        code = """
def traverse(arr):
    result = []
    for i in range(len(arr)):
        result.append(arr[i] * 2)
    return result
"""
        result = shadow.analyze_safe(code)
        dp = [d for d in result.discrepancies if d.pattern_id == "array_traversal"][0]
        assert dp.fusion_policy == "ast_only"
        # Hybrid must equal AST
        assert result.hybrid_detections["array_traversal"] == dp.ast_detected

    def test_no_semantic_promotion(self, shadow):
        """Semantic detection must NOT promote array_traversal."""
        code = """
def f(nums):
    total = 0
    for num in nums:
        total += num
    return total
"""
        result = shadow.analyze_safe(code)
        dp = [d for d in result.discrepancies if d.pattern_id == "array_traversal"][0]
        # Even if semantic detects, hybrid must follow AST
        assert result.hybrid_detections["array_traversal"] == dp.ast_detected


class TestSafetyInvariants:
    """Verify shadow mode cannot affect production."""

    def test_semantic_failure_fallback(self, shadow):
        """Semantic analysis failure must fall back silently."""
        # Invalid code that may cause semantic analysis to fail
        code = "def f("
        result = shadow.analyze_safe(code)
        # Should not crash, may return None or fallback result
        # Either way, no exception
        assert result is None or isinstance(result, type(shadow.analyze_safe("x")))

    def test_no_persistence_side_effects(self, shadow):
        """Shadow analysis must not write to any database or file."""
        code = """
def f(nums):
    return sum(nums)
"""
        # This should complete without any I/O side effects
        result = shadow.analyze_safe(code)
        assert result is not None
        # Verify no files were created (basic check)
        assert not os.path.exists("shadow_output.json")

    def test_code_not_stored(self, shadow):
        """Source code must not be stored in shadow results."""
        code = "secret_password = 'hunter2'"
        result = shadow.analyze_safe(code)
        assert result is not None
        # Only hash should be stored, not the code
        assert result.code_hash != code
        assert len(result.code_hash) == 12  # SHA256 truncated

    def test_latency_measured(self, shadow):
        """Shadow results must include latency measurements."""
        code = "x = 1"
        result = shadow.analyze_safe(code)
        assert result.ast_latency_ms >= 0
        assert result.sem_latency_ms >= 0
        assert result.total_latency_ms >= 0

    def test_all_four_policies_represented(self, shadow):
        """Each target pattern must have a defined fusion policy."""
        assert set(FUSION_POLICIES.keys()) == {
            "two_pointers_opposite",
            "prefix_sum",
            "hash_map_lookup",
            "array_traversal",
        }
