# EuroSciPy Chess Studio

Workshop software for the EuroSciPy 2026 session "Same Recipe, Different
Results: Fine-Tuning Models Across Modalities".

Chess is the shared domain across text, image, audio, and video. The repository
has three deliberately separate teaching assets:

- `web/`: a hand-drawn tldraw whiteboard where the room works;
- `deck/`: a Slidev presentation with its own projected visual system;
- `notebooks/main-nb.ipynb`: a pragmatic, standalone Jupyter notebook.

The notebook is plain Jupyter and runs independently of the whiteboard.

The supporting `tui/` app runs chess against llama.cpp on a phone or laptop.
The isolated `training/` project prepares the bounded chess dataset and trains
LoRA or QLoRA adapters. Neither is required to read or run the notebook.

## Notebook only

This is the smallest useful install. It needs [uv](https://docs.astral.sh/uv/)
and [`just`](https://github.com/casey/just), plus Git to clone the repository.
It does not need Bun, Node, the whiteboard, llama.cpp, or downloaded model
weights. `uv` selects a compatible Python 3.11 or newer and installs the
locked dependencies.

```bash
git clone https://github.com/ramonpzg/ftshop.git
cd ftshop
just install --nb
just session-notebook
```

`just install --nb` creates the locked root `.venv` and registers the
`Python (ftshop .venv)` kernel inside it. `just session-notebook` opens
`notebooks/main-nb.ipynb` in JupyterLab. Most of the notebook is local Python;
the live API and media cells are optional and state which key or server they
need.

To open another notebook with the same environment:

```bash
just session-notebook notebooks/another.ipynb
```

## Full workshop app

The shared room and deck also require [Bun](https://bun.sh). Install every
surface, then start the whiteboard stack:

```bash
just install
just start
```

Open <http://localhost:5173>. The command runs the API on port 8000, the tldraw
sync room on 8010, and the web app on 5173. The deck and notebook are separate
processes, normally started in their own terminals:

```bash
just deck               # Slidev on http://localhost:3030
just session-notebook   # JupyterLab with notebooks/main-nb.ipynb
```

On a weak connection, install only what you will use. Flags can be combined.

| Command | Installs |
|---|---|
| `just install --nb` | Standalone notebook and Jupyter kernel |
| `just install --whiteboard` | Web app, sync room, and API |
| `just install --web` | Web app and sync room only |
| `just install --api` | FastAPI backend only |
| `just install --deck` | Slidev deck only |
| `just install --tui` | Isolated phone chess TUI |
| `just install` | Every surface above |

Installation does not download model weights or the optional multi-GB audio
stack.

## Model endpoints

Hosted model calls use the OpenAI-compatible Chat Completions endpoint,
`/chat/completions`. Choose the provider before starting JupyterLab:

```bash
# Direct OpenAI
export CHAT_PROVIDER=openai
export OPENAI_API_KEY=...
export OPENAI_MODEL=gpt-5.6-luna

# Or OpenRouter
export CHAT_PROVIDER=openrouter
export OPENROUTER_API_KEY=...
export OPENROUTER_MODEL=openai/gpt-5.6-luna
```

Provider-specific model names must match the configured endpoint. The
notebook keeps local Gemma and the hosted provider independent, so one being
unavailable does not prevent the other comparison row from running.

The local baseline is `google/gemma-4-E2B-it-qat-q4_0-gguf`. With a current
llama.cpp installation, this serves it on the notebook's default endpoint,
`http://127.0.0.1:8080/v1`:

```bash
just start-gemma
```

The recipe name reflects the workshop default, but it can serve any local
llama.cpp-compatible GGUF without changing the notebook:

```bash
just start-gemma --model "$HOME/models/my-model.gguf"
```

The API alias stays `gemma-4-2b-local`, which is what the notebook requests.
Other useful forms are:

```bash
just start-gemma --model /path/model.gguf 9017
just start-gemma --hf owner/model-gguf:Q4_K_M
```

If the port changes, set the matching notebook variable before starting
JupyterLab:

```bash
GEMMA_BASE_URL=http://127.0.0.1:9017/v1 \
just session-notebook
```

Run `just start-gemma --help` for the complete syntax. `just download-models`
is an optional presenter-preparation command that downloads and verifies the
workshop Gemma and MusicGen. It is deliberately separate from installation.
Stable Audio remains commented out and is not required.

The published chess artifact is a PEFT adapter, not a deployment-ready GGUF.
Trainer examples use the matching
`google/gemma-4-E2B-it-qat-q4_0-unquantized` weights. llama.cpp use requires a
separate merge and GGUF conversion; passing a GGUF repository directly to TRL
or Axolotl is not the same operation.

Game analysis also produces the detailed real-world scene prompt used for
video generation. It defaults to Luna. When the opponent uses a different
endpoint, set `VIDEO_PROMPT_API_KEY`, `VIDEO_PROMPT_BASE_URL`, and
`VIDEO_PROMPT_MODEL=gpt-5.6-luna` separately. Each value otherwise falls back
to its `OPENAI_*` counterpart.

## Commands

Run `just` to list the full command surface. The regular development commands
are:

```text
just install          Install all core surfaces; flags select individual ones
just download-models  Download and verify all local models
just start            Run API :8000, the canvas sync room :8010, and web :5173
just room-url         Print the board URL for devices on the same network
just start-gemma      Serve default Gemma or a local GGUF through llama.cpp
just chess-adapt      Prepare/train/publish, or pull the public chess adapter
just deck             Run Slidev :3030
just session-notebook Open the standalone Jupyter notebook
just phone-tui        Run the Termux chess TUI (docs/phone-tui.md)
just test             Run API, training, web, deck, and TUI tests
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
it.

## Documentation

- [Architecture](docs/architecture.md)
- [Session plan](docs/session-plan.md)
- [Demo plan](docs/demo-plan.md)
- [Deck plan](docs/deck-plan.md)
- [Local development](docs/local-dev.md)
- [Asset licenses](docs/licenses.md)
- [Chess adapter run](docs/chess-adaptation.md)
- [Phone TUI](docs/phone-tui.md)
- [Current phase prompts](notes/comms/README.md)
