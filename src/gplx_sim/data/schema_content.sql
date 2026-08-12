PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS content_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS situations (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id),
    title TEXT NOT NULL,
    video_filename TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS question_parts (
    id INTEGER PRIMARY KEY,
    situation_id INTEGER NOT NULL REFERENCES situations(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    prompt TEXT NOT NULL,
    display_order INTEGER NOT NULL,
    UNIQUE (situation_id, kind)
);

CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY,
    question_part_id INTEGER NOT NULL REFERENCES question_parts(id) ON DELETE CASCADE,
    answer_text TEXT NOT NULL,
    is_correct INTEGER NOT NULL DEFAULT 0 CHECK (is_correct IN (0, 1)),
    display_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS practice_sets (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS practice_set_items (
    practice_set_id INTEGER NOT NULL REFERENCES practice_sets(id) ON DELETE CASCADE,
    situation_id INTEGER NOT NULL REFERENCES situations(id),
    display_order INTEGER NOT NULL,
    PRIMARY KEY (practice_set_id, situation_id)
);
