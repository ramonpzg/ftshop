import { defineConfig } from "vite";

// Slidev merges this into its own Vite config. Two jobs:
// - host: true binds the LAN so an attendee can open the deck from the
//   presenter's machine.
// - /api proxies to the FastAPI backend, so LiveRoom talks to its own
//   origin and never trips CORS from port 3030.
export default defineConfig({
  server: {
    host: true,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        // Same forwarding rule as the board's proxy: overwrite any
        // client-supplied X-Forwarded-For with the peer address, so the
        // backend's presenter-machine check cannot be spoofed through
        // this origin either.
        xfwd: true,
        configure: (proxy) => {
          proxy.on("proxyReq", (proxyReq, req) => {
            proxyReq.setHeader("x-forwarded-for", req.socket.remoteAddress ?? "");
          });
        },
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
