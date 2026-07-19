# Phase 1 prompt: room correctness

Use this prompt for the first implementation branch.

## Prompt

You are implementing phase 32 of `euro-scipy-chess-studio`: make the shared
workshop room correct before adding more teaching or visual polish.

This is a 90-minute EuroSciPy 2026 workshop hosted from the presenter's
laptop. Around 40 attendees may join over a local network. The current app
looks collaborative but has four correctness failures:

1. Every browser writes a complete tldraw snapshot. Concurrent clients can
   overwrite each other's shapes or the presenter's authored content.
2. "Bring everyone to presenter view" broadcasts only a page slug and calls
   `zoomToFit`. It does not send the presenter's frame or camera, and late
   joiners do not receive the current view.
3. The Slidev LiveRoom calls `localhost:8000` from origin `3030`, which the
   backend rejects. Attendee deck iframes also point at their own
   `localhost:3030`.
4. Canvas seeding is not a migration system. Existing pages miss newly added
   deck or modality shapes because those shapes are created only when a page
   is empty.

Treat these as release blockers. Do not hide them with optimistic status copy.

### Branch and worktree rules

- Read `AGENTS.md`, the final tone section of `CLAUDE.md`,
  `docs/architecture.md`, `docs/session-plan.md`, `docs/demo-plan.md`, and the
  latest relevant handover notes before editing.
- Inspect `git status` first. Preserve all changes you did not make.
- Create and work on `phase-32-room-correctness`. If the tree is not clean or
  contains work you did not create, stop and ask. Do not stash, resolve,
  restore, commit, or delete someone else's work.
- Commit coherent, tested increments throughout the phase. Push the phase
  branch, finish with no relevant untracked or uncommitted files, and do not
  merge it into `main`. Ramon reviews the summary and diff first.
- Do not read or change anything under `notebooks/` or
  `web/public/notebooks/`. The notebook is now a standalone Jupyter asset. Do
  not add or restore a notebook iframe or make a notebook panel part of canvas
  acceptance. An existing legacy panel may remain unless it produces a broken
  user-facing surface; document that decision without changing notebook files.
- Do not perform deck visual redesign or broad copy work in this phase.

### 1. Make shared canvas state safe

Start by documenting the concurrency model you will implement. Inspect the
current tldraw version and its supported sync packages before choosing a
design. Prefer a proven local-first tldraw synchronization mechanism if it can
run entirely on the workshop host and preserve the backend's ownership of
durable state. Do not invent a partial CRDT.

If the supported sync stack cannot fit this repository, implement the smallest
server-owned record or operation model that satisfies the behavior below.
ETags and `409` responses alone are not sufficient if a normal collision still
loses an attendee's work. Full-document last-write-wins is not an acceptable
result.

Required behavior:

- Two browsers can create or edit different attendee-owned shapes
  concurrently and both results remain after reload.
- Presenter-authored pages, frames, notes, deck panels, and modality panels
  cannot be removed or structurally changed by a normal attendee client.
- An attendee can edit only the canvas material the workshop intentionally
  gives them, including their own workspace and drawings. Ownership rules
  must be explicit rather than inferred from colors or labels.
- Reconnect and reload recover the durable room state without replacing it
  with a stale local snapshot.
- Save and connection status distinguish connected, synchronizing, saved,
  stale, conflicted, and offline states where those states can occur. Keep the
  copy short.
- Assets still persist through the backend and remain usable by synchronized
  shapes.
- `just reset-db` and `just reset-canvas` retain their documented separation.

Keep synchronization I/O in a data boundary and orchestration in actions. Do
not put protocol logic inside `ChessStudioCanvas`.

### 2. Synchronize the presenter target, not merely the page

Extend presenter state with an explicit navigation target. A selected frame or
stable camera bounds plus page and monotonically increasing revision are both
reasonable designs. Choose one based on tldraw's public APIs and document why.

Required behavior:

- "Bring everyone" moves joined attendees to the exact frame or useful camera
  region the presenter is showing.
- Prev/Next presentation controls update the shared target when presenter mode
  is active.
- A participant who joins late receives the current presenter target after
  joining. The first poll must not discard it.
- "Send users to workspace" reliably releases remote camera control and moves
  each attendee to their own workspace.
- Presenter clients do not fight their own camera updates.
- Repeated polls with the same revision do nothing. Slow or overlapping polls
  cannot apply an older target after a newer one.
- Missing or deleted frames degrade to a safe page view and a concise error,
  not a blank canvas.

Do not encode presentation geometry in React components. Put target
calculation and state-transition logic in calculations/actions and test it
without a browser where possible.

### 3. Give the deck one valid network path

Remove hardcoded browser-facing localhost assumptions. Prefer same-origin
proxying or one documented runtime configuration used by both Vite apps.

Required behavior:

- The Slidev LiveRoom reaches the running FastAPI backend from port 3030.
- The embedded deck resolves to the presenter host when viewed by an attendee,
  or is deliberately presenter-only and is not rendered as a broken attendee
  iframe.
- Main app and deck development servers bind in a way suitable for a LAN while
  retaining convenient local URLs.
- CORS permits only the documented workshop origins. Do not replace the
  current list with `*`.
- Connected, unavailable, and recovering LiveRoom states can be exercised in
  tests.
- Runtime URLs and network setup are documented in `docs/local-dev.md` and
  `docs/demo-plan.md`.

### 4. Add versioned, idempotent canvas migrations

Replace "seed only when empty" with an explicit canvas schema version and
ordered migrations. Migrations must preserve authored content and attendee
work while ensuring required pages and integration shapes exist.

At minimum, cover pages, deck shape, modality panel shapes, shape defaults that
have changed, and future unknown shape types. The standalone Jupyter notebook
is not a required canvas shape. Running migrations twice must produce the same
document. A failed migration must not overwrite the last valid snapshot.

Test an old but non-empty snapshot that lacks the deck or modality shapes, then
prove the required shapes appear without moving or deleting existing content.

### Tests and acceptance

Add focused unit and integration coverage plus real browser coverage. At
minimum demonstrate:

1. Two browser contexts join as different users, edit concurrently, reload,
   and see both edits.
2. A normal attendee cannot mutate protected authored structure or another
   attendee's workspace.
3. Presenter frame navigation moves an existing attendee and a late joiner to
   the same target.
4. Send-to-workspace returns both attendees to their own workspaces.
5. Deck LiveRoom shows connected when the backend is running and an accurate
   unavailable state when it is not.
6. An old snapshot migrates once and remains stable on a second load.

Run `just lint`, `just typecheck`, `just test`, and the relevant E2E suite. If
the known hardcoded Chromium path blocks E2E, make the smallest portable
configuration correction needed to execute these tests and record that change
for phase 36, where the complete release command surface will be addressed.
Also test at least one desktop projector-sized viewport and one narrow laptop
viewport for panel overlap after remote navigation.

### Documentation and final report

Update architecture and local-development documentation to describe the system
that actually exists, including its concurrency, persistence, ownership, URL,
and recovery behavior. Remove claims that are no longer accurate.

Create:

- `notes/ai/phase-32-room-correctness.md`
- `notes/hu/phase-32-room-correctness.md`

The handover must include the chosen synchronization design, rejected options,
data migration concerns, protocol/version compatibility, tests run, and any
remaining capacity limit. The learning guide must follow the repository's
40 percent Socratic and 60 percent walkthrough convention.

Finish with a concise summary of behavior changed, files changed, checks run,
manual multi-client evidence, and deferred work. Do not claim the phase is
complete unless the concurrent-client and presenter-camera acceptance cases
have actually passed.
