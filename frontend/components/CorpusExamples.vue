<template>
  <section class="corpus" aria-labelledby="corpus-title">
    <div class="wsi-section-title">
      <span class="wsi-section-num">01</span>
      <h2 id="corpus-title">{{ t("corpus.title") }}</h2>
    </div>
    <div class="corpus__grid">
      <button
        v-for="(item, i) in corpus"
        :key="item.url"
        class="corpus__card wsi-panel"
        :style="{ animationDelay: `${Math.min(i, 8) * 70}ms` }"
        @click="emit('select', item.url)"
      >
        <span class="corpus__bar" :class="`corpus__bar--${item.status}`" aria-hidden="true"></span>
        <span class="corpus__body">
          <span class="corpus__lang">{{ item.lang }}</span>
          <span class="corpus__title">{{ item.title }}</span>
          <span class="corpus__meta">
            <template v-if="item.status === 'done'">
              <!-- An unknown count is not zero. The placeholder entries used
                   when the queue is unreachable carry no count, and rendering
                   `?? 0` made the page claim "0 sources" for articles that
                   plainly had plenty. -->
              <span v-if="typeof item.sourceCount === 'number'" class="corpus__count">
                {{ t("corpus.sourceCount", { count: item.sourceCount }) }}
              </span>
              <span v-else class="corpus__pending">{{ t("corpus.countUnknown") }}</span>
            </template>
            <template v-else-if="item.status === 'error'">
              <span class="corpus__failed">{{ t("corpus.failed") }}</span>
            </template>
            <template v-else>
              <!-- Still being analysed: show it is alive rather than hiding it. -->
              <span class="corpus__spinner" aria-hidden="true"></span>
              <span class="corpus__pending">
                {{ item.status === "running"
                    ? t("corpus.running", { pct: item.progressPct ?? 0 })
                    : t("corpus.queued") }}
              </span>
            </template>
          </span>
        </span>
        <span class="corpus__arrow" aria-hidden="true">
          <CdxIcon :icon="cdxIconNext" size="small" />
        </span>
      </button>
    </div>
  </section>
</template>

<script setup>
import { CdxIcon } from "@wikimedia/codex";
import { cdxIconNext } from "@wikimedia/codex-icons";

import { computed, onMounted, onBeforeUnmount } from "vue";
import { useRecentArticles } from "~/composables/useRecentArticles.js";

const { t } = useI18n();
const emit = defineEmits(["select"]);

// Titles and URLs are data, not copy: they name real Wikipedia articles in
// their own language and must not be translated.

// Seed shown only if the queue is unreachable, so the section is never empty.
const FALLBACK = [
  { title: "Emmanuel Macron", lang: "FR", status: "done", sourceCount: null, url: "https://fr.wikipedia.org/wiki/Emmanuel_Macron" },
  { title: "Angela Merkel", lang: "DE", status: "done", sourceCount: null, url: "https://de.wikipedia.org/wiki/Angela_Merkel" },
  { title: "Brexit", lang: "EN", status: "done", sourceCount: null, url: "https://en.wikipedia.org/wiki/Brexit" },
  { title: "Guerre d'Algérie", lang: "FR", status: "done", sourceCount: null, url: "https://fr.wikipedia.org/wiki/Guerre_d%27Alg%C3%A9rie" },
];

const { items, failed, load } = useRecentArticles(20);
const corpus = computed(() => (failed.value || !items.value.length ? FALLBACK : items.value));

onMounted(() => {
  load();
  // Refresh while anything is in flight so a queued card turns into a result
  // without the visitor reloading.
  timer = setInterval(() => {
    if (items.value.some((i) => i.status === "running" || i.status === "pending")) load();
  }, 15000);
});
onBeforeUnmount(() => clearInterval(timer));
let timer;

</script>

<style scoped>
.corpus__bar--done { background: var(--wsi-europe, #3366cc); }
.corpus__bar--running { background: var(--wsi-blue, #3366cc); }
.corpus__bar--pending { background: var(--wsi-amber, #edab00); }
.corpus__bar--error { background: var(--wsi-red, #bf3c2c); }
.corpus__spinner {
  display: inline-block;
  width: 10px;
  height: 10px;
  margin-right: 0.4em;
  border-radius: 50%;
  border: 2px solid var(--wsi-line-soft);
  border-top-color: var(--wsi-blue);
  animation: wsi-spin 0.8s linear infinite;
  vertical-align: -1px;
}
.corpus__pending { color: var(--wsi-ink-soft); }
.corpus__failed { color: var(--wsi-red, #bf3c2c); }
.corpus__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-4);
}
.corpus__card {
  position: relative;
  display: flex;
  align-items: stretch;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-4) var(--space-4) 0;
  text-align: left;
  cursor: pointer;
  border: 1px solid var(--wsi-line-soft);
  background: var(--wsi-surface);
  color: inherit;
  animation: wsi-rise 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
  transition: box-shadow 0.2s ease, transform 0.2s ease, border-color 0.2s ease;
}
.corpus__card:hover {
  border-color: var(--wsi-blue);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.corpus__card:focus-visible {
  outline: 2px solid var(--wsi-blue);
  outline-offset: 2px;
}
.corpus__bar {
  width: 4px;
  border-radius: 0 4px 4px 0;
  flex: none;
}
.corpus__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.corpus__lang {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 500;
  letter-spacing: 0.12em;
  color: var(--wsi-ink-faint);
}
.corpus__title {
  font-family: var(--font-display);
  font-size: 1.18rem;
  font-weight: 600;
  line-height: 1.25;
  color: var(--wsi-ink);
  margin-top: 2px;
}
.corpus__meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 0.84rem;
  color: var(--wsi-ink-soft);
  margin-top: var(--space-2);
}
.corpus__dot { color: var(--wsi-line); }
.corpus__country { color: var(--wsi-ink); font-weight: 500; }
.corpus__arrow {
  align-self: center;
  color: var(--wsi-ink-faint);
  transition: transform 0.2s ease, color 0.2s ease;
}
.corpus__card:hover .corpus__arrow {
  color: var(--wsi-blue);
  transform: translateX(3px);
}
</style>
