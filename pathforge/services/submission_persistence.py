from datetime import date, timedelta
from typing import Dict, Any, Optional

from pathforge.db.profile_manager import iso_now, update_topic_profile
from pathforge.services import parse_problem_pattern
from pathforge.api.services.loader import load_submissions
from pathforge.gap_signal_engine import GapSignalEngine
from pathforge.elo_engine import EloEngine
from pathforge.recommender import get_recommendation
from pathforge.pipeline import _log_recommendation, _mark_last_recommendation_acted_on

_gap_engine = GapSignalEngine()
_elo_engine = EloEngine()


def _calculate_attempt_number(connection, user_id: int, problem_id: Optional[int]) -> int:
    """
    Calculate the next attempt number for a user on a specific problem.
    
    Returns 1 if problem_id is None, otherwise calculates max attempt + 1.
    """
    if problem_id is None:
        return 1
    
    row = connection.execute(
        "SELECT COALESCE(MAX(attempt_number), 0) + 1 AS next_attempt "
        "FROM submissions WHERE user_id = %s AND problem_id = %s",
        (user_id, problem_id),
    ).fetchone()
    return int(row["next_attempt"])


def _update_user_streak(connection, user_id: int, submitted_at: str) -> None:
    """
    Update user's practice streak based on submission timestamp.
    
    Increments streak for consecutive daily submissions, resets otherwise.
    """
    today = date.fromisoformat(submitted_at[:10])
    row = connection.execute(
        "SELECT current_streak, last_submission_date FROM users WHERE id = %s",
        (user_id,)
    ).fetchone()
    if not row:
        return
    
    last_date_str = row["last_submission_date"]
    last_date = date.fromisoformat(last_date_str) if last_date_str else None
    
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


def _save_submission_to_db(
    connection,
    user_id: int,
    problem_id: Optional[int],
    verdict: str,
    detected_pattern: Optional[str],
    attempt_number: int,
    submitted_at: str,
    topic: str,
) -> int:
    """
    Save a submission record to the database.
    
    Returns the ID of the inserted submission.
    """
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
    return cursor.fetchone()["id"]


def create_submission(
    connection,
    user_id: int,
    problem_id: Optional[int],
    problem_data: Optional[Dict[str, Any]],
    verdict: str,
    submitted_at: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a submission and all related persistence records.
    
    This is the central submission persistence function used by both
    run_pipeline() and run_persistence() flows. It handles:
    1. Submission insertion into submissions table
    2. User streak updates
    3. Topic profile updates
    
    Returns a dict with submission_id, submission_record, topic, and pattern.
    """
    timestamp = submitted_at or iso_now()
    
    # Extract pattern and topic information
    topic = "unknown"
    pattern = None
    
    if problem_data and problem_id:
        patterns = parse_problem_pattern(problem_data)
        pattern = patterns[0] if patterns else None
        topic = pattern or "unknown"
    
    # Calculate attempt number
    attempt_number = _calculate_attempt_number(connection, user_id, problem_id)
    
    # Save submission to database
    submission_id = _save_submission_to_db(
        connection=connection,
        user_id=user_id,
        problem_id=problem_id,
        verdict=verdict,
        detected_pattern=pattern,
        attempt_number=attempt_number,
        submitted_at=timestamp,
        topic=topic,
    )
    
    # Update user streak
    _update_user_streak(connection, user_id, timestamp)
    
    # Get the submission record for return
    submission_record = connection.execute(
        "SELECT * FROM submissions WHERE id = %s", (submission_id,)
    ).fetchone()
    
    return {
        "submission_id": submission_id,
        "submission": dict(submission_record) if submission_record else None,
        "topic": topic,
        "pattern": pattern,
    }


def persist_submission(
    connection,
    user_id: int,
    problem_id: Optional[int],
    problem_difficulty: Optional[str],
    code: str,
    ast_output: Dict[str, Any],
    match_result: Dict[str, Any],
    groups: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Process the complete persistence pipeline for a submission.
    
    This function implements the full persistence logic that was
    previously split between run_pipeline() and run_persistence().
    
    It executes the complete flow:
    1. Submission insertion
    2. Gap signal persistence
    3. Elo persistence
    4. Recommendation creation
    
    Returns a dict with all persistence results for further processing.
    """
    timestamp = iso_now()
    
    # Determine submission verdict from match_result
    verdict = "pass" if match_result.get("match_result") in ("FULL_MATCH", "PARTIAL_MATCH") else "fail"
    
    # Get problem data for pattern and other contextual info
    problem_data = None
    if problem_id:
        row = connection.execute(
            "SELECT * FROM problems WHERE id = %s", (problem_id,)
        ).fetchone()
        if row:
            problem_data = dict(row)
    
    # Step 1: Create submission (handled by shared persistence logic)
    submission_result = create_submission(
        connection=connection,
        user_id=user_id,
        problem_id=problem_id,
        problem_data=problem_data,
        verdict=verdict,
        submitted_at=timestamp,
    )
    
    # Step 2: Process gap signals based on submission history and analysis results
    submission_history = load_submissions(connection, user_id)
    gap_output = _gap_engine.compute_signals(
        ast_output=ast_output.get("detected_patterns", []),
        match_result=match_result,
        user_id=user_id,
        submission_history=submission_history,
    )
    _gap_engine.persist_signals(connection, user_id, gap_output)
    
    # Step 3: Process Elo updates based on gap signals and match results
    current_elos = load_user_pattern_elo(connection, user_id)
    elo_output = _elo_engine.compute_updates(
        user_id=str(user_id),
        gap_signals=gap_output.get("gap_signals", []),
        match_result=match_result,
        ast_output=ast_output.get("detected_patterns", []),
        current_elos=current_elos,
    )
    _elo_engine.persist_elos(connection, user_id, elo_output)
    
    # Mark last recommendation acted on before creating new one
    _mark_last_recommendation_acted_on(connection, user_id)
    
    # Step 4: Create recommendation based on submission, problem, and context
    problem_record = problem_data if problem_id else None
    recommendation = get_recommendation(
        user_id, 
        {
            "submission": submission_result["submission"],
            "gap_info": get_gap_info(match_result, submission_result["topic"]),
        }, 
        problem_record,
        connection,
    )
    recommendation_id = _log_recommendation(connection, user_id, recommendation)
    
    return {
        "submission_id": submission_result["submission_id"],
        "submission_result": submission_result,
        "gap_output": gap_output,
        "elo_output": elo_output,
        "recommendation_id": recommendation_id,
    }


def get_gap_info(match_result: Dict[str, Any], topic: str) -> Dict[str, Any]:
    """
    Extract gap analysis information from match result for recommendation generation.
    
    Returns a dict with gap detection status and related details.
    """
    unmatched = match_result.get("unmatched_patterns", [])
    return {
        "gap_detected": bool(unmatched),
        "gap_pattern": unmatched[0] if unmatched else None,
        "matched_pattern": topic,
        "diagnosis_confidence": match_result.get("confidence_score", 0.0),
    }


def process_legacy_pipeline(
    user_id,
    problem_id,
    verdict,
    db_path=None,
):
    """
    Legacy run_pipeline() implementation that uses shared submission persistence.
    
    This maintains the original behavior for legacy compatibility while using
    the shared submission persistence logic.
    """
    from pathforge.db.db import connect
    
    with connect(db_path) as connection:
        try:
            # Use shared submission creation logic
            submission_result = create_submission(
                connection=connection,
                user_id=user_id,
                problem_id=problem_id,
                problem_data=None,  # Legacy pipeline doesn't have problem_data
                verdict="pass" if verdict == "solved" else "fail",
                submitted_at=iso_now(),
            )
            
            # Get problem record if needed
            problem_record = None
            if problem_id:
                row = connection.execute(
                    "SELECT * FROM problems WHERE id = %s", (problem_id,)
                ).fetchone()
                if row:
                    problem_record = dict(row)
            
            # Mark last recommendation acted on
            _mark_last_recommendation_acted_on(connection, user_id)
            
            # Create recommendation
            recommendation = get_recommendation(
                user_id, 
                submission_result, 
                problem_record, 
                connection
            )
            recommendation_id = _log_recommendation(connection, user_id, recommendation)
            
            # Commit all changes
            connection.commit()
            
            return {
                "submission": submission_result["submission"],
                "gap_info": {
                    "gap_detected": False,
                    "gap_pattern": None,
                    "matched_pattern": submission_result["topic"],
                    "diagnosis_confidence": 1.0,
                },
                "recommendation": recommendation,
                "explanation": recommendation.get("explanation", ""),
                "profile_update": None,
            }
        except Exception:
            connection.rollback()
            raise


# Import needed utilities at the bottom to avoid circular imports
from pathforge.api.services.loader import load_submissions, load_user_pattern_elo
from pathforge.recommender import get_recommendation
from pathforge.pipeline import _log_recommendation, _mark_last_recommendation_acted_on
