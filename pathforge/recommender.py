from pathforge.db.db import get_connection
from pathforge.db.profile_manager import get_weakest_topics
from pathforge.pattern_links import leetcode_url

SPECIFIC_THRESHOLD = 0.75
HINT_THRESHOLD = 0.55
DIFFICULTY_ORDER = ["Easy", "Medium", "Hard"]


def get_recommendation(user_id, submission_result, problem_record, db_path=None):
    """Return a confidence-gated recommendation for a completed submission."""
    connection = get_connection(db_path)
    gap_info = submission_result["gap_info"]
    submission = submission_result["submission"]
    current_problem_id = submission["problem_id"]
    companion_mode = problem_record is None
    pattern = gap_info.get("gap_pattern") or gap_info.get("matched_pattern") or submission.get("detected_pattern") or "hash_map_lookup"
    topic = pattern if companion_mode else _topic_from_problem(problem_record)
    confidence = gap_info["diagnosis_confidence"]

    if companion_mode:
        difficulty = _difficulty_for_user(connection, user_id, pattern)
        explanation = _build_explanation("topic_hint", gap_info, None, topic=pattern, no_gap=not gap_info["gap_detected"])
        return _recommendation("topic_hint", None, explanation, confidence, pattern, difficulty, pattern)

    if not gap_info["gap_detected"] and submission["verdict"] == "pass":
        difficulty = _move_difficulty(problem_record["difficulty"], 1)
        problem = _select_problem(user_id, topic, difficulty, db_path=db_path, exclude_problem_id=current_problem_id)
        tier = "specific" if problem else "topic_hint"
        explanation = _build_explanation(tier, gap_info, problem, topic=topic, no_gap=True)
        return _recommendation(tier, problem, explanation, confidence, topic, difficulty, topic)

    if not gap_info["gap_detected"]:
        difficulty = _move_difficulty(problem_record["difficulty"], -1 if submission["verdict"] != "pass" else 0)
        problem = _select_problem(user_id, topic, difficulty, db_path=db_path, exclude_problem_id=current_problem_id)
        tier = "specific" if problem else "topic_hint"
        explanation = _build_explanation(tier, gap_info, problem, topic=topic, no_gap=True)
        return _recommendation(tier, problem, explanation, confidence, topic, difficulty, topic)

    if confidence >= SPECIFIC_THRESHOLD:
        difficulty = _difficulty_for_user(connection, user_id, topic)
        problem = _select_problem(user_id, topic, difficulty, db_path=db_path, exclude_problem_id=current_problem_id)
        selected_topic = topic
        if not problem:
            fallback = get_weakest_topics(connection, user_id, limit=1)
            if fallback:
                selected_topic = fallback[0]["topic"]
                difficulty = _difficulty_from_elo(float(fallback[0]["elo_rating"]))
                problem = _select_problem(user_id, selected_topic, difficulty, db_path=db_path, exclude_problem_id=current_problem_id)
        tier = "specific" if problem else "topic_hint"
        explanation = _build_explanation(tier, gap_info, problem, topic=selected_topic)
        return _recommendation(tier, problem, explanation, confidence, selected_topic, difficulty, selected_topic)

    if confidence >= HINT_THRESHOLD:
        explanation = _build_explanation("topic_hint", gap_info, None, topic=topic)
        return _recommendation("topic_hint", None, explanation, confidence, topic, _difficulty_for_user(connection, user_id, topic), topic)

    explanation = _build_explanation("general_hint", gap_info, None, topic=topic)
    return _recommendation("general_hint", None, explanation, confidence, topic, _difficulty_for_user(connection, user_id, topic), topic)


def _select_problem(user_id, topic, difficulty, db_path=None, exclude_problem_id=None):
    """Select the highest-acceptance unsolved problem for a topic and difficulty."""
    connection = get_connection(db_path)
    row = connection.execute(
        """
        SELECT p.*
        FROM problems p
        WHERE p.difficulty = ?
          AND p.topics LIKE ?
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
        (difficulty, f"%{topic}%", exclude_problem_id, exclude_problem_id, user_id),
    ).fetchone()
    return dict(row) if row else None


def _build_explanation(tier, gap_info, problem, topic=None, no_gap=False):
    """Build a human-readable explanation for the recommendation result."""
    focus = gap_info.get("gap_pattern") or gap_info.get("matched_pattern") or "the core pattern"
    readable_focus = focus.replace("_", " ")
    readable_topic = topic or "this topic"

    if no_gap and problem:
        return (
            f"Nice work: your solution matched the expected approach. "
            f"Try {problem['title']} next to stretch {readable_topic} at a stronger difficulty."
        )
    if no_gap:
        return f"Nice work: your solution matched the expected approach. Keep building momentum in {readable_topic}."

    if tier == "specific" and problem:
        return (
            f"Your submission did not show enough evidence of the expected {readable_focus} approach. "
            f"Try {problem['title']} to practice {readable_focus} in {readable_topic}."
        )
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
        "problem": problem,
        "explanation": explanation,
        "confidence": round(float(confidence), 2),
        "topic": topic,
        "pattern": pattern,
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


