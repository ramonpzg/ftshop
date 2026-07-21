<template>
  <div class="outcome-compare">
    <div class="task-row">
      <span class="task">{{ fixture.task }}</span>
      <span class="chip">{{ fixture.provenance }}</span>
    </div>
    <div class="input-row">
      <span class="input-label">input</span>
      <span class="input-value">{{ fixture.input }}</span>
    </div>

    <div class="columns">
      <div class="col" :class="{ shown: state.baseVisible }">
        <div class="compare-label">{{ fixture.baseLabel }}</div>
        <div class="output">{{ fixture.baseOutput }}</div>
      </div>
      <div class="col adapted" :class="{ shown: state.adaptedVisible }">
        <div class="compare-label">{{ fixture.adaptedLabel }}</div>
        <div class="output">{{ fixture.adaptedOutput }}</div>
      </div>
    </div>

    <table class="metrics">
      <thead>
        <tr>
          <th>metric</th>
          <th :class="{ dim: !state.baseVisible }">base</th>
          <th :class="{ dim: !state.adaptedVisible }">adapted</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="metric in fixture.metrics" :key="metric.name">
          <td>{{ metric.name }}</td>
          <td :class="{ dim: !state.baseVisible }">{{ state.baseVisible ? metric.base : "" }}</td>
          <td
            :class="{
              dim: !state.adaptedVisible,
              good: metric.delta === 'good',
              bad: metric.delta === 'bad',
            }"
          >
            {{ state.adaptedVisible ? metric.adapted : "" }}
          </td>
        </tr>
      </tbody>
    </table>

    <div class="regression" :class="{ shown: state.adaptedVisible }">
      <span class="regression-label">got worse</span>
      <span>{{ fixture.regression }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { compareState } from "../lib/clicks";
import { TEXT_COMPARE_FIXTURE } from "../lib/fixtures";

const props = defineProps({
  /** Slide click count: click 1 shows the base column, click 2 the
   * adapted column, its deltas, and the regression row. */
  clicks: { type: Number, default: 0 },
  fixture: { type: Object, default: () => TEXT_COMPARE_FIXTURE },
});

const state = computed(() => compareState(props.clicks));
</script>

<style scoped>
.outcome-compare {
  max-width: 44rem;
  margin: 0 auto;
  text-align: left;
}

.task-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.task {
  font-weight: 600;
  color: var(--ink);
}

.input-row {
  display: flex;
  gap: 0.8rem;
  align-items: baseline;
  border-top: 1px solid var(--ink);
  padding: 0.5rem 0;
}

.input-label {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--ink-faint);
}

.input-value {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.8rem;
  color: var(--ink-soft);
}

/* Both columns are laid out from click zero; reveals change opacity
 * only, never geometry. */
.columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin: 0.6rem 0 1rem;
}

.col {
  border-top: 2px solid var(--rule);
  padding-top: 0.5rem;
  opacity: 0;
  transition: opacity 250ms var(--ease);
  min-height: 4.6rem;
}

.col.adapted {
  border-top-color: var(--accent);
}

.col.shown {
  opacity: 1;
}

.output {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.85rem;
  color: var(--ink);
  margin-top: 0.4rem;
  white-space: pre-wrap;
}

.metrics th.dim,
.metrics td.dim {
  color: transparent;
}

.metrics td.good {
  color: var(--good);
}

.metrics td.bad {
  color: var(--bad);
}

.regression {
  display: flex;
  gap: 0.8rem;
  align-items: baseline;
  margin-top: 0.8rem;
  min-height: 1.6rem;
  opacity: 0;
  transition: opacity 250ms var(--ease);
}

.regression.shown {
  opacity: 1;
}

.regression-label {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--bad);
}

.regression span:last-child {
  font-size: 0.85rem;
  color: var(--ink-soft);
}
</style>
