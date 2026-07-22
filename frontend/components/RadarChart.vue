<template>
  <section class="radar-chart wsi-panel">
    <header class="radar-chart__head">
      <div class="wsi-section-title">
        <span class="wsi-section-num">01</span>
        <h2>{{ t("radar.title") }}</h2>
      </div>
      <p class="radar-chart__sub">{{ t("radar.subtitle") }}</p>
    </header>
    <div class="radar-chart__canvas">
      <Radar :data="chartData" :options="chartOptions" />
    </div>
    <ul class="radar-chart__axes" :aria-label="t('radar.axesAria')">
      <li v-for="(a, i) in axesList" :key="a.key">
        <span class="radar-chart__axis-label">{{ a.label }}</span>
        <span class="radar-chart__axis-value">{{ a.value }}</span>
        <span class="radar-chart__axis-bar" aria-hidden="true">
          <span class="radar-chart__axis-fill" :style="{ width: a.value + '%' }"></span>
        </span>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { computed } from "vue";
import { Radar } from "vue-chartjs";
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from "chart.js";
import { RADAR_AXES } from "~/utils/labels.js";

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

const { t } = useI18n();

const props = defineProps({
  axes: { type: Object, required: true },
});

const axesList = computed(() =>
  RADAR_AXES.map((k) => ({
    key: k,
    label: t(`radar.axis.${k}`),
    value: Math.round(props.axes[k] ?? 0),
  })),
);

// Chart.js caches whatever strings it was handed, so the labels have to be part
// of the reactive `chartData`: that is what makes the canvas redraw in the new
// language when the header switcher fires.
const chartData = computed(() => ({
  labels: RADAR_AXES.map((k) => t(`radar.axis.${k}`)),
  datasets: [
    {
      label: t("radar.datasetLabel"),
      data: RADAR_AXES.map((k) => props.axes[k] ?? 0),
      backgroundColor: "rgba(51, 102, 204, 0.18)",
      borderColor: "#3366cc",
      borderWidth: 2,
      pointBackgroundColor: "#3366cc",
      pointBorderColor: "#fff",
      pointBorderWidth: 1.5,
      pointRadius: 4,
      pointHoverRadius: 6,
    },
  ],
}));

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 700, easing: "easeOutQuart" },
  scales: {
    r: {
      min: 0,
      max: 100,
      ticks: { stepSize: 25, color: "#72777d", backdropColor: "transparent", font: { size: 9, family: "Source Code Pro" } },
      grid: { color: "rgba(200,204,209,0.5)" },
      angleLines: { color: "rgba(200,204,209,0.5)" },
      pointLabels: { color: "#202122", font: { family: "Source Sans 3", size: 12, weight: 500 } },
    },
  },
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: { label: (ctx) => `${ctx.raw}/100` },
    },
  },
};
</script>

<style scoped>
.radar-chart {
  padding: var(--space-5);
}
.radar-chart__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.radar-chart__sub {
  font-size: 0.8rem;
  color: var(--wsi-ink-faint);
}
.radar-chart__canvas {
  width: 100%;
  height: 340px;
  margin: 0 auto;
}
.radar-chart__axes {
  list-style: none;
  margin: var(--space-4) 0 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-3) var(--space-4);
}
.radar-chart__axes li {
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-rows: auto auto;
  column-gap: var(--space-2);
  row-gap: 4px;
  align-items: center;
}
.radar-chart__axis-label {
  font-size: 0.82rem;
  color: var(--wsi-ink-soft);
}
.radar-chart__axis-value {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--wsi-ink);
  grid-row: 1;
  grid-column: 2;
}
.radar-chart__axis-bar {
  grid-column: 1 / -1;
  grid-row: 2;
  height: 4px;
  border-radius: 2px;
  background: var(--wsi-surface-sunken);
  overflow: hidden;
}
.radar-chart__axis-fill {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--wsi-blue), var(--wsi-green));
  border-radius: 2px;
  transition: width 0.7s cubic-bezier(0.22, 1, 0.36, 1);
}
</style>
