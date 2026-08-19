PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    total_situations INTEGER NOT NULL,
    score REAL,
    score_on_ten REAL
);

CREATE TABLE IF NOT EXISTS session_situations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    situation_id INTEGER NOT NULL,
    situation_code TEXT NOT NULL,
    situation_title TEXT NOT NULL,
    display_order INTEGER NOT NULL,
    score REAL
);

CREATE TABLE IF NOT EXISTS session_answers (
    session_situation_id INTEGER NOT NULL REFERENCES session_situations(id) ON DELETE CASCADE,
    part_id INTEGER NOT NULL,
    selected_answer_id INTEGER,
    correct_answer_id INTEGER NOT NULL,
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    PRIMARY KEY (session_situation_id, part_id)
);

CREATE TABLE IF NOT EXISTS exam_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_code TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    candidate_name TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    total_situations INTEGER NOT NULL,
    score REAL,
    score_on_ten REAL,
    UNIQUE (exam_code, candidate_id)
);
