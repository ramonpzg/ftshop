<template>
  <div class="reward-meter">
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
      <transition name="reward-pop" mode="out-in">
        <div v-if="last" :key="stamp" class="last-reward" :class="{ negative: last.reward < 0 }">
          {{ last.reward > 0 ? "+" : "" }}{{ last.reward }}
        </div>
        <div v-else class="last-reward idle">play a move</div>
      </transition>
      <div class="total-row">
        <span class="total-label">return</span>
        <span class="total-value" :class="{ negative: total < 0 }">{{ total }}</span>
      </div>
    </div>

    <div class="trail">
      <span
        v-for="(entry, index) in trail"
        :key="index"
        class="chip"
        :class="{ negative: entry.reward < 0 }"
        >{{ entry.short }}</span
      >
    </div>

    <p class="meter-footnote">
      The whole environment: python-chess knows the rules, this function knows what they are worth.
    </p>
  </div>
</template>

<script setup>
import { ref } from "vue";

const outcomes = [
  { label: "illegal move", short: "ill", reward: -1 },
  { label: "legal move", short: "ok", reward: 1 },
  { label: "check", short: "chk", reward: 2 },
  { label: "checkmate", short: "mate", reward: 10 },
];

const last = ref(null);
const total = ref(0);
const trail = ref([]);
const stamp = ref(0);

function play(outcome) {
  last.value = outcome;
  total.value += outcome.reward;
  trail.value = [...trail.value.slice(-11), outcome];
  stamp.value += 1;
}
</script>

<style scoped>
.reward-meter {
  max-width: 560px;
  margin: 0 auto;
  padding: 20px 24px;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 12px;
}

.meter-buttons {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.outcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 8px;
  background: rgba(148, 163, 184, 0.08);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.outcome:hover {
  background: rgba(148, 163, 184, 0.16);
  transform: translateY(-2px);
}

.outcome:active {
  transform: translateY(0);
}

.outcome-label {
  font-size: 0.78rem;
  color: #cbd5e1;
}

.outcome-reward {
  font-family: ui-monospace, monospace;
  font-weight: 700;
  color: #34d399;
}

.outcome-reward.negative {
  color: #f87171;
}

.meter-readout {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 18px;
  min-height: 64px;
}

.last-reward {
  font-family: ui-monospace, monospace;
  font-size: 2.6rem;
  font-weight: 800;
  color: #34d399;
}

.last-reward.negative {
  color: #f87171;
}

.last-reward.idle {
  font-size: 1rem;
  font-weight: 400;
  color: #64748b;
  font-style: italic;
}

.total-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.total-label {
  font-size: 0.8rem;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.total-value {
  font-family: ui-monospace, monospace;
  font-size: 1.8rem;
  font-weight: 700;
  color: #e2e8f0;
  font-variant-numeric: tabular-nums;
}

.total-value.negative {
  color: #f87171;
}

.trail {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  min-height: 26px;
  margin-top: 6px;
}

.chip {
  font-family: ui-monospace, monospace;
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(52, 211, 153, 0.12);
  color: #6ee7b7;
}

.chip.negative {
  background: rgba(248, 113, 113, 0.12);
  color: #fca5a5;
}

.meter-footnote {
  margin: 14px 0 0;
  font-size: 0.82rem;
  color: #94a3b8;
  font-style: italic;
}

.reward-pop-enter-active {
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.reward-pop-enter-from {
  opacity: 0;
  transform: scale(0.4);
}

.reward-pop-leave-active {
  transition: all 0.15s ease;
}

.reward-pop-leave-to {
  opacity: 0;
}
</style>
