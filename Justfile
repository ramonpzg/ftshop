set shell := ["bash", "-uc"]

default:
    just --list

install:
    cd web && bun install
    cd api && uv sync
    cd deck && bun install

# Local text-to-audio models (musicgen, stable audio). Several GB.
install-audio:
    cd api && uv sync --extra audio

# The Slidev deck on port 3030. The Presentation page embeds it; the
# tab itself has presenter mode and speaker notes.
deck:
    cd deck && bun run dev

# The whole session as one notebook. The fallback if the app dies on
# stage. Not in the WASM export list on purpose: it trains with JAX and
# calls local models, which pyodide cannot do.
session-notebook:
    uvx marimo edit --sandbox notebooks/full-session.py

# Regenerates notebooks/full-session.md, the readable twin of the
# fallback notebook. Rerun after editing the notebook.
notebook-md:
    cd api && uv run marimo export md ../notebooks/full-session.py -o ../notebooks/full-session.md

# Exports the marimo notebooks to in-browser WASM under web/public/notebooks.
# Rerun after editing anything in notebooks/.
notebooks:
    #!/usr/bin/env bash
    set -euo pipefail
    for nb in chess-machine painting-pieces board-sound real-world-video; do
        (cd api && uv run marimo export html-wasm "../notebooks/$nb.py" -o "../web/public/notebooks/$nb" --mode edit -f)
    done
    echo "notebooks exported. pyodide still loads from its CDN on first open."

start:
    #!/usr/bin/env bash
    set -euo pipefail
    trap 'kill 0' EXIT
    (cd api && uv run uvicorn euro_chess_studio.main:app --reload --port 8000) &
    (cd web && bun run dev) &
    wait

start-backend:
    cd api && uv run uvicorn euro_chess_studio.main:app --reload --port 8000

# Fake OpenAI endpoint with configurable latency. Point the backend at
# it: OPENAI_API_KEY=test OPENAI_BASE_URL=http://127.0.0.1:9999 just start-backend
mock-llm delay="1.2":
    cd api && uv run python -m euro_chess_studio.tools.mock_llm --delay {{delay}}

# Simulates a room hammering a running backend: joins, timed matches,
# model replies, assessments, presenter polling. Latency report at the end.
load-test attendees="20" duration="60":
    cd api && uv run python -m euro_chess_studio.tools.load_sim --attendees {{attendees}} --duration {{duration}}

start-frontend:
    cd web && bun run dev

test:
    cd api && uv run pytest
    cd web && bun test

test-backend:
    cd api && uv run pytest

test-frontend:
    cd web && bun test

test-e2e:
    cd web && bun run test:e2e

lint:
    cd api && uv run ruff check .
    cd web && bun run lint

typecheck:
    cd api && uv run ty check src
    cd web && bun run typecheck

format:
    cd api && uv run ruff format .
    cd web && bun run format

reset-db:
    cd api && uv run python -m euro_chess_studio.data.reset_db

# Deletes the authored canvas (slides, shapes). Keeps uploaded assets.
reset-canvas:
    rm -f data/canvas/snapshot.json data/canvas/snapshot.prev.json
    @echo "canvas reset. uploaded assets in data/assets/ were kept."

seed:
    cd api && uv run python -m euro_chess_studio.data.seed
