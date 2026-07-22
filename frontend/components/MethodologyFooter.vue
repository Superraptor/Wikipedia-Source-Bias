<template>
  <footer class="methodology-footer">
    <div class="wsi-container methodology-footer__inner">
      <div class="methodology-footer__col">
        <p class="methodology-footer__label">Méthodologie</p>
        <p class="methodology-footer__text">
          Assignation géographique via l'éditeur Wikidata (P17 / P495) avec
          repli sur le TLD&nbsp;; leans politiques via conditionnel Wikidata
          et repli MBFC. Les sources <em>«&nbsp;Non-mappé&nbsp;»</em> sont
          signalées explicitement, jamais masquées.
        </p>
      </div>
      <div class="methodology-footer__col methodology-footer__meta">
        <p class="methodology-footer__label">Projet</p>
        <p class="methodology-footer__text">
          Wikimania 2026 — Team 05E <em>Deciphering Biases</em>.
          Outil open-source (MIT) déployé sur Toolforge.
        </p>
        <ul class="methodology-footer__links">
          <li><a href="https://wikimania.wikimedia.org/wiki/2026:Team_challenges/Team_05E_Europe" target="_blank" rel="noopener">Méthodologie &amp; équipe</a></li>
          <li><a href="https://github.com/Superraptor/Wikipedia-Source-Bias" target="_blank" rel="noopener">Code source (GitHub)</a></li>
          <li><a href="https://wikibias-analyzer.toolforge.org/" rel="noopener">wikibias-analyzer.toolforge.org</a></li>
          <li><a href="/status">File d'analyse</a></li>
        </ul>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.methodology-footer {
  border-top: 1px solid var(--wsi-line-soft);
  background: linear-gradient(180deg, transparent, var(--wsi-surface-raised));
  padding: var(--space-6) 0;
  margin-top: auto;
}
.methodology-footer__links {
  list-style: none;
  margin: var(--space-2) 0 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-4);
  font-size: 0.85rem;
}
.methodology-footer__links a {
  color: var(--wsi-blue);
}
.methodology-footer__inner {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: var(--space-6);
}
.methodology-footer__label {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--wsi-ink-faint);
  margin-bottom: var(--space-2);
}
.methodology-footer__text {
  font-size: 0.88rem;
  color: var(--wsi-ink-soft);
  max-width: 60ch;
}
.methodology-footer__meta .methodology-footer__text { max-width: 38ch; }

@media (max-width: 720px) {
  .methodology-footer__inner {
    grid-template-columns: 1fr;
  }
}
</style>
