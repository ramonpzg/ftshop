# Local development

## Prerequisites

- [Bun](https://bun.sh) (frontend tooling)
- [uv](https://docs.astral.sh/uv/) (Python backend tooling, manages its
  own Python)
- `just` (command runner)

## First run

```
just install
just start
```

`just start` runs the backend (`uvicorn`, port 8000) and frontend
(`vite`, port 5173) together and stops both on Ctrl-C. Open
http://localhost:5173.

On backend startup the app initializes `euro_chess_studio.db` at the
repo root, seeds the five pages, and seeds the cached illustrative eval
numbers (Stockfish-dependent metrics, image/audio/video quality scores)
that don't have a live computation path in v0. This happens every
startup and is idempotent.

## Commands

| Command | What it does |
|---|---|
| `just install` | Install frontend and backend dependencies |
| `just start` | Run backend + frontend together |
| `just start-backend` / `just start-frontend` | Run just one side |
| `just test` | Backend `pytest` + frontend `bun test` (fast, no real browser) |
| `just test-e2e` | Playwright smoke tests against real backend + frontend processes |
| `just lint` | `ruff check` + Biome lint |
| `just typecheck` | `ty check` + `tsc --noEmit` |
| `just format` | `ruff format` + Biome format |
| `just reset-db` | Delete and recreate the local SQLite database (empty) |
| `just seed` | Re-populate pages and cached eval fixtures |

`just reset-db` followed by `just seed` is the fastest way back to a
clean demo state without restarting the backend.

## Where things live

See `docs/architecture.md` for the actions/calculations/data split and
how the tldraw canvas and backend state relate. In short:

- Backend domain code: `api/src/euro_chess_studio/`
- Backend tests: `api/tests/` (mirrors the source layout)
- Frontend source: `web/src/`
- Frontend unit/component tests: `web/tests/`
- Frontend end-to-end tests: `web/e2e/`
- Cached job fixtures: `artifacts/cached/{text,image,audio,video}/`

## Testing notes

- Backend tests use a temporary SQLite file per test (`tmp_path`
  fixture) — never the real `euro_chess_studio.db`.
- Frontend component tests run under Bun's test runner with
  `@happy-dom/global-registrator` for a DOM. They mock `fetch` at the
  network boundary rather than mocking application modules, so the
  real fetch-wrapper and action code always runs.
- Full tldraw `Editor` instances aren't created in component tests —
  happy-dom doesn't implement enough browser API surface (canvas
  contexts, ResizeObserver, IndexedDB) for that to work reliably. Real
  canvas interaction is covered by the Playwright e2e suite instead
  (see below), and by manual verification during development.
- Frontend e2e tests (`web/e2e/`) launch real backend and frontend
  processes via Playwright's `webServer` config, pointed at a scratch
  SQLite file in the OS temp directory so they never touch your local
  dev database. They exercise the same custom-shape
  double-click-to-edit interaction used throughout the app (see
  "Interacting with workspace shapes" below).

## Interacting with workspace shapes

Workspace and modality panels are custom tldraw shapes that only
accept pointer events while in **edit mode** — the same convention
tldraw's own video and embed shapes use. Double-click a panel to open
it, click elsewhere to close it. This is why `web/e2e/smoke.spec.ts`
double-clicks with `{ force: true }`: Playwright's default
actionability check refuses to double-click something with
`pointer-events: none`, which is correct outside edit mode but needs
bypassing to *enter* edit mode in an automated test, exactly as a real
double-click would.

## Known limitations (v0)

- No auth. Anyone can join with any name; "your workspace is
  read-only to others" is a client-side UI affordance, not a security
  boundary (see `docs/architecture.md`).
- No live multi-client sync. Two browsers both talking to the same
  backend will see each other's users and workspaces (real, not
  simulated), but there's no push channel — each client only sees
  updates when it re-fetches.
- Several eval metrics (centipawn loss, image/audio/video quality
  scores) are seeded from cached fixtures, not computed live, because
  they need infrastructure (Stockfish, a trained judge model) that's
  out of scope for v0. This is surfaced in the UI via each row's
  `source: cached` badge and the fixture's own `note` field.
- `CloudRunner` is a stub (`NotImplementedError`) — no cloud job
  execution exists yet.
