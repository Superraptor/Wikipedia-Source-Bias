<template>
  <div class="loading-state wsi-panel">
    <span class="loading-state__spinner" aria-hidden="true"></span>
    <p class="loading-state__title">{{ title }}</p>
    <p class="loading-state__sub">{{ subtitle }}</p>
    <CdxProgressBar class="loading-state__bar" />
    <p v-if="pending" class="loading-state__hint">
      Les grands articles peuvent demander plusieurs minutes.
      <a href="/status" target="_blank" rel="noopener">Voir la file d'analyse</a>
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
});

const title = computed(() =>
  props.pending ? "Analyse en file d'attente…" : "Analyse des sources en cours…",
);
const subtitle = computed(() =>
  props.pending
    ? "Un worker traite cet article. Cette page se met à jour automatiquement."
    : "Lecture des références, résolution Wikidata et calcul des distributions.",
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
.loading-state__hint {
  font-size: 0.85rem;
  color: var(--wsi-ink-faint);
  margin-top: var(--space-2);
}
</style>
