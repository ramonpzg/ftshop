import sqlite3

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from euro_chess_studio.data.pages_repo import list_pages
from euro_chess_studio.deps import get_db

router = APIRouter(tags=["pages"])


class PageOut(BaseModel):
    id: str
    slug: str
    title: str
    modality: str
    order_index: int


@router.get("/pages")
def get_pages(conn: sqlite3.Connection = Depends(get_db)) -> list[PageOut]:
    return [PageOut(**dict(row)) for row in list_pages(conn)]
