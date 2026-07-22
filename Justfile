set shell := ["bash", "-uc"]

gemma_model := "google/gemma-4-E2B-it-qat-q4_0-gguf"

default:
    just --list

# Install all core workshop surfaces, or only the requested ones. Models and
# optional audio dependencies stay explicit because they are several GB.
# Examples: `just install --nb`, `just install --deck`,
# `just install --whiteboard`, `just install --api --web`.
install *targets:
    #!/usr/bin/env bash
    set -euo pipefail

    requested="{{ targets }}"
    install_web=0
    install_api=0
    install_deck=0
    install_nb=0

    if [[ -z "${requested}" ]]; then
        install_web=1
        install_api=1
        install_deck=1
        install_nb=1
    fi

    for target in ${requested}; do
        case "${target}" in
            --all)
                install_web=1
                install_api=1
                install_deck=1
                install_nb=1
                ;;
            --whiteboard)
                install_web=1
                install_api=1
                ;;
            --web)
                install_web=1
                ;;
            --api)
                install_api=1
                ;;
            --deck)
                install_deck=1
                ;;
            --nb|--notebook)
                install_nb=1
                ;;
            --help)
                printf '%s\n' \
                    'Usage: just install [--all|--whiteboard|--web|--api|--deck|--nb] ...' \
                    '' \
                    'No flags installs every core surface. Models and optional audio are separate.'
                exit 0
                ;;
            *)
                echo "Unknown install target: ${target}" >&2
                exit 2
                ;;
        esac
    done

    if (( install_web )); then
        echo "Installing whiteboard frontend and sync room"
        (cd web && bun install --frozen-lockfile)
    fi
    if (( install_api )); then
        echo "Installing FastAPI backend"
        (cd api && uv sync --locked)
    fi
    if (( install_deck )); then
        echo "Installing Slidev deck"
        (cd deck && bun install --frozen-lockfile)
    fi
    if (( install_nb )); then
        echo "Installing standalone notebook environment"
        # Keep optional packages Ramon has installed locally (notably
        # MusicGen) while enforcing the locked notebook baseline.
        uv sync --locked --inexact
    fi

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

# Build the bounded Lichess sample, enrich it with Luna, train a Gemma 4
# adapter, and optionally publish it. With no flags this runs the viable
# laptop path: prepare + enrich + QLoRA + push. Generated data and model
# artifacts stay outside git. See `just chess-adapt --help` before a run.
chess-adapt *args:
    #!/usr/bin/env bash
    set -euo pipefail
    arguments=( {{ args }} )
    if (( ${#arguments[@]} == 0 )); then
        arguments=(--all)
    fi

    uv_args=(--project training --python 3.12)
    for argument in "${arguments[@]}"; do
        case "${argument}" in
            --all|--lora|--qlora)
                uv_args+=(--extra gpu)
                break
                ;;
        esac
    done

    uv run "${uv_args[@]}" chess-adapt "${arguments[@]}"

# Resolve the isolated CUDA/Unsloth environment without starting a run.
# This is intentionally separate from `just install`: attendees do not
# need several GB of trainer dependencies.
install-chess-training:
    uv sync --project training --python 3.12 --extra gpu

# The Slidev deck on port 3030. The Presentation page embeds it; the
# tab itself has presenter mode and speaker notes. Two styles share
# every slide: `just deck` is the light paper scoresheet, `just deck
# chalk` is the dark, slightly hand-written one that sits next to
# tldraw.
deck style="paper":
    cd deck && VITE_DECK_STYLE={{ style }} bun run dev

# The whole session as a standalone Jupyter notebook. It is not embedded
# in tldraw and does not depend on the web app.
session-notebook notebook="notebooks/main-nb.ipynb":
    uv run jupyter lab --ServerApp.root_dir=. {{ notebook }}

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

# Print the single URL attendees need on the presenter's local network.
room-url:
    #!/usr/bin/env bash
    set -euo pipefail
    address=""
    if command -v ip >/dev/null 2>&1; then
        address="$(ip route get 1.1.1.1 2>/dev/null | awk '{for (i=1; i<=NF; i++) if ($i == "src") {print $(i+1); exit}}')"
    fi
    if [[ -z "${address}" ]] && command -v ipconfig >/dev/null 2>&1; then
        address="$(ipconfig getifaddr en0 2>/dev/null || true)"
    fi
    if [[ -z "${address}" ]] && command -v hostname >/dev/null 2>&1; then
        address="$(hostname -I 2>/dev/null | awk '{print $1}')"
    fi
    if [[ -z "${address}" ]]; then
        echo "Could not determine a LAN address. Use the Network URL printed by Vite." >&2
        exit 1
    fi
    echo "http://${address}:5173"

test:
    cd api && uv run pytest
    cd training && uv run pytest
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
    cd training && uv run ruff check .
    cd web && bun run lint

typecheck:
    cd api && uv run ty check src
    cd training && uv run ty check src
    cd web && bun run typecheck

format:
    cd api && uv run ruff format .
    cd training && uv run ruff format .
    cd web && bun run format

reset-db:
    cd api && uv run python -m euro_chess_studio.data.reset_db

# Deletes the authored canvas (slides, shapes). Keeps uploaded assets.
reset-canvas:
    rm -f data/canvas/snapshot.json data/canvas/snapshot.prev.json
    @echo "canvas reset. uploaded assets in data/assets/ were kept."

seed:
    cd api && uv run python -m euro_chess_studio.data.seed
