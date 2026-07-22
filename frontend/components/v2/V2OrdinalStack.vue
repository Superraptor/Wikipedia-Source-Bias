<template>
  <figure class="v2-stack">
    <figcaption class="v2-stack__head">
      <div>
        <h3 class="v2-stack__title">{{ title }}</h3>
        <p v-if="subtitle" class="v2-stack__sub">{{ subtitle }}</p>
      </div>
      <button
        v-if="section.available"
        type="button"
        class="v2-stack__toggle"
        :aria-pressed="tableView"
        @click="tableView = !tableView"
      >
        {{ tableView ? t("v2.chart.showChart") : t("v2.chart.showTable") }}
      </button>
    </figcaption>

    <div class="v2-stack__meta">
      <V2EvidenceBadge :evidence="evidence" :detail="evidenceDetail" />
      <V2ProvenanceChip v-if="provenance" :provenance="provenance" :detail="evidenceDetail" />
    </div>

    <p v-if="!section.available" class="v2-stack__empty">
      {{ t(`v2.chart.empty.${section.reason || "missing"}`) }}
    </p>

    <template v-else>
      <div v-if="!tableView" class="v2-stack__bar" role="img" :aria-label="ariaSummary">
        <component
          :is="section.clickable ? 'button' : 'div'"
          v-for="seg in segments"
          :key="seg.key"
          class="v2-stack__seg"
          :type="section.clickable ? 'button' : null"
          :style="{ width: `${seg.share}%`, background: seg.color }"
          :title="`${seg.label} — ${seg.count ?? '—'} (${seg.percentage.toFixed(1)}%)`"
          :aria-label="section.clickable ? t('v2.chart.drill', { bucket: seg.label, n: seg.count ?? 0 }) : null"
          @click="section.clickable && emit('select', { dimension: section.dimension, key: seg.key, label: seg.label })"
        >
          <!-- Only label inside the segment when the text genuinely fits;
               otherwise the legend below carries it. Never clipped. -->
          <span v-if="seg.share >= 18" class="v2-stack__seglabel" :class="{ 'v2-stack__seglabel--dark': seg.darkInk }">
            {{ seg.percentage.toFixed(0) }}%
          </span>
        </component>
      </div>

      <!-- A legend is always present: identity is never colour alone. -->
      <ul v-if="!tableView" class="v2-stack__legend">
        <li v-for="seg in segments" :key="seg.key" class="v2-stack__legenditem">
          <span class="v2-stack__swatch" :style="{ background: seg.color }" aria-hidden="true" />
          <span class="v2-stack__legendname">{{ seg.label }}</span>
          <span class="v2-stack__legendval">{{ seg.count ?? "—" }} · {{ seg.percentage.toFixed(1) }}%</span>
        </li>
      </ul>

      <div v-else class="v2-stack__tablewrap">
        <table class="v2-table">
          <thead>
            <tr>
              <th scope="col">{{ t("v2.chart.category") }}</th>
              <th scope="col" class="v2-table__num">{{ t("v2.chart.count") }}</th>
              <th scope="col" class="v2-table__num">{{ t("v2.chart.share") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="seg in segments" :key="seg.key">
              <th scope="row">{{ seg.label }}</th>
              <td class="v2-table__num">{{ seg.count ?? "—" }}</td>
              <td class="v2-table__num">{{ seg.percentage.toFixed(1) }}%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="v2-stack__foot">
        <V2Coverage :coverage="section.coverage" :unit="unit" />
        <p v-if="section.unknown && section.unknown.percentage > 0" class="v2-stack__unknown">
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
 * A part-to-whole stacked bar for an ORDERED scale.
 *
 * Reliability is the one distribution in the payload with a real order —
 * academic > high > medium > low — so it gets the ordinal ramp (one hue,
 * light to dark, darker meaning more reliable) rather than the categorical
 * hues used for identity. The ramp is validated with the skill's `--ordinal`
 * mode: monotone lightness, adjacent ΔL ≥ 0.06, light end clearing 2:1
 * against the white Codex surface.
 *
 * Ordering is by the scale, never by size, so the same level is always the
 * same shade in the same place across articles.
 */
import { computed, ref } from "vue";
import V2EvidenceBadge from "./V2EvidenceBadge.vue";
import V2ProvenanceChip from "./V2ProvenanceChip.vue";
import V2Coverage from "./V2Coverage.vue";
import { EVIDENCE } from "../../utils/provenance.js";

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
  section: { type: Object, required: true },
  /** Bucket keys lowest→highest on the scale. Anything else lands in `fallback`. */
  scale: { type: Array, required: true },
  labeller: { type: Function, default: null },
  evidence: { type: String, default: EVIDENCE.MEASURED },
  evidenceDetail: { type: String, default: "" },
  provenance: { type: String, default: "" },
  unit: { type: String, default: "sources" },
});

const emit = defineEmits(["select"]);
const { t } = useI18n();
const tableView = ref(false);

// Validated ordinal ramp (light→dark = low→high on the scale). Steps 250 / 350
// / 450 / 650 of the single blue hue; see the palette validation in the
// component doc above.
const RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#0d366b"];
// Ink flips to white once the fill is dark enough for it to clear contrast.
const DARK_INK_FROM = 2;

const segments = computed(() => {
  const byKey = new Map((props.section.bars || []).map((b) => [String(b.key).toLowerCase(), b]));
  const present = props.scale
    .map((key, i) => ({ key, bar: byKey.get(key.toLowerCase()), i }))
    .filter((x) => x.bar);

  const total = present.reduce((a, x) => a + (x.bar.percentage || 0), 0) || 1;
  const n = present.length;

  return present.map((x, idx) => {
    // Spread the present levels across the ramp so a corpus using only two
    // levels still shows a visible light→dark step.
    const rampIdx = n <= 1 ? RAMP.length - 1 : Math.round((idx / (n - 1)) * (RAMP.length - 1));
    return {
      key: x.key,
      label: props.labeller ? props.labeller(x.key) : x.key,
      count: x.bar.count,
      percentage: x.bar.percentage,
      share: (x.bar.percentage / total) * 100,
      color: RAMP[rampIdx],
      darkInk: rampIdx >= DARK_INK_FROM,
    };
  });
});

const ariaSummary = computed(() =>
  segments.value.map((s) => `${s.label}: ${s.percentage.toFixed(1)}%`).join(", "),
);
</script>

<style scoped>
.v2-stack { margin: 0; }
.v2-stack__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}
.v2-stack__title { font-size: 0.95rem; margin: 0; }
.v2-stack__sub { font-size: 0.75rem; color: var(--wsi-ink-soft); margin-top: 2px; }
.v2-stack__toggle {
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
.v2-stack__toggle:hover { border-color: var(--wsi-blue); color: var(--wsi-blue); }
.v2-stack__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
.v2-stack__empty {
  font-size: 0.78rem;
  color: var(--wsi-ink-faint);
  font-style: italic;
  padding: var(--space-3) 0;
}

.v2-stack__bar {
  display: flex;
  /* The 2px surface gap between stacked segments. */
  gap: 2px;
  height: 22px;
  border-radius: 3px;
  overflow: hidden;
}
.v2-stack__seg {
  border: 0;
  padding: 0;
  height: 100%;
  min-width: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  font: inherit;
}
button.v2-stack__seg { cursor: pointer; }
button.v2-stack__seg:hover { filter: brightness(0.92); }
button.v2-stack__seg:focus-visible { outline: 2px solid var(--wsi-blue); outline-offset: 2px; }
.v2-stack__seglabel {
  font-size: 0.66rem;
  font-weight: var(--font-weight-semi-bold);
  color: #0b0b0b;
  font-variant-numeric: tabular-nums;
}
.v2-stack__seglabel--dark { color: #ffffff; }

.v2-stack__legend {
  list-style: none;
  margin: var(--space-3) 0 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
}
.v2-stack__legenditem {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 0.74rem;
}
.v2-stack__swatch {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex: 0 0 auto;
}
.v2-stack__legendname { color: var(--wsi-ink); }
.v2-stack__legendval { color: var(--wsi-ink-soft); font-variant-numeric: tabular-nums; }

.v2-stack__foot {
  margin-top: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.v2-stack__unknown { font-size: 0.72rem; color: var(--wsi-ink-faint); }
.v2-stack__tablewrap { overflow-x: auto; }
</style>
