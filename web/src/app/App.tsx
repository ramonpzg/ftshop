import { useEffect, useState } from "react";
import { ChessStudioCanvas } from "../components/tldraw/ChessStudioCanvas";
import { fetchHealth } from "../data/api";
import "./App.css";

type BackendStatus = "checking" | "connected" | "unreachable";

export function App() {
  const [status, setStatus] = useState<BackendStatus>("checking");

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then(() => {
        if (!cancelled) setStatus("connected");
      })
      .catch(() => {
        if (!cancelled) setStatus("unreachable");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="app-shell">
      <div className="status-badge" data-testid="backend-status">
        Backend: {status}
      </div>
      <ChessStudioCanvas />
    </div>
  );
}
