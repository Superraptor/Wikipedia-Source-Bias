import { ref } from "vue";

export function useAnalysis() {
  const state = ref({
    status: "idle",
    data: null,
    error: null,
  });

  async function load(url) {
    state.value = { status: "loading", data: null, error: null };
    try {
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
      const count = payload.source_count ?? (payload.sources?.length ?? 0);
      if (count === 0) {
        state.value = { status: "empty", data: payload, error: null };
      } else {
        state.value = { status: "loaded", data: payload, error: null };
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
