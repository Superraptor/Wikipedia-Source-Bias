<template>
  <section class="corpus" aria-labelledby="corpus-title">
    <div class="wsi-section-title">
      <span class="wsi-section-num">01</span>
      <h2 id="corpus-title">Articles récents</h2>
    </div>
    <div class="corpus__grid">
      <button
        v-for="(item, i) in corpus"
        :key="item.url"
        class="corpus__card wsi-panel"
        :style="{ animationDelay: `${i * 70}ms` }"
        @click="emit('select', item.url)"
      >
        <span class="corpus__bar" :style="{ background: regionColor(item.region) }" aria-hidden="true"></span>
        <span class="corpus__body">
          <span class="corpus__lang">{{ item.lang }}</span>
          <span class="corpus__title">{{ item.title }}</span>
          <span class="corpus__meta">
            <span class="corpus__count">{{ item.source_count }} sources</span>
            <span class="corpus__dot" aria-hidden="true">·</span>
            <span class="corpus__country">{{ item.dominant_country }}</span>
          </span>
        </span>
        <span class="corpus__arrow" aria-hidden="true">
          <CdxIcon :icon="cdxIconNext" size="small" />
        </span>
      </button>
    </div>
  </section>
</template>

<script setup>
import { CdxIcon } from "@wikimedia/codex";
import { cdxIconNext } from "@wikimedia/codex-icons";

const emit = defineEmits(["select"]);

const corpus = [
  { title: "Emmanuel Macron", lang: "FR", source_count: 881, dominant_country: "France", region: "Europe", url: "https://fr.wikipedia.org/wiki/Emmanuel_Macron" },
  { title: "Angela Merkel", lang: "DE", source_count: 412, dominant_country: "Germany", region: "Europe", url: "https://de.wikipedia.org/wiki/Angela_Merkel" },
  { title: "Brexit", lang: "EN", source_count: 537, dominant_country: "United Kingdom", region: "Europe", url: "https://en.wikipedia.org/wiki/Brexit" },
  { title: "Guerre d'Algérie", lang: "FR", source_count: 642, dominant_country: "France", region: "Europe", url: "https://fr.wikipedia.org/wiki/Guerre_d%27Alg%C3%A9rie" },
];

function regionColor(region) {
  return {
    Europe: "var(--wsi-europe)",
    Americas: "var(--wsi-americas)",
    Asia: "var(--wsi-asia)",
    Africa: "var(--wsi-africa)",
    Oceania: "var(--wsi-oceania)",
  }[region] || "var(--wsi-line)";
}
</script>

<style scoped>
.corpus__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-4);
}
.corpus__card {
  position: relative;
  display: flex;
  align-items: stretch;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-4) var(--space-4) 0;
  text-align: left;
  cursor: pointer;
  border: 1px solid var(--wsi-line-soft);
  background: var(--wsi-surface);
  color: inherit;
  animation: wsi-rise 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
  transition: box-shadow 0.2s ease, transform 0.2s ease, border-color 0.2s ease;
}
.corpus__card:hover {
  border-color: var(--wsi-blue);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.corpus__card:focus-visible {
  outline: 2px solid var(--wsi-blue);
  outline-offset: 2px;
}
.corpus__bar {
  width: 4px;
  border-radius: 0 4px 4px 0;
  flex: none;
}
.corpus__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.corpus__lang {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 500;
  letter-spacing: 0.12em;
  color: var(--wsi-ink-faint);
}
.corpus__title {
  font-family: var(--font-display);
  font-size: 1.18rem;
  font-weight: 600;
  line-height: 1.25;
  color: var(--wsi-ink);
  margin-top: 2px;
}
.corpus__meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 0.84rem;
  color: var(--wsi-ink-soft);
  margin-top: var(--space-2);
}
.corpus__dot { color: var(--wsi-line); }
.corpus__country { color: var(--wsi-ink); font-weight: 500; }
.corpus__arrow {
  align-self: center;
  color: var(--wsi-ink-faint);
  transition: transform 0.2s ease, color 0.2s ease;
}
.corpus__card:hover .corpus__arrow {
  color: var(--wsi-blue);
  transform: translateX(3px);
}
</style>
