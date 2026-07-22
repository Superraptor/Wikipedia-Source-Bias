<template>
  <V2ArticleView :url="url" :title="title" />
</template>

<script setup>
/**
 * /v2/wikipedia/<lang>/<title> — the v2 dashboard for one article.
 *
 * Mirrors the canonical v1 route `/wikipedia/<lang>/<title>` exactly, so the
 * two dashboards can be compared by adding or removing `/v2` from the address
 * bar. v1 is untouched.
 */
import { computed } from "vue";
import V2ArticleView from "~/components/v2/V2ArticleView.vue";
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
