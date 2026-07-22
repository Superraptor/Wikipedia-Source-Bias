<template>
  <figure class="v2-bars">
    <figcaption class="v2-bars__head">
      <div class="v2-bars__titles">
        <h3 class="v2-bars__title">{{ title }}</h3>
        <p v-if="subtitle" class="v2-bars__sub">{{ subtitle }}</p>
      </div>
      <button
        v-if="section.available"
        type="button"
        class="v2-bars__toggle"
        :aria-pressed="tableView"
        @click="tableView = !tableView"
      >
        {{ tableView ? t("v2.chart.showChart") : t("v2.chart.showTable") }}
      </button>
    </figcaption>

    <!-- Where the numbers come from, stated once per chart rather than per bar. -->
    <div class="v2-bars__meta">
      <V2EvidenceBadge :evidence="evidence" :detail="evidenceDetail" />
      <V2ProvenanceChip v-if="provenance" :provenance="provenance" :detail="evidenceDetail" />
    </div>

    <!-- `{}` from the backend and "we looked and everything came back unknown"
         are different facts and must not share an empty state. Neither is
         rendered as a chart of zeroes. -->
    <p v-if="!section.available" class="v2-bars__empty">
      {{ t(`v2.chart.empty.${section.reason || "missing"}`) }}
    </p>

    <template v-else>
      <ol v-if="!tableView" class="v2-bars__list">
        <li v-for="bar in rows" :key="bar.key" class="v2-bars__row">
          <component
            :is="section.clickable && bar.key !== '__other__' ? 'button' : 'div'"
            class="v2-bars__hit"
            :type="section.clickable && bar.key !== '__other__' ? 'button' : null"
            :aria-label="section.clickable && bar.key !== '__other__' ? t('v2.chart.drill', { bucket: labelFor(bar.key), n: bar.count ?? 0 }) : null"
            @click="onSelect(bar)"
          >
            <span class="v2-bars__labels">
              <span class="v2-bars__name">{{ labelFor(bar.key) }}</span>
              <!-- Direct label at the data end: the value is readable without
                   hovering, which is what keeps the tooltip an enhancement. -->
              <span class="v2-bars__value">{{ valueText(bar) }}</span>
            </span>
            <span class="v2-bars__track">
              <span class="v2-bars__fill" :style="{ width: `${scaled(bar.percentage)}%` }" />
            </span>
          </component>
        </li>
      </ol>

      <!-- The table twin. Every value is reachable without colour or hover. -->
      <div v-else class="v2-bars__tablewrap">
        <table class="v2-table">
          <thead>
            <tr>
              <th scope="col">{{ t("v2.chart.category") }}</th>
              <th scope="col" class="v2-table__num">{{ t("v2.chart.count") }}</th>
              <th scope="col" class="v2-table__num">{{ t("v2.chart.share") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in section.bars.concat(section.folded ? section.folded.members.map(memberRow) : [])" :key="e.key">
              <th scope="row">{{ labelFor(e.key) }}</th>
              <td class="v2-table__num">{{ e.count ?? "—" }}</td>
              <td class="v2-table__num">{{ e.percentage.toFixed(1) }}%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="v2-bars__foot">
        <V2Coverage :coverage="section.coverage" :unit="unit" />
        <!-- The "unknown" bucket is deliberately not a bar. On the French test
             article 87.5% of sources have an unknown political leaning; drawing
             that as the tallest bar would make "unknown" the finding. -->
        <p v-if="section.unknown && section.unknown.percentage > 0" class="v2-bars__unknown">
          {{ t("v2.chart.excluded", {
            n: section.unknown.count ?? "—",
            pct: section.unknown.percentage.toFixed(1),
          }) }}
        </p>
      </div>
    </template>
  </figure>
</template>

<script setup>
/**
 * A horizontal bar chart for one nominal distribution.
 *
 * Deliberately one colour for every bar. These categories — countries,
 * languages, source types — have no natural order, so shading them by value
 * would double-encode bar length as hue and spend the only free channel on
 * information the length already carries.
 *
 * Horizontal because the category names are long proper nouns ("United
 * Kingdom", "public_broadcaster") and because it degrades to a single column at
 * 375px without rotating any text.
 */
import { computed, ref } from "vue";
import V2EvidenceBadge from "./V2EvidenceBadge.vue";
import V2ProvenanceChip from "./V2ProvenanceChip.vue";
import V2Coverage from "./V2Coverage.vue";
import { EVIDENCE } from "../../utils/provenance.js";

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
  /** A `distributionSection()` record from useV2Data. */
  section: { type: Object, required: true },
  /** How each bucket key is turned into display text. */
  labeller: { type: Function, default: null },
  evidence: { type: String, default: EVIDENCE.MEASURED },
  evidenceDetail: { type: String, default: "" },
  provenance: { type: String, default: "" },
  unit: { type: String, default: "sources" },
});

const emit = defineEmits(["select"]);
const { t } = useI18n();

const tableView = ref(false);

const rows = computed(() => {
  const bars = props.section.bars || [];
  return props.section.folded ? [...bars, props.section.folded] : bars;
});

// Bars are scaled against the largest bar, not against 100, so a corpus split
// across many small buckets is still readable. The printed value is always the
// true percentage, so the scaling cannot mislead.
const maxPct = computed(() =>
  Math.max(1, ...rows.value.map((b) => b.percentage || 0)),
);
const scaled = (pct) => Math.max(1.5, ((pct || 0) / maxPct.value) * 100);

function labelFor(key) {
  if (key === "__other__") return t("v2.chart.other");
  return props.labeller ? props.labeller(key) : key;
}

function valueText(bar) {
  const pct = `${(bar.percentage ?? 0).toFixed(1)}%`;
  return typeof bar.count === "number" ? `${bar.count} · ${pct}` : pct;
}

function memberRow(key) {
  const found = (props.section.folded?.rows || []).find((r) => r.key === key);
  return found || { key, count: null, percentage: 0 };
}

function onSelect(bar) {
  if (!props.section.clickable || bar.key === "__other__") return;
  emit("select", { dimension: props.section.dimension, key: bar.key, label: labelFor(bar.key) });
}
</script>

<style scoped>
.v2-bars { margin: 0; }
.v2-bars__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}
.v2-bars__title {
  font-size: 0.95rem;
  margin: 0;
}
.v2-bars__sub {
  font-size: 0.75rem;
  color: var(--wsi-ink-soft);
  margin-top: 2px;
}
.v2-bars__toggle {
  flex: 0 0 auto;
  border: 1px solid var(--wsi-line-soft);
  background: var(--wsi-surface);
  border-radius: var(--radius);
  padding: 2px 8px;
  font: inherit;
  font-size: 0.68rem;
  color: var(--wsi-ink-soft);
  cursor: pointer;
}
.v2-bars__toggle:hover { border-color: var(--wsi-blue); color: var(--wsi-blue); }

.v2-bars__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.v2-bars__empty {
  font-size: 0.78rem;
  color: var(--wsi-ink-faint);
  font-style: italic;
  padding: var(--space-3) 0;
}

.v2-bars__list {
  list-style: none;
  margin: 0;
  padding: 0;
}
/* The 2px surface gap between adjacent bars — white doing the separating,
   rather than a stroke drawn around each mark. */
.v2-bars__row + .v2-bars__row { margin-top: 10px; }

.v2-bars__hit {
  display: block;
  width: 100%;
  border: 0;
  background: none;
  padding: 2px 0;
  font: inherit;
  text-align: left;
  color: inherit;
}
button.v2-bars__hit { cursor: pointer; }
button.v2-bars__hit:hover .v2-bars__fill { background: var(--v2-seq-550); }
button.v2-bars__hit:hover .v2-bars__name { color: var(--wsi-blue); }
button.v2-bars__hit:focus-visible {
  outline: 2px solid var(--wsi-blue);
  outline-offset: 2px;
  border-radius: var(--radius);
}

.v2-bars__labels {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: 3px;
}
.v2-bars__name {
  font-size: 0.8rem;
  color: var(--wsi-ink);
  min-width: 0;
  overflow-wrap: anywhere;
}
.v2-bars__value {
  flex: 0 0 auto;
  font-size: 0.75rem;
  color: var(--wsi-ink-soft);
  font-variant-numeric: tabular-nums;
}
.v2-bars__track {
  display: block;
  height: 8px;
  background: var(--v2-seq-100);
  border-radius: 2px;
}
.v2-bars__fill {
  display: block;
  height: 100%;
  background: var(--v2-seq-450);
  /* Square at the baseline, 4px rounded at the data end. */
  border-radius: 0 4px 4px 0;
  transition: background 0.15s ease;
}

.v2-bars__foot {
  margin-top: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.v2-bars__unknown {
  font-size: 0.72rem;
  color: var(--wsi-ink-faint);
}

.v2-bars__tablewrap { overflow-x: auto; }
</style>
