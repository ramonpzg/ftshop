from pathlib import Path

import chess
import pytest

from euro_chess_studio.actions.errors import PageNotFoundError
from euro_chess_studio.actions.moves import make_move
from euro_chess_studio.actions.presenter import (
    bring_to_presenter_view,
    get_presenter_state,
    reset_page,
    send_to_workspaces,
    set_locked,
)
from euro_chess_studio.actions.workspaces import create_or_get_workspace, join_workshop
from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.moves_repo import list_moves
from euro_chess_studio.data.pages_repo import upsert_page
from euro_chess_studio.data.workspaces_repo import get_workspace


def make_conn(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    for page in PAGES:
        upsert_page(conn, page)
    return conn


def test_get_presenter_state_defaults_to_idle(tmp_path: Path):
    conn = make_conn(tmp_path)
    assert get_presenter_state(conn)["mode"] == "idle"


def test_bring_to_presenter_view_sets_mode_and_page(tmp_path: Path):
    conn = make_conn(tmp_path)
    state = bring_to_presenter_view(conn, "presentation")
    assert state["mode"] == "presenter"
    assert state["active_page_slug"] == "presentation"


def test_bring_to_presenter_view_rejects_unknown_page(tmp_path: Path):
    conn = make_conn(tmp_path)
    with pytest.raises(PageNotFoundError):
        bring_to_presenter_view(conn, "not-a-page")


def test_send_to_workspaces_clears_active_page(tmp_path: Path):
    conn = make_conn(tmp_path)
    bring_to_presenter_view(conn, "presentation")
    state = send_to_workspaces(conn)
    assert state["mode"] == "workspaces"
    assert state["active_page_slug"] is None


def test_set_locked_toggles_the_flag(tmp_path: Path):
    conn = make_conn(tmp_path)
    assert set_locked(conn, True)["locked"] == 1
    assert set_locked(conn, False)["locked"] == 0


def test_reset_page_clears_moves_and_resets_board(tmp_path: Path):
    conn = make_conn(tmp_path)
    user = join_workshop(conn, "Ada")
    workspace = create_or_get_workspace(conn, user["id"], "chess-machine")
    make_move(conn, workspace["id"], "e2e4")

    count = reset_page(conn, "chess-machine")

    assert count == 1
    assert list_moves(conn, workspace["id"]) == []
    reloaded = get_workspace(conn, workspace["id"])
    assert reloaded["board_fen"] == chess.STARTING_FEN


def test_reset_page_rejects_unknown_page(tmp_path: Path):
    conn = make_conn(tmp_path)
    with pytest.raises(PageNotFoundError):
        reset_page(conn, "not-a-page")


def test_reset_page_with_no_workspaces_resets_nothing(tmp_path: Path):
    conn = make_conn(tmp_path)
    assert reset_page(conn, "chess-machine") == 0
