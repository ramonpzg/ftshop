<template>
  <div class="modality-grid">
    <div class="grid-head">
      <span></span>
      <span>pairs in</span>
      <span>adapter out</span>
      <span>eval always</span>
    </div>
    <div
      v-for="(row, index) in rows"
      :key="row.modality"
      class="grid-row"
      :class="{ shown: index < shownRows }"
    >
      <span class="modality">{{ row.modality }}</span>
      <span class="cell">{{ row.pairs }}</span>
      <span class="cell">{{ row.adapter }}</span>
      <span class="cell">{{ row.evals }}</span>
    </div>
    <div class="grid-mantra" :class="{ shown: mantraShown }">
      Same recipe. Different results.
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { revealedRows } from "../lib/clicks";

const props = defineProps({
  /** Slide click count. Rows reveal one per click, then the mantra.
   * The default shows everything, for the closing slide. */
  clicks: { type: Number, default: 5 },
});

const rows = [
  {
    modality: "text",
    pairs: "(position, move)",
    adapter: "LoRA on Gemma",
    evals: "legal move rate",
  },
  {
    modality: "image",
    pairs: "(image, caption)",
    adapter: "LoRA on FLUX",
    evals: "VLM as judge",
  },
  {
    modality: "audio",
    pairs: "(text, audio)",
    adapter: "LoRA on MusicGen",
    evals: "duration, clipping",
  },
  {
    modality: "video",
    pairs: "(Luna scene, clip)",
    adapter: "LoRA on LTX",
    evals: "case, continuity",
  },
];

const shownRows = computed(() => revealedRows(props.clicks, rows.length));
const mantraShown = computed(() => props.clicks > rows.length);
</script>

<style scoped>
.modality-grid {
  max-width: 42rem;
  margin: 0 auto;
  padding: 1.2rem 1.4rem;
  background: var(--paper-raised);
  border: 1px solid var(--rule);
  border-radius: 2px;
  text-align: left;
}

.grid-head,
.grid-row {
  display: grid;
  grid-template-columns: 0.7fr 1.2fr 1.2fr 1.2fr;
  gap: 0.8rem;
  align-items: baseline;
}

.grid-head {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-faint);
  padding-bottom: 0.6rem;
  border-bottom: 1px solid var(--ink);
}

/* Rows always occupy their space; clicks toggle visibility only. */
.grid-row {
  padding: 0.6rem 0;
  border-bottom: 1px solid var(--rule);
  opacity: 0;
  transition: opacity 250ms var(--ease);
}

.grid-row.shown {
  opacity: 1;
}

.modality {
  font-weight: 600;
  color: var(--ink);
}

.cell {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.8rem;
  color: var(--ink-soft);
}

.grid-mantra {
  margin-top: 0.9rem;
  text-align: center;
  font-size: 1rem;
  font-weight: 600;
  color: var(--ink);
  opacity: 0;
  transition: opacity 250ms var(--ease);
}

.grid-mantra.shown {
  opacity: 1;
}
</style>
