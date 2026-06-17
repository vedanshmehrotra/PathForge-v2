from flask import Blueprint, current_app, request

from pathforge.pipeline import run_pipeline
from pathforge.routes.auth import error, require_auth, success

submissions_bp = Blueprint("submissions", __name__, url_prefix="/api")


@submissions_bp.post("/submit")
@require_auth
def submit():
    payload = request.get_json(silent=True) or {}
    required = ("user_id", "problem_id", "verdict")
    if any(payload.get(key) in (None, "") for key in required):
        return error("user_id, problem_id, and verdict are required")
    if int(payload["user_id"]) != request.user_id:
        return error("Token user does not match submitted user_id", 403)
    verdict = payload["verdict"]
    if verdict not in ("solved", "unsolved"):
        return error("verdict must be 'solved' or 'unsolved'")

    try:
        result = run_pipeline(
            user_id=int(payload["user_id"]),
            problem_id=int(payload["problem_id"]),
            verdict=verdict,
            db_path=current_app.config.get("DATABASE_PATH"),
        )
    except Exception as exc:
        return error(str(exc), 400)

    profile_update = result.get("profile_update")
    elo_change = None
    if profile_update:
        elo_change = round(profile_update["elo_after"] - profile_update["elo_before"], 2)

    rec = result["recommendation"]
    return success({
        "verdict": verdict,
        "pattern_updated": profile_update["topic"] if profile_update else None,
        "elo_change": elo_change,
        "next_recommendation": rec,
        "explanation": result["explanation"],
    })
