<template>
  <div class="modality-grid">
    <div class="grid-head">
      <span></span>
      <span>pairs in</span>
      <span>adapter out</span>
      <span>eval always</span>
    </div>
    <div
      v-for="(row, index) in rows"
      :key="row.modality"
      class="grid-row"
      :class="{ appear: appeared[index] }"
    >
      <span class="modality">{{ row.modality }}</span>
      <span class="cell">{{ row.pairs }}</span>
      <span class="cell">{{ row.adapter }}</span>
      <span class="cell">{{ row.evals }}</span>
    </div>
    <div class="grid-mantra" :class="{ appear: appeared[rows.length] }">
      Same recipe. Different results.
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";

const props = defineProps({
  stagger: { type: Number, default: 550 },
});

const rows = [
  {
    modality: "text",
    pairs: "(position, move)",
    adapter: "LoRA on Gemma",
    evals: "legal move rate",
  },
  {
    modality: "image",
    pairs: "(image, caption)",
    adapter: "LoRA on FLUX",
    evals: "VLM as judge",
  },
  {
    modality: "audio",
    pairs: "(text, audio)",
    adapter: "LoRA on MusicGen",
    evals: "duration, clipping",
  },
  {
    modality: "video",
    pairs: "(video, caption)",
    adapter: "LoRA on LTX",
    evals: "temporal flicker",
  },
];

const appeared = ref({});

onMounted(() => {
  for (let index = 0; index <= rows.length; index += 1) {
    setTimeout(() => {
      appeared.value[index] = true;
    }, 400 + index * props.stagger);
  }
});
</script>

<style scoped>
.modality-grid {
  max-width: 680px;
  margin: 0 auto;
  padding: 20px 24px;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 12px;
}

.grid-head,
.grid-row {
  display: grid;
  grid-template-columns: 0.7fr 1.2fr 1.2fr 1.2fr;
  gap: 12px;
  align-items: baseline;
}

.grid-head {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
}

.grid-row {
  padding: 10px 0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.07);
  opacity: 0;
  transform: translateX(-18px);
  transition: all 0.55s cubic-bezier(0.22, 1, 0.36, 1);
}

.grid-row.appear {
  opacity: 1;
  transform: translateX(0);
}

.modality {
  font-weight: 700;
  color: #f59e0b;
}

.cell {
  font-family: ui-monospace, monospace;
  font-size: 0.82rem;
  color: #cbd5e1;
}

.grid-mantra {
  margin-top: 16px;
  text-align: center;
  font-size: 1.05rem;
  font-weight: 600;
  color: #e2e8f0;
  opacity: 0;
  transform: scale(0.94);
  transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.grid-mantra.appear {
  opacity: 1;
  transform: scale(1);
}
</style>
