import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, render, screen } from "@testing-library/react";
import { DatasetPanel } from "../../src/components/chess/DatasetPanel";
import type { DatasetRow } from "../../src/data/api";

function makeRow(id: string, shape: string): DatasetRow {
  return {
    id,
    workspace_id: "workspace_1",
    move_id: null,
    shape,
    payload: { id },
    created_at: "now",
  };
}

afterEach(() => {
  cleanup();
});

describe("DatasetPanel", () => {
  test("shows an empty state with no rows", () => {
    render(<DatasetPanel rows={[]} />);
    expect(screen.getByText("Make a move to generate dataset rows.")).toBeTruthy();
  });

  test("shows the most recent row first", () => {
    render(<DatasetPanel rows={[makeRow("1", "fen_to_move"), makeRow("2", "rl_trajectory")]} />);
    const summaries = screen.getAllByRole("group").map((el) => el.textContent);
    expect(summaries[0]).toContain("RL trajectory");
  });

  test("caps the number of rows shown", () => {
    const rows = Array.from({ length: 20 }, (_, i) => makeRow(String(i), "fen_to_move"));
    render(<DatasetPanel rows={rows} maxRows={3} />);
    expect(screen.getAllByRole("group").length).toBe(3);
  });

  test("uses a human label for known shapes", () => {
    render(<DatasetPanel rows={[makeRow("1", "fen_to_move")]} />);
    expect(screen.getByText("FEN -> move")).toBeTruthy();
  });

  test("falls back to the raw shape name for unknown shapes", () => {
    render(<DatasetPanel rows={[makeRow("1", "something_new")]} />);
    expect(screen.getByText("something_new")).toBeTruthy();
  });
});
