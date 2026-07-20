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
    numerator: null,
    denominator: null,
    unit: null,
    direction: null,
    definition: null,
    version: null,
    scope_json: null,
    note: null,
    model: null,
    checkpoint: null,
    run_id: null,
    sample_ids: [],
    position_set_id: null,
    positions: [],
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

  test("computed metrics show their numerator and denominator", () => {
    render(
      <EvalPanel
        results={[
          makeResult({
            metric: "model_legal_move_rate",
            value: 0.5,
            numerator: 3,
            denominator: 6,
            definition: "legal replies / replies received",
          }),
        ]}
      />,
    );
    expect(screen.getByTestId("eval-count-model_legal_move_rate").textContent).toBe("3/6");
  });

  test("a cached metric renders its note instead of posing as live", () => {
    render(
      <EvalPanel
        results={[
          makeResult({
            metric: "centipawn_loss",
            source: "cached",
            note: "Illustrative cached example. A real run needs Stockfish.",
          }),
        ]}
      />,
    );
    expect(screen.getByTestId("eval-note-centipawn_loss").textContent).toContain("Illustrative");
  });

  test("shows only the latest of several runs for the same metric", () => {
    // Reproduces the reported bug: three runs over a growing move
    // history are three real, distinct rows (different position-set
    // windows), but the live panel should show the current state, not
    // every historical run.
    render(
      <EvalPanel
        results={[
          makeResult({
            id: "run_1",
            numerator: 1,
            denominator: 1,
            created_at: "2026-01-01T00:00:00+00:00",
          }),
          makeResult({
            id: "run_2",
            numerator: 2,
            denominator: 2,
            created_at: "2026-01-01T00:01:00+00:00",
          }),
          makeResult({
            id: "run_3",
            numerator: 3,
            denominator: 3,
            created_at: "2026-01-01T00:02:00+00:00",
          }),
        ]}
      />,
    );
    expect(screen.getAllByTestId("eval-panel")).toHaveLength(1);
    expect(screen.getByTestId("eval-count-legal_move_rate").textContent).toBe("3/3");
    // Only one row rendered for this metric, not three.
    expect(document.querySelectorAll(".eval-row")).toHaveLength(1);
  });

  test("keeps a base and an adapted checkpoint as separate, labelled rows", () => {
    render(
      <EvalPanel
        results={[
          makeResult({
            id: "base",
            metric: "model_legal_move_rate",
            model: "gemma-4-2b-local",
            checkpoint: "base",
          }),
          makeResult({
            id: "adapter",
            metric: "model_legal_move_rate",
            model: "gemma-4-2b-local",
            checkpoint: "adapter",
          }),
        ]}
      />,
    );
    expect(document.querySelectorAll(".eval-row")).toHaveLength(2);
    const scopes = [...document.querySelectorAll(".eval-scope")].map((el) => el.textContent);
    expect(scopes.sort()).toEqual(["gemma-4-2b-local adapter", "gemma-4-2b-local base"]);
  });
});
