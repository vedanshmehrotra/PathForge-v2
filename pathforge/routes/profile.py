import json

from flask import Blueprint, current_app, request

from pathforge.db.db import get_connection
from pathforge.db.profile_manager import get_user_profile, get_weakest_topics, iso_now
from pathforge.pattern_links import leetcode_url, pattern_options
from pathforge.recommender import _difficulty_from_elo, _select_problem
from pathforge.routes.auth import error, require_auth, success

profile_bp = Blueprint("profile", __name__, url_prefix="/api")


@profile_bp.get("/profile/<int:user_id>")
@require_auth
def profile(user_id):
    """Return topic profiles, overall Elo, weakest topics, and recent submissions."""
    if user_id != request_user_id():
        return error("Forbidden", 403)
    connection = get_connection(current_app.config.get("DATABASE_PATH"))
    profiles = get_user_profile(connection, user_id)
    recent = connection.execute(
        """
        SELECT s.id, s.problem_id, COALESCE(p.title, s.topic) AS title, s.verdict, s.detected_pattern,
               s.expected_pattern, s.gap_identified, s.diagnosis_confidence,
               s.topic, s.submitted_at
        FROM submissions s
        LEFT JOIN problems p ON p.id = s.problem_id
        WHERE s.user_id = ?
        ORDER BY s.submitted_at DESC
        LIMIT 10
        """,
        (user_id,),
    ).fetchall()
    return success({
        "profiles": profiles,
        "overall_elo": _overall_elo(profiles),
        "weakest_topics": get_weakest_topics(connection, user_id, limit=5),
        "recent_submissions": [dict(row) for row in recent],
        "stats": _stats(connection, user_id),
    })


@profile_bp.get("/recommend/<int:user_id>")
@require_auth
def recommend(user_id):
    """Return the next recommended problem for a user without requiring a new submission."""
    if user_id != request_user_id():
        return error("Forbidden", 403)
    connection = get_connection(current_app.config.get("DATABASE_PATH"))
    refresh = request.args.get("refresh", "").lower() == "true"
    active = None if refresh else _active_recommendation(connection, user_id)
    if active:
        return success(active)
    if refresh:
        _clear_active_recommendation(connection, user_id)

    weakest = get_weakest_topics(connection, user_id, limit=33)
    topic = "hash_map_lookup"
    difficulty = "Easy"
    problem = None

    for w in weakest:
        t = w["topic"]
        d = _difficulty_from_elo(float(w["elo_rating"]))
        p = _select_problem(user_id, t, d, db_path=current_app.config.get("DATABASE_PATH"))
        if p:
            topic, difficulty, problem = t, d, p
            break

    if not problem and weakest:
        t = weakest[0]["topic"]
        for d in ("Easy", "Medium", "Hard"):
            p = _select_problem(user_id, t, d, db_path=current_app.config.get("DATABASE_PATH"))
            if p:
                topic, difficulty, problem = t, d, p
                break

    if not problem:
        p = _first_unsolved_problem(connection, user_id)
        if p:
            topic = json.loads(p["pattern"])[0]
            difficulty = p["difficulty"]
            problem = p
        else:
            return error("No unsolved problems available", 404)
    explanation = f"Practice {topic.replace('_', ' ')} at {difficulty} level. Pick any LeetCode problem from the linked list, solve it there, then paste your Python solution here."
    recommendation_id = _log_recommendation(connection, user_id, problem, topic, explanation)
    return success({
        "tier": "specific",
        "confidence_tier": "specific",
        "problem": problem,
        "explanation": explanation,
        "confidence": 0.0,
        "topic": topic,
        "pattern": topic,
        "pattern_label": topic.replace("_", " "),
        "difficulty": difficulty,
        "leetcode_url": leetcode_url(topic, difficulty),
        "patterns": pattern_options(),
        "id": recommendation_id,
        "returning": False,
    })


def request_user_id():
    """Return the authenticated user id placed on the request by require_auth."""
    from flask import request
    return request.user_id


def _overall_elo(profiles):
    """Return average Elo across topic profiles."""
    if not profiles:
        return 800.0
    return round(sum(float(row["elo_rating"]) for row in profiles) / len(profiles), 2)


def _stats(connection, user_id):
    """Return aggregate dashboard statistics for a user."""
    total = connection.execute("SELECT COUNT(*) AS count FROM submissions WHERE user_id = ?", (user_id,)).fetchone()["count"]
    solved = connection.execute(
        "SELECT COUNT(DISTINCT problem_id) AS count FROM submissions WHERE user_id = ? AND verdict = 'pass' AND gap_identified = 0",
        (user_id,),
    ).fetchone()["count"]
    accuracy_rows = connection.execute(
        """
        SELECT p.difficulty, AVG(CASE WHEN s.verdict = 'pass' THEN 1.0 ELSE 0.0 END) AS accuracy
        FROM submissions s
        JOIN problems p ON p.id = s.problem_id
        WHERE s.user_id = ?
        GROUP BY p.difficulty
        """,
        (user_id,),
    ).fetchall()
    streak_row = connection.execute("SELECT current_streak FROM users WHERE id = ?", (user_id,)).fetchone()
    rates = {row["difficulty"]: round(float(row["accuracy"] or 0), 2) for row in accuracy_rows}
    return {
        "total_submissions": total,
        "total_solved": solved,
        "current_streak": int(streak_row["current_streak"] or 0) if streak_row else 0,
        "accuracy_by_difficulty": rates,
        "pass_rate_by_difficulty": {difficulty: rates.get(difficulty, 0.0) for difficulty in ("Easy", "Medium", "Hard")},
    }


def _current_streak(connection, user_id):
    """Return consecutive latest passing submissions before the first non-pass."""
    rows = connection.execute(
        "SELECT verdict, gap_identified FROM submissions WHERE user_id = ? ORDER BY submitted_at DESC LIMIT 50",
        (user_id,),
    ).fetchall()
    streak = 0
    for row in rows:
        if row["verdict"] == "pass" and row["gap_identified"] == 0:
            streak += 1
        else:
            break
    return streak


def _first_available_topic(connection):
    """Return the first topic in the problem bank."""
    row = connection.execute("SELECT topics FROM problems ORDER BY id ASC LIMIT 1").fetchone()
    return row["topics"].split(",")[0].strip() if row else None


def _first_unsolved_problem(connection, user_id):
    """Return the first problem the user has not solved correctly."""
    row = connection.execute(
        """
        SELECT p.*
        FROM problems p
        WHERE NOT EXISTS (
            SELECT 1 FROM submissions s
            WHERE s.user_id = ? AND s.problem_id = p.id AND s.verdict = 'pass' AND s.gap_identified = 0
        )
        ORDER BY p.difficulty ASC, COALESCE(p.acceptance_rate, 0) DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    return dict(row) if row else None


def _log_recommendation(connection, user_id, problem, topic, explanation):
    """Persist a standalone recommendation row."""
    cursor = connection.execute(
        """
        INSERT INTO recommendations (user_id, problem_id, topic, reason, confidence_tier, created_at)
        VALUES (?, ?, ?, ?, 'specific', ?)
        """,
        (user_id, problem["id"] if problem else None, topic, explanation, iso_now()),
    )
    recommendation_id = cursor.lastrowid
    connection.execute("UPDATE users SET last_recommendation_id = ?, updated_at = ? WHERE id = ?", (recommendation_id, iso_now(), user_id))
    connection.commit()
    return recommendation_id


def _active_recommendation(connection, user_id):
    """Return the user's last unacted recommendation, if one exists."""
    row = connection.execute(
        """
        SELECT r.*, p.difficulty AS problem_difficulty
        FROM users u
        JOIN recommendations r ON r.id = u.last_recommendation_id
        LEFT JOIN problems p ON p.id = r.problem_id
        WHERE u.id = ? AND r.user_id = ? AND r.acted_on = 0
        """,
        (user_id, user_id),
    ).fetchone()
    if not row:
        return None
    topic = row["topic"]
    difficulty = row["problem_difficulty"] or _difficulty_from_elo(_topic_elo(connection, user_id, topic))
    problem = connection.execute("SELECT * FROM problems WHERE id = ?", (row["problem_id"],)).fetchone() if row["problem_id"] else None
    return {
        "tier": row["confidence_tier"],
        "confidence_tier": row["confidence_tier"],
        "problem": dict(problem) if problem else None,
        "explanation": row["reason"],
        "confidence": 0.0,
        "topic": topic,
        "pattern": topic,
        "pattern_label": topic.replace("_", " "),
        "difficulty": difficulty,
        "leetcode_url": leetcode_url(topic, difficulty),
        "patterns": pattern_options(),
        "id": row["id"],
        "returning": True,
    }


def _topic_elo(connection, user_id, topic):
    row = connection.execute(
        "SELECT elo_rating FROM topic_profiles WHERE user_id = ? AND topic = ?",
        (user_id, topic),
    ).fetchone()
    return float(row["elo_rating"]) if row else 800.0


def _clear_active_recommendation(connection, user_id):
    row = connection.execute("SELECT last_recommendation_id FROM users WHERE id = ?", (user_id,)).fetchone()
    if row and row["last_recommendation_id"] is not None:
        connection.execute(
            "UPDATE recommendations SET acted_on = 1, acted_on_at = ? WHERE id = ? AND user_id = ?",
            (iso_now(), row["last_recommendation_id"], user_id),
        )
    connection.execute("UPDATE users SET last_recommendation_id = NULL, updated_at = ? WHERE id = ?", (iso_now(), user_id))
    connection.commit()
