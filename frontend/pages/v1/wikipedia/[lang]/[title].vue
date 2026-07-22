<template>
  <ArticleView :url="url" :title="title" />
</template>

<script setup>
/**
 * Explicit v1 route, so the two dashboards are symmetric:
 *   /v1/wikipedia/fr/Brexit   original dashboard
 *   /v2/wikipedia/fr/Brexit   provenance-first rebuild
 *
 * The unprefixed /wikipedia/... route still serves v1, so existing links keep
 * working; this just makes the version addressable for comparison.
 */
import { computed } from "vue";
import ArticleView from "~/components/ArticleView.vue";
import { wikipediaUrl } from "~/utils/wikiroute.js";

const route = useRoute();
const lang = computed(() => String(route.params.lang || "fr").toLowerCase());
const title = computed(() => {
  const raw = String(route.params.title || "");
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
});
const url = computed(() => wikipediaUrl(lang.value, title.value));
</script>
