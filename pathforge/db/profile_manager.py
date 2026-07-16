from datetime import datetime, timezone

from pathforge.ast_engine.patterns import ALL_PATTERNS
from pathforge.db.elo import outcome_from_submission, update_elo

STARTING_ELO = 800.0

EXPERIENCE_BASELINES = {"beginner": 700.0, "intermediate": 900.0, "advanced": 1100.0}
BROAD_TOPIC_PATTERNS = {
    "arrays": {
        "hash_map_lookup", "hash_map_frequency", "prefix_sum",
        "sliding_window_fixed", "sliding_window_variable",
        "two_pointers_opposite", "two_pointers_same",
    },
    "trees_graphs": {
        "dfs_recursive", "dfs_iterative", "bfs_level_order",
        "bfs_shortest_path", "topological_sort", "union_find", "binary_search_tree",
    },
    "dp": {"dp_1d_forward", "dp_1d_sequence", "dp_2d_grid", "dp_2d_string", "dp_knapsack", "dp_interval", "dp_state_machine"},
    "linked_lists": {"fast_slow_pointers", "linked_list_reversal", "monotonic_stack", "monotonic_deque"},
    "binary_search": {"binary_search_standard", "binary_search_rotated", "binary_search_answer"},
    "greedy_backtracking": {
        "heap_top_k", "greedy_local", "greedy_interval",
        "backtracking_permutation", "backtracking_subset",
    },
}


def seed_initial_topic_profiles(connection, user_id, experience_level, confident_areas, seeded_at=None):
    """Create prior Elo rows for every canonical pattern before the first submission."""
    level = (experience_level or "beginner").strip().lower()
    if level not in EXPERIENCE_BASELINES:
        raise ValueError("experience_level must be beginner, intermediate, or advanced")
    confident = set(confident_areas or []) & set(BROAD_TOPIC_PATTERNS)
    timestamp = seeded_at or iso_now()
    rows = []
    for pattern in sorted(ALL_PATTERNS):
        bonus = 150.0 if any(pattern in BROAD_TOPIC_PATTERNS[area] for area in confident) else 0.0
        rows.append((user_id, pattern, EXPERIENCE_BASELINES[level] + bonus, timestamp, timestamp))
    for row in rows:
        connection.execute(
            """
            INSERT INTO topic_profiles (
                user_id, topic, elo_rating, attempt_count, pass_count,
                pattern_match_count, accuracy, recent_failures, created_at, updated_at
            )
            VALUES (%s, %s, %s, 0, 0, 0, 0.0, 0, %s, %s)
            ON CONFLICT(user_id, topic) DO UPDATE SET
                elo_rating = EXCLUDED.elo_rating,
                updated_at = EXCLUDED.updated_at
            """,
            row,
        )
    connection.commit()
    return {"seeded_patterns": len(rows), "baseline": EXPERIENCE_BASELINES[level], "confident_areas": sorted(confident)}


def normalize_confident_areas(areas):
    """Return known broad topic area ids from a payload value."""
    if not isinstance(areas, list):
        return []
    return [area for area in areas if area in BROAD_TOPIC_PATTERNS]


def iso_now():
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def update_topic_profile(
    connection,
    user_id,
    topic,
    difficulty,
    verdict,
    detected_pattern,
    expected_pattern,
    attempted_at=None,
):
    """Upsert and update one user's per-topic skill profile after a submission."""
    timestamp = attempted_at or iso_now()
    existing = connection.execute(
        """
        SELECT elo_rating, attempt_count, pass_count, pattern_match_count, recent_failures, created_at
        FROM topic_profiles
        WHERE user_id = %s AND topic = %s
        """,
        (user_id, topic),
    ).fetchone()

    if existing:
        elo_before = float(existing["elo_rating"])
        attempt_count = int(existing["attempt_count"])
        pass_count = int(existing["pass_count"])
        pattern_match_count = int(existing["pattern_match_count"])
        recent_failures = int(existing["recent_failures"])
        created_at = None
    else:
        elo_before = STARTING_ELO
        attempt_count = 0
        pass_count = 0
        pattern_match_count = 0
        recent_failures = 0
        created_at = timestamp

    outcome = outcome_from_submission(verdict, detected_pattern, expected_pattern)
    elo_after = update_elo(elo_before, difficulty, outcome)
    new_attempt_count = attempt_count + 1
    new_pass_count = pass_count + (1 if verdict == "pass" else 0)
    new_pattern_match_count = pattern_match_count + (1 if verdict == "pass" and detected_pattern == expected_pattern else 0)
    new_accuracy = new_pass_count / new_attempt_count
    new_recent_failures = recent_failures + 1 if verdict == "fail" else max(0, recent_failures - 1)

    connection.execute(
        """
        INSERT INTO topic_profiles (
            user_id, topic, elo_rating, attempt_count, pass_count,
            pattern_match_count, accuracy, recent_failures,
            last_attempt_at, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT(user_id, topic) DO UPDATE SET
            elo_rating = EXCLUDED.elo_rating,
            attempt_count = EXCLUDED.attempt_count,
            pass_count = EXCLUDED.pass_count,
            pattern_match_count = EXCLUDED.pattern_match_count,
            accuracy = EXCLUDED.accuracy,
            recent_failures = EXCLUDED.recent_failures,
            last_attempt_at = EXCLUDED.last_attempt_at,
            updated_at = EXCLUDED.updated_at
        """,
        (
            user_id,
            topic,
            elo_after,
            new_attempt_count,
            new_pass_count,
            new_pattern_match_count,
            new_accuracy,
            new_recent_failures,
            timestamp,
            created_at or existing["created_at"] if existing else created_at,
            timestamp,
        ),
    )
    # NOTE: Do not commit here. The caller (pipeline.py) must handle atomicity
    # by committing all changes (submission, streak, profile, recommendation) in one transaction.

    return {
        "user_id": user_id,
        "topic": topic,
        "elo_before": elo_before,
        "elo_after": elo_after,
        "attempt_count": new_attempt_count,
        "pass_count": new_pass_count,
        "accuracy": new_accuracy,
        "recent_failures": new_recent_failures,
        "outcome": outcome,
    }


def get_user_profile(connection, user_id):
    """Return all topic profile rows for a user ordered by topic name."""
    rows = connection.execute(
        """
        SELECT user_id, topic, elo_rating, attempt_count, pass_count,
               pattern_match_count, accuracy, recent_failures,
               last_attempt_at, created_at, updated_at
        FROM topic_profiles
        WHERE user_id = %s
        ORDER BY topic ASC
        """,
        (user_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_recommendable_patterns(connection):
    """Return the set of pattern names that have at least 1 primary problem in the bank.

    A pattern is recommendable only when the CSV contains at least one problem
    where that pattern appears as the first element in the pattern JSON array.
    Patterns with zero primary problems (e.g. binary_search_tree, dp_interval)
    would produce non-actionable topic_hint recommendations and are excluded.
    """
    rows = connection.execute(
        """SELECT DISTINCT p.pattern::jsonb->>0 AS pattern
           FROM problems p
           WHERE p.pattern::jsonb->>0 IS NOT NULL"""
    ).fetchall()
    return {row["pattern"] for row in rows}


def ensure_topic_profiles_exist(connection, user_id):
    """Create topic profiles for a user from their submission data if none exist.

    This handles the case where submissions were created outside the normal pipeline
    (e.g., data migration, test data) and the topic_profiles table was never populated.
    Topics are mapped from submission data using the detected/expected pattern, falling
    back to the submission's topic field.
    """
    existing = connection.execute(
        "SELECT COUNT(*) AS cnt FROM topic_profiles WHERE user_id = %s",
        (user_id,),
    ).fetchone()
    if existing and existing["cnt"] > 0:
        return 0

    from pathforge.db.elo import update_elo, outcome_from_submission

    subs = connection.execute(
        """
        SELECT s.topic, s.verdict, s.detected_pattern, s.expected_pattern,
               COALESCE(p.difficulty, 'Easy') AS difficulty, s.submitted_at
        FROM submissions s
        LEFT JOIN problems p ON p.id = s.problem_id
        WHERE s.user_id = %s
        ORDER BY s.submitted_at ASC
        """,
        (user_id,),
    ).fetchall()

    if not subs:
        return 0

    topic_data = {}
    for s in subs:
        topic = s["detected_pattern"] or s["expected_pattern"] or s["topic"]
        if not topic:
            continue
        if topic not in topic_data:
            topic_data[topic] = {
                "attempt_count": 0, "pass_count": 0,
                "elo_rating": 800.0, "recent_failures": 0,
                "last_attempt_at": None,
            }
        td = topic_data[topic]
        td["attempt_count"] += 1
        td["last_attempt_at"] = s["submitted_at"]
        outcome = outcome_from_submission(s["verdict"], s["detected_pattern"], s["expected_pattern"])
        td["elo_rating"] = update_elo(td["elo_rating"], s["difficulty"], outcome)
        td["recent_failures"] += 1 if outcome < 1.0 else max(0, td["recent_failures"] - 1)
        if s["verdict"] == "pass":
            td["pass_count"] += 1

    timestamp = iso_now()
    rows = []
    for topic, td in topic_data.items():
        accuracy = td["pass_count"] / td["attempt_count"] if td["attempt_count"] else 0.0
        rows.append((
            user_id, topic, td["elo_rating"], td["attempt_count"],
            td["pass_count"], 0, accuracy, td["recent_failures"],
            td["last_attempt_at"], timestamp, timestamp,
        ))

    for row in rows:
        connection.execute(
            """
            INSERT INTO topic_profiles (
                user_id, topic, elo_rating, attempt_count, pass_count,
                pattern_match_count, accuracy, recent_failures,
                last_attempt_at, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(user_id, topic) DO NOTHING
            """,
            row,
        )
    return len(rows)


def get_weakest_topics(connection, user_id, limit=5):
    """Return topics ranked by low Elo, low accuracy, and recent failures.

    Only recommendable patterns (those with at least 1 primary problem in the bank)
    are included. Topics with zero available problems (e.g. dp_state_machine,
    topological_sort) are excluded since the system can never produce an actionable
    recommendation for them.

    If no topic profiles exist for the user (e.g. submissions were created outside
    the normal pipeline), profiles are backfilled from submission data automatically.
    """
    recommendable = get_recommendable_patterns(connection)
    if not recommendable:
        return []
    placeholders = ",".join(["%s"] * len(recommendable))
    params = [user_id] + sorted(recommendable) + [limit]
    rows = connection.execute(
        f"""
        SELECT user_id, topic, elo_rating, attempt_count, pass_count,
               pattern_match_count, accuracy, recent_failures,
               last_attempt_at, created_at, updated_at,
                ((1600.0 - elo_rating) / 1200.0)
                + (1.0 - accuracy)
                + (LEAST(recent_failures, 5) / 3.0) AS weakness_score
        FROM topic_profiles
        WHERE user_id = %s
          AND topic IN ({placeholders})
        ORDER BY weakness_score DESC, elo_rating ASC, accuracy ASC
        LIMIT %s
        """,
        tuple(params),
    ).fetchall()

    if not rows:
        ensure_topic_profiles_exist(connection, user_id)
        rows = connection.execute(
            f"""
            SELECT user_id, topic, elo_rating, attempt_count, pass_count,
                   pattern_match_count, accuracy, recent_failures,
                   last_attempt_at, created_at, updated_at,
                    ((1600.0 - elo_rating) / 1200.0)
                    + (1.0 - accuracy)
                    + (LEAST(recent_failures, 5) / 3.0) AS weakness_score
            FROM topic_profiles
            WHERE user_id = %s
              AND topic IN ({placeholders})
            ORDER BY weakness_score DESC, elo_rating ASC, accuracy ASC
            LIMIT %s
            """,
            tuple(params),
        ).fetchall()

    return [dict(row) for row in rows]
