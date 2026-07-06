from pathlib import Path

import chess

from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.pages_repo import upsert_page
from euro_chess_studio.data.users_repo import insert_user
from euro_chess_studio.data.workspaces_repo import (
    count_workspaces_for_page,
    get_workspace_for_user_and_page,
    insert_workspace,
    list_workspaces,
    list_workspaces_with_details,
    update_board_fen,
)


def make_conn(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    for page in PAGES:
        upsert_page(conn, page)
    return conn


def test_count_workspaces_for_page_starts_at_zero(tmp_path: Path):
    conn = make_conn(tmp_path)
    page = conn.execute("SELECT * FROM pages WHERE slug = 'chess-machine'").fetchone()
    assert count_workspaces_for_page(conn, page["id"]) == 0


def test_insert_workspace_and_lookup_by_user_and_page(tmp_path: Path):
    conn = make_conn(tmp_path)
    page = conn.execute("SELECT * FROM pages WHERE slug = 'chess-machine'").fetchone()
    user = insert_user(conn, "Ada")
    ws = insert_workspace(
        conn,
        workspace_id="workspace_1",
        user_id=user["id"],
        page_id=page["id"],
        shape_id="shape:workspace-1",
        board_fen=chess.STARTING_FEN,
    )
    assert ws["board_fen"] == chess.STARTING_FEN
    found = get_workspace_for_user_and_page(conn, user["id"], page["id"])
    assert found["id"] == ws["id"]


def test_position_index_is_allocated_inside_the_insert(tmp_path: Path):
    conn = make_conn(tmp_path)
    page = conn.execute("SELECT * FROM pages WHERE slug = 'chess-machine'").fetchone()
    positions = []
    for i, name in enumerate(["Ada", "Grace", "Edsger"]):
        user = insert_user(conn, name)
        ws = insert_workspace(
            conn,
            workspace_id=f"workspace_{i}",
            user_id=user["id"],
            page_id=page["id"],
            shape_id=f"shape:workspace-{i}",
            board_fen=chess.STARTING_FEN,
        )
        positions.append(ws["position_index"])
    assert positions == [0, 1, 2]
    assert count_workspaces_for_page(conn, page["id"]) == 3


def test_position_index_counts_per_page(tmp_path: Path):
    conn = make_conn(tmp_path)
    chess_machine = conn.execute("SELECT * FROM pages WHERE slug = 'chess-machine'").fetchone()
    painting = conn.execute("SELECT * FROM pages WHERE slug = 'painting-pieces'").fetchone()
    user = insert_user(conn, "Ada")
    ws_a = insert_workspace(
        conn, "workspace_a", user["id"], chess_machine["id"], "shape:a", chess.STARTING_FEN
    )
    ws_b = insert_workspace(
        conn, "workspace_b", user["id"], painting["id"], "shape:b", chess.STARTING_FEN
    )
    assert ws_a["position_index"] == 0
    assert ws_b["position_index"] == 0


def test_list_workspaces_filters_by_page(tmp_path: Path):
    conn = make_conn(tmp_path)
    chess_machine = conn.execute("SELECT * FROM pages WHERE slug = 'chess-machine'").fetchone()
    painting = conn.execute("SELECT * FROM pages WHERE slug = 'painting-pieces'").fetchone()
    user = insert_user(conn, "Ada")
    insert_workspace(
        conn, "workspace_a", user["id"], chess_machine["id"], "shape:a", chess.STARTING_FEN
    )
    insert_workspace(conn, "workspace_b", user["id"], painting["id"], "shape:b", chess.STARTING_FEN)
    assert len(list_workspaces(conn, chess_machine["id"])) == 1
    assert len(list_workspaces(conn)) == 2


def test_list_workspaces_with_details_includes_user_and_page_info(tmp_path: Path):
    conn = make_conn(tmp_path)
    page = conn.execute("SELECT * FROM pages WHERE slug = 'chess-machine'").fetchone()
    user = insert_user(conn, "Ada")
    insert_workspace(conn, "workspace_a", user["id"], page["id"], "shape:a", chess.STARTING_FEN)
    rows = list_workspaces_with_details(conn)
    assert rows[0]["user_name"] == "Ada"
    assert rows[0]["page_slug"] == "chess-machine"


def test_update_board_fen(tmp_path: Path):
    conn = make_conn(tmp_path)
    page = conn.execute("SELECT * FROM pages WHERE slug = 'chess-machine'").fetchone()
    user = insert_user(conn, "Ada")
    ws = insert_workspace(
        conn, "workspace_a", user["id"], page["id"], "shape:a", chess.STARTING_FEN
    )
    new_fen = "8/8/8/8/8/8/8/8 w - - 0 1"
    update_board_fen(conn, ws["id"], new_fen)
    reloaded = get_workspace_for_user_and_page(conn, user["id"], page["id"])
    assert reloaded["board_fen"] == new_fen
