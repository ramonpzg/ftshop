import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from euro_chess_studio.actions.errors import InvalidSnippetError, WorkspaceNotFoundError
from euro_chess_studio.actions.workspaces import (
    PageNotFoundError,
    create_or_get_workspace,
    select_snippet,
)
from euro_chess_studio.data.workspaces_repo import list_workspaces_with_details
from euro_chess_studio.deps import get_db

router = APIRouter(tags=["workspaces"])


class WorkspaceOut(BaseModel):
    id: str
    user_id: str
    page_id: str
    shape_id: str
    position_index: int
    selected_snippet_id: str | None
    board_fen: str


class WorkspaceWithDetailsOut(WorkspaceOut):
    user_name: str
    page_slug: str
    page_title: str


class CreateWorkspaceRequest(BaseModel):
    user_id: str
    page_slug: str


@router.post("/workspaces", status_code=201)
def create_workspace(
    body: CreateWorkspaceRequest, conn: sqlite3.Connection = Depends(get_db)
) -> WorkspaceOut:
    try:
        row = create_or_get_workspace(conn, body.user_id, body.page_slug)
    except PageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return WorkspaceOut(**dict(row))


@router.get("/workspaces")
def get_workspaces(conn: sqlite3.Connection = Depends(get_db)) -> list[WorkspaceWithDetailsOut]:
    return [WorkspaceWithDetailsOut(**dict(row)) for row in list_workspaces_with_details(conn)]


class SelectSnippetRequest(BaseModel):
    snippet_id: str


@router.put("/workspaces/{workspace_id}/snippet")
def put_snippet(
    workspace_id: str, body: SelectSnippetRequest, conn: sqlite3.Connection = Depends(get_db)
) -> WorkspaceOut:
    try:
        row = select_snippet(conn, workspace_id, body.snippet_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidSnippetError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return WorkspaceOut(**dict(row))
