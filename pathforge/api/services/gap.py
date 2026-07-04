"""Gap signal orchestration — loads stored gap signals from DB."""

from typing import Dict, Any, Optional
from pathforge.db.db import get_connection
from pathforge.api.services.loader import load_gap_signals, load_user_info
import config


def get_gap_signals(user_id: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    connection = get_connection(db_path or config.DATABASE_PATH)
    try:
        user = load_user_info(connection, user_id)
        if not user:
            return {"error": f"User {user_id} not found", "stage": "GAP"}

        signals = load_gap_signals(connection, user_id)

        strong = [s["pattern_id"] for s in signals if s["gap_strength"] >= 0.7]
        moderate = [s["pattern_id"] for s in signals if 0.4 <= s["gap_strength"] < 0.7]
        weak = [s["pattern_id"] for s in signals if s["gap_strength"] < 0.4]

        return {
            "gap_signals": signals,
            "summary": {
                "strong_gaps": strong,
                "moderate_gaps": moderate,
                "weak_gaps": weak,
            },
        }
    except Exception as e:
        return {"error": str(e), "stage": "GAP"}
    finally:
        connection.close()
