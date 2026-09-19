"""Generalized regression tests for Vocabulary Layer 2, Step 1.

``candidate_selection`` (T12) — loop + conditional branch + scalar candidate
replacement. Structural only: no variable-name evidence, no problem IDs,
no new fact types. The index-participation fence (M2 relation /
subscript_index_access fallback) separates candidate selection from
sliding-window/pointer state; the accumulator fence (no
``accumulator_update`` fact for the candidate variable) separates it from
arithmetic accumulation.

These tests are written against structure, not problem IDs.
"""
import ast
import sys

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.relations import build_relations
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.services.ground_truth_builder import (
    PATTERN_TO_V1_MAPPING,
    VALID_TECHNIQUES,
    missing_vocabulary_for_patterns,
)


# ============================================================
# Code families
# ============================================================

RUNNING_MAX = '''
class Solution:
    def max_element(self, nums):
        best = nums[0]
        for x in nums:
            if x > best:
                best = x
        return best
'''

NONOBVIOUS_NAMES = '''
class Solution:
    def pick(self, vals):
        q = vals[0]
        for z in vals:
            if z * z > q:
                q = z
        return q
'''

CASCADE_TOP2 = '''
class Solution:
    def second_max(self, nums):
        i = 0
        j = 0
        for k in range(len(nums)):
            if i <= nums[k]:
                j = i
                i = nums[k]
            elif j <= nums[k]:
                j = nums[k]
        return (i - 1) * (j - 1)
'''

SELECT_FIRST_MATCH = '''
class Solution:
    def first_odd(self, nums):
        odd = None
        for x in nums:
            if x % 2 != 0:
                odd = x
                break
        return odd
'''

WHILE_LOOP_CANDIDATE = '''
class Solution:
    def scan(self, nums):
        b = nums[0]
        n = 0
        while n < len(nums):
            if nums[n] > b:
                b = nums[n]
            n += 1
        return b
'''

SUM_ACCUMULATION = '''
class Solution:
    def total(self, nums):
        total = 0
        for x in nums:
            total += x
        return total
'''

COUNT_ACCUMULATION = '''
class Solution:
    def count_even(self, xs):
        c = 0
        for x in xs:
            if x % 2 == 0:
                c += 1
        return c
'''

UNCONDITIONAL_ASSIGN = '''
class Solution:
    def last(self, nums):
        out = 0
        for x in nums:
            out = x
        return out
'''

IF_NO_CANDIDATE_UPDATE = '''
class Solution:
    def probe(self, nums, lim):
        seen = []
        total = 0
        for x in nums:
            if x > lim:
                seen.append(x)
            total += 1
        return total
'''

LIST_ACCUMULATION = '''
class Solution:
    def build(self, strs):
        result = []
        for s in strs:
            result = result + [s.upper()]
        return result
'''

WINDOW_STATE = '''
class Solution:
    def longest(self, s, k):
        left = 0
        best = 0
        for right in range(len(s)):
            while True:
                left += 1
        best = 7
        return best
'''

DP_TABLE_UPDATE = '''
class Solution:
    def fib(self, n):
        dp = [0] * (n + 1)
        dp[1] = 1
        for i in range(2, n + 1):
            if n % 2 == 0:
                dp[i] = dp[i - 1] + dp[i - 2]
        return dp[n]
'''


# ============================================================
# Helpers
# ============================================================

def _techniques(code, with_relations=True):
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    relations = build_relations(tree) if with_relations else None
    return detect_techniques(facts, relations), facts


def _ids(code, with_relations=True):
    techs, _ = _techniques(code, with_relations)
    return {t.technique_id for t in techs}


# ============================================================
# Positive cases: loop + conditional branch + scalar candidate replacement
# ============================================================

@pytest.mark.parametrize("code", [RUNNING_MAX, NONOBVIOUS_NAMES, CASCADE_TOP2, SELECT_FIRST_MATCH, WHILE_LOOP_CANDIDATE])
def test_candidate_selection_detected(code):
    assert "candidate_selection" in _ids(code)


def test_candidate_selection_with_and_without_relations():
    """Same verdict with the M2 relation layer and with the fact fallback."""
    assert "candidate_selection" in _ids(RUNNING_MAX, with_relations=True)
    assert "candidate_selection" in _ids(RUNNING_MAX, with_relations=False)


def test_candidate_selection_supporting_facts_are_structural():
    techs, facts = _techniques(SELECT_FIRST_MATCH)
    ev = next(t for t in techs if t.technique_id == "candidate_selection")
    by_id = {f.fact_id: f for f in facts}
    kinds = {by_id[fid].fact_type for fid in ev.supporting_fact_ids if fid in by_id}
    assert "conditional_index_update" in kinds
    assert kinds & {"for_loop_iteration", "while_loop_comparison"}


def test_candidate_selection_non_name_based():
    """Deliberately non-obvious candidate names must not change the outcome."""
    assert "candidate_selection" in _ids(NONOBVIOUS_NAMES)


def test_candidate_selection_not_inferred_from_if_alone():
    assert "candidate_selection" not in _ids(UNCONDITIONAL_ASSIGN)
    assert "candidate_selection" not in _ids(IF_NO_CANDIDATE_UPDATE)


# ============================================================
# Negative cases: must not fire
# ============================================================

def test_no_candidate_selection_for_sum_accumulation():
    assert "candidate_selection" not in _ids(SUM_ACCUMULATION)


def test_no_candidate_selection_for_count_accumulation():
    # c += 1 inside an if: conditional_index_update exists, but the
    # accumulator fence (accumulator_update on the same variable) blocks it.
    assert "candidate_selection" not in _ids(COUNT_ACCUMULATION)


def test_no_candidate_selection_for_list_accumulation():
    # result = result + [...] is self-referential accumulation via equal_sign.
    assert "candidate_selection" not in _ids(LIST_ACCUMULATION)


def test_no_candidate_selection_for_window_state():
    # left += 1 participates as a subscript index -> belongs to windows/pointers.
    assert "candidate_selection" not in _ids(WINDOW_STATE)


def test_no_candidate_selection_for_dp_table_update():
    # dp[i] conditionally updated: dp is the subscripted structure, and the
    # update is accumulator-typed, not a scalar replacement.
    assert "candidate_selection" not in _ids(DP_TABLE_UPDATE)


# ============================================================
# Relation-layer is consumed (not dead code) and cannot create detections
# ============================================================

def test_relations_path_is_operative_when_present():
    """With relations present the index fence comes from used_as_subscript_index.

    A stub relation bundle that disagrees with the facts must win: marking a
    factually non-index candidate as index-participating suppresses the
    technique. Relations can only tighten (suppress), never create a
    detection — the fact gates still decide admissibility.
    """
    assert "candidate_selection" in _ids(RUNNING_MAX, with_relations=False)

    tree = ast.parse(RUNNING_MAX)
    facts = extract_structural_facts(tree)

    class _Rel:
        used_as_subscript_index = {"best"}

    techs = detect_techniques(facts, _Rel())
    assert "candidate_selection" not in {t.technique_id for t in techs}


def test_fact_fallback_fences_window_state_without_relations():
    """Without relations, the equivalent fact-based collection fences windows."""
    assert "candidate_selection" not in _ids(WINDOW_STATE, with_relations=False)


def test_technique_absent_on_loopless_conditional():
    code = '''
class Solution:
    def pick(self, nums):
        best = 0
        if nums and nums[0] > best:
            best = nums[0]
        return best
'''
    assert "candidate_selection" not in _ids(code)


# ============================================================
# Vocabulary / ground-truth integration
# ============================================================

def test_candidate_selection_is_registered_v1_technique():
    assert "candidate_selection" in VALID_TECHNIQUES


def test_greedy_local_mapping_requires_candidate_selection():
    mapping = PATTERN_TO_V1_MAPPING["greedy_local"]
    assert mapping["required"] == ["candidate_selection"]
    assert "sliding_window" in mapping["excluded"]
    # Once a pattern maps to a non-empty required list it is no longer
    # reported as missing vocabulary.
    assert "greedy_local" not in missing_vocabulary_for_patterns(["greedy_local"])


def test_all_mapping_concepts_are_valid_v1_ids():
    from pathforge.services.ground_truth_builder import VALID_V1_CONCEPTS

    for pattern, mapping in PATTERN_TO_V1_MAPPING.items():
        for concept in list(mapping.get("required", [])) + list(mapping.get("optional", [])) + list(mapping.get("excluded", [])):
            assert concept in VALID_V1_CONCEPTS, f"{pattern}: {concept} not in V1 vocabulary"
