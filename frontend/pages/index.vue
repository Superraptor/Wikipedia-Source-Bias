<template>
  <main class="page-index">
    <!-- The header carries the language switcher, so the landing page needs it
         too: it used to appear only on the dashboard route. -->
    <AppHeader />

    <section class="hero wsi-container">
      <p class="wsi-eyebrow wsi-rise">{{ t("home.eyebrow") }}</p>
      <h1 class="hero__title wsi-rise" style="animation-delay: 60ms">
        {{ t("home.title") }}
      </h1>
      <p class="hero__lede wsi-rise" style="animation-delay: 120ms">
        {{ t("home.lede") }}
      </p>
      <div class="hero__input wsi-rise" style="animation-delay: 180ms">
        <ArticleInput @analyze="goToArticle" />
      </div>
    </section>

    <hr class="wsi-rule wsi-container" />

    <section class="wsi-container page-index__corpus">
      <CorpusExamples @select="goToArticle" />
    </section>

    <MethodologyFooter />
  </main>
</template>

<script setup>
import AppHeader from "~/components/AppHeader.vue";
import ArticleInput from "~/components/ArticleInput.vue";
import CorpusExamples from "~/components/CorpusExamples.vue";
import MethodologyFooter from "~/components/MethodologyFooter.vue";

const { t } = useI18n();
const router = useRouter();

function goToArticle(url) {
  const title = extractTitle(url);
  router.push(`/article/${encodeURIComponent(title)}?src=${encodeURIComponent(url)}`);
}

function extractTitle(url) {
  const m = url.match(/\/wiki\/(.+)$/);
  return m ? decodeURIComponent(m[1]) : url;
}
</script>

<style scoped>
.page-index {
  flex: 1;
  padding-top: var(--space-7);
}
.hero {
  padding-top: var(--space-6);
  padding-bottom: var(--space-7);
}
.hero__title {
  font-size: clamp(2.1rem, 4.6vw, 3.4rem);
  font-weight: 700;
  letter-spacing: -0.025em;
  max-width: 18ch;
  margin: var(--space-3) 0 0;
}
.hero__lede {
  font-size: 1.1rem;
  color: var(--wsi-ink-soft);
  max-width: 56ch;
  margin-top: var(--space-4);
}
.hero__input {
  margin-top: var(--space-6);
  max-width: 720px;
}
.page-index__corpus {
  padding-top: var(--space-6);
  padding-bottom: var(--space-8);
}
</style>
