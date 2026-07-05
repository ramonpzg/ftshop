set shell := ["bash", "-uc"]

default:
    just --list

install:
    cd web && bun install
    cd api && uv sync

start:
    #!/usr/bin/env bash
    set -euo pipefail
    trap 'kill 0' EXIT
    (cd api && uv run uvicorn euro_chess_studio.main:app --reload --port 8000) &
    (cd web && bun run dev) &
    wait

start-backend:
    cd api && uv run uvicorn euro_chess_studio.main:app --reload --port 8000

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

seed:
    cd api && uv run python -m euro_chess_studio.data.seed
