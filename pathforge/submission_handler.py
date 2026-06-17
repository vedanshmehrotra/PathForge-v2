import json
from datetime import date, timedelta

from pathforge.db.profile_manager import iso_now, update_topic_profile


def handle_submission(user_id, problem_id, verdict, connection):
    timestamp = iso_now()

    problem = _get_problem(connection, problem_id)
    pattern = _get_pattern(problem)

    db_verdict = "pass" if verdict == "solved" else "fail"

    profile_update = None
    profile_error = None
    try:
        profile_update = update_topic_profile(
            connection,
            user_id=user_id,
            topic=pattern,
            difficulty=problem["difficulty"],
            verdict=db_verdict,
            detected_pattern=pattern,
            expected_pattern=pattern,
            attempted_at=timestamp,
        )
    except Exception as exc:
        profile_error = str(exc)

    attempt_number = _next_attempt_number(connection, user_id, problem_id)
    submission_id = _save_submission(
        connection=connection,
        user_id=user_id,
        problem_id=problem_id,
        verdict=db_verdict,
        detected_pattern=pattern,
        topic=pattern,
        attempt_number=attempt_number,
        submitted_at=timestamp,
    )

    _update_user_streak(connection, user_id, timestamp)

    record = _get_submission(connection, submission_id)
    gap_info = {
        "gap_detected": False,
        "gap_pattern": None,
        "matched_pattern": pattern,
        "diagnosis_confidence": 1.0,
    }
    return {
        "submission": record,
        "gap_info": gap_info,
        "profile_update": profile_update,
        "profile_error": profile_error,
    }


def _get_problem(connection, problem_id):
    row = connection.execute("SELECT * FROM problems WHERE id = ?", (problem_id,)).fetchone()
    if not row:
        raise ValueError(f"Problem not found: {problem_id}")
    return dict(row)


def _get_pattern(problem):
    patterns = json.loads(problem["pattern"])
    if not patterns:
        raise ValueError(f"Problem {problem['id']} has no pattern")
    return patterns[0]


def _next_attempt_number(connection, user_id, problem_id):
    row = connection.execute(
        "SELECT COALESCE(MAX(attempt_number), 0) + 1 AS next_attempt FROM submissions WHERE user_id = ? AND problem_id = ?",
        (user_id, problem_id),
    ).fetchone()
    return int(row["next_attempt"])


def _save_submission(
    connection,
    user_id,
    problem_id,
    verdict,
    detected_pattern,
    topic,
    attempt_number,
    submitted_at,
):
    cursor = connection.execute(
        """
        INSERT INTO submissions (
            user_id, problem_id, code_text, verdict, detected_pattern,
            detected_confidence, expected_pattern, target_pattern, gap_identified,
            diagnosis_confidence, time_taken_seconds, attempt_number, topic, submitted_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            problem_id,
            "self-reported",
            verdict,
            detected_pattern,
            1.0,
            detected_pattern,
            None,
            0,
            1.0,
            None,
            attempt_number,
            topic,
            submitted_at,
        ),
    )
    connection.commit()
    return cursor.lastrowid


def _update_user_streak(connection, user_id, submitted_at):
    today = date.fromisoformat(submitted_at[:10])
    row = connection.execute("SELECT current_streak, last_submission_date FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        return
    last_date = date.fromisoformat(row["last_submission_date"]) if row["last_submission_date"] else None
    if last_date == today:
        streak = int(row["current_streak"] or 1)
    elif last_date == today - timedelta(days=1):
        streak = int(row["current_streak"] or 0) + 1
    else:
        streak = 1
    connection.execute(
        "UPDATE users SET current_streak = ?, last_submission_date = ?, updated_at = ? WHERE id = ?",
        (streak, today.isoformat(), submitted_at, user_id),
    )
    connection.commit()


def _get_submission(connection, submission_id):
    row = connection.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
    return dict(row)
