# EuroSciPy Chess Studio

Workshop software for the EuroSciPy 2026 session "Same Recipe, Different
Results: Fine-Tuning Models Across Modalities".

Chess is the shared domain across text, image, audio, and video. The repository
has three deliberately separate teaching assets:

- `web/`: a hand-drawn tldraw whiteboard where the room works;
- `deck/`: a Slidev presentation with its own projected visual system;
- `notebooks/full-session.ipynb`: a pragmatic, standalone Jupyter notebook.

The notebook is not a Marimo app and is not required inside the whiteboard.
Legacy Marimo sources and compatibility support for old notebook shapes remain
until a reviewed phase removes them. Do not regenerate the old browser
notebook exports.

## Current status

The app is in pre-workshop hardening. It has a FastAPI backend, durable SQLite
workshop state, a backend-persisted canvas snapshot, cached offline artifacts,
live model and media-generation paths, presenter controls, and room exports.

Current `main` is not yet the release build. Canvas persistence, presenter
navigation, and the deck's network path were phase 32's room-correctness
problems; all three are fixed as of that phase: the canvas is a real
multiplayer room built on tldraw's own sync engine (conflicts resolve per
record, not by one shared snapshot overwriting another), presenter navigation
transmits an exact camera target (bounds, with a frame id riding along), and
the deck reaches the backend through a documented LAN-safe proxy with CORS
limited to the four listed dev origins. See
[notes/comms/README.md](notes/comms/README.md) for the current phase order and
what each remaining phase owns.

## Quick start

Prerequisites: [Bun](https://bun.sh), [uv](https://docs.astral.sh/uv/), and
[`just`](https://github.com/casey/just).

```bash
just install
just start
```

Open <http://localhost:5173>. The API runs at <http://localhost:8000>.
The deck and Jupyter notebook are separate processes:

```bash
just deck               # Slidev on http://localhost:3030
just session-notebook   # JupyterLab with notebooks/full-session.ipynb
```

Model calls use the OpenAI-compatible Chat Completions endpoint,
`/chat/completions`. Configure `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and
`OPENAI_MODEL` together. The current default model is `gpt-5.6-luna`.
Provider-specific model names still need to match the configured endpoint.

The local Gemma baseline is
`google/gemma-4-E2B-it-qat-q4_0-gguf`. For llama.cpp, start it with:

```bash
just download-models  # Gemma, MusicGen, Stable Audio; download and verify
just start-gemma      # OpenAI-compatible API on http://127.0.0.1:8080/v1
```

Stable Audio is gated. Accept its Hugging Face license and set `HF_TOKEN`
before running `just download-models`.

That repository is a deployment-ready QAT GGUF. Trainer examples use the
matching `google/gemma-4-E2B-it-qat-q4_0-unquantized` weights, then convert the
merged result back to GGUF. Passing a GGUF repository directly to TRL or
Axolotl is not the same operation.

Game analysis also produces the detailed real-world scene prompt used for
video generation. It defaults to Luna. When the opponent uses a different
endpoint, set `VIDEO_PROMPT_API_KEY`, `VIDEO_PROMPT_BASE_URL`, and
`VIDEO_PROMPT_MODEL=gpt-5.6-luna` separately. Each value otherwise falls back
to its `OPENAI_*` counterpart.

## Commands

Run `just` to list the full command surface. The regular development commands
are:

```text
just install          Install web, API, deck, and Jupyter dependencies
just download-models  Download and verify all local models
just start            Run API :8000, the canvas sync room :8010, and web :5173
just start-gemma      Run Gemma 4 through llama.cpp on :8080
just deck             Run Slidev :3030
just session-notebook Open the standalone Jupyter notebook
just test             Run backend and frontend tests
just test-e2e         Run Playwright smoke tests
just lint             Run Ruff and Biome
just typecheck        Run ty and TypeScript checks
just format           Format API and web code
just reset-db         Reset SQLite workshop state
just reset-canvas     Delete the authored canvas snapshot
just seed             Seed pages and cached eval fixtures
just mock-llm         Run the local Chat Completions test server
just load-test        Simulate a room against a running backend
```

## Development workflow

`main` is the default branch locally and on GitHub. Each phase starts from an
accepted `main`, uses the branch named in its prompt, and remains unmerged until
Ramon reviews the agent summary and diff.

Commit throughout a phase. Commits should be coherent, tested at the relevant
scope, and written like a concise development log. Push the phase branch for
review. A finished phase has no relevant untracked or uncommitted files and
includes its `notes/ai/` handover and `notes/hu/` learning guide.

Playwright uses its own default browser discovery for `just test-e2e`. Set
`CHESS_STUDIO_CHROMIUM` to a specific executable path if you need to override
it; phase 36 owns the rest of the release command surface.

## Documentation

- [Architecture](docs/architecture.md)
- [Session plan](docs/session-plan.md)
- [Demo plan](docs/demo-plan.md)
- [Deck plan](docs/deck-plan.md)
- [Local development](docs/local-dev.md)
- [Asset licenses](docs/licenses.md)
- [Current phase prompts](notes/comms/README.md)
