<template>
  <section class="top-countries wsi-panel">
    <header class="top-countries__head">
      <div class="wsi-section-title">
        <span class="wsi-section-num">03</span>
        <h2>Top 10 pays</h2>
      </div>
      <ul class="top-countries__legend" aria-label="Régions">
        <li v-for="r in legendRegions" :key="r.key">
          <span class="top-countries__swatch" :style="{ background: r.color }"></span>
          {{ r.label }}
        </li>
      </ul>
    </header>
    <div class="top-countries__chart">
      <Bar v-if="hasData" :data="chartData" :options="chartOptions" />
      <p v-else class="top-countries__empty">Aucune donnée géographique disponible.</p>
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

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

// Chart.js draws to <canvas> and cannot resolve CSS custom properties, so these
// are concrete hex values kept in sync with @wikimedia/codex-design-tokens:
// Europe = --color-progressive (#36c), Africa = --color-destructive (#bf3c2c),
// Oceania = --color-disabled (#a2a9b1), Non-mappé = --border-color-subtle (#c8ccd1).
const REGION_COLORS = {
  Europe: "#36c",
  Americas: "#fc3",
  Asia: "#ac6600",
  Africa: "#bf3c2c",
  Oceania: "#a2a9b1",
  "Non-mappé": "#c8ccd1",
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
  if (!country) return "Non-mappé";
  if (country === "Non-mappé" || country.toLowerCase() === "unknown") return "Non-mappé";
  return COUNTRY_REGION[country] || "Non-mappé";
}

const legendRegions = [
  { key: "Europe", label: "Europe", color: REGION_COLORS.Europe },
  { key: "Americas", label: "Amériques", color: REGION_COLORS.Americas },
  { key: "Asia", label: "Asie", color: REGION_COLORS.Asia },
  { key: "Africa", label: "Afrique", color: REGION_COLORS.Africa },
  { key: "Oceania", label: "Océanie", color: REGION_COLORS.Oceania },
  { key: "Non-mappé", label: "Non-mappé", color: REGION_COLORS["Non-mappé"] },
];

const props = defineProps({ analysis: { type: Object, required: true } });

const top10 = computed(() => {
  const dist = props.analysis.aggregated_bias?.geography_distribution || {};
  return Object.entries(dist)
    .map(([country, v]) => ({
      country,
      count: v.count || 0,
      percentage: v.percentage || 0,
      region: regionFor(country),
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);
});

const hasData = computed(() => top10.value.some((t) => t.count > 0));

const chartData = computed(() => ({
  labels: top10.value.map((t) => t.country),
  datasets: [
    {
      label: "Sources",
      data: top10.value.map((t) => t.count),
      backgroundColor: top10.value.map((t) => REGION_COLORS[t.region] || REGION_COLORS["Non-mappé"]),
      borderColor: top10.value.map((t) => REGION_COLORS[t.region] || REGION_COLORS["Non-mappé"]),
      borderWidth: 0,
      borderRadius: 3,
      barPercentage: 0.72,
    },
  ],
}));

const chartOptions = {
  indexAxis: "y",
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => {
          const t = top10.value[ctx.dataIndex];
          return `${t.count} sources (${t.percentage}%) — ${t.region}`;
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
};
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
