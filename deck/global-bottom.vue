<template>
  <footer v-if="showFooter" class="deck-footer">
    <span>SAME RECIPE, DIFFERENT RESULTS · EUROSCIPY 2026</span>
    <span class="page">{{ nav.currentPage }}</span>
  </footer>
</template>

<script setup>
import { useNav } from "@slidev/client";
import { computed } from "vue";

const nav = useNav();

// Section openers and full-bleed media slides opt out with
// `footer: false` in their frontmatter.
const showFooter = computed(() => {
  const frontmatter = nav.currentSlideRoute.value?.meta?.slide?.frontmatter ?? {};
  return frontmatter.footer !== false;
});
</script>
