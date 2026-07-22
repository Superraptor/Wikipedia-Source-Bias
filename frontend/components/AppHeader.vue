<template>
  <header class="app-header">
    <div class="wsi-container app-header__bar">
      <a class="app-header__brand" href="/" @click.prevent="goHome">
        <span class="app-header__mark" aria-hidden="true">
          <CdxIcon :icon="cdxIconLogoWikimedia" />
        </span>
        <span class="app-header__wordmark">
          <span class="app-header__title">{{ t("app.name") }}</span>
          <span class="app-header__subtitle">{{ t("header.tagline") }}</span>
        </span>
      </a>
      <nav class="app-header__nav" :aria-label="t('header.navAria')">
        <a class="app-header__navlink" href="https://wikimania.wikimedia.org/wiki/2026:Team_challenges/Team_05E_Europe" target="_blank" rel="noopener">
          {{ t("header.methodology") }}
        </a>
        <a class="app-header__navlink" href="/status">
          {{ t("header.queue") }}
        </a>
        <a class="app-header__navlink" href="https://github.com/Superraptor/Wikipedia-Source-Bias" target="_blank" rel="noopener">
          {{ t("header.sourceCode") }}
        </a>
        <!-- A native <select> rather than a custom popup: it is keyboard- and
             screen-reader-operable for free, and needs no extra JS. -->
        <div class="app-header__lang">
          <CdxIcon :icon="cdxIconLanguage" size="small" class="app-header__lang-icon" aria-hidden="true" />
          <select
            class="app-header__navlink app-header__lang-select"
            :aria-label="t('header.languageAria')"
            :value="locale"
            @change="onLocaleChange"
          >
            <option v-for="l in locales" :key="l.code" :value="l.code">
              {{ l.name }}
            </option>
          </select>
        </div>
      </nav>
    </div>
    <div class="app-header__accent" aria-hidden="true"></div>
  </header>
</template>

<script setup>
import { CdxIcon } from "@wikimedia/codex";
import { cdxIconLogoWikimedia, cdxIconLanguage } from "@wikimedia/codex-icons";

const { t, locale, locales, setLocale } = useI18n();
const router = useRouter();

function goHome() {
  router.push("/");
}

// setLocale() also writes the locale cookie configured in nuxt.config, which is
// what makes an explicit choice outrank browser detection on the next visit.
function onLocaleChange(event) {
  setLocale(event.target.value);
}
</script>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: saturate(140%) blur(10px);
  -webkit-backdrop-filter: saturate(140%) blur(10px);
  border-bottom: 1px solid var(--wsi-line-soft);
}
.app-header__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 68px;
}
.app-header__brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  color: inherit;
}
.app-header__brand:hover {
  text-decoration: none;
}
.app-header__mark {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 9px;
  color: var(--color-inverted-fixed);
  background:
    radial-gradient(120% 120% at 30% 20%, #4a7bd8 0%, var(--wsi-blue) 55%, var(--wsi-blue-700) 100%);
  box-shadow: var(--shadow-sm);
}
.app-header__wordmark {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}
.app-header__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.18rem;
  letter-spacing: -0.015em;
  color: var(--wsi-ink);
}
.app-header__subtitle {
  font-size: 0.78rem;
  color: var(--wsi-ink-soft);
}
.app-header__nav {
  display: flex;
  gap: var(--space-5);
}
.app-header__navlink {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--wsi-ink-soft);
}
.app-header__navlink:hover {
  color: var(--wsi-blue-700);
  text-decoration: none;
}
.app-header__lang {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--wsi-ink-soft);
}
.app-header__lang:hover,
.app-header__lang:focus-within {
  color: var(--wsi-blue-700);
}
.app-header__lang-icon {
  flex: none;
}
/* Matches .app-header__navlink; the appearance reset removes the OS chrome so
   the control reads as one more nav item. */
.app-header__lang-select {
  appearance: none;
  -webkit-appearance: none;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 0.9rem;
  font-weight: 500;
  line-height: inherit;
  padding: 2px 2px 2px 0;
  cursor: pointer;
  border-radius: var(--radius, 2px);
}
.app-header__lang-select:focus-visible {
  outline: 2px solid var(--wsi-blue);
  outline-offset: 2px;
}
.app-header__lang-select option {
  color: var(--wsi-ink);
  background: var(--wsi-surface);
}
.app-header__accent {
  height: 3px;
  background: linear-gradient(90deg,
    var(--wsi-blue) 0%,
    var(--wsi-green) 38%,
    var(--wsi-amber) 62%,
    var(--wsi-red) 100%);
  opacity: 0.85;
}

@media (max-width: 720px) {
  /* The tagline is decorative, so it goes. The nav must NOT: hiding it left
     the language switcher, the analysis queue and the source link completely
     unreachable on a phone. It wraps onto its own row instead. */
  .app-header__subtitle {
    display: none;
  }
  .app-header__bar {
    flex-wrap: wrap;
    row-gap: var(--space-2);
  }
  .app-header__nav {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
    gap: var(--space-1) var(--space-3);
    font-size: 0.85rem;
  }
  .app-header__navlink,
  .app-header__lang-select {
    font-size: 0.85rem;
  }
  /* Comfortable touch targets without making the bar tall. */
  .app-header__navlink {
    padding: 2px 0;
  }
}
</style>
