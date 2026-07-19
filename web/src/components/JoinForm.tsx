import { type FormEvent, useState } from "react";
import { joinWorkshop, type JoinResult } from "../actions/joinWorkshop";
import "./JoinForm.css";

interface JoinFormProps {
  ready: boolean;
  onJoined: (result: JoinResult) => void;
}

export function JoinForm({ ready, onJoined }: JoinFormProps) {
  const [name, setName] = useState("");
  const [status, setStatus] = useState<"idle" | "joining" | "error">("idle");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!ready || !name.trim()) return;
    setStatus("joining");
    try {
      const result = await joinWorkshop(name.trim());
      onJoined(result);
    } catch {
      setStatus("error");
    }
  }

  return (
    <div className="join-form-overlay">
      <form className="join-form" onSubmit={handleSubmit}>
        <h1>EuroSciPy Chess Studio</h1>
        <p>Same recipe, different results. Fine-tuning across modalities.</p>
        <label htmlFor="join-name">Your name</label>
        <input
          id="join-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Ada"
        />
        <button type="submit" disabled={!ready || !name.trim() || status === "joining"}>
          {ready ? "Join" : "Loading canvas..."}
        </button>
        {status === "error" && (
          <p className="join-form-error">Could not join. Check the backend is running.</p>
        )}
      </form>
    </div>
  );
}
