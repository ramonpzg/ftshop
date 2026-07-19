/** Orchestration for the workshop's single sync room: load, migrate,
 * open, persist. I/O goes through the CanvasBackend boundary; document
 * repair goes through the pure migration pipeline. */

import type { TLRecord, TLStoreSnapshot } from "@tldraw/tlschema";
import { TLSocketRoom } from "@tldraw/sync-core";
import { createSaveScheduler, type SaveStatus } from "../src/actions/canvasSaveScheduler";
import { migrateCanvasDocument } from "../src/calculations/canvasMigrations";
import type { CanvasBackend } from "./persistence";
import { loadWithRetry, roomSnapshotToDocument } from "./persistence";
import { createRoomSchema, runtimeSchemaSequences, upgradeAndValidateDocument } from "./schema";

export interface WorkshopRoom {
  room: TLSocketRoom<TLRecord>;
  persistStatus(): SaveStatus;
  /** Resolves true when the document is fully persisted; false when
   * unsaved changes remain after a failed save. */
  flush(): Promise<boolean>;
  appliedMigrations: string[];
}

export async function openWorkshopRoom(backend: CanvasBackend): Promise<WorkshopRoom> {
  // The backend may still be starting; a failed load after the retries
  // aborts the boot rather than opening a room on a blank document that
  // would later overwrite the real one.
  const stored = await loadWithRetry(backend, { attempts: 30, delayMs: 1000 });

  // A thrown migration also aborts the boot. The stored snapshot has not
  // been written to, so the last valid document survives untouched.
  const { snapshot, applied, changed } = migrateCanvasDocument(stored, runtimeSchemaSequences());

  // The last gate: tldraw's own migrator plus full record validation.
  // The workshop migrations check types and structure; only the real
  // validators can catch a malformed record of a known type, and a
  // document that fails them must never reach connecting clients.
  const schema = createRoomSchema();
  const document = upgradeAndValidateDocument(snapshot, schema);

  let scheduler: ReturnType<typeof createSaveScheduler> | null = null;
  const room = new TLSocketRoom({
    schema,
    initialSnapshot: {
      store: document.store,
      schema: document.schema,
    } as unknown as TLStoreSnapshot,
    onDataChange() {
      scheduler?.markDirty();
    },
    log: {
      warn: (...args: unknown[]) => console.warn("[sync]", ...args),
      error: (...args: unknown[]) => console.error("[sync]", ...args),
    },
  });

  scheduler = createSaveScheduler({
    getSnapshot: () =>
      roomSnapshotToDocument(room.getCurrentSnapshot()) as unknown as Record<string, unknown>,
    save: (document) => backend.save(document as never),
    debounceMs: 1000,
    retryMs: 3000,
  });

  if (changed || document.upgraded) {
    // Persist right away whenever migration altered anything: named
    // steps, a schema down-conversion, or tldraw's own up-migration of
    // older sequences. The file on disk must be valid for this runtime
    // even if no one ever draws. The backend answered the load moments
    // ago; if this write fails, opening the room anyway would run it
    // on a document the disk cannot represent.
    scheduler.markDirty();
    if (!(await scheduler.flush())) {
      throw new Error("could not persist the migrated canvas; refusing to open the room");
    }
  }

  return {
    room,
    persistStatus: () => scheduler.status(),
    flush: () => scheduler.flush(),
    appliedMigrations: applied,
  };
}
