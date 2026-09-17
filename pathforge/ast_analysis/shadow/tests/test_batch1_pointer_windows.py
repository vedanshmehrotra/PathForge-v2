"""Generalized regression tests for Batch 1 (F1 + F2 + F4).

F1 — groups with an empty ``required`` list are explicitly unmatchable.
F2 — same-direction pointer progression is separate evidence from
     opposite-direction scanning (bidirectional_index_scan unchanged).
F4 — variable-window sliding_window requires real index participation.

These tests are written against structure, not problem IDs: each case is a
minimal snippet representing a family (same-direction pointers, converging
pointers, fast/slow, jump-style windows, shrink-style windows, nested
doubling loops, scalar accumulation).
"""
import ast

import pytest

from pathforge.ast_analysis.shadow.data_structures import MatchOutcome
from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.matching import evaluate_solution_groups
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.services.ground_truth_builder import (
    PATTERN_TO_V1_MAPPING, VALID_TECHNIQUES,
)
from pathforge.services.problem_resolver import _split_csv_patterns_to_groups


# ============================================================
# Code families
# ============================================================

SAME_DIRECTION_ARRAY = """
class Solution:
    def moveZeroes(self, nums):
        left = 0
        for right in range(len(nums)):
            if nums[right] != 0:
                nums[left], nums[right] = nums[right], nums[left]
                left += 1
"""

SAME_DIRECTION_LINKED = """
class Solution:
    def mergeTwoLists(self, list1, list2):
        dummy = ListNode()
        tail = dummy
        while list1 and list2:
            if list1.val <= list2.val:
                tail.next = list1
                list1 = list1.next
            else:
                tail.next = list2
                list2 = list2.next
            tail = tail.next
        tail.next = list1 if list1 else list2
        return dummy.next
"""

FAST_SLOW_LINKED = """
class Solution:
    def hasCycle(self, head):
        slow = head
        fast = head
        while fast and fast.next:
            slow = slow.next
            fast = fast.next.next
            if slow == fast:
                return True
        return False
"""

OPPOSITE_DIRECTION = """
class Solution:
    def twoSum(self, numbers, target):
        left = 0
        right = len(numbers) - 1
        while left < right:
            cur = numbers[left] + numbers[right]
            if cur == target:
                return [left + 1, right + 1]
            elif cur < target:
                left += 1
            else:
                right -= 1
        return []
"""

OPPOSITE_DIRECTION_MAX_AREA = """
class Solution:
    def maxArea(self, height):
        left, right = 0, len(height) - 1
        best = 0
        while left < right:
            area = min(height[left], height[right]) * (right - left)
            best = max(best, area)
            if height[left] < height[right]:
                left += 1
            else:
                right -= 1
        return best
"""

SINGLE_INDEX_LOOP = """
class Solution:
    def runningSum(self, nums):
        total = 0
        for i in range(len(nums)):
            total += nums[i]
        return total
"""

SCALAR_ACCUMULATION_WHILE = """
class Solution:
    def f(self, nums):
        total = 0
        i = 0
        while i < len(nums):
            if nums[i] > 0:
                total += nums[i]
            i += 1
        return total
"""

NESTED_DOUBLING_LOOP = """
class Solution:
    def divide(self, dividend, divisor):
        dividend, divisor = abs(dividend), abs(divisor)
        quotient = 0
        while dividend >= divisor:
            value = divisor
            multiple = 1
            while dividend >= (value << 1):
                value <<= 1
                multiple <<= 1
            dividend -= value
            quotient += multiple
        return quotient
"""

EXPONENTIATION_BY_SQUARING = """
class Solution:
    def myPow(self, x, n):
        result = 1
        while n > 0:
            if n % 2 == 1:
                result *= x
            x *= x
            n //= 2
        return result
"""

WINDOW_SHRINK_SUBSCRIPT = """
class Solution:
    def minSubArrayLen(self, target, nums):
        left = 0
        total = 0
        best = float('inf')
        for right in range(len(nums)):
            total += nums[right]
            while total >= target:
                best = min(best, right - left + 1)
                total -= nums[left]
                left += 1
        return best if best != float('inf') else 0
"""

WINDOW_JUMP_STYLE = """
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
# Helpers
# ============================================================

def _facts(code):
    return extract_structural_facts(ast.parse(code))


def _techniques(code):
    return detect_techniques(_facts(code))


def _technique_ids(code):
    return {t.technique_id for t in _techniques(code)}


def _strategy_ids(code):
    facts = _facts(code)
    techs = detect_techniques(facts)
    return {s.strategy_id for s in evaluate_strategies(techs, facts)}


def _outcome(code, groups):
    facts = _facts(code)
    techs = detect_techniques(facts)
    strats = evaluate_strategies(techs, facts)
    return evaluate_solution_groups(groups, techs, strats, facts)


def _group(required, optional=None, excluded=None, authority="llm_proposed"):
    return {
        "id": "group_0",
        "required": list(required),
        "optional": list(optional or []),
        "excluded": list(excluded or []),
        "threshold": 0.5,
        "authority_tier": authority,
        "patterns": [],
    }


# ============================================================
# F1 — empty-required groups are explicitly unmatchable
# ============================================================

class TestF1UnmatchableGroups:

    def test_empty_required_is_unmatchable_not_unsatisfied(self):
        """A group with no requirement cannot be satisfied by any submission."""
        out = _outcome(SAME_DIRECTION_LINKED, [_group([])])
        assert isinstance(out, MatchOutcome)
        assert out.outcome == "UNRESOLVED"
        assert out.unmatchable_group_ids == ["group_0"]
        assert any("unmatchable" in r for r in out.reasoning)

    def test_empty_required_never_confirmed_even_when_optional_is_detected(self):
        """Optional evidence alone must not confirm a requirement-less group."""
        # sequential_accumulation fires for the nested doubling loop; it is the
        # only optional of the greedy_local mapping, and it must not confirm.
        out = _outcome(
            NESTED_DOUBLING_LOOP,
            [_group([], optional=["sequential_accumulation"])],
        )
        assert out.outcome == "UNRESOLVED"
        assert out.unmatchable_group_ids == ["group_0"]

    def test_empty_required_group_with_exclusion_still_contradicts(self):
        """Exclusion-only groups keep their existing contradiction signal."""
        groups = [_group([], excluded=["recursive_branching"], authority="editorial")]
        out = _outcome(FAST_SLOW_LINKED, groups)
        # no recursion here -> not contradicted, but still unmatchable
        assert out.outcome == "UNRESOLVED"
        assert out.unmatchable_group_ids == ["group_0"]

        recursive = "class S:\n    def f(self, n):\n        if n <= 1:\n            return n\n        return f(n - 1) + f(n - 2)\n"
        out_rec = _outcome(recursive, [_group([], excluded=["recursive_branching"],
                                              authority="editorial")])
        assert out_rec.outcome == "CONTRADICTED"

    def test_unmatchable_group_does_not_block_a_satisfiable_group(self):
        """A satisfiable sibling group still confirms."""
        groups = [
            {"id": "group_0", "required": [], "optional": [], "excluded": [],
             "threshold": 0.5, "authority_tier": "llm_proposed", "patterns": []},
            {"id": "group_1", "required": ["linked_list_traversal"], "optional": [],
             "excluded": [], "threshold": 0.5, "authority_tier": "llm_proposed",
             "patterns": []},
        ]
        out = _outcome(SAME_DIRECTION_LINKED, groups)
        assert out.outcome == "CONFIRMED"
        assert out.satisfied_group_ids == ["group_1"]
        assert out.unmatchable_group_ids == ["group_0"]

    def test_ordinary_groups_unaffected(self):
        out = _outcome(FAST_SLOW_LINKED, [_group(["linked_list_traversal"])])
        assert out.outcome == "CONFIRMED"
        assert out.unmatchable_group_ids == []


# ============================================================
# F2 — same-direction pointer evidence
# ============================================================

class TestF2ForwardPointerAdvance:

    def test_concept_is_registered(self):
        assert "forward_pointer_advance" in VALID_TECHNIQUES

    def test_fires_for_same_direction_array_pointers(self):
        assert "forward_pointer_advance" in _technique_ids(SAME_DIRECTION_ARRAY)

    def test_fires_for_same_direction_linked_pointers(self):
        assert "forward_pointer_advance" in _technique_ids(SAME_DIRECTION_LINKED)

    def test_fires_for_fast_slow_pointers(self):
        assert "forward_pointer_advance" in _technique_ids(FAST_SLOW_LINKED)

    @pytest.mark.parametrize("code,name", [
        (OPPOSITE_DIRECTION, "two_sum_sorted"),
        (OPPOSITE_DIRECTION_MAX_AREA, "max_area"),
    ])
    def test_does_not_fire_for_opposite_direction_scans(self, code, name):
        ids = _technique_ids(code)
        assert "forward_pointer_advance" not in ids, f"{name}: must stay bidirectional"
        assert "bidirectional_index_scan" in ids, f"{name}: bidirectional evidence lost"

    def test_does_not_fire_for_single_index_loop(self):
        assert "forward_pointer_advance" not in _technique_ids(SINGLE_INDEX_LOOP)

    def test_does_not_fire_for_nested_doubling_loop(self):
        assert "forward_pointer_advance" not in _technique_ids(NESTED_DOUBLING_LOOP)

    def test_does_not_fire_for_union_find_root_chasing(self):
        """while parent[x] != x: x = parent[x] is pointer chasing, not two pointers."""
        code = (
            "class DSU:\n"
            "    def find(self, parent, x):\n"
            "        while parent[x] != x:\n"
            "            x = parent[x]\n"
            "        return x\n"
            "    def union(self, parent, a, b):\n"
            "        ra = self.find(parent, a)\n"
            "        rb = self.find(parent, b)\n"
            "        parent[ra] = rb\n"
        )
        assert "forward_pointer_advance" not in _technique_ids(code)

    def test_bidirectional_index_scan_unchanged_for_opposite_consumers(self):
        """two_pointers_opposite / binary_search inputs keep working."""
        assert "two_pointers_opposite" in _strategy_ids(OPPOSITE_DIRECTION)
        assert "two_pointers_opposite" in _strategy_ids(OPPOSITE_DIRECTION_MAX_AREA)

    def test_mapping_no_longer_routes_same_direction_into_bidirectional(self):
        assert PATTERN_TO_V1_MAPPING["two_pointers_same"]["required"] == [
            "forward_pointer_advance"
        ]
        assert PATTERN_TO_V1_MAPPING["fast_slow_pointers"]["required"] == [
            "forward_pointer_advance"
        ]
        # opposite-direction pattern is untouched
        assert PATTERN_TO_V1_MAPPING["two_pointers_opposite"]["required"] == [
            "two_pointers_opposite"
        ]

    def test_same_direction_group_confirms_for_same_direction_code(self):
        groups = _split_csv_patterns_to_groups(["two_pointers_same"], {}, 1.0, "llm_proposed")
        assert _outcome(SAME_DIRECTION_ARRAY, groups).outcome == "CONFIRMED"
        assert _outcome(SAME_DIRECTION_LINKED, groups).outcome == "CONFIRMED"

    def test_fast_slow_group_confirms_for_cycle_detection(self):
        groups = _split_csv_patterns_to_groups(["fast_slow_pointers"], {}, 1.0, "llm_proposed")
        assert _outcome(FAST_SLOW_LINKED, groups).outcome == "CONFIRMED"

    def test_same_direction_group_not_confirmed_for_opposite_direction_code(self):
        """Converging pointers are not same-direction evidence."""
        groups = _split_csv_patterns_to_groups(["two_pointers_same"], {}, 1.0, "llm_proposed")
        out = _outcome(OPPOSITE_DIRECTION, groups)
        assert out.outcome != "CONFIRMED"


# ============================================================
# F4 — sliding_window requires index participation
# ============================================================

class TestF4WindowIndexParticipation:

    def test_shrink_style_window_still_detected(self):
        assert "sliding_window" in _strategy_ids(WINDOW_SHRINK_SUBSCRIPT)

    def test_jump_style_window_still_detected(self):
        """left moves via max(...) and only appears in window-size arithmetic."""
        assert "sliding_window" in _strategy_ids(WINDOW_JUMP_STYLE)

    def test_nested_doubling_loop_is_not_a_window(self):
        assert "sliding_window" not in _strategy_ids(NESTED_DOUBLING_LOOP)

    def test_exponentiation_by_squaring_is_not_a_window(self):
        assert "sliding_window" not in _strategy_ids(EXPONENTIATION_BY_SQUARING)

    def test_while_accumulation_with_index_is_not_a_window(self):
        """Indexes a collection, but shrinks no window."""
        assert "sliding_window" not in _strategy_ids(SCALAR_ACCUMULATION_WHILE)

    def test_nested_doubling_loop_does_not_confirm_a_window_group(self):
        groups = _split_csv_patterns_to_groups(["sliding_window_variable"], {}, 1.0, "llm_proposed")
        out = _outcome(NESTED_DOUBLING_LOOP, groups)
        assert out.outcome != "CONFIRMED"

    def test_jump_style_window_confirms_a_window_group(self):
        groups = _split_csv_patterns_to_groups(["sliding_window_variable"], {}, 1.0, "llm_proposed")
        assert _outcome(WINDOW_JUMP_STYLE, groups).outcome == "CONFIRMED"
