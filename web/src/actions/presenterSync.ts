import type { Editor, TLShapeId } from "tldraw";
import {
  type CanvasDocView,
  type PresenterSyncState,
  resolvePresenterView,
  shouldApplyPresenterState,
} from "../calculations/presenterTarget";
import { createOrGetWorkspace, fetchPresenterState } from "../data/api";
import { pageIdForSlug } from "../lib/tldrawIds";
import { PRIMARY_WORKSPACE_PAGE_SLUG } from "./joinWorkshop";
import { navigateToWorkspace } from "./navigateToWorkspace";

export interface PresenterSyncOptions {
  editor: Editor;
  /** The presenter's own client must not have its camera driven remotely. */
  isPresenter: boolean;
  getCurrentUserId: () => string | null;
  onLockedChange: (locked: boolean) => void;
  /** Latest state on every poll, for surfacing mode to the UI. */
  onStateChange?: (state: PresenterSyncState) => void;
  /** Concise user-facing message when a target degrades (missing frame
   * or page). */
  onNotice?: (notice: string) => void;
  intervalMs?: number;
}

function docViewForEditor(editor: Editor): CanvasDocView {
  return {
    hasPage(pageSlug) {
      return editor.getPages().some((page) => page.id === pageIdForSlug(pageSlug));
    },
    frameBounds(frameId, pageSlug) {
      const shape = editor.getShape(frameId as TLShapeId);
      if (!shape) return null;
      if (editor.getAncestorPageId(shape) !== pageIdForSlug(pageSlug)) return null;
      const bounds = editor.getShapePageBounds(shape.id);
      return bounds ? { x: bounds.x, y: bounds.y, w: bounds.w, h: bounds.h } : null;
    },
  };
}

async function applyPresenterView(
  editor: Editor,
  state: PresenterSyncState,
  userId: string | null,
  onNotice?: (notice: string) => void,
): Promise<void> {
  const view = resolvePresenterView(state, docViewForEditor(editor));
  if (view.kind === "none") {
    if (view.notice) onNotice?.(view.notice);
    return;
  }
  if (view.kind === "workspace") {
    if (!userId) return;
    const workspace = await createOrGetWorkspace(userId, PRIMARY_WORKSPACE_PAGE_SLUG);
    navigateToWorkspace(editor, workspace, PRIMARY_WORKSPACE_PAGE_SLUG);
    return;
  }
  editor.setCurrentPage(pageIdForSlug(view.pageSlug));
  if (view.kind === "bounds") {
    editor.zoomToBounds(view.bounds as never, {
      inset: view.inset,
      animation: { duration: 250 },
    });
    return;
  }
  editor.zoomToFit({ animation: { duration: 250 } });
  if (view.notice) onNotice?.(view.notice);
}

/**
 * Polls presenter state so presenter actions reach every client, not
 * just the browser the button was clicked in.
 *
 * Ordering rests on the server's monotonic revision: the first
 * completed poll applies the current target (late joiners land where
 * the room is), afterwards only strictly newer revisions apply, so
 * repeated polls do nothing and a slow response cannot roll the camera
 * back. Polls are single-flight; a tick is skipped while the previous
 * apply is still running.
 */
export function startPresenterSync(options: PresenterSyncOptions): () => void {
  const { editor, isPresenter, getCurrentUserId, onLockedChange, onStateChange, onNotice } =
    options;
  let lastAppliedRevision: number | null = null;
  let stopped = false;
  let inFlight = false;

  async function tick(): Promise<void> {
    if (inFlight) return;
    inFlight = true;
    try {
      let state: PresenterSyncState;
      try {
        state = await fetchPresenterState();
      } catch {
        return; // backend blip; next tick retries
      }
      if (stopped) return;

      onStateChange?.(state);
      onLockedChange(state.locked);
      const shouldBeReadonly = state.locked && !isPresenter;
      if (editor.getIsReadonly() !== shouldBeReadonly) {
        editor.updateInstanceState({ isReadonly: shouldBeReadonly });
      }

      if (!shouldApplyPresenterState(state, lastAppliedRevision)) {
        lastAppliedRevision = Math.max(lastAppliedRevision ?? 0, state.revision);
        return;
      }
      if (isPresenter) {
        lastAppliedRevision = state.revision;
        return;
      }
      // The revision is consumed only after the view actually applied.
      // A transient failure (say, the workspace lookup during
      // send-to-workspace) leaves it unconsumed, so the next poll
      // retries the same target instead of leaving this client behind.
      try {
        await applyPresenterView(editor, state, getCurrentUserId(), onNotice);
        lastAppliedRevision = state.revision;
      } catch {
        // next tick retries this revision
      }
    } finally {
      inFlight = false;
    }
  }

  void tick();
  const timer = setInterval(() => void tick(), options.intervalMs ?? 3000);
  return () => {
    stopped = true;
    clearInterval(timer);
  };
}
