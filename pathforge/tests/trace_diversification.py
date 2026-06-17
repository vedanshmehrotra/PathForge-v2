"""Trace script demonstrating recommendation diversification.

Simulates:
1. 3 consecutive passes on hash_map_lookup → rotation after 3rd pass
2. 3 consecutive fails on sliding_window_variable → rotation after 3rd fail
"""
import tempfile
from pathforge.db.db import init_db
from pathforge.db.profile_manager import seed_initial_topic_profiles, update_topic_profile
from pathforge.recommender import get_recommendation

PROBLEMS = [
    (1, "Two Sum", "Easy", "Array, Hash Table", '["hash_map_lookup"]', '[]', 85.0),
    (2, "Group Anagrams", "Medium", "Array, String", '["hash_map_lookup"]', '[]', 72.0),
    (3, "Longest Substring", "Medium", "String, Sliding Window", '["sliding_window_variable"]', '[]', 68.0),
    (4, "BFS Practice", "Easy", "Graph", '["bfs_level_order"]', '[]', 91.0),
    (5, "Permutations", "Medium", "Backtracking", '["backtracking_permutation"]', '[]', 65.0),
    (6, "Binary Search Basic", "Easy", "Binary Search", '["binary_search_standard"]', '[]', 80.0),
]

def seed(connection):
    for pid, title, diff, topics, pattern, tcs, acc in PROBLEMS:
        connection.execute(
            "INSERT INTO problems (id, title, difficulty, topics, pattern, test_cases, acceptance_rate, created_at) VALUES (?,?,?,?,?,?,?,'2026-06-04T00:00:00+00:00')",
            (pid, title, diff, topics, pattern, tcs, acc),
        )
    connection.commit()

def add_submission(connection, user_id, problem_id, verdict, topic, submitted_at):
    connection.execute(
        "INSERT INTO submissions (user_id, problem_id, code_text, verdict, detected_pattern, detected_confidence, expected_pattern, target_pattern, gap_identified, diagnosis_confidence, time_taken_seconds, attempt_number, topic, submitted_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (user_id, problem_id, "code", verdict, topic, 1.0, topic, None, 0, 1.0, None, 1, topic, submitted_at),
    )
    connection.commit()

def run_trace():
    db_path = tempfile.mktemp(suffix=".sqlite3")
    connection = init_db(db_path)

    seed(connection)
    # Create user
    connection.execute(
        "INSERT INTO users (id, username, email, password_hash, created_at, updated_at) VALUES (1,'user','u@e.com','h','2026-06-04T00:00:00+00:00','2026-06-04T00:00:00+00:00')"
    )
    connection.commit()

    # Seed profiles (all patterns with baseline)
    seed_initial_topic_profiles(connection, 1, "intermediate", [])

    # Build problems dict
    problems = {r["id"]: dict(r) for r in connection.execute("SELECT * FROM problems").fetchall()}

    # Also insert Array and Graph profiles for backward compat with _rotate_topic fallback
    for topic, elo in [("Array", 850), ("Graph", 700)]:
        connection.execute(
            "INSERT INTO topic_profiles (user_id, topic, elo_rating, attempt_count, pass_count, accuracy, recent_failures, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(user_id, topic) DO UPDATE SET elo_rating=excluded.elo_rating, accuracy=excluded.accuracy, recent_failures=excluded.recent_failures, updated_at=excluded.updated_at",
            (1, topic, elo, 3, 1, 0.33, 2, "2026-06-04T00:00:00+00:00", "2026-06-04T00:00:00+00:00"),
        )
    connection.commit()

    print("=" * 78)
    print("TRACE 1: 3 consecutive passes on hash_map_lookup -> rotation")
    print("=" * 78)

    for i in range(4):
        ts = f"2026-06-0{5+i}T12:00:00+00:00"
        problem = problems[1]  # always "Two Sum" (hash_map_lookup, Easy)
        verdict_str = "pass"

        if i < 3:
            # Submit + update profile
            add_submission(connection, 1, problem["id"], verdict_str, "hash_map_lookup", ts)
            update_topic_profile(connection, 1, "hash_map_lookup", problem["difficulty"], verdict_str, "hash_map_lookup", "hash_map_lookup", ts)
        else:
            # 4th: check the lock by submitting again but the lock check queries the last 3 submissions
            # For the 4th call, the 3 previous submissions are all passes → lock should trigger
            add_submission(connection, 1, problem["id"], verdict_str, "hash_map_lookup", ts)
            update_topic_profile(connection, 1, "hash_map_lookup", problem["difficulty"], verdict_str, "hash_map_lookup", "hash_map_lookup", ts)

        # Build submission_result
        submission_result = {
            "submission": {
                "id": 0,
                "user_id": 1,
                "problem_id": problem["id"],
                "verdict": verdict_str,
                "detected_pattern": "hash_map_lookup",
                "detected_confidence": 1.0,
                "expected_pattern": "hash_map_lookup",
                "gap_identified": 0,
                "topic": "hash_map_lookup",
            },
            "gap_info": {
                "gap_detected": False,
                "gap_pattern": None,
                "matched_pattern": "hash_map_lookup",
                "diagnosis_confidence": 1.0,
            },
        }

        rec = get_recommendation(1, submission_result, problem, connection)
        subject = f"Submission #{i+1}: pass on hash_map_lookup"
        print(f"\n{subject}")
        print(f"  recommended topic: {rec['topic']}")
        print(f"  recommended difficulty: {rec['difficulty']}")
        print(f"  problem: {rec['problem']['title'] if rec['problem'] else None}")
        print(f"  explanation: {rec['explanation']}")
        print(f"  (tier: {rec['tier']})")

    print()
    print("=" * 78)
    print("TRACE 2: 3 consecutive fails on sliding_window_variable -> rotation")
    print("=" * 78)

    # Reset profiles: get_weakest_topics still uses the global weakness scores,
    # but we want to show rotation. Since profiles are seeded, sliding_window_variable
    # should have a normal elo of 900. We'll set it lower for demonstration.
    connection.execute(
        "UPDATE topic_profiles SET elo_rating = 750, recent_failures = 0, accuracy = 0.5, attempt_count = 2, pass_count = 1 WHERE user_id = 1 AND topic = 'sliding_window_variable'"
    )
    connection.commit()

    for i in range(4):
        ts = f"2026-06-0{9+i}T12:00:00+00:00"
        problem = problems[3]  # "BFS Practice" but we'll force the topic to be sliding_window_variable
        # Actually we need a sliding_window_variable problem. Let's use problem 3.
        problem = problems[3]  # problem id 3 = "Longest Substring" with sliding_window_variable
        verdict_str = "fail"

        # Submit
        add_submission(connection, 1, problem["id"], verdict_str, "sliding_window_variable", ts)
        update_topic_profile(connection, 1, "sliding_window_variable", problem["difficulty"], verdict_str, "sliding_window_variable", "sliding_window_variable", ts)

        submission_result = {
            "submission": {
                "id": 0,
                "user_id": 1,
                "problem_id": problem["id"],
                "verdict": verdict_str,
                "detected_pattern": "sliding_window_variable",
                "detected_confidence": 1.0,
                "expected_pattern": "sliding_window_variable",
                "gap_identified": 0,
                "topic": "sliding_window_variable",
            },
            "gap_info": {
                "gap_detected": False,
                "gap_pattern": None,
                "matched_pattern": "sliding_window_variable",
                "diagnosis_confidence": 1.0,
            },
        }

        rec = get_recommendation(1, submission_result, problem, connection)
        subject = f"Submission #{i+1}: fail on sliding_window_variable"
        print(f"\n{subject}")
        print(f"  recommended topic: {rec['topic']}")
        print(f"  recommended difficulty: {rec['difficulty']}")
        print(f"  problem: {rec['problem']['title'] if rec['problem'] else None}")
        print(f"  explanation: {rec['explanation']}")
        print(f"  (tier: {rec['tier']}, recent_failures now: {connection.execute('SELECT recent_failures FROM topic_profiles WHERE user_id=1 AND topic=?', ('sliding_window_variable',)).fetchone()['recent_failures']})")

    connection.close()
    import os
    try:
        os.remove(db_path)
    except OSError:
        pass


if __name__ == "__main__":
    run_trace()
