import json
from datetime import date, timedelta

from pathforge.ast_engine import classify_pattern, extract_features, sanitize_code
from pathforge.db.db import get_connection
from pathforge.db.profile_manager import iso_now, update_topic_profile
from pathforge.judge0_client import evaluate_submission, get_verdict

LANGUAGE_IDS = {
    "python": 71,
    "python3": 71,
    "java": 62,
}


def handle_submission(user_id, problem_id, source_code, language, db_path=None, verdict=None, target_pattern=None):
    """Analyze pasted code, persist a self-reported submission, and update the pattern profile."""
    connection = get_connection(db_path)
    timestamp = iso_now()
    problem = _get_problem(connection, problem_id) if problem_id else None
    if language.lower().replace(" ", "") not in ("python", "python3"):
        raise ValueError("PathForge currently supports Python solution analysis only.")
    expected_pattern = target_pattern or (_first_pattern(problem["pattern"]) if problem else None)
    if not expected_pattern:
        raise ValueError("target_pattern is required for companion-mode submissions")
    self_reported = verdict is not None
    evaluation = {"verdict": verdict, "source": "self_reported", "test_results": [], "first_failure": None}
    if verdict is None:
        language_id = _get_language_id(language)
        test_cases = json.loads(problem["test_cases"])
        evaluation = evaluate_submission(source_code, language_id, test_cases)
        verdict = get_verdict(evaluation)
    if verdict not in ("pass", "fail"):
        raise ValueError("verdict must be 'pass' or 'fail'")

    ast_result = _analyze_code(source_code)
    if ast_result.get("status") == "rejected":
        raise ValueError(ast_result["message"])
    detected_pattern = ast_result["detected_pattern"]
    if detected_pattern is None:
        raise ValueError(_format_analysis_errors(ast_result.get("errors")))
    detected_confidence = ast_result["detected_confidence"]
    topic = detected_pattern if self_reported else _first_topic(problem["topics"])
    gap_identified = int(detected_pattern != expected_pattern)
    attempt_number = _next_attempt_number(connection, user_id, problem_id) if problem_id else _next_user_attempt_number(connection, user_id)
    time_taken_seconds = _total_execution_seconds(evaluation)

    submission_id = _save_submission(
        connection=connection,
        user_id=user_id,
        problem_id=problem_id,
        source_code=source_code,
        verdict=verdict,
        detected_pattern=detected_pattern,
        detected_confidence=detected_confidence,
        expected_pattern=expected_pattern,
        target_pattern=target_pattern,
        gap_identified=gap_identified,
        time_taken_seconds=time_taken_seconds,
        attempt_number=attempt_number,
        topic=topic,
        submitted_at=timestamp,
    )

    profile_update = None
    profile_error = None
    if verdict in ("pass", "fail"):
        try:
            profile_update = update_topic_profile(
                connection,
                user_id=user_id,
                topic=topic,
                difficulty=_difficulty_for_profile(connection, user_id, topic, problem),
                verdict=verdict,
                detected_pattern=detected_pattern,
                expected_pattern=expected_pattern,
                attempted_at=timestamp,
            )
            _update_submission_elo(connection, submission_id, profile_update)
        except Exception as exc:
            profile_error = str(exc)

    _update_user_streak(connection, user_id, timestamp)
    _update_recommendation_feedback(connection, user_id, detected_pattern)

    record = _get_submission(connection, submission_id)
    return {
        "submission": record,
        "evaluation": evaluation,
        "ast": ast_result,
        "profile_update": profile_update,
        "profile_error": profile_error,
    }


def _get_problem(connection, problem_id):
    """Return a problem row by ID or raise ValueError if it does not exist."""
    row = connection.execute("SELECT * FROM problems WHERE id = ?", (problem_id,)).fetchone()
    if not row:
        raise ValueError(f"Problem not found: {problem_id}")
    return row


def _get_language_id(language):
    """Map a user-facing language name to a Judge0 language ID."""
    key = language.lower().replace(" ", "")
    if key not in LANGUAGE_IDS:
        raise ValueError(f"Unsupported language: {language}")
    return LANGUAGE_IDS[key]


def _first_pattern(pattern_json):
    """Return the first expected pattern from the problem pattern JSON field."""
    patterns = json.loads(pattern_json)
    if not patterns:
        raise ValueError("Problem has no expected pattern")
    return patterns[0]


def _first_topic(topics):
    """Return the first topic from the comma-separated topics field."""
    return topics.split(",")[0].strip()


def _analyze_code(source_code):
    """Run AST safety, extraction, and classification with structured fallback errors."""
    is_safe, errors, root = sanitize_code(source_code)
    if not is_safe:
        language_error = _language_not_supported_error(errors)
        if language_error:
            return language_error
        return {
            "detected_pattern": None,
            "detected_confidence": 0.0,
            "errors": errors,
            "scores": {},
        }

    features = extract_features(root)
    scores = classify_pattern(features)
    detected_pattern, detected_confidence = max(scores.items(), key=lambda item: item[1])
    return {
        "detected_pattern": detected_pattern,
        "detected_confidence": detected_confidence,
        "errors": [],
        "scores": scores,
    }


def _language_not_supported_error(errors):
    """Return the structured v1 rejection for obvious non-Python submissions."""
    for error in errors:
        if isinstance(error, dict) and error.get("reason") == "language_not_supported":
            return {
                "status": "rejected",
                "reason": "language_not_supported",
                "message": "PathForge currently only supports Python solutions",
                "detected_pattern": None,
                "detected_confidence": 0.0,
                "errors": errors,
                "scores": {},
            }
    return None


def _format_analysis_errors(errors):
    """Return a concise user-facing analysis error string."""
    if not errors:
        return "Could not analyze this Python solution"
    first_error = errors[0]
    if isinstance(first_error, dict):
        return first_error.get("message") or "Could not analyze this Python solution"
    return str(first_error)


def _next_attempt_number(connection, user_id, problem_id):
    """Return the next attempt number for a user/problem pair."""
    row = connection.execute(
        "SELECT COALESCE(MAX(attempt_number), 0) + 1 AS next_attempt FROM submissions WHERE user_id = ? AND problem_id = ?",
        (user_id, problem_id),
    ).fetchone()
    return int(row["next_attempt"])


def _next_user_attempt_number(connection, user_id):
    """Return the next attempt number for companion-mode submissions without a fixed problem."""
    row = connection.execute(
        "SELECT COALESCE(MAX(attempt_number), 0) + 1 AS next_attempt FROM submissions WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return int(row["next_attempt"])


def _difficulty_for_profile(connection, user_id, topic, problem):
    """Return problem difficulty or derive one from the user's current pattern Elo."""
    if problem:
        return problem["difficulty"]
    row = connection.execute(
        "SELECT elo_rating FROM topic_profiles WHERE user_id = ? AND topic = ?",
        (user_id, topic),
    ).fetchone()
    elo = float(row["elo_rating"]) if row else 800.0
    if elo < 1000:
        return "Easy"
    if elo <= 1300:
        return "Medium"
    return "Hard"


def _total_execution_seconds(evaluation):
    """Return summed Judge0 execution time as an integer number of seconds when available."""
    total = 0.0
    seen_time = False
    for result in evaluation.get("test_results", []):
        if result.get("execution_time") is not None:
            seen_time = True
            total += float(result["execution_time"])
    return int(round(total)) if seen_time else None


def _save_submission(
    connection,
    user_id,
    problem_id,
    source_code,
    verdict,
    detected_pattern,
    detected_confidence,
    expected_pattern,
    gap_identified,
    time_taken_seconds,
    attempt_number,
    topic,
    submitted_at,
    target_pattern,
):
    """Insert the submission row and commit it before downstream profile updates."""
    cursor = connection.execute(
        """
        INSERT INTO submissions (
            user_id, problem_id, code_text, verdict, detected_pattern,
            detected_confidence, expected_pattern, target_pattern, gap_identified,
            time_taken_seconds, attempt_number, topic, submitted_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            problem_id,
            source_code,
            verdict,
            detected_pattern,
            detected_confidence,
            expected_pattern,
            target_pattern,
            gap_identified,
            time_taken_seconds,
            attempt_number,
            topic,
            submitted_at,
        ),
    )
    connection.commit()
    return cursor.lastrowid


def _update_submission_elo(connection, submission_id, profile_update):
    """Persist Elo before/after values back onto a saved submission row."""
    connection.execute(
        "UPDATE submissions SET elo_before = ?, elo_after = ? WHERE id = ?",
        (profile_update["elo_before"], profile_update["elo_after"], submission_id),
    )
    connection.commit()


def _get_submission(connection, submission_id):
    """Return a saved submission row as a dictionary."""
    row = connection.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
    return dict(row)


def _update_recommendation_feedback(connection, user_id, detected_pattern):
    """Track whether the active recommendation was followed and its 3-submission Elo delta."""
    recommendation = connection.execute(
        """
        SELECT r.*
        FROM users u
        JOIN recommendations r ON r.id = u.last_recommendation_id
        WHERE u.id = ? AND r.user_id = ?
        """,
        (user_id, user_id),
    ).fetchone()
    if not recommendation:
        return

    topic = recommendation["topic"]
    if detected_pattern == topic:
        connection.execute("UPDATE recommendations SET followed = 1 WHERE id = ?", (recommendation["id"],))

    for pending in connection.execute(
        """
        SELECT id, topic, created_at
        FROM recommendations
        WHERE user_id = ? AND elo_delta_after IS NULL
        """,
        (user_id,),
    ).fetchall():
        _populate_recommendation_elo_delta(connection, user_id, pending)
    connection.commit()


def _update_user_streak(connection, user_id, submitted_at):
    """Update consecutive-day submission streak for the user."""
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


def _populate_recommendation_elo_delta(connection, user_id, recommendation):
    rows = connection.execute(
        """
        SELECT elo_before, elo_after
        FROM submissions
        WHERE user_id = ? AND topic = ? AND submitted_at >= ?
        ORDER BY submitted_at ASC, id ASC
        LIMIT 3
        """,
        (user_id, recommendation["topic"], recommendation["created_at"]),
    ).fetchall()
    if len(rows) >= 3 and rows[0]["elo_before"] is not None:
        current = connection.execute(
            "SELECT elo_rating FROM topic_profiles WHERE user_id = ? AND topic = ?",
            (user_id, recommendation["topic"]),
        ).fetchone()
        if current:
            delta = float(current["elo_rating"]) - float(rows[0]["elo_before"])
            connection.execute("UPDATE recommendations SET elo_delta_after = ? WHERE id = ?", (delta, recommendation["id"]))



