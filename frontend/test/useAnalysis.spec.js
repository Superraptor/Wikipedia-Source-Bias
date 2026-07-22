import { describe, it, expect, vi, beforeEach } from "vitest";
import { useAnalysis } from "../composables/useAnalysis.js";

function mockFetchOk(payload) {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve(payload),
  });
}

function mockFetch404() {
  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status: 404,
    json: () => Promise.resolve({ error: "not found" }),
  });
}

beforeEach(() => {
  global.fetch = vi.fn();
});

describe("useAnalysis", () => {
  it("starts idle", () => {
    const { state } = useAnalysis();
    expect(state.value.status).toBe("idle");
    expect(state.value.data).toBeNull();
    expect(state.value.error).toBeNull();
  });

  it("transitions to loaded on successful fetch", async () => {
    mockFetchOk({ page_title: "X", source_count: 5, sources: [{}], aggregated_bias: {} });
    const { state, load } = useAnalysis();
    await load("https://fr.wikipedia.org/wiki/X");
    expect(state.value.status).toBe("loaded");
    expect(state.value.data.source_count).toBe(5);
  });

  it("transitions to empty when 0 sources", async () => {
    mockFetchOk({ page_title: "X", source_count: 0, sources: [], aggregated_bias: {} });
    const { state, load } = useAnalysis();
    await load("https://fr.wikipedia.org/wiki/X");
    expect(state.value.status).toBe("empty");
  });

  it("transitions to error on non-2xx", async () => {
    mockFetch404();
    const { state, load } = useAnalysis();
    await load("https://fr.wikipedia.org/wiki/X");
    expect(state.value.status).toBe("error");
    expect(state.value.error).toBeTruthy();
  });

  // The backend queues work and answers 202 until a worker finishes; 202 is
  // `ok`, so it must not be mistaken for a completed result.
  it("polls while the backend reports 202 pending, then loads", async () => {
    const pending = {
      ok: true,
      status: 202,
      json: () => Promise.resolve({ status: "pending" }),
    };
    const done = {
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({ page_title: "X", source_count: 3, sources: [{}], aggregated_bias: {} }),
    };
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce(pending)
      .mockResolvedValueOnce(pending)
      .mockResolvedValueOnce(done);

    const { state, load } = useAnalysis({ pollIntervalMs: 0 });
    await load("https://fr.wikipedia.org/wiki/X");

    expect(global.fetch).toHaveBeenCalledTimes(3);
    expect(state.value.status).toBe("loaded");
    expect(state.value.data.source_count).toBe(3);
  });

  it("does not treat a 202 body as a zero-source result", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: () => Promise.resolve({ status: "pending" }),
    });
    const { state, load } = useAnalysis({ pollIntervalMs: 0, pollTimeoutMs: 0 });
    await load("https://fr.wikipedia.org/wiki/X");
    // Would have been a misleading "empty" dashboard before 202 was handled.
    expect(state.value.status).toBe("error");
  });

  it("encodes the url query parameter", async () => {
    mockFetchOk({ page_title: "X", source_count: 1, sources: [{}], aggregated_bias: {} });
    const { load } = useAnalysis();
    await load("https://fr.wikipedia.org/wiki/Emmanuel_Macron");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining(encodeURIComponent("https://fr.wikipedia.org/wiki/Emmanuel_Macron")),
    );
  });
});
