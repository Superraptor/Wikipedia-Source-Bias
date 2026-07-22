<template>
  <CdxMessage type="notice" class="empty-state">
    {{ t("states.empty") }}
  </CdxMessage>
</template>

<script setup>
import { CdxMessage } from "@wikimedia/codex";

const { t } = useI18n();
</script>

<style scoped>
.empty-state {
  margin: var(--space-5) 0;
}
</style>
