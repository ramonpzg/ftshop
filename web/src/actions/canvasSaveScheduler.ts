import type { CanvasSnapshot } from "../data/api";

export type SaveStatus = "idle" | "saving" | "saved" | "error";

export interface CanvasSaveScheduler {
  /** Call whenever the document changed. Debounces the actual save. */
  markDirty(): void;
  /** Save now if dirty, and wait for any in-flight save. For unload handlers. */
  flush(): Promise<void>;
  status(): SaveStatus;
  dispose(): void;
}

interface SchedulerOptions {
  getSnapshot: () => CanvasSnapshot;
  save: (snapshot: CanvasSnapshot) => Promise<unknown>;
  /** Quiet period after the last change before saving. */
  debounceMs?: number;
  /** How long to wait before retrying a failed save. */
  retryMs?: number;
  onStatusChange?: (status: SaveStatus) => void;
}

/**
 * Debounced, coalescing persistence loop for the canvas document.
 *
 * Rules: one save in flight at a time; changes during a save trigger one
 * follow-up save; a failed save keeps the document dirty and retries on a
 * timer, so a backend hiccup never silently drops the presenter's edits.
 */
export function createSaveScheduler(options: SchedulerOptions): CanvasSaveScheduler {
  const debounceMs = options.debounceMs ?? 800;
  const retryMs = options.retryMs ?? 3000;

  let dirty = false;
  let disposed = false;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let inFlight: Promise<void> | null = null;
  let currentStatus: SaveStatus = "idle";

  function setStatus(next: SaveStatus) {
    if (currentStatus === next) return;
    currentStatus = next;
    options.onStatusChange?.(next);
  }

  function clearTimer() {
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
  }

  function schedule(delay: number) {
    clearTimer();
    timer = setTimeout(() => {
      timer = null;
      void runSave();
    }, delay);
  }

  async function runSave(): Promise<void> {
    if (disposed || !dirty) return;
    if (inFlight) return;
    dirty = false;
    setStatus("saving");
    inFlight = options
      .save(options.getSnapshot())
      .then(() => {
        if (!dirty) setStatus("saved");
      })
      .catch(() => {
        dirty = true;
        setStatus("error");
        if (!disposed) schedule(retryMs);
      })
      .finally(() => {
        inFlight = null;
        if (dirty && !disposed && timer === null) schedule(debounceMs);
      });
    await inFlight;
  }

  return {
    markDirty() {
      if (disposed) return;
      dirty = true;
      schedule(debounceMs);
    },
    async flush() {
      clearTimer();
      if (inFlight) await inFlight;
      while (dirty && !disposed) {
        await runSave();
        if (inFlight) await inFlight;
        if (currentStatus === "error") break;
      }
    },
    status() {
      return currentStatus;
    },
    dispose() {
      disposed = true;
      clearTimer();
    },
  };
}
