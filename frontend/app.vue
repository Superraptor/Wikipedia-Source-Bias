<template>
  <div class="wsi-app">
    <NuxtPage />
  </div>
</template>

<script setup>
import { computed } from "vue";

const { t, locale, locales } = useI18n();

// `lang` used to be hard-coded to "fr" in nuxt.config. It has to follow the
// active locale: with strategy `no_prefix` the locale can change after mount
// (browser detection, or the header switcher) without any navigation, and a
// wrong `lang` misleads screen readers and translation tooling.
const htmlLang = computed(() => {
  const match = locales.value.find((l) => l.code === locale.value);
  return match?.language || locale.value;
});
const htmlDir = computed(() => {
  const match = locales.value.find((l) => l.code === locale.value);
  return match?.dir || "ltr";
});

useHead({
  htmlAttrs: { lang: htmlLang, dir: htmlDir },
  title: () => t("app.name"),
  meta: [{ name: "description", content: () => t("app.description") }],
});
</script>

<style>
.wsi-app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
