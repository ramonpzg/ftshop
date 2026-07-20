<template>
  <div class="cost-at-target">
    <table>
      <thead>
        <tr>
          <th>modality</th>
          <th>task and target</th>
          <th>local setup, amortised</th>
          <th>local /req</th>
          <th>api /req</th>
          <th>volume</th>
          <th>target met</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in rows" :key="row.modality" :class="{ shown: index < shownRows }">
          <td>{{ row.modality }}</td>
          <td>
            <span class="task">{{ row.task }}</span>
            <span class="target">{{ row.target }}</span>
          </td>
          <td class="cost">{{ row.localSetup }}</td>
          <td class="cost">{{ row.localPerRequest }}</td>
          <td class="cost">{{ row.apiPerRequest }}</td>
          <td>{{ row.volume }}</td>
          <td>{{ row.thresholdMet }}</td>
        </tr>
      </tbody>
    </table>
    <p class="paths">{{ paths }}</p>
    <p class="footnote">
      Setup cost carries its amortisation basis; per-request costs are marginal;
      the volume column states the assumption the amortisation uses. Values are
      placeholders until checked close to the session; every final number gets a
      source and access date.
    </p>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { revealedRows } from "../lib/clicks";
import { COST_PATHS, COST_ROWS } from "../lib/fixtures";

const props = defineProps({
  /** Slide click count; one row per click, in the fixed modality order. */
  clicks: { type: Number, default: 0 },
});

const rows = COST_ROWS;
const paths = COST_PATHS;
const shownRows = computed(() => revealedRows(props.clicks, rows.length));
</script>

<style scoped>
.cost-at-target {
  max-width: 54rem;
  margin: 0 auto;
  text-align: left;
}

.cost-at-target td,
.cost-at-target th {
  font-size: 0.7rem;
  padding-right: 0.5rem;
}

.task {
  display: block;
}

.target {
  display: block;
  color: var(--ink-soft);
  font-size: 0.62rem;
}

/* Rows keep their space; reveal is visibility only. */
tbody tr {
  opacity: 0;
  transition: opacity 250ms var(--ease);
}

tbody tr.shown {
  opacity: 1;
}

.cost {
  color: var(--accent);
}

.paths {
  margin-top: 0.7rem;
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.65rem;
  color: var(--ink-faint);
}

.footnote {
  margin-top: 0.4rem;
  font-size: 0.72rem;
  line-height: 1.5;
  color: var(--ink-soft);
}
</style>
