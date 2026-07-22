<template>
  <main class="page-index">
    <section class="hero wsi-container">
      <p class="wsi-eyebrow wsi-rise">Wikimania 2026 · Team 05E — Deciphering Biases</p>
      <h1 class="hero__title wsi-rise" style="animation-delay: 60ms">
        D'où viennent les sources d'un article&nbsp;Wikipedia&nbsp;?
      </h1>
      <p class="hero__lede wsi-rise" style="animation-delay: 120ms">
        Saisissez l'URL d'un article pour révéler la répartition géographique,
        le pluralisme politique et la démographie de ses sources —
        là où se niche, en filigrane, le biais citationnel.
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
import ArticleInput from "~/components/ArticleInput.vue";
import CorpusExamples from "~/components/CorpusExamples.vue";
import MethodologyFooter from "~/components/MethodologyFooter.vue";

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
