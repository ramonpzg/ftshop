# Phase 5 prompt: engineering and release readiness

Use this prompt after the room, data, learning flow, and deck branches have
been reviewed and accepted.

## Prompt

You are implementing phase 36 of `euro-scipy-chess-studio`: finish the
engineering and operational work needed to run the accepted workshop build in
a real EuroSciPy room.

Earlier phases fixed behavior and teaching truth. This phase reduces
maintenance and rehearsal risk without redesigning accepted flows. The main
problems are oversized React workflow components, repository-owned commits,
inconsistent async failure handling, a release command surface that excludes
the deck, weak E2E coverage, and no single presenter preflight.

### Branch and boundaries

- Start from the accepted phase 35 result and create
  `phase-36-release-readiness`.
- Read `AGENTS.md`, `CLAUDE.md`, architecture, local development, session and
  demo plans, plus all phase 32-35 handovers before editing.
- Inspect the current behavior and tests before extracting code. Refactoring
  must preserve the accepted UX and API contracts unless a documented defect
  requires a small correction.
- Preserve unrelated work. Do not read, edit, format, export, regenerate, or
  resolve anything in `notebooks/` or `web/public/notebooks/`.
- The notebook is standalone Jupyter. Do not add Marimo commands, notebook
  exports, a tldraw notebook panel, or an iframe requirement to release checks.
- Do not perform another visual redesign or rewrite the workshop narrative.
- Everything operational must be reachable through the `Justfile`. Do not add
  one-off shell or Python scripts outside the existing package/tool structure.

### 1. Enforce actions, calculations, and data boundaries

Audit frontend components, starting with `WorkspacePanel`, `ModalityPanel`,
`PresenterPanel`, presenter synchronization, and the monolithic API client.
Extract by responsibility, not by line count alone.

Target shape:

- components render typed view state and send user commands;
- actions or focused controllers orchestrate API calls and state transitions;
- calculations perform pure transformations such as derived clock state,
  dataset presentation, camera targets, and comparison labels;
- data modules own HTTP, local storage, synchronization transport, timeout,
  serialization, and provider-specific I/O;
- domain state machines are testable without rendering React.

Avoid a generic hook or service layer that merely moves the same mixed logic
to another large file. Keep feature ownership visible. Split `data/api.ts` by
resource only where it improves contract clarity and testability.

On the backend, finish the transaction model begun in phase 33. Repositories
must not decide transaction boundaries. Actions should be able to commit or
roll back a complete operation. Cover concurrent game creation, ply numbering,
dataset row insertion, assessment persistence, job completion, and reset
operations with appropriate constraints.

Document the final boundaries in `docs/architecture.md` using concrete files
from the implementation.

### 2. Standardize asynchronous and offline behavior

Create one small, consistent approach for browser requests and polling:

- request timeout and cancellation;
- in-flight guards so intervals do not overlap;
- monotonic revisions or request ordering where stale responses matter;
- typed errors with a concise user-facing message and diagnostic detail for
  logs;
- explicit initial loading, refreshing, stale, offline, failed, retrying, and
  recovered states where relevant;
- bounded retry with jitter for safe reads, not automatic repetition of
  destructive commands;
- cleanup on component unmount and page navigation.

Apply it to workspace loading, presenter state, attendee roster, room games,
jobs, eval refresh, artifact refresh, deck LiveRoom, generation, and canvas
connection. Do not blanket-catch and suppress errors. A backend interruption
must leave existing content visible when safe and say that it may be stale.

Preserve the phase 33 Chat Completions contract. Do not migrate text calls to
the Responses API during client consolidation. The shared request layer must
retain model-capability handling, bounded retries, provider request IDs,
redaction, raw-response provenance, and the narrowly defined retry for the
observed transient generic permissions `401`. Do not broaden that exception to
explicit invalid-key or access-denial responses during refactoring.

For long fal generation requests, use fal's queue/status mechanism or another
supported asynchronous boundary rather than tying up a request worker for ten
minutes. Persist provider request ID and status, support polling and failure,
and add cancellation if the provider supports it. Keep provider details behind
the job runner/data boundary.

### 3. Build one portable verification surface

Repair Playwright configuration so it uses the installed or Playwright-managed
browser by default and supports an explicit executable override without a
machine-specific hardcoded path.

Add or consolidate Just recipes so a contributor can run:

- install, including documented Playwright browser setup;
- lint for API, web, and deck;
- typecheck for API, web, and deck where supported;
- unit/integration tests for API, web, and deck;
- production builds for web and deck;
- E2E with isolated temporary database, canvas, and asset directories;
- a full release check that composes the above without modifying authored
  workshop data;
- a rehearsal load test and presenter preflight.

`just test-e2e` must start and stop its own services cleanly, use temporary
state, choose available ports safely, and leave no background process. Do not
require the user to shut down unrelated local services without checking them.

Expand E2E coverage around the actual workshop contract:

1. join and identity recovery;
2. two-client concurrent canvas editing and ownership;
3. presenter frame, late join, lock, release, and reset;
4. timed game with legal, illegal, timeout, model failure, and recovery paths;
5. dataset/scenario export and base/adapted eval provenance;
6. image/audio/video cached fallbacks and media playback presence;
7. deck embedded and standalone, LiveRoom connected and offline;
8. backend restart or temporary loss with UI recovery;
9. projector and narrow-laptop layouts without incoherent overlap.

Use focused tests and shared fixtures. Do not create a single long E2E that
fails ambiguously after fifteen minutes.

### 4. Add presenter preflight and workshop capability protection

Implement `just preflight` and a concise presenter-visible preflight view. It
must check without spending provider money by default:

- database, canvas, backup, assets, and generated-artifact paths are writable;
- authored canvas schema is current and required pages/shapes exist;
- web, API, deck, proxy, and LiveRoom connectivity;
- cached artifacts exist, have expected hashes or metadata, and local media is
  readable;
- configured provider aliases are known and credentials are present when live
  use is requested;
- the configured OpenAI-compatible text model passes a no-cost configuration
  check without referring to `gpt-5.5-mini`, and an opt-in smoke uses
  `/chat/completions`;
- enough disk space exists for expected media;
- mock LLM and offline fallback paths can complete;
- presenter state can be reset and the room is empty or intentionally reused;
- current build/revision and dependency lock information are visible.

Provide a separate explicit opt-in live provider smoke that reports estimated
or configured spend before sending requests. Never print secrets.

Replace `?presenter=1` as the only protection for reset, lock, navigation, and
room-wide export. A workshop-scoped capability token generated at startup and
kept out of attendee URLs is sufficient. This is not an enterprise-auth
project. Protect destructive/presenter actions, apply upload/body size limits,
validate names and media types, and add modest rate limits where one attendee
could otherwise disrupt the room.

Keep local development convenient and document how the presenter URL or token
is obtained. Never embed a long-lived secret in frontend source or committed
canvas data.

### 5. Rehearse the release, not just the modules

Run the complete release check from a clean worktree or equivalent isolated
checkout without touching Ramon's notebook work. Verify that the authored
canvas and required cached assets are actually tracked or reproducibly seeded;
a clean clone must not open an empty workshop.

The standalone Jupyter notebook is not part of the automated app build in this
phase. The runbook may state how Ramon opens it, but release readiness must not
depend on serving it through Vite, tldraw, Marimo, or a notebook export.

Run the room load simulation for 40 attendees against the final stack,
including the web proxy, browser polling/sync, presenter changes, canvas
activity, mock model latency, and representative exports. Report p50, p95,
errors, database contention, synchronization lag, and memory growth. The
existing backend-only load simulation may be extended or complemented through
a proper package tool exposed by `just load-test`; do not leave an ad hoc
script.

Perform and document these rehearsals:

- offline/no-key run using every cached fallback;
- LAN run with at least two physical devices or clearly document why it could
  not be performed;
- presenter laptop at intended projector resolution;
- backend restart and recovery;
- deck restart and recovery;
- clean reset between two workshop sessions.

Update the runbook with exact commands, expected successful output, recovery
actions, hard stop conditions, and a short release checklist. Do not fill it
with general advice.

### Tests and acceptance

Run every Just recipe changed or added. At minimum the final evidence must
include successful `just lint`, `just typecheck`, `just test`, production
build, `just test-e2e`, `just preflight`, and the 40-attendee rehearsal. Capture
the one remaining deprecation warning or eliminate it if it belongs to this
repository.

Inspect browser screenshots and console logs. A green HTTP or unit-test suite
does not prove the canvas rendered, media loaded, deck connected, or panels fit.
Check for blank canvas pixels, clipped text, overlapping panels, unhandled
promises, failed network calls, leaked polling after navigation, and orphaned
server processes.

### Documentation and final report

Update `README.md`, `Justfile` comments, architecture, local development, demo
plan, and a practical release/rehearsal runbook. Keep commands in one source of
truth and link to it rather than duplicating stale copies.

Create:

- `notes/ai/phase-36-release-readiness.md`
- `notes/hu/phase-36-release-readiness.md`

The handover must include the final module boundaries, transaction design,
async request policy, complete command matrix, E2E coverage, capability-token
flow, preflight output, load results, manual rehearsal evidence, remaining
warnings, and any external dependency that can still fail on workshop day.
The learning guide should ask why a repository committing inside `insert()`
cannot guarantee a move and its six dataset rows are atomic, and why a load
test that bypasses the browser does not measure presenter synchronization.

Finish with a release verdict: ready, conditionally ready, or not ready. Tie it
to concrete failed or passed acceptance evidence. Do not call the repository
ready merely because the automated suite is green.
