/** Data boundary between the sync room and the FastAPI backend.
 *
 * The backend stays the owner of the durable canvas: the room loads the
 * snapshot over GET /canvas at boot and writes every change back with
 * PUT /canvas, debounced through the same save scheduler the browser
 * used to run. Nothing here knows about the sync protocol; nothing in
 * the room code performs I/O.
 */

import type { RoomSnapshot } from "@tldraw/sync-core";
import type { CanvasDocumentSnapshot } from "../src/calculations/canvasMigrations";

export interface CanvasBackend {
  load(): Promise<CanvasDocumentSnapshot | null>;
  save(snapshot: CanvasDocumentSnapshot): Promise<void>;
}

export function createHttpCanvasBackend(apiUrl: string): CanvasBackend {
  return {
    async load() {
      const response = await fetch(`${apiUrl}/canvas`);
      if (!response.ok) throw new Error(`GET /canvas failed: ${response.status}`);
      const body = (await response.json()) as { snapshot: CanvasDocumentSnapshot | null };
      return body.snapshot;
    },
    async save(snapshot) {
      const response = await fetch(`${apiUrl}/canvas`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ snapshot }),
      });
      if (!response.ok) throw new Error(`PUT /canvas failed: ${response.status}`);
    },
  };
}

/** The room speaks RoomSnapshot; the backend stores the same {store,
 * schema} document snapshot it always has, so reset-canvas, git history,
 * and the one-step backup keep working unchanged. */
export function roomSnapshotToDocument(snapshot: RoomSnapshot): CanvasDocumentSnapshot {
  const store: CanvasDocumentSnapshot["store"] = {};
  for (const { state } of snapshot.documents) {
    store[state.id] = state as unknown as CanvasDocumentSnapshot["store"][string];
  }
  return {
    store,
    schema: snapshot.schema as unknown as CanvasDocumentSnapshot["schema"],
  };
}

export async function loadWithRetry(
  backend: CanvasBackend,
  options: { attempts: number; delayMs: number },
): Promise<CanvasDocumentSnapshot | null> {
  let lastError: unknown;
  for (let attempt = 0; attempt < options.attempts; attempt++) {
    try {
      return await backend.load();
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, options.delayMs));
    }
  }
  throw lastError;
}
