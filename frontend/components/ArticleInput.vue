<template>
  <form class="article-input" @submit.prevent="onSubmit">
    <div class="article-input__field">
      <CdxTextInput
        v-model="url"
        input-type="url"
        placeholder="https://fr.wikipedia.org/wiki/..."
        aria-label="URL de l'article Wikipedia à analyser"
        class="article-input__input"
    />
    </div>
    <CdxButton
      action="progressive"
      weight="primary"
      type="submit"
      class="article-input__submit"
    >
      <CdxIcon :icon="cdxIconSearch" class="article-input__submit-icon" />
      Analyser
    </CdxButton>
  </form>
  <p v-if="hint" class="article-input__hint">{{ hint }}</p>
</template>

<script setup>
import { ref } from "vue";
import { CdxTextInput, CdxButton, CdxIcon } from "@wikimedia/codex";
import { cdxIconSearch } from "@wikimedia/codex-icons";

const emit = defineEmits(["analyze"]);
const url = ref("");
const hint = ref("");

const WIKI_RE = /^https?:\/\/[a-z]{2,}\.wikipedia\.org\/wiki\//i;

function onSubmit() {
  const v = url.value.trim();
  if (!v) {
    hint.value = "Saisissez une URL Wikipedia.";
    return;
  }
  if (!WIKI_RE.test(v)) {
    hint.value = "L'URL doit pointer vers un article Wikipedia (ex : https://fr.wikipedia.org/wiki/...).";
    return;
  }
  hint.value = "";
  emit("analyze", v);
}
</script>

<style scoped>
.article-input {
  display: flex;
  gap: var(--space-3);
  align-items: stretch;
}
.article-input__field {
  flex: 1;
  min-width: 0;
}
.article-input__input {
  height: 100%;
}
.article-input__input :deep(.cdx-text-input__input) {
  height: 48px;
  font-size: 1rem;
  padding-left: var(--space-4);
  border-radius: var(--radius-lg);
  border-color: var(--wsi-line);
  background: var(--wsi-surface);
}
.article-input__input :deep(.cdx-text-input__input):focus {
  border-color: var(--wsi-blue);
  box-shadow: 0 0 0 3px var(--wsi-blue-050);
  outline: none;
}
.article-input__submit {
  height: 48px;
  padding: 0 var(--space-5);
  border-radius: var(--radius-lg);
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 0.98rem;
}
.article-input__submit-icon {
  margin-right: 0;
}
.article-input__hint {
  margin-top: var(--space-2);
  font-size: 0.85rem;
  color: var(--wsi-red);
}

@media (max-width: 560px) {
  .article-input {
    flex-direction: column;
  }
  .article-input__submit {
    justify-content: center;
  }
}
</style>
