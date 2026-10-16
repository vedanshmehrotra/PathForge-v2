-- PostgreSQL schema for PathForge

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    experience_level TEXT,
    confident_areas TEXT NOT NULL DEFAULT '[]',
    onboarding_complete BOOLEAN NOT NULL DEFAULT FALSE,
    last_recommendation_id INTEGER,
    current_streak INTEGER NOT NULL DEFAULT 0,
    last_submission_date TEXT,
    supabase_id TEXT UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
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
    premium_only BOOLEAN NOT NULL DEFAULT FALSE,
    category TEXT,
    likes INTEGER,
    dislikes INTEGER,
    similar_questions TEXT,
    title_slug TEXT,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS submissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    problem_id INTEGER,
    code_text TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('pass', 'fail', 'error', 'tle')),
    detected_pattern TEXT,
    detected_confidence REAL NOT NULL DEFAULT 0.0 CHECK (detected_confidence >= 0.0 AND detected_confidence <= 1.0),
    expected_pattern TEXT,
    target_pattern TEXT,
    gap_identified BOOLEAN NOT NULL DEFAULT FALSE,
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
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    problem_id INTEGER,
    topic TEXT NOT NULL,
    reason TEXT,
    confidence_tier TEXT CHECK (confidence_tier IN ('specific', 'topic_hint', 'general_hint')),
    acted_on BOOLEAN NOT NULL DEFAULT FALSE,
    followed BOOLEAN NOT NULL DEFAULT FALSE,
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

CREATE TABLE IF NOT EXISTS gap_signals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    pattern_id TEXT NOT NULL,
    gap_strength REAL NOT NULL DEFAULT 0.0 CHECK (gap_strength >= 0.0 AND gap_strength <= 1.0),
    frequency INTEGER NOT NULL DEFAULT 0 CHECK (frequency >= 0),
    last_seen TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, pattern_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_gap_signals_user ON gap_signals(user_id);
CREATE INDEX IF NOT EXISTS idx_gap_signals_user_strength ON gap_signals(user_id, gap_strength DESC);
CREATE INDEX IF NOT EXISTS idx_gap_signals_user_pattern ON gap_signals(user_id, pattern_id);

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

CREATE INDEX IF NOT EXISTS idx_user_pattern_elo_user ON user_pattern_elo(user_id);
CREATE INDEX IF NOT EXISTS idx_user_pattern_elo_user_pattern ON user_pattern_elo(user_id, pattern_id);
CREATE INDEX IF NOT EXISTS idx_user_pattern_elo_elo ON user_pattern_elo(elo DESC);

CREATE TABLE IF NOT EXISTS problem_ground_truth (
    problem_id INTEGER PRIMARY KEY,
    patterns TEXT NOT NULL DEFAULT '[]',
    confidence TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE
);

-- Migration: add columns missing from original PG schema
ALTER TABLE problems ADD COLUMN IF NOT EXISTS title_slug TEXT;
ALTER TABLE problems ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE problems ADD COLUMN IF NOT EXISTS updated_at TEXT NOT NULL DEFAULT '';
CREATE INDEX IF NOT EXISTS idx_problems_title_slug ON problems(title_slug);

-- Phase 0B: submission evidence fields
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS verdict_type TEXT DEFAULT 'authoritative';
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS detected_patterns_json JSONB;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS code_hash TEXT;

-- Phase 0C: ground truth solution groups
ALTER TABLE problem_ground_truth ADD COLUMN IF NOT EXISTS solution_groups JSONB;
ALTER TABLE problem_ground_truth ADD COLUMN IF NOT EXISTS validation_status TEXT DEFAULT 'unobserved';

-- Phase 3A: shadow analysis persistence
-- Canonical structural facts (re-derivable source of truth)
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS structural_facts_json JSONB;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS shadow_extractor_version TEXT;
-- Derived technique/strategy evidence (cached projections)
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS technique_evidence_json JSONB;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS strategy_evidence_json JSONB;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS shadow_match_outcome_json JSONB;
-- Version tracking for re-derivation
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS shadow_technique_def_version TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS shadow_strategy_def_version TEXT;
