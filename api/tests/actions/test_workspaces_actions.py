from pathlib import Path

import pytest

from euro_chess_studio.actions.workspaces import (
    PageNotFoundError,
    create_or_get_workspace,
    join_workshop,
)
from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.pages_repo import upsert_page


def make_conn(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    for page in PAGES:
        upsert_page(conn, page)
    return conn


def test_join_workshop_creates_a_user(tmp_path: Path):
    conn = make_conn(tmp_path)
    user = join_workshop(conn, "Ada")
    assert user["name"] == "Ada"


def test_join_workshop_rejects_blank_name(tmp_path: Path):
    conn = make_conn(tmp_path)
    with pytest.raises(ValueError):
        join_workshop(conn, "   ")


def test_create_or_get_workspace_creates_new_workspace(tmp_path: Path):
    conn = make_conn(tmp_path)
    user = join_workshop(conn, "Ada")
    ws = create_or_get_workspace(conn, user["id"], "chess-machine")
    assert ws["user_id"] == user["id"]
    assert ws["position_index"] == 0
    assert ws["shape_id"] == f"shape:workspace-{user['id']}-chess-machine"


def test_create_or_get_workspace_is_idempotent(tmp_path: Path):
    conn = make_conn(tmp_path)
    user = join_workshop(conn, "Ada")
    first = create_or_get_workspace(conn, user["id"], "chess-machine")
    second = create_or_get_workspace(conn, user["id"], "chess-machine")
    assert first["id"] == second["id"]


def test_create_or_get_workspace_assigns_increasing_positions(tmp_path: Path):
    conn = make_conn(tmp_path)
    ada = join_workshop(conn, "Ada")
    grace = join_workshop(conn, "Grace")
    ws_ada = create_or_get_workspace(conn, ada["id"], "chess-machine")
    ws_grace = create_or_get_workspace(conn, grace["id"], "chess-machine")
    assert ws_ada["position_index"] == 0
    assert ws_grace["position_index"] == 1


def test_create_or_get_workspace_rejects_unknown_page(tmp_path: Path):
    conn = make_conn(tmp_path)
    user = join_workshop(conn, "Ada")
    with pytest.raises(PageNotFoundError):
        create_or_get_workspace(conn, user["id"], "not-a-page")
