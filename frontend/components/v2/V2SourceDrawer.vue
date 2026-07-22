<template>
  <Teleport to="body">
    <div v-if="open" class="v2-drawer" role="dialog" aria-modal="true" :aria-label="heading">
      <div class="v2-drawer__scrim" @click="emit('close')" />
      <div ref="panelEl" class="v2-drawer__panel" tabindex="-1" @keydown.esc="emit('close')">
        <header class="v2-drawer__head">
          <div>
            <p class="v2-drawer__eyebrow">{{ t("v2.drawer.eyebrow") }}</p>
            <h2 class="v2-drawer__title">{{ heading }}</h2>
            <p class="v2-drawer__count">{{ t("v2.drawer.count", { n: sources.length }) }}</p>
          </div>
          <button type="button" class="v2-drawer__close" :aria-label="t('v2.drawer.close')" @click="emit('close')">
            &times;
          </button>
        </header>

        <p v-if="!sources.length" class="v2-drawer__empty">{{ t("v2.drawer.empty") }}</p>

        <div v-else class="v2-drawer__body">
          <V2SourceCard v-for="(s, i) in sources" :key="`${s.url}-${i}`" :source="s" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
/**
 * "Which sources are actually in this bar?"
 *
 * Clicking any bar or stack segment opens this. It is the mechanism that makes
 * every aggregate falsifiable: if the chart says seven French sources, the
 * drawer lists seven sources and shows, per source, whether "French" came from
 * a Wikidata publisher statement or from reading `.fr` off the domain.
 */
import { nextTick, ref, watch } from "vue";
import V2SourceCard from "./V2SourceCard.vue";

const props = defineProps({
  open: { type: Boolean, default: false },
  /** Translated bucket name for the heading. */
  heading: { type: String, default: "" },
  sources: { type: Array, default: () => [] },
});

const emit = defineEmits(["close"]);
const { t } = useI18n();

const panelEl = ref(null);

// Move focus into the dialog when it opens, and stop the page behind it from
// scrolling, so the drawer is usable from the keyboard and on a phone.
watch(
  () => props.open,
  async (isOpen) => {
    if (typeof document !== "undefined") {
      document.body.style.overflow = isOpen ? "hidden" : "";
    }
    if (isOpen) {
      await nextTick();
      panelEl.value?.focus();
    }
  },
);
</script>

<style scoped>
.v2-drawer {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}
.v2-drawer__scrim {
  position: absolute;
  inset: 0;
  background: rgba(32, 33, 34, 0.4);
}
.v2-drawer__panel {
  position: relative;
  width: min(560px, 100%);
  background: var(--wsi-surface);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: var(--space-5);
}
.v2-drawer__panel:focus { outline: none; }
/* At 375px the drawer becomes a full-height sheet rather than a side panel. */
@media (max-width: 640px) {
  .v2-drawer__panel { padding: var(--space-4) var(--space-3); }
}

.v2-drawer__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  position: sticky;
  top: calc(var(--space-5) * -1);
  background: var(--wsi-surface);
  padding-top: var(--space-1);
}
.v2-drawer__eyebrow {
  font-size: 0.64rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--wsi-blue-700);
  font-weight: var(--font-weight-semi-bold);
}
.v2-drawer__title { font-size: 1.15rem; margin: var(--space-1) 0 0; overflow-wrap: anywhere; }
.v2-drawer__count { font-size: 0.76rem; color: var(--wsi-ink-soft); margin-top: var(--space-1); }
.v2-drawer__close {
  flex: 0 0 auto;
  border: 1px solid var(--wsi-line-soft);
  background: var(--wsi-surface);
  border-radius: var(--radius);
  width: 32px;
  height: 32px;
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
  color: var(--wsi-ink-soft);
}
.v2-drawer__close:hover { border-color: var(--wsi-blue); color: var(--wsi-blue); }

.v2-drawer__body { display: grid; gap: var(--space-3); }
.v2-drawer__empty { font-size: 0.8rem; color: var(--wsi-ink-faint); font-style: italic; }
</style>
