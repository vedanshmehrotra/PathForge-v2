import logging
import os
from contextlib import contextmanager
from typing import Optional

import psycopg2
import psycopg2.extras
import psycopg2.pool

logger = logging.getLogger(__name__)


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
    """Verify all required tables exist, then apply idempotent schema migrations.

    The migration section of schema_pg.sql contains ALTER TABLE statements
    using ADD COLUMN IF NOT EXISTS which are safe to run repeatedly.
    """
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
                "Run pathforge/db/schema_pg.sql against the database first."
            )

        # Apply idempotent migrations (ADD COLUMN IF NOT EXISTS, CREATE INDEX IF NOT EXISTS)
        _apply_migrations(conn)
    finally:
        conn.close()


def _strip_comment_lines(sql_text: str) -> str:
    """Remove SQL comment-only lines (lines starting with --) from a statement.

    Inline comments within a statement are preserved. Only lines that are
    entirely a SQL comment (optionally with leading whitespace) are removed.
    This allows classification of statements that have a leading comment
    before the actual DDL keyword.
    """
    lines = sql_text.split("\n")
    stripped_lines = [line for line in lines if not line.strip().startswith("--")]
    return "\n".join(stripped_lines)


def _classify_statement(stmt: str) -> str:
    """Classify a SQL statement after stripping leading comments.

    Returns:
        'migration' for ALTER TABLE / CREATE INDEX (idempotent DDL)
        'skip' for CREATE TABLE, comments, or other statements
    """
    cleaned = _strip_comment_lines(stmt).strip()
    if not cleaned:
        return "skip"
    upper = cleaned.upper()
    if upper.startswith("ALTER TABLE") or upper.startswith("CREATE INDEX"):
        return "migration"
    return "skip"


def _extract_statements(sql: str) -> list[str]:
    """Split SQL file into individual statements by semicolon delimiter.

    Returns stripped, non-empty statement chunks.
    """
    statements = []
    for raw in sql.split(";"):
        stmt = raw.strip()
        if stmt:
            statements.append(stmt)
    return statements


def _apply_migrations(conn) -> None:
    """Execute idempotent DDL statements from schema_pg.sql.

    Strategy: Commit each statement individually. This ensures that if one
    migration fails (e.g., incompatible type change), all prior successful
    migrations are preserved. Each statement uses IF NOT EXISTS, making
    re-execution safe.
    """
    import os
    schema_path = os.path.join(os.path.dirname(__file__), "schema_pg.sql")
    if not os.path.exists(schema_path):
        return

    with open(schema_path, "r") as f:
        sql = f.read()

    cur = conn._conn.cursor()
    for stmt in _extract_statements(sql):
        if _classify_statement(stmt) != "migration":
            continue
        # Reconstruct the executable SQL by stripping leading comment lines
        # but preserving the actual DDL and any inline comments.
        executable = _strip_comment_lines(stmt).strip()
        try:
            cur.execute(executable)
            conn._conn.commit()
        except Exception as exc:
            # Roll back this single failed statement; prior commits are safe.
            conn._conn.rollback()
            logger.warning(
                "Migration statement failed (continuing): %s — %s",
                executable[:120],
                exc,
            )
