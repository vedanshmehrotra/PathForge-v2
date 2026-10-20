"""Practice suggestions use exposure, never match-derived correctness or skill."""

from contextlib import ExitStack, contextmanager
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from pathforge.tests.test_shadow_display_contract import isolated_services


PROBLEMS = [
    {"id": 999, "title": "Two Sum", "difficulty": "Easy", "topics": "Array, Hash Table",
     "link": "https://leetcode.com/problems/two-sum/"},
    {"id": 888, "title": "Binary Search", "difficulty": "Easy", "topics": "Array, Binary Search",
     "link": "https://leetcode.com/problems/binary-search/"},
    {"id": 777, "title": "Number of Islands", "difficulty": "Medium", "topics": "Graph",
     "link": "https://leetcode.com/problems/number-of-islands/"},
    {"id": 666, "title": "Remove Outermost Parentheses", "difficulty": "Easy", "topics": "String, Stack",
     "link": "https://leetcode.com/problems/remove-outermost-parentheses/"},
]


@contextmanager
def practice_service(history=(), problems=PROBLEMS):
    with isolated_services(), ExitStack() as stack:
        from pathforge.api.services import recommend_service as service
        connection = Mock()
        connection.execute.return_value.fetchall.return_value = list(history)
        connection.execute.return_value.fetchone.return_value = {"code_only_submissions": 0}
        stack.enter_context(patch.object(service, "get_connection", return_value=connection))
        stack.enter_context(patch.object(service, "load_user_info", return_value={"id": 7}))
        stack.enter_context(patch.object(service, "load_problem_bank", return_value=problems))
        forbidden = Mock(side_effect=AssertionError("Practice must not use inferred learner state"))
        for name in ("load_user_pattern_elo", "load_gap_signals", "load_submissions", "RecommendationEngine"):
            stack.enter_context(patch.object(service, name, forbidden))
        yield service, connection
        forbidden.assert_not_called()
        connection.commit.assert_not_called()


def test_practice_service_cold_start_is_usable_without_learner_diagnoses():
    with practice_service() as (service, connection):
        result = service.get_recommendations(7, mode="practice")
        assert result["policy"] == "recorded_practice_v1"
        assert result["state"] == "available"
        assert {r["problem_id"] for r in result["recommendations"]} == {"999", "888", "777", "666"}
        assert all(r["score"] is None and r["pattern"] == "" for r in result["recommendations"])
        connection.close.assert_called_once()
        sql, params = connection.execute.call_args.args
        assert params == (7, 1001)
        assert "WHERE user_id = %s" in sql and "ORDER BY id DESC" in sql
        assert "verdict" not in sql and "LIMIT %s" in sql


def test_actual_service_uses_history_as_exposure_and_offers_a_revisit():
    with practice_service([{"problem_id": 888}, {"problem_id": 999}]) as (service, _):
        result = service.get_recommendations(7, mode="practice")
    assert {r["problem_id"] for r in result["recommendations"]} == {"777", "666", "999"}
    revisit = next(r for r in result["recommendations"] if r["practice_kind"] == "revisit")
    assert revisit["problem_id"] == "999"  # Least recently recorded, not the latest paste.
    assert "previously recorded" in revisit["reason"]
    assert result["history"]["mapped_problems"] == 2


def plan(history=(), problems=PROBLEMS, **kwargs):
    from pathforge.practice_recommendations import recommend_practice
    return recommend_practice(problems, list(history), **kwargs)


def test_repeated_match_verdicts_do_not_count_as_new_exposure_or_change_choices():
    single = [{"problem_id": 888}, {"problem_id": 999}]
    duplicated = [{"problem_id": 888, "verdict": "pass", "verdict_type": "authoritative"}] * 20 + single
    assert plan(single) == plan(duplicated)


def test_default_mix_prioritizes_a_less_recorded_catalog_topic():
    # Two Sum's Array and Hash Table exposure is recorded; String is not recorded.
    result = plan([{"problem_id": 999}])
    assert result["recommendations"][0]["problem_id"] == "666"
    assert "999" not in {r["problem_id"] for r in result["recommendations"]}


def test_all_seen_offers_older_revisits_without_declaring_any_solved():
    result = plan([{"problem_id": pid} for pid in (888, 777, 666, 999)])
    assert [r["problem_id"] for r in result["recommendations"]] == ["999", "666", "777"]
    assert all(r["practice_kind"] == "revisit" for r in result["recommendations"])


def test_optional_difficulty_filters_the_entire_bank_before_ranking():
    result = plan(difficulty="Medium")
    assert [r["problem_id"] for r in result["recommendations"]] == ["777"]
    assert plan(difficulty="Hard")["state"] == "no_candidates"


def test_session_skip_exhaustion_and_caught_up_are_distinct():
    assert plan(excluded_ids=["999", "888", "777", "666"])["state"] == "session_exhausted"
    assert plan([{"problem_id": 999}], problems=PROBLEMS[:1])["state"] == "caught_up"
    assert plan(problems=[])["state"] == "no_candidates"


def test_unknown_history_is_not_assigned_a_topic_or_confused_with_frontend_ids():
    result = plan([{"problem_id": 1}, {"problem_id": None}])
    assert result["history"]["mapped_problems"] == 0
    assert result["history"]["unmapped_submissions"] == 2
    assert {r["problem_id"] for r in result["recommendations"]} == {"999", "888", "777", "666"}


@pytest.mark.parametrize("bad", [None, "https://evil.invalid/problems/two-sum/", "javascript:alert(1)"])
def test_missing_or_unsafe_links_cannot_be_candidates(bad):
    assert plan(problems=[{**PROBLEMS[0], "link": bad}])["state"] == "no_candidates"


@pytest.mark.parametrize("field,value", [("id", None), ("id", True), ("title", None),
                                         ("title", " "), ("difficulty", "Unknown")])
def test_unusable_catalog_metadata_is_skipped(field, value):
    assert plan(problems=[{**PROBLEMS[0], field: value}])["state"] == "no_candidates"


def test_missing_topics_do_not_block_safe_suggestions_or_invent_a_topic():
    result = plan(problems=[{**PROBLEMS[0], "topics": None}])
    assert result["recommendations"][0]["topics"] == []
    assert result["recommendations"][0]["pattern"] == ""


def test_url_aliases_share_exposure_and_skip_identity():
    alias = {**PROBLEMS[0], "id": 123}
    result = plan([{"problem_id": 123}], problems=[*PROBLEMS, alias])
    assert "999" not in {r["problem_id"] for r in result["recommendations"]}
    result = plan(problems=[*PROBLEMS, alias], excluded_ids=["123"])
    assert len(result["recommendations"]) == 3


def test_conflicting_internal_identity_is_not_recommended_or_borrowed():
    conflict = {**PROBLEMS[1], "id": 999}
    result = plan([{"problem_id": 999}], problems=[PROBLEMS[0], conflict])
    assert result["state"] == "no_candidates"
    assert result["history"]["unmapped_submissions"] == 1


def test_bounded_history_reports_truncation_and_never_claims_all_time_novelty():
    result = plan([{"problem_id": 999}] * 1001)
    assert result["history"]["truncated"] is True
    assert result["history"]["mapped_problems"] == 1
    assert all("recent recorded practice" in r["reason"] for r in result["recommendations"])


def test_practice_route_uses_verified_user_not_request_identity():
    with isolated_services():
        from pathforge.api.routes import recommend as route
        with patch.object(route, "get_current_user", return_value=SimpleNamespace(user_id=7)), \
             patch.object(route, "get_recommendations", return_value={"recommendations": []}) as service:
            route.recommend_endpoint(route.RecommendRequest(user_id=999, mode="practice", difficulty="Medium",
                                                            excluded_ids=["888"]), Mock())
        service.assert_called_once_with(7, mode="practice", difficulty="Medium", excluded_ids=["888"])


def test_legacy_route_preserves_call_contract():
    with isolated_services():
        from pathforge.api.routes import recommend as route
        with patch.object(route, "get_current_user", return_value=SimpleNamespace(user_id=7)), \
             patch.object(route, "get_recommendations", return_value={"recommendations": []}) as service:
            route.recommend_endpoint(route.RecommendRequest(user_id=999), Mock())
        service.assert_called_once_with(7)


@pytest.mark.parametrize("fields", [{"mode": "adaptive"}, {"difficulty": "Extreme"},
                                   {"excluded_ids": ["1"] * 51}])
def test_invalid_practice_requests_fail_before_database_access(fields):
    from pydantic import ValidationError
    with isolated_services():
        from pathforge.api.routes.recommend import RecommendRequest
        with pytest.raises(ValidationError):
            RecommendRequest(user_id=7, **fields)


def test_history_failure_does_not_fall_back_to_diagnostic_ranker():
    with practice_service() as (service, connection):
        connection.execute.side_effect = RuntimeError("Isolated history unavailable")
        result = service.get_recommendations(7, mode="practice")
        assert result["stage"] == "RECOMMENDATION" and "error" in result
        connection.close.assert_called_once()


def test_small_limits_are_respected_without_mutating_inputs():
    from copy import deepcopy
    source = deepcopy(PROBLEMS)
    for limit in range(1, 6):
        result = plan([{"problem_id": 888}, {"problem_id": 999}], limit=limit)
        assert len(result["recommendations"]) <= limit
        assert len({r["problem_url"] for r in result["recommendations"]}) == len(result["recommendations"])
    assert source == PROBLEMS
