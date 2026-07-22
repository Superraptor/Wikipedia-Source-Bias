<template>
  <section class="v2-gender">
    <header class="v2-gender__head">
      <h3 class="v2-gender__title">{{ t("v2.gender.title") }}</h3>
      <p class="v2-gender__lede">{{ t("v2.gender.lede") }}</p>
    </header>

    <p v-if="!gender.total" class="v2-gender__empty">{{ t("v2.gender.noAuthors") }}</p>

    <template v-else>
      <!-- Two panels, never one merged chart. Adding a Wikidata statement to a
           spelling guess would produce a number that describes neither. -->
      <div class="v2-gender__grid">
        <article
          v-for="panel in panels"
          :key="panel.id"
          class="v2-gender__panel"
          :class="`v2-gender__panel--${panel.id}`"
        >
          <header class="v2-gender__panelhead">
            <V2EvidenceBadge :evidence="panel.evidence" :detail="panel.detail" />
            <p class="v2-gender__panelname">{{ panel.name }}</p>
            <V2ProvenanceChip :provenance="panel.provenance" :detail="panel.detail" />
          </header>

          <!-- Zero confirmed authors is "nothing is confirmed", not "0% women". -->
          <p v-if="panel.data.coverage.empty" class="v2-gender__none">
            {{ t(`v2.gender.none.${panel.id}`, { total: gender.total }) }}
          </p>

          <ul v-else class="v2-gender__bars">
            <li v-for="e in panel.data.entries" :key="e.key" class="v2-gender__bar">
              <span class="v2-gender__barlabels">
                <span class="v2-gender__barname">{{ genderLabel(e.key) }}</span>
                <span class="v2-gender__barval">{{ e.count }} · {{ e.percentage.toFixed(0) }}%</span>
              </span>
              <span class="v2-gender__track">
                <span
                  class="v2-gender__fill"
                  :class="{ 'v2-gender__fill--est': panel.id === 'estimated' }"
                  :style="{ width: `${e.percentage}%`, '--v2-fill': hueFor(e.key) }"
                />
              </span>
            </li>
          </ul>

          <V2Coverage :coverage="panel.data.coverage" unit="authors" />
        </article>
      </div>

      <p class="v2-gender__undetermined">
        {{ t("v2.gender.undetermined", { n: gender.undetermined, total: gender.total }) }}
      </p>

      <!-- The receipt. Where the two channels disagree, name the authors: it is
           the clearest possible demonstration of why they are shown apart. -->
      <details v-if="disagreements.length" class="v2-gender__diff">
        <summary>{{ t("v2.gender.disagreeTitle", { n: disagreements.length }) }}</summary>
        <p class="v2-gender__diffnote">{{ t("v2.gender.disagreeNote") }}</p>
        <ul class="v2-gender__difflist">
          <li v-for="d in disagreements" :key="`${d.name}-${d.wikidataId}`">
            <span class="v2-gender__diffname">{{ d.name }}</span>
            <span class="v2-gender__diffbody">
              {{ t(`v2.gender.disagree.${d.kind}`, {
                estimated: d.estimated ? genderLabel(d.estimated) : t("v2.gender.unknownValue"),
                measured: genderLabel(d.measured),
                confidence: d.confidence != null ? Math.round(d.confidence * 100) : "—",
              }) }}
            </span>
            <V2ProvenanceChip
              provenance="wikidata"
              :reference="{ id: d.wikidataId, name: d.name, url: wikidataUrl(d.wikidataId) }"
              :text="d.wikidataId || ''"
            />
          </li>
        </ul>
      </details>

      <!-- The backend also publishes its own pre-aggregated gender numbers.
           They are shown here, clearly subordinate, so the corrected keys are
           visible and the per-author walk above can be checked against them. -->
      <details class="v2-gender__agg">
        <summary>{{ t("v2.gender.aggTitle") }}</summary>
        <p class="v2-gender__diffnote">{{ t("v2.gender.aggNote") }}</p>
        <div class="v2-gender__aggwrap">
          <table class="v2-table">
            <thead>
              <tr>
                <th scope="col">{{ t("v2.gender.aggKey") }}</th>
                <th v-for="k in ['female', 'male', 'unknown']" :key="k" scope="col" class="v2-table__num">
                  {{ genderLabel(k) }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in aggregateRows" :key="row.id">
                <th scope="row"><code>{{ row.id }}</code></th>
                <td v-for="k in ['female', 'male', 'unknown']" :key="k" class="v2-table__num">
                  {{ row.values[k] != null ? `${row.values[k].toFixed(1)}%` : "—" }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </details>
    </template>
  </section>
</template>

<script setup>
/**
 * Author gender, split by how it is known.
 *
 * v1's `authorParity` axis read `aggregated_bias.author_gender_distribution` —
 * a key the backend has never emitted. It resolved to `undefined`, so the axis
 * was pinned at 0 for every article. The real keys are
 * `author_gender_distribution_estimate` and `human_author_gender_distribution`.
 *
 * But fixing the key alone would still have been wrong, because both aggregates
 * are dominated by the name-spelling heuristic: on the German test article
 * `human_author_gender_distribution` reports 87.5% "unknown" while Wikidata
 * states a gender for authors the heuristic gave up on. So v2 walks
 * `author_profiles` itself and reports two independent distributions with their
 * own sample sizes, and names the authors where they disagree.
 */
import { computed } from "vue";
import V2EvidenceBadge from "./V2EvidenceBadge.vue";
import V2ProvenanceChip from "./V2ProvenanceChip.vue";
import V2Coverage from "./V2Coverage.vue";
import { EVIDENCE, PROVENANCE, wikidataUrl } from "~/utils/provenance.js";

const props = defineProps({
  /** `genderEvidenceSplit()` output. */
  gender: { type: Object, required: true },
  /** `genderDisagreements()` output. */
  disagreements: { type: Array, default: () => [] },
  /** The corrected aggregate sections, for the audit table. */
  aggregateEstimate: { type: Object, default: null },
  aggregateHuman: { type: Object, default: null },
});

const { t } = useI18n();

// Two categorical slots. Validated all-pairs against the white Codex surface
// (worst CVD ΔE 9.2, worst normal-vision ΔE 24.0).
const HUES = { female: "#2a78d6", male: "#eb6834" };
const hueFor = (key) => HUES[key] || "var(--wsi-ink-faint)";

const genderLabel = (key) => t(`v2.gender.value.${key}`, key);

const panels = computed(() => [
  {
    id: "measured",
    name: t("v2.gender.measuredName"),
    evidence: EVIDENCE.MEASURED,
    provenance: PROVENANCE.WIKIDATA,
    detail: t("v2.gender.measuredDetail"),
    data: props.gender.measured,
  },
  {
    id: "estimated",
    name: t("v2.gender.estimatedName"),
    evidence: EVIDENCE.ESTIMATED,
    provenance: PROVENANCE.HEURISTIC,
    detail: t("v2.gender.estimatedDetail"),
    data: props.gender.estimated,
  },
]);

/** Flatten a distribution section back to `{female, male, unknown}` percentages. */
function rowValues(section) {
  if (!section?.available && !section?.entries?.length) return {};
  const out = {};
  for (const e of section.entries || []) out[String(e.key).toLowerCase()] = e.percentage;
  return out;
}

const aggregateRows = computed(() =>
  [
    { id: "author_gender_distribution_estimate", section: props.aggregateEstimate },
    { id: "human_author_gender_distribution", section: props.aggregateHuman },
  ]
    .filter((r) => r.section)
    .map((r) => ({ id: r.id, values: rowValues(r.section) })),
);
</script>

<style scoped>
.v2-gender__head { margin-bottom: var(--space-4); }
.v2-gender__title { font-size: 1.05rem; margin: 0; }
.v2-gender__lede {
  font-size: 0.8rem;
  color: var(--wsi-ink-soft);
  margin-top: var(--space-2);
  max-width: 62ch;
}
.v2-gender__empty { font-size: 0.8rem; color: var(--wsi-ink-faint); font-style: italic; }

.v2-gender__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-4);
}
.v2-gender__panel {
  border: 1px solid var(--wsi-line-soft);
  border-radius: var(--radius);
  padding: var(--space-3);
  background: var(--wsi-surface);
}
/* The estimated panel is visibly the weaker artefact: a dashed edge on a
   sunken plane, so the hierarchy survives even without reading the badge. */
.v2-gender__panel--estimated {
  border-style: dashed;
  background: var(--wsi-surface-sunken);
}
.v2-gender__panelhead {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
.v2-gender__panelname {
  font-size: 0.8rem;
  font-weight: var(--font-weight-semi-bold);
  flex: 1 1 auto;
  min-width: 0;
}
.v2-gender__none {
  font-size: 0.76rem;
  color: var(--wsi-ink-faint);
  font-style: italic;
  margin-bottom: var(--space-3);
}

.v2-gender__bars { list-style: none; margin: 0 0 var(--space-3); padding: 0; }
.v2-gender__bar + .v2-gender__bar { margin-top: 8px; }
.v2-gender__barlabels {
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
  font-size: 0.75rem;
  margin-bottom: 3px;
}
.v2-gender__barname { color: var(--wsi-ink); }
.v2-gender__barval { color: var(--wsi-ink-soft); font-variant-numeric: tabular-nums; }
.v2-gender__track {
  display: block;
  height: 8px;
  background: var(--wsi-surface-raised);
  border-radius: 2px;
}
.v2-gender__fill {
  display: block;
  height: 100%;
  border-radius: 0 4px 4px 0;
  background: var(--v2-fill);
}
/* Texture is the backup identity channel: estimated bars are hatched at 45°,
   so "this is a guess" survives greyscale, CVD and forced-colors. */
.v2-gender__fill--est {
  background-image: repeating-linear-gradient(
    45deg,
    var(--v2-fill) 0 3px,
    color-mix(in srgb, var(--v2-fill) 45%, #ffffff) 3px 6px
  );
  background-color: var(--v2-fill);
}

.v2-gender__undetermined {
  margin-top: var(--space-3);
  font-size: 0.75rem;
  color: var(--wsi-ink-soft);
}

.v2-gender__diff,
.v2-gender__agg {
  margin-top: var(--space-4);
  border-top: 1px solid var(--wsi-line-soft);
  padding-top: var(--space-3);
}
.v2-gender__diff summary,
.v2-gender__agg summary {
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: var(--font-weight-semi-bold);
  color: var(--wsi-blue);
}
.v2-gender__diffnote {
  font-size: 0.75rem;
  color: var(--wsi-ink-soft);
  margin-top: var(--space-2);
  max-width: 66ch;
}
.v2-gender__difflist {
  list-style: none;
  margin: var(--space-3) 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.v2-gender__difflist li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  font-size: 0.76rem;
}
.v2-gender__diffname { font-weight: var(--font-weight-semi-bold); }
.v2-gender__diffbody { color: var(--wsi-ink-soft); }
.v2-gender__aggwrap { overflow-x: auto; margin-top: var(--space-3); }
.v2-gender__aggwrap code { font-family: var(--font-mono); font-size: 0.7rem; }
</style>
