<template>
  <div class="data-universe">
    <svg viewBox="0 0 620 340" class="diagram">
      <!-- Public circles, largest first. Geometry is fixed; clicks
           toggle visibility only. -->
      <g v-for="(circle, index) in circles" :key="circle.label" :class="{ shown: index < state.circlesVisible }" class="circle-group">
        <circle
          :cx="circle.cx"
          :cy="circle.cy"
          :r="circle.r"
          fill="none"
          :stroke="circle.stroke"
          stroke-width="1.5"
        />
        <text :x="circle.lx" :y="circle.ly" :text-anchor="circle.anchor" class="label">
          {{ circle.label }}
        </text>
      </g>

      <!-- The final click splits the useful set into train and eval. -->
      <g class="split" :class="{ shown: state.splitVisible }">
        <line x1="352" y1="108" x2="352" y2="262" class="split-line" />
        <text x="322" y="292" text-anchor="end" class="split-label">TRAIN</text>
        <text x="382" y="292" text-anchor="start" class="split-label">HELD-OUT EVAL</text>
      </g>
    </svg>
    <p class="footnote" :class="{ shown: state.splitVisible }">
      The same examples do not get to prove both that we learned and that we
      generalised.
    </p>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { universeState } from "../lib/clicks";

const props = defineProps({
  /** Slide click count. The first circle is visible at zero clicks;
   * four clicks add the rest, the fifth draws the train/eval split. */
  clicks: { type: Number, default: 0 },
});

const state = computed(() => universeState(props.clicks));

const circles = [
  {
    label: "data we think exists",
    cx: 210,
    cy: 178,
    r: 148,
    lx: 96,
    ly: 48,
    anchor: "start",
    stroke: "var(--ink-faint)",
  },
  {
    label: "data we can access",
    cx: 232,
    cy: 186,
    r: 108,
    lx: 140,
    ly: 92,
    anchor: "start",
    stroke: "var(--ink-soft)",
  },
  {
    label: "data we can legally use",
    cx: 254,
    cy: 190,
    r: 76,
    lx: 196,
    ly: 128,
    anchor: "start",
    stroke: "var(--ink)",
  },
  {
    label: "data relevant to the task",
    cx: 292,
    cy: 192,
    r: 54,
    lx: 292,
    ly: 196,
    anchor: "middle",
    stroke: "var(--accent)",
  },
  {
    label: "private or newly created",
    cx: 402,
    cy: 192,
    r: 76,
    lx: 462,
    ly: 122,
    anchor: "middle",
    stroke: "var(--accent)",
  },
];
</script>

<style scoped>
.data-universe {
  max-width: 40rem;
  margin: 0 auto;
}

.diagram {
  width: 100%;
}

.circle-group,
.split {
  opacity: 0;
  transition: opacity 250ms var(--ease);
}

.circle-group.shown,
.split.shown {
  opacity: 1;
}

/* Paper halo keeps labels readable where they cross a stroke. */
.label {
  font-family: "IBM Plex Sans", sans-serif;
  font-size: 13px;
  fill: var(--ink);
  paint-order: stroke;
  stroke: var(--paper);
  stroke-width: 4px;
  stroke-linejoin: round;
}

.split-line {
  stroke: var(--accent);
  stroke-width: 2;
  stroke-dasharray: 6 4;
}

.split-label {
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  letter-spacing: 0.08em;
  fill: var(--ink);
}

.footnote {
  min-height: 1.6rem;
  font-size: 0.85rem;
  color: var(--ink-soft);
  text-align: center;
  opacity: 0;
  transition: opacity 250ms var(--ease);
  margin: 0;
}

.footnote.shown {
  opacity: 1;
}
</style>
