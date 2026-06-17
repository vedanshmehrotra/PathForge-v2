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


def _apply_lightweight_migrations(connection):
    """Add new nullable columns when an older local SQLite file already exists."""
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
