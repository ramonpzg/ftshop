<template>
  <div class="live-room">
    <div class="room-header">
      <h3 class="room-title">The room, right now</h3>
      <span class="chip" :class="{ live: phase === 'connected' }">
        {{ CHIP_LABELS[phase] }}
      </span>
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
      Backend offline. Start it with <code>just start</code>.
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
import { createSingleFlight, INITIAL_LIVE_ROOM_STATE, pollRoomOnce } from "../lib/liveRoom";

const props = defineProps({
  // Same-origin path proxied by the Slidev dev server to the backend,
  // so the deck reaches FastAPI from port 3030 without CORS.
  apiBase: { type: String, default: "/api" },
  maxGames: { type: Number, default: 8 },
});

// One label per connection phase; OFFLINE is reserved for the
// unavailable state, not the initial lookup.
const CHIP_LABELS = {
  connecting: "CONNECTING",
  connected: "LIVE",
  recovering: "RECONNECTING",
  unavailable: "OFFLINE",
};

const state = ref(INITIAL_LIVE_ROOM_STATE);
const room = computed(() => state.value.room);
const phase = computed(() => state.value.phase);
const fetchedAt = computed(() => state.value.fetchedAt);
const now = ref(Date.now());
let poll = null;
let tick = null;

// Polls are single-flight with a timeout: a request slower than the
// interval still lands (later ticks are skipped, not raced), and a
// hung request is aborted instead of blocking the loop forever.
const runPoll = createSingleFlight();

async function fetchGames(signal) {
  const response = await fetch(`${props.apiBase}/presenter/games`, { signal });
  if (!response.ok) throw new Error(String(response.status));
  return response.json();
}

function load() {
  return runPoll(async () => {
    state.value = await pollRoomOnce(fetchGames, state.value, { timeoutMs: 8000 });
  });
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
  max-width: 40rem;
  margin: 0 auto;
  padding: 1.2rem 1.4rem;
  background: var(--paper-raised);
  border: 1px solid var(--rule);
  border-radius: 2px;
  text-align: left;
}

.room-header {
  display: flex;
  align-items: baseline;
  gap: 0.8rem;
  padding-bottom: 0.7rem;
  border-bottom: 1px solid var(--ink);
}

.room-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--ink);
}

.room-totals {
  display: flex;
  gap: 0.9rem;
  margin-left: auto;
  font-size: 0.8rem;
  color: var(--ink-soft);
}

.total strong {
  color: var(--ink);
  font-family: "IBM Plex Mono", monospace;
  font-variant-numeric: tabular-nums;
}

.total.accent strong {
  color: var(--accent);
}

.room-offline {
  padding: 1.4rem 0 0.6rem;
  font-size: 0.85rem;
  color: var(--ink-soft);
}

.room-stale {
  padding: 0.6rem 0 0.2rem;
  font-size: 0.75rem;
  color: var(--bad);
}

.room-games {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  margin-top: 0.7rem;
  max-height: 300px;
  overflow-y: auto;
}

.game-row {
  display: flex;
  align-items: baseline;
  gap: 0.8rem;
  padding: 0.35rem 0.6rem;
  border-bottom: 1px solid var(--rule);
  font-size: 0.85rem;
  color: var(--ink);
  transition: opacity 250ms var(--ease);
}

.game-row.playing .game-status {
  color: var(--accent);
}

.game-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.game-status {
  font-family: "IBM Plex Mono", monospace;
  font-weight: 600;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}

.game-moves {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.7rem;
  color: var(--ink-faint);
}

.game-row-enter-active,
.game-row-leave-active {
  transition: opacity 250ms var(--ease);
}

.game-row-enter-from,
.game-row-leave-to {
  opacity: 0;
}
</style>
