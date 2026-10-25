"""Source-justified recommendation choices; recorded attempts are not solved labels."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from pathforge.tests.test_practice_recommendations import practice_service
from pathforge.tests.test_shadow_display_contract import isolated_services

NOW = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
POLICY = "calendar_practice_v2"
BANK = [
    {"id": 1, "title": "Two Sum", "difficulty": "Easy", "topics": "Array, Hash Table",
     "link": "https://leetcode.com/problems/two-sum/"},
    {"id": 198, "title": "House Robber", "difficulty": "Medium", "topics": "Array, Dynamic Programming",
     "link": "https://leetcode.com/problems/house-robber/"},
    {"id": 704, "title": "Binary Search", "difficulty": "Easy", "topics": "Array, Binary Search",
     "link": "https://leetcode.com/problems/binary-search/"},
    {"id": 35, "title": "Search Insert Position", "difficulty": "Easy", "topics": "Array, Binary Search",
     "link": "https://leetcode.com/problems/search-insert-position/"},
    {"id": 3, "title": "Longest Substring Without Repeating Characters", "difficulty": "Medium",
     "topics": "String, Sliding Window", "link": "https://leetcode.com/problems/longest-substring-without-repeating-characters/"},
    {"id": 567, "title": "Permutation in String", "difficulty": "Medium", "topics": "String, Sliding Window",
     "link": "https://leetcode.com/problems/permutation-in-string/"},
    {"id": 20, "title": "Valid Parentheses", "difficulty": "Easy", "topics": "String, Stack",
     "link": "https://leetcode.com/problems/valid-parentheses/"},
    {"id": 200, "title": "Number of Islands", "difficulty": "Medium", "topics": "Array, Matrix, Depth-First Search",
     "link": "https://leetcode.com/problems/number-of-islands/"},
]


def event(pid, days=0, **extra):
    return {"problem_id": pid, "submitted_at": (NOW-timedelta(days=days)).isoformat(), **extra}


def plan(history=(), bank=BANK, **kwargs):
    from pathforge.calendar_practice import recommend_calendar_practice
    return recommend_calendar_practice(bank, list(history), now=NOW, **kwargs)


def test_specific_return_follow_up_and_variety_have_factual_anchors():
    out = plan([event(3), event(704, 10)])
    returned, follow, other = out["recommendations"]
    assert (returned["problem_id"], returned["practice_kind"]) == ("35", "related_return")
    assert returned["reason_evidence"] == {"anchor_url": BANK[2]["link"], "anchor_title": "Binary Search",
        "anchor_date": "2026-10-10", "shared_topics": ["Binary Search"]}
    assert (follow["problem_id"], follow["practice_kind"]) == ("567", "follow_up")
    assert follow["reason_evidence"]["anchor_date"] == "2026-10-20"
    assert other["practice_kind"] == "explore"


def test_broad_array_overlap_cannot_be_a_targeted_follow_up():
    out = plan([event(1)], bank=BANK[:2], difficulty="Medium")
    assert out["recommendations"][0]["problem_id"] == "198"
    assert out["recommendations"][0]["practice_kind"] == "explore"
    assert "reason_evidence" not in out["recommendations"][0]


def test_companion_uses_current_problem_instead_of_latest_history_and_avoids_hard_jumps():
    bank = [*BANK,
        {"id": 217, "title": "Contains Duplicate", "difficulty": "Easy", "topics": "Array, Hash Table",
         "link": "https://leetcode.com/problems/contains-duplicate/"},
        {"id": 30, "title": "Hard hash practice", "difficulty": "Hard", "topics": "Hash Table",
         "link": "https://leetcode.com/problems/substring-with-concatenation-of-all-words/"}]
    out = plan([event(3)], bank=bank, focus_slug="two-sum", allow_explore=False)
    assert [r["problem_id"] for r in out["recommendations"]] == ["217"]
    rec = out["recommendations"][0]
    assert rec["practice_kind"] == "follow_up" and rec["pattern"] == ""
    assert rec["reason_evidence"] == {"anchor_url": BANK[0]["link"], "anchor_title": "Two Sum",
                                       "shared_topics": ["Hash Table"]}
    assert out["context"]["related_available"] is True


def test_companion_no_related_candidate_is_honest_and_exploration_is_optional():
    failed = plan(focus_slug="two-sum", allow_explore=False)
    assert failed["recommendations"] == []
    assert failed["context"]["related_available"] is False
    accepted = plan(focus_slug="two-sum")
    assert all(r["practice_kind"] == "explore" for r in accepted["recommendations"])
    assert all(r["difficulty"] == "Easy" for r in accepted["recommendations"])
    assert all(r["problem_id"] != "1" for r in accepted["recommendations"])
    assert plan(focus_slug="missing-problem")["state"] == "context_unavailable"


def test_companion_route_preserves_authenticated_ownership_and_validates_context():
    from pydantic import ValidationError
    from fastapi import HTTPException
    with isolated_services():
        from pathforge.api.routes import recommend as route
        with patch.object(route, "get_current_user", return_value=SimpleNamespace(user_id=7)), \
             patch.object(route, "get_recommendations", return_value={"recommendations": []}) as service:
            route.recommend_endpoint(route.RecommendRequest(user_id=999, mode="companion",
                context_problem_slug="two-sum", submission_status="failed"), Mock())
            service.assert_called_once_with(7, mode="companion", policy=POLICY,
                context_problem_slug="two-sum", submission_status="failed")
            with pytest.raises(HTTPException) as error:
                route.recommend_endpoint(route.RecommendRequest(user_id=999, mode="companion"), Mock())
            assert error.value.status_code == 422
        with pytest.raises(ValidationError):
            route.RecommendRequest(user_id=7, mode="companion", context_problem_slug="../admin")


def test_companion_service_reuses_calendar_policy_without_loading_elo_or_writing():
    with practice_service([event(3)], BANK) as (service, connection):
        result = service.get_recommendations(7, mode="companion", context_problem_slug="two-sum",
                                             submission_status="failed")
    assert result["recommendations"] == []
    assert result["context"]["source_problem_url"] == BANK[0]["link"]
    assert connection.execute.call_args_list[0].args[1] == (7, 1001)
    assert all("SELECT" in call.args[0] for call in connection.execute.call_args_list)


def test_weak_relation_returns_an_actual_old_problem_instead():
    out = plan([event(20), event(1, 10)], bank=[BANK[0], BANK[1], BANK[6]])
    returned = out["recommendations"][0]
    assert (returned["problem_id"], returned["practice_kind"]) == ("1", "revisit")
    assert returned["reason_evidence"]["anchor_date"] == "2026-10-10"
    assert "forgot" not in returned["reason"] and "weak" not in returned["reason"]


def test_recent_specific_topic_exposure_prevents_false_stale_topic_return():
    out = plan([event(3), event(35, 1), event(704, 10)])
    assert all(r["practice_kind"] != "related_return" for r in out["recommendations"])


def test_no_preferences_or_history_required_and_unique_safe_destinations():
    out = plan()
    assert len(out["recommendations"]) == 3
    assert all(r["practice_kind"] == "starter" for r in out["recommendations"])
    assert len({r["problem_url"] for r in out["recommendations"]}) == 3
    assert out["summary"]["primary_weak_patterns"] == []
    assert all(r["score"] is None and not r["pattern"] for r in out["recommendations"])


@pytest.mark.parametrize("field,value", [("verdict", "fail"), ("verdict", "pass"),
    ("detected_pattern", "brute_force"), ("shadow", {"outcome": "CONFIRMED"}),
    ("ground_truth", {"authority": "HUMAN_APPROVED"}), ("elo", 9999), ("skill_gap", 1.0)])
def test_diagnostics_never_change_the_slate(field, value):
    history = [event(3), event(704, 10)]
    assert plan([{**e, field: value} for e in history],
                bank=[{**p, field: value} for p in BANK]) == plan(history)


def test_repeated_analyses_and_aliases_are_not_new_learning_evidence():
    history = [event(3), event(704, 10)]
    assert plan(history * 5) == plan(history)
    out = plan([event(999)], bank=[*BANK, {**BANK[0], "id": 999}])
    assert BANK[0]["link"] not in {r["problem_url"] for r in out["recommendations"]}
    assert out["history"]["mapped_problems"] == 1


@pytest.mark.parametrize("stamp", [None, "bad", "2026-10-19", "2026-10-21T12:00:00Z",
                                  "0001-01-01T00:00:00+14:00"])
def test_unknown_latest_date_is_withheld_without_borrowing_an_older_anchor(stamp):
    out = plan([{**event(3), "submitted_at": stamp}, event(704, 10)])
    assert "3" not in {r["problem_id"] for r in out["recommendations"]}
    assert out["history"]["invalid_timestamps"] == 1
    assert all(r["practice_kind"] != "follow_up" for r in out["recommendations"])


def test_empty_saturated_skipped_and_filter_states_are_distinct():
    assert plan(bank=[])["state"] == "no_candidates"
    assert plan(excluded_ids=[p["id"] for p in BANK])["state"] == "session_exhausted"
    assert plan([event(1)], bank=BANK[:1])["state"] == "caught_up"
    assert plan(difficulty="Hard")["state"] == "no_candidates"
    out = plan([event(p["id"], i * 10) for i, p in enumerate(BANK)])
    assert len(out["recommendations"]) == 1  # At most one old problem per slate.
    assert all(r["practice_kind"] == "revisit" for r in out["recommendations"])
    assert "1" not in {r["problem_id"] for r in out["recommendations"]}


def test_recent_saturated_bank_does_not_invent_a_due_date():
    assert plan([event(p["id"]) for p in BANK])["state"] == "caught_up"


def test_invalid_catalog_conflicts_and_unknown_history_are_disclosed():
    bad = [{**BANK[0], "link": "https://evil.invalid/problems/two-sum/"}]
    assert plan(bank=bad)["recommendations"] == []
    conflict = [{**BANK[0], "link": BANK[1]["link"]}, BANK[0]]
    assert plan(bank=conflict)["recommendations"] == []
    assert plan([event(9999)])["history"]["unmapped_submissions"] == 1
    assert plan([event(3)] * 1001)["history"]["truncated"] is True


def test_anchor_dates_and_order_are_deterministic_within_valid_window():
    history = [event(3), event(704, 10), event(20, 20)]
    assert plan(history) == plan(list(reversed(history)))
    assert plan(history, excluded_ids=[35])["recommendations"][0]["practice_kind"] == "revisit"


def test_filters_cannot_be_relaxed_and_inputs_are_not_mutated():
    source = deepcopy([BANK, [event(3), event(704, 10)]])
    result = plan(source[1], bank=source[0], difficulty="Medium", excluded_ids=[567])
    assert all(r["difficulty"] == "Medium" and r["problem_id"] != "567" for r in result["recommendations"])
    assert source == [BANK, [event(3), event(704, 10)]]


def test_calendar_service_reads_dates_only_for_verified_owner_and_never_writes():
    with practice_service([event(3), event(704, 10)], BANK) as (service, connection):
        with patch.object(service, "datetime") as clock:
            clock.now.return_value = NOW
            out = service.get_recommendations(7, mode="practice", policy=POLICY)
        assert out["recommendations"][0]["problem_id"] == "35"
        assert out["recommendations"][1]["problem_id"] == "567"
        sql, params = connection.execute.call_args_list[0].args
        assert "submitted_at" in sql and "WHERE user_id = %s" in sql
        assert params == (7, 1001)
        connection.close.assert_called_once()


def test_calendar_route_preserves_identity_and_serializes_actual_service_result():
    import json
    with practice_service([event(3), event(704, 10)], BANK) as (service, connection):
        from pathforge.api.routes import recommend as route
        with patch.object(route, "get_current_user", return_value=SimpleNamespace(user_id=7)):
            out = route.recommend_endpoint(route.RecommendRequest(user_id=999, mode="practice", policy=POLICY), Mock())
    wire = json.loads(json.dumps(out))
    assert wire["policy"] == POLICY and wire["user_id"] == 7
    sql, params = connection.execute.call_args_list[0].args
    assert "submitted_at" in sql and params == (7, 1001)
    assert "verdict" not in sql and "elo" not in sql
    assert wire["summary"]["primary_weak_patterns"] == []


def test_calendar_history_failure_is_an_error_not_a_cold_start():
    with practice_service(problems=BANK) as (service, connection):
        connection.execute.side_effect = RuntimeError("History unavailable")
        assert "error" in service.get_recommendations(7, mode="practice", policy=POLICY)


def test_unknown_policy_is_rejected_before_service_calls():
    from pydantic import ValidationError
    with isolated_services():
        from pathforge.api.routes.recommend import RecommendRequest
        with pytest.raises(ValidationError):
            RecommendRequest(user_id=7, mode="practice", policy="mastery_magic")


def test_seven_days_is_elapsed_time_not_a_midnight_boundary():
    early = NOW-timedelta(days=7)+timedelta(seconds=1)
    out = plan([event(3), {**event(704), "submitted_at": early.isoformat()}])
    assert all(r["practice_kind"] not in ("revisit", "related_return") for r in out["recommendations"])
    assert plan([event(3), event(704, 7)])["recommendations"][0]["practice_kind"] == "related_return"


def test_date_deduplication_uses_utc_and_revisit_cites_last_attempt():
    history = [event(20), event(1, 30), event(1, 10),
               {"problem_id": 1, "submitted_at": "2026-10-10T17:30:00+05:30"}]
    out = plan(history, bank=[BANK[0], BANK[1], BANK[6]])
    assert out["history"]["dated_exposures"] == 3  # one latest + two distinct past UTC days
    assert out["recommendations"][0]["reason_evidence"]["anchor_date"] == "2026-10-10"


def test_unknown_time_for_a_url_prevents_borrowing_its_older_valid_date():
    out = plan([{**event(1), "submitted_at": None}, event(1, 30)], bank=BANK[:2], difficulty="Medium")
    assert out["recommendations"][0]["practice_kind"] == "explore"


def test_fractional_exposure_does_not_credit_a_many_tag_attempt_as_four_attempts():
    def task(pid, topic, slug):
        return {"id": pid, "title": slug, "topics": topic, "difficulty": "Easy",
                "link": f"https://leetcode.com/problems/{slug}/"}
    bank = [task(1, "Matrix", "latest-fixture"), task(2, "A,B,C,D", "multi-fixture"),
            task(3, "E", "single-fixture"), task(4, "D", "z-fraction-fixture"),
            task(5, "E", "a-full-fixture")]
    out = plan([event(1), event(2, 1), event(3, 2)], bank=bank)
    assert out["recommendations"][0]["problem_id"] == "4"
    assert out["recommendations"][0]["practice_kind"] == "explore"


def test_same_url_conflicting_metadata_is_not_resolved_by_row_order():
    conflict = {**BANK[0], "id": 101, "topics": "Dynamic Programming"}
    assert plan(bank=[BANK[0], conflict])["recommendations"] == []
    assert plan(bank=[conflict, BANK[0]])["recommendations"] == []


@pytest.mark.parametrize("history,now", [(None, NOW), ({}, NOW), ([], datetime(2026, 10, 20))])
def test_missing_history_or_unusable_clock_cannot_invent_a_schedule(history, now):
    from pathforge.calendar_practice import recommend_calendar_practice
    with pytest.raises(ValueError):
        recommend_calendar_practice(BANK, history, now=now)


def test_missing_topics_still_allows_general_choices_without_targeted_claims():
    out = plan([event(1)], bank=[{**p, "topics": None} for p in BANK])
    assert all(r["practice_kind"] == "explore" and r["topics"] == [] for r in out["recommendations"])


@pytest.mark.parametrize("target_in_catalog", [True, False])
def test_actual_catalog_loader_needs_no_ground_truth_and_never_invents_absent_problems(target_in_catalog):
    """Exercise real loader SQL, service, route and JSON without a ground-truth table."""
    import json
    bank = [p for p in BANK if target_in_catalog or p["id"] != 35]
    queries = []

    class CatalogConnection:
        def __init__(self):
            self.commit = Mock(side_effect=AssertionError("Recommendation writes are forbidden"))
            self.close = Mock()

        def execute(self, sql, params=()):
            normalized = " ".join(sql.lower().split())
            queries.append((normalized, params))
            assert normalized.startswith("select ")
            assert "ground_truth" not in normalized
            if "from users" in normalized:
                assert params == (7,)
                return SimpleNamespace(fetchone=lambda: {"id": 7})
            if "from problems" in normalized:
                return SimpleNamespace(fetchall=lambda: deepcopy(bank))
            if "from submissions" in normalized:
                if "count(*)" in normalized:
                    assert params == (7,)
                    return SimpleNamespace(fetchone=lambda: {"code_only_submissions": 0})
                assert params == (7, 1001) and "submitted_at" in normalized
                return SimpleNamespace(fetchall=lambda: [event(704)])
            raise AssertionError(f"Unexpected query: {normalized}")

    with isolated_services():
        from pathforge.api.routes import recommend as route
        from pathforge.api.services import recommend_service as service
        connection = CatalogConnection()
        forbidden = Mock(side_effect=AssertionError("No diagnostic ranker or loaders allowed"))
        with patch.object(service, "get_connection", return_value=connection), \
             patch.object(route, "get_current_user", return_value=SimpleNamespace(user_id=7)), \
             patch.object(service, "datetime") as clock, \
             patch.object(service, "RecommendationEngine", forbidden), \
             patch.object(service, "load_submissions", forbidden), \
             patch.object(service, "load_gap_signals", forbidden), \
             patch.object(service, "load_user_pattern_elo", forbidden):
            clock.now.return_value = NOW
            response = route.recommend_endpoint(route.RecommendRequest(
                user_id=999, mode="practice", policy=POLICY), Mock())
        wire = json.loads(json.dumps(response))
        assert wire["policy"] == POLICY and wire["user_id"] == 7
        targets = [p for p in wire["recommendations"] if p["problem_id"] == "35"]
        if target_in_catalog:
            assert len(targets) == 1 and targets[0]["practice_kind"] == "follow_up"
        else:
            assert targets == []
        assert len(queries) == 4  # user + catalog + distinct history + code-only count; no GT lookup
        connection.commit.assert_not_called()
        connection.close.assert_called_once()
        forbidden.assert_not_called()
