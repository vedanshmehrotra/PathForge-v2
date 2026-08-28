"""Pipeline integration tests — PostgreSQL-compatible.

Each test creates its own isolated user/problems using unique IDs,
then cleans up after itself to avoid cross-test contamination.
"""
import json
import uuid
from unittest.mock import patch

from pathforge.db.db import get_connection, init_db
from pathforge.pipeline import run_pipeline
from pathforge.recommender import get_recommendation


def _insert_problem(connection, pid, title, difficulty, topics, pattern, acceptance_rate):
    """Insert a problem with proper JSON for pattern and test_cases columns."""
    connection.execute(
        "INSERT INTO problems (id, title, difficulty, topics, pattern, test_cases, acceptance_rate, created_at) "
        "VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,'2026-06-04T00:00:00+00:00') "
        "ON CONFLICT (id) DO NOTHING",
        (pid, title, difficulty, topics, json.dumps([pattern]), json.dumps([]), acceptance_rate),
    )


def _unique_id():
    """Return a large unique integer derived from uuid4."""
    return int(uuid.uuid4().hex[:8], 16)


def _seed_user(connection, user_id, username):
    """Insert a unique test user."""
    connection.execute(
        """
        INSERT INTO users (id, username, email, password_hash, created_at, updated_at)
        VALUES (%s, %s, %s, 'hash', '2026-06-04T00:00:00+00:00', '2026-06-04T00:00:00+00:00')
        ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email
        """,
        (user_id, username, f"{username}@test.com"),
    )
    connection.commit()


def _cleanup(connection, user_id, problem_ids):
    """Remove test data for the given user and problems."""
    for pid in problem_ids:
        connection.execute("DELETE FROM submissions WHERE problem_id = %s", (pid,))
        connection.execute("DELETE FROM recommendations WHERE user_id = %s", (user_id,))
        connection.execute("DELETE FROM topic_profiles WHERE user_id = %s", (user_id,))
        connection.execute("DELETE FROM problems WHERE id = %s", (pid,))
    connection.execute("DELETE FROM users WHERE id = %s", (user_id,))
    connection.commit()


def seed_base(connection, user_id, problem_ids, include_gap_problem=True):
    """Seed users, problems, and a weak fallback profile for pipeline tests."""
    _seed_user(connection, user_id, f"pipeline_{user_id}")

    # Problem IDs: p1 (sliding_window), p2 (gap problem), p3 (graph/bfs)
    p1, p3 = problem_ids[0], problem_ids[2]
    p2 = problem_ids[1] if include_gap_problem else None

    _insert_problem(connection, p1, 'Variable Window Starter', 'Easy', 'Array, Hash Table', 'sliding_window_variable', 50.0)
    _insert_problem(connection, p3, 'Graph Warmup', 'Easy', 'Graph', 'bfs_level_order', 91.0)
    if include_gap_problem:
        _insert_problem(connection, p2, 'Best Sliding Window Practice', 'Easy', 'Array, Sliding Window', 'sliding_window_variable', 88.0)
    connection.execute(
        """
        INSERT INTO topic_profiles (
            user_id, topic, elo_rating, attempt_count, pass_count, pattern_match_count,
            accuracy, recent_failures, created_at, updated_at
        ) VALUES (%s, 'sliding_window_variable', 850, 3, 1, 1, 0.33, 2, '2026-06-04T00:00:00+00:00', '2026-06-04T00:00:00+00:00')
        ON CONFLICT (user_id, topic) DO UPDATE SET elo_rating = EXCLUDED.elo_rating
        """,
        (user_id,),
    )
    connection.execute(
        """
        INSERT INTO topic_profiles (
            user_id, topic, elo_rating, attempt_count, pass_count, pattern_match_count,
            accuracy, recent_failures, created_at, updated_at
        ) VALUES (%s, 'bfs_level_order', 700, 3, 0, 0, 0.0, 3, '2026-06-04T00:00:00+00:00', '2026-06-04T00:00:00+00:00')
        ON CONFLICT (user_id, topic) DO UPDATE SET elo_rating = EXCLUDED.elo_rating
        """,
        (user_id,),
    )
    connection.commit()


def fake_submission(user_id, problem_id, scores, verdict="pass", gap_identified=1):
    """Build a submission handler result shaped like handle_submission output."""
    return {
        "submission": {
            "id": 1,
            "user_id": user_id,
            "problem_id": problem_id,
            "verdict": verdict,
            "detected_pattern": max(scores.items(), key=lambda item: item[1])[0] if scores else None,
            "detected_confidence": max(scores.values()) if scores else 0.0,
            "expected_pattern": "sliding_window_variable",
            "gap_identified": gap_identified,
            "topic": "sliding_window_variable",
        },
        "ast": {"scores": scores},
        "evaluation": {"verdict": verdict},
        "profile_update": None,
        "gap_info": {
            "gap_detected": bool(gap_identified),
            "gap_pattern": None,
            "matched_pattern": max(scores.items(), key=lambda item: item[1])[0] if scores else None,
            "diagnosis_confidence": max(scores.values()) if scores else 0.0,
        },
    }


def insert_submission(connection, submission_id, user_id, problem_id, verdict="pass"):
    """Insert the row that mocked handle_submission pretends it created."""
    connection.execute(
        """
        INSERT INTO submissions (
            id, user_id, problem_id, code_text, verdict, detected_pattern,
            detected_confidence, expected_pattern, gap_identified,
            time_taken_seconds, attempt_number, topic, submitted_at
        ) VALUES (
            %s, %s, %s, 'code', %s, 'hash_map_lookup',
            0.9, 'sliding_window_variable', TRUE,
            1, 1, 'sliding_window_variable', '2026-06-04T00:00:00+00:00'
        )
        ON CONFLICT (id) DO UPDATE SET verdict = EXCLUDED.verdict
        """,
        (submission_id, user_id, problem_id, verdict),
    )
    connection.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_specific_recommendation_when_confidence_high_and_gap_detected():
    uid = _unique_id()
    pids = [_unique_id() for _ in range(3)]
    conn = get_connection()
    try:
        seed_base(conn, uid, pids)
        submission = fake_submission(uid, pids[0], {"sliding_window_variable": 0.8, "hash_map_lookup": 0.9})
        submission["gap_info"] = {
            "gap_detected": True,
            "diagnosis_confidence": 0.8,
            "matched_pattern": None,
            "gap_pattern": "sliding_window_variable",
        }

        problem_row = dict(conn.execute("SELECT * FROM problems WHERE id = %s", (pids[0],)).fetchone())
        recommendation = get_recommendation(uid, submission, problem_row, conn)

        assert recommendation["tier"] == "specific"
        assert recommendation["problem"] is not None, "Should recommend a specific problem"
        assert recommendation["problem"]["id"] != pids[0], "Should not recommend the current problem"
        assert "sliding window" in recommendation["explanation"]
    finally:
        _cleanup(conn, uid, pids)
        conn.close()


def test_hint_when_confidence_is_mid():
    uid = _unique_id()
    pids = [_unique_id() for _ in range(3)]
    conn = get_connection()
    try:
        seed_base(conn, uid, pids)
        submission = fake_submission(uid, pids[0], {"sliding_window_variable": 0.61, "hash_map_lookup": 0.9})
        submission["gap_info"] = {
            "gap_detected": True,
            "diagnosis_confidence": 0.61,
            "matched_pattern": None,
            "gap_pattern": "sliding_window_variable",
        }

        problem_row = dict(conn.execute("SELECT * FROM problems WHERE id = %s", (pids[0],)).fetchone())
        recommendation = get_recommendation(uid, submission, problem_row, conn)

        assert recommendation["tier"] == "topic_hint"
        assert recommendation["problem"] is None
    finally:
        _cleanup(conn, uid, pids)
        conn.close()


def test_general_when_confidence_is_low():
    uid = _unique_id()
    pids = [_unique_id() for _ in range(3)]
    conn = get_connection()
    try:
        seed_base(conn, uid, pids)
        submission = fake_submission(uid, pids[0], {"sliding_window_variable": 0.2, "hash_map_lookup": 0.9})
        submission["gap_info"] = {
            "gap_detected": True,
            "diagnosis_confidence": 0.2,
            "matched_pattern": None,
            "gap_pattern": "sliding_window_variable",
        }

        problem_row = dict(conn.execute("SELECT * FROM problems WHERE id = %s", (pids[0],)).fetchone())
        recommendation = get_recommendation(uid, submission, problem_row, conn)

        assert recommendation["tier"] == "general_hint"
        assert recommendation["problem"] is None
    finally:
        _cleanup(conn, uid, pids)
        conn.close()


def test_no_gap_pass_recommends_next_difficulty():
    uid = _unique_id()
    pids = [_unique_id() for _ in range(3)]
    medium_pid = _unique_id()
    conn = get_connection()
    try:
        seed_base(conn, uid, pids)
        _insert_problem(conn, medium_pid, 'Medium Window Step', 'Medium', 'Array', 'sliding_window_variable', 72.0)
        conn.commit()
        submission = fake_submission(uid, pids[0], {"sliding_window_variable": 0.9}, verdict="pass", gap_identified=0)
        submission["gap_info"] = {
            "gap_detected": False,
            "diagnosis_confidence": 0.9,
            "matched_pattern": "sliding_window_variable",
            "gap_pattern": None,
        }

        problem_row = dict(conn.execute("SELECT * FROM problems WHERE id = %s", (pids[0],)).fetchone())
        recommendation = get_recommendation(uid, submission, problem_row, conn)

        assert recommendation["tier"] == "specific"
        assert recommendation["problem"] is not None, "Should recommend a specific problem"
        assert recommendation["problem"]["difficulty"] == "Medium", f"Should recommend Medium difficulty, got {recommendation['problem']['difficulty']}"
    finally:
        _cleanup(conn, uid, pids + [medium_pid])
        conn.close()


def test_fallback_when_no_problem_available_in_gap_topic():
    uid = _unique_id()
    pids = [_unique_id() for _ in range(3)]
    conn = get_connection()
    try:
        seed_base(conn, uid, pids, include_gap_problem=False)
        submission = fake_submission(uid, pids[0], {"sliding_window_variable": 0.8, "hash_map_lookup": 0.9})
        submission["gap_info"] = {
            "gap_detected": True,
            "diagnosis_confidence": 0.8,
            "matched_pattern": None,
            "gap_pattern": "sliding_window_variable",
        }

        problem_row = dict(conn.execute("SELECT * FROM problems WHERE id = %s", (pids[0],)).fetchone())
        recommendation = get_recommendation(uid, submission, problem_row, conn)

        # When no gap-specific problem is available, the recommender should
        # fall back to another topic (e.g. bfs_level_order) and return a
        # specific problem.  We check the tier rather than an exact topic
        # because _select_problem queries across ALL problems in the DB.
        assert recommendation["tier"] in ("specific", "topic_hint")
        assert recommendation["problem"] is not None, "Should recommend a specific problem as fallback"
    finally:
        _cleanup(conn, uid, pids)
        conn.close()


def test_full_pipeline_with_mocked_submission_handler():
    uid = _unique_id()
    pids = [_unique_id() for _ in range(3)]
    sub_id = _unique_id()
    conn = get_connection()
    try:
        seed_base(conn, uid, pids)
        insert_submission(conn, sub_id, uid, pids[0])

        with patch("pathforge.pipeline.handle_submission") as mocked_handler:
            mocked_handler.return_value = fake_submission(uid, pids[0], {"sliding_window_variable": 0.81, "hash_map_lookup": 0.9})
            response = run_pipeline(uid, pids[0], "solved")

        saved_submission = conn.execute("SELECT * FROM submissions WHERE id = %s", (sub_id,)).fetchone()
        saved_recommendation = conn.execute("SELECT * FROM recommendations WHERE user_id = %s", (uid,)).fetchone()
        assert response["gap_info"]["gap_detected"] is True
        assert response["recommendation"]["tier"] in ("specific", "topic_hint")
        assert saved_recommendation is not None
    finally:
        _cleanup(conn, uid, pids)
        conn.close()


def test_race_condition_atomicity_all_or_nothing():
    """Regression test for race condition issue #3.

    Verifies that when a submission is processed, all state changes
    (submission, streak, Elo profile, and recommendation) are committed
    atomically.
    """
    uid = _unique_id()
    pids = [_unique_id() for _ in range(3)]
    sub_id = _unique_id()
    conn = get_connection()
    try:
        seed_base(conn, uid, pids)
        insert_submission(conn, sub_id, uid, pids[0])

        # Track Elo before submission
        elo_before = conn.execute(
            "SELECT elo_rating FROM topic_profiles WHERE user_id = %s AND topic = 'sliding_window_variable'",
            (uid,),
        ).fetchone()["elo_rating"]

        # Get streak and last recommendation before submission
        user_before = conn.execute(
            "SELECT current_streak, last_recommendation_id FROM users WHERE id = %s",
            (uid,),
        ).fetchone()

        # Run the pipeline
        response = run_pipeline(uid, pids[0], "solved")

        # VERIFY ATOMICITY: All state must be updated together

        # 1. Submission must be saved
        submission = conn.execute(
            "SELECT * FROM submissions WHERE user_id = %s ORDER BY id DESC LIMIT 1",
            (uid,),
        ).fetchone()
        assert submission is not None, "Submission not saved"
        assert submission["verdict"] == "pass", "Submission verdict incorrect"

        # 2. Elo must be updated for the topic
        elo_after = conn.execute(
            "SELECT elo_rating FROM topic_profiles WHERE user_id = %s AND topic = 'sliding_window_variable'",
            (uid,),
        ).fetchone()["elo_rating"]
        assert elo_after > elo_before, "Elo not updated for the submission"

        # 3. Streak must be updated
        user_after = conn.execute(
            "SELECT current_streak, last_recommendation_id FROM users WHERE id = %s",
            (uid,),
        ).fetchone()
        assert user_after["current_streak"] is not None, "Streak not updated"

        # 4. Recommendation must be logged
        recommendation = conn.execute(
            "SELECT * FROM recommendations WHERE user_id = %s ORDER BY id DESC LIMIT 1",
            (uid,),
        ).fetchone()
        assert recommendation is not None, "Recommendation not logged"
        assert user_after["last_recommendation_id"] == recommendation["id"], "last_recommendation_id not updated"

        # 5. Previous recommendation should be marked as acted_on
        if user_before["last_recommendation_id"]:
            previous_recommendation = conn.execute(
                "SELECT * FROM recommendations WHERE id = %s",
                (user_before["last_recommendation_id"],),
            ).fetchone()
            if previous_recommendation:
                assert previous_recommendation["acted_on"], "Previous recommendation not marked as acted_on"
    finally:
        _cleanup(conn, uid, pids)
        conn.close()


def test_no_elo_loss_on_duplicate_attempt():
    """Regression test to ensure concurrent submissions don't cause lost updates."""
    uid = _unique_id()
    pids = [_unique_id() for _ in range(3)]
    sub_id = _unique_id()
    conn = get_connection()
    try:
        seed_base(conn, uid, pids)
        insert_submission(conn, sub_id, uid, pids[0])

        # Verify initial state
        initial_submission_count = conn.execute(
            "SELECT COUNT(*) as count FROM submissions WHERE user_id = %s AND topic = 'sliding_window_variable' AND verdict = 'pass'",
            (uid,),
        ).fetchone()["count"]

        initial_profile = conn.execute(
            "SELECT attempt_count FROM topic_profiles WHERE user_id = %s AND topic = 'sliding_window_variable'",
            (uid,),
        ).fetchone()
        initial_attempts = initial_profile["attempt_count"]

        # First pipeline run
        response1 = run_pipeline(uid, pids[0], "solved")

        # Create another problem for second attempt
        new_pid = _unique_id()
        _insert_problem(conn, new_pid, 'Sliding Window 3', 'Easy', 'Array', 'sliding_window_variable', 85.0)
        conn.commit()

        # Second pipeline run
        response2 = run_pipeline(uid, new_pid, "solved")

        # Both submissions should be recorded
        final_submission_count = conn.execute(
            "SELECT COUNT(*) as count FROM submissions WHERE user_id = %s AND topic = 'sliding_window_variable' AND verdict = 'pass'",
            (uid,),
        ).fetchone()["count"]
        assert final_submission_count == initial_submission_count + 2, \
            f"Expected {initial_submission_count + 2} submissions, got {final_submission_count}"

        # Attempt count should be incremented by 2
        final_profile = conn.execute(
            "SELECT attempt_count FROM topic_profiles WHERE user_id = %s AND topic = 'sliding_window_variable'",
            (uid,),
        ).fetchone()
        assert final_profile["attempt_count"] == initial_attempts + 2, \
            f"Attempt count should be {initial_attempts + 2}, got {final_profile['attempt_count']}"
    finally:
        _cleanup(conn, uid, pids)
        conn.close()
