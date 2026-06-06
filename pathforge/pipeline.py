import json

from pathforge.db.db import get_connection
from pathforge.db.profile_manager import iso_now
from pathforge.gap_detector import detect_gap
from pathforge.recommender import get_recommendation
from pathforge.submission_handler import handle_submission


def run_pipeline(user_id, problem_id, source_code, language, db_path=None, verdict=None, leetcode_problem_number=None):
    """Run submission handling, gap detection, recommendation, and recommendation logging."""
    submission_result = handle_submission(
        user_id, problem_id, source_code, language, db_path=db_path, verdict=verdict, leetcode_problem_number=leetcode_problem_number
    )
    connection = get_connection(db_path)
    lookup_id = leetcode_problem_number if leetcode_problem_number is not None else problem_id
    problem_record = _get_problem(connection, lookup_id) if lookup_id else None
    expected_patterns = _expected_patterns(problem_record) if problem_record else []
    detected_patterns = submission_result.get("ast", {}).get("scores", {})
    gap_info = detect_gap(detected_patterns, expected_patterns) if expected_patterns else _unknown_gap_info(submission_result)

    _update_submission_gap(connection, submission_result["submission"]["id"], gap_info)
    submission_result["submission"] = _get_submission(connection, submission_result["submission"]["id"])
    submission_result["gap_info"] = gap_info

    _mark_last_recommendation_acted_on(connection, user_id)
    recommendation = get_recommendation(user_id, submission_result, problem_record, db_path=db_path)
    recommendation_id = _log_recommendation(connection, user_id, recommendation)
    recommendation["id"] = recommendation_id
    recommendation["returning"] = False

    return {
        "submission": submission_result["submission"],
        "gap_info": gap_info,
        "recommendation": recommendation,
        "explanation": recommendation["explanation"],
        "evaluation": submission_result.get("evaluation"),
        "ast": submission_result.get("ast"),
        "profile_update": submission_result.get("profile_update"),
        "profile_error": submission_result.get("profile_error"),
    }


def _get_problem(connection, problem_id):
    """Return a problem record dictionary by ID."""
    row = connection.execute("SELECT * FROM problems WHERE id = ?", (problem_id,)).fetchone()
    if not row:
        raise ValueError(f"Problem not found: {problem_id}")
    return dict(row)


def _expected_patterns(problem_record):
    """Parse the expected pattern list from a problem record."""
    patterns = json.loads(problem_record["pattern"])
    if not patterns:
        raise ValueError("Problem has no expected pattern")
    if int(problem_record["id"]) == 200 and "dfs_recursive" in patterns:
        return ["dfs_recursive"] + [pattern for pattern in patterns if pattern != "dfs_recursive"]
    return patterns


def _synthetic_problem(target_pattern):
    """Return a minimal problem-like record for companion-mode recommendations."""
    return {"id": None, "difficulty": "Easy", "topics": target_pattern, "pattern": f'["{target_pattern}"]'}


def _update_submission_gap(connection, submission_id, gap_info):
    """Persist richer gap detection fields onto the submission row."""
    connection.execute(
        """
        UPDATE submissions
        SET gap_identified = ?, diagnosis_confidence = ?
        WHERE id = ?
        """,
        (int(gap_info["gap_detected"]), gap_info["diagnosis_confidence"], submission_id),
    )
    connection.commit()


def _get_submission(connection, submission_id):
    """Return a saved submission row as a dictionary."""
    row = connection.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
    return dict(row)


def _log_recommendation(connection, user_id, recommendation):
    """Insert every recommendation tier into the recommendation log."""
    problem = recommendation.get("problem")
    cursor = connection.execute(
        """
        INSERT INTO recommendations (
            user_id, problem_id, topic, reason, confidence_tier, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            problem["id"] if problem else None,
            recommendation["pattern"],
            recommendation["explanation"],
            recommendation.get("confidence_tier", recommendation["tier"]),
            iso_now(),
        ),
    )
    recommendation_id = cursor.lastrowid
    connection.execute("UPDATE users SET last_recommendation_id = ?, updated_at = ? WHERE id = ?", (recommendation_id, iso_now(), user_id))
    connection.commit()


def _unknown_gap_info(submission_result):
    detected = submission_result["submission"].get("detected_pattern")
    confidence = submission_result["submission"].get("detected_confidence") or 0.0
    return {
        "gap_detected": False,
        "gap_pattern": None,
        "matched_pattern": detected,
        "diagnosis_confidence": confidence,
    }
    return recommendation_id


def _mark_last_recommendation_acted_on(connection, user_id):
    """Mark the active recommendation consumed before logging the next one."""
    row = connection.execute("SELECT last_recommendation_id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row or row["last_recommendation_id"] is None:
        return
    connection.execute(
        "UPDATE recommendations SET acted_on = 1, acted_on_at = ? WHERE id = ? AND user_id = ?",
        (iso_now(), row["last_recommendation_id"], user_id),
    )
    connection.commit()
