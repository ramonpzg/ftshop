from pathlib import Path

import chess

from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.eval_results_repo import insert_eval_result, list_eval_results
from euro_chess_studio.data.pages_repo import upsert_page
from euro_chess_studio.data.users_repo import insert_user
from euro_chess_studio.data.workspaces_repo import insert_workspace


def make_conn(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    return conn


def test_insert_and_list_eval_results(tmp_path: Path):
    conn = make_conn(tmp_path)
    insert_eval_result(
        conn,
        modality="text",
        metric="legal_move_rate",
        value=1.0,
        workspace_id=None,
        source="computed",
    )
    rows = list_eval_results(conn)
    assert len(rows) == 1
    assert rows[0]["metric"] == "legal_move_rate"
    assert rows[0]["value"] == 1.0


def test_list_eval_results_filters_by_modality_and_workspace(tmp_path: Path):
    conn = make_conn(tmp_path)
    for page in PAGES:
        upsert_page(conn, page)
    page = conn.execute("SELECT * FROM pages WHERE slug = 'chess-machine'").fetchone()
    ada = insert_user(conn, "Ada")
    grace = insert_user(conn, "Grace")
    workspace_1 = insert_workspace(
        conn, "workspace_1", ada["id"], page["id"], "shape:1", 0, chess.STARTING_FEN
    )
    workspace_2 = insert_workspace(
        conn, "workspace_2", grace["id"], page["id"], "shape:2", 1, chess.STARTING_FEN
    )

    insert_eval_result(
        conn,
        modality="text",
        metric="a",
        value=1.0,
        workspace_id=workspace_1["id"],
        source="computed",
    )
    insert_eval_result(
        conn,
        modality="image",
        metric="b",
        value=2.0,
        workspace_id=workspace_2["id"],
        source="cached",
    )
    assert len(list_eval_results(conn, modality="text")) == 1
    assert len(list_eval_results(conn, workspace_id=workspace_2["id"])) == 1
    assert len(list_eval_results(conn)) == 2
