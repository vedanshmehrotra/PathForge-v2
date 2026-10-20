"""Isolated persistence orchestration; no configured or shared database access."""
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pathforge.services.pattern_levels import pattern_level
from pathforge.services.practice_tracking import analysis_key, get_pattern_practice
from pathforge.tests.test_b6_product_eligibility import persistence_case, _persistence_group


@pytest.mark.parametrize("rating,level,progress", [(400, 1, 0), (599.99, 1, 99.99), (600, 2, 0), (1200, 5, 0), (1232, 5, 16), (399, 1, 0)])
def test_levels_convert_existing_rating_at_boundaries(rating, level, progress):
    result = pattern_level(rating)
    assert result["level"] == level
    assert abs(result["progress_percent"] - progress) <= .01
    assert result["experience"] >= 0


@pytest.mark.parametrize("rating", [float("nan"), float("inf")])
def test_invalid_rating_cannot_become_invented_progress(rating):
    with pytest.raises(ValueError):
        pattern_level(rating)


def test_submission_identity_is_stable_across_editor_whitespace_and_restarts():
    event = {"source": "extension", "submission_id": "123"}
    assert analysis_key(1, "code\r\n", event) == analysis_key(1, "code\n", event)
    assert analysis_key(1, "code", event) != analysis_key(2, "code", event)
    assert analysis_key(1, "code", event) != analysis_key(1, "code", {**event, "submission_id": "124"})
    assert analysis_key(1, "code", event) != analysis_key(1, "code", {"source": "extension"})
    assert analysis_key(1, "code", event, "2026-10-20") == analysis_key(1, "code", event, "2026-10-21")
    assert analysis_key(1, "code", practice_day="2026-10-20") != analysis_key(1, "code", practice_day="2026-10-21")


def test_replay_cannot_touch_elo_profiles_streak_or_recommendations(persistence_case):
    case = persistence_case
    original = case.connection.execute
    def execute(sql, params):
        if "analysis_key =" in sql:
            return SimpleNamespace(fetchone=lambda: {"id": 456, "verdict_type": "authoritative"})
        return original(sql, params)
    case.connection.execute = execute
    result = case.run([_persistence_group("externally_listed")])
    assert result["replayed"] and result["submission_id"] == 456
    assert result["elo_updates_count"] == 0 and result["skill_updates_skipped"]
    assert "pg_advisory_xact_lock" in case.connection.queries[0][0]
    assert not any("INSERT" in sql or "UPDATE" in sql for sql, _ in case.connection.queries)
    for effect in (case.profile, case.streak, case.elo_engine.compute_updates, case.recommend):
        effect.assert_not_called()


def test_second_solution_same_problem_today_is_saved_without_scoring(persistence_case):
    case = persistence_case
    original = case.connection.execute
    def execute(sql, params):
        if "AND skill_updates_applied = TRUE" in sql:
            assert params[:2] == (7, 209)
            assert params[2].endswith("T00:00:00+00:00")
            return SimpleNamespace(fetchone=lambda: {"id": 5})
        return original(sql, params)
    case.connection.execute = execute
    result = case.run([_persistence_group("externally_listed")])
    assert result["score_reason"] == "problem_already_scored_today"
    assert result["submission_id"] == 123 and result["skill_updates_skipped"]
    case.streak.assert_called_once()
    case.profile.assert_not_called()
    case.elo_engine.compute_updates.assert_not_called()


def test_draft_cannot_score_even_when_patterns_have_reviewed_authority(persistence_case):
    from pathforge.services.persistence import run_persistence
    case = persistence_case
    group = _persistence_group("externally_listed")
    result = run_persistence(case.connection, 7, 209, "Medium", "code",
        {"detected_patterns": [{"pattern_id": "sliding_window_variable", "confidence": .9}]},
        {"match_result": "FULL_MATCH", "matched_groups": [0], "unmatched_patterns": []},
        [group], {"source": "extension", "submission_id": None})
    assert result["score_reason"] == "awaiting_submission"
    assert result["skill_updates_skipped"]
    case.elo_engine.compute_updates.assert_not_called()


def test_replay_new_submission_daily_limit_and_next_day_revisit(persistence_case, monkeypatch):
    from pathforge.services import persistence
    case = persistence_case
    ledger = []
    def execute(sql, params):
        case.connection.queries.append((sql, params))
        row = None
        if "analysis_key =" in sql:
            row = next((r for r in ledger if (r["user_id"], r["analysis_key"]) == params), None)
        elif "INSERT INTO submissions" in sql:
            row = {"id": len(ledger) + 1, "user_id": params[0], "problem_id": params[1],
                   "submitted_at": params[13], "verdict_type": params[14], "analysis_key": params[17], "scored": False}
            ledger.append(row)
        elif "AND skill_updates_applied = TRUE" in sql:
            row = next((r for r in ledger if r["user_id"] == params[0] and r["problem_id"] == params[1]
                        and r["scored"] and r["submitted_at"] >= params[2]), None)
        elif "UPDATE submissions SET skill_updates_applied" in sql:
            next(r for r in ledger if r["id"] == params[0])["scored"] = True
        elif "SELECT * FROM submissions" in sql:
            row = next(r for r in ledger if r["id"] == params[0])
        elif "SELECT * FROM problems" in sql:
            row = {"id": params[0], "difficulty": "Medium"}
        elif "pg_advisory_xact_lock" not in sql:
            raise AssertionError(sql)
        return SimpleNamespace(fetchone=lambda: row)
    case.connection.execute = execute
    def attempt(submission, problem=209, status="accepted"):
        return persistence.run_persistence(case.connection, 7, problem, "Medium", "code",
            {"detected_patterns": [{"pattern_id": "sliding_window_variable", "confidence": .9}]},
            {"match_result": "FULL_MATCH", "matched_groups": [0], "unmatched_patterns": []},
            [_persistence_group("externally_listed")],
            {"source": "extension", "submission_id": submission, "submission_status": status})
    monkeypatch.setattr(persistence, "iso_now", lambda: "2026-10-20T12:00:00+00:00")
    assert attempt("100", status="failed")["score_reason"] == "submission_not_accepted"
    assert case.elo_engine.compute_updates.call_count == 0
    assert attempt("101")["score_reason"] == "scored"
    assert attempt("101")["replayed"]
    assert attempt("102")["score_reason"] == "problem_already_scored_today"
    assert case.elo_engine.compute_updates.call_count == 1
    assert len(ledger) == 3
    assert attempt("103", problem=210)["score_reason"] == "scored"
    monkeypatch.setattr(persistence, "iso_now", lambda: "2026-10-21T12:00:00+00:00")
    assert attempt("101")["replayed"]
    assert attempt("104")["score_reason"] == "scored"
    assert case.elo_engine.compute_updates.call_count == 3
    assert len(ledger) == 5


@pytest.mark.parametrize("jsonb", [False, True])
def test_unscored_secondary_patterns_and_recent_practice_repair_history(jsonb):
    def row(id, day, problem=1, patterns=None, legacy=""):
        return dict(id=id, problem_id=problem, code_hash=str(id), detected_pattern=legacy,
                    detected_patterns_json=(patterns or []) if jsonb else json.dumps(patterns or []),
                    submitted_at=f"2026-10-{day:02d}T12:00:00+00:00")
    detected = [{"pattern_id": "hash_map_lookup"}, {"pattern_id": "array_traversal"},
                {"pattern_id": "binary_search_standard", "detected": False}]
    connection = Mock()
    connection.execute.return_value.fetchall.return_value = [
        row(1, 1, legacy="array_traversal"), row(2, 20, patterns=detected),
        row(3, 20, patterns=detected), row(4, 20, problem=2, patterns=detected),
        row(5, 20, patterns=[{"pattern_id": "ignored", "detected": False}], legacy="ignored")]
    records = {r["topic"]: r for r in get_pattern_practice(connection, 7)}
    assert records["array_traversal"]["last_attempt_at"].startswith("2026-10-20")
    assert records["array_traversal"]["attempt_count"] == 3
    assert records["hash_map_lookup"]["attempt_count"] == 2
    assert "binary_search_standard" not in records and "ignored" not in records
    connection.execute.assert_called_once()
    assert connection.execute.call_args.args[1] == (7,)


def test_unique_index_is_an_automatic_migration():
    from pathforge.db.db import _classify_statement
    assert _classify_statement("CREATE UNIQUE INDEX IF NOT EXISTS idx ON submissions(user_id, analysis_key)") == "migration"


@pytest.mark.parametrize("stamp", [
    datetime(2026, 10, 20, 12, tzinfo=timezone.utc),
    datetime(2026, 10, 20, 12),
    "2026-10-20T12:00:00Z",
    "2026-10-20 12:00:00",
])
def test_practice_history_accepts_postgres_datetimes_and_legacy_text(stamp):
    connection = Mock()
    connection.execute.return_value.fetchall.return_value = [{
        "id": 1, "problem_id": 1, "code_hash": "fixture", "detected_pattern": "hash_map_lookup",
        "detected_patterns_json": [{"pattern_id": "hash_map_lookup"}, {"pattern_id": "array_traversal"}],
        "submitted_at": stamp}]
    records = get_pattern_practice(connection, 7)
    assert records == [{"topic": pattern, "attempt_count": 1, "last_attempt_at": "2026-10-20T12:00:00+00:00"}
                       for pattern in ["array_traversal", "hash_map_lookup"]]
    json.dumps(records)  # API records contain serializable, normalized timestamps.


def test_mixed_timestamp_types_count_sessions_by_utc_day_and_compare_instants():
    def row(id, stamp):
        return {"id": id, "problem_id": 1, "code_hash": "fixture", "detected_pattern": "array_traversal",
                "detected_patterns_json": None, "submitted_at": stamp}
    connection = Mock()
    connection.execute.return_value.fetchall.return_value = [
        row(1, "2026-10-20T00:30:00+02:00"),  # October 19 in UTC.
        row(2, datetime(2026, 10, 19, 23, tzinfo=timezone.utc)),
        row(3, datetime(2026, 10, 20, 0, 30, tzinfo=timezone(timedelta(hours=-2)))),
        row(4, "2026-10-20T01:00:00+00:00"),
        row(5, None), row(6, "invalid date"), row(7, 42),
    ]
    assert get_pattern_practice(connection, 7) == [{"topic": "array_traversal", "attempt_count": 2,
                                                  "last_attempt_at": "2026-10-20T02:30:00+00:00"}]


def test_profile_http_response_handles_native_database_timestamps_and_allowed_origin(monkeypatch):
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.testclient import TestClient
    from pathforge.api import auth_routes

    connection = Mock()
    def execute(query, params):
        assert params == (7,)
        rows = ([{"topic": "hash_map_lookup", "elo_rating": 1208}]
                if "FROM topic_profiles" in query else [{
                    "id": 1, "problem_id": 1, "code_hash": "fixture", "detected_pattern": "hash_map_lookup",
                    "detected_patterns_json": [{"pattern_id": "hash_map_lookup"}, {"pattern_id": "array_traversal"}],
                    "submitted_at": datetime(2026, 10, 20, 12, tzinfo=timezone.utc)}])
        return SimpleNamespace(fetchall=lambda: rows)
    connection.execute.side_effect = execute
    monkeypatch.setattr(auth_routes, "get_connection", lambda *_: connection)
    app = FastAPI()  # Does not import the application or initialize its database.
    origin = "https://path-forge-v2.vercel.app"
    app.add_middleware(CORSMiddleware, allow_origins=[origin])
    app.include_router(auth_routes.router)
    app.dependency_overrides[auth_routes.get_current_user] = lambda: SimpleNamespace(user_id=7)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/auth/profile", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    body = response.json()
    assert body["overall_elo"] == 1208
    assert body["practice_records"][0] == {"topic": "array_traversal", "attempt_count": 1,
                                          "last_attempt_at": "2026-10-20T12:00:00+00:00"}
    connection.close.assert_called_once()


def test_profile_endpoint_reads_all_practice_for_the_authenticated_owner(monkeypatch):
    from pathforge.api import auth_routes
    connection = Mock()
    monkeypatch.setattr(auth_routes, "get_connection", lambda *_: connection)
    profiles = Mock(return_value=[{"topic": "hash_map_lookup", "elo_rating": 1208}])
    practice = Mock(return_value=[{"topic": "array_traversal", "attempt_count": 2, "last_attempt_at": "2026-10-20T12:00:00+00:00"}])
    monkeypatch.setattr(auth_routes, "get_user_profile", profiles)
    monkeypatch.setattr(auth_routes, "get_pattern_practice", practice)
    response = auth_routes.get_profile(SimpleNamespace(user_id=7))
    assert response["practice_records"][0]["topic"] == "array_traversal"
    assert response["profiles"][0]["elo_rating"] == 1208
    profiles.assert_called_once_with(connection, 7)
    practice.assert_called_once_with(connection, 7)
    connection.close.assert_called_once()


@pytest.mark.parametrize("id,status,reason", [
    (None, None, "awaiting_submission"),
    ("42", None, "submission_status_unavailable"),
    ("42", "failed", "submission_not_accepted"),
    ("42", "accepted", "scored"),
])
def test_only_accepted_extension_submissions_can_score(persistence_case, id, status, reason):
    from pathforge.services.persistence import run_persistence
    case = persistence_case
    event = {"source": "extension", "submission_id": id, "submission_status": status}
    result = run_persistence(case.connection, 7, 209, "Medium", "code",
        {"detected_patterns": [{"pattern_id": "sliding_window_variable", "confidence": .9}]},
        {"match_result": "FULL_MATCH", "matched_groups": [0], "unmatched_patterns": []},
        [_persistence_group("externally_listed")], event)
    assert result["score_reason"] == reason
    assert result["skill_updates_skipped"] is (reason != "scored")
    assert case.elo_engine.compute_updates.call_count == int(reason == "scored")
    assert case.profile.call_count == int(reason == "scored")
    insert = next(params for sql, params in case.connection.queries if "INSERT INTO submissions" in sql)
    assert insert[0] == 7
    assert json.loads(insert[18]) == event
    assert any("UPDATE submissions SET skill_updates_applied" in sql
               for sql, _ in case.connection.queries) is (reason == "scored")


@pytest.mark.parametrize("kind", ["unreviewed", "missing_patterns"])
def test_accepted_does_not_promote_ineligible_pattern_evidence(persistence_case, kind):
    from pathforge.services.persistence import run_persistence
    case = persistence_case
    group = _persistence_group("llm_proposed" if kind == "unreviewed" else "externally_listed")
    result = run_persistence(case.connection, 7, 209, "Medium", "code",
        {"detected_patterns": [{"pattern_id": "sliding_window_variable", "confidence": .9}]},
        {"match_result": "FULL_MATCH" if kind == "unreviewed" else "NO_MATCH",
         "matched_groups": [0] if kind == "unreviewed" else [],
         "unmatched_patterns": [] if kind == "unreviewed" else ["sliding_window_variable"]},
        [group], {"source": "extension", "submission_id": "43", "submission_status": "accepted"})
    assert result["skill_updates_skipped"]
    case.elo_engine.compute_updates.assert_not_called()
    case.profile.assert_not_called()


def test_unknown_old_client_receipt_does_not_hide_a_later_confirmed_verdict():
    event = {"source": "extension", "submission_id": "42"}
    assert analysis_key(1, "code", event) != analysis_key(1, "code", {**event, "submission_status": "accepted"})


def test_api_rejects_nonfinal_verdict_and_advertises_the_new_policy():
    from pydantic import ValidationError
    from pathforge.api.routes.analyze import PracticeEvent
    from pathforge.api.auth_routes import verify_session
    with pytest.raises(ValidationError):
        PracticeEvent(source="extension", submission_id="42", submission_status="pending")
    assert verify_session(SimpleNamespace(user_id=7, supabase_id="fixture", email="fixture@example.invalid"))["practice_policy_version"] == 2


@pytest.mark.parametrize("headers", [
    {"origin": "chrome-extension://fixture"},
    {"origin": "moz-extension://fixture"},
    {"referer": "chrome-extension://fixture/panel.html"},
])
def test_legacy_extension_headers_cannot_enable_draft_scoring(headers):
    from pathforge.services.practice_tracking import request_practice_event, scoring_limit
    event = request_practice_event(None, headers)
    connection = Mock()
    assert scoring_limit(connection, 7, 1, "2026-10-20T12:00:00+00:00", event) == "awaiting_submission"
    connection.execute.assert_not_called()


def test_website_request_context_and_explicit_event_are_preserved():
    from pathforge.services.practice_tracking import request_practice_event
    assert request_practice_event(None, {"origin": "https://path-forge-v2.vercel.app"}) is None
    event = {"source": "extension", "submission_id": "42", "submission_status": "accepted"}
    assert request_practice_event(event, {"origin": "chrome-extension://fixture"}) == event


def test_malformed_jsonb_detections_do_not_break_the_practice_page():
    connection = Mock()
    connection.execute.return_value.fetchall.return_value = [{
        "id": 1, "problem_id": 1, "code_hash": "fixture", "detected_pattern": "",
        "detected_patterns_json": [None, {"pattern_id": []}, {"pattern_id": {"invalid": True}},
                                   {"pattern_id": "array_traversal"}],
        "submitted_at": "2026-10-20T12:00:00+00:00"}]
    assert get_pattern_practice(connection, 7) == [{
        "topic": "array_traversal", "attempt_count": 1, "last_attempt_at": "2026-10-20T12:00:00+00:00"}]


@pytest.mark.parametrize("status,expected", [("failed", "submission_not_accepted"), ("accepted", "scored")])
def test_actual_analysis_route_preserves_submission_verdict_and_verified_owner(persistence_case, status, expected):
    from pathforge.api.routes import analyze
    from pathforge.ast_analysis.shadow import persistence as shadow_storage
    from pathforge.tests.test_problem_preparation_boundary import MemoryConnection
    from pathforge.tests.test_b6_product_eligibility import WINDOW_209
    from src.ast_detection.semantic.shadow_detector import ShadowDetector
    from unittest.mock import patch

    class Connection(MemoryConnection):
        inserted = None
        def execute(self, sql, params):
            if any(fragment in sql for fragment in ("pg_advisory_xact_lock", "analysis_key =", "skill_updates_applied =")):
                return SimpleNamespace(fetchone=lambda: None)
            if "INSERT INTO submissions" in sql:
                self.inserted = params
                return SimpleNamespace(fetchone=lambda: {"id": 123})
            if "SELECT * FROM submissions" in sql:
                return SimpleNamespace(fetchone=lambda: {"id": 123, "user_id": 7})
            return super().execute(sql, params)

    group = _persistence_group("externally_listed")
    connection = Connection(ground_truth={"patterns": group["patterns"], "confidence": {}, "solution_groups": [group]})
    persistence_case.elo_engine.compute_updates.return_value = {"pattern_elo_updates": [
        {"pattern_id": "sliding_window_variable", "old_elo": 1200, "new_elo": 1208, "delta": 8}]}
    with patch.object(analyze, "get_current_user", return_value=SimpleNamespace(user_id=7)), \
         patch.object(analyze, "get_connection", return_value=connection), \
         patch.object(shadow_storage, "persist_shadow_analysis"), \
         patch.object(ShadowDetector, "analyze_safe", return_value=None):
        result = analyze.analyze_endpoint(analyze.AnalyzeRequest(user_id=999, code=WINDOW_209,
            problem={"leetcode_id": 209}, practice_event={"source": "extension", "submission_id": "901",
                "submission_status": status}), SimpleNamespace(headers={"origin": "chrome-extension://fixture"})).model_dump()
    assert result["persisted"]["score_reason"] == expected
    assert result["persisted"]["skill_updates_skipped"] is (status != "accepted")
    assert len(result["elo_updates"]) == int(status == "accepted")
    assert connection.inserted[0] == 7
    assert json.loads(connection.inserted[18])["submission_status"] == status
    connection.commit.assert_called_once()
    connection.close.assert_called_once()
