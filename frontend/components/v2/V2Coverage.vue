<template>
  <p v-if="coverage && coverage.total" class="v2-cov" :class="{ 'v2-cov--thin': thin }">
    <span class="v2-cov__track" aria-hidden="true">
      <span class="v2-cov__fill" :style="{ width: `${Math.min(100, coverage.pct)}%` }" />
    </span>
    <span class="v2-cov__text">{{ text }}</span>
  </p>
</template>

<script setup>
/**
 * "Based on 6 of 8 sources."
 *
 * Every partial metric carries one of these. The backend already tells us the
 * sample size in several places — `readability_metrics.readability_count`,
 * `subjectivity_sample_count` — and v1 displayed none of them, so a score
 * computed from 2 of 10 sources looked exactly as solid as one computed from
 * all 10.
 *
 * `thin` is true when coverage is low enough that the number below should be
 * read as indicative only; the wording changes rather than just the bar.
 */
import { computed } from "vue";

const props = defineProps({
  /** A `coverage()` record from useV2Data. */
  coverage: { type: Object, default: null },
  /** What is being counted: "sources" (default) or "authors". */
  unit: { type: String, default: "sources" },
});

const { t } = useI18n();

// Below a third of the corpus a metric is a hint, not a description of it.
const thin = computed(() => props.coverage && props.coverage.pct < 34);

const text = computed(() => {
  const c = props.coverage;
  if (!c || !c.total) return "";
  if (c.empty) return t(`v2.coverage.none.${props.unit}`, { total: c.total });
  if (c.complete) return t(`v2.coverage.all.${props.unit}`, { total: c.total });
  return t(`v2.coverage.partial.${props.unit}`, {
    known: c.known,
    total: c.total,
    pct: c.pct,
  });
});
</script>

<style scoped>
.v2-cov {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  font-size: 0.72rem;
  color: var(--wsi-ink-soft);
}
.v2-cov__track {
  flex: 0 0 44px;
  height: 4px;
  border-radius: 2px;
  /* Unfilled track is a lighter step of the fill's own ramp, so the ratio
     reads across the whole bar rather than as a bar floating on the page. */
  background: var(--v2-seq-100);
  overflow: hidden;
}
.v2-cov__fill {
  display: block;
  height: 100%;
  border-radius: 2px;
  background: var(--v2-seq-450);
}
.v2-cov--thin .v2-cov__fill { background: var(--v2-seq-250); }
.v2-cov--thin .v2-cov__text { color: var(--wsi-ink-faint); }
.v2-cov__text { min-width: 0; }
</style>
