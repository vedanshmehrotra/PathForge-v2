import logging

from pathforge.db.profile_manager import get_weakest_topics
from pathforge.pattern_links import leetcode_url

logger = logging.getLogger(__name__)

SPECIFIC_THRESHOLD = 0.75
HINT_THRESHOLD = 0.55
DIFFICULTY_ORDER = ["Easy", "Medium", "Hard"]


def get_recommendation(user_id, submission_result, problem_record, connection):
    """Return a confidence-gated recommendation for a completed submission."""
    gap_info = submission_result["gap_info"]
    submission = submission_result["submission"]
    current_problem_id = submission["problem_id"]
    companion_mode = problem_record is None
    pattern = gap_info.get("gap_pattern") or gap_info.get("matched_pattern") or submission.get("detected_pattern") or "hash_map_lookup"
    topic = pattern
    confidence = gap_info["diagnosis_confidence"]

    if companion_mode:
        difficulty = _difficulty_for_user(connection, user_id, pattern)
        explanation = _build_explanation("topic_hint", gap_info, None, topic=pattern, no_gap=not gap_info["gap_detected"])
        return _recommendation("topic_hint", None, explanation, confidence, pattern, difficulty, pattern)

    if not gap_info["gap_detected"] and submission["verdict"] == "pass":
        if _check_pattern_lock(connection, user_id, topic, "pass"):
            new_topic = _rotate_topic(connection, user_id, topic)
            difficulty = _difficulty_for_user(connection, user_id, new_topic)
            problem = _select_problem(connection, user_id, new_topic, difficulty)
            tier = "specific" if problem else "topic_hint"
            explanation = _build_explanation("rotate", gap_info, problem, topic=new_topic, old_topic=topic, verdict="pass")
            return _recommendation(tier, problem, explanation, confidence, new_topic, difficulty, new_topic)
        difficulty = _move_difficulty(problem_record["difficulty"], 1)
        problem = _select_problem(connection, user_id, topic, difficulty, exclude_problem_id=current_problem_id)
        if not problem:
            new_topic = _rotate_topic(connection, user_id, topic)
            if new_topic != topic:
                difficulty = _difficulty_for_user(connection, user_id, new_topic)
                problem = _select_problem(connection, user_id, new_topic, difficulty)
                tier = "specific" if problem else "topic_hint"
                explanation = _build_explanation("rotate", gap_info, problem, topic=new_topic, old_topic=topic, verdict="pass")
                return _recommendation(tier, problem, explanation, confidence, new_topic, difficulty, new_topic)
        tier = "specific" if problem else "topic_hint"
        explanation = _build_explanation(tier, gap_info, problem, topic=topic, no_gap=True, verdict="pass")
        return _recommendation(tier, problem, explanation, confidence, topic, difficulty, topic)

    if not gap_info["gap_detected"]:
        if _check_pattern_lock(connection, user_id, topic, "fail"):
            new_topic = _rotate_topic(connection, user_id, topic)
            difficulty = _difficulty_for_user(connection, user_id, new_topic)
            problem = _select_problem(connection, user_id, new_topic, difficulty)
            tier = "specific" if problem else "topic_hint"
            explanation = _build_explanation("rotate", gap_info, problem, topic=new_topic, old_topic=topic, verdict="fail")
            return _recommendation(tier, problem, explanation, confidence, new_topic, difficulty, new_topic)
        difficulty = _move_difficulty(problem_record["difficulty"], -1 if submission["verdict"] != "pass" else 0)
        problem = _select_problem(connection, user_id, topic, difficulty, exclude_problem_id=current_problem_id)
        if not problem and submission["verdict"] != "pass":
            new_topic = _rotate_topic(connection, user_id, topic)
            if new_topic != topic:
                difficulty = _difficulty_for_user(connection, user_id, new_topic)
                problem = _select_problem(connection, user_id, new_topic, difficulty)
                tier = "specific" if problem else "topic_hint"
                explanation = _build_explanation("rotate", gap_info, problem, topic=new_topic, old_topic=topic, verdict="fail")
                return _recommendation(tier, problem, explanation, confidence, new_topic, difficulty, new_topic)
        tier = "specific" if problem else "topic_hint"
        explanation = _build_explanation(tier, gap_info, problem, topic=topic, no_gap=True, verdict="fail")
        return _recommendation(tier, problem, explanation, confidence, topic, difficulty, topic)

    if confidence >= SPECIFIC_THRESHOLD:
        difficulty = _difficulty_for_user(connection, user_id, topic)
        problem = _select_problem(connection, user_id, topic, difficulty, exclude_problem_id=current_problem_id)
        selected_topic = topic
        if not problem:
            fallback = get_weakest_topics(connection, user_id, limit=33)
            for fb in fallback:
                ft = fb["topic"]
                if ft == selected_topic:
                    continue
                fd = _difficulty_from_elo(float(fb["elo_rating"]))
                p = _select_problem(connection, user_id, ft, fd, exclude_problem_id=current_problem_id)
                if p:
                    selected_topic = ft
                    difficulty = fd
                    problem = p
                    break
        tier = "specific" if problem else "topic_hint"
        explanation = _build_explanation(tier, gap_info, problem, topic=selected_topic)
        return _recommendation(tier, problem, explanation, confidence, selected_topic, difficulty, selected_topic)

    if confidence >= HINT_THRESHOLD:
        explanation = _build_explanation("topic_hint", gap_info, None, topic=topic)
        return _recommendation("topic_hint", None, explanation, confidence, topic, _difficulty_for_user(connection, user_id, topic), topic)

    explanation = _build_explanation("general_hint", gap_info, None, topic=topic)
    return _recommendation("general_hint", None, explanation, confidence, topic, _difficulty_for_user(connection, user_id, topic), topic)


def _select_problem(connection, user_id, topic, difficulty, exclude_problem_id=None):
    """Select the highest-acceptance unsolved problem for a topic and difficulty."""
    row = connection.execute(
        """
        SELECT p.*
        FROM problems p
        WHERE p.difficulty = ?
          AND (p.topics LIKE ? OR json_extract(p.pattern, '$[0]') = ?)
          AND (? IS NULL OR p.id != ?)
          AND NOT EXISTS (
              SELECT 1
              FROM submissions s
              WHERE s.user_id = ?
                AND s.problem_id = p.id
                AND s.verdict = 'pass'
                AND s.gap_identified = 0
          )
        ORDER BY COALESCE(p.acceptance_rate, 0) DESC, p.id ASC
        LIMIT 1
        """,
        (difficulty, f"%{topic}%", topic, exclude_problem_id, exclude_problem_id, user_id),
    ).fetchone()
    return dict(row) if row else None


def _check_pattern_lock(connection, user_id, topic, verdict):
    """Return True if the user has 3+ consecutive passes or fails on the same topic."""
    if verdict == "pass":
        rows = connection.execute(
            """SELECT verdict FROM submissions
               WHERE user_id = ? AND topic = ?
               ORDER BY submitted_at DESC LIMIT 3""",
            (user_id, topic),
        ).fetchall()
        if len(rows) >= 3 and all(r["verdict"] == "pass" for r in rows):
            return True
    elif verdict == "fail":
        row = connection.execute(
            "SELECT recent_failures FROM topic_profiles WHERE user_id = ? AND topic = ?",
            (user_id, topic),
        ).fetchone()
        if row and int(row["recent_failures"]) >= 3:
            return True
    return False


def _rotate_topic(connection, user_id, exclude_topic):
    """Pick the weakest topic with available problems, different from exclude_topic."""
    weakest = get_weakest_topics(connection, user_id, limit=33)
    for w in weakest:
        candidate = w["topic"]
        if candidate == exclude_topic:
            continue
        difficulty = _difficulty_from_elo(float(w["elo_rating"]))
        problem = _select_problem(connection, user_id, candidate, difficulty)
        if problem:
            return candidate
        logger.info(
            "_rotate_topic: skipped topic '%s' (no available problem at %s for user %s)",
            candidate, difficulty, user_id,
        )
    logger.warning(
        "_rotate_topic: no viable topic found for user %s, falling back to '%s'",
        user_id, exclude_topic,
    )
    return exclude_topic


def _build_explanation(tier, gap_info, problem, topic=None, old_topic=None, no_gap=False, verdict=None):
    """Build a human-readable explanation for the recommendation result."""
    focus = gap_info.get("gap_pattern") or gap_info.get("matched_pattern") or "the core pattern"
    readable_focus = focus.replace("_", " ")
    readable_topic = (topic or "this pattern").replace("_", " ")

    if tier == "rotate":
        readable_old = (old_topic or "the previous topic").replace("_", " ")
        if verdict == "fail":
            return f"{readable_focus} is tough. Let's practice {readable_topic} and come back stronger."
        return f"Nice streak on {readable_old}! Switching to {readable_topic}, your weakest area."

    if no_gap:
        if verdict == "pass":
            return f"Nice work on {readable_topic}. Keep up the momentum!"
        return f"{readable_topic} needs more practice. Try this problem to build confidence."

    if tier == "specific" and problem:
        return f"Practice {readable_focus} next using the linked LeetCode problem list."
    if tier == "topic_hint":
        return (
            f"Your result suggests a possible gap in {readable_topic}. "
            f"Review {readable_focus} before moving to another problem."
        )
    return f"Focus on the fundamentals of {readable_topic} before taking on a more targeted recommendation."


def _recommendation(tier, problem, explanation, confidence, topic, difficulty, pattern):
    """Return the normalized recommendation dictionary."""
    return {
        "tier": tier,
        "confidence_tier": tier,
        "problem": problem,
        "explanation": explanation,
        "confidence": round(float(confidence), 2),
        "topic": topic,
        "pattern": pattern,
        "pattern_label": pattern.replace("_", " "),
        "difficulty": difficulty,
        "leetcode_url": leetcode_url(pattern, difficulty),
    }


def gap_info_pattern(problem, topic):
    """Return the recommended pattern identifier."""
    return topic if topic else (problem["pattern"] if problem else "hash_map_lookup")


def _difficulty_for_user(connection, user_id, topic):
    """Return target difficulty for a user's current topic Elo."""
    row = connection.execute(
        "SELECT elo_rating FROM topic_profiles WHERE user_id = ? AND topic = ?",
        (user_id, topic),
    ).fetchone()
    elo = float(row["elo_rating"]) if row else 800.0
    return _difficulty_from_elo(elo)


def _difficulty_from_elo(elo_rating):
    """Map a topic Elo rating to an appropriate problem difficulty."""
    if elo_rating < 1000:
        return "Easy"
    if elo_rating <= 1300:
        return "Medium"
    return "Hard"


def _move_difficulty(difficulty, delta):
    """Move a difficulty up or down by one bounded tier."""
    index = DIFFICULTY_ORDER.index(difficulty)
    return DIFFICULTY_ORDER[max(0, min(len(DIFFICULTY_ORDER) - 1, index + delta))]


def _topic_from_problem(problem_record):
    """Return the first topic from a problem record's comma-separated topics."""
    return problem_record["topics"].split(",")[0].strip()


