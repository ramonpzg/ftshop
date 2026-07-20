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

## The review round: what a second reader caught

Ramon reviewed the branch and found nine real bugs. None of them were
typos. All of them were the same shape of mistake: a piece of state
was read once, trusted for the rest of a function, and the function
never asked itself "is this still true by the time I act on it?" That
question is the whole discipline of concurrent and time-sensitive
code, and it is very easy to forget to ask because the happy path
never needs it.

Take the worst one. `model_turn` reads the board, asks the model, and
applies the reply. Between "ask" and "apply" sits a network round
trip, which on a bad day is sixty seconds. Anything could happen to
the board in that window: another request racing in, a fresh game
starting, a resignation. The bug was applying the reply anyway,
trusting that the board the model saw was still the board that
existed. Here is the question worth sitting with before you read the
fix: what test would catch this, given that in a single-threaded test
process nothing genuinely races? You cannot wait for a real race to
happen by accident. You have to manufacture one on purpose, which the
fix does by having the model's own stubbed reply, mid-flight, go
start and finish a second `model_turn` call before returning. That is
a race you can write down and run every time, not one you hope shows
up in CI.

The fix itself is a pattern worth keeping: an optimistic precondition.
Before you act on a decision made from a snapshot, you check whether
the snapshot still matches reality, atomically, right before writing.
If it doesn't, you refuse and say so, rather than writing anyway and
hoping the mismatch doesn't matter. Notice what this is not: it is not
a lock. Nothing blocked the second request from running. The board was
free to change; the guarantee is only that a decision from a stale
snapshot cannot land unnoticed. That is a cheaper, weaker, and in this
case sufficient promise, and weaker-but-sufficient is usually the
right trade in a system with one SQLite file and forty attendees, not
a distributed database.

The clock-expiry bug is the same shape wearing a different coat. A
model reply arrives, genuinely legal, genuinely on time by the model's
own reckoning -- and then the code that applies it discovers the
clock ran out a moment ago. The old code let that discovery destroy
the evidence: the exception fired before anything was written, so a
possibly-correct answer left no trace at all. Ask yourself: why does
that matter, given the game is over either way and the move was never
going to count? It matters because the workshop's entire premise is
that you can inspect what the model actually did. "The clock happened
to run out one HTTP round-trip before we recorded anything" is an
implementation detail of a Bun process, not a fact about the model's
competence, and letting an implementation detail erase data is
exactly the kind of small dishonesty this whole phase exists to
remove. The fix records the attempt before the exception is allowed to
propagate. The order of operations -- evidence first, consequence
second -- is the lesson, and it recurs: failed attempts in general
commit before the turn resolves, for the identical reason.

The eval-result scoping bug rewards a slower kind of attention. Nothing
crashed. Nothing raced. `replace_eval_result` just deleted and
reinserted using an identity that didn't include which model the
number was about, so scoring model A and then model B produced two
computations and one row. The visible symptom -- a plausible-looking
number sitting on screen -- is more dangerous than a crash, because
nothing tells you to go looking. This is why the review asked
specifically "can a base and an adapted model's results coexist,"
rather than "does it crash": the failure mode you should worry about
in a metrics system is never the loud one.

One quieter finding is worth naming because it will recur in your own
code long after this workshop: `accept()` on a failed API call did
`.catch(() => scenario)`, silently returning to where it started as if
the click had never happened. A catch clause that swallows an error
without doing anything observable is not error handling, it's error
disposal. If you cannot articulate what the user sees when this branch
runs, that is the signal to stop and add it, not to ship the catch
and move on.

## The second review: bugs that survived the first fix

Ramon reviewed the branch again after the nine fixes above, and found
seven more. Three of them are the uncomfortable kind: a fix from the
first round that looked complete, checked the right thing, and was
still wrong. Sit with that for a second before reading on, because it
is the actual lesson of this section. A review that only asks "did you
fix the bug I reported" will wave all three through. A review that
asks "does the fix actually hold" will not.

Start with the atomic-move fix, because it is the sharpest version of
the lesson. Round one added `MovePrecondition`: before applying a
reply, check whether the board still matches the position the model
saw. That is correct. The bug survived anyway, because the check ran
*before* the write lock, not inside it. Here is the question worth
answering yourself before the explanation: if the check is correct and
the write is correct, how can putting them in the wrong order still
produce two duplicate moves? The answer is that "correct" and
"correct" do not compose into "correct together" for free -- between
your check passing and your write landing, the whole point of a race
is that something else gets to run. SQLite's default transaction mode
(`BEGIN DEFERRED`) does not actually take a lock until the first write
statement executes, so a `SELECT` that runs first, even one written
with every intention of being a precondition check, is reading
unprotected state. Two connections can both read "the board matches,"
both feel satisfied, and both write. `BEGIN IMMEDIATE` takes the write
lock up front, before any of the rereads happen, so the second
connection simply cannot get a look at the board until the first one
finishes and commits or rolls back. The fix is not "add a check." The
fix is "make sure nothing can happen between the check and the write."
Those are different claims, and only the second one is actually a
guarantee. Proving it needed two real `sqlite3.connect` handles and a
`threading.Barrier`, not one connection calling itself twice -- a
single connection cannot race itself, because SQLite already
serializes writes on one connection by construction. If your
reproduction can't be raced, it isn't testing the race.

The frozen-input-set bug is a different flavor of the same disease:
looks fixed, isn't, but this time nothing needs two threads to see it.
Round one gave every metric a `sample_ids` field -- the exact row ids
a number was computed from. That reads like an audit trail, and it is
one. It is not, and never could be, proof that two models were
measured on the same positions. Ask yourself why not, and be precise
about it: every model produces its own reply rows, with its own ids,
every time. A base model's attempt and an adapted model's attempt on
the identical FEN string get two different, unrelated ids, always, by
construction. Matching ids between two runs was never possible even in
the best case, so "same sample_ids" could never have meant "same
positions" -- the field was answering a question ("what did this one
run consist of") that sounds like, but is not, the question the
workshop actually needs answered ("did these two runs see the same
thing"). The fix hashes what the metric was actually *about* -- the
FEN strings, the input -- instead of what the metric happened to
*produce* -- the row ids, the output. `compute_position_set_id` sorts
and deduplicates the FEN list before hashing it. Why bother, given the
list is already right there? Because the order rows arrived in and how
many times a position got sampled are accidents of collection, not
facts about which positions were tested, and a fingerprint that
changed when those accidents changed would be measuring your test
harness, not your model.

The deadline bug is worth your attention even if you never touch this
codebase again, because the mistake generalizes to almost any system
with retries. `model_turn` computes a correct remaining budget and
hands it to the transport as `timeout=0.2`. The transport, faced with
a flaky connection, retries up to three times -- and gives each retry
the same `timeout=0.2`, because that is the only number it was handed.
Nothing in that number says "and don't come back after 0.2 seconds
total," because a plain float can't say that. It can only say "wait
this long," and "wait this long" is a promise that resets every time
you say it again. A budget that gets reinterpreted as a fresh
allowance at every retry boundary is not a budget, it just looks like
one until something downstream retries. The fix turns the number into
a deadline the moment it arrives -- an absolute point in time,
`time.monotonic() + timeout` -- and every retry and every backoff sleep
after that asks "how much of that time is actually left," not "what
was I originally told." A deadline survives being asked about twice.
An allowance does not.

The remaining findings are quicker versions of lessons you have
already learned this phase, which is itself worth noticing: once you
know the shape of a bug, you start seeing its cousins everywhere. The
turn-ownership check only ever looked one direction -- participant
playing the model's color was rejected, the reverse was never even
checked -- which is the same "we tested the case we thought of, not
the case that's possible" gap as the eval-scoping bug, just on a
different table. The frontend's stale-board bug is the "state read
once, trusted for the rest of a function" lesson from round one,
recurring in React instead of SQL: `refreshGameStatus` fetched fresh
server state and then only used *some* of it, leaving the board's own
local fen exactly as stale as before the refresh pretended to happen.

The scenario-reload gap is the most interesting of the smaller three,
because the live UI had already solved it by accident. `suggest()`
never calls `setScenario` on failure, so a failed request just leaves
whatever mapping was already on screen sitting there, with the new
error rendered underneath it. Nobody designed that as a policy; it
fell out of only writing state on the success branch. The reload path
had no such accident to lean on -- it is a cold start, there is no
"whatever was already on screen" to leave alone -- so the moment
reload needed to reproduce the same behavior, the team discovered that
behavior had never actually been written down anywhere as a rule.
Ask yourself: what is the rule, stated plainly, that "don't overwrite
on failure" is actually implementing? It is "show the last mapping
that worked, and separately, whether the most recent attempt failed."
Those are two different facts about two possibly-different rows, and
the endpoint had been collapsing them into one row the whole time.
Making an implicit accident into an explicit contract is often the
real fix, not a footnote to it.

## The third review: the same lock-before-check bug, twice more

A third round found six more findings. Two are round one's
check-before-the-lock bug again, applied to code nobody had checked
against it yet.

The clock-expiry bug is the clearer of the two. Round one fixed
check-then-write for the board position: a read taken before the write
lock can be stale by the time the write happens. The clock check still
ran before `BEGIN IMMEDIATE`, on the reasoning that nesting
`expire_if_over`'s own commit inside the transaction was unsafe. That
reasoning does not hold up: on the branch where the clock has expired,
the next line is a raise, so there is nothing later in the transaction
for an early commit to disturb. The reviewer proved the bug by holding
the write lock open on a second real connection until a near-expired
game genuinely ran out of time, then releasing it -- the blocked move
landed anyway. The fix moves the check inside the lock, onto a fresh
read. Knowing a pattern exists is not the same as having checked every
place it applies.

The turn-conflict 409 is a smaller version of the same gap: a check
written for one direction of a two-way condition, with the other
direction unverified until someone looked for it on purpose.

The eval-panel bug is a different mistake: conflating what should be
*stored* with what should be *shown*. Keeping every position-set
window is correct -- that is the actual history, and it is what lets
two runs prove they measured the same positions. A live panel answers
a different question, though: what is true right now, not what has
ever been true. That reduction now lives in its own pure function,
`latestEvalResultsByScope`, instead of being implied by whichever
query happened to feed the component.

The `position_set_id` fix deserves the closest look. The id exists to
let two eval runs prove they measured the same input. The old code
answered that with the deduplicated *set* of positions sampled. That
is not the same claim as "the same input," because a metric's
denominator counts every attempt, duplicates included: a position
sampled once and the same position sampled a hundred times have
different multiplicities and different denominators, so they are not
the same measurement, whatever else is true of them. Deduplicating
before hashing erased that difference. The fix hashes the sorted list
with duplicates intact instead of the sorted set.

The remaining two are smaller. A retry-loop counter was incremented
before the check that decides whether the attempt happens at all, so a
bail-out with no request sent still counted as one -- moving the
increment below the check means it only counts things that actually
happened. And a README kept asserting three things a previous phase
had already fixed, because nobody's job was to walk back through old
prose and check whether it was still true.

## The fourth review: a test that could pass while lying

The round-3 fix for the false-timeout-loss bug told the two 409 causes
apart by matching the exception's message text. That is a real fix,
but it rests on a fact that has nothing to do with the bug: the exact
wording of an English sentence. Change the wording -- a copy edit, not
a logic change -- and the match silently stops working, while the
test built to catch this keeps passing, because its mock repeats the
old wording rather than a message that has actually changed. A test
can only catch a regression in the thing it varies; if the wording is
frozen in the mock, the test is checking the mock, not the contract.
The fix gives the two causes a `code` that is not prose and is not
supposed to change: `"clock_expired"`, `"not_your_turn"`. The message
stays free to reword; the code is the part a client is actually
allowed to depend on. This is the same discipline the whole phase has
been circling -- a claim only means what it says if something is
actually pinning it down, not just repeating it back unchanged.

The other two findings this round were about this document and its
neighbor: `CLAUDE.md` still described a `just start` from before the
sync room existed, and the previous section of this file ran long and
overreached with a claim about "confidence" that the position-set-id
fix does not actually establish. Both are fixed the same way as
everything else in this phase: read the claim again, compare it to
what is actually true, and correct it.
