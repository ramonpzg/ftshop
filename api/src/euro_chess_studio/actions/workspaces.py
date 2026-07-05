"""Actions that mutate state: joining the workshop and creating workspaces."""

import sqlite3

import chess

from euro_chess_studio.actions.errors import (
    InvalidSnippetError,
    PageNotFoundError,
    WorkspaceNotFoundError,
)
from euro_chess_studio.calculations.ids import generate_id, workspace_shape_id
from euro_chess_studio.calculations.snippets import VALID_SNIPPET_IDS
from euro_chess_studio.data.pages_repo import get_page_by_slug
from euro_chess_studio.data.users_repo import insert_user
from euro_chess_studio.data.workspaces_repo import (
    count_workspaces_for_page,
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

    existing = get_workspace_for_user_and_page(conn, user_id, page["id"])
    if existing is not None:
        return existing

    position_index = count_workspaces_for_page(conn, page["id"])
    shape_id = workspace_shape_id(user_id, page_slug)
    workspace_id = generate_id("workspace")
    return insert_workspace(
        conn,
        workspace_id=workspace_id,
        user_id=user_id,
        page_id=page["id"],
        shape_id=shape_id,
        position_index=position_index,
        board_fen=chess.STARTING_FEN,
    )


def select_snippet(conn: sqlite3.Connection, workspace_id: str, snippet_id: str) -> sqlite3.Row:
    if get_workspace(conn, workspace_id) is None:
        raise WorkspaceNotFoundError(f"unknown workspace id: {workspace_id}")
    if snippet_id not in VALID_SNIPPET_IDS:
        raise InvalidSnippetError(f"unknown snippet id: {snippet_id}")
    update_selected_snippet(conn, workspace_id, snippet_id)
    row = get_workspace(conn, workspace_id)
    assert row is not None
    return row
