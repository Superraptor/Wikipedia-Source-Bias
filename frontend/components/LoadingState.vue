<template>
  <div class="loading-state wsi-panel">
    <span class="loading-state__spinner" aria-hidden="true"></span>
    <p class="loading-state__title">{{ title }}</p>
    <p class="loading-state__sub">{{ subtitle }}</p>
    <CdxProgressBar class="loading-state__bar" />
    <div v-if="pending && progress" class="loading-state__progress">
      <p v-if="progress.pct !== null" class="loading-state__pct">
        {{ t("states.pendingProgress", { done: progress.done, total: progress.total, pct: progress.pct }) }}
      </p>
      <p v-if="progress.eta" class="loading-state__pct">
        {{ t("states.pendingEta", { eta: progress.eta }) }}
      </p>
      <p v-if="progress.queuePosition" class="loading-state__pct">
        {{ t("states.pendingQueue", { n: progress.queuePosition }) }}
      </p>
      <p
        v-if="progress.health"
        class="loading-state__health"
        :class="{ 'loading-state__health--stalled': progress.health === 'stalled' }"
      >
        {{ progress.health === "stalled"
            ? t("states.pendingStalled", { quiet: progress.quietFor })
            : t("states.pendingAlive") }}
      </p>
    </div>
    <p v-if="pending" class="loading-state__hint">
      {{ t("states.pendingHint") }}
      <a href="/status" target="_blank" rel="noopener">{{ t("states.pendingHintLink") }}</a>
    </p>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { CdxProgressBar } from "@wikimedia/codex";

// `pending` means the backend has queued the analysis and a worker will pick
// it up; `loading` is just the in-flight HTTP request. They look similar but
// the wait is wildly different, so say so.
const props = defineProps({
  pending: { type: Boolean, default: false },
  progress: { type: Object, default: null },
});

const { t } = useI18n();

const title = computed(() =>
  t(props.pending ? "states.pendingTitle" : "states.loadingTitle"),
);
const subtitle = computed(() =>
  t(props.pending ? "states.pendingSubtitle" : "states.loadingSubtitle"),
);
</script>

<style scoped>
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: var(--space-2);
  padding: var(--space-7) var(--space-6);
  margin: var(--space-6) 0;
}
.loading-state__spinner {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 3px solid var(--wsi-line-soft);
  border-top-color: var(--wsi-blue);
  animation: wsi-spin 0.8s linear infinite;
  margin-bottom: var(--space-3);
}
.loading-state__title {
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--wsi-ink);
}
.loading-state__sub {
  font-size: 0.9rem;
  color: var(--wsi-ink-soft);
  max-width: 46ch;
}
.loading-state__bar {
  width: min(320px, 100%);
  margin-top: var(--space-3);
}
.loading-state__progress {
  margin-top: var(--space-2);
  font-size: 0.9rem;
  color: var(--wsi-ink-soft);
}
.loading-state__pct {
  font-variant-numeric: tabular-nums;
}
.loading-state__health {
  margin-top: var(--space-1);
  font-weight: 600;
  color: var(--wsi-green, #14866d);
}
.loading-state__health--stalled {
  color: var(--wsi-amber, #edab00);
}
.loading-state__hint {
  font-size: 0.85rem;
  color: var(--wsi-ink-faint);
  margin-top: var(--space-2);
}
</style>
