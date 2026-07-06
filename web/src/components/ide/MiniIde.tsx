import { ArrowSquareOut } from "@phosphor-icons/react";
import { python } from "@codemirror/lang-python";
import { yaml } from "@codemirror/lang-yaml";
import CodeMirror from "@uiw/react-codemirror";
import { getSnippetById, SNIPPETS } from "../../lib/snippets";
import "./MiniIde.css";

interface MiniIdeProps {
  selectedSnippetId: string | null;
  onSelectSnippet: (snippetId: string) => void;
}

const pythonLang = [python()];
const yamlLang = [yaml()];

// unsloth studio -p 8888, run on the presenter's machine.
const UNSLOTH_STUDIO_URL = "http://localhost:8888";

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
        <a
          className="mini-ide-tab mini-ide-studio-link"
          href={UNSLOTH_STUDIO_URL}
          target="_blank"
          rel="noreferrer"
          title="Opens your local Unsloth Studio. Launch it with: unsloth studio -p 8888"
        >
          Unsloth Studio <ArrowSquareOut size={10} />
        </a>
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
          extensions={snippet.language === "yaml" ? yamlLang : pythonLang}
          theme="dark"
          height="100%"
          basicSetup={{ lineNumbers: true, foldGutter: false }}
        />
      </div>
    </div>
  );
}
