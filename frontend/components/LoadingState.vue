<template>
  <div class="loading-state wsi-panel">
    <span class="loading-state__spinner" aria-hidden="true"></span>
    <p class="loading-state__title">Analyse des sources en cours…</p>
    <p class="loading-state__sub">Lecture des références, résolution Wikidata et calcul des distributions.</p>
    <CdxProgressBar class="loading-state__bar" />
  </div>
</template>

<script setup>
import { CdxProgressBar } from "@wikimedia/codex";
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
</style>
