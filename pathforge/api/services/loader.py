"""Data loading service — bridges DB to engine inputs."""

import json
from typing import List, Dict, Any, Optional


def load_problem_bank(connection) -> List[Dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, title, difficulty, topics, pattern, link, acceptance_rate, category
        FROM problems
        ORDER BY id ASC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def load_submissions(connection, user_id: int) -> List[Dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, problem_id, verdict, detected_pattern, detected_confidence,
               expected_pattern, target_pattern, gap_identified, diagnosis_confidence,
               topic, attempt_number, submitted_at
        FROM submissions
        WHERE user_id = ?
        ORDER BY submitted_at ASC
        """,
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def load_gap_signals(connection, user_id: int) -> List[Dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT pattern_id, gap_strength, frequency, last_seen
        FROM gap_signals
        WHERE user_id = ?
        ORDER BY gap_strength DESC
        """,
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def load_user_pattern_elo(connection, user_id: int) -> Dict[str, float]:
    rows = connection.execute(
        """
        SELECT pattern_id, elo
        FROM user_pattern_elo
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchall()
    return {row["pattern_id"]: row["elo"] for row in rows}


def load_recent_match_results(connection, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, problem_id, verdict, detected_pattern, target_pattern,
               diagnosis_confidence, submitted_at
        FROM submissions
        WHERE user_id = ?
        ORDER BY submitted_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def load_user_info(connection, user_id: int) -> Optional[Dict[str, Any]]:
    row = connection.execute(
        "SELECT id, username, experience_level, confident_areas, current_streak FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return dict(row) if row else None
