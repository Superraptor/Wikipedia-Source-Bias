<template>
  <CdxMessage type="notice" class="empty-state">
    Aucune source trouvée. L'article peut ne pas avoir de références standardisées.
  </CdxMessage>
</template>

<script setup>
import { CdxMessage } from "@wikimedia/codex";
</script>

<style scoped>
.empty-state {
  margin: var(--space-5) 0;
}
</style>
