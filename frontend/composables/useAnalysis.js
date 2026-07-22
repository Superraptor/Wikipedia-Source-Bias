import { ref } from "vue";

// The backend queues analyses and answers 202 until a worker finishes, because
// a full scrape runs for minutes -- far longer than a request may live on
// Toolforge. See backend/worker.py.
const POLL_INTERVAL_MS = 3000;
const POLL_TIMEOUT_MS = 10 * 60 * 1000;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export function useAnalysis(options = {}) {
  const pollIntervalMs = options.pollIntervalMs ?? POLL_INTERVAL_MS;
  const pollTimeoutMs = options.pollTimeoutMs ?? POLL_TIMEOUT_MS;

  const state = ref({
    status: "idle",
    data: null,
    error: null,
  });

  function settle(payload) {
    const count = payload.source_count ?? (payload.sources?.length ?? 0);
    state.value = {
      status: count === 0 ? "empty" : "loaded",
      data: payload,
      error: null,
    };
  }

  async function load(url) {
    state.value = { status: "loading", data: null, error: null };
    const deadline = Date.now() + pollTimeoutMs;

    try {
      while (true) {
        const resp = await fetch(`/api/analyze?url=${encodeURIComponent(url)}`);
        const payload = await resp.json();

        if (!resp.ok) {
          state.value = {
            status: "error",
            data: null,
            error: payload.error || `HTTP ${resp.status}`,
          };
          return;
        }

        // 202 is `ok`, so this must be checked before the success path.
        if (resp.status === 202) {
          if (Date.now() >= deadline) {
            state.value = {
              status: "error",
              data: null,
              error: "L'analyse a expiré. Réessayez dans quelques minutes.",
            };
            return;
          }
          state.value = { status: "pending", data: null, error: null };
          await sleep(pollIntervalMs);
          continue;
        }

        settle(payload);
        return;
      }
    } catch (e) {
      state.value = { status: "error", data: null, error: String(e) };
    }
  }

  function reset() {
    state.value = { status: "idle", data: null, error: null };
  }

  return { state, load, reset };
}
