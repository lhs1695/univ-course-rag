import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      "/auth": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/admin": {
        target: "http://127.0.0.1:8000", changeOrigin: true,
        bypass(req) {
          if (req.method === "GET" && String(req.headers.accept || "").includes("text/html")) {
            return "/index.html";
          }
        },
      },
      "/courses": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        bypass(req) {
          const pathname = String(req.url || "").split("?", 1)[0];
          const isDocumentContent = /^\/courses\/[^/]+\/documents\/[^/]+\/content$/.test(pathname);
          if (req.method === "GET" && isDocumentContent) {
            return undefined;
          }
          if (req.method === "GET" && String(req.headers.accept || "").includes("text/html")) {
            return "/index.html";
          }
        },
      },
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/ready": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/runtime": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
