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
        Usage estimates, not total cost. Data, setup, idle time, failed
        generations, and human work are outside these totals.
      </p>
    </div>

    <div class="panel">
      <div class="panel-head">
        <span class="eyebrow">one concrete batch</span>
        <span class="batch">{{ current.batch }}</span>
      </div>

      <div class="paths">
        <div class="path">
          <span class="compare-label">machine you control</span>
          <span class="identity">{{ current.selfHosted.identity }}</span>
          <strong class="cost">{{ current.selfHosted.cost }}</strong>
          <span class="basis">{{ current.selfHosted.basis }}</span>
        </div>
        <div class="path compare-col adapted">
          <span class="compare-label">api</span>
          <span class="identity">{{ current.api.identity }}</span>
          <strong class="cost">{{ current.api.cost }}</strong>
          <span class="basis">{{ current.api.basis }}</span>
        </div>
      </div>

      <p class="takeaway">{{ current.takeaway }}</p>
      <p class="sources">{{ current.source }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { stepIndex } from "../lib/clicks";
import { COST_ROWS } from "../lib/fixtures";

const props = defineProps({
  /** Slide click count; three clicks step text, image, audio, video.
   * One modality at a time, full size, instead of four rows shrunk
   * to fit one frame. */
  clicks: { type: Number, default: 0 },
});

const rows = COST_ROWS;
const active = computed(() => stepIndex(props.clicks, rows.length));
const current = computed(() => rows[active.value]);
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

.eyebrow {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.7rem;
  text-transform: uppercase;
  color: var(--ink-faint);
}

.batch {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--ink);
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
  font-size: 0.78rem;
  color: var(--ink-soft);
}

.cost {
  margin-top: 0.25rem;
  font-size: 1.8rem;
  line-height: 1.1;
  font-weight: 600;
  color: var(--ink);
}

.basis {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.75rem;
  line-height: 1.4;
  color: var(--ink-soft);
}

.takeaway {
  margin: 1rem 0 0;
  border-top: 1px solid var(--rule);
  padding-top: 0.75rem;
  font-size: 0.95rem;
  color: var(--ink);
}

.sources {
  margin-top: 0.45rem;
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.7rem;
  line-height: 1.4;
  color: var(--ink-faint);
}
</style>
