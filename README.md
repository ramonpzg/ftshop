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

Current `main` is not yet the release build. In particular, canvas persistence
still writes a whole shared snapshot, presenter navigation does not transmit an
exact camera target, and the deck/backend development origins need tightening.
The ordered implementation briefs start with those room-correctness problems:
[notes/comms/README.md](notes/comms/README.md).

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

## Commands

Run `just` to list the full command surface. The regular development commands
are:

```text
just install          Install web, API, deck, and Jupyter dependencies
just start            Run API :8000 and web :5173
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

## Documentation

- [Architecture](docs/architecture.md)
- [Session plan](docs/session-plan.md)
- [Demo plan](docs/demo-plan.md)
- [Deck plan](docs/deck-plan.md)
- [Local development](docs/local-dev.md)
- [Asset licenses](docs/licenses.md)
- [Current phase prompts](notes/comms/README.md)
