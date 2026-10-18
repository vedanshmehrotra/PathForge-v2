"""Actual detector/matcher/persistence path; all connections and writes isolated."""
import copy
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from pathforge.tests.test_b6_product_eligibility import (
    WINDOW_209, _assert_product_consequences, _persistence_group, persistence_case,
)


def execute(case, groups):
    from pathforge.api.services.analysis import run_analysis
    from pathforge.services.persistence import run_persistence

    analysis = run_analysis(WINDOW_209, accepted_solution_groups=groups)
    assert "error" not in analysis
    before = copy.deepcopy((analysis, groups))
    result = run_persistence(
        connection=case.connection, user_id=7, problem_id=209 if groups else None,
        problem_difficulty="Medium" if groups else None, code=WINDOW_209,
        ast_output=analysis["ast"], match_result=analysis["match_result"], groups=groups)
    assert (analysis, groups) == before
    assert case.connection.queries[0][1][2] == WINDOW_209
    return analysis, result


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("kind,expected_match", [
    ("partial", "PARTIAL_MATCH"), ("absent", "NO_MATCH"),
    ("ambiguous", "FULL_MATCH"), ("unmatchable", "FULL_MATCH"),
    ("unmapped", "FULL_MATCH"), ("disagreement", "FULL_MATCH"),
    ("conflict", "FULL_MATCH"), ("structural", "FULL_MATCH"),
    ("proposal", "FULL_MATCH"), ("no_problem", "NO_GROUND_TRUTH"),
])
def test_inconclusive_comparisons_save_practice_without_any_skill_updates(
    monkeypatch, persistence_case, enabled, kind, expected_match,
):
    from pathforge.services import product_eligibility as b6

    monkeypatch.setenv(b6.FLAG_ENV_VAR, "1" if enabled else "")
    group = _persistence_group("externally_listed")
    group["approach_definition"] = "EXPLICIT"
    if kind == "partial":
        group["patterns"].append("prefix_sum")
    elif kind == "absent":
        group["patterns"] = ["binary_search_standard"]
    elif kind == "ambiguous":
        group.pop("approach_definition")
    elif kind == "unmatchable":
        group["matchable"] = False
    elif kind == "unmapped":
        group["unmapped_patterns"] = ["unrepresented_component"]
    elif kind == "disagreement":
        group["derivation_patterns"] = ["binary_search_standard"]
    elif kind == "conflict":
        group["authority_tier"] = "llm_proposed"
    elif kind == "structural":
        group.update(evidence="structurally_observed", authority_tier="structurally_observed")
    elif kind == "proposal":
        group.update(evidence="llm_proposed", authority_tier="llm_proposed")
    analysis, result = execute(persistence_case, None if kind == "no_problem" else [group])
    assert analysis["match_result"]["match_result"] == expected_match
    _assert_product_consequences(persistence_case, result, False)
    assert result["comparison_gate"]["eligible"] is False
    if not enabled:
        persistence_case.evaluate.assert_not_called()
        persistence_case.gate.assert_not_called()


@pytest.mark.parametrize("enabled", [False, True])
def test_complete_usable_authorizing_comparison_retains_existing_updates(
    monkeypatch, persistence_case, enabled,
):
    from pathforge.services import product_eligibility as b6

    monkeypatch.setenv(b6.FLAG_ENV_VAR, "1" if enabled else "")
    group = _persistence_group("externally_listed")
    group["approach_definition"] = "EXPLICIT"
    analysis, result = execute(persistence_case, [group])
    assert analysis["match_result"]["match_result"] == "FULL_MATCH"
    assert result["comparison_gate"] == {"eligible": True, "reason": "complete_authorizing_comparison"}
    _assert_product_consequences(persistence_case, result, True)


@pytest.mark.parametrize("authority", ["llm_proposed", "human_curated"])
def test_reviewed_or_matching_alternative_cannot_bypass_legacy_gate(persistence_case, authority):
    group = _persistence_group(authority)
    group["approach_definition"] = "EXPLICIT"
    _analysis, result = execute(persistence_case, [group])
    _assert_product_consequences(persistence_case, result, False)


def test_unmatched_authorizing_alternative_cannot_authorize_a_proposal(persistence_case):
    proposed = _persistence_group("llm_proposed")
    proposed["approach_definition"] = "EXPLICIT"
    reviewed = {**_persistence_group("externally_listed"), "patterns": ["binary_search_standard"],
                "approach_definition": "EXPLICIT"}
    analysis, result = execute(persistence_case, [proposed, reviewed])
    assert analysis["match_result"]["matched_groups"] == [0]
    _assert_product_consequences(persistence_case, result, False)


def test_unused_explicit_alternative_does_not_block_an_authorizing_full_match(persistence_case):
    group = _persistence_group("externally_listed")
    group.update(approach_definition="EXPLICIT", family_relation="ONE_OF", alternative_group_id="options")
    other = {**group, "id": "other", "patterns": ["binary_search_standard"]}
    analysis, result = execute(persistence_case, [other, group])
    assert analysis["match_result"]["matched_groups"] == [1]
    assert analysis["match_result"]["unmatched_patterns"] == []
    _assert_product_consequences(persistence_case, result, True)


def test_stale_match_result_cannot_enable_skills(persistence_case):
    from pathforge.services.persistence import run_persistence

    group = {**_persistence_group("externally_listed"), "approach_definition": "EXPLICIT"}
    result = run_persistence(
        connection=persistence_case.connection, user_id=7, problem_id=209,
        problem_difficulty="Medium", code=WINDOW_209, ast_output={"detected_patterns": []},
        match_result={"match_result": "FULL_MATCH", "matched_groups": [0], "unmatched_patterns": []},
        groups=[group])
    assert result["comparison_gate"]["reason"] == "comparison_inconsistent"
    _assert_product_consequences(persistence_case, result, False)


def test_cached_partial_comparison_reports_no_skill_consequences_through_actual_api(persistence_case):
    from pathforge.api.routes import analyze
    from pathforge.ast_analysis.shadow import persistence as shadow_storage
    from pathforge.tests.test_problem_preparation_boundary import MemoryConnection
    from src.ast_detection.semantic.shadow_detector import ShadowDetector

    class Connection(MemoryConnection):
        def execute(self, sql, params):
            if "INSERT INTO submissions" in sql:
                self.writes.append("submission")
                return SimpleNamespace(fetchone=lambda: {"id": 123})
            return super().execute(sql, params)

    group = {**_persistence_group("externally_listed"),
             "patterns": ["sliding_window_variable", "prefix_sum"],
             "required": ["sliding_window", "sequential_accumulation"]}
    connection = Connection(ground_truth={"patterns": group["patterns"], "confidence": {},
                                         "solution_groups": [group]})
    original = copy.deepcopy(connection.ground_truth)
    with patch.object(analyze, "get_current_user", return_value=SimpleNamespace(user_id=7)), \
         patch.object(analyze, "get_connection", return_value=connection), \
         patch.object(shadow_storage, "persist_shadow_analysis"), \
         patch.object(ShadowDetector, "analyze_safe", return_value=None):
        response = analyze.analyze_endpoint(analyze.AnalyzeRequest(
            user_id=999, code=WINDOW_209, problem={"leetcode_id": 209}), None).model_dump()
    assert response["match_result"]["match_result"] == "PARTIAL_MATCH"
    assert response["problem_info"]["solution_groups"][0]["pattern_evidence_state"] == "SOME_OBSERVED"
    assert response["persisted"]["skill_updates_skipped"] is True
    assert response["elo_updates"] == []
    assert response["persisted"]["gap_signals_count"] == 0
    assert connection.ground_truth == original
    assert connection.writes == ["submission"]
    connection.commit.assert_called_once()
    for operation in (persistence_case.profile, persistence_case.gap_engine.compute_signals,
                      persistence_case.gap_engine.persist_signals, persistence_case.elo_engine.compute_updates,
                      persistence_case.elo_engine.persist_elos, persistence_case.recommend):
        operation.assert_not_called()
