import { useState } from "react";
import type { DatasetRow } from "../../data/api";
import "./DatasetPanel.css";

interface DatasetPanelProps {
  rows: DatasetRow[];
}

const SHAPE_LABELS: Record<string, string> = {
  pgn_prefix_to_move: "PGN prefix -> move",
  fen_to_move: "FEN -> move",
  fen_legal_moves_to_move: "FEN + legal moves -> move",
  board_tensor_to_move_class: "Board tensor -> move class",
  policy_value_to_move: "Policy + value labels",
  rl_trajectory: "RL trajectory",
};

const SHAPE_ORDER = Object.keys(SHAPE_LABELS);

/** One group per dataset shape, in teaching order. Groups are stable
 * across moves and their open state lives in React, not in the DOM:
 * open "FEN -> move", play on, and watch the newest row replace the
 * old one in place. That live update is the point of the panel. */
export function DatasetPanel({ rows }: DatasetPanelProps) {
  const [open, setOpen] = useState<Record<string, boolean>>({});

  const byShape = new Map<string, DatasetRow[]>();
  for (const row of rows) {
    const group = byShape.get(row.shape);
    if (group) {
      group.push(row);
    } else {
      byShape.set(row.shape, [row]);
    }
  }

  if (byShape.size === 0) {
    return <p className="dataset-panel-empty">Make a move to generate dataset rows.</p>;
  }

  const shapes = [
    ...SHAPE_ORDER.filter((shape) => byShape.has(shape)),
    ...[...byShape.keys()].filter((shape) => !SHAPE_ORDER.includes(shape)),
  ];

  function toggle(shape: string) {
    setOpen((prev) => ({ ...prev, [shape]: !prev[shape] }));
  }

  return (
    <div className="dataset-panel" data-testid="dataset-panel">
      {shapes.map((shape) => {
        const group = byShape.get(shape);
        if (!group) return null;
        const latest = group[group.length - 1];
        const isOpen = open[shape] === true;
        return (
          <section key={shape} className="dataset-row" data-shape={shape} data-open={isOpen}>
            <button
              type="button"
              className="dataset-row-toggle"
              onClick={() => toggle(shape)}
              data-testid={`dataset-shape-${shape}`}
            >
              <span>{SHAPE_LABELS[shape] ?? shape}</span>
              <span className="dataset-row-count">{group.length}</span>
            </button>
            {isOpen && <pre>{JSON.stringify(latest.payload, null, 2)}</pre>}
          </section>
        );
      })}
    </div>
  );
}
