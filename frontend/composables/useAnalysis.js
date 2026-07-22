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

  // `error` holds text that comes from the network/backend and is shown as-is.
  // `errorKey` holds an i18n key for failures this composable decides itself;
  // the composable has no access to `t`, so the view translates it.
  const state = ref({
    status: "idle",
    data: null,
    error: null,
    errorKey: null,
  });

  function settle(payload) {
    const count = payload.source_count ?? (payload.sources?.length ?? 0);
    state.value = {
      status: count === 0 ? "empty" : "loaded",
      data: payload,
      error: null,
      errorKey: null,
    };
  }

  async function load(url) {
    state.value = { status: "loading", data: null, error: null, errorKey: null };
    const deadline = Date.now() + pollTimeoutMs;

    try {
      while (true) {
        const resp = await fetch(`/api/analyze?url=${encodeURIComponent(url)}`);
        const payload = await resp.json();

        if (!resp.ok) {
          // A coded error gets a translated sentence; anything else falls back
          // to whatever the backend said.
          const errorKey =
            payload.code === "article_not_found"
              ? "states.errorArticleNotFound"
              : null;
          state.value = {
            status: "error",
            data: null,
            error: errorKey ? null : payload.error || `HTTP ${resp.status}`,
            errorKey,
          };
          return;
        }

        // 202 is `ok`, so this must be checked before the success path.
        if (resp.status === 202) {
          if (Date.now() >= deadline) {
            state.value = {
              status: "error",
              data: null,
              error: null,
              errorKey: "states.errorTimeout",
            };
            return;
          }
          // Carry the queue detail through so the UI can show progress and say
          // whether the worker is alive; a bare "pending" left users unable to
          // tell a long analysis from a dead one.
          state.value = {
            status: "pending",
            data: null,
            error: null,
            errorKey: null,
            progress: {
              done: payload.progress_done ?? null,
              total: payload.progress_total ?? null,
              pct: payload.progress_pct ?? null,
              eta: payload.eta ?? null,
              health: payload.health ?? null,
              quietFor: payload.quiet_for ?? null,
              queuePosition: payload.queue_position ?? null,
              queueState: payload.queue_state ?? null,
            },
          };
          await sleep(pollIntervalMs);
          continue;
        }

        settle(payload);
        return;
      }
    } catch (e) {
      state.value = { status: "error", data: null, error: String(e), errorKey: null };
    }
  }

  function reset() {
    state.value = { status: "idle", data: null, error: null, errorKey: null };
  }

  return { state, load, reset };
}
