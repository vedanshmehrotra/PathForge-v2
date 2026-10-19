"""Preparation coverage is distinct from canonical strategy/scoring coverage.

Sources below express ordinary implementations, not generated diagnoses.
Run through scripts.verify_foundation.offline before importing API modules.
"""
import copy
from contextlib import ExitStack
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from pathforge.ast_engine.patterns import ALL_PATTERNS
from pathforge.tests.test_b6_product_eligibility import persistence_case, _assert_product_consequences


OBSERVATIONS = {"array_traversal", "sorting", "brute_force"}
PATTERNS = sorted(ALL_PATTERNS | OBSERVATIONS)
SOURCES = {
    "array_traversal": """def locate(values, target):
    for index in range(len(values)):
        if values[index] == target:
            return index
    return -1
""",
    "sorting": """class Solution:
    def targetIndices(self, nums: List[int], target: int) -> List[int]:
        result = []
        nums.sort()
        for index in range(len(nums)):
            if nums[index] == target:
                result.append(index)
        return result
""",
    "brute_force": """def pairs(values, target):
    result = []
    for first in range(len(values)):
        for second in range(first + 1, len(values)):
            if values[first] + values[second] == target:
                result.append((first, second))
    return result
""",
    "dfs_iterative": """def traverse(start, graph):
    stack = [start]
    visited = set()
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                stack.append(neighbor)
    return visited
""",
    "heap_top_k": """import heapq
def top_k(values, k):
    heap = []
    for value in values:
        heapq.heappush(heap, value)
        if len(heap) > k:
            heapq.heappop(heap)
    return heap
""",
    "topological_sort": """from collections import deque
def canFinish(count, prerequisites):
    graph = [[] for _ in range(count)]
    indegree = [0] * count
    for u, v in prerequisites:
        graph[v].append(u)
        indegree[u] += 1
    queue = deque([i for i in range(count) if indegree[i] == 0])
    visited = 0
    while queue:
        node = queue.popleft()
        visited += 1
        for child in graph[node]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    return visited == count
""",
    "greedy_interval": """def merge(intervals):
    intervals.sort(key=lambda item: item[0])
    merged = []
    for interval in intervals:
        if not merged or merged[-1][1] < interval[0]:
            merged.append(interval)
        else:
            merged[-1][1] = max(merged[-1][1], interval[1])
    return merged
""",
}


def proposal(patterns):
    return {"approach_contract_version": 2, "patterns": patterns,
            "approaches": [{"name": "Explicit source approach", "patterns": patterns}]}


@pytest.fixture
def services():
    from pathforge.services import ground_truth_builder as builder, problem_resolver as resolver
    from pathforge.tests.test_problem_preparation_boundary import MemoryConnection
    return builder, resolver, MemoryConnection


@pytest.mark.parametrize("pattern", PATTERNS)
def test_every_registered_pattern_survives_actual_preparation_and_cached_reload(services, pattern):
    builder, resolver, Connection = services
    connection = Connection(ground_truth=None)
    with patch.object(builder, "call_llm", return_value=proposal([pattern])) as llm:
        context = resolver.resolve_problem(connection, leetcode_id=209)
        llm.assert_called_once()
    stored = copy.deepcopy(connection.ground_truth)
    assert context.accepted_solution_groups[0]["patterns"] == [pattern]
    assert json.loads(stored["patterns"]) == [pattern]
    with patch.object(builder, "call_llm", side_effect=AssertionError("Cached: generation forbidden")):
        again = resolver.resolve_problem(connection, leetcode_id=209, allow_preparation=False)
    assert again.accepted_solution_groups == context.accepted_solution_groups
    assert connection.writes == ["ground_truth"]
    assert connection.ground_truth == stored
    assert context.accepted_solution_groups[0]["authority_tier"] == "llm_proposed"


def test_prompt_and_preparation_cover_actual_detector_ids():
    from src.ast_detection.registry import get_all_detectors
    from pathforge.llm.openrouter_client import _build_prompt
    registered = {d.pattern_id for d in get_all_detectors()}
    assert registered == set(PATTERNS)
    prompt = _build_prompt("Local description; never sent to a provider.")
    missing = sorted(p for p in registered if p not in prompt)
    assert not missing, f"Registered patterns missing from generation vocabulary: {missing}"


@pytest.mark.parametrize("pattern", sorted(SOURCES))
def test_real_pattern_overlap_is_available_without_canonical_promotion(services, pattern):
    builder, resolver, Connection = services
    from pathforge.api.services.analysis import run_analysis
    from pathforge.api.services.approaches import describe_approaches
    from pathforge.services.approach_policy import skill_comparison_gate
    from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
    connection = Connection(ground_truth=None)
    with patch.object(builder, "call_llm", return_value=proposal([pattern])):
        context = resolver.resolve_problem(connection, leetcode_id=209)
    groups = context.accepted_solution_groups
    result = run_analysis(SOURCES[pattern], accepted_solution_groups=groups)
    assert pattern in {p["pattern_id"] for p in result["ast"]["detected_patterns"]}
    assert result["match_result"]["match_result"] == "FULL_MATCH"
    description = describe_approaches(groups, result["ast"])[0].model_dump()
    assert description["pattern_evidence_state"] == "ALL_OBSERVED"
    assert description["review_state"] == "UNREVIEWED"
    assert not skill_comparison_gate(groups, result["ast"], result["match_result"])["eligible"]
    shadow = run_shadow_analysis(SOURCES[pattern], groups)
    assert shadow is not None
    assert not any(f["authoritative"] for f in shadow["authority"]["families"])
    assert shadow["strategy_selection"]["submission"]["selected"] is None
    assert groups[0]["matchable"] is False
    assert groups[0]["required"] == []


def test_unknown_partial_requirement_is_not_silently_dropped(services):
    builder, _resolver, Connection = services
    connection = Connection(ground_truth=None)
    with patch.object(builder, "call_llm", return_value=proposal(["sorting", "unimplemented_mechanism"])):
        with pytest.raises(builder.GroundTruthError):
            builder.build_ground_truth(209, "Local description", connection)
    assert connection.writes == []


def test_registry_drift_is_detected_without_expanding_rated_taxonomy():
    from pathforge.analysis_capabilities import (
        PREPARATION_PATTERN_IDS, OBSERVATION_PATTERN_IDS, PATTERN_DESCRIPTIONS, PATTERN_TO_V1_MAPPING,
    )
    from src.ast_detection.registry import get_all_detectors
    assert PREPARATION_PATTERN_IDS == {d.pattern_id for d in get_all_detectors()}
    assert OBSERVATION_PATTERN_IDS == OBSERVATIONS
    assert not (ALL_PATTERNS & OBSERVATIONS)
    assert set(PATTERN_DESCRIPTIONS) == PREPARATION_PATTERN_IDS
    assert set(PATTERN_TO_V1_MAPPING) == ALL_PATTERNS


def build_capability_cases():
    """Actual builder, preparation, cached analysis, persistence and serialization."""
    from pathforge.api.routes import analyze, prepare_problem
    from pathforge.services import ground_truth_builder as builder, persistence
    from pathforge.services import product_eligibility as b6
    from pathforge.tests.test_problem_preparation_boundary import MemoryConnection, PROBLEM
    from pathforge.ast_analysis.shadow import persistence as shadow_storage
    from src.ast_detection.semantic.shadow_detector import ShadowDetector
    import config

    class Connection(MemoryConnection):
        def execute(self, sql, params):
            if "INSERT INTO submissions" in sql:
                self.writes.append("submission")
                return SimpleNamespace(fetchone=lambda: {"id": 123})
            return super().execute(sql, params)

    cases = {}
    specifications = {name: ([name], code) for name, code in SOURCES.items()}
    specifications["sort_scan"] = (["sorting", "array_traversal"], SOURCES["sorting"])
    specifications["sort_scan_renamed"] = (["sorting", "array_traversal"], """def positions(items, wanted):
    ordered = sorted(items)
    found = []
    for position, item in enumerate(ordered):
        if item == wanted:
            found.append(position)
    return found
""")
    for name, (patterns, code) in specifications.items():
        connection = Connection(problem={**PROBLEM, "title": "Local " + name}, ground_truth=None)
        forbidden = Mock(side_effect=AssertionError("Pattern-only evidence cannot update skills"))
        with ExitStack() as stack:
            for route in (analyze, prepare_problem):
                stack.enter_context(patch.object(route, "get_current_user", return_value=SimpleNamespace(user_id=7)))
                stack.enter_context(patch.object(route, "get_connection", return_value=connection))
            for module, field, replacement in (
                (persistence, "_next_attempt_number", Mock(return_value=1)),
                (persistence, "_update_user_streak", Mock()),
                (persistence, "update_topic_profile", forbidden),
                (persistence, "get_recommendation", forbidden),
                (persistence, "_gap_engine", SimpleNamespace(compute_signals=forbidden, persist_signals=forbidden)),
                (persistence, "_elo_engine", SimpleNamespace(compute_updates=forbidden, persist_elos=forbidden)),
                (b6, "flag_enabled", Mock(return_value=False)),
                (config, "SHADOW_AUTHORITY_PRODUCT_GATING", False),
                (shadow_storage, "persist_shadow_analysis", Mock()),
                (ShadowDetector, "analyze_safe", Mock(return_value=None)),
            ):
                stack.enter_context(patch.object(module, field, replacement))
            with patch.object(builder, "call_llm", return_value=proposal(patterns)) as llm:
                prepared = prepare_problem.prepare_problem_endpoint(
                    prepare_problem.PrepareRequest(problem={"leetcode_id": 209}), None).model_dump()
                llm.assert_called_once()
            before = copy.deepcopy(connection.ground_truth)
            with patch.object(builder, "call_llm", side_effect=AssertionError("Analysis is DB-only")):
                response = analyze.analyze_endpoint(analyze.AnalyzeRequest(
                    user_id=999, code=code, problem={"leetcode_id": 209}), None).model_dump()
        assert connection.ground_truth == before
        assert connection.writes == ["ground_truth", "submission"]
        forbidden.assert_not_called()
        cases[name] = {"code": code, "expected_patterns": patterns, "preparation": prepared, "response": response}
    return cases


def test_actual_api_and_persistence_keep_pattern_only_feedback_unscored():
    for case in build_capability_cases().values():
        response = case["response"]
        assert response["match_result"]["match_result"] == "FULL_MATCH"
        approach = response["problem_info"]["solution_groups"][0]
        assert set(approach["observed_patterns"]) == set(case["expected_patterns"])
        assert approach["pattern_evidence_state"] == "ALL_OBSERVED"
        assert approach["review_state"] == "UNREVIEWED"
        assert response["persisted"]["skill_updates_skipped"] is True
        assert response["persisted"]["elo_updates_count"] == 0
        assert response["persisted"]["gap_signals_count"] == 0
        assert response["elo_updates"] == []
        assert response["shadow_analysis"]["strategy_selection"]["submission"]["selected"] is None


@pytest.mark.parametrize("metadata", [
    {"unmapped_patterns": ["unimplemented"]}, {"unmapped_patterns": []},
    {"unmapped_patterns": [None]}, {"matchable": "false"},
    {"derivation_patterns": ["prefix_sum"]}, {"approach_definition": "UNSPECIFIED"},
    {"family_relation": "ONE_OF"}, {"authority_tier": "HUMAN_APPROVED"},
])
def test_unknown_or_inconsistent_gaps_do_not_gain_pattern_comparability(metadata):
    from pathforge.api.services.approaches import describe_approaches
    from pathforge.api.services.analysis import run_analysis
    group = {"id": "g", "patterns": ["sorting"], "approach_definition": "EXPLICIT",
             "unmapped_patterns": ["sorting"], "matchable": False,
             "authority_tier": "llm_proposed", "evidence": "llm_proposed", **metadata}
    result = run_analysis(SOURCES["sorting"])
    assert describe_approaches([group], result["ast"])[0].pattern_evidence_state == "UNAVAILABLE"


def test_observations_cannot_become_rated_skills_even_with_approved_metadata():
    from pathforge.services.approach_policy import skill_comparison_gate
    from pathforge.api.services.analysis import run_analysis
    groups = [{"patterns": ["sorting"], "required": ["binary_search"],
               "approach_definition": "EXPLICIT", "authority_tier": "EXTERNAL_VERIFIED",
               "evidence": "externally_listed"}]
    result = run_analysis(SOURCES["sorting"], accepted_solution_groups=groups)
    assert result["match_result"]["match_result"] == "FULL_MATCH"
    assert skill_comparison_gate(groups, result["ast"], result["match_result"]) == {
        "eligible": False, "reason": "observational_components_not_scoring"}


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("pattern", sorted(SOURCES))
def test_real_persistence_never_scores_canonical_gaps_even_with_approved_authority(
    services, persistence_case, monkeypatch, enabled, pattern,
):
    builder, _resolver, _Connection = services
    from pathforge.api.services.analysis import run_analysis
    from pathforge.services import persistence, product_eligibility as b6
    import config
    monkeypatch.setenv(b6.FLAG_ENV_VAR, "1" if enabled else "")
    monkeypatch.setattr(config, "SHADOW_AUTHORITY_PRODUCT_GATING", False)
    groups = builder._build_solution_groups([pattern], {}, proposal([pattern])["approaches"])
    groups[0].update(authority_tier="EXTERNAL_VERIFIED", evidence="externally_listed")
    result = run_analysis(SOURCES[pattern], accepted_solution_groups=groups)
    stored = persistence.run_persistence(
        connection=persistence_case.connection, user_id=7, problem_id=209,
        problem_difficulty="Medium", code=SOURCES[pattern], ast_output=result["ast"],
        match_result=result["match_result"], groups=groups)
    _assert_product_consequences(persistence_case, stored, False)
