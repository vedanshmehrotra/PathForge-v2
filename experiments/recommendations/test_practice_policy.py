import copy
import json

import pytest

from experiments.recommendations.practice_policy import load_catalog, recommend_practice


@pytest.mark.parametrize("topic,difficulty,excluded,expected,state", [
    (None,None,[],[1,1021,704],"available"),
    ("Strings","Easy",[],[1021],"available"),
    ("Arrays","Medium",[],[198,53],"available"),
    ("Grids","Easy",[],[],"no_candidates"),
    (None,"Hard",[],[],"no_candidates"),
    ("Strings","Easy",[1021],[],"session_exhausted"),
    ("Not in catalog",None,[],[],"no_candidates"),
    (None,None,[1,1021,704],[70,3,200],"available"),
])
def test_actual_prototype_selection(topic, difficulty, excluded, expected, state):
    catalog = load_catalog()
    before = copy.deepcopy(catalog)
    result = recommend_practice(catalog, topic, difficulty, excluded)
    assert [item["leetcode_id"] for item in result["recommendations"]] == expected
    assert result["state"] == state
    assert result["session_only"] is True
    assert catalog == before
    assert not any(key in result for key in ("score", "mastery", "weak_patterns", "correctness"))


def test_history_and_analysis_are_not_accepted_inputs():
    with pytest.raises(TypeError):
        recommend_practice(load_catalog(), shadow={"outcome":"CONFIRMED"})
    with pytest.raises(TypeError):
        recommend_practice(load_catalog(), submissions=[{"verdict":"pass"}])


@pytest.mark.parametrize("mutate", [
    lambda data: data["items"].append(copy.deepcopy(data["items"][0])),
    lambda data: data["items"][0].update(problem_url="https://example.invalid/problem"),
    lambda data: data["items"][0].update(leetcode_id=True),
    lambda data: data["items"][0].update(topic=""),
])
def test_catalog_errors_fail_explicitly_without_fallback(tmp_path, mutate):
    data = load_catalog()
    mutate(data)
    source = tmp_path / "catalog.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_catalog(source)


@pytest.mark.parametrize("limit", [0,6,True])
def test_invalid_list_size_is_controlled(limit):
    with pytest.raises(ValueError):
        recommend_practice(load_catalog(), limit=limit)


def test_default_order_is_deterministic_and_deduplicated():
    catalog = load_catalog()
    catalog["items"].append(copy.deepcopy(catalog["items"][0]))
    first = recommend_practice(catalog, limit=5)
    assert first == recommend_practice(catalog, limit=5)
    ids = [item["leetcode_id"] for item in first["recommendations"]]
    assert len(ids) == len(set(ids))
