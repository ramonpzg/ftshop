import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from euro_chess_studio.actions.errors import (
    GameAlreadyActiveError,
    GameClockExpiredError,
    GameNotExpiredError,
    InvalidOpponentModelError,
    InvalidTimeLimitError,
    ModelReplyError,
    NoActiveGameError,
    NotYourTurnError,
    ScenarioNotFoundError,
    ScenarioReviewError,
    WorkspaceNotFoundError,
    turn_conflict_detail,
)
from euro_chess_studio.actions.games import (
    GameStatus,
    flag_timeout,
    game_status,
    start_game,
    start_over,
)
from euro_chess_studio.actions.model_turn import ModelTurnError, ModelTurnResult, model_turn
from euro_chess_studio.actions.scenario import (
    latest_scenario_for_workspace,
    review_scenario,
    suggest_scenario,
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
    get_opponent_models,
    is_llm_configured,
    is_room_model_play_open,
)
from euro_chess_studio.deps import get_db
from euro_chess_studio.routes.client_host import require_presenter_machine
from euro_chess_studio.routes.moves import DatasetRowOut, MoveOut, _dataset_row_out

router = APIRouter(tags=["game"])


class GameOut(BaseModel):
    id: str
    workspace_id: str
    time_limit_seconds: int
    opponent_model: str | None
    started_at: str
    ended_at: str | None
    result: str | None
    seconds_left: float


class GameRecordOut(BaseModel):
    wins: int
    losses: int
    draws: int


class FinishedGameOut(BaseModel):
    id: str
    result: str
    time_limit_seconds: int
    ended_at: str
    legal_moves: int


class GameStatusOut(BaseModel):
    game: GameOut | None
    record: GameRecordOut
    board_fen: str
    # Newest first: the match log for "how did today go".
    history: list[FinishedGameOut]
    # True when this response is the first news of a timeout that
    # happened while the player was away (reload, server restart).
    expired_while_away: bool


class StartGameRequest(BaseModel):
    time_limit_seconds: int = Field(
        default=DEFAULT_TIME_LIMIT_SECONDS,
        ge=MIN_TIME_LIMIT_SECONDS,
        le=MAX_TIME_LIMIT_SECONDS,
    )
    opponent_model: str | None = None


def _room_model_play_closed_detail(activity: str) -> str:
    """The teaching refusal for a closed room: names both gates and the
    workflow that opens them, so the operator reading the 403 knows
    exactly what to run and set."""
    return (
        f"{activity} while room model play is closed (opening it to "
        "attendees takes a known-local endpoint, loopback "
        "OPENAI_BASE_URL or OPPONENT_ENDPOINT_IS_LOCAL=1, plus "
        "ROOM_MODEL_PLAY=1 set after the room-scale load test against "
        "the real endpoint)"
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
        history=[FinishedGameOut(**dict(row)) for row in status.history],
        expired_while_away=status.expired_while_away,
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
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
) -> GameStatusOut:
    # The room model policy, fail closed. Picking any non-default model
    # -- the frontier beat -- is a presenter move, because forty
    # attendees on a metered model is a budget burst and forty on a
    # second local model is a second way to sink the presenter's GPU.
    # The default itself is only open to the room when both gates hold:
    # the endpoint is known local (loopback OPENAI_BASE_URL or
    # OPPONENT_ENDPOINT_IS_LOCAL=1; protects the budget) and the
    # operator set ROOM_MODEL_PLAY=1 after the room-scale load test
    # (protects capacity: forty simultaneous requests queue behind one
    # llama.cpp server and exhaust the model-turn deadlines whether or
    # not the endpoint is free). Without both, attendees free-play and
    # model inference stays presenter-led.
    if body.opponent_model is not None and body.opponent_model != get_llm_model():
        require_presenter_machine(request, "starting a game against a non-default model")
    elif not is_room_model_play_open():
        require_presenter_machine(request, _room_model_play_closed_detail("a timed model game"))
    try:
        return _game_status_out(
            start_game(conn, workspace_id, body.time_limit_seconds, body.opponent_model)
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (InvalidTimeLimitError, InvalidOpponentModelError) as exc:
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
    opponent_models: list[str]
    # Whether attendee model play is open (local endpoint plus the
    # operator's post-load-test ROOM_MODEL_PLAY=1). Attendee clients
    # use this to offer free play instead of a Start button whose
    # every click would 403.
    room_model_play: bool


@router.get("/llm/status")
def llm_status() -> LlmStatusOut:
    return LlmStatusOut(
        configured=is_llm_configured(),
        model=get_llm_model(),
        opponent_models=get_opponent_models(),
        room_model_play=is_room_model_play_open(),
    )


class AttemptOut(BaseModel):
    """One recorded model attempt, bounded for the client."""

    attempt_number: int
    actor: str
    status: str
    parsed_move: str | None
    is_legal: bool | None
    model: str | None
    error_detail: str | None


def _attempt_out(row: sqlite3.Row) -> AttemptOut:
    return AttemptOut(
        attempt_number=row["attempt_number"],
        actor=row["actor"],
        status=row["status"],
        parsed_move=row["parsed_move"],
        is_legal=None if row["is_legal"] is None else bool(row["is_legal"]),
        model=row["model"],
        error_detail=row["error_detail"],
    )


class ModelTurnOut(BaseModel):
    # "model_move", "fallback_move", "unavailable", or "stale". Only
    # "model_move" and "fallback_move" leave a move on the board;
    # "unavailable" and "stale" leave it unchanged, and detail says why.
    outcome: str
    move: MoveOut | None
    dataset_rows: list[DatasetRowOut]
    game_result: str | None
    attempts: list[AttemptOut]
    detail: str | None


def _model_turn_out(result: ModelTurnResult) -> ModelTurnOut:
    move_result = result.move_result
    return ModelTurnOut(
        outcome=result.outcome,
        move=MoveOut(**dict(move_result.move)) if move_result else None,
        dataset_rows=[_dataset_row_out(row) for row in move_result.dataset_rows]
        if move_result
        else [],
        game_result=move_result.game_result if move_result else None,
        attempts=[_attempt_out(row) for row in result.attempts],
        detail=result.detail,
    )


class ScenarioOut(BaseModel):
    id: str
    workspace_id: str
    game_id: str | None
    ply: int
    status: str
    # The effective text a client shows: participant-approved when
    # reviewed, the raw suggestion otherwise.
    assessment: str | None
    real_world: str | None
    video_prompt: str | None
    suggested_assessment: str | None
    suggested_real_world: str | None
    suggested_video_prompt: str | None
    model: str | None
    provider_alias: str | None
    prompt_version: str | None
    # Set when status is 'failed': why the last attempt for this
    # workspace didn't produce a usable scenario. Lets a client show the
    # same recoverable error state on reload that a live failure shows,
    # instead of the failure silently reverting to the empty state.
    error_detail: str | None
    created_at: str


class ScenarioReloadOut(BaseModel):
    """Reload needs both rows to reproduce what a live failure already
    shows on screen: the previous mapping stays visible while the new
    failure is surfaced alongside it. `latest` is the true most recent
    row -- possibly a failure -- so the failure is never hidden.
    `latest_success` is the most recent row that actually produced a
    usable mapping, for restoring what should stay on screen under it;
    None when nothing has ever succeeded for this workspace."""

    latest: ScenarioOut | None
    latest_success: ScenarioOut | None


def _scenario_out(row: sqlite3.Row) -> ScenarioOut:
    reviewed = row["status"] in ("accepted", "edited")
    return ScenarioOut(
        id=row["id"],
        workspace_id=row["workspace_id"],
        game_id=row["game_id"],
        ply=row["ply"],
        status=row["status"],
        assessment=row["final_assessment"] if reviewed else row["suggested_assessment"],
        real_world=row["final_real_world"] if reviewed else row["suggested_real_world"],
        video_prompt=row["final_video_prompt"] if reviewed else row["suggested_video_prompt"],
        suggested_assessment=row["suggested_assessment"],
        suggested_real_world=row["suggested_real_world"],
        suggested_video_prompt=row["suggested_video_prompt"],
        model=row["model"],
        provider_alias=row["provider_alias"],
        prompt_version=row["prompt_version"],
        error_detail=row["error_detail"],
        created_at=row["created_at"],
    )


def _map_llm_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, WorkspaceNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, LlmNotConfiguredError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, (LlmRequestError, ModelReplyError, ModelTurnError)):
        return HTTPException(status_code=502, detail=str(exc))
    raise exc


@router.post("/workspaces/{workspace_id}/model-move")
def post_model_move(
    workspace_id: str, request: Request, conn: sqlite3.Connection = Depends(get_db)
) -> ModelTurnOut:
    # The same two gates as starting a timed model game: a model turn
    # is one inference request, model_turn works on free-play boards
    # too (no active game required), and forty attendees triggering
    # replies saturate a local server exactly as well as forty timed
    # games do. The UI never requests replies outside a game, but the
    # policy cannot live in the UI.
    if not is_room_model_play_open():
        require_presenter_machine(request, _room_model_play_closed_detail("a model reply"))
    try:
        result = model_turn(conn, workspace_id)
    except (GameClockExpiredError, NotYourTurnError) as exc:
        raise HTTPException(status_code=409, detail=turn_conflict_detail(exc)) from exc
    except (WorkspaceNotFoundError, LlmNotConfiguredError, ModelTurnError) as exc:
        raise _map_llm_errors(exc) from exc
    return _model_turn_out(result)


@router.post("/workspaces/{workspace_id}/assess")
def post_assess(
    workspace_id: str, request: Request, conn: sqlite3.Connection = Depends(get_db)
) -> ScenarioOut:
    # Room model policy: every assessment is a scenario-model call, and
    # it used to fire automatically after each model turn -- forty
    # attendees times one call per exchange. Generation is manual now
    # (the frontend has no auto-trigger) and presenter-machine only;
    # reviewing a landed mapping stays open to the room.
    require_presenter_machine(request, "position assessment (a scenario-model call)")
    try:
        row = suggest_scenario(conn, workspace_id)
    except (WorkspaceNotFoundError, LlmNotConfiguredError, LlmRequestError, ModelReplyError) as exc:
        raise _map_llm_errors(exc) from exc
    return _scenario_out(row)


@router.get("/workspaces/{workspace_id}/scenario")
def get_scenario(
    workspace_id: str, conn: sqlite3.Connection = Depends(get_db)
) -> ScenarioReloadOut:
    try:
        state = latest_scenario_for_workspace(conn, workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ScenarioReloadOut(
        latest=_scenario_out(state.latest) if state.latest is not None else None,
        latest_success=(
            _scenario_out(state.latest_success) if state.latest_success is not None else None
        ),
    )


class ScenarioReviewRequest(BaseModel):
    accept: bool = False
    assessment: str | None = None
    real_world: str | None = None
    video_prompt: str | None = None


@router.post("/scenarios/{scenario_id}/review")
def post_scenario_review(
    scenario_id: str,
    body: ScenarioReviewRequest,
    conn: sqlite3.Connection = Depends(get_db),
) -> ScenarioOut:
    try:
        row = review_scenario(
            conn,
            scenario_id,
            accept=body.accept,
            assessment=body.assessment,
            real_world=body.real_world,
            video_prompt=body.video_prompt,
        )
    except ScenarioNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ScenarioReviewError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _scenario_out(row)
