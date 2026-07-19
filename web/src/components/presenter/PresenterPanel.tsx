import {
  ArrowCounterClockwise,
  DownloadSimple,
  Lock,
  LockOpen,
  ProjectorScreen,
  UsersThree,
} from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import type { Editor } from "tldraw";
import { navigateToWorkspace } from "../../actions/navigateToWorkspace";
import { bringEveryoneHere } from "../../actions/presenterNavigation";
import {
  createOrGetWorkspace,
  type DatasetExport,
  exportFullTextDataset,
  exportTextDataset,
  fetchRoomGames,
  lockEditing,
  resetPage,
  type RoomGames,
  sendToWorkspaces,
  unlockEditing,
} from "../../data/api";
import type { LocalUser } from "../../data/localUser";
import { formatClock, shortResult } from "../../lib/gameClock";
import "./PresenterPanel.css";

const RESETTABLE_PAGE_SLUG = "chess-machine";

interface PresenterPanelProps {
  editor: Editor | null;
  currentUser: LocalUser | null;
  locked: boolean;
  onLockedChange: (locked: boolean) => void;
  /** Immediate mode feedback for this client; attendees learn the mode
   * through the poll loop instead. */
  onModeChange?: (mode: string) => void;
  onPageReset: () => void;
}

const ROOM_POLL_MS = 3000;

export function PresenterPanel({
  editor,
  currentUser,
  locked,
  onLockedChange,
  onModeChange,
  onPageReset,
}: PresenterPanelProps) {
  const [room, setRoom] = useState<RoomGames | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      fetchRoomGames()
        .then((games) => {
          if (!cancelled) setRoom(games);
        })
        .catch(() => {});
    };
    load();
    const poll = setInterval(load, ROOM_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(poll);
    };
  }, []);

  async function handleDownload(run: () => Promise<DatasetExport>) {
    setExporting(true);
    try {
      const result = await run();
      window.open(`/api${result.url}`, "_blank");
    } finally {
      setExporting(false);
    }
  }
  async function handleBringToPresenterView() {
    // Attendees get pulled to the page and camera region the presenter
    // is actually looking at, not just a whole-page fit.
    if (!editor) return;
    const state = await bringEveryoneHere(editor);
    onModeChange?.(state.mode);
  }

  async function handleSendToWorkspaces() {
    const state = await sendToWorkspaces();
    onModeChange?.(state.mode);
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
      <h2 className="presenter-panel-subhead">Games</h2>
      {room === null ? (
        <p className="presenter-room-empty">Loading the room.</p>
      ) : room.games.length === 0 ? (
        <p className="presenter-room-empty">No games yet.</p>
      ) : (
        <>
          <p className="presenter-room-totals" data-testid="room-totals">
            {room.playing} playing, {room.finished} finished, {room.total_dataset_rows} samples
          </p>
          <ul className="presenter-room-games" data-testid="room-games">
            {room.games.map((game) => (
              <li key={game.id} data-status={shortResult(game.result)}>
                <span className="presenter-room-name">{game.user_name}</span>
                <span className="presenter-room-status">
                  {game.result === null
                    ? formatClock(game.seconds_left ?? 0)
                    : shortResult(game.result)}
                </span>
                <span className="presenter-room-moves">{game.legal_moves} mv</span>
              </li>
            ))}
          </ul>
        </>
      )}
      <button
        type="button"
        onClick={() => handleDownload(exportTextDataset)}
        disabled={exporting}
        title="Every game's prompt/completion pairs as chess_sft.jsonl. What the training snippets load."
        data-testid="download-sft"
      >
        <DownloadSimple size={13} /> Download SFT dataset
      </button>
      <button
        type="button"
        onClick={() => handleDownload(exportFullTextDataset)}
        disabled={exporting}
        title="The full archive: every sample from every game, all six shapes, with workspace provenance. Take this to the GPU."
        data-testid="download-full"
      >
        <DownloadSimple size={13} /> Download all shapes
      </button>
    </section>
  );
}
