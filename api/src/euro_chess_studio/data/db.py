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
    opponent_model TEXT,
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
    -- Who attempted the move: participant, model, fallback, presenter.
    -- Databases migrated from before provenance existed carry 'unknown';
    -- those rows are excluded from per-actor metrics rather than guessed.
    actor TEXT NOT NULL,
    -- The model that produced the move, when actor is model or fallback.
    model TEXT,
    created_at TEXT NOT NULL
);

-- One row per raw model reply, immutable, including replies that never
-- became a move. The moves table records what happened to the board;
-- this table records what the model actually said and how it was judged.
CREATE TABLE IF NOT EXISTS model_attempts (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    game_id TEXT REFERENCES games(id),
    task TEXT NOT NULL,
    actor TEXT NOT NULL,
    model TEXT,
    provider_alias TEXT,
    prompt_version TEXT,
    checkpoint TEXT,
    ply INTEGER,
    fen TEXT,
    attempt_number INTEGER NOT NULL,
    status TEXT NOT NULL,
    raw_response TEXT,
    request_ids_json TEXT NOT NULL DEFAULT '[]',
    json_requested INTEGER NOT NULL DEFAULT 0,
    parse_ok INTEGER NOT NULL DEFAULT 0,
    parsed_move TEXT,
    is_legal INTEGER,
    applied_move_id TEXT REFERENCES moves(id),
    error_detail TEXT,
    -- Transport-layer provenance the Chat Completions client already
    -- computes (ChatOutcome): how many HTTP attempts this one reply
    -- took, and whether a capability was dropped after the provider
    -- rejected it. Distinct from attempt_number, which counts the
    -- model turn's own retries, not the transport's.
    transport_attempts INTEGER,
    json_mode_dropped INTEGER,
    reasoning_effort_dropped INTEGER,
    created_at TEXT NOT NULL
);

-- The persisted real-world scenario mapping. The raw suggestion is
-- immutable once written; participant review lands in the final_*
-- columns so an edit never overwrites what the model actually proposed.
CREATE TABLE IF NOT EXISTS scenario_assessments (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    game_id TEXT REFERENCES games(id),
    attempt_id TEXT REFERENCES model_attempts(id),
    ply INTEGER NOT NULL,
    fen TEXT NOT NULL,
    status TEXT NOT NULL,
    suggested_assessment TEXT,
    suggested_real_world TEXT,
    suggested_video_prompt TEXT,
    final_assessment TEXT,
    final_real_world TEXT,
    final_video_prompt TEXT,
    model TEXT,
    provider_alias TEXT,
    prompt_version TEXT,
    error_detail TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
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
    -- Provenance: what the value measures and over what. Computed rows
    -- fill numerator/denominator/scope; cached rows carry the fixture's
    -- note explaining why the number is illustrative.
    numerator INTEGER,
    denominator INTEGER,
    unit TEXT,
    direction TEXT,
    definition TEXT,
    version TEXT,
    scope_json TEXT,
    note TEXT,
    -- model and checkpoint are pulled out of scope_json into real
    -- identity columns: a base and an adapted model's results for the
    -- same metric/workspace must coexist rather than overwrite each
    -- other, and that requires filtering and uniqueness SQL can use
    -- directly, not a JSON blob.
    model TEXT,
    checkpoint TEXT,
    -- Which job execution produced this row (shared by every metric
    -- from one run_job call) and exactly which move/attempt ids fed
    -- the numerator and denominator: the frozen input set, auditable
    -- after the fact instead of re-derived from whatever the tables
    -- happen to contain later.
    run_id TEXT,
    sample_ids_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS presenter_state (
    id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    locked INTEGER NOT NULL,
    active_page_slug TEXT,
    focused_user_id TEXT REFERENCES users(id),
    updated_at TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 0,
    target_frame_id TEXT,
    target_bounds_json TEXT
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
    # database created before a column existed needs it patched in
    # place instead of forcing a reset-db mid-workshop.
    move_columns = {row[1] for row in conn.execute("PRAGMA table_info(moves)")}
    if "game_id" not in move_columns:
        conn.execute("ALTER TABLE moves ADD COLUMN game_id TEXT REFERENCES games(id)")
    if "actor" not in move_columns:
        # Pre-provenance rows genuinely do not record who moved. 'unknown'
        # keeps them out of per-actor metrics instead of guessing.
        conn.execute("ALTER TABLE moves ADD COLUMN actor TEXT NOT NULL DEFAULT 'unknown'")
    if "model" not in move_columns:
        conn.execute("ALTER TABLE moves ADD COLUMN model TEXT")
    eval_columns = {row[1] for row in conn.execute("PRAGMA table_info(eval_results)")}
    for column, column_type in [
        ("numerator", "INTEGER"),
        ("denominator", "INTEGER"),
        ("unit", "TEXT"),
        ("direction", "TEXT"),
        ("definition", "TEXT"),
        ("version", "TEXT"),
        ("scope_json", "TEXT"),
        ("note", "TEXT"),
        ("model", "TEXT"),
        ("checkpoint", "TEXT"),
        ("run_id", "TEXT"),
        ("sample_ids_json", "TEXT"),
    ]:
        if column not in eval_columns:
            conn.execute(f"ALTER TABLE eval_results ADD COLUMN {column} {column_type}")
    attempt_columns = {row[1] for row in conn.execute("PRAGMA table_info(model_attempts)")}
    for column, column_type in [
        ("transport_attempts", "INTEGER"),
        ("json_mode_dropped", "INTEGER"),
        ("reasoning_effort_dropped", "INTEGER"),
    ]:
        if column not in attempt_columns:
            conn.execute(f"ALTER TABLE model_attempts ADD COLUMN {column} {column_type}")
    game_columns = {row[1] for row in conn.execute("PRAGMA table_info(games)")}
    if "opponent_model" not in game_columns:
        conn.execute("ALTER TABLE games ADD COLUMN opponent_model TEXT")
    presenter_columns = {row[1] for row in conn.execute("PRAGMA table_info(presenter_state)")}
    if "revision" not in presenter_columns:
        conn.execute("ALTER TABLE presenter_state ADD COLUMN revision INTEGER NOT NULL DEFAULT 0")
    if "target_frame_id" not in presenter_columns:
        conn.execute("ALTER TABLE presenter_state ADD COLUMN target_frame_id TEXT")
    if "target_bounds_json" not in presenter_columns:
        conn.execute("ALTER TABLE presenter_state ADD COLUMN target_bounds_json TEXT")
    conn.commit()
