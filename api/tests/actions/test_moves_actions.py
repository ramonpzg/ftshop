import json
from pathlib import Path

import chess
import pytest

from euro_chess_studio.actions.moves import WorkspaceNotFoundError, make_move
from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.pages_repo import upsert_page
from euro_chess_studio.data.users_repo import insert_user
from euro_chess_studio.data.workspaces_repo import get_workspace, insert_workspace


def make_workspace(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    for page in PAGES:
        upsert_page(conn, page)
    page = conn.execute("SELECT * FROM pages WHERE slug = 'chess-machine'").fetchone()
    user = insert_user(conn, "Ada")
    workspace = insert_workspace(
        conn, "workspace_1", user["id"], page["id"], "shape:1", 0, chess.STARTING_FEN
    )
    return conn, workspace


def test_make_move_updates_the_board_on_a_legal_move(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    result = make_move(conn, workspace["id"], "e2e4")
    assert result.move["is_legal"] == 1
    assert len(result.dataset_rows) == 6
    reloaded = get_workspace(conn, workspace["id"])
    assert reloaded["board_fen"] != chess.STARTING_FEN


def test_make_move_rejects_an_illegal_move_without_changing_the_board(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    result = make_move(conn, workspace["id"], "e2e5")
    assert result.move["is_legal"] == 0
    assert result.dataset_rows == []
    reloaded = get_workspace(conn, workspace["id"])
    assert reloaded["board_fen"] == chess.STARTING_FEN


def test_make_move_raises_for_unknown_workspace(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    with pytest.raises(WorkspaceNotFoundError):
        make_move(conn, "workspace_does_not_exist", "e2e4")


def test_make_move_pgn_prefix_grows_across_a_sequence(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    make_move(conn, workspace["id"], "e2e4")
    result = make_move(conn, workspace["id"], "e7e5")
    dataset_by_shape = {row["shape"]: row for row in result.dataset_rows}
    payload = json.loads(dataset_by_shape["pgn_prefix_to_move"]["payload_json"])
    assert payload["prefix"] == "1. e4"
    assert payload["target_san"] == "e5"
