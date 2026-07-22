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
      title: "Wiki Source Bias Analyzer",
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
      link: [
        { rel: "preconnect", href: "https://fonts.googleapis.com" },
        { rel: "preconnect", href: "https://fonts.gstatic.com", crossorigin: "" },
        {
          rel: "stylesheet",
          href: "https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&family=Source+Code+Pro:wght@400;500&display=swap",
        },
      ],
    },
  },
  nitro: {
    routeRules: {
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
