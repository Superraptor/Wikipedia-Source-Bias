<template>
  <div v-if="findings.length" class="imbalance">
    <div
      v-for="(f, i) in findings"
      :key="i"
      class="imbalance__item"
      :class="`imbalance__item--${f.severity}`"
    >
      <span class="imbalance__icon" aria-hidden="true">{{ f.severity === "coverage" ? "❓" : "⚠️" }}</span>
      <div class="imbalance__body">
        <p class="imbalance__headline">{{ headline(f) }}</p>
        <p class="imbalance__why">{{ why(f) }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * A calm, explained notice when a corpus is strongly concentrated. It states
 * the fact and its caveat -- never that the article is "biased" -- because a
 * national topic citing national sources is expected, not a defect.
 */
import { computed } from "vue";
import { detectImbalance } from "~/composables/useImbalance.js";
import { countryLabel, regionLabel } from "~/utils/labels.js";

const props = defineProps({ analysis: { type: Object, required: true } });
const { t } = useI18n();

const findings = computed(() => detectImbalance(props.analysis).findings);

function label(f) {
  if (f.dimension === "geography") return countryLabel(f.key, t);
  if (f.dimension === "region") return regionLabel(f.key, t);
  return f.key; // language: already a display string
}

function headline(f) {
  if (f.severity === "coverage") {
    return t("imbalance.coverageHeadline", { pct: f.pct });
  }
  return t(`imbalance.headline.${f.dimension}`, { value: label(f), pct: f.pct });
}

function why(f) {
  if (f.severity === "coverage") return t("imbalance.coverageWhy");
  // The caveat is the important part: this may be expected.
  return t(`imbalance.why.${f.dimension}`, { value: label(f), pct: f.pct });
}
</script>

<style scoped>
.imbalance {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.imbalance__item {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: 4px;
  border: 1px solid var(--wsi-line);
  background: var(--wsi-surface-raised);
}
.imbalance__item--strong {
  border-color: var(--wsi-amber, #edab00);
  background: color-mix(in srgb, var(--wsi-amber, #edab00) 8%, transparent);
}
.imbalance__item--coverage {
  border-color: var(--wsi-ink-faint);
}
.imbalance__icon {
  font-size: 1.1rem;
  line-height: 1.4;
  flex: none;
}
.imbalance__headline {
  margin: 0;
  font-weight: 600;
  color: var(--wsi-ink);
}
.imbalance__why {
  margin: 2px 0 0;
  font-size: 0.875rem;
  color: var(--wsi-ink-soft);
}
</style>
