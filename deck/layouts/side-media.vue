<template>
  <div class="slidev-layout side-media" :class="side">
    <div class="media">
      <slot name="media" />
    </div>
    <div class="body">
      <slot />
    </div>
  </div>
</template>

<script setup>
// The deck's image-left/image-right equivalent for arbitrary media:
// the `media` slot takes any component (PhoneTuiReplay, MediaFrame,
// a bare video), the default slot takes title and text, and the
// `side` frontmatter key picks the column:
//
//   ---
//   layout: side-media
//   side: right
//   ---
//   # Title and text go here
//   ::media::
//   <PhoneTuiReplay />
//
// Slidev passes slide frontmatter entries to the layout as props.
defineProps({
  side: {
    type: String,
    default: "left",
    validator: (value) => value === "left" || value === "right",
  },
});
</script>

<style scoped>
.side-media {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 3rem;
  align-items: center;
}

.side-media.right {
  grid-template-columns: 1fr auto;
}

.side-media.right .media {
  order: 2;
}

.body {
  max-width: 26rem;
}
</style>
