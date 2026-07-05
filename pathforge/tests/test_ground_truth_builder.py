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
