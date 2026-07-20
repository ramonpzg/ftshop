<template>
  <div class="notation-morph">
    <div class="board-side">
      <ChessBoard :fen="example.positionFen" :highlights="[example.from, example.to]" size="270px" />
      <div class="position-label">{{ example.positionLabel }} The move: bishop f1 to b5.</div>
    </div>
    <div class="rep-side">
      <div
        v-for="(rep, index) in example.representations"
        :key="rep.name"
        class="rep-item"
        :class="{ active: index === active, seen: index < active }"
      >
        <span class="rep-name">{{ rep.name }}</span>
        <span class="rep-stores">{{ rep.stores }}</span>
      </div>
      <div class="rep-panel">
        <pre class="rep-value">{{ example.representations[active].value }}</pre>
        <div class="rep-point">{{ example.representations[active].point }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { NOTATION_EXAMPLE } from "../lib/chess";
import { stepIndex } from "../lib/clicks";
import ChessBoard from "./ChessBoard.vue";

const props = defineProps({
  /** Slide click count: three clicks step FEN, UCI, SAN, PGN while
   * the board and the move stay fixed. */
  clicks: { type: Number, default: 0 },
});

const example = NOTATION_EXAMPLE;
const active = computed(() => stepIndex(props.clicks, example.representations.length));
</script>

<style scoped>
.notation-morph {
  display: grid;
  grid-template-columns: 270px 1fr;
  gap: 2rem;
  max-width: 46rem;
  margin: 0 auto;
  text-align: left;
  align-items: start;
}

.position-label {
  margin-top: 0.6rem;
  font-size: 0.8rem;
  color: var(--ink-soft);
}

.rep-item {
  display: flex;
  gap: 0.8rem;
  align-items: baseline;
  padding: 0.3rem 0;
  color: var(--ink-faint);
}

.rep-item.seen {
  color: var(--ink-soft);
}

.rep-item.active {
  color: var(--ink);
}

.rep-name {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.85rem;
  font-weight: 600;
  width: 3.2rem;
}

.rep-item.active .rep-name {
  color: var(--accent);
}

.rep-stores {
  font-size: 0.85rem;
}

/* Fixed-height panel: stepping representations never reflows. */
.rep-panel {
  margin-top: 0.8rem;
  border: 1px solid var(--rule);
  border-radius: 2px;
  background: var(--paper-raised);
  padding: 0.9rem 1.1rem;
  min-height: 8.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.rep-value {
  margin: 0;
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.8rem;
  line-height: 1.5;
  color: var(--ink);
  white-space: pre-wrap;
  word-break: break-all;
}

.rep-point {
  margin-top: auto;
  font-size: 0.82rem;
  color: var(--ink-soft);
  border-top: 1px solid var(--rule);
  padding-top: 0.5rem;
}
</style>
