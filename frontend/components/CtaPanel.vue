<template>
  <section class="cta-panel wsi-panel">
    <header class="cta-panel__head">
      <div class="wsi-section-title">
        <span class="wsi-section-num">07</span>
        <h2>Exporter</h2>
      </div>
    </header>
    <ul class="cta-panel__list">
      <li>
        <CdxButton action="progressive" weight="primary" class="cta-panel__btn" @click="downloadJson">
          <CdxIcon :icon="cdxIconDownload" size="small" /> Rapport JSON
        </CdxButton>
      </li>
      <li>
        <CdxButton class="cta-panel__btn" @click="share">
          <CdxIcon :icon="cdxIconLink" size="small" /> Partager l'analyse
        </CdxButton>
        <p v-if="shareFeedback" class="cta-panel__feedback">{{ shareFeedback }}</p>
      </li>
      <li>
        <a :href="analysis.page_url" target="_blank" rel="noopener" class="cta-panel__link">
          <CdxIcon :icon="cdxIconArticle" size="small" /> Voir sur Wikipedia
          <CdxIcon :icon="cdxIconLinkExternal" size="small" class="cta-panel__ext" />
        </a>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { ref } from "vue";
import { CdxButton, CdxIcon } from "@wikimedia/codex";
import {
  cdxIconDownload,
  cdxIconLink,
  cdxIconArticle,
  cdxIconLinkExternal,
} from "@wikimedia/codex-icons";

const props = defineProps({ analysis: { type: Object, required: true } });

const shareFeedback = ref("");

function downloadJson() {
  const blob = new Blob([JSON.stringify(props.analysis, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${props.analysis.page_title || "analysis"}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

async function share() {
  shareFeedback.value = "";
  try {
    await navigator.clipboard.writeText(window.location.href);
    shareFeedback.value = "Lien copié dans le presse-papier.";
  } catch {
    shareFeedback.value = "Copiez ce lien : " + window.location.href;
  }
  setTimeout(() => (shareFeedback.value = ""), 3500);
}
</script>

<style scoped>
.cta-panel {
  padding: var(--space-5);
}
.cta-panel__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.cta-panel__btn {
  width: 100%;
  justify-content: center;
}
.cta-panel__btn :deep(.cdx-icon) {
  margin-right: var(--space-2);
}
.cta-panel__feedback {
  margin: var(--space-2) 0 0;
  font-size: 0.8rem;
  color: var(--wsi-green);
}
.cta-panel__link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-3);
  border: 1px solid var(--wsi-line);
  border-radius: var(--radius);
  color: var(--wsi-ink);
  font-size: 0.9rem;
  font-weight: 500;
  transition: border-color 0.18s ease, color 0.18s ease;
}
.cta-panel__link:hover {
  text-decoration: none;
  border-color: var(--wsi-blue);
  color: var(--wsi-blue-700);
}
.cta-panel__ext {
  margin-left: auto;
  color: var(--wsi-ink-faint);
}
</style>
