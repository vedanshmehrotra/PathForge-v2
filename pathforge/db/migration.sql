-- ============================================================
-- PathForge: PostgreSQL schema migration
-- Run once manually against the live Supabase database.
-- Not executed by the application.
-- ============================================================

-- 1. Add missing column to users
ALTER TABLE users ADD COLUMN IF NOT EXISTS supabase_id TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_supabase_id
    ON users(supabase_id);

-- 2. Add missing columns to problems
ALTER TABLE problems ADD COLUMN IF NOT EXISTS title_slug TEXT;
ALTER TABLE problems ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE problems ADD COLUMN IF NOT EXISTS updated_at TEXT NOT NULL DEFAULT '';

-- 3. Recreate gap_signals (0 rows, verified safe)
DROP TABLE IF EXISTS gap_signals CASCADE;

CREATE TABLE gap_signals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    pattern_id TEXT NOT NULL,
    gap_strength REAL NOT NULL DEFAULT 0.0
        CHECK (gap_strength >= 0.0 AND gap_strength <= 1.0),
    frequency INTEGER NOT NULL DEFAULT 0
        CHECK (frequency >= 0),
    last_seen TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, pattern_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. Create user_pattern_elo (does not exist in live DB)
CREATE TABLE IF NOT EXISTS user_pattern_elo (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    pattern_id TEXT NOT NULL,
    elo REAL NOT NULL DEFAULT 1200.0 CHECK (elo >= 400.0),
    last_updated TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, pattern_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 5. Create problem_ground_truth (does not exist in live DB)
CREATE TABLE IF NOT EXISTS problem_ground_truth (
    problem_id INTEGER PRIMARY KEY,
    patterns TEXT NOT NULL DEFAULT '[]',
    confidence TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE
);

-- 6. Indexes
CREATE INDEX IF NOT EXISTS idx_problems_title_slug ON problems(title_slug);
CREATE INDEX IF NOT EXISTS idx_gap_signals_user ON gap_signals(user_id);
CREATE INDEX IF NOT EXISTS idx_gap_signals_user_strength ON gap_signals(user_id, gap_strength DESC);
CREATE INDEX IF NOT EXISTS idx_gap_signals_user_pattern ON gap_signals(user_id, pattern_id);
CREATE INDEX IF NOT EXISTS idx_user_pattern_elo_user ON user_pattern_elo(user_id);
CREATE INDEX IF NOT EXISTS idx_user_pattern_elo_user_pattern ON user_pattern_elo(user_id, pattern_id);
CREATE INDEX IF NOT EXISTS idx_user_pattern_elo_elo ON user_pattern_elo(elo DESC);
