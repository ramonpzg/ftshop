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
Example twelve repeats example one's position. The base model, sampled
twice, answered differently each time; the adapted model answered
identically. The position-set hash keeps both copies, so a suite with
the repeat is a different measurement from a suite without it,
which is exactly right: the denominator is twelve, not eleven distinct
positions with an asterisk.

## The trade-off that keeps the panel honest

The comparison shows legality up, JSON validity up, and explanation
rate falling from 0.75 to zero. That last metric exists because a
demo where adaptation only wins is an advertisement, and this is a
workshop. The mechanism is worth stating precisely: the training pairs
are bare `{"move": ...}` completions, so the adapter learned to stop
talking. Nothing in the data asked it to keep explaining, so it
does not. The regression is not a bug in the adapter, it is the
adapter doing exactly what the data said, which is the sharpest
sentence about fine-tuning the session gets to say. Each modality's
cached evidence card carries its own regression for the same reason:
piece identity dips when style pushes hard, clipping rises when the
music gets loud, frame detail softens when motion stabilizes.

Notice also what the trade-off metric is not. It is computed from the
stored raw replies with a deterministic rule (strip the JSON span,
count remaining letters), the same class of measurement as
valid_json_rate. It would have been easy to invent an "explanation
quality" number. Ask yourself why that would have poisoned the well,
in a phase whose entire theme is that numbers must be able to say
where they came from.

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
built backwards from four outcomes a participant should be able to
demonstrate, results first, decomposition after. The room sees the
adapted model beat the base model on frozen positions, hears the
motif sharpen, watches the flicker settle, and only then gets told
what a LoRA is. Seventy-two minutes of core with hard stops, eighteen
of declared flex, and a cut list ordered by what dies first when
reality attends the session.

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

## Where to poke first

Read `calculations/adaptation.py` and `calculations/comparison.py`
back to back; they are the phase in miniature, identity then refusal.
Then run the chain yourself from the panel and deliberately do it
wrong: freeze the room, try to train on it, read the 409. Then break
a benchmark on purpose with the live path and watch every delta
decline to exist. The system teaches best when you try to make it
lie.
