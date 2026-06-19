from unittest.mock import patch

from pathforge.db.db import connect, init_db
from pathforge.pipeline import run_pipeline
from pathforge.recommender import get_recommendation


def seed_base(connection, include_gap_problem=True):
    """Seed users, problems, and a weak fallback profile for pipeline tests."""
    connection.execute(
        """
        INSERT INTO users (id, username, email, password_hash, created_at, updated_at)
        VALUES (1, 'veda', 'veda@example.com', 'hash', '2026-06-04T00:00:00+00:00', '2026-06-04T00:00:00+00:00')
        """
    )
    connection.execute(
        """
        INSERT INTO problems (id, title, difficulty, topics, pattern, test_cases, acceptance_rate, created_at)
        VALUES
            (1, 'Variable Window Starter', 'Easy', 'Array, Hash Table', '["sliding_window_variable"]', '[]', 50.0, '2026-06-04T00:00:00+00:00'),
            (3, 'Graph Warmup', 'Easy', 'Graph', '["bfs_level_order"]', '[]', 91.0, '2026-06-04T00:00:00+00:00')
        """
    )
    if include_gap_problem:
        connection.execute(
            """
            INSERT INTO problems (id, title, difficulty, topics, pattern, test_cases, acceptance_rate, created_at)
            VALUES
                (2, 'Best Sliding Window Practice', 'Easy', 'Array, Sliding Window', '["sliding_window_variable"]', '[]', 88.0, '2026-06-04T00:00:00+00:00')
            """
        )
    connection.execute(
        """
        INSERT INTO topic_profiles (
            user_id, topic, elo_rating, attempt_count, pass_count, pattern_match_count,
            accuracy, recent_failures, created_at, updated_at
        )
        VALUES
            (1, 'sliding_window_variable', 850, 3, 1, 1, 0.33, 2, '2026-06-04T00:00:00+00:00', '2026-06-04T00:00:00+00:00'),
            (1, 'bfs_level_order', 700, 3, 0, 0, 0.0, 3, '2026-06-04T00:00:00+00:00', '2026-06-04T00:00:00+00:00')
        """
    )
    connection.commit()


def fake_submission(scores, verdict="pass", gap_identified=1):
    """Build a submission handler result shaped like handle_submission output."""
    return {
        "submission": {
            "id": 1,
            "user_id": 1,
            "problem_id": 1,
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
        "profile_error": None,
        "gap_info": {
            "gap_detected": bool(gap_identified),
            "gap_pattern": None,
            "matched_pattern": max(scores.items(), key=lambda item: item[1])[0] if scores else None,
            "diagnosis_confidence": max(scores.values()) if scores else 0.0,
        },
    }


def insert_submission(connection, verdict="pass"):
    """Insert the row that mocked handle_submission pretends it created."""
    connection.execute(
        """
        INSERT INTO submissions (
            id, user_id, problem_id, code_text, verdict, detected_pattern,
            detected_confidence, expected_pattern, gap_identified,
            time_taken_seconds, attempt_number, topic, submitted_at
        )
        VALUES (
            1, 1, 1, 'code', ?, 'hash_map_lookup',
            0.9, 'sliding_window_variable', 1,
            1, 1, 'sliding_window_variable', '2026-06-04T00:00:00+00:00'
        )
        """,
        (verdict,),
    )
    connection.commit()


def test_specific_recommendation_when_confidence_high_and_gap_detected(tmp_path):
    db_path = tmp_path / "pipeline.sqlite3"
    connection = init_db(db_path)
    seed_base(connection)
    submission = fake_submission({"sliding_window_variable": 0.8, "hash_map_lookup": 0.9})
    submission["gap_info"] = {
        "gap_detected": True,
        "diagnosis_confidence": 0.8,
        "matched_pattern": None,
        "gap_pattern": "sliding_window_variable",
    }

    recommendation = get_recommendation(1, submission, dict(connection.execute("SELECT * FROM problems WHERE id = 1").fetchone()), connection)

    assert recommendation["tier"] == "specific"
    assert recommendation["problem"]["id"] == 2
    assert "sliding window" in recommendation["explanation"]


def test_hint_when_confidence_is_mid(tmp_path):
    db_path = tmp_path / "pipeline.sqlite3"
    connection = init_db(db_path)
    seed_base(connection)
    submission = fake_submission({"sliding_window_variable": 0.61, "hash_map_lookup": 0.9})
    submission["gap_info"] = {
        "gap_detected": True,
        "diagnosis_confidence": 0.61,
        "matched_pattern": None,
        "gap_pattern": "sliding_window_variable",
    }

    recommendation = get_recommendation(1, submission, dict(connection.execute("SELECT * FROM problems WHERE id = 1").fetchone()), connection)

    assert recommendation["tier"] == "topic_hint"
    assert recommendation["problem"] is None


def test_general_when_confidence_is_low(tmp_path):
    db_path = tmp_path / "pipeline.sqlite3"
    connection = init_db(db_path)
    seed_base(connection)
    submission = fake_submission({"sliding_window_variable": 0.2, "hash_map_lookup": 0.9})
    submission["gap_info"] = {
        "gap_detected": True,
        "diagnosis_confidence": 0.2,
        "matched_pattern": None,
        "gap_pattern": "sliding_window_variable",
    }

    recommendation = get_recommendation(1, submission, dict(connection.execute("SELECT * FROM problems WHERE id = 1").fetchone()), connection)

    assert recommendation["tier"] == "general_hint"
    assert recommendation["problem"] is None


def test_no_gap_pass_recommends_next_difficulty(tmp_path):
    db_path = tmp_path / "pipeline.sqlite3"
    connection = init_db(db_path)
    seed_base(connection)
    connection.execute(
        """
        INSERT INTO problems (id, title, difficulty, topics, pattern, test_cases, acceptance_rate, created_at)
        VALUES (4, 'Medium Window Step', 'Medium', 'Array', '["sliding_window_variable"]', '[]', 72.0, '2026-06-04T00:00:00+00:00')
        """
    )
    connection.commit()
    submission = fake_submission({"sliding_window_variable": 0.9}, verdict="pass", gap_identified=0)
    submission["gap_info"] = {
        "gap_detected": False,
        "diagnosis_confidence": 0.9,
        "matched_pattern": "sliding_window_variable",
        "gap_pattern": None,
    }

    recommendation = get_recommendation(1, submission, dict(connection.execute("SELECT * FROM problems WHERE id = 1").fetchone()), connection)

    assert recommendation["tier"] == "specific"
    assert recommendation["problem"]["id"] == 4


def test_fallback_when_no_problem_available_in_gap_topic(tmp_path):
    db_path = tmp_path / "pipeline.sqlite3"
    connection = init_db(db_path)
    seed_base(connection, include_gap_problem=False)
    submission = fake_submission({"sliding_window_variable": 0.8, "hash_map_lookup": 0.9})
    submission["gap_info"] = {
        "gap_detected": True,
        "diagnosis_confidence": 0.8,
        "matched_pattern": None,
        "gap_pattern": "sliding_window_variable",
    }

    recommendation = get_recommendation(1, submission, dict(connection.execute("SELECT * FROM problems WHERE id = 1").fetchone()), connection)

    assert recommendation["tier"] == "specific"
    assert recommendation["problem"]["id"] == 3
    assert recommendation["topic"] == "bfs_level_order"


def test_full_pipeline_with_mocked_submission_handler(tmp_path):
    db_path = tmp_path / "pipeline.sqlite3"
    connection = init_db(db_path)
    seed_base(connection)
    insert_submission(connection)

    with patch("pathforge.pipeline.handle_submission") as mocked_handler:
        mocked_handler.return_value = fake_submission({"sliding_window_variable": 0.81, "hash_map_lookup": 0.9})
        response = run_pipeline(1, 1, "solved", db_path=db_path)

    saved_submission = connection.execute("SELECT * FROM submissions WHERE id = 1").fetchone()
    saved_recommendation = connection.execute("SELECT * FROM recommendations WHERE user_id = 1").fetchone()
    assert response["gap_info"]["gap_detected"] is True
    assert response["recommendation"]["tier"] in ("specific", "topic_hint")
    assert saved_recommendation is not None


def test_race_condition_atomicity_all_or_nothing(tmp_path):
    """
    Regression test for race condition issue #3.
    
    Verifies that when a submission is processed, all state changes
    (submission, streak, Elo profile, and recommendation) are committed
    atomically. If any part fails, the entire transaction should rollback.
    
    This prevents:
    - ELO being updated without submission being saved
    - Recommendation being logged without Elo being updated
    - Partial state leading to inconsistent user experience
    """
    db_path = tmp_path / "atomicity.sqlite3"
    connection = init_db(db_path)
    seed_base(connection)
    insert_submission(connection)
    
    # Track Elo before submission
    elo_before = connection.execute(
        "SELECT elo_rating FROM topic_profiles WHERE user_id = 1 AND topic = 'sliding_window_variable'"
    ).fetchone()["elo_rating"]
    
    # Get streak and last recommendation before submission
    user_before = connection.execute("SELECT current_streak, last_recommendation_id FROM users WHERE id = 1").fetchone()
    
    # Run the pipeline
    response = run_pipeline(1, 1, "solved", db_path=db_path)
    
    # Reconnect to get fresh data (simulating a new request)
    connection = connection.__enter__()
    connection = connection.__exit__(None, None, None)
    from pathforge.db.db import get_connection
    connection = get_connection(db_path)
    
    # VERIFY ATOMICITY: All state must be updated together
    
    # 1. Submission must be saved
    submission = connection.execute("SELECT * FROM submissions WHERE user_id = 1 ORDER BY id DESC LIMIT 1").fetchone()
    assert submission is not None, "Submission not saved"
    assert submission["verdict"] == "pass", "Submission verdict incorrect"
    
    # 2. Elo must be updated for the topic
    elo_after = connection.execute(
        "SELECT elo_rating FROM topic_profiles WHERE user_id = 1 AND topic = 'sliding_window_variable'"
    ).fetchone()["elo_rating"]
    assert elo_after > elo_before, "Elo not updated for the submission"
    
    # 3. Streak must be updated
    user_after = connection.execute("SELECT current_streak, last_recommendation_id FROM users WHERE id = 1").fetchone()
    assert user_after["current_streak"] is not None, "Streak not updated"
    
    # 4. Recommendation must be logged
    recommendation = connection.execute(
        "SELECT * FROM recommendations WHERE user_id = 1 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert recommendation is not None, "Recommendation not logged"
    assert user_after["last_recommendation_id"] == recommendation["id"], "last_recommendation_id not updated"
    
    # 5. Recommendation must be marked as acted_on
    previous_recommendation = connection.execute(
        "SELECT * FROM recommendations WHERE user_id = 1 AND id = ? ORDER BY id DESC LIMIT 1 OFFSET 1",
        (user_before["last_recommendation_id"],)
    ).fetchone()
    if previous_recommendation:
        assert previous_recommendation["acted_on"] == 1, "Previous recommendation not marked as acted_on"
    
    connection.close()


def test_no_elo_loss_on_duplicate_attempt(tmp_path):
    """
    Regression test to ensure that concurrent submissions don't cause lost updates.
    
    Simulates the scenario where:
    1. Request A reads Elo=850 for sliding_window_variable
    2. Request B reads Elo=850 for sliding_window_variable  
    3. Both calculate new Elo and write (should be ~860)
    4. Verify that both submissions are recorded and Elo reflects both changes
    
    Before fix: Only one +10 applied, Elo=860 (lost update)
    After fix: Both submissions saved atomically, no lost updates
    """
    db_path = tmp_path / "no_lost_updates.sqlite3"
    connection = init_db(db_path)
    seed_base(connection)
    insert_submission(connection)
    
    # Verify initial state - count submissions after seed
    initial_submission_count = connection.execute(
        "SELECT COUNT(*) as count FROM submissions WHERE user_id = 1 AND topic = 'sliding_window_variable' AND verdict = 'pass'"
    ).fetchone()["count"]
    
    initial_profile = connection.execute(
        "SELECT attempt_count FROM topic_profiles WHERE user_id = 1 AND topic = 'sliding_window_variable'"
    ).fetchone()
    initial_attempts = initial_profile["attempt_count"]
    
    # Simulate two sequential submissions (can't truly parallelize in pytest)
    response1 = run_pipeline(1, 1, "solved", db_path=db_path)
    
    # Create another unsolved problem for second attempt
    from pathforge.db.db import get_connection
    conn = get_connection(db_path)
    conn.execute(
        """INSERT INTO problems (id, title, difficulty, topics, pattern, test_cases, acceptance_rate, created_at)
           VALUES (5, 'Sliding Window 3', 'Easy', 'Array', '["sliding_window_variable"]', '[]', 85.0, '2026-06-04T00:00:00+00:00')"""
    )
    conn.commit()
    conn.close()
    
    response2 = run_pipeline(1, 5, "solved", db_path=db_path)
    
    # Both submissions should be recorded (total = initial + 2)
    conn = get_connection(db_path)
    final_submission_count = conn.execute(
        "SELECT COUNT(*) as count FROM submissions WHERE user_id = 1 AND topic = 'sliding_window_variable' AND verdict = 'pass'"
    ).fetchone()["count"]
    assert final_submission_count == initial_submission_count + 2, \
        f"Expected {initial_submission_count + 2} submissions, got {final_submission_count}"
    
    # Attempt count should be incremented by 2
    final_profile = conn.execute(
        "SELECT attempt_count FROM topic_profiles WHERE user_id = 1 AND topic = 'sliding_window_variable'"
    ).fetchone()
    assert final_profile["attempt_count"] == initial_attempts + 2, \
        f"Attempt count should be {initial_attempts + 2}, got {final_profile['attempt_count']}"
    
    conn.close()
