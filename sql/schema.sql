-- SQLite schema for Doit state & audit tracking
-- Compatible with Win11 & Ubuntu. Runs once on DB init.

PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS goals (
    goal_id TEXT PRIMARY KEY,
    project TEXT NOT NULL,
    query TEXT NOT NULL,
    status TEXT CHECK(status IN ('planning', 'in_progress', 'completed', 'blocked', 'failed')) DEFAULT 'planning',
    current_step INTEGER DEFAULT 0,
    max_steps INTEGER DEFAULT 15,
    plan_json TEXT,
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id TEXT REFERENCES goals(goal_id),
    step_index INTEGER NOT NULL,
    tool_name TEXT,
    parameters TEXT,
    result TEXT,
    rationale TEXT,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id TEXT,
    event_type TEXT,
    prompt_hash TEXT,
    response_snippet TEXT,
    created_at DATETIME DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_steps_goal ON steps(goal_id);
CREATE INDEX IF NOT EXISTS idx_audit_goal ON audit_log(goal_id);