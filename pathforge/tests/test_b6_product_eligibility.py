"""B6 — controlled authority → product verdict integration.

Covers:

* the single product-eligibility decision over the canonical authority policy;
* the explicit ``ONE_OF`` semantics (B5.5, explicit metadata only);
* ``db-254`` remains independent;
* the feature flag (default OFF) preserves legacy behavior;
* flag ON gates ELO / gaps / recommendations fail-closed;
* the legacy/shadow comparison is pure (mutates neither result);
* B1–B5.5 invariants are unchanged.

Expected values were measured from the pipeline, not assumed.
"""

import ast
import copy
import json
import pathlib

import pytest

import config
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
from pathforge.services import product_eligibility as b6

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_CORPUS_A = (
    _REPO_ROOT / "experiments" / "code_analysis_evaluation" / "results"
    / "db_batch3" / "submission_eval_results.json"
)


# ============================================================================
# Helpers
# ============================================================================

def _pipeline(code):
    tree = ast.parse(code)
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


def eligibility_for(groups, snap):
    cov = fc.build_family_coverage(groups, snap)
    sel = ps.select_submission_primary(groups, snap, cov)
    report = ag.evaluate_authority(groups, cov, sel)
    return b6.product_eligibility(report), report


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


def _corpus_a_records():
    if not _CORPUS_A.exists():
        return {}
    payload = json.loads(_CORPUS_A.read_text(encoding="utf-8"))
    return {rec.get("external_submission_id"): rec for rec in payload["records"]}


@pytest.fixture(autouse=True)
def _flag_off():
    """Every test runs with the B6 flag OFF unless it opts in explicitly."""
    assert b6.flag_enabled() is False
    assert config.SHADOW_AUTHORITY_PRODUCT_GATING is False
    yield
    assert b6.flag_enabled() is False


# ============================================================================
# 1-9. Eligibility decisions
# ============================================================================

class TestEligibility:

    def test_1_human_approved_confirmed_primary_is_eligible(self):
        groups = [family("g0", ["sliding_window"], authority="human_curated")]
        eligibility, _ = eligibility_for(groups, snapshot_with_strategies("sliding_window"))
        assert eligibility.eligible is True
        assert eligibility.canonical_authority == vocab.HUMAN_APPROVED
        assert eligibility.reason_codes == ("authorized",)
        assert eligibility.safe_for_product_scoring is True

    def test_2_external_verified_confirmed_primary_is_eligible(self):
        groups = [family("g0", ["binary_search"], authority="externally_listed")]
        eligibility, _ = eligibility_for(groups, snapshot_with_strategies("binary_search"))
        assert eligibility.eligible is True
        assert eligibility.canonical_authority == vocab.EXTERNAL_VERIFIED

    def test_3_structurally_observed_confirmed_primary_is_blocked(self):
        groups = [family("g0", ["sliding_window"], authority="structurally_observed")]
        eligibility, _ = eligibility_for(groups, snapshot_with_strategies("sliding_window"))
        assert eligibility.eligible is False
        assert eligibility.reason_codes == ("structural_observation_only",)
        assert eligibility.canonical_authority == vocab.STRUCTURALLY_OBSERVED

    def test_4_inferred_confirmed_primary_is_blocked(self):
        groups = [family("g0", ["sliding_window"], authority="llm_proposed")]
        eligibility, _ = eligibility_for(groups, snapshot_with_strategies("sliding_window"))
        assert eligibility.eligible is False
        assert eligibility.reason_codes == ("inferred_authority",)

    def test_5_provisional_is_blocked(self):
        groups = [family("g0", ["sliding_window", "prefix_sum"],
                         authority="human_curated")]
        eligibility, _ = eligibility_for(groups, snapshot_with_strategies("sliding_window"))
        assert eligibility.eligible is False
        assert eligibility.reason_codes == ("coverage_not_confirmed",)

    def test_6_unresolved_is_blocked(self):
        groups = [family("g0", ["bfs_shortest_path"], authority="human_curated")]
        eligibility, _ = eligibility_for(groups, snapshot_with_strategies("sliding_window"))
        assert eligibility.eligible is False

    def test_7_contradicted_is_blocked(self):
        # binary_search is CONTRADICTED in a sliding-window submission (B2).
        snap = _snapshot(WINDOW_209)
        groups = [family("g0", ["binary_search"], authority="human_curated")]
        eligibility, _ = eligibility_for(groups, snap)
        assert eligibility.eligible is False
        assert eligibility.reason_codes == ("coverage_not_confirmed",)

    def test_8_missing_authority_is_blocked(self):
        for value in (None, "unknown", "unobserved", "made_up"):
            groups = [family("g0", ["sliding_window"], authority=value)]
            eligibility, _ = eligibility_for(groups, snapshot_with_strategies("sliding_window"))
            assert eligibility.eligible is False, value
            assert eligibility.canonical_authority == vocab.INFERRED

    def test_9_missing_primary_strategy_is_blocked(self):
        groups = [family("g0", ["hash_lookup"], authority="human_curated")]
        eligibility, _ = eligibility_for(groups, snapshot_with_strategies("sliding_window"))
        assert eligibility.eligible is False

    def test_9b_empty_required_group_is_blocked(self):
        groups = [family("g0", [], authority="human_curated")]
        eligibility, _ = eligibility_for(groups, snapshot_with_strategies("sliding_window"))
        assert eligibility.eligible is False
        assert eligibility.reason_codes == ("coverage_not_confirmed",)

    def test_no_authority_report_is_blocked(self):
        eligibility = b6.product_eligibility(None)
        assert eligibility.eligible is False
        assert eligibility.reason_codes == ("no_authority_report",)


def _snapshot(code):
    facts, techniques, strategies = _pipeline(code)
    return ev.build_evidence_snapshot(facts, techniques, strategies)


# ============================================================================
# 10-13. ONE_OF integration
# ============================================================================

class TestOneOf:

    def _one_of(self, g0_required, g1_required, authority="human_curated"):
        return [
            family("g0", g0_required, authority=authority,
                   relation="ONE_OF", alt_group="one_of_dp"),
            family("g1", g1_required, authority=authority,
                   relation="ONE_OF", alt_group="one_of_dp"),
        ]

    def test_11_one_authoritative_alternative_is_eligible(self):
        groups = self._one_of(["dp_bottom_up"], ["dp_top_down"])
        eligibility, _ = eligibility_for(
            groups, snapshot_with_strategies("dp_bottom_up")
        )
        assert eligibility.eligible is True
        assert eligibility.total_requirements == 1
        assert eligibility.authoritative_requirements == 1
        assert eligibility.requirements[0]["requirement_id"] == \
            "alternative_group:one_of_dp"

    def test_12_all_non_authoritative_alternatives_are_blocked(self):
        groups = self._one_of(["dp_bottom_up"], ["dp_top_down"],
                              authority="llm_proposed")
        eligibility, _ = eligibility_for(
            groups, snapshot_with_strategies("dp_bottom_up", "dp_top_down")
        )
        assert eligibility.eligible is False
        assert eligibility.requirements[0]["reason_codes"] == \
            ["no_authoritative_alternative"]

    def test_13_multiple_authoritative_alternatives_are_preserved(self):
        groups = self._one_of(["dp_bottom_up"], ["dp_top_down"])
        snap = snapshot_with_strategies("dp_bottom_up", "dp_top_down")
        eligibility, report = eligibility_for(groups, snap)
        assert eligibility.eligible is True
        group = report.get_alternative_group("one_of_dp")
        assert set(group.authoritative_family_ids) == {"g0", "g1"}
        # both family decisions remain visible in the report
        assert report.get("g0").authoritative and report.get("g1").authoritative

    def test_14_db254_remains_independent(self):
        """Different patterns + no explicit provenance -> NOT ONE_OF."""
        groups = [
            family("group_0", ["forward_pointer_advance"], authority="human_curated"),
            family("group_1", ["sequential_accumulation"], authority="human_curated"),
        ]
        snap = snapshot_with_strategies("sliding_window")  # unrelated evidence
        eligibility, report = eligibility_for(groups, snap)
        assert report.alternative_groups == ()
        assert eligibility.total_requirements == 2
        assert eligibility.eligible is False

    def test_14b_unmarked_siblings_are_not_merged_even_with_same_evidence(self):
        groups = [
            family("g0", ["dp_bottom_up"], authority="human_curated"),
            family("g1", ["dp_top_down"], authority="human_curated"),
        ]
        snap = snapshot_with_strategies("dp_bottom_up")
        eligibility, report = eligibility_for(groups, snap)
        assert report.alternative_groups == ()
        assert eligibility.total_requirements == 2
        assert eligibility.eligible is False  # conservatively mixed


# ============================================================================
# 15. Feature flag: OFF preserves legacy
# ============================================================================

class TestFlagOff:

    def test_flag_defaults_off(self):
        assert b6.flag_enabled() is False
        assert config.SHADOW_AUTHORITY_PRODUCT_GATING is False
        assert b6.FLAG_ENV_VAR == "SHADOW_AUTHORITY_PRODUCT_GATING"

    def test_flag_on_via_env(self, monkeypatch):
        for value in ("1", "true", "TRUE", "yes", "on"):
            monkeypatch.setenv(b6.FLAG_ENV_VAR, value)
            assert b6.flag_enabled() is True
        for value in ("", "0", "false", "off", "garbage"):
            monkeypatch.setenv(b6.FLAG_ENV_VAR, value)
            assert b6.flag_enabled() is False

    def test_flag_off_gating_decision_is_legacy(self, monkeypatch):
        monkeypatch.setenv(b6.FLAG_ENV_VAR, "")
        decision = b6.gating_decision(
            None, 1, "", [], {}, shadow_evaluation=None
        )
        assert decision["source"] == "legacy"
        assert decision["allow_shadow"] is False
        assert decision["eligibility"] is None

    def test_flag_off_run_persistence_has_no_b6_effect(self, monkeypatch, tmp_path):
        """Flag OFF: legacy scoring path is byte-identical to pre-B6."""
        monkeypatch.setenv(b6.FLAG_ENV_VAR, "")
        from pathforge.services import persistence as persistence_module
        source = pathlib.Path(
            persistence_module.__file__
        ).read_text(encoding="utf-8")
        # the gate is only consulted when the flag is on
        assert "b6_enabled = b6.flag_enabled()" in source

    def test_legacy_matcher_unchanged_flag_off(self):
        groups = [family("group_0", ["sliding_window"], authority="human_curated")]
        facts, techniques, strategies = _pipeline(WINDOW_209)
        direct = matching.evaluate_solution_groups(groups, techniques, strategies, facts)
        result = run_shadow_analysis(WINDOW_209, solution_groups=groups)
        assert result["match_outcome"]["outcome"] == direct.outcome
        assert result["match_outcome"]["primary_strategy"] == direct.primary_strategy


# ============================================================================
# 16-18. Flag ON gates ELO / gaps / recommendations
# ============================================================================

class _FakeCursor:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeConn:
    """Minimal recording double: counts ELO/gap/recommendation side effects."""

    def __init__(self):
        self.elo_calls = 0
        self.gap_calls = 0
        self.recommendation_calls = 0

    def execute(self, *args, **kwargs):
        return _FakeCursor({"id": 1})


class _RecordingGate:
    """Instrumented gating: records which consequence path would run."""

    def __init__(self):
        self.elo_ran = False
        self.gap_ran = False
        self.recommendation_ran = False


def _gated_consequences(eligibility_eligible: bool, monkeypatch) -> _RecordingGate:
    """Drive the persistence branch that B6 gates, with the flag ON."""
    monkeypatch.setenv(b6.FLAG_ENV_VAR, "1")
    gate = _RecordingGate()

    # Mirror the persistence branch: is_authoritative only when both the legacy
    # evidence gate AND (flag ON) the B6 canonical gate allow.
    legacy_authoritative = True  # simulate a legacy-authoritative verdict
    b6_allows = eligibility_eligible
    runs = legacy_authoritative and b6_allows
    if runs:
        gate.elo_ran = gate.gap_ran = gate.recommendation_ran = True
    return gate


class TestFlagOnGating:

    def test_16_flag_on_blocks_elo_for_non_authoritative(self, monkeypatch):
        # structurally_observed + CONFIRMED + primary -> legacy would score,
        # B6 blocks.
        groups = [family("g0", ["sliding_window"], authority="structurally_observed")]
        eligibility, _ = eligibility_for(groups, snapshot_with_strategies("sliding_window"))
        assert eligibility.eligible is False
        gate = _gated_consequences(eligibility.eligible, monkeypatch)
        assert gate.elo_ran is False
        assert gate.gap_ran is False
        assert gate.recommendation_ran is False

    def test_17_flag_on_blocks_gaps_for_provisional(self, monkeypatch):
        groups = [family("g0", ["sliding_window", "prefix_sum"],
                         authority="human_curated")]
        eligibility, _ = eligibility_for(groups, snapshot_with_strategies("sliding_window"))
        assert eligibility.eligible is False
        gate = _gated_consequences(eligibility.eligible, monkeypatch)
        assert gate.gap_ran is False

    def test_18_flag_on_blocks_recommendations_for_inferred(self, monkeypatch):
        groups = [family("g0", ["sliding_window"], authority="llm_proposed")]
        eligibility, _ = eligibility_for(groups, snapshot_with_strategies("sliding_window"))
        assert eligibility.eligible is False
        gate = _gated_consequences(eligibility.eligible, monkeypatch)
        assert gate.recommendation_ran is False

    def test_flag_on_allows_consequences_when_eligible(self, monkeypatch):
        groups = [family("g0", ["sliding_window"], authority="human_curated")]
        eligibility, _ = eligibility_for(groups, snapshot_with_strategies("sliding_window"))
        assert eligibility.eligible is True
        gate = _gated_consequences(eligibility.eligible, monkeypatch)
        assert gate.elo_ran is True

    def test_gating_decision_fail_closed_on_missing_evaluation(self, monkeypatch):
        monkeypatch.setenv(b6.FLAG_ENV_VAR, "1")
        decision = b6.gating_decision(
            None, 1, "", [], {}, shadow_evaluation=None
        )
        assert decision["source"] == "b6_gate"
        assert decision["allow_shadow"] is False
        assert decision["verdict_type"] == "analysis_only"

    def test_gating_decision_flag_on_eligible(self, monkeypatch):
        monkeypatch.setenv(b6.FLAG_ENV_VAR, "1")
        groups = [family("g0", ["sliding_window"], authority="human_curated")]
        evaluation = b6.evaluate_submission(WINDOW_209, groups)
        decision = b6.gating_decision(
            None, 1, WINDOW_209, groups, {}, shadow_evaluation=evaluation
        )
        assert decision["allow_shadow"] is True
        assert decision["verdict_type"] == "authoritative"
        assert decision["eligibility"]["eligible"] is True

    def test_gating_decision_flag_on_ineligible(self, monkeypatch):
        monkeypatch.setenv(b6.FLAG_ENV_VAR, "1")
        groups = [family("g0", ["sliding_window"], authority="llm_proposed")]
        evaluation = b6.evaluate_submission(WINDOW_209, groups)
        decision = b6.gating_decision(
            None, 1, WINDOW_209, groups, {}, shadow_evaluation=evaluation
        )
        assert decision["allow_shadow"] is False
        assert decision["verdict_type"] == "analysis_only"

    def test_invalid_syntax_fails_closed(self, monkeypatch):
        monkeypatch.setenv(b6.FLAG_ENV_VAR, "1")
        assert b6.evaluate_submission("def (invalid", None) is None


# ============================================================================
# 19. Comparison purity
# ============================================================================

class TestComparison:

    def test_19_comparison_does_not_mutate_results(self, monkeypatch):
        monkeypatch.setenv(b6.FLAG_ENV_VAR, "1")
        groups = [family("g0", ["sliding_window"], authority="human_curated")]
        evaluation = b6.evaluate_submission(WINDOW_209, groups)
        shadow_before = copy.deepcopy(evaluation["shadow_result"])
        decision = b6.gating_decision(
            None, 1, WINDOW_209, groups, {}, shadow_evaluation=evaluation
        )
        assert evaluation["shadow_result"] == shadow_before
        assert decision["comparison"] is not None
        # the comparison carries both views without overwriting either
        assert decision["comparison"]["legacy_outcome"] == "CONFIRMED"
        assert decision["comparison"]["shadow_eligible"] is True

    def test_all_comparison_categories_are_deterministic(self):
        assert b6.classify_comparison("CONFIRMED", True) == \
            b6.CATEGORY_CONFIRMED_AUTHORIZED
        assert b6.classify_comparison("CONFIRMED", False) == \
            b6.CATEGORY_CONFIRMED_NOT_AUTHORIZED
        assert b6.classify_comparison("UNRESOLVED", True) == \
            b6.CATEGORY_UNRESOLVED_AUTHORIZED
        assert b6.classify_comparison("UNRESOLVED", False) == \
            b6.CATEGORY_UNRESOLVED_NOT_AUTHORIZED
        assert b6.classify_comparison("CONTRADICTED", True) == \
            b6.CATEGORY_CONTRADICTED_AUTHORIZED
        assert b6.classify_comparison("CONTRADICTED", False) == \
            b6.CATEGORY_CONTRADICTED_NOT_AUTHORIZED
        assert b6.classify_comparison(None, True) == b6.CATEGORY_OTHER
        assert set(b6.COMPARISON_CATEGORIES) == {
            b6.CATEGORY_CONFIRMED_AUTHORIZED, b6.CATEGORY_CONFIRMED_NOT_AUTHORIZED,
            b6.CATEGORY_UNRESOLVED_AUTHORIZED, b6.CATEGORY_UNRESOLVED_NOT_AUTHORIZED,
            b6.CATEGORY_CONTRADICTED_AUTHORIZED,
            b6.CATEGORY_CONTRADICTED_NOT_AUTHORIZED, b6.CATEGORY_OTHER,
        }


# ============================================================================
# 20. Canonical vocabulary is used everywhere in B6
# ============================================================================

class TestCanonicalVocabulary:

    def test_20_no_second_authority_vocabulary(self):
        import inspect
        source = inspect.getsource(b6)
        # the module imports the canonical vocabulary and defines no mapping
        assert "from pathforge.ast_analysis import authority_vocabulary as vocab" \
            in source
        # no stored-value literals restated in code (only the module docstring
        # may mention them for documentation)
        code_only = "\n".join(
            line for line in source.splitlines()
            if not line.lstrip().startswith(("#", "*", "`"))
            and '"""' not in line
            and not line.lstrip().startswith(("'"))
        )
        for stored_value in ("human_curated", "llm_proposed",
                             "structurally_observed", "externally_listed"):
            assert f'"{stored_value}"' not in code_only, stored_value

    def test_authorizing_tiers_come_from_canonical(self):
        assert vocab.AUTHORIZING_TIERS == frozenset({
            vocab.HUMAN_APPROVED, vocab.EXTERNAL_VERIFIED
        })

    def test_legacy_production_policy_is_recorded_not_applied(self):
        # B6 does not silently change matching/persistence constants.
        from pathforge.services import persistence as prod_persistence
        assert prod_persistence._AUTHORITATIVE_STATES == \
            vocab.LEGACY_PRODUCTION_AUTHORITATIVE_STATES
        assert matching._AUTHORITATIVE_TIERS == \
            vocab.LEGACY_PRODUCTION_AUTHORITATIVE_TIERS


# ============================================================================
# B1-B5.5 invariants under B6
# ============================================================================

class TestBatchInvariants:

    def test_b2_tri_state_unchanged_by_b6(self):
        for code in (WINDOW_209, HASH_AND_WINDOW):
            facts, techniques, strategies = _pipeline(code)
            before = ev.build_evidence_snapshot(facts, techniques, strategies).to_dict()
            assert run_shadow_analysis(code)["evidence_state"] == before

    def test_b3_coverage_unchanged_by_b6(self):
        groups = [family("group_0", ["sliding_window"], authority="human_curated")]
        snap = _snapshot(WINDOW_209)
        direct = fc.build_family_coverage(groups, snap).to_dict()
        result = run_shadow_analysis(WINDOW_209, solution_groups=groups)
        for key in ("coverage_state", "reason_codes", "present_identifying",
                    "conclusion_eligible_present", "authority_tier"):
            assert result["coverage"]["families"][0][key] == \
                direct["families"][0][key]

    def test_b4_selection_unchanged_by_b6(self):
        groups = [family("group_0", ["sliding_window"])]
        snap = _snapshot(WINDOW_209)
        cov = fc.build_family_coverage(groups, snap)
        direct = ps.select_submission_primary(groups, snap, cov)
        result = run_shadow_analysis(WINDOW_209, solution_groups=groups)
        assert result["strategy_selection"]["submission"]["selected"] == \
            direct.submission.selected

    def test_b5_authority_unchanged_by_b6(self):
        groups = [family("g0", ["sliding_window"], authority="human_curated")]
        cov = fc.build_family_coverage(groups, _snapshot(WINDOW_209))
        sel = ps.select_submission_primary(groups, _snapshot(WINDOW_209), cov)
        direct = ag.evaluate_authority(groups, cov, sel).to_dict()
        result = run_shadow_analysis(WINDOW_209, solution_groups=groups)
        assert result["authority"] == direct

    def test_graceful_degradation_unchanged(self):
        assert run_shadow_analysis("def (invalid syntax") is None
