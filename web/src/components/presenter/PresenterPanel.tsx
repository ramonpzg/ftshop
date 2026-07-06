import {
  ArrowCounterClockwise,
  Lock,
  LockOpen,
  ProjectorScreen,
  UsersThree,
} from "@phosphor-icons/react";
import type { Editor } from "tldraw";
import { navigateToWorkspace } from "../../actions/navigateToWorkspace";
import { pageIdForSlug } from "../../actions/seedTldrawDocument";
import {
  bringToPresenterView,
  createOrGetWorkspace,
  lockEditing,
  resetPage,
  sendToWorkspaces,
  unlockEditing,
} from "../../data/api";
import type { LocalUser } from "../../data/localUser";
import { PAGES } from "../../lib/pages";
import "./PresenterPanel.css";

const RESETTABLE_PAGE_SLUG = "chess-machine";

function currentWorkshopPageSlug(editor: Editor | null): string {
  if (!editor) return PAGES[0].slug;
  const currentId = editor.getCurrentPageId();
  const page = PAGES.find((p) => pageIdForSlug(p.slug) === currentId);
  return page?.slug ?? PAGES[0].slug;
}

interface PresenterPanelProps {
  editor: Editor | null;
  currentUser: LocalUser | null;
  locked: boolean;
  onLockedChange: (locked: boolean) => void;
  onPageReset: () => void;
}

export function PresenterPanel({
  editor,
  currentUser,
  locked,
  onLockedChange,
  onPageReset,
}: PresenterPanelProps) {
  async function handleBringToPresenterView() {
    // Attendees get pulled to the page the presenter is actually on.
    const slug = currentWorkshopPageSlug(editor);
    await bringToPresenterView(slug);
    editor?.setCurrentPage(pageIdForSlug(slug));
  }

  async function handleSendToWorkspaces() {
    await sendToWorkspaces();
    if (editor && currentUser) {
      const workspace = await createOrGetWorkspace(currentUser.id, RESETTABLE_PAGE_SLUG);
      navigateToWorkspace(editor, workspace, RESETTABLE_PAGE_SLUG);
    }
  }

  async function handleToggleLock() {
    const next = locked ? await unlockEditing() : await lockEditing();
    onLockedChange(next.locked);
  }

  async function handleResetPage() {
    const confirmed = window.confirm("Reset every attendee's game on the chess page?");
    if (!confirmed) return;
    await resetPage(RESETTABLE_PAGE_SLUG);
    onPageReset();
  }

  return (
    <section className="presenter-panel" aria-label="Presenter controls">
      <h2>Presenter</h2>
      <button type="button" onClick={handleBringToPresenterView}>
        <ProjectorScreen size={13} /> Bring everyone to presenter view
      </button>
      <button type="button" onClick={handleSendToWorkspaces}>
        <UsersThree size={13} /> Send users to their workspace
      </button>
      <button type="button" onClick={handleToggleLock}>
        {locked ? <LockOpen size={13} /> : <Lock size={13} />}
        {locked ? " Unlock editing" : " Lock editing"}
      </button>
      <button type="button" onClick={handleResetPage}>
        <ArrowCounterClockwise size={13} /> Reset page
      </button>
    </section>
  );
}
