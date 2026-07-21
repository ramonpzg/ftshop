set shell := ["bash", "-uc"]

gemma_model := "google/gemma-4-E2B-it-qat-q4_0-gguf"

default:
    just --list

install:
    cd web && bun install
    cd api && uv sync
    cd deck && bun install
    cd tui && uv sync

# Local text-to-audio models (musicgen, stable audio). Several GB.
install-audio:
    cd api && uv sync --extra audio

# Regenerate the committed workshop media under artifacts/cached/media
# (piece renders, synthesized audio, the storyboard clips). Deterministic;
# provenance lives in the tool's docstring and docs/licenses.md.
make-media:
    cd api && uv sync --extra media
    cd api && uv run python -m euro_chess_studio.tools.make_media

# Download every model used locally and verify it before the session.
# Stable Audio is gated: accept its license and set HF_TOKEN first.
download-models:
    #!/usr/bin/env bash
    set -euo pipefail
    command -v llama >/dev/null || {
        echo "llama.cpp is required: https://github.com/ggml-org/llama.cpp" >&2
        exit 1
    }

    echo "Downloading {{ gemma_model }} into the llama.cpp cache"
    llama download -hf "{{ gemma_model }}:Q4_0"
    echo "Verifying Gemma with an offline load"
    llama cli \
        -hf "{{ gemma_model }}:Q4_0" \
        --no-mmproj --single-turn \
        --no-display-prompt --no-show-timings --reasoning off \
        --prompt "Tell a quick one-line joke." --predict 64

    audio_models=(
        "facebook/musicgen-small"
        # "stabilityai/stable-audio-open-1.0"
    )
    for model in "${audio_models[@]}"; do
        echo "Downloading ${model}"
        uvx --from huggingface-hub hf download "${model}"
        uvx --from huggingface-hub hf cache verify "${model}" --fail-on-missing-files
    done

# Gemma 4 on llama.cpp's OpenAI-compatible API at http://127.0.0.1:8080/v1.
start-gemma port="8080":
    #!/usr/bin/env bash
    set -euo pipefail
    command -v llama >/dev/null || {
        echo "llama.cpp is required: https://github.com/ggml-org/llama.cpp" >&2
        exit 1
    }
    exec llama serve \
        -hf "{{ gemma_model }}:Q4_0" \
        --alias gemma-4-2b-local \
        --host 127.0.0.1 \
        --port "{{ port }}"

# The Slidev deck on port 3030. The Presentation page embeds it; the
# tab itself has presenter mode and speaker notes. Two styles share
# every slide: `just deck` is the light paper scoresheet, `just deck
# chalk` is the dark, slightly hand-written one that sits next to
# tldraw.
deck style="paper":
    cd deck && VITE_DECK_STYLE={{ style }} bun run dev

# The whole session as a standalone Jupyter notebook. It is not embedded
# in tldraw and does not depend on the web app.
session-notebook:
    cd api && uv run jupyter lab --ServerApp.root_dir=.. ../notebooks/full-session.ipynb

# The phone chess TUI, desktop convenience run. Expects a llama.cpp
# server on 127.0.0.1:9017 (`just start-gemma 9017`; the TUI default
# avoids crowded 8080). The phone itself does not need just:
# docs/phone-tui.md has the Termux path.
phone-tui:
    cd tui && uv run chess-tui

test-tui:
    cd tui && uv run pytest

# Sdist and wheel build for the TUI. The phone installs from the repo
# checkout, but the package must always be buildable.
package-tui:
    cd tui && uv build

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
    cd tui && uv run pytest

test-backend:
    cd api && uv run pytest

test-frontend:
    cd web && bun test

test-e2e:
    cd web && bun run test:e2e

lint:
    cd api && uv run ruff check .
    cd web && bun run lint
    cd tui && uv run ruff check .

typecheck:
    cd api && uv run ty check src
    cd web && bun run typecheck
    cd tui && uv run ty check src

format:
    cd api && uv run ruff format .
    cd web && bun run format
    cd tui && uv run ruff format .

reset-db:
    cd api && uv run python -m euro_chess_studio.data.reset_db

# Deletes the authored canvas (slides, shapes). Keeps uploaded assets.
reset-canvas:
    rm -f data/canvas/snapshot.json data/canvas/snapshot.prev.json
    @echo "canvas reset. uploaded assets in data/assets/ were kept."

seed:
    cd api && uv run python -m euro_chess_studio.data.seed
