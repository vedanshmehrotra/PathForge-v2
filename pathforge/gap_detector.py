MATCH_THRESHOLD = 0.55


def detect_gap(detected_patterns, expected_patterns):
    """Compare detected AST pattern scores with expected patterns and return gap metadata."""
    expected = _normalize_expected_patterns(expected_patterns)
    scores = detected_patterns or {}

    matching = [
        (pattern, float(scores.get(pattern, 0.0)))
        for pattern in expected
        if float(scores.get(pattern, 0.0)) >= MATCH_THRESHOLD
    ]
    matched_pattern = max(matching, key=lambda item: item[1])[0] if matching else None
    diagnosis_confidence = max((float(scores.get(pattern, 0.0)) for pattern in expected), default=0.0)

    return {
        "gap_detected": matched_pattern is None,
        "diagnosis_confidence": round(diagnosis_confidence, 2),
        "matched_pattern": matched_pattern,
        "gap_pattern": None if matched_pattern else (expected[0] if expected else None),
    }


def _normalize_expected_patterns(expected_patterns):
    """Return expected patterns as a clean list regardless of input shape."""
    if expected_patterns is None:
        return []
    if isinstance(expected_patterns, str):
        return [expected_patterns]
    return [pattern for pattern in expected_patterns if pattern]
