# Phase 35, for the human: deck identity and copy

Status first, because it matters for how you read this: phase 34
integration is pending. This phase ran in parallel with phase 34 under
the two-stage rule, so what exists on this branch is the deck
foundation. The repository-wide copy pass, the banter removal in
`web/`, and the reconciliation with phase 34's session and demo plans
all wait until 34 merges. The deck itself, though, is rebuilt end to
end.

## What actually changed

The old deck was a dark Seriph theme with glassy slate cards, an amber
accent, and components that animated themselves on a schedule. It read
like a competent conference deck from a template. The new deck is
paper and ink. Off-white ground, near-black text, IBM Plex Sans and
Mono served from files inside the repo, one blue accent used the way
an arbiter uses a pen, and square corners everywhere. The visual
ancestor is a chess scoresheet, not a chessboard. No slide is dressed
up as a board; the board shows up only when an actual position is
under discussion.

Why a scoresheet and not a board? Think about what the deck has to
display for ninety minutes: notation, code, tables of metrics,
before/after comparisons. That is what the printed side of chess has
been solving for a century with black ink, thin rules, and one pen
color. A board theme would decorate; a scoresheet system organizes.

## A question before you read the code

The old DatasetShapes component cycled through six dataset encodings
on a 3.2 second timer. The new one steps on presenter clicks. Before
you accept that as obviously right, ask: what exactly was wrong with
the timer? The animation was identical. The content was identical.
The difference is who owns the clock. With a timer, the component
decides when the audience compares shape three to shape four, and if
you are still talking about shape three, tough. An automatic
three-second transition is a teaching decision made by a `setInterval`
instead of the teacher. That is the entire motion philosophy of this
phase in one component.

Follow-up question: why do the components not own their click state
either? Look at `deck/lib/clicks.ts`. Every stepper derives its frame
from a `clicks` number the slide hands it, through a pure function.
What would break if `DatasetShapes` kept an internal counter and
incremented it on a button? Walk backward through the deck in
presenter mode and you will have the answer: internal state does not
rewind. A pure mapping from click count to visible state means slide
navigation is the single source of truth, forward and backward land on
identical frames, and a bun test can drive every state without
mounting a component. The repo's architecture rule about calculations
living apart from rendering is not ceremony; it is what made these
components testable at all.

## The shared system versus identical components

The design doc defines one surface treatment, one accent, two semantic
colors, and fixed geometry rules. Yet DatasetShapes has a rail and a
panel, DataUniverse is an SVG of circles, CostAtTarget is a table, and
NotationMorph is a board with a stepper. Why does a shared design
system not force every component into one shape? Because the system
constrains the vocabulary, not the sentence. Tokens, type, spacing,
and reveal behavior are shared; the structure of each component
follows its concept. Six encodings of one move want a stepper. Five
nested data boundaries want circles. Four modality costs want rows.
When every component looks the same, the design system is doing the
thinking that the content should be doing.

The test for whether a component deserved to exist at all was: does it
show real workshop data or a precise transformation? ChessBoard
renders actual FEN strings through a parser in `lib/chess.ts`, and the
tests caught two real bugs there, an inverted light-square parity and
a FEN I had hand-built with the bishop already on b5 in the position
that was supposed to show it still on f1. Hand-authored chess data is
exactly as error-prone as any other hand-authored data, which is the
same lesson the workshop teaches about datasets.

## What the tone pass did and did not touch

The banned list is short and honest: em dashes, emoji, and a dozen
stock phrases that had already crept into the copy, "pocket money",
"not vibes", "all yours to keep", "pawns dream". The check lives in
`lib/copyRules.ts` and runs over deck-owned files as a bun test. It
does not pretend a regex can hear tone. It catches the punctuation and
the phrases that a tired writer pastes back in at midnight; the rest
stays editorial.

Notice what survived: the dog-thinking meme, "what could possibly go
wrong", "Cool bruh" with the cookie GIF, goth Minions, the corporate
lamp paragraph. Those are not banter. They are delivery beats Ramon
placed deliberately, and PLAN_V2 protects them by name. The
distinction the tone pass draws is between a joke the speaker performs
on purpose and a pun the interface makes at you. The first commands a
room. The second is a component wearing a novelty tie.

One more question worth sitting with: the copy check exempts the
chess glyph Unicode block from its emoji detection. Why is that not a
loophole? Look at what the deck renders boards with, then look at
which Unicode blocks the emoji regex covers. The answer says something
about why allowlists should be narrow and specific rather than
clever.

## Placeholders as a contract

Around thirty assets are Ramon's to supply: photos, screenshots, the
TUI recording, memes, generated pairs. Every one renders through
`MediaFrame`, which shows the expected file name, the expected
content, and the final aspect ratio, and swaps to the real asset the
moment the file lands in `deck/public/assets/`. No geometry shifts. A
test cross-checks every referenced file against the inventory table in
`docs/deck-plan.md`, so the inventory cannot silently drift from the
slides. Nothing was generated or scraped to make slides look finished,
because a placeholder that states its contract is more useful than a
stock image that lies.

## What waits for phase 34

The banter pools in `web/src/lib/gameBanter.ts`, including "rooks
before feelings" and "GPU sulking", are phase 34 territory until it
merges. So are the session and demo plans, the licenses file, and
every measured number in the OutcomeCompare and CostAtTarget fixtures.
The handover lists all of it. Until then, treat this branch as a
finished deck skeleton with its evidence still in transit.
