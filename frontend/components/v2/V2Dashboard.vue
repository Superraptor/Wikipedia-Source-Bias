<template>
  <div class="v2-root">
    <!-- Says plainly that this is the experimental view and how it differs. -->
    <aside class="v2-root__banner">
      <p class="v2-root__bannertitle">{{ t("v2.banner.title") }}</p>
      <p class="v2-root__bannertext">{{ t("v2.banner.text") }}</p>
    </aside>

    <V2EvidenceSummary :model="model" />

    <section class="v2-root__section">
      <header class="v2-root__sechead">
        <h2 class="v2-root__sectitle">{{ t("v2.sections.corpus.title") }}</h2>
        <p class="v2-root__seclede">{{ t("v2.sections.corpus.lede") }}</p>
      </header>
      <div class="v2-root__grid">
        <div class="wsi-panel v2-root__card">
          <V2BarChart
            :title="t('v2.charts.geography.title')"
            :subtitle="t('v2.charts.geography.subtitle')"
            :section="model.corpus.geography"
            :labeller="(k) => countryLabel(k, t)"
            :evidence="EVIDENCE.MEASURED"
            :evidence-detail="t('v2.charts.geography.detail')"
            provenance="wikidata"
            @select="openDrawer"
          />
        </div>
        <div class="wsi-panel v2-root__card">
          <V2BarChart
            :title="t('v2.charts.language.title')"
            :subtitle="t('v2.charts.language.subtitle')"
            :section="model.corpus.language"
            :evidence="EVIDENCE.ESTIMATED"
            :evidence-detail="t('v2.charts.language.detail')"
            provenance="heuristic"
            @select="openDrawer"
          />
        </div>
        <div class="wsi-panel v2-root__card">
          <V2BarChart
            :title="t('v2.charts.region.title')"
            :subtitle="t('v2.charts.region.subtitle')"
            :section="model.corpus.region"
            :labeller="regionName"
            :evidence="EVIDENCE.MEASURED"
            provenance="wikidata"
            @select="openDrawer"
          />
        </div>
        <div class="wsi-panel v2-root__card">
          <V2BarChart
            :title="t('v2.charts.sourceType.title')"
            :subtitle="t('v2.charts.sourceType.subtitle')"
            :section="model.corpus.sourceType"
            :labeller="(k) => vocab('sourceType', k)"
            :evidence="EVIDENCE.ESTIMATED"
            :evidence-detail="t('v2.charts.sourceType.detail')"
            provenance="heuristic"
            @select="openDrawer"
          />
        </div>
      </div>
    </section>

    <section class="v2-root__section">
      <header class="v2-root__sechead">
        <h2 class="v2-root__sectitle">{{ t("v2.sections.editorial.title") }}</h2>
        <p class="v2-root__seclede">{{ t("v2.sections.editorial.lede") }}</p>
      </header>
      <div class="v2-root__grid">
        <div class="wsi-panel v2-root__card">
          <!-- The raw leaning strings are shown as the backend emits them
               ("liberal conservatism", "neoliberalism, centre-left"). Folding
               them onto a left-right axis would be a judgement this tool has no
               basis for, and is exactly the kind of invention v2 removes. -->
          <V2BarChart
            :title="t('v2.charts.leaning.title')"
            :subtitle="t('v2.charts.leaning.subtitle')"
            :section="model.editorial.leaning"
            :labeller="(k) => leanBadge(k, t).label"
            :evidence="EVIDENCE.MEASURED"
            :evidence-detail="t('v2.charts.leaning.detail')"
            provenance="wikidata"
            @select="openDrawer"
          />
        </div>
        <div class="wsi-panel v2-root__card">
          <V2OrdinalStack
            :title="t('v2.charts.reliability.title')"
            :subtitle="t('v2.charts.reliability.subtitle')"
            :section="model.editorial.reliability"
            :scale="RELIABILITY_SCALE"
            :labeller="(k) => reliabilityLabel(k, t)"
            :evidence="EVIDENCE.ESTIMATED"
            :evidence-detail="t('v2.charts.reliability.detail')"
            provenance="heuristic"
            @select="openDrawer"
          />
        </div>
      </div>
    </section>

    <section class="v2-root__section">
      <header class="v2-root__sechead">
        <h2 class="v2-root__sectitle">{{ t("v2.sections.authors.title") }}</h2>
        <p class="v2-root__seclede">{{ t("v2.sections.authors.lede") }}</p>
      </header>

      <div class="wsi-panel v2-root__card v2-root__card--wide">
        <V2GenderEvidence
          :gender="model.authors.gender"
          :disagreements="model.authors.disagreements"
          :aggregate-estimate="model.authors.aggregateGenderEstimate"
          :aggregate-human="model.authors.aggregateHuman"
        />
      </div>

      <div class="v2-root__grid">
        <div class="wsi-panel v2-root__card">
          <V2BarChart
            :title="t('v2.charts.authorType.title')"
            :subtitle="t('v2.charts.authorType.subtitle')"
            :section="model.authors.type"
            :labeller="(k) => vocab('authorType', k)"
            :evidence="EVIDENCE.ESTIMATED"
            :evidence-detail="t('v2.charts.authorType.detail')"
            provenance="heuristic"
            unit="authors"
          />
        </div>
        <div class="wsi-panel v2-root__card">
          <V2BarChart
            :title="t('v2.charts.authorNationality.title')"
            :subtitle="t('v2.charts.authorNationality.subtitle')"
            :section="model.authors.nationality"
            :labeller="(k) => countryLabel(k, t)"
            :evidence="EVIDENCE.ESTIMATED"
            :evidence-detail="t('v2.charts.authorNationality.detail')"
            provenance="heuristic"
            unit="authors"
          />
        </div>
        <div class="wsi-panel v2-root__card">
          <!-- Citizenship is the Wikidata-backed twin of the nationality guess
               above; it is usually far sparser, and saying so is the point. -->
          <V2BarChart
            :title="t('v2.charts.authorCitizenship.title')"
            :subtitle="t('v2.charts.authorCitizenship.subtitle')"
            :section="model.authors.citizenship"
            :labeller="(k) => countryLabel(k, t)"
            :evidence="EVIDENCE.MEASURED"
            :evidence-detail="t('v2.charts.authorCitizenship.detail')"
            provenance="wikidata"
            unit="authors"
          />
        </div>
        <div class="wsi-panel v2-root__card">
          <V2BarChart
            :title="t('v2.charts.authorOccupation.title')"
            :subtitle="t('v2.charts.authorOccupation.subtitle')"
            :section="model.authors.occupation"
            :evidence="EVIDENCE.MEASURED"
            :evidence-detail="t('v2.charts.authorOccupation.detail')"
            provenance="wikidata"
            unit="authors"
          />
        </div>
        <div class="wsi-panel v2-root__card">
          <V2BarChart
            :title="t('v2.charts.authorEmployer.title')"
            :subtitle="t('v2.charts.authorEmployer.subtitle')"
            :section="model.authors.employer"
            :evidence="EVIDENCE.MEASURED"
            :evidence-detail="t('v2.charts.authorEmployer.detail')"
            provenance="wikidata"
            unit="authors"
          />
        </div>
        <div class="wsi-panel v2-root__card">
          <V2BarChart
            :title="t('v2.charts.authorSubregion.title')"
            :subtitle="t('v2.charts.authorSubregion.subtitle')"
            :section="model.authors.subregion"
            :labeller="regionName"
            :evidence="EVIDENCE.ESTIMATED"
            provenance="heuristic"
            unit="authors"
          />
        </div>
      </div>
    </section>

    <section class="v2-root__section">
      <header class="v2-root__sechead">
        <h2 class="v2-root__sectitle">{{ t("v2.sections.text.title") }}</h2>
        <p class="v2-root__seclede">{{ t("v2.sections.text.lede") }}</p>
      </header>
      <div class="v2-root__grid">
        <div class="wsi-panel v2-root__card">
          <h3 class="v2-root__cardtitle">{{ t("v2.charts.languageBias.title") }}</h3>
          <div class="v2-root__meta">
            <V2EvidenceBadge :evidence="EVIDENCE.ESTIMATED" :detail="t('v2.charts.languageBias.detail')" />
            <V2ProvenanceChip provenance="heuristic" :detail="t('v2.charts.languageBias.detail')" />
          </div>
          <p v-if="!model.language.available" class="v2-root__empty">
            {{ t("v2.chart.empty.missing") }}
          </p>
          <div v-else class="v2-root__meters">
            <V2Meter
              v-if="model.language.subjectivity"
              :label="t('v2.metrics.subjectivity')"
              :value="model.language.subjectivity.value"
              :max="1"
              :hint="t('v2.metrics.subjectivityHint')"
              :coverage="model.language.subjectivity.coverage"
            />
            <V2Meter
              v-if="model.language.sensationalism"
              :label="t('v2.metrics.sensationalism')"
              :value="model.language.sensationalism.value"
              :max="1"
              :hint="t('v2.metrics.sensationalismHint')"
              :coverage="model.language.sensationalism.coverage"
            />
            <V2Meter
              v-if="model.language.opinion"
              :label="t('v2.metrics.opinion')"
              :value="model.language.opinion.value"
              :max="100"
              :precision="1"
              suffix="%"
              :hint="t('v2.metrics.opinionHint')"
              :coverage="model.language.opinion.coverage"
            />
          </div>
        </div>

        <div class="wsi-panel v2-root__card">
          <h3 class="v2-root__cardtitle">{{ t("v2.charts.readability.title") }}</h3>
          <div class="v2-root__meta">
            <V2EvidenceBadge :evidence="EVIDENCE.MEASURED" :detail="t('v2.charts.readability.detail')" />
            <V2ProvenanceChip provenance="heuristic" :detail="t('v2.charts.readability.detail')" />
          </div>
          <p v-if="!model.readability.available" class="v2-root__empty">
            {{ t("v2.chart.empty.missing") }}
          </p>
          <template v-else>
            <V2Meter
              :label="t('v2.metrics.flesch')"
              :value="model.readability.value"
              :max="100"
              :precision="1"
              :hint="t(`v2.metrics.fleschBand.${model.readability.band}`)"
              :coverage="model.readability.coverage"
            />
            <p class="v2-root__note">{{ t("v2.metrics.fleschNote") }}</p>
          </template>
        </div>
      </div>
    </section>

    <section class="v2-root__section">
      <V2DerivedPanel :derived="model.derived" />
    </section>

    <section class="v2-root__section">
      <V2SourceLedger :sources="model.sources" />
    </section>

    <V2SourceDrawer
      :open="drawer.open"
      :heading="drawer.heading"
      :sources="drawer.sources"
      @close="drawer.open = false"
    />
  </div>
</template>

<script setup>
/**
 * The v2 dashboard.
 *
 * Information architecture, top to bottom:
 *
 *   1. Evidence coverage — how much of this corpus rests on a checkable
 *      external reference. Stated before any finding.
 *   2. Where the sources come from — geography, language, region, type.
 *   3. Editorial character — political leaning (raw), reliability (ordered).
 *   4. Who wrote them — the measured/estimated gender split, then the author
 *      distributions, sparse ones included and labelled as such.
 *   5. Text signals — subjectivity, sensationalism, opinion share, readability,
 *      each with its real sample size.
 *   6. Derived indicators — the only composites, with their formulas.
 *   7. The source ledger — every source and every reference behind it.
 *
 * The v1 radar is gone. Three of its five axes restated a distribution more
 * crudely than the distribution itself does, and two read keys that do not
 * exist in the payload and were therefore pinned at zero for every article.
 */
import { reactive } from "vue";
import V2EvidenceSummary from "./V2EvidenceSummary.vue";
import V2BarChart from "./V2BarChart.vue";
import V2OrdinalStack from "./V2OrdinalStack.vue";
import V2GenderEvidence from "./V2GenderEvidence.vue";
import V2Meter from "./V2Meter.vue";
import V2DerivedPanel from "./V2DerivedPanel.vue";
import V2SourceLedger from "./V2SourceLedger.vue";
import V2SourceDrawer from "./V2SourceDrawer.vue";
import V2EvidenceBadge from "./V2EvidenceBadge.vue";
import V2ProvenanceChip from "./V2ProvenanceChip.vue";
import { EVIDENCE } from "../../utils/provenance.js";
import { sourcesForBucket } from "../../composables/useV2Data.js";
import { countryLabel, isUnmapped, leanBadge, reliabilityLabel } from "../../utils/labels.js";

const props = defineProps({
  /** `buildV2Model()` output. */
  model: { type: Object, required: true },
});

const { t, te } = useI18n();

/**
 * Translate a backend vocabulary value, falling back to the raw value.
 *
 * The analyzer's `source_type` / `author_type` vocabularies are open-ended, so
 * a value we have no wording for must still be displayed as-is rather than
 * rendered as a raw `v2.sourceType.foo` key path.
 */
const vocab = (ns, key) => (te(`v2.${ns}.${key}`) ? t(`v2.${ns}.${key}`) : key);

/**
 * Region label, guarded against gaps in the shared `region.*` catalogue.
 *
 * `utils/labels.js` `regionLabel()` calls `t('region.' + region)` unguarded,
 * but the catalogue only defines Europe / Americas / Asia / Africa / Oceania /
 * unmapped, while the backend actually emits UN sub-region names — the English
 * test article returns "North America", which has no key. v1 renders the raw
 * path `region.North America` on screen for those sources.
 *
 * Fixing the catalogue means touching shared v1 keys, so v2 falls back to the
 * backend's own English name instead, which is at least correct.
 */
const regionName = (key) => {
  if (isUnmapped(key)) return t("region.unmapped");
  return te(`region.${key}`) ? t(`region.${key}`) : key;
};

// Lowest to highest, so the ordinal ramp always runs the same way regardless of
// which levels a given article happens to contain.
const RELIABILITY_SCALE = ["low", "medium", "high", "academic"];

const drawer = reactive({ open: false, heading: "", sources: [] });

function openDrawer({ dimension, key, label }) {
  drawer.sources = sourcesForBucket(props.model.sources, dimension, key);
  drawer.heading = label;
  drawer.open = true;
}
</script>

<!--
  Chart tokens and the shared table style are intentionally NOT scoped.

  Two reasons. The source drawer is `Teleport`ed to <body>, so it renders
  outside `.v2-root` and would lose any custom property declared on it. And
  `.v2-table` markup lives in child components' own templates, which a scoped
  rule here would never reach. Both are namespaced `v2-`, so nothing collides
  with the v1 dashboard, which never mounts this component.
-->
<style>
:root {
  /* A single blue ramp — the validated sequential hue — plus the two evidence
     inks. Light values only, deliberately: the surrounding app is light-only
     (Codex ships no dark theme here and main.css has no `prefers-color-scheme`
     block), so dark chart steps would put dark marks on a permanently white
     page. If the app gains a dark theme, add the dark steps here and re-run
     the palette validator against the dark surface. */
  --v2-seq-100: #cde2fb;
  --v2-seq-250: #86b6ef;
  --v2-seq-450: #2a78d6;
  --v2-seq-550: #1c5cab;
  /* Evidence inks: distinct from the sequential ramp so an evidence marker
     never reads as a data mark. Both clear 4.5:1 on the white Codex surface. */
  --v2-measured: #184f95;
  --v2-estimated: #8a5300;
}

/* The table twin every chart can switch to — the WCAG-clean equivalent, so no
   value in v2 is reachable only through colour or only through hover. */
.v2-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.76rem;
}
.v2-table th,
.v2-table td {
  text-align: left;
  padding: 4px 8px 4px 0;
  border-bottom: 1px solid var(--wsi-line-soft);
  font-weight: 400;
}
.v2-table thead th {
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--wsi-ink-faint);
  font-weight: var(--font-weight-semi-bold);
}
.v2-table__num {
  text-align: right;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
</style>

<style scoped>
.v2-root {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.v2-root__banner {
  border: 1px solid var(--wsi-line);
  border-left: 3px solid var(--wsi-blue);
  border-radius: var(--radius);
  background: var(--wsi-blue-050);
  padding: var(--space-3) var(--space-4);
}
.v2-root__bannertitle {
  font-size: 0.7rem;
  font-weight: var(--font-weight-semi-bold);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--wsi-blue-700);
}
.v2-root__bannertext {
  font-size: 0.8rem;
  color: var(--wsi-ink-soft);
  margin-top: var(--space-1);
  max-width: 78ch;
}

.v2-root__section { display: flex; flex-direction: column; gap: var(--space-4); }
.v2-root__sechead { display: grid; gap: var(--space-1); }
.v2-root__sectitle { font-size: 1.2rem; margin: 0; }
.v2-root__seclede { font-size: 0.82rem; color: var(--wsi-ink-soft); max-width: 72ch; }

.v2-root__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-4);
}
@media (max-width: 640px) {
  /* At 375px a 300px minimum plus padding would overflow; one column instead. */
  .v2-root__grid { grid-template-columns: 1fr; }
}
.v2-root__card { padding: var(--space-4); }
.v2-root__card--wide { grid-column: 1 / -1; }
.v2-root__cardtitle { font-size: 0.95rem; margin: 0 0 var(--space-2); }
.v2-root__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.v2-root__meters { display: grid; gap: var(--space-4); }
.v2-root__empty { font-size: 0.78rem; color: var(--wsi-ink-faint); font-style: italic; }
.v2-root__note {
  margin-top: var(--space-3);
  font-size: 0.72rem;
  color: var(--wsi-ink-faint);
  line-height: 1.45;
}
</style>
