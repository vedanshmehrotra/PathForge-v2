"""Opt-in PostgreSQL checks. Never falls back to the application's DATABASE_URL.

Use a dedicated test database via PATHFORGE_TEST_DATABASE_URL. Each test owns a
temporary schema and removes only that schema after closing its connections.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
import threading
import time
import uuid

import psycopg2
from psycopg2 import sql
import pytest

from pathforge.db.db import PgConnection
from pathforge.services.practice_tracking import analysis_key, find_recorded_analysis, scoring_limit, get_pattern_practice


@pytest.fixture(params=["TEXT", "TIMESTAMPTZ"])
def database(request):
    dsn = os.environ.get("PATHFORGE_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("Dedicated PostgreSQL test database not configured")
    if dsn == os.environ.get("DATABASE_URL"):
        pytest.fail("Test database must be distinct from the application database", pytrace=False)
    try:
        admin = psycopg2.connect(dsn)
    except psycopg2.Error:
        pytest.fail("Could not connect to the explicitly configured test database", pytrace=False)
    schema = "practice_test_" + uuid.uuid4().hex
    admin.autocommit = True
    with admin.cursor() as cursor:
        cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        cursor.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        cursor.execute(sql.SQL("""CREATE TABLE submissions (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT, problem_id BIGINT,
            analysis_key TEXT, verdict_type TEXT DEFAULT 'analysis_only',
            skill_updates_applied BOOLEAN DEFAULT FALSE, submitted_at {},
            code_hash TEXT, detected_pattern TEXT, detected_patterns_json JSONB,
            UNIQUE(user_id, analysis_key))""").format(sql.SQL(request.param)))
    def connection():
        raw = psycopg2.connect(dsn)
        with raw.cursor() as cursor:
            cursor.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        return raw, PgConnection(raw, None)
    try:
        yield connection
    finally:
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        admin.close()


@pytest.mark.parametrize("same_submission", [True, False])
def test_parallel_replays_and_distinct_submissions_cannot_both_score(database, same_submission):
    barrier = threading.Barrier(2)
    stamp = "2026-10-20T12:00:00+00:00"
    def attempt(number):
        raw, connection = database()
        try:
            event = {"source": "extension", "submission_id": "100" if same_submission else str(100 + number),
                     "submission_status": "accepted"}
            key = analysis_key(1, "code", event, stamp[:10])
            barrier.wait(timeout=10)
            recorded = find_recorded_analysis(connection, 7, key)
            if recorded:
                raw.commit()
                return "replayed"
            # Give the other transaction an opportunity to race this decision.
            time.sleep(.05)
            reason = scoring_limit(connection, 7, 1, stamp, event)
            connection.execute("""INSERT INTO submissions
                (user_id, problem_id, analysis_key, skill_updates_applied, submitted_at)
                VALUES (%s,%s,%s,%s,%s)""", (7, 1, key, reason is None, stamp))
            raw.commit()
            return reason or "scored"
        finally:
            raw.close()
    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = list(workers.map(attempt, (0, 1)))
    assert outcomes.count("scored") == 1
    assert outcomes.count("replayed" if same_submission else "problem_already_scored_today") == 1
    raw, connection = database()
    try:
        row = connection.execute("SELECT COUNT(*) AS saved, COUNT(*) FILTER (WHERE skill_updates_applied) AS scored FROM submissions").fetchone()
        assert row["saved"] == (1 if same_submission else 2)
        assert row["scored"] == 1
    finally:
        raw.close()


def test_real_jsonb_preserves_secondary_pattern_recency(database):
    raw, connection = database()
    try:
        connection.execute("""INSERT INTO submissions
            (user_id, problem_id, submitted_at, detected_pattern, detected_patterns_json)
            VALUES (%s,%s,%s,%s,%s)""", (7, 1, "2026-10-20T12:00:00+00:00", "hash_map_lookup",
            json.dumps([{"pattern_id": "hash_map_lookup"}, {"pattern_id": "array_traversal"}])))
        raw.commit()
        records = {record["topic"]: record for record in get_pattern_practice(connection, 7)}
        assert records["array_traversal"]["last_attempt_at"] == "2026-10-20T12:00:00+00:00"
        assert records["array_traversal"]["attempt_count"] == 1
    finally:
        raw.close()
