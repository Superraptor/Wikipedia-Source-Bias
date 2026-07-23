<template>
  <div class="dashboard-layout">
    <!-- The unmapped count is no longer a warning banner. Unmapped sources are
         common and expected (generic .com/.net domains carry no country
         signal), so leading every dashboard with a yellow alert overstated it.
         The count is still visible in the geography chart and each affected
         row still carries its per-source reason. -->

    <ImbalanceNotice :analysis="analysis" />

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
        <h2>{{ t("dashboard.compareTitle") }}</h2>
      </div>
      <ArticleInput @analyze="$emit('compare', $event)" />
    </section>

    <MethodologyFooter />
  </div>
</template>

<script setup>
import ImbalanceNotice from "~/components/ImbalanceNotice.vue";
import { computed } from "vue";
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
import { isUnmapped } from "~/utils/labels.js";

const { t } = useI18n();

const props = defineProps({
  analysis: { type: Object, required: true },
});
defineEmits(["compare"]);

const radarAxes = computed(() => computeRadarAxes(props.analysis));


</script>

<style scoped>
.dashboard-layout {
  max-width: var(--maxw);
  margin: 0 auto;
  padding: var(--space-5) var(--space-6) 0;
}
@media (max-width: 640px) {
  /* Nested inside .wsi-container, which already pads horizontally. Keeping
     both meant the content box lost 128px of a 375px screen. */
  .dashboard-layout {
    padding-left: 0;
    padding-right: 0;
  }
  .dashboard-layout__grid {
    gap: var(--space-3);
  }
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
