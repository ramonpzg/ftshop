# Learning guide: phase 34, complete learning experience

Phase 33 made the machinery stop lying. This phase made it teach. The
difference matters: a truthful system that keeps its evidence in
SQLite is honest the way a locked filing cabinet is honest. Nobody
learns anything from a locked cabinet. The work here was opening the
drawers in the right order, on stage, in ninety minutes, without
faking a single document.

Start with a question before you read any code. The workshop's whole
pitch is one sentence, pairs in, adapter out, eval always. If you had
to make that sentence falsifiable, what would each third need to
carry? Sit with it. Your answer is probably some form of "identity":
which pairs exactly, which adapter exactly, evaluated on what exactly.
That instinct is the entire phase. Now let's see how far the
implementation agrees with you.

## Freezing data until it can testify

The room generates dataset rows continuously. That is lovely for the
aha moment and useless for provenance, because "the training data" is
a moving target while people keep playing. So `dataset_snapshots`
freezes a moment: the SFT rows themselves, stored inline, plus the
counts of what was refused entry. A fallback move, the alphabetically
first legal move the app plays when the model face-plants, stays in
the audit archive and out of the snapshot, and the snapshot records
how many rows it excluded rather than quietly not mentioning them.
Then everything gets hashed.

Here is the first Socratic stop. Why does the snapshot store
`rows_json` instead of just the ids of the dataset rows it froze?
The ids are smaller and the rows are right there in the database.
Think about what `reset_page` does. Now think about a presenter
resetting the chess page between rehearsal and showtime, and the
snapshot's ids pointing at rows that no longer exist. A snapshot that
can be hollowed out by later cleanup is not frozen, it is a list of
promises. Self-contained or nothing.

The hash itself reuses the trick phase 33 settled on for position
sets: sort the serialized rows, keep duplicates, take a sha256 prefix.
Order-independent because the same data in a different order is the
same data. Duplicate-preserving because the same row twice is not the
same data. If you can explain why both properties are needed with a
concrete failure for each, you have understood most of the identity
design in this repo.

## Why an adapter without a dataset hash is not reproducible

The adapter row carries base model, method, seed, output task, config
id, config hash, config json, dataset snapshot id, dataset content
hash, runner, result source, and limitations. That looks like
bureaucracy until you try to delete any one column and say what you
lost.

Drop the seed and two "identical" runs diverge for reasons you can no
longer name. Drop the config hash and "we used roughly these
hyperparameters" becomes archaeology. Drop the dataset content hash
and here is the interesting one, the question the phase prompt insists
you can answer: what exactly breaks?

Reproducing a training run means re-running the same procedure on the
same inputs. The snapshot id gives you a pointer, but a pointer is a
name, not a guarantee; names can be reassigned, databases can be
rebuilt, a "reference-sft-v1" on your machine and mine can quietly
differ by one row someone re-authored. The content hash is the only
thing that lets you take a pile of rows in your hands and prove they
are the inputs this adapter saw, without trusting anyone's labeling
discipline including your own. An adapter without it is a claim that
training happened, on something, at some point. That is a rumor with
a learning rate.

The cached training replay takes this seriously to the point of
rudeness. The fixture records the hash of the dataset it was actually
recorded against, and if the presenter selects any other snapshot,
the handler refuses with a 409 that names both hashes. We could have
"gracefully" produced the adapter anyway and noted the discrepancy
somewhere. Why is the refusal better teaching than the note? Because
the audience only believes what the system enforces. A warning label
on a lie is still a lie with paperwork.

There is a second refusal hiding in the same handler: a snapshot that
shares even one FEN with a held-out suite cannot train. Before reading
on, construct the dishonest scenario this prevents. It is the oldest
trick in the benchmark book, and the fact that a workshop app bothers
to structurally forbid it is half the lesson about why leaderboards
need auditing.

## Why a delta without a matching frozen set is decoration

Phase 33 left a beautiful loose end: `position_set_id`, a hash proving
which positions a metric was measured over, with organic gameplay
guaranteeing that two models essentially never match. The handover
even said it plainly, comparability was provable but never achieved.
This phase built the thing that achieves it: a benchmark runner that
forces a checkpoint through a frozen suite, twelve examples, exact
prompts, one position deliberately included twice.

So, the required question. Two numbers, base 0.58, adapted 1.00. The
delta is +0.42. Under what conditions is that arithmetic and under
what conditions is it decoration? Subtraction always works; that is
the trap. The delta means something only if both numbers answer the
same question, and "the same question" here decomposes into matching
suite content hash (same examples), matching prompt contract (same
ask), matching metric version (same ruler), and matching non-null
position-set ids (same inputs actually measured, not just intended).
Break any one and you have two unrelated measurements posing as a
before and after. The UI renders that case as "Not comparable" with
the reason, both values still visible. Refusing to subtract is a
result. It might be the most educational result the panel can show.

And it happens naturally. Run the base benchmark live and let one
provider call time out. That example drops out of every denominator,
because a model that never answered was not measured, and now the live
run's position set covers eleven positions where the replayed adapted
run covers twelve. Same suite, same prompts, same intentions,
different measurement. Every delta refuses. Most systems would have
averaged over the gap and called it robustness.

The multiplicity detail deserves ten seconds of your suspicion.
Example twelve repeats example one's position. The scripted base
replies differ between the two copies; the scripted adapted replies
are identical. The position-set hash keeps both copies, so a suite
with the repeat is a different measurement from a suite without it,
which is exactly right: the denominator is twelve, not eleven distinct
positions with an asterisk.

## The trade-off that keeps the panel honest

The comparison shows legality up, JSON validity up, and explanation
rate falling from 0.67 to zero. That last metric exists because a
demo where adaptation only wins is an advertisement, and this is a
workshop. The mechanism is worth stating precisely, and so is what
kind of claim it is. The sft-v2 prompt asks for
`{"move": ..., "why": ...}` with the why explicitly optional. The
scripted base replies fill the field eight times in twelve; the
scripted adapted replies never do. No model produced either set, and
the second review round rightly objected to prose that said the
adapter "learned to stop talking" as if narrating a run that
happened. What the fixtures do is stage the trade that bare
`{"move": ...}` completions are known to buy, so the chain can
demonstrate how you would catch it: nothing in such data asks the
model to keep explaining, and a metric with the explanation inside
the contract is what makes the collapse measurable instead of
anecdotal. The measurement is real. The biography is not. Each
modality's cached evidence card carries its own staged regression for
the same reason: piece identity dips when style pushes hard, clipping
rises when the music gets loud, frame detail softens when motion
stabilizes.

The first version of this metric earned a review finding, and the
finding is better teaching than the metric. Version one counted prose
outside the JSON object as explanation. Sit with what that rewards.
The prompt demanded pure JSON, valid_json_rate punished anything
else, and explanation_rate paid the model for breaking exactly that
rule. One reply could be a defect on one ruler and a virtue on the
other. So the question you should be able to answer now: what does a
regression have to be compatible with before "regressed" is a fact
about the model rather than a contradiction between your rulers? The
fix was to move the explanation inside the contract as an optional
field, and the reward for doing it honestly is that both numbers can
be true at once, twelve of twelve valid JSON and zero of twelve
explanations, no asterisk required. It would still have been easy to
invent an "explanation quality" number. Ask yourself why that would
have poisoned the well, in a phase whose entire theme is that numbers
must be able to say where they came from.

## Media that exists

Before this phase, the cached artifacts were JSON descriptions of
media that did not exist, a menu with no kitchen. Now
`artifacts/cached/media/` holds eleven committed files, every one
generated inside this repo by `just make-media` with fixed seeds:
the watercolor bishop pair, a synthesized capture click, one motif
arranged calm and then sharpened, and two takes of the incident-room
animatic, steady and deliberately flickering. The flickering "base"
take is the larger file, because per-frame jitter is exactly what a
video encoder cannot compress. The failure mode is visible in the
file size before you press play. I refuse to apologize for how much I
enjoy that.

The honesty rule for media is the same as for numbers: nothing claims
a producer it did not have. No file says a model made it; the
provenance blocks name the script, the seed, the source SVG and its
CC BY-SA license. The panels render the artifact first and keep the
raw payload behind a disclosure, and a missing or broken file renders
as words instead of a blank rectangle, because a blank rectangle in
front of forty people is a small death.

## The run of show, rebuilt backwards

The old plan taught mechanisms for thirty-five minutes and hoped the
payoff arrived before the audience's attention did. The new one is
built backwards from outcomes, and after the review it follows
deck/PLAN_V2.md exactly: the personal origin story lands on a
recording of the Termux TUI before anyone is taught a single chess
rule, because people who have never pushed a pawn still understand a
terminal game when they watch one. Then the A/B beat, which output
came from the adapted model, with a reveal table where at least one
row gets worse. Then why adapt at all, then the delayed chess recap
that names objects the room has already seen, then the board, then
the notebook. The room sees the adapted model beat the base model on
frozen positions, hears the motif sharpen, watches the flicker
settle, and only then gets told what a LoRA is. Seventy minutes of
core with hard stops, twenty of declared flex, an optional
two-minute coda showing what the room produced, and a cut list
ordered by what dies first when reality attends the session.

One structural question worth chewing: the plan marks audio and video
as presenter-led and gives attendees prediction tasks instead of
buttons. Why is saying that out loud better than the usual theater of
pretending everything is hands-on? Count the requests. Forty browsers
times one generation each is a bill and a bottleneck; one presenter
run plus forty reads is a demo. The honesty is not just ethical, it
is the only version that survives venue wi-fi.

The measured part is measured. The scripted rehearsal ran the entire
core's app surface against a fresh keyless backend: total system wait
1.22 seconds, slowest step the ten-file media fetch at 69
milliseconds, forty simulated attendees polling concurrently in under
three seconds with zero provider involvement. The session's budget is
speech and humans; the machine is effectively free. Which is how a
ninety-minute plan earns the right to be about teaching instead of
about waiting.

## What the review caught

The first delivery of this phase collected twelve findings. Fixing
them taught more than building it did, which is how reviews are
supposed to work and rarely do. The instructive ones follow; treat
each as a question before you read its answer.

Start with the embarrassing one. The evidence chain was scrupulously
honest in its columns, result_source said cached, the runner said
replay, and it was still misleading, because a room reads framing,
not schemas. A fixture replay with real hashes and real arithmetic
looks exactly like a training run to anyone who does not know which
column to distrust. What is the difference between recording the
truth and telling it? The fix is a banner that says scripted
illustration, no model was trained, in words, on the panel, in the
fixtures, and in the run of show. If the audience must know one
thing, the system says that thing out loud instead of filing it.

Next, concurrency. SQLite allows one writer at a time, and the live
benchmark used to make its provider calls inside the job's write
transaction. Picture the room: the presenter clicks Run base live,
the provider takes its time, and forty attendees' moves queue behind
a lock that is waiting on someone else's network. The fix is
boringly classical, gather then persist. Collect every reply with no
database in hand, then write once, briefly. The test for it is the
part worth copying: a fake chat client that performs a write through
a second connection during every call, so if the handler ever holds
the lock while gathering, the test deadlocks instead of passing
politely. The same finding's cousin got fixed alongside it: a live
run now has a whole-run deadline, aborts after three consecutive
transport failures, and the panel grew a Stop waiting button,
because three minutes of a frozen panel in front of a room is not a
wait, it is a fire.

Then history. Rerunning a benchmark used to replace the previous
run's metric rows, latest wins. Ask what the word evidence means if
a rerun can rewrite it. A ledger you can overwrite is a whiteboard
with self-esteem. Benchmark metrics are now insert-only, keyed by
run; reruns add rows, comparisons pick the latest per checkpoint,
and the old runs keep standing there like witnesses.

The foreign key that had to die is a nice SQLite war story. Each
benchmark run now records the job_config_id that produced it, but
run_job inserts the config after the handler finishes, so the
reference points forward in insertion order. The textbook answer,
deferred foreign keys, turned out to be non-deterministic in this
stack, passing in isolated repros and failing inside the real
transaction. So the column is plain TEXT, the old constraint was
removed by table rebuild, and consistency comes from the shared
transaction instead of a checker that could not make up its mind.
When a guarantee is unreliable, holding onto it anyway is
sentimentality, not rigor.

The guardrail finding is the one to internalize for any shared-room
software. The adaptation panel hid its buttons from attendees, and
hiding is not authorization; the jobs endpoint would run a paid
generation for anyone with curl and the LAN address. Now the backend
classifies paid job types and refuses them for any client that is
not on the presenter's machine. Why is loopback an acceptable proxy
for "the presenter" here? Because the backend binds localhost behind
the repo's own forwarding proxies, so on this topology the only
loopback traffic is the presenter's browser. Change the topology and
that assumption dies with it, which the handover says in bold ink.

Two smaller ones, same moral. Suite validation used to check shape,
so a suite claiming "zzzz" was a legal move validated fine; it now
re-derives legality from the FEN with python-chess and re-renders
the prompt from the contract, so the suite proves its claims instead
of formatting them. And the e2e stacks used to inherit whatever
OPENAI_API_KEY your shell carried, which once made a live button
appear in a test that assumed keyless; credentials are now pinned
empty in every spawned stack, and the final suite run was executed
with a deliberately poisoned key in the shell to prove the isolation
holds. What does your test environment inherit from you? Wrong
question order. What do your tests assume you are not carrying?

## The review came back

The corrected build got reviewed again and collected eleven more
findings. If the first round taught mechanism, this one taught
humility about identity, and one finding is good enough to retell in
full.

Two benchmark runs, same suite, same prompts, matching position sets,
matching metric versions. Every check the panel had, green. Still not
a before and after. What else has to match? Sit with it before
reading on. The answer is the model. The comparison selected the
latest base run regardless of who produced it, so a live run of
gpt-5.6-luna received valid fine-tuning deltas against the scripted
gemma adapter. Same exam, same grading, different student, and the
report card said "improved". The fix adds lineage to comparability
and makes selection prefer the base run whose model the adapter
actually adapted. The uncomfortable part: our own end-to-end test
asserted the Luna pair was comparable. A test suite is a list of
claims you have stopped questioning. Reviews exist because some of
those claims are wrong on purpose-shaped accident.

The forwarding guard fell to a one-line spoof. Vite's xfwd APPENDS to
whatever X-Forwarded-For the client sent, and the backend trusted the
first entry, so "127.0.0.1" from a LAN laptop arrived as
"127.0.0.1, lan-ip" and read as the presenter. A proxy that appends
is a witness; a client that writes the first entry is a novelist. The
proxies now overwrite the header with the peer they actually saw, and
the backend reads the last word, not the first.

Then arithmetic. Every model turn auto-fired a scenario call, on top
of the opponent call the turn already needed. Two calls per exchange,
times forty attendees, times a five-minute game. Multiply before you
ship. The fix is a policy short enough to say on stage: the room
plays the local default model; assessments and every generation job,
local audio included (an attendee could previously load a multi-GB
MusicGen onto the presenter's GPU, and the route test proved it by
doing exactly that for seven minutes), belong to the presenter's
machine, enforced with 403s. Related honesty: "Stop waiting" stopped
the browser, not the server. The run kept spending after the button
promised otherwise, and a refreshed panel would happily start a
duplicate. Ask what your cancel button actually cancels. The
round-two fix made the button say what it does and locked the
launching tab until the run landed or timed out, which, as review
three pointed out, guards exactly one tab. The full fix is below.

Small ones, same lesson. A FEN with no black king passed suite
validation because chess.Board parses it and politely generates moves
for a position that cannot exist; parseable is not playable, and
is_valid() is now the gate. An upgraded database kept presenting its
obsolete sft-v1 suite because "first suite with a comparison" favored
whoever had history; current contract now outranks seniority. And the
panel fetched its "shared evidence" exactly once at mount, which
makes it a screenshot, not a share; it polls now, single-flight,
five seconds.

## Round three: where state lives

The third review found four things. Three of them are one question:
where does the truth live, and what happens when the place you put
it goes away?

Start with the policy. After round two, attendees could only play
the default opponent. Ask who decides what the default is. An
environment variable. Ask what that variable holds on a fresh
checkout. Luna, on a hosted endpoint, billed per token. So the
policy was "attendees play whatever OPENAI_MODEL says", which is not
a policy. Our own test asserted a LAN browser could start a Luna
game because Luna was the default. Write that sentence out and it
refutes itself. The fix is to fail closed: an attendee start now
needs evidence that the endpoint is local, either a loopback base
URL, which the backend can check for itself, or an explicit
OPPONENT_ENDPOINT_IS_LOCAL=1 from the operator who put llama.cpp on
another box. No evidence, no game, and the refusal names the missing
variable. The evidence is never the model name, because a name
proves nothing about who serves it. Ask what your system does when
configuration is half-done. Whatever it does then is your actual
default.

The same round made us stop claiming something adjacent. The demo
plan described a picker with local Gemma as the default and Luna as
the frontier pick, on two different endpoints. The client has one
OPENAI_BASE_URL and one key, and OPPONENT_MODELS only changes the
model string in the request body, so every picker entry resolves
against the same endpoint. Per-model endpoints are the phase 4b
named-profile registry, and until that integration lands the
two-endpoint picker is a plan, not a feature. The docs now say so.

Now the duplicate live run, the finding that corrected this very
document. Round two kept the live-controls lock in React state, and
the previous version of this guide called the duplicate problem
fixed. React state is memory owned by one tab, with the lifespan of
that tab. Reload and it is gone; open a second presenter tab and it
never existed. A guard on spending has to live where every tab can
see it and no tab can lose it, which means the server, which means a
committed row. run_job now writes a run_locks row before the first
provider call and deletes it in a finally; a second request reads
the row and gets a 409 with the seconds remaining; the state
response carries in_progress so a reloaded panel wakes up already
locked. Two details are worth sitting with. Why does the row have an
expiry? Because a process that dies mid-run cannot run its finally,
and a lock nobody holds should not outlive everyone who could
release it; 330 seconds is the server's own worst case plus slack,
the number the panel already used. And why is the insert a plain
INSERT rather than an upsert? Because two requests can race past the
read, and the primary key constraint then decides the winner exactly
once, in the database, where the race actually happens. Where should
state live? Ask who has to agree on it.

The third finding: the panel used to replace everything with
"Backend down?" the moment one poll failed. One dropped request and
forty screens of evidence become forty apologies. The evidence did
not stop being true because a fetch failed. Now the empty failure
state renders only when nothing ever loaded; after that, a failed
poll keeps the last good state on screen under a stale notice that
clears itself when the poll recovers.

And the fourth: the refusal copy ended with "not a before", which is
not a sentence. It now reads "not a valid baseline for this
adapter." The refusal is the teaching material; it has to survive
grammar.

## Round four: local is not the same as available

Review four asked a question round three had quietly skipped. The
locality gate proves where the bill goes. What does it prove about
throughput? Nothing. A local server that answers one request in two
seconds answers forty simultaneous requests in whatever order it
likes, and the last ones in line blow through the 30 second turn
deadline while costing nothing at all. Free and overloaded are
compatible.

So the room now opens on measurement instead of location. Attendee
timed games and model replies need a second flag, ROOM_MODEL_PLAY=1,
and the workflow that earns it is written into the demo plan: run
the real load test against the actual llama.cpp endpoint on the
venue laptop, read the model-move p95, and set the flag only if it
sits inside the turn deadline with no errors. The mock load test
cannot answer this question; it measures the backend while standing
in for the very thing under test. Until the flag is set the room
free-plays, every move still lands in the dataset with the same
rewards, and Gemma answers once, presenter-led, on the projector.
The attendee panel says "Free play today" instead of offering a
button that would only 403. Ask which of your prep checks measure
the thing you will actually do in the room, and which measure a
stand-in.

Two smaller corrections in the same round. A backend restart used to
leave the live-run lock in the table for up to its full 330 second
TTL, locking the panel for a run that could not possibly still
exist; startup now clears the table, because a lock that outlives
its process guards nothing. The TTL stays for the case startup
cannot see, a process that is alive but hung. Different failure,
different remedy. And the duplicate-run guarantee is now tested as
an actual race: one test holds a runner mid-flight on one connection
while a second connection is refused, and another pins the exact
interleaving where both requests read an empty table and the primary
key decides. A guarantee that only exists in production traffic is a
hope with good posture. That one stays.

## Round five: trust your instruments last

Round five audited the things the other rounds leaned on, and both
findings are the same lesson: the code that certifies your system
deserves the scrutiny you give the system, because a broken
instrument fails in the direction of good news.

The load simulator had four ways to bless a broken room. It counted
only 5xx and transport failures as errors, so a run where every
model move was refused with 403 reported an error column of zero.
The three outcomes that signal trouble, unavailable, stale, and
fallback, all arrive as HTTP 200, so the transport layer saw
success. Unavailable and stale carry no move, and the simulator
indexed into the move unconditionally, so it crashed on precisely
the runs it existed to measure. And it still fired an assessment
after every exchange, a workload the room stopped producing two
rounds ago, so it measured double the model traffic the real room
generates. Each defect points the same way. Ask of any test
harness: if the system under test failed right now, which line of
the report would say so? If you cannot answer, the harness is
measuring something else. The simulator now counts every non-2xx as
an error, reads model turns through a function that survives a null
move and tallies all four outcomes, retries an open model turn the
way the UI's retry button does, drops assessments from the workload,
and ends with a verdict that says PASS, FAIL, or that the run
carried no model traffic and cannot certify anything. That last case
matters: zero errors over zero model calls proves nothing, and the
old report could not tell the difference.

The second finding is a classic. Acquiring the lock read the row,
decided it was expired, deleted it, and inserted a fresh one, all
outside a transaction that held the write lock. Two requests could
both read the same expired row; the first replaced it, the second
then deleted the first's brand-new lock and inserted its own, and
both reported success. Walk through it once with two fingers on the
page and the bug is obvious, which is the point: interleavings do
not announce themselves, you have to go looking. The fix is to take
the write lock before the read, one short BEGIN IMMEDIATE
transaction around read, decide, delete, insert, so the loser's read
happens after the winner's insert and sees a fresh row instead of an
expired one. The lock row also carries an owner token now, and
release deletes only its own row, because a run that hangs past its
TTL, gets replaced, and then wakes up to run its finally must not
delete its successor's lock. Ask where else you read a value, decide
something, and write on the strength of that decision without
holding anything that keeps the value true. Every one of those is
this bug waiting for traffic.

## Where to poke first

Read `calculations/adaptation.py` and `calculations/comparison.py`
back to back; they are the phase in miniature, identity then refusal.
Then run the chain yourself from the panel and deliberately do it
wrong: freeze the room, try to train on it, read the 409. Then break
a benchmark on purpose with the live path and watch every delta
decline to exist. The system teaches best when you try to make it
lie.
