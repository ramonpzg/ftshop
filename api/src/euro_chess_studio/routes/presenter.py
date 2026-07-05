import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from euro_chess_studio.actions.errors import PageNotFoundError
from euro_chess_studio.actions.presenter import (
    bring_to_presenter_view,
    get_presenter_state,
    reset_page,
    send_to_workspaces,
    set_locked,
)
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


@router.post("/reset-page")
def post_reset_page(
    body: PageSlugRequest, conn: sqlite3.Connection = Depends(get_db)
) -> ResetPageResponse:
    try:
        count = reset_page(conn, body.page_slug)
    except PageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ResetPageResponse(workspaces_reset=count)
