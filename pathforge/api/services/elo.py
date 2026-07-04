"""Elo orchestration — loads stored Elo ratings from DB."""

from typing import Dict, Any, Optional
from pathforge.db.db import get_connection
from pathforge.api.services.loader import load_user_pattern_elo, load_user_info
import config


def get_elo_ratings(user_id: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    connection = get_connection(db_path or config.DATABASE_PATH)
    try:
        user = load_user_info(connection, user_id)
        if not user:
            return {"error": f"User {user_id} not found", "stage": "ELO"}

        elos = load_user_pattern_elo(connection, user_id)
        if not elos:
            return {"pattern_elo": {}, "message": "No Elo ratings yet. Submit code to initialize."}

        sorted_patterns = sorted(elos.items(), key=lambda x: x[1])
        weakest = [p for p, _ in sorted_patterns[:5]]
        strongest = [p for p, _ in sorted_patterns[-5:]]

        return {
            "pattern_elo": elos,
            "summary": {
                "average_elo": round(sum(elos.values()) / max(len(elos), 1), 2),
                "weakest_patterns": weakest,
                "strongest_patterns": strongest,
            },
        }
    except Exception as e:
        return {"error": str(e), "stage": "ELO"}
    finally:
        connection.close()
