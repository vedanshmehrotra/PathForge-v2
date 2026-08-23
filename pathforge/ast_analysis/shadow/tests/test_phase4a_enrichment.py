"""Phase 4A tests — multi-group generation, vocabulary mapping, and validation.

Tests:
- Single-group generation
- Multi-group generation
- Invalid group rejection
- Vocabulary validation
- Threshold validation
- Authority preservation
- Provenance preservation
- Real validation cases
"""
import pytest

from pathforge.services.ground_truth_builder import (
    _build_solution_groups,
    _validate_group,
    validate_solution_groups,
    PATTERN_TO_V1_MAPPING,
    VALID_V1_CONCEPTS,
    VALID_TECHNIQUES,
    VALID_STRATEGIES,
)
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
from pathforge.ast_analysis.shadow.matching import evaluate_solution_groups
from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
import ast


# ============================================================
# Test code samples
# ============================================================

ADD_TWO_NUMBERS = """
def addTwoNumbers(l1, l2):
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

PROBLEM_2996 = """
def missingInteger(nums):
    i = 1
    summ = nums[0]
    while i <= len(nums)-1 and nums[i] == nums[i-1]+1:
        summ += nums[i]
        i += 1
    while summ in nums:
        summ += 1
    return summ
"""

IS_PALINDROME = """
def is_palindrome(s):
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True
"""

BINARY_SEARCH = """
def binary_search(nums, target):
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

SLIDING_WINDOW = """
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
"""


# ============================================================
# Vocabulary mapping tests
# ============================================================

class TestVocabularyMapping:
    """Test that old patterns map correctly to V1 vocabulary."""

    def test_all_patterns_have_mappings(self):
        """Every legacy pattern has a mapping entry."""
        from pathforge.ast_engine.patterns import ALL_PATTERNS
        for pattern in ALL_PATTERNS:
            assert pattern in PATTERN_TO_V1_MAPPING, \
                f"Pattern '{pattern}' has no V1 mapping"

    def test_valid_concepts_are_known(self):
        """All valid V1 concepts are registered."""
        assert len(VALID_TECHNIQUES) == 9  # 6 original + 3 Phase 5A
        assert len(VALID_STRATEGIES) == 9  # 8 original + 1 Phase 5A
        assert len(VALID_V1_CONCEPTS) == 18  # 9 + 9

    def test_binary_search_maps_correctly(self):
        """binary_search_standard maps to binary_search strategy."""
        mapping = PATTERN_TO_V1_MAPPING["binary_search_standard"]
        assert "binary_search" in mapping["required"]
        assert "two_pointers_opposite" in mapping["excluded"]

    def test_two_pointers_maps_correctly(self):
        """two_pointers_opposite maps to two_pointers_opposite strategy."""
        mapping = PATTERN_TO_V1_MAPPING["two_pointers_opposite"]
        assert "two_pointers_opposite" in mapping["required"]
        assert "binary_search" in mapping["excluded"]

    def test_sliding_window_maps_correctly(self):
        """sliding_window_fixed maps to sliding_window strategy."""
        mapping = PATTERN_TO_V1_MAPPING["sliding_window_fixed"]
        assert "sliding_window" in mapping["required"]
        assert "two_pointers_opposite" in mapping["excluded"]

    def test_dfs_maps_correctly(self):
        """dfs_recursive maps to recursive_branching technique."""
        mapping = PATTERN_TO_V1_MAPPING["dfs_recursive"]
        assert "recursive_branching" in mapping["required"]

    def test_backtracking_maps_correctly(self):
        """backtracking_permutation maps to dfs_backtracking strategy."""
        mapping = PATTERN_TO_V1_MAPPING["backtracking_permutation"]
        assert "dfs_backtracking" in mapping["required"]
        assert "dp_top_down" in mapping["excluded"]

    def test_dp_maps_correctly(self):
        """dp_1d_forward maps to dp_bottom_up strategy."""
        mapping = PATTERN_TO_V1_MAPPING["dp_1d_forward"]
        assert "dp_bottom_up" in mapping["required"]

    def test_union_find_maps_correctly(self):
        """union_find maps to union_find strategy."""
        mapping = PATTERN_TO_V1_MAPPING["union_find"]
        assert "union_find" in mapping["required"]

    def test_linked_list_reversal_unmapped(self):
        """linked_list_reversal has no direct V1 technique."""
        mapping = PATTERN_TO_V1_MAPPING["linked_list_reversal"]
        assert len(mapping["required"]) == 0

    def test_hash_map_unmapped(self):
        """hash_map_lookup has no direct V1 technique."""
        mapping = PATTERN_TO_V1_MAPPING["hash_map_lookup"]
        assert len(mapping["required"]) == 0


# ============================================================
# Multi-group generation tests
# ============================================================

class TestMultiGroupGeneration:
    """Test multi-group solution-group generation."""

    def test_single_pattern_produces_one_group(self):
        """Single pattern produces one group."""
        groups = _build_solution_groups(
            ["binary_search_standard"],
            {"binary_search_standard": 0.8},
        )
        assert len(groups) >= 1
        assert groups[0]["id"] == "group_0"

    def test_multiple_patterns_same_strategy_produce_one_group(self):
        """Multiple patterns mapping to same strategy produce one group."""
        groups = _build_solution_groups(
            ["dp_1d_forward", "dp_1d_sequence"],
            {"dp_1d_forward": 0.8, "dp_1d_sequence": 0.7},
        )
        # Both map to dp_bottom_up → should be in same group
        assert len(groups) >= 1
        required = groups[0].get("required", [])
        assert "dp_bottom_up" in required

    def test_different_strategies_produce_multiple_groups(self):
        """Patterns mapping to different strategies produce multiple groups."""
        groups = _build_solution_groups(
            ["binary_search_standard", "two_pointers_opposite"],
            {"binary_search_standard": 0.8, "two_pointers_opposite": 0.7},
        )
        # These map to different strategies → multiple groups
        assert len(groups) >= 2

    def test_approaches_parameter_enables_multi_group(self):
        """LLM-provided approaches enable multi-group generation."""
        approaches = [
            {"name": "binary_search", "patterns": ["binary_search_standard"]},
            {"name": "two_pointers", "patterns": ["two_pointers_opposite"]},
        ]
        groups = _build_solution_groups(
            ["binary_search_standard", "two_pointers_opposite"],
            {"binary_search_standard": 0.8, "two_pointers_opposite": 0.7},
            approaches=approaches,
        )
        assert len(groups) >= 2

    def test_empty_patterns_produces_no_groups(self):
        """Empty patterns list produces no groups."""
        groups = _build_solution_groups([], {})
        assert len(groups) == 0


# ============================================================
# Structural validation tests
# ============================================================

class TestStructuralValidation:
    """Test structural validation of solution groups."""

    def test_valid_group_accepted(self):
        """A well-formed group is accepted."""
        group = {
            "id": "group_0",
            "required": ["carry_propagation"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"] is True

    def test_invalid_concept_rejected(self):
        """A group with invalid concept ID is rejected."""
        group = {
            "id": "group_0",
            "required": ["nonexistent_concept"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"] is False
        assert "not in V1 vocabulary" in result["reason"]

    def test_threshold_out_of_bounds_rejected(self):
        """A group with threshold outside [0.0, 1.0] is rejected."""
        group = {
            "id": "group_0",
            "required": ["carry_propagation"],
            "optional": [],
            "excluded": [],
            "threshold": 1.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"] is False
        assert "out of bounds" in result["reason"]

    def test_required_and_excluded_conflict_rejected(self):
        """A group with concept both required and excluded is rejected."""
        group = {
            "id": "group_0",
            "required": ["carry_propagation"],
            "optional": [],
            "excluded": ["carry_propagation"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"] is False
        assert "both required and excluded" in result["reason"]

    def test_invalid_authority_tier_rejected(self):
        """A group with invalid authority tier is rejected."""
        group = {
            "id": "group_0",
            "required": ["carry_propagation"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "invalid_tier",
        }
        result = _validate_group(group)
        assert result["valid"] is False
        assert "not valid" in result["reason"]

    def test_optional_and_excluded_conflict_rejected(self):
        """A group with concept both optional and excluded is rejected."""
        group = {
            "id": "group_0",
            "required": [],
            "optional": ["carry_propagation"],
            "excluded": ["carry_propagation"],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }
        result = _validate_group(group)
        assert result["valid"] is False
        assert "both optional and excluded" in result["reason"]

    def test_validate_solution_groups_adds_status(self):
        """validate_solution_groups adds validation status to each group."""
        groups = [
            {
                "id": "group_0",
                "required": ["carry_propagation"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "llm_proposed",
            },
            {
                "id": "group_1",
                "required": ["nonexistent"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "llm_proposed",
            },
        ]
        validated = validate_solution_groups(groups)
        assert validated[0]["validation"] == "accepted"
        assert validated[1]["validation"] == "rejected"


# ============================================================
# Authority and provenance tests
# ============================================================

class TestAuthorityAndProvenance:
    """Test authority and provenance preservation."""

    def test_llm_proposed_groups_remain_non_authoritative(self):
        """LLM-proposed groups are always non-authoritative."""
        groups = _build_solution_groups(
            ["binary_search_standard"],
            {"binary_search_standard": 0.8},
        )
        assert groups[0]["authority_tier"] == "llm_proposed"

    def test_provenance_preserved(self):
        """Provenance metadata is preserved."""
        groups = _build_solution_groups(
            ["binary_search_standard"],
            {"binary_search_standard": 0.8},
        )
        assert "llm_ground_truth" in groups[0]["provenance"]
        assert "vocabulary_v1" in groups[0]["provenance"]

    def test_legacy_fields_preserved(self):
        """Legacy fields are preserved for backward compatibility."""
        groups = _build_solution_groups(
            ["binary_search_standard"],
            {"binary_search_standard": 0.8},
        )
        assert "patterns" in groups[0]
        assert "evidence" in groups[0]
        assert "confidence" in groups[0]

    def test_threshold_default(self):
        """Default threshold is 0.5 for LLM-proposed groups."""
        groups = _build_solution_groups(
            ["binary_search_standard"],
            {"binary_search_standard": 0.8},
        )
        assert groups[0]["threshold"] == 0.5


# ============================================================
# Real validation case tests
# ============================================================

class TestRealValidationCases:
    """Test the real validation cases specified in Phase 4A."""

    def test_add_two_numbers_structured_group(self):
        """Add Two Numbers: structured group for carry_propagation."""
        groups = [{
            "id": "group_0",
            "required": ["carry_propagation"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }]

        result = run_shadow_analysis(ADD_TWO_NUMBERS, solution_groups=groups)
        assert result is not None

        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}

        # carry_propagation evidence present
        assert "carry_propagation" in tech_ids
        # No linked-list-reversal strategy
        assert "linked_list_reversal" not in strat_ids
        # CONFIRMED with matching group
        assert result["match_outcome"]["outcome"] == "CONFIRMED"

    def test_add_two_numbers_old_label_no_contradiction(self):
        """Add Two Numbers: old linked_list_reversal label cannot force contradiction."""
        # Old flat-pattern group with linked_list_reversal
        # This should NOT produce CONTRADICTED in the new system
        groups = [{
            "id": "group_0",
            "required": ["linked_list_reversal"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }]

        result = run_shadow_analysis(ADD_TWO_NUMBERS, solution_groups=groups)
        assert result is not None
        # linked_list_reversal is not a V1 technique → group not satisfied
        # But should NOT be CONTRADICTED (no excluded evidence fires)
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_2996_remains_unresolved(self):
        """Problem 2996: remains UNRESOLVED (no V1 strategy represents it)."""
        result = run_shadow_analysis(PROBLEM_2996)
        assert result is not None

        tech_ids = {t["technique_id"] for t in result["technique_evidence"]}
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}

        # Structural facts preserved
        assert len(result["structural_facts"]) > 0
        # Techniques honest
        assert "sequential_accumulation" in tech_ids
        # No hash_map
        assert "hash_map" not in strat_ids
        # No binary_search
        assert "binary_search" not in strat_ids
        # No fake strategy
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_palindrome_confirmed(self):
        """Palindrome: CONFIRMED with two-pointer group."""
        groups = [{
            "id": "group_0",
            "required": ["two_pointers_opposite"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }]

        result = run_shadow_analysis(IS_PALINDROME, solution_groups=groups)
        assert result is not None
        assert "two_pointers_opposite" in {s["strategy_id"] for s in result["strategy_evidence"]}
        assert result["match_outcome"]["outcome"] == "CONFIRMED"

    def test_binary_search_confirmed(self):
        """Binary Search: CONFIRMED, not two_pointers_opposite."""
        groups = [{
            "id": "group_0",
            "required": ["binary_search"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }]

        result = run_shadow_analysis(BINARY_SEARCH, solution_groups=groups)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "binary_search" in strat_ids
        assert "two_pointers_opposite" not in strat_ids
        assert result["match_outcome"]["outcome"] == "CONFIRMED"

    def test_sliding_window_confirmed(self):
        """Sliding Window: CONFIRMED, not two_pointers_opposite."""
        groups = [{
            "id": "group_0",
            "required": ["sliding_window"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "llm_proposed",
        }]

        result = run_shadow_analysis(SLIDING_WINDOW, solution_groups=groups)
        assert result is not None
        strat_ids = {s["strategy_id"] for s in result["strategy_evidence"]}
        assert "sliding_window" in strat_ids
        assert "two_pointers_opposite" not in strat_ids
        assert result["match_outcome"]["outcome"] == "CONFIRMED"


# ============================================================
# Multi-group behavior tests
# ============================================================

class TestMultiGroupBehavior:
    """Test multi-group behavior with the new generation."""

    def test_two_simultaneously_satisfied_groups(self):
        """Two groups can both be satisfied by the same submission."""
        # Palindrome can satisfy both bidirectional_index_scan and
        # a custom group requiring loop_state_tracking
        groups = [
            {
                "id": "group_0",
                "required": ["bidirectional_index_scan"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "llm_proposed",
            },
            {
                "id": "group_1",
                "required": ["loop_state_tracking"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "llm_proposed",
            },
        ]

        result = run_shadow_analysis(IS_PALINDROME, solution_groups=groups)
        assert result is not None
        # Both groups satisfied → CONFIRMED (best wins)
        assert result["match_outcome"]["outcome"] == "CONFIRMED"

    def test_no_matching_groups_unresolved(self):
        """No matching groups → UNRESOLVED."""
        groups = [
            {
                "id": "group_0",
                "required": ["recursive_branching"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "llm_proposed",
            },
        ]

        result = run_shadow_analysis(ADD_TWO_NUMBERS, solution_groups=groups)
        assert result is not None
        assert result["match_outcome"]["outcome"] == "UNRESOLVED"

    def test_invalid_group_doesnt_poison_valid(self):
        """Invalid group does not poison valid groups."""
        groups = [
            {
                "id": "group_0",
                "required": ["carry_propagation"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "llm_proposed",
            },
            {
                "id": "group_1",
                "required": ["nonexistent_concept"],
                "optional": [],
                "excluded": [],
                "threshold": 0.5,
                "authority_tier": "llm_proposed",
            },
        ]

        # Validate groups
        validated = validate_solution_groups(groups)
        assert validated[0]["validation"] == "accepted"
        assert validated[1]["validation"] == "rejected"

        # Use only accepted groups for matching
        accepted = [g for g in validated if g["validation"] == "accepted"]
        result = run_shadow_analysis(ADD_TWO_NUMBERS, solution_groups=accepted)
        assert result is not None
        assert result["match_outcome"]["outcome"] == "CONFIRMED"

    def test_multi_group_from_patterns(self):
        """Multi-group generation from split patterns."""
        groups = _build_solution_groups(
            ["binary_search_standard", "two_pointers_opposite"],
            {"binary_search_standard": 0.8, "two_pointers_opposite": 0.7},
        )
        # These map to different strategies → multiple groups
        assert len(groups) >= 2
        # Each group is valid
        for group in groups:
            result = _validate_group(group)
            assert result["valid"], f"Group {group['id']} invalid: {result['reason']}"


# ============================================================
# Edge case tests
# ============================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_approaches_list(self):
        """Empty approaches list uses single-group fallback."""
        groups = _build_solution_groups(
            ["binary_search_standard"],
            {"binary_search_standard": 0.8},
            approaches=[],
        )
        assert len(groups) >= 1

    def test_single_approach_uses_single_group(self):
        """Single approach uses single-group generation."""
        approaches = [
            {"name": "binary_search", "patterns": ["binary_search_standard"]},
        ]
        groups = _build_solution_groups(
            ["binary_search_standard"],
            {"binary_search_standard": 0.8},
            approaches=approaches,
        )
        assert len(groups) >= 1

    def test_unmapped_patterns_preserved(self):
        """Unmapped patterns are preserved in diagnostic metadata."""
        groups = _build_solution_groups(
            ["linked_list_reversal"],
            {"linked_list_reversal": 0.8},
        )
        assert len(groups) >= 1
        # linked_list_reversal is unmapped → no required concepts
        assert len(groups[0].get("required", [])) == 0

    def test_threshold_boundary_values(self):
        """Threshold boundary values are accepted."""
        for threshold in [0.0, 0.5, 1.0]:
            group = {
                "id": "group_0",
                "required": ["carry_propagation"],
                "optional": [],
                "excluded": [],
                "threshold": threshold,
                "authority_tier": "llm_proposed",
            }
            result = _validate_group(group)
            assert result["valid"], f"threshold {threshold} should be valid"
