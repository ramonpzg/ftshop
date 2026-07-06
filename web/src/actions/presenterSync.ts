import type { Editor } from "tldraw";
import { createOrGetWorkspace, fetchPresenterState, type PresenterState } from "../data/api";
import { PRIMARY_WORKSPACE_PAGE_SLUG } from "./joinWorkshop";
import { navigateToWorkspace } from "./navigateToWorkspace";
import { pageIdForSlug } from "./seedTldrawDocument";

export interface PresenterSyncOptions {
  editor: Editor;
  /** The presenter's own client must not have its camera driven remotely. */
  isPresenter: boolean;
  getCurrentUserId: () => string | null;
  onLockedChange: (locked: boolean) => void;
  intervalMs?: number;
}

async function applyPresenterMode(
  editor: Editor,
  state: PresenterState,
  userId: string | null,
): Promise<void> {
  if (state.mode === "presenter" && state.active_page_slug) {
    editor.setCurrentPage(pageIdForSlug(state.active_page_slug));
    editor.zoomToFit({ animation: { duration: 250 } });
    return;
  }
  if (state.mode === "workspaces" && userId) {
    const workspace = await createOrGetWorkspace(userId, PRIMARY_WORKSPACE_PAGE_SLUG);
    navigateToWorkspace(editor, workspace, PRIMARY_WORKSPACE_PAGE_SLUG);
  }
}

/**
 * Polls presenter state so presenter actions reach every client, not just
 * the browser the button was clicked in. Lock applies immediately (tldraw
 * read-only for attendees); camera moves apply only when the state
 * actually changed, so clients aren't yanked around on every poll.
 * Returns a stop function.
 */
export function startPresenterSync(options: PresenterSyncOptions): () => void {
  const { editor, isPresenter, getCurrentUserId, onLockedChange } = options;
  let lastUpdatedAt: string | null = null;
  let stopped = false;

  async function tick(): Promise<void> {
    let state: PresenterState;
    try {
      state = await fetchPresenterState();
    } catch {
      return; // backend blip; next tick retries
    }
    if (stopped) return;

    onLockedChange(state.locked);
    const shouldBeReadonly = state.locked && !isPresenter;
    if (editor.getIsReadonly() !== shouldBeReadonly) {
      editor.updateInstanceState({ isReadonly: shouldBeReadonly });
    }

    const changed = lastUpdatedAt !== null && state.updated_at !== lastUpdatedAt;
    lastUpdatedAt = state.updated_at;
    if (changed && !isPresenter) {
      await applyPresenterMode(editor, state, getCurrentUserId());
    }
  }

  void tick();
  const timer = setInterval(() => void tick(), options.intervalMs ?? 3000);
  return () => {
    stopped = true;
    clearInterval(timer);
  };
}
