"""Tests for topic diversity and solved-problem filtering.

PostgreSQL-compatible with unique IDs per test and proper cleanup.
"""

import json
import uuid

from pathforge.db.db import get_connection
from pathforge.recommender import (
    _select_problem,
    _consecutive_recommendations_for_topic,
    _maybe_rotate_for_diversity,
    get_recommendation,
)


def _uid():
    return int(uuid.uuid4().hex[:8], 16)


def seed_db(connection, uid, pids):
    """Seed minimal data for diversity tests."""
    connection.execute(
        "INSERT INTO users (id, username, email, password_hash, created_at, updated_at) "
        "VALUES (%s, %s, %s, 'h', '2026-06-19T00:00:00Z', '2026-06-19T00:00:00Z') "
        "ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email",
        (uid, f"div_{uid}", f"div_{uid}@test.com"),
    )
    # pids[0] -> hash_map_lookup, pids[1] -> hash_map_lookup, pids[2] -> bfs_level_order
    for pid, title, difficulty, topic_str, pattern_str, acc_rate in [
        (pids[0], 'A', 'Easy', 'Array', json.dumps(["hash_map_lookup"]), 80.0),
        (pids[1], 'B', 'Easy', 'Array', json.dumps(["hash_map_lookup"]), 85.0),
        (pids[2], 'C', 'Easy', 'Graph', json.dumps(["bfs_level_order"]), 90.0),
    ]:
        connection.execute(
            "INSERT INTO problems (id, title, difficulty, topics, pattern, test_cases, acceptance_rate, created_at) "
            "VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,'2026-06-19T00:00:00Z') "
            "ON CONFLICT (id) DO NOTHING",
            (pid, title, difficulty, topic_str, pattern_str, json.dumps([]), acc_rate),
        )
    connection.execute(
        "INSERT INTO topic_profiles (user_id, topic, elo_rating, attempt_count, pass_count, pattern_match_count, accuracy, recent_failures, created_at, updated_at) "
        "VALUES (%s,'hash_map_lookup',850,0,0,0,0.0,0,'2026-06-19T00:00:00Z','2026-06-19T00:00:00Z') "
        "ON CONFLICT (user_id, topic) DO UPDATE SET elo_rating = EXCLUDED.elo_rating",
        (uid,),
    )
    connection.execute(
        "INSERT INTO topic_profiles (user_id, topic, elo_rating, attempt_count, pass_count, pattern_match_count, accuracy, recent_failures, created_at, updated_at) "
        "VALUES (%s,'bfs_level_order',700,0,0,0,0.0,0,'2026-06-19T00:00:00Z','2026-06-19T00:00:00Z') "
        "ON CONFLICT (user_id, topic) DO UPDATE SET elo_rating = EXCLUDED.elo_rating",
        (uid,),
    )
    connection.commit()


def _cleanup(connection, uid, pids):
    """Remove test data."""
    for pid in pids:
        connection.execute("DELETE FROM submissions WHERE problem_id = %s", (pid,))
    connection.execute("DELETE FROM submissions WHERE user_id = %s", (uid,))
    connection.execute("DELETE FROM recommendations WHERE user_id = %s", (uid,))
    connection.execute("DELETE FROM topic_profiles WHERE user_id = %s", (uid,))
    connection.execute("DELETE FROM users WHERE id = %s", (uid,))
    for pid in pids:
        connection.execute("DELETE FROM problems WHERE id = %s", (pid,))
    connection.commit()


def insert_submission(connection, user_id, problem_id, verdict, topic, submitted_at):
    connection.execute(
        "INSERT INTO submissions (user_id, problem_id, code_text, verdict, detected_pattern, detected_confidence, expected_pattern, target_pattern, gap_identified, diagnosis_confidence, time_taken_seconds, attempt_number, topic, submitted_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (user_id, problem_id, "code", verdict, topic, 1.0, topic, None, False, 1.0, None, 1, topic, submitted_at),
    )


def insert_recommendation(connection, user_id, topic, created_at):
    connection.execute(
        "INSERT INTO recommendations (user_id, topic, reason, confidence_tier, created_at) VALUES (%s,%s,%s,%s,%s)",
        (user_id, topic, "test", "specific", created_at),
    )


def test_solved_problem_is_excluded_by_select_problem():
    """Regression: solved problems must never be returned by _select_problem."""
    uid = _uid()
    pids = [_uid() for _ in range(3)]
    conn = get_connection()
    try:
        seed_db(conn, uid, pids)

        # User solves pids[0]
        insert_submission(conn, uid, pids[0], "pass", "hash_map_lookup", "2026-06-19T10:00:00Z")
        conn.commit()

        # pids[0] should be excluded, pids[1] or another unsolved problem should be returned
        result = _select_problem(conn, uid, "hash_map_lookup", "Easy")
        assert result is not None, "Should find unsolved problem"
        assert result["id"] != pids[0], f"Should NOT return solved problem pids[0], got {result['id']}"

        # After solving pids[1], neither of our test problems should be returned
        insert_submission(conn, uid, pids[1], "pass", "hash_map_lookup", "2026-06-19T11:00:00Z")
        conn.commit()
        result = _select_problem(conn, uid, "hash_map_lookup", "Easy")
        if result is not None:
            assert result["id"] not in (pids[0], pids[1]), \
                f"Should not return solved problems, got {result['id']}"
    finally:
        _cleanup(conn, uid, pids)
        conn.close()


def test_consecutive_recommendations_no_false_positive():
    """_consecutive_recommendations_for_topic returns False when topic differs."""
    uid = _uid()
    pids = [_uid() for _ in range(3)]
    conn = get_connection()
    try:
        seed_db(conn, uid, pids)

        insert_recommendation(conn, uid, "hash_map_lookup", "2026-06-19T10:00:00Z")
        insert_recommendation(conn, uid, "bfs_level_order", "2026-06-19T11:00:00Z")
        conn.commit()

        assert not _consecutive_recommendations_for_topic(conn, uid, "hash_map_lookup")
        assert not _consecutive_recommendations_for_topic(conn, uid, "bfs_level_order")
    finally:
        _cleanup(conn, uid, pids)
        conn.close()


def test_consecutive_recommendations_detects_loop():
    """_consecutive_recommendations_for_topic returns True when same topic in last 2."""
    uid = _uid()
    pids = [_uid() for _ in range(3)]
    conn = get_connection()
    try:
        seed_db(conn, uid, pids)

        insert_recommendation(conn, uid, "hash_map_lookup", "2026-06-19T10:00:00Z")
        insert_recommendation(conn, uid, "hash_map_lookup", "2026-06-19T11:00:00Z")
        conn.commit()

        assert _consecutive_recommendations_for_topic(conn, uid, "hash_map_lookup")
    finally:
        _cleanup(conn, uid, pids)
        conn.close()


def test_consecutive_recommendations_single_entry_returns_false():
    """With only 1 recommendation, should return False."""
    uid = _uid()
    pids = [_uid() for _ in range(3)]
    conn = get_connection()
    try:
        seed_db(conn, uid, pids)

        insert_recommendation(conn, uid, "hash_map_lookup", "2026-06-19T10:00:00Z")
        conn.commit()

        assert not _consecutive_recommendations_for_topic(conn, uid, "hash_map_lookup")
    finally:
        _cleanup(conn, uid, pids)
        conn.close()


def test_topic_diversity_rotation_on_pass():
    """get_recommendation should rotate when same topic recommended 2+ times consecutively."""
    uid = _uid()
    pids = [_uid() for _ in range(3)]
    conn = get_connection()
    try:
        seed_db(conn, uid, pids)

        insert_recommendation(conn, uid, "hash_map_lookup", "2026-06-19T10:00:00Z")
        insert_recommendation(conn, uid, "hash_map_lookup", "2026-06-19T11:00:00Z")
        conn.commit()

        problem_row = dict(conn.execute("SELECT * FROM problems WHERE id = %s", (pids[0],)).fetchone())
        submission_result = {
            "submission": {
                "problem_id": pids[0],
                "verdict": "pass",
                "detected_pattern": "hash_map_lookup",
                "topic": "hash_map_lookup",
            },
            "gap_info": {
                "gap_detected": False,
                "gap_pattern": None,
                "matched_pattern": "hash_map_lookup",
                "diagnosis_confidence": 1.0,
            },
        }

        rec = get_recommendation(uid, submission_result, problem_row, conn)

        assert rec["topic"] != "hash_map_lookup", f"Expected rotation away from hash_map_lookup, got {rec['topic']}"
        assert rec["topic"] == "bfs_level_order", f"Expected bfs_level_order, got {rec['topic']}"
        assert rec["tier"] == "specific", f"Expected specific recommendation, got {rec['tier']}"
        assert rec["problem"] is not None, "Should have a specific problem"
    finally:
        _cleanup(conn, uid, pids)
        conn.close()


def test_no_unnecessary_rotation_when_topic_diverse():
    """get_recommendation should NOT rotate when topic has NOT been over-recommended."""
    uid = _uid()
    pids = [_uid() for _ in range(3)]
    medium_pid = _uid()
    conn = get_connection()
    try:
        seed_db(conn, uid, pids)
        conn.execute(
            "INSERT INTO problems (id, title, difficulty, topics, pattern, test_cases, acceptance_rate, created_at) "
            "VALUES (%s,'M','Medium','Array',%s::jsonb,%s::jsonb,75.0,'2026-06-19T00:00:00Z') "
            "ON CONFLICT (id) DO NOTHING",
            (medium_pid, json.dumps(["hash_map_lookup"]), json.dumps([])),
        )
        conn.commit()

        insert_recommendation(conn, uid, "bfs_level_order", "2026-06-19T10:00:00Z")
        insert_recommendation(conn, uid, "hash_map_lookup", "2026-06-19T11:00:00Z")
        conn.commit()

        problem_row = dict(conn.execute("SELECT * FROM problems WHERE id = %s", (pids[0],)).fetchone())
        submission_result = {
            "submission": {
                "problem_id": pids[0],
                "verdict": "pass",
                "detected_pattern": "hash_map_lookup",
                "topic": "hash_map_lookup",
            },
            "gap_info": {
                "gap_detected": False,
                "gap_pattern": None,
                "matched_pattern": "hash_map_lookup",
                "diagnosis_confidence": 1.0,
            },
        }

        rec = get_recommendation(uid, submission_result, problem_row, conn)

        assert rec["topic"] == "hash_map_lookup", f"Expected hash_map_lookup, got {rec['topic']}"
        assert rec["tier"] == "specific", f"Expected specific, got {rec['tier']}"
    finally:
        _cleanup(conn, uid, pids + [medium_pid])
        conn.close()


def test_maybe_rotate_for_diversity_no_rotation_when_not_needed():
    """_maybe_rotate_for_diversity returns (None, False) when no rotation needed."""
    uid = _uid()
    pids = [_uid() for _ in range(3)]
    conn = get_connection()
    try:
        seed_db(conn, uid, pids)
        insert_recommendation(conn, uid, "bfs_level_order", "2026-06-19T10:00:00Z")
        conn.commit()

        gap_info = {
            "gap_detected": False,
            "diagnosis_confidence": 1.0,
            "matched_pattern": "hash_map_lookup",
        }
        problem_row = dict(conn.execute("SELECT * FROM problems WHERE id = %s", (pids[0],)).fetchone())

        rec, rotated = _maybe_rotate_for_diversity(
            conn, uid, "hash_map_lookup", gap_info, "Easy",
            1, problem_row, False, "pass",
        )
        assert not rotated
        assert rec is None
    finally:
        _cleanup(conn, uid, pids)
        conn.close()


def test_maybe_rotate_for_diversity_triggers_rotation():
    """_maybe_rotate_for_diversity rotates when topic over-recommended."""
    uid = _uid()
    pids = [_uid() for _ in range(3)]
    conn = get_connection()
    try:
        seed_db(conn, uid, pids)
        insert_recommendation(conn, uid, "hash_map_lookup", "2026-06-19T10:00:00Z")
        insert_recommendation(conn, uid, "hash_map_lookup", "2026-06-19T11:00:00Z")
        conn.commit()

        gap_info = {
            "gap_detected": False,
            "diagnosis_confidence": 1.0,
            "matched_pattern": "hash_map_lookup",
        }
        problem_row = dict(conn.execute("SELECT * FROM problems WHERE id = %s", (pids[0],)).fetchone())

        rec, rotated = _maybe_rotate_for_diversity(
            conn, uid, "hash_map_lookup", gap_info, "Easy",
            1, problem_row, False, "pass",
        )
        assert rotated, "Should rotate due to consecutive same-topic recommendations"
        assert rec is not None
        assert rec["topic"] == "bfs_level_order", f"Expected bfs_level_order, got {rec['topic']}"
        assert rec["tier"] == "specific"
    finally:
        _cleanup(conn, uid, pids)
        conn.close()
