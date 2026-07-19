# Phase 33: truthful evaluation and data

This phase is about a boring virtue: the numbers on screen now mean
what they say. Before it, valid_json_rate parsed JSON the app itself
had serialized, which is like grading your own handwriting by
photocopying the textbook. The legal move rate blended your moves with
the model's, the "move class" was a UCI string wearing an integer's
name tag, and the scenario mapping evaporated on reload. All fixed.
The interesting part is how, because every fix is the same move
performed in a different place: separate the evidence from the
conclusion, store the evidence, and compute the conclusion from it in
front of witnesses.

## Why raw attempts and applied moves are different records

Start with the question that shaped the schema. The moves table
records what happened to the board. When the model replies "I would
castle early and keep the tension," nothing happened to the board.
Where does that reply go?

Before you read the answer, work out what breaks if you force it into
the moves table anyway, the way the old code recorded illegal model
replies as reward -1 moves. What is the fen_after of a move that never
moved? What ply does prose occupy? And when you later compute a legal
move rate over that table, whose failure are you measuring, the model
that suggested nonsense or the participant who fat-fingered a knight?
Sit with that last one, because it was a real bug: one denominator,
two populations, one number that described neither.

The answer is a second table, model_attempts, and it is immutable on
purpose. One row per raw reply, or per failure to get a reply at all:
the model, the provider alias, the prompt version, the position asked
about, the attempt number, the raw text, and how far it got through
judgment, parsed, syntactically valid, legal, applied. The moves table
stays what it always was, a log of things that changed the board, and
it gained an actor column so you can finally ask "whose move was
this" without inferring it from whose turn it probably was.

Here is a question worth arguing with yourself about. Old databases
have moves with no actor. The migration labels them unknown rather
than guessing white-means-participant. Why not guess? The heuristic
would be right nearly always. The reason is what the guess would do to
the metric: a wrong guess does not show up as an error, it shows up as
a slightly wrong number that looks exactly like a right number. A row
labelled unknown is excluded from every per-actor denominator, and the
metric's scope says so. Honest and slightly smaller beats confident
and contaminated.

## The state machine, or what to do when the model keeps being wrong

The old model_move was optimistic: ask once, parse, apply, and if
anything failed, throw. The board sat on black's turn until a human
noticed. The new actions/model_turn.py is a loop with a written
constitution. Each attempt is recorded before anything else is
decided: transport_failed, empty, parse_failed, invalid_move_syntax,
illegal, or applied. Failed attempts commit immediately, in their own
transactions, and this is worth pausing on. Why commit a failure
before you know how the turn ends?

Because the failure is evidence, and the eval counts evidence. If the
turn's final state rolled back everything, a model that failed twice
and then got rescued would leave no trace of failing. The workshop's
whole pitch is that you can inspect the path from behavior to data;
a rollback there would be the system quietly forgiving its model.

Two attempts is the default budget. Then the road forks, and the fork
encodes a judgment about fault. If the model answered at least once,
however badly, the environment plays the first legal move in UCI sort
order, recorded under actor fallback with a note saying why. The game
continues, and because metrics filter by actor, the fallback's
competence is never billed to the model. But if every attempt died in
transport, no move is invented, because inventing a move to cover for
an unreachable provider would be fiction. The turn returns
unavailable, the UI says so in plain words, and a retry button waits.
Ask yourself which of these two cases you would have merged if you
were in a hurry, and what the merged version would have lied about.

The fallback choice itself is a small honesty exercise. Sorted-first
legal move: a2a3, the least ambitious move in chess. Why not a random
legal move? Because random is unfalsifiable in a demo. When the
notice says "Fallback played a7a5 (first legal move in UCI order)"
anyone in the room can check it. Determinism is the difference
between an explanation and an alibi.

## Metrics that carry their own receipts

calculations/evals.py now returns a MetricResult instead of a float.
Value, numerator, denominator, unit, direction, a definition sentence,
a version, and the scope filters that produced the sample. The eval
panel shows 0/4 next to 0.0, and that fraction is doing more teaching
than the decimal is.

The definitions are worth reading slowly, because each one is a
decision about the denominator. model_legal_move_rate counts replies
received; a transport failure is not the model's answer, so it does
not lower the model's score. valid_json_rate counts replies where JSON
was requested, and parses the stored raw text with the exact extractor
the app uses to consume replies. Same parser for consumption and for
grading, so the metric cannot drift away from reality. And an empty
sample returns unavailable, never zero, never 1.0. What would a zero
over an empty sample claim? That the model failed at everything it was
never asked to do. What would 1.0 claim? Worse.

One boundary case deserves your suspicion: a reply that parsed to a
legal move but never got applied because a later attempt won the
race, or because the clock fell in between. The metric counts it as
legal anyway. Why is that right? Because the metric measures the
model's ability to produce legal moves, not the environment's
willingness to accept them. The moment you let application status leak
into a competence metric, you are grading the referee.

## Datasets that stopped pretending

board_tensor_to_move_class used to ship a UCI string in a field named
like an integer, while the deck showed a made-up 796. Now
calculations/move_vocab.py defines the vocabulary: from_square times
320, plus to_square times 5, plus a promotion code. Size 20480, most
of it unreachable, all of it invertible, and the deck's example is
3980, which really is e2e4. Wasteful? Sure, AlphaZero packs the same
idea into 8x8x73 planes. But an attendee can invert 3980 in their
head, and a vocabulary you can invert in your head is worth three
clever ones in a workshop.

policy_value_to_move had the more subtle problem. It shipped a
value_target of reward over ten, which meant every ordinary legal
move whispered "this position is slightly good." That is not a
position value, that is a participation trophy. The row is now
policy_move_reward: the one-hot policy is labelled as the move
actually played, and move_reward is named for what it is, an
immediate shaped reward. The note in the row says what a real value
target would need, the final outcome or an engine, and that neither
is invented here. Question to chew on: the row works for unfinished
games precisely because nothing in it waits for the result. What
would you have to add to the system the moment you wanted
outcome-based values, and where would the label "backfilled at game
end" have to appear so nobody mistakes it for something known at move
time?

## Scenarios that survive a refresh

The three-field mapping, assessment, real_world, video_prompt, is one
of the workshop's distinctive datasets, and it lived in component
state. Refresh, gone. It now has a table with a design rule you have
seen twice already in this document: the raw suggestion is written
once and never updated, and participant review lands in separate
final columns. Accept copies, edit replaces, and either way the
model's original stays inspectable. The export carries both, with
approved null until a human touched it, so the presenter can tell
vetted examples from raw model output at a glance. Even a failed call
gets a row, status failed with its reason, inserted next to the
history rather than over it. Recovery is asking again, not repairing
state.

Notice what the transport had to provide for this to work: the raw
reply, the model, the provider alias, the request ids. That is why
ChatOutcome exists. The old client returned a string, and a string
cannot testify.

## The transport, briefly

One client, two typed profiles, opponent and video_prompt, so local
Gemma plays chess while hosted Luna writes film direction in the same
process, and a test proves neither borrows the other's endpoint,
model, or capabilities. Capability knowledge sits in a catalog,
model_catalog.py, instead of scattered if-statements: Luna gets
reasoning_effort, llama.cpp does not, unknown models get the cautious
default. A 400 triggers a retry-without-field exactly when the error
message names the field, once, and the fallback is recorded in
provenance. Every other 400 is your bug and fails loudly.

The 401 story got stricter, and the reason is a nice case study in
not generalizing from one good day. During key propagation, one
specific generic message flipped from 401 to 200 on retry. The old
code retried that message unconditionally. The new code demands
evidence: either this exact credential already succeeded in this
process, or the operator explicitly set the recent-key flag because
they just rotated the key. Same observed exception, preserved; the
temptation to treat every 401 as weather, resisted. If you rotate the
workshop key the morning of, set OPENAI_RECENT_KEY_401_RETRY=1 and
delete it after.

## Where the commits went

Repositories on the game path no longer commit; actions do. make_move
is one transaction: move row, board update, six dataset rows, maybe a
game outcome, all or nothing, verified by a test that opens a second
connection and looks for leaks. Why a second connection? Because on
the same connection, uncommitted writes are visible to you, and a
test that only asks you cannot tell a transaction from wishful
thinking. The one deliberate exception is the clock: expire_if_over
commits its timeout loss on its own, because the flag fell whether or
not the action that noticed it goes on to succeed. Time does not
participate in your transaction.

If you change this area, copy the second-connection test pattern.
sqlite3 will not warn you when a repo function quietly grows a commit
and turns your atomic action back into three independent hopes.
