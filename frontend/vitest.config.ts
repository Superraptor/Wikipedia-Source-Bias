import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  // plugin-vue and the `~` alias let component render tests run, not just the
  // data-shaping layer. Without them a .vue import fails to parse and the only
  // testable surface is plain .js.
  plugins: [vue()],
  resolve: {
    alias: {
      "~": fileURLToPath(new URL("./", import.meta.url)),
      "@": fileURLToPath(new URL("./", import.meta.url)),
    },
  },
  test: {
    environment: "happy-dom",
    setupFiles: ["./test/setup.js"],
  },
});
