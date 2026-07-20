"""Migration tests: a database created before phase 33 gains provenance
columns and the new tables without losing a single move."""

from pathlib import Path

import chess

from euro_chess_studio.data.db import get_connection, init_db

# The schema as it stood before this phase: no actor or model on moves,
# no provenance columns on eval_results, no model_attempts or
# scenario_assessments tables.
PRE_PHASE_33_SCHEMA = """
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE pages (
    id TEXT PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    modality TEXT NOT NULL,
    order_index INTEGER NOT NULL
);
CREATE TABLE workspaces (
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
CREATE TABLE games (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    time_limit_seconds INTEGER NOT NULL,
    opponent_model TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    result TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE moves (
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
CREATE TABLE dataset_rows (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    move_id TEXT REFERENCES moves(id),
    shape TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE eval_results (
    id TEXT PRIMARY KEY,
    modality TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    workspace_id TEXT REFERENCES workspaces(id),
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def build_pre_phase_db(path: Path):
    conn = get_connection(path)
    conn.executescript(PRE_PHASE_33_SCHEMA)
    conn.execute("INSERT INTO users VALUES ('user_1', 'Ada', 'then')")
    conn.execute("INSERT INTO pages VALUES ('page_1', 'chess-machine', 'Text', 'text', 0)")
    conn.execute(
        "INSERT INTO workspaces VALUES ('ws_1', 'user_1', 'page_1', 'shape:1', 0, NULL, ?, 'then')",
        (chess.STARTING_FEN,),
    )
    conn.execute(
        "INSERT INTO games VALUES ('game_1', 'ws_1', 300, NULL, 'then', 'later', 'win', 'then')"
    )
    conn.execute(
        "INSERT INTO moves VALUES ('move_1', 'ws_1', 'game_1', 0, 'e2e4', 'e4', "
        "'fen-a', 'fen-b', 1, 0, 0, 1, 'then')"
    )
    conn.execute(
        "INSERT INTO moves VALUES ('move_2', 'ws_1', 'game_1', 1, 'e9e4', NULL, "
        "'fen-b', 'fen-b', 0, 0, 0, -1, 'then')"
    )
    conn.execute(
        "INSERT INTO dataset_rows VALUES ('dsrow_1', 'ws_1', 'move_1', 'fen_to_move', '{}', 'then')"
    )
    conn.execute(
        "INSERT INTO eval_results VALUES ('eval_1', 'text', 'legal_move_rate', 0.5, "
        "'ws_1', 'computed', 'then')"
    )
    conn.commit()
    return conn


def test_pre_phase_database_migrates_without_losing_moves(tmp_path: Path):
    conn = build_pre_phase_db(tmp_path / "old.db")
    try:
        init_db(conn)

        moves = conn.execute("SELECT * FROM moves ORDER BY id").fetchall()
        assert [move["id"] for move in moves] == ["move_1", "move_2"]
        assert moves[0]["san"] == "e4" and moves[0]["is_legal"] == 1
        assert moves[1]["is_legal"] == 0
        # Pre-provenance rows do not record who moved; they are labelled
        # unknown, not guessed.
        assert all(move["actor"] == "unknown" for move in moves)
        assert all(move["model"] is None for move in moves)

        eval_row = conn.execute("SELECT * FROM eval_results").fetchone()
        assert eval_row["value"] == 0.5
        assert eval_row["note"] is None
        # Pre-scope-identity rows migrate in with no model/checkpoint/
        # run_id: they read as "unscoped", not as belonging to some
        # accidental model.
        assert eval_row["model"] is None
        assert eval_row["checkpoint"] is None
        assert eval_row["run_id"] is None
        assert eval_row["sample_ids_json"] is None

        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert {"model_attempts", "scenario_assessments"}.issubset(tables)
    finally:
        conn.close()


def test_migration_is_idempotent_and_new_moves_record_their_actor(tmp_path: Path):
    conn = build_pre_phase_db(tmp_path / "old.db")
    try:
        init_db(conn)
        init_db(conn)

        from euro_chess_studio.data.moves_repo import insert_move

        row = insert_move(
            conn,
            workspace_id="ws_1",
            uci="g8f6",
            san="Nf6",
            fen_before="fen-b",
            fen_after="fen-c",
            is_legal=True,
            is_check=False,
            is_checkmate=False,
            reward=1,
            actor="model",
            model="gpt-5.6-luna",
            game_id="game_1",
        )
        conn.commit()
        assert row["actor"] == "model"
        assert row["model"] == "gpt-5.6-luna"
    finally:
        conn.close()


def test_pre_capability_provenance_model_attempts_table_migrates(tmp_path: Path):
    """A database from between the model_attempts table's introduction
    and the capability-provenance fix: the table exists but without
    transport_attempts/json_mode_dropped/reasoning_effort_dropped."""
    conn = get_connection(tmp_path / "mid.db")
    conn.executescript("""
        CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE model_attempts (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            game_id TEXT,
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
            applied_move_id TEXT,
            error_detail TEXT,
            created_at TEXT NOT NULL
        );
    """)
    conn.execute(
        "INSERT INTO model_attempts "
        "(id, workspace_id, task, actor, attempt_number, status, created_at) "
        "VALUES ('attempt_1', 'ws_1', 'move', 'model', 1, 'applied', 'then')"
    )
    conn.commit()
    try:
        init_db(conn)
        row = conn.execute("SELECT * FROM model_attempts WHERE id = 'attempt_1'").fetchone()
        assert row["transport_attempts"] is None
        assert row["json_mode_dropped"] is None
        assert row["reasoning_effort_dropped"] is None

        from euro_chess_studio.data.model_attempts_repo import insert_attempt

        new_row = insert_attempt(
            conn,
            workspace_id="ws_1",
            task="move",
            actor="model",
            attempt_number=1,
            status="applied",
            transport_attempts=2,
            json_mode_dropped=True,
            reasoning_effort_dropped=False,
        )
        conn.commit()
        assert new_row["transport_attempts"] == 2
        assert new_row["json_mode_dropped"] == 1
        assert new_row["reasoning_effort_dropped"] == 0
    finally:
        conn.close()
