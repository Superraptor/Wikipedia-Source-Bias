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
      <div class="world-map__scale" aria-hidden="true"></div>
      <span class="world-map__legend-label">{{ maxCount }}</span>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from "vue";
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

function colorFor(count) {
  if (!count) return "#f1f4f8";
  const max = Math.max(1, maxCount.value);
  const t = Math.min(1, count / max);
  const r = Math.round(214 - 158 * t);
  const g = Math.round(234 - 92 * t);
  const b = Math.round(245 - 138 * t);
  return `rgb(${r}, ${g}, ${b})`;
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
  background: linear-gradient(90deg, #f1f4f8 0%, #cfe0f3 55%, #4a7bd8 100%);
}
</style>
