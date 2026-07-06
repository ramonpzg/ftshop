import { useEffect, useState } from "react";
import type { Editor } from "tldraw";
import { navigateToWorkspace } from "../../actions/navigateToWorkspace";
import { pageIdForSlug } from "../../actions/seedTldrawDocument";
import {
  bringToPresenterView,
  createOrGetWorkspace,
  fetchPresenterState,
  lockEditing,
  type PresenterState,
  resetPage,
  sendToWorkspaces,
  unlockEditing,
} from "../../data/api";
import type { LocalUser } from "../../data/localUser";
import "./PresenterPanel.css";

const PRESENTER_HOME_PAGE_SLUG = "presentation";
const RESETTABLE_PAGE_SLUG = "chess-machine";

interface PresenterPanelProps {
  editor: Editor | null;
  currentUser: LocalUser | null;
  onLockedChange: (locked: boolean) => void;
  onPageReset: () => void;
}

export function PresenterPanel({
  editor,
  currentUser,
  onLockedChange,
  onPageReset,
}: PresenterPanelProps) {
  const [state, setState] = useState<PresenterState | null>(null);

  // biome-ignore lint/correctness/useExhaustiveDependencies: fetch once on mount; onLockedChange is a stable setter from App
  useEffect(() => {
    fetchPresenterState().then((s) => {
      setState(s);
      onLockedChange(s.locked);
    });
  }, []);

  async function handleBringToPresenterView() {
    const next = await bringToPresenterView(PRESENTER_HOME_PAGE_SLUG);
    setState(next);
    editor?.setCurrentPage(pageIdForSlug(PRESENTER_HOME_PAGE_SLUG));
  }

  async function handleSendToWorkspaces() {
    const next = await sendToWorkspaces();
    setState(next);
    if (editor && currentUser) {
      const workspace = await createOrGetWorkspace(currentUser.id, RESETTABLE_PAGE_SLUG);
      navigateToWorkspace(editor, workspace, RESETTABLE_PAGE_SLUG);
    }
  }

  async function handleToggleLock() {
    const next = state?.locked ? await unlockEditing() : await lockEditing();
    setState(next);
    onLockedChange(next.locked);
  }

  async function handleResetPage() {
    await resetPage(RESETTABLE_PAGE_SLUG);
    onPageReset();
  }

  return (
    <section className="presenter-panel" aria-label="Presenter controls">
      <h2>Presenter</h2>
      <button type="button" onClick={handleBringToPresenterView}>
        Bring everyone to presenter view
      </button>
      <button type="button" onClick={handleSendToWorkspaces}>
        Send users to their workspace
      </button>
      <button type="button" onClick={handleToggleLock}>
        {state?.locked ? "Unlock editing" : "Lock editing"}
      </button>
      <button type="button" onClick={handleResetPage}>
        Reset page
      </button>
    </section>
  );
}
