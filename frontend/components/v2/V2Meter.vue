<template>
  <div class="v2-meter">
    <div class="v2-meter__top">
      <span class="v2-meter__label">{{ label }}</span>
      <span class="v2-meter__value">{{ display }}</span>
    </div>
    <span class="v2-meter__track" role="img" :aria-label="`${label}: ${display}`">
      <span class="v2-meter__fill" :style="{ width: `${pct}%` }" />
    </span>
    <p v-if="hint" class="v2-meter__hint">{{ hint }}</p>
    <V2Coverage :coverage="coverage" :unit="unit" />
  </div>
</template>

<script setup>
/**
 * A single ratio against its scale.
 *
 * These are the metrics v1 tried to fold into a "neutrality" radar axis by
 * reading `aggregated_bias.average_subjectivity_score`, which does not exist —
 * the value lives at `language_bias_metrics.average_subjectivity_score`. So
 * `1 - undefined` was NaN, and the axis read 0 forever.
 *
 * A meter rather than a chart because each of these is one number against a
 * known limit, and because inverting them into a "score" is what made v1
 * dishonest: a subjectivity of 0.0 is reported as 0.0 subjectivity, not as
 * "100% neutral".
 */
import { computed } from "vue";
import V2Coverage from "./V2Coverage.vue";

const props = defineProps({
  label: { type: String, required: true },
  value: { type: Number, required: true },
  /** Top of the scale (1 for the 0–1 scores, 100 for percentages). */
  max: { type: Number, default: 1 },
  /** Digits after the decimal point. */
  precision: { type: Number, default: 2 },
  /** Unit suffix appended to the displayed value. */
  suffix: { type: String, default: "" },
  hint: { type: String, default: "" },
  coverage: { type: Object, default: null },
  unit: { type: String, default: "sources" },
});

const pct = computed(() => {
  if (!props.max) return 0;
  return Math.max(0, Math.min(100, (props.value / props.max) * 100));
});

const display = computed(() => `${props.value.toFixed(props.precision)}${props.suffix}`);
</script>

<style scoped>
.v2-meter { display: flex; flex-direction: column; gap: var(--space-2); }
.v2-meter__top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
}
.v2-meter__label { font-size: 0.8rem; color: var(--wsi-ink); }
.v2-meter__value {
  font-size: 0.95rem;
  font-weight: var(--font-weight-semi-bold);
  color: var(--wsi-ink);
}
.v2-meter__track {
  display: block;
  height: 8px;
  border-radius: 2px;
  /* Unfilled track is a lighter step of the fill's own ramp. */
  background: var(--v2-seq-100);
}
.v2-meter__fill {
  display: block;
  height: 100%;
  border-radius: 0 4px 4px 0;
  background: var(--v2-seq-450);
}
.v2-meter__hint { font-size: 0.72rem; color: var(--wsi-ink-soft); }
</style>
