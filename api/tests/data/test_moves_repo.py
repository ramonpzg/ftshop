from pathlib import Path

import chess

from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.moves_repo import (
    count_legal_moves,
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
        conn, "workspace_1", user["id"], page["id"], "shape:1", 0, chess.STARTING_FEN
    )
    return conn, workspace


def test_insert_and_list_moves(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    insert_move(
        conn,
        workspace_id=workspace["id"],
        ply=0,
        uci="e2e4",
        san="e4",
        fen_before=chess.STARTING_FEN,
        fen_after="irrelevant",
        is_legal=True,
        is_check=False,
        is_checkmate=False,
        reward=1,
    )
    moves = list_moves(conn, workspace["id"])
    assert len(moves) == 1
    assert moves[0]["san"] == "e4"
    assert moves[0]["is_legal"] == 1


def test_count_legal_moves_ignores_illegal_attempts(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    insert_move(
        conn,
        workspace_id=workspace["id"],
        ply=0,
        uci="e2e5",
        san=None,
        fen_before=chess.STARTING_FEN,
        fen_after=chess.STARTING_FEN,
        is_legal=False,
        is_check=False,
        is_checkmate=False,
        reward=-1,
    )
    assert count_legal_moves(conn, workspace["id"]) == 0
    insert_move(
        conn,
        workspace_id=workspace["id"],
        ply=0,
        uci="e2e4",
        san="e4",
        fen_before=chess.STARTING_FEN,
        fen_after="irrelevant",
        is_legal=True,
        is_check=False,
        is_checkmate=False,
        reward=1,
    )
    assert count_legal_moves(conn, workspace["id"]) == 1


def test_list_legal_sans_excludes_illegal_attempts(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    insert_move(
        conn,
        workspace_id=workspace["id"],
        ply=0,
        uci="e2e4",
        san="e4",
        fen_before=chess.STARTING_FEN,
        fen_after="fen-1",
        is_legal=True,
        is_check=False,
        is_checkmate=False,
        reward=1,
    )
    insert_move(
        conn,
        workspace_id=workspace["id"],
        ply=1,
        uci="e7e6",
        san=None,
        fen_before="fen-1",
        fen_after="fen-1",
        is_legal=False,
        is_check=False,
        is_checkmate=False,
        reward=-1,
    )
    insert_move(
        conn,
        workspace_id=workspace["id"],
        ply=1,
        uci="e7e5",
        san="e5",
        fen_before="fen-1",
        fen_after="fen-2",
        is_legal=True,
        is_check=False,
        is_checkmate=False,
        reward=1,
    )
    assert list_legal_sans(conn, workspace["id"]) == ["e4", "e5"]
