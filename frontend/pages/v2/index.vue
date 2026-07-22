<template>
  <div class="v2-entry">
    <AppHeader />

    <main class="wsi-container v2-entry__main">
      <p class="wsi-eyebrow">{{ t("v2.entry.eyebrow") }}</p>
      <h1 class="v2-entry__title">{{ t("v2.entry.title") }}</h1>
      <p class="v2-entry__lede">{{ t("v2.entry.lede") }}</p>

      <form class="v2-entry__form" @submit.prevent="go">
        <label class="v2-entry__label" for="v2-url">{{ t("v2.entry.label") }}</label>
        <div class="v2-entry__row">
          <input
            id="v2-url"
            v-model="input"
            type="url"
            class="v2-entry__input"
            :placeholder="t('v2.entry.placeholder')"
            required
          />
          <button type="submit" class="v2-entry__submit">{{ t("v2.entry.submit") }}</button>
        </div>
        <p v-if="invalid" class="v2-entry__error">{{ t("v2.entry.invalid") }}</p>
      </form>

      <section class="v2-entry__changes">
        <h2 class="v2-entry__subtitle">{{ t("v2.entry.changesTitle") }}</h2>
        <ul class="v2-entry__list">
          <li v-for="i in 4" :key="i">{{ t(`v2.entry.change${i}`) }}</li>
        </ul>
      </section>
    </main>
  </div>
</template>

<script setup>
/**
 * /v2 — entry point for the experimental dashboard.
 *
 * Deliberately minimal: it exists so `/v2` is not a 404 and so the v2 route can
 * be reached without hand-editing a URL. The home page (v1) is untouched.
 */
import { ref } from "vue";
import AppHeader from "~/components/AppHeader.vue";
import { parseWikipediaUrl } from "~/utils/wikiroute.js";

const { t } = useI18n();
const router = useRouter();

const input = ref("");
const invalid = ref(false);

function go() {
  const parsed = parseWikipediaUrl(input.value.trim());
  if (!parsed) {
    invalid.value = true;
    return;
  }
  invalid.value = false;
  router.push(`/v2/wikipedia/${parsed.lang}/${encodeURIComponent(parsed.title)}`);
}
</script>

<style scoped>
.v2-entry { flex: 1; }
.v2-entry__main { padding: var(--space-6) var(--space-6) var(--space-7); }
.v2-entry__title {
  font-size: clamp(1.8rem, 3.6vw, 2.6rem);
  margin: var(--space-2) 0 0;
  letter-spacing: -0.02em;
}
.v2-entry__lede {
  margin-top: var(--space-3);
  font-size: 0.9rem;
  color: var(--wsi-ink-soft);
  max-width: 68ch;
}
.v2-entry__form { margin-top: var(--space-6); max-width: 640px; }
.v2-entry__label {
  display: block;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--wsi-ink-faint);
  margin-bottom: var(--space-2);
}
.v2-entry__row { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.v2-entry__input {
  flex: 1 1 240px;
  min-width: 0;
  border: 1px solid var(--wsi-line);
  border-radius: var(--radius);
  padding: 8px 10px;
  font: inherit;
  font-size: 0.85rem;
  background: var(--wsi-surface);
  color: var(--wsi-ink);
}
.v2-entry__input:focus-visible { outline: 2px solid var(--wsi-blue); outline-offset: 1px; }
.v2-entry__submit {
  flex: 0 0 auto;
  border: 1px solid var(--wsi-blue);
  background: var(--wsi-blue);
  color: #fff;
  border-radius: var(--radius);
  padding: 8px 18px;
  font: inherit;
  font-size: 0.85rem;
  font-weight: var(--font-weight-semi-bold);
  cursor: pointer;
}
.v2-entry__submit:hover { background: var(--wsi-blue-700); }
.v2-entry__error { margin-top: var(--space-2); font-size: 0.78rem; color: var(--wsi-red); }

.v2-entry__changes { margin-top: var(--space-7); }
.v2-entry__subtitle { font-size: 1.05rem; margin: 0 0 var(--space-3); }
.v2-entry__list {
  margin: 0;
  padding-left: 1.1rem;
  display: grid;
  gap: var(--space-2);
  font-size: 0.82rem;
  color: var(--wsi-ink-soft);
  max-width: 72ch;
}
</style>
