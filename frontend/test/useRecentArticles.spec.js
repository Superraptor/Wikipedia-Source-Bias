import { describe, it, expect, vi, beforeEach } from "vitest";
import { useRecentArticles } from "../composables/useRecentArticles.js";

function mockStatus(recent) {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true, status: 200, json: () => Promise.resolve({ recent }),
  });
}

beforeEach(() => { global.fetch = vi.fn(); });

describe("useRecentArticles", () => {
  it("puts in-flight articles first", async () => {
    mockStatus([
      { page_url: "https://fr.wikipedia.org/wiki/A", display_title: "A", status: "done" },
      { page_url: "https://en.wikipedia.org/wiki/B", display_title: "B", status: "running" },
      { page_url: "https://de.wikipedia.org/wiki/C", display_title: "C", status: "pending" },
    ]);
    const { items, load } = useRecentArticles();
    await load();
    expect(items.value.map((i) => i.status)).toEqual(["running", "pending", "done"]);
  });

  it("derives the language from the wikipedia host", async () => {
    mockStatus([{ page_url: "https://de.wikipedia.org/wiki/Berlin", display_title: "Berlin", status: "done" }]);
    const { items, load } = useRecentArticles();
    await load();
    expect(items.value[0].lang).toBe("DE");
  });

  it("honours the limit", async () => {
    mockStatus(Array.from({ length: 40 }, (_, i) => ({
      page_url: `https://fr.wikipedia.org/wiki/A${i}`, display_title: `A${i}`, status: "done",
    })));
    const { items, load } = useRecentArticles(20);
    await load();
    expect(items.value).toHaveLength(20);
  });

  it("drops rows without a url", async () => {
    mockStatus([{ display_title: "ghost", status: "done" }]);
    const { items, load } = useRecentArticles();
    await load();
    expect(items.value).toHaveLength(0);
  });

  it("flags failure instead of throwing", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("offline"));
    const { items, failed, load } = useRecentArticles();
    await load();
    expect(failed.value).toBe(true);
    expect(items.value).toEqual([]);
  });
});
