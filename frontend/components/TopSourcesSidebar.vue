<template>
  <section class="top-sources wsi-panel">
    <header class="top-sources__head">
      <div class="wsi-section-title">
        <span class="wsi-section-num">06</span>
        <h2>{{ t("topSources.title") }}</h2>
      </div>
    </header>
    <ol class="top-sources__list">
      <li v-for="(s, i) in top5" :key="i" class="top-sources__item">
        <span class="top-sources__rank">{{ i + 1 }}</span>
        <div class="top-sources__main">
          <span class="top-sources__domain" :title="s.domain">{{ s.domain || s.url }}</span>
          <span class="top-sources__meta">
            <span class="top-sources__country">{{ countryLabel(s.geography?.country, t) }}</span>
            <span class="top-sources__sep" aria-hidden="true">·</span>
            <span class="top-sources__rel">{{ reliabilityLabel(s.reliability, t) }}</span>
          </span>
        </div>
      </li>
    </ol>
  </section>
</template>

<script setup>
import { computed } from "vue";
import { countryLabel, reliabilityLabel } from "~/utils/labels.js";

const { t } = useI18n();
const props = defineProps({ analysis: { type: Object, required: true } });

const top5 = computed(() => (props.analysis.sources || []).slice(0, 5));
</script>

<style scoped>
.top-sources {
  padding: var(--space-5);
}
.top-sources__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}
.top-sources__item {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--wsi-line-soft);
}
.top-sources__item:last-child { border-bottom: 0; }
.top-sources__rank {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--wsi-blue-700);
  width: 1.5ch;
  flex: none;
  padding-top: 1px;
}
.top-sources__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.top-sources__domain {
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--wsi-ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.top-sources__meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 0.78rem;
  color: var(--wsi-ink-soft);
}
.top-sources__sep { color: var(--wsi-line); }
</style>
