<template>
  <figure class="media-frame" :class="{ centered }" :style="{ maxWidth: width }">
    <div
      class="stage"
      :class="{ dark, audio: kind === 'audio', capped: !!height && kind !== 'audio' }"
      :style="stageStyle"
    >
      <img
        v-if="kind === 'image' && !failed"
        :src="src"
        :alt="alt || expected"
        class="fill"
        @error="failed = true"
      />
      <video
        v-else-if="kind === 'video' && !failed"
        :src="src"
        :poster="poster || undefined"
        class="fill"
        controls
        preload="metadata"
        @error="failed = true"
      />
      <div v-else-if="kind === 'audio' && !failed" class="audio-stage">
        <audio :src="src" controls preload="metadata" @error="failed = true" />
      </div>
      <div v-else class="placeholder">
        <span class="ph-name">PLACEHOLDER · {{ file }}</span>
        <span class="ph-expected">{{ expected }}</span>
        <span v-if="kind !== 'audio'" class="ph-ratio">{{ ratio.replace("/", ":") }}</span>
      </div>
    </div>
    <figcaption class="caption-row">
      <span class="caption">{{ caption }}</span>
      <span v-if="source" class="provenance">{{ source }}</span>
    </figcaption>
  </figure>
</template>

<script setup>
import { computed, ref, watch } from "vue";

const props = defineProps({
  /** File name under deck/public/assets/. The frame renders the file
   * when it exists and a same-geometry placeholder when it does not,
   * so dropping the asset in finishes the slide. */
  file: { type: String, required: true },
  /** CSS aspect-ratio, e.g. "16/9". Fixed whether or not the asset exists. */
  ratio: { type: String, default: "16/9" },
  kind: { type: String, default: "image" },
  /** What Ramon intends to put here; shown inside the placeholder. */
  expected: { type: String, required: true },
  caption: { type: String, default: "" },
  source: { type: String, default: "" },
  poster: { type: String, default: "" },
  alt: { type: String, default: "" },
  width: { type: String, default: "100%" },
  /** Cap the stage height; width derives from the aspect ratio.
   * Portrait media must set this or it overflows the 16:9 canvas. */
  height: { type: String, default: "" },
  dark: { type: Boolean, default: false },
  /** Float the complete frame in the center of the slide. */
  centered: { type: Boolean, default: false },
});

const failed = ref(false);
const src = computed(() => `/assets/${props.file}`);
const stageStyle = computed(() => {
  if (props.kind === "audio") return {};
  if (props.height) return { aspectRatio: props.ratio, height: props.height };
  return { aspectRatio: props.ratio };
});
watch(
  () => props.file,
  () => {
    failed.value = false;
  },
);
</script>

<style scoped>
.media-frame {
  margin: 0;
  width: 100%;
}

.media-frame.centered {
  position: absolute;
  inset: 0;
  z-index: 10;
  height: max-content;
  margin: auto;
}

.stage {
  max-width: 100%;
  margin: 0 auto;
  border: 1px solid var(--rule);
  border-radius: 2px;
  background: var(--paper-raised);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stage.dark {
  background: #211f1b;
  border-color: #211f1b;
}

.stage:not(.audio) {
  width: 100%;
}

.stage.capped {
  width: auto;
}

.fill {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

/* Audio needs a control strip, not a picture frame; the stage stays
 * compact regardless of the ratio prop. */
.stage.audio {
  min-height: 3.4rem;
  padding: 0.4rem 0;
}

.stage.audio .placeholder {
  flex-direction: row;
  align-items: baseline;
  gap: 1rem;
  padding: 0.4rem 1rem;
}

.audio-stage {
  width: 100%;
  padding: 0 8%;
}

.audio-stage audio {
  width: 100%;
}

.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  text-align: center;
}

.ph-name {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.7rem;
  letter-spacing: 0.08em;
  color: var(--accent);
}

.ph-expected {
  font-size: 0.85rem;
  color: var(--ink-soft);
  max-width: 26rem;
}

.ph-ratio {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.65rem;
  color: var(--ink-faint);
}

.stage.dark .ph-expected {
  color: #f3f1ec;
}

/* The caption row is reserved even when empty, so a caption arriving
 * later cannot shift the layout. */
.caption-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 1rem;
  min-height: 1.3rem;
  margin-top: 0.4rem;
}

.caption {
  font-size: 0.8rem;
  color: var(--ink-soft);
}
</style>
