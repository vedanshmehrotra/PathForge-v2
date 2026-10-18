"""Descriptive approaches are cached knowledge, never empty matchable groups."""
import copy
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from pathforge.tests.test_problem_preparation_boundary import MemoryConnection, PROBLEM, GROUND_TRUTH
from pathforge.api.routes import analyze, prepare_problem
from pathforge.services import ground_truth_builder as builder, problem_resolver as resolver


def description(name="Enumerate all subsets", text="Extend each existing subset with the next input item."):
    return {"name": name, "description": text, "patterns": [],
            "comparison_support": "UNSUPPORTED",
            "coverage_limit": "The complete approach has no matchable requirements in the current catalogue."}


def proposal(*approaches):
    return {"approach_contract_version": 2, "patterns": sorted({p for a in approaches for p in a["patterns"]}),
            "approaches": list(approaches)}


@pytest.fixture
def routes(monkeypatch):
    for route in (analyze, prepare_problem):
        monkeypatch.setattr(route, "get_current_user", lambda request: SimpleNamespace(user_id=7))
    monkeypatch.setattr(resolver, "fetch_problem_by_slug", Mock(side_effect=AssertionError("GraphQL forbidden")))
    monkeypatch.setattr(resolver, "fetch_title_slug_by_id", Mock(side_effect=AssertionError("GraphQL forbidden")))

    def prepare(connection):
        monkeypatch.setattr(prepare_problem, "get_connection", lambda path: connection)
        return prepare_problem.prepare_problem_endpoint(prepare_problem.PrepareRequest(problem={"leetcode_id": 209}), None)

    return prepare


@pytest.mark.parametrize("item", [description(),
    description("Bracket stack", "Push opening brackets and match closing brackets against the last opening bracket."),
    description("Nesting depth", "Count opening and closing parentheses and emit only inner characters.")])
def test_description_only_preparation_is_explicitly_unsupported_and_cached(routes, item):
    conn = MemoryConnection(ground_truth=None)
    with patch.object(builder, "call_llm", return_value=proposal(item)) as llm:
        with pytest.raises(HTTPException) as raised:
            routes(conn)
        assert raised.value.status_code == 409
        detail = raised.value.detail
        assert detail["code"] == "COMPARISON_UNSUPPORTED"
        assert detail["approaches"][0]["name"] == item["name"]
        assert detail["approaches"][0]["patterns"] == []
        assert detail["approaches"][0]["comparison_support"] == "UNSUPPORTED"
        assert conn.writes == ["ground_truth"]
        saved = copy.deepcopy(conn.ground_truth)
        with pytest.raises(HTTPException) as again:
            routes(conn)
        assert again.value.detail == detail
        llm.assert_called_once()
        assert conn.ground_truth == saved
        assert conn.writes == ["ground_truth"]
    record = json.loads(saved["solution_groups"])[0]
    assert json.loads(saved["patterns"]) == []
    assert record["record_type"] == "unscored_approach"
    assert record["authority_tier"] == "llm_proposed"
    assert len(record["source_sha256"]) == 64


def test_mixed_approaches_keep_descriptions_out_of_all_matching_inputs(routes):
    raw = proposal({"name": "Dictionary", "patterns": ["hash_map_lookup"]}, description())
    conn = MemoryConnection(ground_truth=None)
    with patch.object(builder, "call_llm", return_value=raw):
        prepared = routes(conn)
    assert len(prepared.solution_groups) == 1
    assert len(prepared.unscored_approaches) == 1
    saved = copy.deepcopy(conn.ground_truth)
    conn.problem["pattern"] = ["prefix_sum"]  # Flat labels must not convert descriptions into requirements.
    with patch.object(builder, "call_llm", side_effect=AssertionError("Cached: LLM forbidden")):
        ctx = resolver.resolve_problem(conn, leetcode_id=209, allow_preparation=False)
    assert len(ctx.accepted_solution_groups) == len(ctx.unscored_approaches) == 1
    assert ctx.accepted_solution_groups[0]["patterns"] == ["hash_map_lookup"]
    assert all(g.get("record_type") != "unscored_approach" for g in ctx.accepted_solution_groups)
    assert conn.ground_truth == saved


@pytest.mark.parametrize("change", [
    {"description": " "}, {"name": ""}, {"coverage_limit": None},
    {"patterns": ["prefix_sum"]}, {"comparison_support": "MAYBE"},
])
def test_invalid_descriptions_fail_before_any_write(routes, change):
    conn = MemoryConnection(ground_truth=None)
    with patch.object(builder, "call_llm", return_value=proposal({**description(), **change})):
        with pytest.raises(HTTPException) as raised:
            routes(conn)
    assert raised.value.status_code == 502
    assert conn.writes == [] and conn.ground_truth is None


def test_empty_unversioned_and_old_invalid_rows_do_not_become_descriptions(routes):
    for raw in ({"patterns": [], "approaches": []}, {"patterns": [], "approaches": [description()]}):
        conn = MemoryConnection(ground_truth=None)
        with patch.object(builder, "call_llm", return_value=raw):
            with pytest.raises(HTTPException) as raised:
                routes(conn)
        assert raised.value.status_code == 502 and conn.writes == []
    conn = MemoryConnection(ground_truth={**GROUND_TRUTH, "patterns": [], "solution_groups": [{"patterns": []}]})
    saved = copy.deepcopy(conn.ground_truth)
    with patch.object(builder, "call_llm", side_effect=AssertionError("No regeneration")):
        with pytest.raises(HTTPException) as raised:
            routes(conn)
    assert raised.value.status_code == 409 and raised.value.detail["code"] == "GROUND_TRUTH_UNAVAILABLE"
    assert conn.writes == [] and conn.ground_truth == saved


@pytest.mark.parametrize("change", [
    {"authority_tier": "HUMAN_APPROVED"}, {"contract_version": 3}, {"patterns": ["prefix_sum"]},
    {"required": ["sliding_window"]}, {"source_sha256": None}, {"description": []},
    {"record_type": "unknown"}, {"provenance": ["human_curated"]},
])
def test_corrupt_cached_description_is_unavailable_never_repaired(routes, change):
    from pathforge.services.approach_descriptions import description_record
    record = {**description_record(description(), 0, "a" * 64), **change}
    conn = MemoryConnection(ground_truth={**GROUND_TRUTH, "patterns": [], "solution_groups": [record]})
    saved = copy.deepcopy(conn.ground_truth)
    with patch.object(builder, "call_llm", side_effect=AssertionError("No regeneration")):
        with pytest.raises(HTTPException) as raised:
            routes(conn)
    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "GROUND_TRUTH_UNAVAILABLE"
    assert conn.ground_truth == saved and conn.writes == []


def test_unsupported_analysis_stops_before_engines_and_persistence(routes, monkeypatch):
    conn = MemoryConnection(ground_truth=None)
    with patch.object(builder, "call_llm", return_value=proposal(description())):
        with pytest.raises(HTTPException):
            routes(conn)
    saved = copy.deepcopy(conn.ground_truth)
    forbidden = Mock(side_effect=AssertionError("No engine, persistence or generation"))
    monkeypatch.setattr(analyze, "get_connection", lambda path: conn)
    monkeypatch.setattr(analyze, "run_analysis", forbidden)
    monkeypatch.setattr(analyze, "run_persistence", forbidden)
    monkeypatch.setattr(builder, "call_llm", forbidden)
    with pytest.raises(HTTPException) as raised:
        analyze.analyze_endpoint(analyze.AnalyzeRequest(user_id=999, code="pass", problem={"leetcode_id": 209}), None)
    assert raised.value.status_code == 409 and raised.value.detail["code"] == "COMPARISON_UNSUPPORTED"
    forbidden.assert_not_called()
    assert conn.ground_truth == saved and conn.writes == ["ground_truth"]


def build_contract_cases():
    """Actual preparation, analysis, persistence and canonical output with I/O doubles.

    Sources are deliberately ordinary Python; parsed, never executed. Expected
    behavior concerns coverage and skill safety, not functional correctness.
    """
    from contextlib import ExitStack
    import config
    from pathforge.services import persistence, product_eligibility as b6
    from pathforge.ast_analysis.shadow import persistence as shadow_storage
    from src.ast_detection.semantic.shadow_detector import ShadowDetector
    from pathforge.tests.test_approach_family_contract import DEPTH_CODE, corpus_sources

    sources = corpus_sources()
    specs = {
        "subsets": ("""class Solution:
    def subsets(self, nums):
        output = [[]]
        for item in nums:
            added = []
            for subset in output:
                candidate = list(subset)
                candidate.append(item)
                added.append(candidate)
            output.extend(added)
        return output
""", proposal(description())),
        "brackets": ("""class Solution:
    def isValid(self, s):
        openings = []
        pairs = {')': '(', ']': '[', '}': '{'}
        for char in s:
            if char in '([{':
                openings.append(char)
            else:
                if not openings or openings.pop() != pairs[char]:
                    return False
        return len(openings) == 0
""", proposal(description("Bracket stack", "Match each closing bracket with the most recent opening bracket."))),
        "depth": (DEPTH_CODE, proposal(description("Nesting depth", "Keep characters inside each primitive using a depth counter."))),
        "prefix_product": ("""class Solution:
    def productExceptSelf(self, nums):
        n = len(nums)
        result = [1] * n
        prefix = 1
        for i in range(n):
            result[i] = prefix
            prefix *= nums[i]
        suffix = 1
        for i in range(n - 1, -1, -1):
            result[i] *= suffix
            suffix *= nums[i]
        return result
""", proposal(description("Prefix and suffix products", "Combine products before and after each position without division."))),
        "mixed": (sources["hash_two_sum(self)"], proposal(
            {"name": "Complement dictionary", "patterns": ["hash_map_lookup"]},
            description("Enumerate pairs", "Consider pairs of distinct positions and compare their sum to the target."))),
        "window": (sources["fw_max_sum_k"], proposal({"name": "Fixed window", "patterns": ["sliding_window_fixed"]})),
        "binary": (sources["bs_renamed_vars"], proposal({"name": "Sequence binary search", "patterns": ["binary_search_standard"]})),
        "dsu": (sources["uf_classic"], proposal({"name": "Disjoint sets", "patterns": ["union_find"]})),
    }

    class Connection(MemoryConnection):
        def execute(self, sql, params):
            if 'INSERT INTO submissions' in sql:
                self.writes.append('submission')
                return SimpleNamespace(fetchone=lambda: {'id': 123})
            return super().execute(sql, params)

    cases = {}
    for name, (code, raw) in specs.items():
        conn = Connection(problem={**PROBLEM, "title": name}, ground_truth=None)
        no_skill_updates = Mock(side_effect=AssertionError("Skill updates forbidden for proposed/unsupported expectations"))
        with ExitStack() as stack:
            for route in (prepare_problem, analyze):
                stack.enter_context(patch.object(route, 'get_current_user', return_value=SimpleNamespace(user_id=7)))
                stack.enter_context(patch.object(route, 'get_connection', return_value=conn))
            stack.enter_context(patch.object(builder, 'call_llm', return_value=copy.deepcopy(raw)))
            try:
                prep = prepare_problem.prepare_problem_endpoint(prepare_problem.PrepareRequest(problem={"leetcode_id": 209}), None)
                prepared, status = prep.model_dump(), 200
            except HTTPException as exc:
                assert exc.status_code == 409 and exc.detail['code'] == 'COMPARISON_UNSUPPORTED'
                prepared, status = {'detail': exc.detail}, 409
        saved = copy.deepcopy(conn.ground_truth)
        with ExitStack() as stack:
            for target, field, replacement in (
                (analyze, 'get_current_user', Mock(return_value=SimpleNamespace(user_id=7))),
                (analyze, 'get_connection', Mock(return_value=conn)),
                (persistence, '_next_attempt_number', Mock(return_value=1)),
                (persistence, '_update_user_streak', Mock()),
                (persistence, 'update_topic_profile', no_skill_updates),
                (persistence, 'get_recommendation', no_skill_updates),
                (persistence, '_gap_engine', SimpleNamespace(compute_signals=no_skill_updates, persist_signals=no_skill_updates)),
                (persistence, '_elo_engine', SimpleNamespace(compute_updates=no_skill_updates, persist_elos=no_skill_updates)),
                (b6, 'flag_enabled', Mock(return_value=False)),
                (config, 'SHADOW_AUTHORITY_PRODUCT_GATING', False),
                (shadow_storage, 'persist_shadow_analysis', Mock()),
                (ShadowDetector, 'analyze_safe', Mock(return_value=None)),
                (builder, 'call_llm', Mock(side_effect=AssertionError('Analysis is DB-only'))),
            ):
                stack.enter_context(patch.object(target, field, replacement))
            response = analyze.analyze_endpoint(analyze.AnalyzeRequest(user_id=999, code=code,
                problem={"leetcode_id": 209} if status == 200 else None), None).model_dump()
        assert response['persisted']['skill_updates_skipped'] is True
        assert response['elo_updates'] == [] and response['persisted']['gap_signals_count'] == 0
        assert conn.writes == ['ground_truth', 'submission'] and conn.ground_truth == saved
        no_skill_updates.assert_not_called()
        cases[name] = {'code': code, 'prepare': prepared, 'prepare_status': status, 'response': response}
    return cases


def test_real_engine_and_persistence_contract():
    cases = build_contract_cases()
    for name in ('subsets', 'brackets', 'depth', 'prefix_product'):
        assert cases[name]['response']['problem_info'] is None
        assert cases[name]['response']['match_result']['match_result'] == 'NO_GROUND_TRUTH'
    assert 'prefix_sum' not in {p['pattern_id'] for p in cases['prefix_product']['response']['ast']['detected_patterns']}
    for name, pattern in [('mixed', 'hash_map_lookup'), ('window', 'sliding_window_fixed'),
                          ('binary', 'binary_search_standard'), ('dsu', 'union_find')]:
        response = cases[name]['response']
        assert response['match_result']['match_result'] == 'FULL_MATCH'
        assert pattern in {p['pattern_id'] for p in response['ast']['detected_patterns']}
    mixed = cases['mixed']['response']
    assert len(mixed['problem_info']['unscored_approaches']) == 1
    assert len(mixed['problem_info']['solution_groups']) == 1
    assert len(mixed['shadow_analysis']['coverage']['families']) == 1
