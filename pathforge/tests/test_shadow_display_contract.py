"""Canonical Shadow serialization contracts and real, isolated UI test payloads."""

import ast
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
from unittest.mock import Mock, patch

import pytest


@contextmanager
def isolated_services():
    import dotenv
    import psycopg2
    import psycopg2.pool

    forbidden = Mock(side_effect=AssertionError("Database/external service access forbidden"))
    with patch.dict(os.environ):
        os.environ.pop("DATABASE_URL", None)
        with patch.object(dotenv, "load_dotenv", return_value=False), \
             patch.object(psycopg2, "connect", forbidden), \
             patch.object(psycopg2.pool, "ThreadedConnectionPool", forbidden), \
             patch.object(socket.socket, "connect", forbidden), \
             patch.object(socket, "create_connection", forbidden):
            yield
        assert forbidden.call_count == 0


def build_engine_cases():
    """Run both engines; only problem fixtures and persistence metadata are synthetic."""
    specifications = {
        "bs_renamed_vars": ("binary_search", "binary_search_standard"),
        "hash_two_sum(self)": ("hash_lookup", "hash_map_lookup"),
        "ps_not_prefix_just_sum": ("sequential_accumulation", "array_traversal"),
    }
    corpus = Path(__file__).resolve().parents[1] / "ast_analysis/shadow/tests/evaluation_corpus.py"
    sources = {}
    for node in ast.walk(ast.parse(corpus.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "add":
            name = ast.literal_eval(node.args[0])
            if name in specifications:
                sources[name] = ast.literal_eval(node.args[1])
    assert set(sources) == set(specifications)

    with isolated_services():
        from pathforge.api.routes.analyze import AnalyzeResponse, ShadowAnalysisResult
        from pathforge.api.services.analysis import run_analysis
        from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis

        cases = {}
        for name, (concept, pattern) in specifications.items():
            groups = [{"id": "display_family", "required": [concept], "patterns": [pattern],
                       "optional": [], "forbidden": [], "authority_tier": "STRUCTURALLY_OBSERVED"}]
            analysis = run_analysis(sources[name], accepted_solution_groups=groups)
            assert "error" not in analysis
            raw = run_shadow_analysis(sources[name], groups)
            assert raw is not None
            response = AnalyzeResponse(
                **analysis,
                # Transport-only metadata: no submission is inserted or scored.
                persisted={"submission_id": 7, "gap_signals_count": 0, "elo_updates_count": 0},
                shadow_analysis=ShadowAnalysisResult(**raw),
            ).model_dump()
            cases[name] = {"code": sources[name], "raw": raw, "response": response}
        return cases


@pytest.fixture(scope="module")
def engine_cases():
    return build_engine_cases()


@pytest.mark.parametrize("name", ["bs_renamed_vars", "hash_two_sum(self)", "ps_not_prefix_just_sum"])
def test_canonical_fields_survive_actual_response_serialization(engine_cases, name):
    case = engine_cases[name]
    wire = case["response"]["shadow_analysis"]
    for key in ("coverage", "strategy_selection"):
        assert key in wire, f"API discarded canonical {key}"
        assert wire[key] == case["raw"][key]
    for key in ("match_outcome", "structural_facts", "technique_evidence", "strategy_evidence"):
        assert wire[key] == case["raw"][key]


def test_fixture_expectations_are_established_by_actual_engines(engine_cases):
    confirmed = engine_cases["bs_renamed_vars"]["raw"]
    assert confirmed["coverage"]["families"][0]["coverage_state"] == "CONFIRMED"
    assert confirmed["strategy_selection"]["submission"]["selected"] == "binary_search"
    hash_lookup = engine_cases["hash_two_sum(self)"]["raw"]
    assert hash_lookup["match_outcome"]["outcome"] == "CONFIRMED"
    assert hash_lookup["coverage"]["families"][0]["coverage_state"] == "PROVISIONAL"
    assert hash_lookup["strategy_selection"]["submission"]["selected"] is None
    running_total = engine_cases["ps_not_prefix_just_sum"]["raw"]
    assert running_total["match_outcome"]["outcome"] == "CONFIRMED"
    assert running_total["coverage"]["families"][0]["coverage_state"] == "UNRESOLVED"
    assert running_total["strategy_selection"]["submission"]["selected"] is None
    for case in engine_cases.values():
        assert all(not family["authoritative"] for family in case["raw"]["authority"]["families"])


def test_older_payload_remains_serializable():
    with isolated_services():
        from pathforge.api.routes.analyze import ShadowAnalysisResult
        result = ShadowAnalysisResult(match_outcome={"outcome": "CONFIRMED"}).model_dump()
    assert result["match_outcome"] == {"outcome": "CONFIRMED"}
    assert result.get("coverage") is None
    assert result.get("strategy_selection") is None


if __name__ == "__main__":
    print(json.dumps(build_engine_cases()))
