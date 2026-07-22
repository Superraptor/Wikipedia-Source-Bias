<template>
  <span class="v2-ev" :class="`v2-ev--${evidence}`" :title="title">
    <!-- Identity is icon + word, never colour alone: a solid disc for a sourced
         statement, a hatched disc for a guess, a hollow ring for nothing. The
         three read apart in greyscale, under any CVD, and in forced-colors. -->
    <svg class="v2-ev__mark" viewBox="0 0 12 12" aria-hidden="true" focusable="false">
      <defs v-if="evidence === 'estimated'">
        <pattern :id="hatchId" width="3" height="3" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="3" height="3" fill="var(--v2-ev-bg)" />
          <line x1="0" y1="0" x2="0" y2="3" stroke="currentColor" stroke-width="1.4" />
        </pattern>
      </defs>
      <circle
        cx="6"
        cy="6"
        r="5"
        :fill="fill"
        :stroke="evidence === 'absent' ? 'currentColor' : 'none'"
        stroke-width="1.5"
      />
    </svg>
    <span class="v2-ev__text">{{ label }}</span>
  </span>
</template>

<script setup>
/**
 * The measured / estimated / absent marker.
 *
 * The single most important control in v2. `wikidata_author.gender` is a
 * statement someone published about a named person; `author_profiles[].gender`
 * with `confidence.gender = 0.7` and the note "estimated via first name and
 * surname linguistic origin heuristics" is a guess derived from spelling. v1
 * rendered both as the same bar. Nothing in v2 shows an attribute without one
 * of these beside it.
 */
import { computed, useId } from "vue";
import { EVIDENCE } from "~/utils/provenance.js";

const props = defineProps({
  /** One of EVIDENCE.MEASURED | ESTIMATED | ABSENT. */
  evidence: { type: String, default: EVIDENCE.ABSENT },
  /** Optional detail appended to the tooltip (a note, a confidence, a rating). */
  detail: { type: String, default: "" },
  /** Hide the word and keep only the mark, for dense table cells. */
  compact: { type: Boolean, default: false },
});

const { t } = useI18n();

// `useId` gives a per-instance id, so several hatched badges on one page do not
// all point at the first <pattern> in the document.
const hatchId = `v2hatch-${useId()}`;

const fill = computed(() => {
  if (props.evidence === EVIDENCE.MEASURED) return "currentColor";
  if (props.evidence === EVIDENCE.ESTIMATED) return `url(#${hatchId})`;
  return "none";
});

const label = computed(() =>
  props.compact ? "" : t(`v2.evidence.${props.evidence}`),
);

const title = computed(() => {
  const head = t(`v2.evidence.${props.evidence}Long`);
  return props.detail ? `${head} — ${props.detail}` : head;
});
</script>

<style scoped>
.v2-ev {
  --v2-ev-bg: var(--wsi-surface);
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: 0.7rem;
  font-weight: var(--font-weight-semi-bold);
  letter-spacing: 0.02em;
  white-space: nowrap;
}
.v2-ev__mark {
  width: 10px;
  height: 10px;
  flex: 0 0 auto;
}
/* Text stays in an ink token; the mark beside it carries the distinction. */
.v2-ev--measured { color: var(--v2-measured); }
.v2-ev--estimated { color: var(--v2-estimated); }
.v2-ev--absent { color: var(--wsi-ink-faint); }
.v2-ev__text { color: var(--wsi-ink-soft); }
.v2-ev--absent .v2-ev__text { color: var(--wsi-ink-faint); }
</style>
