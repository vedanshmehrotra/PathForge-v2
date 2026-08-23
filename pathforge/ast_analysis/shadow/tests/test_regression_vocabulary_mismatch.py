"""Regression tests for the vocabulary mismatch bug fix.

Verifies:
1. Technique evidence can match solution groups without requiring strategy evidence
2. Legacy patterns are preserved for the production matcher
3. No false positive strategy assignments from unrelated techniques
4. UNRESOLVED remains non-punitive when no match exists
"""
import pytest

from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
from pathforge.services.ground_truth_builder import (
    PATTERN_TO_V1_MAPPING, _build_solution_groups,
)
from pathforge.services.problem_resolver import _load_ground_truth, _parse_json_field
from src.matching_engine.matching_engine import MatchingEngine


# ============================================================
# Test 1: Sequential accumulation matches prefix_sum-style group
# ============================================================

class TestSequentialAccumulationMatch:
    """Sequential accumulation should match solution groups requiring it."""

    def test_sequential_accumulation_confirms_with_correct_group(self):
        """A loop-based accumulation should match a group requiring sequential_accumulation."""
        code = """
def prefix_sum(nums):
    result = 0
    i = 0
    while i < len(nums):
        result += nums[i]
        i += 1
    return result
"""
        groups = [{
            "id": "group_0",
            "required": ["sequential_accumulation"],
            "optional": ["iterative_table_filling"],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }]
        result = run_shadow_analysis(code, solution_groups=groups)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "sequential_accumulation" in tech_ids
        assert result["match_outcome"]["outcome"] == "CONFIRMED"

    def test_sequential_accumulation_unresolved_without_group(self):
        """Without a matching solution group, result should be UNRESOLVED."""
        code = """
def accumulate(nums):
    total = 0
    for x in nums:
        total += x
    return total
"""
        result = run_shadow_analysis(code, solution_groups=None)
        assert result is not None
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_sequential_accumulation_does_not_become_binary_search(self):
        """sequential_accumulation must NOT produce binary_search strategy."""
        code = """
def prefix_sum(nums):
    result = 0
    i = 0
    while i < len(nums):
        result += nums[i]
        i += 1
    return result
"""
        result = run_shadow_analysis(code)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "binary_search" not in strat_ids
        assert "two_pointers_opposite" not in strat_ids


# ============================================================
# Test 2: Carry propagation matches linked-list addition group
# ============================================================

class TestCarryPropagationMatch:
    """Carry propagation should match solution groups requiring it."""

    def test_carry_propagation_confirms_with_correct_group(self):
        """Add Two Numbers with carry propagation should match a carry_propagation group."""
        code = """
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
"""
        groups = [{
            "id": "group_0",
            "required": ["carry_propagation"],
            "optional": ["node_constructor", "multiple_pointer_traversal"],
            "excluded": ["two_pointers_opposite"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }]
        result = run_shadow_analysis(code, solution_groups=groups)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "carry_propagation" in tech_ids
        assert result["match_outcome"]["outcome"] == "CONFIRMED"

    def test_carry_propagation_unresolved_for_linked_list_reversal_group(self):
        """Add Two Numbers should NOT match a linked_list_traversal group (reversal)."""
        code = """
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
"""
        groups = [{
            "id": "group_0",
            "required": ["linked_list_traversal"],
            "optional": ["pointer_rewiring"],
            "excluded": ["two_pointers_opposite"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }]
        result = run_shadow_analysis(code, solution_groups=groups)
        assert result is not None
        # carry_propagation IS detected, but linked_list_traversal is NOT
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "carry_propagation" in tech_ids
        assert "linked_list_traversal" not in tech_ids
        # Should be UNRESOLVED (wrong group for this code)
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_linked_list_reversal_matches_traversal_group(self):
        """Linked-list reversal should match a linked_list_traversal group."""
        code = """
def reverseList(head):
    prev = None
    curr = head
    while curr:
        next_node = curr.next
        curr.next = prev
        prev = curr
        curr = next_node
    return prev
"""
        groups = [{
            "id": "group_0",
            "required": ["linked_list_traversal"],
            "optional": ["pointer_rewiring", "multiple_pointer_traversal"],
            "excluded": ["two_pointers_opposite"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }]
        result = run_shadow_analysis(code, solution_groups=groups)
        assert result is not None
        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        assert "linked_list_traversal" in tech_ids
        assert result["match_outcome"]["outcome"] == "CONFIRMED"


# ============================================================
# Test 3: Valid technique must NOT become unrelated strategy
# ============================================================

class TestNoFalseStrategyAssignment:
    """Techniques must not automatically produce unrelated strategies."""

    def test_carry_propagation_no_unrelated_strategy(self):
        """carry_propagation must NOT produce two_pointers_opposite or binary_search."""
        code = """
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
"""
        result = run_shadow_analysis(code)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        # carry_propagation should NOT trigger any of these
        assert "two_pointers_opposite" not in strat_ids
        assert "binary_search" not in strat_ids
        assert "sliding_window" not in strat_ids
        assert "bfs_shortest_path" not in strat_ids
        assert "dp_bottom_up" not in strat_ids

    def test_linked_list_traversal_no_unrelated_strategy(self):
        """linked_list_traversal must NOT produce binary_search or DP strategies."""
        code = """
def reverseList(head):
    prev = None
    curr = head
    while curr:
        next_node = curr.next
        curr.next = prev
        prev = curr
        curr = next_node
    return prev
"""
        result = run_shadow_analysis(code)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "binary_search" not in strat_ids
        assert "dp_bottom_up" not in strat_ids
        assert "dp_top_down" not in strat_ids


# ============================================================
# Test 4: No match → UNRESOLVED, never false positive
# ============================================================

class TestUnresolvedBehavior:
    """When no mapping exists, result must be UNRESOLVED, never a false positive."""

    def test_no_group_produces_unresolved(self):
        """Without solution groups, outcome must be UNRESOLVED."""
        code = """
def simple_loop(nums):
    total = 0
    for x in nums:
        total += x
    return total
"""
        result = run_shadow_analysis(code, solution_groups=None)
        assert result is not None
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"
        assert result["match_outcome"]["authority_tier"] == "unknown"

    def test_empty_group_list_produces_unresolved(self):
        """With empty solution groups, outcome must be UNRESOLVED."""
        code = """
def simple_loop(nums):
    total = 0
    for x in nums:
        total += x
    return total
"""
        result = run_shadow_analysis(code, solution_groups=[])
        assert result is not None
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_no_false_contradiction_for_unknown_pattern(self):
        """Unknown patterns must NOT produce CONTRADICTED."""
        code = """
def mystery(nums):
    result = 0
    for x in nums:
        result += x
    return result
"""
        groups = [{
            "id": "group_0",
            "required": ["some_nonexistent_technique"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }]
        result = run_shadow_analysis(code, solution_groups=groups)
        assert result is not None
        assert result["match_outcome"]["outcome"] != "CONTRADICTED"


# ============================================================
# Test 5: Legacy pattern preservation for production matcher
# ============================================================

class TestLegacyPatternPreservation:
    """The production matcher must receive legacy pattern IDs, not V1 concepts."""

    def test_build_single_group_preserves_patterns(self):
        """_build_solution_groups stores original legacy patterns."""
        groups = _build_solution_groups(
            ["linked_list_reversal"],
            {"linked_list_reversal": 0.8},
        )
        assert len(groups) >= 1
        group = groups[0]
        # The 'patterns' field should contain the original legacy pattern
        assert "linked_list_reversal" in group.get("patterns", [])
        # The 'required' field should contain V1 concepts
        assert "linked_list_traversal" in group.get("required", [])

    def test_build_single_group_preserves_multiple_patterns(self):
        """Multiple legacy patterns are preserved in the patterns field."""
        groups = _build_solution_groups(
            ["prefix_sum", "sliding_window_variable"],
            {"prefix_sum": 0.8, "sliding_window_variable": 0.7},
        )
        assert len(groups) >= 1
        all_patterns = []
        for g in groups:
            all_patterns.extend(g.get("patterns", []))
        # Original legacy patterns should be present
        assert "prefix_sum" in all_patterns or "sliding_window_variable" in all_patterns


# ============================================================
# Test 6: V1 mapping correctness after fix
# ============================================================

class TestV1MappingAfterFix:
    """Verify the V1 mapping produces correct required/optional lists."""

    def test_linked_list_reversal_maps_to_traversal(self):
        """linked_list_reversal now maps to linked_list_traversal."""
        mapping = PATTERN_TO_V1_MAPPING["linked_list_reversal"]
        assert "linked_list_traversal" in mapping["required"]
        assert "two_pointers_opposite" in mapping["excluded"]

    def test_monotonic_stack_maps_to_maintenance(self):
        """monotonic_stack now maps to monotonic_stack_maintenance."""
        mapping = PATTERN_TO_V1_MAPPING["monotonic_stack"]
        assert "monotonic_stack_maintenance" in mapping["required"]

    def test_prefix_sum_unchanged(self):
        """prefix_sum mapping is unchanged."""
        mapping = PATTERN_TO_V1_MAPPING["prefix_sum"]
        assert "sequential_accumulation" in mapping["required"]

    def test_binary_search_standard_unchanged(self):
        """binary_search_standard mapping is unchanged."""
        mapping = PATTERN_TO_V1_MAPPING["binary_search_standard"]
        assert "binary_search" in mapping["required"]
