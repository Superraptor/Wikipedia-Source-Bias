<template>
  <section class="top-countries wsi-panel">
    <header class="top-countries__head">
      <div class="wsi-section-title">
        <span class="wsi-section-num">03</span>
        <h2>{{ t("topCountries.title") }}</h2>
      </div>
      <ul class="top-countries__legend" :aria-label="t('topCountries.legendAria')">
        <li v-for="r in legendRegions" :key="r.key">
          <span class="top-countries__swatch" :style="{ background: r.color }"></span>
          {{ r.label }}
        </li>
      </ul>
    </header>
    <div class="top-countries__chart">
      <Bar v-if="hasData" :data="chartData" :options="chartOptions" />
      <p v-else class="top-countries__empty">{{ t("topCountries.empty") }}</p>
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";
import { Bar } from "vue-chartjs";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from "chart.js";

import { UNMAPPED, countryLabel, isUnmapped, regionLabel } from "~/utils/labels.js";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

// Chart.js draws to <canvas> and cannot resolve CSS custom properties, so these
// are concrete hex values kept in sync with @wikimedia/codex-design-tokens:
// Europe = --color-progressive (#36c), Africa = --color-destructive (#bf3c2c),
// Oceania = --color-disabled (#a2a9b1), unmapped = --border-color-subtle (#c8ccd1).
// Keyed by the language-neutral region key, never by a display label.
const REGION_COLORS = {
  Europe: "#36c",
  Americas: "#fc3",
  Asia: "#ac6600",
  Africa: "#bf3c2c",
  Oceania: "#a2a9b1",
  [UNMAPPED]: "#c8ccd1",
};

const COUNTRY_REGION = {
  France: "Europe", Germany: "Europe", "United Kingdom": "Europe",
  Italy: "Europe", Spain: "Europe", Switzerland: "Europe",
  Netherlands: "Europe", Belgium: "Europe", Sweden: "Europe",
  Norway: "Europe", Denmark: "Europe", Finland: "Europe", Poland: "Europe",
  Austria: "Europe", Ireland: "Europe", Portugal: "Europe", Greece: "Europe",
  "Czech Republic": "Europe", "Czechia": "Europe", Romania: "Europe",
  Hungary: "Europe", Russia: "Europe",
  "United States": "Americas", "United States of America": "Americas",
  Canada: "Americas", Mexico: "Americas", Brazil: "Americas",
  Argentina: "Americas", Chile: "Americas", Colombia: "Americas",
  Peru: "Americas", Venezuela: "Americas",
  China: "Asia", Japan: "Asia", India: "Asia", "South Korea": "Asia",
  "North Korea": "Asia", Israel: "Asia", Turkey: "Asia",
  "Saudi Arabia": "Asia", Iran: "Asia", Iraq: "Asia", Pakistan: "Asia",
  Indonesia: "Asia", Taiwan: "Asia", Vietnam: "Asia", Thailand: "Asia",
  Nigeria: "Africa", Egypt: "Africa", "South Africa": "Africa",
  Algeria: "Africa", Morocco: "Africa", Kenya: "Africa", Ethiopia: "Africa",
  Australia: "Oceania", "New Zealand": "Oceania",
};

function regionFor(country) {
  if (isUnmapped(country)) return UNMAPPED;
  return COUNTRY_REGION[country] || UNMAPPED;
}

const { t } = useI18n();

const legendRegions = computed(() =>
  Object.keys(REGION_COLORS).map((key) => ({
    key,
    label: regionLabel(key, t),
    color: REGION_COLORS[key],
  })),
);

const props = defineProps({ analysis: { type: Object, required: true } });

const top10 = computed(() => {
  const dist = props.analysis.aggregated_bias?.geography_distribution || {};
  return Object.entries(dist)
    .map(([country, v]) => ({
      country: countryLabel(country, t),
      count: v.count || 0,
      percentage: v.percentage || 0,
      region: regionFor(country),
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);
});

const hasData = computed(() => top10.value.some((r) => r.count > 0));

const chartData = computed(() => ({
  labels: top10.value.map((r) => r.country),
  datasets: [
    {
      label: t("topCountries.datasetLabel"),
      data: top10.value.map((r) => r.count),
      backgroundColor: top10.value.map((r) => REGION_COLORS[r.region] || REGION_COLORS[UNMAPPED]),
      borderColor: top10.value.map((r) => REGION_COLORS[r.region] || REGION_COLORS[UNMAPPED]),
      borderWidth: 0,
      borderRadius: 3,
      barPercentage: 0.72,
    },
  ],
}));

// Computed rather than a constant: the tooltip formatter closes over `t`, and
// Chart.js only re-reads its options when the object identity changes, so a
// locale switch would otherwise leave French tooltips on an English chart.
const chartOptions = computed(() => ({
  indexAxis: "y",
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => {
          const row = top10.value[ctx.dataIndex];
          return t("topCountries.tooltip", {
            count: row.count,
            pct: row.percentage,
            region: regionLabel(row.region, t),
          });
        },
      },
    },
  },
  scales: {
    x: {
      beginAtZero: true,
      grid: { color: "rgba(200,204,209,0.4)", drawBorder: false },
      ticks: { color: "#54595d", font: { family: "Source Sans 3" } },
    },
    y: {
      grid: { display: false, drawBorder: false },
      ticks: { color: "#202122", font: { family: "Source Sans 3", weight: 500 } },
    },
  },
}));
</script>

<style scoped>
.top-countries {
  padding: var(--space-5) var(--space-5) var(--space-6);
}
.top-countries__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.top-countries__legend {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  font-size: 0.78rem;
  color: var(--wsi-ink-soft);
}
.top-countries__legend li {
  display: flex;
  align-items: center;
  gap: 6px;
}
.top-countries__swatch {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}
.top-countries__chart {
  height: 360px;
  position: relative;
}
.top-countries__empty {
  color: var(--wsi-ink-soft);
  font-size: 0.9rem;
}
</style>
