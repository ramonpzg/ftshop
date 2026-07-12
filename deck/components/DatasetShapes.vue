<template>
  <div class="dataset-shapes" @mouseenter="paused = true" @mouseleave="paused = false">
    <div class="shapes-header">
      <span class="the-move">1. e4</span>
      <span class="becomes">becomes</span>
    </div>

    <transition name="shape-morph" mode="out-in">
      <div :key="active" class="shape-card">
        <div class="shape-name">{{ shapes[active].name }}</div>
        <pre class="shape-payload">{{ shapes[active].payload }}</pre>
        <div class="shape-point">{{ shapes[active].point }}</div>
      </div>
    </transition>

    <div class="shape-dots">
      <button
        v-for="(shape, index) in shapes"
        :key="shape.name"
        type="button"
        class="dot"
        :class="{ active: index === active }"
        :title="shape.name"
        @click="active = index"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from "vue";

const active = ref(0);
const paused = ref(false);
let timer = null;

const shapes = [
  {
    name: "PGN prefix -> move",
    payload: `{"prefix": "", "target_san": "e4"}`,
    point: "The model learns to continue a game script.",
  },
  {
    name: "FEN -> move",
    payload: `{"fen": "rnbqkbnr/pppppppp/8/8/8/8/\nPPPPPPPP/RNBQKBNR w KQkq - 0 1",
 "target_uci": "e2e4"}`,
    point: "The model learns positions, not histories.",
  },
  {
    name: "FEN + legal moves -> move",
    payload: `{"fen": "...", "legal_moves":
 ["a2a3","a2a4","b2b3", ...],
 "target_uci": "e2e4"}`,
    point: "The environment does the rules. The model does the choosing.",
  },
  {
    name: "Board tensor -> move class",
    payload: `{"tensor": [8x8x12 planes],
 "move_class": 796}`,
    point: "No language at all. This is AlphaZero's diet.",
  },
  {
    name: "Policy + value labels",
    payload: `{"fen": "...", "policy": {"e2e4": 0.6, ...},
 "value": 0.02}`,
    point: "Two heads: what to play, who is winning.",
  },
  {
    name: "RL trajectory",
    payload: `{"state_fen": "...", "action_uci": "e2e4",
 "reward": 1, "next_state_fen": "...",
 "done": false}`,
    point: "State, action, reward. The gym formulation.",
  },
];

onMounted(() => {
  timer = setInterval(() => {
    if (!paused.value) active.value = (active.value + 1) % shapes.length;
  }, 3200);
});

onUnmounted(() => clearInterval(timer));
</script>

<style scoped>
.dataset-shapes {
  max-width: 620px;
  margin: 0 auto;
}

.shapes-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 14px;
}

.the-move {
  font-family: ui-monospace, monospace;
  font-size: 1.6rem;
  font-weight: 700;
  color: #f59e0b;
}

.becomes {
  font-size: 0.9rem;
  color: #94a3b8;
}

.shape-card {
  padding: 18px 22px;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 12px;
  min-height: 180px;
}

.shape-name {
  font-size: 1rem;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 10px;
}

.shape-payload {
  margin: 0 0 10px;
  padding: 10px 12px;
  background: rgba(2, 6, 23, 0.6);
  border-radius: 8px;
  font-size: 0.78rem;
  line-height: 1.5;
  color: #a5b4c8;
  white-space: pre-wrap;
  word-break: break-word;
}

.shape-point {
  font-size: 0.88rem;
  color: #94a3b8;
  font-style: italic;
}

.shape-dots {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 14px;
}

.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  border: none;
  background: rgba(148, 163, 184, 0.25);
  cursor: pointer;
  padding: 0;
  transition: all 0.3s ease;
}

.dot.active {
  background: #f59e0b;
  transform: scale(1.3);
}

.shape-morph-enter-active,
.shape-morph-leave-active {
  transition: all 0.45s cubic-bezier(0.22, 1, 0.36, 1);
}

.shape-morph-enter-from {
  opacity: 0;
  transform: translateY(14px) scale(0.985);
}

.shape-morph-leave-to {
  opacity: 0;
  transform: translateY(-14px) scale(0.985);
}
</style>
