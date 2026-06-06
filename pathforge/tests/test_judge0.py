from unittest.mock import Mock, patch

from pathforge.db.db import init_db
from pathforge.judge0_client import evaluate_submission, get_verdict, run_single_test
from pathforge.submission_handler import handle_submission


TEST_CASES = [
    {"input": "1", "expected": "2"},
    {"input": "2", "expected": "4"},
    {"input": "3", "expected": "6"},
    {"input": "4", "expected": "8"},
]


def judge0_response(stdout="", status_id=3, description="Accepted", time="0.01"):
    """Build a minimal Judge0 response payload for tests."""
    return {
        "status": {"id": status_id, "description": description},
        "stdout": stdout,
        "stderr": None,
        "time": time,
        "memory": 1024,
    }


def seed_user_and_problem(connection):
    """Insert one user and one problem needed by submission handler tests."""
    connection.execute(
        """
        INSERT INTO users (id, username, email, password_hash, created_at, updated_at)
        VALUES (1, 'veda', 'veda@example.com', 'hash', '2026-06-03T00:00:00+00:00', '2026-06-03T00:00:00+00:00')
        """
    )
    connection.execute(
        """
        INSERT INTO problems (
            id, title, difficulty, topics, pattern, test_cases, created_at
        )
        VALUES (
            1,
            'Two Sum',
            'Easy',
            'Array, Hash Table',
            '["hash_map_lookup"]',
            '[{"input": "1", "expected": "2"}, {"input": "2", "expected": "4"}, {"input": "3", "expected": "6"}, {"input": "4", "expected": "8"}]',
            '2026-06-03T00:00:00+00:00'
        )
        """
    )
    connection.commit()


def test_pass_verdict_when_all_test_cases_match():
    with patch("pathforge.judge0_client.run_single_test") as mocked_run:
        mocked_run.side_effect = [
            judge0_response("2\n"),
            judge0_response("4\n"),
            judge0_response("6\n"),
            judge0_response("8\n"),
        ]

        result = evaluate_submission("print(input())", 71, TEST_CASES)

    assert get_verdict(result) == "pass"
    assert result["first_failure"] is None
    assert all(test["passed"] for test in result["test_results"])


def test_fail_verdict_when_one_test_case_has_wrong_output():
    with patch("pathforge.judge0_client.run_single_test") as mocked_run:
        mocked_run.side_effect = [
            judge0_response("2"),
            judge0_response("wrong"),
            judge0_response("6"),
            judge0_response("8"),
        ]

        result = evaluate_submission("print(input())", 71, TEST_CASES)

    assert get_verdict(result) == "fail"
    assert result["first_failure"]["test_case"] == 2
    assert result["first_failure"]["reason"] == "Wrong output"


def test_tle_verdict():
    with patch("pathforge.judge0_client.run_single_test") as mocked_run:
        mocked_run.side_effect = [
            judge0_response("2"),
            judge0_response("", status_id=5, description="Time Limit Exceeded"),
            judge0_response("6"),
            judge0_response("8"),
        ]

        result = evaluate_submission("while True: pass", 71, TEST_CASES)

    assert get_verdict(result) == "tle"
    assert result["first_failure"]["reason"] == "Time Limit Exceeded"


def test_run_single_test_retries_once_on_non_200():
    first = Mock(status_code=500, text="server error")
    second = Mock(status_code=200)
    second.json.return_value = judge0_response("2")

    with patch("pathforge.judge0_client.JUDGE0_API_KEY", "key"):
        with patch("pathforge.judge0_client.time.sleep"):
            with patch("pathforge.judge0_client.requests.post", side_effect=[first, second]) as mocked_post:
                result = run_single_test("print(2)", 71, "")

    assert result["status"]["id"] == 3
    assert mocked_post.call_count == 2


def test_submission_is_saved_to_db_after_evaluation(tmp_path):
    db_path = tmp_path / "judge0.sqlite3"
    connection = init_db(db_path)
    seed_user_and_problem(connection)

    code = """
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in seen:
            return [seen[diff], i]
        seen[num] = i
    return []
"""
    with patch("pathforge.submission_handler.evaluate_submission") as mocked_eval:
        mocked_eval.return_value = {
            "verdict": "pass",
            "passed": True,
            "test_results": [judge0_response("2")],
            "first_failure": None,
        }

        result = handle_submission(1, 1, code, "python", db_path=db_path)

    row = connection.execute("SELECT * FROM submissions WHERE id = ?", (result["submission"]["id"],)).fetchone()
    assert row["verdict"] == "pass"
    assert row["problem_id"] == 1
    assert row["detected_pattern"] == "hash_map_lookup"


def test_topic_profile_is_updated_after_evaluation(tmp_path):
    db_path = tmp_path / "judge0.sqlite3"
    connection = init_db(db_path)
    seed_user_and_problem(connection)

    code = """
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in seen:
            return [seen[diff], i]
        seen[num] = i
    return []
"""
    with patch("pathforge.submission_handler.evaluate_submission") as mocked_eval:
        mocked_eval.return_value = {
            "verdict": "pass",
            "passed": True,
            "test_results": [judge0_response("2")],
            "first_failure": None,
        }

        handle_submission(1, 1, code, "python", db_path=db_path)

    profile = connection.execute(
        "SELECT * FROM topic_profiles WHERE user_id = 1 AND topic = 'hash_map_lookup'"
    ).fetchone()
    submission = connection.execute("SELECT * FROM submissions WHERE user_id = 1").fetchone()
    assert profile["attempt_count"] == 1
    assert profile["pass_count"] == 1
    assert submission["elo_before"] == 800
    assert submission["elo_after"] > 800
