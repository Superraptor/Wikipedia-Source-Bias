<template>
  <div class="kpi-cards">
    <article class="kpi-card wsi-panel">
      <span class="kpi-card__label">{{ t("kpi.sourcesLabel") }}</span>
      <span class="kpi-card__value">{{ analysis.source_count }}</span>
      <span class="kpi-card__hint">{{ t("kpi.sourcesHint") }}</span>
    </article>
    <article class="kpi-card wsi-panel">
      <span class="kpi-card__label">{{ t("kpi.dominantLabel") }}</span>
      <span class="kpi-card__value kpi-card__value--small">{{ dominant.country }}</span>
      <span class="kpi-card__hint kpi-card__hint--pct">{{ t("kpi.dominantHint", { pct: dominant.percentage }) }}</span>
    </article>
    <article class="kpi-card wsi-panel">
      <span class="kpi-card__label">{{ t("kpi.opinionLabel") }}</span>
      <span class="kpi-card__value">{{ opinion.count }}</span>
      <span class="kpi-card__hint kpi-card__hint--pct">{{ t("kpi.opinionHint", { pct: opinion.percentage }) }}</span>
    </article>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { isUnmapped } from "~/utils/labels.js";

const { t } = useI18n();
const props = defineProps({ analysis: { type: Object, required: true } });

const dominant = computed(() => {
  const dist = props.analysis.aggregated_bias?.geography_distribution || {};
  let best = { country: t("app.empty"), percentage: 0 };
  for (const [k, v] of Object.entries(dist)) {
    if (isUnmapped(k)) continue;
    if ((v.percentage || 0) > best.percentage) best = { country: k, percentage: v.percentage || 0 };
  }
  return best;
});

const opinion = computed(() => {
  const count = props.analysis.aggregated_bias?.opinion_source_count || 0;
  const total = props.analysis.source_count || 1;
  return { count, percentage: Math.round((100 * count) / total * 10) / 10 };
});
</script>

<style scoped>
.kpi-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
}
.kpi-card {
  padding: var(--space-4) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: 2px;
  position: relative;
  overflow: hidden;
}
.kpi-card::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 3px;
  background: var(--wsi-blue);
  opacity: 0.85;
}
.kpi-card:nth-child(2)::before { background: var(--wsi-amber); }
.kpi-card:nth-child(3)::before { background: var(--wsi-red); }
.kpi-card__label {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--wsi-ink-faint);
}
.kpi-card__value {
  font-family: var(--font-display);
  font-size: 2.4rem;
  font-weight: 700;
  line-height: 1.05;
  color: var(--wsi-ink);
  font-variant-numeric: tabular-nums;
  margin-top: var(--space-2);
}
.kpi-card__value--small {
  font-size: 1.5rem;
  line-height: 1.15;
}
.kpi-card__hint {
  font-size: 0.82rem;
  color: var(--wsi-ink-soft);
  margin-top: var(--space-1);
}
.kpi-card__hint--pct {
  font-variant-numeric: tabular-nums;
}

@media (max-width: 720px) {
  .kpi-cards {
    grid-template-columns: 1fr;
  }
}
</style>
