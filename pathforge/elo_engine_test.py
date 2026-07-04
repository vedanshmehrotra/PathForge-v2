"""Unit tests for the Elo System engine."""

from pathforge.elo_engine import (
    EloEngine,
    match_result_to_score,
    _expected_score,
    _compute_k,
    _anti_drift_adjustment,
    INITIAL_ELO,
    MIN_ELO,
)


def test_match_result_to_score():
    assert match_result_to_score("FULL_MATCH") == 1.0
    assert match_result_to_score("PARTIAL_MATCH") == 0.5
    assert match_result_to_score("NO_MATCH") == 0.0
    assert match_result_to_score("UNKNOWN") == 0.0


def test_expected_score():
    e = _expected_score(1200.0, 1200.0)
    assert e == 0.5
    e2 = _expected_score(1600.0, 1200.0)
    assert e2 > 0.5
    e3 = _expected_score(800.0, 1200.0)
    assert e3 < 0.5


def test_compute_k_default():
    assert _compute_k(1200.0, 0.0, 0) == 32


def test_compute_k_gap_boost():
    assert _compute_k(1200.0, 0.7, 0) == 48


def test_compute_k_stability_reduces():
    assert _compute_k(1200.0, 0.0, 5) == 24


def test_compute_k_bounded():
    huge = _compute_k(1200.0, 1.0, 0)
    assert huge <= 64
    tiny = _compute_k(1200.0, 0.0, 20)
    assert tiny >= 8


def test_anti_drift_no_history():
    assert _anti_drift_adjustment("FULL_MATCH", []) == 1.0


def test_anti_drift_repeated_full_match():
    history = [
        {"match_result": "FULL_MATCH"},
        {"match_result": "FULL_MATCH"},
        {"match_result": "FULL_MATCH"},
        {"match_result": "FULL_MATCH"},
    ]
    adj = _anti_drift_adjustment("FULL_MATCH", history)
    assert adj < 1.0


def test_anti_drift_repeated_no_match():
    history = [
        {"match_result": "NO_MATCH"},
        {"match_result": "NO_MATCH"},
        {"match_result": "NO_MATCH"},
        {"match_result": "NO_MATCH"},
    ]
    adj = _anti_drift_adjustment("NO_MATCH", history)
    assert adj < 1.0


def test_anti_drift_saturation_floor():
    history = [
        {"match_result": "NO_MATCH"},
        {"match_result": "NO_MATCH"},
        {"match_result": "NO_MATCH"},
        {"match_result": "NO_MATCH"},
        {"match_result": "NO_MATCH"},
        {"match_result": "NO_MATCH"},
    ]
    adj = _anti_drift_adjustment("NO_MATCH", history)
    assert adj >= 0.3


def test_full_match_increases_elo():
    engine = EloEngine()
    result = engine.compute_updates(
        user_id="1",
        gap_signals=[],
        match_result={
            "match_result": "FULL_MATCH",
            "matched_groups": [0],
            "unmatched_patterns": [],
            "confidence_score": 0.9,
        },
        current_elos={"hash_map_lookup": 1200.0},
    )
    updates = result["pattern_elo_updates"]
    assert len(updates) == 1
    assert updates[0]["old_elo"] == 1200.0
    assert updates[0]["new_elo"] > 1200.0
    assert updates[0]["delta"] > 0


def test_no_match_decreases_elo():
    engine = EloEngine()
    result = engine.compute_updates(
        user_id="1",
        gap_signals=[],
        match_result={
            "match_result": "NO_MATCH",
            "matched_groups": [],
            "unmatched_patterns": ["dfs_recursive"],
            "confidence_score": 0.0,
        },
        current_elos={"dfs_recursive": 1200.0},
    )
    updates = result["pattern_elo_updates"]
    assert len(updates) >= 1
    dfs = [u for u in updates if u["pattern_id"] == "dfs_recursive"]
    assert len(dfs) >= 1
    assert dfs[0]["new_elo"] < 1200.0
    assert dfs[0]["delta"] < 0


def test_partial_match_neutral():
    engine = EloEngine()
    result = engine.compute_updates(
        user_id="1",
        gap_signals=[],
        match_result={
            "match_result": "PARTIAL_MATCH",
            "matched_groups": [0],
            "unmatched_patterns": [],
            "confidence_score": 0.5,
        },
        current_elos={"hash_map_lookup": 1200.0},
        ast_output=[{"pattern_id": "hash_map_lookup", "confidence": 0.7}],
    )
    updates = result["pattern_elo_updates"]
    assert len(updates) >= 1


def test_gap_penalty_reduces_elo_gain():
    engine = EloEngine()
    result_with_gap = engine.compute_updates(
        user_id="1",
        gap_signals=[{"pattern_id": "hash_map_lookup", "gap_strength": 0.8}],
        match_result={
            "match_result": "FULL_MATCH",
            "matched_groups": [0],
            "unmatched_patterns": [],
            "confidence_score": 0.9,
        },
        current_elos={"hash_map_lookup": 1200.0},
    )
    result_no_gap = engine.compute_updates(
        user_id="1",
        gap_signals=[],
        match_result={
            "match_result": "FULL_MATCH",
            "matched_groups": [0],
            "unmatched_patterns": [],
            "confidence_score": 0.9,
        },
        current_elos={"hash_map_lookup": 1200.0},
    )
    gain_with_gap = result_with_gap["pattern_elo_updates"][0]["delta"]
    gain_no_gap = result_no_gap["pattern_elo_updates"][0]["delta"]
    assert gain_with_gap < gain_no_gap


def test_cold_start_initializes_at_1200():
    engine = EloEngine()
    result = engine.compute_updates(
        user_id="1",
        gap_signals=[],
        match_result={
            "match_result": "FULL_MATCH",
            "matched_groups": [0],
            "unmatched_patterns": ["bfs_level_order"],
            "confidence_score": 0.9,
        },
        current_elos=None,
    )
    updates = result["pattern_elo_updates"]
    bfs = [u for u in updates if u["pattern_id"] == "bfs_level_order"]
    assert len(bfs) >= 1
    assert bfs[0]["old_elo"] == INITIAL_ELO


def test_output_structure():
    engine = EloEngine()
    result = engine.compute_updates(
        user_id="42",
        gap_signals=[],
        match_result={
            "match_result": "FULL_MATCH",
            "matched_groups": [0],
            "unmatched_patterns": [],
            "confidence_score": 0.9,
        },
        current_elos={"hash_map_lookup": 1200.0},
    )
    required_keys = {"user_id", "pattern_elo_updates", "global_summary"}
    assert set(result.keys()) == required_keys
    required_summary_keys = {"average_elo_change", "strongest_improvement_patterns", "weakest_patterns"}
    assert set(result["global_summary"].keys()) == required_summary_keys
    update_keys = {"pattern_id", "old_elo", "new_elo", "delta", "confidence_weight"}
    for update in result["pattern_elo_updates"]:
        assert set(update.keys()) == update_keys


def test_elo_never_below_min():
    engine = EloEngine()
    result = engine.compute_updates(
        user_id="1",
        gap_signals=[{"pattern_id": "dfs_recursive", "gap_strength": 0.9}],
        match_result={
            "match_result": "NO_MATCH",
            "matched_groups": [],
            "unmatched_patterns": ["dfs_recursive"],
            "confidence_score": 0.0,
        },
        current_elos={"dfs_recursive": 400.0},
    )
    for u in result["pattern_elo_updates"]:
        assert u["new_elo"] >= MIN_ELO


def test_conflicting_signals_handled():
    engine = EloEngine()
    result = engine.compute_updates(
        user_id="1",
        gap_signals=[{"pattern_id": "hash_map_lookup", "gap_strength": 0.8}],
        match_result={
            "match_result": "NO_MATCH",
            "matched_groups": [],
            "unmatched_patterns": ["hash_map_lookup"],
            "confidence_score": 0.0,
        },
        ast_output=[{"pattern_id": "hash_map_lookup", "confidence": 0.75}],
        current_elos={"hash_map_lookup": 1200.0},
    )
    updates = result["pattern_elo_updates"]
    hm = [u for u in updates if u["pattern_id"] == "hash_map_lookup"]
    assert len(hm) >= 1
    assert hm[0]["confidence_weight"] > 0.3


def test_persist_elos(monkeypatch):
    class FakeConnection:
        def __init__(self):
            self.executed = []

        def execute(self, sql, params):
            self.executed.append((sql, params))

    conn = FakeConnection()
    engine = EloEngine()
    elo_output = {
        "user_id": "1",
        "pattern_elo_updates": [
            {
                "pattern_id": "hash_map_lookup",
                "old_elo": 1200.0,
                "new_elo": 1232.0,
                "delta": 32.0,
                "confidence_weight": 1.0,
            },
        ],
        "global_summary": {
            "average_elo_change": 32.0,
            "strongest_improvement_patterns": ["hash_map_lookup"],
            "weakest_patterns": [],
        },
    }
    engine.persist_elos(conn, user_id=1, elo_output=elo_output)
    assert len(conn.executed) == 1
    sql = conn.executed[0][0]
    assert "INSERT INTO user_pattern_elo" in sql
    assert "ON CONFLICT" in sql
    params = conn.executed[0][1]
    assert params[0] == 1
    assert params[1] == "hash_map_lookup"
    assert params[2] == 1232.0


def test_ast_reinforcement_prevents_collapse():
    engine = EloEngine()
    result = engine.compute_updates(
        user_id="1",
        gap_signals=[],
        match_result={
            "match_result": "NO_MATCH",
            "matched_groups": [],
            "unmatched_patterns": [],
            "confidence_score": 0.0,
        },
        ast_output=[{"pattern_id": "hash_map_lookup", "confidence": 0.85}],
        current_elos={"hash_map_lookup": 1200.0},
    )
    hm = [u for u in result["pattern_elo_updates"] if u["pattern_id"] == "hash_map_lookup"]
    assert len(hm) >= 1
    assert hm[0]["new_elo"] > 1100.0


def test_no_gap_signals_still_updates():
    engine = EloEngine()
    result = engine.compute_updates(
        user_id="1",
        gap_signals=[],
        match_result={
            "match_result": "NO_MATCH",
            "matched_groups": [],
            "unmatched_patterns": ["topological_sort"],
            "confidence_score": 0.0,
        },
        current_elos={"topological_sort": 1200.0},
    )
    updates = result["pattern_elo_updates"]
    ts = [u for u in updates if u["pattern_id"] == "topological_sort"]
    assert len(ts) >= 1
    assert ts[0]["delta"] < 0
