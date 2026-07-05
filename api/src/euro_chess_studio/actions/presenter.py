"""Actions that mutate presenter_state and, for reset, workspace game state."""

import sqlite3

import chess

from euro_chess_studio.actions.errors import PageNotFoundError
from euro_chess_studio.data.dataset_rows_repo import delete_dataset_rows_for_workspace
from euro_chess_studio.data.moves_repo import delete_moves_for_workspace
from euro_chess_studio.data.pages_repo import get_page_by_slug
from euro_chess_studio.data.presenter_state_repo import (
    get_or_create_presenter_state,
    update_presenter_state,
)
from euro_chess_studio.data.workspaces_repo import list_workspaces, update_board_fen


def get_presenter_state(conn: sqlite3.Connection) -> sqlite3.Row:
    return get_or_create_presenter_state(conn)


def bring_to_presenter_view(conn: sqlite3.Connection, page_slug: str) -> sqlite3.Row:
    if get_page_by_slug(conn, page_slug) is None:
        raise PageNotFoundError(f"unknown page slug: {page_slug}")
    return update_presenter_state(conn, mode="presenter", active_page_slug=page_slug)


def send_to_workspaces(conn: sqlite3.Connection) -> sqlite3.Row:
    return update_presenter_state(conn, mode="workspaces", active_page_slug=None)


def set_locked(conn: sqlite3.Connection, locked: bool) -> sqlite3.Row:
    return update_presenter_state(conn, locked=locked)


def reset_page(conn: sqlite3.Connection, page_slug: str) -> int:
    """Clears every workspace's game on a page: moves, dataset rows, and the
    board reset to the starting position. Returns the number of workspaces
    reset.
    """
    page = get_page_by_slug(conn, page_slug)
    if page is None:
        raise PageNotFoundError(f"unknown page slug: {page_slug}")

    workspaces = list_workspaces(conn, page["id"])
    for workspace in workspaces:
        # dataset_rows.move_id references moves(id), so it must go first.
        delete_dataset_rows_for_workspace(conn, workspace["id"])
        delete_moves_for_workspace(conn, workspace["id"])
        update_board_fen(conn, workspace["id"], chess.STARTING_FEN)
    return len(workspaces)
