"""Tests for topic diversity and solved-problem filtering."""

from pathforge.recommender import (
    _select_problem,
    _consecutive_recommendations_for_topic,
    _maybe_rotate_for_diversity,
    get_recommendation,
)


def seed_db(connection):
    """Seed minimal data for diversity tests."""
    connection.execute(
        "INSERT INTO users (id, username, email, password_hash, created_at, updated_at) VALUES (1,'u','e','h','2026-06-19T00:00:00Z','2026-06-19T00:00:00Z')",
    )
    connection.execute(
        "INSERT INTO problems (id, title, difficulty, topics, pattern, test_cases, acceptance_rate, created_at) VALUES (1,'A','Easy','Array','[\"hash_map_lookup\"]','[]',80.0,'2026-06-19T00:00:00Z')",
    )
    connection.execute(
        "INSERT INTO problems (id, title, difficulty, topics, pattern, test_cases, acceptance_rate, created_at) VALUES (2,'B','Easy','Array','[\"hash_map_lookup\"]','[]',85.0,'2026-06-19T00:00:00Z')",
    )
    connection.execute(
        "INSERT INTO problems (id, title, difficulty, topics, pattern, test_cases, acceptance_rate, created_at) VALUES (3,'C','Easy','Graph','[\"bfs_level_order\"]','[]',90.0,'2026-06-19T00:00:00Z')",
    )
    connection.execute(
        "INSERT INTO topic_profiles (user_id, topic, elo_rating, attempt_count, pass_count, pattern_match_count, accuracy, recent_failures, created_at, updated_at) VALUES (1,'hash_map_lookup',850,0,0,0,0.0,0,'2026-06-19T00:00:00Z','2026-06-19T00:00:00Z')",
    )
    connection.execute(
        "INSERT INTO topic_profiles (user_id, topic, elo_rating, attempt_count, pass_count, pattern_match_count, accuracy, recent_failures, created_at, updated_at) VALUES (1,'bfs_level_order',700,0,0,0,0.0,0,'2026-06-19T00:00:00Z','2026-06-19T00:00:00Z')",
    )
    connection.commit()


def insert_submission(connection, user_id, problem_id, verdict, topic, submitted_at):
    connection.execute(
        "INSERT INTO submissions (user_id, problem_id, code_text, verdict, detected_pattern, detected_confidence, expected_pattern, target_pattern, gap_identified, diagnosis_confidence, time_taken_seconds, attempt_number, topic, submitted_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (user_id, problem_id, "code", verdict, topic, 1.0, topic, None, 0, 1.0, None, 1, topic, submitted_at),
    )


def insert_recommendation(connection, user_id, topic, created_at):
    connection.execute(
        "INSERT INTO recommendations (user_id, topic, reason, confidence_tier, created_at) VALUES (?,?,?,?,?)",
        (user_id, topic, "test", "specific", created_at),
    )


def test_solved_problem_is_excluded_by_select_problem(tmp_path):
    """Regression: solved problems must never be returned by _select_problem."""
    db_path = tmp_path / "test_solved_excluded.sqlite3"
    from pathforge.db.db import init_db
    connection = init_db(db_path)
    seed_db(connection)

    # User solves problem 1
    insert_submission(connection, 1, 1, "pass", "hash_map_lookup", "2026-06-19T10:00:00Z")
    connection.commit()

    # Problem 1 should be excluded, problem 2 should be returned
    result = _select_problem(connection, 1, "hash_map_lookup", "Easy")
    assert result is not None, "Should find unsolved problem"
    assert result["id"] == 2, f"Should return problem 2 (unsolved), got {result['id']}"

    # After solving problem 2, no problems left for hash_map_lookup
    insert_submission(connection, 1, 2, "pass", "hash_map_lookup", "2026-06-19T11:00:00Z")
    connection.commit()
    result = _select_problem(connection, 1, "hash_map_lookup", "Easy")
    assert result is None, "Should return None when all problems solved"


def test_consecutive_recommendations_no_false_positive(tmp_path):
    """_consecutive_recommendations_for_topic returns False when topic differs."""
    db_path = tmp_path / "test_no_false_positive.sqlite3"
    from pathforge.db.db import init_db
    connection = init_db(db_path)
    seed_db(connection)

    # Insert recommendations for different topics
    insert_recommendation(connection, 1, "hash_map_lookup", "2026-06-19T10:00:00Z")
    insert_recommendation(connection, 1, "bfs_level_order", "2026-06-19T11:00:00Z")
    connection.commit()

    assert not _consecutive_recommendations_for_topic(connection, 1, "hash_map_lookup")
    assert not _consecutive_recommendations_for_topic(connection, 1, "bfs_level_order")


def test_consecutive_recommendations_detects_loop(tmp_path):
    """_consecutive_recommendations_for_topic returns True when same topic in last 2."""
    db_path = tmp_path / "test_detects_loop.sqlite3"
    from pathforge.db.db import init_db
    connection = init_db(db_path)
    seed_db(connection)

    insert_recommendation(connection, 1, "hash_map_lookup", "2026-06-19T10:00:00Z")
    insert_recommendation(connection, 1, "hash_map_lookup", "2026-06-19T11:00:00Z")
    connection.commit()

    assert _consecutive_recommendations_for_topic(connection, 1, "hash_map_lookup")


def test_consecutive_recommendations_single_entry_returns_false(tmp_path):
    """With only 1 recommendation, should return False."""
    db_path = tmp_path / "test_single.sqlite3"
    from pathforge.db.db import init_db
    connection = init_db(db_path)
    seed_db(connection)

    insert_recommendation(connection, 1, "hash_map_lookup", "2026-06-19T10:00:00Z")
    connection.commit()

    assert not _consecutive_recommendations_for_topic(connection, 1, "hash_map_lookup")


def test_topic_diversity_rotation_on_pass(tmp_path):
    """get_recommendation should rotate when same topic recommended 2+ times consecutively."""
    db_path = tmp_path / "test_diversity_pass.sqlite3"
    from pathforge.db.db import init_db
    connection = init_db(db_path)
    seed_db(connection)
    connection.commit()

    # Set up: hash_map_lookup has been recommended twice consecutively
    insert_recommendation(connection, 1, "hash_map_lookup", "2026-06-19T10:00:00Z")
    insert_recommendation(connection, 1, "hash_map_lookup", "2026-06-19T11:00:00Z")
    connection.commit()

    problem_record = dict(connection.execute("SELECT * FROM problems WHERE id = 1").fetchone())
    submission_result = {
        "submission": {
            "problem_id": 1,
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

    rec = get_recommendation(1, submission_result, problem_record, connection)

    # Should have rotated away from hash_map_lookup due to diversity check
    assert rec["topic"] != "hash_map_lookup", f"Expected rotation away from hash_map_lookup, got {rec['topic']}"
    assert rec["topic"] == "bfs_level_order", f"Expected bfs_level_order, got {rec['topic']}"
    assert rec["tier"] == "specific", f"Expected specific recommendation, got {rec['tier']}"
    assert "diversity" not in rec["explanation"].lower()  # Should use "rotate" explanation
    assert rec["problem"] is not None, "Should have a specific problem"


def test_no_unnecessary_rotation_when_topic_diverse(tmp_path):
    """get_recommendation should NOT rotate when topic has NOT been over-recommended."""
    db_path = tmp_path / "test_no_unnecessary_rotation.sqlite3"
    from pathforge.db.db import init_db
    connection = init_db(db_path)
    seed_db(connection)
    # Need a Medium problem so the pass flow can stay on hash_map_lookup
    connection.execute(
        "INSERT INTO problems (id, title, difficulty, topics, pattern, test_cases, acceptance_rate, created_at) VALUES (4,'M','Medium','Array','[\"hash_map_lookup\"]','[]',75.0,'2026-06-19T00:00:00Z')",
    )
    connection.commit()

    # Set up: last 2 recommendations are for different topics
    insert_recommendation(connection, 1, "bfs_level_order", "2026-06-19T10:00:00Z")
    insert_recommendation(connection, 1, "hash_map_lookup", "2026-06-19T11:00:00Z")
    connection.commit()

    problem_record = dict(connection.execute("SELECT * FROM problems WHERE id = 1").fetchone())
    submission_result = {
        "submission": {
            "problem_id": 1,
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

    rec = get_recommendation(1, submission_result, problem_record, connection)

    # Should stay on hash_map_lookup (no diversity issue)
    assert rec["topic"] == "hash_map_lookup", f"Expected hash_map_lookup, got {rec['topic']}"
    assert rec["tier"] == "specific", f"Expected specific, got {rec['tier']}"


def test_maybe_rotate_for_diversity_no_rotation_when_not_needed(tmp_path):
    """_maybe_rotate_for_diversity returns (None, False) when no rotation needed."""
    db_path = tmp_path / "test_no_rotation_needed.sqlite3"
    from pathforge.db.db import init_db
    connection = init_db(db_path)
    seed_db(connection)
    insert_recommendation(connection, 1, "bfs_level_order", "2026-06-19T10:00:00Z")
    connection.commit()

    gap_info = {
        "gap_detected": False,
        "diagnosis_confidence": 1.0,
        "matched_pattern": "hash_map_lookup",
    }
    problem_record = dict(connection.execute("SELECT * FROM problems WHERE id = 1").fetchone())

    rec, rotated = _maybe_rotate_for_diversity(
        connection, 1, "hash_map_lookup", gap_info, "Easy",
        1, problem_record, False, "pass",
    )
    assert not rotated
    assert rec is None


def test_maybe_rotate_for_diversity_triggers_rotation(tmp_path):
    """_maybe_rotate_for_diversity rotates when topic over-recommended."""
    db_path = tmp_path / "test_rotation_triggers.sqlite3"
    from pathforge.db.db import init_db
    connection = init_db(db_path)
    seed_db(connection)
    insert_recommendation(connection, 1, "hash_map_lookup", "2026-06-19T10:00:00Z")
    insert_recommendation(connection, 1, "hash_map_lookup", "2026-06-19T11:00:00Z")
    connection.commit()

    gap_info = {
        "gap_detected": False,
        "diagnosis_confidence": 1.0,
        "matched_pattern": "hash_map_lookup",
    }
    problem_record = dict(connection.execute("SELECT * FROM problems WHERE id = 1").fetchone())

    rec, rotated = _maybe_rotate_for_diversity(
        connection, 1, "hash_map_lookup", gap_info, "Easy",
        1, problem_record, False, "pass",
    )
    assert rotated, "Should rotate due to consecutive same-topic recommendations"
    assert rec is not None
    assert rec["topic"] == "bfs_level_order", f"Expected bfs_level_order, got {rec['topic']}"
    assert rec["tier"] == "specific"
