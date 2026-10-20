"""Real client -> builder -> resolver -> endpoint recovery with offline doubles."""
import copy
import io
import json
from urllib.error import HTTPError
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from pathforge.llm import openrouter_client as client
from pathforge.services import ground_truth_builder as builder
from pathforge.tests.test_problem_preparation_boundary import boundary, MemoryConnection, GROUND_TRUTH


V3 = {"approach_contract_version": 3, "approaches": [
    {"name": "Sort and scan", "patterns": ["sorting", "array_traversal"],
     "confidence": {"sorting": .9, "array_traversal": .8}}]}


def completion(raw):
    return json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(raw)}}]}).encode()


def test_real_provider_contract_prepares_then_uses_cache_without_new_generation(boundary, monkeypatch):
    connection = MemoryConnection(ground_truth=None)
    monkeypatch.setenv("OPENROUTER_API_KEY", "isolated-fixture-key")
    transport = Mock(return_value=completion(V3))
    with patch.object(client, "_post_request", transport), patch.object(builder, "call_llm", client.generate_ground_truth):
        prepared = boundary.prepare(connection)
        assert prepared.solution_groups[0].patterns == ["array_traversal", "sorting"]
        assert connection.writes == ["ground_truth"]
        assert connection.commit.call_count == 1
        boundary.prepare(connection)
        boundary.analyze(connection, {"leetcode_id": 209})
    transport.assert_called_once()
    assert '"approach_contract_version": 3' in transport.call_args.args[0]
    assert "top-level patterns must" not in transport.call_args.args[0]


@pytest.mark.parametrize("status,code", [(429, "PREPARATION_RATE_LIMITED"),
                                        (401, "PREPARATION_UNAVAILABLE")])
def test_provider_failure_is_distinct_sanitized_and_not_automatically_retried(boundary, monkeypatch, status, code):
    connection = MemoryConnection(ground_truth=None)
    monkeypatch.setenv("OPENROUTER_API_KEY", "isolated-fixture-key")
    error = HTTPError("https://provider.invalid/", status, "private-provider-message",
                      {"Retry-After": "30"}, io.BytesIO(b"sensitive provider body"))
    with patch.object(client, "_post_request", side_effect=error) as request, \
         patch.object(client.time, "sleep") as sleep, \
         patch.object(builder, "call_llm", client.generate_ground_truth), pytest.raises(HTTPException) as raised:
        boundary.prepare(connection)
    assert raised.value.status_code == 502 and raised.value.detail["code"] == code
    assert "private-provider" not in str(raised.value.detail) and "sensitive" not in str(raised.value.detail)
    if status == 429:
        assert raised.value.headers == {"Retry-After": "30"}
        assert raised.value.detail["retry_after"] == 30
    request.assert_called_once()
    sleep.assert_not_called()
    assert connection.writes == []
    connection.commit.assert_not_called()
    boundary.engine.assert_not_called()
    boundary.persist.assert_not_called()


@pytest.mark.parametrize("raw", [
    {"patterns": ["sorting"], "approaches": [{"name": "Scan", "patterns": ["array_traversal"]}]},
    {"approach_contract_version": 3, "approaches": [{"name": "Invalid", "patterns": [None]}]},
])
def test_inconsistent_output_rejects_before_storage_and_has_code_only_recovery(boundary, monkeypatch, raw):
    connection = MemoryConnection(ground_truth=None)
    monkeypatch.setenv("OPENROUTER_API_KEY", "isolated-fixture-key")
    with patch.object(client, "_post_request", return_value=completion(raw)) as transport, \
         patch.object(builder, "call_llm", client.generate_ground_truth), pytest.raises(HTTPException) as raised:
        boundary.prepare(connection)
    assert raised.value.status_code == 502
    assert raised.value.detail["code"] == "PREPARATION_INVALID_OUTPUT"
    assert "inspect your code on its own" in raised.value.detail["message"]
    assert "contest" not in raised.value.detail["message"]
    assert connection.ground_truth is None and connection.writes == []
    connection.commit.assert_not_called()
    boundary.persist.assert_not_called()
    transport.assert_called_once()


def test_invalid_json_is_not_silently_repaired_or_a_paid_retry(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "isolated-fixture-key")
    with patch.object(client, "_post_request", return_value=b"not JSON") as request:
        with pytest.raises(client.LLMPreparationError) as raised:
            client.generate_ground_truth("Synthetic source")
    assert raised.value.code == "PREPARATION_INVALID_OUTPUT"
    request.assert_called_once()


def test_existing_cached_ground_truth_remains_unchanged(boundary):
    connection = MemoryConnection()
    before = copy.deepcopy(connection.ground_truth)
    boundary.prepare(connection)
    assert connection.ground_truth == before == GROUND_TRUTH
    assert connection.writes == []
    boundary.llm.assert_not_called()


def test_descriptive_only_new_contract_does_not_force_an_unsupported_algorithm_into_a_pattern():
    raw = {"approach_contract_version": 3, "approaches": [{"name": "Digit arithmetic",
        "description": "Read digits using remainders and division.", "patterns": [],
        "comparison_support": "UNSUPPORTED", "coverage_limit": "Digit arithmetic is outside the supported vocabulary."}]}
    patterns, confidence, approaches = builder.normalize_ground_truth_response(raw)
    assert patterns == [] and confidence == {}
    assert approaches[0]["comparison_support"] == "UNSUPPORTED"


def test_v3_reaches_actual_analysis_matching_shadow_and_unrated_persistence():
    from pathforge.tests import test_analysis_capabilities as capabilities
    def v3(patterns):
        return {"approach_contract_version": 3,
                "approaches": [{"name": "Explicit components", "patterns": patterns}]}
    with patch.object(capabilities, "proposal", side_effect=v3):
        cases = capabilities.build_capability_cases()
    assert cases
    for case in cases.values():
        response = case["response"]
        assert response["match_result"]["match_result"] == "FULL_MATCH"
        approach = response["problem_info"]["solution_groups"][0]
        assert set(approach["observed_patterns"]) == set(case["expected_patterns"])
        assert approach["review_state"] == "UNREVIEWED"
        assert response["persisted"]["skill_updates_skipped"] is True
        assert response["elo_updates"] == [] and response["persisted"]["gap_signals_count"] == 0
        assert response["shadow_analysis"]["strategy_selection"]["submission"]["selected"] is None
