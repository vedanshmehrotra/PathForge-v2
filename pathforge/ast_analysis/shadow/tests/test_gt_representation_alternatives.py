"""Ground-truth representation repair: alternatives must not collapse into a conjunction.

Vocabulary Layer 2 Step 2 exposed a representation defect: when a stored
``solution_groups`` row has no explicit ``required`` and its flat ``patterns``
list spans more than one **solution family**, ``_load_ground_truth`` re-derived
the concepts with ``_map_legacy_patterns_to_v1`` and merged them into ONE
conjunctive ``required`` list. ``["hash_map_lookup", "prefix_sum"]`` means
"approach A **or** approach B", so the merge produced a group no single
implementation could satisfy once more than one of the patterns had a
vocabulary concept.

The repair keeps explicit ``required`` authoritative and, for
vocabulary-derived groups, expands multi-family patterns into the same
alternative groups the flat-pattern fallback already derives.

These tests are structural: no problem-ID logic, no variable-name logic.
"""
import ast
import sys

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.relations import build_relations
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.matching import evaluate_solution_groups
from pathforge.services.ground_truth_builder import (
    find_ground_truth_disagreements,
    pattern_family,
    patterns_span_multiple_families,
    refresh_group_vocabulary,
)
from pathforge.services.problem_resolver import (
    _load_ground_truth,
    _split_csv_patterns_to_groups,
)


# ============================================================
# Fake DB harness
# ============================================================

class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeConnection:
    """Minimal connection double for ``_load_ground_truth``.

    Returns one stored ground-truth row and an optional curated ``pattern``
    value from ``problems``.
    """

    def __init__(self, gt_row, curated=None):
        self._gt_row = gt_row
        self._curated = curated

    def execute(self, query, params=None):
        if "problem_ground_truth" in query:
            return _Result(self._gt_row)
        if "FROM problems" in query:
            return _Result({"pattern": self._curated} if self._curated is not None else None)
        return _Result(None)


def _gt_row(solution_groups, patterns=None):
    groups = solution_groups
    return {
        "patterns": patterns if patterns is not None else [],
        "confidence": {},
        "solution_groups": groups,
        "validation_status": "unverified",
    }


def _load(solution_groups, pid=999, curated=None, patterns=None):
    """Load groups the way the app does, through the real ``_load_ground_truth``."""
    conn = _FakeConnection(_gt_row(solution_groups, patterns), curated=curated)
    return _load_ground_truth(conn, pid)


def _refresh_marked(solution_groups):
    """Run the Batch 2A vocabulary refresh, as the loader does, and return the groups."""
    for group in solution_groups:
        group.setdefault("provenance", ["vocabulary_v1"])
    from pathforge.services.ground_truth_builder import refresh_groups_vocabulary

    refresh_groups_vocabulary(solution_groups)
    return solution_groups


def _signature(groups):
    return sorted(
        (
            tuple(sorted(g.get("required") or [])),
            tuple(sorted(g.get("optional") or [])),
            tuple(sorted(g.get("excluded") or [])),
        )
        for g in groups
    )


# ============================================================
# 3236-shaped fixtures (flat alternatives, no explicit required)
# ============================================================

TWO_FAMILY_GROUP = [{
    "id": "group_0",
    "evidence": "llm_proposed",
    "patterns": ["hash_map_lookup", "prefix_sum"],
    "confidence": {"prefix_sum": 0.85, "hash_map_lookup": 0.75},
}]

LC3236_PREFIX_VARIANT_A = '''
class Solution:
    def missingInteger(self, nums: List[int]) -> int:
        j = 1
        summ = nums[0]
        while j <= len(nums) - 1 and nums[j] == nums[j - 1] + 1:
            summ += nums[j]
            j += 1
        while summ in nums:
            summ += 1
        return summ
'''

LC3236_PREFIX_VARIANT_B = '''
def missingInteger(nums):
    i = 1
    summ = nums[0]
    while i <= len(nums) - 1 and nums[i] == nums[i - 1] + 1:
        summ += nums[i]
        i += 1
    while summ in nums:
        summ += 1
    return summ
'''

LC3236_PREFIX_VARIANT_C = '''
class Solution:
    def missingInteger(self, nums: List[int]) -> int:
        i = 1
        summ = nums[0]
        while i < len(nums) and nums[i] == nums[i - 1] + 1:
            summ += nums[i]
            i += 1
        while summ in nums:
            summ += 1
        return summ
'''


def _shadow_outcome(code, groups):
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    techniques = detect_techniques(facts, build_relations(tree))
    strategies = evaluate_strategies(techniques, facts)
    return evaluate_solution_groups(groups, techniques, strategies, facts).outcome


# ============================================================
# 1. Alternatives must not become a conjunction
# ============================================================

class TestAlternativesNotConjunction:
    def test_two_family_patterns_load_as_two_alternative_groups(self):
        groups, _ = _load(TWO_FAMILY_GROUP)
        assert len(groups) == 2, groups
        assert sorted(tuple(g["required"]) for g in groups) == [
            ("hash_lookup",), ("sequential_accumulation",),
        ]

    def test_no_group_requires_both_families(self):
        groups, _ = _load(TWO_FAMILY_GROUP)
        for g in groups:
            assert len(g["required"]) == 1, g

    def test_family_patterns_are_kept_per_group(self):
        groups, _ = _load(TWO_FAMILY_GROUP)
        by_req = {g["required"][0]: g for g in groups}
        assert by_req["hash_lookup"]["patterns"] == ["hash_map_lookup"]
        assert by_req["sequential_accumulation"]["patterns"] == ["prefix_sum"]

    def test_exclusions_are_derived_per_family(self):
        groups, _ = _load(TWO_FAMILY_GROUP)
        by_req = {g["required"][0]: g for g in groups}
        assert by_req["hash_lookup"]["excluded"] == ["recursive_branching"]

    def test_stale_marked_group_is_still_expanded(self):
        """A provenance-marked group whose refresh is skipped is still expanded."""
        solution_groups = _refresh_marked([dict(g) for g in TWO_FAMILY_GROUP])
        groups, _ = _load(solution_groups)
        assert len(groups) == 2


# ============================================================
# 2. Stored path converges with the flat-pattern fallback
# ============================================================

class TestFallbackConvergence:
    def test_loaded_groups_match_the_fallback_splitter(self):
        loaded, _ = _load(TWO_FAMILY_GROUP)
        fallback = _split_csv_patterns_to_groups(
            ["hash_map_lookup", "prefix_sum"], {}, 1.0, "llm_proposed"
        )
        assert _signature(loaded) == _signature(fallback)

    def test_family_helper_is_the_shared_definition(self):
        assert pattern_family("hash_map_lookup") == "hash_lookup"
        assert pattern_family("prefix_sum") == "sequential_accumulation"
        assert pattern_family("topological_sort") is None
        assert patterns_span_multiple_families(["hash_map_lookup", "prefix_sum"])
        assert not patterns_span_multiple_families(["sliding_window_fixed", "sliding_window_variable"])

    def test_single_family_patterns_merge_same_as_before(self):
        groups, _ = _load([{
            "id": "group_0",
            "evidence": "llm_proposed",
            "patterns": ["sliding_window_fixed", "sliding_window_variable"],
        }])
        assert len(groups) == 1
        assert groups[0]["required"] == ["sliding_window"]


# ============================================================
# 3. Real submissions confirm against the repaired groups
# ============================================================

class TestSubmissionsAgainstRepairedGroups:
    @pytest.mark.parametrize("code", [
        LC3236_PREFIX_VARIANT_A, LC3236_PREFIX_VARIANT_B, LC3236_PREFIX_VARIANT_C,
    ])
    def test_3236_style_submissions_confirm(self, code):
        groups, _ = _load(TWO_FAMILY_GROUP)
        assert _shadow_outcome(code, groups) == "CONFIRMED"

    def test_conjunctive_representation_would_fail_them(self):
        """Control: the pre-fix conjunctive group is what made them UNRESOLVED."""
        conjunctive = [{
            "id": "group_0",
            "required": ["hash_lookup", "sequential_accumulation"],
            "patterns": ["hash_map_lookup", "prefix_sum"],
        }]
        groups, _ = _load(conjunctive)
        assert groups[0]["required"] == ["hash_lookup", "sequential_accumulation"]
        assert _shadow_outcome(LC3236_PREFIX_VARIANT_A, groups) == "UNRESOLVED"


# ============================================================
# 4/5. Explicit structured groups stay authoritative
# ============================================================

class TestExplicitStructuredGroupsPreserved:
    def test_genuine_conjunction_is_preserved(self):
        groups, _ = _load([{
            "id": "group_0",
            "required": ["hash_lookup", "sequential_accumulation"],
            "patterns": ["hash_map_lookup", "prefix_sum"],
        }])
        assert len(groups) == 1
        assert groups[0]["required"] == ["hash_lookup", "sequential_accumulation"]

    def test_required_optional_excluded_preserved_exactly(self):
        groups, _ = _load([{
            "id": "group_0",
            "required": ["sequential_accumulation"],
            "optional": ["iterative_table_filling"],
            "excluded": ["bfs_shortest_path"],
            "patterns": ["hash_map_lookup", "prefix_sum"],
        }])
        assert len(groups) == 1
        assert groups[0]["required"] == ["sequential_accumulation"]
        assert groups[0]["optional"] == ["iterative_table_filling"]
        assert groups[0]["excluded"] == ["bfs_shortest_path"]


# ============================================================
# 6. Empty-required groups stay unmatchable (Batch 2A invariant)
# ============================================================

class TestEmptyRequiredStillUnmatchable:
    def test_unmapped_single_pattern_stays_unmatchable(self):
        groups, _ = _load([{"id": "group_0", "patterns": ["topological_sort"], "required": []}])
        assert len(groups) == 1
        assert groups[0]["required"] == []
        assert groups[0]["matchable"] is False
        assert groups[0].get("matchability_reason")

    def test_refresh_does_not_collapse_multi_family_group(self):
        group = {
            "id": "group_0",
            "patterns": ["hash_map_lookup", "prefix_sum"],
            "required": [],
            "provenance": ["vocabulary_v1"],
        }
        assert refresh_group_vocabulary(group, {}) is False
        assert group["required"] == []

    def test_refresh_still_updates_single_family_group(self):
        group = {
            "id": "group_0",
            "patterns": ["prefix_sum"],
            "required": ["sliding_window"],
            "provenance": ["vocabulary_v1"],
        }
        assert refresh_group_vocabulary(group, {}) is True
        assert group["required"] == ["sequential_accumulation"]


# ============================================================
# 7. hash_lookup behavior unchanged
# ============================================================

class TestHashLookupUnchanged:
    def test_hash_lookup_still_detected(self):
        code = '''
class Solution:
    def twoSum(self, nums, target):
        seen = {}
        for i, num in enumerate(nums):
            complement = target - num
            if complement in seen:
                return [seen[complement], i]
            seen[num] = i
        return []
'''
        tree = ast.parse(code)
        techs = {t.technique_id for t in detect_techniques(extract_structural_facts(tree))}
        assert "hash_lookup" in techs

    def test_set_membership_still_not_hash_lookup(self):
        code = '''
def f(nums):
    seen = set()
    for n in nums:
        if n in seen:
            return True
        seen.add(n)
    return False
'''
        tree = ast.parse(code)
        techs = {t.technique_id for t in detect_techniques(extract_structural_facts(tree))}
        assert "hash_lookup" not in techs


# ============================================================
# 8/9/10. Genericity + representation consistency
# ============================================================

class TestGenericityAndConsistency:
    def test_derivation_is_problem_id_independent(self):
        a, _ = _load([dict(g) for g in TWO_FAMILY_GROUP], pid=1)
        b, _ = _load([dict(g) for g in TWO_FAMILY_GROUP], pid=987654)
        assert _signature(a) == _signature(b)

    def test_flat_patterns_and_structured_groups_do_not_disagree(self):
        groups, _ = _load(TWO_FAMILY_GROUP)
        findings = find_ground_truth_disagreements(
            ["hash_map_lookup", "prefix_sum"], groups
        )
        kinds = {f["kind"] for f in findings}
        assert "pattern_not_in_groups" not in kinds
        assert "group_pattern_not_declared" not in kinds
        assert "concept_not_derived_from_patterns" not in kinds
        assert "unmatchable_group" not in kinds

    def test_alternatives_are_still_matchable(self):
        groups, _ = _load(TWO_FAMILY_GROUP)
        assert all(g["matchable"] for g in groups)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
