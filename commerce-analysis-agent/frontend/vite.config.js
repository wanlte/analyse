import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      "/health": "http://127.0.0.1:8000",
      "/auth": "http://127.0.0.1:8000",
      "/me": "http://127.0.0.1:8000",
      "/datasets": "http://127.0.0.1:8000",
      "/resource-packs": "http://127.0.0.1:8000",
      "/analyses": "http://127.0.0.1:8000",
      "/boards": "http://127.0.0.1:8000",
      "/home": "http://127.0.0.1:8000",
      "/avatars": "http://127.0.0.1:8000",
    },
  },
});
