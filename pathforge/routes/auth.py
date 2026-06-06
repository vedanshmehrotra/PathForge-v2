from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
import json

from flask import Blueprint, current_app, jsonify, request

from pathforge.db.db import get_connection
from pathforge.db.profile_manager import (
    BROAD_TOPIC_PATTERNS,
    EXPERIENCE_BASELINES,
    iso_now,
    normalize_confident_areas,
    seed_initial_topic_profiles,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def success(data, status=200):
    """Return a consistent successful JSON response."""
    return jsonify({"success": True, "data": data}), status


def error(message, status=400):
    """Return a consistent error JSON response."""
    return jsonify({"success": False, "error": message}), status


def require_auth(view):
    """Require a valid Bearer JWT before executing an API route."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return error("Missing bearer token", 401)
        try:
            payload = jwt.decode(header.removeprefix("Bearer ").strip(), _jwt_secret(), algorithms=["HS256"])
        except jwt.PyJWTError:
            return error("Invalid or expired token", 401)
        request.user_id = int(payload["sub"])
        return view(*args, **kwargs)

    return wrapped


@auth_bp.post("/register")
def register():
    """Create a user and return a JWT token."""
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    display_name = (payload.get("display_name") or username).strip()
    experience_level = (payload.get("experience_level") or "beginner").strip().lower()
    confident_areas = normalize_confident_areas(payload.get("confident_areas") or [])
    if not username or not email or not password:
        return error("username, email, and password are required")
    if experience_level not in EXPERIENCE_BASELINES:
        return error("experience_level must be beginner, intermediate, or advanced")

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    now = iso_now()
    connection = get_connection(current_app.config.get("DATABASE_PATH"))
    try:
        cursor = connection.execute(
            """
            INSERT INTO users (
                username, email, password_hash, display_name,
                experience_level, confident_areas, onboarding_complete,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (username, email, password_hash, display_name, experience_level, json.dumps(confident_areas), now, now),
        )
        connection.commit()
    except Exception:
        return error("Username or email already exists", 409)

    user_id = cursor.lastrowid
    seed = seed_initial_topic_profiles(connection, user_id, experience_level, confident_areas, seeded_at=now)
    return success({
        "user_id": user_id,
        "token": _make_token(user_id),
        "username": username,
        "onboarding_complete": False,
        "seed": seed,
    }, 201)


@auth_bp.post("/login")
def login():
    """Validate credentials and return a JWT token."""
    payload = request.get_json(silent=True) or {}
    username_or_email = (payload.get("username") or payload.get("email") or "").strip()
    password = payload.get("password") or ""
    if not username_or_email or not password:
        return error("username/email and password are required")

    connection = get_connection(current_app.config.get("DATABASE_PATH"))
    row = connection.execute(
        "SELECT * FROM users WHERE username = ? OR email = ?",
        (username_or_email, username_or_email.lower()),
    ).fetchone()
    if not row or not bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
        return error("Invalid credentials", 401)

    return success({
        "user_id": row["id"],
        "token": _make_token(row["id"]),
        "username": row["username"],
        "onboarding_complete": bool(row["onboarding_complete"]),
    })


def _make_token(user_id):
    """Create a signed JWT for a user."""
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(days=7)}
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def _jwt_secret():
    """Return the configured JWT signing secret."""
    return current_app.config["JWT_SECRET"]


@auth_bp.get("/onboarding/diagnostic")
@require_auth
def diagnostic():
    """Return the next onboarding diagnostic problem for the authenticated user."""
    connection = get_connection(current_app.config.get("DATABASE_PATH"))
    user = connection.execute("SELECT confident_areas, onboarding_complete FROM users WHERE id = ?", (request.user_id,)).fetchone()
    if not user:
        return error("User not found", 404)
    confident = json.loads(user["confident_areas"] or "[]")
    problems = _diagnostic_problems(connection, request.user_id, confident)
    submitted_ids = {
        row["problem_id"] for row in connection.execute(
            "SELECT DISTINCT problem_id FROM submissions WHERE user_id = ? AND problem_id IS NOT NULL",
            (request.user_id,),
        ).fetchall()
    }
    remaining = [problem for problem in problems if problem["id"] not in submitted_ids]
    if not remaining:
        connection.execute("UPDATE users SET onboarding_complete = 1, updated_at = ? WHERE id = ?", (iso_now(), request.user_id))
        connection.commit()
        return success({"complete": True, "problem": None, "remaining": 0, "total": len(problems)})
    return success({"complete": False, "problem": remaining[0], "remaining": len(remaining), "total": len(problems)})


def _diagnostic_problems(connection, user_id, confident_areas):
    """Pick one Easy problem from up to five broad areas the user did not mark confident."""
    confident = set(confident_areas or [])
    area_order = [area for area in BROAD_TOPIC_PATTERNS if area not in confident] + [area for area in BROAD_TOPIC_PATTERNS if area in confident]
    selected = []
    seen_ids = set()
    for area in area_order:
        if len(selected) >= 5:
            break
        patterns = sorted(BROAD_TOPIC_PATTERNS[area])
        where = " OR ".join(["pattern LIKE ?" for _ in patterns])
        row = connection.execute(
            f"""
            SELECT * FROM problems
            WHERE difficulty = 'Easy' AND ({where})
            ORDER BY COALESCE(acceptance_rate, 0) DESC, id ASC
            LIMIT 1
            """,
            [f'%"{pattern}"%' for pattern in patterns],
        ).fetchone()
        if row and row["id"] not in seen_ids:
            problem = dict(row)
            problem["target_pattern"] = json.loads(problem["pattern"])[0]
            problem["area"] = area
            selected.append(problem)
            seen_ids.add(problem["id"])
    return selected
