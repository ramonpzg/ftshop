"""Action: attempt a move in a workspace's chess game."""

import sqlite3
from dataclasses import dataclass

from euro_chess_studio.actions.errors import (
    GameClockExpiredError,
    NotYourTurnError,
    StaleMoveError,
    WorkspaceNotFoundError,
)
from euro_chess_studio.actions.games import expire_if_over
from euro_chess_studio.calculations.dataset import build_dataset_rows
from euro_chess_studio.calculations.reward import compute_reward
from euro_chess_studio.chess.board import apply_move, get_legal_moves
from euro_chess_studio.data.dataset_rows_repo import insert_dataset_row
from euro_chess_studio.data.games_repo import end_game, get_active_game
from euro_chess_studio.data.moves_repo import insert_move, list_legal_sans
from euro_chess_studio.data.workspaces_repo import get_workspace, update_board_fen


@dataclass(frozen=True)
class MakeMoveResult:
    move: sqlite3.Row
    dataset_rows: list[sqlite3.Row]
    # Set when this move ended a timed game: "win", "loss", or "draw".
    game_result: str | None = None


# In a timed match the participant always plays white and the
# configured model answers as black (actions/model_turn.py); there is
# no color picker. This is the one place that convention is enforced
# server-side, not just by the frontend disabling the board.
PARTICIPANT_COLOR = "w"


@dataclass(frozen=True)
class MovePrecondition:
    """An optimistic-concurrency guard for a decision made against a
    position at some earlier point (e.g. before a slow network call).
    make_move refuses to apply when the board has moved on, instead of
    silently applying a choice made against a position that no longer
    exists."""

    fen: str
    game_id: str | None
    ply: int


def make_move(
    conn: sqlite3.Connection,
    workspace_id: str,
    uci: str,
    actor: str = "participant",
    model: str | None = None,
    commit: bool = True,
    precondition: MovePrecondition | None = None,
) -> MakeMoveResult:
    """One attempted move: the move record, the board update, the dataset
    rows, and any game outcome commit together or not at all. Callers that
    compose a larger transaction (the model turn) pass commit=False and
    commit themselves.

    When `precondition` is given, the move is applied only if the
    workspace's board, active game, and ply still match it exactly.
    A mismatch raises StaleMoveError before anything is written: the
    caller decided this move against a position that has since changed
    (a concurrent move landed, a clock expired and a new game started,
    and so on), and applying it anyway would misattribute a decision
    made against stale information as a legitimate reply to the
    current position.
    """
    workspace = get_workspace(conn, workspace_id)
    if workspace is None:
        raise WorkspaceNotFoundError(f"unknown workspace id: {workspace_id}")

    # The server clock is the referee. A move that arrives after the
    # flag fell is not a move; the game is already a timeout loss.
    game = get_active_game(conn, workspace_id)
    if game is not None and expire_if_over(conn, game) is None:
        raise GameClockExpiredError("time ran out; that game is a loss")
    game_id = game["id"] if game is not None else None

    # The public move route has no other way to know whose turn it is;
    # without this check a raw API call could play both colors, silently
    # standing in for the model, bypassing its recorded attempts and its
    # unavailable/retry recovery state, and polluting the participant's
    # own legal-move-rate and the exported dataset with moves the model
    # was supposed to make. Free play (no active game) has no such
    # contract to violate and is unrestricted.
    if actor == "participant" and game_id is not None:
        active_color = workspace["board_fen"].split(" ")[1]
        if active_color != PARTICIPANT_COLOR:
            raise NotYourTurnError(
                "it is the model's turn; call /model-move instead of playing for it"
            )

    if precondition is not None:
        current_ply = len(list_legal_sans(conn, workspace_id, game_id))
        if (
            workspace["board_fen"] != precondition.fen
            or game_id != precondition.game_id
            or current_ply != precondition.ply
        ):
            raise StaleMoveError(
                "board changed since this move was decided: expected "
                f"fen={precondition.fen!r} game={precondition.game_id!r} "
                f"ply={precondition.ply}; found fen={workspace['board_fen']!r} "
                f"game={game_id!r} ply={current_ply}"
            )

    fen_before = workspace["board_fen"]
    legal_moves_before = get_legal_moves(fen_before)
    result = apply_move(fen_before, uci)
    reward = compute_reward(
        legal=result.legal, is_check=result.is_check, is_checkmate=result.is_checkmate
    )

    try:
        move_row = insert_move(
            conn,
            workspace_id=workspace_id,
            uci=result.uci,
            san=result.san,
            fen_before=result.fen_before,
            fen_after=result.fen_after,
            is_legal=result.legal,
            is_check=result.is_check,
            is_checkmate=result.is_checkmate,
            reward=reward,
            actor=actor,
            model=model,
            game_id=game_id,
        )

        dataset_row_records: list[sqlite3.Row] = []
        game_result: str | None = None
        if result.legal:
            update_board_fen(conn, workspace_id, result.fen_after)
            prior_sans = list_legal_sans(conn, workspace_id, game_id)[:-1]
            for row in build_dataset_rows(prior_sans, legal_moves_before, result):
                dataset_row_records.append(
                    insert_dataset_row(
                        conn,
                        workspace_id=workspace_id,
                        move_id=move_row["id"],
                        shape=row["shape"],
                        payload=row["payload"],
                    )
                )
            if game is not None:
                game_result = _finish_game_if_over(conn, game_id, result, actor)
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    return MakeMoveResult(move=move_row, dataset_rows=dataset_row_records, game_result=game_result)


def _finish_game_if_over(
    conn: sqlite3.Connection, game_id: str | None, result, actor: str
) -> str | None:
    """Checkmate by the participant wins the game, checkmate by the model
    (or its fallback) loses it, a stalemate draws it. Anything else
    plays on."""
    assert game_id is not None
    if result.is_checkmate:
        outcome = "loss" if actor in ("model", "fallback") else "win"
    elif not get_legal_moves(result.fen_after):
        outcome = "draw"
    else:
        return None
    end_game(conn, game_id, outcome)
    return outcome
