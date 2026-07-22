<template>
  <div class="cost-at-target">
    <div class="rail">
      <div
        v-for="(row, index) in rows"
        :key="row.modality"
        class="rail-item"
        :class="{ active: index === active, seen: index < active }"
      >
        <span class="rail-index">{{ index + 1 }}</span>
        <span class="rail-name">{{ row.modality }}</span>
      </div>
      <p class="footnote">
        Self-hosted: laptop or rented GPU you control, not physical location.
        Cells marked measured live or in session come from the room, not a
        rate card.
      </p>
    </div>

    <div class="panel">
      <div class="panel-head">
        <span class="task">{{ current.task }}</span>
        <span class="target">target: {{ current.target }}</span>
        <span class="volume">volume assumption: {{ current.volume }}</span>
      </div>

      <div class="paths">
        <div class="path">
          <span class="compare-label">self-hosted</span>
          <span class="identity">{{ current.selfHosted.identity }}</span>
          <span class="outcome">{{ current.selfHosted.outcome }}</span>
          <div class="facts">
            <span class="fact">device {{ current.selfHosted.device }}</span>
            <span class="fact">setup, amortised {{ current.selfHosted.setupCost }}</span>
            <span class="fact">latency {{ current.selfHosted.latency }}</span>
            <span class="fact">per request {{ current.selfHosted.perRequestCost }}</span>
            <span class="fact threshold" :class="thresholdClass(current.selfHosted.thresholdMet)">
              target met: {{ current.selfHosted.thresholdMet }}
            </span>
          </div>
        </div>
        <div class="path compare-col adapted">
          <span class="compare-label">api</span>
          <span class="identity">{{ current.api.identity }}</span>
          <span class="outcome">{{ current.api.outcome }}</span>
          <div class="facts">
            <span class="fact">latency {{ current.api.latency }}</span>
            <span class="fact">per request {{ current.api.perRequestCost }}</span>
            <span class="fact threshold" :class="thresholdClass(current.api.thresholdMet)">
              target met: {{ current.api.thresholdMet }}
            </span>
          </div>
        </div>
      </div>

      <p class="sources">{{ sources }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { stepIndex } from "../lib/clicks";
import { COST_ROWS, COST_SOURCES } from "../lib/fixtures";

const props = defineProps({
  /** Slide click count; three clicks step text, image, audio, video.
   * One modality at a time, full size, instead of four rows shrunk
   * to fit one frame. */
  clicks: { type: Number, default: 0 },
});

const rows = COST_ROWS;
const sources = COST_SOURCES;
const active = computed(() => stepIndex(props.clicks, rows.length));
const current = computed(() => rows[active.value]);

function thresholdClass(value) {
  if (value === "yes") return "delta-good";
  if (value === "no") return "delta-bad";
  return "";
}
</script>

<style scoped>
.cost-at-target {
  display: grid;
  grid-template-columns: 12rem 1fr;
  gap: 2rem;
  max-width: 52rem;
  margin: 0 auto;
  text-align: left;
}

.rail-item {
  display: flex;
  gap: 0.6rem;
  align-items: baseline;
  padding: 0.35rem 0;
  color: var(--ink-faint);
}

.rail-item.seen {
  color: var(--ink-soft);
}

.rail-item.active {
  color: var(--ink);
}

.rail-index {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.7rem;
  width: 1rem;
}

.rail-item.active .rail-index {
  color: var(--accent);
}

.rail-name {
  font-size: 0.95rem;
  font-weight: 500;
}

.footnote {
  margin-top: 1.2rem;
  font-size: 0.7rem;
  line-height: 1.45;
  color: var(--ink-faint);
}

/* Fixed-height panel: stepping modalities never reflows. */
.panel {
  border: 1px solid var(--rule);
  border-radius: 2px;
  background: var(--paper-raised);
  padding: 1rem 1.2rem;
  min-height: 17rem;
}

.panel-head {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  border-bottom: 1px solid var(--ink);
  padding-bottom: 0.6rem;
  margin-bottom: 0.8rem;
}

.task {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--ink);
}

.target {
  font-size: 0.85rem;
  color: var(--ink-soft);
}

.volume {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.7rem;
  color: var(--ink-faint);
}

.paths {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.4rem;
}

.path {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  border-top: 2px solid var(--rule);
  padding-top: 0.5rem;
}

.identity {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.75rem;
  color: var(--ink);
}

.outcome {
  font-size: 0.9rem;
  color: var(--ink);
}

.facts {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  margin-top: 0.2rem;
}

.fact {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.78rem;
  color: var(--ink-soft);
}

.fact.threshold {
  font-weight: 600;
}

.sources {
  margin-top: 0.8rem;
  border-top: 1px solid var(--rule);
  padding-top: 0.5rem;
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.7rem;
  line-height: 1.5;
  color: var(--ink-faint);
}
</style>
