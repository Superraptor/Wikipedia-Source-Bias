<template>
  <section class="v2-sum wsi-panel">
    <div class="v2-sum__hero">
      <p class="v2-sum__herolabel">{{ t("v2.summary.sources") }}</p>
      <p class="v2-sum__heronum">{{ model.sourceCount }}</p>
      <p class="v2-sum__herohint">
        {{ t("v2.summary.heroHint", { authors: model.authorCount, books: model.bookCount ?? 0 }) }}
      </p>
    </div>

    <!-- How much of the corpus has an external reference behind it. This is
         the honest headline for a provenance-first dashboard: before any
         finding, say how much of it rests on something checkable. -->
    <ul class="v2-sum__tiles">
      <li v-for="tile in tiles" :key="tile.id" class="v2-sum__tile">
        <p class="v2-sum__tilelabel">{{ tile.label }}</p>
        <p class="v2-sum__tileval">{{ tile.cov.known }}<span class="v2-sum__tileof">/{{ tile.cov.total }}</span></p>
        <V2Coverage :coverage="tile.cov" unit="sources" />
        <p class="v2-sum__tilehint">{{ tile.hint }}</p>
      </li>
    </ul>
  </section>
</template>

<script setup>
/**
 * The corpus header: one hero number and the evidence-coverage tiles.
 *
 * Deliberately the first thing on the page. v1 opened with a five-axis radar
 * that looked authoritative regardless of whether anything had been measured;
 * v2 opens by stating how much of the corpus it can actually vouch for, so
 * every chart below is read against that.
 */
import { computed } from "vue";
import V2Coverage from "./V2Coverage.vue";

const props = defineProps({
  /** `buildV2Model()` output. */
  model: { type: Object, required: true },
});

const { t } = useI18n();

const tiles = computed(() => {
  const e = props.model.evidence;
  return [
    {
      id: "wikidata",
      label: t("v2.summary.wikidata"),
      cov: e.wikidata,
      hint: t("v2.summary.wikidataHint"),
    },
    { id: "mbfc", label: t("v2.summary.mbfc"), cov: e.mbfc, hint: t("v2.summary.mbfcHint") },
    {
      id: "geo",
      label: t("v2.summary.geoMeasured"),
      cov: e.geographyMeasured,
      hint: t("v2.summary.geoMeasuredHint"),
    },
    {
      id: "lean",
      label: t("v2.summary.leanKnown"),
      cov: e.leaningKnown,
      hint: t("v2.summary.leanKnownHint"),
    },
  ];
});
</script>

<style scoped>
.v2-sum {
  padding: var(--space-5);
  display: grid;
  gap: var(--space-5);
  grid-template-columns: minmax(160px, 220px) 1fr;
  align-items: start;
}
@media (max-width: 760px) {
  .v2-sum { grid-template-columns: 1fr; }
}

.v2-sum__herolabel {
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--wsi-ink-faint);
}
/* The one hero figure on the page, in the body sans and with proportional
   figures — tabular-nums makes a large standalone number look loose. */
.v2-sum__heronum {
  font-family: var(--font-body);
  font-size: 3rem;
  font-weight: var(--font-weight-bold, 700);
  line-height: 1;
  margin-top: var(--space-2);
  color: var(--wsi-ink);
}
.v2-sum__herohint {
  font-size: 0.76rem;
  color: var(--wsi-ink-soft);
  margin-top: var(--space-2);
}

.v2-sum__tiles {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-4);
}
.v2-sum__tile {
  display: grid;
  gap: var(--space-1);
  border-left: 2px solid var(--wsi-line-soft);
  padding-left: var(--space-3);
}
.v2-sum__tilelabel {
  font-size: 0.72rem;
  color: var(--wsi-ink-soft);
  font-weight: var(--font-weight-semi-bold);
}
.v2-sum__tileval {
  font-size: 1.5rem;
  font-weight: var(--font-weight-semi-bold);
  line-height: 1.1;
}
.v2-sum__tileof { font-size: 0.9rem; color: var(--wsi-ink-faint); font-weight: 400; }
.v2-sum__tilehint { font-size: 0.68rem; color: var(--wsi-ink-faint); line-height: 1.4; }
</style>
