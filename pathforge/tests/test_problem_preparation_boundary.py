"""Cache/preparation contracts, with no real database or external requests."""

import copy
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from pathforge.api.routes import analyze, prepare_problem
from pathforge.db import db
from pathforge.llm.graphql_client import GraphQLUnavailableError
from pathforge.services import ground_truth_builder as builder
from pathforge.services import problem_resolver as resolver


PROBLEM = {
    "id": 209, "title_slug": "minimum-size-subarray-sum", "title": "Fixture problem",
    "difficulty": "Medium", "topics": [], "description": "Fixture description", "pattern": [],
}
GROUP = {
    "id": "g0", "patterns": ["sliding_window_variable"], "required": ["sliding_window"],
    "evidence": "externally_listed", "authority_tier": "EXTERNAL_VERIFIED",
}
GROUND_TRUTH = {
    "patterns": ["sliding_window_variable"], "confidence": {},
    "solution_groups": [GROUP], "validation_status": "externally_listed",
}
EMPTY_GROUND_TRUTH = {
    "patterns": [], "confidence": {}, "solution_groups": [], "validation_status": "llm_proposed",
}


class MemoryConnection:
    def __init__(self, problem=PROBLEM, ground_truth=GROUND_TRUTH):
        self.problem = copy.deepcopy(problem)
        self.ground_truth = copy.deepcopy(ground_truth)
        self.writes = []
        self.commit = Mock()
        self.rollback = Mock()
        self.close = Mock()

    def execute(self, sql, params):
        sql = " ".join(sql.split())
        if sql.startswith("INSERT INTO problems"):
            self.writes.append("problem")
            self.problem = {**copy.deepcopy(PROBLEM), "pattern": params[6]}
            row = None
        elif sql.startswith("INSERT INTO problem_ground_truth"):
            self.writes.append("ground_truth")
            self.ground_truth = {
                "patterns": params[1], "confidence": params[2], "solution_groups": params[3],
                "validation_status": "llm_proposed",
            }
            row = None
        elif sql.startswith("SELECT 1 FROM problem_ground_truth"):
            row = {"present": 1} if self.ground_truth is not None else None
        elif "FROM problem_ground_truth" in sql:
            row = copy.deepcopy(self.ground_truth)
        elif sql.startswith("SELECT pattern FROM problems"):
            row = {"pattern": self.problem["pattern"]} if self.problem else None
        elif "FROM problems" in sql:
            row = copy.deepcopy(self.problem)
        else:
            raise AssertionError(f"Unexpected SQL: {sql}")
        return SimpleNamespace(fetchone=lambda: row)


@pytest.fixture
def boundary(monkeypatch):
    from pathforge.ast_analysis.shadow import shadow_runner
    from src.ast_detection.semantic.shadow_detector import ShadowDetector

    monkeypatch.setattr(db, "_ensure_pool", Mock(side_effect=AssertionError("Database forbidden")))
    fetch = Mock(side_effect=AssertionError("GraphQL forbidden"))
    lookup = Mock(side_effect=AssertionError("GraphQL ID lookup forbidden"))
    llm = Mock(side_effect=AssertionError("LLM forbidden"))
    monkeypatch.setattr(resolver, "fetch_problem_by_slug", fetch)
    monkeypatch.setattr(resolver, "fetch_title_slug_by_id", lookup)
    monkeypatch.setattr(builder, "call_llm", llm)
    for route in (analyze, prepare_problem):
        monkeypatch.setattr(route, "get_current_user", Mock(return_value=SimpleNamespace(user_id=7)))
    engine = Mock(return_value={
        "ast": {"detected_patterns": []},
        "match_result": {"match_result": "FULL_MATCH", "unmatched_patterns": []},
    })
    persist = Mock(return_value={
        "submission_id": 123, "gap_signals_count": 0, "elo_updates_count": 0,
    })
    monkeypatch.setattr(analyze, "run_analysis", engine)
    monkeypatch.setattr(analyze, "run_persistence", persist)
    monkeypatch.setattr(shadow_runner, "run_shadow_analysis", Mock(return_value=None))
    monkeypatch.setattr(ShadowDetector, "analyze_safe", Mock(return_value=None))

    def run_analysis(connection, identifier):
        monkeypatch.setattr(analyze, "get_connection", Mock(return_value=connection))
        request = analyze.AnalyzeRequest(user_id=999, code="def solve(): return 1", problem=identifier)
        return analyze.analyze_endpoint(request, None)

    def run_preparation(connection):
        monkeypatch.setattr(prepare_problem, "get_connection", Mock(return_value=connection))
        request = prepare_problem.PrepareRequest(problem={"leetcode_id": 209})
        return prepare_problem.prepare_problem_endpoint(request, None)

    return SimpleNamespace(
        analyze=run_analysis, prepare=run_preparation, fetch=fetch, lookup=lookup,
        llm=llm, engine=engine, persist=persist,
    )


def assert_no_preparation(case, connection):
    case.fetch.assert_not_called()
    case.lookup.assert_not_called()
    case.llm.assert_not_called()
    assert connection.writes == []


@pytest.mark.parametrize("identifier", [{"leetcode_id": 209}, {"title_slug": PROBLEM["title_slug"]}])
def test_cached_analysis_uses_only_existing_context(boundary, identifier):
    connection = MemoryConnection()
    result = boundary.analyze(connection, identifier)
    assert result.problem_info.leetcode_id == 209
    groups = boundary.engine.call_args.kwargs["accepted_solution_groups"]
    assert groups[0]["patterns"] == GROUP["patterns"]
    assert groups[0]["required"] == GROUP["required"]
    assert boundary.persist.call_args.kwargs["user_id"] == 7
    assert_no_preparation(boundary, connection)
    connection.commit.assert_called_once()
    connection.close.assert_called_once()


def test_analysis_without_problem_preserves_context_free_path(boundary):
    connection = MemoryConnection(None, None)
    boundary.analyze(connection, None)
    assert boundary.engine.call_args.kwargs["accepted_solution_groups"] is None
    assert boundary.persist.call_args.kwargs["problem_id"] is None
    assert_no_preparation(boundary, connection)


@pytest.mark.parametrize("problem,ground_truth,code,reason", [
    (None, None, "PREPARATION_REQUIRED", "PROBLEM_NOT_CACHED"),
    (PROBLEM, None, "PREPARATION_REQUIRED", "GROUND_TRUTH_MISSING"),
    (PROBLEM, EMPTY_GROUND_TRUTH, "GROUND_TRUTH_UNAVAILABLE", "UNUSABLE_GROUND_TRUTH"),
    (PROBLEM, {**EMPTY_GROUND_TRUTH, "solution_groups": "invalid-json"},
     "GROUND_TRUTH_UNAVAILABLE", "UNUSABLE_GROUND_TRUTH"),
    (PROBLEM, {**EMPTY_GROUND_TRUTH, "solution_groups": [{"patterns": []}]},
     "GROUND_TRUTH_UNAVAILABLE", "UNUSABLE_GROUND_TRUTH"),
])
def test_unready_analysis_rejects_before_engines_or_writes(boundary, problem, ground_truth, code, reason):
    connection = MemoryConnection(problem, ground_truth)
    with pytest.raises(HTTPException) as raised:
        boundary.analyze(connection, {"leetcode_id": 209})
    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == code
    assert raised.value.detail["reason"] == reason
    assert isinstance(raised.value.detail["message"], str)
    boundary.engine.assert_not_called()
    boundary.persist.assert_not_called()
    assert_no_preparation(boundary, connection)
    connection.commit.assert_not_called()
    connection.close.assert_called_once()


def test_legacy_flat_ground_truth_remains_usable(boundary):
    connection = MemoryConnection(ground_truth={**GROUND_TRUTH, "solution_groups": None})
    boundary.analyze(connection, {"leetcode_id": 209})
    assert boundary.engine.call_args.kwargs["accepted_solution_groups"][0]["patterns"] == GROUP["patterns"]
    assert_no_preparation(boundary, connection)


def test_readiness_does_not_require_canonical_product_authority(boundary):
    ground_truth = {**GROUND_TRUTH, "solution_groups": [{**GROUP, "authority_tier": "llm_proposed", "evidence": "llm_proposed"}]}
    connection = MemoryConnection(ground_truth=ground_truth)
    boundary.analyze(connection, {"leetcode_id": 209})
    assert boundary.engine.call_args.kwargs["accepted_solution_groups"][0]["authority_tier"] == "llm_proposed"
    assert_no_preparation(boundary, connection)


def test_cached_preparation_does_not_regenerate(boundary):
    connection = MemoryConnection()
    result = boundary.prepare(connection)
    assert result.leetcode_id == 209
    assert_no_preparation(boundary, connection)


@pytest.mark.parametrize("ground_truth", [EMPTY_GROUND_TRUTH, {**EMPTY_GROUND_TRUTH, "patterns": "invalid-json"}])
def test_unusable_stored_preparation_never_reports_success_or_regenerates(boundary, ground_truth):
    connection = MemoryConnection(ground_truth=ground_truth)
    with pytest.raises(HTTPException) as raised:
        boundary.prepare(connection)
    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "GROUND_TRUTH_UNAVAILABLE"
    assert_no_preparation(boundary, connection)


@pytest.mark.parametrize("problem", [PROBLEM, None])
def test_preparation_alone_fills_missing_cache(boundary, problem):
    connection = MemoryConnection(problem, None)
    boundary.fetch.side_effect = None
    boundary.fetch.return_value = {"questionId": "209", "title": "Fixture problem", "difficulty": "Medium", "content": "Fixture description", "topicTags": []}
    boundary.lookup.side_effect = None
    boundary.lookup.return_value = PROBLEM["title_slug"]
    boundary.llm.side_effect = None
    boundary.llm.return_value = {"patterns": ["sliding_window_variable"], "confidence": {}}
    result = boundary.prepare(connection)
    assert result.leetcode_id == 209
    assert boundary.fetch.call_count == int(problem is None)
    boundary.llm.assert_called_once()
    assert connection.writes == (["problem", "ground_truth"] if problem is None else ["ground_truth"])
    boundary.persist.assert_not_called()


@pytest.mark.parametrize("output", [
    {"patterns": [], "confidence": {}},
    {"patterns": ["not_a_registered_pattern"], "confidence": {}},
    {"patterns": [None], "confidence": {}},
    {"patterns": ["prefix_sum"], "approaches": [None]},
])
def test_unusable_generated_output_returns_502_without_ground_truth_write(boundary, output):
    connection = MemoryConnection(ground_truth=None)
    boundary.llm.side_effect = None
    boundary.llm.return_value = output
    with pytest.raises(HTTPException) as raised:
        boundary.prepare(connection)
    assert raised.value.status_code == 502
    assert "Ground truth generation failed" in raised.value.detail
    assert connection.writes == []
    assert connection.ground_truth is None
    connection.commit.assert_not_called()
    connection.close.assert_called_once()


@pytest.mark.parametrize("failure,status", [("not_found", 404), ("graphql", 502), ("llm", 502)])
def test_preparation_preserves_external_failure_statuses(boundary, failure, status):
    connection = MemoryConnection(None if failure != "llm" else PROBLEM, None)
    boundary.lookup.side_effect = None
    boundary.lookup.return_value = PROBLEM["title_slug"]
    if failure == "not_found":
        boundary.fetch.side_effect = None
        boundary.fetch.return_value = None
    elif failure == "graphql":
        boundary.fetch.side_effect = GraphQLUnavailableError("isolated failure")
    else:
        boundary.llm.side_effect = None
        boundary.llm.return_value = None
    with pytest.raises(HTTPException) as raised:
        boundary.prepare(connection)
    assert raised.value.status_code == status
    assert connection.writes == []
    connection.close.assert_called_once()


@pytest.mark.parametrize("prepare", [False, True], ids=["analyze", "prepare"])
@pytest.mark.parametrize("as_text", [False, True], ids=["jsonb", "json-text"])
@pytest.mark.parametrize("patterns", [[None], [{}]], ids=["null-pattern", "object-pattern"])
def test_malformed_stored_patterns_reject_before_analysis_or_writes(
    boundary, prepare, as_text, patterns,
):
    groups = [{"patterns": patterns}]
    ground_truth = {**GROUND_TRUTH, "solution_groups": json.dumps(groups) if as_text else groups}
    connection = MemoryConnection(ground_truth=ground_truth)
    original = copy.deepcopy(connection.ground_truth)
    with pytest.raises(HTTPException) as raised:
        if prepare:
            boundary.prepare(connection)
        else:
            boundary.analyze(connection, {"leetcode_id": 209})
    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "GROUND_TRUTH_UNAVAILABLE"
    assert raised.value.detail["reason"] == "UNUSABLE_GROUND_TRUTH"
    assert isinstance(raised.value.detail["message"], str)
    boundary.engine.assert_not_called()
    boundary.persist.assert_not_called()
    assert_no_preparation(boundary, connection)
    assert connection.ground_truth == original
    connection.commit.assert_not_called()
    connection.close.assert_called_once()


@pytest.mark.parametrize("prepare", [False, True], ids=["analyze", "prepare"])
@pytest.mark.parametrize("field,value", [
    ("patterns", [{}]),
    ("patterns", "invalid-json"),
    ("confidence", []),
    ("solution_groups", {}),
    ("solution_groups", [None]),
    ("solution_groups", "invalid-json"),
    ("solution_groups", [{**GROUP, "patterns": "sliding_window_variable"}]),
    ("solution_groups", [{**GROUP, "required": [{}]}]),
    ("solution_groups", [{**GROUP, "optional": None}]),
    ("solution_groups", [{**GROUP, "excluded": "binary_search"}]),
    ("solution_groups", [{**GROUP, "provenance": [{}]}]),
    ("solution_groups", [{**GROUP, "confidence": []}]),
    ("solution_groups", [{"patterns": None, "required": None}]),
])
def test_stored_pattern_containers_fail_closed(boundary, prepare, field, value):
    connection = MemoryConnection(ground_truth={**GROUND_TRUTH, field: value})
    original = copy.deepcopy(connection.ground_truth)
    with pytest.raises(HTTPException) as raised:
        if prepare:
            boundary.prepare(connection)
        else:
            boundary.analyze(connection, {"leetcode_id": 209})
    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "GROUND_TRUTH_UNAVAILABLE"
    boundary.engine.assert_not_called()
    boundary.persist.assert_not_called()
    assert_no_preparation(boundary, connection)
    assert connection.ground_truth == original
    connection.commit.assert_not_called()


@pytest.mark.parametrize("prepare", [False, True], ids=["analyze", "prepare"])
@pytest.mark.parametrize("groups", [None, "", [], "[]", "null"])
def test_absent_stored_groups_preserve_legacy_json_fallback(boundary, prepare, groups):
    connection = MemoryConnection(ground_truth={
        **GROUND_TRUTH, "patterns": json.dumps(GROUND_TRUTH["patterns"]),
        "solution_groups": groups,
    })
    original = copy.deepcopy(connection.ground_truth)
    if prepare:
        assert boundary.prepare(connection).leetcode_id == 209
    else:
        boundary.analyze(connection, {"leetcode_id": 209})
        assert boundary.engine.call_args.kwargs["accepted_solution_groups"][0]["patterns"] == GROUP["patterns"]
    assert_no_preparation(boundary, connection)
    assert connection.ground_truth == original


@pytest.mark.parametrize("patterns", [None, []])
def test_group_without_legacy_patterns_keeps_required_fallback(boundary, patterns):
    group = {**GROUP, "patterns": patterns}
    connection = MemoryConnection(ground_truth={**GROUND_TRUTH, "solution_groups": [group]})
    boundary.analyze(connection, {"leetcode_id": 209})
    loaded = boundary.engine.call_args.kwargs["accepted_solution_groups"][0]
    assert loaded["patterns"] == loaded["required"] == GROUP["required"]
    assert_no_preparation(boundary, connection)


def test_legacy_readiness_does_not_require_shadow_vocabulary(boundary):
    ground_truth = {
        **GROUND_TRUTH, "patterns": ["dfs_iterative"],
        "solution_groups": [{"patterns": ["dfs_iterative"], "required": []}],
    }
    connection = MemoryConnection(ground_truth=ground_truth)
    boundary.analyze(connection, {"leetcode_id": 209})
    loaded = boundary.engine.call_args.kwargs["accepted_solution_groups"][0]
    assert loaded["patterns"] == ["dfs_iterative"]
    assert loaded["matchable"] is False
    assert_no_preparation(boundary, connection)


def test_unrelated_loader_programming_errors_are_not_readiness_errors(boundary, monkeypatch):
    monkeypatch.setattr(builder, "refresh_groups_vocabulary", Mock(side_effect=TypeError("loader bug")))
    connection = MemoryConnection()
    with pytest.raises(TypeError, match="loader bug"):
        boundary.analyze(connection, {"leetcode_id": 209})
    boundary.engine.assert_not_called()
    boundary.persist.assert_not_called()
    assert_no_preparation(boundary, connection)


def test_stored_data_validation_preserves_curated_reconciliation(boundary):
    connection = MemoryConnection(problem={**PROBLEM, "pattern": ["hash_map_lookup"]})
    original = copy.deepcopy(connection.ground_truth)
    boundary.analyze(connection, {"leetcode_id": 209})
    loaded = boundary.engine.call_args.kwargs["accepted_solution_groups"][0]
    assert loaded["patterns"] == ["hash_map_lookup"]
    assert loaded["required"] == GROUP["required"]
    assert loaded["derivation_patterns"] == GROUP["patterns"]
    assert "csv_curated_override" in loaded["provenance"]
    assert connection.ground_truth == original
    assert_no_preparation(boundary, connection)


def test_database_failures_are_not_ground_truth_shape_errors(boundary, monkeypatch):
    connection = MemoryConnection()
    execute = connection.execute

    def fail_ground_truth_select(sql, params):
        if "SELECT patterns, confidence" in sql:
            raise RuntimeError("database read failed")
        return execute(sql, params)

    monkeypatch.setattr(connection, "execute", fail_ground_truth_select)
    with pytest.raises(RuntimeError, match="database read failed"):
        boundary.analyze(connection, {"leetcode_id": 209})
    boundary.engine.assert_not_called()
    boundary.persist.assert_not_called()
    assert_no_preparation(boundary, connection)
