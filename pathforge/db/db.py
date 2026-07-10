import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = PACKAGE_DIR.parent / "pathforge.sqlite3"
SCHEMA_PATH = PACKAGE_DIR / "schema.sql"


def get_connection(db_path=None):
    """Return a SQLite connection with row dictionaries and foreign keys enabled."""
    path = db_path or os.environ.get("PATHFORGE_DB_PATH") or DEFAULT_DB_PATH
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")  
    return connection


@contextmanager
def connect(db_path=None):
    """Context manager yielding a SQLite connection with WAL mode, busy_timeout, and auto-close."""
    connection = get_connection(db_path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA synchronous=NORMAL")
    try:
        yield connection
    finally:
        connection.close()


def init_db(db_path=None):
    """Create all PathForge database tables and indexes from schema.sql."""
    connection = get_connection(db_path)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as schema_file:
        connection.executescript(schema_file.read())
    _apply_lightweight_migrations(connection)
    connection.commit()
    return connection


def _ensure_gap_signals_table(connection):
    tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "gap_signals" not in tables:
        connection.execute("""
            CREATE TABLE gap_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                pattern_id TEXT NOT NULL,
                gap_strength REAL NOT NULL DEFAULT 0.0 CHECK (gap_strength >= 0.0 AND gap_strength <= 1.0),
                frequency INTEGER NOT NULL DEFAULT 0 CHECK (frequency >= 0),
                last_seen TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, pattern_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        connection.execute("CREATE INDEX idx_gap_signals_user ON gap_signals(user_id)")
        connection.execute("CREATE INDEX idx_gap_signals_user_strength ON gap_signals(user_id, gap_strength DESC)")
        connection.execute("CREATE INDEX idx_gap_signals_user_pattern ON gap_signals(user_id, pattern_id)")


def _ensure_user_pattern_elo_table(connection):
    tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "user_pattern_elo" not in tables:
        connection.execute("""
            CREATE TABLE user_pattern_elo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                pattern_id TEXT NOT NULL,
                elo REAL NOT NULL DEFAULT 1200.0 CHECK (elo >= 400.0),
                last_updated TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, pattern_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        connection.execute("CREATE INDEX idx_user_pattern_elo_user ON user_pattern_elo(user_id)")
        connection.execute("CREATE INDEX idx_user_pattern_elo_user_pattern ON user_pattern_elo(user_id, pattern_id)")
        connection.execute("CREATE INDEX idx_user_pattern_elo_elo ON user_pattern_elo(elo DESC)")


def _ensure_problem_ground_truth_table(connection):
    tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "problem_ground_truth" not in tables:
        connection.execute("""
            CREATE TABLE problem_ground_truth (
                problem_id INTEGER PRIMARY KEY,
                patterns TEXT NOT NULL DEFAULT '[]',
                confidence TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE
            )
        """)


def _ensure_problem_metadata_columns(connection):
    """Add title_slug and description columns to problems table if missing."""
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(problems)").fetchall()}
    if "title_slug" not in columns:
        connection.execute("ALTER TABLE problems ADD COLUMN title_slug TEXT")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_problems_title_slug ON problems(title_slug)")
    if "description" not in columns:
        connection.execute("ALTER TABLE problems ADD COLUMN description TEXT")
    backfill = connection.execute(
        "SELECT COUNT(*) AS c FROM problems WHERE title_slug IS NULL AND link IS NOT NULL AND link LIKE '%/problems/%'"
        ).fetchone()["c"]
    if backfill > 0:
        connection.execute("""
            UPDATE problems
            SET title_slug = RTRIM(
                SUBSTR(link, INSTR(link, '/problems/') + 10),
                '/'
            )
            WHERE title_slug IS NULL AND link IS NOT NULL AND link LIKE '%/problems/%'
        """)


def _apply_lightweight_migrations(connection):
    """Add new nullable columns when an older local SQLite file already exists."""
    _ensure_gap_signals_table(connection)
    _ensure_user_pattern_elo_table(connection)
    _ensure_problem_ground_truth_table(connection)
    _ensure_problem_metadata_columns(connection)

    user_columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
    if "supabase_id" not in user_columns:
        # SQLite does not support ADD COLUMN ... UNIQUE; add the column then create the index
        connection.execute("ALTER TABLE users ADD COLUMN supabase_id TEXT")
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_supabase_id ON users(supabase_id)")
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(submissions)").fetchall()}
    if "diagnosis_confidence" not in columns:
        connection.execute("ALTER TABLE submissions ADD COLUMN diagnosis_confidence REAL NOT NULL DEFAULT 0.0")
    if "target_pattern" not in columns:
        connection.execute("ALTER TABLE submissions ADD COLUMN target_pattern TEXT")

    user_columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
    if "experience_level" not in user_columns:
        connection.execute("ALTER TABLE users ADD COLUMN experience_level TEXT")
    if "confident_areas" not in user_columns:
        connection.execute("ALTER TABLE users ADD COLUMN confident_areas TEXT NOT NULL DEFAULT '[]'")
    if "onboarding_complete" not in user_columns:
        connection.execute("ALTER TABLE users ADD COLUMN onboarding_complete INTEGER NOT NULL DEFAULT 0")
    if "last_recommendation_id" not in user_columns:
        connection.execute("ALTER TABLE users ADD COLUMN last_recommendation_id INTEGER")
    if "current_streak" not in user_columns:
        connection.execute("ALTER TABLE users ADD COLUMN current_streak INTEGER NOT NULL DEFAULT 0")
    if "last_submission_date" not in user_columns:
        connection.execute("ALTER TABLE users ADD COLUMN last_submission_date TEXT")

    recommendation_columns = {row["name"] for row in connection.execute("PRAGMA table_info(recommendations)").fetchall()}
    if "followed" not in recommendation_columns:
        connection.execute("ALTER TABLE recommendations ADD COLUMN followed INTEGER NOT NULL DEFAULT 0")
    if "elo_delta_after" not in recommendation_columns:
        connection.execute("ALTER TABLE recommendations ADD COLUMN elo_delta_after REAL DEFAULT NULL")
