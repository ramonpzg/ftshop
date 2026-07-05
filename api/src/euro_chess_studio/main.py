from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.pages_repo import upsert_page
from euro_chess_studio.data.seed import seed_cached_evals
from euro_chess_studio.routes import (
    artifacts,
    evals,
    jobs,
    moves,
    pages,
    presenter,
    users,
    workspaces,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection()
    try:
        init_db(conn)
        for page in PAGES:
            upsert_page(conn, page)
        seed_cached_evals(conn)
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

app.include_router(pages.router)
app.include_router(users.router)
app.include_router(workspaces.router)
app.include_router(moves.router)
app.include_router(presenter.router)
app.include_router(jobs.router)
app.include_router(artifacts.router)
app.include_router(evals.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
