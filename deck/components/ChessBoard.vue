<template>
  <div class="board" :style="{ width: size }">
    <div
      v-for="cell in squares"
      :key="cell.square"
      class="cell"
      :class="{ light: cell.light, highlight: highlightSet.has(cell.square) }"
    >
      <span v-if="cell.glyph" class="glyph">{{ cell.glyph }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { boardFromFen } from "../lib/chess";

const props = defineProps({
  fen: { type: String, required: true },
  /** Squares to outline in the accent color, e.g. ["f1", "b5"]. */
  highlights: { type: Array, default: () => [] },
  size: { type: String, default: "300px" },
});

const squares = computed(() => boardFromFen(props.fen));
const highlightSet = computed(() => new Set(props.highlights));
</script>

<style scoped>
.board {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  aspect-ratio: 1 / 1;
  border: 1px solid var(--ink);
}

.cell {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e7e2d6;
}

.cell.light {
  background: var(--paper-raised);
}

.cell.highlight::after {
  content: "";
  position: absolute;
  inset: 6%;
  border: 2px solid var(--accent);
}

.glyph {
  font-size: 1.55em;
  line-height: 1;
  color: var(--ink);
}
</style>
