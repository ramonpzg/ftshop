# Learning guide: phase 30, the 401 nobody saw and the render nobody needed

Five complaints from actually using the thing: tiny fonts, a mystery
about verifiers, an opponent that would not move, a sticky board, and
an analysis panel that failed politely. Two of those five were the
same bug, and the sticky board is the most instructive React lesson
in this repo so far.

## The opponent that would not move

The keys were in the environment. The button was enabled. The model
never moved. What failed?

Nothing failed loudly, which was the failure. Your key was an
OpenRouter key; the client's default base URL is api.openai.com; an
OpenRouter key presented to OpenAI gets a 401; the UI caught the
error and displayed... nothing much. "Assessment failed. Next move
retries." is technically true the way a shrug is technically an
answer.

The configuration fix is one principle: the key and the base URL
travel together. Set OPENAI_BASE_URL to OpenRouter, use OpenRouter's
model naming (provider/model), done; local-dev.md now has the exact
block. But the durable fix is the other one: every model failure now
prints its actual reason on the board. "Model error: could not reach
http://127.0.0.1:9: Connection refused." A system that names its
misconfiguration gets fixed in thirty seconds; one that shrugs gets
debugged for an evening. If you take one habit from this phase, take
that one: error messages are a user interface, usually the one you
meet at the worst moment.

While in there: the client also learned to wrap transport errors
(dead host, timeout) into the same clean error type, because an
unreachable endpoint was surfacing as an anonymous 500, and
anonymous 500s are where debugging time goes to die.

## Two models, one board

You wanted the room to watch small Gemma lose and gpt-5.5 not lose,
back to back. That is now OPPONENT_MODELS in the env: list more than
one model and Start game grows a picker. The chosen model rides on
the games row, so each match knows who it was against, start over
keeps the opponent, and the thinking line says who is thinking.

Worth noticing where the choice lives: on the game, not in React
state and not in a global setting. Ask what each alternative would
break. React state: reload mid-game and the opponent is forgotten.
Global setting: one attendee's pick changes everyone's opponent. On
the game row, the durable entity that already owns the clock and the
result also owns the opponent, and every downstream question (who
was this loss against?) has an answer forever. Data modeling is
mostly deciding which noun owns which fact.

## The sticky board, or: who re-renders when the clock ticks

The board felt unresponsive. The profiler question: what re-renders
twice a second in that panel? Answer: everything. The countdown was
`useState` in WorkspacePanel, so every 500ms tick re-rendered the
panel and all its children, including a CodeMirror editor that could
not care less about chess clocks. Clicking a square had to compete
with that churn for frame time.

The fix is a boundary. The clock is now its own little component:
it owns its interval, its seconds, its re-render. The parent hands
it a game and a callback and hears nothing until the flag falls.
One component re-renders twice a second; it contains an icon and
five characters. The general rule: state that changes on a timer
should live in the smallest component that displays it. React does
not charge you for components; it charges you for renders.

Second boundary, same idea: MiniIde is now memo()ed, so the most
expensive child in the tree only re-renders when the snippet
actually changes. The catch worth internalizing is that memo
compares props by identity, so the onSelectSnippet callback had to
become a useCallback. A memo whose function props are recreated
every render is a no-op wearing a performance costume.

## Bigger type, bigger board, bigger box

Fonts moved up two sizes at the base (13 to 15px) and one everywhere
else; the board grew from 280 to 340px; the workspace shape grew to
1240x900 so the bigger content fits without the awkward scroll you
screenshotted. The interesting part is the persisted-canvas problem:
your existing shapes were saved at the old size and would stay
cramped forever. ensureWorkspaceShape now grows any workspace shape
below the new minimum on sight, and never shrinks one, so a shape
you deliberately made huge stays huge. Migrations are not only for
databases; any persisted artifact eventually needs one, including
drawings.

## Verifiers: no, and here is the pointer

We do not use PrimeIntellect's verifiers library. The RL environment
in this workshop is compute_reward plus python-chess legality,
hand-rolled, five lines, because five lines fit on a slide and the
point is the concept: the environment scores actions, illegal costs
you, mate pays. Verifiers is what the same idea looks like grown up:
environment classes, rubrics, rollouts, GRPO trainers. The reward
snippet and the notebook's training ladder now both name it, so an
attendee who wants the production version leaves with the link. Use
the toy to teach, point at the tool for work. Never confuse the two
in either direction.
