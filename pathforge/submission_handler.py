from datetime import date, timedelta
from typing import Union

from pathforge.db.profile_manager import iso_now, update_topic_profile
from pathforge.services import parse_problem_pattern


def to_date(value: Union[str, date, None]) -> Union[date, None]:
    """Safely convert a value to a `datetime.date`.

    Accepts:
    - ``datetime.date`` — returned as-is.
    - ISO-format string (e.g. ``"2026-07-27"``) — parsed via ``date.fromisoformat``.
    - ``None`` — returns ``None``.

    This exists because PostgreSQL ``DATE`` columns are returned by psycopg2
    as ``datetime.date`` objects, not strings. Calling
    ``date.fromisoformat(date_obj)`` would raise ``TypeError``.
    """
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def handle_submission(user_id, problem_id, verdict, connection):
    timestamp = iso_now()

    problem = _get_problem(connection, problem_id)
    pattern = _get_pattern(problem)

    db_verdict = "pass" if verdict == "solved" else "fail"

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
    }


def _get_problem(connection, problem_id):
    row = connection.execute("SELECT * FROM problems WHERE id = %s", (problem_id,)).fetchone()
    if not row:
        raise ValueError(f"Problem not found: {problem_id}")
    return dict(row)


def _get_pattern(problem):
    patterns = parse_problem_pattern(problem)
    if not patterns:
        raise ValueError(f"Problem {problem['id']} has no pattern")
    return patterns[0]


def _next_attempt_number(connection, user_id, problem_id):
    row = connection.execute(
        "SELECT COALESCE(MAX(attempt_number), 0) + 1 AS next_attempt FROM submissions WHERE user_id = %s AND problem_id = %s",
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
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
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
            False,
            1.0,
            None,
            attempt_number,
            topic,
            submitted_at,
        ),
    )
    # NOTE: Do not commit here. The caller (pipeline.py) must handle atomicity
    # by committing all changes (submission, streak, profile, recommendation) in one transaction.
    return cursor.fetchone()["id"]


def _update_user_streak(connection, user_id, submitted_at):
    today = to_date(submitted_at[:10] if isinstance(submitted_at, str) else submitted_at)
    row = connection.execute("SELECT current_streak, last_submission_date FROM users WHERE id = %s", (user_id,)).fetchone()
    if not row:
        return
    last_date = to_date(row["last_submission_date"])
    if last_date == today:
        streak = int(row["current_streak"] or 1)
    elif last_date == today - timedelta(days=1):
        streak = int(row["current_streak"] or 0) + 1
    else:
        streak = 1
    connection.execute(
        "UPDATE users SET current_streak = %s, last_submission_date = %s, updated_at = %s WHERE id = %s",
        (streak, today.isoformat(), submitted_at, user_id),
    )
    # NOTE: Do not commit here. The caller (pipeline.py) must handle atomicity
    # by committing all changes (submission, streak, profile, recommendation) in one transaction.


def _get_submission(connection, submission_id):
    row = connection.execute("SELECT * FROM submissions WHERE id = %s", (submission_id,)).fetchone()
    return dict(row)
