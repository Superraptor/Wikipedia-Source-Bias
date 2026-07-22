<template>
  <section class="sources-table wsi-panel">
    <header class="sources-table__head">
      <div class="wsi-section-title">
        <span class="wsi-section-num">05</span>
        <h2>{{ t("sourcesTable.title") }}</h2>
      </div>
      <span class="sources-table__count">{{ t("sourcesTable.count", { count: analysis.sources.length }) }}</span>
    </header>
    <div class="sources-table__scroll">
      <table>
        <thead>
          <tr>
            <th scope="col">{{ t("sourcesTable.columnSource") }}</th>
            <th scope="col">{{ t("sourcesTable.columnCountry") }}</th>
            <th scope="col">{{ t("sourcesTable.columnLean") }}</th>
            <th scope="col">{{ t("sourcesTable.columnReliability") }}</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(s, i) in paginated" :key="i">
            <tr
              class="sources-table__row"
              :class="{ 'sources-table__row--open': expanded === i }"
              :aria-expanded="expanded === i"
              @click="toggle(i)"
            >
              <td class="sources-table__src">
                <span class="sources-table__domain">{{ s.domain || truncate(s.url, 28) }}</span>
                <span class="sources-table__url">{{ truncate(s.url, 52) }}</span>
              </td>
              <td :data-label="t('sourcesTable.columnCountry')">
                {{ countryLabel(s.geography?.country, t) }}
                <!-- Explains WHY a source is unmapped; without it an unmapped
                     row is indistinguishable from a bug. The backend sends a
                     reason code, the sentence is built from the locale file. -->
                <abbr
                  v-if="geographyNote(s.geography?.note, t)"
                  class="sources-table__note"
                  :title="geographyNote(s.geography.note, t)"
                  >&#9432;</abbr
                >
              </td>
              <td :data-label="t('sourcesTable.columnLean')"><LeanBadge :lean="s.political_leaning" /></td>
              <td :data-label="t('sourcesTable.columnReliability')"><ReliabilityBadge :level="s.reliability" /></td>
            </tr>
            <tr v-if="expanded === i" class="sources-table__detail">
              <td colspan="4">
                <dl class="sources-table__detail-grid">
                  <div v-if="hasDetail(s.wikidata_publisher)">
                    <dt>{{ t("sourcesTable.wikidataPublisher") }}</dt>
                    <dd><pre>{{ fmt(s.wikidata_publisher) }}</pre></dd>
                  </div>
                  <div v-if="hasDetail(s.mbfc)">
                    <dt>{{ t("sourcesTable.mbfc") }}</dt>
                    <dd><pre>{{ fmt(s.mbfc) }}</pre></dd>
                  </div>
                  <div v-if="hasDetail(s.language_bias)">
                    <dt>{{ t("sourcesTable.languageBias") }}</dt>
                    <dd><pre>{{ fmt(s.language_bias) }}</pre></dd>
                  </div>
                  <div v-if="s.author_profiles && s.author_profiles.length">
                    <dt>{{ t("sourcesTable.authors") }}</dt>
                    <dd><pre>{{ fmt(s.author_profiles) }}</pre></dd>
                  </div>
                  <div v-if="!hasAnyDetail(s)">
                    <dt>{{ t("sourcesTable.enrichedDetails") }}</dt>
                    <dd><p class="sources-table__nodetail">{{ t("sourcesTable.noDetails") }}</p></dd>
                  </div>
                </dl>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
    <div class="sources-table__pager">
      <CdxButton weight="quiet" :disabled="page === 0" @click="prev">
        <CdxIcon :icon="cdxIconPrevious" size="small" /> {{ t("sourcesTable.previous") }}
      </CdxButton>
      <span class="sources-table__pager-info">{{ t("sourcesTable.pageInfo", { page: page + 1, total: totalPages }) }}</span>
      <CdxButton weight="quiet" :disabled="page >= totalPages - 1" @click="next">
        {{ t("sourcesTable.next") }} <CdxIcon :icon="cdxIconNext" size="small" />
      </CdxButton>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, h } from "vue";
import { CdxButton, CdxIcon } from "@wikimedia/codex";
import { cdxIconNext, cdxIconPrevious } from "@wikimedia/codex-icons";
import { countryLabel, geographyNote, leanBadge, reliabilityBadge } from "~/utils/labels.js";

const { t } = useI18n();
const props = defineProps({ analysis: { type: Object, required: true } });

const PAGE_SIZE = 20;
const page = ref(0);
const expanded = ref(null);

const totalPages = computed(() =>
  Math.max(1, Math.ceil(props.analysis.sources.length / PAGE_SIZE)),
);
const paginated = computed(() =>
  props.analysis.sources.slice(page.value * PAGE_SIZE, (page.value + 1) * PAGE_SIZE),
);

function toggle(i) {
  expanded.value = expanded.value === i ? null : i;
}
function prev() {
  page.value = Math.max(0, page.value - 1);
  expanded.value = null;
}
function next() {
  page.value = Math.min(totalPages.value - 1, page.value + 1);
  expanded.value = null;
}
function truncate(s, n) {
  if (!s) return "";
  return s.length > n ? s.slice(0, n) + "…" : s;
}
function hasDetail(d) {
  return d && typeof d === "object" && Object.keys(d).length > 0;
}
function hasAnyDetail(s) {
  return hasDetail(s.wikidata_publisher) || hasDetail(s.mbfc) || hasDetail(s.language_bias) || (s.author_profiles && s.author_profiles.length);
}
function fmt(o) {
  return JSON.stringify(o, null, 2);
}

// The value -> badge mapping lives in ~/utils/labels.js so it can be unit
// tested against both catalogues without mounting this table.
const LeanBadge = (badgeProps) => {
  const m = leanBadge(badgeProps.lean, t);
  return h("span", { class: `badge ${m.cls}` }, m.label);
};
LeanBadge.props = ["lean"];

const ReliabilityBadge = (badgeProps) => {
  const m = reliabilityBadge(badgeProps.level, t);
  return h("span", { class: `badge ${m.cls}` }, m.label);
};
ReliabilityBadge.props = ["level"];
</script>

<style scoped>
/* Below 640px the four columns cannot coexist: the table became a horizontal
   scroller whose country / leaning / reliability columns sat off-screen, so
   the numbers that matter were invisible unless you thought to swipe. Each
   row becomes a card with labelled fields instead. */
@media (max-width: 640px) {
  .sources-table__scroll {
    overflow-x: visible;
  }
  .sources-table thead {
    /* Visually hidden, still announced to screen readers. */
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
  .sources-table table,
  .sources-table tbody,
  .sources-table tr,
  .sources-table td {
    display: block;
    width: 100%;
  }
  .sources-table__row {
    border: 1px solid var(--wsi-line-soft);
    border-radius: 4px;
    padding: var(--space-2);
    margin-bottom: var(--space-2);
  }
  .sources-table__row td {
    border-bottom: 0;
    padding: 2px 0;
  }
  .sources-table__row td[data-label]::before {
    content: attr(data-label) " ";
    font-family: var(--font-mono);
    font-size: 0.68rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--wsi-ink-faint);
    margin-right: 0.4em;
  }
  .sources-table__src {
    min-width: 0;
  }
  .sources-table__url {
    word-break: break-all;
  }
  .sources-table__detail td {
    padding: var(--space-2) 0;
  }
  .sources-table__detail pre {
    white-space: pre-wrap;
    word-break: break-word;
  }
}
.sources-table {
  padding: var(--space-5);
}
.sources-table__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.sources-table__count {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--wsi-ink-faint);
}
.sources-table__scroll {
  overflow-x: auto;
}
.sources-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.sources-table th {
  text-align: left;
  padding: var(--space-2) var(--space-3);
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--wsi-ink-faint);
  border-bottom: 1px solid var(--wsi-line);
  white-space: nowrap;
}
.sources-table td {
  padding: var(--space-3);
  border-bottom: 1px solid var(--wsi-line-soft);
  vertical-align: top;
  color: var(--wsi-ink);
}
.sources-table__row {
  cursor: pointer;
  transition: background 0.15s ease;
}
.sources-table__row:hover { background: var(--wsi-surface-raised); }
.sources-table__row--open { background: var(--wsi-blue-050); }
.sources-table__src {
  min-width: 220px;
}
.sources-table__domain {
  display: block;
  font-weight: 600;
  color: var(--wsi-ink);
}
.sources-table__url {
  display: block;
  font-family: var(--font-mono);
  font-size: 0.76rem;
  color: var(--wsi-ink-faint);
  margin-top: 2px;
  word-break: break-all;
}
.sources-table__detail td {
  background: var(--wsi-surface-raised);
  padding: var(--space-4) var(--space-5);
}
.sources-table__detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-4);
  margin: 0;
}
.sources-table__detail-grid dt {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--wsi-ink-faint);
  margin-bottom: var(--space-2);
}
.sources-table__detail-grid dd {
  margin: 0;
}
.sources-table__detail-grid pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--font-mono);
  font-size: 0.78rem;
  color: var(--wsi-ink-soft);
  margin: 0;
  line-height: 1.5;
}
.sources-table__nodetail {
  font-size: 0.85rem;
  color: var(--wsi-ink-soft);
  font-style: italic;
}
.sources-table__pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-top: var(--space-4);
}
.sources-table__pager-info {
  font-family: var(--font-mono);
  font-size: 0.82rem;
  color: var(--wsi-ink-soft);
}

:deep(.badge) {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 500;
  line-height: 1.5;
  border: 1px solid transparent;
  white-space: nowrap;
}
:deep(.lean--left) { background: var(--background-color-progressive-subtle); color: var(--color-progressive--hover); border-color: #c8ddf3; }
:deep(.lean--right) { background: var(--background-color-destructive-subtle); color: var(--color-destructive); border-color: #f6b5b3; }
:deep(.lean--center) { background: var(--background-color-progressive-subtle); color: var(--color-progressive--hover); border-color: #cfe0f5; }
:deep(.lean--neutral) { background: var(--background-color-success-subtle); color: var(--color-success); border-color: #c6e3d8; }
:deep(.lean--unknown) { background: var(--background-color-neutral-subtle); color: var(--color-subtle); border-color: var(--border-color-subtle); }
:deep(.rel--academic) { background: var(--background-color-progressive-subtle); color: var(--color-progressive--hover); border-color: #c8ddf3; }
:deep(.rel--high) { background: var(--background-color-success-subtle); color: var(--color-success); border-color: #c6e3d8; }
:deep(.rel--medium) { background: var(--background-color-warning-subtle); color: var(--color-warning); border-color: #f0d878; }
:deep(.rel--low) { background: var(--background-color-destructive-subtle); color: var(--color-destructive); border-color: #f6b5b3; }
:deep(.rel--unknown) { background: var(--background-color-neutral-subtle); color: var(--color-subtle); border-color: var(--border-color-subtle); }

.sources-table__note {
  margin-left: 0.35em;
  cursor: help;
  border: 0;
  text-decoration: none;
  color: var(--wsi-ink-faint);
  font-size: 0.9em;
}
</style>
