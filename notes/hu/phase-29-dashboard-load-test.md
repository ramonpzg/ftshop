# Learning guide: phase 29, watching the room and surviving it

Three questions came in: can I see every game at once and take the
data home in one click, is our LLM path async, and will forty humans
melt the laptop. The first is a feature, the second is a vocabulary
lesson, and the third is a number nobody should guess when they can
measure.

## The dashboard, or: the data was already there

The presenter panel now has a Games section: every match in the room,
active first, with a live countdown or a result, move counts, and a
totals line. Two buttons under it collect the harvest: the SFT export
the snippets already load, and a new full archive with every sample
from every game across all six shapes, each line tagged with its
shape and workspace of origin. That file is what rides to the GPU.

Notice how little new state this required: none. Games, moves, and
dataset rows were already durable; the dashboard is one JOIN with two
correlated subqueries and a poll. When a feature costs a query and a
component, that is your prior data model paying dividends. The one
decision worth pausing on: the endpoint reconciles every active clock
with the wall clock before answering. Why there? Because a dashboard
that shows an abandoned game as "playing, -14:32" is lying, and the
lazy-expiry rule from phase 27 says the truth gets computed whenever
someone looks.

## "Is it async?" is the wrong question, pleasingly

The honest answer: no, `llm_client.chat()` is synchronous httpx, and
every route in the API is `def`, not `async def`. The useful answer:
that does not mean what people fear it means. FastAPI runs sync
routes in a thread pool. The event loop never blocks; each in-flight
request just rents a worker thread. So the real question is not "is
it async" but "how many threads do we have and how long does each
request hold one".

Now count. A model move holds a thread for the whole LLM round trip,
say 1.2 seconds. The UI fires two LLM-bound calls per exchange (the
move and the assessment). Forty attendees exchanging every four
seconds means roughly 40 x 2 x 1.2 / 4 = 24 threads busy on average,
with bursts well above. The default pool is 40. Uncomfortably close,
so the lifespan now raises it to 120. That is the entire "async
migration": one line, once you know which resource is actually
scarce. A rewrite to async httpx would buy nothing until the room
triples.

The database needed the same treatment. SQLite's default journal mode
makes readers and writers block each other; a room of forty writing
moves while polling presenter state is exactly the wrong workload for
it. WAL mode (write-ahead logging) lets readers proceed during
writes, and a busy timeout makes colliding writers queue politely
instead of throwing "database is locked". Delightful side effect: the
test suite got four times faster, because it commits hundreds of
times and commits got cheap. Ask yourself why the fix for a
production concurrency problem sped up single-threaded tests, and
you will understand WAL better than most.

## Measure, then believe

The new `just load-test` simulates the room: every fake attendee
joins, starts a timed match, plays legal moves with think time,
triggers the model reply and the assessment like the real UI does,
and polls presenter state every three seconds. A mock OpenAI endpoint
(`just mock-llm`) answers with 1.2 seconds of artificial latency,
because a fast mock would be flattering ourselves: it is precisely
the slow upstream that stresses the thread pool. The mock is
threaded, which is not a detail. A single-threaded mock serializes
every model call in the room, and then you are load testing your
mock.

Results, on a container with a fifth of your laptop's cores: forty
attendees, sixty seconds, zero errors. Board moves at 21ms median.
Model-bound calls at the mock's latency plus about a second of
queueing. Ten moves per second landing in SQLite, four thousand
dataset rows in a minute, the dashboard rendering forty live
countdowns while it happened.

And one bug that only load could find: two requests out of three
hundred failed at cold start, because twenty clients simultaneously
polled presenter state on an empty table, all passed the "does the
singleton row exist" check, and all tried to insert it. Check-then-
insert races are invisible at one user and guaranteed at forty. The
fix is to let the database arbitrate: INSERT OR IGNORE, exactly one
winner, everyone reads the same row afterwards. The general rule
hiding in there: uniqueness is the database's job, and any uniqueness
your application code enforces with an if-statement is a race you
have not met yet.

So: will it run on your laptop? The floor established here says yes,
with roughly three times the headroom. The week before EuroSciPy,
run the same three commands on the machine that will actually be on
stage, and turn "should" into a number.
