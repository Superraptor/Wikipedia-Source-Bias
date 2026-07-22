export default defineNuxtConfig({
  ssr: false,
  devtools: { enabled: true },
  css: [
    "@wikimedia/codex-design-tokens/dist/theme-wikimedia-ui-root.css",
    "@wikimedia/codex-design-tokens/dist/theme-wikimedia-ui.css",
    "@wikimedia/codex/dist/codex.style.css",
    "leaflet/dist/leaflet.css",
    "~/assets/main.css",
  ],
  app: {
    head: {
      title: "WikiBias Analyzer",
      htmlAttrs: { lang: "fr" },
      meta: [
        { name: "viewport", content: "width=device-width, initial-scale=1" },
        {
          name: "description",
          content:
            "Analyser les biais citationnels des articles Wikipedia : origine géographique, pluralisme politique et démographique des sources.",
        },
        { name: "theme-color", content: "#3366cc" },
      ],
      // No third-party <link>s here on purpose. The Toolforge Terms of Use
      // (rule 7) forbid exposing end users' browsers to third parties, so the
      // previous Google Fonts preconnect + stylesheet could not ship. Typography
      // now comes from the Codex design tokens' own font stack; to restore the
      // Source family, self-host the woff2 files under frontend/assets.
    },
  },
  nitro: {
    routeRules: {
      // Dev-only. `ssr: false` + `nuxt generate` produces a static bundle with
      // no Nitro server, so in production Flask serves the SPA and /api on the
      // same origin instead (see backend/app.py).
      "/api/**": {
        proxy: "http://127.0.0.1:5000/api/**",
      },
    },
  },
  vite: {
    optimizeDeps: {
      include: ["chart.js", "vue-chartjs", "leaflet"],
    },
  },
});
