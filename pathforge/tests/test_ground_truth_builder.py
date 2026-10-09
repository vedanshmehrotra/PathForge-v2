import json
from unittest.mock import Mock

import pytest

from pathforge.services import ground_truth_builder as builder
from pathforge.services.ground_truth_builder import _normalize_patterns, _clamp_confidence


def test_normalize_patterns_canonical():
    patterns = ["hash_map_lookup", "prefix_sum"]
    confidence = {"hash_map_lookup": 0.9}
    canonical, filtered = _normalize_patterns(patterns, confidence)
    assert sorted(canonical) == sorted(["hash_map_lookup", "prefix_sum"])
    assert filtered["hash_map_lookup"] == 0.9


def test_normalize_patterns_non_canonical_removed():
    patterns = ["hash_map_lookup", "made_up_pattern"]
    confidence = {}
    canonical, filtered = _normalize_patterns(patterns, confidence)
    assert canonical == ["hash_map_lookup"]


def test_normalize_patterns_case_and_hyphen():
    patterns = ["Hash-Map-Lookup", "PREFIX_SUM"]
    confidence = {}
    canonical, filtered = _normalize_patterns(patterns, confidence)
    assert "hash_map_lookup" in canonical
    assert "prefix_sum" in canonical


def test_normalize_patterns_discards_all_invalid():
    patterns = ["foo", "bar", "baz"]
    canonical, filtered = _normalize_patterns(patterns, confidence={})
    assert canonical == []


def test_clamp_confidence_valid():
    assert _clamp_confidence(0.9) == 0.9
    assert _clamp_confidence(1.5) == 1.0
    assert _clamp_confidence(-0.5) == 0.0


def test_clamp_confidence_invalid():
    assert _clamp_confidence("abc") == 0.5
    assert _clamp_confidence(None) == 0.5


@pytest.fixture
def generated(monkeypatch):
    connection = Mock(spec=["execute", "commit", "rollback"])
    llm = Mock()
    store = Mock(wraps=builder._store_ground_truth)
    monkeypatch.setattr(builder, "call_llm", llm)
    monkeypatch.setattr(builder, "_store_ground_truth", store)
    return connection, llm, store


@pytest.mark.parametrize("patterns", [[], ["not_a_registered_pattern"]], ids=["empty", "unrecognized"])
def test_build_rejects_empty_normalized_output_before_storage(generated, patterns):
    connection, llm, store = generated
    llm.return_value = {"patterns": patterns, "confidence": {}}
    with pytest.raises(builder.GroundTruthError):
        builder.build_ground_truth(209, "Fixture description", connection)
    store.assert_not_called()
    connection.execute.assert_not_called()
    connection.commit.assert_not_called()


@pytest.mark.parametrize("output", [
    None, [], "not an object", {},
    {"patterns": None}, {"patterns": "prefix_sum"}, {"patterns": [None]},
    {"patterns": [42]}, {"patterns": [{}]}, {"patterns": [["prefix_sum"]]},
    {"patterns": ["prefix_sum", None]},
    {"patterns": ["prefix_sum"], "confidence": None},
    {"patterns": ["prefix_sum"], "confidence": []},
    {"patterns": ["prefix_sum"], "confidence": {1: 0.9}},
    {"patterns": ["prefix_sum"], "approaches": "not a list"},
    {"patterns": ["prefix_sum"], "approaches": {}},
    {"patterns": ["prefix_sum"], "approaches": [None]},
    {"patterns": ["prefix_sum"], "approaches": [{"patterns": "prefix_sum"}]},
    {"patterns": ["prefix_sum"], "approaches": [{"patterns": [{}]}]},
    {"patterns": ["prefix_sum"], "approaches": [{"confidence": []}]},
    {"patterns": ["prefix_sum"], "approaches": [{"confidence": {"prefix_sum": []}}]},
    {"patterns": ["prefix_sum"], "approaches": [{"confidence": {"prefix_sum": "not a score"}}]},
    {"patterns": ["prefix_sum"], "approaches": [{"name": {}}]},
    {"patterns": ["prefix_sum"], "approaches": [{"patterns": ["prefix_sum"], "confidence": {"prefix_sum": float("nan")}}]},
    {"patterns": ["prefix_sum"], "extra": object()},
])
def test_build_rejects_malformed_response_before_storage(generated, output):
    connection, llm, store = generated
    llm.return_value = output
    with pytest.raises(builder.GroundTruthError):
        builder.build_ground_truth(209, "Fixture description", connection)
    store.assert_not_called()
    connection.execute.assert_not_called()


def test_valid_output_preserves_normalization_and_inferred_authority(generated):
    connection, llm, store = generated
    llm.return_value = {
        "patterns": ["PREFIX_SUM", "prefix_sum", "not_a_registered_pattern"],
        "confidence": {"prefix_sum": 1.3},
    }
    assert builder.build_ground_truth(209, "Fixture description", connection) == ["prefix_sum"]
    store.assert_called_once()
    connection.execute.assert_called_once()
    sql, params = connection.execute.call_args.args
    assert "INSERT INTO problem_ground_truth" in sql
    assert json.loads(params[1]) == ["prefix_sum"]
    assert json.loads(params[2]) == {"prefix_sum": 1.0}
    group = json.loads(params[3])[0]
    assert group["required"] == ["sequential_accumulation"]
    assert group["authority_tier"] == group["evidence"] == "llm_proposed"
    connection.commit.assert_not_called()


@pytest.mark.parametrize("approaches", [None, []])
def test_optional_confidence_and_approaches_preserve_single_group_fallback(generated, approaches):
    connection, llm, _store = generated
    llm.return_value = {"patterns": ["prefix_sum"], "approaches": approaches}
    builder.build_ground_truth(209, "Fixture description", connection)
    params = connection.execute.call_args.args[1]
    assert json.loads(params[2]) == {}
    assert json.loads(params[3])[0]["patterns"] == ["prefix_sum"]


def test_valid_explicit_approaches_preserve_group_construction(generated):
    connection, llm, _store = generated
    llm.return_value = {
        "patterns": ["binary_search_standard", "two_pointers_opposite"],
        "approaches": [
            {"name": "search", "patterns": ["binary_search_standard"]},
            {"name": "pointers", "patterns": ["two_pointers_opposite"]},
        ],
    }
    builder.build_ground_truth(209, "Fixture description", connection)
    groups = json.loads(connection.execute.call_args.args[1][3])
    assert [group["required"] for group in groups] == [["binary_search"], ["two_pointers_opposite"]]
    assert all(group["authority_tier"] == "llm_proposed" for group in groups)


def test_approaches_inherit_existing_normalized_confidence_fallback(generated):
    connection, llm, _store = generated
    llm.return_value = {
        "patterns": ["binary_search_standard", "two_pointers_opposite"],
        "confidence": {"binary_search_standard": "bad score", "two_pointers_opposite": 1.3},
        "approaches": [
            {"patterns": ["binary_search_standard"]},
            {"patterns": ["two_pointers_opposite"]},
        ],
    }
    builder.build_ground_truth(209, "Fixture description", connection)
    groups = json.loads(connection.execute.call_args.args[1][3])
    assert groups[0]["confidence"] == {"binary_search_standard": 0.5}
    assert groups[1]["confidence"] == {"two_pointers_opposite": 1.0}


def test_missing_shadow_vocabulary_does_not_invalidate_legacy_ground_truth(generated):
    connection, llm, _store = generated
    llm.return_value = {"patterns": ["dfs_iterative"], "confidence": {}}
    assert builder.build_ground_truth(209, "Fixture description", connection) == ["dfs_iterative"]
    params = connection.execute.call_args.args[1]
    assert json.loads(params[1]) == ["dfs_iterative"]
    assert json.loads(params[3]) == []


def test_storage_rejects_empty_flat_patterns_before_sql():
    connection = Mock(spec=["execute"])
    with pytest.raises(builder.GroundTruthError):
        builder._store_ground_truth(connection, 209, [], {})
    connection.execute.assert_not_called()
