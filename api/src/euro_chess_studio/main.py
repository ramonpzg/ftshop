from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.pages_repo import list_pages, upsert_page


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection()
    try:
        init_db(conn)
        for page in PAGES:
            upsert_page(conn, page)
    finally:
        conn.close()
    yield


app = FastAPI(title="EuroSciPy Chess Studio API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class PageOut(BaseModel):
    id: str
    slug: str
    title: str
    modality: str
    order_index: int


@app.get("/pages")
def get_pages() -> list[PageOut]:
    conn = get_connection()
    try:
        rows = list_pages(conn)
        return [PageOut(**dict(row)) for row in rows]
    finally:
        conn.close()
