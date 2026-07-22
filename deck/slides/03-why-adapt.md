---
footer: false
class: part-opener
---

<div class="part-number">3</div>
<div class="part-title">Why adapt anything?</div>
<div class="part-sub">Economics, data, style. In that order.</div>

<!--
TIMING: 10 seconds.
SAY: The results exist. Now the reasons.
CLICK: none.
SOURCE: none.
CUT: never.
FALLBACK: static.
-->

---
clicks: 3
footer: false
---

# What does repeated use cost?

<CostAtTarget :clicks="$clicks" />

<!--
TIMING: 90 seconds.
SAY: Each click asks one question: what would this fixed batch cost? Left is a machine we control. Right is an API. These are usage estimates, not total cost, and they do not prove equal quality. Text is already cheap through an API. Local audio already worked here. The image and video numbers are rate-card arithmetic, not completed experiments.
CLICK: 3. Text is visible first; the three clicks step image, audio, video. One modality on screen at a time, readable from the back.
SOURCE: rates checked 2026-07-22: gpt-5.6-luna $1/$6 per 1M tokens (OpenRouter); FLUX.2 LoRA $0.021/MP and LTX-2-19B $0.0018 per generated megapixel-frame (fal); Eleven Music $0.15/minute (ElevenLabs); RTX 4090 $0.69/hour and H100 PCIe $2.89/hour (Runpod). LTX's report measures 1.22 seconds per 720p step on H100. Totals are derived from the workloads shown.
CUT: the audio and video steps if time is short.
FALLBACK: the structure reads without final numbers.
-->

---
footer: false
---

# Providers do not have your data

<div class="data-cols">
<div>
  <div class="compare-label">the public-ish corpus</div>
  <p>What the general model was trained on. Scraped, licensed, public, and, more recently, synthetic data.</p>
  <MediaFrame
    file="hf-synth-data.png"
    ratio="1/1"
    height="210px"
    expected="FinePhrase synthetic-data explorer screenshot."
    source="huggingface.co/spaces/HuggingFaceFW/finephrase"
  />
</div>
<div class="compare-col adapted">
  <div class="compare-label">this exact behavior</div>
  <p>The private, licensed, reviewed, or newly created examples that define
  the task. The model has not seen them.</p>
</div>
</div>

<p v-click class="reserve statement-quiet">
Hosted fine-tuning still sends data to a provider. Local ownership and
fine-tuning are related decisions, not the same decision.
</p>

<style>
.data-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  margin-top: 1rem;
}
.data-cols > div {
  border-top: 2px solid var(--rule);
  padding-top: 0.6rem;
}
</style>

<!--
TIMING: 45 seconds.
SAY: The general model has not seen the examples that define this exact behavior.
CLICK: 1. The ownership distinction.
SOURCE: none.
CUT: never.
FALLBACK: static.
-->

---
clicks: 4
---

# Providers do not know your style

<div class="style-grid">
<div v-click="1" class="reserve">
<MediaFrame
  file="goth-minions.jpg"
  ratio="4/3"
  expected="Goth Minions."
  source="Meme. Record origin and license."
/>
</div>
<div v-click="2" class="reserve style-text">
  <span class="compare-label">the lamp announcement</span>
  <div class="style-placeholder">
    PLACEHOLDER: assets/corporate-lamp.txt. The jargon-heavy paragraph about
    the new lamps on employees' desks, rendered verbatim.
  </div>
</div>
<div v-click="3" class="reserve">
<MediaFrame
  file="style-translation.mp4"
  ratio="16/9"
  kind="video"
  expected="Bachata background, or the Thinking Machines translation clip."
  source="Record source and license."
/>
</div>
<div v-click="4" class="reserve">
<MediaFrame
  file="canva-template.mp4"
  ratio="16/9"
  kind="video"
  expected="The real Canva video-template example. Carries the claim."
  source="Canva. Record source and license."
/>
</div>
</div>

<style>
/* One row, four beats, revealed left to right. Cell heights are
 * bounded so nothing leaves the 16:9 frame at 720p. */
.style-grid {
  display: grid;
  grid-template-columns: 0.9fr 1fr 1.1fr 1.1fr;
  gap: 1rem;
  margin-top: 0.5rem;
  align-items: start;
}
.style-text {
  border: 1px solid var(--rule);
  border-radius: 2px;
  background: var(--paper-raised);
  padding: 0.9rem 1.1rem;
  min-height: 10rem;
}
.style-placeholder {
  font-size: 0.8rem;
  color: var(--ink-soft);
  margin-top: 0.4rem;
}
</style>

<!--
TIMING: 75 seconds.
SAY: Style is the thing providers cannot know by default. The first three beats set up personality; the Canva template is the concrete case and lands last.
CLICK: 4. Goth Minions, the lamp paragraph, the translation clip, then Canva.
SOURCE: all four assets pending with source and license. End on Canva.
CUT: beats one to three can compress; Canva stays.
FALLBACK: placeholders keep the grid stable.
-->

---
clicks: 5
---

# The data we can actually use

<DataUniverse :clicks="$clicks" />

<!--
TIMING: 60 seconds.
SAY: Five boundaries: data we think exists, data we can access, data we can legally use, data relevant to the task, and the private or newly created data outside the public circles.
CLICK: 5. Four clicks add circles, the fifth splits the useful set into training and held-out evaluation.
SOURCE: none; the diagram is the content.
CUT: never; the split sets up every eval slide after it.
FALLBACK: static SVG, renders offline.
-->

---
layout: center
footer: false
---

# Cool bruh, what now?

<MediaFrame
  file="meme-cookie.gif"
  ratio="1/1"
  width="320px"
  expected="Chunky boy deciding which cookie to eat."
  source="Meme. Record origin and license."
/>

<!--
TIMING: 10 seconds.
SAY: Nothing. Let it breathe.
CLICK: none.
SOURCE: assets/meme-cookie.gif pending.
CUT: never. This beat releases pressure before the decision slide; no copy gets added around it.
FALLBACK: the placeholder is less funny. Land the line and move on.
-->

---

# Choose the intervention, not a tribe

<div class="options">
  <div class="option">
    <span class="option-name">Prompt</span>
    <span>for instructions that change per request</span>
  </div>
  <div class="option">
    <span class="option-name">Retrieve</span>
    <span>facts that change or need citations</span>
  </div>
  <div class="option">
    <span class="option-name">Tools</span>
    <span>rules and exact calculations</span>
  </div>
  <div class="option">
    <span class="option-name">Fine-tune</span>
    <span>repeated behavior that examples define better than prose</span>
  </div>
</div>

<p class="statement-quiet">
The chess app already combines them: python-chess owns legality, the prompt
supplies the position, an adapted model learns how to choose.
</p>

<style>
.options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-top: 1rem;
}
.option {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  border-top: 2px solid var(--ink);
  padding-top: 0.6rem;
}
.option-name {
  font-weight: 700;
  font-size: 1.15rem;
}
.option span:last-child {
  font-size: 0.9rem;
  color: var(--ink-soft);
}
</style>

<!--
TIMING: 60 seconds.
SAY: These combine. The chess app already does.
CLICK: none; the four options are compared at once.
SOURCE: none.
CUT: never.
FALLBACK: static.
-->

---
layout: center
---

<div class="statement">
Use the hosted model when it is the better tool. Own an adapted model when the
repeated task, the data, latency, or the offline requirement justifies it.
</div>

<!--
TIMING: 20 seconds.
SAY: This is the defensible version of the claim, using only examples already shown.
CLICK: none.
SOURCE: none.
CUT: never.
FALLBACK: static.
-->

---

# What the model tree may become

<MediaFrame
  file="future-tree.png"
  ratio="16/9"
  width="80%"
  expected="The future tree diagram from v1: one general model, several adapters, merged variants, local aliases, provider models."
/>

<!--
TIMING: 45 seconds. OPTIONAL: the default route skips this slide.
SAY: One general model, several adapters, merged variants, local aliases, and provider models can coexist. We are not at the effortless version of that yet.
CLICK: none.
SOURCE: assets/future-tree.png pending, redrawn from v1.
CUT: optional. Remove during delivery if it does not lead directly into the technical section.
FALLBACK: static.
-->

---
layout: center
footer: false
---

<div class="statement">
Enough preamble, let's get started.
</div>

<!--
TIMING: 10 seconds.
SAY: The line is the reset. Say it and switch context.
CLICK: none.
SOURCE: none.
CUT: never; it acknowledges the transition.
FALLBACK: static.
-->
