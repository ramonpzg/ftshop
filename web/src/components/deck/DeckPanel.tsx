import { ArrowSquareOut } from "@phosphor-icons/react";
import { useState } from "react";
import { resolveDeckUrl } from "../../calculations/deckUrl";
import { usePresenterState } from "../../lib/presenterContext";
import "./DeckPanel.css";

interface DeckPanelProps {
  defaultUrl: string;
  isEditing: boolean;
}

const DECK_URL_KEY = "euro-chess-studio:deck-url";

/**
 * The Slidev deck, embedded on the Presentation page. The deck runs as
 * its own server (just deck, port 3030); this panel just frames it.
 * Presenting from the board and presenting from the deck tab are both
 * fine; this exists so the three assets share one surface.
 */
export function DeckPanel({ defaultUrl, isEditing }: DeckPanelProps) {
  const { isPresenter } = usePresenterState();
  const [url, setUrl] = useState(() => localStorage.getItem(DECK_URL_KEY) ?? defaultUrl);
  // An attendee on the LAN gets a localhost deck URL rewritten to the
  // presenter's host; the shape's stored URL stays untouched.
  const displayUrl = resolveDeckUrl(url, window.location.hostname);

  function handleUrlChange(value: string) {
    setUrl(value);
    localStorage.setItem(DECK_URL_KEY, value);
  }

  return (
    <div className="deck-panel" data-testid="deck-panel">
      <header className="deck-panel-header">
        <span>Deck</span>
        {isPresenter && (
          <input
            className="deck-panel-url"
            value={url}
            onChange={(event) => handleUrlChange(event.target.value)}
            spellCheck={false}
            title="Where the Slidev server lives. Start it with: just deck"
          />
        )}
        <span className="deck-panel-hint-inline">Blank? Run: just deck</span>
        <a
          className="deck-panel-open"
          href={displayUrl}
          target="_blank"
          rel="noreferrer"
          title="Open the deck in its own tab. Presenter mode and speaker notes live there."
        >
          <ArrowSquareOut size={12} /> Open
        </a>
        {!isEditing && <span className="deck-panel-hint">Double-click to open</span>}
      </header>
      <iframe className="deck-panel-frame" src={displayUrl} title="Workshop deck" />
    </div>
  );
}
