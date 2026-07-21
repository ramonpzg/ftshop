"""SQLite connection and schema. Repositories hold no business logic
and never commit; the action that composes them owns the transaction."""

import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    result TEXT,
    termination TEXT,
    duration_seconds REAL
);

CREATE TABLE IF NOT EXISTS plies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL REFERENCES games(id),
    ply INTEGER NOT NULL,
    actor TEXT NOT NULL,
    uci TEXT NOT NULL,
    san TEXT NOT NULL,
    fen_before TEXT NOT NULL,
    fen_after TEXT NOT NULL,
    is_capture INTEGER NOT NULL,
    comment TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (game_id, ply)
);

CREATE TABLE IF NOT EXISTS model_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL REFERENCES games(id),
    ply INTEGER NOT NULL,
    attempt INTEGER NOT NULL,
    corrective INTEGER NOT NULL,
    status TEXT NOT NULL,
    raw_reply TEXT,
    parsed_move TEXT,
    comment TEXT,
    request_id TEXT,
    latency_ms INTEGER,
    error_detail TEXT,
    created_at TEXT NOT NULL
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn
