# Learning guide: phase 32, room correctness

The app looked collaborative the way a movie set looks like a town.
Forty browsers each uploading a complete snapshot of the same document
is not collaboration, it is forty people taking turns overwriting the
whiteboard and hoping nobody notices. This phase made the room real.
Four problems, four fixes, and a running theme: stop trusting whoever
wrote last.

## Why snapshots had to die

Start by convincing yourself the old design was broken, because the
failure is subtle enough that it survived thirty-one phases. Every
client held the full document, and every edit scheduled a debounced
PUT of everything. Walk through two attendees, Ada and Grace, drawing
at the same time. Ada's PUT lands at t=1. Grace's store still holds
the document from t=0, plus her own new note. Her PUT lands at t=2.
What happened to Ada's note? Gone, and nobody got an error, because
nothing went wrong at the HTTP level. Every request succeeded. That is
the sinister part: the system was lying politely.

Question one, and think about it before reading on: would ETags have
fixed this? The server rejects Grace's PUT because her base version is
stale, she refetches, retries, and... her retry contains the refetched
document merged with what, exactly? Her whole local store. Merging two
full documents needs to know which record changed on which side, which
is exactly the bookkeeping a snapshot doesn't have. A 409 turns silent
data loss into a retry loop that loses the same data with more steps.
That is why the phase prompt banned it explicitly.

The fix is to stop shipping documents and start shipping changes.
tldraw publishes its own sync engine, the one behind tldraw.com
multiplayer: a client pushes record-level diffs, the server orders
them, everyone else pulls and rebases. We host it in a very small Bun
process, `web/sync-server/index.ts`, around one `TLSocketRoom`. Read
that file first; it is under a hundred lines and every line is either
an HTTP route, a WebSocket handler, or a shutdown hook. The room does
the hard part, and the hard part is exactly the thing you should never
write yourself. The prompt called this "do not invent a partial CRDT"
and it was right to.

Now the architectural question worth chewing on: the backend was
supposed to own durable state, and suddenly there is a second server
holding the document in memory. Why is this not a violation? Look at
`web/sync-server/persistence.ts`. The room loads from GET /canvas and
persists to PUT /canvas. It never touches the filesystem. The Bun
process owns the *live* document the way RAM owns your unsaved
spreadsheet; the file on disk, its rolling backup, reset-canvas, git
history, all still flow through FastAPI. If the sync server dies, the
last debounced write is on disk where it always was. Ask yourself what
would have happened if we had given the room its own SQLite instead:
two sources of truth, and the reviewed phase after this one would have
been "which database is lying."

One consequence deserves a pause: `just reset-canvas` now requires the
stack to be stopped. Why? The room holds the document in memory and
persists on change. Delete the file while the room runs and the next
debounced save resurrects everything. This is not a bug, it is what
"the room owns the live document" means. The Justfile comment and the
docs both say so, because a mid-workshop presenter will not deduce it
under pressure.

## Ownership, written down instead of implied

The old protection model was a CSS class. Someone else's workspace
rendered read-only, which stops exactly the people who were not going
to break anything anyway. The review demanded rules that are explicit
rather than inferred from colors, and the implementation is two small
files worth reading in order.

First `web/src/calculations/canvasOwnership.ts`. Every page and shape
carries `meta.owner`. The presenter owns structure; an attendee owns
their workspace shape and what they draw; a record with no owner
belongs to the presenter. Why default to presenter rather than
"unowned means anyone may edit"? Because the only records without
owners are the ones authored before ownership existed, and those are
precisely the slides the workshop cannot afford to lose. A protective
default fails closed.

Second `web/src/actions/registerCanvasPermissions.ts`. tldraw's store
side effects let you intercept mutations before they commit: return
the previous record to block a change, return false to block a
delete, remove a disallowed create inside the same transaction. The
crucial subtlety is the `source` argument. Every handler ignores
anything that is not `"user"`. Sit with that: what would happen if an
attendee's client also enforced rules on `"remote"` records? Ada's
client would receive the presenter's legitimate edit, decide the
presenter shape is not Ada's to change, and revert it, pushing the
revert back through sync. Two clients with different opinions about
the same record, politely correcting each other forever. Enforce your
own hands, trust the server's stream.

And the honest boundary, stated in the docs rather than hidden: there
is no auth. A hand-rolled WebSocket client can ignore all of this. The
server refuses writes from sessions that never identified a user,
which keeps drive-by watchers read-only, but per-shape enforcement is
client-side. For a conference room of scipy people, that is the right
trade, and saying so out loud beats pretending otherwise.

## The presenter target, or: what is a revision for

The old "bring everyone" sent a page slug. Attendees ran zoomToFit on
a page that is thousands of units wide. The presenter would be talking
about slide four while forty screens showed a satellite photo of the
whole canvas. And a late joiner received nothing at all, because the
first poll deliberately recorded the state without applying it, on the
theory that yanking a fresh client was rude. The theory had it exactly
backwards: the fresh client is the one that most needs to know where
the room is.

The new state is page plus optional frame plus the camera bounds the
presenter was actually looking at, plus a revision the backend bumps
inside the UPDATE statement itself. Look at
`update_presenter_state` in the repo layer: `revision = revision + 1`
lives in the same SQL statement as the rest of the update. Why there,
and not read-increment-write in Python? Two concurrent updates would
both read 7, both write 8, and the revision would stop being an
ordering. SQLite serializes the two UPDATEs, so each one increments
what the other wrote. The monotonic counter costs one SQL expression.

Now the client. `shouldApplyPresenterState` in
`calculations/presenterTarget.ts` is four lines and carries the whole
correctness argument: first completed poll applies whenever the room
is in a driven mode (that is the late joiner fix), afterwards only
strictly greater revisions apply. Work through what each rule kills.
Same revision twice: repeated polls do nothing, nobody's camera
twitches every three seconds. Older revision after newer: a slow
response that left the server before your last apply cannot roll you
back. What does the presenter's own client do with all this? It
applies the lock and nothing else; driving the presenter's camera with
their own broadcast is how you get a feedback loop with a projector
attached.

Degradation is a pure function too. Frame exists: zoom to its current
bounds, so a frame the presenter nudged still resolves correctly.
Frame gone: fall back to the bounds captured at click time. Those gone
too: page fit plus a one-line notice. Page gone: stay put and say so.
The test file walks every branch without a browser, which is the
payoff of keeping geometry out of React components.

## The deck stops calling itself

The Slidev deck ran on port 3030 and its LiveRoom component fetched
localhost:8000 directly. Two failures in one line: the backend's CORS
list rejected the 3030 origin, and "localhost" is the wrong machine
for every attendee in the room. The pattern that fixes both is the
same one the main app already used: proxy, and speak only to your own
origin. `deck/vite.config.ts` gives Slidev an /api proxy and binds the
LAN; LiveRoom's default apiBase becomes `/api`. Question: why does
this make the CORS problem vanish rather than merely move? Because the
browser now requests its own origin, and the proxy's request to
FastAPI is server-to-server, where CORS does not exist. The CORS list
stays four documented localhost origins, not a wildcard, and LAN
attendees never appear in it because they never talk to 8000 directly.

The embedded deck panel had the mirror problem: one synced shape, one
stored URL, and localhost:3030 means "my machine" on forty different
machines. `resolveDeckUrl` rewrites a localhost deck URL to whatever
hostname the app itself was loaded from, at render time, leaving the
stored prop alone. Why not migrate the stored URL instead? Because the
presenter, on their own machine, wants localhost, and every attendee
wants something different. There is no single correct stored value, so
the correction belongs at the point where each browser knows who it
is.

LiveRoom's connection handling also grew a fourth state, and it is
worth asking why "recovering" is not just "unavailable". The panel had
data, the backend blipped, retries are running. Blanking the list
would tell the room "everything is gone"; keeping stale numbers with a
terse note tells the truth. The four-phase machine lives in
`deck/lib/liveRoom.ts` as a pure reducer, six tests, no Vue involved.

## Migrations instead of hope

Seeding only ran on empty pages, so a canvas authored in phase 20
never grew the deck panel added in phase 31. The replacement is
boring, versioned, and ordered, which is the highest compliment
migration code can receive. The document records its workshop version
in the document record's meta; `migrateCanvasDocument` clones the
input, applies every step above the recorded version, stamps the new
version, and returns. Run it twice, get the same document. Throw
mid-migration, and the caller still holds the untouched original,
which the sync server translates into "refuse to open the room, exit
nonzero, leave the file alone."

Two design questions worth answering for yourself. First: why do the
migrations run on the sync server rather than in each client, where
the seeding used to live? Count the writers. Forty clients racing to
create the same deck panel with the same deterministic id mostly
works, which is the worst kind of works. One writer, before any client
connects, needs no coordination at all. Second: why do the record
builders in `canvasRecords.ts` spell out every default prop of a note
shape, thirteen fields of it? Because there is no Editor on the server
to fill defaults, and the store validators reject partial records. The
tests push every built record through the real tldraw validators, so
the thirteen fields are checked, not hoped about.

The migration pipeline also carries the phase's oddest artifact: a
schema *down*-step. The offline dev environment pins tldraw at 5.1.1,
and the authored snapshot was saved by 5.2.2, which is one version
ahead in exactly three sequences. The pre-step renames one note field
back (upstream's own down migration, verbatim), clamps two sequences
that only matter for shapes the snapshot does not contain, and throws
on anything else from the future. It is narrow on purpose. A general
"downgrade whatever we find" function is how authored content gets
quietly mangled; a function that handles three known cases and
refuses the rest is how it does not.

## What the tests actually prove

The unit suites cover the pure logic, but the phase's acceptance lives
in `web/e2e/room.spec.ts`, which drives two and three real Chromium
contexts against one room. Concurrent notes from two attendees survive
both browsers reloading. An attendee attacking the deck panel, a page,
and a peer's note changes nothing anywhere, while their own note stays
editable. Bring-everyone plus Next lands an existing attendee and a
late joiner on the same camera region, and send-to-workspace returns
both to their own boards. The suite reads document state through a
window hook on the live editor rather than squinting at pixels, which
is why the assertions are exact.

One last question to carry into phase 33: the status badge now says
"Room: live" instead of "Canvas: saved", and the docs claim stale and
conflicted states cannot occur. That claim rests on the rebase model.
What would have to change in the architecture for those words to
become false again? Keep the answer somewhere handy, because the next
person who adds a cache between the client and the room will need to
hear it.
