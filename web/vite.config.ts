import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

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
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/sync": {
        target: "http://localhost:8010",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
