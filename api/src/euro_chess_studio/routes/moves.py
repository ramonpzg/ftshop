import json
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from euro_chess_studio.actions.errors import GameClockExpiredError
from euro_chess_studio.actions.moves import WorkspaceNotFoundError, make_move
from euro_chess_studio.data.dataset_rows_repo import list_dataset_rows
from euro_chess_studio.data.moves_repo import list_moves
from euro_chess_studio.data.workspaces_repo import get_workspace
from euro_chess_studio.deps import get_db
from euro_chess_studio.routes.workspaces import WorkspaceOut

router = APIRouter(tags=["moves"])


class MoveRequest(BaseModel):
    uci: str


class MoveOut(BaseModel):
    id: str
    workspace_id: str
    game_id: str | None = None
    ply: int
    uci: str
    san: str | None
    fen_before: str
    fen_after: str
    is_legal: bool
    is_check: bool
    is_checkmate: bool
    reward: int
    created_at: str


class DatasetRowOut(BaseModel):
    id: str
    workspace_id: str
    move_id: str | None
    shape: str
    payload: dict[str, Any]
    created_at: str


def _dataset_row_out(row: sqlite3.Row) -> DatasetRowOut:
    data = dict(row)
    data["payload"] = json.loads(data.pop("payload_json"))
    return DatasetRowOut(**data)


class MoveResponse(BaseModel):
    move: MoveOut
    dataset_rows: list[DatasetRowOut]
    # Present when this move ended a timed game: "win", "loss", "draw".
    game_result: str | None = None


class WorkspaceStateOut(BaseModel):
    workspace: WorkspaceOut
    moves: list[MoveOut]
    dataset_rows: list[DatasetRowOut]


@router.post("/workspaces/{workspace_id}/moves")
def post_move(
    workspace_id: str, body: MoveRequest, conn: sqlite3.Connection = Depends(get_db)
) -> MoveResponse:
    try:
        result = make_move(conn, workspace_id, body.uci)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GameClockExpiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return MoveResponse(
        move=MoveOut(**dict(result.move)),
        dataset_rows=[_dataset_row_out(row) for row in result.dataset_rows],
        game_result=result.game_result,
    )


@router.get("/workspaces/{workspace_id}/state")
def get_workspace_state(
    workspace_id: str, conn: sqlite3.Connection = Depends(get_db)
) -> WorkspaceStateOut:
    workspace = get_workspace(conn, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail=f"unknown workspace id: {workspace_id}")
    return WorkspaceStateOut(
        workspace=WorkspaceOut(**dict(workspace)),
        moves=[MoveOut(**dict(row)) for row in list_moves(conn, workspace_id)],
        dataset_rows=[_dataset_row_out(row) for row in list_dataset_rows(conn, workspace_id)],
    )
