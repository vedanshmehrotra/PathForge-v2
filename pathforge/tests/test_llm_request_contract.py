"""Real client/builder paths with isolated HTTP responses and connection doubles."""

import json
from unittest.mock import Mock

import pytest

from pathforge.llm import openrouter_client as client


VALID = {"patterns": ["prefix_sum"], "confidence": {"prefix_sum": 0.9},
         "approaches": [{"name": "Prefix totals", "patterns": ["prefix_sum"]}]}


@pytest.fixture
def transport(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "isolated-fixture-key")
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.delenv("OPENROUTER_MAX_TOKENS", raising=False)
    state = {"finish_reason": "stop", "content": json.dumps(VALID), "requests": []}

    def urlopen(request, timeout):
        state["requests"].append({"body": json.loads(request.data), "timeout": timeout})
        response = Mock()
        response.read.return_value = json.dumps({"choices": [{
            "finish_reason": state["finish_reason"], "message": {"content": state["content"]},
        }]}).encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        return response

    monkeypatch.setattr(client.urllib.request, "urlopen", urlopen)
    return state


def test_default_request_preserves_model_and_token_budget(transport):
    assert client.call_llm("Fixture problem") == VALID
    request = transport["requests"][0]["body"]
    assert request["model"] == "openai/gpt-4o-mini"
    assert request["max_tokens"] == 1000
    assert len(transport["requests"]) == 1


def test_explicit_model_and_token_budget_reach_real_request(transport, monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODEL", "fixture/explicit-model")
    monkeypatch.setenv("OPENROUTER_MAX_TOKENS", "2400")
    assert client.call_llm("Fixture problem") == VALID
    request = transport["requests"][0]["body"]
    assert request["model"] == "fixture/explicit-model"
    assert request["max_tokens"] == 2400


@pytest.mark.parametrize("name,value", [
    ("OPENROUTER_MODEL", ""), ("OPENROUTER_MODEL", "   "),
    ("OPENROUTER_MAX_TOKENS", "0"), ("OPENROUTER_MAX_TOKENS", "-1"),
    ("OPENROUTER_MAX_TOKENS", "lots"), ("OPENROUTER_MAX_TOKENS", "1.5"),
])
def test_invalid_configuration_makes_no_request(transport, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    assert client.call_llm("Fixture problem") is None
    assert transport["requests"] == []


@pytest.mark.parametrize("reason", ["length", "content_filter", "error", "tool_calls"])
def test_incomplete_or_failed_completion_is_rejected_even_with_valid_json(transport, reason):
    transport["finish_reason"] = reason
    assert client.call_llm("Fixture problem") is None
    assert len(transport["requests"]) == 1  # No automatic paid retry for rejected completion.


@pytest.mark.parametrize("content", [None, 7, {}, []])
def test_nontext_content_is_a_controlled_failure(transport, content):
    transport["content"] = content
    assert client.call_llm("Fixture problem") is None
    assert len(transport["requests"]) == 1


@pytest.mark.parametrize("reason", ["stop", "length", "error"])
def test_actual_client_to_builder_storage_boundary(transport, monkeypatch, reason):
    from pathforge.tests.test_shadow_display_contract import isolated_services

    transport["finish_reason"] = reason
    with isolated_services():
        from pathforge.services import ground_truth_builder as builder
        monkeypatch.setattr(builder, "call_llm", client.call_llm)
        connection = Mock(spec=["execute", "commit", "rollback"])
        if reason == "stop":
            assert builder.build_ground_truth(209, "Fixture problem", connection) == ["prefix_sum"]
            connection.execute.assert_called_once()
            params = connection.execute.call_args.args[1]
            group = json.loads(params[3])[0]
            assert group["authority_tier"] == "llm_proposed"
            assert group["approach_definition"] == "EXPLICIT"
        else:
            with pytest.raises(builder.GroundTruthError):
                builder.build_ground_truth(209, "Fixture problem", connection)
            connection.execute.assert_not_called()
        connection.commit.assert_not_called()
