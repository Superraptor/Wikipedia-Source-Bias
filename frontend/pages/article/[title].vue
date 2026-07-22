<template>
  <ArticleView v-if="url" :url="url" :title="title" />
</template>

<script setup>
/**
 * Legacy route: /article/<title>?src=<encoded url>.
 *
 * Kept so existing links keep working, but it redirects to the canonical
 * /wikipedia/<lang>/<title> whenever the source is a Wikipedia URL, so the
 * ugly form does not stay in the address bar or get shared onward.
 */
import { computed, onMounted } from "vue";
import ArticleView from "~/components/ArticleView.vue";
import { parseWikipediaUrl, routeFor } from "~/utils/wikiroute.js";

const { locale } = useI18n();
const route = useRoute();
const router = useRouter();

const title = computed(() => {
  const raw = String(route.params.title || "");
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
});

const url = computed(() => {
  const src = route.query.src;
  if (typeof src === "string" && /^https?:\/\/.+/i.test(src)) return src;
  if (title.value.startsWith("http")) return title.value;
  // No ?src at all: assume the Wikipedia edition matching the interface language.
  return `https://${locale.value}.wikipedia.org/wiki/${encodeURIComponent(title.value)}`;
});

onMounted(() => {
  const parsed = parseWikipediaUrl(url.value);
  if (parsed) router.replace(routeFor(parsed.lang, parsed.title));
});
</script>
