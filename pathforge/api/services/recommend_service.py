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


DIFFICULTY_ORDER = ["Easy", "Medium", "Hard"]


def _build_problem_lookup(problems):
    lookup = {}
    for p in problems:
        pid = str(p.get("id", ""))
        if pid:
            lookup[pid] = {
                "title": p.get("title", ""),
                "difficulty": p.get("difficulty", "Easy"),
            }
    return lookup


def _difficulty_to_label(difficulty_score: float) -> str:
    """Reverse-map a 0-1 difficulty_score back to Easy/Medium/Hard."""
    idx = round(difficulty_score * (len(DIFFICULTY_ORDER) - 1))
    return DIFFICULTY_ORDER[min(idx, len(DIFFICULTY_ORDER) - 1)]


def get_recommendations(user_id: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    connection = get_connection(db_path or config.DATABASE_PATH)
    try:
        user = load_user_info(connection, user_id)
        if not user:
            return {"error": f"User {user_id} not found", "stage": "RECOMMENDATION"}

        problems = load_problem_bank(connection)
        if not problems:
            return {"error": "No problems in bank", "stage": "RECOMMENDATION"}

        problem_lookup = _build_problem_lookup(problems)
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

        raw_recs = result.get("recommended_problems", [])
        recommendations = []
        for r in raw_recs:
            pid = str(r.get("problem_id", ""))
            pdata = problem_lookup.get(pid, {})
            target_patterns = r.get("target_patterns", [])
            recommendations.append({
                "problem_id": pid,
                "title": pdata.get("title", r.get("title", "")),
                "difficulty": pdata.get("difficulty", _difficulty_to_label(r.get("difficulty_score", 0.5))),
                "pattern": target_patterns[0] if target_patterns else "",
                "reason": r.get("reason", ""),
                "score": round(r.get("expected_learning_gain", 0.0) * 100, 1),
            })

        return {
            "user_id": user_id,
            "recommendations": recommendations[:5],
            "summary": {
                "primary_weak_patterns": result.get("summary", {}).get("primary_weak_patterns", []),
                "focus_area": result.get("summary", {}).get("focus_area", ""),
                "recommendation_strategy": result.get("summary", {}).get("recommendation_strategy", ""),
            },
        }
    except Exception as e:
        return {"error": str(e), "stage": "RECOMMENDATION"}
    finally:
        connection.close()
