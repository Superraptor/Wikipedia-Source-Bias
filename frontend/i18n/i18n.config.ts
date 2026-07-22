export default defineI18nConfig(() => ({
  legacy: false,
  // French is the reference catalogue: a key missing from en.json renders the
  // French sentence rather than the raw key.
  fallbackLocale: "fr",
  // Warnings are noise in production but useful while translating.
  missingWarn: process.env.NODE_ENV !== "production",
  fallbackWarn: process.env.NODE_ENV !== "production",
}));
