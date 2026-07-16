import os
from contextlib import contextmanager
from typing import Optional

import psycopg2
import psycopg2.extras
import psycopg2.pool


_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None

REQUIRED_TABLES = [
    "users", "problems", "submissions", "topic_profiles",
    "recommendations", "gap_signals", "user_pattern_elo", "problem_ground_truth",
]


def _get_database_url() -> str:
    """Return the PostgreSQL connection URL from environment."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is required for PostgreSQL. "
            "Set it to your Supabase connection string."
        )
    return url


def _ensure_pool() -> psycopg2.pool.ThreadedConnectionPool:
    """Create the connection pool if it doesn't exist yet."""
    global _pool
    if _pool is None:
        url = _get_database_url()
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=url,
        )
    return _pool


class PgConnection:
    """Wrapper around psycopg2 connection that mimics sqlite3.Row dict access."""

    def __init__(self, conn, pool):
        self._conn = conn
        self._pool = pool
        self.row_factory = None
        self._returned = False

    def execute(self, query, params=None):
        """Execute a query and return self for chaining."""
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params)
        self._last_cursor = cur
        return self

    def fetchone(self):
        """Fetch one row from the last executed query."""
        return self._last_cursor.fetchone()

    def fetchall(self):
        """Fetch all rows from the last executed query."""
        return self._last_cursor.fetchall()

    @property
    def lastrowid(self):
        """Return the last inserted row ID (from RETURNING clause or cursor)."""
        if hasattr(self._last_cursor, "lastrowid"):
            return self._last_cursor.lastrowid
        return None

    def commit(self):
        """Commit the current transaction."""
        self._conn.commit()

    def rollback(self):
        """Rollback the current transaction."""
        self._conn.rollback()

    def close(self):
        """Return connection to the pool exactly once."""
        if self._returned:
            return
        self._returned = True
        if self._pool and self._conn and not self._conn.closed:
            self._pool.putconn(self._conn)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_connection(db_path: Optional[str] = None) -> PgConnection:
    """Return a PostgreSQL connection with dict-like row access.

    The db_path parameter is ignored for PostgreSQL (kept for API compatibility).
    """
    pool = _ensure_pool()
    conn = pool.getconn()
    conn.autocommit = False
    pg_conn = PgConnection(conn, pool)
    return pg_conn


@contextmanager
def connect(db_path: Optional[str] = None):
    """Context manager yielding a PostgreSQL connection with auto-close."""
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    """Verify all required tables exist. Perform zero schema mutations."""
    conn = get_connection(db_path)
    try:
        cur = conn._conn.cursor()
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )
        existing = {row[0] for row in cur.fetchall()}
        missing = [t for t in REQUIRED_TABLES if t not in existing]
        if missing:
            raise RuntimeError(
                f"Missing required tables: {', '.join(missing)}. "
                "Run pathforge/db/migration.sql against the database first."
            )
    finally:
        conn.close()
