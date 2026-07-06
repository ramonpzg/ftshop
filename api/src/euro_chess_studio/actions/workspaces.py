"""Actions that mutate state: joining the workshop and creating workspaces."""

import sqlite3

import chess

from euro_chess_studio.actions.errors import (
    InvalidSnippetError,
    PageNotFoundError,
    UserNotFoundError,
    WorkspaceNotFoundError,
)
from euro_chess_studio.calculations.ids import generate_id, workspace_shape_id
from euro_chess_studio.calculations.snippets import VALID_SNIPPET_IDS
from euro_chess_studio.data.pages_repo import get_page_by_slug
from euro_chess_studio.data.users_repo import get_user, insert_user
from euro_chess_studio.data.workspaces_repo import (
    get_workspace,
    get_workspace_for_user_and_page,
    insert_workspace,
    update_selected_snippet,
)


def join_workshop(conn: sqlite3.Connection, name: str) -> sqlite3.Row:
    if not name.strip():
        raise ValueError("name must not be empty")
    return insert_user(conn, name.strip())


def create_or_get_workspace(conn: sqlite3.Connection, user_id: str, page_slug: str) -> sqlite3.Row:
    page = get_page_by_slug(conn, page_slug)
    if page is None:
        raise PageNotFoundError(f"unknown page slug: {page_slug}")
    # A stale user id (browser remembers a user the database no longer
    # has, e.g. after just reset-db) must be a clean 404 the client can
    # recover from, not a foreign-key 500.
    if get_user(conn, user_id) is None:
        raise UserNotFoundError(f"unknown user id: {user_id}")

    existing = get_workspace_for_user_and_page(conn, user_id, page["id"])
    if existing is not None:
        return existing

    shape_id = workspace_shape_id(user_id, page_slug)
    workspace_id = generate_id("workspace")
    try:
        return insert_workspace(
            conn,
            workspace_id=workspace_id,
            user_id=user_id,
            page_id=page["id"],
            shape_id=shape_id,
            board_fen=chess.STARTING_FEN,
        )
    except sqlite3.IntegrityError:
        # Two requests from the same user raced past the existence check;
        # the UNIQUE(user_id, page_id) constraint let exactly one win.
        existing = get_workspace_for_user_and_page(conn, user_id, page["id"])
        assert existing is not None
        return existing


def select_snippet(conn: sqlite3.Connection, workspace_id: str, snippet_id: str) -> sqlite3.Row:
    if get_workspace(conn, workspace_id) is None:
        raise WorkspaceNotFoundError(f"unknown workspace id: {workspace_id}")
    if snippet_id not in VALID_SNIPPET_IDS:
        raise InvalidSnippetError(f"unknown snippet id: {snippet_id}")
    update_selected_snippet(conn, workspace_id, snippet_id)
    row = get_workspace(conn, workspace_id)
    assert row is not None
    return row
