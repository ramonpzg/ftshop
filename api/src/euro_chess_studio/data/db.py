"""SQLite connection and schema management. No business logic here."""

import sqlite3
from pathlib import Path

from euro_chess_studio.config import get_db_path

# The column list is shared between the CREATE in SCHEMA and the
# nullability rebuild in init_db, so the two can never drift apart.
MODEL_ATTEMPTS_COLUMNS_SQL = """(
    id TEXT PRIMARY KEY,
    -- Nullable since phase 34: an organic game attempt belongs to a
    -- workspace, a benchmark attempt belongs to the room (a frozen
    -- evaluation suite, not any attendee's board).
    workspace_id TEXT REFERENCES workspaces(id),
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
    -- 'live' when the row records a real provider reply (or failure);
    -- 'replayed' when the raw_response was loaded from a reviewed
    -- fixture. A replayed row never carries provider request ids and
    -- never poses as a live model attempt.
    reply_source TEXT NOT NULL DEFAULT 'live',
    -- Set on benchmark attempts only: which benchmark run produced the
    -- row and which frozen suite example it answered.
    benchmark_run_id TEXT,
    suite_example_id TEXT,
    created_at TEXT NOT NULL
)"""

SCHEMA = f"""
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
CREATE TABLE IF NOT EXISTS model_attempts {MODEL_ATTEMPTS_COLUMNS_SQL};

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
    -- the numerator and denominator: an audit trail back to the
    -- underlying rows, auditable after the fact instead of re-derived
    -- from whatever the tables happen to contain later.
    run_id TEXT,
    sample_ids_json TEXT,
    -- The actual frozen input set: the exact fens the sample rows were
    -- about (position_set_json), and a deterministic hash of that set
    -- (position_set_id) so two rows -- a base and an adapted model, or
    -- two runs of the same model -- can prove they measured the same
    -- positions instead of assuming it from matching scope alone.
    -- Included in a computed row's replace identity, so a genuinely
    -- different position set (a different evaluation window) coexists
    -- instead of silently overwriting an earlier one for the same
    -- model/checkpoint.
    position_set_id TEXT,
    position_set_json TEXT,
    created_at TEXT NOT NULL
);

-- A frozen training dataset: the exact SFT rows, hashed, with the
-- eligibility and approval counts that explain what was kept out.
-- rows_json makes the snapshot self-contained: the source dataset_rows
-- can be reset later without the snapshot losing what it froze.
CREATE TABLE IF NOT EXISTS dataset_snapshots (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    modality TEXT NOT NULL,
    -- 'seeded' for the reviewed reference fixture, 'frozen' for a
    -- snapshot taken from the room's own play.
    origin TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    excluded_ineligible_count INTEGER NOT NULL,
    source_game_count INTEGER NOT NULL,
    source_workspace_count INTEGER NOT NULL,
    -- Scenario mappings ride along as counts so raw model suggestions
    -- and participant-approved mappings stay distinguishable.
    scenario_raw_count INTEGER NOT NULL,
    scenario_approved_count INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    rows_json TEXT NOT NULL,
    source_row_ids_json TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL
);

-- A frozen evaluation suite: durable example ids, the exact FEN and
-- rendered prompt for every example (duplicates preserved as real
-- multiplicity), a content hash, and the position-set hash both
-- benchmark checkpoints must reproduce for a comparison to be honest.
CREATE TABLE IF NOT EXISTS eval_suites (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    modality TEXT NOT NULL,
    origin TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    example_count INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    position_set_id TEXT NOT NULL,
    examples_json TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL
);

-- Durable adapter provenance: which base checkpoint, which frozen
-- dataset (by id and content hash), which configuration (by hash and
-- in full), which runner produced it and whether the result was a
-- cached replay or a live run. An adapter without these is not
-- reproducible, so none of them are optional.
CREATE TABLE IF NOT EXISTS adapters (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    modality TEXT NOT NULL,
    checkpoint TEXT NOT NULL,
    base_model TEXT NOT NULL,
    method TEXT NOT NULL,
    seed INTEGER NOT NULL,
    output_task TEXT NOT NULL,
    config_id TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    config_json TEXT NOT NULL,
    dataset_snapshot_id TEXT NOT NULL REFERENCES dataset_snapshots(id),
    dataset_content_hash TEXT NOT NULL,
    runner TEXT NOT NULL,
    result_source TEXT NOT NULL,
    limitations TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- One row per benchmark execution: which suite (by id and content
-- hash), which checkpoint and resolved model, whether replies were
-- live or replayed, and the position-set hash of what actually got
-- measured. The id doubles as the run_id on eval_results rows and the
-- benchmark_run_id on model_attempts rows.
CREATE TABLE IF NOT EXISTS benchmark_runs (
    id TEXT PRIMARY KEY,
    suite_id TEXT NOT NULL REFERENCES eval_suites(id),
    suite_content_hash TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    checkpoint TEXT NOT NULL,
    model TEXT NOT NULL,
    provider_alias TEXT,
    source TEXT NOT NULL,
    example_count INTEGER NOT NULL,
    reply_count INTEGER NOT NULL,
    transport_failed_count INTEGER NOT NULL,
    position_set_id TEXT,
    job_config_id TEXT REFERENCES job_configs(id),
    note TEXT,
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


def _relax_model_attempts_workspace(conn: sqlite3.Connection) -> None:
    """Databases created before phase 34 declared workspace_id NOT NULL.
    Benchmark attempts belong to the room rather than any workspace, and
    SQLite has no ALTER COLUMN, so this is the documented rebuild:
    create the current shape, copy every row, swap the tables. Runs once
    per old database and is a no-op afterwards."""
    workspace_column = next(
        row for row in conn.execute("PRAGMA table_info(model_attempts)") if row[1] == "workspace_id"
    )
    not_null = bool(workspace_column[3])
    if not not_null:
        return
    # The ALTER statements above may have opened an implicit
    # transaction; PRAGMA foreign_keys is silently ignored inside one.
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        conn.execute(f"CREATE TABLE model_attempts_rebuilt {MODEL_ATTEMPTS_COLUMNS_SQL}")
        columns = ", ".join(
            row[1] for row in conn.execute("PRAGMA table_info(model_attempts_rebuilt)")
        )
        conn.execute(
            f"INSERT INTO model_attempts_rebuilt ({columns}) SELECT {columns} FROM model_attempts"
        )
        conn.execute("DROP TABLE model_attempts")
        conn.execute("ALTER TABLE model_attempts_rebuilt RENAME TO model_attempts")
        conn.commit()
    except Exception:
        conn.rollback()
        # CREATE TABLE ran in autocommit if the BEGIN itself failed;
        # make sure a half-made rebuild table never survives.
        conn.execute("DROP TABLE IF EXISTS model_attempts_rebuilt")
        raise
    finally:
        # SQLite never re-checks existing rows when this turns back on;
        # a legacy database's orphaned rows stay untouched rather than
        # failing a startup migration mid-workshop.
        conn.execute("PRAGMA foreign_keys = ON")


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
        ("position_set_id", "TEXT"),
        ("position_set_json", "TEXT"),
    ]:
        if column not in eval_columns:
            conn.execute(f"ALTER TABLE eval_results ADD COLUMN {column} {column_type}")
    attempt_columns = {row[1] for row in conn.execute("PRAGMA table_info(model_attempts)")}
    for column, column_type in [
        ("transport_attempts", "INTEGER"),
        ("json_mode_dropped", "INTEGER"),
        ("reasoning_effort_dropped", "INTEGER"),
        ("reply_source", "TEXT NOT NULL DEFAULT 'live'"),
        ("benchmark_run_id", "TEXT"),
        ("suite_example_id", "TEXT"),
    ]:
        if column not in attempt_columns:
            conn.execute(f"ALTER TABLE model_attempts ADD COLUMN {column} {column_type}")
    _relax_model_attempts_workspace(conn)
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
