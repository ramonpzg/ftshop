import { ArrowSquareOut } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { usePresenterState } from "../../lib/presenterContext";
import "./NotebookPanel.css";

interface NotebookPanelProps {
  pageSlug: string;
  isEditing: boolean;
}

type NotebookSource = "wasm" | "live";

const LIVE_URL_KEY = "euro-chess-studio:live-notebook-url";
const DEFAULT_LIVE_URL = "http://localhost:2718";

function wasmUrl(pageSlug: string): string {
  return `/notebooks/${pageSlug}/index.html`;
}

/**
 * The page's marimo notebook. Attendees get the WASM export running in
 * their own browser; the presenter can flip to a live marimo server for
 * real hardware, or pop either out to a tab if the canvas feels tight.
 */
export function NotebookPanel({ pageSlug, isEditing }: NotebookPanelProps) {
  const { isPresenter } = usePresenterState();
  const [source, setSource] = useState<NotebookSource>("wasm");
  const [liveUrl, setLiveUrl] = useState(
    () => localStorage.getItem(LIVE_URL_KEY) ?? DEFAULT_LIVE_URL,
  );
  const [wasmBuilt, setWasmBuilt] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    // The dev server answers unknown paths with the SPA shell (also 200,
    // also text/html), so a plain iframe would show the app inside itself
    // when the export is missing. Only a body that is actually marimo's
    // counts as built.
    fetch(wasmUrl(pageSlug))
      .then(async (response) => {
        const body = response.ok ? await response.text() : "";
        if (!cancelled) setWasmBuilt(body.includes("marimo"));
      })
      .catch(() => {
        if (!cancelled) setWasmBuilt(false);
      });
    return () => {
      cancelled = true;
    };
  }, [pageSlug]);

  function handleLiveUrlChange(value: string) {
    setLiveUrl(value);
    localStorage.setItem(LIVE_URL_KEY, value);
  }

  const src = source === "live" ? liveUrl : wasmUrl(pageSlug);
  const showIframe = source === "live" || wasmBuilt === true;

  return (
    <div className="notebook-panel" data-testid={`notebook-panel-${pageSlug}`}>
      <header className="notebook-panel-header">
        <span>Notebook</span>
        {isPresenter && (
          <span className="notebook-panel-source">
            <button
              type="button"
              className={source === "wasm" ? "active" : ""}
              onClick={() => setSource("wasm")}
              title="The in-browser WASM export every attendee gets."
            >
              Browser
            </button>
            <button
              type="button"
              className={source === "live" ? "active" : ""}
              onClick={() => setSource("live")}
              title="Your locally running marimo server, real hardware. Start it with: marimo edit notebooks/"
            >
              Live
            </button>
          </span>
        )}
        {isPresenter && source === "live" && (
          <input
            className="notebook-panel-url"
            value={liveUrl}
            onChange={(event) => handleLiveUrlChange(event.target.value)}
            spellCheck={false}
          />
        )}
        <a
          className="notebook-panel-open"
          href={src}
          target="_blank"
          rel="noreferrer"
          title="Open this notebook in its own tab."
        >
          <ArrowSquareOut size={12} /> Open
        </a>
        {!isEditing && <span className="notebook-panel-hint">Double-click to open</span>}
      </header>
      {showIframe ? (
        <iframe className="notebook-panel-frame" src={src} title={`${pageSlug} notebook`} />
      ) : (
        <div className="notebook-panel-missing">
          {wasmBuilt === null ? "Checking for the notebook build" : "Notebook not built. Run: just notebooks"}
        </div>
      )}
    </div>
  );
}
