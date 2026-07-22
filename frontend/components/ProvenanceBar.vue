<template>
  <aside v-if="analysis" class="prov">
    <p class="prov__line">
      <span class="prov__label">{{ t("provenance.input") }}</span>
      <a
        v-if="analysis.revision_permalink"
        :href="analysis.revision_permalink"
        target="_blank"
        rel="noopener"
      >{{ t("provenance.revision", { id: analysis.revision_id }) }}</a>
      <span v-else class="prov__unknown">{{ t("provenance.revisionUnknown") }}</span>

      <span class="prov__sep" aria-hidden="true">·</span>

      <span class="prov__label">{{ t("provenance.method") }}</span>
      <a :href="methodSourceUrl" target="_blank" rel="noopener" class="prov__mono">
        {{ analysis.method_version || t("provenance.methodUnknown") }}
      </a>

      <span class="prov__sep" aria-hidden="true">·</span>

      <a :href="methodologyUrl" target="_blank" rel="noopener">{{ t("provenance.howItWorks") }}</a>
      <span class="prov__sep" aria-hidden="true">·</span>
      <a :href="disputeUrl" target="_blank" rel="noopener">{{ t("provenance.dispute") }}</a>
    </p>
  </aside>
</template>

<script setup>
/**
 * States the exact inputs behind the figures on the page.
 *
 * A number without its revision is not reproducible: the article changes, and
 * so does the analyser. The method version is a content hash of the modules
 * that determine a result, so two analyses carrying different hashes are
 * genuinely not comparable -- and the page now says so instead of implying
 * they are.
 */
import { computed } from "vue";

const props = defineProps({ analysis: { type: Object, default: null } });
const { t } = useI18n();

const REPO = "https://github.com/Superraptor/Wikipedia-Source-Bias";
const methodologyUrl = `${REPO}/blob/main/METHODOLOGY.md`;
const methodSourceUrl = `${REPO}/tree/main/wikipedia_sources_bias`;

// Pre-fills an issue with everything needed to reproduce the disagreement.
const disputeUrl = computed(() => {
  const a = props.analysis || {};
  const title = `Disputed result: ${a.page_title || a.page_url || "analysis"}`;
  const body = [
    `**Article:** ${a.page_url || "?"}`,
    `**Revision analysed:** ${a.revision_id || "unknown"}`,
    `**Method version:** ${a.method_version || "unknown"}`,
    `**Sources analysed:** ${a.source_count ?? "?"}`,
    "",
    "**What looks wrong:**",
    "",
    "**What you would expect instead, and why:**",
    "",
  ].join("\n");
  return `${REPO}/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
});
</script>

<style scoped>
.prov {
  margin: var(--space-3) 0 var(--space-5);
  padding: var(--space-2) var(--space-3);
  border-left: 2px solid var(--wsi-line);
  background: var(--wsi-surface-raised);
  border-radius: 2px;
}
.prov__line {
  margin: 0;
  font-size: 0.8rem;
  color: var(--wsi-ink-soft);
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: baseline;
}
.prov__label {
  color: var(--wsi-ink-faint);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.prov__mono {
  font-family: var(--font-mono);
}
.prov__unknown {
  color: var(--wsi-ink-faint);
  font-style: italic;
}
.prov__sep {
  color: var(--wsi-line);
}
.prov a {
  color: var(--wsi-blue);
}
</style>
