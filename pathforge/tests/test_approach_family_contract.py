"""Source-based approach contracts; real engines, isolated transport/storage."""
import ast
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from pathforge.tests.test_shadow_display_contract import isolated_services


COMPOSITE = {"patterns": ["prefix_sum", "hash_map_lookup"], "confidence": {},
             "approaches": [{"name": "Prefix totals with dictionary lookup",
                             "patterns": ["prefix_sum", "hash_map_lookup"]}]}
DEPTH_CODE = """class Solution:
    def removeOuterParentheses(self, s: str) -> str:
        ans = ''
        depth = 0
        for x in s:
            if x == '(':
                if depth > 0:
                    ans += x
                depth += 1
            else:
                depth -= 1
                if depth > 0:
                    ans += x
        return ans
"""


def corpus_sources():
    names = {"fw_max_sum_k", "bs_renamed_vars", "uf_classic", "hash_two_sum(self)"}
    source = Path(__file__).resolve().parents[1] / "ast_analysis/shadow/tests/evaluation_corpus.py"
    result = {}
    for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "add":
            name = ast.literal_eval(node.args[0])
            if name in names:
                result[name] = ast.literal_eval(node.args[1])
    assert set(result) == names
    return result


@pytest.fixture
def preparation():
    with isolated_services():
        from pathforge.services import ground_truth_builder as builder, problem_resolver as resolver
        from pathforge.tests.test_problem_preparation_boundary import MemoryConnection
        yield builder, resolver, MemoryConnection


def test_generation_requests_explicit_approaches():
    from pathforge.llm.openrouter_client import _build_prompt
    assert '"approaches"' in _build_prompt("Local fixture")


def test_single_explicit_approach_survives_actual_preparation(preparation):
    builder, resolver, Connection = preparation
    conn = Connection(ground_truth=None)
    with patch.object(builder, "call_llm", return_value=copy.deepcopy(COMPOSITE)):
        ctx = resolver.resolve_problem(conn, leetcode_id=209)
    groups = ctx.accepted_solution_groups
    assert len(groups) == 1
    assert set(groups[0]["patterns"]) == {"prefix_sum", "hash_map_lookup"}
    assert set(groups[0]["required"]) == {"sequential_accumulation", "hash_lookup"}
    assert groups[0]["approach_name"] == COMPOSITE["approaches"][0]["name"]
    assert groups[0]["approach_definition"] == "EXPLICIT"
    assert groups[0]["authority_tier"] == groups[0]["evidence"] == "llm_proposed"
    assert ctx.ground_truth_consistency == []
    assert conn.writes == ["ground_truth"]


def test_explicit_approaches_normalize_components_and_confidence(preparation):
    builder, resolver, Connection = preparation
    raw = {"patterns": ["PREFIX_SUM", "HASH-MAP-LOOKUP"], "confidence": {},
           "approaches": [{"name": "Combined", "patterns": ["PREFIX_SUM", "Hash-Map-Lookup"],
                           "confidence": {"prefix_sum": 1.3, "hash_map_lookup": 0.8}}]}
    conn = Connection(ground_truth=None)
    with patch.object(builder, "call_llm", return_value=raw):
        ctx = resolver.resolve_problem(conn, leetcode_id=209)
    group = ctx.accepted_solution_groups[0]
    assert set(group["patterns"]) == {"prefix_sum", "hash_map_lookup"}
    assert group["confidence"] == {"prefix_sum": 1.0, "hash_map_lookup": 0.8}


@pytest.mark.parametrize("components", [[], ["unsupported"], ["prefix_sum", "unsupported"]])
def test_invalid_explicit_components_never_reach_storage(preparation, components):
    builder, _resolver, Connection = preparation
    conn = Connection(ground_truth=None)
    raw = {"patterns": ["prefix_sum"], "approaches": [{"patterns": components}]}
    with patch.object(builder, "call_llm", return_value=raw), pytest.raises(builder.GroundTruthError):
        builder.build_ground_truth(209, "Local description", conn)
    assert conn.writes == []


def test_new_flat_output_does_not_infer_alternatives(preparation):
    builder, _resolver, Connection = preparation
    conn = Connection(ground_truth=None)
    with patch.object(builder, "call_llm", return_value={"patterns": COMPOSITE["patterns"]}):
        builder.build_ground_truth(209, "Local description", conn)
    groups = json.loads(conn.ground_truth["solution_groups"])
    assert len(groups) == 1
    assert groups[0]["approach_definition"] == "UNSPECIFIED"
    assert "family_relation" not in groups[0]


def test_explicit_alternatives_survive_load_and_reconciliation(preparation):
    builder, resolver, Connection = preparation
    raw = {"patterns": ["sliding_window_fixed", "prefix_sum"], "approaches": [
        {"name": "Window", "patterns": ["sliding_window_fixed"]},
        {"name": "Prefix differences", "patterns": ["prefix_sum"]},
    ]}
    conn = Connection(ground_truth=None)
    with patch.object(builder, "call_llm", return_value=raw):
        resolver.resolve_problem(conn, leetcode_id=209)
    before = copy.deepcopy(conn.ground_truth)
    conn.problem["pattern"] = ["sliding_window_fixed"]  # Flat CSV cannot redefine alternatives.
    with patch.object(builder, "call_llm", side_effect=AssertionError("No regeneration")):
        ctx = resolver.resolve_problem(conn, leetcode_id=209, allow_preparation=False)
    assert [g["patterns"] for g in ctx.accepted_solution_groups] == [["sliding_window_fixed"], ["prefix_sum"]]
    assert [g["approach_name"] for g in ctx.accepted_solution_groups] == ["Window", "Prefix differences"]
    assert all(g["family_relation"] == "ONE_OF" for g in ctx.accepted_solution_groups)
    assert len({g["alternative_group_id"] for g in ctx.accepted_solution_groups}) == 1
    assert all(g["authority_tier"] == "llm_proposed" for g in ctx.accepted_solution_groups)
    assert conn.ground_truth == before
    assert conn.writes == ["ground_truth"]


def test_flat_and_explicit_pattern_disagreement_causes_no_write(preparation):
    builder, _resolver, Connection = preparation
    conn = Connection(ground_truth=None)
    raw = {"patterns": ["sliding_window_fixed"], "approaches": [{"patterns": ["prefix_sum"]}]}
    with patch.object(builder, "call_llm", return_value=raw), pytest.raises(builder.GroundTruthError):
        builder.build_ground_truth(209, "Local description", conn)
    assert conn.writes == []


def test_cached_legacy_flat_comparisons_remain_unchanged_and_diagnostic(preparation):
    _builder, resolver, Connection = preparation
    from pathforge.api.services.approaches import describe_approaches
    conn = Connection(ground_truth={"patterns": COMPOSITE["patterns"], "confidence": {},
                                   "solution_groups": None, "validation_status": "llm_proposed"})
    before = copy.deepcopy(conn.ground_truth)
    ctx = resolver.resolve_problem(conn, leetcode_id=209, allow_preparation=False)
    assert len(ctx.accepted_solution_groups) == 2  # Historical comparison contract preserved.
    assert all(g.definition_state == "LEGACY_UNSPECIFIED" for g in describe_approaches(ctx.accepted_solution_groups))
    assert conn.ground_truth == before
    assert conn.writes == []


def test_new_explicit_combined_concepts_are_not_reinterpreted_by_refresh(preparation):
    builder, _resolver, _Connection = preparation
    group = builder._build_solution_groups(COMPOSITE["patterns"], {}, COMPOSITE["approaches"])[0]
    before = copy.deepcopy(group)
    assert builder.refresh_groups_vocabulary([group]) == []
    assert group == before


def test_explicit_legacy_approach_survives_missing_canonical_vocabulary(preparation):
    builder, resolver, Connection = preparation
    from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
    raw = {"patterns": ["dfs_iterative"], "approaches": [
        {"name": "Explicit stack traversal", "patterns": ["dfs_iterative"]}]}
    conn = Connection(ground_truth=None)
    with patch.object(builder, "call_llm", return_value=raw):
        context = resolver.resolve_problem(conn, leetcode_id=209)
    group = context.accepted_solution_groups[0]
    assert group["patterns"] == ["dfs_iterative"]
    assert group["approach_definition"] == "EXPLICIT"
    assert group["approach_name"] == "Explicit stack traversal"
    assert group["required"] == []
    assert group["matchable"] is False
    stored = json.loads(conn.ground_truth["solution_groups"])
    assert len(stored) == 1 and stored[0]["matchable"] is False
    shadow = run_shadow_analysis("def traverse(items):\n    for item in items:\n        print(item)\n", [group])
    assert shadow["coverage"]["families"][0]["coverage_state"] == "UNMATCHABLE"
    assert not any(f["authoritative"] for f in shadow["authority"]["families"])


def test_preparation_response_exposes_explicit_groups(preparation):
    builder, _resolver, Connection = preparation
    from pathforge.api.routes import prepare_problem
    conn = Connection(ground_truth=None)
    with patch.object(builder, "call_llm", return_value=copy.deepcopy(COMPOSITE)), \
         patch.object(prepare_problem, "get_current_user", return_value=SimpleNamespace(user_id=7)), \
         patch.object(prepare_problem, "get_connection", return_value=conn):
        response = prepare_problem.prepare_problem_endpoint(
            prepare_problem.PrepareRequest(problem={"leetcode_id": 209}), None).model_dump()
    group = response["solution_groups"][0]
    assert set(group["patterns"]) == {"prefix_sum", "hash_map_lookup"}
    assert group["review_state"] == "UNREVIEWED"
    assert group["comparison_state"] == "NOT_EVALUATED"


def test_invalid_explicit_preparation_keeps_http_502(preparation):
    builder, _resolver, Connection = preparation
    from fastapi import HTTPException
    from pathforge.api.routes import prepare_problem
    conn = Connection(ground_truth=None)
    raw = {"patterns": ["prefix_sum"], "approaches": [{"patterns": []}]}
    with patch.object(builder, "call_llm", return_value=raw), \
         patch.object(prepare_problem, "get_current_user", return_value=SimpleNamespace(user_id=7)), \
         patch.object(prepare_problem, "get_connection", return_value=conn), \
         pytest.raises(HTTPException) as failure:
        prepare_problem.prepare_problem_endpoint(prepare_problem.PrepareRequest(problem={"leetcode_id": 209}), None)
    assert failure.value.status_code == 502
    assert conn.writes == []


def test_authority_conflict_cannot_be_presented_as_reviewed(preparation):
    from pathforge.api.services.approaches import describe_approaches
    group = {"id": "conflict", "patterns": ["prefix_sum"], "required": ["sequential_accumulation"],
             "approach_definition": "EXPLICIT", "authority_tier": "HUMAN_APPROVED", "evidence": "llm_proposed"}
    description = describe_approaches([group])[0]
    assert description.review_state == "CONFLICT"
    assert description.limitations


def test_malformed_optional_name_degrades_to_stored_group(preparation):
    from pathforge.api.services.approaches import describe_approaches
    group = {"id": "old", "patterns": ["prefix_sum"], "approach_name": {"invalid": True}}
    description = describe_approaches([group])[0]
    assert description.name == "Stored group 1"
    assert description.definition_state == "LEGACY_UNSPECIFIED"


@pytest.mark.parametrize("metadata", [
    {"family_relation": 42},
    {"family_relation": "ONE_OF", "alternative_group_id": {"invalid": True}},
    {"family_relation": "ONE_OF"},
])
def test_cached_optional_relation_metadata_degrades_without_writes(preparation, metadata):
    builder, _resolver, Connection = preparation
    from pathforge.api.routes import prepare_problem
    from pathforge.tests.test_problem_preparation_boundary import GROUND_TRUTH
    row = copy.deepcopy(GROUND_TRUTH)
    row["solution_groups"][0].update(metadata)
    conn = Connection(ground_truth=row)
    before = copy.deepcopy(conn.ground_truth)
    with patch.object(builder, "call_llm", side_effect=AssertionError("No regeneration")), \
         patch.object(prepare_problem, "get_current_user", return_value=SimpleNamespace(user_id=7)), \
         patch.object(prepare_problem, "get_connection", return_value=conn):
        response = prepare_problem.prepare_problem_endpoint(
            prepare_problem.PrepareRequest(problem={"leetcode_id": 209}), None)
    description = response.solution_groups[0]
    assert description.definition_state == "LEGACY_UNSPECIFIED"
    assert any("relationship metadata" in message for message in description.limitations)
    assert conn.ground_truth == before
    assert conn.writes == []


def test_independent_relation_remains_explicit(preparation):
    from pathforge.api.services.approaches import describe_approaches
    group = {"id": "independent", "patterns": ["prefix_sum"], "required": ["sequential_accumulation"],
             "approach_definition": "EXPLICIT", "family_relation": "INDEPENDENT"}
    assert describe_approaches([group])[0].definition_state == "EXPLICIT"


def build_engine_cases():
    """Real resolver, engines, endpoint and API serializer; only transport writes mocked."""
    with isolated_services():
        from pathforge.api.routes import analyze
        from pathforge.services import ground_truth_builder as builder
        from pathforge.tests.test_problem_preparation_boundary import MemoryConnection
        from pathforge.ast_analysis.shadow import persistence as shadow_persistence
        from src.ast_detection.semantic.shadow_detector import ShadowDetector

        def group(name, pattern, concept, **extra):
            return {"id": name, "approach_name": name, "approach_definition": "EXPLICIT",
                    "patterns": [pattern], "required": [concept], "optional": [], "excluded": [],
                    "authority_tier": "EXTERNAL_VERIFIED", "evidence": "externally_listed", **extra}

        sources = corpus_sources()
        alternatives = [group("Window", "sliding_window_fixed", "sliding_window"),
                        group("Prefix differences", "prefix_sum", "sequential_accumulation")]
        for g in alternatives:
            g.update(family_relation="ONE_OF", alternative_group_id="max_sum_alternatives")
        specifications = {
            "fixed_alternative": (sources["fw_max_sum_k"], alternatives),
            "binary_search": (sources["bs_renamed_vars"], [group("Sequence search", "binary_search_standard", "binary_search")]),
            "union_find": (sources["uf_classic"], [group("Disjoint sets", "union_find", "union_find")]),
            "lookup": (sources["hash_two_sum(self)"], [group("Complement lookup", "hash_map_lookup", "hash_lookup")]),
            "composite_partial": (sources["hash_two_sum(self)"], [
                {**group("Combined prefix and lookup", "hash_map_lookup", "hash_lookup"),
                 "patterns": ["prefix_sum", "hash_map_lookup"], "required": ["sequential_accumulation", "hash_lookup"]}]),
            "tentative": (sources["fw_max_sum_k"], [group("Proposed window", "sliding_window_fixed", "sliding_window",
                authority_tier="llm_proposed", evidence="llm_proposed")]),
            "legacy_ambiguous": (sources["fw_max_sum_k"], [{"id": "old", "patterns": ["sliding_window_fixed"],
                "required": ["sliding_window"], "authority_tier": "llm_proposed", "evidence": "llm_proposed"}]),
            "malformed_relation": (sources["fw_max_sum_k"], [group("Malformed family relation", "sliding_window_fixed", "sliding_window", family_relation=42)]),
            "incomplete_relation": (sources["fw_max_sum_k"], [group("Incomplete alternative", "sliding_window_fixed", "sliding_window", family_relation="ONE_OF")]),
            "nesting_depth": (DEPTH_CODE, [group("Proposed window", "sliding_window_fixed", "sliding_window",
                authority_tier="llm_proposed", evidence="llm_proposed")]),
            "no_problem": (DEPTH_CODE, None),
        }
        cases = {}
        for name, (code, groups) in specifications.items():
            conn = MemoryConnection(ground_truth={"patterns": sorted({p for g in groups for p in g["patterns"]}), "confidence": {}, "solution_groups": groups,
                "validation_status": "externally_listed"} if groups else None)
            with patch.object(analyze, "get_current_user", return_value=SimpleNamespace(user_id=7)), \
                 patch.object(analyze, "get_connection", return_value=conn), \
                 patch.object(analyze, "run_persistence", return_value={"submission_id": 7, "gap_signals_count": 0, "elo_updates_count": 0}), \
                 patch.object(shadow_persistence, "persist_shadow_analysis"), \
                 patch.object(ShadowDetector, "analyze_safe", return_value=None), \
                 patch.object(builder, "call_llm", side_effect=AssertionError("No generation during analysis")):
                response = analyze.analyze_endpoint(analyze.AnalyzeRequest(user_id=999, code=code,
                    problem={"leetcode_id": 209} if groups else None), None).model_dump()
            assert conn.writes == []
            cases[name] = {"code": code, "response": response}
        return cases


@pytest.fixture(scope="module")
def engine_cases():
    return build_engine_cases()


def test_full_alternative_has_no_gap_from_unused_approach(engine_cases):
    response = engine_cases["fixed_alternative"]["response"]
    assert response["match_result"]["match_result"] == "FULL_MATCH"
    assert response["match_result"]["unmatched_patterns"] == []
    assert response["submission_gap"]["gap_identified"] is False
    groups = response["problem_info"]["solution_groups"]
    assert [g["comparison_state"] for g in groups] == ["FULL_MATCH", "NO_MATCH"]
    assert groups[1]["unobserved_patterns"] == ["prefix_sum"]  # Still available per approach.


def test_partial_composite_preserves_both_requirements(engine_cases):
    response = engine_cases["composite_partial"]["response"]
    assert response["match_result"]["match_result"] == "PARTIAL_MATCH"
    group = response["problem_info"]["solution_groups"][0]
    assert group["observed_patterns"] == ["hash_map_lookup"]
    assert group["unobserved_patterns"] == ["prefix_sum"]


@pytest.mark.parametrize("case,pattern,strategy", [
    ("fixed_alternative", "sliding_window_fixed", "sliding_window"),
    ("binary_search", "binary_search_standard", "binary_search"),
    ("union_find", "union_find", "union_find"),
])
def test_supported_engines_preserved(engine_cases, case, pattern, strategy):
    response = engine_cases[case]["response"]
    assert pattern in [p["pattern_id"] for p in response["ast"]["detected_patterns"]]
    assert response["match_result"]["match_result"] == "FULL_MATCH"
    assert response["shadow_analysis"]["strategy_selection"]["submission"]["selected"] == strategy


def test_lookup_remains_technique_only(engine_cases):
    shadow = engine_cases["lookup"]["response"]["shadow_analysis"]
    assert shadow["strategy_selection"]["submission"]["selected"] is None
    assert shadow["coverage"]["families"][0]["coverage_state"] == "PROVISIONAL"


@pytest.mark.parametrize("case", ["tentative", "legacy_ambiguous", "nesting_depth"])
def test_unreviewed_or_legacy_context_is_diagnostic(engine_cases, case):
    group = engine_cases[case]["response"]["problem_info"]["solution_groups"][0]
    assert group["review_state"] == "UNREVIEWED"
    assert group["limitations"]
    if case == "legacy_ambiguous":
        assert group["definition_state"] == "LEGACY_UNSPECIFIED"


@pytest.mark.parametrize("case", ["malformed_relation", "incomplete_relation"])
def test_analysis_preserves_usable_patterns_with_bad_optional_metadata(engine_cases, case):
    response = engine_cases[case]["response"]
    assert response["match_result"]["match_result"] == "FULL_MATCH"
    group = response["problem_info"]["solution_groups"][0]
    assert group["definition_state"] == "LEGACY_UNSPECIFIED"
    assert group["observed_patterns"] == ["sliding_window_fixed"]


def test_nesting_depth_is_not_a_window(engine_cases):
    response = engine_cases["nesting_depth"]["response"]
    assert "sliding_window_fixed" not in [p["pattern_id"] for p in response["ast"]["detected_patterns"]]
    assert response["shadow_analysis"]["strategy_selection"]["submission"]["selected"] != "sliding_window"


def test_context_free_analysis_preserved(engine_cases):
    response = engine_cases["no_problem"]["response"]
    assert response["problem_info"] is None
    assert response["match_result"]["match_result"] == "NO_GROUND_TRUTH"


if __name__ == "__main__":
    print(json.dumps(build_engine_cases()))
