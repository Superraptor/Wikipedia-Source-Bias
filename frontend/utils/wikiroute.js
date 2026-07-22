/**
 * Canonical in-app routes for Wikipedia articles.
 *
 * The old form was `/article/Brexit?src=https%3A%2F%2Fen.wikipedia.org%2F...`
 * -- the whole source URL percent-encoded into a query string, which is ugly,
 * unshareable and duplicates information already in the path. Wikipedia's own
 * shape is `<lang>.wikipedia.org/wiki/<Title>`, so mirror it:
 *
 *     /wikipedia/en/Brexit
 *
 * Non-Wikipedia or otherwise unparseable URLs keep the ?src= form, because
 * there is no lang/title to put in the path.
 */

const WIKI_HOST = /^([a-z][a-z0-9-]*)\.(?:m\.)?wikipedia\.org$/i;

/** Parse a Wikipedia article URL into {lang, title}, or null. */
export function parseWikipediaUrl(url) {
  if (!url || typeof url !== "string") return null;
  let u;
  try {
    u = new URL(url);
  } catch {
    return null;
  }
  const host = u.hostname.match(WIKI_HOST);
  if (!host) return null;
  const m = u.pathname.match(/^\/wiki\/(.+)$/);
  if (!m) return null;
  let title;
  try {
    title = decodeURIComponent(m[1]);
  } catch {
    title = m[1];
  }
  if (!title) return null;
  return { lang: host[1].toLowerCase(), title };
}

/** Rebuild the canonical Wikipedia URL. Query strings are dropped. */
export function wikipediaUrl(lang, title) {
  return `https://${lang}.wikipedia.org/wiki/${encodeURIComponent(title)}`;
}

/** The in-app route for a source URL. */
export function routeForUrl(url, version = DEFAULT_VERSION) {
  const parsed = parseWikipediaUrl(url);
  if (parsed) return routeFor(parsed.lang, parsed.title, version);
  const title = (url || "").split("/").pop() || "article";
  return `/article/${encodeURIComponent(title)}?src=${encodeURIComponent(url)}`;
}

// Default dashboard version for generated links.
export const DEFAULT_VERSION = "v1";

export function routeFor(lang, title, version = DEFAULT_VERSION) {
  return `/${version}/wikipedia/${lang}/${encodeURIComponent(title)}`;
}
