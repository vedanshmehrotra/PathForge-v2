"""B5.5 — Ground-Truth / authority normalization + alternative families.

Covers the four normalization areas:

* one canonical authority vocabulary (stored value → canonical tier);
* Ground-Truth serialization that preserves ``authority_tier``;
* ``authority_tier`` vs ``evidence`` agreement reporting;
* explicit ``ONE_OF`` alternative families and their aggregation.

Plus regression checks that B2/B3/B4, the legacy matcher and production
scoring are unchanged.

Expected values were measured from the pipeline, not assumed.
"""

import copy
import json
import pathlib

import pytest

from pathforge.ast_analysis import authority_vocabulary as vocab
from pathforge.ast_analysis.shadow import authority_gating as ag
from pathforge.ast_analysis.shadow import evidence_state as ev
from pathforge.ast_analysis.shadow import family_coverage as fc
from pathforge.ast_analysis.shadow import matching
from pathforge.ast_analysis.shadow import primary_strategy as ps
from pathforge.ast_analysis.shadow.data_structures import StrategyEvidence
from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.relations import build_relations
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.services.ground_truth_builder import (
    VALID_AUTHORITY_TIERS,
    alternative_group_id_for,
    deserialize_solution_groups,
    find_ground_truth_disagreements,
    mark_family_relations,
    serialize_solution_groups,
)
from pathforge.services.problem_resolver import _load_ground_truth

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_CORPUS_A = (
    _REPO_ROOT / "experiments" / "code_analysis_evaluation" / "results"
    / "db_batch3" / "submission_eval_results.json"
)


# ============================================================================
# Helpers
# ============================================================================

def _pipeline(code):
    tree = __import__("ast").parse(code)
    relations = build_relations(tree)
    facts = extract_structural_facts(tree)
    techniques = detect_techniques(facts, relations=relations)
    strategies = evaluate_strategies(techniques, facts)
    return facts, techniques, strategies


def snapshot_with_strategies(*strategy_ids, confidence=0.9):
    return ev.build_evidence_snapshot(
        [], [],
        [StrategyEvidence(strategy_id=s, confidence=confidence) for s in strategy_ids],
    )


def family(family_id, required, authority=None, relation=None, alt_group=None):
    fam = {"id": family_id, "required": list(required)}
    if authority is not None:
        fam["authority_tier"] = authority
    if relation is not None:
        fam["family_relation"] = relation
    if alt_group is not None:
        fam["alternative_group_id"] = alt_group
    return fam


def evaluate(groups, snap):
    cov = fc.build_family_coverage(groups, snap)
    sel = ps.select_submission_primary(groups, snap, cov)
    return ag.evaluate_authority(groups, cov, sel)


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeConnection:
    def __init__(self, gt_row, curated=None):
        self._gt_row = gt_row
        self._curated = curated

    def execute(self, query, params=None):
        if "problem_ground_truth" in query:
            return _Result(self._gt_row)
        if "FROM problems" in query:
            return _Result({"pattern": self._curated}
                           if self._curated is not None else None)
        return _Result(None)


def _gt_row(solution_groups, patterns=None):
    return {
        "patterns": patterns if patterns is not None else [],
        "confidence": {},
        "solution_groups": solution_groups,
        "validation_status": "unverified",
    }


def _load(solution_groups, pid=999, curated=None, patterns=None):
    conn = _FakeConnection(_gt_row(solution_groups, patterns), curated=curated)
    return _load_ground_truth(conn, pid)


def _corpus_a_records():
    if not _CORPUS_A.exists():
        return {}
    payload = json.loads(_CORPUS_A.read_text(encoding="utf-8"))
    return {rec.get("external_submission_id"): rec for rec in payload["records"]}


TWO_SUM = """
class Solution:
    def twoSum(self, nums, target):
        seen = {}
        for i, num in enumerate(nums):
            complement = target - num
            if complement in seen:
                return [seen[complement], i]
            seen[num] = i
        return []
"""

WINDOW_209 = """
def minSubArrayLen(target, nums):
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

BINARY_SEARCH = """
def search(nums, target):
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

CLIMB_BOTTOM_UP = """
def climbStairs(n):
    if n <= 2:
        return n
    table = [0] * (n + 1)
    table[1] = 1
    table[2] = 2
    for i in range(3, n + 1):
        table[i] = table[i - 1] + table[i - 2]
    return table[n]
"""

HASH_AND_WINDOW = """
def solve(nums, target):
    seen = {}
    left = 0
    total = 0
    best = 0
    for right in range(len(nums)):
        total += nums[right]
        if target - nums[right] in seen:
            best = max(best, total)
        while total > target:
            total -= nums[left]
            left += 1
        seen[nums[right]] = right
    return best
"""


# ============================================================================
# 1-11. AUTHORITY
# ============================================================================

class TestCanonicalAuthority:

    @pytest.mark.parametrize("stored, expected", [
        ("human_curated", vocab.HUMAN_APPROVED),
        ("human_approved", vocab.HUMAN_APPROVED),
        ("reviewed", vocab.HUMAN_APPROVED),
        ("editorial", vocab.HUMAN_APPROVED),
        ("externally_listed", vocab.EXTERNAL_VERIFIED),
        ("structurally_observed", vocab.STRUCTURALLY_OBSERVED),
        ("llm_proposed", vocab.INFERRED),
        ("bootstrap", vocab.INFERRED),
        ("unknown", vocab.INFERRED),
        ("unobserved", vocab.INFERRED),
    ])
    def test_1_to_10_stored_values_map_canonically(self, stored, expected):
        assert vocab.normalize_authority_tier(stored) == expected

    def test_1_human_curated_is_human_approved(self):
        assert vocab.normalize_authority_tier("human_curated") == vocab.HUMAN_APPROVED
        assert vocab.is_authorizing("human_curated") is True

    def test_2_human_approved_is_human_approved(self):
        assert vocab.is_authorizing("human_approved") is True

    def test_3_reviewed_is_human_approved(self):
        assert vocab.normalize_authority_tier("reviewed") == vocab.HUMAN_APPROVED

    def test_4_editorial_is_human_approved(self):
        assert vocab.normalize_authority_tier("editorial") == vocab.HUMAN_APPROVED

    def test_5_externally_listed_is_external_verified(self):
        assert vocab.normalize_authority_tier("externally_listed") == \
            vocab.EXTERNAL_VERIFIED
        assert vocab.is_authorizing("externally_listed") is True

    def test_6_structurally_observed_is_not_authorizing(self):
        assert vocab.normalize_authority_tier("structurally_observed") == \
            vocab.STRUCTURALLY_OBSERVED
        assert vocab.is_authorizing("structurally_observed") is False

    def test_7_llm_proposed_is_inferred(self):
        assert vocab.normalize_authority_tier("llm_proposed") == vocab.INFERRED

    def test_8_bootstrap_is_inferred(self):
        assert vocab.normalize_authority_tier("bootstrap") == vocab.INFERRED

    def test_9_unknown_is_conservative(self):
        assert vocab.normalize_authority_tier("unknown") == vocab.INFERRED
        assert vocab.is_missing_authority("unknown") is True

    def test_10_unobserved_is_conservative(self):
        assert vocab.normalize_authority_tier("unobserved") == vocab.INFERRED
        assert vocab.is_missing_authority("unobserved") is True

    def test_11_unknown_cannot_accidentally_authorize(self):
        for value in ("unknown", "unobserved", "", None, "made_up", "llm_proposed"):
            assert vocab.is_authorizing(value) is False
            assert vocab.normalize_authority_tier(value) not in vocab.AUTHORIZING_TIERS

    def test_single_canonical_vocabulary_is_shared(self):
        # B5 re-exports the canonical map rather than restating it.
        assert ag.AUTHORITY_TIER_MAP is vocab.SOURCE_TIER_MAP
        assert ag.AUTHORIZING_TIERS is vocab.AUTHORIZING_TIERS
        assert ag.BUILDER_AUTHORITY_TIERS == vocab.VALID_GT_TIERS
        # The builder accepts the canonical set (human_curated included).
        assert VALID_AUTHORITY_TIERS == set(vocab.VALID_GT_TIERS)
        assert "human_curated" in VALID_AUTHORITY_TIERS
        assert "reviewed" in VALID_AUTHORITY_TIERS

    def test_legacy_shadow_authority_uses_canonical_vocabulary(self):
        from pathforge.ast_analysis.shadow import authority as legacy
        assert legacy.VALID_AUTHORITY_TIERS == set(vocab.KNOWN_SOURCE_TIERS)


# ============================================================================
# 12-14. SERIALIZATION
# ============================================================================

class TestSerialization:

    GROUPS = [
        {"id": "group_0", "version": 1, "required": ["dp_bottom_up"],
         "optional": ["iterative_table_filling"], "excluded": ["recursive_branching"],
         "threshold": 0.5, "authority_tier": "human_curated",
         "provenance": ["csv_curated"], "patterns": ["dp_1d_forward"],
         "derivation_patterns": ["dp_1d_forward"], "evidence": "human_curated",
         "confidence": {"dp_1d_forward": 0.9}, "matchable": True},
        {"id": "group_1", "required": ["dp_top_down"], "authority_tier": "human_curated",
         "family_relation": "ONE_OF", "alternative_group_id": "one_of_x"},
    ]

    def test_12_authority_tier_survives_round_trip(self):
        round_tripped = deserialize_solution_groups(
            json.dumps(serialize_solution_groups(self.GROUPS))
        )
        assert round_tripped == self.GROUPS
        assert round_tripped[0]["authority_tier"] == "human_curated"
        assert round_tripped[1]["family_relation"] == "ONE_OF"

    def test_13_no_unrelated_field_changes(self):
        round_tripped = deserialize_solution_groups(
            json.dumps(serialize_solution_groups(self.GROUPS))
        )
        for original, restored in zip(self.GROUPS, round_tripped):
            assert original == restored
            assert set(original) == set(restored)

    def test_13b_serialization_from_text_and_list_are_equivalent(self):
        as_text = deserialize_solution_groups(
            json.dumps(serialize_solution_groups(self.GROUPS))
        )
        as_list = deserialize_solution_groups(serialize_solution_groups(self.GROUPS))
        assert as_text == as_list

    def test_14_missing_authority_remains_explicitly_missing(self):
        group = {"id": "group_0", "required": ["sliding_window"]}
        round_tripped = deserialize_solution_groups(json.dumps([group]))
        assert "authority_tier" not in round_tripped[0]
        # absent metadata is not silently invented
        assert vocab.normalize_authority_tier(
            round_tripped[0].get("authority_tier")
        ) == vocab.INFERRED

    def test_14b_loader_preserves_authority_tier(self):
        groups, _ = _load([{
            "id": "group_0", "required": ["sliding_window"],
            "patterns": ["sliding_window_variable"], "authority_tier": "human_curated",
        }], pid=209)
        assert groups[0]["authority_tier"] == "human_curated"


# ============================================================================
# 15-16. EVIDENCE vs AUTHORITY_TIER
# ============================================================================

class TestAuthorityEvidence:

    def test_15_disagreement_is_detected_and_reported(self):
        agree = vocab.authority_evidence_agreement(
            {"authority_tier": "human_curated", "evidence": "human_curated"}
        )
        assert agree["agree"] is True

        disagree = vocab.authority_evidence_agreement(
            {"authority_tier": "structurally_observed", "evidence": "llm_proposed"}
        )
        assert disagree["agree"] is False
        assert disagree["authority_canonical"] == vocab.STRUCTURALLY_OBSERVED
        assert disagree["evidence_canonical"] == vocab.INFERRED

        findings = vocab.find_authority_evidence_disagreements([
            {"id": "g0", "authority_tier": "human_curated", "evidence": "llm_proposed"},
            {"id": "g1", "authority_tier": "llm_proposed", "evidence": "llm_proposed"},
        ])
        assert [f["group_id"] for f in findings] == ["g0"]

    def test_16_canonical_interpretation_is_deterministic(self):
        group = {"authority_tier": "editorial", "evidence": "editorial"}
        first = vocab.canonical_authority_of_group(group)
        second = vocab.canonical_authority_of_group(copy.deepcopy(group))
        assert first == second == ("editorial", vocab.HUMAN_APPROVED)

    def test_16b_group_without_tier_falls_back_to_evidence(self):
        stored, canonical = vocab.canonical_authority_of_group(
            {"evidence": "structurally_observed"}
        )
        assert stored == "structurally_observed"
        assert canonical == vocab.STRUCTURALLY_OBSERVED


# ============================================================================
# 17-24. ALTERNATIVES / ONE_OF
# ============================================================================

def _one_of_groups():
    return [
        family("g0", ["dp_bottom_up"], authority="human_curated",
               relation="ONE_OF", alt_group="one_of_dp"),
        family("g1", ["dp_top_down"], authority="human_curated",
               relation="ONE_OF", alt_group="one_of_dp"),
    ]


class TestAlternatives:

    def test_17_explicit_one_of_families_are_represented(self):
        snap = snapshot_with_strategies("dp_bottom_up")
        report = evaluate(_one_of_groups(), snap)
        assert report.logical_requirement_count() == 1
        assert len(report.alternative_groups) == 1
        group = report.alternative_groups[0]
        assert group.family_ids == ("g0", "g1")
        assert group.authoritative is True
        assert group.authoritative_family_ids == ("g0",)

    def test_18_one_confirmed_alternative_satisfies_the_group(self):
        snap = snapshot_with_strategies("dp_bottom_up")
        report = evaluate(_one_of_groups(), snap)
        assert report.get("g0").authoritative is True
        assert report.get("g1").authoritative is False
        assert report.get_alternative_group("one_of_dp").authoritative is True

    def test_19_unresolved_sibling_does_not_cause_mixed_authority(self):
        snap = snapshot_with_strategies("dp_bottom_up")
        with_relation = evaluate(_one_of_groups(), snap)
        assert with_relation.aggregation == ag.AGG_ALL_FAMILIES_AUTHORITATIVE
        assert with_relation.safe_for_product_scoring() is True

        # Same evidence without the explicit relation -> conservatively mixed.
        plain = [family("g0", ["dp_bottom_up"], authority="human_curated"),
                 family("g1", ["dp_top_down"], authority="human_curated")]
        without = evaluate(plain, snap)
        assert without.aggregation == ag.AGG_MIXED_AUTHORITY
        assert without.safe_for_product_scoring() is False

    def test_20_two_confirmed_alternatives_remain_visible(self):
        snap = snapshot_with_strategies("dp_bottom_up", "dp_top_down")
        report = evaluate(_one_of_groups(), snap)
        group = report.get_alternative_group("one_of_dp")
        assert set(group.authoritative_family_ids) == {"g0", "g1"}
        assert group.reason_codes == (ag.REASON_ALTERNATIVE_MULTIPLE_SATISFIED,)
        # both individual decisions preserved
        assert report.get("g0").authoritative and report.get("g1").authoritative

    def test_21_no_confirmed_alternative_remains_unsatisfied(self):
        snap = snapshot_with_strategies("sliding_window")  # unrelated
        report = evaluate(_one_of_groups(), snap)
        group = report.get_alternative_group("one_of_dp")
        assert group.authoritative is False
        assert group.reason_codes == (ag.REASON_ALTERNATIVE_UNSATISFIED,)
        assert report.safe_for_product_scoring() is False

    def test_21b_one_of_of_one_is_not_treated_as_a_group(self):
        groups = [family("g0", ["dp_bottom_up"], authority="human_curated",
                         relation="ONE_OF", alt_group="solo")]
        snap = snapshot_with_strategies("dp_bottom_up")
        report = evaluate(groups, snap)
        assert report.alternative_groups == ()
        assert report.logical_requirement_count() == 1
        assert report.get("g0").authoritative is True

    def test_22_independent_families_remain_independent(self):
        groups = [
            family("g0", ["dp_bottom_up"], authority="human_curated"),
            family("g1", ["dp_top_down"], authority="human_curated"),
        ]
        snap = snapshot_with_strategies("dp_bottom_up")
        report = evaluate(groups, snap)
        assert report.alternative_groups == ()
        assert report.logical_requirement_count() == 2
        assert report.aggregation == ag.AGG_MIXED_AUTHORITY

    def test_23_unrelated_families_are_not_merged(self):
        groups = [
            family("g0", ["dp_bottom_up"], authority="human_curated",
                   relation="ONE_OF", alt_group="set_a"),
            family("g1", ["dp_top_down"], authority="human_curated",
                   relation="ONE_OF", alt_group="set_a"),
            family("g2", ["sliding_window"], authority="human_curated"),
        ]
        snap = snapshot_with_strategies("dp_bottom_up", "sliding_window")
        report = evaluate(groups, snap)
        assert report.logical_requirement_count() == 2
        assert len(report.alternative_groups) == 1
        assert report.aggregation == ag.AGG_ALL_FAMILIES_AUTHORITATIVE

    def test_24_alternative_metadata_survives_serialization(self):
        groups = _one_of_groups()
        round_tripped = deserialize_solution_groups(
            json.dumps(serialize_solution_groups(groups))
        )
        assert round_tripped == groups
        snap = snapshot_with_strategies("dp_bottom_up")
        assert evaluate(round_tripped, snap).aggregation == \
            ag.AGG_ALL_FAMILIES_AUTHORITATIVE

    def test_24a_mark_family_relations_marks_curated_alternatives(self):
        groups = [
            {"id": "group_0", "required": ["dp_bottom_up"],
             "patterns": ["dp_1d_forward"], "derivation_patterns": ["dp_1d_forward"]},
            {"id": "group_1", "required": ["dp_top_down"],
             "patterns": ["dp_1d_forward"], "derivation_patterns": ["dp_1d_forward"]},
        ]
        assert mark_family_relations(groups) == ["group_0", "group_1"]
        assert groups[0]["family_relation"] == "ONE_OF"
        assert groups[0]["alternative_group_id"] == groups[1]["alternative_group_id"]
        # idempotent
        assert mark_family_relations(groups) == []

    def test_24b_mark_family_relations_leaves_independent_families_alone(self):
        groups = [
            {"id": "group_0", "required": ["forward_pointer_advance"],
             "patterns": ["two_pointers_same"], "derivation_patterns": ["two_pointers_same"]},
            {"id": "group_1", "required": ["sequential_accumulation"],
             "patterns": ["prefix_sum"], "derivation_patterns": ["prefix_sum"]},
        ]
        assert mark_family_relations(groups) == []
        assert "family_relation" not in groups[0]

    def test_24c_loader_marks_stored_curated_alternatives(self):
        groups, _ = _load([
            {"id": "group_0", "required": ["dp_bottom_up"],
             "patterns": ["dp_1d_forward"], "derivation_patterns": ["dp_1d_forward"],
             "authority_tier": "human_curated"},
            {"id": "group_1", "required": ["dp_top_down"],
             "patterns": ["dp_1d_forward"], "derivation_patterns": ["dp_1d_forward"],
             "authority_tier": "human_curated"},
        ], pid=237)
        assert groups[0]["family_relation"] == "ONE_OF"
        assert groups[0]["alternative_group_id"] == groups[1]["alternative_group_id"]
        assert alternative_group_id_for(("dp_1d_forward",)) == \
            groups[0]["alternative_group_id"]

    def test_24d_loader_marks_csv_split_alternatives(self):
        groups, _ = _load(None, pid=999, patterns=["bfs_shortest_path", "dp_1d_forward"])
        assert len(groups) == 2
        assert all(g["family_relation"] == "ONE_OF" for g in groups)
        assert groups[0]["alternative_group_id"] == groups[1]["alternative_group_id"]


# ============================================================================
# 25-35. REGRESSION
# ============================================================================

class TestRegression:

    def _record(self, submission_id):
        records = _corpus_a_records()
        rec = records[submission_id]
        groups = copy.deepcopy(rec["groups"])
        for g in groups:
            g.setdefault("authority_tier", rec.get("shadow_authority_tier") or "unknown")
        return rec["source_code"], groups

    def test_25_lc209_behaviour_unchanged(self):
        code, groups = self._record("db-190")
        result = run_shadow_analysis(code, solution_groups=groups)
        assert result["coverage"]["aggregate_state"] == "CONFIRMED"
        assert result["strategy_selection"]["submission"]["selected"] == "sliding_window"
        assert result["match_outcome"]["outcome"] == "CONFIRMED"
        fam = result["authority"]["families"][0]
        assert fam["authoritative"] is True

    def test_26_lc102_behaviour_unchanged(self):
        code, groups = self._record("db-244")
        groups = [dict(g, authority_tier="unknown") for g in groups]
        result = run_shadow_analysis(code, solution_groups=groups)
        assert result["strategy_selection"]["submission"]["selected"] == "bfs_shortest_path"
        assert result["coverage"]["aggregate_state"] == "CONFIRMED"
        assert result["authority"]["families"][0]["authoritative"] is False

    def test_27_lc704_behaviour_unchanged(self):
        code, groups = self._record("db-235")
        result = run_shadow_analysis(code, solution_groups=groups)
        assert result["strategy_selection"]["submission"]["selected"] == "binary_search"
        assert result["authority"]["families"][0]["authoritative"] is True

    @pytest.mark.parametrize("submission_id", ["db-49", "db-51", "db-194"])
    def test_28_lc3236_stays_unresolved_and_non_authoritative(self, submission_id):
        code, groups = self._record(submission_id)
        result = run_shadow_analysis(code, solution_groups=groups)
        assert result["coverage"]["aggregate_state"] == "UNRESOLVED"
        assert result["authority"]["families"][0]["authoritative"] is False
        assert result["authority"]["safe_for_product_scoring"] is False

    def test_29_lc1_stays_unmatchable_and_non_authoritative(self):
        code, groups = self._record("db-11")
        result = run_shadow_analysis(code, solution_groups=groups)
        assert result["coverage"]["aggregate_state"] == "UNMATCHABLE"
        assert result["authority"]["families"][0]["authoritative"] is False

    def test_30_lc560_does_not_fabricate_a_strategy(self):
        groups = [family("g0", ["frequency_counting", "sequential_accumulation"],
                         authority="human_curated")]
        result = run_shadow_analysis(HASH_AND_WINDOW, solution_groups=groups)
        assert result["strategy_selection"]["submission"]["selected"] is None
        assert result["authority"]["families"][0]["authoritative"] is False

    def test_31_b2_evidence_unchanged(self):
        for code in (TWO_SUM, WINDOW_209, BINARY_SEARCH):
            facts, techniques, strategies = _pipeline(code)
            assert run_shadow_analysis(code)["evidence_state"] == \
                ev.build_evidence_snapshot(facts, techniques, strategies).to_dict()

    def test_32_ordinary_b3_coverage_unchanged(self):
        groups = [{"id": "group_0", "required": ["sliding_window"],
                   "authority_tier": "human_curated"}]
        _, techniques, strategies = _pipeline(WINDOW_209)
        facts = extract_structural_facts(__import__("ast").parse(WINDOW_209))
        direct = fc.build_family_coverage(
            groups, ev.build_evidence_snapshot(facts, techniques, strategies)
        )
        result = run_shadow_analysis(WINDOW_209, solution_groups=groups)
        # every semantic field is unchanged; only the additive relation fields
        # are new (and must be None for an ordinary family)
        for key in ("coverage_state", "reason_codes", "present_identifying",
                    "not_established_identifying", "contradicted_identifying",
                    "present_supporting", "conclusion_eligible_present",
                    "authority_tier"):
            assert result["coverage"]["families"][0][key] == \
                direct.families[0].to_dict()[key], key
        assert result["coverage"]["families"][0]["family_relation"] is None
        assert result["coverage"]["families"][0]["alternative_group_id"] is None

    def test_33_b4_selection_unchanged(self):
        groups = [{"id": "group_0", "required": ["sliding_window"]}]
        facts, techniques, strategies = _pipeline(WINDOW_209)
        snap = ev.build_evidence_snapshot(facts, techniques, strategies)
        cov = fc.build_family_coverage(groups, snap)
        direct = ps.select_submission_primary(groups, snap, cov)
        result = run_shadow_analysis(WINDOW_209, solution_groups=groups)
        assert result["strategy_selection"]["submission"]["selected"] == \
            direct.submission.selected

    def test_34_legacy_matcher_unchanged(self):
        groups = [{"id": "group_0", "required": ["sliding_window"],
                   "authority_tier": "human_curated"}]
        facts, techniques, strategies = _pipeline(WINDOW_209)
        direct = matching.evaluate_solution_groups(groups, techniques, strategies, facts)
        result = run_shadow_analysis(WINDOW_209, solution_groups=groups)
        assert result["match_outcome"]["outcome"] == direct.outcome
        assert result["match_outcome"]["primary_strategy"] == direct.primary_strategy

    def test_35_no_production_scoring_changes(self):
        # The recorded production policy is unchanged by B5.5 (migration is B6).
        from pathforge.services import persistence as prod_persistence
        assert prod_persistence._AUTHORITATIVE_STATES == \
            vocab.LEGACY_PRODUCTION_AUTHORITATIVE_STATES
        assert matching._AUTHORITATIVE_TIERS == \
            vocab.LEGACY_PRODUCTION_AUTHORITATIVE_TIERS

    def test_gt_disagreements_are_still_reported(self):
        groups = [
            {"id": "group_1", "required": ["dp_top_down"],
             "patterns": ["dp_1d_forward"], "derivation_patterns": ["dp_1d_forward"]},
        ]
        findings = find_ground_truth_disagreements(["dp_1d_forward"], groups)
        assert any(f["kind"] == "concept_not_derived_from_patterns" for f in findings)
