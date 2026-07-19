/** The workshop's canvas sync server. One Bun process, one room.
 *
 * Clients connect over WebSocket (proxied through the Vite dev server at
 * /sync, so attendees on the venue LAN reach it through the same origin
 * as the app). The room is tldraw's own TLSocketRoom: per-record
 * conflict resolution, reconnect handling, and presence come from
 * @tldraw/sync-core, not from anything invented here.
 *
 * Durable state still belongs to the FastAPI backend: the snapshot loads
 * from GET /canvas at boot, migrates, and persists back through
 * PUT /canvas on every change, debounced. If the backend is unreachable
 * at boot, or a migration fails, the process exits nonzero and the
 * stored snapshot is left exactly as it was.
 *
 * Sessions that identify a joined userId, or the presenter flag, get a
 * writable connection; anonymous watchers are read-only at the socket.
 * Fine-grained ownership (who may edit which shape) is enforced in every
 * client via store side effects; there is no authentication in v0, and
 * that boundary is documented rather than pretended away.
 */

import { openWorkshopRoom } from "./room";
import { createHttpCanvasBackend } from "./persistence";

const PORT = Number(process.env.CHESS_STUDIO_SYNC_PORT ?? 8010);
const API_URL = process.env.CHESS_STUDIO_API_URL ?? "http://127.0.0.1:8000";

interface SessionData {
  sessionId: string;
  isReadonly: boolean;
}

const backend = createHttpCanvasBackend(API_URL);

const workshop = await openWorkshopRoom(backend).catch((error: unknown) => {
  console.error("[sync] failed to open the room; the stored snapshot was not touched:", error);
  return process.exit(1);
});
if (workshop.appliedMigrations.length > 0) {
  console.log("[sync] canvas migrations applied:", workshop.appliedMigrations.join(", "));
}

const server = Bun.serve<SessionData>({
  port: PORT,
  fetch(request, srv) {
    const url = new URL(request.url);
    if (url.pathname === "/sync/health" || url.pathname === "/health") {
      return Response.json({
        status: "ok",
        persist: workshop.persistStatus(),
        sessions: workshop.room.getNumActiveSessions(),
      });
    }
    if (url.pathname === "/sync") {
      const sessionId = url.searchParams.get("sessionId");
      if (!sessionId) return new Response("missing sessionId", { status: 400 });
      const userId = url.searchParams.get("userId");
      const isPresenter = url.searchParams.get("presenter") === "1";
      const upgraded = srv.upgrade(request, {
        data: { sessionId, isReadonly: !isPresenter && !userId },
      });
      return upgraded ? undefined : new Response("websocket upgrade failed", { status: 400 });
    }
    return new Response("not found", { status: 404 });
  },
  websocket: {
    open(ws) {
      workshop.room.handleSocketConnect({
        sessionId: ws.data.sessionId,
        socket: ws,
        isReadonly: ws.data.isReadonly,
      });
    },
    message(ws, message) {
      workshop.room.handleSocketMessage(ws.data.sessionId, message);
    },
    close(ws) {
      workshop.room.handleSocketClose(ws.data.sessionId);
    },
  },
});

console.log(`[sync] room open on :${server.port}, persisting to ${API_URL}`);

async function shutdown() {
  // A failed final write is data loss, not a detail: retry briefly, and
  // if dirty state remains, say so loudly and exit nonzero so nothing
  // upstream mistakes this for a clean stop.
  for (let attempt = 0; attempt < 3; attempt++) {
    if (await workshop.flush()) {
      process.exit(0);
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  console.error(
    "[sync] shutdown with UNSAVED canvas changes: the backend refused the final write.",
    "The on-disk snapshot is stale. Restart the backend and the sync server before trusting it.",
  );
  process.exit(1);
}
process.on("SIGINT", () => void shutdown());
process.on("SIGTERM", () => void shutdown());
