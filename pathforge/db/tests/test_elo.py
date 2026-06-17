from pathforge.db.db import init_db
from pathforge.db.elo import calculate_expected, get_k_factor, update_elo
from pathforge.db.profile_manager import get_weakest_topics, update_topic_profile


def test_get_k_factor_by_difficulty():
    assert get_k_factor("Easy") == 32
    assert get_k_factor("Medium") == 24
    assert get_k_factor("Hard") == 16


def test_calculate_expected_standard_elo():
    assert round(calculate_expected(800, 800), 3) == 0.5
    assert calculate_expected(1200, 900) > 0.8
    assert calculate_expected(800, 1200) < 0.1


def test_update_elo_win_increases_rating():
    updated = update_elo(800, "Easy", 1.0)
    assert updated > 800


def test_update_elo_partial_win_has_smaller_gain_than_full_win():
    partial = update_elo(800, "Easy", 0.5)
    full = update_elo(800, "Easy", 1.0)
    assert 800 < partial < full


def test_update_elo_loss_decreases_rating_with_floor():
    updated = update_elo(800, "Medium", 0.0)
    assert 400 <= updated < 800
    assert update_elo(400, "Hard", 0.0) == 400


def test_multi_submission_profile_sequence(tmp_path):
    db_path = tmp_path / "pathforge_test.sqlite3"
    connection = init_db(db_path)
    connection.execute(
        """
        INSERT INTO users (username, email, password_hash, created_at, updated_at)
        VALUES ('veda', 'veda@example.com', 'hash', '2026-06-03T00:00:00+00:00', '2026-06-03T00:00:00+00:00')
        """
    )
    connection.commit()

    first = update_topic_profile(
        connection,
        user_id=1,
        topic="Array",
        difficulty="Easy",
        verdict="pass",
        detected_pattern="hash_map_lookup",
        expected_pattern="hash_map_lookup",
        attempted_at="2026-06-03T00:01:00+00:00",
    )
    second = update_topic_profile(
        connection,
        user_id=1,
        topic="Array",
        difficulty="Medium",
        verdict="pass",
        detected_pattern="two_pointers_same",
        expected_pattern="sliding_window_variable",
        attempted_at="2026-06-03T00:02:00+00:00",
    )
    third = update_topic_profile(
        connection,
        user_id=1,
        topic="Array",
        difficulty="Hard",
        verdict="fail",
        detected_pattern="dp_1d_forward",
        expected_pattern="dp_1d_forward",
        attempted_at="2026-06-03T00:03:00+00:00",
    )

    row = connection.execute("SELECT * FROM topic_profiles WHERE user_id = 1 AND topic = 'Array'").fetchone()
    assert first["outcome"] == 1.0
    assert second["outcome"] == 0.5
    assert third["outcome"] == 0.0
    assert row["attempt_count"] == 3
    assert row["pass_count"] == 2
    assert row["pattern_match_count"] == 1
    assert round(row["accuracy"], 2) == 0.67
    assert row["recent_failures"] == 1
    assert row["elo_rating"] >= 400


def test_get_weakest_topics_ranks_low_skill_first(tmp_path):
    db_path = tmp_path / "pathforge_test.sqlite3"
    connection = init_db(db_path)
    connection.execute(
        """
        INSERT INTO users (username, email, password_hash, created_at, updated_at)
        VALUES ('veda', 'veda@example.com', 'hash', '2026-06-03T00:00:00+00:00', '2026-06-03T00:00:00+00:00')
        """
    )
    connection.execute(
        """
        INSERT INTO problems (id, title, difficulty, topics, pattern, test_cases, acceptance_rate, created_at)
        VALUES
            (1, 'Dummy', 'Easy', 'Array', '["hash_map_lookup"]', '[]', 50.0, '2026-06-03T00:00:00+00:00')
        """
    )
    connection.execute(
        """
        INSERT INTO topic_profiles (
            user_id, topic, elo_rating, attempt_count, pass_count,
            pattern_match_count, accuracy, recent_failures,
            created_at, updated_at
        )
        VALUES
            (1, 'hash_map_lookup', 700, 5, 1, 1, 0.2, 3, '2026-06-03T00:00:00+00:00', '2026-06-03T00:00:00+00:00'),
            (1, 'bfs_level_order', 1100, 5, 4, 4, 0.8, 0, '2026-06-03T00:00:00+00:00', '2026-06-03T00:00:00+00:00')
        """
    )
    # Seed a second problem so bfs_level_order is also recommendable
    connection.execute(
        """
        INSERT INTO problems (id, title, difficulty, topics, pattern, test_cases, acceptance_rate, created_at)
        VALUES
            (2, 'Dummy2', 'Easy', 'Graph', '["bfs_level_order"]', '[]', 50.0, '2026-06-03T00:00:00+00:00')
        """
    )
    connection.commit()

    weakest = get_weakest_topics(connection, user_id=1)
    assert weakest[0]["topic"] == "hash_map_lookup"
    assert weakest[0]["weakness_score"] > weakest[1]["weakness_score"]
