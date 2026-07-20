from contextlib import asynccontextmanager

import anyio.to_thread
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from euro_chess_studio.actions.adaptation import seed_adaptation_fixtures
from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.config import load_dotenv
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.pages_repo import upsert_page
from euro_chess_studio.data.seed import seed_cached_evals
from euro_chess_studio.routes import (
    adaptation,
    artifacts,
    canvas,
    datasets,
    evals,
    game,
    generation,
    jobs,
    moves,
    pages,
    presenter,
    users,
    workspaces,
)

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Sync routes each hold one worker thread, and a model-move request
    # holds its thread for the whole LLM round trip. The default pool of
    # 40 lets a full room saturate it; give the workshop headroom.
    anyio.to_thread.current_default_thread_limiter().total_tokens = 120
    conn = get_connection()
    try:
        init_db(conn)
        for page in PAGES:
            upsert_page(conn, page)
        seed_cached_evals(conn)
        seed_adaptation_fixtures(conn)
    finally:
        conn.close()
    yield


app = FastAPI(title="EuroSciPy Chess Studio API", lifespan=lifespan)

# The documented workshop origins only. LAN attendees never appear here:
# their browsers talk to the Vite dev server (5173) or the Slidev dev
# server (3030), and those servers proxy /api to this backend
# server-side, where CORS does not apply. The list exists for direct
# localhost access during development and rehearsal.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3030",
        "http://127.0.0.1:3030",
    ],
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
app.include_router(canvas.router)
app.include_router(game.router)
app.include_router(datasets.router)
app.include_router(generation.router)
app.include_router(adaptation.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
