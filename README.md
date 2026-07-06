# EuroSciPy Chess Studio

Local-first workshop app for the EuroSciPy 2026 session
"Same Recipe, Different Results: Fine-Tuning Models Across Modalities".

A tldraw-based whiteboard walks attendees through fine-tuning the same
chess domain across four modalities: text, image, audio, video.

## Quick start

```
just install
just start
```

Frontend runs at http://localhost:5173, backend at http://localhost:8000.

## Commands

The main ones: `just install`, `just start`, `just test`, `just lint`,
`just typecheck`, `just format`, `just reset-db`, `just reset-canvas`,
`just seed`. Run `just` alone to list everything.

## Docs

- `docs/architecture.md` - how the pieces fit together
- `docs/session-plan.md` - the session itself: narrative, topics, page by page
- `docs/demo-plan.md` - how to run the workshop
- `docs/local-dev.md` - day to day development
- `docs/licenses.md` - third party assets and their licenses
