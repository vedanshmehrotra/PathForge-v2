from flask import Blueprint, current_app, request

from pathforge.pipeline import run_pipeline
from pathforge.routes.auth import error, require_auth, success

submissions_bp = Blueprint("submissions", __name__, url_prefix="/api")


@submissions_bp.post("/submit")
@require_auth
def submit():
    """Submit source code to the PathForge pipeline and return the full result."""
    payload = request.get_json(silent=True) or {}
    required = ("user_id", "source_code", "language", "verdict", "target_pattern")
    if any(payload.get(key) in (None, "") for key in required):
        return error("user_id, source_code, language, verdict, and target_pattern are required")
    if int(payload["user_id"]) != request.user_id:
        return error("Token user does not match submitted user_id", 403)

    try:
        result = run_pipeline(
            user_id=int(payload["user_id"]),
            problem_id=int(payload["problem_id"]) if payload.get("problem_id") else None,
            source_code=payload["source_code"],
            language=payload["language"],
            verdict=payload["verdict"],
            target_pattern=payload["target_pattern"],
            db_path=current_app.config.get("DATABASE_PATH"),
        )
    except Exception as exc:
        return error(str(exc), 400)
    return success(result)
