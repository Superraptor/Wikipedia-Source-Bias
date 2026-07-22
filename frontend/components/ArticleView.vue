<template>
  <div class="page-article">
    <AppHeader />

    <section class="article-hero wsi-container">
      <p class="wsi-eyebrow">{{ t("article.eyebrow") }}</p>
      <h1 class="article-hero__title">{{ displayTitle }}</h1>
      <a v-if="state.data?.page_url" class="article-hero__url" :href="state.data.page_url" target="_blank" rel="noopener">
        {{ state.data.page_url }}
      </a>
    </section>

    <main class="wsi-container page-article__main">
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
</style>
