import { ref } from "vue";

/**
 * Recently analysed (and in-flight) articles, from the live queue.
 *
 * This list used to be four hardcoded entries with invented source counts.
 * Driving it from /api/status means it reflects what the tool has actually
 * done, and lets a visitor see work in progress rather than a static brochure.
 */
const STATUS_ORDER = { running: 0, pending: 1, done: 2, error: 3 };

export function useRecentArticles(limit = 20) {
  const items = ref([]);
  const loading = ref(false);
  const failed = ref(false);

  function langOf(url) {
    const m = (url || "").match(/^https?:\/\/([a-z0-9-]+)\.(?:m\.)?wikipedia\.org/i);
    return m ? m[1].toUpperCase() : "";
  }

  async function load() {
    loading.value = true;
    failed.value = false;
    try {
      const resp = await fetch("/api/status");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const payload = await resp.json();
      const rows = Array.isArray(payload.recent) ? payload.recent : [];
      items.value = rows
        .filter((r) => r.page_url)
        // In-flight first: seeing something running is the point of including it.
        .sort((a, b) => (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9))
        .slice(0, limit)
        .map((r) => ({
          title: r.display_title || r.page_url,
          url: r.page_url,
          lang: langOf(r.page_url),
          status: r.status,
          sourceCount: r.source_count,
          progressPct: r.progress_pct ?? null,
        }));
    } catch (e) {
      failed.value = true;
      items.value = [];
    } finally {
      loading.value = false;
    }
  }

  return { items, loading, failed, load };
}
