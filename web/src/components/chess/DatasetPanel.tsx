import type { DatasetRow } from "../../data/api";
import "./DatasetPanel.css";

interface DatasetPanelProps {
  rows: DatasetRow[];
  maxRows?: number;
}

const SHAPE_LABELS: Record<string, string> = {
  pgn_prefix_to_move: "PGN prefix -> move",
  fen_to_move: "FEN -> move",
  fen_legal_moves_to_move: "FEN + legal moves -> move",
  board_tensor_to_move_class: "Board tensor -> move class",
  policy_value_to_move: "Policy + value labels",
  rl_trajectory: "RL trajectory",
};

export function DatasetPanel({ rows, maxRows = 6 }: DatasetPanelProps) {
  const recent = rows.slice(-maxRows).reverse();

  if (recent.length === 0) {
    return <p className="dataset-panel-empty">Make a move to generate dataset rows.</p>;
  }

  return (
    <div className="dataset-panel" data-testid="dataset-panel">
      {recent.map((row) => (
        <details key={row.id} className="dataset-row">
          <summary>{SHAPE_LABELS[row.shape] ?? row.shape}</summary>
          <pre>{JSON.stringify(row.payload, null, 2)}</pre>
        </details>
      ))}
    </div>
  );
}
