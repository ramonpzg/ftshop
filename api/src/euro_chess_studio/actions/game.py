"""Actions for the model opponent and the live game analysis."""

import sqlite3

from euro_chess_studio.actions.errors import WorkspaceNotFoundError
from euro_chess_studio.actions.moves import MakeMoveResult, make_move
from euro_chess_studio.calculations.llm_prompts import (
    build_assess_messages,
    build_move_messages,
    parse_assess_reply,
    parse_move_reply,
)
from euro_chess_studio.chess.board import get_legal_moves
from euro_chess_studio.data import llm_client
from euro_chess_studio.data.moves_repo import list_legal_sans
from euro_chess_studio.data.workspaces_repo import get_workspace


class ModelReplyError(RuntimeError):
    """The model answered, but not with anything usable."""


def model_move(conn: sqlite3.Connection, workspace_id: str) -> MakeMoveResult:
    """Asks the configured model for a move and records it exactly like a
    human move. An illegal choice is recorded too (reward -1) without
    advancing the board: the environment catching the model is part of
    the lesson."""
    workspace = get_workspace(conn, workspace_id)
    if workspace is None:
        raise WorkspaceNotFoundError(f"unknown workspace id: {workspace_id}")

    fen = workspace["board_fen"]
    legal_moves = get_legal_moves(fen)
    if not legal_moves:
        raise ModelReplyError("no legal moves in this position; the game is over")

    reply = llm_client.chat(build_move_messages(fen, legal_moves), json_response=True)
    uci = parse_move_reply(reply)
    if uci is None:
        raise ModelReplyError(f"model reply had no usable move: {reply[:200]}")

    return make_move(conn, workspace_id, uci)


def assess_position(conn: sqlite3.Connection, workspace_id: str) -> dict:
    """One terse position assessment plus the real-world scenario mapping
    the session plan is built around."""
    workspace = get_workspace(conn, workspace_id)
    if workspace is None:
        raise WorkspaceNotFoundError(f"unknown workspace id: {workspace_id}")

    sans = list_legal_sans(conn, workspace_id)
    reply = llm_client.chat(build_assess_messages(sans, workspace["board_fen"]), json_response=True)
    parsed = parse_assess_reply(reply)
    if parsed is None:
        raise ModelReplyError(f"model reply had no usable assessment: {reply[:200]}")
    return {**parsed, "model": llm_client.get_llm_model()}
