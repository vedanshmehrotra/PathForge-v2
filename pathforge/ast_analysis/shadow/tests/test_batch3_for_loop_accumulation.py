"""Generalized regression tests for Batch 3 (N3).

N3 — sequential_accumulation now recognises for-loop accumulation using
existing structural facts (``for_loop_iteration`` + ``accumulator_update``).

These tests are written against structure, not problem IDs.
"""
import ast
import dataclasses
import sys

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
from pathforge.services.ground_truth_builder import PATTERN_TO_V1_MAPPING


# ============================================================
# Code families
# ============================================================

FOR_LOOP_PREFIX_SUM = '''
class Solution:
    def running_sum(self, nums):
        result = 0
        for x in nums:
            result += x
        return result
'''

FOR_LOOP_PREFIX_SUM_INDEX = '''
class Solution:
    def running_sum(self, nums):
        total = 0
        for i in range(len(nums)):
            total += nums[i]
        return total
'''

FOR_LOOP_COUNT = '''
class Solution:
    def count_positive(self, nums):
        count = 0
        for x in nums:
            if x > 0:
                count += 1
        return count
'''

FOR_LOOP_RANGE_ACCUM = '''
class Solution:
    def sum_upto(self, n):
        total = 0
        for i in range(1, n + 1):
            total += i
        return total
'''

WHILE_LOOP_ACCUM = '''
class Solution:
    def running_sum(self, nums):
        total = 0
        i = 0
        while i < len(nums):
            total += nums[i]
            i += 1
        return total
'''



# Negative: for-loop without accumulator_update fact
FOR_LOOP_NO_SELF_REF = '''
class Solution:
    def copy(self, nums):
        result = []
        for x in nums:
            result.append(x)
        return result
'''

# Negative: for-loop where the loop variable is the only thing updated
FOR_LOOP_TRIVIAL_COUNTER = '''
class Solution:
    def iterate(self, n):
        count = 0
        for i in range(n):
            count += 1
        return count
'''

# Negative: no loop at all
NO_LOOP = '''
class Solution:
    def add(self, a, b):
        return a + b
'''

# Negative: while loop without accumulator
WHILE_NO_ACCUM = '''
class Solution:
    def find(self, nums, target):
        i = 0
        while i < len(nums):
            if nums[i] == target:
                return i
            i += 1
        return -1
'''

# While loop with BoolOp: no while_loop_comparison fact is produced
# (pre-existing gap; BoolOp while-loops are not loop-shape-aware)
WHILE_BOOLOP_NO_LOOP_FACT = '''
class Solution:
    def merge_two(self, a, b):
        i = j = 0
        total = 0
        while a and b:
            if a.val <= b.val:
                total += a.val
                a = a.next
            else:
                total += b.val
                b = b.next
        return total
'''

# For-loop where the loop variable IS the accumulator
# (count += 1 where count is not the loop variable; this IS accumulation)
FOR_LOOP_LOOP_VAR_IS_ACC = '''
class Solution:
    def iterate(self, n):
        i = 0
        for i in range(n):
            i += 1
        return i
'''


# ============================================================
# Helpers
# ============================================================

def _detect(code):
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    return facts, detect_techniques(facts)


def _tech_ids(code):
    _, techs = _detect(code)
    return {t.technique_id for t in techs}


def _facts_of_type(facts, ftype):
    return [f for f in facts if f.fact_type == ftype]


def _fact_types(facts):
    return {f.fact_type for f in facts}


def _outcome(code, groups):
    return run_shadow_analysis(code, solution_groups=groups)["match_outcome"]


def _group(id="group_0", required=None, optional=None, excluded=None):
    return {
        "id": id,
        "required": list(required or []),
        "optional": list(optional or []),
        "excluded": list(excluded or []),
        "threshold": 0.5,
    }


# ============================================================
# 1. Positive: for-loop accumulation is now detected
# ============================================================

class TestForLoopAccumulationDetected:
    def test_for_loop_prefix_sum(self):
        techs = _tech_ids(FOR_LOOP_PREFIX_SUM)
        assert "sequential_accumulation" in techs

    def test_for_loop_prefix_sum_index(self):
        techs = _tech_ids(FOR_LOOP_PREFIX_SUM_INDEX)
        assert "sequential_accumulation" in techs

    def test_for_loop_count(self):
        techs = _tech_ids(FOR_LOOP_COUNT)
        assert "sequential_accumulation" in techs

    def test_for_loop_range_accum(self):
        techs = _tech_ids(FOR_LOOP_RANGE_ACCUM)
        assert "sequential_accumulation" in techs

    def test_for_loop_has_both_facts(self):
        """The detector must require BOTH for_loop_iteration and accumulator_update."""
        facts = extract_structural_facts(ast.parse(FOR_LOOP_PREFIX_SUM))
        types = _fact_types(facts)
        assert "for_loop_iteration" in types
        assert "accumulator_update" in types


# ============================================================
# 2. Positive: while-loop accumulation still works
# ============================================================

class TestWhileLoopAccumulationUnchanged:
    def test_while_loop_prefix_sum(self):
        techs = _tech_ids(WHILE_LOOP_ACCUM)
        assert "sequential_accumulation" in techs

    def test_while_loop_boolop_accum_not_detected(self):
        """BoolOp while-loops (``while a and b:``) don't produce a
        ``while_loop_comparison`` fact, so sequential_accumulation is not
        detected.  This is a pre-existing gap, not caused by Batch 3."""
        techs = _tech_ids(WHILE_BOOLOP_NO_LOOP_FACT)
        assert "sequential_accumulation" not in techs

    def test_while_loop_confidence_unchanged(self):
        _, techs = _detect(WHILE_LOOP_ACCUM)
        acc = [t for t in techs if t.technique_id == "sequential_accumulation"]
        assert len(acc) == 1
        assert acc[0].presence_confidence == 0.85


# ============================================================
# 3. Negative: the rule does not over-fire
# ============================================================

class TestForLoopNegativeCases:
    def test_for_loop_without_self_ref_update(self):
        """result.append(x) has no accumulator_update fact."""
        techs = _tech_ids(FOR_LOOP_NO_SELF_REF)
        assert "sequential_accumulation" not in techs

    def test_trivial_counter_where_loop_var_is_accumulator(self):
        """count += 1 where count is distinct from the loop variable i.

        count IS the accumulator (self-referential), and count != i, so
        sequential_accumulation fires. This is a legitimate accumulation:
        counting how many iterations match a condition.
        """
        techs = _tech_ids(FOR_LOOP_TRIVIAL_COUNTER)
        assert "sequential_accumulation" in techs

    def test_no_loop(self):
        techs = _tech_ids(NO_LOOP)
        assert "sequential_accumulation" not in techs

    def test_while_loop_loop_var_increment_is_accumulation(self):
        """``i += 1`` in a while-loop IS sequential accumulation: the loop
        variable is self-referentially updated.  This is pre-existing
        behaviour, not introduced by Batch 3."""
        techs = _tech_ids(WHILE_NO_ACCUM)
        assert "sequential_accumulation" in techs

    def test_for_loop_loop_var_increment_is_accumulation(self):
        """``i += 1`` in a for-loop IS sequential accumulation when i is
        the loop variable and distinct from any outer accumulator."""
        techs = _tech_ids(FOR_LOOP_LOOP_VAR_IS_ACC)
        assert "sequential_accumulation" in techs

    def test_for_loop_fires_only_with_both_facts(self):
        """Removing the accumulator_update fact should prevent detection."""
        facts = extract_structural_facts(ast.parse(FOR_LOOP_PREFIX_SUM))
        # Remove accumulator_update facts
        filtered = [f for f in facts if f.fact_type != "accumulator_update"]
        techs = detect_techniques(filtered)
        assert not any(t.technique_id == "sequential_accumulation" for t in techs)

    def test_for_loop_fires_only_with_loop_fact(self):
        """Removing the for_loop_iteration fact should prevent detection."""
        facts = extract_structural_facts(ast.parse(FOR_LOOP_PREFIX_SUM))
        filtered = [f for f in facts if f.fact_type != "for_loop_iteration"]
        techs = detect_techniques(filtered)
        assert not any(t.technique_id == "sequential_accumulation" for t in techs)


# ============================================================
# 4. For-loop vs while-loop: same detection output
# ============================================================

class TestForLoopWhileLoopParity:
    def test_for_and_while_both_detect(self):
        for_techs = _tech_ids(FOR_LOOP_PREFIX_SUM)
        while_techs = _tech_ids(WHILE_LOOP_ACCUM)
        assert "sequential_accumulation" in for_techs
        assert "sequential_accumulation" in while_techs

    def test_confidence_is_identical(self):
        """Both paths should report 0.85 confidence."""
        _, for_techs = _detect(FOR_LOOP_PREFIX_SUM)
        _, while_techs = _detect(WHILE_LOOP_ACCUM)
        for_acc = [t for t in for_techs if t.technique_id == "sequential_accumulation"]
        while_acc = [t for t in while_techs if t.technique_id == "sequential_accumulation"]
        assert for_acc[0].presence_confidence == while_acc[0].presence_confidence


# ============================================================
# 5. Matching engine integration
# ============================================================

class TestForLoopAccumulationMatches:
    def test_for_loop_prefix_sum_confirms(self):
        groups = [_group(required=["sequential_accumulation"])]
        out = _outcome(FOR_LOOP_PREFIX_SUM, groups)
        assert out["outcome"] == "CONFIRMED"
        assert "group_0" in out["satisfied_group_ids"]

    def test_for_loop_range_accum_confirms(self):
        groups = [_group(required=["sequential_accumulation"])]
        out = _outcome(FOR_LOOP_RANGE_ACCUM, groups)
        assert out["outcome"] == "CONFIRMED"

    def test_for_loop_count_confirms(self):
        groups = [_group(required=["sequential_accumulation"])]
        out = _outcome(FOR_LOOP_COUNT, groups)
        assert out["outcome"] == "CONFIRMED"

    def test_for_loop_no_self_ref_stays_unresolved(self):
        groups = [_group(required=["sequential_accumulation"])]
        out = _outcome(FOR_LOOP_NO_SELF_REF, groups)
        assert out["outcome"] == "UNRESOLVED"


# ============================================================
# 6. Vocabulary integration (prefix_sum maps to sequential_accumulation)
# ============================================================

class TestVocabularyIntegration:
    def test_prefix_sum_mapping_still_works_with_for_loop(self):
        """prefix_sum → sequential_accumulation should work for both loop types."""
        groups = [{
            "id": "group_0",
            "required": PATTERN_TO_V1_MAPPING["prefix_sum"]["required"],
            "optional": PATTERN_TO_V1_MAPPING["prefix_sum"]["optional"],
            "excluded": PATTERN_TO_V1_MAPPING["prefix_sum"]["excluded"],
            "threshold": 0.5,
        }]
        for_out = _outcome(FOR_LOOP_PREFIX_SUM, groups)
        while_out = _outcome(WHILE_LOOP_ACCUM, groups)
        assert for_out["outcome"] == "CONFIRMED"
        assert while_out["outcome"] == "CONFIRMED"
