import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command }) => ({
  plugins: [react()],
  // Absolute base for the GitHub Pages build so every asset + data.json + the
  // service worker resolve to the correct path even inside a standalone iOS PWA
  // (a relative "./" base breaks there when the URL has no trailing slash).
  base: command === "build" ? "/worldcup-predictor/" : "/",
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
}));
