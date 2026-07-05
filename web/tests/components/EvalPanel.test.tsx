import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, render, screen } from "@testing-library/react";
import { EvalPanel } from "../../src/components/eval/EvalPanel";
import type { EvalResult } from "../../src/data/api";

function makeResult(overrides: Partial<EvalResult> = {}): EvalResult {
  return {
    id: "eval_1",
    modality: "text",
    metric: "legal_move_rate",
    value: 1.0,
    workspace_id: null,
    source: "computed",
    created_at: "now",
    ...overrides,
  };
}

afterEach(() => {
  cleanup();
});

describe("EvalPanel", () => {
  test("shows an empty state with no results", () => {
    render(<EvalPanel results={[]} />);
    expect(screen.getByText("No eval results yet.")).toBeTruthy();
  });

  test("renders a human label and formatted value for each metric", () => {
    render(<EvalPanel results={[makeResult({ metric: "centipawn_loss", value: 38.512 })]} />);
    expect(screen.getByText("Centipawn Loss")).toBeTruthy();
    expect(screen.getByText("38.51")).toBeTruthy();
  });

  test("shows the source of each metric", () => {
    render(<EvalPanel results={[makeResult({ source: "cached" })]} />);
    expect(screen.getByText("cached")).toBeTruthy();
  });
});
