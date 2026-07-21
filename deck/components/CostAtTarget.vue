<template>
  <div class="cost-at-target">
    <div
      v-for="(row, index) in rows"
      :key="row.modality"
      class="row-card"
      :class="{ shown: index < shownRows }"
    >
      <div class="row-head">
        <span class="modality">{{ row.modality }}</span>
        <span class="task">{{ row.task }} · target: {{ row.target }}</span>
        <span class="setup">
          device {{ row.device }} · setup {{ row.setupCost }} · volume {{ row.volume }}
        </span>
      </div>

      <div class="paths">
        <div class="path">
          <span class="compare-label">self-hosted</span>
          <div class="path-facts">
            <span class="outcome">{{ row.selfHosted.outcome }}</span>
            <div class="fact-row">
              <span class="fact">latency {{ row.selfHosted.latency }}</span>
              <span class="fact">/req {{ row.selfHosted.perRequestCost }}</span>
              <span class="fact threshold" :class="thresholdClass(row.selfHosted.thresholdMet)">
                met: {{ row.selfHosted.thresholdMet }}
              </span>
            </div>
          </div>
        </div>
        <div class="path compare-col adapted">
          <span class="compare-label">api</span>
          <div class="path-facts">
            <span class="outcome">{{ row.api.outcome }}</span>
            <div class="fact-row">
              <span class="fact">latency {{ row.api.latency }}</span>
              <span class="fact">/req {{ row.api.perRequestCost }}</span>
              <span class="fact threshold" :class="thresholdClass(row.api.thresholdMet)">
                met: {{ row.api.thresholdMet }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <p class="footnote">
      Self-hosted: laptop or rented GPU you control, not physical location.
      Placeholders until checked close to the session; every number gets a
      source and access date.
    </p>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { revealedRows } from "../lib/clicks";
import { COST_ROWS } from "../lib/fixtures";

const props = defineProps({
  /** Slide click count; one row per click, in the fixed modality order. */
  clicks: { type: Number, default: 0 },
});

const rows = COST_ROWS;
const shownRows = computed(() => revealedRows(props.clicks, rows.length));

function thresholdClass(value) {
  if (value === "yes") return "delta-good";
  if (value === "no") return "delta-bad";
  return "";
}
</script>

<style scoped>
.cost-at-target {
  max-width: 46rem;
  margin: 0 auto;
  text-align: left;
}

.row-card {
  border-top: 1px solid var(--rule);
  padding: 0.22rem 0;
  opacity: 0;
  transition: opacity 250ms var(--ease);
}

.row-card.shown {
  opacity: 1;
}

.row-card:first-child {
  border-top: none;
}

.row-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.6rem;
  margin-bottom: 0.12rem;
  line-height: 1.15;
}

.modality {
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--ink);
}

.task {
  font-size: 0.7rem;
  color: var(--ink-soft);
}

.setup {
  margin-left: auto;
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.58rem;
  color: var(--ink-faint);
}

.paths {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.path {
  border-top: 2px solid var(--rule);
  padding-top: 0.12rem;
  line-height: 1.15;
}

.path-facts {
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
  margin-top: 0.08rem;
}

.outcome {
  font-size: 0.72rem;
  color: var(--ink);
}

.fact-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.fact {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.6rem;
  color: var(--ink-soft);
}

.fact.threshold {
  font-weight: 600;
}

.footnote {
  margin-top: 0.25rem;
  font-size: 0.56rem;
  line-height: 1.25;
  color: var(--ink-faint);
}
</style>
