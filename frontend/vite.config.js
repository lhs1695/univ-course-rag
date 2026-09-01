import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      "/auth": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/admin": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/courses": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        bypass(req) {
          if (req.method === "GET" && String(req.headers.accept || "").includes("text/html")) {
            return "/index.html";
          }
        },
      },
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
