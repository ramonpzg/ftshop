# Workshop polish phase prompts

These prompts turn the July 2026 workshop review into five implementation
phases plus one supplemental deck-fallback phase. Run them in order. Each
phase gets its own branch, review, and explicit acceptance before the next
phase starts.

| Phase | Branch | Main outcome | Review findings |
| --- | --- | --- | --- |
| [1](p1-room-correctness.md) | `phase-32-room-correctness` | Concurrent attendees and presenter control work without corrupting the room | 1-4 |
| [2](p2-truthful-evaluation.md) | `phase-33-truthful-evaluation` | Chat Completions, model attempts, datasets, scenarios, and metrics mean what the UI says | 5-8 plus model-call correction |
| [3](p3-learning-experience.md) | `phase-34-learning-experience` | Outcome-first demos expose the full adaptation loop inside a realistic 90-minute plan | 9-12 plus revised teaching order |
| [4](p4-deck-identity-copy.md) | `phase-35-deck-identity-copy` | The deck has its own restrained visual language and the product copy matches Ramon's voice | 13-15 |
| [4b](p4b-deck-model-fallbacks.md) | `phase-35b-deck-model-fallbacks` | The deck can compare cached or live Local/API outputs without depending on the whiteboard | Supplemental fallback |
| [5](p5-release-readiness.md) | `phase-36-release-readiness` | Architecture, failure handling, automated checks, preflight, and rehearsal support a real room | 16-19 |

## How to use them

1. Give only the current phase prompt to the implementation agent.
2. Start each branch from the accepted result of the previous phase, not from
   five parallel copies of the current repository.
3. Review the agent's summary and diff before accepting the phase.
4. Run the documented acceptance checks before merging or starting the next
   branch.
5. Keep notebook work outside all five phases. Do not read, edit, format,
   export, regenerate, or resolve conflicts in `notebooks/` or
   `web/public/notebooks/`.

The accepted `main` should be clean before a phase starts. If a future
worktree contains changes the phase agent did not create, the agent must stop
and ask rather than repairing, stashing, committing, or discarding them.

## Current product decisions

These decisions supersede older Marimo and model references in the repository
and apply to every phase:

- OpenAI-compatible text calls use the Chat Completions endpoint,
  `/chat/completions`. Do not migrate this workshop to the Responses API.
- `gpt-5.5-mini` does not exist and must not remain as a default, fixture,
  example, test value, speaker note, or documented option. The current
  configurable default supplied by Ramon is `gpt-5.6-luna`.
- The workshop notebook is now a plain Jupyter notebook. It is a standalone
  pragmatic asset, not a Marimo app and not a required tldraw iframe.
- Notebook content remains outside these phases. Integration and runbook text
  may acknowledge the standalone Jupyter workflow without editing notebook
  files.
- The provisional teaching order is: concise motivation, why chess and the
  required chess basics, Ramon's route into the domain, outcome-first demos,
  then decomposition of the data, adaptation, and evaluation details. Keep
  the material modular because Ramon will refine this sequence after the
  engineering fixes.

## Shared standards

All five phases must follow `AGENTS.md`, `CLAUDE.md`, and
`docs/architecture.md`. In particular:

- Actions orchestrate, calculations stay pure, and data modules perform I/O.
- React components render and delegate. They do not become workflow engines.
- The FastAPI backend owns durable workshop state.
- Text-model I/O uses one tested Chat Completions client boundary. Model and
  provider capability differences do not leak into React components.
- Model selection uses named backend profiles. A profile binds endpoint,
  credential source, concrete model, and capabilities; browser controls submit
  only the stable profile ID and never receive provider URLs or secrets.
- Tests use real calculations and temporary databases. Do not mock the whole
  application into passing.
- Visible copy is direct, terse, practical, and borderline boring. No emojis,
  em dashes, marketing language, puns, or fake excitement.
- Use existing frameworks and dependencies where they solve the problem. Do
  not build a collaboration, chess, media, or presentation engine from
  scratch when a proven local-first option fits.
- Run project work through the `Justfile`. Add or improve recipes instead of
  leaving one-off scripts behind.
- Commit coherent increments throughout the phase and push the phase branch.
  Commit every phase-owned source, test, fixture, migration, lockfile, and
  document. Finish with a clean tree. Do not merge into `main` before Ramon
  reviews the summary and diff.
- End every phase with both its `notes/ai/` handover and `notes/hu/` learning
  guide. These are part of the deliverable, not cleanup after the work.
