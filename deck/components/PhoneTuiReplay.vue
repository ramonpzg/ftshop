<template>
  <div class="phone-wrap">
    <div class="phone">
      <video
        v-if="!failed"
        :src="src"
        :poster="poster"
        preload="metadata"
        playsinline
        controls
        @error="failed = true"
      />
      <div v-else class="placeholder">
        <span class="ph-name">PLACEHOLDER · {{ file }}</span>
        <span class="ph-expected">
          Termux TUI recording: start the llama.cpp server, open the TUI, one
          participant move, one Gemma move, the commentary, the game record,
          a short replay. Poster frame: {{ posterFile }}.
        </span>
        <span class="ph-ratio">9:19.5</span>
      </div>
    </div>
    <span class="provenance">{{ source }}</span>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  file: { type: String, default: "tui-recording.mp4" },
  posterFile: { type: String, default: "tui-poster.png" },
  source: { type: String, default: "recorded on the presenter phone, local file" },
});

const failed = ref(false);
const src = computed(() => `/assets/${props.file}`);
const poster = computed(() => `/assets/${props.posterFile}`);
</script>

<style scoped>
.phone-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
}

/* The phone is the one dark frame in part 1: the recording is a dark
 * terminal and the bezel keeps its geometry stable. Native controls
 * give seeking, restart, and volume during the demo; no autoplay. */
.phone {
  aspect-ratio: 9 / 19.5;
  height: 340px;
  background: #211f1b;
  border: 1px solid #211f1b;
  border-radius: 14px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* contain, never cover: the plan requires the recording uncropped. */
.phone video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.placeholder {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 1rem;
  text-align: center;
}

.ph-name {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.65rem;
  letter-spacing: 0.08em;
  color: #9db4ee;
}

.ph-expected {
  font-size: 0.72rem;
  line-height: 1.45;
  color: var(--paper);
}

.ph-ratio {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.6rem;
  color: #8a8377;
}
</style>
