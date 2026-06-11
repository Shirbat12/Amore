-- Relational store schema for A-MORE (section 2.1).
-- Structured, consistent data: users, their baseline, and per-date metrics.
-- Rich/semi-structured fields (tag lists, profile tokens) are kept as JSON text
-- here for convenience and mirrored in full in the JSON document store.

CREATE TABLE IF NOT EXISTS users (
    user_id               TEXT PRIMARY KEY,
    baseline_first_dates  INTEGER DEFAULT 0,
    baseline_second_dates INTEGER DEFAULT 0,
    baseline_burnout      INTEGER
);

CREATE TABLE IF NOT EXISTS dates (
    id           TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL,
    vas          REAL NOT NULL,
    sentiment    REAL DEFAULT 0,
    second_date  INTEGER,              -- 1 yes / 0 no / NULL maybe
    created_at   TEXT NOT NULL,
    vas_scores   TEXT,                 -- JSON
    profile      TEXT,                 -- JSON list of dry tokens
    tags         TEXT,                 -- JSON list of character tags
    topic_tags   TEXT,                 -- JSON
    vibe_tags    TEXT,                 -- JSON
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

CREATE INDEX IF NOT EXISTS idx_dates_user ON dates (user_id);
