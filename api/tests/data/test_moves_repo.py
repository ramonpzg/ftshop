from pathlib import Path

import chess

from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.moves_repo import (
    count_legal_moves,
    delete_moves_for_workspace,
    insert_move,
    list_legal_sans,
    list_moves,
)
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


def record_move(conn, workspace_id: str, *, uci: str, san: str | None, legal: bool, reward: int):
    return insert_move(
        conn,
        workspace_id=workspace_id,
        uci=uci,
        san=san,
        fen_before=chess.STARTING_FEN,
        fen_after="irrelevant",
        is_legal=legal,
        is_check=False,
        is_checkmate=False,
        reward=reward,
    )


def test_insert_and_list_moves(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    record_move(conn, workspace["id"], uci="e2e4", san="e4", legal=True, reward=1)
    moves = list_moves(conn, workspace["id"])
    assert len(moves) == 1
    assert moves[0]["san"] == "e4"
    assert moves[0]["is_legal"] == 1


def test_ply_is_allocated_from_legal_move_count(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    first = record_move(conn, workspace["id"], uci="e2e4", san="e4", legal=True, reward=1)
    illegal = record_move(conn, workspace["id"], uci="e7e6", san=None, legal=False, reward=-1)
    second = record_move(conn, workspace["id"], uci="e7e5", san="e5", legal=True, reward=1)
    assert first["ply"] == 0
    # An illegal attempt does not consume a ply; it happens "at" the next one.
    assert illegal["ply"] == 1
    assert second["ply"] == 1


def test_count_legal_moves_ignores_illegal_attempts(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    record_move(conn, workspace["id"], uci="e2e5", san=None, legal=False, reward=-1)
    assert count_legal_moves(conn, workspace["id"]) == 0
    record_move(conn, workspace["id"], uci="e2e4", san="e4", legal=True, reward=1)
    assert count_legal_moves(conn, workspace["id"]) == 1


def test_list_legal_sans_excludes_illegal_attempts(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    record_move(conn, workspace["id"], uci="e2e4", san="e4", legal=True, reward=1)
    record_move(conn, workspace["id"], uci="e7e6", san=None, legal=False, reward=-1)
    record_move(conn, workspace["id"], uci="e7e5", san="e5", legal=True, reward=1)
    assert list_legal_sans(conn, workspace["id"]) == ["e4", "e5"]


def test_delete_moves_for_workspace(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    record_move(conn, workspace["id"], uci="e2e4", san="e4", legal=True, reward=1)
    delete_moves_for_workspace(conn, workspace["id"])
    assert list_moves(conn, workspace["id"]) == []
