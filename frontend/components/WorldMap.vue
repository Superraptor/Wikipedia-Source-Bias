<template>
  <section class="world-map wsi-panel">
    <header class="world-map__head">
      <div class="wsi-section-title">
        <span class="wsi-section-num">04</span>
        <h2>Carte des sources</h2>
      </div>
      <p class="world-map__sub">Intensité par pays</p>
    </header>
    <div ref="mapEl" class="world-map__canvas" role="img" aria-label="Carte choroplèthe du nombre de sources par pays"></div>
    <div class="world-map__legend">
      <span class="world-map__legend-label">0</span>
      <div class="world-map__scale" :style="{ background: legendGradient }" aria-hidden="true"></div>
      <span class="world-map__legend-label">{{ maxCount }}</span>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from "vue";
import * as L from "leaflet";
import worldGeo from "~/assets/world.json";

const props = defineProps({ analysis: { type: Object, required: true } });

const GEOJSON_TO_BACKEND = {
  "United States of America": "United States",
  "Republic of Serbia": "Serbia",
  "United Republic of Tanzania": "Tanzania",
  "Republic of the Congo": "Congo",
  "Democratic Republic of the Congo": "DR Congo",
  "Macedonia": "North Macedonia",
  "Bahamas": "The Bahamas",
};

const mapEl = ref(null);
let map = null;
let geoLayer = null;
const countryCounts = ref({});
const maxCount = ref(0);

function recompute() {
  const dist = props.analysis.aggregated_bias?.geography_distribution || {};
  const counts = {};
  for (const [k, v] of Object.entries(dist)) counts[k] = v.count || 0;
  countryCounts.value = counts;
  maxCount.value = Math.max(0, ...Object.values(counts));
  if (geoLayer) geoLayer.setStyle(styleFor);
}

function countFor(feature) {
  const name = feature.properties.name;
  if (countryCounts.value[name] != null) return countryCounts.value[name];
  const alias = GEOJSON_TO_BACKEND[name];
  if (alias && countryCounts.value[alias] != null) return countryCounts.value[alias];
  return 0;
}

// Single source of truth for the choropleth scale. The legend gradient is
// generated from these same stops -- previously colorFor() interpolated its own
// hard-coded RGB endpoints that landed on green at the top of the range while
// the legend CSS ended in blue, so the map and its key disagreed.
const SCALE_STOPS = [
  { at: 0, rgb: [241, 244, 248] },   // #f1f4f8
  { at: 0.55, rgb: [207, 224, 243] }, // #cfe0f3
  { at: 1, rgb: [74, 123, 216] },     // #4a7bd8
];

function sampleScale(t) {
  const x = Math.min(1, Math.max(0, t));
  let lo = SCALE_STOPS[0];
  let hi = SCALE_STOPS[SCALE_STOPS.length - 1];
  for (let i = 0; i < SCALE_STOPS.length - 1; i += 1) {
    if (x >= SCALE_STOPS[i].at && x <= SCALE_STOPS[i + 1].at) {
      lo = SCALE_STOPS[i];
      hi = SCALE_STOPS[i + 1];
      break;
    }
  }
  const span = hi.at - lo.at || 1;
  const k = (x - lo.at) / span;
  const c = lo.rgb.map((v, i) => Math.round(v + (hi.rgb[i] - v) * k));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

const legendGradient = computed(
  () =>
    `linear-gradient(90deg, ${SCALE_STOPS.map(
      (s) => `${sampleScale(s.at)} ${Math.round(s.at * 100)}%`,
    ).join(", ")})`,
);

function colorFor(count) {
  if (!count) return sampleScale(0);
  return sampleScale(count / Math.max(1, maxCount.value));
}

function styleFor(feature) {
  const c = countFor(feature);
  return {
    fillColor: colorFor(c),
    weight: 1,
    color: "#a8adb3",
    fillOpacity: c ? 0.85 : 0.35,
  };
}

onMounted(async () => {
  await nextTick();
  recompute();
  map = L.map(mapEl.value, {
    attributionControl: false,
    zoomControl: false,
    scrollWheelZoom: false,
    worldCopyJump: true,
  }).setView([28, 14], 1);
  L.control.zoom({ position: "bottomright" }).addTo(map);
  geoLayer = L.geoJSON(worldGeo, { style: styleFor }).addTo(map);
  setTimeout(() => map.invalidateSize(), 60);
});

watch(() => props.analysis, recompute, { deep: true });

onBeforeUnmount(() => {
  if (map) {
    map.remove();
    map = null;
    geoLayer = null;
  }
});
</script>

<style scoped>
.world-map {
  padding: var(--space-5) var(--space-5) var(--space-4);
}
.world-map__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.world-map__sub {
  font-size: 0.8rem;
  color: var(--wsi-ink-faint);
}
.world-map__canvas {
  height: 240px;
  border: 1px solid var(--wsi-line-soft);
  border-radius: var(--radius);
  overflow: hidden;
}
.world-map__legend {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-3);
  font-size: 0.78rem;
  color: var(--wsi-ink-soft);
}
.world-map__legend-label {
  font-family: var(--font-mono);
  min-width: 2ch;
  text-align: center;
}
.world-map__scale {
  flex: 1;
  height: 8px;
  border-radius: 4px;
  /* background comes from legendGradient, built from SCALE_STOPS */
}
</style>
