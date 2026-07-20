from pathlib import Path

from euro_chess_studio.data.db import get_connection, init_db

EXPECTED_TABLES = {
    "users",
    "pages",
    "workspaces",
    "moves",
    "dataset_rows",
    "job_configs",
    "artifacts",
    "eval_results",
    "presenter_state",
    "model_attempts",
    "scenario_assessments",
}


def test_init_db_creates_all_tables(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    try:
        init_db(conn)
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        table_names = {row["name"] for row in rows}
        assert EXPECTED_TABLES.issubset(table_names)
    finally:
        conn.close()


def test_init_db_is_idempotent(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    try:
        init_db(conn)
        init_db(conn)
    finally:
        conn.close()


def test_get_connection_enables_foreign_keys(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    try:
        (fk_enabled,) = conn.execute("PRAGMA foreign_keys").fetchone()
        assert fk_enabled == 1
    finally:
        conn.close()


def test_init_db_patches_presenter_state_created_before_targets(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    try:
        # A database from before phase 32: presenter_state without the
        # revision or target columns, holding live state.
        conn.execute(
            """
            CREATE TABLE presenter_state (
                id TEXT PRIMARY KEY,
                mode TEXT NOT NULL,
                locked INTEGER NOT NULL,
                active_page_slug TEXT,
                focused_user_id TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO presenter_state "
            "VALUES ('singleton', 'presenter', 1, 'presentation', NULL, 'then')"
        )
        conn.commit()

        init_db(conn)

        row = conn.execute("SELECT * FROM presenter_state").fetchone()
        assert row["mode"] == "presenter"
        assert row["revision"] == 0
        assert row["target_frame_id"] is None
        assert row["target_bounds_json"] is None
    finally:
        conn.close()
