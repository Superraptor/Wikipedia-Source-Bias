<template>
  <ArticleView :url="url" :title="title" />
</template>

<script setup>
/**
 * Canonical article route, mirroring Wikipedia's own shape:
 *   /wikipedia/fr/Brexit  ->  https://fr.wikipedia.org/wiki/Brexit
 *
 * No ?src= query string: the language and title in the path are enough to
 * rebuild the source URL, so the link is short and shareable.
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
