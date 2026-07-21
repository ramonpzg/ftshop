# Third party assets

## Chess piece SVGs

`web/public/pieces/*.svg` (wK, wQ, wR, wB, wN, wP, bK, bQ, bR, bB, bN, bP)

- Author: Colin M.L. Burnett (Wikimedia user "Cburnett"), with minor
  contributions from other Wikimedia editors.
- Source: originally published on Wikimedia Commons
  (`Category:SVG chess pieces`). Fetched from the lichess.org `lila`
  repository's mirror of the same files
  (`public/piece/cburnett/*.svg`), which preserves the original artwork
  unmodified.
- License: Cburnett released these under multiple license options,
  including CC BY-SA 3.0, GFDL, and a 3-clause BSD license. This project
  uses them under **CC BY-SA 3.0** with attribution as given above.
- No modifications were made to the artwork.

If this project is redistributed, keep this attribution alongside the
SVG files.

## tldraw SDK

`web/` uses the tldraw SDK (v5). tldraw ships under its own
business-source-style license, not a classic OSS license. Development
and localhost or LAN serving need no key. A production deployment on a
public domain needs a license key from tldraw: a free hobby license
(with watermark) for non-commercial use, or a commercial key. See
https://tldraw.dev/community/license.

## Icons

UI icons come from Phosphor Icons (`@phosphor-icons/react`), MIT
licensed.

## Deck fonts

The Slidev deck self-hosts these Fontsource packages. Each package
includes the font's SIL Open Font License 1.1 text under
`deck/node_modules/@fontsource/<family>/LICENSE`.

- IBM Plex Sans (`@fontsource/ibm-plex-sans`), copyright IBM Corp.
- IBM Plex Mono (`@fontsource/ibm-plex-mono`), copyright IBM Corp.
- Shantell Sans (`@fontsource/shantell-sans`), copyright The Shantell
  Sans Project Authors (https://github.com/arrowtype/shantell-sans).

All three are licensed under **SIL OFL 1.1**. They are bundled with the
deck, so presentation does not require a font download.

## Workshop media fixtures

`artifacts/cached/media/{image,audio,video}/*`

Every file is generated inside this repository by
`api/src/euro_chess_studio/tools/make_media.py` (`just make-media`),
deterministically seeded so a regeneration is reviewable against the
committed bytes. No provider or model produced any of them; each
fixture JSON that references a file repeats its method in a
`provenance` block, and the artifact panels label them illustrative.

- `image/style_before.png`, `image/style_after.png`: the Cburnett
  white bishop (`web/public/pieces/wB.svg`, CC BY-SA 3.0, attribution
  above) rasterized with cairosvg, and the same silhouette restyled
  programmatically into watercolor washes with Pillow. Both are
  derivatives of the CC BY-SA 3.0 artwork and carry the same license
  with the same attribution.
- `audio/capture_sound.wav`: a synthesized wood-impact click (filtered
  noise burst plus low sine thumps). `audio/board_music_base.wav` and
  `audio/board_music_adapted.wav`: one original motif rendered twice,
  calm and sharpened. All synthesized with numpy; the `_waveform.png`
  files are plots of those exact samples. Original in-repo material,
  no third-party audio.
- `video/scene_clip.mp4`, `video/scene_clip_base.mp4`,
  `video/scene_poster.png`, `video/scene_frames.png`: a storyboard
  animatic of the rushed-release incident scene, drawn frame by frame
  with Pillow and encoded to H.264 with PyAV (the base take adds
  per-frame jitter). Original in-repo material; no chessboard, chess
  pieces, or readable text appears.

Generation tooling licenses: Pillow (MIT-CMU), numpy (BSD), cairosvg
(LGPL-3.0, used as a build-time tool only), PyAV (BSD) bundling FFmpeg
libraries (LGPL). None of these ship in the application runtime; they
are the `media` extra used only by `just make-media`.
