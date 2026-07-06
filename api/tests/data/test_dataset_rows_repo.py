from pathlib import Path

import chess

from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.dataset_rows_repo import (
    delete_dataset_rows_for_workspace,
    insert_dataset_row,
    list_dataset_rows,
)
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.pages_repo import upsert_page
from euro_chess_studio.data.users_repo import insert_user
from euro_chess_studio.data.workspaces_repo import insert_workspace


def make_workspace(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    for page in PAGES:
        upsert_page(conn, page)
    page = conn.execute("SELECT * FROM pages WHERE slug = 'chess-machine'").fetchone()
    user = insert_user(conn, "Ada")
    workspace = insert_workspace(
        conn, "workspace_1", user["id"], page["id"], "shape:1", chess.STARTING_FEN
    )
    return conn, workspace


def test_insert_dataset_row_round_trips_payload_as_json(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    row = insert_dataset_row(
        conn,
        workspace_id=workspace["id"],
        move_id=None,
        shape="fen_to_move",
        payload={"fen": chess.STARTING_FEN, "target_uci": "e2e4"},
    )
    assert row["shape"] == "fen_to_move"
    assert '"fen"' in row["payload_json"]


def test_list_dataset_rows_returns_rows_in_creation_order(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    insert_dataset_row(
        conn, workspace_id=workspace["id"], move_id=None, shape="a", payload={"n": 1}
    )
    insert_dataset_row(
        conn, workspace_id=workspace["id"], move_id=None, shape="b", payload={"n": 2}
    )
    rows = list_dataset_rows(conn, workspace["id"])
    assert [row["shape"] for row in rows] == ["a", "b"]


def test_delete_dataset_rows_for_workspace(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    insert_dataset_row(
        conn, workspace_id=workspace["id"], move_id=None, shape="a", payload={"n": 1}
    )
    delete_dataset_rows_for_workspace(conn, workspace["id"])
    assert list_dataset_rows(conn, workspace["id"]) == []
