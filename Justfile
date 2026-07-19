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

# The whole session as a standalone Jupyter notebook. It is not embedded
# in tldraw and does not depend on the web app.
session-notebook:
    cd api && uv run jupyter lab --ServerApp.root_dir=.. ../notebooks/full-session.ipynb

start:
    #!/usr/bin/env bash
    set -euo pipefail
    trap 'kill 0' EXIT
    (cd api && uv run uvicorn euro_chess_studio.main:app --reload --port 8000) &
    (cd web && bun run sync-server) &
    (cd web && bun run dev) &
    # First exit takes the stack down: a room without its backend, or a
    # frontend without its room, is worse than a visible failure. The
    # complete release command surface is phase 36's item.
    wait -n

start-backend:
    cd api && uv run uvicorn euro_chess_studio.main:app --reload --port 8000

# The canvas sync room on port 8010. Loads the snapshot from the backend,
# runs canvas migrations, and persists every change back through it.
start-sync:
    cd web && bun run sync-server

# Fake OpenAI endpoint with configurable latency. Point the backend at
# it: OPENAI_API_KEY=test OPENAI_BASE_URL=http://127.0.0.1:9999 just start-backend
mock-llm delay="1.2":
    cd api && uv run python -m euro_chess_studio.tools.mock_llm --delay {{ delay }}

# Simulates a room hammering a running backend: joins, timed matches,
# model replies, assessments, presenter polling. Latency report at the end.
load-test attendees="20" duration="60":
    cd api && uv run python -m euro_chess_studio.tools.load_sim --attendees {{ attendees }} --duration {{ duration }}

start-frontend:
    cd web && bun run dev

test:
    cd api && uv run pytest
    cd web && bun test
    cd deck && bun test

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
