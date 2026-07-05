"""Action: attempt a move in a workspace's chess game."""

import sqlite3
from dataclasses import dataclass

from euro_chess_studio.calculations.dataset import build_dataset_rows
from euro_chess_studio.calculations.reward import compute_reward
from euro_chess_studio.chess.board import apply_move, get_legal_moves
from euro_chess_studio.data.dataset_rows_repo import insert_dataset_row
from euro_chess_studio.data.moves_repo import count_legal_moves, insert_move, list_legal_sans
from euro_chess_studio.data.workspaces_repo import get_workspace, update_board_fen


class WorkspaceNotFoundError(ValueError):
    pass


@dataclass(frozen=True)
class MakeMoveResult:
    move: sqlite3.Row
    dataset_rows: list[sqlite3.Row]


def make_move(conn: sqlite3.Connection, workspace_id: str, uci: str) -> MakeMoveResult:
    workspace = get_workspace(conn, workspace_id)
    if workspace is None:
        raise WorkspaceNotFoundError(f"unknown workspace id: {workspace_id}")

    fen_before = workspace["board_fen"]
    legal_moves_before = get_legal_moves(fen_before)
    result = apply_move(fen_before, uci)
    reward = compute_reward(
        legal=result.legal, is_check=result.is_check, is_checkmate=result.is_checkmate
    )
    ply = count_legal_moves(conn, workspace_id)

    move_row = insert_move(
        conn,
        workspace_id=workspace_id,
        ply=ply,
        uci=result.uci,
        san=result.san,
        fen_before=result.fen_before,
        fen_after=result.fen_after,
        is_legal=result.legal,
        is_check=result.is_check,
        is_checkmate=result.is_checkmate,
        reward=reward,
    )

    dataset_row_records: list[sqlite3.Row] = []
    if result.legal:
        update_board_fen(conn, workspace_id, result.fen_after)
        prior_sans = list_legal_sans(conn, workspace_id)[:-1]
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

    return MakeMoveResult(move=move_row, dataset_rows=dataset_row_records)
