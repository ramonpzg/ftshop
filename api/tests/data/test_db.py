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
