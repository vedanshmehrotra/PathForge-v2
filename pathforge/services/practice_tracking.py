"""Analysis deduplication and observed practice history, independent of skill authority."""
import hashlib
import json
from datetime import datetime, timezone

PRACTICE_POLICY_VERSION = 2


def request_practice_event(event, headers):
    """Recognizable legacy extension requests remain analysis-only.

    Origin is not an identity or a source of scoring authority. It only adds a
    restriction for older companions that lack explicit submission metadata.
    """
    if event is not None:
        return event
    if any(str(headers.get(name, "")).lower().startswith(("chrome-extension://", "moz-extension://"))
           for name in ("origin", "referer")):
        return {"source": "extension", "submission_id": None, "submission_status": None}
    return None


def analysis_key(problem_id, code, practice_event=None, practice_day=None):
    event = practice_event or {}
    # Reopening a submitted solution reuses its identity, including after a
    # browser restart. Drafts and explicit website analyses use the full code.
    normalized = code.replace("\r\n", "\n").strip()
    identity = [problem_id, event.get("source", "website"),
                [event["submission_id"], event.get("submission_status")] if event.get("submission_id")
                else [practice_day, hashlib.sha256(normalized.encode()).hexdigest()]]
    return hashlib.sha256(json.dumps(identity).encode()).hexdigest()


def find_recorded_analysis(connection, user_id, key):
    # Serialize one user's submissions through commit, including different keys,
    # so parallel panels cannot both pass the per-problem scoring limit.
    connection.execute("SELECT pg_advisory_xact_lock(%s)", (int(user_id),))
    return connection.execute(
        "SELECT id, verdict_type FROM submissions WHERE user_id = %s AND analysis_key = %s",
        (user_id, key),
    ).fetchone()


def scoring_limit(connection, user_id, problem_id, timestamp, practice_event=None):
    event = practice_event or {}
    if event.get("source") == "extension":
        if not event.get("submission_id"):
            return "awaiting_submission"
        if event.get("submission_status") == "failed":
            return "submission_not_accepted"
        if event.get("submission_status") != "accepted":
            return "submission_status_unavailable"
    day_start = timestamp[:10] + "T00:00:00+00:00"
    previous = connection.execute(
        """SELECT id FROM submissions WHERE user_id = %s
           AND problem_id IS NOT DISTINCT FROM %s AND skill_updates_applied = TRUE
           AND submitted_at >= %s LIMIT 1""",
        (user_id, problem_id, day_start),
    ).fetchone()
    return "problem_already_scored_today" if previous else None


def _practice_timestamp(value):
    """Normalize native PostgreSQL timestamps and legacy text to UTC ISO text."""
    if isinstance(value, datetime):
        stamp = value
    elif isinstance(value, str):
        try:
            stamp = datetime.fromisoformat(value)
        except ValueError:
            return None
    else:
        return None
    # Legacy timestamps without an offset were recorded in UTC.
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc).isoformat()


def get_pattern_practice(connection, user_id):
    """Read observed patterns from saved analyses, including unscored practice.

    Count one practice session per problem and UTC date for each observed
    pattern. Multiple editor revisions and refreshes cannot inflate the count.
    Existing rows are read without backfilling or changing any ratings.
    """
    rows = connection.execute(
        """SELECT id, problem_id, code_hash, detected_pattern,
                  detected_patterns_json, submitted_at
           FROM submissions WHERE user_id = %s ORDER BY submitted_at ASC, id ASC""",
        (user_id,),
    ).fetchall()
    records = {}
    for row in rows:
        detections = row["detected_patterns_json"]
        if isinstance(detections, str):
            try:
                detections = json.loads(detections)
            except ValueError:
                detections = []
        if not isinstance(detections, list):
            detections = []
        patterns = set()
        for detection in detections:
            if not isinstance(detection, dict) or not detection.get("detected", True):
                continue
            pattern = detection.get("pattern_id") or detection.get("name")
            if isinstance(pattern, str) and pattern:
                patterns.add(pattern)
        if not detections and row["detected_pattern"]:
            patterns.add(row["detected_pattern"])
        stamp = _practice_timestamp(row["submitted_at"])
        if not stamp:
            continue
        identity = row["problem_id"] if row["problem_id"] is not None else row["code_hash"] or row["id"]
        for pattern in patterns:
            if not isinstance(pattern, str) or not pattern:
                continue
            record = records.setdefault(pattern, {"topic": pattern, "sessions": set(), "last_attempt_at": stamp})
            record["sessions"].add((identity, stamp[:10]))
            record["last_attempt_at"] = max(record["last_attempt_at"], stamp)
    return [{"topic": p, "attempt_count": len(r["sessions"]), "last_attempt_at": r["last_attempt_at"]}
            for p, r in sorted(records.items())]
