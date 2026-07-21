---
footer: false
class: part-opener
---

<div class="part-number">2</div>
<div class="part-title">Four adaptation problems, one domain</div>

<div class="opener-modalities">
  <span v-click class="reserve">Text</span>
  <span v-click class="reserve">Image</span>
  <span v-click class="reserve">Audio</span>
  <span v-click class="reserve">Video</span>
</div>

<style>
.opener-modalities {
  display: flex;
  gap: 2.2rem;
  margin-top: 1.6rem;
  font-family: "IBM Plex Mono", monospace;
  font-size: 1.1rem;
  color: var(--accent);
}
</style>

<!--
TIMING: 30 seconds.
SAY: These are four adaptation problems, not necessarily four model processes. The text path alone may use a player model and a scenario writer.
CLICK: 4. One modality name per click.
SOURCE: none.
CUT: never; this frames part 2.
FALLBACK: static.
-->

---

# Text can do more than choose a move

<div class="mapping-grid">
<MediaFrame
  file="mapping-game.png"
  ratio="4/5"
  expected="A completed board and its game log, the same artifact the three mapping slides reuse."
/>
<div v-click class="reserve mapping-panel">
  <span class="compare-label">real-world mapping</span>
  <div class="mapping-placeholder">
    PLACEHOLDER: one detailed real-world mapping of this exact game, written by
    the scenario workflow. Situation at work, at home, or in sport.
  </div>
  <span class="provenance">scenario writer: gpt-5.6-luna · prompt version pending · CACHED, date pending</span>
</div>
</div>

<style>
.mapping-grid {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 2.5rem;
  align-items: start;
  margin-top: 0.3rem;
}
.mapping-panel {
  border: 1px solid var(--rule);
  border-radius: 2px;
  background: var(--paper-raised);
  padding: 1rem 1.2rem;
  min-height: 12rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}
.mapping-placeholder {
  font-size: 0.95rem;
  color: var(--ink-soft);
}
.mapping-panel .provenance {
  margin-top: auto;
}
</style>

<!--
TIMING: 45 seconds.
SAY: The game model chooses moves. A separate text workflow can map the same sequence to a situation at work, at home, or in sport. Those mappings can become their own reviewed dataset.
CLICK: 1. The mapping panel appears next to the fixed game.
SOURCE: Luna is the scenario writer and is labelled as such. This output is never called a fine-tuned chess model result.
CUT: never; slides 11 to 13 depend on this framing.
FALLBACK: placeholders carry the structure.
-->

---

# Mapping one: work

<div class="mapping-grid">
<MediaFrame
  file="mapping-game.png"
  ratio="4/5"
  expected="Same completed board and game log as the previous slide, same position on screen."
/>
<div class="mapping-panel">
  <span class="compare-label">raw mapping</span>
  <div class="mapping-placeholder">
    PLACEHOLDER: mapping one, the exact game or final FEN plus the raw model
    mapping. A workplace situation.
  </div>
  <div v-click class="reserve edited">
    <span class="compare-label">approved edit</span>
    <div class="mapping-placeholder">
      PLACEHOLDER: the approved edit, shown only where it differs from the raw
      mapping.
    </div>
  </div>
  <span class="provenance">scenario writer: gpt-5.6-luna · prompt version pending · CACHED, date pending</span>
</div>
</div>

<style>
.mapping-grid {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 2.5rem;
  align-items: start;
  margin-top: 0.3rem;
}
.mapping-panel {
  border: 1px solid var(--rule);
  border-radius: 2px;
  background: var(--paper-raised);
  padding: 1rem 1.2rem;
  min-height: 14rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}
.mapping-placeholder {
  font-size: 0.9rem;
  color: var(--ink-soft);
}
.edited {
  border-top: 2px solid var(--accent);
  padding-top: 0.6rem;
}
.mapping-panel .provenance {
  margin-top: auto;
}
</style>

<!--
TIMING: 45 seconds.
SAY: The board and log do not move. Only the description changes. That change is the event.
CLICK: 1. The approved edit appears under the raw mapping.
SOURCE: exact game or final FEN pending; model and prompt version in the disclosure line. No chess pieces in any later video prompt derived from this.
CUT: one or two of the three mappings can be skipped without breaking the argument.
FALLBACK: placeholders carry the structure.
-->

---

# Mapping two: home

<div class="mapping-grid">
<MediaFrame
  file="mapping-game.png"
  ratio="4/5"
  expected="Same completed board and game log, same position on screen."
/>
<div class="mapping-panel">
  <span class="compare-label">raw mapping</span>
  <div class="mapping-placeholder">
    PLACEHOLDER: mapping two, the exact game or final FEN plus the raw model
    mapping. A situation at home.
  </div>
  <div v-click class="reserve edited">
    <span class="compare-label">approved edit</span>
    <div class="mapping-placeholder">
      PLACEHOLDER: the approved edit where it differs.
    </div>
  </div>
  <span class="provenance">scenario writer: gpt-5.6-luna · prompt version pending · CACHED, date pending</span>
</div>
</div>

<style>
.mapping-grid {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 2.5rem;
  align-items: start;
  margin-top: 0.3rem;
}
.mapping-panel {
  border: 1px solid var(--rule);
  border-radius: 2px;
  background: var(--paper-raised);
  padding: 1rem 1.2rem;
  min-height: 14rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}
.mapping-placeholder {
  font-size: 0.9rem;
  color: var(--ink-soft);
}
.edited {
  border-top: 2px solid var(--accent);
  padding-top: 0.6rem;
}
.mapping-panel .provenance {
  margin-top: auto;
}
</style>

<!--
TIMING: 45 seconds. OPTIONAL: the default route skips this slide.
SAY: Same game, different life. The mapping is the variable.
CLICK: 1. The approved edit appears.
SOURCE: as mapping one.
CUT: skippable.
FALLBACK: placeholders carry the structure.
-->

---

# Mapping three: sport

<div class="mapping-grid">
<MediaFrame
  file="mapping-game.png"
  ratio="4/5"
  expected="Same completed board and game log, same position on screen."
/>
<div class="mapping-panel">
  <span class="compare-label">raw mapping</span>
  <div class="mapping-placeholder">
    PLACEHOLDER: mapping three, the exact game or final FEN plus the raw model
    mapping. A situation in sport.
  </div>
  <div v-click class="reserve edited">
    <span class="compare-label">approved edit</span>
    <div class="mapping-placeholder">
      PLACEHOLDER: the approved edit where it differs.
    </div>
  </div>
  <span class="provenance">scenario writer: gpt-5.6-luna · prompt version pending · CACHED, date pending</span>
</div>
</div>

<style>
.mapping-grid {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 2.5rem;
  align-items: start;
  margin-top: 0.3rem;
}
.mapping-panel {
  border: 1px solid var(--rule);
  border-radius: 2px;
  background: var(--paper-raised);
  padding: 1rem 1.2rem;
  min-height: 14rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}
.mapping-placeholder {
  font-size: 0.9rem;
  color: var(--ink-soft);
}
.edited {
  border-top: 2px solid var(--accent);
  padding-top: 0.6rem;
}
.mapping-panel .provenance {
  margin-top: auto;
}
</style>

<!--
TIMING: 45 seconds. OPTIONAL: the default route skips this slide.
SAY: Third and last. The same sequence reads as a match under pressure.
CLICK: 1. The approved edit appears.
SOURCE: as mapping one.
CUT: skippable.
FALLBACK: placeholders carry the structure.
-->

---

# Image adaptation

<div class="image-pair">
<div>
  <div class="compare-label">BASE</div>
  <div v-click class="reserve">
  <MediaFrame
    file="image-base.png"
    ratio="1/1"
    expected="Base model output: an actual board and pieces, one specific theme."
  />
  </div>
</div>
<div class="compare-col adapted">
  <div class="compare-label">ADAPTED</div>
  <div v-click class="reserve">
  <MediaFrame
    file="image-adapted.png"
    ratio="1/1"
    expected="Adapted output, same prompt where possible."
  />
  </div>
</div>
<div>
  <div class="compare-label">SECOND STYLE</div>
  <div v-click class="reserve">
  <MediaFrame
    file="image-style-2.png"
    ratio="1/1"
    expected="A second style, only if it earns the time."
  />
  </div>
</div>
</div>

<div class="provenance">
same prompt where possible · adapter/model identity, seed, dimensions pending ·
piece-identity check, style-adherence check pending
</div>

<style>
.image-pair {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 1.5rem;
  margin-top: 0.5rem;
}
</style>

<!--
TIMING: 60 seconds.
SAY: The useful question is not whether it looks cool. The pieces still need to be identifiable and the style needs to hold across the full set.
CLICK: 3. Base output, adapted output, then a second style if it earns the time.
SOURCE: evidence line pending: same prompt, adapter identity, seed, dimensions, identity and style checks.
CUT: the third click.
FALLBACK: placeholders keep all three frames.
-->

---

# Audio adaptation

<div class="audio-grid">
<div class="audio-board">
  <ChessBoard fen="r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3" size="230px" />
  <div class="provenance">the position the sounds belong to</div>
</div>
<div class="audio-rows">
  <div v-click class="reserve audio-row">
    <span class="compare-label">capture sound</span>
    <MediaFrame file="audio-capture.wav" ratio="16/3" kind="audio" expected="A capture: wooden piece landing on wood." />
  </div>
  <div v-click class="reserve audio-row">
    <span class="compare-label">background, one genre</span>
    <MediaFrame file="audio-genre.wav" ratio="16/3" kind="audio" expected="Background music in one genre. MusicGen local path." />
  </div>
  <div v-click class="reserve audio-row">
    <span class="compare-label">spoken move, optional</span>
    <MediaFrame file="audio-move.wav" ratio="16/3" kind="audio" expected="A spoken move announcement." />
  </div>
</div>
</div>

<style>
.audio-grid {
  display: grid;
  grid-template-columns: 230px 1fr;
  gap: 2.5rem;
  align-items: start;
  margin-top: 0.3rem;
}
.audio-row {
  margin-bottom: 0.5rem;
}
.audio-row .compare-label {
  display: block;
  margin-bottom: 0.2rem;
}
</style>

<!--
TIMING: 45 seconds.
SAY: Audio can cover captures, music, room tone, or speech. These are different tasks and are not one adapter doing everything.
CLICK: 3. Capture sound, background genre, optional spoken move. Nothing autoplays; each row has its own control.
SOURCE: MusicGen is enough for the local path; Stable Audio optional. Files pending with provenance.
CUT: the third click.
FALLBACK: placeholders keep the rows; the board renders locally.
-->

---

# Video from the real-world case

<div class="video-grid">
<div v-click class="reserve scene-panel">
  <span class="compare-label">scene prompt</span>
  <div class="scene-placeholder">
    PLACEHOLDER: the detailed Luna scene description for one mapping. Camera,
    light, sound. No board, no pieces, no move notation.
  </div>
  <span class="provenance">scenario writer: gpt-5.6-luna · CACHED, date pending</span>
</div>
<div v-click class="reserve">
<MediaFrame
  file="video-scene.mp4"
  ratio="16/9"
  kind="video"
  poster="/assets/video-scene-poster.png"
  expected="The generated clip staging that case. LTX or the configured API video path."
/>
</div>
</div>

<style>
.video-grid {
  display: grid;
  grid-template-columns: 1fr 1.3fr;
  gap: 2rem;
  align-items: start;
  margin-top: 0.3rem;
}
.scene-panel {
  border: 1px solid var(--rule);
  border-radius: 2px;
  background: var(--paper-raised);
  padding: 1rem 1.2rem;
  min-height: 12rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}
.scene-placeholder {
  font-size: 0.9rem;
  color: var(--ink-soft);
}
.scene-panel .provenance {
  margin-top: auto;
}
</style>

<!--
TIMING: 60 seconds.
SAY: The video model stages the real-world situation. It is not trying to animate a chess move. That looked bad and was not the interesting part anyway.
CLICK: 2. The scene prompt first, then the clip with its poster. Playback is manual.
SOURCE: LTX, Gemini, or another video model; identity recorded with the file. The generated scene contains no board, pieces, or move notation unless the source mapping requires one.
CUT: playback can be skipped; the poster carries the point.
FALLBACK: poster and placeholder keep the geometry.
-->

---

# Which one was adapted? Text

<div class="ab-grid">
<div>
  <div class="compare-label">A</div>
  <MediaFrame file="ab-text-a.png" ratio="16/10" expected="Model reply A for the same position, rendered as text." />
</div>
<div>
  <div class="compare-label">B</div>
  <MediaFrame file="ab-text-b.png" ratio="16/10" expected="Model reply B for the same position." />
</div>
</div>

<details class="ab-answer">
<summary>Answer</summary>
<p>PLACEHOLDER: answer and pair provenance. Model card, adapter, license,
input, parameters. If the pair does not share a controlled input, it is an
adapted/reference pair, not a before/after experiment.</p>
</details>

<style>
.ab-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  margin-top: 0.5rem;
}
.ab-answer {
  margin-top: 0.9rem;
  min-height: 2.6rem;
  font-size: 0.85rem;
  color: var(--ink-soft);
  border-top: 2px solid var(--accent);
  padding-top: 0.5rem;
}
</style>

<!--
TIMING: 30 seconds.
SAY: Which is base and which is adapted?
CLICK: none. The Answer disclosure sits outside the Slidev click sequence, so a presenter clicker (ArrowRight/PageDown) advances past it without opening it; default is to hold answers for the combined reveal. If the room is quiet, open it directly (click, or Enter when focused) and keep moving.
SOURCE: only an actual adapted/reference pair fills this slide; provenance pending.
CUT: any of the four A/B slides can be skipped independently.
FALLBACK: placeholders keep the frames.
-->

---

# Which one was adapted? Image

<div class="ab-grid">
<div>
  <div class="compare-label">A</div>
  <MediaFrame file="ab-image-a.png" ratio="1/1" expected="Generated board image A, same prompt as B." />
</div>
<div>
  <div class="compare-label">B</div>
  <MediaFrame file="ab-image-b.png" ratio="1/1" expected="Generated board image B." />
</div>
</div>

<details class="ab-answer">
<summary>Answer</summary>
<p>PLACEHOLDER: answer and pair provenance.</p>
</details>

<style>
.ab-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  max-width: 30rem;
  margin: 0.5rem auto 0;
}
.ab-answer {
  margin-top: 0.9rem;
  min-height: 2.6rem;
  font-size: 0.85rem;
  color: var(--ink-soft);
  border-top: 2px solid var(--accent);
  padding-top: 0.5rem;
}
</style>

<!--
TIMING: 30 seconds.
SAY: Same prompt, two sets of pieces.
CLICK: none. Answer sits outside the click sequence, same policy as the text pair.
SOURCE: pair provenance pending.
CUT: skippable.
FALLBACK: placeholders keep the frames.
-->

---

# Which one was adapted? Audio

<div class="ab-audio">
<div>
  <div class="compare-label">A</div>
  <MediaFrame file="ab-audio-a.wav" ratio="16/3" kind="audio" expected="Clip A for the same text prompt." />
</div>
<div>
  <div class="compare-label">B</div>
  <MediaFrame file="ab-audio-b.wav" ratio="16/3" kind="audio" expected="Clip B for the same text prompt." />
</div>
</div>

<details class="ab-answer">
<summary>Answer</summary>
<p>PLACEHOLDER: answer and pair provenance.</p>
</details>

<style>
.ab-audio {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-width: 34rem;
  margin: 0.5rem auto 0;
}
.ab-answer {
  max-width: 34rem;
  margin: 0.9rem auto 0;
  min-height: 2.6rem;
  font-size: 0.85rem;
  color: var(--ink-soft);
  border-top: 2px solid var(--accent);
  padding-top: 0.5rem;
}
</style>

<!--
TIMING: 30 seconds, both clips play once.
SAY: Two clips, one text prompt.
CLICK: none. Answer sits outside the click sequence, same policy.
SOURCE: pair provenance pending. No autoplay.
CUT: skippable.
FALLBACK: placeholders keep the rows.
-->

---

# Which one was adapted? Video

<div class="ab-grid">
<div>
  <div class="compare-label">A</div>
  <MediaFrame file="ab-video-a.mp4" ratio="16/9" kind="video" expected="Scene clip A, same saved prompt as B. No chess objects." />
</div>
<div>
  <div class="compare-label">B</div>
  <MediaFrame file="ab-video-b.mp4" ratio="16/9" kind="video" expected="Scene clip B." />
</div>
</div>

<details class="ab-answer">
<summary>Answer</summary>
<p>PLACEHOLDER: answer and pair provenance.</p>
</details>

<style>
.ab-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  margin-top: 0.5rem;
}
.ab-answer {
  margin-top: 0.9rem;
  min-height: 2.6rem;
  font-size: 0.85rem;
  color: var(--ink-soft);
  border-top: 2px solid var(--accent);
  padding-top: 0.5rem;
}
</style>

<!--
TIMING: 30 seconds; play the clips only if the room is engaged.
SAY: Same saved scene prompt, two clips.
CLICK: none. Answer sits outside the click sequence, same policy.
SOURCE: pair provenance pending.
CUT: skippable.
FALLBACK: posters and placeholders keep the frames.
-->

---
clicks: 4
---

# The reveal

<table class="reveal-table">
  <thead>
    <tr>
      <th>modality</th>
      <th>answer</th>
      <th>target behavior</th>
      <th>metric (n)</th>
      <th>provenance</th>
      <th>got worse</th>
    </tr>
  </thead>
  <tbody>
    <tr v-click="1">
      <td>text</td><td>--</td><td>--</td><td>--</td><td>PENDING</td><td>--</td>
    </tr>
    <tr v-click="2">
      <td>image</td><td>--</td><td>--</td><td>--</td><td>PENDING</td><td>--</td>
    </tr>
    <tr v-click="3">
      <td>audio</td><td>--</td><td>--</td><td>--</td><td>PENDING</td><td>--</td>
    </tr>
    <tr v-click="4">
      <td>video</td><td>--</td><td>--</td><td>--</td><td>PENDING</td><td>--</td>
    </tr>
  </tbody>
</table>

<p class="reveal-note">
At least one adapted result improves its target and gets worse somewhere else.
Fine-tuning is a trade.
</p>

<style>
.reveal-table td {
  font-size: 0.78rem;
}
.reveal-table tbody tr {
  transition: opacity 250ms var(--ease);
}
.reveal-table tbody tr.slidev-vclick-hidden {
  opacity: 0;
  visibility: hidden;
  transform: none;
}
.reveal-note {
  margin-top: 1rem;
  font-size: 0.9rem;
  color: var(--ink-soft);
}
</style>

<!--
TIMING: 75 seconds.
SAY: One row per modality: the answer, the exact target behavior, one metric with its sample size, cached or live provenance, and one limitation or regression.
CLICK: 4. One row per click, fixed modality order.
SOURCE: every cell lands with the accepted phase 34 evidence or from recorded pairs; nothing here is invented in the meantime.
CUT: never; this is the payoff of the four questions.
FALLBACK: the structure reads even before the data lands.
-->
