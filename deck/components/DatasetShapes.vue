<template>
  <div class="dataset-shapes">
    <div class="rail">
      <div class="the-move">1. e4</div>
      <div
        v-for="(shape, index) in shapes"
        :key="shape.name"
        class="rail-item"
        :class="{ active: index === active, seen: index < active }"
      >
        <span class="rail-index">{{ index + 1 }}</span>
        <span class="rail-name">{{ shape.name }}</span>
      </div>
    </div>
    <div class="panel">
      <pre class="payload">{{ shapes[active].payload }}</pre>
      <div class="point">{{ shapes[active].point }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { stepIndex } from "../lib/clicks";
import { DATASET_SHAPES } from "../lib/datasetShapes";

const props = defineProps({
  /** Slide click count; the slide declares `clicks: 5` so the five
   * presenter clicks step through all six encodings. */
  clicks: { type: Number, default: 0 },
});

const shapes = DATASET_SHAPES;
const active = computed(() => stepIndex(props.clicks, shapes.length));
</script>

<style scoped>
.dataset-shapes {
  display: grid;
  grid-template-columns: 15rem 1fr;
  gap: 1.6rem;
  max-width: 46rem;
  margin: 0 auto;
  text-align: left;
}

.the-move {
  font-family: "IBM Plex Mono", monospace;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--ink);
  border-bottom: 1px solid var(--ink);
  padding-bottom: 0.5rem;
  margin-bottom: 0.7rem;
}

.rail-item {
  display: flex;
  gap: 0.6rem;
  align-items: baseline;
  padding: 0.32rem 0;
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
  font-size: 0.88rem;
  font-weight: 500;
}

/* The panel reserves its full height so stepping never reflows. */
.panel {
  border: 1px solid var(--rule);
  border-radius: 2px;
  background: var(--paper-raised);
  padding: 1rem 1.2rem;
  min-height: 15rem;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.payload {
  margin: 0;
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.82rem;
  line-height: 1.55;
  color: var(--ink);
  white-space: pre-wrap;
  word-break: break-word;
}

.point {
  margin-top: auto;
  font-size: 0.85rem;
  color: var(--ink-soft);
  border-top: 1px solid var(--rule);
  padding-top: 0.6rem;
  min-height: 3.4rem;
}
</style>
