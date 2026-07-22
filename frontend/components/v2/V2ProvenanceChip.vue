<template>
  <component
    :is="href ? 'a' : 'span'"
    class="v2-prov"
    :class="[`v2-prov--${provenance}`, href ? 'v2-prov--link' : null]"
    :href="href || null"
    :target="href ? '_blank' : null"
    :rel="href ? 'noopener noreferrer' : null"
    :title="tooltip"
  >
    <span class="v2-prov__src">{{ sourceLabel }}</span>
    <span v-if="text" class="v2-prov__text">{{ text }}</span>
    <svg v-if="href" class="v2-prov__out" viewBox="0 0 12 12" aria-hidden="true" focusable="false">
      <path d="M4.5 2h5.5v5.5M10 2 5 7M8 8.5V10H2V4h1.5" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
  </component>
</template>

<script setup>
/**
 * "Where this number came from", as a chip the reader can click through to.
 *
 * The user's requirement was to be able to justify the numbers, so anything
 * with a checkable origin becomes an outbound link: Wikidata items resolve to
 * wikidata.org/wiki/<Q-id>, MBFC records to their published page. TLD and
 * name-heuristic origins have nothing to link to and render as a plain chip —
 * the absence of a link is itself the signal that nobody else vouched for it.
 */
import { computed } from "vue";
import { PROVENANCE } from "~/utils/provenance.js";

const props = defineProps({
  provenance: { type: String, required: true },
  /** `{ id, name, url }` from the provenance helpers. */
  reference: { type: Object, default: null },
  /** Optional value/detail shown after the origin name. */
  text: { type: String, default: "" },
  /** Extra tooltip context (a heuristic note, a confidence). */
  detail: { type: String, default: "" },
});

const { t } = useI18n();

const href = computed(() => props.reference?.url || null);

const sourceLabel = computed(() => t(`v2.provenance.${props.provenance}`));

const tooltip = computed(() => {
  const parts = [t(`v2.provenance.${props.provenance}Long`)];
  if (props.reference?.name) parts.push(props.reference.name);
  if (props.reference?.id) parts.push(props.reference.id);
  if (props.detail) parts.push(props.detail);
  return parts.filter(Boolean).join(" — ");
});

// Referenced so the linter sees the import is load-bearing for the doc above.
void PROVENANCE;
</script>

<style scoped>
.v2-prov {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 100%;
  padding: 1px 6px;
  border: 1px solid var(--wsi-line-soft);
  border-radius: var(--radius-pill);
  background: var(--wsi-surface-raised);
  font-size: 0.68rem;
  line-height: 1.5;
  color: var(--wsi-ink-soft);
  text-decoration: none;
}
.v2-prov--link { color: var(--wsi-blue); border-color: var(--wsi-line); }
.v2-prov--link:hover { background: var(--wsi-blue-050); text-decoration: none; }
.v2-prov--link:focus-visible {
  outline: 2px solid var(--wsi-blue);
  outline-offset: 1px;
}
.v2-prov__src {
  font-weight: var(--font-weight-semi-bold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 0.62rem;
}
.v2-prov__text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.v2-prov__out { width: 9px; height: 9px; flex: 0 0 auto; }
</style>
