<template>
  <div class="live-room">
    <div class="room-header">
      <h3 class="room-title">The room, right now</h3>
      <div v-if="room" class="room-totals">
        <span class="total"
          ><strong>{{ room.playing }}</strong> playing</span
        >
        <span class="total"
          ><strong>{{ room.finished }}</strong> finished</span
        >
        <span class="total accent"
          ><strong>{{ room.total_dataset_rows }}</strong> samples</span
        >
      </div>
    </div>

    <div v-if="phase === 'unavailable'" class="room-offline" data-phase="unavailable">
      Backend offline. Start it with <code>just start</code>, this panel finds it on its own.
    </div>

    <div v-else-if="phase === 'connecting'" class="room-offline" data-phase="connecting">
      Looking for the room.
    </div>

    <div v-else-if="phase === 'recovering'" class="room-stale" data-phase="recovering">
      Reconnecting. Numbers may be stale.
    </div>

    <transition-group v-if="room" name="game-row" tag="div" class="room-games" data-phase="connected">
      <div
        v-for="game in visibleGames"
        :key="game.id"
        class="game-row"
        :class="{ playing: game.result === null }"
      >
        <span class="game-name">{{ game.user_name }}</span>
        <span class="game-status">
          {{ game.result === null ? clock(game) : shortResult(game.result) }}
        </span>
        <span class="game-moves">{{ game.legal_moves }} mv</span>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { applyPollResult, createLatestGate, INITIAL_LIVE_ROOM_STATE } from "../lib/liveRoom";

const props = defineProps({
  // Same-origin path proxied by the Slidev dev server to the backend,
  // so the deck reaches FastAPI from port 3030 without CORS.
  apiBase: { type: String, default: "/api" },
  maxGames: { type: Number, default: 8 },
});

const state = ref(INITIAL_LIVE_ROOM_STATE);
const room = computed(() => state.value.room);
const phase = computed(() => state.value.phase);
const fetchedAt = computed(() => state.value.fetchedAt);
const now = ref(Date.now());
let poll = null;
let tick = null;

// Overlapping polls resolve latest-wins: a slow older response must
// never overwrite fresher data or the recovery state.
const gate = createLatestGate();

async function load() {
  const token = gate.begin();
  try {
    const response = await fetch(`${props.apiBase}/presenter/games`);
    if (!response.ok) throw new Error(String(response.status));
    const payload = await response.json();
    if (!gate.isCurrent(token)) return;
    state.value = applyPollResult(state.value, { ok: true, room: payload, at: Date.now() });
  } catch {
    if (!gate.isCurrent(token)) return;
    state.value = applyPollResult(state.value, { ok: false });
  }
}

const visibleGames = computed(() => {
  if (!room.value) return [];
  return room.value.games.slice(0, props.maxGames);
});

function clock(game) {
  const elapsed = (now.value - fetchedAt.value) / 1000;
  const left = Math.max(0, (game.seconds_left ?? 0) - elapsed);
  const minutes = Math.floor(left / 60);
  const seconds = Math.floor(left % 60);
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function shortResult(result) {
  if (result === "win") return "win";
  if (result === "draw") return "draw";
  return "loss";
}

onMounted(() => {
  load();
  poll = setInterval(load, 3000);
  tick = setInterval(() => {
    now.value = Date.now();
  }, 1000);
});

onUnmounted(() => {
  clearInterval(poll);
  clearInterval(tick);
});
</script>

<style scoped>
.live-room {
  max-width: 640px;
  margin: 0 auto;
  padding: 20px 24px;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 12px;
}

.room-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
}

.room-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #e2e8f0;
}

.room-totals {
  display: flex;
  gap: 14px;
  font-size: 0.85rem;
  color: #94a3b8;
}

.total strong {
  color: #e2e8f0;
  font-variant-numeric: tabular-nums;
}

.total.accent strong {
  color: #f59e0b;
}

.room-offline {
  padding: 24px 0 12px;
  font-size: 0.9rem;
  color: #94a3b8;
}

.room-offline code {
  color: #f59e0b;
}

.room-stale {
  padding: 10px 0 4px;
  font-size: 0.8rem;
  color: #f59e0b;
}

.room-games {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 12px;
  max-height: 320px;
  overflow-y: auto;
}

.game-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 0.9rem;
  color: #cbd5e1;
  transition: all 0.4s ease;
}

.game-row.playing {
  background: rgba(148, 163, 184, 0.08);
}

.game-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.game-status {
  font-family: ui-monospace, monospace;
  font-weight: 600;
  color: #e2e8f0;
  font-variant-numeric: tabular-nums;
}

.game-row.playing .game-status {
  color: #f59e0b;
}

.game-moves {
  font-size: 0.75rem;
  color: #64748b;
}

.game-row-enter-active,
.game-row-leave-active {
  transition: all 0.5s ease;
}

.game-row-enter-from,
.game-row-leave-to {
  opacity: 0;
  transform: translateX(-16px);
}
</style>
