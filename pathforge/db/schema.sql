PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    experience_level TEXT,
    confident_areas TEXT NOT NULL DEFAULT '[]',
    onboarding_complete INTEGER NOT NULL DEFAULT 0 CHECK (onboarding_complete IN (0, 1)),
    last_recommendation_id INTEGER,
    current_streak INTEGER NOT NULL DEFAULT 0,
    last_submission_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (last_recommendation_id) REFERENCES recommendations(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS problems (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
    topics TEXT NOT NULL,
    pattern TEXT NOT NULL,
    test_cases TEXT NOT NULL,
    link TEXT,
    acceptance_rate REAL,
    premium_only INTEGER NOT NULL DEFAULT 0 CHECK (premium_only IN (0, 1)),
    category TEXT,
    likes INTEGER,
    dislikes INTEGER,
    similar_questions TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    problem_id INTEGER,
    code_text TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('pass', 'fail', 'error', 'tle')),
    detected_pattern TEXT,
    detected_confidence REAL NOT NULL DEFAULT 0.0 CHECK (detected_confidence >= 0.0 AND detected_confidence <= 1.0),
    expected_pattern TEXT NOT NULL,
    target_pattern TEXT,
    gap_identified INTEGER NOT NULL CHECK (gap_identified IN (0, 1)),
    diagnosis_confidence REAL NOT NULL DEFAULT 0.0 CHECK (diagnosis_confidence >= 0.0 AND diagnosis_confidence <= 1.0),
    time_taken_seconds INTEGER,
    attempt_number INTEGER NOT NULL DEFAULT 1 CHECK (attempt_number >= 1),
    topic TEXT NOT NULL,
    elo_before REAL,
    elo_after REAL,
    submitted_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS topic_profiles (
    user_id INTEGER NOT NULL,
    topic TEXT NOT NULL,
    elo_rating REAL NOT NULL DEFAULT 800.0 CHECK (elo_rating >= 400.0),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    pass_count INTEGER NOT NULL DEFAULT 0,
    pattern_match_count INTEGER NOT NULL DEFAULT 0,
    accuracy REAL NOT NULL DEFAULT 0.0 CHECK (accuracy >= 0.0 AND accuracy <= 1.0),
    recent_failures INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, topic),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    problem_id INTEGER,
    topic TEXT NOT NULL,
    reason TEXT,
    confidence_tier TEXT CHECK (confidence_tier IN ('specific', 'topic_hint', 'general_hint')),
    acted_on INTEGER NOT NULL DEFAULT 0 CHECK (acted_on IN (0, 1)),
    followed INTEGER NOT NULL DEFAULT 0 CHECK (followed IN (0, 1)),
    elo_delta_after REAL DEFAULT NULL,
    created_at TEXT NOT NULL,
    acted_on_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_problems_difficulty ON problems(difficulty);
CREATE INDEX IF NOT EXISTS idx_problems_pattern ON problems(pattern);
CREATE INDEX IF NOT EXISTS idx_submissions_user_time ON submissions(user_id, submitted_at);
CREATE INDEX IF NOT EXISTS idx_submissions_problem ON submissions(problem_id);
CREATE INDEX IF NOT EXISTS idx_submissions_user_topic ON submissions(user_id, topic);
CREATE INDEX IF NOT EXISTS idx_topic_profiles_user_elo ON topic_profiles(user_id, elo_rating);
CREATE INDEX IF NOT EXISTS idx_recommendations_user_time ON recommendations(user_id, created_at);
