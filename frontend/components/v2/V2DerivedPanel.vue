<template>
  <section class="v2-derived wsi-panel">
    <header class="v2-derived__head">
      <div>
        <h3 class="v2-derived__title">{{ t("v2.derived.title") }}</h3>
        <p class="v2-derived__lede">{{ t("v2.derived.lede") }}</p>
      </div>
      <span class="v2-derived__tag">{{ t("v2.derived.tag") }}</span>
    </header>

    <ul class="v2-derived__list">
      <li v-for="d in available" :key="d.dimension" class="v2-derived__item">
        <div class="v2-derived__row">
          <span class="v2-derived__name">{{ t(`v2.derived.metric.${d.dimension}`) }}</span>
          <span class="v2-derived__value">{{ d.value.toFixed(1) }}%</span>
        </div>
        <p class="v2-derived__read">
          {{ t(`v2.derived.reading.${d.dimension}`, { top: d.top, pct: d.value.toFixed(1) }) }}
        </p>

        <!-- The formula and its exact inputs, so a reader can redo the
             arithmetic. A composite that cannot be checked is indistinguishable
             from an invented one, which is what the v1 radar was. -->
        <details class="v2-derived__how">
          <summary>{{ t("v2.derived.how") }}</summary>
          <p class="v2-derived__formula"><code>{{ d.formula }}</code></p>
          <dl class="v2-derived__inputs">
            <div>
              <dt>{{ t("v2.derived.inputTop") }}</dt>
              <dd>{{ d.inputs.topKey }} = {{ d.inputs.topValue }}</dd>
            </div>
            <div>
              <dt>{{ t("v2.derived.inputTotal") }}</dt>
              <dd>{{ d.inputs.knownTotal }}</dd>
            </div>
            <div>
              <dt>{{ t("v2.derived.inputExcluded") }}</dt>
              <dd>{{ d.inputs.excluded }}</dd>
            </div>
            <div>
              <dt>{{ t("v2.derived.inputResult") }}</dt>
              <dd>{{ d.inputs.topValue }} / {{ d.inputs.knownTotal }} × 100 = {{ d.value.toFixed(1) }}%</dd>
            </div>
          </dl>
          <p class="v2-derived__caveat">{{ t("v2.derived.caveat") }}</p>
        </details>

        <V2Coverage :coverage="d.coverage" unit="sources" />
      </li>
    </ul>

    <p v-if="!available.length" class="v2-derived__empty">{{ t("v2.derived.empty") }}</p>
  </section>
</template>

<script setup>
/**
 * The only composite numbers in v2 — and they show their work.
 *
 * v1's radar had five composites (geo_diversity, political_pluralism,
 * author_parity, neutrality, reliability) whose formulas existed only in
 * `useRadarData.js`: nothing in the UI said they were derived, what went into
 * them, or that two of them were structurally stuck at zero. They were, as the
 * user put it, made up.
 *
 * v2 keeps exactly one kind of composite — concentration, the share held by the
 * largest known bucket — because it is a single division over a distribution
 * the reader can see charted directly above, and because it is computed over
 * KNOWN buckets only so an unplaceable corpus cannot read as a diverse one.
 * It is labelled derived, and every input is printed.
 */
import { computed } from "vue";
import V2Coverage from "./V2Coverage.vue";

const props = defineProps({
  /** `concentration()` records from useV2Data. */
  derived: { type: Array, default: () => [] },
});

const { t } = useI18n();

const available = computed(() => (props.derived || []).filter((d) => d && d.available));
</script>

<style scoped>
.v2-derived { padding: var(--space-5); }
.v2-derived__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.v2-derived__title { font-size: 1.05rem; margin: 0; }
.v2-derived__lede {
  font-size: 0.8rem;
  color: var(--wsi-ink-soft);
  margin-top: var(--space-2);
  max-width: 60ch;
}
/* Says "computed by this tool" on the tin, right next to the numbers. */
.v2-derived__tag {
  flex: 0 0 auto;
  border: 1px dashed var(--wsi-line);
  border-radius: var(--radius-pill);
  padding: 2px 8px;
  font-size: 0.62rem;
  font-weight: var(--font-weight-semi-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--v2-estimated);
}

.v2-derived__list { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--space-5); }
.v2-derived__item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.v2-derived__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
}
.v2-derived__name { font-size: 0.85rem; font-weight: var(--font-weight-semi-bold); }
.v2-derived__value { font-size: 1.3rem; font-weight: var(--font-weight-semi-bold); }
.v2-derived__read { font-size: 0.78rem; color: var(--wsi-ink-soft); }

.v2-derived__how summary {
  cursor: pointer;
  font-size: 0.74rem;
  color: var(--wsi-blue);
}
.v2-derived__formula { margin-top: var(--space-2); }
.v2-derived__formula code {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  background: var(--wsi-surface-sunken);
  border-radius: var(--radius);
  padding: 2px 6px;
  display: inline-block;
  overflow-wrap: anywhere;
}
.v2-derived__inputs {
  margin: var(--space-3) 0 0;
  display: grid;
  gap: var(--space-2);
  font-size: 0.74rem;
}
.v2-derived__inputs > div {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.v2-derived__inputs dt { color: var(--wsi-ink-soft); }
.v2-derived__inputs dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}
.v2-derived__caveat {
  margin-top: var(--space-3);
  font-size: 0.72rem;
  color: var(--wsi-ink-faint);
  max-width: 60ch;
}
.v2-derived__empty { font-size: 0.8rem; color: var(--wsi-ink-faint); font-style: italic; }
</style>
