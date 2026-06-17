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
            (1, 'Array', 850, 3, 1, 1, 0.33, 2, '2026-06-04T00:00:00+00:00', '2026-06-04T00:00:00+00:00'),
            (1, 'Graph', 700, 3, 0, 0, 0.0, 3, '2026-06-04T00:00:00+00:00', '2026-06-04T00:00:00+00:00')
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
            "topic": "Array",
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
            1, 1, 'Array', '2026-06-04T00:00:00+00:00'
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
