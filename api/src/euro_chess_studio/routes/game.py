import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from euro_chess_studio.actions.errors import WorkspaceNotFoundError
from euro_chess_studio.actions.game import ModelReplyError, assess_position, model_move
from euro_chess_studio.data.llm_client import (
    LlmNotConfiguredError,
    LlmRequestError,
    get_llm_model,
    is_llm_configured,
)
from euro_chess_studio.deps import get_db
from euro_chess_studio.routes.moves import MoveOut, MoveResponse, _dataset_row_out

router = APIRouter(tags=["game"])


class LlmStatusOut(BaseModel):
    configured: bool
    model: str


@router.get("/llm/status")
def llm_status() -> LlmStatusOut:
    return LlmStatusOut(configured=is_llm_configured(), model=get_llm_model())


class AssessmentOut(BaseModel):
    assessment: str
    real_world: str
    model: str


def _map_llm_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, WorkspaceNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, LlmNotConfiguredError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, (LlmRequestError, ModelReplyError)):
        return HTTPException(status_code=502, detail=str(exc))
    raise exc


@router.post("/workspaces/{workspace_id}/model-move")
def post_model_move(workspace_id: str, conn: sqlite3.Connection = Depends(get_db)) -> MoveResponse:
    try:
        result = model_move(conn, workspace_id)
    except (WorkspaceNotFoundError, LlmNotConfiguredError, LlmRequestError, ModelReplyError) as exc:
        raise _map_llm_errors(exc) from exc
    return MoveResponse(
        move=MoveOut(**dict(result.move)),
        dataset_rows=[_dataset_row_out(row) for row in result.dataset_rows],
    )


@router.post("/workspaces/{workspace_id}/assess")
def post_assess(workspace_id: str, conn: sqlite3.Connection = Depends(get_db)) -> AssessmentOut:
    try:
        result = assess_position(conn, workspace_id)
    except (WorkspaceNotFoundError, LlmNotConfiguredError, LlmRequestError, ModelReplyError) as exc:
        raise _map_llm_errors(exc) from exc
    return AssessmentOut(**result)
