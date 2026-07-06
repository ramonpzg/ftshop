import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from euro_chess_studio.actions.errors import (
    GameAlreadyActiveError,
    GameClockExpiredError,
    GameNotExpiredError,
    InvalidTimeLimitError,
    NoActiveGameError,
    WorkspaceNotFoundError,
)
from euro_chess_studio.actions.game import ModelReplyError, assess_position, model_move
from euro_chess_studio.actions.games import (
    GameStatus,
    flag_timeout,
    game_status,
    start_game,
    start_over,
)
from euro_chess_studio.calculations.game_clock import (
    DEFAULT_TIME_LIMIT_SECONDS,
    MAX_TIME_LIMIT_SECONDS,
    MIN_TIME_LIMIT_SECONDS,
    remaining_seconds,
)
from euro_chess_studio.data.llm_client import (
    LlmNotConfiguredError,
    LlmRequestError,
    get_llm_model,
    is_llm_configured,
)
from euro_chess_studio.deps import get_db
from euro_chess_studio.routes.moves import MoveOut, MoveResponse, _dataset_row_out

router = APIRouter(tags=["game"])


class GameOut(BaseModel):
    id: str
    workspace_id: str
    time_limit_seconds: int
    started_at: str
    ended_at: str | None
    result: str | None
    seconds_left: float


class GameRecordOut(BaseModel):
    wins: int
    losses: int
    draws: int


class GameStatusOut(BaseModel):
    game: GameOut | None
    record: GameRecordOut
    board_fen: str


class StartGameRequest(BaseModel):
    time_limit_seconds: int = Field(
        default=DEFAULT_TIME_LIMIT_SECONDS,
        ge=MIN_TIME_LIMIT_SECONDS,
        le=MAX_TIME_LIMIT_SECONDS,
    )


def _game_status_out(status: GameStatus) -> GameStatusOut:
    game = None
    if status.game is not None:
        game = GameOut(
            **dict(status.game),
            seconds_left=remaining_seconds(
                status.game["started_at"],
                status.game["time_limit_seconds"],
                datetime.now(UTC),
            ),
        )
    return GameStatusOut(
        game=game,
        record=GameRecordOut(**status.record),
        board_fen=status.workspace["board_fen"],
    )


@router.get("/workspaces/{workspace_id}/game")
def get_game_status(workspace_id: str, conn: sqlite3.Connection = Depends(get_db)) -> GameStatusOut:
    try:
        return _game_status_out(game_status(conn, workspace_id))
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/workspaces/{workspace_id}/game/start")
def post_start_game(
    workspace_id: str,
    body: StartGameRequest,
    conn: sqlite3.Connection = Depends(get_db),
) -> GameStatusOut:
    try:
        return _game_status_out(start_game(conn, workspace_id, body.time_limit_seconds))
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTimeLimitError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GameAlreadyActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/workspaces/{workspace_id}/game/start-over")
def post_start_over(workspace_id: str, conn: sqlite3.Connection = Depends(get_db)) -> GameStatusOut:
    try:
        return _game_status_out(start_over(conn, workspace_id))
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NoActiveGameError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/workspaces/{workspace_id}/game/timeout")
def post_flag_timeout(
    workspace_id: str, conn: sqlite3.Connection = Depends(get_db)
) -> GameStatusOut:
    try:
        return _game_status_out(flag_timeout(conn, workspace_id))
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (NoActiveGameError, GameNotExpiredError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


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
    except GameClockExpiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (WorkspaceNotFoundError, LlmNotConfiguredError, LlmRequestError, ModelReplyError) as exc:
        raise _map_llm_errors(exc) from exc
    return MoveResponse(
        move=MoveOut(**dict(result.move)),
        dataset_rows=[_dataset_row_out(row) for row in result.dataset_rows],
        game_result=result.game_result,
    )


@router.post("/workspaces/{workspace_id}/assess")
def post_assess(workspace_id: str, conn: sqlite3.Connection = Depends(get_db)) -> AssessmentOut:
    try:
        result = assess_position(conn, workspace_id)
    except (WorkspaceNotFoundError, LlmNotConfiguredError, LlmRequestError, ModelReplyError) as exc:
        raise _map_llm_errors(exc) from exc
    return AssessmentOut(**result)
