import json

from flask import Blueprint, current_app, request

from pathforge.db.db import connect
from pathforge.routes.auth import error, require_auth, success

problems_bp = Blueprint("problems", __name__, url_prefix="/api")


@problems_bp.get("/problems")
@require_auth
def list_problems():
    """Return paginated problems with optional difficulty, topic, and title search filters."""
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)
    difficulty = request.args.get("difficulty")
    topic = request.args.get("topic")
    search = request.args.get("search")
    where, params = _problem_filters(difficulty, topic, search)
    offset = (page - 1) * per_page
    with connect(current_app.config.get("DATABASE_PATH")) as connection:
        rows = connection.execute(
            f"""
            SELECT id, title, difficulty, topics, pattern, link, acceptance_rate
            FROM problems
            {where}
            ORDER BY id ASC
            LIMIT ? OFFSET ?
            """,
            (*params, per_page, offset),
        ).fetchall()
        total = connection.execute(f"SELECT COUNT(*) AS total FROM problems {where}", params).fetchone()["total"]
        return success({"items": [dict(row) for row in rows], "page": page, "per_page": per_page, "total": total})


@problems_bp.get("/problems/<int:problem_id>")
@require_auth
def get_problem(problem_id):
    """Return one problem record with test case count but without test case bodies."""
    with connect(current_app.config.get("DATABASE_PATH")) as connection:
        row = connection.execute("SELECT * FROM problems WHERE id = ?", (problem_id,)).fetchone()
        if not row:
            return error("Problem not found", 404)
        problem = dict(row)
        try:
            problem["test_case_count"] = len(json.loads(problem.get("test_cases") or "[]"))
        except json.JSONDecodeError:
            problem["test_case_count"] = 0
        problem.pop("test_cases", None)
        return success(problem)


def _problem_filters(difficulty, topic, search):
    """Build a parameterized SQL filter clause for problem queries."""
    clauses = []
    params = []
    if difficulty:
        clauses.append("difficulty = ?")
        params.append(difficulty)
    if topic:
        clauses.append("topics LIKE ?")
        params.append(f"%{topic}%")
    if search:
        clauses.append("title LIKE ?")
        params.append(f"%{search}%")
    return ("WHERE " + " AND ".join(clauses) if clauses else ""), tuple(params)
