import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The proxy targets follow the same env vars the backend and sync
// server read, so an isolated stack (the e2e durability project runs
// one on its own ports) can stand up a matching dev server. Defaults
// are the documented workshop ports.
const apiTarget = `http://localhost:${process.env.CHESS_STUDIO_API_PORT ?? "8000"}`;
const syncTarget = `http://localhost:${process.env.CHESS_STUDIO_SYNC_PORT ?? "8010"}`;

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    // Uses ?url asset imports that the dependency prebundler cannot
    // process; Vite handles them fine outside of it.
    exclude: ["@tldraw/assets"],
  },
  server: {
    // Bind all interfaces so attendees on the venue network can reach the
    // presenter's machine. The backend and the sync room stay on
    // localhost; everything goes through this dev server's proxies, so
    // every client talks to one origin.
    host: true,
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
        // The backend distinguishes the presenter's machine from LAN
        // attendees for paid generation; xfwd forwards the real client.
        xfwd: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/sync": {
        target: syncTarget,
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
