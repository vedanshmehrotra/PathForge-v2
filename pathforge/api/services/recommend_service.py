"""Recommendation orchestration — runs Recommendation Engine from stored data."""

from typing import Dict, Any, Optional
from pathforge.db.db import get_connection
from pathforge.api.services.loader import (
    load_problem_bank,
    load_submissions,
    load_gap_signals,
    load_user_pattern_elo,
    load_user_info,
)
from pathforge.recommendation_engine import RecommendationEngine
import config


def get_recommendations(user_id: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    connection = get_connection(db_path or config.DATABASE_PATH)
    try:
        user = load_user_info(connection, user_id)
        if not user:
            return {"error": f"User {user_id} not found", "stage": "RECOMMENDATION"}

        problems = load_problem_bank(connection)
        if not problems:
            return {"error": "No problems in bank", "stage": "RECOMMENDATION"}

        engine = RecommendationEngine(problems)

        elos = load_user_pattern_elo(connection, user_id)
        gaps = load_gap_signals(connection, user_id)
        subs = load_submissions(connection, user_id)

        sub_list = []
        for s in subs:
            sub_list.append({
                "detected_pattern": s.get("detected_pattern") or s.get("topic", ""),
                "verdict": s.get("verdict", ""),
                "problem_id": s.get("problem_id"),
                "submitted_at": s.get("submitted_at", ""),
            })

        result = engine.recommend(
            user_id=str(user_id),
            user_pattern_elo=elos if elos else None,
            gap_signals=gaps if gaps else None,
            recent_submissions=sub_list if sub_list else None,
        )

        return result
    except Exception as e:
        return {"error": str(e), "stage": "RECOMMENDATION"}
    finally:
        connection.close()
