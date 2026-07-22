<template>
  <CdxMessage type="error" class="error-state">
    Impossible d'analyser cet article. Vérifiez l'URL et réessayez.
    <template v-if="detail">
      <span class="error-state__detail"> — {{ detail }}</span>
    </template>
  </CdxMessage>
</template>

<script setup>
import { CdxMessage } from "@wikimedia/codex";
defineProps({ detail: { type: String, default: "" } });
</script>

<style scoped>
.error-state {
  margin: var(--space-5) 0;
}
.error-state__detail {
  color: var(--wsi-ink-soft);
  font-size: 0.85rem;
}
</style>
