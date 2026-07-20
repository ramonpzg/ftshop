/** Long-content fit guards. The stepper panels reserve fixed heights,
 * so payloads and captions have hard budgets; exceeding them clips on
 * a 1280x720 projector. These limits were set from the rendered deck,
 * not guessed. */

import { describe, expect, test } from "bun:test";
import { NOTATION_EXAMPLE } from "../lib/chess";
import { DATASET_SHAPES } from "../lib/datasetShapes";
import { COST_ROWS, TEXT_COMPARE_PLACEHOLDER } from "../lib/fixtures";

describe("dataset shapes are honest and fit their panel", () => {
  for (const shape of DATASET_SHAPES) {
    test(`${shape.name} payload is strictly valid JSON`, () => {
      expect(() => JSON.parse(shape.payload)).not.toThrow();
    });

    test(`${shape.name} payload and point stay inside the reserved panel`, () => {
      // The panel wraps at roughly 55 mono characters; the reserved
      // height holds nine wrapped rows. Estimate wrapped rows rather
      // than capping raw line length, since full FENs must not be
      // truncated just to fit one line.
      const wrappedRows = shape.payload
        .split("\n")
        .reduce((rows, line) => rows + Math.max(1, Math.ceil(line.length / 55)), 0);
      expect(wrappedRows).toBeLessThanOrEqual(9);
      expect(shape.point.length).toBeLessThanOrEqual(160);
    });
  }
});

describe("notation representations fit their panel", () => {
  for (const rep of NOTATION_EXAMPLE.representations) {
    test(`${rep.name} value and point fit`, () => {
      expect(rep.value.length).toBeLessThanOrEqual(80);
      expect(rep.point.length).toBeLessThanOrEqual(120);
    });
  }
});

describe("cost rows fit one line each", () => {
  for (const row of COST_ROWS) {
    test(`${row.modality} cells stay short enough for the six-column table`, () => {
      for (const cell of [row.task, row.target, row.local, row.api, row.cost]) {
        expect(cell.length).toBeLessThanOrEqual(44);
      }
    });
  }
});

describe("compare fixture fits", () => {
  test("outputs and regression line fit their reserved rows", () => {
    expect(TEXT_COMPARE_PLACEHOLDER.input.length).toBeLessThanOrEqual(70);
    expect(TEXT_COMPARE_PLACEHOLDER.regression.length).toBeLessThanOrEqual(70);
    expect(TEXT_COMPARE_PLACEHOLDER.metrics.length).toBeLessThanOrEqual(4);
  });
});
