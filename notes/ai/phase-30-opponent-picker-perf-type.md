# Handover: phase 30, the opponent picker, the perf pass, and readable type

Written 2026-07-07, from Ramon's five-item feedback after playing on
his own machine with real keys.

## What was built

**The opponent wiring diagnosis.** His opponent "not working" was a
key/base-URL mismatch: an OpenRouter key against the default
api.openai.com returns 401, and the UI ate the error. Two fixes: the
docs now lead with "the key and the base URL travel together" plus a
complete OpenRouter recipe, and the UI now says what went wrong.
Model-move failures show `Model error: <the server's actual reason>`
in the notice line, assessment failures append their detail, and
llm_client wraps httpx transport errors (unreachable host, timeout)
into LlmRequestError so they surface as clean 502s instead of raw
500s. Verified live: a dead base URL now prints "Model error: could
not reach http://127.0.0.1:9: Connection refused" under the board.

**The opponent picker.** OPPONENT_MODELS (comma-separated env) adds
models to /llm/status; when more than one is on offer, Start game
grows a second select. The chosen model is validated against the
offer list (422 otherwise), stored on the games row
(opponent_model column, ALTER TABLE migration for live DBs), used by
model_move for that game's replies, carried across Start over, and
shown in the thinking line ("gemma-4-2b-it is thinking"). Analysis
stays on OPENAI_MODEL. The two-game demo beat (small Gemma, then
gpt-5.5, same board) is in demo-plan.

**The perf pass.** The board felt sticky because the countdown state
lived in WorkspacePanel: two renders per second through the whole
tree, CodeMirror included. The clock is now its own memoized
GameCountdown component (chess/GameCountdown.tsx) that re-renders
only itself; it calls onExpired once at zero and retries if the
server disagrees. MiniIde is memo()ed with a useCallback'd
onSelectSnippet, so the most expensive child skips every render that
is not a snippet switch. Panel re-renders now happen on real events
only.

**Readable type.** The workspace type scale moved up: panel base
13px to 15px, everything else +1px (12/13 for body and headers, 11px
floors). The board grew 280 to 340px, the CodeMirror font 12 to
13px. The workspace shape default grew from 1160x800 to 1240x900
(layout.ts constants moved with it), and ensureWorkspaceShape now
grows existing persisted shapes to the new minimum on sight, but
never shrinks one the user enlarged. The board section now fits its
board, clock, record, and history without scrolling at default zoom.

**Verifiers.** We are not using PrimeIntellect's verifiers library;
the RL environment here is hand-rolled (compute_reward plus python-
chess legality) so it fits on a slide. The reward_function snippet
and the notebook's training ladder now both point to verifiers as
the production-grade version of the same idea.

## Intentionally deferred, and why

- **No async llm_client**, same reasoning as phase 29: the threadpool
  answer holds at this scale.
- **Analysis does not use the per-game opponent model.** Commentary
  quality should not degrade when you demo the weak opponent;
  OPENAI_MODEL stays the commentator.
- **No react-window or deeper memoization.** The countdown isolation
  plus MiniIde memo removed the periodic re-renders; the rest are
  event-driven and cheap.

## Known issues / tech debt

- Existing workspace shapes placed by the old 1160x800 grid keep old
  positions; grown to 1240x900 they may sit closer than the new
  gutter intends (old row pitch 880 vs new height 900 leaves -20px
  vertical overlap for pre-existing multi-row grids). A reset-db
  relayouts everything with the new constants; Ramon's authoring
  canvas has one workspace per page and is unaffected.
- The exact OpenRouter id for small Gemma is unverified from this
  container; the docs say to check their registry. Nothing in code
  hardcodes it.
- Zoom inside an opened workspace: plain wheel scrolls the panel
  (canScroll), so canvas zoom needs ctrl/cmd+wheel or pinch, which
  tldraw still routes to the camera. The bigger type mostly removes
  the need.

## What the next phase should tackle first

1. Ramon's real-keys rehearsal, now with the exact env block from
   local-dev.md. The error surfacing will name any remaining
   misconfiguration on the board itself.
2. Confirm the small-Gemma OpenRouter id and put the verified id in
   local-dev.md.

## Gotchas

- GameCountdown keys its deadline effect on game.id: status refetches
  return new objects for the same game and must not restart the
  clock. Same reasoning as the old in-panel effect, now enforced by
  the component boundary.
- The onExpired contract returns a boolean: false means "the server
  says not yet, keep ticking". Losing that return value reintroduces
  the frozen-at-0:00 clock-skew bug.
- memo(MiniIde) only works because onSelectSnippet is useCallback'd
  on [workspaceId]. Add a dependency to that callback and every
  render recreates it, silently turning the memo off.
- pydantic extra="ignore" again: GameOut gained opponent_model by
  adding the field; dict(row) already carried it.
