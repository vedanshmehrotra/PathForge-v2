"""
QA Simulation: Three User Journeys through PathForge's Recommendation Loop.

Simulates 20-submission sequences for Users A (high performer), B (struggling), C (mixed).
Reports recommendation choices, rotation triggers, Elo trajectories, and topic mastery.
"""
import csv
import json
import os
import sqlite3
import sys
import tempfile
from collections import defaultdict, Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pathforge.db.db import init_db
from pathforge.db.profile_manager import seed_initial_topic_profiles, update_topic_profile
from pathforge.recommender import get_recommendation, _select_problem, _difficulty_for_user

sys.setrecursionlimit(10000)

DATA_DIR = Path(__file__).resolve().parent / "pathforge" / "data"
CSV_PATH = DATA_DIR / "pathforge_problems_fixed.csv"
DIFFICULTY_ORDER = ["Easy", "Medium", "Hard"]

def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def patch_get_connection(db_path):
    """Replace get_connection in all importing modules with a shared connection."""
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    c.execute("PRAGMA journal_mode = WAL")
    c.execute("PRAGMA busy_timeout = 10000")

    def shared(path=None):
        return c

    from pathforge.db import db as dbm
    from pathforge import recommender as rm
    dbm.get_connection = shared
    rm.get_connection = shared
    return c


def unpatch_get_connection():
    from pathforge.db import db as dbm
    from pathforge import recommender as rm

    def fresh(path=None):
        # This unpatch leaves a working default get_connection
        return sqlite3.connect(str(path)) if path else sqlite3.connect(":memory:")
    dbm.get_connection = fresh
    rm.get_connection = fresh


def seed_problems(connection, csv_path):
    existing = connection.execute("SELECT COUNT(*) AS c FROM problems").fetchone()["c"]
    if existing:
        return
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = []
        for row in csv.DictReader(f):
            rows.append((
                int(row["ID"]), row["Title"], row["Difficulty"],
                row["Topics"], row["pattern"], row["Example Test Cases"],
                row["Link"],
                float(row["Acceptance Rate (%)"]) if row["Acceptance Rate (%)"] else None,
                1 if row.get("Premium Only", "").upper() == "TRUE" else 0,
                row.get("Category", ""), int(row.get("Likes", 0) or 0),
                int(row.get("Dislikes", 0) or 0), row.get("Similar Questions", ""),
                iso_now(),
            ))
    connection.executemany("""
        INSERT OR IGNORE INTO problems (
            id, title, difficulty, topics, pattern, test_cases, link,
            acceptance_rate, premium_only, category, likes, dislikes,
            similar_questions, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    connection.commit()


class PassPredictor:
    def __init__(self, base_rates, topic_multipliers=None):
        self.base_rates = base_rates
        self.topic_multipliers = topic_multipliers or {}

    def probability(self, difficulty, topic):
        base = self.base_rates.get(difficulty, 0.5)
        return base * self.topic_multipliers.get(topic, 1.0)

    def verdict(self, difficulty, topic, step=None):
        import random
        rng = random.Random(42 + (step or 0))
        return "solved" if rng.random() < self.probability(difficulty, topic) else "unsolved"


def get_problem(connection, pid):
    return dict(connection.execute("SELECT * FROM problems WHERE id = ?", (pid,)).fetchone())


def do_submit(user_id, problem, verdict_str, submitted_at, db_path):
    """Submit a problem, update profiles, save submission, get recommendation."""
    connection = patch_get_connection(db_path)
    pattern = json.loads(problem["pattern"])[0]
    ts = submitted_at
    db_verdict = "pass" if verdict_str == "solved" else "fail"

    profile_update = update_topic_profile(
        connection, user_id=user_id, topic=pattern,
        difficulty=problem["difficulty"], verdict=db_verdict,
        detected_pattern=pattern, expected_pattern=pattern, attempted_at=ts,
    )

    connection.execute("""
        INSERT INTO submissions (user_id, problem_id, code_text, verdict,
            detected_pattern, detected_confidence, expected_pattern,
            target_pattern, gap_identified, diagnosis_confidence,
            time_taken_seconds, attempt_number, topic, submitted_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (user_id, problem["id"], "self-reported", db_verdict, pattern, 1.0,
          pattern, None, 0, 1.0, None, 1, pattern, ts))
    connection.commit()

    # Build submission result
    sid = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
    record = dict(connection.execute("SELECT * FROM submissions WHERE rowid = ?", (sid,)).fetchone())
    gap_info = {"gap_detected": False, "gap_pattern": None, "matched_pattern": pattern, "diagnosis_confidence": 1.0}
    sub_result = {"submission": record, "gap_info": gap_info, "profile_update": profile_update}

    rec = get_recommendation(user_id, sub_result, problem)

    profiles = {p["topic"]: dict(p) for p in connection.execute(
        "SELECT * FROM topic_profiles WHERE user_id = ?", (user_id,)).fetchall()}

    return {
        "step": 0, "problem_id": problem["id"], "problem_title": problem["title"],
        "problem_difficulty": problem["difficulty"], "topic": pattern,
        "verdict": db_verdict, "elo_before": profile_update["elo_before"],
        "elo_after": profile_update["elo_after"],
        "recent_failures": profile_update["recent_failures"],
        "recommendation": rec, "profiles": profiles,
    }


def pick_initial_problem(connection, user_id):
    """Pick first problem from the user's weakest topic with an Easy problem available."""
    weakest = connection.execute("""
        SELECT topic FROM topic_profiles WHERE user_id = ?
        ORDER BY ((1600.0-elo_rating)/1200.0)+(1.0-accuracy)+(MIN(recent_failures,5)/3.0) DESC,
                 elo_rating ASC, accuracy ASC
    """, (user_id,)).fetchall()
    for w in weakest:
        t = w["topic"]
        row = connection.execute("""
            SELECT p.* FROM problems p
            WHERE p.difficulty = 'Easy' AND json_extract(p.pattern, '$[0]') = ?
            ORDER BY COALESCE(p.acceptance_rate, 0) DESC, p.id ASC LIMIT 1
        """, (t,)).fetchone()
        if row:
            return dict(row)
    # fallback
    row = connection.execute("SELECT p.* FROM problems p WHERE p.difficulty='Easy' ORDER BY p.id LIMIT 1").fetchone()
    return dict(row) if row else None





def run_user(user_id, name, experience, pass_predictor, max_steps, db_path, csv_path):
    """Run a user simulation with safeguards against dead ends."""
    conn = patch_get_connection(db_path)
    init_db(db_path)
    seed_problems(conn, csv_path)

    conn.execute("""INSERT INTO users (id,username,email,password_hash,created_at,updated_at) VALUES (?,?,?,?,?,?)""",
        (user_id, name, f"{name}@test.com", "hash", iso_now(), iso_now()))
    conn.commit()
    seed_initial_topic_profiles(conn, user_id, experience, [])

    first = pick_initial_problem(conn, user_id)
    if not first:
        return []

    history = []
    used_topic_counts = Counter()

    for step in range(1, max_steps + 1):
        if step == 1:
            pid = first["id"]
            forced = False
        else:
            last = history[-1]
            rec = last["recommendation"]
            nxt = rec.get("problem")
            forced = False
            if not nxt:
                # Dead-end: recommendation has no problem (topic_hint)
                # Fallback to any unsolved problem (simulates user choosing manually)
                nxt = conn.execute("""
                    SELECT p.* FROM problems p
                    WHERE NOT EXISTS (
                        SELECT 1 FROM submissions s
                        WHERE s.user_id = ? AND s.problem_id = p.id AND s.verdict = 'pass'
                    )
                    ORDER BY COALESCE(p.acceptance_rate, 0) DESC, p.id ASC LIMIT 1
                """, (user_id,)).fetchone()
                forced = True
            if not nxt:
                break
            pid = nxt["id"] if isinstance(nxt, dict) else nxt["id"]

        problem = get_problem(conn, pid)
        topic = json.loads(problem["pattern"])[0]
        diff = problem["difficulty"]
        verdict = pass_predictor.verdict(diff, topic, step=step)
        ts = (datetime(2026, 6, 1) + timedelta(hours=step)).isoformat()

        state = do_submit(user_id, problem, verdict, ts, db_path)
        state["step"] = step
        state["forced"] = forced
        history.append(state)
        used_topic_counts[topic] += 1

    dead_ends = [s for s in history if s["recommendation"].get("problem") is None]
    rotations = [s for s in history
                 if "Switch" in s["recommendation"].get("explanation", "")
                 or "tough" in s["recommendation"].get("explanation", "").lower()]

    profiles = {p["topic"]: dict(p) for p in conn.execute(
        "SELECT * FROM topic_profiles WHERE user_id = ?", (user_id,)).fetchall()}
    unpatch_get_connection()
    return history, profiles, used_topic_counts, dead_ends, rotations


def fmt_explanation(expl):
    """Shorten explanation for display."""
    if not expl:
        return ""
    return expl[:90] + ("..." if len(expl) > 90 else "")


def print_user_journey(name, history, final_profiles, topic_counts, dead_ends, rotations):
    print(f"\n{'='*100}")
    print(f"USER {name} - {len(history)} submissions")
    print(f"{'='*100}")
    print(f"{'Step':>4} {'Topic':<28} {'Diff':<7} {'Verdict':<7} {'Elo':>10} {'RecTopic':<28} {'RecDiff':<7} {'RecID':<6} {'Tier':<12} {'Explanation':<60}")
    print(f"{'-'*4} {'-'*28} {'-'*7} {'-'*7} {'-'*10} {'-'*28} {'-'*7} {'-'*6} {'-'*12} {'-'*60}")

    for s in history:
        rec = s["recommendation"]
        ed = f"{s['elo_before']:.0f}->{s['elo_after']:.0f}"
        vd = "PASS" if s["verdict"] == "pass" else "FAIL"
        rid = str(rec["problem"]["id"]) if rec["problem"] else "-"
        rex = fmt_explanation(rec.get("explanation", ""))
        tier = rec["tier"]
        fallback = " [F]" if s.get("forced") else ""
        print(f"{s['step']:>4} {s['topic']:<28} {s['problem_difficulty']:<7} {vd:<7} {ed:>10} {rec['topic']:<28} {rec['difficulty']:<7} {rid:<6} {tier:<12} {rex}{fallback}")

    print(f"\n--- Dead-end Recommendations ---")
    if dead_ends:
        for s in dead_ends:
            expl = s["recommendation"].get("explanation", "")
            print(f"  Step {s['step']}: topic_hint with no problem - {expl}")
        print(f"  TOTAL DEAD-ENDS: {len(dead_ends)}")
    else:
        print(f"  NONE - all recommendations have actionable problems.")

    print(f"\n--- Rotation Events ---")
    if rotations:
        for s in rotations:
            vd = "PASS" if s["verdict"] == "pass" else "FAIL"
            expl = s["recommendation"].get("explanation", "")
            print(f"  Step {s['step']} ({vd} on {s['topic']}): {expl}")
        rotation_steps = [s["step"] for s in rotations]
        print(f"  Rotation count: {len(rotations)} at steps: {rotation_steps}")
    else:
        print(f"  No rotation events triggered.")

    print(f"\n--- Explanation highlights (rotations & notable) ---")
    for s in history:
        expl = s["recommendation"].get("explanation", "")
        if not expl:
            continue
        if any(kw in expl for kw in ["Switch", "tough", "weakest", "streak"]):
            vd = "PASS" if s["verdict"] == "pass" else "FAIL"
            print(f"  Step {s['step']} ({vd} on {s['topic']}): {expl}")

    top5 = sorted(final_profiles.values(),
        key=lambda p: ((1600-p["elo_rating"])/1200)+(1-p["accuracy"])+(min(p["recent_failures"],5)/3),
        reverse=True)[:5]
    print(f"\n--- Final Top 5 Weakest Topics ---")
    for p in top5:
        ws = ((1600-p["elo_rating"])/1200)+(1-p["accuracy"])+(min(p["recent_failures"],5)/3)
        print(f"  {p['topic']:<30} Elo={p['elo_rating']:<7.0f} Acc={p['accuracy']:.2f} RFail={p['recent_failures']} WScore={ws:.3f}")

    print(f"\n--- Topic Mastery ---")
    for t, cnt in sorted(topic_counts.items()):
        prof = final_profiles.get(t, {})
        pct = prof.get("pass_count", 0)
        total = prof.get("attempt_count", 0)
        acc = pct / total if total else 0
        elo = prof.get("elo_rating", 700)
        print(f"  {t:<30} {cnt:>2}x  acc={acc:.0%}  Elo={elo:.0f}")


def evaluate_system(all_results):
    print(f"\n{'#'*100}")
    print(f"PRODUCT EVALUATION")
    print(f"{'#'*100}")

    print(f"\n--- 0. Dead-End Validation ---")
    total_dead_ends = 0
    for item in all_results:
        name, history, final_profiles, dead_ends, rotations = item
        n = len(dead_ends)
        total_dead_ends += n
        if n:
            print(f"  FAIL: {name}  -  {n} dead-end recommendation(s) found")
            for s in dead_ends:
                print(f"    Step {s['step']}: {s['recommendation'].get('explanation','')}")
        else:
            print(f"  PASS: {name} - all recommendations have actionable problems")
    if total_dead_ends == 0:
        print(f"  >>> ALL USERS: No dead-end recommendations. Validation PASSED.")
    else:
        print(f"  >>> WARNING: {total_dead_ends} dead-end(s) detected across all users.")

    print(f"\n--- 1. Difficulty Progression ---")
    for item in all_results:
        name, history, _, _, _ = item
        diffs = [s["problem_difficulty"] for s in history]
        cd = Counter(diffs)
        seq = " -> ".join(diffs[:10]) + ("..." if len(diffs) > 10 else "")
        print(f"  {name}: E={cd.get('Easy',0)} M={cd.get('Medium',0)} H={cd.get('Hard',0)} | {seq}")

    print(f"\n--- 2. Topic Switching ---")
    for item in all_results:
        name, history, _, _, _ = item
        topics = [s["topic"] for s in history]
        switches = sum(1 for i in range(1, len(topics)) if topics[i] != topics[i-1])
        rate = switches / len(topics) * 100 if topics else 0
        print(f"  {name}: {switches} switches in {len(topics)} submissions ({rate:.0f}% switch rate)")

    print(f"\n--- 3. Max Consecutive Same Topic ---")
    for item in all_results:
        name, history, _, _, _ = item
        topics = [s["topic"] for s in history]
        mx = cur = 1
        for i in range(1, len(topics)):
            if topics[i] == topics[i-1]:
                cur += 1; mx = max(mx, cur)
            else:
                cur = 1
        print(f"  {name}: max = {mx}")

    print(f"\n--- 4. Topic Coverage ---")
    all_seen = set()
    for item in all_results:
        name, history, _, _, _ = item
        topics = set(s["topic"] for s in history)
        all_seen |= topics
        print(f"  {name}: {len(topics)} unique topics")
    print(f"  Combined: {len(all_seen)} unique topics across users")

    print(f"\n--- 5. Weakest Topics Coverage ---")
    for item in all_results:
        name, history, final_profiles, _, _ = item
        weak = sorted(final_profiles.values(),
            key=lambda p: ((1600-p["elo_rating"])/1200)+(1-p["accuracy"])+(min(p["recent_failures"],5)/3),
            reverse=True)
        top3 = [p["topic"] for p in weak[:3]]
        practiced = set(s["topic"] for s in history)
        unseen = [t for t in top3 if t not in practiced]
        if unseen:
            print(f"  {name}: MISSED weakest: {unseen}")
            for t in unseen:
                p = next(p2 for p2 in weak if p2["topic"] == t)
                ws = ((1600-p["elo_rating"])/1200)+(1-p["accuracy"])+(min(p["recent_failures"],5)/3)
                print(f"     {t}: Elo={p['elo_rating']:.0f} Acc={p['accuracy']:.2f} WScore={ws:.3f}")
        else:
            print(f"  {name}: All top-3 weakest practiced")

    # Difficulty lock-in analysis
    print(f"\n--- 6. Difficulty Band Lock-in ---")
    for item in all_results:
        name, history, _, _, _ = item
        diffs = [s["problem_difficulty"] for s in history]
        counts = Counter(diffs)
        locked = any(v >= len(history) * 0.6 for v in counts.values())
        print(f"  {name}: {'LOCKED' if locked else 'varied'}  -  {dict(counts)}")

    # Elo stagnation
    print(f"\n--- 7. Elo Stagnation ---")
    for item in all_results:
        name, history, _, _, _ = item
        if len(history) < 5:
            continue
        recent = history[-5:]
        elo_range = max(s["elo_after"] for s in recent) - min(s["elo_after"] for s in recent)
        print(f"  {name}: Elo range over last 5 = {elo_range:.0f} {'(stagnant)' if elo_range < 20 else '(moving)'}")


def main():
    db_path_a = tempfile.mktemp(suffix=".sqlite3")
    db_path_b = tempfile.mktemp(suffix=".sqlite3")
    db_path_c = tempfile.mktemp(suffix=".sqlite3")
    steps = 20

    # User A: High performer (~85% pass)
    predictor_a = PassPredictor({"Easy": 0.95, "Medium": 0.85, "Hard": 0.65})
    # User B: Struggling (~20% pass)
    predictor_b = PassPredictor({"Easy": 0.40, "Medium": 0.15, "Hard": 0.05})
    # User C: Mixed performer
    predictor_c = PassPredictor(
        {"Easy": 0.85, "Medium": 0.60, "Hard": 0.35},
        topic_multipliers={
            "hash_map_lookup": 1.5, "hash_map_frequency": 1.4,
            "prefix_sum": 1.3, "two_pointers_opposite": 1.3,
            "two_pointers_same": 1.2, "fast_slow_pointers": 1.2,
            "dp_1d_forward": 0.4, "dp_1d_sequence": 0.3,
            "dp_2d_grid": 0.3, "dp_2d_string": 0.25,
            "bfs_level_order": 0.5, "dfs_recursive": 0.55, "dfs_iterative": 0.5,
        },
    )

    print("Simulating User A..."); sys.stdout.flush()
    ha, pa, tca, dea, rota = run_user(1, "A (High Performer)", "intermediate", predictor_a, steps, db_path_a, CSV_PATH)

    print("Simulating User B..."); sys.stdout.flush()
    hb, pb, tcb, deb, rotb = run_user(2, "B (Struggling)", "intermediate", predictor_b, steps, db_path_b, CSV_PATH)

    print("Simulating User C..."); sys.stdout.flush()
    hc, pc, tcc, dec, rotc = run_user(3, "C (Mixed)", "intermediate", predictor_c, steps, db_path_c, CSV_PATH)

    print_user_journey("A (High Performer)", ha, pa, tca, dea, rota)
    print_user_journey("B (Struggling)", hb, pb, tcb, deb, rotb)
    print_user_journey("C (Mixed)", hc, pc, tcc, dec, rotc)

    evaluate_system([("A (High Performer)", ha, pa, dea, rota), ("B (Struggling)", hb, pb, deb, rotb), ("C (Mixed)", hc, pc, dec, rotc)])

    for p in [db_path_a, db_path_b, db_path_c]:
        try: os.remove(p)
        except: pass
    print(f"\n{'='*100}")
    print("SIMULATION COMPLETE")


if __name__ == "__main__":
    main()
