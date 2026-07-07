"""SQLite connection and schema management. No business logic here."""

import sqlite3
from pathlib import Path

from euro_chess_studio.config import get_db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pages (
    id TEXT PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    modality TEXT NOT NULL,
    order_index INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    page_id TEXT NOT NULL REFERENCES pages(id),
    shape_id TEXT NOT NULL,
    position_index INTEGER NOT NULL,
    selected_snippet_id TEXT,
    board_fen TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (user_id, page_id)
);

CREATE TABLE IF NOT EXISTS games (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    time_limit_seconds INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    result TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS moves (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    game_id TEXT REFERENCES games(id),
    ply INTEGER NOT NULL,
    uci TEXT NOT NULL,
    san TEXT,
    fen_before TEXT NOT NULL,
    fen_after TEXT NOT NULL,
    is_legal INTEGER NOT NULL,
    is_check INTEGER NOT NULL,
    is_checkmate INTEGER NOT NULL,
    reward INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dataset_rows (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    move_id TEXT REFERENCES moves(id),
    shape TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job_configs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT REFERENCES workspaces(id),
    job_type TEXT NOT NULL,
    params_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    job_config_id TEXT REFERENCES job_configs(id),
    modality TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    cached INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eval_results (
    id TEXT PRIMARY KEY,
    modality TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    workspace_id TEXT REFERENCES workspaces(id),
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS presenter_state (
    id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    locked INTEGER NOT NULL,
    active_page_slug TEXT,
    focused_user_id TEXT REFERENCES users(id),
    updated_at TEXT NOT NULL
);
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    # FastAPI runs sync route/dependency code in a thread pool, and a
    # generator dependency's setup and teardown aren't guaranteed to land on
    # the same worker thread. sqlite3 refuses to open/close across threads
    # by default (check_same_thread=True), so disable that check here; each
    # request still gets its own connection, opened and closed within that
    # request's handling, never shared concurrently.
    conn = sqlite3.connect(db_path or get_db_path(), check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # A room of 40 attendees means 40 threads committing at once. WAL
    # lets readers proceed during writes, and the busy timeout queues
    # colliding writers instead of throwing "database is locked".
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    # CREATE TABLE IF NOT EXISTS never alters an existing table, so a
    # database created before the games feature is missing moves.game_id.
    # Patch it in place instead of forcing a reset-db mid-workshop.
    move_columns = {row[1] for row in conn.execute("PRAGMA table_info(moves)")}
    if "game_id" not in move_columns:
        conn.execute("ALTER TABLE moves ADD COLUMN game_id TEXT REFERENCES games(id)")
    conn.commit()
