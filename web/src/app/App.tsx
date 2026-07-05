import { useEffect, useState } from "react";
import { fetchHealth } from "../data/api";

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
    <main>
      <h1>EuroSciPy Chess Studio</h1>
      <p data-testid="backend-status">Backend: {status}</p>
    </main>
  );
}
