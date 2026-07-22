<template>
  <section class="v2-ledger wsi-panel">
    <header class="v2-ledger__head">
      <div>
        <h2 class="v2-ledger__title">{{ t("v2.ledger.title") }}</h2>
        <p class="v2-ledger__lede">{{ t("v2.ledger.lede") }}</p>
      </div>
    </header>

    <div class="v2-ledger__controls">
      <label class="v2-ledger__search">
        <span class="v2-ledger__searchlabel">{{ t("v2.ledger.filterLabel") }}</span>
        <input
          v-model="query"
          type="search"
          class="v2-ledger__input"
          :placeholder="t('v2.ledger.filterPlaceholder')"
        />
      </label>
      <p class="v2-ledger__showing">{{ t("v2.ledger.showing", { n: filtered.length, total: sources.length }) }}</p>
    </div>

    <p v-if="!filtered.length" class="v2-ledger__empty">{{ t("v2.ledger.noMatch") }}</p>

    <div v-else class="v2-ledger__list">
      <V2SourceCard v-for="(s, i) in visible" :key="`${s.url}-${i}`" :source="s" />
    </div>

    <button
      v-if="filtered.length > visible.length"
      type="button"
      class="v2-ledger__more"
      @click="limit += PAGE"
    >
      {{ t("v2.ledger.more", { n: Math.min(PAGE, filtered.length - visible.length) }) }}
    </button>
  </section>
</template>

<script setup>
/**
 * The full evidence ledger: every source, every attribute, every reference.
 *
 * The dashboard above is a set of summaries; this is the underlying record, and
 * the reason the summaries can be trusted. It is also the table view of last
 * resort for the charts — nothing in v2 is reachable only through colour or
 * only through hover.
 *
 * Rendering is paged because a long article can carry hundreds of sources and
 * each card is fairly heavy.
 */
import { computed, ref, watch } from "vue";
import V2SourceCard from "./V2SourceCard.vue";

const props = defineProps({
  sources: { type: Array, default: () => [] },
});

const { t } = useI18n();

const PAGE = 25;
const query = ref("");
const limit = ref(PAGE);

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return props.sources;
  return props.sources.filter((s) => {
    const hay = [
      s.domain,
      s.url,
      s.citation_text,
      s.geography?.country,
      s.political_leaning,
      s.reliability,
      s.source_type,
      s.language,
      s.wikidata_publisher?.wikidata_name,
      ...(s.author_profiles || []).map((a) => a.name),
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return hay.includes(q);
  });
});

const visible = computed(() => filtered.value.slice(0, limit.value));

// A new query starts from the top; otherwise a narrowed list keeps a paging
// offset that no longer means anything.
watch(query, () => {
  limit.value = PAGE;
});
</script>

<style scoped>
.v2-ledger { padding: var(--space-5); }
.v2-ledger__head { margin-bottom: var(--space-4); }
.v2-ledger__title { font-size: 1.05rem; margin: 0; }
.v2-ledger__lede {
  font-size: 0.8rem;
  color: var(--wsi-ink-soft);
  margin-top: var(--space-2);
  max-width: 66ch;
}
.v2-ledger__controls {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.v2-ledger__search { display: grid; gap: var(--space-1); flex: 1 1 220px; }
.v2-ledger__searchlabel {
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--wsi-ink-faint);
}
.v2-ledger__input {
  border: 1px solid var(--wsi-line);
  border-radius: var(--radius);
  padding: 6px 8px;
  font: inherit;
  font-size: 0.82rem;
  background: var(--wsi-surface);
  color: var(--wsi-ink);
  width: 100%;
}
.v2-ledger__input:focus-visible { outline: 2px solid var(--wsi-blue); outline-offset: 1px; }
.v2-ledger__showing { font-size: 0.74rem; color: var(--wsi-ink-soft); }
.v2-ledger__list { display: grid; gap: var(--space-3); }
.v2-ledger__empty { font-size: 0.8rem; color: var(--wsi-ink-faint); font-style: italic; }
.v2-ledger__more {
  margin-top: var(--space-4);
  border: 1px solid var(--wsi-line);
  background: var(--wsi-surface);
  border-radius: var(--radius);
  padding: 6px 14px;
  font: inherit;
  font-size: 0.78rem;
  color: var(--wsi-blue);
  cursor: pointer;
}
.v2-ledger__more:hover { background: var(--wsi-blue-050); }
</style>
