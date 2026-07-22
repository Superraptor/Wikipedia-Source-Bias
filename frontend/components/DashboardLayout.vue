<template>
  <div class="dashboard-layout">
    <div v-if="unmappedCount > 0" class="dashboard-layout__notice">
      <CdxMessage type="warning" :fade-in="true">
        {{ unmappedCount }} source{{ unmappedCount > 1 ? "s" : "" }} non-mappée{{ unmappedCount > 1 ? "s" : "" }}
        ({{ unmappedPct }}%) — pays d'origine non résolu via Wikidata ou TLD.
      </CdxMessage>
    </div>

    <div class="dashboard-layout__grid">
      <div class="dashboard-layout__main">
        <RadarChart :axes="radarAxes" />
        <KpiCards :analysis="analysis" />
        <TopCountriesBar :analysis="analysis" />
        <SourcesTable :analysis="analysis" />
      </div>
      <aside class="dashboard-layout__side">
        <WorldMap :analysis="analysis" />
        <TopSourcesSidebar :analysis="analysis" />
        <CtaPanel :analysis="analysis" />
      </aside>
    </div>

    <section class="dashboard-layout__compare">
      <div class="wsi-section-title">
        <span class="wsi-section-num">08</span>
        <h2>Comparer avec un autre article</h2>
      </div>
      <ArticleInput @analyze="$emit('compare', $event)" />
    </section>

    <MethodologyFooter />
  </div>
</template>

<script setup>
import { computed } from "vue";
import { CdxMessage } from "@wikimedia/codex";
import RadarChart from "~/components/RadarChart.vue";
import KpiCards from "~/components/KpiCards.vue";
import TopCountriesBar from "~/components/TopCountriesBar.vue";
import SourcesTable from "~/components/SourcesTable.vue";
import WorldMap from "~/components/WorldMap.vue";
import TopSourcesSidebar from "~/components/TopSourcesSidebar.vue";
import CtaPanel from "~/components/CtaPanel.vue";
import MethodologyFooter from "~/components/MethodologyFooter.vue";
import ArticleInput from "~/components/ArticleInput.vue";
import { computeRadarAxes } from "~/composables/useRadarData.js";

const props = defineProps({
  analysis: { type: Object, required: true },
});
defineEmits(["compare"]);

const radarAxes = computed(() => computeRadarAxes(props.analysis));

const unmappedCount = computed(() => {
  const dist = props.analysis.aggregated_bias?.geography_distribution || {};
  let n = 0;
  for (const [k, v] of Object.entries(dist)) {
    if (k.toLowerCase() === "non-mappé" || k.toLowerCase() === "unknown") n += v.count || 0;
  }
  return n;
});

const unmappedPct = computed(() => {
  const total = props.analysis.source_count || 1;
  return Math.round((100 * unmappedCount.value) / total * 10) / 10;
});
</script>

<style scoped>
.dashboard-layout {
  max-width: var(--maxw);
  margin: 0 auto;
  padding: var(--space-5) var(--space-6) 0;
}
.dashboard-layout__notice {
  margin-bottom: var(--space-4);
}
.dashboard-layout__grid {
  display: grid;
  grid-template-columns: minmax(0, 1.9fr) minmax(280px, 1fr);
  gap: var(--space-5);
  align-items: start;
}
.dashboard-layout__main {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  min-width: 0;
}
.dashboard-layout__side {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  position: sticky;
  top: 84px;
}
.dashboard-layout__compare {
  margin-top: var(--space-7);
  padding-top: var(--space-5);
  border-top: 1px solid var(--wsi-line-soft);
}

@media (max-width: 980px) {
  .dashboard-layout__grid {
    grid-template-columns: 1fr;
  }
  .dashboard-layout__side {
    position: static;
  }
}
</style>
