import { python } from "@codemirror/lang-python";
import CodeMirror from "@uiw/react-codemirror";
import { getSnippetById, SNIPPETS } from "../../lib/snippets";
import "./MiniIde.css";

interface MiniIdeProps {
  selectedSnippetId: string | null;
  onSelectSnippet: (snippetId: string) => void;
}

const pythonLang = [python()];

export function MiniIde({ selectedSnippetId, onSelectSnippet }: MiniIdeProps) {
  const activeId = selectedSnippetId ?? SNIPPETS[0].id;
  const snippet = getSnippetById(activeId);

  return (
    <div className="mini-ide">
      <div className="mini-ide-tabs">
        {SNIPPETS.map((s) => (
          <button
            key={s.id}
            type="button"
            className={s.id === activeId ? "mini-ide-tab mini-ide-tab-active" : "mini-ide-tab"}
            onClick={() => onSelectSnippet(s.id)}
            data-testid={`snippet-tab-${s.id}`}
          >
            {s.label}
          </button>
        ))}
      </div>
      <div className="mini-ide-window">
        <div className="mini-ide-window-bar" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <CodeMirror
          key={activeId}
          value={snippet.code}
          extensions={pythonLang}
          theme="dark"
          height="100%"
          basicSetup={{ lineNumbers: true, foldGutter: false }}
        />
      </div>
    </div>
  );
}
