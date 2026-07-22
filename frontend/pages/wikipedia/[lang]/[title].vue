<template>
  <p class="sr-only">{{ url }}</p>
</template>

<script setup>
/**
 * Legacy unprefixed route. Everything now lives under an explicit version
 * (/v1/... or /v2/...), so this only exists to redirect links that were shared
 * before the prefix was introduced.
 */
import { computed, onMounted } from "vue";
import { routeFor } from "~/utils/wikiroute.js";

const route = useRoute();
const router = useRouter();

const lang = computed(() => String(route.params.lang || "fr").toLowerCase());
const title = computed(() => {
  const raw = String(route.params.title || "");
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
});
const url = computed(() => `https://${lang.value}.wikipedia.org/wiki/${title.value}`);

onMounted(() => router.replace(routeFor(lang.value, title.value)));
</script>

<style scoped>
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}
</style>
