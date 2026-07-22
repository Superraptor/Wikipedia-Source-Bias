<template>
  <div class="v2-page">
    <AppHeader />

    <section class="v2-page__hero wsi-container">
      <p class="wsi-eyebrow">{{ t("v2.article.eyebrow") }}</p>
      <h1 class="v2-page__title">{{ displayTitle }}</h1>
      <a
        v-if="state.data?.page_url"
        class="v2-page__url"
        :href="state.data.page_url"
        target="_blank"
        rel="noopener noreferrer"
      >
        {{ state.data.page_url }}
      </a>
      <!-- Both dashboards read the same analysis, so the comparison is
           one click and no re-fetch. -->
      <NuxtLink class="v2-page__switch" :to="v1Route">{{ t("v2.article.viewV1") }}</NuxtLink>
    </section>

    <main class="wsi-container v2-page__main">
      <LoadingState v-if="state.status === 'loading'" />
      <LoadingState v-else-if="state.status === 'pending'" pending :progress="state.progress" />
      <ErrorState v-else-if="state.status === 'error'" :detail="errorDetail" />
      <EmptyState v-else-if="state.status === 'empty'" />
      <V2Dashboard v-else-if="state.status === 'loaded' && model" :model="model" />
      <ErrorState v-else :detail="t('states.errorUnexpected', { status: state.status })" />
    </main>
  </div>
</template>

<script setup>
/**
 * The v2 article view.
 *
 * Mirrors `components/ArticleView.vue` and reuses `useAnalysis` unchanged — the
 * queue-and-poll behaviour, the 202 handling and the error vocabulary are all
 * shared, so v1 and v2 can only ever differ in how the same payload is
 * presented. Only the dashboard component below it is new.
 */
import { computed, onMounted, watch } from "vue";
import AppHeader from "../AppHeader.vue";
import LoadingState from "../LoadingState.vue";
import ErrorState from "../ErrorState.vue";
import EmptyState from "../EmptyState.vue";
import V2Dashboard from "./V2Dashboard.vue";
import { useAnalysis } from "../../composables/useAnalysis.js";
import { buildV2Model } from "../../composables/useV2Data.js";
import { parseWikipediaUrl, routeFor, routeForUrl } from "../../utils/wikiroute.js";

const props = defineProps({
  url: { type: String, required: true },
  title: { type: String, default: "" },
});

const { t } = useI18n();
const { state, load } = useAnalysis();

const displayTitle = computed(() => (props.title || "").replace(/_/g, " "));

const model = computed(() => (state.value.data ? buildV2Model(state.value.data) : null));

const errorDetail = computed(() =>
  state.value.errorKey ? t(state.value.errorKey) : state.value.error || "",
);

const v1Route = computed(() => {
  const parsed = parseWikipediaUrl(props.url);
  return parsed ? routeFor(parsed.lang, parsed.title) : routeForUrl(props.url);
});

onMounted(() => load(props.url));
watch(() => props.url, (u) => u && load(u));
</script>

<style scoped>
.v2-page { flex: 1; }
.v2-page__hero {
  padding-top: var(--space-6);
  padding-bottom: var(--space-5);
}
.v2-page__title {
  font-size: clamp(1.8rem, 3.6vw, 2.6rem);
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: var(--space-2) 0 0;
}
.v2-page__url {
  display: inline-block;
  margin-top: var(--space-2);
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--wsi-ink-soft);
  word-break: break-all;
}
.v2-page__switch {
  display: inline-block;
  margin-top: var(--space-3);
  font-size: 0.78rem;
}
.v2-page__main { padding-bottom: var(--space-7); }
</style>
