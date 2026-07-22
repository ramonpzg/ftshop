---
theme: default
title: Same Recipe, Different Results
info: |
  Same Recipe, Different Results.
  Fine-tuning models across text, image, audio, and video.
  One domain: chess. EuroSciPy 2026 workshop.
colorSchema: light
fonts:
  provider: none
  sans: IBM Plex Sans
  mono: IBM Plex Mono
drawings:
  persist: false
transition: fade
mdc: true
footer: false
# This entry IS the default route: the ranges exclude the slides whose
# notes say OPTIONAL (Oscar; mappings two and three; the A/B guessing
# block and its reveal; the model tree),
# keeping the opening at the 20-25 minute budget. slides-full.md
# imports everything for rehearsal; tests/route.test.ts keeps these
# ranges honest against the OPTIONAL markers.
src: ./slides/01-origin.md#1-3,5-8
---

---
src: ./slides/02-outcomes.md#1-3,6-10,16
---

---
src: ./slides/03-why-adapt.md#1-8,10
---

---
src: ./slides/04-chess-primer.md
---

---
src: ./slides/05-technical-reference.md
---
