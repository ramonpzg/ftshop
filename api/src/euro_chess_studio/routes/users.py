import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from euro_chess_studio.actions.workspaces import join_workshop
from euro_chess_studio.data.users_repo import list_users
from euro_chess_studio.deps import get_db

router = APIRouter(tags=["users"])


class UserOut(BaseModel):
    id: str
    name: str
    created_at: str


class JoinRequest(BaseModel):
    name: str


@router.post("/users", status_code=201)
def create_user(body: JoinRequest, conn: sqlite3.Connection = Depends(get_db)) -> UserOut:
    try:
        row = join_workshop(conn, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return UserOut(**dict(row))


@router.get("/users")
def get_users(conn: sqlite3.Connection = Depends(get_db)) -> list[UserOut]:
    return [UserOut(**dict(row)) for row in list_users(conn)]
