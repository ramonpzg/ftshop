import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
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

  test("groups rows by shape with a running count", () => {
    render(
      <DatasetPanel
        rows={[
          makeRow("1", "fen_to_move"),
          makeRow("2", "fen_to_move"),
          makeRow("3", "rl_trajectory"),
        ]}
      />,
    );
    expect(screen.getAllByRole("button").length).toBe(2);
    expect(screen.getByTestId("dataset-shape-fen_to_move").textContent).toContain("2");
  });

  test("shapes keep the teaching order regardless of arrival order", () => {
    render(
      <DatasetPanel rows={[makeRow("1", "rl_trajectory"), makeRow("2", "pgn_prefix_to_move")]} />,
    );
    const labels = screen.getAllByRole("button").map((el) => el.textContent);
    expect(labels[0]).toContain("PGN prefix");
    expect(labels[1]).toContain("RL trajectory");
  });

  test("an open group stays open and shows the newest payload as rows arrive", () => {
    const { rerender } = render(<DatasetPanel rows={[makeRow("1", "fen_to_move")]} />);
    fireEvent.click(screen.getByTestId("dataset-shape-fen_to_move"));
    expect(screen.getByText((text) => text.includes('"id": "1"'))).toBeTruthy();

    rerender(<DatasetPanel rows={[makeRow("1", "fen_to_move"), makeRow("2", "fen_to_move")]} />);

    expect(screen.getByText((text) => text.includes('"id": "2"'))).toBeTruthy();
    expect(screen.getByTestId("dataset-shape-fen_to_move").textContent).toContain("2");
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
