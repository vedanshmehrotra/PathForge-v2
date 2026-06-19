from pathforge.db.db import connect
from pathforge.db.profile_manager import iso_now
from pathforge.recommender import get_recommendation
from pathforge.submission_handler import handle_submission


def run_pipeline(user_id, problem_id, verdict, db_path=None):
    with connect(db_path) as connection:
        try:
            submission_result = handle_submission(
                user_id, problem_id, verdict, connection
            )
            problem_record = _find_problem(connection, problem_id)

            _mark_last_recommendation_acted_on(connection, user_id)
            recommendation = get_recommendation(user_id, submission_result, problem_record, connection)
            recommendation_id = _log_recommendation(connection, user_id, recommendation)
            recommendation["id"] = recommendation_id
            recommendation["returning"] = False

            # Commit all changes atomically: submission, streak, profile, recommendations
            connection.commit()

            return {
                "submission": submission_result["submission"],
                "gap_info": submission_result["gap_info"],
                "recommendation": recommendation,
                "explanation": recommendation["explanation"],
                "profile_update": submission_result.get("profile_update"),
                "profile_error": submission_result.get("profile_error"),
            }
        except Exception:
            connection.rollback()
            raise


def _find_problem(connection, problem_id):
    row = connection.execute("SELECT * FROM problems WHERE id = ?", (problem_id,)).fetchone()
    return dict(row) if row else None


def _log_recommendation(connection, user_id, recommendation):
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
    # NOTE: Do not commit here. The caller (run_pipeline) handles atomicity.
    return recommendation_id


def _mark_last_recommendation_acted_on(connection, user_id):
    row = connection.execute("SELECT last_recommendation_id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row or row["last_recommendation_id"] is None:
        return
    connection.execute(
        "UPDATE recommendations SET acted_on = 1, acted_on_at = ? WHERE id = ? AND user_id = ?",
        (iso_now(), row["last_recommendation_id"], user_id),
    )
    # NOTE: Do not commit here. The caller (run_pipeline) handles atomicity.
