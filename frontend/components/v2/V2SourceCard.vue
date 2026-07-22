<template>
  <article class="v2-src">
    <header class="v2-src__head">
      <a class="v2-src__domain" :href="source.url" target="_blank" rel="noopener noreferrer">
        {{ source.domain || source.url }}
      </a>
      <span class="v2-src__type">{{ typeLabel }}</span>
    </header>

    <p v-if="source.citation_text" class="v2-src__cite">{{ source.citation_text }}</p>

    <!-- One row per attribute: the value, how strongly it is known, and a
         link to whoever asserted it. This is the atom the whole dashboard
         aggregates; every bar upstream resolves to rows like these. -->
    <dl class="v2-src__attrs">
      <div v-for="row in attributeRows" :key="row.id" class="v2-src__attr">
        <dt class="v2-src__attrname">{{ row.label }}</dt>
        <dd class="v2-src__attrval">
          <span class="v2-src__value" :class="{ 'v2-src__value--none': row.ev.evidence === 'absent' }">
            {{ row.display }}
          </span>
          <V2EvidenceBadge :evidence="row.ev.evidence" :detail="row.detail" />
          <V2ProvenanceChip
            v-if="row.ev.provenance !== 'none'"
            :provenance="row.ev.provenance"
            :reference="row.ev.ref"
            :detail="row.detail"
          />
          <!-- The backend explains *why* a source could not be placed
               (generic TLD, no country signal). That reason is the most useful
               thing on the row when the value is missing. -->
          <span v-if="row.note" class="v2-src__note">{{ row.note }}</span>
        </dd>
      </div>
    </dl>

    <section v-if="authors.length" class="v2-src__authors">
      <h4 class="v2-src__authorstitle">{{ t("v2.ledger.authors", { n: authors.length }) }}</h4>
      <ul class="v2-src__authorlist">
        <li v-for="(a, i) in authors" :key="`${a.name}-${i}`" class="v2-src__author">
          <span class="v2-src__authorname">{{ a.name || t("v2.ledger.unnamedAuthor") }}</span>
          <span class="v2-src__authorattrs">
            <span class="v2-src__authorattr">
              <span class="v2-src__attrname">{{ t("v2.ledger.gender") }}</span>
              <span class="v2-src__value">{{ a.genderDisplay }}</span>
              <V2EvidenceBadge :evidence="a.genderEv.evidence" :detail="a.genderDetail" />
              <V2ProvenanceChip
                v-if="a.genderEv.provenance !== 'none'"
                :provenance="a.genderEv.provenance"
                :reference="a.genderEv.ref"
                :detail="a.genderDetail"
              />
            </span>
            <span class="v2-src__authorattr">
              <span class="v2-src__attrname">{{ t("v2.ledger.nationality") }}</span>
              <span class="v2-src__value">{{ a.natDisplay }}</span>
              <V2EvidenceBadge :evidence="a.natEv.evidence" :detail="a.natDetail" />
              <V2ProvenanceChip
                v-if="a.natEv.provenance !== 'none'"
                :provenance="a.natEv.provenance"
                :reference="a.natEv.ref"
                :detail="a.natDetail"
              />
            </span>
          </span>
        </li>
      </ul>
    </section>
  </article>
</template>

<script setup>
/**
 * One source, with the evidence behind every attribute.
 *
 * The user's requirement — "I want to get the references so the user knows
 * where the data comes from, it's important to justify the numbers" — bottoms
 * out here. Every aggregate in the dashboard is a count over these cards, and
 * every bar can be opened to reach them.
 */
import { computed } from "vue";
import V2EvidenceBadge from "./V2EvidenceBadge.vue";
import V2ProvenanceChip from "./V2ProvenanceChip.vue";
import {
  authorGenderEvidence,
  authorNationalityEvidence,
  geographyEvidence,
  leaningEvidence,
  reliabilityEvidence,
} from "~/utils/provenance.js";
import { countryLabel, geographyNote, leanBadge, reliabilityLabel } from "~/utils/labels.js";

const props = defineProps({
  source: { type: Object, required: true },
});

const { t } = useI18n();

const typeLabel = computed(() =>
  props.source.source_type ? t(`v2.sourceType.${props.source.source_type}`, props.source.source_type) : "—",
);

const dash = t("app.empty");

const attributeRows = computed(() => {
  const s = props.source;

  const geo = geographyEvidence(s);
  const lean = leaningEvidence(s);
  const rel = reliabilityEvidence(s);

  return [
    {
      id: "country",
      label: t("v2.ledger.country"),
      ev: geo,
      display: geo.value ? countryLabel(geo.value, t) : dash,
      // A TLD-derived country is a real inference but nobody vouched for it.
      detail: geo.provenance === "tld" ? t("v2.provenance.tldLong") : geo.ref?.name || "",
      note: geo.value ? "" : geographyNote(geo.note, t),
    },
    {
      id: "leaning",
      label: t("v2.ledger.leaning"),
      ev: lean,
      display: lean.value ? leanBadge(lean.value, t).label : dash,
      detail: lean.detail || "",
      note: "",
    },
    {
      id: "reliability",
      label: t("v2.ledger.reliability"),
      ev: rel,
      display: rel.value ? reliabilityLabel(rel.value, t) : dash,
      detail: rel.detail || "",
      note: "",
    },
    {
      id: "language",
      label: t("v2.ledger.language"),
      // Detected from the fetched page text by the backend, so: estimated,
      // heuristic. Presenting it as measured would overstate it.
      ev: {
        value: s.language || null,
        evidence: s.language ? "estimated" : "absent",
        provenance: s.language ? "heuristic" : "none",
        ref: null,
      },
      display: s.language || dash,
      detail: s.language_bias?.detected_language
        ? t("v2.ledger.detectedLanguage", { lang: s.language_bias.detected_language })
        : "",
      note: "",
    },
  ];
});

const authors = computed(() =>
  (props.source.author_profiles || []).map((profile) => {
    const genderEv = authorGenderEvidence(profile);
    const natEv = authorNationalityEvidence(profile);
    const pct = (v) => (v != null ? `${Math.round(v * 100)}%` : "");
    return {
      name: profile.name,
      genderEv,
      genderDisplay: genderEv.value ? t(`v2.gender.value.${genderEv.value}`, genderEv.value) : dash,
      genderDetail:
        genderEv.provenance === "heuristic"
          ? [pct(genderEv.confidence) && t("v2.ledger.confidence", { pct: pct(genderEv.confidence) }), genderEv.note]
              .filter(Boolean)
              .join(" — ")
          : genderEv.ref?.name || "",
      natEv,
      natDisplay: natEv.value ? countryLabel(natEv.value, t) : dash,
      natDetail:
        natEv.provenance === "heuristic"
          ? [pct(natEv.confidence) && t("v2.ledger.confidence", { pct: pct(natEv.confidence) }), natEv.note]
              .filter(Boolean)
              .join(" — ")
          : natEv.ref?.name || "",
    };
  }),
);
</script>

<style scoped>
.v2-src {
  border: 1px solid var(--wsi-line-soft);
  border-radius: var(--radius);
  padding: var(--space-3);
  background: var(--wsi-surface);
}
.v2-src__head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
}
.v2-src__domain {
  font-weight: var(--font-weight-semi-bold);
  font-size: 0.85rem;
  overflow-wrap: anywhere;
}
.v2-src__type {
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--wsi-ink-faint);
}
.v2-src__cite {
  margin-top: var(--space-2);
  font-size: 0.74rem;
  color: var(--wsi-ink-soft);
  line-height: 1.45;
  /* Citations run to several hundred characters; clamp rather than truncate in
     JS so the full text stays selectable and searchable. */
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.v2-src__attrs { margin: var(--space-3) 0 0; display: grid; gap: var(--space-2); }
.v2-src__attr { display: grid; gap: 2px; }
.v2-src__attrname {
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--wsi-ink-faint);
}
.v2-src__attrval {
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}
.v2-src__value { font-size: 0.8rem; color: var(--wsi-ink); }
.v2-src__value--none { color: var(--wsi-ink-faint); }
.v2-src__note {
  flex: 1 1 100%;
  font-size: 0.7rem;
  color: var(--wsi-ink-faint);
  line-height: 1.4;
}

.v2-src__authors {
  margin-top: var(--space-3);
  border-top: 1px solid var(--wsi-line-soft);
  padding-top: var(--space-3);
}
.v2-src__authorstitle {
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--wsi-ink-faint);
  margin: 0 0 var(--space-2);
  font-family: var(--font-body);
}
.v2-src__authorlist { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--space-3); }
.v2-src__authorname { font-size: 0.8rem; font-weight: var(--font-weight-semi-bold); }
.v2-src__authorattrs { display: grid; gap: var(--space-1); margin-top: 2px; }
.v2-src__authorattr {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}
</style>
