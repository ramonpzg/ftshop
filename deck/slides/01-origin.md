<div class="title-pieces" aria-hidden="true">
  <span style="top: 6%; left: 6%; font-size: 5.5rem; transform: rotate(-14deg);">&#9822;</span>
  <span style="top: 12%; right: 10%; font-size: 7rem; transform: rotate(10deg);">&#9820;</span>
  <span style="bottom: 14%; left: 12%; font-size: 6.5rem; transform: rotate(8deg);">&#9819;</span>
  <span style="bottom: 8%; right: 22%; font-size: 5rem; transform: rotate(-8deg);">&#9821;</span>
  <span style="top: 44%; right: 4%; font-size: 4.5rem; transform: rotate(-18deg);">&#9823;</span>
  <span style="bottom: 30%; left: 40%; font-size: 4rem; transform: rotate(16deg);">&#9818;</span>
</div>

<div class="title-block">

<div class="kicker">EUROSCIPY 2026 · WORKSHOP</div>

# Same Recipe,<br>Different Results

<div class="title-modalities">

Fine-tuning across text, image, audio, and video.<br>
One domain: chess.

</div>

</div>

<style>
.title-block {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 100%;
}
.title-modalities {
  margin-top: 1.4rem;
  font-size: 1.15rem;
  color: var(--ink-soft);
}
.title-pieces span {
  position: absolute;
  color: var(--ink);
  opacity: 0.14;
  user-select: none;
  line-height: 1;
}
</style>

<!--
TIMING: 30 seconds, hard stop.
SAY: One sentence. We will use chess to inspect the same adaptation recipe across text, image, audio, and video.
CLICK: none.
SOURCE: none; the background is typographic chess glyphs, no asset.
CUT: never.
FALLBACK: static slide, nothing to fail.
-->

---

# This is what I looked like when I discovered chess

<div class="origin-grid">
<MediaFrame
  file="origin-photo.png"
  ratio="4/3"
  expected="Old picture of Ramon, full enough to read from the back of the room."
/>
<div v-click class="reserve">
<MediaFrame
  file="old-book.jpg"
  ratio="3/4"
  width="400px"
  height="400px"
  expected="The chess book, photographed as a physical object. Not in a card."
/>
</div>
</div>

<style>
.origin-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 2.5rem;
  align-items: center;
  margin-top: 0.5rem;
}
</style>

<!--
TIMING: 45 seconds.
SAY: I bought a book and everything to get better at it, opened it five times, never saw it again, was not any good, and stopped playing.
CLICK: 1. The book appears as a second physical object next to the photo.
SOURCE: assets/origin-photo.jpg and assets/origin-book.jpg, Ramon's own.
CUT: never. This is origin, not instruction. Do not explain chess yet.
FALLBACK: placeholders render with final geometry until the photos land.
-->

---

# Fast forward to April 2026

<div class="launch-stack">
<MediaFrame
  file="duolingo-launch.png"
  ratio="16/9"
  expected="The Duolingo chess launch post."
  height="400px"
  source="Duolingo, launch post. https://blog.duolingo.com/chess-course/"
/>
<div v-click class="reserve overlay">
<MediaFrame
  file="duo-example-cmate.jpg"
  ratio="9/19.5"
  height="400px"
  expected="Duolingo chess mode, app screenshot."
/>
</div>
</div>

<style>
.launch-stack {
  position: relative;
  max-width: 34rem;
  margin: 0.5rem auto 0;
}
.launch-stack .overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>

<!--
TIMING: 30 seconds.
SAY: Chess mode launched earlier in the year. I only noticed it in Japan, opening the app to practise Japanese.
CLICK: 1. The app screenshot takes over the launch post.
SOURCE: Duolingo launch post and app screenshot; record source URL, license, access date in the asset inventory.
CUT: never.
FALLBACK: placeholders keep the geometry.
-->

---

# Oscar and I became best friends

<div class="phone-fixed">
<MediaFrame
  file="oscar-game.png"
  ratio="9/19.5"
  height="330px"
  expected="One game against Oscar, app screenshot."
/>
<div v-click class="reserve overlay">
<MediaFrame
  file="oscar.png"
  ratio="9/19.5"
  height="330px"
  expected="Oscar."
/>
</div>
</div>

<style>
.phone-fixed {
  position: relative;
  width: fit-content;
  margin: 0.5rem auto 0;
}
.phone-fixed .overlay {
  position: absolute;
  inset: 0;
}
</style>

<!--
TIMING: 30 seconds. OPTIONAL: the default route skips this slide.
SAY: The main player and I became best friends. This is allowed to sound slightly ridiculous because it happened.
CLICK: 1. The same phone frame stays in place; its contents change from the game to Oscar.
SOURCE: assets/oscar-game.png, assets/oscar.png, Ramon's screenshots.
CUT: can be skipped in a tight room without breaking the arc.
FALLBACK: placeholders keep the phone geometry.
-->

---

# 5, 20, 500

<div class="count-grid">
<div class="counters">
  <div v-click class="reserve count-line"><span class="count">5</span> games a day</div>
  <div v-click class="reserve count-line"><span class="count">20</span> games a day</div>
  <div v-click class="reserve count-line"><span class="count">500</span> games in the first month</div>
</div>
<div v-click class="reserve">
<MediaFrame
  file="queens-gambit.jpg"
  ratio="16/9"
  expected="Queen's Gambit still."
  source="until I had to watch this..."
/>
</div>
</div>

<style>
.count-grid {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 2.5rem;
  align-items: center;
  margin-top: 1rem;
}
.count-line {
  font-size: 1.2rem;
  color: var(--ink-soft);
  padding: 0.5rem 0;
}
.count {
  font-family: "IBM Plex Mono", monospace;
  font-size: 2.6rem;
  font-weight: 600;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
  margin-right: 0.6rem;
}
</style>

<!--
TIMING: 45 seconds.
SAY: I got hooked, and then I watched it for the first time.
CLICK: 4. Three counts land one at a time, then the Queen's Gambit image.
SOURCE: the counts are the record Ramon tells on stage; do not add an Elo or total-game number around them.
CUT: never.
FALLBACK: static counts read fine without the image.
-->

---

# No internet, no problem?

<div class="no-internet">
<MediaFrame
  file="no-internet.jpg"
  ratio="9/19.5"
  height="445px"
  expected="Duolingo chess rendered useless from Sydney to Doha."
/>
<p class="statement-quiet">
    You don't really know you're an addict until you start experiencing bad withdrawal symptoms...
</p>
</div>

<div v-click class="reserve centered-overlay">
<MediaFrame
  file="frustrated.jpg"
  ratio="1/1"
  height="330px"
  width="370px"
  expected="Oscar."
/>
</div>

<div v-click class="reserve centered-overlay">
<MediaFrame
  file="plane-chair-meme.png"
  ratio="4/3"
  height="370px"
  width="470px"
  expected="Oscar."
/>
</div>

<style>
.no-internet {
  display: flex;
  gap: 3rem;
  align-items: center;
  margin-top: 0.5rem;
}
.no-internet p {
  max-width: 20rem;
}
.centered-overlay {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: grid;
  place-items: center;
}
</style>

<!--
TIMING: 20 seconds.
SAY: On the way back from Japan I could not play. That is the constraint that matters.
CLICK: none.
SOURCE: assets/no-internet.png, Ramon's screenshot.
CUT: never; this is the problem statement.
FALLBACK: the sentence carries the slide if the screenshot is missing.
-->

---

# A reasonable response to that problem

<div class="response-grid">
<div v-click class="reserve">
<MediaFrame
  file="meme-dog-thinking.jpg"
  ratio="1/1"
  width="300px"
  expected="The dog-thinking meme."
/>
</div>
<div class="response-lines">
  <p v-click class="reserve">What if I completely change what I had planned for my talk with less than a month to go</p>
  <p v-click class="reserve emphasis">What could possibly go wrong</p>
</div>
</div>

<div v-click class="reserve centered-overlay">
<MediaFrame
  file="burning-house.jpg"
  ratio="4/3"
  height="370px"
  width="470px"
  expected="Oscar."
/>
</div>

<style>
.response-grid {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 3rem;
  align-items: center;
  margin-top: 0.5rem;
}
.response-lines p {
  font-size: 1.3rem;
  padding: 0.6rem 0;
}
.response-lines .emphasis {
  font-weight: 700;
  font-size: 1.6rem;
}

.centered-overlay {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: grid;
  place-items: center;
}
</style>

<!--
TIMING: 45 seconds.
SAY: Surely people have fine-tuned models on chess moves. Has anyone explained the complete process, released the evidence, and then done something personal with it?
CLICK: 3. The dog-thinking meme, the talk-plan line, then "what could possibly go wrong".
SOURCE: assets/meme-dog-thinking.jpg pending.
CUT: never. These beats help command the room; keep the visible words short and let the delivery do the setup.
FALLBACK: lines land without the meme.
-->

---
layout: side-media
side: left
footer: false
---

# my goal...

<p>it runs on my phone, records wins, losses, and draws, keeps the moves, and replays the game.</p>

<div v-click class="reserve objective">
  <span class="compare-label">ideally...</span>
  <p>I'd prefer to win while taking as few opposing pieces as possible. Because Sun Tzu says it too</p>
</div>

<MediaFrame
  v-click
  class="reserve"
  centered
  file="sun-tzu.jpg"
  ratio="4/3"
  width="470px"
  height="350px"
/>

::media::

<PhoneTuiReplay height="470px" file="tui-demo.mp4" source="" width="300px" />

<style>
.objective {
  margin-top: 1.2rem;
  border-top: 2px solid var(--accent);
  padding-top: 0.6rem;
}
.objective p {
  font-size: 1.2rem;
  font-weight: 600;
}
</style>

<!--
TIMING: 2 minutes including the recording, hard stop 2:30.
SAY: This is the end goal in one object. The recording shows the local llama.cpp server starting, the TUI opening, one participant move, one Gemma move, the commentary, the game record, and a short replay. Its commentary is sassy as fuck. It is not Stockfish analysis and I will not sell it as one.
CLICK: 1. The objective appears. Phrase it without the double negative; prefer an actual recorded result when one exists.
SOURCE: assets/tui-recording.mp4 and assets/tui-poster.png, recorded on the presenter phone. Art of War quote optional here; record source if used.
CUT: the replay steps inside the recording can be trimmed; the object itself cannot.
FALLBACK: the video is local with a poster frame. Do not demo the phone live unless chosen on the day.
-->
