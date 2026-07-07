import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from euro_chess_studio.actions.errors import PageNotFoundError
from euro_chess_studio.actions.games import room_games
from euro_chess_studio.actions.presenter import (
    bring_to_presenter_view,
    get_presenter_state,
    reset_page,
    send_to_workspaces,
    set_locked,
)
from euro_chess_studio.calculations.game_clock import remaining_seconds
from euro_chess_studio.deps import get_db

router = APIRouter(prefix="/presenter", tags=["presenter"])


class PresenterStateOut(BaseModel):
    mode: str
    locked: bool
    active_page_slug: str | None
    focused_user_id: str | None
    updated_at: str


class PageSlugRequest(BaseModel):
    page_slug: str


class ResetPageResponse(BaseModel):
    workspaces_reset: int


@router.get("")
def get_state(conn: sqlite3.Connection = Depends(get_db)) -> PresenterStateOut:
    return PresenterStateOut(**dict(get_presenter_state(conn)))


@router.post("/bring-to-presenter-view")
def post_bring_to_presenter_view(
    body: PageSlugRequest, conn: sqlite3.Connection = Depends(get_db)
) -> PresenterStateOut:
    try:
        row = bring_to_presenter_view(conn, body.page_slug)
    except PageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PresenterStateOut(**dict(row))


@router.post("/send-to-workspaces")
def post_send_to_workspaces(conn: sqlite3.Connection = Depends(get_db)) -> PresenterStateOut:
    return PresenterStateOut(**dict(send_to_workspaces(conn)))


@router.post("/lock")
def post_lock(conn: sqlite3.Connection = Depends(get_db)) -> PresenterStateOut:
    return PresenterStateOut(**dict(set_locked(conn, True)))


@router.post("/unlock")
def post_unlock(conn: sqlite3.Connection = Depends(get_db)) -> PresenterStateOut:
    return PresenterStateOut(**dict(set_locked(conn, False)))


class RoomGameOut(BaseModel):
    id: str
    workspace_id: str
    user_name: str
    result: str | None
    time_limit_seconds: int
    started_at: str
    ended_at: str | None
    seconds_left: float | None
    legal_moves: int
    dataset_rows: int


class RoomGamesOut(BaseModel):
    games: list[RoomGameOut]
    playing: int
    finished: int
    total_dataset_rows: int


@router.get("/games")
def get_room_games(conn: sqlite3.Connection = Depends(get_db)) -> RoomGamesOut:
    """The dashboard feed: every game with live status, active first."""
    room = room_games(conn)
    now = datetime.now(UTC)
    games = [
        RoomGameOut(
            **dict(row),
            seconds_left=(
                remaining_seconds(row["started_at"], row["time_limit_seconds"], now)
                if row["result"] is None
                else None
            ),
        )
        for row in room.games
    ]
    playing = sum(1 for game in games if game.result is None)
    return RoomGamesOut(
        games=games,
        playing=playing,
        finished=len(games) - playing,
        total_dataset_rows=room.total_dataset_rows,
    )


@router.post("/reset-page")
def post_reset_page(
    body: PageSlugRequest, conn: sqlite3.Connection = Depends(get_db)
) -> ResetPageResponse:
    try:
        count = reset_page(conn, body.page_slug)
    except PageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ResetPageResponse(workspaces_reset=count)
