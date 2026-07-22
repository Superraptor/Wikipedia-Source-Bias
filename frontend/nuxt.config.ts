export default defineNuxtConfig({
  ssr: false,
  devtools: { enabled: true },
  modules: ["@nuxtjs/i18n"],
  i18n: {
    // `no_prefix` keeps a single set of URLs. Flask serves this SPA from a
    // static directory (backend/app.py) and would need extra rewrite rules for
    // /en/** and /fr/**; the locale lives in a cookie instead.
    strategy: "no_prefix",
    defaultLocale: "fr",
    vueI18n: "./i18n.config.ts",
    locales: [
      { code: "fr", language: "fr-FR", dir: "ltr", name: "Français", file: "fr.json" },
      { code: "en", language: "en-US", dir: "ltr", name: "English", file: "en.json" },
    ],
    // With `ssr: false` there is no server to read Accept-Language, so
    // detection has to happen in the browser. `nuxt generate` sets
    // nitro.static, which makes the module load its `i18n:plugin:ssg-detect`
    // plugin: on `app:mounted` it reads the cookie first and falls back to
    // navigator.languages, then calls setLocale(). An explicit choice made
    // through the header switcher writes the same cookie, so it wins on every
    // later visit. `alwaysRedirect: false` is what makes the cookie win.
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: "wikibias_locale",
      cookieSecure: true,
      alwaysRedirect: false,
      fallbackLocale: "fr",
      redirectOn: "root",
    },
    bundle: {
      // Ship both catalogues in the bundle: no runtime request, which the
      // Toolforge Terms of Use (rule 7) require anyway.
      optimizeTranslationDirective: false,
    },
  },
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
      // `lang` and the description are locale-dependent and therefore set from
      // app.vue, which re-runs them whenever the active locale changes. Only
      // locale-independent tags belong here.
      meta: [
        { name: "viewport", content: "width=device-width, initial-scale=1" },
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
