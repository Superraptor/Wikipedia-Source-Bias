<template>
  <header class="app-header">
    <div class="wsi-container app-header__bar">
      <a class="app-header__brand" href="/" @click.prevent="goHome">
        <span class="app-header__mark" aria-hidden="true">
          <CdxIcon :icon="cdxIconLogoWikimedia" />
        </span>
        <span class="app-header__wordmark">
          <span class="app-header__title">Wiki Source Bias Analyzer</span>
          <span class="app-header__subtitle">Décrypter les biais citationnels des articles Wikipedia</span>
        </span>
      </a>
      <nav class="app-header__nav" aria-label="Principal">
        <a class="app-header__navlink" href="https://www.mediawiki.org/wiki/Wikimedia_Codex" target="_blank" rel="noopener">
          Méthodologie
        </a>
        <a class="app-header__navlink" href="https://github.com/Superraptor/Wikipedia-Source-Bias" target="_blank" rel="noopener">
          Code source
        </a>
      </nav>
    </div>
    <div class="app-header__accent" aria-hidden="true"></div>
  </header>
</template>

<script setup>
import { CdxIcon } from "@wikimedia/codex";
import { cdxIconLogoWikimedia } from "@wikimedia/codex-icons";

const router = useRouter();
function goHome() {
  router.push("/");
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
  .app-header__subtitle,
  .app-header__nav {
    display: none;
  }
}
</style>
