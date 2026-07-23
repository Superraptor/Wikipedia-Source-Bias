<template>
  <div class="page-article">
    <AppHeader />

    <!-- A missing article gets NO dashboard chrome: presenting an eyebrow
         reading "tableau de bord" above a large title for a page that does not
         exist implied both that the article was real and that an analysis had
         been produced. -->
    <section v-if="!notFound" class="article-hero wsi-container">
      <p class="wsi-eyebrow">{{ t("article.eyebrow") }}</p>
      <h1 class="article-hero__title">{{ displayTitle }}</h1>
      <a v-if="state.data?.page_url" class="article-hero__url" :href="state.data.page_url" target="_blank" rel="noopener">
        {{ state.data.page_url }}
      </a>
    </section>

    <main v-if="notFound" class="wsi-container page-article__notfound">
      <div class="notfound wsi-panel">
        <p class="notfound__icon" aria-hidden="true">🔍</p>
        <h1 class="notfound__title">{{ t("states.notFoundTitle") }}</h1>
        <p class="notfound__text">{{ t("states.errorArticleNotFound") }}</p>
        <p class="notfound__url">{{ url }}</p>
        <div class="notfound__actions">
          <a class="notfound__button" href="/">{{ t("states.notFoundBackHome") }}</a>
          <a class="notfound__link" :href="url" target="_blank" rel="noopener">
            {{ t("states.notFoundCheckWikipedia") }}
          </a>
        </div>
      </div>
    </main>

    <main v-else class="wsi-container page-article__main">
      <LoadingState v-if="state.status === 'loading'" />
      <LoadingState v-else-if="state.status === 'pending'" pending :progress="state.progress" />
      <ErrorState v-else-if="state.status === 'error'" :detail="errorDetail" />
      <EmptyState v-else-if="state.status === 'empty'" />
      <DashboardLayout
        v-else-if="state.status === 'loaded' && state.data"
        :analysis="state.data"
        @compare="goToArticle"
      />
      <!-- Never render nothing: an unhandled status used to leave a blank
           page with no way to tell a queued analysis from a broken one. -->
      <ErrorState
        v-else
        :detail="t('states.errorUnexpected', { status: state.status })"
      />
      <!-- Provenance at the FOOT of the analysis: it answers "where did this
           come from" once the reader has seen the figures. -->
      <ProvenanceBar v-if="state.status === 'loaded'" :analysis="state.data" />
    </main>
  </div>
</template>

<script setup>
/**
 * The article dashboard, shared by both route shapes: the canonical
 * /wikipedia/<lang>/<title> and the legacy /article/<title>?src=<url>.
 */
import { computed, onMounted, watch } from "vue";
import AppHeader from "~/components/AppHeader.vue";
import LoadingState from "~/components/LoadingState.vue";
import ErrorState from "~/components/ErrorState.vue";
import EmptyState from "~/components/EmptyState.vue";
import DashboardLayout from "~/components/DashboardLayout.vue";
import ProvenanceBar from "~/components/ProvenanceBar.vue";
import { useAnalysis } from "~/composables/useAnalysis.js";
import { routeForUrl } from "~/utils/wikiroute.js";

const props = defineProps({
  // Wikipedia URL to analyse.
  url: { type: String, required: true },
  // Human-readable article name for the hero.
  title: { type: String, default: "" },
});

const { t } = useI18n();
const router = useRouter();
const { state, load } = useAnalysis();

const displayTitle = computed(() => (props.title || "").replace(/_/g, " "));

// The backend answers 404 with code "article_not_found"; useAnalysis turns
// that into this key. Anything else is a genuine analysis failure.
const notFound = computed(
  () => state.value.status === "error"
    && state.value.errorKey === "states.errorArticleNotFound",
);

// useAnalysis reports its own failures as i18n keys (it has no access to `t`)
// and backend/network failures as ready-made text.
const errorDetail = computed(() =>
  state.value.errorKey ? t(state.value.errorKey) : state.value.error || "",
);

onMounted(() => load(props.url));
watch(() => props.url, (u) => u && load(u));

function goToArticle(url) {
  router.push(routeForUrl(url));
}
</script>

<style scoped>
.page-article {
  flex: 1;
}
.article-hero {
  padding-top: var(--space-6);
  padding-bottom: var(--space-5);
}
.article-hero__title {
  font-size: clamp(1.8rem, 3.6vw, 2.6rem);
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: var(--space-2) 0 0;
}
.article-hero__url {
  display: inline-block;
  margin-top: var(--space-2);
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--wsi-ink-soft);
  word-break: break-all;
}
.page-article__main {
  padding-bottom: var(--space-7);
}
.page-article__notfound {
  padding: var(--space-7) 0;
}
.notfound {
  max-width: 46rem;
  margin: 0 auto;
  padding: var(--space-7) var(--space-6);
  text-align: center;
}
.notfound__icon {
  font-size: 2rem;
  line-height: 1;
  margin-bottom: var(--space-3);
}
.notfound__title {
  font-family: var(--font-display);
  font-size: 1.4rem;
  font-weight: 700;
  margin: 0 0 var(--space-2);
}
.notfound__text {
  color: var(--wsi-ink-soft);
  max-width: 40ch;
  margin: 0 auto var(--space-3);
}
.notfound__url {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--wsi-ink-faint);
  word-break: break-all;
  margin-bottom: var(--space-4);
}
.notfound__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  justify-content: center;
  align-items: center;
}
.notfound__button {
  background: var(--wsi-blue);
  color: #fff;
  border-radius: 2px;
  padding: 6px 16px;
  font-weight: 600;
  text-decoration: none;
}
.notfound__link {
  color: var(--wsi-blue);
  font-size: 0.9rem;
}
</style>
