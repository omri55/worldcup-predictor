import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Relative base so the build works under any GitHub Pages subpath
  // (e.g. https://user.github.io/worldcup-predictor/) without hardcoding it.
  base: "./",
  server: {
    port: 5173,
    host: true, // listen on all interfaces (LAN + tunnel access)
    allowedHosts: true, // accept the Cloudflare tunnel's *.trycloudflare.com host
    proxy: {
      // Forward API calls to the FastAPI backend (also works through the tunnel,
      // since the iPhone only ever talks to Vite, which proxies /api locally).
      "/api": "http://127.0.0.1:8000",
    },
  },
});
