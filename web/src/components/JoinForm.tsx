import { type FormEvent, useState } from "react";
import type { Editor } from "tldraw";
import { joinWorkshop, type JoinResult } from "../actions/joinWorkshop";
import "./JoinForm.css";

interface JoinFormProps {
  editor: Editor | null;
  onJoined: (result: JoinResult) => void;
}

export function JoinForm({ editor, onJoined }: JoinFormProps) {
  const [name, setName] = useState("");
  const [status, setStatus] = useState<"idle" | "joining" | "error">("idle");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!editor || !name.trim()) return;
    setStatus("joining");
    try {
      const result = await joinWorkshop(editor, name.trim());
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
        <button type="submit" disabled={!editor || !name.trim() || status === "joining"}>
          {editor ? "Join" : "Loading canvas..."}
        </button>
        {status === "error" && (
          <p className="join-form-error">Could not join. Check the backend is running.</p>
        )}
      </form>
    </div>
  );
}
