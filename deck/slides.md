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
---

<div class="title-grid">
<div>

<div class="kicker">EUROSCIPY 2026 · WORKSHOP</div>

# Same Recipe,<br>Different Results

<div class="title-modalities">

Fine-tuning across text, image, audio, and video.<br>
One domain: chess.

</div>

</div>
<div>
<MediaFrame
  file="cover.jpg"
  ratio="4/3"
  expected="One strong chess image or a frame of the actual TUI board. Not a generic AI illustration."
/>
</div>
</div>

<style>
.title-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 3rem;
  align-items: center;
  height: 100%;
}
.title-modalities {
  margin-top: 1.4rem;
  font-size: 1.15rem;
  color: var(--ink-soft);
}
</style>

<!--
TIMING: 30 seconds, hard stop.
SAY: One sentence. We will use chess to inspect the same adaptation recipe across text, image, audio, and video.
CLICK: none.
SOURCE: cover image pending (assets/cover.jpg); record source and license when it lands.
CUT: never.
FALLBACK: static slide, nothing to fail.
-->

---
src: ./slides/01-origin.md
---

---
src: ./slides/02-outcomes.md
---

---
src: ./slides/03-why-adapt.md
---

---
src: ./slides/04-chess-primer.md
---

---
src: ./slides/05-technical-reference.md
---
