<template>
  <div class="reward-meter">
    <div class="meter-head">
      <span class="head-label">Environment feedback</span>
      <span class="head-note">python-chess owns the rules. This function owns what they are worth.</span>
    </div>
    <div class="meter-buttons">
      <button
        v-for="outcome in outcomes"
        :key="outcome.label"
        type="button"
        class="outcome"
        @click="play(outcome)"
      >
        <span class="outcome-label">{{ outcome.label }}</span>
        <span class="outcome-reward" :class="{ negative: outcome.reward < 0 }">
          {{ outcome.reward > 0 ? "+" : "" }}{{ outcome.reward }}
        </span>
      </button>
    </div>

    <div class="meter-readout">
      <div class="last-reward" :class="{ negative: last && last.reward < 0, idle: !last }">
        {{ last ? `${last.reward > 0 ? "+" : ""}${last.reward}` : "press an outcome" }}
      </div>
      <div class="total-row">
        <span class="total-label">return</span>
        <span class="total-value" :class="{ negative: total < 0 }">{{ total }}</span>
      </div>
    </div>

    <div class="trail">
      <span
        v-for="(entry, index) in trail"
        :key="index"
        class="trail-chip"
        :class="{ negative: entry.reward < 0 }"
        >{{ entry.short }}</span
      >
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";

// Presenter-controlled by design: nothing here moves until a button
// is pressed, and remounting the slide resets to the same idle state.
const outcomes = [
  { label: "illegal move", short: "ill", reward: -1 },
  { label: "legal move", short: "ok", reward: 1 },
  { label: "check", short: "chk", reward: 2 },
  { label: "checkmate", short: "mate", reward: 10 },
];

const last = ref(null);
const total = ref(0);
const trail = ref([]);

function play(outcome) {
  last.value = outcome;
  total.value += outcome.reward;
  trail.value = [...trail.value.slice(-11), outcome];
}
</script>

<style scoped>
.reward-meter {
  max-width: 36rem;
  margin: 0 auto;
  padding: 1.2rem 1.4rem;
  background: var(--paper-raised);
  border: 1px solid var(--rule);
  border-radius: 2px;
  text-align: left;
}

.meter-head {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding-bottom: 0.8rem;
  border-bottom: 1px solid var(--ink);
  margin-bottom: 0.9rem;
}

.head-label {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--ink-faint);
}

.head-note {
  font-size: 0.85rem;
  color: var(--ink-soft);
}

.meter-buttons {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.6rem;
}

.outcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  padding: 0.6rem 0.5rem;
  background: var(--paper);
  border: 1px solid var(--rule);
  border-radius: 2px;
  cursor: pointer;
  transition: border-color 150ms var(--ease);
}

.outcome:hover {
  border-color: var(--ink);
}

.outcome:active {
  border-color: var(--accent);
}

.outcome-label {
  font-size: 0.75rem;
  color: var(--ink);
}

.outcome-reward {
  font-family: "IBM Plex Mono", monospace;
  font-weight: 600;
  color: var(--good);
}

.outcome-reward.negative {
  color: var(--bad);
}

.meter-readout {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 1rem;
  min-height: 3.4rem;
}

.last-reward {
  font-family: "IBM Plex Mono", monospace;
  font-size: 2.2rem;
  font-weight: 600;
  color: var(--good);
}

.last-reward.negative {
  color: var(--bad);
}

.last-reward.idle {
  font-size: 0.85rem;
  font-weight: 400;
  color: var(--ink-faint);
}

.total-row {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
}

.total-label {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.68rem;
  color: var(--ink-faint);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.total-value {
  font-family: "IBM Plex Mono", monospace;
  font-size: 1.6rem;
  font-weight: 600;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}

.total-value.negative {
  color: var(--bad);
}

.trail {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
  min-height: 1.5rem;
  margin-top: 0.4rem;
}

.trail-chip {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.65rem;
  padding: 0.1rem 0.5rem;
  border: 1px solid var(--good);
  border-radius: 2px;
  color: var(--good);
}

.trail-chip.negative {
  border-color: var(--bad);
  color: var(--bad);
}
</style>
