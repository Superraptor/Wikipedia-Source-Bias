<template>
  <CdxMessage type="error" class="error-state">
    {{ t("states.error") }}
    <template v-if="detail">
      <span class="error-state__detail"> — {{ detail }}</span>
    </template>
  </CdxMessage>
</template>

<script setup>
import { CdxMessage } from "@wikimedia/codex";

const { t } = useI18n();
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
