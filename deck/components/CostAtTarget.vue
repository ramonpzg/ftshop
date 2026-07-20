<template>
  <div class="cost-at-target">
    <table>
      <thead>
        <tr>
          <th>modality</th>
          <th>task</th>
          <th>target quality</th>
          <th>local base/adapted</th>
          <th>api reference</th>
          <th>cost</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in rows" :key="row.modality" :class="{ shown: index < shownRows }">
          <td>{{ row.modality }}</td>
          <td>{{ row.task }}</td>
          <td>{{ row.target }}</td>
          <td>{{ row.local }}</td>
          <td>{{ row.api }}</td>
          <td class="cost">{{ row.cost }}</td>
        </tr>
      </tbody>
    </table>
    <p class="footnote">
      Each row includes training or rental cost, hardware amortisation, request
      volume, and the quality threshold being met. Numbers are placeholders
      until checked close to the session; every final number gets a source and
      access date.
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
</script>

<style scoped>
.cost-at-target {
  max-width: 52rem;
  margin: 0 auto;
  text-align: left;
}

.cost-at-target td,
.cost-at-target th {
  font-size: 0.72rem;
  padding-right: 0.6rem;
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

.footnote {
  margin-top: 0.8rem;
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--ink-soft);
}
</style>
