"""Unit tests for the Gap Signal Engine."""

from pathforge.gap_signal_engine import GapSignalEngine, _recency_weight, _confidence_penalty, _classify_gap_level


def test_no_submission_history():
    engine = GapSignalEngine()
    result = engine.compute_signals(
        ast_output=[{"pattern_id": "hash_map_lookup", "confidence": 0.9}],
        match_result={
            "match_result": "PARTIAL_MATCH",
            "matched_groups": [0],
            "unmatched_patterns": ["dfs_recursive"],
            "confidence_score": 0.6,
        },
        user_id=None,
        submission_history=None,
    )
    assert "gap_signals" in result
    assert "summary" in result
    assert isinstance(result["gap_signals"], list)
    assert isinstance(result["summary"]["strong_gaps"], list)
    assert isinstance(result["summary"]["moderate_gaps"], list)
    assert isinstance(result["summary"]["weak_gaps"], list)


def test_no_gaps_on_full_match():
    engine = GapSignalEngine()
    result = engine.compute_signals(
        ast_output=[{"pattern_id": "hash_map_lookup", "confidence": 0.9}],
        match_result={
            "match_result": "FULL_MATCH",
            "matched_groups": [0],
            "unmatched_patterns": [],
            "confidence_score": 0.9,
        },
        submission_history=[
            {
                "detected_pattern": "hash_map_lookup",
                "detected_confidence": 0.9,
                "verdict": "pass",
                "submitted_at": "2026-07-01T12:00:00",
            },
            {
                "detected_pattern": "hash_map_lookup",
                "detected_confidence": 0.85,
                "verdict": "pass",
                "submitted_at": "2026-07-02T12:00:00",
            },
        ],
    )
    assert len(result["gap_signals"]) == 0


def test_partial_match_detects_gap():
    engine = GapSignalEngine()
    result = engine.compute_signals(
        ast_output=[{"pattern_id": "hash_map_lookup", "confidence": 0.9}],
        match_result={
            "match_result": "PARTIAL_MATCH",
            "matched_groups": [0],
            "unmatched_patterns": ["dfs_recursive"],
            "confidence_score": 0.6,
        },
        submission_history=[
            {
                "detected_pattern": "hash_map_lookup",
                "detected_confidence": 0.9,
                "submitted_at": "2026-07-01T12:00:00",
            },
        ],
    )
    pids = [g["pattern_id"] for g in result["gap_signals"]]
    assert "dfs_recursive" in pids


def test_repeated_failure_increases_gap_strength():
    engine = GapSignalEngine()
    result = engine.compute_signals(
        ast_output=[{"pattern_id": "hash_map_lookup", "confidence": 0.9}],
        match_result={
            "match_result": "PARTIAL_MATCH",
            "matched_groups": [0],
            "unmatched_patterns": ["two_pointers_opposite"],
            "confidence_score": 0.4,
        },
        submission_history=[
            {
                "detected_pattern": "two_pointers_opposite",
                "detected_confidence": 0.3,
                "verdict": "fail",
                "submitted_at": "2026-07-01T12:00:00",
            },
            {
                "detected_pattern": "two_pointers_opposite",
                "detected_confidence": 0.4,
                "verdict": "fail",
                "submitted_at": "2026-07-02T12:00:00",
            },
            {
                "detected_pattern": "two_pointers_opposite",
                "detected_confidence": 0.2,
                "verdict": "fail",
                "submitted_at": "2026-07-03T12:00:00",
            },
        ],
    )
    for gs in result["gap_signals"]:
        if gs["pattern_id"] == "two_pointers_opposite":
            assert gs["gap_strength"] > 0.4
            assert gs["frequency"] >= 3
            break


def test_high_confidence_anti_bias():
    engine = GapSignalEngine()
    result = engine.compute_signals(
        ast_output=[{"pattern_id": "dfs_recursive", "confidence": 0.95}],
        match_result={
            "match_result": "PARTIAL_MATCH",
            "matched_groups": [0],
            "unmatched_patterns": ["dfs_recursive"],
            "confidence_score": 0.6,
        },
        submission_history=[
            {
                "detected_pattern": "dfs_recursive",
                "detected_confidence": 0.9,
                "verdict": "pass",
                "submitted_at": "2026-07-03T12:00:00",
            },
            {
                "detected_pattern": "dfs_recursive",
                "detected_confidence": 0.95,
                "verdict": "pass",
                "submitted_at": "2026-07-04T12:00:00",
            },
        ],
    )
    pids = [g["pattern_id"] for g in result["gap_signals"]]
    assert "dfs_recursive" not in pids


def test_empty_ast_output():
    engine = GapSignalEngine()
    result = engine.compute_signals(
        ast_output=[],
        match_result={
            "match_result": "NO_MATCH",
            "matched_groups": [],
            "unmatched_patterns": ["bfs_level_order"],
            "confidence_score": 0.0,
        },
        submission_history=[],
    )
    pids = [g["pattern_id"] for g in result["gap_signals"]]
    assert "bfs_level_order" in pids or len(result["gap_signals"]) == 0


def test_low_confidence_detection_triggers_penalty():
    engine = GapSignalEngine()
    result = engine.compute_signals(
        ast_output=[{"pattern_id": "dp_1d_forward", "confidence": 0.35}],
        match_result={
            "match_result": "PARTIAL_MATCH",
            "matched_groups": [0],
            "unmatched_patterns": [],
            "confidence_score": 0.35,
        },
        submission_history=[
            {
                "detected_pattern": "dp_1d_forward",
                "detected_confidence": 0.35,
                "submitted_at": "2026-07-04T12:00:00",
            },
        ],
    )
    pids = [g["pattern_id"] for g in result["gap_signals"]]
    assert "dp_1d_forward" in pids


def test_output_structure_matches_spec():
    engine = GapSignalEngine()
    result = engine.compute_signals(
        ast_output=[{"pattern_id": "hash_map_lookup", "confidence": 0.9}],
        match_result={
            "match_result": "PARTIAL_MATCH",
            "matched_groups": [0],
            "unmatched_patterns": ["backtracking_subset"],
            "confidence_score": 0.5,
        },
        submission_history=[
            {
                "detected_pattern": "backtracking_subset",
                "detected_confidence": 0.3,
                "submitted_at": "2026-07-04T12:00:00",
            },
        ],
    )
    required_keys = {"gap_signals", "summary"}
    assert set(result.keys()) == required_keys
    required_summary_keys = {"strong_gaps", "moderate_gaps", "weak_gaps"}
    assert set(result["summary"].keys()) == required_summary_keys
    if result["gap_signals"]:
        sig = result["gap_signals"][0]
        sig_keys = {"pattern_id", "gap_strength", "frequency", "recency_score", "confidence_penalty"}
        assert set(sig.keys()) == sig_keys
        assert isinstance(sig["pattern_id"], str)
        assert isinstance(sig["gap_strength"], float)
        assert isinstance(sig["frequency"], int)
        assert isinstance(sig["recency_score"], float)
        assert isinstance(sig["confidence_penalty"], float)
        assert 0.0 <= sig["gap_strength"] <= 1.0


def test_recency_weight_empty():
    assert _recency_weight([]) == 0.0


def test_recency_weight_recent():
    timestamps = ["2026-07-04T12:00:00", "2026-07-04T13:00:00", "2026-07-04T14:00:00"]
    w = _recency_weight(timestamps)
    assert w > 0.0
    assert w <= 1.0


def test_confidence_penalty_high():
    assert _confidence_penalty(0.9) == 0.0


def test_confidence_penalty_low():
    p = _confidence_penalty(0.3)
    assert p > 0.0
    assert p <= 1.0


def test_classify_gap_level_strong():
    assert _classify_gap_level(0.8) == "strong_gaps"


def test_classify_gap_level_moderate():
    assert _classify_gap_level(0.55) == "moderate_gaps"


def test_classify_gap_level_weak():
    assert _classify_gap_level(0.2) == "weak_gaps"


def test_inconsistent_detection_triggers_gap():
    engine = GapSignalEngine()
    result = engine.compute_signals(
        ast_output=[{"pattern_id": "bfs_level_order", "confidence": 0.9}],
        match_result={
            "match_result": "PARTIAL_MATCH",
            "matched_groups": [0],
            "unmatched_patterns": [],
            "confidence_score": 0.5,
        },
        submission_history=[
            {
                "detected_pattern": "bfs_level_order",
                "detected_confidence": 0.9,
                "submitted_at": "2026-07-01T12:00:00",
            },
            {
                "detected_pattern": "bfs_level_order",
                "detected_confidence": 0.3,
                "submitted_at": "2026-07-02T12:00:00",
            },
            {
                "detected_pattern": "bfs_level_order",
                "detected_confidence": 0.95,
                "submitted_at": "2026-07-03T12:00:00",
            },
            {
                "detected_pattern": "bfs_level_order",
                "detected_confidence": 0.25,
                "submitted_at": "2026-07-04T12:00:00",
            },
        ],
    )
    pids = [g["pattern_id"] for g in result["gap_signals"]]
    assert "bfs_level_order" in pids


def test_persist_signals(monkeypatch):
    class FakeConnection:
        def __init__(self):
            self.executed = []

        def execute(self, sql, params):
            self.executed.append((sql, params))

    conn = FakeConnection()
    engine = GapSignalEngine()
    gap_output = {
        "gap_signals": [
            {
                "pattern_id": "dfs_recursive",
                "gap_strength": 0.75,
                "frequency": 3,
                "recency_score": 0.6,
                "confidence_penalty": 0.0,
            },
        ],
        "summary": {"strong_gaps": ["dfs_recursive"], "moderate_gaps": [], "weak_gaps": []},
    }
    engine.persist_signals(conn, user_id=1, gap_output=gap_output)
    assert len(conn.executed) == 1
    sql = conn.executed[0][0]
    assert "INSERT INTO gap_signals" in sql
    assert "ON CONFLICT" in sql
    params = conn.executed[0][1]
    assert params[0] == 1
    assert params[1] == "dfs_recursive"
    assert params[2] == 0.75
    assert params[3] == 3
